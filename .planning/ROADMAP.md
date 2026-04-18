# Roadmap: 多Agent智能软件研发辅助平台

## Overview

本项目围绕 `OpenHands 底座 + 模板中心 + 角色化协作` 推进建设，优先交付代码工程模式，并为论文修改模式预留扩展位。路线图遵循“先完成 OpenHands 接入和基础工程，再逐步补齐模板、调度、仓库分析、模型路由、审批历史和 GitHub 只读集成，最后扩展论文修改专用编排”的顺序，避免在早期把系统复杂度拉得过高。

## Phases

**Phase Numbering:**
- Integer phases (`1`, `2`, `3`): 正常规划阶段
- Decimal phases (`2.1`, `2.2`): 紧急插入阶段

- [x] **Phase 1: OpenHands Foundation** - 建立项目基础结构，完成 `OpenHands` 适配层和 `FastAPI` 入口
- [x] **Phase 2: Preset Template Center** - 建立模板配置机制和预设模式入口
- [x] **Phase 3: Agent Instantiation & Orchestration** - 基于模板实现角色化 Agent 实例化与串行调度
- [x] **Phase 4: Repository Analysis & Context Injection** - 补齐仓库分析、关键文件识别和上下文注入
- [ ] **Phase 5: Model Routing** - 实现统一模型配置、模式路由和默认策略
- [ ] **Phase 6: Approval & History** - 增强审批、执行日志、历史记录和结果索引
- [ ] **Phase 7: GitHub Read-Only Context** - 接入 GitHub 只读上下文并完善结果展示
- [ ] **Phase 8: Academic Paper Revision Mode** - 实现论文标准分析、改写与审稿循环

## Phase Details

### Phase 1: OpenHands Foundation

**Goal**: 建立基于 `OpenHands` 的项目基础结构，形成可运行的本地单用户服务，提供统一任务入口、适配层和规范化响应。  
**Depends on**: Nothing  
**Requirements**: [FOUND-01, FOUND-02, FOUND-03, FOUND-04]  
**Success Criteria**:
1. 用户可以在本地启动基础服务。
2. 系统可以接收基础任务请求并通过适配层转发给 `OpenHands`。
3. 系统可以返回统一格式结果，并记录最小可用日志。  
**Plans**: 3 plans

Plans:
- [x] 01-01: 建立基础工程目录、配置结构和运行骨架
- [x] 01-02: 实现 `FastAPI` 任务入口和统一请求/响应模型
- [x] 01-03: 实现 `OpenHands` 适配层接线与本地端到端演示

### Phase 2: Preset Template Center

**Goal**: 建立模板中心和预设模式入口，支持代码工程、代码审查、文档整理和论文修改模式。  
**Depends on**: Phase 1  
**Requirements**: [PRESET-01, PRESET-02, PRESET-03]  
**Success Criteria**:
1. 用户可以选择不同 `preset_mode` 发起任务。
2. 系统可以根据模式加载模板配置。
3. 模板数据可被后续调度链消费。  
**Plans**: 2 plans

Plans:
- [x] 02-01: 设计模板数据结构与默认配置
- [x] 02-02: 实现模板加载逻辑与模式选择入口

### Phase 3: Agent Instantiation & Orchestration

**Goal**: 基于模板实现角色化 Agent 实例化与串行任务调度，优先覆盖代码工程模式。  
**Depends on**: Phase 2  
**Requirements**: [AGENT-01, AGENT-02, AGENT-03]  
**Success Criteria**:
1. 代码工程模式下可以自动实例化项目经理、后端、前端、审查 Agent。
2. 任务可以按“规划 -> 实现 -> 审查”的既定流程执行。
3. 系统可以生成阶段摘要和汇总结果。  
**Plans**: 2 plans

Plans:
- [x] 03-01: 定义角色职责和实例化规则
- [x] 03-02: 实现串行调度流程和阶段结果汇总

### Phase 4: Repository Analysis & Context Injection

**Goal**: 增强研发场景所需的仓库理解能力，支持本地仓库扫描、关键文件识别和上下文注入。  
**Depends on**: Phase 3  
**Requirements**: [REPO-01, REPO-02, REPO-03]  
**Success Criteria**:
1. 系统可以对指定仓库生成结构化摘要。
2. 系统可以识别 `README`、依赖文件、配置文件和关键入口文件。
3. 调度模块可以把仓库摘要注入任务上下文。  
**Plans**: 2 plans

Plans:
- [x] 04-01: 实现仓库扫描与关键文件识别
- [x] 04-02: 实现 `Repo Summary` 和上下文注入

### Phase 5: Model Routing

**Goal**: 建立统一模型配置和基于模式、任务类型的模型路由能力。  
**Depends on**: Phase 4  
**Requirements**: [MODEL-01, MODEL-02, MODEL-03]  
**Success Criteria**:
1. 系统可以维护多个模型配置。
2. 不同模式和任务类型可以选择正确模型。
3. 模型配置变更可被执行链读取。  
**Plans**: TBD

Plans:
- [ ] 05-01: 设计模型配置结构与默认策略
- [ ] 05-02: 实现模式路由与管理入口

### Phase 6: Approval & History

**Goal**: 建立高风险操作审批、执行日志、历史记录和结果索引。  
**Depends on**: Phase 5  
**Requirements**: [CTRL-01, CTRL-02, CTRL-03]  
**Success Criteria**:
1. Shell 执行、大范围文件修改和关键配置覆盖会触发审批。
2. 审批结果、阶段日志和任务日志可查询。
3. 历史记录页可以查看结果产物索引。  
**Plans**: TBD

Plans:
- [ ] 06-01: 实现审批触发和审批记录
- [ ] 06-02: 实现日志和历史记录持久化

### Phase 7: GitHub Read-Only Context

**Goal**: 通过 GitHub 仓库、Issue、PR 摘要补充外部上下文，并增强结果展示体验。  
**Depends on**: Phase 6  
**Requirements**: [GH-01, GH-02, RESULT-01]  
**Success Criteria**:
1. 任务可以引入 GitHub 仓库元信息和 Issue/PR 摘要。
2. 结果页能展示最终结果、阶段摘要和关键提示。
3. 历史页和结果页满足课程演示要求。  
**Plans**: TBD

Plans:
- [ ] 07-01: 实现 GitHub 只读上下文获取
- [ ] 07-02: 增强结果页与历史页展示

### Phase 8: Academic Paper Revision Mode

**Goal**: 基于 `paper-revision` 模式实现论文标准分析、文风对齐、审稿意见生成和多轮修改闭环，优先支持期刊论文场景。  
**Depends on**: Phase 7  
**Requirements**: [PAPER-01, PAPER-02, PAPER-03]  
**Success Criteria**:
1. `paper-revision` 模式下可以自动实例化标准/文风分析 Agent、改写 Agent 和审稿 Agent。
2. 对于期刊论文，系统可以检索期刊官网投稿规范，并汇总同类论文的结构与文风特征。
3. 系统可以执行至少一轮“标准分析 -> 改写 -> 审稿 -> 再修改”的循环，并返回最终修改摘要与审稿建议。  
**Plans**: TBD

Plans:
- [ ] 08-01: 定义论文修改角色职责、期刊标准采集策略和输入输出结构
- [ ] 08-02: 实现论文改写与审稿循环，并生成最终修改报告

## Progress

**Execution Order:**  
Phases execute in numeric order: `1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8`

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. OpenHands Foundation | 3/3 | Complete | 2026-04-18 |
| 2. Preset Template Center | 2/2 | Complete | 2026-04-18 |
| 3. Agent Instantiation & Orchestration | 2/2 | Complete | 2026-04-18 |
| 4. Repository Analysis & Context Injection | 2/2 | Complete | 2026-04-19 |
| 5. Model Routing | 0/2 | Not started | - |
| 6. Approval & History | 0/2 | Not started | - |
| 7. GitHub Read-Only Context | 0/2 | Not started | - |
| 8. Academic Paper Revision Mode | 0/2 | Not started | - |
