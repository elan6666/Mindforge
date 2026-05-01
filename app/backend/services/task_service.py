"""Task orchestration service."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from uuid import uuid4

from app.backend.core.config import Settings, get_settings
from app.backend.core.logging import get_logger
from app.backend.integration.openhands_adapter import OpenHandsAdapter
from app.backend.schemas.academic_context import AcademicContextSummary
from app.backend.schemas.approval import ApprovalRecord
from app.backend.schemas.github_context import GitHubContextSummary
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
from app.backend.services.academic_context_service import (
    AcademicContextService,
    get_academic_context_service,
)
from app.backend.services.coordinator_selection_service import (
    CoordinatorSelectionError,
    CoordinatorSelectionService,
    get_coordinator_selection_service,
)
from app.backend.services.history_service import HistoryService, get_history_service
from app.backend.services.github_context_service import (
    GitHubContextError,
    GitHubContextService,
    get_github_context_service,
)
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

TOOL_FLAG_NAMES = ("web_search", "deep_analysis", "code_execution", "canvas")


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
    github_context: GitHubContextSummary | None
    academic_context: AcademicContextSummary | None


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
        github_context_service: GitHubContextService,
        academic_context_service: AcademicContextService,
    ) -> None:
        self.settings = settings
        self.preset_service = preset_service
        self.model_router = model_router
        self.coordinator_selector = coordinator_selector
        self.approval_service = approval_service
        self.history_service = history_service
        self.github_context_service = github_context_service
        self.academic_context_service = academic_context_service
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
                "metadata": self._build_execution_metadata(payload),
            }
        )

        repo_analysis = self._maybe_analyze_repo(
            execution_payload,
            preset.requires_repo_analysis,
        )
        try:
            github_context = self.github_context_service.resolve_context(
                github_repo=payload.github_repo,
                github_issue_number=payload.github_issue_number,
                github_pr_number=payload.github_pr_number,
            )
        except GitHubContextError as exc:
            return TaskResponse(
                status="failed",
                message="GitHub context resolution failed.",
                data=TaskResponseData(
                    output="",
                    provider="github-context",
                    metadata={
                        "github_repo": payload.github_repo,
                        "github_issue_number": payload.github_issue_number,
                        "github_pr_number": payload.github_pr_number,
                    },
                ),
                error_message=str(exc),
            )
        academic_context = self.academic_context_service.resolve_context(payload)
        return PreparedTaskExecution(
            requested_payload=payload,
            execution_payload=execution_payload,
            preset=preset,
            used_default_preset=used_default,
            task_model_selection=task_model_selection,
            rule_template_selection=rule_template_selection,
            effective_role_model_overrides=effective_role_model_overrides,
            repo_analysis=repo_analysis,
            github_context=github_context,
            academic_context=academic_context,
        )

    @staticmethod
    def _build_execution_metadata(payload: TaskRequest) -> dict[str, object]:
        """Merge structured composer fields into public task metadata."""
        metadata: dict[str, object] = dict(payload.metadata)
        if payload.conversation_id:
            metadata["conversation_id"] = payload.conversation_id
        if payload.conversation_history:
            metadata["conversation_history"] = [
                message.model_dump(mode="json", exclude_none=True)
                for message in payload.conversation_history
            ]
            metadata["conversation_turn_count"] = len(payload.conversation_history) + 1
        if payload.attachments:
            metadata["attachments"] = [
                attachment.model_dump(mode="json", exclude_none=True)
                for attachment in payload.attachments
            ]

        tool_flags = TaskService._collect_tool_flags(payload, metadata)
        if tool_flags:
            metadata["tool_flags"] = tool_flags
        return metadata

    @staticmethod
    def _collect_tool_flags(
        payload: TaskRequest,
        metadata: dict[str, object],
    ) -> dict[str, object]:
        """Normalize composer flags from legacy metadata, grouped flags, and top-level fields."""
        flags: dict[str, object] = {}
        for flag_name in TOOL_FLAG_NAMES:
            metadata_value = metadata.get(flag_name)
            if isinstance(metadata_value, bool):
                flags[flag_name] = metadata_value

        metadata_tool_flags = metadata.get("tool_flags")
        if isinstance(metadata_tool_flags, dict):
            flags.update(metadata_tool_flags)

        flags.update(payload.tool_flags.model_dump(mode="json", exclude_none=True))
        for flag_name in TOOL_FLAG_NAMES:
            request_value = getattr(payload, flag_name)
            if request_value is not None:
                flags[flag_name] = request_value
        return flags

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
        if prepared.preset.preset_mode in {"code-engineering", "paper-revision"}:
            try:
                response = self.orchestrator.execute_preset(
                    prepared.execution_payload,
                    prepared.preset,
                    repo_analysis=prepared.repo_analysis,
                    github_context=prepared.github_context,
                    academic_context=prepared.academic_context,
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
        normalized_request["prompt"] = self._augment_prompt_with_conversation_history(
            prepared.execution_payload.prompt,
            prepared.execution_payload.conversation_history,
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
        if prepared.github_context is not None:
            normalized_request["metadata"]["github_context"] = prepared.github_context.model_dump()
            normalized_request["prompt"] = self._augment_prompt_with_github_context(
                normalized_request["prompt"],
                prepared.github_context,
            )
        if prepared.academic_context is not None:
            normalized_request["metadata"]["academic_context"] = (
                prepared.academic_context.model_dump()
            )
            normalized_request["prompt"] = self._augment_prompt_with_academic_context(
                normalized_request["prompt"],
                prepared.academic_context,
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
            "github_repo": prepared.requested_payload.github_repo,
            "github_issue_number": prepared.requested_payload.github_issue_number,
            "github_pr_number": prepared.requested_payload.github_pr_number,
            "journal_name": prepared.requested_payload.journal_name,
            "journal_url": prepared.requested_payload.journal_url,
            "reference_paper_urls": prepared.requested_payload.reference_paper_urls,
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
            "github_context": (
                prepared.github_context.model_dump()
                if prepared.github_context is not None
                else None
            ),
            "academic_context": (
                prepared.academic_context.model_dump()
                if prepared.academic_context is not None
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

    @staticmethod
    def _augment_prompt_with_github_context(
        prompt: str,
        github_context: GitHubContextSummary,
    ) -> str:
        """Append GitHub summary text for single-pass executions."""
        lines = [prompt, "", "GitHub context:"]
        if github_context.repository is not None:
            repo = github_context.repository
            lines.append(
                f"- repository: {repo.full_name} | branch={repo.default_branch} | "
                f"language={repo.primary_language or 'unknown'} | stars={repo.stargazers_count}"
            )
            if repo.description:
                lines.append(f"- repository description: {repo.description}")
        if github_context.issue is not None:
            issue = github_context.issue
            lines.append(
                f"- issue: #{issue.number} {issue.title} [{issue.state}] by {issue.author or 'unknown'}"
            )
            if issue.body_excerpt:
                lines.append(f"- issue excerpt: {issue.body_excerpt}")
        if github_context.pull_request is not None:
            pull = github_context.pull_request
            lines.append(
                f"- pull request: #{pull.number} {pull.title} [{pull.state}] "
                f"head={pull.head_ref or '-'} base={pull.base_ref or '-'}"
            )
            if pull.body_excerpt:
                lines.append(f"- pull request excerpt: {pull.body_excerpt}")
        return "\n".join(lines)

    @staticmethod
    def _augment_prompt_with_academic_context(
        prompt: str,
        academic_context: AcademicContextSummary,
    ) -> str:
        """Append academic paper context for single-pass executions."""
        lines = [prompt, "", "Academic context:"]
        if academic_context.journal is not None:
            journal = academic_context.journal
            lines.append(
                f"- journal: {journal.journal_name or 'unknown'} | "
                f"url={journal.journal_url or '-'} | status={journal.status}"
            )
            if journal.title:
                lines.append(f"- journal guideline title: {journal.title}")
            if journal.excerpt:
                lines.append(f"- journal guideline excerpt: {journal.excerpt}")
        for index, reference in enumerate(
            academic_context.reference_papers,
            start=1,
        ):
            lines.append(
                f"- reference paper {index}: {reference.title or reference.url} "
                f"| status={reference.status}"
            )
            if reference.excerpt:
                lines.append(f"- reference paper {index} excerpt: {reference.excerpt}")
        for warning in academic_context.warnings:
            lines.append(f"- warning: {warning}")
        return "\n".join(lines)

    @staticmethod
    def _augment_prompt_with_conversation_history(
        prompt: str,
        conversation_history: list[object],
    ) -> str:
        """Prefix the current prompt with recent conversation context."""
        rendered_history = TaskService._format_conversation_history(conversation_history)
        if not rendered_history:
            return prompt
        return "\n".join(
            [
                "Conversation so far:",
                *rendered_history,
                "",
                "Current user request:",
                prompt,
            ]
        )

    @staticmethod
    def _format_conversation_history(conversation_history: list[object]) -> list[str]:
        """Render recent messages into a compact model-readable transcript."""
        rendered: list[str] = []
        for message in conversation_history[-16:]:
            role = str(getattr(message, "role", "user"))
            content = str(getattr(message, "content", "")).strip()
            if not content:
                continue
            label = {
                "assistant": "Assistant",
                "system": "System",
                "user": "User",
            }.get(role, role.title())
            if len(content) > 4000:
                content = content[:3997] + "..."
            rendered.append(f"{label}: {content}")
        return rendered


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
        get_github_context_service(),
        get_academic_context_service(),
    )


def clear_task_service_cache() -> None:
    """Clear cached task service after mutable config changes."""
    get_task_service.cache_clear()
