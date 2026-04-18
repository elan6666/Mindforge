from app.backend.core.config import Settings
from app.backend.schemas.task import TaskRequest
from app.backend.services.preset_service import PresetService
from app.backend.services.task_service import TaskService


def make_service(**settings_overrides) -> TaskService:
    settings = Settings(**settings_overrides)
    return TaskService(settings, PresetService())


def test_submit_uses_default_preset_and_mock_provider():
    service = make_service(openhands_mode="mock")

    response = service.submit(TaskRequest(prompt="Analyze repository"))

    assert response.status == "completed"
    assert response.data.provider == "mock-openhands"
    assert response.data.metadata["resolved_preset_mode"] == "default"
    assert response.data.metadata["used_default_preset"] is True


def test_submit_unknown_preset_returns_failed_response():
    service = make_service(openhands_mode="mock")

    response = service.submit(
        TaskRequest(prompt="Analyze repository", preset_mode="missing-preset")
    )

    assert response.status == "failed"
    assert response.message == "Preset resolution failed."
    assert "Unknown preset_mode" in response.error_message
    assert "available_presets" in response.data.metadata
