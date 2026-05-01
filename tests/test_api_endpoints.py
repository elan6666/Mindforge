import json

import pytest
from fastapi.testclient import TestClient

from app.backend.core.config import clear_settings_cache
from app.backend.services.coordinator_selection_service import (
    clear_coordinator_selection_service_cache,
)
from app.backend.services.academic_context_service import clear_academic_context_service_cache
from app.backend.services.approval_service import clear_approval_service_cache
from app.backend.services.github_context_service import clear_github_context_service_cache
from app.backend.services.history_service import clear_history_service_cache
from app.backend.services.model_registry_service import clear_model_registry_service_cache
from app.backend.services.model_routing_service import clear_model_routing_service_cache
from app.backend.services.rule_template_service import clear_rule_template_service_cache
from app.backend.main import create_app
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
    templates_path.write_text(json.dumps({"templates": []}, indent=2), encoding="utf-8")

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
    clear_academic_context_service_cache()
    clear_task_service_cache()

    yield

    clear_model_registry_service_cache()
    clear_model_routing_service_cache()
    clear_rule_template_service_cache()
    clear_coordinator_selection_service_cache()
    clear_academic_context_service_cache()
    clear_task_service_cache()


@pytest.fixture()
def isolated_history_storage(tmp_path, monkeypatch):
    db_path = tmp_path / "mindforge-test.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))
    clear_settings_cache()
    clear_history_service_cache()
    clear_approval_service_cache()
    clear_github_context_service_cache()
    clear_academic_context_service_cache()
    clear_task_service_cache()

    yield

    clear_task_service_cache()
    clear_academic_context_service_cache()
    clear_approval_service_cache()
    clear_history_service_cache()
    clear_github_context_service_cache()
    clear_settings_cache()


@pytest.fixture()
def mocked_github_api(monkeypatch):
    class DummyResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/repos/openai/openai-python"):
            return DummyResponse(
                200,
                {
                    "full_name": "openai/openai-python",
                    "description": "OpenAI Python SDK",
                    "html_url": "https://github.com/openai/openai-python",
                    "default_branch": "main",
                    "language": "Python",
                    "stargazers_count": 100,
                    "forks_count": 50,
                    "open_issues_count": 25,
                    "visibility": "public",
                },
            )
        if url.endswith("/repos/openai/openai-python/issues/123"):
            return DummyResponse(
                200,
                {
                    "number": 123,
                    "title": "Bug report",
                    "state": "open",
                    "html_url": "https://github.com/openai/openai-python/issues/123",
                    "user": {"login": "octocat"},
                    "labels": [{"name": "bug"}],
                    "comments": 4,
                    "body": "Issue body for testing",
                },
            )
        if url.endswith("/repos/openai/openai-python/pulls/9"):
            return DummyResponse(
                200,
                {
                    "number": 9,
                    "title": "Fix bug",
                    "state": "open",
                    "html_url": "https://github.com/openai/openai-python/pull/9",
                    "user": {"login": "octocat"},
                    "labels": [{"name": "enhancement"}],
                    "comments": 2,
                    "review_comments": 1,
                    "draft": False,
                    "merged": False,
                    "head": {"ref": "feature-branch"},
                    "base": {"ref": "main"},
                    "body": "PR body for testing",
                },
            )
        return DummyResponse(404, {"message": "Not Found"})

    monkeypatch.setattr(
        "app.backend.services.github_context_service.requests.get",
        fake_get,
    )
    clear_github_context_service_cache()
    clear_task_service_cache()
    yield
    clear_task_service_cache()
    clear_github_context_service_cache()


@pytest.fixture()
def mocked_academic_pages(monkeypatch):
    class DummyResponse:
        status_code = 200
        text = ""

        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=None, headers=None):
        if "guidelines" in url:
            return DummyResponse(
                "<html><title>Author Guidelines</title><body>Use structured abstracts and concise language.</body></html>"
            )
        return DummyResponse(
            "<html><title>Reference Paper</title><body>The paper foregrounds contributions before method details.</body></html>"
        )

    monkeypatch.setattr(
        "app.backend.services.academic_context_service.requests.get",
        fake_get,
    )
    clear_academic_context_service_cache()
    clear_task_service_cache()
    yield
    clear_task_service_cache()
    clear_academic_context_service_cache()


def test_health_endpoint_returns_liveness_payload():
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "mindforge",
    }


def test_tasks_endpoint_returns_mock_openhands_response(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={"prompt": "Analyze repository structure"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "completed"
    assert body["data"]["provider"] == "mock-openhands"
    assert body["data"]["metadata"]["resolved_preset_mode"] == "default"
    assert body["data"]["metadata"]["task_model_selection"]["model_id"] == "gpt-5.4"


def test_tasks_endpoint_persists_composer_metadata_to_history(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Use attached context without prompt stuffing",
            "attachments": [
                {
                    "id": "upload-1",
                    "name": "notes.txt",
                    "mime_type": "text/plain",
                    "size_bytes": 42,
                    "excerpt": "Important uploaded notes",
                    "metadata": {"source": "composer", "line_count": 2},
                }
            ],
            "tool_flags": {"deep_analysis": True},
            "web_search": True,
            "canvas": True,
        },
    )

    body = response.json()
    task_id = body["data"]["metadata"]["task_id"]

    assert response.status_code == 200
    assert body["data"]["metadata"]["attachments"][0]["text_excerpt"] == (
        "Important uploaded notes"
    )
    assert body["data"]["metadata"]["tool_flags"]["web_search"] is True
    assert body["data"]["metadata"]["tool_flags"]["deep_analysis"] is True
    assert body["data"]["metadata"]["tool_flags"]["canvas"] is True
    assert body["data"]["metadata"]["task_model_selection"]["model_id"] == "gpt-5.4"

    history_response = client.get(f"/api/history/tasks/{task_id}")
    history_body = history_response.json()

    assert history_response.status_code == 200
    assert history_body["metadata"]["attachments"][0]["metadata"]["source"] == "composer"
    assert history_body["metadata"]["tool_flags"]["web_search"] is True
    assert history_body["metadata"]["tool_flags"]["canvas"] is True
    assert history_body["metadata"]["task_model_selection"]["model_id"] == "gpt-5.4"


def test_tasks_endpoint_persists_conversation_context_to_history(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Continue with implementation risks",
            "conversation_id": "conversation-web-1",
            "conversation_history": [
                {"role": "user", "content": "Plan this feature", "task_id": "task-1"},
                {
                    "role": "assistant",
                    "content": "Use a staged rollout",
                    "task_id": "task-1",
                },
            ],
        },
    )

    body = response.json()
    task_id = body["data"]["metadata"]["task_id"]

    assert response.status_code == 200
    assert body["data"]["metadata"]["conversation_id"] == "conversation-web-1"
    assert body["data"]["metadata"]["conversation_turn_count"] == 3

    history_response = client.get(f"/api/history/tasks/{task_id}")
    history_body = history_response.json()

    assert history_response.status_code == 200
    assert history_body["request_payload"]["conversation_id"] == "conversation-web-1"
    assert history_body["metadata"]["conversation_history"][1]["role"] == "assistant"
    assert history_body["metadata"]["conversation_history"][1]["content"] == (
        "Use a staged rollout"
    )


def test_tasks_endpoint_returns_structured_400_for_unknown_preset(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={"prompt": "Analyze repository structure", "preset_mode": "bad-preset"},
    )

    body = response.json()

    assert response.status_code == 400
    assert body["status"] == "failed"
    assert "Unknown preset_mode" in body["error_message"]


def test_presets_endpoint_returns_available_presets(isolated_history_storage):
    client = TestClient(create_app())

    response = client.get("/api/presets")

    body = response.json()

    assert response.status_code == 200
    assert any(item["preset_mode"] == "code-engineering" for item in body)
    assert any(item["preset_mode"] == "paper-revision" for item in body)


def test_provider_and_model_endpoints_return_registry_data(isolated_history_storage):
    client = TestClient(create_app())

    provider_response = client.get("/api/providers")
    model_response = client.get("/api/models")

    assert provider_response.status_code == 200
    assert any(item["provider_id"] == "openai" for item in provider_response.json())
    assert any(item["provider_id"] == "volces-ark" for item in provider_response.json())

    assert model_response.status_code == 200
    assert any(item["model_id"] == "gpt-5.4" for item in model_response.json())
    assert any(
        item["model_id"] == "doubao-seed-2.0-lite"
        for item in model_response.json()
    )


def test_code_engineering_tasks_endpoint_returns_orchestration_trace(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Plan backend work",
            "preset_mode": "code-engineering",
            "repo_path": ".",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["data"]["provider"] == "multi-stage-orchestrator"
    trace = body["data"]["metadata"]["orchestration"]
    assert len(trace["stages"]) == 4
    assert trace["stages"][0]["role"] == "project-manager"
    assert trace["stages"][0]["model"] == "gpt-5.4"
    assert body["data"]["metadata"]["repo_analysis"]["status"] == "analyzed"
    assert body["data"]["metadata"]["task_model_selection"]["model_id"] == "gpt-5.4"


def test_paper_revision_tasks_endpoint_persists_academic_context(
    isolated_history_storage,
    mocked_academic_pages,
):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Revise this paper abstract for the target journal.",
            "preset_mode": "paper-revision",
            "task_type": "writing",
            "journal_name": "Example Journal",
            "journal_url": "https://journal.example/guidelines",
            "reference_paper_urls": ["https://paper.example/reference"],
        },
    )

    body = response.json()
    task_id = body["data"]["metadata"]["task_id"]

    assert response.status_code == 200
    assert body["data"]["provider"] == "multi-stage-orchestrator"
    trace = body["data"]["metadata"]["orchestration"]
    assert trace["strategy"] == "serial-paper-revision"
    assert len(trace["stages"]) == 6
    assert trace["stages"][0]["role"] == "standards-editor"
    assert trace["stages"][-1]["role"] == "final-reviewer"
    assert body["data"]["metadata"]["academic_context"]["journal"]["title"] == (
        "Author Guidelines"
    )
    assert body["data"]["metadata"]["academic_context"]["reference_papers"][0]["title"] == (
        "Reference Paper"
    )

    history_response = client.get(f"/api/history/tasks/{task_id}")
    assert history_response.status_code == 200
    assert history_response.json()["metadata"]["academic_context"]["journal"]["status"] == (
        "fetched"
    )


def test_tasks_endpoint_returns_400_for_unknown_model_override(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Analyze repository structure",
            "model_override": "missing-model",
        },
    )

    body = response.json()

    assert response.status_code == 400
    assert body["status"] == "failed"
    assert "missing-model" in body["error_message"]


def test_code_engineering_api_honors_role_model_overrides(isolated_history_storage):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Plan backend work",
            "preset_mode": "code-engineering",
            "role_model_overrides": {"frontend": "gpt-5.4"},
        },
    )

    body = response.json()

    assert response.status_code == 200
    trace = body["data"]["metadata"]["orchestration"]
    assert trace["stages"][2]["role"] == "frontend"
    assert trace["stages"][2]["model"] == "gpt-5.4"
    assert (
        trace["stages"][2]["metadata"]["model_selection"]["selection_source"]
        == "explicit-role-override"
    )


def test_control_models_endpoint_updates_model_state(isolated_model_control_storage):
    client = TestClient(create_app())

    update_response = client.put(
        "/api/control/models/gpt-5.4",
        json={"priority": "low", "enabled": False},
    )
    models_response = client.get("/api/models")

    assert update_response.status_code == 200
    assert update_response.json()["priority"] == "low"
    assert update_response.json()["enabled"] is False
    assert any(
        item["model_id"] == "gpt-5.4"
        and item["priority"] == "low"
        and item["enabled"] is False
        for item in models_response.json()
    )


def test_control_providers_endpoint_updates_provider_config(
    isolated_model_control_storage,
    monkeypatch,
):
    client = TestClient(create_app())
    monkeypatch.setenv("MIND_TEST_OPENAI_KEY", "secret-value")

    update_response = client.put(
        "/api/control/providers/openai",
        json={
            "enabled": False,
            "api_base_url": "https://openai.test/v1",
            "api_key_env": "MIND_TEST_OPENAI_KEY",
            "protocol": "openai",
            "anthropic_api_base_url": "https://openai.test/anthropic",
        },
    )
    control_response = client.get("/api/control/providers")
    registry_response = client.get("/api/providers")

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["provider_id"] == "openai"
    assert body["enabled"] is False
    assert body["api_base_url"] == "https://openai.test/v1"
    assert body["api_key_env"] == "MIND_TEST_OPENAI_KEY"
    assert body["api_key_configured"] is True
    assert body["protocol"] == "openai"
    assert body["anthropic_api_base_url"] == "https://openai.test/anthropic"
    assert "secret-value" not in str(body)
    assert any(
        item["provider_id"] == "openai"
        and item["api_base_url"] == "https://openai.test/v1"
        for item in control_response.json()
    )
    assert any(
        item["provider_id"] == "openai" and item["enabled"] is False
        for item in registry_response.json()
    )
    from app.backend.services import model_loader

    saved_overrides = model_loader.PROVIDER_OVERRIDES_PATH.read_text(encoding="utf-8")
    assert "MIND_TEST_OPENAI_KEY" in saved_overrides
    assert "secret-value" not in saved_overrides


def test_control_provider_connection_endpoint_can_be_mocked(
    isolated_model_control_storage,
    monkeypatch,
):
    client = TestClient(create_app())
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")

    class FakeResponse:
        status_code = 200

    def fake_get(url, headers, timeout):
        assert url == "https://api.openai.com/v1/models"
        assert headers["Authorization"] == "Bearer secret-value"
        assert timeout == 10
        return FakeResponse()

    monkeypatch.setattr(
        "app.backend.services.model_control_service.requests.get",
        fake_get,
    )

    response = client.post("/api/control/providers/openai/test")

    assert response.status_code == 200
    body = response.json()
    assert body["provider_id"] == "openai"
    assert body["ok"] is True
    assert body["status"] == "connected"
    assert body["api_key_env"] == "OPENAI_API_KEY"
    assert body["api_key_configured"] is True
    assert body["upstream_status"] == 200
    assert "secret-value" not in str(body)


def test_control_provider_update_rejects_invalid_protocol(isolated_model_control_storage):
    client = TestClient(create_app())

    response = client.put(
        "/api/control/providers/openai",
        json={"protocol": "unsupported-protocol"},
    )

    assert response.status_code == 400
    assert "Unsupported provider protocol" in response.json()["detail"]


def test_control_provider_update_rejects_invalid_url(isolated_model_control_storage):
    client = TestClient(create_app())

    response = client.put(
        "/api/control/providers/openai",
        json={"api_base_url": "not-a-url"},
    )

    assert response.status_code == 400
    assert "Provider URLs must start" in response.json()["detail"]


def test_control_user_provider_and_model_crud(isolated_model_control_storage):
    client = TestClient(create_app())

    provider_response = client.post(
        "/api/control/providers",
        json={
            "provider_id": "custom-ark",
            "display_name": "Custom Ark",
            "description": "User provider",
            "api_base_url": "https://ark.example/v3",
            "protocol": "openai-compatible",
            "api_key": "secret-value",
            "api_key_env": "CUSTOM_ARK_KEY",
        },
    )
    model_response = client.post(
        "/api/control/models",
        json={
            "model_id": "custom-doubao",
            "display_name": "Custom Doubao",
            "provider_id": "custom-ark",
            "upstream_model": "doubao-seed-2.0-lite",
            "priority": "high",
            "supported_preset_modes": ["code-engineering"],
        },
    )
    providers_response = client.get("/api/control/user-providers")
    models_response = client.get("/api/control/user-models")

    assert provider_response.status_code == 201
    provider_body = provider_response.json()
    assert provider_body["provider_id"] == "custom-ark"
    assert provider_body["is_custom"] is True
    assert provider_body["api_key_configured"] is True
    assert "secret-value" not in str(provider_body)
    assert model_response.status_code == 201
    assert model_response.json()["is_custom"] is True
    assert any(item["provider_id"] == "custom-ark" for item in providers_response.json())
    assert any(item["model_id"] == "custom-doubao" for item in models_response.json())

    delete_response = client.delete("/api/control/providers/custom-ark")
    assert delete_response.status_code == 204
    assert client.get("/api/control/user-providers").json() == []
    assert client.get("/api/control/user-models").json() == []


def test_rule_template_endpoints_support_crud(isolated_model_control_storage):
    client = TestClient(create_app())

    create_response = client.post(
        "/api/control/rule-templates",
        json={
            "template_id": "paper-style",
            "display_name": "Paper Style",
            "description": "Paper review template",
            "preset_mode": "paper-revision",
            "task_types": ["writing"],
            "default_coordinator_model_id": "gpt-5.4",
            "enabled": True,
            "is_default": True,
            "trigger_keywords": ["paper", "journal"],
            "assignments": [
                {
                    "role": "style-reviewer",
                    "responsibility": "Review style",
                    "model_id": "kimi-2.5",
                }
            ],
            "notes": "test template",
        },
    )
    list_response = client.get("/api/control/rule-templates")
    delete_response = client.delete("/api/control/rule-templates/paper-style")

    assert create_response.status_code == 201
    assert create_response.json()["template_id"] == "paper-style"
    assert list_response.status_code == 200
    assert any(item["template_id"] == "paper-style" for item in list_response.json())
    assert delete_response.status_code == 204


def test_rule_template_update_endpoint_persists_changes(isolated_model_control_storage):
    client = TestClient(create_app())

    client.post(
        "/api/control/rule-templates",
        json={
            "template_id": "paper-style",
            "display_name": "Paper Style",
            "description": "Paper review template",
            "preset_mode": "paper-revision",
            "task_types": ["writing"],
            "default_coordinator_model_id": "gpt-5.4",
            "enabled": True,
            "is_default": True,
            "trigger_keywords": ["paper"],
            "assignments": [
                {
                    "role": "style-reviewer",
                    "responsibility": "Review style",
                    "model_id": "kimi-2.5",
                }
            ],
            "notes": "initial",
        },
    )

    update_response = client.put(
        "/api/control/rule-templates/paper-style",
        json={
            "template_id": "paper-style",
            "display_name": "Paper Style Updated",
            "description": "Updated paper review template",
            "preset_mode": "paper-revision",
            "task_types": ["writing", "review"],
            "default_coordinator_model_id": "gpt-5.4",
            "enabled": True,
            "is_default": False,
            "trigger_keywords": ["paper", "journal"],
            "assignments": [
                {
                    "role": "content-reviewer",
                    "responsibility": "Review content",
                    "model_id": "glm-5.1",
                }
            ],
            "notes": "updated",
        },
    )
    list_response = client.get("/api/control/rule-templates")

    assert update_response.status_code == 200
    assert update_response.json()["display_name"] == "Paper Style Updated"
    assert update_response.json()["assignments"][0]["model_id"] == "glm-5.1"
    assert any(
        item["template_id"] == "paper-style"
        and item["display_name"] == "Paper Style Updated"
        and item["assignments"][0]["role"] == "content-reviewer"
        for item in list_response.json()
    )


def test_tasks_endpoint_returns_rule_template_selection_metadata(
    isolated_model_control_storage,
    isolated_history_storage,
):
    client = TestClient(create_app())

    client.post(
        "/api/control/rule-templates",
        json={
            "template_id": "paper-style",
            "display_name": "Paper Style",
            "description": "Paper review template",
            "preset_mode": "paper-revision",
            "task_types": ["writing"],
            "default_coordinator_model_id": "gpt-5.4",
            "enabled": True,
            "is_default": True,
            "trigger_keywords": ["paper", "journal", "abstract"],
            "assignments": [
                {
                    "role": "style-reviewer",
                    "responsibility": "Review style",
                    "model_id": "kimi-2.5",
                }
            ],
            "notes": "test template",
        },
    )

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Please revise this journal paper abstract.",
            "preset_mode": "paper-revision",
            "task_type": "writing",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["data"]["metadata"]["rule_template_selection"]["template_id"] == "paper-style"
    assert (
        body["data"]["metadata"]["rule_template_selection"]["coordinator_model_id"]
        == "gpt-5.4"
    )


def test_pending_approval_can_be_approved_and_persisted(isolated_history_storage):
    client = TestClient(create_app())

    submit_response = client.post(
        "/api/tasks",
        json={
            "prompt": "Apply risky repository write",
            "preset_mode": "code-engineering",
            "metadata": {
                "requires_approval": True,
                "approval_actions": ["write files"],
            },
        },
    )

    submit_body = submit_response.json()
    task_id = submit_body["data"]["metadata"]["task_id"]

    assert submit_response.status_code == 200
    assert submit_body["status"] == "pending_approval"

    pending_response = client.get("/api/approvals/pending")
    assert pending_response.status_code == 200
    assert any(item["task_id"] == task_id for item in pending_response.json())

    approve_response = client.post(
        f"/api/approvals/{task_id}/approve",
        json={"comment": "Proceed"},
    )
    approve_body = approve_response.json()

    assert approve_response.status_code == 200
    assert approve_body["status"] == "completed"
    assert approve_body["data"]["metadata"]["approval"]["status"] == "approved"

    history_response = client.get(f"/api/history/tasks/{task_id}")
    history_body = history_response.json()

    assert history_response.status_code == 200
    assert history_body["status"] == "completed"
    assert history_body["approval"]["status"] == "approved"
    assert history_body["stages"]


def test_pending_approval_can_be_rejected(isolated_history_storage):
    client = TestClient(create_app())

    submit_response = client.post(
        "/api/tasks",
        json={
            "prompt": "Apply risky repository write",
            "metadata": {
                "requires_approval": True,
                "approval_actions": ["execute shell"],
            },
        },
    )
    task_id = submit_response.json()["data"]["metadata"]["task_id"]

    reject_response = client.post(
        f"/api/approvals/{task_id}/reject",
        json={"comment": "Stop here"},
    )
    reject_body = reject_response.json()

    assert reject_response.status_code == 200
    assert reject_body["status"] == "rejected"

    history_response = client.get("/api/history/tasks", params={"status": "rejected"})
    assert history_response.status_code == 200
    assert any(item["task_id"] == task_id for item in history_response.json())


def test_history_endpoint_filters_pending_approval_items(isolated_history_storage):
    client = TestClient(create_app())

    pending_response = client.post(
        "/api/tasks",
        json={
            "prompt": "Apply risky repository write",
            "metadata": {
                "requires_approval": True,
                "approval_actions": ["execute shell"],
            },
        },
    )
    completed_response = client.post(
        "/api/tasks",
        json={
            "prompt": "Read repository summary",
        },
    )

    pending_task_id = pending_response.json()["data"]["metadata"]["task_id"]
    completed_task_id = completed_response.json()["data"]["metadata"]["task_id"]

    filtered_response = client.get("/api/history/tasks", params={"status": "pending_approval"})

    assert filtered_response.status_code == 200
    filtered_task_ids = {item["task_id"] for item in filtered_response.json()}
    assert pending_task_id in filtered_task_ids
    assert completed_task_id not in filtered_task_ids


def test_github_read_only_endpoints_return_summaries(
    isolated_history_storage,
    mocked_github_api,
):
    client = TestClient(create_app())

    repo_response = client.get("/api/github/repositories/openai/openai-python")
    issue_response = client.get("/api/github/repositories/openai/openai-python/issues/123")
    pr_response = client.get("/api/github/repositories/openai/openai-python/pulls/9")

    assert repo_response.status_code == 200
    assert repo_response.json()["full_name"] == "openai/openai-python"
    assert issue_response.status_code == 200
    assert issue_response.json()["number"] == 123
    assert pr_response.status_code == 200
    assert pr_response.json()["number"] == 9


def test_tasks_endpoint_persists_github_context(
    isolated_history_storage,
    mocked_github_api,
):
    client = TestClient(create_app())

    response = client.post(
        "/api/tasks",
        json={
            "prompt": "Review upstream issue and PR context",
            "github_repo": "openai/openai-python",
            "github_issue_number": 123,
            "github_pr_number": 9,
        },
    )

    body = response.json()
    task_id = body["data"]["metadata"]["task_id"]

    assert response.status_code == 200
    assert body["data"]["metadata"]["github_context"]["repository"]["full_name"] == (
        "openai/openai-python"
    )
    assert body["data"]["metadata"]["github_context"]["issue"]["number"] == 123
    assert body["data"]["metadata"]["github_context"]["pull_request"]["number"] == 9

    history_response = client.get(f"/api/history/tasks/{task_id}")
    assert history_response.status_code == 200
    assert (
        history_response.json()["metadata"]["github_context"]["repository"]["full_name"]
        == "openai/openai-python"
    )
