# Requirements: Mindforge

**Defined:** 2026-04-18  
**Last updated:** 2026-04-19

## v1 Requirements

### Foundation

- [x] **FOUND-01**: The user can start a local service and submit tasks.
- [x] **FOUND-02**: The system forwards baseline task execution through a unified adapter boundary to OpenHands.
- [x] **FOUND-03**: The backend exposes a FastAPI entrypoint with normalized request and response contracts.
- [x] **FOUND-04**: The system records minimal task logs and execution summaries.

### Preset Templates

- [x] **PRESET-01**: The user can choose preset modes including code engineering, code review, document organization, and paper revision.
- [x] **PRESET-02**: The system loads preset configuration from `preset_mode`.
- [x] **PRESET-03**: Presets include at least `preset_mode`, `agent_roles`, `execution_flow`, `default_models`, `requires_repo_analysis`, and `requires_approval`.

### Agent Collaboration

- [x] **AGENT-01**: In `code-engineering`, the system auto-instantiates project manager, backend, frontend, and reviewer roles.
- [x] **AGENT-02**: The system supports a serial role-based flow of planning, implementation, and review.
- [x] **AGENT-03**: The system returns structured stage results and an aggregate final output.

### Repository Context

- [x] **REPO-01**: The system can analyze a local repository structure.
- [x] **REPO-02**: The system can identify important files such as `README`, dependency files, config files, Docker files, and entrypoints.
- [x] **REPO-03**: The system can generate and inject a structured repository summary.

### Backend Model Routing

- [x] **MODEL-01**: The system can maintain multiple provider and model definitions.
- [x] **MODEL-02**: The system can route model selection by task type, preset mode, and agent role.
- [x] **MODEL-03**: The system supports default models, explicit overrides, and priority levels.

### OpenHands Reuse Strategy

- [x] **REUSE-01**: For major new subsystems, the implementation plan identifies preferred OpenHands reference modules before new Mindforge code is introduced.
- [x] **REUSE-02**: The project reuses or adapts MIT-licensed OpenHands patterns for frontend workspace structure, runtime-oriented tools, skill/instruction loading, or agent abstractions where that is cheaper and clearer than a greenfield rewrite.
- [x] **REUSE-03**: The project does not copy `enterprise/`-scoped OpenHands code or adopt unnecessary cloud or multi-tenant complexity into the prototype.

### Frontend Workspace

- [x] **UI-01**: The frontend provides a Codex-like app shell with a left sidebar for new task, history, projects, presets, and settings entrypoints.
- [x] **UI-02**: The main workspace provides a chat-style task composer with common controls such as preset selection, repository input, default coordinator model, and submit action.
- [x] **UI-03**: The frontend provides execution/result panels for final output, stage traces, repository summary, and task metadata.

### Model Control Center And Rule Templates

- [x] **RULE-01**: The frontend lets the user manage available models and set model priority as `high`, `medium`, `low`, or `disabled`.
- [x] **RULE-02**: The frontend lets the user author rule templates that assign different responsibilities or agent roles to different models.
- [x] **RULE-03**: The system supports a default coordinator model that first analyzes the task, then selects a rule template, then assigns models to agents automatically.
- [x] **RULE-04**: The system supports per-scenario rules such as paper revision where different models can be assigned to content revision, style review, and content review.

### Control And History

- [x] **CTRL-01**: The system triggers approval for high-risk actions.
- [x] **CTRL-02**: The system records approval decisions, task-level logs, and stage-level logs.
- [x] **CTRL-03**: The system supports viewing task history, approval records, and result artifacts.

### External Context And Results

- [ ] **GH-01**: The system can read GitHub repository metadata.
- [ ] **GH-02**: The system can read issue and pull request summaries as context.
- [ ] **RESULT-01**: The system presents final results, stage summaries, key metadata, and execution logs.

## v2 Requirements

### Advanced Collaboration

- [ ] **ADV-01**: The system supports parallel multi-agent orchestration.
- [ ] **ADV-02**: The system supports worktree-isolated execution.
- [ ] **ADV-03**: The system supports long-term memory and cross-project knowledge reuse.

### Academic Paper Revision

- [ ] **PAPER-01**: In `paper-revision`, the system instantiates standards analysis, reviser, and reviewer agents.
- [ ] **PAPER-02**: For journal tasks, the system can collect journal submission guidelines and summarize style patterns from relevant papers.
- [ ] **PAPER-03**: The system supports at least one full revision loop of review, revise, and re-review.

### Skills And Repository Instructions

- [ ] **SKILL-01**: The system supports a directory for reusable, shareable skill content that captures domain knowledge and workflow guidance.
- [ ] **SKILL-02**: The system supports repository-specific instructions that are auto-loaded for a given project, similar in spirit to OpenHands repo instructions.
- [ ] **SKILL-03**: The system keeps executable runtime tools separate from prompt/instruction skills so architecture remains understandable.

## Out Of Scope

| Feature | Reason |
|---------|--------|
| Custom agent runtime | The roadmap is explicitly based on OpenHands reuse. |
| GitHub write operations | The current milestone stays read-only to reduce risk. |
| Full multi-tenant auth | Out of scope for the current prototype milestone. |
| Heavy browser automation | Deferred until the core orchestration path is stable. |
| Automatic paper submission | Paper mode assists revision only. |

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
| MODEL-01 | Phase 5 | Complete |
| MODEL-02 | Phase 5 | Complete |
| MODEL-03 | Phase 5 | Complete |
| REUSE-01 | Phase 5 / Phase 6 / future phases | Complete |
| REUSE-02 | Phase 5 / Phase 6 / Phase 7 / future phases | Complete |
| REUSE-03 | Phase 5 / future phases | Complete |
| UI-01 | Phase 6 | Complete |
| UI-02 | Phase 6 | Complete |
| UI-03 | Phase 6 / Phase 9 | Complete |
| RULE-01 | Phase 7 | Complete |
| RULE-02 | Phase 7 | Complete |
| RULE-03 | Phase 7 | Complete |
| RULE-04 | Phase 7 / Phase 10 | Complete |
| CTRL-01 | Phase 8 | Complete |
| CTRL-02 | Phase 8 | Complete |
| CTRL-03 | Phase 8 | Complete |
| GH-01 | Phase 9 | Pending |
| GH-02 | Phase 9 | Pending |
| RESULT-01 | Phase 9 | Pending |
| PAPER-01 | Phase 10 | Pending |
| PAPER-02 | Phase 10 | Pending |
| PAPER-03 | Phase 10 | Pending |
| SKILL-01 | Backlog / future phase | Pending |
| SKILL-02 | Backlog / future phase | Pending |
| SKILL-03 | Backlog / future phase | Pending |

**Coverage:**
- v1 requirements: 29 total
- v2 requirements: 9 total
- roadmap-mapped requirements: 32
- unmapped requirements: 6
