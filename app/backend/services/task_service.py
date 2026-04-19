"""Task orchestration service."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from uuid import uuid4

from app.backend.core.config import Settings, get_settings
from app.backend.core.logging import get_logger
from app.backend.integration.openhands_adapter import OpenHandsAdapter
from app.backend.schemas.approval import ApprovalRecord
from app.backend.schemas.model import ModelSelection
from app.backend.schemas.preset import PresetDefinition
from app.backend.schemas.repository import RepoAnalysisResult
from app.backend.schemas.rule_template import RuleTemplateSelection
from app.backend.schemas.task import TaskRequest, TaskResponse, TaskResponseData
from app.backend.services.approval_service import (
    ApprovalError,
    ApprovalService,
    get_approval_service,
)
from app.backend.services.coordinator_selection_service import (
    CoordinatorSelectionError,
    CoordinatorSelectionService,
    get_coordinator_selection_service,
)
from app.backend.services.history_service import HistoryService, get_history_service
from app.backend.services.model_routing_service import (
    ModelRoutingError,
    ModelRoutingService,
    get_model_routing_service,
)
from app.backend.services.orchestration_service import SerialOrchestrationService
from app.backend.services.preset_service import (
    PresetNotFoundError,
    PresetService,
    get_preset_service,
)
from app.backend.services.repository_service import RepositoryAnalysisService
from app.backend.services.result_normalizer import normalize_task_result


@dataclass(slots=True)
class PreparedTaskExecution:
    """Resolved task execution context before runtime handoff."""

    requested_payload: TaskRequest
    execution_payload: TaskRequest
    preset: PresetDefinition
    used_default_preset: bool
    task_model_selection: ModelSelection
    rule_template_selection: RuleTemplateSelection | None
    effective_role_model_overrides: dict[str, str]
    repo_analysis: RepoAnalysisResult | None


class TaskService:
    """Coordinate request normalization, adapter execution, approval, and history."""

    def __init__(
        self,
        settings: Settings,
        preset_service: PresetService,
        model_router: ModelRoutingService,
        coordinator_selector: CoordinatorSelectionService,
        approval_service: ApprovalService,
        history_service: HistoryService,
    ) -> None:
        self.settings = settings
        self.preset_service = preset_service
        self.model_router = model_router
        self.coordinator_selector = coordinator_selector
        self.approval_service = approval_service
        self.history_service = history_service
        self.logger = get_logger("app.task_service")
        self.adapter = OpenHandsAdapter(settings)
        self.orchestrator = SerialOrchestrationService(self.adapter, model_router)
        self.repository_service = RepositoryAnalysisService()

    def submit(self, payload: TaskRequest) -> TaskResponse:
        """Run a task through the adapter boundary and normalize the output."""
        prepared = self._prepare_execution(payload)
        if isinstance(prepared, TaskResponse):
            return prepared

        task_id = str(uuid4())
        approval_requirement = self.approval_service.evaluate_requirement(
            payload,
            prepared.preset,
            prepared.task_model_selection,
            prepared.rule_template_selection,
        )
        if approval_requirement.required:
            pending_metadata = self._build_common_metadata(
                prepared,
                task_id=task_id,
            )
            approval = self.history_service.create_pending_task(
                task_id=task_id,
                request=payload,
                metadata=pending_metadata,
                approval_requirement=approval_requirement,
            )
            return self._build_pending_approval_response(
                task_id=task_id,
                prepared=prepared,
                approval=approval,
            )

        response = self._execute_prepared(prepared, task_id=task_id)
        self.history_service.record_task_result(task_id, payload, response)
        return response

    def approve(self, task_id: str, comment: str | None = None) -> TaskResponse:
        """Approve a pending task and continue execution."""
        detail = self.history_service.get_task_detail(task_id)
        if detail is None:
            raise ApprovalError(f"Unknown task '{task_id}'.")
        if detail.approval is None or detail.approval.status != "pending":
            raise ApprovalError(f"Task '{task_id}' is not waiting for approval.")

        request = TaskRequest.model_validate(detail.request_payload)
        prepared = self._prepare_execution(request)
        if isinstance(prepared, TaskResponse):
            self.history_service.record_task_result(task_id, request, prepared)
            return prepared

        approval = self.approval_service.approve(task_id, comment=comment)
        response = self._execute_prepared(prepared, task_id=task_id, approval=approval)
        self.history_service.record_task_result(task_id, request, response)
        return response

    def reject(self, task_id: str, comment: str | None = None) -> TaskResponse:
        """Reject a pending task without executing it."""
        detail = self.history_service.get_task_detail(task_id)
        if detail is None:
            raise ApprovalError(f"Unknown task '{task_id}'.")
        if detail.approval is None or detail.approval.status != "pending":
            raise ApprovalError(f"Task '{task_id}' is not waiting for approval.")

        approval = self.approval_service.reject(task_id, comment=comment)
        response = TaskResponse(
            status="rejected",
            message="Task was rejected during approval.",
            data=TaskResponseData(
                output="",
                provider="mindforge-approval-gate",
                metadata={
                    **detail.metadata,
                    "task_id": task_id,
                    "approval": approval.model_dump(),
                },
            ),
        )
        self.history_service.record_task_result(
            task_id,
            TaskRequest.model_validate(detail.request_payload),
            response,
        )
        return response

    def _prepare_execution(self, payload: TaskRequest) -> PreparedTaskExecution | TaskResponse:
        """Resolve presets, routing, templates, and repository context."""
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
                data=TaskResponseData(
                    output="",
                    provider="preset-registry",
                    metadata={
                        "requested_preset_mode": payload.preset_mode,
                        "available_presets": [
                            preset_item.preset_mode
                            for preset_item in self.preset_service.list_presets()
                        ],
                    },
                ),
                error_message=str(exc),
            )

        try:
            rule_template_selection = self.coordinator_selector.select_template(
                prompt=payload.prompt,
                preset_mode=preset.preset_mode,
                task_type=payload.task_type,
                explicit_template_id=payload.rule_template_id,
            )
        except CoordinatorSelectionError as exc:
            return TaskResponse(
                status="failed",
                message="Rule template selection failed.",
                data=TaskResponseData(
                    output="",
                    provider="rule-template-selection",
                    metadata={
                        "requested_rule_template_id": payload.rule_template_id,
                        "resolved_preset_mode": preset.preset_mode,
                    },
                ),
                error_message=str(exc),
            )

        effective_model_override = payload.model_override or (
            rule_template_selection.coordinator_model_id
            if rule_template_selection is not None
            else None
        )
        try:
            task_model_selection = self.model_router.resolve_for_task(
                preset_mode=preset.preset_mode,
                task_type=payload.task_type,
                explicit_model=effective_model_override,
            )
        except ModelRoutingError as exc:
            self.logger.warning(
                "model routing failed",
                extra={
                    "preset_mode": preset.preset_mode,
                    "task_type": payload.task_type or "",
                    "model_override": payload.model_override or "",
                    "error": str(exc),
                },
            )
            return TaskResponse(
                status="failed",
                message="Model routing failed.",
                data=TaskResponseData(
                    output="",
                    provider="model-routing",
                    metadata={
                        "requested_model_override": payload.model_override,
                        "requested_rule_template_id": payload.rule_template_id,
                        "requested_role_model_overrides": payload.role_model_overrides,
                        "resolved_preset_mode": preset.preset_mode,
                    },
                ),
                error_message=str(exc),
            )

        effective_role_model_overrides = {
            **(
                rule_template_selection.role_model_overrides
                if rule_template_selection is not None
                else {}
            ),
            **payload.role_model_overrides,
        }
        execution_payload = payload.model_copy(
            update={
                "model_override": effective_model_override,
                "role_model_overrides": effective_role_model_overrides,
            }
        )

        repo_analysis = self._maybe_analyze_repo(
            execution_payload,
            preset.requires_repo_analysis,
        )
        return PreparedTaskExecution(
            requested_payload=payload,
            execution_payload=execution_payload,
            preset=preset,
            used_default_preset=used_default,
            task_model_selection=task_model_selection,
            rule_template_selection=rule_template_selection,
            effective_role_model_overrides=effective_role_model_overrides,
            repo_analysis=repo_analysis,
        )

    def _execute_prepared(
        self,
        prepared: PreparedTaskExecution,
        *,
        task_id: str,
        approval: ApprovalRecord | None = None,
    ) -> TaskResponse:
        """Execute a fully prepared task."""
        normalized_request = self._build_normalized_request(prepared)
        self.logger.info(
            "submitting task",
            extra={
                "task_id": task_id,
                "preset_mode": prepared.preset.preset_mode,
                "repo_path": prepared.execution_payload.repo_path or "",
                "openhands_mode": self.settings.openhands_mode,
            },
        )
        if prepared.preset.preset_mode == "code-engineering":
            try:
                response = self.orchestrator.execute_code_engineering(
                    prepared.execution_payload,
                    prepared.preset,
                    repo_analysis=prepared.repo_analysis,
                )
            except ModelRoutingError as exc:
                return TaskResponse(
                    status="failed",
                    message="Model routing failed during orchestration setup.",
                    data=TaskResponseData(
                        output="",
                        provider="model-routing",
                        metadata={
                            "task_id": task_id,
                            "resolved_preset_mode": prepared.preset.preset_mode,
                            "requested_role_model_overrides": prepared.requested_payload.role_model_overrides,
                            "effective_role_model_overrides": prepared.effective_role_model_overrides,
                            "approval": approval.model_dump() if approval is not None else None,
                        },
                    ),
                    error_message=str(exc),
                )
        else:
            result = self.adapter.run_task(normalized_request)
            self.logger.info(
                "task finished",
                extra={
                    "task_id": task_id,
                    "status": result.status,
                    "provider": result.provider,
                },
            )
            response = normalize_task_result(result)

        response.data.metadata.update(
            {
                **self._build_common_metadata(prepared, task_id=task_id),
                "approval": approval.model_dump() if approval is not None else None,
            }
        )
        return response

    def _build_normalized_request(self, prepared: PreparedTaskExecution) -> dict[str, object]:
        """Build the adapter payload for single-pass execution."""
        normalized_request = prepared.execution_payload.model_dump()
        normalized_request["preset_mode"] = prepared.preset.preset_mode
        normalized_request["metadata"] = self._build_common_metadata(
            prepared,
            task_id=None,
        )
        normalized_request["model"] = prepared.task_model_selection.upstream_model
        normalized_request["provider_id"] = prepared.task_model_selection.provider_id
        if prepared.repo_analysis is not None:
            normalized_request["metadata"]["repo_analysis"] = prepared.repo_analysis.model_dump()
            if prepared.repo_analysis.repo_summary is not None:
                normalized_request["prompt"] = self._augment_prompt_with_repo_summary(
                    prepared.execution_payload.prompt,
                    prepared.repo_analysis,
                )
        return normalized_request

    def _build_common_metadata(
        self,
        prepared: PreparedTaskExecution,
        *,
        task_id: str | None,
    ) -> dict[str, object]:
        """Build shared task metadata used for execution and persistence."""
        metadata: dict[str, object] = {
            **prepared.execution_payload.metadata,
            "resolved_preset": prepared.preset.model_dump(),
            "resolved_preset_mode": prepared.preset.preset_mode,
            "requested_preset_mode": prepared.requested_payload.preset_mode,
            "used_default_preset": prepared.used_default_preset,
            "preset_summary": {
                "preset_mode": prepared.preset.preset_mode,
                "display_name": prepared.preset.display_name,
                "requires_repo_analysis": prepared.preset.requires_repo_analysis,
                "requires_approval": prepared.preset.requires_approval,
            },
            "requested_rule_template_id": prepared.requested_payload.rule_template_id,
            "requested_role_model_overrides": prepared.requested_payload.role_model_overrides,
            "task_model_selection": prepared.task_model_selection.model_dump(),
            "rule_template_selection": (
                prepared.rule_template_selection.model_dump()
                if prepared.rule_template_selection is not None
                else None
            ),
            "effective_role_model_overrides": prepared.effective_role_model_overrides,
            "repo_analysis": (
                prepared.repo_analysis.model_dump()
                if prepared.repo_analysis is not None
                else None
            ),
        }
        if task_id is not None:
            metadata["task_id"] = task_id
        return metadata

    def _build_pending_approval_response(
        self,
        *,
        task_id: str,
        prepared: PreparedTaskExecution,
        approval: ApprovalRecord,
    ) -> TaskResponse:
        """Return a blocking approval response before runtime execution."""
        return TaskResponse(
            status="pending_approval",
            message="Task is waiting for approval.",
            data=TaskResponseData(
                output="",
                provider="mindforge-approval-gate",
                metadata={
                    **self._build_common_metadata(prepared, task_id=task_id),
                    "approval": approval.model_dump(),
                },
            ),
        )

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
    return TaskService(
        get_settings(),
        get_preset_service(),
        get_model_routing_service(),
        get_coordinator_selection_service(),
        get_approval_service(),
        get_history_service(),
    )


def clear_task_service_cache() -> None:
    """Clear cached task service after mutable config changes."""
    get_task_service.cache_clear()
