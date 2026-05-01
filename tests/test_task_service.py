from app.backend.core.config import Settings
from app.backend.schemas.github_context import GitHubContextSummary
from app.backend.schemas.task import TaskRequest
from app.backend.services.academic_context_service import AcademicContextService
from app.backend.services.approval_service import ApprovalService
from app.backend.services.coordinator_selection_service import (
    get_coordinator_selection_service,
)
from app.backend.services.github_context_service import GitHubContextService
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
        GitHubContextService(settings),
        AcademicContextService(settings),
    )


def test_submit_uses_default_preset_and_mock_provider(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(TaskRequest(prompt="Analyze repository"))

    assert response.status == "completed"
    assert response.data.provider == "mock-openhands"
    assert response.data.metadata["resolved_preset_mode"] == "default"
    assert response.data.metadata["used_default_preset"] is True
    assert response.data.metadata["task_model_selection"]["model_id"] == "gpt-5.4"


def test_submit_includes_composer_attachments_and_tool_flags_metadata(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(
        TaskRequest(
            prompt="Summarize the uploaded context",
            attachments=[
                {
                    "id": "att-1",
                    "name": "requirements.md",
                    "mimeType": "text/markdown",
                    "sizeBytes": 128,
                    "textExcerpt": "Backend contract requirements",
                    "metadata": {"source": "composer-upload", "sha256": "abc123"},
                }
            ],
            tool_flags={"deep_analysis": True},
            web_search=True,
            code_execution=False,
        )
    )

    metadata = response.data.metadata

    assert response.status == "completed"
    assert metadata["attachments"] == [
        {
            "id": "att-1",
            "name": "requirements.md",
            "mime_type": "text/markdown",
            "size_bytes": 128,
            "text_excerpt": "Backend contract requirements",
            "metadata": {"source": "composer-upload", "sha256": "abc123"},
        }
    ]
    assert metadata["tool_flags"]["web_search"] is True
    assert metadata["tool_flags"]["deep_analysis"] is True
    assert metadata["tool_flags"]["code_execution"] is False
    assert metadata["task_model_selection"]["model_id"] == "gpt-5.4"


def test_submit_includes_conversation_history_metadata_and_prompt_context(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(
        TaskRequest(
            prompt="What are the remaining risks?",
            conversation_id="conversation-1",
            conversation_history=[
                {
                    "role": "user",
                    "content": "Please review the architecture.",
                    "taskId": "task-a",
                },
                {
                    "role": "assistant",
                    "content": "The API boundary is clear.",
                    "task_id": "task-a",
                },
            ],
        )
    )

    metadata = response.data.metadata

    assert response.status == "completed"
    assert metadata["conversation_id"] == "conversation-1"
    assert metadata["conversation_turn_count"] == 3
    assert metadata["conversation_history"][0]["task_id"] == "task-a"
    assert "Conversation so far:" in response.data.output
    assert "User: Please review the architecture." in response.data.output
    assert "Assistant: The API boundary is clear." in response.data.output
    assert "Current user request:" in response.data.output
    assert "What are the remaining risks?" in response.data.output


def test_submit_omits_mock_trace_from_conversation_prompt_context(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(
        TaskRequest(
            prompt="Continue the task",
            conversation_id="conversation-1",
            conversation_history=[
                {
                    "role": "assistant",
                    "content": (
                        "[mock-openhands]\n"
                        "received prompt: internal debug prompt\n"
                        "OpenHands adapter executed through the configured boundary."
                    ),
                }
            ],
        )
    )

    assert response.status == "completed"
    assert "内部调试回显已省略" in response.data.output
    assert "received prompt: internal debug prompt" not in response.data.output


def test_submit_includes_requested_skills_metadata_and_prompt_context(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(
        TaskRequest(
            prompt="Polish the web app",
            skills=["frontend-design", "gsd-do", "frontend-design"],
        )
    )

    assert response.status == "completed"
    assert response.data.metadata["skills"] == ["frontend-design", "gsd-do"]
    assert "Requested skills:" in response.data.output
    assert "- frontend-design" in response.data.output
    assert "- gsd-do" in response.data.output


def test_lightweight_greeting_does_not_trigger_code_orchestration(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(
        TaskRequest(prompt="你好", preset_mode="code-engineering")
    )

    assert response.status == "completed"
    assert response.data.provider == "mindforge-intake"
    assert response.data.metadata["execution_mode"] == "plain-chat"
    assert "orchestration" not in response.data.metadata
    assert "你好" in response.data.output


def test_lightweight_date_question_does_not_expose_mock_adapter(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(
        TaskRequest(
            prompt="今天几号",
            conversation_history=[
                {"role": "user", "content": "hi"},
                {
                    "role": "assistant",
                    "content": "你好！我是 Mindforge。",
                },
            ],
        )
    )

    assert response.status == "completed"
    assert response.data.provider == "mindforge-intake"
    assert response.data.metadata["lightweight_intent"] == "date"
    assert "今天是" in response.data.output
    assert "[mock-openhands]" not in response.data.output


def test_lightweight_capability_question_does_not_expose_mock_adapter(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(TaskRequest(prompt="你能做什么"))

    assert response.status == "completed"
    assert response.data.provider == "mindforge-intake"
    assert response.data.metadata["lightweight_intent"] == "capability"
    assert "代码工程任务" in response.data.output
    assert "[mock-openhands]" not in response.data.output


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
    assert selection["coordinator_model_id"] == "doubao-seed-2.0-lite"
    assert "paper" in selection["matched_keywords"]
    trace = response.data.metadata["orchestration"]
    assert trace["strategy"] == "serial-paper-revision"
    assert [stage["role"] for stage in trace["stages"]] == [
        "standards-editor",
        "reviser",
        "style-reviewer",
        "content-reviewer",
        "reviser",
        "final-reviewer",
    ]
    assert trace["completed_stages"] == 6


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


def test_submit_includes_github_context_metadata(tmp_path, monkeypatch):
    service = make_service(tmp_path, openhands_mode="mock")

    def fake_resolve_context(**kwargs):
        return {
            "repository": {
                "owner": "openai",
                "name": "openai-python",
                "full_name": "openai/openai-python",
                "description": "OpenAI Python SDK",
                "html_url": "https://github.com/openai/openai-python",
                "default_branch": "main",
                "primary_language": "Python",
                "stargazers_count": 1,
                "forks_count": 2,
                "open_issues_count": 3,
                "visibility": "public",
            },
            "issue": None,
            "pull_request": None,
        }

    monkeypatch.setattr(
        service.github_context_service,
        "resolve_context",
        lambda **kwargs: GitHubContextSummary.model_validate(fake_resolve_context()),
    )

    response = service.submit(
        TaskRequest(
            prompt="Review issue context",
            github_repo="openai/openai-python",
        )
    )

    assert response.status == "completed"
    assert response.data.metadata["github_context"]["repository"]["full_name"] == (
        "openai/openai-python"
    )
