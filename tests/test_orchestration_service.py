from app.backend.integration.openhands_adapter import AdapterResult
from app.backend.schemas.academic_context import AcademicContextSummary
from app.backend.schemas.github_context import GitHubContextSummary
from app.backend.schemas.repository import RepoAnalysisResult, RepoKeyFile, RepoSummary
from app.backend.schemas.task import TaskRequest
from app.backend.services.model_routing_service import get_model_routing_service
from app.backend.services.orchestration_service import SerialOrchestrationService
from app.backend.services.preset_service import PresetService


class RecordingAdapter:
    def __init__(self, fail_on_role: str | None = None) -> None:
        self.fail_on_role = fail_on_role
        self.calls: list[dict[str, object]] = []

    def run_task(self, payload: dict[str, object]) -> AdapterResult:
        self.calls.append(payload)
        metadata = payload.get("metadata", {}) or {}
        role = metadata.get("orchestration_role", "unknown")
        if role == self.fail_on_role:
            return AdapterResult(
                status="failed",
                output=f"{role} failed",
                provider="fake-adapter",
                metadata={"role": role},
                error_message=f"{role} boom",
            )
        return AdapterResult(
            status="completed",
            output=f"{role} completed",
            provider="fake-adapter",
            metadata={"role": role},
        )


def build_repo_analysis() -> RepoAnalysisResult:
    return RepoAnalysisResult(
        status="analyzed",
        repo_summary=RepoSummary(
            repo_path=".",
            resolved_path="E:/CODE/Mindforge",
            repository_name="Mindforge",
            detected_stack=["Python"],
            top_level_directories=["app", "tests"],
            key_files=[RepoKeyFile(path="README.md", category="documentation")],
            entrypoints=["app/backend/main.py"],
            summary_text="Repository 'Mindforge' appears to use Python.",
        ),
    )


def build_github_context() -> GitHubContextSummary:
    return GitHubContextSummary.model_validate(
        {
            "repository": {
                "owner": "openai",
                "name": "openai-python",
                "full_name": "openai/openai-python",
                "description": "OpenAI Python SDK",
                "html_url": "https://github.com/openai/openai-python",
                "default_branch": "main",
                "primary_language": "Python",
                "stargazers_count": 100,
                "forks_count": 10,
                "open_issues_count": 5,
                "visibility": "public",
            },
            "issue": {
                "number": 123,
                "title": "Bug report",
                "state": "open",
                "html_url": "https://github.com/openai/openai-python/issues/123",
                "author": "octocat",
                "labels": ["bug"],
                "comment_count": 3,
                "body_excerpt": "Issue context",
            },
            "pull_request": {
                "number": 9,
                "title": "Fix bug",
                "state": "open",
                "html_url": "https://github.com/openai/openai-python/pull/9",
                "author": "octocat",
                "labels": ["enhancement"],
                "comment_count": 2,
                "review_comment_count": 1,
                "draft": False,
                "merged": False,
                "head_ref": "feature",
                "base_ref": "main",
                "body_excerpt": "PR context",
            },
        }
    )


def test_execute_code_engineering_runs_all_roles_in_order():
    preset, _ = PresetService().resolve("code-engineering")
    adapter = RecordingAdapter()
    service = SerialOrchestrationService(adapter, get_model_routing_service())

    response = service.execute_code_engineering(
        TaskRequest(prompt="Add login", preset_mode="code-engineering", repo_path="."),
        preset,
        repo_analysis=build_repo_analysis(),
    )

    assert response.status == "completed"
    assert response.data.provider == "multi-stage-orchestrator"
    trace = response.data.metadata["orchestration"]
    assert [stage["role"] for stage in trace["stages"]] == [
        "project-manager",
        "backend",
        "frontend",
        "reviewer",
    ]
    assert [stage["model"] for stage in trace["stages"]] == [
        "gpt-5.4",
        "gpt-5.4",
        "kimi-2.5",
        "glm-5.1",
    ]
    assert trace["completed_stages"] == 4
    assert all("repo_analysis" in call["metadata"] for call in adapter.calls)
    assert "Repository summary:" in adapter.calls[0]["prompt"]


def test_execute_code_engineering_injects_github_context_into_stage_prompt():
    preset, _ = PresetService().resolve("code-engineering")
    adapter = RecordingAdapter()
    service = SerialOrchestrationService(adapter, get_model_routing_service())

    response = service.execute_code_engineering(
        TaskRequest(prompt="Review upstream issue", preset_mode="code-engineering"),
        preset,
        github_context=build_github_context(),
    )

    assert response.status == "completed"
    assert adapter.calls
    first_prompt = adapter.calls[0]["prompt"]
    assert "GitHub repository: openai/openai-python" in first_prompt
    assert "GitHub issue: #123 Bug report [open]" in first_prompt
    assert "GitHub issue excerpt: Issue context" in first_prompt
    assert "GitHub pull request: #9 Fix bug [open]" in first_prompt
    assert "GitHub pull request excerpt: PR context" in first_prompt
    assert adapter.calls[0]["metadata"]["github_context"]["repository"]["full_name"] == (
        "openai/openai-python"
    )


def test_execute_code_engineering_stops_on_failed_stage():
    preset, _ = PresetService().resolve("code-engineering")
    adapter = RecordingAdapter(fail_on_role="backend")
    service = SerialOrchestrationService(adapter, get_model_routing_service())

    response = service.execute_code_engineering(
        TaskRequest(prompt="Add login", preset_mode="code-engineering"),
        preset,
    )

    assert response.status == "failed"
    assert response.error_message == "backend boom"
    trace = response.data.metadata["orchestration"]
    assert trace["failed_stage"] == "backend"
    assert len(trace["stages"]) == 2
    assert [call["metadata"]["orchestration_role"] for call in adapter.calls] == [
        "project-manager",
        "backend",
    ]


def test_execute_code_engineering_honors_role_model_override():
    preset, _ = PresetService().resolve("code-engineering")
    adapter = RecordingAdapter()
    service = SerialOrchestrationService(adapter, get_model_routing_service())

    response = service.execute_code_engineering(
        TaskRequest(
            prompt="Add login",
            preset_mode="code-engineering",
            role_model_overrides={"frontend": "gpt-5.4"},
        ),
        preset,
    )

    trace = response.data.metadata["orchestration"]

    assert trace["stages"][2]["model"] == "gpt-5.4"
    assert trace["stages"][2]["metadata"]["model_selection"]["selection_source"] == (
        "explicit-role-override"
    )


def test_execute_paper_revision_runs_review_revise_rereview_cycle():
    preset, _ = PresetService().resolve("paper-revision")
    adapter = RecordingAdapter()
    service = SerialOrchestrationService(adapter, get_model_routing_service())
    academic_context = AcademicContextSummary.model_validate(
        {
            "journal": {
                "journal_name": "Example Journal",
                "journal_url": "https://journal.example/guidelines",
                "title": "Author guidelines",
                "excerpt": "Use concise academic English.",
                "status": "fetched",
            },
            "reference_papers": [
                {
                    "url": "https://paper.example/one",
                    "title": "Representative Paper",
                    "excerpt": "This paper uses a clear contribution-first structure.",
                    "status": "fetched",
                }
            ],
            "warnings": [],
        }
    )

    response = service.execute_preset(
        TaskRequest(
            prompt="Revise this abstract for journal submission.",
            preset_mode="paper-revision",
            task_type="writing",
        ),
        preset,
        academic_context=academic_context,
    )

    assert response.status == "completed"
    trace = response.data.metadata["orchestration"]
    assert trace["strategy"] == "serial-paper-revision"
    assert [stage["stage_id"] for stage in trace["stages"]] == [
        "analyze-standards",
        "revise",
        "style-review",
        "content-review",
        "iterate",
        "re-review",
    ]
    assert [stage["role"] for stage in trace["stages"]] == [
        "standards-editor",
        "reviser",
        "style-reviewer",
        "content-reviewer",
        "reviser",
        "final-reviewer",
    ]
    assert [stage["model"] for stage in trace["stages"]] == [
        "doubao-seed-2.0-lite",
        "doubao-seed-2.0-lite",
        "doubao-seed-2.0-lite",
        "doubao-seed-2.0-lite",
        "doubao-seed-2.0-lite",
        "doubao-seed-2.0-lite",
    ]
    assert "Academic context:" in adapter.calls[0]["prompt"]
    assert adapter.calls[0]["metadata"]["academic_context"]["journal"]["status"] == "fetched"
