"""Adapter boundary for OpenHands-backed task execution."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import requests

from app.backend.core.config import Settings


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
        if mode == "http" and self.settings.openhands_base_url:
            return self._run_http(payload)
        return self._run_mock(payload)

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
