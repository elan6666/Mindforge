from app.backend.integration.openhands_adapter import AdapterResult
from app.backend.schemas.repository import RepoAnalysisResult, RepoKeyFile, RepoSummary
from app.backend.schemas.task import TaskRequest
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
            resolved_path="E:/CODE/agent助手",
            repository_name="agent助手",
            detected_stack=["Python"],
            top_level_directories=["app", "tests"],
            key_files=[RepoKeyFile(path="README.md", category="documentation")],
            entrypoints=["app/backend/main.py"],
            summary_text="Repository 'agent助手' appears to use Python.",
        ),
    )


def test_execute_code_engineering_runs_all_roles_in_order():
    preset, _ = PresetService().resolve("code-engineering")
    adapter = RecordingAdapter()
    service = SerialOrchestrationService(adapter)

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
    assert trace["completed_stages"] == 4
    assert all("repo_analysis" in call["metadata"] for call in adapter.calls)
    assert "Repository summary:" in adapter.calls[0]["prompt"]


def test_execute_code_engineering_stops_on_failed_stage():
    preset, _ = PresetService().resolve("code-engineering")
    adapter = RecordingAdapter(fail_on_role="backend")
    service = SerialOrchestrationService(adapter)

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
