---
phase: 11-provider-api-management-center
researched: 2026-04-30
status: research
owner_role: product-competitive-research
---

# Phase 11 Research: Provider API Management Center

## 1. Strategic Baselines

Mindforge should use Codex, Claude Code, and OpenHands as benchmark constraints, not as feature-copy targets.

| Reference | Role for Mindforge | Practical bar |
| --- | --- | --- |
| Codex | Engineering execution baseline | Can inspect a codebase, edit multiple files, run tests, explain results, and hand back reviewable changes. |
| Claude Code | Terminal/IDE execution baseline | Can work inside the developer environment, understand repo context, run commands, and deliver committed code. |
| OpenHands | Architecture reference | Runtime, agent/action/observation concepts, skills, repo instructions, and sandbox/runtime separation. |
| Mindforge | Product orchestration layer | Presets, multi-agent roles, multi-provider routing, rule templates, approvals, history, and paper/development modes. |

This means Phase 11 should not become a generic API-key form. It should be the provider-control layer that makes future Codex/Claude-style execution trustworthy: providers are visible, testable, configurable, and safe.

## 2. Reference Projects

| Project | Source | Relevant ideas | What Mindforge should adopt |
| --- | --- | --- | --- |
| OpenHands | https://github.com/OpenHands/OpenHands, https://docs.openhands.dev/ | LLM settings, runtime separation, skills/microagents, OpenAI-compatible provider setup. | Keep adapter/runtime boundaries clear; avoid scattering provider credentials across task requests. |
| LiteLLM | https://github.com/BerriAI/litellm, https://docs.litellm.ai/ | Multi-provider gateway, virtual keys, fallback, budgets, rate limits, observability callbacks. | Borrow the concepts of provider health, fallback, usage tracking, and budget fields, but do not implement a full proxy in this phase. |
| Open WebUI | https://github.com/open-webui/open-webui, https://docs.openwebui.com/ | Admin connection settings, OpenAI-compatible base URLs, API key configuration, model discovery/allowlist, RBAC. | Build a clear Provider/API management UI with connection status and model allowlist as future work. |
| Dify | https://github.com/langgenius/dify, https://docs.dify.ai/ | Workspace-level model provider credentials, custom providers, model testing, logs, team roles. | Separate provider credentials/config from model entries and expose status in the UI. |
| LLM-Rosetta | https://github.com/Oaklight/llm-rosetta | Cross-provider protocol translation through a common intermediate representation. | Keep `protocol` and future `capabilities` fields so Mindforge can later support OpenAI Responses, Anthropic Messages, Gemini, and tool-call translation. |
| Portkey AI Gateway | https://github.com/Portkey-AI/gateway, https://portkey.ai/docs/product/ai-gateway | Routing, retries, fallbacks, budgets, caching, guardrails, gateway observability. | Reserve reliability and budget hooks for later phases; Phase 11 should only expose safe provider config and connection checks. |
| Helicone | https://github.com/helicone/helicone, https://docs.helicone.ai/ | LLM observability, request traces, cost/latency/error dashboards. | Add provider/model/stage metadata now so future observability can be added without rewriting history records. |

## 3. Feature Matrix

| Capability | Competitive pattern | Phase 11 decision |
| --- | --- | --- |
| Provider/API key configuration | OpenHands, Open WebUI, and Dify put provider URL, model, and key references in settings. | Add Provider/API Management Center with non-secret provider overrides. |
| Secret handling | Mature tools avoid showing secrets after save and separate credentials from normal config. | Store only env var names and key configured status; never store or return actual key values. |
| OpenAI-compatible support | Open WebUI, Dify, LiteLLM, and many gateways treat OpenAI-compatible APIs as the lowest-cost integration path. | Make OpenAI-compatible protocol first-class via `openai`, `openai-chat`, or `openai-compatible`. |
| Anthropic-compatible support | Claude-native tools and providers need a separate endpoint/protocol shape. | Keep `anthropic_api_base_url` and `anthropic` protocol metadata, but do not implement the runtime adapter yet. |
| Connection test | Open WebUI and Dify validate credentials before users rely on a provider. | Add `/api/control/providers/{provider_id}/test`, returning status-only success/failure. |
| Model discovery | Open WebUI can discover `/models` and supports manual model IDs when discovery fails. | Defer model discovery/allowlist to backlog; do provider-level tests now. |
| Fallback | LiteLLM/Portkey support retries, load balancing, circuit breakers, and budget-aware fallback. | Keep current routing priority model; add provider enabled/disabled and health-test data as the next step. |
| Usage and audit | Dify, LiteLLM, and Helicone surface logs, token usage, latency, and errors. | Continue task/stage history; reserve provider call metrics and audit events for a follow-up phase. |
| Team permissions | Dify/Open WebUI use workspace roles/RBAC. | Defer RBAC. Mindforge remains local-first/single-user for this milestone. |

## 4. Phase 11 MVP Scope

Phase 11 should ship:

- Editable provider state through backend APIs.
- Frontend Provider/API Management panel.
- Non-secret provider overrides layered on top of `catalog.yaml`.
- `api_key_env` and derived `api_key_configured` status.
- Connection testing for OpenAI-compatible providers.
- Protocol and URL validation.
- Tests proving secrets are not returned or persisted.
- Documentation that frames Codex/Claude/OpenHands as benchmark constraints.

## 5. Backlog

- Model discovery from `/models` plus manual allowlist.
- Per-provider and per-model health status stored over time.
- Retry/fallback policies with cooldowns.
- Token/cost/latency dashboards.
- Provider configuration audit events.
- Local ignored secret store or OS keychain integration.
- Native Anthropic Messages, OpenAI Responses, Gemini, and cross-protocol translation.
- Team roles and provider-level permissions.

## 6. Sources

- OpenHands: https://github.com/OpenHands/OpenHands
- OpenHands LLM settings: https://docs.openhands.dev/openhands/usage/settings/llm-settings
- OpenAI Codex docs: https://platform.openai.com/docs/codex
- OpenAI Codex introduction: https://openai.com/index/introducing-codex/
- Claude Code product page: https://www.anthropic.com/claude-code
- Claude Code settings: https://docs.anthropic.com/en/docs/claude-code/settings
- LiteLLM: https://github.com/BerriAI/litellm
- LiteLLM docs: https://docs.litellm.ai/
- Open WebUI: https://github.com/open-webui/open-webui
- Open WebUI provider connections: https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/
- Dify: https://github.com/langgenius/dify
- Dify model providers: https://docs.dify.ai/en/use-dify/workspace/model-providers
- LLM-Rosetta: https://github.com/Oaklight/llm-rosetta
- Portkey AI Gateway: https://github.com/Portkey-AI/gateway
- Helicone: https://github.com/helicone/helicone
