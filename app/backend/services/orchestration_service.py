"""Serial orchestration for role-based multi-agent execution."""

from dataclasses import dataclass

from app.backend.integration.openhands_adapter import OpenHandsAdapter
from app.backend.schemas.model import ModelSelection
from app.backend.schemas.orchestration import OrchestrationTrace, StageExecution
from app.backend.schemas.preset import PresetDefinition
from app.backend.schemas.repository import RepoAnalysisResult
from app.backend.schemas.task import TaskRequest, TaskResponse, TaskResponseData
from app.backend.services.model_routing_service import (
    ModelRoutingError,
    ModelRoutingService,
)

ROLE_TITLES: dict[str, str] = {
    "project-manager": "Project Manager",
    "backend": "Backend Engineer",
    "frontend": "Frontend Engineer",
    "reviewer": "Reviewer",
}

ROLE_INSTRUCTIONS: dict[str, str] = {
    "project-manager": (
        "Break the request into implementation steps, define handoff priorities, "
        "and clarify what backend and frontend should each deliver."
    ),
    "backend": (
        "Focus on APIs, server-side logic, data contracts, and backend change risks."
    ),
    "frontend": (
        "Focus on UI flow, view structure, user interactions, and frontend change risks."
    ),
    "reviewer": (
        "Review the prior stage outputs, identify contradictions or missing details, "
        "and provide a final recommendation with follow-up actions."
    ),
}


@dataclass(frozen=True, slots=True)
class StageDefinition:
    """Internal description of one serial orchestration stage."""

    order: int
    role: str
    stage_id: str
    stage_name: str
    model_selection: ModelSelection
    instructions: str


class SerialOrchestrationService:
    """Execute multi-stage serial orchestration for supported presets.

    The current implementation is a Mindforge-side MVP used to validate
    role-based flows such as `code-engineering`. Future phases should keep the
    product-level orchestration behavior but gradually align execution semantics
    with upstream OpenHands agent, state, action, and observation concepts
    instead of expanding a divergent custom protocol indefinitely.
    """

    def __init__(
        self,
        adapter: OpenHandsAdapter,
        model_router: ModelRoutingService,
    ) -> None:
        self.adapter = adapter
        self.model_router = model_router

    def execute_code_engineering(
        self,
        payload: TaskRequest,
        preset: PresetDefinition,
        repo_analysis: RepoAnalysisResult | None = None,
    ) -> TaskResponse:
        """Run the code-engineering preset as a serial role chain."""
        stage_defs = self._build_stage_definitions(payload, preset)
        trace = OrchestrationTrace(
            preset_mode=preset.preset_mode,
            strategy="serial-role-orchestration",
            total_stages=len(stage_defs),
            completed_stages=0,
        )

        for stage in stage_defs:
            stage_payload = self._build_stage_payload(
                payload=payload,
                preset=preset,
                stage=stage,
                trace=trace,
                repo_analysis=repo_analysis,
            )
            result = self.adapter.run_task(stage_payload)
            stage_execution = StageExecution(
                order=stage.order,
                stage_id=stage.stage_id,
                stage_name=stage.stage_name,
                role=stage.role,
                model=stage.model_selection.model_id,
                status=result.status,
                provider=result.provider,
                summary=self._summarize_output(result.output),
                output=result.output,
                metadata={
                    **result.metadata,
                    "model_selection": stage.model_selection.model_dump(),
                },
                error_message=result.error_message,
            )
            trace.stages.append(stage_execution)

            if result.status != "completed":
                trace.failed_stage = stage.stage_id
                trace.completed_stages = len(
                    [item for item in trace.stages if item.status == "completed"]
                )
                return self._build_failure_response(payload, preset, trace)

        trace.completed_stages = len(trace.stages)
        return self._build_success_response(payload, preset, trace)

    def _build_stage_definitions(
        self,
        payload: TaskRequest,
        preset: PresetDefinition,
    ) -> list[StageDefinition]:
        """Translate preset role order into concrete stage definitions."""
        stages: list[StageDefinition] = []
        for order, role in enumerate(preset.agent_roles, start=1):
            stage_id = role.replace("_", "-")
            model_selection = self.model_router.resolve_for_role(
                preset_mode=preset.preset_mode,
                task_type=payload.task_type,
                role=role,
                explicit_model=payload.role_model_overrides.get(role),
                preset_default_model=preset.default_models.get(role),
            )
            stages.append(
                StageDefinition(
                    order=order,
                    role=role,
                    stage_id=stage_id,
                    stage_name=ROLE_TITLES.get(role, role.replace("-", " ").title()),
                    model_selection=model_selection,
                    instructions=ROLE_INSTRUCTIONS.get(
                        role,
                        "Produce a role-specific implementation handoff.",
                    ),
                )
            )
        return stages

    def _build_stage_payload(
        self,
        payload: TaskRequest,
        preset: PresetDefinition,
        stage: StageDefinition,
        trace: OrchestrationTrace,
        repo_analysis: RepoAnalysisResult | None = None,
    ) -> dict[str, object]:
        """Build the adapter payload for a single stage."""
        return {
            "prompt": self._compose_stage_prompt(
                payload,
                stage,
                trace,
                repo_analysis=repo_analysis,
            ),
            "preset_mode": preset.preset_mode,
            "repo_path": payload.repo_path,
            "metadata": {
                **payload.metadata,
                "orchestration_role": stage.role,
                "orchestration_stage": stage.stage_id,
                "orchestration_stage_name": stage.stage_name,
                "orchestration_stage_order": stage.order,
                "orchestration_model": stage.model_selection.model_id,
                "orchestration_model_selection": stage.model_selection.model_dump(),
                "orchestration_previous_summaries": [
                    {
                        "stage_id": item.stage_id,
                        "stage_name": item.stage_name,
                        "summary": item.summary,
                    }
                    for item in trace.stages
                ],
                "repo_analysis": (
                    repo_analysis.model_dump() if repo_analysis is not None else None
                ),
            },
            "model": stage.model_selection.upstream_model,
            "provider_id": stage.model_selection.provider_id,
        }

    def _compose_stage_prompt(
        self,
        payload: TaskRequest,
        stage: StageDefinition,
        trace: OrchestrationTrace,
        repo_analysis: RepoAnalysisResult | None = None,
    ) -> str:
        """Create a deterministic stage prompt for the current role."""
        lines = [
            f"Role: {stage.stage_name} ({stage.role})",
            f"Stage order: {stage.order}/{trace.total_stages}",
            f"User request: {payload.prompt}",
            f"Repository path: {payload.repo_path or 'not provided'}",
            f"Primary responsibility: {stage.instructions}",
        ]
        if repo_analysis is not None:
            if repo_analysis.repo_summary is not None:
                lines.append(f"Repository summary: {repo_analysis.repo_summary.summary_text}")
                if repo_analysis.repo_summary.entrypoints:
                    lines.append(
                        "Likely entrypoints: "
                        + ", ".join(repo_analysis.repo_summary.entrypoints[:4])
                    )
                if repo_analysis.repo_summary.key_files:
                    lines.append(
                        "Key files: "
                        + ", ".join(
                            item.path
                            for item in repo_analysis.repo_summary.key_files[:6]
                        )
                    )
            elif repo_analysis.warnings:
                lines.append(
                    "Repository analysis warnings: "
                    + " ".join(repo_analysis.warnings)
                )
        if trace.stages:
            lines.append("Previous stage summaries:")
            for item in trace.stages:
                lines.append(f"- [{item.stage_name}] {item.summary}")
        lines.extend(
            [
                "Return a concise execution note with: objective, proposed changes, risks, and handoff.",
                "Keep the answer role-specific.",
            ]
        )
        return "\n".join(lines)

    def _build_success_response(
        self,
        payload: TaskRequest,
        preset: PresetDefinition,
        trace: OrchestrationTrace,
    ) -> TaskResponse:
        """Return a normalized success response for a completed orchestration."""
        return TaskResponse(
            status="completed",
            message="Task executed successfully through serial orchestration.",
            data=TaskResponseData(
                output=self._format_final_output(payload, trace),
                provider="multi-stage-orchestrator",
                metadata={
                    "orchestration": trace.model_dump(),
                    "resolved_agent_roles": preset.agent_roles,
                    "execution_flow": preset.execution_flow,
                    "final_handoff": trace.stages[-1].summary if trace.stages else "",
                },
            ),
        )

    def _build_failure_response(
        self,
        payload: TaskRequest,
        preset: PresetDefinition,
        trace: OrchestrationTrace,
    ) -> TaskResponse:
        """Return a normalized failure response with stage-level diagnostics."""
        failed_stage = trace.stages[-1]
        return TaskResponse(
            status="failed",
            message="Task execution failed during serial orchestration.",
            data=TaskResponseData(
                output=self._format_final_output(payload, trace),
                provider="multi-stage-orchestrator",
                metadata={
                    "orchestration": trace.model_dump(),
                    "resolved_agent_roles": preset.agent_roles,
                    "execution_flow": preset.execution_flow,
                    "failed_stage": failed_stage.stage_id,
                },
            ),
            error_message=failed_stage.error_message
            or f"Stage '{failed_stage.stage_name}' failed.",
        )

    def _format_final_output(
        self,
        payload: TaskRequest,
        trace: OrchestrationTrace,
    ) -> str:
        """Render a readable final output from all stage results."""
        lines = [
            "[serial-orchestration]",
            f"preset mode: {trace.preset_mode}",
            f"user request: {payload.prompt}",
            "",
        ]
        for item in trace.stages:
            lines.extend(
                [
                    f"## Stage {item.order}: {item.stage_name}",
                    item.output,
                    "",
                ]
            )
        lines.append("## Final Summary")
        lines.append(
            f"completed stages: {trace.completed_stages}/{trace.total_stages}"
        )
        if trace.failed_stage:
            lines.append(f"failed stage: {trace.failed_stage}")
        elif trace.stages:
            lines.append(f"final handoff: {trace.stages[-1].summary}")
        return "\n".join(lines)

    @staticmethod
    def _summarize_output(output: str, limit: int = 220) -> str:
        """Reduce multi-line stage output to a compact summary string."""
        compact = " ".join(output.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."
