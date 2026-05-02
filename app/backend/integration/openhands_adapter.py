"""Adapter boundary for OpenHands-backed task execution."""

from dataclasses import dataclass
from datetime import UTC, datetime
import os
from typing import Any

import requests

from app.backend.core.config import Settings

OPENAI_COMPATIBLE_PROTOCOLS = {"openai", "openai-chat", "openai-compatible"}


@dataclass(slots=True)
class AdapterResult:
    """Normalized raw result returned by the adapter."""

    status: str
    output: str
    provider: str
    metadata: dict[str, Any]
    error_message: str | None = None


class OpenHandsAdapter:
    """Encapsulate all communication with the OpenHands runtime.

    Phase 1 deliberately keeps this boundary narrow: Mindforge owns the task API,
    presets, orchestration, and repository context, while this adapter owns the
    runtime handoff. The current HTTP contract is intentionally small and should
    converge toward a real OpenHands-compatible upstream contract over time
    instead of spawning a separate long-lived local runtime protocol.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run_task(self, payload: dict[str, Any]) -> AdapterResult:
        """Execute the task using the configured adapter mode."""
        mode = self.settings.openhands_mode.lower()
        if mode == "disabled":
            return AdapterResult(
                status="failed",
                output="OpenHands adapter is disabled by configuration.",
                provider="disabled",
                metadata={"mode": mode},
                error_message="Adapter disabled",
            )
        if mode in {"model-api", "model_api"}:
            return self._run_model_api(payload)
        if mode == "http":
            if self.settings.openhands_base_url:
                return self._run_http(payload)
            return AdapterResult(
                status="failed",
                output="OpenHands HTTP adapter requires OPENHANDS_BASE_URL.",
                provider="openhands-http",
                metadata={"mode": mode},
                error_message="OPENHANDS_BASE_URL is required when OPENHANDS_MODE=http.",
            )
        if mode == "mock":
            return self._run_mock(payload)
        return AdapterResult(
            status="failed",
            output="Unsupported OpenHands adapter mode.",
            provider="openhands-adapter",
            metadata={"mode": mode},
            error_message=(
                "OPENHANDS_MODE must be one of model-api, http, mock, or disabled."
            ),
        )

    def _run_http(self, payload: dict[str, Any]) -> AdapterResult:
        """Forward task payload to an HTTP endpoint when configured.

        This is currently a minimal upstream bridge. Later phases should evolve
        the request and response shape by aligning to the real OpenHands service
        contract rather than layering on Mindforge-only transport semantics.
        """
        try:
            response = requests.post(
                self.settings.openhands_base_url.rstrip("/") + "/tasks",
                json=payload,
                timeout=self.settings.openhands_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            return AdapterResult(
                status=body.get("status", "completed"),
                output=body.get("output", ""),
                provider="openhands-http",
                metadata={"upstream_status": response.status_code, "body": body},
            )
        except requests.RequestException as exc:
            return AdapterResult(
                status="failed",
                output="OpenHands HTTP adapter request failed.",
                provider="openhands-http",
                metadata={"mode": "http"},
                error_message=str(exc),
            )

    def _run_model_api(self, payload: dict[str, Any]) -> AdapterResult:
        """Execute a task through an OpenAI-compatible model provider endpoint."""
        from app.backend.services.model_loader import load_provider_secrets
        from app.backend.services.model_registry_service import get_model_registry_service

        provider_id = str(payload.get("provider_id") or "")
        model = str(payload.get("model") or "")
        prompt = str(payload.get("prompt") or "").strip()
        if not provider_id or not model:
            return AdapterResult(
                status="failed",
                output="Model API adapter requires a provider_id and model.",
                provider="model-api",
                metadata={"mode": "model-api", "provider_id": provider_id, "model": model},
                error_message="Missing provider_id or model.",
            )

        provider = get_model_registry_service().get_provider(provider_id)
        if provider is None or not provider.enabled:
            return AdapterResult(
                status="failed",
                output="Model API provider is not available.",
                provider="model-api",
                metadata={"mode": "model-api", "provider_id": provider_id, "model": model},
                error_message=f"Provider '{provider_id}' is not registered or enabled.",
            )
        if not provider.api_base_url:
            return AdapterResult(
                status="failed",
                output="Model API provider has no base URL configured.",
                provider=f"model-api:{provider_id}",
                metadata={"mode": "model-api", "provider_id": provider_id, "model": model},
                error_message=f"Provider '{provider_id}' has no api_base_url.",
            )

        protocol = str(provider.metadata.get("protocol", "openai")).lower()
        if protocol not in OPENAI_COMPATIBLE_PROTOCOLS:
            return AdapterResult(
                status="failed",
                output="Model API adapter currently supports OpenAI-compatible providers only.",
                provider=f"model-api:{provider_id}",
                metadata={
                    "mode": "model-api",
                    "provider_id": provider_id,
                    "model": model,
                    "protocol": protocol,
                },
                error_message=f"Unsupported provider protocol '{protocol}'.",
            )

        api_key_env = str(
            provider.metadata.get("api_key_env")
            or f"{provider_id.upper().replace('-', '_')}_API_KEY"
        )
        secrets = load_provider_secrets()
        api_key = secrets.api_keys.get(provider_id) or os.getenv(api_key_env)
        if not api_key:
            return AdapterResult(
                status="failed",
                output="Model API key is not configured.",
                provider=f"model-api:{provider_id}",
                metadata={
                    "mode": "model-api",
                    "provider_id": provider_id,
                    "model": model,
                    "api_key_env": api_key_env,
                },
                error_message=f"Environment variable '{api_key_env}' is required.",
            )

        endpoint_path = str(
            provider.metadata.get("chat_completions_path", "/chat/completions")
        )
        endpoint = provider.api_base_url.rstrip("/") + endpoint_path
        tool_flags = self._extract_tool_flags(payload)
        system_prompt = self._build_system_prompt(tool_flags)
        max_tokens = self.settings.model_api_max_tokens
        if tool_flags.get("deep_analysis") is True:
            max_tokens = min(max_tokens * 2, 4096)
        try:
            response = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": max_tokens,
                },
                timeout=self.settings.model_api_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            output = (
                body.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return AdapterResult(
                status="completed",
                output=output or "",
                provider=f"model-api:{provider_id}",
                metadata={
                    "mode": "model-api",
                    "provider_id": provider_id,
                    "model": model,
                    "endpoint": endpoint,
                    "upstream_status": response.status_code,
                    "usage": body.get("usage"),
                    "tool_flags_applied": tool_flags,
                    "max_tokens": max_tokens,
                },
            )
        except (KeyError, IndexError, ValueError, requests.RequestException) as exc:
            return AdapterResult(
                status="failed",
                output="Model API adapter request failed.",
                provider=f"model-api:{provider_id}",
                metadata={
                    "mode": "model-api",
                    "provider_id": provider_id,
                    "model": model,
                    "endpoint": endpoint,
                },
                error_message=str(exc),
            )

    @staticmethod
    def _extract_tool_flags(payload: dict[str, Any]) -> dict[str, bool]:
        """Extract capability flags from normalized task metadata."""
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            return {}
        raw_flags = metadata.get("tool_flags")
        if not isinstance(raw_flags, dict):
            return {}
        return {
            key: bool(raw_flags.get(key))
            for key in ("web_search", "deep_analysis", "code_execution", "canvas")
            if raw_flags.get(key) is not None
        }

    @staticmethod
    def _build_system_prompt(tool_flags: dict[str, bool]) -> str:
        """Build the model-system prompt from enabled Mindforge capabilities."""
        lines = [
            "You are a Mindforge execution agent.",
            "Return concise, structured, task-specific output.",
        ]
        if tool_flags.get("deep_analysis"):
            lines.append(
                "Deep analysis mode is enabled: reason through constraints, risks, alternatives, and validation steps before final recommendations."
            )
        if tool_flags.get("web_search"):
            lines.append(
                "Web search context may be included in the user message; cite or clearly attribute that context when using it. If search returns no_results, do not refuse or ask for clarification when the user request can be answered from runtime context or general reasoning."
            )
        if tool_flags.get("code_execution"):
            lines.append(
                "Code execution results may be included in the user message; use them as observed evidence, not guesses."
            )
        if tool_flags.get("canvas"):
            lines.append(
                "Canvas mode is enabled: format the answer as an editable artifact with clear headings and reusable structure."
            )
        return " ".join(lines)

    def _run_mock(self, payload: dict[str, Any]) -> AdapterResult:
        """Provide a deterministic local demo result for Phase 1."""
        prompt = payload.get("prompt", "").strip() or "No prompt provided."
        preset_mode = payload.get("preset_mode") or "default"
        repo_path = payload.get("repo_path") or "not-specified"
        model = payload.get("model") or "not-resolved"
        provider_id = payload.get("provider_id") or "not-resolved"
        metadata = payload.get("metadata", {}) or {}
        stage = metadata.get("orchestration_stage")
        role = metadata.get("orchestration_role")
        timestamp = datetime.now(UTC).isoformat()
        output = (
            "[mock-openhands]\n"
            f"received prompt: {prompt}\n"
            f"preset mode: {preset_mode}\n"
            f"repo path: {repo_path}\n"
            f"stage: {stage or 'single-pass'}\n"
            f"role: {role or 'coordinator'}\n"
            f"model: {model}\n"
            f"provider: {provider_id}\n"
            "OpenHands adapter executed through the configured boundary."
        )
        return AdapterResult(
            status="completed",
            output=output,
            provider="mock-openhands",
            metadata={
                "mode": "mock",
                "timestamp": timestamp,
                "stage": stage,
                "role": role,
                "model": model,
                "provider_id": provider_id,
            },
        )
