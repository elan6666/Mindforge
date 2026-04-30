# Project Overview

## Project Name

Mindforge

## Positioning

Mindforge is a multi-agent assistant platform for software development and academic paper revision. The system reuses OpenHands as the execution base and adds preset-driven orchestration, repository analysis, model routing, approval, history, and result presentation on top of it.

## Goals

1. Provide a unified task entrypoint and structured result output.
2. Support preset-driven multi-agent collaboration, with `code-engineering` as the primary delivery path.
3. Automatically instantiate role-based agents such as project manager, backend, frontend, and reviewer for software tasks.
4. Support paper revision workflows with standards analysis, rewriting, reviewer feedback, and iterative revision.
5. Support unified provider and model configuration, routing, and execution parameters.
6. Expose a user-facing model control center where users can manage available models, priorities, and enablement state.
7. Support rule templates that map responsibilities or agent roles to specific models.
8. Use a default coordinator model to analyze a user task, select a matching rule template, and assign different models to different agents.
9. Provide a Codex-like application workspace with sidebar navigation, chat-driven task entry, history, preset switching, and execution/result panels.
10. Support approval checkpoints, execution logs, history, and GitHub read-only context.
11. Learn selectively from OpenHands repository architecture, especially the separation between reusable skills, repository-specific instructions, runtime tools, and agent implementations.
12. Provide a Provider/API Management Center so users can safely configure model providers, env-var based credentials, connection checks, and provider status.

## Target Users

- Software developers
- Software engineering students
- Teams building prototype multi-agent developer tools
- Students and researchers who need paper revision and reviewer-style feedback

## Core Principles

- Reuse a mature runtime instead of rebuilding an agent core from scratch.
- Reuse proven OpenHands implementations where they fit, instead of inventing parallel local abstractions first.
- Keep presets and orchestration rules explicit and inspectable.
- Separate backend routing concerns from user-facing rule authoring concerns.
- Keep the primary path narrow first, then expand with specialized workflows.
- Make important execution decisions traceable and reviewable.
- Treat Codex and Claude Code as the execution-quality floor: real codebase understanding, multi-file edits, tests, explanations, and reviewable delivery.
- Treat OpenHands as the architecture reference for runtime boundaries, agent/action/observation concepts, skills, and repository instructions.
- Keep Mindforge's differentiation in controllable product orchestration: presets, rules, roles, provider/model routing, approvals, history, and paper/development modes.

## In Scope

- OpenHands integration and adapter boundary
- Selective code-level reuse of OpenHands MIT-licensed implementations for frontend shell, runtime-oriented tools, skill/instruction loading, and agent abstractions
- Preset-driven execution modes
- Role-based agent orchestration
- Repository analysis and context injection
- Unified provider and model routing
- Codex-like app workspace and interaction shell
- User-facing model control center
- Provider/API Management Center with non-secret provider overrides and connection tests
- Rule templates for assigning different models to different agents
- Reusable skill content and repository-specific instructions
- Approval, history, logs, and result views
- GitHub read-only context
- Paper revision mode

## Out of Scope

- Building a custom agent runtime from scratch
- GitHub write operations such as auto-PR creation
- Full multi-tenant permissions and enterprise auth
- Deep browser automation in the initial milestone
- Automatic paper submission or copyright handling flows

## MVP

The MVP remains centered on `code-engineering`:

1. Accept a user task and optional repository input.
2. Resolve a preset and execute a role-based orchestration flow.
3. Inject lightweight repository context before execution.
4. Return structured stage summaries, final output, and execution metadata.

Near-term planned expansion after the MVP:

1. Backend provider/model registry and routing.
2. A Codex-like app workspace with sidebar, chat composer, session history, task panels, and mode switching.
3. A user-facing model control center with priority settings: `high`, `medium`, `low`, `disabled`.
4. Rule templates such as paper revision, where different responsibilities map to different models.
5. Coordinator-driven task analysis that selects a rule template and assigns models to agents automatically.
6. A lightweight skills/instructions system inspired by OpenHands, without copying its full legacy/V1 layering.
7. Phase-specific implementation guidance that points developers to preferred OpenHands reference areas before new code is introduced.

## Technology Baseline

- Runtime base: `OpenHands`
- Backend: `Python + FastAPI`
- Frontend: `React + TypeScript`
- Storage: `SQLite`
- Repository analysis: `GitPython`
- Visualization: `Mermaid / ECharts`
- External read-only context: `GitHub`

## Success Criteria

### Product

- A user can complete an end-to-end `code-engineering` task.
- The system returns structured stage outputs and metadata.
- The system can maintain multiple model definitions and route execution to the expected model.
- The system can configure provider connection metadata and verify credential status without exposing API keys.
- The system exposes a coherent frontend workspace for chat, task launch, history, and result inspection.
- A user can manage model priorities and author rule templates from the frontend.
- A user can define a scenario such as paper revision and map different responsibilities to different models.
- The project has a clear home for reusable skills and repository-specific instructions.
- Developers can point to explicit OpenHands reference implementations for major new subsystems instead of describing them as greenfield rewrites.

### Delivery

- Documents, architecture, and implementation stay aligned.
- Each phase has a clear boundary and measurable success criteria.
- The project remains demonstrable and incrementally extensible.

## Current Status

- Phase 1 complete: local FastAPI service, normalized task API, and an OpenHands adapter boundary; real upstream runtime integration is still pending.
- Phase 2 complete: YAML-backed preset center and preset discovery API.
- Phase 3 complete: serial role orchestration for `code-engineering`, currently implemented as a Mindforge-side MVP flow that may later align more closely with OpenHands agent semantics.
- Phase 4 complete: local repository analysis and context injection, currently kept intentionally lightweight so it can later merge into a broader workspace-context and instructions system.
- Phase 5 complete: backend provider/model registry, routing rules, explicit overrides, and execution-time model selection.
- Phase 6 complete: a runnable React + Vite workspace shell now provides sidebar navigation, chat-style task launch, session history, and result panels backed by the existing APIs.
- Phase 7 complete: the frontend now exposes a model control center and rule-template editor, and the backend records coordinator-driven template selection plus effective role-model assignment.
- Phase 8 complete: blocking approvals, SQLite-backed task/stage history, approval APIs, and frontend history/approval views are now in place.
- Phase 9 complete: GitHub read-only repository/issue/PR context is now available through task metadata, dedicated APIs, and frontend result/history views.
- Phase 10 complete: academic paper revision now runs standards analysis, revision, style review, content review, iteration, and final re-review with journal/reference context support.
- Phase 11 complete: Provider/API Management Center now exposes provider overrides, API key env-var status, and sanitized connection testing.
- The current milestone is feature-complete and ready for audit, hardening, or next-milestone planning.
- Skills architecture is currently planned as a selective follow-up capability rather than a prerequisite for Phase 5.
- Future implementation phases should treat OpenHands as the default reference source for reusable MIT-licensed patterns before introducing Mindforge-specific replacements.
