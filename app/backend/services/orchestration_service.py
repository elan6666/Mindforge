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
        *,
        prefer_user_model_defaults: bool = False,
    ) -> None:
        self.adapter = adapter
        self.model_router = model_router
        self.prefer_user_model_defaults = prefer_user_model_defaults

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
            prefer_user_default=self.prefer_user_model_defaults,
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
        ]
        conversation_lines = self._format_conversation_history(
            payload.conversation_history,
        )
        if conversation_lines:
            lines.extend(["Conversation so far:", *conversation_lines])
        skill_lines = self._format_skills(payload.skills)
        if skill_lines:
            lines.extend(["Requested skills:", *skill_lines])
        skill_context_lines = self._format_skill_context(
            payload.metadata.get("skills_context"),
        )
        if skill_context_lines:
            lines.extend(["Loaded local skill context:", *skill_context_lines])
        runtime_context_lines = self._format_runtime_context(
            payload.metadata.get("runtime_context"),
        )
        if runtime_context_lines:
            lines.extend(["Current runtime context:", *runtime_context_lines])
        tool_context_lines = self._format_tool_context(payload.metadata.get("tool_context"))
        if tool_context_lines:
            lines.extend(["Mindforge tool context:", *tool_context_lines])
        mcp_context_lines = self._format_mcp_context(payload.metadata.get("mcp_context"))
        if mcp_context_lines:
            lines.extend(["MCP tool context:", *mcp_context_lines])
        file_context_lines = self._format_file_context(payload.metadata.get("file_context"))
        if file_context_lines:
            lines.extend(["Uploaded file context:", *file_context_lines])
        lines.extend(
            [
                f"User request: {payload.prompt}",
                f"Repository path: {payload.repo_path or 'not provided'}",
                f"Primary responsibility: {stage.instructions}",
            ]
        )
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
    def _format_skills(skills: list[str]) -> list[str]:
        """Render user-selected skills as runtime-readable hints."""
        rendered: list[str] = []
        seen: set[str] = set()
        for skill in skills:
            value = str(skill).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            rendered.append(f"- {value}")
        return rendered

    @staticmethod
    def _format_runtime_context(runtime_context: object) -> list[str]:
        """Render current runtime facts for role-specific prompts."""
        if not isinstance(runtime_context, dict) or not runtime_context:
            return []
        rendered: list[str] = []
        current_date = runtime_context.get("current_date")
        current_time = runtime_context.get("current_time")
        weekday = runtime_context.get("weekday")
        timezone = runtime_context.get("timezone")
        utc_offset = runtime_context.get("utc_offset")
        if current_date:
            rendered.append(f"- current_date: {current_date}")
        if weekday:
            rendered.append(f"- weekday: {weekday}")
        if current_time:
            rendered.append(f"- current_time: {current_time}")
        if timezone or utc_offset:
            rendered.append(f"- timezone: {timezone or 'local'} {utc_offset or ''}".rstrip())
        rendered.append(
            "- If the user asks about today, now, or current date/time, answer directly from these facts."
        )
        rendered.append(
            "- Do not treat missing web search results as missing user intent for date/time questions."
        )
        return rendered

    @staticmethod
    def _format_skill_context(skills_context: object) -> list[str]:
        """Render selected SKILL.md excerpts for role-specific prompts."""
        if not isinstance(skills_context, dict) or not skills_context:
            return []
        rendered: list[str] = [
            f"- status: {skills_context.get('status')}",
            f"- runtime: {skills_context.get('runtime') or 'prompt-context'}",
        ]
        skills = skills_context.get("skills")
        if isinstance(skills, list):
            for skill in skills[:6]:
                if not isinstance(skill, dict):
                    continue
                rendered.append(
                    f"- {skill.get('skill_id')}: {skill.get('name')} | "
                    f"{skill.get('description') or ''}"
                )
                excerpt = str(skill.get("content_excerpt") or "").strip()
                if excerpt:
                    rendered.append("```skill")
                    rendered.append(excerpt[:1800])
                    rendered.append("```")
        missing = skills_context.get("missing")
        if isinstance(missing, list) and missing:
            rendered.append("- missing: " + ", ".join(str(item) for item in missing))
        return rendered

    @staticmethod
    def _format_tool_context(tool_context: object) -> list[str]:
        """Render tool execution context for role-specific stage prompts."""
        if not isinstance(tool_context, dict) or not tool_context:
            return []
        rendered: list[str] = []
        if "deep_analysis" in tool_context:
            rendered.append(
                "- Deep analysis is enabled: consider tradeoffs, risks, and edge cases."
            )
        web_context = tool_context.get("web_search")
        if isinstance(web_context, dict):
            rendered.append(f"- Web search status: {web_context.get('status')}")
            results = web_context.get("results")
            if isinstance(results, list) and results:
                for index, result in enumerate(results[:5], start=1):
                    if isinstance(result, dict):
                        rendered.append(
                            f"  {index}. {result.get('title') or 'Untitled'} | "
                            f"{result.get('url') or '-'} | {result.get('snippet') or ''}"
                        )
            elif web_context.get("status") == "no_results":
                rendered.append(
                    "  no web results were found; continue from runtime context or general reasoning when sufficient."
                )
        code_context = tool_context.get("code_execution")
        if isinstance(code_context, dict):
            rendered.append(
                "- Code execution status: "
                f"{code_context.get('status')} ({code_context.get('language')})"
            )
            if code_context.get("stdout"):
                rendered.append(f"  stdout: {code_context.get('stdout')}")
            if code_context.get("stderr"):
                rendered.append(f"  stderr: {code_context.get('stderr')}")
        if "canvas" in tool_context:
            rendered.append(
                "- Canvas is enabled: make the final answer suitable for editable artifact use."
            )
        return rendered

    @staticmethod
    def _format_file_context(file_context: object) -> list[str]:
        """Render retrieved uploaded-file chunks for role-specific prompts."""
        if not isinstance(file_context, dict) or not file_context:
            return []
        rendered = [f"- retrieval status: {file_context.get('status')}"]
        files = file_context.get("files")
        if isinstance(files, list) and files:
            rendered.append("- files:")
            for file in files[:8]:
                if isinstance(file, dict):
                    rendered.append(
                        "  - "
                        f"{file.get('name')} | file_id={file.get('file_id')} | "
                        f"status={file.get('status')} | parser={file.get('parser')}"
                    )
        chunks = file_context.get("chunks")
        if isinstance(chunks, list) and chunks:
            rendered.append("- retrieved chunks:")
            for index, chunk in enumerate(chunks[:8], start=1):
                if isinstance(chunk, dict):
                    rendered.append(
                        f"  [{index}] file_id={chunk.get('file_id')} "
                        f"chunk={chunk.get('order')} score={chunk.get('score')}"
                    )
                    rendered.append(f"  {chunk.get('text') or ''}")
        return rendered

    @staticmethod
    def _format_mcp_context(mcp_context: object) -> list[str]:
        """Render selected MCP tool catalogs for role-specific prompts."""
        if not isinstance(mcp_context, dict) or not mcp_context:
            return []
        rendered = [f"- status: {mcp_context.get('status')}"]
        servers = mcp_context.get("servers")
        if isinstance(servers, list):
            for server in servers[:6]:
                if not isinstance(server, dict):
                    continue
                rendered.append(
                    f"- server {server.get('server_id')}: status={server.get('status')}"
                )
                if server.get("error_message"):
                    rendered.append(f"  error: {server.get('error_message')}")
                tools = server.get("tools")
                if isinstance(tools, list):
                    for tool in tools[:12]:
                        if isinstance(tool, dict):
                            rendered.append(
                                f"  - tool {tool.get('name')}: {tool.get('description') or ''}"
                            )
        return rendered

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

    @staticmethod
    def _format_conversation_history(conversation_history: list[object]) -> list[str]:
        """Render recent conversation messages for stage prompts."""
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
