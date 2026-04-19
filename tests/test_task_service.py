from app.backend.core.config import Settings
from app.backend.schemas.task import TaskRequest
from app.backend.services.approval_service import ApprovalService
from app.backend.services.coordinator_selection_service import (
    get_coordinator_selection_service,
)
from app.backend.services.history_service import HistoryService
from app.backend.services.model_routing_service import get_model_routing_service
from app.backend.services.preset_service import PresetService
from app.backend.services.task_service import TaskService


def make_service(tmp_path, **settings_overrides) -> TaskService:
    settings_overrides.setdefault("sqlite_db_path", str(tmp_path / "mindforge-test.db"))
    settings = Settings(**settings_overrides)
    return TaskService(
        settings,
        PresetService(),
        get_model_routing_service(),
        get_coordinator_selection_service(),
        ApprovalService(HistoryService(settings)),
        HistoryService(settings),
    )


def test_submit_uses_default_preset_and_mock_provider(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(TaskRequest(prompt="Analyze repository"))

    assert response.status == "completed"
    assert response.data.provider == "mock-openhands"
    assert response.data.metadata["resolved_preset_mode"] == "default"
    assert response.data.metadata["used_default_preset"] is True
    assert response.data.metadata["task_model_selection"]["model_id"] == "gpt-5.4"


def test_submit_unknown_preset_returns_failed_response(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(
        TaskRequest(prompt="Analyze repository", preset_mode="missing-preset")
    )

    assert response.status == "failed"
    assert response.message == "Preset resolution failed."
    assert "Unknown preset_mode" in response.error_message
    assert "available_presets" in response.data.metadata


def test_submit_invalid_model_override_returns_failed_response(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(
        TaskRequest(prompt="Analyze repository", model_override="missing-model")
    )

    assert response.status == "failed"
    assert response.message == "Model routing failed."
    assert "missing-model" in response.error_message


def test_submit_uses_matching_rule_template_metadata(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(
        TaskRequest(
            prompt="Please revise this journal paper abstract and reviewer response.",
            preset_mode="paper-revision",
            task_type="writing",
        )
    )

    assert response.status == "completed"
    selection = response.data.metadata["rule_template_selection"]
    assert selection["template_id"] == "paper-revision-journal"
    assert selection["coordinator_model_id"] == "gpt-5.4"
    assert "paper" in selection["matched_keywords"]


def test_submit_unknown_rule_template_returns_failed_response(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(
        TaskRequest(
            prompt="Analyze repository",
            preset_mode="code-engineering",
            rule_template_id="missing-template",
        )
    )

    assert response.status == "failed"
    assert response.message == "Rule template selection failed."
    assert "missing-template" in response.error_message


def test_submit_high_risk_task_enters_pending_approval(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(
        TaskRequest(
            prompt="Run a high-risk write task",
            preset_mode="code-engineering",
            metadata={
                "requires_approval": True,
                "approval_actions": ["write files", "execute shell"],
            },
        )
    )

    assert response.status == "pending_approval"
    assert response.data.provider == "mindforge-approval-gate"
    assert response.data.metadata["approval"]["status"] == "pending"
    assert response.data.metadata["task_id"]
