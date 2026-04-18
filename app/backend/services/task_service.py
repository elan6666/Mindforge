"""Task orchestration service."""

from functools import lru_cache

from app.backend.core.config import Settings, get_settings
from app.backend.core.logging import get_logger
from app.backend.integration.openhands_adapter import OpenHandsAdapter
from app.backend.schemas.repository import RepoAnalysisResult
from app.backend.schemas.task import TaskRequest, TaskResponse
from app.backend.services.orchestration_service import SerialOrchestrationService
from app.backend.services.preset_service import (
    PresetNotFoundError,
    PresetService,
    get_preset_service,
)
from app.backend.services.repository_service import RepositoryAnalysisService
from app.backend.services.result_normalizer import normalize_task_result


class TaskService:
    """Coordinate request normalization, adapter execution, and response shaping."""

    def __init__(self, settings: Settings, preset_service: PresetService) -> None:
        self.settings = settings
        self.preset_service = preset_service
        self.logger = get_logger("app.task_service")
        self.adapter = OpenHandsAdapter(settings)
        self.orchestrator = SerialOrchestrationService(self.adapter)
        self.repository_service = RepositoryAnalysisService()

    def submit(self, payload: TaskRequest) -> TaskResponse:
        """Run a task through the adapter boundary and normalize the output."""
        normalized_request = payload.model_dump()
        try:
            preset, used_default = self.preset_service.resolve(payload.preset_mode)
        except PresetNotFoundError as exc:
            self.logger.warning(
                "preset resolution failed",
                extra={"preset_mode": payload.preset_mode or "", "error": str(exc)},
            )
            return TaskResponse(
                status="failed",
                message="Preset resolution failed.",
                data={
                    "output": "",
                    "provider": "preset-registry",
                    "metadata": {
                        "requested_preset_mode": payload.preset_mode,
                        "available_presets": [
                            preset.preset_mode
                            for preset in self.preset_service.list_presets()
                        ],
                    },
                },
                error_message=str(exc),
            )

        normalized_request["preset_mode"] = preset.preset_mode
        normalized_request["metadata"] = {
            **payload.metadata,
            "resolved_preset": preset.model_dump(),
            "used_default_preset": used_default,
            "requested_preset_mode": payload.preset_mode,
        }
        repo_analysis = self._maybe_analyze_repo(payload, preset.requires_repo_analysis)
        if repo_analysis is not None:
            normalized_request["metadata"]["repo_analysis"] = repo_analysis.model_dump()
            if repo_analysis.repo_summary is not None:
                normalized_request["prompt"] = self._augment_prompt_with_repo_summary(
                    payload.prompt,
                    repo_analysis,
                )
        self.logger.info(
            "submitting task",
            extra={
                "preset_mode": preset.preset_mode,
                "repo_path": payload.repo_path or "",
                "openhands_mode": self.settings.openhands_mode,
            },
        )
        if preset.preset_mode == "code-engineering":
            response = self.orchestrator.execute_code_engineering(
                payload,
                preset,
                repo_analysis=repo_analysis,
            )
            response.data.metadata.update(
                {
                    "resolved_preset_mode": preset.preset_mode,
                    "requested_preset_mode": payload.preset_mode,
                    "used_default_preset": used_default,
                    "preset_summary": {
                        "preset_mode": preset.preset_mode,
                        "display_name": preset.display_name,
                        "requires_repo_analysis": preset.requires_repo_analysis,
                        "requires_approval": preset.requires_approval,
                    },
                    "repo_analysis": (
                        repo_analysis.model_dump() if repo_analysis is not None else None
                    ),
                }
            )
            return response
        result = self.adapter.run_task(normalized_request)
        self.logger.info(
            "task finished",
            extra={
                "status": result.status,
                "provider": result.provider,
            },
        )
        response = normalize_task_result(result)
        response.data.metadata.update(
            {
                "resolved_preset_mode": preset.preset_mode,
                "requested_preset_mode": payload.preset_mode,
                "used_default_preset": used_default,
                "preset_summary": {
                    "preset_mode": preset.preset_mode,
                    "display_name": preset.display_name,
                    "requires_repo_analysis": preset.requires_repo_analysis,
                    "requires_approval": preset.requires_approval,
                },
                "repo_analysis": (
                    repo_analysis.model_dump() if repo_analysis is not None else None
                ),
            }
        )
        return response

    def _maybe_analyze_repo(
        self,
        payload: TaskRequest,
        requires_repo_analysis: bool,
    ) -> RepoAnalysisResult | None:
        """Run repository analysis when the preset or request needs it."""
        if not requires_repo_analysis and not payload.repo_path:
            return None
        analysis = self.repository_service.analyze(payload.repo_path)
        self.logger.info(
            "repository analysis finished",
            extra={
                "repo_path": payload.repo_path or "",
                "repo_analysis_status": analysis.status,
            },
        )
        return analysis

    @staticmethod
    def _augment_prompt_with_repo_summary(
        prompt: str,
        repo_analysis: RepoAnalysisResult,
    ) -> str:
        """Append repository summary text for single-pass executions."""
        if repo_analysis.repo_summary is None:
            return prompt
        return (
            f"{prompt}\n\n"
            "Repository summary:\n"
            f"{repo_analysis.repo_summary.summary_text}"
        )


@lru_cache(maxsize=1)
def get_task_service() -> TaskService:
    """Create a cached task service instance for dependency injection."""
    return TaskService(get_settings(), get_preset_service())
