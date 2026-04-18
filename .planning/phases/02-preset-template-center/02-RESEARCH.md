# Phase 2: Preset Template Center - Research

**Researched:** 2026-04-18
**Domain:** preset/template configuration design, YAML-backed preset registry, API-level preset selection
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Phase 2 采用文件配置优先，默认模板以 `YAML` 文件形式存放。
- 模板文件放在独立目录中，不写死在 `TaskService` 中。
- 沿用现有 `TaskRequest.preset_mode` 作为模式入口。
- Phase 2 不做真实 Agent 实例化执行。
- `preset_mode` 为空时回退到 `default`，显式未知值返回结构化错误。

### the agent's Discretion
- YAML 组织方式
- loader/service 命名
- discovery 接口字段细节

### Deferred Ideas (OUT OF SCOPE)
- 多 Agent 角色实例化
- 串行调度执行
- 仓库分析与审批开关的真实执行逻辑

</user_constraints>

<research_summary>
## Summary

对当前代码基线而言，最稳的模板中心实现不是先做数据库和后台管理，而是建立“静态模板文件 + schema 校验 + loader + registry + API integration”这条清晰链路。这样做有两个直接好处：第一，模板内容可以被课程演示直接查看；第二，后续 Phase 3 到 Phase 6 可以继续复用同一套模板对象，而不用推翻存储方式。

现有 Phase 1 已经有 `TaskRequest.preset_mode`、`TaskService` 和统一响应 contract，因此 Phase 2 的标准做法应该是在 service 层插入“解析 preset -> 加载模板 -> 注入模板元信息 -> 再调用 adapter”的步骤，同时新增一个轻量 discovery 接口，便于前端或 CLI 查询当前支持的模式。

**Primary recommendation:** 用 `YAML + Pydantic schema + preset loader + registry service + /api/presets discovery + /api/tasks integration` 完成 Phase 2，严格只交付模板定义与加载能力。
</research_summary>

<standard_stack>
## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyYAML | project-pinned | 解析 preset YAML 文件 | Python 中处理轻量配置最直接 |
| Pydantic | existing | 模板 schema 校验 | 当前后端已经用 Pydantic，复用成本最低 |
| FastAPI | existing | 暴露 preset discovery 和 task integration | 已是现有 API 基础 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | 模板目录扫描 | 读取本地模板文件时使用 |
| functools.lru_cache | stdlib | 缓存模板注册表 | 模板变更不频繁时可减少重复 IO |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| YAML files | JSON files | JSON 更简单，但可读性和注释能力较弱 |
| 文件模板 | SQLite 存储 | SQLite 更适合后续管理，但当前阶段成本更高 |
| 直接写在 Python dict | 独立 YAML + schema | 写死在代码里不利于扩展和展示 |

**Installation:**
```bash
pip install pyyaml
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```text
app/
├─ backend/
│  ├─ api/routes/presets.py      # discovery endpoint
│  ├─ schemas/preset.py          # preset schema
│  ├─ services/preset_loader.py  # YAML loader
│  ├─ services/preset_service.py # registry/query layer
│  └─ services/task_service.py   # consume preset metadata before adapter call
└─ presets/
   ├─ default.yaml
   ├─ code-engineering.yaml
   ├─ code-review.yaml
   └─ doc-organize.yaml
```

### Pattern 1: File-backed registry with schema validation
**What:** 启动或首次访问时读取模板文件，并用 schema 校验后缓存。
**When to use:** 模板数量少、变动频率低、以课程演示和原型验证为主时。
**Example:**
```python
preset = PresetDefinition.model_validate(yaml.safe_load(path.read_text("utf-8")))
```

### Pattern 2: Task service enrichment before adapter execution
**What:** `TaskService` 在调用 adapter 前先解析 `preset_mode`，并把模板元信息放进 metadata 或 normalized request。
**When to use:** API 已经稳定，希望模板中心对上游调用尽量透明时。
**Example:**
```python
resolved_preset = preset_service.resolve(payload.preset_mode)
normalized_request["metadata"]["preset"] = resolved_preset.model_dump()
```

### Anti-Patterns to Avoid
- **把模板对象散落在 route 和 service 里各自维护一套字段:** 会导致后续 Phase 3 之前就出现字段漂移。
- **Phase 2 直接实现角色执行链:** 这会提前侵入 Phase 3 的边界。
- **缺少 default 模板:** 会让 `preset_mode` 可选字段在运行时没有稳定回退路径。
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 模板校验 | 手写字段检查 | Pydantic schema | 字段演进时更稳，错误信息更清晰 |
| 配置解析 | 自己写 YAML parser | PyYAML | 当前阶段没有必要自造解析器 |
| 模板注册缓存 | 每次请求都重新扫目录 | loader + service cache | 模板文件读取频率低，缓存更直接 |
| API 入口重复设计 | 新建平行任务接口 | 复用 `/api/tasks` + `preset_mode` | 当前已有稳定入口，不应推翻 |

**Key insight:** Phase 2 的难点不是“如何执行模板”，而是“如何让模板成为一个可被后续阶段稳定消费的对象”。
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Template schema drift
**What goes wrong:** YAML 文件字段和 Python 中消费字段不一致。
**Why it happens:** 没有统一 schema 或 loader 做校验。
**How to avoid:** 所有模板文件必须先过 `PresetDefinition` 校验。
**Warning signs:** 某些模板能加载、某些模板在运行时 KeyError。

### Pitfall 2: Default fallback ambiguity
**What goes wrong:** 用户不传 `preset_mode` 时系统行为不稳定，或显式传错值时被静默吞掉。
**Why it happens:** 缺少明确的回退和错误策略。
**How to avoid:** 把“空值回退 default、未知值报错”写进 service 逻辑和响应 contract。
**Warning signs:** 同一接口对不同异常输入返回不可预测结果。

### Pitfall 3: Scope bleed into orchestration
**What goes wrong:** Phase 2 的实现开始处理角色实例化和执行顺序。
**Why it happens:** 模板字段里已经包含 `agent_roles` 和 `execution_flow`，容易顺手做执行逻辑。
**How to avoid:** 只做定义、解析、返回，不做运行。
**Warning signs:** `TaskService` 出现 “for role in agent_roles” 之类的执行代码。
</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns from current architecture:

### Preset schema shape
```python
class PresetDefinition(BaseModel):
    preset_mode: str
    display_name: str
    description: str
    agent_roles: list[str]
    execution_flow: list[str]
    default_models: dict[str, str]
    requires_repo_analysis: bool = False
    requires_approval: bool = False
```

### Preset resolution in service layer
```python
resolved = preset_service.resolve(payload.preset_mode)
normalized_request["metadata"]["resolved_preset"] = resolved.model_dump()
```

### Discovery endpoint
```python
@router.get("/presets", response_model=list[PresetSummary])
def list_presets(service: PresetService = Depends(get_preset_service)):
    return service.list_presets()
```
</code_examples>

<sota_updates>
## State of the Art (2024-2025)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| prompt 写死在代码里 | externalized preset/template config | 2024+ | 便于协作、对齐和扩展 |
| 单一入口无模式区分 | preset-driven task context | 2024+ | 更适合多场景 coding assistant |
| 执行前不做 schema validation | config schema first | 2024+ | 降低运行时漂移风险 |

**New tools/patterns to consider:**
- 通过 API 暴露 preset discovery，方便 GUI 和 CLI 统一获取可选模式
- 把模板定义为“元信息 + 开关”，后续再逐阶段接入真实执行逻辑

**Deprecated/outdated:**
- 把每种模式硬编码成 if/else prompt 分支
- 不区分“模式选择”和“执行编排”的实现阶段
</sota_updates>

<open_questions>
## Open Questions

1. **模板目录命名是否固定为 `app/presets`？**
   - What we know: 需要独立目录存储模板文件。
   - What's unclear: 具体命名尚未写死。
   - Recommendation: planning 里直接选一个稳定路径，例如 `app/presets`。

2. **是否在 Phase 2 就加 discovery 接口？**
   - What we know: 预设模式入口需要被观察到。
   - What's unclear: 是否只依靠 `preset_mode` 入参即可。
   - Recommendation: 增加轻量 `GET /api/presets`，成本低且便于演示。
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `app/backend/schemas/task.py`
- `app/backend/services/task_service.py`

### Secondary (MEDIUM confidence)
- `output/doc/多Agent智能软件研发辅助平台_概要设计说明书_OpenHands版.docx`
- `output/doc/多Agent智能软件研发辅助平台_详细设计说明书_OpenHands版.docx`

### Tertiary (LOW confidence - needs validation)
- None
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: preset schema, YAML config, service integration
- Ecosystem: PyYAML, Pydantic, FastAPI
- Patterns: file-backed registry, task enrichment, preset discovery
- Pitfalls: drift, fallback ambiguity, scope bleed

**Confidence breakdown:**
- Standard stack: HIGH
- Architecture: HIGH
- Pitfalls: HIGH
- Code examples: MEDIUM

**Research date:** 2026-04-18
**Valid until:** 2026-05-18
</metadata>

---

*Phase: 02-preset-template-center*
*Research completed: 2026-04-18*
*Ready for planning: yes*

