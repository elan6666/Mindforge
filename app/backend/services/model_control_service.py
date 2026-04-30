"""User-editable model control service for Phase 7."""

from functools import lru_cache
import os

import requests

OPENAI_COMPATIBLE_PROTOCOLS = {"openai", "openai-chat", "openai-compatible"}
SUPPORTED_PROVIDER_PROTOCOLS = OPENAI_COMPATIBLE_PROTOCOLS | {"anthropic"}

from app.backend.schemas.model import (
    ModelControlUpdate,
    ProviderConnectionTestResult,
    ProviderControlUpdate,
    ModelOverrideEntry,
    ModelSummary,
    ModelOverridesDocument,
    ProviderOverrideEntry,
    ProviderOverridesDocument,
    ProviderSummary,
)
from app.backend.services.model_loader import (
    load_model_catalog,
    load_model_overrides,
    load_provider_overrides,
    save_model_overrides,
    save_provider_overrides,
)
from app.backend.services.model_registry_service import (
    clear_model_registry_service_cache,
    get_model_registry_service,
)


class ModelControlError(ValueError):
    """Raised when a model control mutation is invalid."""


class ModelControlService:
    """Persist mutable model state without editing the seed catalog."""

    def list_models(self) -> list[ModelSummary]:
        """Return the currently effective model list."""
        return get_model_registry_service().list_models()

    def list_providers(self) -> list[ProviderSummary]:
        """Return the currently effective editable provider list."""
        return get_model_registry_service().list_providers()

    def update_model(
        self,
        model_id: str,
        payload: ModelControlUpdate,
    ) -> ModelSummary:
        """Persist editable fields for one model and return the merged view."""
        seed_catalog = load_model_catalog()
        if not any(model.model_id == model_id for model in seed_catalog.models):
            raise ModelControlError(f"Unknown model '{model_id}'.")

        overrides = load_model_overrides()
        entry = overrides.models.get(model_id, ModelOverrideEntry())
        if payload.priority is not None:
            entry.priority = payload.priority
        if payload.enabled is not None:
            entry.enabled = payload.enabled
        overrides.models[model_id] = entry
        save_model_overrides(overrides)
        self._clear_related_caches()

        updated = next(
            (item for item in self.list_models() if item.model_id == model_id),
            None,
        )
        if updated is None:
            raise ModelControlError(f"Updated model '{model_id}' could not be loaded.")
        return updated

    def update_provider(
        self,
        provider_id: str,
        payload: ProviderControlUpdate,
    ) -> ProviderSummary:
        """Persist editable fields for one provider and return the merged view."""
        seed_catalog = load_model_catalog()
        if not any(provider.provider_id == provider_id for provider in seed_catalog.providers):
            raise ModelControlError(f"Unknown provider '{provider_id}'.")

        overrides = load_provider_overrides()
        entry = overrides.providers.get(provider_id, ProviderOverrideEntry())
        fields_set = payload.model_fields_set

        if "enabled" in fields_set:
            entry.enabled = payload.enabled
        if "api_base_url" in fields_set:
            entry.api_base_url = self._normalize_optional_url(payload.api_base_url)
        if "api_key_env" in fields_set:
            entry.api_key_env = self._normalize_optional_string(payload.api_key_env)
        if "protocol" in fields_set:
            protocol = self._normalize_optional_string(payload.protocol)
            if protocol and protocol.lower() not in SUPPORTED_PROVIDER_PROTOCOLS:
                raise ModelControlError(
                    f"Unsupported provider protocol '{payload.protocol}'. "
                    f"Supported protocols: {', '.join(sorted(SUPPORTED_PROVIDER_PROTOCOLS))}."
                )
            entry.protocol = protocol.lower() if protocol else None
        if "anthropic_api_base_url" in fields_set:
            entry.anthropic_api_base_url = self._normalize_optional_url(
                payload.anthropic_api_base_url
            )

        if entry.model_dump(exclude_none=True):
            overrides.providers[provider_id] = entry
        else:
            overrides.providers.pop(provider_id, None)
        save_provider_overrides(overrides)
        self._clear_related_caches()

        updated = get_model_registry_service().get_provider_summary(provider_id)
        if updated is None:
            raise ModelControlError(f"Updated provider '{provider_id}' could not be loaded.")
        return updated

    def test_provider_connection(
        self,
        provider_id: str,
    ) -> ProviderConnectionTestResult:
        """Check whether a provider has usable local API settings."""
        registry = get_model_registry_service()
        provider = registry.get_provider(provider_id)
        summary = registry.get_provider_summary(provider_id)
        if provider is None or summary is None:
            raise ModelControlError(f"Unknown provider '{provider_id}'.")

        if not summary.enabled:
            return self._provider_test_result(
                summary,
                ok=False,
                status="disabled",
                detail="Provider is disabled.",
            )
        if not summary.api_base_url:
            return self._provider_test_result(
                summary,
                ok=False,
                status="missing_api_base_url",
                detail="Provider api_base_url is not configured.",
            )
        if not summary.api_key_env:
            return self._provider_test_result(
                summary,
                ok=False,
                status="missing_api_key_env",
                detail="Provider api_key_env is not configured.",
            )

        api_key = os.getenv(summary.api_key_env)
        if not api_key:
            return self._provider_test_result(
                summary,
                ok=False,
                status="missing_api_key",
                detail=f"Environment variable '{summary.api_key_env}' is not set.",
            )

        if summary.protocol not in OPENAI_COMPATIBLE_PROTOCOLS:
            return self._provider_test_result(
                summary,
                ok=False,
                status="unsupported_protocol",
                detail=f"Connection test does not support protocol '{summary.protocol}'.",
            )

        endpoint = summary.api_base_url.rstrip("/") + "/models"
        try:
            response = requests.get(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
        except requests.RequestException as exc:
            return self._provider_test_result(
                summary,
                ok=False,
                status="request_failed",
                detail=str(exc),
            )

        ok = 200 <= response.status_code < 400
        return self._provider_test_result(
            summary,
            ok=ok,
            status="connected" if ok else "http_error",
            detail=(
                "Provider connection test succeeded."
                if ok
                else f"Provider returned HTTP {response.status_code}."
            ),
            upstream_status=response.status_code,
        )

    def get_overrides_document(self) -> ModelOverridesDocument:
        """Expose the raw overrides document for debugging or future UI use."""
        return load_model_overrides()

    def get_provider_overrides_document(self) -> ProviderOverridesDocument:
        """Expose the raw provider overrides document for debugging or future UI use."""
        return load_provider_overrides()

    @staticmethod
    def _normalize_optional_string(value: str | None) -> str | None:
        """Normalize empty editable strings to no override."""
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @classmethod
    def _normalize_optional_url(cls, value: str | None) -> str | None:
        """Normalize and validate optional provider URLs."""
        normalized = cls._normalize_optional_string(value)
        if normalized is None:
            return None
        if not normalized.startswith(("http://", "https://")):
            raise ModelControlError("Provider URLs must start with http:// or https://.")
        return normalized

    @staticmethod
    def _provider_test_result(
        summary: ProviderSummary,
        *,
        ok: bool,
        status: str,
        detail: str,
        upstream_status: int | None = None,
    ) -> ProviderConnectionTestResult:
        """Build a sanitized provider connection result."""
        return ProviderConnectionTestResult(
            provider_id=summary.provider_id,
            ok=ok,
            status=status,
            detail=detail,
            protocol=summary.protocol,
            api_base_url=summary.api_base_url,
            api_key_env=summary.api_key_env,
            api_key_configured=summary.api_key_configured,
            upstream_status=upstream_status,
        )

    @staticmethod
    def _clear_related_caches() -> None:
        """Reset all cached services affected by model-state changes."""
        from app.backend.services.coordinator_selection_service import (
            clear_coordinator_selection_service_cache,
        )
        from app.backend.services.model_routing_service import (
            clear_model_routing_service_cache,
        )
        from app.backend.services.task_service import clear_task_service_cache

        clear_model_registry_service_cache()
        clear_model_routing_service_cache()
        clear_coordinator_selection_service_cache()
        clear_task_service_cache()


@lru_cache(maxsize=1)
def get_model_control_service() -> ModelControlService:
    """Return a cached model control service."""
    return ModelControlService()
