"""Task orchestration service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from time import perf_counter
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4

import requests

from app.backend.core.config import Settings, get_settings
from app.backend.core.logging import get_logger
from app.backend.integration.openhands_adapter import OpenHandsAdapter
from app.backend.schemas.academic_context import AcademicContextSummary
from app.backend.schemas.approval import ApprovalRecord
from app.backend.schemas.artifacts import ArtifactExportRequest
from app.backend.schemas.file_context import FileContextSummary
from app.backend.schemas.github_context import GitHubContextSummary
from app.backend.schemas.model import ModelSelection
from app.backend.schemas.preset import PresetDefinition
from app.backend.schemas.repository import RepoAnalysisResult
from app.backend.schemas.rule_template import RuleTemplateSelection
from app.backend.schemas.task import (
    LoopStageRetryRequest,
    TaskRequest,
    TaskResponse,
    TaskResponseData,
)
from app.backend.services.approval_service import (
    ApprovalError,
    ApprovalService,
    get_approval_service,
)
from app.backend.services.artifact_service import ArtifactService
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
from app.backend.services.file_context_service import (
    FileContextService,
    get_file_context_service,
)
from app.backend.services.mcp_service import get_mcp_service
from app.backend.services.loop_service import get_loop_service
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
from app.backend.services.project_space_service import get_project_space_service
from app.backend.services.repository_service import RepositoryAnalysisService
from app.backend.services.result_normalizer import normalize_task_result
from app.backend.services.skill_registry_service import get_skill_registry_service

TOOL_FLAG_NAMES = ("web_search", "deep_analysis", "code_execution", "canvas")
DOCUMENT_FORMAT_LABELS = {
    "pdf": "PDF",
    "docx": "Word",
    "md": "Markdown",
    "tex": "LaTeX",
}
DOCUMENT_GENERATION_PATTERN = re.compile(
    r"(帮我|请|给我|生成|制作|做|写|整理|输出|创建|create|generate|make|write)",
    re.IGNORECASE,
)
CURRENT_DOCUMENT_TERMS = (
    "热点",
    "热榜",
    "趋势",
    "最新",
    "今日",
    "今天",
    "近期",
    "排行榜",
    "trending",
    "hot",
    "latest",
    "recent",
    "news",
)
PYTHON_CODE_BLOCK_PATTERN = re.compile(
    r"```(?:python|py)\s*(?P<code>.*?)```",
    re.IGNORECASE | re.DOTALL,
)
EVIDENCE_URL_PATTERN = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)
EVIDENCE_SOURCE_PATTERN = re.compile(
    r"(?:source|sources|reference|references|来源|出处|引用|文件|命令)\s*[:：]\s*(?P<value>[^\n；;]+)",
    re.IGNORECASE,
)
EVIDENCE_DATE_PATTERN = re.compile(
    r"(?:20\d{2}[-/年.]\d{1,2}(?:[-/月.]\d{1,2}日?)?|20\d{2}|截至\s*\d{1,2}\s*月\s*\d{1,2}\s*日?)"
)
COUNTER_EVIDENCE_PATTERN = re.compile(
    r"(?:反证|反例|风险|不确定|counter[- ]?evidence|counterexample|risk|uncertainty|limitation)",
    re.IGNORECASE,
)
CODE_EXECUTION_TIMEOUT_SECONDS = 8
TEXT_LIMIT = 4000


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
        file_context_service: FileContextService | None = None,
    ) -> None:
        self.settings = settings
        self.preset_service = preset_service
        self.model_router = model_router
        self.coordinator_selector = coordinator_selector
        self.approval_service = approval_service
        self.history_service = history_service
        self.github_context_service = github_context_service
        self.academic_context_service = academic_context_service
        self.file_context_service = file_context_service or FileContextService(settings)
        self.artifact_service = ArtifactService(settings)
        self.logger = get_logger("app.task_service")
        self.adapter = OpenHandsAdapter(settings)
        self.orchestrator = SerialOrchestrationService(
            self.adapter,
            model_router,
            prefer_user_model_defaults=self._prefer_user_model_defaults(),
        )
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
        request = request.model_copy(
            update={
                "metadata": {
                    **request.metadata,
                    "tool_execution_approved": True,
                    "approved_task_id": task_id,
                }
            }
        )
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

    def retry_loop_stage(
        self,
        task_id: str,
        stage_id: str,
        payload: LoopStageRetryRequest,
    ):
        """Retry one persisted Loop stage and write the refreshed trace to history."""
        detail = self.history_service.get_task_detail(task_id)
        if detail is None:
            raise ValueError(f"Unknown task '{task_id}'.")
        metadata = dict(detail.metadata)
        loop_run = metadata.get("loop_run")
        if not isinstance(loop_run, dict):
            raise ValueError(f"Task '{task_id}' does not contain a Loop run.")
        stages = loop_run.get("stages")
        if not isinstance(stages, list):
            raise ValueError(f"Task '{task_id}' has no Loop stages to retry.")

        stage_index = next(
            (
                index
                for index, item in enumerate(stages)
                if isinstance(item, dict) and str(item.get("stage_id")) == stage_id
            ),
            None,
        )
        if stage_index is None:
            raise ValueError(f"Unknown Loop stage '{stage_id}'.")

        request = TaskRequest.model_validate(detail.request_payload)
        loop_id = str(loop_run.get("loop_id") or request.loop_id or "")
        loop = get_loop_service().get_loop(loop_id)
        if loop is None:
            raise ValueError(f"Unknown loop '{loop_id}'.")
        step = next((item for item in loop.steps if item.step_id == stage_id), None)
        if step is None:
            raise ValueError(f"Loop '{loop_id}' has no stage '{stage_id}'.")

        prepared = self._prepare_execution(request)
        if isinstance(prepared, TaskResponse):
            raise ValueError(prepared.error_message or prepared.message)
        normalized_request = self._build_normalized_request(prepared)
        role = next(
            (item for item in loop.roles if item.role_id == step.owner_role),
            None,
        )
        role_id = role.role_id if role is not None else step.owner_role
        role_models = self._resolve_loop_role_models(prepared, loop)
        model_id = payload.model_override or str(
            (stages[stage_index] if isinstance(stages[stage_index], dict) else {}).get("model")
            or ""
        )
        try:
            model_selection = self.model_router.resolve_for_role(
                preset_mode=prepared.preset.preset_mode,
                task_type=prepared.execution_payload.task_type,
                role=role_id,
                explicit_model=model_id or None,
                prefer_user_default=self._prefer_user_model_defaults(),
            )
        except ModelRoutingError:
            model_selection = role_models[role_id]

        previous_summaries = [
            {
                "stage_id": str(item.get("stage_id") or ""),
                "stage_name": str(item.get("stage_name") or ""),
                "role": str(item.get("role") or ""),
                "model": str(item.get("model") or ""),
                "summary": str(item.get("summary") or ""),
            }
            for item in stages[:stage_index]
            if isinstance(item, dict)
        ]
        retry_prompt = self._compose_loop_stage_prompt(
            base_prompt=str(normalized_request.get("prompt") or request.prompt),
            loop_name=loop.name,
            role_name=role.name if role is not None else role_id,
            role_id=role_id,
            role_responsibility=(
                role.responsibility if role is not None else "Run this Loop stage."
            ),
            step_title=step.title,
            step_instruction=step.instruction,
            expected_output=step.expected_output,
            evidence_required=step.evidence_required,
            evidence_rules=loop.evidence_rules,
            previous_summaries=previous_summaries,
            order=stage_index + 1,
            total=len(loop.steps),
        )
        if payload.note:
            retry_prompt = f"{retry_prompt}\n\nRetry operator note:\n{payload.note}"

        started_at = datetime.now().astimezone().isoformat()
        start = perf_counter()
        result = self.adapter.run_task(
            {
                **normalized_request,
                "prompt": retry_prompt,
                "model": model_selection.upstream_model,
                "provider_id": model_selection.provider_id,
                "metadata": {
                    **(
                        normalized_request.get("metadata")
                        if isinstance(normalized_request.get("metadata"), dict)
                        else {}
                    ),
                    "loop_id": loop.loop_id,
                    "loop_name": loop.name,
                    "loop_role": role_id,
                    "loop_stage": step.step_id,
                    "loop_stage_name": step.title,
                    "loop_stage_order": stage_index + 1,
                    "loop_retry": True,
                    "loop_retry_note": payload.note,
                    "loop_model": model_selection.model_id,
                    "loop_model_selection": model_selection.model_dump(mode="json"),
                    "loop_previous_summaries": previous_summaries,
                },
            }
        )
        duration_ms = int((perf_counter() - start) * 1000)
        completed_at = datetime.now().astimezone().isoformat()

        original_stage = stages[stage_index] if isinstance(stages[stage_index], dict) else {}
        retry_count = int(original_stage.get("retry_count") or 0) + 1
        summary = self._summarize_output(result.output)
        stages[stage_index] = {
            **original_stage,
            "order": stage_index + 1,
            "stage_id": step.step_id,
            "stage_name": step.title,
            "role": role_id,
            "role_name": role.name if role is not None else role_id,
            "status": result.status,
            "summary": summary or step.instruction,
            "output": result.output,
            "evidence_required": step.evidence_required,
            "expected_output": step.expected_output,
            "model": model_selection.model_id,
            "model_selection": model_selection.model_dump(mode="json"),
            "provider": result.provider,
            "metadata": result.metadata,
            "error_message": result.error_message,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "attempt": retry_count + 1,
            "retry_count": retry_count,
            "retry_note": payload.note,
        }

        failed_stage = next(
            (
                str(item.get("stage_id") or "")
                for item in stages
                if isinstance(item, dict) and item.get("status") != "completed"
            ),
            None,
        )
        status = "failed" if failed_stage else "completed"
        loop_run["status"] = status
        loop_run["stages"] = stages
        loop_run["completed_at"] = completed_at
        self._decorate_loop_run_runtime(loop_run)
        metadata["loop_run"] = loop_run
        metadata["failed_stage"] = failed_stage
        metadata["artifact_provenance"] = self._build_artifact_provenance(metadata)
        output = self._format_loop_output(
            loop_name=str(loop_run.get("loop_name") or loop.name),
            user_prompt=request.prompt,
            stages=[stage for stage in stages if isinstance(stage, dict)],
            failed_stage=failed_stage,
        )
        updated = self.history_service.update_task_result_metadata(
            task_id,
            metadata=metadata,
            output=output,
            status=status,
            message=(
                f"Loop stage '{stage_id}' retried successfully."
                if status == "completed"
                else f"Loop stage '{stage_id}' retry finished with a failure."
            ),
            provider="loop-orchestrator",
            error_message=(
                f"Loop stage '{failed_stage}' failed." if failed_stage else None
            ),
        )
        if updated is None:
            raise ValueError(f"Unknown task '{task_id}'.")
        return updated

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
                prefer_user_default=self._prefer_user_model_defaults(),
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
        project_context = self._resolve_project_context(payload)
        payload = self._apply_project_defaults(payload, project_context)
        execution_metadata = self._build_execution_metadata(payload)
        if project_context:
            execution_metadata["project_context"] = project_context
        document_generation = self._detect_document_generation_intent(payload)
        if document_generation:
            execution_metadata["document_generation"] = document_generation
            tool_flags = dict(execution_metadata.get("tool_flags") or {})
            tool_flags.setdefault("deep_analysis", True)
            if document_generation.get("needs_web_search") is True:
                tool_flags["web_search"] = True
            execution_metadata["tool_flags"] = tool_flags
        file_context = self._resolve_file_context(payload)
        if file_context is not None:
            execution_metadata["file_context"] = file_context.model_dump(mode="json")
        skills_context = self._resolve_skill_context(payload)
        if skills_context:
            execution_metadata["skills_context"] = skills_context
        mcp_context = self._resolve_mcp_context(payload)
        if mcp_context:
            execution_metadata["mcp_context"] = mcp_context
        tool_context = self._resolve_tool_context(payload, execution_metadata)
        if tool_context:
            execution_metadata["tool_context"] = tool_context
        execution_payload = payload.model_copy(
            update={
                "model_override": effective_model_override,
                "role_model_overrides": effective_role_model_overrides,
                "metadata": execution_metadata,
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

    def _resolve_file_context(self, payload: TaskRequest) -> FileContextSummary | None:
        """Resolve parsed uploaded file chunks plus legacy text excerpts."""
        file_ids = [
            attachment.file_id
            for attachment in payload.attachments
            if attachment.file_id
        ]
        file_context = self.file_context_service.resolve_context(
            file_ids=file_ids,
            query=payload.prompt,
            limit=8,
        )
        legacy_chunks = []
        for index, attachment in enumerate(payload.attachments):
            if attachment.file_id or not attachment.text_excerpt:
                continue
            legacy_chunks.append(
                {
                    "chunk_id": f"inline:{attachment.id or index}",
                    "file_id": attachment.id or f"inline-{index}",
                    "order": index,
                    "text": attachment.text_excerpt,
                    "char_start": 0,
                    "char_end": len(attachment.text_excerpt),
                    "score": 0,
                }
            )
        if not file_ids and not legacy_chunks:
            return None
        payload_data = file_context.model_dump(mode="json")
        payload_data["chunks"].extend(legacy_chunks)
        if legacy_chunks and payload_data["status"] in {"skipped", "not_found", "no_chunks"}:
            payload_data["status"] = "retrieved"
        return FileContextSummary.model_validate(payload_data)

    @staticmethod
    def _resolve_skill_context(payload: TaskRequest) -> dict[str, object]:
        """Load selected skills as public prompt context metadata."""
        skill_ids = TaskService._normalize_skills(payload.skills)
        if not skill_ids:
            return {}
        loaded = get_skill_registry_service().load_prompt_context(skill_ids)
        found_ids = {item.skill_id for item in loaded}
        return {
            "status": "ready" if loaded else "not_found",
            "runtime": "prompt-context",
            "skills": [
                {
                    "skill_id": item.skill_id,
                    "name": item.name,
                    "description": item.description,
                    "content_excerpt": item.content_excerpt,
                }
                for item in loaded
            ],
            "missing": [skill_id for skill_id in skill_ids if skill_id not in found_ids],
        }

    def _prefer_user_model_defaults(self) -> bool:
        """Use user-created model defaults for real model API execution."""
        return self.settings.openhands_mode.lower() in {"model-api", "model_api"}

    @staticmethod
    def _build_execution_metadata(payload: TaskRequest) -> dict[str, object]:
        """Merge structured composer fields into public task metadata."""
        metadata: dict[str, object] = dict(payload.metadata)
        if payload.loop_id:
            loop = get_loop_service().get_loop(payload.loop_id)
            if loop is not None:
                metadata["loop_id"] = loop.loop_id
                metadata["loop"] = {
                    "loop_id": loop.loop_id,
                    "name": loop.name,
                    "version": loop.version,
                    "forge_id": loop.forge_id,
                    "description": loop.description,
                    "source": loop.source,
                }
                metadata["loop_run"] = {
                    "loop_id": loop.loop_id,
                    "loop_name": loop.name,
                    "version": loop.version,
                    "forge_id": loop.forge_id,
                    "status": "prepared",
                    "roles": [
                        role.model_dump(mode="json")
                        for role in loop.roles
                    ],
                    "stages": [
                        {
                            "order": index,
                            "stage_id": step.step_id,
                            "stage_name": step.title,
                            "role": step.owner_role,
                            "status": "pending",
                            "summary": step.instruction,
                            "output": "",
                            "evidence_required": step.evidence_required,
                            "expected_output": step.expected_output,
                        }
                        for index, step in enumerate(loop.steps, start=1)
                    ],
                    "evidence_rules": loop.evidence_rules,
                    "artifact_outputs": [
                        artifact.model_dump(mode="json")
                        for artifact in loop.artifact_outputs
                    ],
                    "improvement_count": loop.improvement_count,
                }
        if payload.project_id:
            metadata["project_id"] = payload.project_id
        if payload.conversation_id:
            metadata["conversation_id"] = payload.conversation_id
        if payload.conversation_history:
            metadata["conversation_history"] = [
                message.model_dump(mode="json", exclude_none=True)
                for message in payload.conversation_history
            ]
            metadata["conversation_turn_count"] = len(payload.conversation_history) + 1
        if payload.skills:
            metadata["skills"] = TaskService._normalize_skills(payload.skills)
        if payload.mcp_server_ids:
            metadata["mcp_server_ids"] = TaskService._normalize_skills(payload.mcp_server_ids)
        if payload.attachments:
            metadata["attachments"] = [
                attachment.model_dump(mode="json", exclude_none=True)
                for attachment in payload.attachments
            ]
        metadata["runtime_context"] = TaskService._build_runtime_context()

        tool_flags = TaskService._collect_tool_flags(payload, metadata)
        if tool_flags:
            metadata["tool_flags"] = tool_flags
        return metadata

    @staticmethod
    def _resolve_mcp_context(payload: TaskRequest) -> dict[str, object]:
        """Resolve selected MCP server tool catalogs for model-readable context."""
        server_ids = TaskService._normalize_skills(payload.mcp_server_ids)
        if not server_ids:
            return {}
        return get_mcp_service().prompt_context(server_ids)

    @staticmethod
    def _resolve_project_context(payload: TaskRequest) -> dict[str, object]:
        """Resolve reusable project-space instructions, memory, and files."""
        if not payload.project_id:
            return {}
        return get_project_space_service().prompt_context(
            payload.project_id,
            query=payload.prompt,
        ).model_dump(mode="json", exclude_none=True)

    @staticmethod
    def _apply_project_defaults(
        payload: TaskRequest,
        project_context: dict[str, object],
    ) -> TaskRequest:
        """Merge project defaults without overriding explicit task config."""
        project = project_context.get("project")
        if not isinstance(project, dict):
            return payload
        updates: dict[str, object] = {}
        if not payload.repo_path and project.get("repo_path"):
            updates["repo_path"] = project["repo_path"]
        if not payload.github_repo and project.get("github_repo"):
            updates["github_repo"] = project["github_repo"]
        project_skills = project.get("skill_ids")
        if isinstance(project_skills, list):
            merged_skills = TaskService._normalize_skills(
                [str(item) for item in project_skills] + payload.skills
            )
            if merged_skills:
                updates["skills"] = merged_skills
        project_mcp_servers = project.get("mcp_server_ids")
        if isinstance(project_mcp_servers, list):
            merged_mcp_servers = TaskService._normalize_skills(
                [str(item) for item in project_mcp_servers] + payload.mcp_server_ids
            )
            if merged_mcp_servers:
                updates["mcp_server_ids"] = merged_mcp_servers
        return payload.model_copy(update=updates) if updates else payload

    @staticmethod
    def _detect_document_generation_intent(
        payload: TaskRequest,
    ) -> dict[str, object] | None:
        """Detect natural-language requests that should produce a downloadable document."""
        prompt = payload.prompt.strip()
        if not prompt:
            return None
        lowered = prompt.lower()
        target_format = TaskService._detect_requested_document_format(lowered)
        if target_format is None:
            return None
        if DOCUMENT_GENERATION_PATTERN.search(prompt) is None:
            return None
        topic = TaskService._clean_document_topic(prompt, target_format)
        title = topic or f"Mindforge {DOCUMENT_FORMAT_LABELS[target_format]} 文档"
        needs_web_search = any(term in lowered for term in CURRENT_DOCUMENT_TERMS)
        return {
            "status": "requested",
            "source": "natural-language",
            "format": target_format,
            "format_label": DOCUMENT_FORMAT_LABELS[target_format],
            "title": title[:96],
            "topic": topic,
            "needs_web_search": needs_web_search,
        }

    @staticmethod
    def _detect_requested_document_format(lowered_prompt: str) -> str | None:
        """Map document format aliases, including common Word typo, to artifact formats."""
        if re.search(r"(^|[^a-z])pdf([^a-z]|$)|pdf文件|pdf报告|pdf文档", lowered_prompt):
            return "pdf"
        if re.search(r"\b(docx|doc|word)\b|world文档|word文档|world文件|word文件|微软文档", lowered_prompt):
            return "docx"
        if re.search(r"\b(markdown|md)\b|markdown文档|md文档", lowered_prompt):
            return "md"
        if re.search(r"\b(latex|tex)\b|latex文档|tex文档", lowered_prompt):
            return "tex"
        return None

    @staticmethod
    def _clean_document_topic(prompt: str, target_format: str) -> str:
        """Derive a human-readable title from the user's document request."""
        value = prompt.strip()
        value = re.sub(
            r"(帮我|请|给我|生成|制作|做|写|整理|输出|创建|一个|一份|create|generate|make|write)",
            "",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"(pdf|docx|doc|word|world|markdown|md|latex|tex|文件|文档|报告|版|排版后?的?)",
            "",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(r"[：:，,。.!！?？\s]+", " ", value).strip()
        if not value:
            return f"Mindforge {DOCUMENT_FORMAT_LABELS[target_format]} 文档"
        if not re.search(r"(报告|简报|分析|文档)$", value):
            value = f"{value}报告"
        return value

    @staticmethod
    def _build_runtime_context() -> dict[str, str]:
        """Capture runtime date/time facts that should not depend on web search."""
        now = datetime.now().astimezone()
        return {
            "current_date": now.date().isoformat(),
            "current_time": now.strftime("%H:%M:%S"),
            "weekday": now.strftime("%A"),
            "timezone": now.tzname() or "",
            "utc_offset": now.strftime("%z"),
        }

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

    def _resolve_tool_context(
        self,
        payload: TaskRequest,
        metadata: dict[str, object],
    ) -> dict[str, object]:
        """Execute requested lightweight tools and return model-ready context."""
        tool_flags = metadata.get("tool_flags")
        if not isinstance(tool_flags, dict):
            return {}

        context: dict[str, object] = {}
        if tool_flags.get("deep_analysis") is True:
            context["deep_analysis"] = {
                "status": "enabled",
                "effect": "The model call receives deeper analysis instructions and a larger token budget.",
            }
        if tool_flags.get("web_search") is True:
            context["web_search"] = self._run_web_search(payload.prompt)
        if tool_flags.get("code_execution") is True:
            if self._code_execution_allowed(payload, metadata):
                context["code_execution"] = self._run_python_code(payload)
            else:
                context["code_execution"] = {
                    "status": "blocked",
                    "language": "python",
                    "reason": "Code execution requires an approved task.",
                    "policy": {
                        "requires_approval": self.settings.code_execution_requires_approval,
                        "approved": bool(metadata.get("tool_execution_approved")),
                    },
                }
        if tool_flags.get("canvas") is True:
            context["canvas"] = {
                "status": "enabled",
                "artifact_strategy": "model-output-markdown",
                "effect": "The final model output is saved as an editable canvas artifact.",
            }
        return context

    def _code_execution_allowed(
        self,
        payload: TaskRequest,
        metadata: dict[str, object],
    ) -> bool:
        """Decide whether user-provided code may execute in the local runtime."""
        if not self.settings.code_execution_requires_approval:
            return True
        return bool(
            metadata.get("tool_execution_approved")
            or payload.metadata.get("tool_execution_approved")
        )

    @staticmethod
    def _run_web_search(query: str) -> dict[str, object]:
        """Fetch no-key web context and read top result pages."""
        instant_results: list[dict[str, str]] = []
        search_results: list[dict[str, str]] = []
        errors: list[str] = []
        try:
            response = requests.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_redirect": "1",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
                headers={"User-Agent": "Mindforge/0.1"},
                timeout=8,
            )
            response.raise_for_status()
            body = response.json()
        except (ValueError, requests.RequestException, AttributeError) as exc:
            body = {}
            errors.append(str(exc))

        abstract = str(body.get("AbstractText") or "").strip()
        abstract_url = str(body.get("AbstractURL") or "").strip()
        if abstract:
            instant_results.append(
                {
                    "title": str(body.get("Heading") or "DuckDuckGo abstract"),
                    "url": abstract_url,
                    "snippet": abstract[:TEXT_LIMIT],
                    "source_type": "instant_answer",
                }
            )

        def add_related(items: list[object]) -> None:
            for item in items:
                if len(instant_results) >= 5:
                    return
                if not isinstance(item, dict):
                    continue
                nested = item.get("Topics")
                if isinstance(nested, list):
                    add_related(nested)
                    continue
                text = str(item.get("Text") or "").strip()
                if not text:
                    continue
                instant_results.append(
                    {
                        "title": text.split(" - ", 1)[0][:120],
                        "url": str(item.get("FirstURL") or ""),
                        "snippet": text[:TEXT_LIMIT],
                        "source_type": "instant_answer",
                    }
                )

        related_topics = body.get("RelatedTopics")
        if isinstance(related_topics, list):
            add_related(related_topics)

        try:
            search_results = TaskService._run_duckduckgo_html_search(query)
        except (requests.RequestException, AttributeError) as exc:
            errors.append(str(exc))

        merged_results = TaskService._merge_search_results(instant_results, search_results)
        read_results = TaskService._read_search_result_pages(merged_results, query)
        final_results = read_results or merged_results
        return {
            "status": "fetched" if final_results else ("failed" if errors else "no_results"),
            "query": query,
            "provider": "duckduckgo+page-reader",
            "results": final_results,
            "citations": TaskService._build_web_citations(final_results),
            "errors": errors,
        }

    @staticmethod
    def _run_duckduckgo_html_search(query: str) -> list[dict[str, str]]:
        """Search DuckDuckGo HTML results without an API key."""
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mindforge/0.1"},
            timeout=8,
        )
        response.raise_for_status()
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []
        html = getattr(response, "text", "")
        if not isinstance(html, str) or not html.strip():
            return []
        soup = BeautifulSoup(html, "html.parser")
        results: list[dict[str, str]] = []
        for result in soup.select(".result")[:8]:
            link = result.select_one(".result__a")
            if link is None:
                continue
            raw_url = str(link.get("href") or "")
            url = TaskService._normalize_duckduckgo_url(raw_url)
            title = link.get_text(" ", strip=True)
            snippet_node = result.select_one(".result__snippet")
            snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
            if url and title:
                results.append(
                    {
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "source_type": "search_result",
                    }
                )
        return results

    @staticmethod
    def _normalize_duckduckgo_url(raw_url: str) -> str:
        """Extract the real target from DuckDuckGo redirect URLs."""
        if not raw_url:
            return ""
        parsed = urlparse(raw_url)
        if "duckduckgo.com" in parsed.netloc and parsed.query:
            uddg = parse_qs(parsed.query).get("uddg")
            if uddg:
                return unquote(uddg[0])
        return raw_url

    @staticmethod
    def _merge_search_results(
        *groups: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Deduplicate result groups while preserving useful order."""
        merged: list[dict[str, str]] = []
        seen: set[str] = set()
        for group in groups:
            for result in group:
                url = str(result.get("url") or "")
                key = url.rstrip("/") or str(result.get("title") or "")
                if not key or key in seen:
                    continue
                seen.add(key)
                merged.append(result)
        return merged[:8]

    @staticmethod
    def _read_search_result_pages(
        results: list[dict[str, str]],
        query: str,
    ) -> list[dict[str, str]]:
        """Fetch and extract readable text from top result pages."""
        enriched: list[dict[str, str]] = []
        for result in results[:5]:
            url = str(result.get("url") or "")
            if not url.startswith(("http://", "https://")):
                enriched.append(result)
                continue
            page_text = ""
            read_method = ""
            try:
                page = requests.get(
                    url,
                    headers={"User-Agent": "Mindforge/0.1"},
                    timeout=8,
                )
                page.raise_for_status()
                page_text = TaskService._extract_webpage_text(page.text)
            except (requests.RequestException, AttributeError):
                page_text = ""
            if page_text:
                read_method = "http"
            else:
                page_text = TaskService._read_page_with_browser(url)
                read_method = "browser" if page_text else ""
            if not page_text:
                enriched.append(result)
                continue
            snippet = TaskService._select_relevant_excerpt(page_text, query)
            enriched.append(
                {
                    **result,
                    "snippet": snippet or str(result.get("snippet") or ""),
                    "content_excerpt": page_text[:TEXT_LIMIT],
                    "source_type": "browser_page" if read_method == "browser" else "webpage",
                    "read_method": read_method,
                    "score": str(TaskService._score_text(page_text, query)),
                }
            )
        return sorted(
            enriched,
            key=lambda item: float(item.get("score") or 0),
            reverse=True,
        )

    @staticmethod
    def _read_page_with_browser(url: str) -> str:
        """Render a page with Playwright and extract visible text when HTTP parsing fails."""
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError:
            return ""
        browser = None
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=12000)
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)
                except PlaywrightError:
                    pass
                texts = page.locator("article, main").all_inner_texts()
                text = "\n\n".join(part.strip() for part in texts if part.strip())
                if not text:
                    text = page.locator("body").inner_text(timeout=3000)
                return re.sub(r"\n{3,}", "\n\n", text).strip()
        except Exception:
            return ""
        finally:
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass

    @staticmethod
    def _build_web_citations(results: list[dict[str, str]]) -> list[dict[str, str]]:
        """Return compact citation metadata for model prompts and UI inspection."""
        citations: list[dict[str, str]] = []
        for index, result in enumerate(results[:5], start=1):
            url = str(result.get("url") or "")
            if not url:
                continue
            citations.append(
                {
                    "index": str(index),
                    "title": str(result.get("title") or f"Result {index}"),
                    "url": url,
                    "snippet": str(result.get("snippet") or "")[:500],
                }
            )
        return citations

    @staticmethod
    def _extract_webpage_text(html: str) -> str:
        """Extract readable webpage text from HTML."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return re.sub(r"<[^>]+>", " ", html)
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
            tag.decompose()
        candidates = soup.find_all(["article", "main"])
        text = "\n".join(
            node.get_text("\n", strip=True)
            for node in candidates
            if node.get_text(strip=True)
        )
        if not text:
            text = soup.get_text("\n", strip=True)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    @staticmethod
    def _select_relevant_excerpt(text: str, query: str) -> str:
        """Pick a compact query-relevant excerpt from page text."""
        if not text:
            return ""
        terms = [term.lower() for term in re.findall(r"[\w\u4e00-\u9fff]+", query)]
        paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
        if not terms:
            return text[:TEXT_LIMIT]
        best = ""
        best_score = -1
        for paragraph in paragraphs[:80]:
            lower = paragraph.lower()
            score = sum(lower.count(term) for term in terms)
            if score > best_score:
                best = paragraph
                best_score = score
        return (best or text)[:TEXT_LIMIT]

    @staticmethod
    def _score_text(text: str, query: str) -> float:
        """Simple lexical relevance score."""
        lower = text.lower()
        terms = set(re.findall(r"[\w\u4e00-\u9fff]+", query.lower()))
        return float(sum(lower.count(term) for term in terms))

    @staticmethod
    def _run_python_code(payload: TaskRequest) -> dict[str, object]:
        """Run an explicit fenced Python block in an isolated temporary directory."""
        code = TaskService._extract_python_code(payload)
        if not code:
            return {
                "status": "skipped",
                "language": "python",
                "reason": "No fenced Python code block was provided.",
            }
        if len(code) > 12000:
            return {
                "status": "skipped",
                "language": "python",
                "reason": "Python code block is too large to execute safely.",
            }

        with tempfile.TemporaryDirectory(prefix="mindforge-code-") as temp_dir:
            script_path = Path(temp_dir) / "snippet.py"
            script_path.write_text(code, encoding="utf-8")
            try:
                completed = subprocess.run(
                    [sys.executable, "-I", str(script_path)],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=CODE_EXECUTION_TIMEOUT_SECONDS,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                stdout = (
                    exc.stdout.decode(errors="replace")
                    if isinstance(exc.stdout, bytes)
                    else exc.stdout
                )
                stderr = (
                    exc.stderr.decode(errors="replace")
                    if isinstance(exc.stderr, bytes)
                    else exc.stderr
                )
                return {
                    "status": "timeout",
                    "language": "python",
                    "timeout_seconds": CODE_EXECUTION_TIMEOUT_SECONDS,
                    "stdout": TaskService._truncate_text(stdout or ""),
                    "stderr": TaskService._truncate_text(stderr or ""),
                }

        return {
            "status": "completed" if completed.returncode == 0 else "failed",
            "language": "python",
            "exit_code": completed.returncode,
            "stdout": TaskService._truncate_text(completed.stdout),
            "stderr": TaskService._truncate_text(completed.stderr),
        }

    @staticmethod
    def _extract_python_code(payload: TaskRequest) -> str:
        """Extract the first explicit Python code block from prompt or text attachments."""
        sources = [payload.prompt]
        sources.extend(
            attachment.text_excerpt or ""
            for attachment in payload.attachments
            if attachment.text_excerpt
        )
        for source in sources:
            match = PYTHON_CODE_BLOCK_PATTERN.search(source)
            if match:
                return match.group("code").strip()
        return ""

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
        if prepared.execution_payload.loop_id:
            try:
                response = self._execute_loop_prepared(prepared, normalized_request)
            except ModelRoutingError as exc:
                return TaskResponse(
                    status="failed",
                    message="Model routing failed during Loop execution setup.",
                    data=TaskResponseData(
                        output="",
                        provider="model-routing",
                        metadata={
                            "task_id": task_id,
                            "loop_id": prepared.execution_payload.loop_id,
                            "requested_role_model_overrides": prepared.requested_payload.role_model_overrides,
                            "effective_role_model_overrides": prepared.effective_role_model_overrides,
                            "approval": approval.model_dump() if approval is not None else None,
                        },
                    ),
                    error_message=str(exc),
                )
        elif prepared.preset.preset_mode in {"code-engineering", "paper-revision"}:
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

        response.data.metadata = {
            **self._build_common_metadata(prepared, task_id=task_id),
            **response.data.metadata,
            "approval": approval.model_dump() if approval is not None else None,
        }
        self._attach_loop_run_trace(response)
        self._attach_canvas_artifacts(response)
        self._attach_generated_document_artifact(response)
        self._attach_execution_report(response)
        return response

    def _execute_loop_prepared(
        self,
        prepared: PreparedTaskExecution,
        normalized_request: dict[str, object],
    ) -> TaskResponse:
        """Execute a portable Loop as concrete per-role model calls."""
        loop_id = prepared.execution_payload.loop_id
        loop = get_loop_service().get_loop(loop_id or "")
        if loop is None:
            return TaskResponse(
                status="failed",
                message="Loop execution failed.",
                data=TaskResponseData(
                    output="",
                    provider="loop-orchestrator",
                    metadata={"loop_id": loop_id},
                ),
                error_message=f"Unknown loop '{loop_id}'.",
            )

        role_models = self._resolve_loop_role_models(prepared, loop)
        stages: list[dict[str, object]] = []
        previous_summaries: list[dict[str, object]] = []
        failed_stage: str | None = None

        for order, step in enumerate(loop.steps, start=1):
            role = next(
                (item for item in loop.roles if item.role_id == step.owner_role),
                None,
            )
            role_id = role.role_id if role is not None else step.owner_role
            model_selection = role_models[role_id]
            stage_payload = {
                **normalized_request,
                "prompt": self._compose_loop_stage_prompt(
                    base_prompt=str(normalized_request.get("prompt") or ""),
                    loop_name=loop.name,
                    role_name=role.name if role is not None else role_id,
                    role_id=role_id,
                    role_responsibility=(
                        role.responsibility if role is not None else "Run this Loop stage."
                    ),
                    step_title=step.title,
                    step_instruction=step.instruction,
                    expected_output=step.expected_output,
                    evidence_required=step.evidence_required,
                    evidence_rules=loop.evidence_rules,
                    previous_summaries=previous_summaries,
                    order=order,
                    total=len(loop.steps),
                ),
                "model": model_selection.upstream_model,
                "provider_id": model_selection.provider_id,
                "metadata": {
                    **(
                        normalized_request.get("metadata")
                        if isinstance(normalized_request.get("metadata"), dict)
                        else {}
                    ),
                    "loop_id": loop.loop_id,
                    "loop_name": loop.name,
                    "loop_role": role_id,
                    "loop_stage": step.step_id,
                    "loop_stage_name": step.title,
                    "loop_stage_order": order,
                    "loop_model": model_selection.model_id,
                    "loop_model_selection": model_selection.model_dump(mode="json"),
                    "loop_previous_summaries": previous_summaries,
                },
            }
            started_at = datetime.now().astimezone().isoformat()
            start = perf_counter()
            result = self.adapter.run_task(stage_payload)
            duration_ms = int((perf_counter() - start) * 1000)
            completed_at = datetime.now().astimezone().isoformat()
            summary = self._summarize_output(result.output)
            stage = {
                "order": order,
                "stage_id": step.step_id,
                "stage_name": step.title,
                "role": role_id,
                "role_name": role.name if role is not None else role_id,
                "status": result.status,
                "summary": summary or step.instruction,
                "output": result.output,
                "evidence_required": step.evidence_required,
                "expected_output": step.expected_output,
                "model": model_selection.model_id,
                "model_selection": model_selection.model_dump(mode="json"),
                "provider": result.provider,
                "metadata": result.metadata,
                "error_message": result.error_message,
                "started_at": started_at,
                "completed_at": completed_at,
                "duration_ms": duration_ms,
                "attempt": 1,
                "retry_count": 0,
            }
            stages.append(stage)
            previous_summaries.append(
                {
                    "stage_id": step.step_id,
                    "stage_name": step.title,
                    "role": role_id,
                    "model": model_selection.model_id,
                    "summary": summary,
                }
            )
            if result.status != "completed":
                failed_stage = step.step_id
                break

        status = "failed" if failed_stage else "completed"
        loop_run = {
            "loop_id": loop.loop_id,
            "loop_name": loop.name,
            "version": loop.version,
            "forge_id": loop.forge_id,
            "status": status,
            "roles": [role.model_dump(mode="json") for role in loop.roles],
            "stages": stages,
            "evidence_rules": loop.evidence_rules,
            "artifact_outputs": [
                artifact.model_dump(mode="json") for artifact in loop.artifact_outputs
            ],
            "improvement_count": loop.improvement_count,
            "completed_at": datetime.now().astimezone().isoformat(),
        }
        self._decorate_loop_run_runtime(loop_run)
        return TaskResponse(
            status=status,
            message=(
                "Loop executed successfully."
                if status == "completed"
                else "Loop execution failed."
            ),
            data=TaskResponseData(
                output=self._format_loop_output(
                    loop_name=loop.name,
                    user_prompt=prepared.execution_payload.prompt,
                    stages=stages,
                    failed_stage=failed_stage,
                ),
                provider="loop-orchestrator",
                metadata={
                    "loop_id": loop.loop_id,
                    "loop_run": loop_run,
                    "loop_model_routing": {
                        role_id: selection.model_dump(mode="json")
                        for role_id, selection in role_models.items()
                    },
                    "failed_stage": failed_stage,
                },
            ),
            error_message=(
                f"Loop stage '{failed_stage}' failed." if failed_stage else None
            ),
        )

    def _resolve_loop_role_models(
        self,
        prepared: PreparedTaskExecution,
        loop: object,
    ) -> dict[str, ModelSelection]:
        """Assign models to Loop roles, preferring distinct user models."""
        roles = list(getattr(loop, "roles", []) or [])
        explicit = dict(prepared.effective_role_model_overrides)
        assigned: dict[str, ModelSelection] = {}
        used_model_ids: set[str] = set()

        preferred_ids = self._preferred_loop_model_ids(str(getattr(loop, "loop_id", "")))
        custom_models = [
            model
            for model in self.model_router.registry.iter_enabled_custom_models()
            if model.model_id not in preferred_ids
        ]
        fallback_ids = [*preferred_ids, *[model.model_id for model in custom_models]]

        for index, role in enumerate(roles):
            role_id = str(getattr(role, "role_id", "") or f"role-{index + 1}")
            model_id = explicit.get(role_id)
            if not model_id:
                model_id = self._next_loop_model_id(
                    fallback_ids=fallback_ids,
                    used_model_ids=used_model_ids,
                    role_index=index,
                )
            selection = self.model_router.resolve_for_role(
                preset_mode=prepared.preset.preset_mode,
                task_type=prepared.execution_payload.task_type,
                role=role_id,
                explicit_model=model_id,
                prefer_user_default=self._prefer_user_model_defaults(),
            )
            assigned[role_id] = selection
            used_model_ids.add(selection.model_id)
        return assigned

    def _next_loop_model_id(
        self,
        *,
        fallback_ids: list[str],
        used_model_ids: set[str],
        role_index: int,
    ) -> str | None:
        """Return the next enabled model id while avoiding repeats when possible."""
        valid_ids = [
            model_id
            for model_id in fallback_ids
            if self.model_router.registry.get_model(model_id) is not None
        ]
        for model_id in valid_ids:
            if model_id not in used_model_ids:
                return model_id
        if valid_ids:
            return valid_ids[role_index % len(valid_ids)]
        return None

    @staticmethod
    def _preferred_loop_model_ids(loop_id: str) -> list[str]:
        """Return role-order model preferences for built-in demo Loops."""
        if loop_id != "worldcup-prediction-loop":
            return []
        return [
            "deepseek-v4-flash",
            "Doubao-Seed-2.0-lite",
            "Kimi-K2.6",
            "GLM-5.1",
            "deepseek-v4-pro",
        ]

    @staticmethod
    def _compose_loop_stage_prompt(
        *,
        base_prompt: str,
        loop_name: str,
        role_name: str,
        role_id: str,
        role_responsibility: str,
        step_title: str,
        step_instruction: str,
        expected_output: str,
        evidence_required: list[str],
        evidence_rules: list[str],
        previous_summaries: list[dict[str, object]],
        order: int,
        total: int,
    ) -> str:
        """Create one Loop stage prompt for a concrete role/model call."""
        lines = [
            f"Loop: {loop_name}",
            f"Stage: {order}/{total} - {step_title}",
            f"Agent: {role_name} ({role_id})",
            f"Agent responsibility: {role_responsibility}",
            f"Stage instruction: {step_instruction}",
            f"Expected output: {expected_output or 'Role-specific stage output'}",
            "",
            "User request:",
            base_prompt,
        ]
        if previous_summaries:
            lines.extend(["", "Previous Loop stage summaries:"])
            for item in previous_summaries:
                lines.append(
                    "- "
                    f"{item.get('stage_name')} / {item.get('role')} / "
                    f"{item.get('model')}: {item.get('summary')}"
                )
        if evidence_rules:
            lines.extend(["", "Evidence rules:"])
            lines.extend(f"- {rule}" for rule in evidence_rules)
        lines.extend(
            [
                "",
                "Evidence verification contract:",
                "- Include an Evidence table or bullets with source/reference, date or observed period, claim, and why it matters.",
                "- Include Counter-evidence or risk explicitly.",
                "- Include Confidence as a percentage.",
                "- If the stage uses project evidence, cite file path, command, screenshot, test output, or task id.",
                "- If the stage uses external/current-world evidence, cite a URL or source name plus publication/observation date.",
            ]
        )
        if evidence_required:
            lines.extend(["", "Stage evidence requirements:"])
            lines.extend(f"- {item}" for item in evidence_required)
        lines.extend(
            [
                "",
                "Return only this agent's concise, evidence-aware contribution.",
                "Do not skip the evidence contract; the runtime will mark missing fields in Evidence Ledger.",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _format_loop_output(
        *,
        loop_name: str,
        user_prompt: str,
        stages: list[dict[str, object]],
        failed_stage: str | None,
    ) -> str:
        """Render Loop stage outputs into a single user-facing report."""
        lines = [
            "[loop-orchestration]",
            f"loop: {loop_name}",
            f"user request: {user_prompt}",
            "",
        ]
        for stage in stages:
            lines.extend(
                [
                    (
                        f"## Stage {stage.get('order')}: {stage.get('stage_name')} "
                        f"- {stage.get('role_name') or stage.get('role')} "
                        f"[{stage.get('model')}]"
                    ),
                    str(stage.get("output") or ""),
                    "",
                ]
            )
        lines.append("## Loop Summary")
        lines.append(f"completed stages: {len([s for s in stages if s.get('status') == 'completed'])}/{len(stages)}")
        if failed_stage:
            lines.append(f"failed stage: {failed_stage}")
        elif stages:
            lines.append(f"final stage: {stages[-1].get('stage_name')}")
        return "\n".join(lines)

    @staticmethod
    def _decorate_loop_run_runtime(loop_run: dict[str, object]) -> None:
        """Attach runtime-only Loop observability fields."""
        raw_stages = loop_run.get("stages")
        stages = [stage for stage in raw_stages if isinstance(stage, dict)] if isinstance(raw_stages, list) else []
        loop_run["runtime_version"] = "loop-runtime-v2"
        loop_run["timeline"] = [
            {
                "order": stage.get("order"),
                "stage_id": stage.get("stage_id"),
                "stage_name": stage.get("stage_name"),
                "role": stage.get("role"),
                "model": stage.get("model"),
                "status": stage.get("status"),
                "started_at": stage.get("started_at"),
                "completed_at": stage.get("completed_at"),
                "duration_ms": int(stage.get("duration_ms") or 0),
                "attempt": int(stage.get("attempt") or 1),
                "retry_count": int(stage.get("retry_count") or 0),
            }
            for stage in stages
        ]
        loop_run["model_performance"] = TaskService._build_loop_model_performance(stages)
        loop_run["evidence_ledger"] = TaskService._build_loop_evidence_ledger(stages)
        loop_run["improve_suggestions"] = TaskService._build_loop_improve_suggestions(
            loop_run,
            stages,
        )
        loop_run["total_duration_ms"] = sum(
            int(stage.get("duration_ms") or 0) for stage in stages
        )
        loop_run["runtime_controls"] = {
            "can_retry_stage": True,
            "can_improve_loop": True,
            "can_export_trace": True,
        }

    @staticmethod
    def _build_loop_model_performance(
        stages: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Summarize observed model behavior across Loop stages."""
        models: dict[str, dict[str, object]] = {}
        for stage in stages:
            model_id = str(stage.get("model") or "unknown")
            entry = models.setdefault(
                model_id,
                {
                    "model_id": model_id,
                    "provider": stage.get("provider"),
                    "roles": [],
                    "stages": [],
                    "completed_count": 0,
                    "failed_count": 0,
                    "total_duration_ms": 0,
                    "total_tokens": 0,
                    "confidences": [],
                },
            )
            role = str(stage.get("role") or "")
            if role and role not in entry["roles"]:
                entry["roles"].append(role)
            entry["stages"].append(stage.get("stage_id"))
            if stage.get("status") == "completed":
                entry["completed_count"] = int(entry["completed_count"]) + 1
            else:
                entry["failed_count"] = int(entry["failed_count"]) + 1
            entry["total_duration_ms"] = int(entry["total_duration_ms"]) + int(
                stage.get("duration_ms") or 0
            )
            usage = (
                stage.get("metadata", {}).get("usage")
                if isinstance(stage.get("metadata"), dict)
                else None
            )
            if isinstance(usage, dict):
                token_count = (
                    usage.get("total_tokens")
                    or usage.get("total")
                    or usage.get("completion_tokens")
                    or usage.get("output_tokens")
                    or 0
                )
                try:
                    entry["total_tokens"] = int(entry["total_tokens"]) + int(token_count)
                except (TypeError, ValueError):
                    pass
            confidence = TaskService._extract_confidence(stage.get("output"))
            if confidence is not None:
                entry["confidences"].append(confidence)

        performance = []
        for entry in models.values():
            confidences = entry.pop("confidences")
            confidence_count = len(confidences) if isinstance(confidences, list) else 0
            entry["average_confidence"] = (
                round(sum(confidences) / confidence_count, 1)
                if confidence_count
                else None
            )
            performance.append(entry)
        return sorted(
            performance,
            key=lambda item: str(item.get("model_id") or ""),
        )

    @staticmethod
    def _build_loop_evidence_ledger(
        stages: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Build a compact evidence verification ledger from stage outputs."""
        ledger: list[dict[str, object]] = []
        for stage in stages:
            requirements = stage.get("evidence_required")
            required_items = (
                [str(item) for item in requirements if str(item).strip()]
                if isinstance(requirements, list)
                else []
            )
            output = str(stage.get("output") or "")
            verification = TaskService._verify_stage_evidence(output, required_items)
            if stage.get("status") != "completed" or not output.strip():
                verification["status"] = "missing"
                verification["evidence_score"] = 0
            ledger.append(
                {
                    "stage_id": stage.get("stage_id"),
                    "stage_name": stage.get("stage_name"),
                    "role": stage.get("role"),
                    "model": stage.get("model"),
                    "status": verification["status"],
                    "evidence_score": verification["evidence_score"],
                    "requirements": verification["requirements"],
                    "checks": verification["checks"],
                    "sources": verification["sources"],
                    "dates": verification["dates"],
                    "confidence": verification["confidence"],
                    "missing_fields": verification["missing_fields"],
                    "counter_evidence_present": verification["counter_evidence_present"],
                    "expected_output": stage.get("expected_output"),
                    "summary": stage.get("summary"),
                }
            )
        return ledger

    @staticmethod
    def _verify_stage_evidence(
        output: str,
        required_items: list[str],
    ) -> dict[str, object]:
        """Validate the evidence contract for one stage output."""
        text = str(output or "")
        sources = TaskService._extract_evidence_sources(text)
        dates = TaskService._extract_evidence_dates(text)
        confidence = TaskService._extract_confidence(text)
        counter_present = bool(COUNTER_EVIDENCE_PATTERN.search(text))
        requirements = [
            {
                "requirement": item,
                "status": (
                    "provided"
                    if TaskService._requirement_is_satisfied(text, item)
                    else "missing"
                ),
            }
            for item in required_items
        ]
        checks = [
            {
                "field": "source_reference",
                "label": "来源/引用",
                "status": "provided" if sources else "missing",
            },
            {
                "field": "source_date",
                "label": "日期/时间范围",
                "status": "provided" if dates else "missing",
            },
            {
                "field": "counter_evidence",
                "label": "反证/风险",
                "status": "provided" if counter_present else "missing",
            },
            {
                "field": "confidence",
                "label": "置信度",
                "status": "provided" if confidence is not None else "missing",
            },
        ]
        checks.extend(
            {
                "field": f"requirement:{item['requirement']}",
                "label": str(item["requirement"]),
                "status": item["status"],
            }
            for item in requirements
        )
        total = len(checks)
        provided = len([item for item in checks if item.get("status") == "provided"])
        score = round((provided / total) * 100) if total else 100
        missing_fields = [
            str(item.get("label") or item.get("field"))
            for item in checks
            if item.get("status") != "provided"
        ]
        if not text.strip():
            status = "missing"
        elif score >= 90:
            status = "verified"
        elif score >= 50:
            status = "partial"
        else:
            status = "missing"
        return {
            "status": status,
            "evidence_score": score,
            "requirements": requirements,
            "checks": checks,
            "sources": sources[:8],
            "dates": dates[:8],
            "confidence": confidence,
            "missing_fields": missing_fields,
            "counter_evidence_present": counter_present,
        }

    @staticmethod
    def _extract_evidence_sources(output: str) -> list[dict[str, str]]:
        """Extract URL, source, file, or command references from output text."""
        sources: list[dict[str, str]] = []
        seen: set[str] = set()
        for match in EVIDENCE_URL_PATTERN.finditer(output):
            value = match.group(0).rstrip(".,;，。)")
            if value in seen:
                continue
            seen.add(value)
            sources.append({"kind": "url", "value": value})
        for match in EVIDENCE_SOURCE_PATTERN.finditer(output):
            value = " ".join(match.group("value").split()).strip(" -")
            if not value or value in seen:
                continue
            seen.add(value)
            sources.append({"kind": "reference", "value": value[:180]})
        return sources

    @staticmethod
    def _extract_evidence_dates(output: str) -> list[str]:
        """Extract dates or observed periods from output text."""
        dates: list[str] = []
        seen: set[str] = set()
        for match in EVIDENCE_DATE_PATTERN.finditer(output):
            value = match.group(0)
            if value in seen:
                continue
            seen.add(value)
            dates.append(value)
        return dates

    @staticmethod
    def _requirement_is_satisfied(output: str, requirement: str) -> bool:
        """Best-effort check that a stage-specific evidence requirement is present."""
        normalized_output = " ".join(output.lower().split())
        normalized_requirement = " ".join(requirement.lower().split())
        if normalized_requirement and normalized_requirement in normalized_output:
            return True
        tokens = [
            token
            for token in re.split(r"[\s,，/|;；:：()（）-]+", normalized_requirement)
            if len(token) >= 3
        ]
        if not tokens:
            return bool(normalized_output.strip())
        matches = sum(1 for token in tokens if token in normalized_output)
        return matches >= max(1, min(len(tokens), 2))

    @staticmethod
    def _build_loop_improve_suggestions(
        loop_run: dict[str, object],
        stages: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Generate actionable Loop-level improvement prompts from the run."""
        suggestions: list[dict[str, object]] = []
        failed = [stage for stage in stages if stage.get("status") != "completed"]
        if failed:
            suggestions.append(
                {
                    "kind": "retry",
                    "priority": "high",
                    "title": "重跑失败 stage",
                    "detail": f"先重跑 {failed[0].get('stage_name') or failed[0].get('stage_id')}，再让后续 stage 读取新的摘要。",
                    "stage_id": failed[0].get("stage_id"),
                }
            )
        missing_evidence = [
            item
            for item in TaskService._build_loop_evidence_ledger(stages)
            if item.get("status") in {"missing", "partial"}
        ]
        if missing_evidence:
            suggestions.append(
                {
                    "kind": "evidence",
                    "priority": "high",
                    "title": "补齐证据字段",
                    "detail": "至少有一个 stage 缺少来源、日期、反证、置信度或 stage-specific evidence，建议重跑该 stage 或拆出证据收集步骤。",
                    "stage_id": missing_evidence[0].get("stage_id"),
                }
            )
        distinct_models = {
            str(stage.get("model") or "") for stage in stages if stage.get("model")
        }
        if len(stages) > 1 and len(distinct_models) < min(3, len(stages)):
            suggestions.append(
                {
                    "kind": "model_routing",
                    "priority": "medium",
                    "title": "增加模型分工差异",
                    "detail": "当前模型分布偏集中，建议给研究、反方、综合角色分配不同模型。",
                }
            )
        if not suggestions:
            suggestions.extend(
                [
                    {
                        "kind": "judge",
                        "priority": "medium",
                        "title": "加入独立 reviewer stage",
                        "detail": "把最终合成和反证审查拆开，让 reviewer 只评分证据、冲突和信心。",
                    },
                    {
                        "kind": "evidence",
                        "priority": "medium",
                        "title": "把证据规则变成可验证字段",
                        "detail": "为每个 stage 增加来源、时间范围、反例、置信度四个固定输出字段。",
                    },
                    {
                        "kind": "memory",
                        "priority": "low",
                        "title": "保存表现最好的模型-role 映射",
                        "detail": f"本次 {loop_run.get('loop_name', 'Loop')} 可把 model_performance 作为下轮默认路由依据。",
                    },
                ]
            )
        return suggestions[:5]

    @staticmethod
    def _extract_confidence(output: object) -> float | None:
        """Best-effort confidence percentage extraction for model performance."""
        text = str(output or "")
        match = re.search(
            r"(?:confidence|置信度|把握|概率)[^\d]{0,16}(\d{1,3}(?:\.\d+)?)\s*%",
            text,
            re.IGNORECASE,
        )
        if match is None:
            match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", text)
        if match is None:
            return None
        try:
            value = float(match.group(1))
        except ValueError:
            return None
        if value < 0 or value > 100:
            return None
        return value

    @staticmethod
    def _summarize_output(output: str, limit: int = 220) -> str:
        """Reduce a model output to a compact stage summary."""
        compact = " ".join(str(output or "").split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."

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
        normalized_request["prompt"] = self._augment_prompt_with_project_context(
            normalized_request["prompt"],
            normalized_request["metadata"].get("project_context"),
        )
        normalized_request["prompt"] = self._augment_prompt_with_skills(
            normalized_request["prompt"],
            prepared.execution_payload.skills,
        )
        normalized_request["prompt"] = self._augment_prompt_with_mcp_context(
            normalized_request["prompt"],
            normalized_request["metadata"].get("mcp_context"),
        )
        normalized_request["model"] = prepared.task_model_selection.upstream_model
        normalized_request["provider_id"] = prepared.task_model_selection.provider_id
        if prepared.repo_analysis is not None:
            normalized_request["metadata"]["repo_analysis"] = prepared.repo_analysis.model_dump()
            if prepared.repo_analysis.repo_summary is not None:
                normalized_request["prompt"] = self._augment_prompt_with_repo_summary(
                    normalized_request["prompt"],
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
        normalized_request["prompt"] = self._augment_prompt_with_file_context(
            normalized_request["prompt"],
            normalized_request["metadata"].get("file_context"),
        )
        normalized_request["prompt"] = self._augment_prompt_with_runtime_context(
            normalized_request["prompt"],
            normalized_request["metadata"].get("runtime_context"),
        )
        normalized_request["prompt"] = self._augment_prompt_with_tool_context(
            normalized_request["prompt"],
            normalized_request["metadata"].get("tool_context"),
        )
        normalized_request["prompt"] = self._augment_prompt_with_document_generation(
            normalized_request["prompt"],
            normalized_request["metadata"].get("document_generation"),
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
            "project_id": prepared.execution_payload.project_id,
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
    def _augment_prompt_with_project_context(
        prompt: str,
        project_context: object,
    ) -> str:
        """Append project-level instructions, memory, and selected file snippets."""
        if not isinstance(project_context, dict) or not project_context:
            return prompt
        lines = [prompt, "", "Project space context:"]
        lines.append(f"- status: {project_context.get('status')}")
        project = project_context.get("project")
        if isinstance(project, dict):
            lines.append(f"- project_id: {project.get('project_id')}")
            lines.append(f"- project_name: {project.get('display_name')}")
            if project.get("description"):
                lines.append(f"- description: {project.get('description')}")
            if project.get("instructions"):
                lines.append("- project_instructions:")
                lines.append(str(project.get("instructions"))[:TEXT_LIMIT])
            if project.get("memory"):
                lines.append("- project_memory:")
                lines.append(str(project.get("memory"))[:TEXT_LIMIT])
            if project.get("repo_path"):
                lines.append(f"- default_repo_path: {project.get('repo_path')}")
            if project.get("github_repo"):
                lines.append(f"- default_github_repo: {project.get('github_repo')}")
            if project.get("skill_ids"):
                lines.append("- project_skills: " + ", ".join(project.get("skill_ids")[:12]))
            if project.get("mcp_server_ids"):
                lines.append(
                    "- project_mcp_servers: "
                    + ", ".join(project.get("mcp_server_ids")[:12])
                )
        file_context = project_context.get("file_context")
        if isinstance(file_context, dict):
            files = file_context.get("files")
            if isinstance(files, list) and files:
                lines.append("- project_files:")
                for file in files[:8]:
                    if isinstance(file, dict):
                        lines.append(
                            f"  - {file.get('name')} | file_id={file.get('file_id')} | "
                            f"chunks={file.get('chunk_count')}"
                        )
            chunks = file_context.get("chunks")
            if isinstance(chunks, list) and chunks:
                lines.append("- relevant_project_file_chunks:")
                for index, chunk in enumerate(chunks[:8], start=1):
                    if isinstance(chunk, dict):
                        lines.append(
                            f"  [{index}] file_id={chunk.get('file_id')} "
                            f"chunk={chunk.get('order')} score={chunk.get('score')}"
                        )
                        lines.append(f"  {chunk.get('text') or ''}")
        warnings = project_context.get("warnings")
        if isinstance(warnings, list):
            for warning in warnings:
                lines.append(f"- warning: {warning}")
        lines.append(
            "- Treat project instructions and memory as durable user context unless the current user request overrides them."
        )
        return "\n".join(lines)

    @staticmethod
    def _augment_prompt_with_file_context(
        prompt: str,
        file_context: object,
    ) -> str:
        """Append retrieved file chunks and source metadata."""
        if not isinstance(file_context, dict) or not file_context:
            return prompt
        lines = [prompt, "", "Uploaded file context:"]
        lines.append(f"- retrieval status: {file_context.get('status')}")
        files = file_context.get("files")
        if isinstance(files, list) and files:
            lines.append("- files:")
            for file in files[:8]:
                if not isinstance(file, dict):
                    continue
                lines.append(
                    "  - "
                    f"{file.get('name')} | file_id={file.get('file_id')} | "
                    f"status={file.get('status')} | parser={file.get('parser')} | "
                    f"chunks={file.get('chunk_count')}"
                )
        chunks = file_context.get("chunks")
        if isinstance(chunks, list) and chunks:
            lines.append("- retrieved chunks:")
            for index, chunk in enumerate(chunks[:8], start=1):
                if not isinstance(chunk, dict):
                    continue
                lines.append(
                    f"  [{index}] file_id={chunk.get('file_id')} "
                    f"chunk={chunk.get('order')} score={chunk.get('score')}"
                )
                lines.append(f"  {chunk.get('text') or ''}")
        warnings = file_context.get("warnings")
        if isinstance(warnings, list):
            for warning in warnings:
                lines.append(f"- warning: {warning}")
        lines.append(
            "- Use uploaded file chunks as source-grounded context and mention file names or chunk ids when relevant."
        )
        return "\n".join(lines)

    @staticmethod
    def _augment_prompt_with_runtime_context(
        prompt: str,
        runtime_context: object,
    ) -> str:
        """Append current runtime date/time facts for time-sensitive questions."""
        if not isinstance(runtime_context, dict) or not runtime_context:
            return prompt
        lines = [prompt, "", "Current runtime context:"]
        current_date = runtime_context.get("current_date")
        current_time = runtime_context.get("current_time")
        weekday = runtime_context.get("weekday")
        timezone = runtime_context.get("timezone")
        utc_offset = runtime_context.get("utc_offset")
        if current_date:
            lines.append(f"- current_date: {current_date}")
        if weekday:
            lines.append(f"- weekday: {weekday}")
        if current_time:
            lines.append(f"- current_time: {current_time}")
        if timezone or utc_offset:
            lines.append(f"- timezone: {timezone or 'local'} {utc_offset or ''}".rstrip())
        lines.append(
            "- If the user asks about today, now, or the current date/time, answer directly from current_date/current_time above."
        )
        lines.append(
            "- Do not treat missing web search results as missing user intent for date/time questions."
        )
        return "\n".join(lines)

    @staticmethod
    def _augment_prompt_with_tool_context(
        prompt: str,
        tool_context: object,
    ) -> str:
        """Append executed tool results and capability instructions to the model prompt."""
        if not isinstance(tool_context, dict) or not tool_context:
            return prompt
        lines = [prompt, "", "Mindforge tool context:"]

        if "deep_analysis" in tool_context:
            lines.append(
                "- Deep analysis is enabled: analyze tradeoffs, risks, and edge cases before answering."
            )

        web_context = tool_context.get("web_search")
        if isinstance(web_context, dict):
            lines.append(
                "- Web search status: "
                f"{web_context.get('status')} via {web_context.get('provider')}"
            )
            results = web_context.get("results")
            if isinstance(results, list) and results:
                for index, result in enumerate(results[:5], start=1):
                    if not isinstance(result, dict):
                        continue
                    lines.append(
                        f"  {index}. {result.get('title') or 'Untitled'} | "
                        f"{result.get('url') or '-'} | {result.get('snippet') or ''}"
                    )
                citations = web_context.get("citations")
                if isinstance(citations, list) and citations:
                    lines.append(
                        "  Use these numbered web results as citations when the answer depends on current web facts."
                    )
            elif web_context.get("status") == "no_results":
                lines.append(
                    "  no web results were found; continue answering from runtime context or general reasoning when sufficient."
                )
            elif web_context.get("error_message"):
                lines.append(f"  search error: {web_context.get('error_message')}")

        code_context = tool_context.get("code_execution")
        if isinstance(code_context, dict):
            lines.append(
                "- Code execution status: "
                f"{code_context.get('status')} ({code_context.get('language')})"
            )
            if "exit_code" in code_context:
                lines.append(f"  exit code: {code_context.get('exit_code')}")
            if code_context.get("stdout"):
                lines.append(f"  stdout: {code_context.get('stdout')}")
            if code_context.get("stderr"):
                lines.append(f"  stderr: {code_context.get('stderr')}")
            if code_context.get("reason"):
                lines.append(f"  note: {code_context.get('reason')}")

        if "canvas" in tool_context:
            lines.append(
                "- Canvas is enabled: structure the answer as a clean editable artifact with headings."
            )

        return "\n".join(lines)

    @staticmethod
    def _augment_prompt_with_document_generation(
        prompt: str,
        document_generation: object,
    ) -> str:
        """Append final instructions for requests that should become downloadable files."""
        if not isinstance(document_generation, dict) or not document_generation:
            return prompt
        format_label = document_generation.get("format_label") or "document"
        title = str(document_generation.get("title") or "Mindforge 文档")
        topic = str(document_generation.get("topic") or title)
        lines = [
            prompt,
            "",
            "Document generation request:",
            f"- target_format: {format_label}",
            f"- document_title: {title}",
            f"- topic: {topic}",
            "- Write the final answer as the source content for a polished downloadable document.",
            "- Use Markdown structure with a clear # title, executive summary, sections, bullets, and tables when useful.",
            "- If web/search context is available, use it to ground facts and include source links or citations in the document.",
            "- Do not say that you cannot create files; Mindforge will render this content into the requested file format automatically.",
            "- Keep the content publication-ready rather than conversational.",
        ]
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
    def _augment_prompt_with_skills(prompt: str, skills: list[str]) -> str:
        """Append requested local SKILL.md instructions as bounded prompt context."""
        normalized = TaskService._normalize_skills(skills)
        if not normalized:
            return prompt
        details = get_skill_registry_service().load_prompt_context(normalized)
        if details:
            lines = [prompt, "", "Loaded local skills:"]
            for detail in details[:6]:
                lines.append(
                    f"- {detail.skill_id}: {detail.name} | {detail.description}"
                )
                lines.append("```skill")
                lines.append(detail.content_excerpt[:1800])
                lines.append("```")
            missing = [skill for skill in normalized if all(item.skill_id != skill for item in details)]
            if missing:
                lines.append("Requested skills not found: " + ", ".join(missing))
            return "\n".join(lines)
        return "\n".join(
            [
                prompt,
                "",
                "Requested skills:",
                *[f"- {skill}" for skill in normalized],
            ]
        )

    @staticmethod
    def _augment_prompt_with_mcp_context(prompt: str, mcp_context: object) -> str:
        """Append MCP tool catalogs selected by the user."""
        if not isinstance(mcp_context, dict) or not mcp_context:
            return prompt
        lines = [prompt, "", "MCP tool context:"]
        lines.append(f"- status: {mcp_context.get('status')}")
        servers = mcp_context.get("servers")
        if isinstance(servers, list):
            for server in servers[:6]:
                if not isinstance(server, dict):
                    continue
                lines.append(
                    f"- server {server.get('server_id')}: status={server.get('status')}"
                )
                if server.get("error_message"):
                    lines.append(f"  error: {server.get('error_message')}")
                tools = server.get("tools")
                if isinstance(tools, list):
                    for tool in tools[:12]:
                        if isinstance(tool, dict):
                            lines.append(
                                f"  - tool {tool.get('name')}: {tool.get('description') or ''}"
                            )
        lines.append(
            "- If the user asks to use an MCP tool, explain which tool should be called unless a direct tool result is already present."
        )
        return "\n".join(lines)

    @staticmethod
    def _normalize_skills(skills: list[str]) -> list[str]:
        """Remove empty and duplicate skill ids while preserving user order."""
        normalized: list[str] = []
        seen: set[str] = set()
        for skill in skills:
            value = str(skill).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    @staticmethod
    def _attach_canvas_artifacts(response: TaskResponse) -> None:
        """Persist editable canvas artifacts when the canvas capability is enabled."""
        metadata = response.data.metadata
        tool_flags = metadata.get("tool_flags")
        if not isinstance(tool_flags, dict) or tool_flags.get("canvas") is not True:
            return
        artifacts = metadata.get("canvas_artifacts")
        if not isinstance(artifacts, list):
            artifacts = []
        task_id = str(metadata.get("task_id") or uuid4())
        timestamp = datetime.now().astimezone().isoformat()
        artifacts.append(
            {
                "artifact_id": f"canvas-{task_id}",
                "kind": "markdown",
                "title": "Mindforge 输出画布",
                "source": "model-output",
                "editable": True,
                "content": response.data.output,
                "version": 1,
                "updated_at": timestamp,
                "versions": [
                    {
                        "version": 1,
                        "title": "Mindforge 输出画布",
                        "content": response.data.output,
                        "updated_at": timestamp,
                        "source": "initial-output",
                    }
                ],
            }
        )
        tool_context = metadata.get("tool_context")
        if isinstance(tool_context, dict) and isinstance(
            tool_context.get("code_execution"),
            dict,
        ):
            artifacts.append(
                {
                    "artifact_id": f"code-run-{task_id}",
                    "kind": "code-execution-result",
                    "title": "代码执行结果",
                    "source": "code_execution",
                    "editable": False,
                    "content": tool_context["code_execution"],
                }
            )
        metadata["canvas_artifacts"] = artifacts

    def _attach_generated_document_artifact(self, response: TaskResponse) -> None:
        """Create downloadable files for natural-language document generation tasks."""
        if response.status != "completed":
            return
        metadata = response.data.metadata
        document_generation = metadata.get("document_generation")
        if not isinstance(document_generation, dict):
            return
        format_name = str(document_generation.get("format") or "")
        if format_name not in DOCUMENT_FORMAT_LABELS:
            return
        content = response.data.output.strip()
        if not content:
            return
        task_id = str(metadata.get("task_id") or "")
        artifact = self.artifact_service.export(
            ArtifactExportRequest(
                title=str(document_generation.get("title") or "Mindforge 文档"),
                content=content,
                format=format_name,  # type: ignore[arg-type]
                source_task_id=task_id or None,
                loop_id=(
                    str(metadata.get("loop_id"))
                    if metadata.get("loop_id") is not None
                    else None
                ),
                loop_name=(
                    str((metadata.get("loop") or {}).get("name"))
                    if isinstance(metadata.get("loop"), dict)
                    else None
                ),
                provenance=self._build_artifact_provenance(metadata),
            )
        )
        generated = metadata.get("generated_artifacts")
        if not isinstance(generated, list):
            generated = []
        artifact_payload = artifact.model_dump(mode="json")
        generated.insert(0, artifact_payload)
        metadata["generated_artifacts"] = generated
        document_generation["status"] = "generated"
        document_generation["artifact_id"] = artifact.artifact_id
        document_generation["download_url"] = artifact.download_url
        metadata["document_generation"] = document_generation
        response.data.output = "\n\n".join(
            [
                content,
                (
                    f"已生成 {artifact.format.upper()} 文件："
                    f"{artifact.filename}\n下载地址：{artifact.download_url}"
                ),
            ]
        )

    def _attach_execution_report(self, response: TaskResponse) -> None:
        """Attach a compact run report for UI inspection and audit."""
        metadata = response.data.metadata
        tool_flags = metadata.get("tool_flags") if isinstance(metadata, dict) else {}
        if not isinstance(tool_flags, dict):
            tool_flags = {}
        tool_context = metadata.get("tool_context")
        if not isinstance(tool_context, dict):
            tool_context = {}
        steps: list[dict[str, object]] = [
            {
                "id": "context",
                "label": "上下文装配",
                "status": "completed",
                "summary": "已合并对话、运行时、文件、Skills、MCP 和预设上下文。",
            },
            {
                "id": "model",
                "label": "模型路由",
                "status": "completed",
                "summary": (
                    (metadata.get("task_model_selection") or {}).get("model_id")
                    if isinstance(metadata.get("task_model_selection"), dict)
                    else "resolved"
                ),
            },
        ]
        if tool_flags:
            tool_statuses = []
            for flag_name in TOOL_FLAG_NAMES:
                if flag_name not in tool_flags:
                    continue
                context_value = tool_context.get(flag_name)
                status_value = (
                    context_value.get("status")
                    if isinstance(context_value, dict)
                    else ("requested" if tool_flags.get(flag_name) else "off")
                )
                tool_statuses.append(f"{flag_name}={status_value}")
            steps.append(
                {
                    "id": "tools",
                    "label": "工具能力",
                    "status": "completed",
                    "summary": ", ".join(tool_statuses) or "未请求工具能力",
                }
            )
        orchestration = metadata.get("orchestration")
        if isinstance(orchestration, dict):
            steps.append(
                {
                    "id": "orchestration",
                    "label": "多 Agent 编排",
                    "status": "completed"
                    if orchestration.get("completed_stages") == orchestration.get("total_stages")
                    else "partial",
                    "summary": (
                        f"{orchestration.get('completed_stages', 0)}/"
                        f"{orchestration.get('total_stages', 0)} stages"
                    ),
                }
            )
        loop_run = metadata.get("loop_run")
        if isinstance(loop_run, dict):
            steps.append(
                {
                    "id": "loop",
                    "label": "Loop 循环",
                    "status": loop_run.get("status") or "completed",
                    "summary": (
                        f"{loop_run.get('loop_name', 'Loop')} / "
                        f"{len(loop_run.get('stages') or [])} steps"
                    ),
                }
            )
        if metadata.get("generated_artifacts"):
            steps.append(
                {
                    "id": "artifacts",
                    "label": "产物生成",
                    "status": "completed",
                    "summary": f"{len(metadata.get('generated_artifacts') or [])} 个下载文件",
                }
            )
        warnings: list[str] = []
        code_context = tool_context.get("code_execution")
        if isinstance(code_context, dict) and code_context.get("status") == "blocked":
            warnings.append(str(code_context.get("reason") or "Code execution was blocked."))
        mcp_context = metadata.get("mcp_context")
        if isinstance(mcp_context, dict):
            warnings.append(
                "MCP 当前作为 catalog/proxy 能力接入；自动工具调用仍需后续安全审批链。"
            )
        skills_context = metadata.get("skills_context")
        if isinstance(skills_context, dict):
            warnings.append(
                "Skills 当前作为 prompt-context 接入；脚本/assets 生命周期尚未完整托管。"
            )
        metadata["execution_report"] = {
            "runtime_boundary": {
                "adapter": "OpenHandsAdapter",
                "openhands_mode": self.settings.openhands_mode,
                "skills_runtime": "prompt-context",
                "mcp_runtime": "catalog/proxy",
                "code_execution": "approval-gated-python-snippet",
            },
            "steps": steps,
            "warnings": warnings,
        }

    @staticmethod
    def _attach_loop_run_trace(response: TaskResponse) -> None:
        """Finalize loop trace metadata after runtime execution."""
        metadata = response.data.metadata
        loop_run = metadata.get("loop_run")
        if not isinstance(loop_run, dict):
            return
        orchestration = metadata.get("orchestration")
        orchestration_stages = (
            orchestration.get("stages")
            if isinstance(orchestration, dict) and isinstance(orchestration.get("stages"), list)
            else []
        )
        stages = loop_run.get("stages")
        if not isinstance(stages, list):
            stages = []
        next_stages: list[dict[str, object]] = []
        for index, stage in enumerate(stages, start=1):
            if not isinstance(stage, dict):
                continue
            source = (
                orchestration_stages[index - 1]
                if index - 1 < len(orchestration_stages)
                and isinstance(orchestration_stages[index - 1], dict)
                else {}
            )
            next_stages.append(
                {
                    **stage,
                    "status": source.get("status") or stage.get("status") or response.status,
                    "summary": source.get("summary") or stage.get("summary") or "",
                    "output": (
                        source.get("output")
                        or stage.get("output")
                        or (
                            response.data.output[:1200]
                            if index == len(stages)
                            else stage.get("expected_output") or ""
                        )
                    ),
                    "model": source.get("model")
                    or stage.get("model")
                    or (
                        metadata.get("task_model_selection", {}).get("model_id")
                        if isinstance(metadata.get("task_model_selection"), dict)
                        else ""
                    ),
                    "provider": source.get("provider")
                    or stage.get("provider")
                    or response.data.provider,
                }
            )
        loop_run["status"] = response.status
        loop_run["stages"] = next_stages
        loop_run["completed_at"] = datetime.now().astimezone().isoformat()
        TaskService._decorate_loop_run_runtime(loop_run)
        metadata["loop_run"] = loop_run
        metadata["artifact_provenance"] = TaskService._build_artifact_provenance(metadata)

    @staticmethod
    def _build_artifact_provenance(metadata: dict[str, object]) -> dict[str, object]:
        """Build portable provenance metadata for exported artifacts."""
        loop = metadata.get("loop")
        model = metadata.get("task_model_selection")
        return {
            "task_id": metadata.get("task_id"),
            "loop": loop if isinstance(loop, dict) else None,
            "model": model if isinstance(model, dict) else None,
            "models": TaskService._collect_loop_stage_models(metadata),
            "preset_mode": metadata.get("resolved_preset_mode"),
            "evidence_rules": (
                metadata.get("loop_run", {}).get("evidence_rules")
                if isinstance(metadata.get("loop_run"), dict)
                else []
            ),
            "artifact_outputs": (
                metadata.get("loop_run", {}).get("artifact_outputs")
                if isinstance(metadata.get("loop_run"), dict)
                else []
            ),
        }

    @staticmethod
    def _collect_loop_stage_models(metadata: dict[str, object]) -> list[dict[str, object]]:
        """Collect distinct model provenance from Loop stages."""
        loop_run = metadata.get("loop_run")
        if not isinstance(loop_run, dict):
            return []
        stages = loop_run.get("stages")
        if not isinstance(stages, list):
            return []
        models: list[dict[str, object]] = []
        seen: set[str] = set()
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            model_id = str(stage.get("model") or "")
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            models.append(
                {
                    "model_id": model_id,
                    "role": stage.get("role"),
                    "stage_id": stage.get("stage_id"),
                    "provider": stage.get("provider"),
                }
            )
        return models

    @staticmethod
    def _format_conversation_history(conversation_history: list[object]) -> list[str]:
        """Render recent messages into a compact model-readable transcript."""
        rendered: list[str] = []
        for message in conversation_history[-16:]:
            role = str(getattr(message, "role", "user"))
            content = str(getattr(message, "content", "")).strip()
            if not content:
                continue
            content = TaskService._sanitize_history_content(role, content)
            label = {
                "assistant": "Assistant",
                "system": "System",
                "user": "User",
            }.get(role, role.title())
            if len(content) > 4000:
                content = content[:3997] + "..."
            rendered.append(f"{label}: {content}")
        return rendered

    @staticmethod
    def _sanitize_history_content(role: str, content: str) -> str:
        """Keep internal mock adapter traces out of future model prompts."""
        if role == "assistant" and content.lstrip().startswith("[mock-openhands]"):
            return "前一轮任务已由本地 mock 执行器完成，内部调试回显已省略。"
        return content

    @staticmethod
    def _truncate_text(value: str, limit: int = TEXT_LIMIT) -> str:
        """Keep tool metadata compact for prompts and history."""
        if len(value) <= limit:
            return value
        return value[: limit - 3] + "..."


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
        get_file_context_service(),
    )


def clear_task_service_cache() -> None:
    """Clear cached task service after mutable config changes."""
    get_task_service.cache_clear()
