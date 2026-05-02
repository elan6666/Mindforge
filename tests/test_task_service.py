import requests

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
    settings_overrides.setdefault("file_storage_path", str(tmp_path / "files"))
    settings_overrides.setdefault("artifact_storage_path", str(tmp_path / "artifacts"))
    settings_overrides.setdefault("mcp_registry_path", str(tmp_path / "mcp_servers.json"))
    settings_overrides.setdefault("project_spaces_path", str(tmp_path / "project_spaces.json"))
    settings_overrides.setdefault("skill_settings_path", str(tmp_path / "skill_settings.json"))
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


def test_submit_executes_enabled_tool_capabilities(tmp_path, monkeypatch):
    service = make_service(
        tmp_path,
        openhands_mode="mock",
        code_execution_requires_approval=False,
    )

    class FakeSearchResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "Heading": "Mindforge",
                "AbstractText": "Mindforge is a multi-agent workspace.",
                "AbstractURL": "https://example.test/mindforge",
                "RelatedTopics": [],
            }

    class FakePageResponse:
        text = "<html><body>Mindforge is a multi-agent workspace.</body></html>"

        def raise_for_status(self):
            return None

    def fake_get(url, params=None, headers=None, timeout=None):
        if "duckduckgo.com" in url:
            return FakeSearchResponse()
        return FakePageResponse()

    monkeypatch.setattr(
        "app.backend.services.task_service.requests.get",
        fake_get,
    )

    response = service.submit(
        TaskRequest(
            prompt="Search and run this:\n```python\nprint(2 + 2)\n```",
            tool_flags={
                "deep_analysis": True,
                "web_search": True,
                "code_execution": True,
                "canvas": True,
            },
        )
    )

    metadata = response.data.metadata
    tool_context = metadata["tool_context"]

    assert response.status == "completed"
    assert tool_context["deep_analysis"]["status"] == "enabled"
    assert tool_context["web_search"]["status"] == "fetched"
    assert tool_context["web_search"]["results"][0]["title"] == "Mindforge"
    assert tool_context["code_execution"]["status"] == "completed"
    assert tool_context["code_execution"]["stdout"].strip() == "4"
    assert "Mindforge tool context:" in response.data.output
    assert "stdout: 4" in response.data.output
    assert metadata["canvas_artifacts"][0]["kind"] == "markdown"
    assert metadata["canvas_artifacts"][1]["kind"] == "code-execution-result"
    assert metadata["execution_report"]["runtime_boundary"]["code_execution"] == (
        "approval-gated-python-snippet"
    )


def test_code_execution_is_blocked_without_approval_by_default(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(
        TaskRequest(
            prompt="Run this:\n```python\nprint(2 + 2)\n```",
            tool_flags={"code_execution": True},
        )
    )

    code_context = response.data.metadata["tool_context"]["code_execution"]
    assert response.status == "completed"
    assert code_context["status"] == "blocked"
    assert "requires an approved task" in code_context["reason"]
    assert response.data.metadata["execution_report"]["warnings"]


def test_submit_generates_document_artifact_from_natural_language_request(
    tmp_path,
    monkeypatch,
):
    service = make_service(tmp_path, openhands_mode="mock")

    class FakeSearchResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "Heading": "GitHub trending",
                "AbstractText": "Current GitHub hot repositories and developer trends.",
                "AbstractURL": "https://example.test/github-trending",
                "RelatedTopics": [],
            }

    monkeypatch.setattr(
        "app.backend.services.task_service.requests.get",
        lambda *args, **kwargs: FakeSearchResponse(),
    )

    response = service.submit(TaskRequest(prompt="帮我做一个 GitHub 热点的 PDF"))

    metadata = response.data.metadata
    artifact = metadata["generated_artifacts"][0]
    assert response.status == "completed"
    assert metadata["document_generation"]["format"] == "pdf"
    assert metadata["document_generation"]["status"] == "generated"
    assert metadata["tool_flags"]["web_search"] is True
    assert metadata["tool_context"]["web_search"]["status"] == "fetched"
    assert artifact["format"] == "pdf"
    assert artifact["source_task_id"] == metadata["task_id"]
    assert artifact["download_url"] in response.data.output
    assert (tmp_path / "artifacts").exists()


def test_web_search_uses_browser_reader_when_http_page_read_fails(
    tmp_path,
    monkeypatch,
):
    service = make_service(tmp_path, openhands_mode="mock")

    class FakeSearchResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "Heading": "Mindforge Docs",
                "AbstractText": "Initial search result.",
                "AbstractURL": "https://example.test/rendered",
                "RelatedTopics": [],
            }

    def fake_get(url, params=None, headers=None, timeout=None):
        if "duckduckgo.com" in url:
            return FakeSearchResponse()
        raise requests.RequestException("static fetch failed")

    monkeypatch.setattr(
        "app.backend.services.task_service.requests.get",
        fake_get,
    )
    monkeypatch.setattr(
        "app.backend.services.task_service.TaskService._read_page_with_browser",
        staticmethod(lambda url: "Browser rendered Mindforge documentation content."),
    )

    response = service.submit(
        TaskRequest(
            prompt="Find Mindforge documentation",
            web_search=True,
        )
    )

    web_context = response.data.metadata["tool_context"]["web_search"]
    assert web_context["status"] == "fetched"
    assert web_context["results"][0]["source_type"] == "browser_page"
    assert web_context["results"][0]["read_method"] == "browser"
    assert web_context["citations"][0]["url"] == "https://example.test/rendered"


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
    assert (
        "Loaded local skills:" in response.data.output
        or "Requested skills:" in response.data.output
    )
    assert "frontend-design" in response.data.output
    assert "gsd-do" in response.data.output


def test_greeting_uses_adapter_boundary_not_local_preset_response(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(TaskRequest(prompt="你好"))

    assert response.status == "completed"
    assert response.data.provider == "mock-openhands"
    assert response.data.metadata["resolved_preset_mode"] == "default"
    assert "你好" in response.data.output
    assert "mindforge-intake" not in response.data.provider


def test_date_question_uses_adapter_boundary_with_conversation_context(tmp_path):
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
    assert response.data.provider == "mock-openhands"
    assert response.data.metadata["runtime_context"]["current_date"]
    assert "Conversation so far:" in response.data.output
    assert "Current user request:" in response.data.output
    assert "Current runtime context:" in response.data.output
    assert "current_date:" in response.data.output
    assert "今天几号" in response.data.output
    assert "mindforge-intake" not in response.data.provider


def test_date_question_with_no_web_results_still_uses_runtime_context(
    tmp_path,
    monkeypatch,
):
    service = make_service(tmp_path, openhands_mode="mock")

    class FakeSearchResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"RelatedTopics": []}

    monkeypatch.setattr(
        "app.backend.services.task_service.requests.get",
        lambda *args, **kwargs: FakeSearchResponse(),
    )

    response = service.submit(
        TaskRequest(
            prompt="今天几号",
            web_search=True,
        )
    )

    assert response.status == "completed"
    assert response.data.metadata["tool_context"]["web_search"]["status"] == "no_results"
    assert "current_date:" in response.data.output
    assert "answer directly from current_date" in response.data.output
    assert "no web results were found; continue answering" in response.data.output


def test_capability_question_uses_adapter_boundary_not_local_preset_response(tmp_path):
    service = make_service(tmp_path, openhands_mode="mock")

    response = service.submit(TaskRequest(prompt="你能做什么"))

    assert response.status == "completed"
    assert response.data.provider == "mock-openhands"
    assert "你能做什么" in response.data.output
    assert "mindforge-intake" not in response.data.provider


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
