"""Serial orchestration for role-based multi-agent execution."""

from dataclasses import dataclass

from app.backend.integration.openhands_adapter import OpenHandsAdapter
from app.backend.schemas.academic_context import AcademicContextSummary
from app.backend.schemas.github_context import GitHubContextSummary
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
    "standards-editor": "Standards Editor",
    "reviser": "Paper Reviser",
    "style-reviewer": "Style Reviewer",
    "content-reviewer": "Content Reviewer",
    "final-reviewer": "Final Reviewer",
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
    "standards-editor": (
        "Extract the journal requirements, academic standards, manuscript constraints, "
        "and venue-specific writing signals that later stages must follow."
    ),
    "reviser": (
        "Revise the manuscript content according to the standards analysis and reviewer "
        "feedback while preserving the author's claims and evidence."
    ),
    "style-reviewer": (
        "Review academic tone, clarity, concision, section flow, and journal-style fit. "
        "Return concrete writing issues and rewrite suggestions."
    ),
    "content-reviewer": (
        "Review argument quality, novelty, methodology clarity, evidence strength, and "
        "response-to-reviewer completeness."
    ),
    "final-reviewer": (
        "Re-review the revised draft against the standards and reviewer comments, then "
        "identify remaining blockers before submission."
    ),
}

PAPER_REVISION_STAGE_FLOW: tuple[tuple[str, str, str], ...] = (
    ("analyze-standards", "standards-editor", "Standards Analysis"),
    ("revise", "reviser", "Revision Draft"),
    ("style-review", "style-reviewer", "Style Review"),
    ("content-review", "content-reviewer", "Content Review"),
    ("iterate", "reviser", "Revision Iteration"),
    ("re-review", "final-reviewer", "Final Re-review"),
)


@dataclass(frozen=True, slots=True)
class StageDefinition:
    """Internal description of one serial orchestration stage."""

    order: int
    role: str
    stage_id: str
    stage_name: str
    model_selection: ModelSelection
    instructions: str
    flow_step: str | None = None


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
        github_context: GitHubContextSummary | None = None,
    ) -> TaskResponse:
        """Run the code-engineering preset as a serial role chain."""
        return self.execute_preset(
            payload,
            preset,
            repo_analysis=repo_analysis,
            github_context=github_context,
        )

    def execute_preset(
        self,
        payload: TaskRequest,
        preset: PresetDefinition,
        repo_analysis: RepoAnalysisResult | None = None,
        github_context: GitHubContextSummary | None = None,
        academic_context: AcademicContextSummary | None = None,
    ) -> TaskResponse:
        """Run a supported preset as a serial role chain."""
        stage_defs = self._build_stage_definitions(payload, preset)
        trace = OrchestrationTrace(
            preset_mode=preset.preset_mode,
            strategy=self._strategy_for_preset(preset.preset_mode),
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
                github_context=github_context,
                academic_context=academic_context,
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
        if preset.preset_mode == "paper-revision":
            return [
                self._build_stage_definition(
                    payload=payload,
                    preset=preset,
                    order=order,
                    role=role,
                    stage_id=stage_id,
                    stage_name=stage_name,
                    flow_step=stage_id,
                )
                for order, (stage_id, role, stage_name) in enumerate(
                    PAPER_REVISION_STAGE_FLOW,
                    start=1,
                )
            ]

        stages: list[StageDefinition] = []
        for order, role in enumerate(preset.agent_roles, start=1):
            stage_id = role.replace("_", "-")
            stages.append(
                self._build_stage_definition(
                    payload=payload,
                    preset=preset,
                    order=order,
                    role=role,
                    stage_id=stage_id,
                    stage_name=ROLE_TITLES.get(role, role.replace("-", " ").title()),
                )
            )
        return stages

    def _build_stage_definition(
        self,
        *,
        payload: TaskRequest,
        preset: PresetDefinition,
        order: int,
        role: str,
        stage_id: str,
        stage_name: str,
        flow_step: str | None = None,
    ) -> StageDefinition:
        """Resolve one stage definition including its role-specific model."""
        model_selection = self.model_router.resolve_for_role(
            preset_mode=preset.preset_mode,
            task_type=payload.task_type,
            role=role,
            explicit_model=payload.role_model_overrides.get(role),
            preset_default_model=preset.default_models.get(role),
        )
        return StageDefinition(
            order=order,
            role=role,
            stage_id=stage_id,
            stage_name=stage_name,
            model_selection=model_selection,
            instructions=ROLE_INSTRUCTIONS.get(
                role,
                "Produce a role-specific implementation handoff.",
            ),
            flow_step=flow_step,
        )

    def _build_stage_payload(
        self,
        payload: TaskRequest,
        preset: PresetDefinition,
        stage: StageDefinition,
        trace: OrchestrationTrace,
        repo_analysis: RepoAnalysisResult | None = None,
        github_context: GitHubContextSummary | None = None,
        academic_context: AcademicContextSummary | None = None,
    ) -> dict[str, object]:
        """Build the adapter payload for a single stage."""
        return {
            "prompt": self._compose_stage_prompt(
                payload,
                stage,
                trace,
                repo_analysis=repo_analysis,
                github_context=github_context,
                academic_context=academic_context,
            ),
            "preset_mode": preset.preset_mode,
            "repo_path": payload.repo_path,
            "metadata": {
                **payload.metadata,
                "orchestration_role": stage.role,
                "orchestration_stage": stage.stage_id,
                "orchestration_stage_name": stage.stage_name,
                "orchestration_stage_order": stage.order,
                "orchestration_flow_step": stage.flow_step,
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
                "github_context": (
                    github_context.model_dump() if github_context is not None else None
                ),
                "academic_context": (
                    academic_context.model_dump()
                    if academic_context is not None
                    else None
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
        github_context: GitHubContextSummary | None = None,
        academic_context: AcademicContextSummary | None = None,
    ) -> str:
        """Create a deterministic stage prompt for the current role."""
        lines = [
            f"Role: {stage.stage_name} ({stage.role})",
            f"Stage order: {stage.order}/{trace.total_stages}",
            f"Flow step: {stage.flow_step or stage.stage_id}",
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
        if github_context is not None:
            if github_context.repository is not None:
                lines.append(
                    "GitHub repository: "
                    f"{github_context.repository.full_name} "
                    f"(default branch: {github_context.repository.default_branch}, "
                    f"language: {github_context.repository.primary_language or 'unknown'})"
                )
                if github_context.repository.description:
                    lines.append(
                        f"GitHub repository description: {github_context.repository.description}"
                    )
            if github_context.issue is not None:
                lines.append(
                    "GitHub issue: "
                    f"#{github_context.issue.number} {github_context.issue.title} "
                    f"[{github_context.issue.state}]"
                )
                if github_context.issue.body_excerpt:
                    lines.append(
                        f"GitHub issue excerpt: {github_context.issue.body_excerpt}"
                    )
            if github_context.pull_request is not None:
                lines.append(
                    "GitHub pull request: "
                    f"#{github_context.pull_request.number} {github_context.pull_request.title} "
                    f"[{github_context.pull_request.state}]"
                )
                if github_context.pull_request.body_excerpt:
                    lines.append(
                        f"GitHub pull request excerpt: {github_context.pull_request.body_excerpt}"
                    )
        if academic_context is not None:
            lines.append("Academic context:")
            if academic_context.journal is not None:
                journal = academic_context.journal
                lines.append(
                    "Journal guidelines: "
                    f"{journal.journal_name or 'unknown journal'} | "
                    f"url={journal.journal_url or '-'} | status={journal.status}"
                )
                if journal.title:
                    lines.append(f"Journal guideline title: {journal.title}")
                if journal.excerpt:
                    lines.append(f"Journal guideline excerpt: {journal.excerpt}")
            for index, reference in enumerate(
                academic_context.reference_papers,
                start=1,
            ):
                lines.append(
                    f"Reference paper {index}: {reference.title or reference.url} "
                    f"| status={reference.status}"
                )
                if reference.excerpt:
                    lines.append(f"Reference paper {index} excerpt: {reference.excerpt}")
            if academic_context.warnings:
                lines.append(
                    "Academic context warnings: "
                    + " ".join(academic_context.warnings)
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

    @staticmethod
    def _strategy_for_preset(preset_mode: str) -> str:
        """Return the trace strategy label for a preset."""
        if preset_mode == "paper-revision":
            return "serial-paper-revision"
        return "serial-role-orchestration"

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
