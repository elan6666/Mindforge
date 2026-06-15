"""Portable Loop Library storage and loop.md import/export."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
import json
import re
from pathlib import Path

from app.backend.core.config import Settings, get_settings
from app.backend.schemas.loops import (
    LoopArtifactSpec,
    LoopDefinition,
    LoopImproveRequest,
    LoopImportRequest,
    LoopMarkdownExport,
    LoopRole,
    LoopStep,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "loop"


class LoopService:
    """Manage Loop definitions as portable workflow assets."""

    def __init__(self, settings: Settings) -> None:
        self.path = Path(settings.loop_library_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save({item.loop_id: item for item in self._default_loops()})

    def list_loops(self) -> list[LoopDefinition]:
        """Return all Loop definitions."""
        return sorted(self._load().values(), key=lambda item: (item.forge_id, item.name))

    def get_loop(self, loop_id: str) -> LoopDefinition | None:
        """Return a Loop by id."""
        return self._load().get(loop_id)

    def upsert_loop(self, loop: LoopDefinition) -> LoopDefinition:
        """Create or update a Loop."""
        records = self._load()
        loop.updated_at = _now()
        loop.loop_md = self.to_markdown(loop)
        records[loop.loop_id] = loop
        self._save(records)
        return loop

    def import_markdown(self, payload: LoopImportRequest) -> LoopDefinition:
        """Create a Loop from portable loop.md content."""
        loop = self.from_markdown(payload.content)
        loop.source = "loop.md"
        return self.upsert_loop(loop)

    def export_markdown(self, loop_id: str) -> LoopMarkdownExport | None:
        """Return a portable loop.md file payload."""
        loop = self.get_loop(loop_id)
        if loop is None:
            return None
        content = loop.loop_md or self.to_markdown(loop)
        return LoopMarkdownExport(
            loop_id=loop.loop_id,
            filename=f"{loop.loop_id}.loop.md",
            content=content,
        )

    def improve_loop(self, loop_id: str, payload: LoopImproveRequest) -> LoopDefinition | None:
        """Record one improvement pass after a Loop run."""
        loop = self.get_loop(loop_id)
        if loop is None:
            return None
        loop.improvement_count += 1
        note = (payload.note or "").strip()
        if note:
            loop.evaluation_rubric = [
                *loop.evaluation_rubric,
                f"Iteration {loop.improvement_count}: {note}",
            ][-8:]
        loop.version = self._bump_patch(loop.version)
        return self.upsert_loop(loop)

    def to_markdown(self, loop: LoopDefinition) -> str:
        """Serialize a Loop to a readable, portable loop.md document."""
        lines = [
            f"# Loop: {loop.name}",
            "",
            f"- id: {loop.loop_id}",
            f"- version: {loop.version}",
            f"- forge: {loop.forge_id}",
            f"- status: {loop.status}",
            "",
            "## Purpose",
            loop.description,
            "",
            "## Inputs",
            *[f"- {item}" for item in loop.inputs],
            "",
            "## Roles",
            *[
                f"- {role.name} ({role.role_id}): {role.responsibility}"
                for role in loop.roles
            ],
            "",
            "## Steps",
            *[
                (
                    f"{index}. {step.title} [{step.owner_role}] - "
                    f"{step.instruction} -> {step.expected_output}"
                )
                for index, step in enumerate(loop.steps, start=1)
            ],
            "",
            "## Tools",
            *[f"- {item}" for item in loop.tools],
            "",
            "## Evidence Rules",
            *[f"- {item}" for item in loop.evidence_rules],
            "",
            "## Artifacts",
            *[
                f"- {artifact.title} ({artifact.format}): {artifact.purpose}"
                for artifact in loop.artifact_outputs
            ],
            "",
            "## Evaluation",
            *[f"- {item}" for item in loop.evaluation_rubric],
            "",
            "## Memory Policy",
            loop.memory_policy,
            "",
        ]
        return "\n".join(lines)

    def from_markdown(self, content: str) -> LoopDefinition:
        """Parse a pragmatic loop.md subset into a LoopDefinition."""
        title_match = re.search(r"^#\s*Loop:\s*(.+)$", content, re.MULTILINE)
        name = title_match.group(1).strip() if title_match else "Imported Loop"
        metadata = dict(re.findall(r"^-\s*([a-z_]+):\s*(.+)$", content, re.MULTILINE))
        sections = self._parse_sections(content)
        roles = []
        for index, raw in enumerate(sections.get("Roles", []), start=1):
            cleaned = raw.lstrip("- ").strip()
            match = re.match(r"(.+?)\s*\((.+?)\):\s*(.+)", cleaned)
            roles.append(
                LoopRole(
                    role_id=_slug(match.group(2) if match else f"role-{index}"),
                    name=(match.group(1).strip() if match else cleaned or f"Role {index}"),
                    responsibility=(match.group(3).strip() if match else cleaned),
                )
            )
        steps = []
        for index, raw in enumerate(sections.get("Steps", []), start=1):
            cleaned = re.sub(r"^\d+\.\s*", "", raw).strip()
            title_part, _, rest = cleaned.partition(" - ")
            title = title_part.split("[")[0].strip() or f"Step {index}"
            owner_match = re.search(r"\[(.+?)\]", title_part)
            expected = rest.split("->", 1)[1].strip() if "->" in rest else ""
            instruction = rest.split("->", 1)[0].strip() if rest else cleaned
            steps.append(
                LoopStep(
                    step_id=f"step-{index}",
                    title=title,
                    owner_role=_slug(owner_match.group(1) if owner_match else "coordinator"),
                    instruction=instruction,
                    expected_output=expected,
                )
            )
        purpose = "\n".join(sections.get("Purpose", [])).strip()
        artifacts = []
        for raw in sections.get("Artifacts", []):
            cleaned = raw.lstrip("- ").strip()
            title, _, purpose_text = cleaned.partition(":")
            artifacts.append(
                LoopArtifactSpec(
                    title=title.strip() or "Loop artifact",
                    format="markdown",
                    purpose=purpose_text.strip(),
                )
            )
        return LoopDefinition(
            loop_id=metadata.get("id", _slug(name)),
            name=name,
            description=purpose or "Imported portable Loop.",
            forge_id=metadata.get("forge", "code-forge"),
            version=metadata.get("version", "1.0.0"),
            status=metadata.get("status", "ready"),
            inputs=[item.lstrip("- ").strip() for item in sections.get("Inputs", [])],
            roles=roles or [LoopRole(role_id="coordinator", name="Coordinator", responsibility="Run the loop.")],
            steps=steps or [
                LoopStep(
                    step_id="step-1",
                    title="Run loop",
                    owner_role="coordinator",
                    instruction="Execute the imported Loop.",
                    expected_output="Loop result",
                )
            ],
            tools=[item.lstrip("- ").strip() for item in sections.get("Tools", [])],
            evidence_rules=[
                item.lstrip("- ").strip() for item in sections.get("Evidence Rules", [])
            ],
            artifact_outputs=artifacts,
            evaluation_rubric=[
                item.lstrip("- ").strip() for item in sections.get("Evaluation", [])
            ],
            memory_policy="\n".join(sections.get("Memory Policy", [])).strip()
            or "Record loop output and improvement notes.",
            updated_at=_now(),
            loop_md=content,
        )

    @staticmethod
    def _parse_sections(content: str) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = {}
        current: str | None = None
        for line in content.splitlines():
            heading = re.match(r"^##\s+(.+)$", line)
            if heading:
                current = heading.group(1).strip()
                sections[current] = []
                continue
            if current and line.strip():
                sections[current].append(line.strip())
        return sections

    @staticmethod
    def _bump_patch(version: str) -> str:
        parts = [int(part) if part.isdigit() else 0 for part in version.split(".")[:3]]
        while len(parts) < 3:
            parts.append(0)
        parts[2] += 1
        return ".".join(str(part) for part in parts)

    def _load(self) -> dict[str, LoopDefinition]:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        return {
            key: LoopDefinition.model_validate(value)
            for key, value in data.get("loops", {}).items()
        }

    def _save(self, records: dict[str, LoopDefinition]) -> None:
        self.path.write_text(
            json.dumps(
                {"loops": {key: value.model_dump(mode="json") for key, value in records.items()}},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _default_loops(self) -> list[LoopDefinition]:
        now = _now()
        return [
            LoopDefinition(
                loop_id="code-review-loop",
                name="Code Review Loop",
                description="把代码任务变成可审计的工程循环：读仓库、拆风险、运行验证、产出报告、再改进 Loop。",
                forge_id="code-forge",
                trigger_phrases=["代码审查", "修 bug", "PR review", "run code loop"],
                inputs=["repo path", "issue or PR", "acceptance criteria", "test command"],
                roles=[
                    LoopRole(role_id="pm", name="Project Manager", responsibility="拆任务、定边界、确认验收标准"),
                    LoopRole(role_id="backend", name="Backend Agent", responsibility="分析 API、数据和后端风险"),
                    LoopRole(role_id="frontend", name="Frontend Agent", responsibility="检查 UI、状态、交互和浏览器验证"),
                    LoopRole(role_id="reviewer", name="Reviewer", responsibility="审查遗漏、测试证据和回归风险"),
                ],
                steps=[
                    LoopStep(step_id="context", title="读取上下文", owner_role="pm", instruction="确认仓库、目标、约束和可执行验证。", evidence_required=["repo summary"], expected_output="任务边界"),
                    LoopStep(step_id="risk", title="拆解风险", owner_role="backend", instruction="列出后端、前端、数据、权限和依赖风险。", evidence_required=["changed surface"], expected_output="风险清单"),
                    LoopStep(step_id="build", title="实施或建议", owner_role="frontend", instruction="按最小改动完成实现或给出可执行建议。", evidence_required=["diff or plan"], expected_output="实现说明"),
                    LoopStep(step_id="verify", title="运行验证", owner_role="reviewer", instruction="运行测试、类型检查或浏览器检查，并记录失败项。", evidence_required=["test output"], expected_output="验证结果"),
                    LoopStep(step_id="improve", title="改进 Loop", owner_role="pm", instruction="根据本次结果更新下一轮 Loop 的检查点。", evidence_required=["review note"], expected_output="Loop 改进建议"),
                ],
                tools=["GitHub", "Codex Security", "Build Web Apps", "Browser"],
                evidence_rules=["每个结论绑定文件、命令、截图或模型输出来源。", "失败验证不能隐藏，必须进入下一轮改进。"],
                artifact_outputs=[
                    LoopArtifactSpec(title="代码审查报告", format="markdown", purpose="交付给用户或老师的工程证据"),
                    LoopArtifactSpec(title="验证记录", format="markdown", purpose="说明跑了什么、结果如何"),
                ],
                evaluation_rubric=["是否解决目标", "是否有可追溯证据", "是否能复用到下一台设备"],
                approval_checkpoints=["写入文件", "执行外部命令", "调用付费 API"],
                updated_at=now,
            ),
            LoopDefinition(
                loop_id="worldcup-prediction-loop",
                name="World Cup Prediction Loop",
                description="用五个专家 Agent 从球队状态、阵容、战术、赛程和赔率/舆情维度预测冠军，并把过程截图给演示 PPT。",
                forge_id="research-forge",
                trigger_phrases=["世界杯预测", "冠军预测", "demo loop"],
                inputs=["tournament year", "candidate teams", "available sources", "model pair"],
                roles=[
                    LoopRole(role_id="form", name="状态分析 Agent", responsibility="看近期战绩、伤病和核心球员状态"),
                    LoopRole(role_id="squad", name="阵容深度 Agent", responsibility="比较首发、替补、年龄结构和位置短板"),
                    LoopRole(role_id="tactics", name="战术 Agent", responsibility="分析打法适配、攻防转换和教练稳定性"),
                    LoopRole(role_id="schedule", name="赛程 Agent", responsibility="评估分组、淘汰赛路径和旅途消耗"),
                    LoopRole(role_id="market", name="外部信号 Agent", responsibility="参考赔率、媒体共识和不确定性"),
                ],
                steps=[
                    LoopStep(step_id="question", title="锁定问题", owner_role="form", instruction="确认预测目标和候选队。", evidence_required=["candidate teams", "recent form source"], expected_output="研究问题"),
                    LoopStep(step_id="evidence", title="多源收集", owner_role="squad", instruction="分别收集五个维度证据。", evidence_required=["squad depth source", "injury or roster source"], expected_output="证据表"),
                    LoopStep(step_id="debate", title="专家讨论", owner_role="tactics", instruction="让五个 Agent 给出候选冠军和反证。", evidence_required=["tactical evidence", "counter-evidence"], expected_output="分歧点"),
                    LoopStep(step_id="score", title="评分合并", owner_role="market", instruction="按维度评分并给出置信度。", evidence_required=["market odds source", "media consensus source"], expected_output="冠军预测"),
                    LoopStep(step_id="artifact", title="沉淀产物", owner_role="schedule", instruction="生成 War Room 过程和报告截图清单。", evidence_required=["schedule source", "travel or rest-day evidence"], expected_output="演示素材"),
                ],
                tools=["Browser", "Data Analytics", "Documents", "Presentations"],
                evidence_rules=["不要只给结论，必须展示每个 Agent 的证据和不确定性。", "预测必须包含反证和置信度。"],
                artifact_outputs=[
                    LoopArtifactSpec(title="世界杯预测报告", format="markdown", purpose="课堂演示 demo"),
                    LoopArtifactSpec(title="War Room 过程截图", format="image-set", purpose="PPT 展示多 Agent 过程"),
                ],
                evaluation_rubric=["维度覆盖是否完整", "证据是否可追溯", "结论是否自然可信"],
                updated_at=now,
            ),
        ]


@lru_cache(maxsize=1)
def get_loop_service() -> LoopService:
    return LoopService(get_settings())


def clear_loop_service_cache() -> None:
    get_loop_service.cache_clear()
