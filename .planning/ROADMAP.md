# Roadmap: Mindforge

## Overview

Mindforge is being built in a controlled sequence:

1. establish the OpenHands-based backend skeleton,
2. add presets and role orchestration,
3. inject repository context,
4. build backend model routing and provider/model registry,
5. add a Codex-like frontend workspace shell,
6. add a user-facing model control center and rule templates,
7. then continue with approval, history, GitHub read-only context, and the full academic paper revision workflow.

This keeps backend execution concerns separate from user-facing model and rule authoring concerns.

## Implementation Guidance

Mindforge should avoid greenfield rewrites where OpenHands already provides a usable MIT-licensed pattern. For each new major subsystem, the plan should first check whether OpenHands already solves the same problem in a reusable way, then adapt or simplify that implementation instead of inventing a parallel local abstraction.

Preferred OpenHands reference areas:

- frontend workspace shell: `frontend/src/components/features/conversation/`, `frontend/src/components/features/chat/`, `frontend/src/components/features/browser/`
- reusable skills and repo instructions: `skills/README.md`, `skills/`, `.openhands/microagents/`, `.openhands/skills/`
- skill/instruction loading and workspace-context recall: `openhands/memory/memory.py`
- runtime-oriented tool separation: `openhands/runtime/plugins/agent_skills/`
- agent/state/action abstractions and delegation concepts: `openhands/agenthub/README.md`

Explicit exclusions:

- do not copy `enterprise/` code into the prototype roadmap
- do not import OpenHands cloud or multi-tenant complexity unless a later phase explicitly requires it
- do not recreate OpenHands-compatible structures locally first if a simpler adaptation of the upstream pattern would work

## Phases

**Phase Numbering:**
- Integer phases (`1`, `2`, `3`): normal planned phases
- Decimal phases (`2.1`, `2.2`): inserted urgent phases

- [x] **Phase 1: OpenHands Foundation** - build the base project structure, FastAPI entrypoint, and OpenHands adapter boundary
- [x] **Phase 2: Preset Template Center** - build preset configuration and preset discovery
- [x] **Phase 3: Agent Instantiation & Orchestration** - instantiate role-based agents and run serial orchestration for `code-engineering`
- [x] **Phase 4: Repository Analysis & Context Injection** - analyze local repositories and inject repo summaries into execution context
- [x] **Phase 5: Model Routing & Registry** - implement backend provider/model registry, routing rules, and execution-time model selection
- [x] **Phase 6: Frontend Workspace Shell** - add a Codex-like app shell with sidebar navigation, chat workspace, history, presets, and result panels
- [x] **Phase 7: Model Control Center & Rule Templates** - add user-facing model management, model priorities, rule templates, and dynamic agent-model assignment
- [x] **Phase 8: Approval & History** - add approvals, execution logs, history, and result indexing
- [ ] **Phase 9: GitHub Read-Only Context** - add GitHub repository, issue, and PR read-only context plus richer result presentation
- [ ] **Phase 10: Academic Paper Revision Mode** - complete the paper revision workflow including standards analysis, rewriting, reviewer loops, and journal-guideline-driven rules

## Phase Details

### Phase 1: OpenHands Foundation

**Goal**: Build the OpenHands-based backend skeleton and provide a runnable local single-user service.  
**Depends on**: Nothing  
**Requirements**: [FOUND-01, FOUND-02, FOUND-03, FOUND-04]  
**Success Criteria**:
1. A user can start the local backend service.
2. The system accepts a task request and forwards it through the adapter boundary.
3. The system returns normalized responses and minimal logs.  
**Plans**: 3 plans

Plans:
- [x] 01-01: create the project skeleton, configuration, and runtime bootstrap
- [x] 01-02: implement the FastAPI task API and normalized request/response contracts
- [x] 01-03: connect the OpenHands adapter and complete a local end-to-end demo

Calibration note:
- Phase 1 establishes the OpenHands adapter boundary and demo bridge, but it should not be described as full embedded OpenHands runtime integration yet.

### Phase 2: Preset Template Center

**Goal**: Build a preset center and entrypoint for multiple execution modes.  
**Depends on**: Phase 1  
**Requirements**: [PRESET-01, PRESET-02, PRESET-03]  
**Success Criteria**:
1. Users can submit tasks with different `preset_mode` values.
2. The system loads the correct preset configuration.
3. Preset data can be consumed by downstream orchestration.  
**Plans**: 2 plans

Plans:
- [x] 02-01: design the preset schema and default preset files
- [x] 02-02: implement preset loading, discovery, and preset-aware task submission

Calibration note:
- Presets are a Mindforge product-layer abstraction and should remain decoupled from OpenHands internals so downstream features can evolve without patching the upstream runtime.

### Phase 3: Agent Instantiation & Orchestration

**Goal**: Instantiate role-based agents from presets and orchestrate `code-engineering` as a serial flow.  
**Depends on**: Phase 2  
**Requirements**: [AGENT-01, AGENT-02, AGENT-03]  
**Success Criteria**:
1. `code-engineering` auto-instantiates project manager, backend, frontend, and reviewer roles.
2. Tasks execute through a deterministic serial orchestration flow.
3. The system returns structured stage summaries and final output.  
**Plans**: 2 plans

Plans:
- [x] 03-01: define role responsibilities and instantiation rules
- [x] 03-02: implement serial orchestration and stage result aggregation

Calibration note:
- The current serial orchestration is a valid MVP path, but future phases should converge toward OpenHands-style agent, state, action, and observation semantics instead of growing an unrelated local execution protocol.

### Phase 4: Repository Analysis & Context Injection

**Goal**: Add repository understanding for local development tasks.  
**Depends on**: Phase 3  
**Requirements**: [REPO-01, REPO-02, REPO-03]  
**Success Criteria**:
1. The system can produce a structured repository summary.
2. The system can identify key files, dependencies, config files, and likely entrypoints.
3. Repo context is injected into execution before orchestration.  
**Plans**: 2 plans

Plans:
- [x] 04-01: implement repository scanning and key-file detection
- [x] 04-02: inject `Repo Summary` into task and orchestration context

Calibration note:
- Repository analysis remains intentionally lightweight and should later merge into a broader workspace-context layer that can also host reusable skills and repository-specific instructions.

### Phase 5: Model Routing & Registry

**Goal**: Build the backend provider/model registry and routing engine.  
**Depends on**: Phase 4  
**Requirements**: [MODEL-01, MODEL-02, MODEL-03, REUSE-01, REUSE-02, REUSE-03]  
**Success Criteria**:
1. The system can store multiple providers and model definitions.
2. The system can resolve models by preset mode, task type, and agent role.
3. The system supports explicit model overrides plus priority-based defaults.  
**Plans**: 2 plans

Plans:
- [x] 05-01: design provider/model schemas, priority levels, and fallback strategy
- [x] 05-02: implement model registry APIs, routing service, and execution integration

OpenHands-first references for implementation:
- treat existing OpenHands runtime and agent abstractions as the upstream shape for execution-time model selection
- prefer adapting OpenHands-compatible configuration boundaries over inventing a second internal runtime contract

### Phase 6: Frontend Workspace Shell

**Goal**: Add a Codex-like application workspace for the main user interaction loop.  
**Depends on**: Phase 5  
**Requirements**: [UI-01, UI-02, UI-03, REUSE-01, REUSE-02, REUSE-03]  
**Success Criteria**:
1. The frontend provides a left sidebar with common navigation entries such as new task, session history, projects, presets, and settings.
2. The main workspace exposes a chat-style task composer with common controls such as preset selection, repository input, default coordinator model, and submit action.
3. The UI provides tabs or panels for final output, stage traces, repository summary, and task metadata.  
**Plans**: 2 plans

Plans:
- [x] 06-01: design and implement the app shell, sidebar navigation, and session/task history layout
- [x] 06-02: implement the chat workspace, common task controls, and execution/result panels

OpenHands-first references for implementation:
- reuse OpenHands workspace composition patterns from `frontend/src/components/features/conversation/`
- mirror proven chat/input organization from `frontend/src/components/features/chat/`
- borrow browser, terminal, and changes panel structure before designing custom panel systems

### Phase 7: Model Control Center & Rule Templates

**Goal**: Add a user-facing model control center and rule-template-driven dynamic model assignment.  
**Depends on**: Phase 6  
**Requirements**: [RULE-01, RULE-02, RULE-03, RULE-04, REUSE-01, REUSE-02, REUSE-03]  
**Success Criteria**:
1. Users can manage models from the frontend and set priority as `high`, `medium`, `low`, or `disabled`.
2. Users can create rule templates that map different agent responsibilities to different models.
3. The system uses a default coordinator model to analyze the task, select a matching rule template, and assign models to agents.
4. Scenario rules such as paper revision can map different models to content revision, style review, and content review.  
**Plans**: 2 plans

Plans:
- [x] 07-01: implement the frontend model control center and model priority management
- [x] 07-02: implement rule-template authoring, coordinator analysis, and dynamic agent-model assignment

OpenHands-first references for implementation:
- reuse upstream settings and model-selection UX patterns where possible instead of designing a parallel settings system first
- keep Mindforge-specific rule-template authoring as the custom layer on top of reused workspace and settings primitives

### Phase 8: Approval & History

**Goal**: Add approval checkpoints, execution logs, history, and result indexing.  
**Depends on**: Phase 7  
**Requirements**: [CTRL-01, CTRL-02, CTRL-03]  
**Success Criteria**:
1. High-risk actions trigger approval.
2. Approval records, task logs, and stage logs can be queried.
3. Users can browse task history and result artifacts.  
**Plans**: 2 plans

Plans:
- [x] 08-01: implement approval triggers and approval records
- [x] 08-02: implement execution log and history persistence

### Phase 9: GitHub Read-Only Context

**Goal**: Add GitHub repository, issue, and PR summaries as read-only context and improve result presentation.  
**Depends on**: Phase 8  
**Requirements**: [GH-01, GH-02, RESULT-01]  
**Success Criteria**:
1. Tasks can use GitHub metadata and issue/PR summaries as external context.
2. Result views show final output, stage summaries, and key execution signals.
3. Result and history pages are presentation-ready.  
**Plans**: 2 plans

Plans:
- [ ] 09-01: implement GitHub read-only context retrieval
- [ ] 09-02: improve result and history presentation

### Phase 10: Academic Paper Revision Mode

**Goal**: Complete the paper revision workflow with standards analysis, rewriting, reviewer loops, and journal-aware rule templates.  
**Depends on**: Phase 9  
**Requirements**: [PAPER-01, PAPER-02, PAPER-03, RULE-04, REUSE-01, REUSE-02, REUSE-03]  
**Success Criteria**:
1. `paper-revision` instantiates standards analysis, reviser, and reviewer agents.
2. Journal tasks can use guideline collection and representative paper-style summaries.
3. The workflow supports at least one complete cycle of review, revise, and re-review.
4. Paper revision can consume Phase 6 rule templates for role-to-model assignment.  
**Plans**: 2 plans

Plans:
- [ ] 10-01: define paper revision role contracts, journal-guideline collection, and IO structure
- [ ] 10-02: implement rewriting, reviewer loops, and final revision reports

OpenHands-first references for implementation:
- reuse the generic role, stage, and workspace-context mechanisms established in earlier reused subsystems
- build paper revision as a Mindforge-specific workflow on top of reused orchestration and settings foundations rather than introducing a separate framework

## Progress

**Execution Order:**  
Phases execute in numeric order: `1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10`

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. OpenHands Foundation | 3/3 | Complete | 2026-04-18 |
| 2. Preset Template Center | 2/2 | Complete | 2026-04-18 |
| 3. Agent Instantiation & Orchestration | 2/2 | Complete | 2026-04-18 |
| 4. Repository Analysis & Context Injection | 2/2 | Complete | 2026-04-19 |
| 5. Model Routing & Registry | 2/2 | Complete | 2026-04-19 |
| 6. Frontend Workspace Shell | 2/2 | Complete | 2026-04-19 |
| 7. Model Control Center & Rule Templates | 2/2 | Complete | 2026-04-19 |
| 8. Approval & History | 2/2 | Complete | 2026-04-19 |
| 9. GitHub Read-Only Context | 0/2 | Not started | - |
| 10. Academic Paper Revision Mode | 0/2 | Not started | - |
