# Phase 1: OpenHands Foundation - Research

**Researched:** 2026-04-18
**Domain:** OpenHands integration, Python FastAPI service scaffold, local single-user orchestration entry
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 采用 `API-first` 路线，优先把 FastAPI 服务和统一任务入口跑通。
- 以外部适配层优先，尽量不直接修改 OpenHands 核心逻辑。
- Phase 1 先建立后端主骨架，前端只做占位。
- 目标运行形态是本地单用户服务。
- “Phase 1 完成”定义为一次端到端任务转发演示可用，并返回统一响应，同时记录基础日志。

### the agent's Discretion
- Python 包布局和命名细节
- 配置库和日志落盘实现

### Deferred Ideas (OUT OF SCOPE)
- 模板中心与预设模式
- 角色化 Agent 实例化
- 仓库分析与上下文注入
- 审批、历史记录和 GitHub 集成

</user_constraints>

<research_summary>
## Summary

Phase 1 的关键不是“把 OpenHands 改得很深”，而是建立一个可持续扩展的接入边界。对你们这个项目而言，标准做法不是直接在业务入口里散落 OpenHands 调用，而是用独立的适配层把任务请求、上下文、运行参数和结果对象统一起来，再由 FastAPI 负责暴露稳定接口。

从工程节奏上看，最稳的路线是先交付一个本地单用户服务：提供健康检查、任务提交接口、统一响应模型、基础日志和一个可替换的 OpenHands adapter。这样后续 Phase 2 到 Phase 7 都是在既有骨架上加模块，而不是回头重构入口层。

**Primary recommendation:** 用 `FastAPI + Pydantic schemas + integration adapter + service layer + lightweight SQLite/log storage` 建立最小可运行骨架，显式保留 GUI/CLI 和后续模板调度的接入位。
</research_summary>

<standard_stack>
## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | project-pinned | 后端主语言 | 与 OpenHands 二开路线和你们既定技术栈一致 |
| FastAPI | project-pinned | 提供 HTTP 任务入口和健康检查 | 轻量、类型友好、适合原型和服务骨架 |
| Pydantic | project-pinned | 请求/响应和配置模型 | 与 FastAPI 自然配合，减少手写校验 |
| OpenHands | selected baseline | Agent runtime / coding assistant 底座 | 直接复用现有能力，避免从零实现 agent 内核 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uvicorn | project-pinned | 本地服务运行 | 启动 FastAPI 开发服务 |
| sqlite3 / SQLModel-equivalent | project-pinned | 最小日志与历史落盘 | Phase 1 只需基础持久化 |
| structlog / logging | project-pinned | 统一日志输出 | 需要结构化日志时使用 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI | Flask | Flask 更轻，但类型和 schema 一体化较弱 |
| 直接改 OpenHands 核心 | 外部 adapter | 外部 adapter 初期更稳，后续升级底座风险更低 |
| 立即做前后端一体 | API-first | API-first 更适合先验证接入边界和请求链路 |

**Installation:**
```bash
# 以项目选择的 OpenHands 基线和 Python 依赖为准
pip install fastapi uvicorn pydantic
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```text
app/
├─ backend/
│  ├─ api/            # FastAPI routes and request handling
│  ├─ core/           # settings, logging, app factory
│  ├─ integration/    # OpenHands adapter boundary
│  ├─ schemas/        # request/response/domain schemas
│  ├─ services/       # task orchestration and normalization
│  └─ storage/        # log/history persistence
├─ frontend/          # GUI extension placeholder only in Phase 1
└─ scripts/           # local startup and verification helpers
```

### Pattern 1: Thin API, explicit service layer
**What:** API 路由只做参数接收、调用 service、返回 schema，不直接编写 OpenHands 调用逻辑。
**When to use:** 所有任务提交、健康检查和后续模式选择入口。
**Example:**
```python
@router.post("/tasks", response_model=TaskResponse)
def create_task(payload: TaskRequest, service: TaskService = Depends(get_task_service)):
    return service.submit(payload)
```

### Pattern 2: Adapter boundary for external runtime
**What:** 用单独 adapter 封装 OpenHands 调用，把底层请求参数、异常和结果标准化。
**When to use:** 任何需要调用 OpenHands runtime 的路径。
**Example:**
```python
class OpenHandsAdapter:
    def run_task(self, request: NormalizedTaskRequest) -> AdapterResult:
        ...
```

### Anti-Patterns to Avoid
- **在 API 路由里直接拼 OpenHands 调用细节:** 这会让 Phase 2+ 的功能全耦合到入口层。
- **Phase 1 就设计复杂多 Agent 状态机:** 当前阶段只需要单条基础转发链路。
- **把 GUI、CLI、API 同时做完:** 会稀释 Phase 1 的交付焦点。
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP 服务骨架 | 手写 WSGI/路由层 | FastAPI | 请求校验、文档和依赖注入都已有成熟方案 |
| 请求对象校验 | 手写 dict 解析 | Pydantic schemas | 可读性和维护性更好 |
| OpenHands 内部运行时 | 自研 agent loop | OpenHands baseline + adapter | 当前项目目标就是复用底座 |
| 日志持久化体系 | 一开始就做复杂 observability | Phase 1 最小日志表或文件落盘 | MVP 只需要可追踪和可演示 |

**Key insight:** Phase 1 的价值在于建立可演进的接入边界，不在于自研基础设施。
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Adapter boundary leaks
**What goes wrong:** API 层、service 层和 adapter 层都知道 OpenHands 的内部字段和异常细节。
**Why it happens:** 早期为了快，把调用细节直接写进 route。
**How to avoid:** 统一 `TaskRequest -> NormalizedTaskRequest -> AdapterResult -> TaskResponse` 转换链。
**Warning signs:** 多个文件同时 import 同一套底座内部对象或字段。

### Pitfall 2: Skeleton without runnable demo
**What goes wrong:** 目录建好了，但没有真正可启动的服务和端到端转发。
**Why it happens:** 过度关注分层和命名，忽略最小运行闭环。
**How to avoid:** 在 Plan 里强制加入启动命令、健康检查和任务转发验收。
**Warning signs:** 只有文档和空文件，没有可执行入口。

### Pitfall 3: Early over-design
**What goes wrong:** 在 Phase 1 就引入模板中心、角色图、复杂数据库结构。
**Why it happens:** 把后续阶段问题提前塞进基础接入阶段。
**How to avoid:** 明确 Phase 1 只做基础入口、适配层和最小日志。
**Warning signs:** Phase 1 的文件里出现模板匹配、角色实例化、GitHub 集成等逻辑。
</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns from official sources:

### App factory
```python
from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="Multi-Agent Assistant")
    return app
```

### Unified request schema
```python
from pydantic import BaseModel

class TaskRequest(BaseModel):
    prompt: str
    preset_mode: str | None = None
    repo_path: str | None = None
```

### Adapter result normalization
```python
class AdapterResult(BaseModel):
    status: str
    output: str
    raw_provider: str | None = None
```
</code_examples>

<sota_updates>
## State of the Art (2024-2025)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 单一聊天式 AI 工具 | 可集成的 coding agent runtime | 2024+ | 底座复用优于从零实现 agent loop |
| 直接耦合模型 SDK | adapter / gateway 分层 | 2024+ | 后续模型替换和路由更容易 |
| 一开始搭全量产品壳 | 先打通 API-first skeleton | 2024+ | 更适合 MVP 和二开验证 |

**New tools/patterns to consider:**
- 基于 OpenHands 的本地 GUI / CLI / API 多入口复用
- 为后续模型路由预留统一 request/response contract

**Deprecated/outdated:**
- 直接在业务入口散落 provider-specific 调用
- 没有 schema 的自由格式输入输出
</sota_updates>

<open_questions>
## Open Questions

1. **OpenHands 的具体接入方式是 SDK 直连还是命令/服务封装？**
   - What we know: 你们已经决定以 OpenHands 为底座。
   - What's unclear: 具体采用的本地运行面和调用契约尚未落到代码。
   - Recommendation: 规划阶段先把 adapter 设计为可替换边界，不把实现方式写死。

2. **Phase 1 的最小日志落盘采用 SQLite 还是文件？**
   - What we know: 你们整体技术基线里已有 SQLite。
   - What's unclear: 是否在 Phase 1 就需要数据库表。
   - Recommendation: 计划允许“文件日志或 SQLite 任一满足验收”，执行时按实现成本择优。
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md` - 项目约束和技术基线
- `.planning/REQUIREMENTS.md` - Phase 1 对应需求
- `.planning/ROADMAP.md` - 阶段目标和成功标准

### Secondary (MEDIUM confidence)
- `output/doc/多Agent智能软件研发辅助平台_概要设计说明书_OpenHands版.docx` - 模块边界和系统流程
- `output/doc/多Agent智能软件研发辅助平台_详细设计说明书_OpenHands版.docx` - 数据对象和模块职责

### Tertiary (LOW confidence - needs validation)
- None
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: OpenHands integration + FastAPI skeleton
- Ecosystem: schema, adapter, logging, local service shape
- Patterns: API-first, thin routes, explicit adapter boundary
- Pitfalls: over-design, no runnable demo, adapter leakage

**Confidence breakdown:**
- Standard stack: MEDIUM - 与既定技术栈一致，但具体 OpenHands 接入契约待执行时确认
- Architecture: HIGH - 分层边界和最小骨架判断清晰
- Pitfalls: HIGH - 直接来自当前项目阶段特征
- Code examples: MEDIUM - 为规划示意，不绑定最终实现细节

**Research date:** 2026-04-18
**Valid until:** 2026-05-18
</metadata>

---

*Phase: 01-openhands-foundation*
*Research completed: 2026-04-18*
*Ready for planning: yes*
