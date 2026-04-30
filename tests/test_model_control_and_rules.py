import json

import pytest

from app.backend.schemas.model import (
    ModelControlUpdate,
    ModelCreateRequest,
    ProviderControlUpdate,
    ProviderCreateRequest,
)
from app.backend.schemas.rule_template import RuleAssignment, RuleTemplateUpsert
from app.backend.services.coordinator_selection_service import (
    clear_coordinator_selection_service_cache,
    get_coordinator_selection_service,
)
from app.backend.services.model_control_service import get_model_control_service
from app.backend.services.model_loader import load_model_catalog
from app.backend.services.model_registry_service import (
    clear_model_registry_service_cache,
    get_model_registry_service,
)
from app.backend.services.model_routing_service import clear_model_routing_service_cache
from app.backend.services.rule_template_service import (
    clear_rule_template_service_cache,
    get_rule_template_service,
)
from app.backend.services.task_service import clear_task_service_cache


@pytest.fixture()
def isolated_model_control_storage(tmp_path, monkeypatch):
    control_dir = tmp_path / "model_control"
    control_dir.mkdir(parents=True, exist_ok=True)
    overrides_path = control_dir / "model_overrides.json"
    provider_overrides_path = control_dir / "provider_overrides.json"
    provider_secrets_path = control_dir / "provider_secrets.json"
    templates_path = control_dir / "rule_templates.json"
    overrides_path.write_text('{"models": {}}', encoding="utf-8")
    provider_overrides_path.write_text('{"providers": {}}', encoding="utf-8")
    provider_secrets_path.write_text('{"api_keys": {}}', encoding="utf-8")
    templates_path.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "template_id": "code-engineering-default",
                        "display_name": "Code Engineering Default",
                        "description": "Default multi-role template",
                        "preset_mode": "code-engineering",
                        "task_types": ["planning", "review"],
                        "default_coordinator_model_id": "gpt-5.4",
                        "enabled": True,
                        "is_default": True,
                        "trigger_keywords": ["backend", "frontend", "login"],
                        "assignments": [
                            {
                                "role": "frontend",
                                "responsibility": "UI flow",
                                "model_id": "kimi-2.5",
                            }
                        ],
                        "notes": "",
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    from app.backend.services import model_loader, rule_template_loader

    monkeypatch.setattr(model_loader, "MODEL_CONTROL_DIR", control_dir)
    monkeypatch.setattr(model_loader, "MODEL_OVERRIDES_PATH", overrides_path)
    monkeypatch.setattr(model_loader, "PROVIDER_OVERRIDES_PATH", provider_overrides_path)
    monkeypatch.setattr(model_loader, "PROVIDER_SECRETS_PATH", provider_secrets_path)
    monkeypatch.setattr(rule_template_loader, "RULE_TEMPLATES_PATH", templates_path)

    clear_model_registry_service_cache()
    clear_model_routing_service_cache()
    clear_rule_template_service_cache()
    clear_coordinator_selection_service_cache()
    clear_task_service_cache()

    yield

    clear_model_registry_service_cache()
    clear_model_routing_service_cache()
    clear_rule_template_service_cache()
    clear_coordinator_selection_service_cache()
    clear_task_service_cache()


def test_model_control_updates_priority_and_enabled_state(isolated_model_control_storage):
    service = get_model_control_service()

    updated = service.update_model(
        "gpt-5.4",
        ModelControlUpdate(priority="low", enabled=False),
    )

    assert updated.model_id == "gpt-5.4"
    assert updated.priority == "low"
    assert updated.enabled is False
    registry_model = get_model_registry_service().get_model("gpt-5.4")
    assert registry_model is not None
    assert registry_model.priority == "low"
    assert registry_model.enabled is False


def test_model_control_updates_provider_overrides(isolated_model_control_storage):
    service = get_model_control_service()

    updated = service.update_provider(
        "openai",
        ProviderControlUpdate(
            enabled=False,
            api_base_url="https://openai.test/v1",
            api_key_env="MIND_TEST_OPENAI_KEY",
            protocol="openai",
            anthropic_api_base_url="https://openai.test/anthropic",
        ),
    )

    assert updated.provider_id == "openai"
    assert updated.enabled is False
    assert updated.api_base_url == "https://openai.test/v1"
    assert updated.api_key_env == "MIND_TEST_OPENAI_KEY"
    assert updated.protocol == "openai"
    assert updated.anthropic_api_base_url == "https://openai.test/anthropic"

    registry_provider = get_model_registry_service().get_provider("openai")
    assert registry_provider is not None
    assert registry_provider.enabled is False
    assert registry_provider.api_base_url == "https://openai.test/v1"
    assert registry_provider.metadata["api_key_env"] == "MIND_TEST_OPENAI_KEY"
    assert registry_provider.metadata["protocol"] == "openai"
    assert registry_provider.metadata["anthropic_api_base_url"] == (
        "https://openai.test/anthropic"
    )


def test_model_control_creates_user_provider_model_and_secret(
    isolated_model_control_storage,
):
    service = get_model_control_service()

    provider = service.create_provider(
        ProviderCreateRequest(
            provider_id="custom-ark",
            display_name="Custom Ark",
            description="User-owned Ark endpoint",
            api_base_url="https://ark.example/v3",
            protocol="openai-compatible",
            api_key="secret-value",
            api_key_env="CUSTOM_ARK_KEY",
        )
    )
    model = service.create_model(
        ModelCreateRequest(
            model_id="custom-doubao",
            display_name="Custom Doubao",
            provider_id="custom-ark",
            upstream_model="doubao-seed-2.0-lite",
            priority="high",
            supported_preset_modes=["code-engineering"],
            supported_roles=["backend"],
        )
    )

    assert provider.is_custom is True
    assert provider.api_key_configured is True
    assert "secret-value" not in provider.model_dump_json()
    assert model.is_custom is True
    assert model.provider_id == "custom-ark"
    assert any(item.provider_id == "custom-ark" for item in service.list_custom_providers())
    assert any(item.model_id == "custom-doubao" for item in service.list_custom_models())

    registry = get_model_registry_service()
    assert registry.get_provider("custom-ark") is not None
    assert registry.get_model("custom-doubao") is not None


def test_provider_connection_uses_user_saved_api_key(
    isolated_model_control_storage,
    monkeypatch,
):
    service = get_model_control_service()
    service.create_provider(
        ProviderCreateRequest(
            provider_id="custom-ark",
            display_name="Custom Ark",
            api_base_url="https://ark.example/v3",
            protocol="openai-compatible",
            api_key="secret-value",
        )
    )

    class FakeResponse:
        status_code = 200

    def fake_get(url, headers, timeout):
        assert url == "https://ark.example/v3/models"
        assert headers["Authorization"] == "Bearer secret-value"
        assert timeout == 10
        return FakeResponse()

    monkeypatch.setattr(
        "app.backend.services.model_control_service.requests.get",
        fake_get,
    )

    result = service.test_provider_connection("custom-ark")

    assert result.ok is True
    assert result.status == "connected"
    assert result.api_key_configured is True


def test_rule_template_upsert_and_selection(isolated_model_control_storage):
    templates = get_rule_template_service()

    templates.upsert_template(
        RuleTemplateUpsert(
            template_id="paper-style",
            display_name="Paper Style",
            description="Paper review rule",
            preset_mode="paper-revision",
            task_types=["writing"],
            default_coordinator_model_id="gpt-5.4",
            enabled=True,
            is_default=True,
            trigger_keywords=["paper", "abstract", "journal"],
            assignments=[
                RuleAssignment(
                    role="style-reviewer",
                    responsibility="Review writing style",
                    model_id="kimi-2.5",
                ),
                RuleAssignment(
                    role="reviewer",
                    responsibility="Review content",
                    model_id="glm-5.1",
                ),
            ],
            notes="",
        )
    )

    selection = get_coordinator_selection_service().select_template(
        prompt="Please revise the journal paper abstract.",
        preset_mode="paper-revision",
        task_type="writing",
    )

    assert selection is not None
    assert selection.template_id == "paper-style"
    assert selection.coordinator_model_id == "gpt-5.4"
    assert selection.role_model_overrides["style-reviewer"] == "kimi-2.5"


def test_rule_template_validation_rejects_unknown_model(isolated_model_control_storage):
    templates = get_rule_template_service()

    with pytest.raises(ValueError):
        templates.upsert_template(
            RuleTemplateUpsert(
                template_id="bad-template",
                display_name="Bad Template",
                description="Broken model reference",
                preset_mode="code-engineering",
                task_types=[],
                default_coordinator_model_id="gpt-5.4",
                enabled=True,
                is_default=False,
                trigger_keywords=[],
                assignments=[
                    RuleAssignment(
                        role="frontend",
                        responsibility="Frontend work",
                        model_id="missing-model",
                    )
                ],
                notes="",
            )
        )
