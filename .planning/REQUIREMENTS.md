# Requirements: 多Agent智能软件研发辅助平台

**Defined:** 2026-04-18  
**Core Value:** 基于 `OpenHands` 交付一个通过预设模式驱动多角色协作的多 Agent 助手平台。

## v1 Requirements

### Foundation

- [x] **FOUND-01**: 用户可以在本地启动基础服务或任务入口。
- [x] **FOUND-02**: 系统可以通过统一适配层把基础任务请求转发给 `OpenHands`。
- [x] **FOUND-03**: 系统提供 `FastAPI` 扩展入口和统一请求/响应模型。
- [x] **FOUND-04**: 系统可以记录最小可用的任务日志和运行结果摘要。

### Preset Templates

- [x] **PRESET-01**: 用户可以选择代码工程模式、代码审查模式、文档整理模式、论文修改模式发起任务。
- [x] **PRESET-02**: 系统可以根据 `preset_mode` 加载模板配置。
- [x] **PRESET-03**: 模板配置至少包含 `preset_mode`、`agent_roles`、`execution_flow`、`default_models`、`requires_repo_analysis`、`requires_approval`。

### Agent Collaboration

- [x] **AGENT-01**: 代码工程模式下系统可以自动实例化项目经理、后端、前端、审查 Agent。
- [x] **AGENT-02**: 系统支持按“规划 -> 实现 -> 审查”的串行流程调度任务。
- [x] **AGENT-03**: 系统可以汇总各阶段结果并生成结构化输出。

### Repository Context

- [x] **REPO-01**: 系统可以分析本地仓库目录结构。
- [x] **REPO-02**: 系统可以识别关键文件，如 `README`、依赖文件、配置文件、Docker 文件和入口文件。
- [x] **REPO-03**: 系统可以生成并注入结构化仓库摘要。

### Model Routing

- [ ] **MODEL-01**: 系统可以维护多个模型配置。
- [ ] **MODEL-02**: 系统可以按任务类型和预设模式进行模型路由。
- [ ] **MODEL-03**: 系统支持默认模型和优先级设置。

### Control & History

- [ ] **CTRL-01**: 系统在高风险步骤触发人工审批。
- [ ] **CTRL-02**: 系统记录审批结果、任务级日志和阶段级日志。
- [ ] **CTRL-03**: 系统支持查看历史任务、审批记录和结果产物索引。

### External Context & Results

- [ ] **GH-01**: 系统支持读取 GitHub 仓库元信息。
- [ ] **GH-02**: 系统支持读取 Issue 和 PR 摘要作为上下文。
- [ ] **RESULT-01**: 系统展示最终结果、阶段摘要、关键信息和执行日志。

## v2 Requirements

### Advanced Collaboration

- **ADV-01**: 系统支持并行多 Agent 调度。
- **ADV-02**: 系统支持 `worktree` 隔离执行。
- **ADV-03**: 系统支持长期记忆和跨项目知识沉淀。

### Academic Paper Revision

- **PAPER-01**: 系统支持在 `paper-revision` 模式下实例化标准/文风分析 Agent、改写 Agent 和审稿 Agent。
- **PAPER-02**: 当任务指定为期刊论文时，系统支持检索期刊官网投稿规范，并汇总相关期刊论文的结构与文风特征。
- **PAPER-03**: 系统支持基于审稿意见进行至少一轮“审稿 -> 修改 -> 复审”循环，并输出最终修改摘要。

## Out of Scope

| Feature | Reason |
|---------|--------|
| 自研 Agent 内核 | 当前路线明确复用 `OpenHands`，避免重复造轮子 |
| GitHub 写操作 | MVP 先保持只读，降低风险和实现复杂度 |
| 多租户权限系统 | 超出课程设计和原型验证阶段范围 |
| 浏览器 Agent | 第一阶段不引入额外自动化复杂度 |
| 自动投稿与版权处理 | 论文模式仅提供修改辅助，不负责投稿和版权相关流程 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| FOUND-04 | Phase 1 | Complete |
| PRESET-01 | Phase 2 | Complete |
| PRESET-02 | Phase 2 | Complete |
| PRESET-03 | Phase 2 | Complete |
| AGENT-01 | Phase 3 | Complete |
| AGENT-02 | Phase 3 | Complete |
| AGENT-03 | Phase 3 | Complete |
| REPO-01 | Phase 4 | Complete |
| REPO-02 | Phase 4 | Complete |
| REPO-03 | Phase 4 | Complete |
| MODEL-01 | Phase 5 | Pending |
| MODEL-02 | Phase 5 | Pending |
| MODEL-03 | Phase 5 | Pending |
| CTRL-01 | Phase 6 | Pending |
| CTRL-02 | Phase 6 | Pending |
| CTRL-03 | Phase 6 | Pending |
| GH-01 | Phase 7 | Pending |
| GH-02 | Phase 7 | Pending |
| RESULT-01 | Phase 7 | Pending |
| PAPER-01 | Phase 8 | Pending |
| PAPER-02 | Phase 8 | Pending |
| PAPER-03 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 22 total
- v2 requirements: 6 total
- Roadmap-mapped requirements: 25
- Unmapped requirements: 3

---
*Requirements defined: 2026-04-18*  
*Last updated: 2026-04-18 after adding paper-revision mode*
