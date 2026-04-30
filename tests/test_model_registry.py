from app.backend.services.model_registry_service import get_model_registry_service
from app.backend.services.model_routing_service import get_model_routing_service


def test_model_registry_lists_expected_providers_and_models():
    registry = get_model_registry_service()

    providers = registry.list_providers()
    models = registry.list_models()

    assert any(item.provider_id == "openai" for item in providers)
    assert any(item.provider_id == "moonshot" for item in providers)
    assert any(item.provider_id == "volces-ark" for item in providers)
    assert any(item.model_id == "gpt-5.4" for item in models)
    assert any(item.model_id == "doubao-seed-2.0-lite" for item in models)
    assert any(item.model_id == "glm-5.1" for item in models)


def test_model_routing_resolves_role_specific_model():
    router = get_model_routing_service()

    selection = router.resolve_for_role(
        preset_mode="code-engineering",
        task_type=None,
        role="frontend",
    )

    assert selection.model_id == "kimi-2.5"
    assert selection.selection_source == "routing-role-default"


def test_model_routing_resolves_explicit_override():
    router = get_model_routing_service()

    selection = router.resolve_for_task(
        preset_mode="default",
        task_type=None,
        explicit_model="glm-5.1",
    )

    assert selection.model_id == "glm-5.1"
    assert selection.selection_source == "explicit-task-override"


def test_model_routing_resolves_task_type_default_when_scope_matches():
    router = get_model_routing_service()

    selection = router.resolve_for_task(
        preset_mode="paper-revision",
        task_type="writing",
    )

    assert selection.model_id == "doubao-seed-2.0-lite"
    assert selection.selection_source == "task-type-default"
