"""User-editable model control service for Phase 7."""

from functools import lru_cache
import os

import requests

OPENAI_COMPATIBLE_PROTOCOLS = {"openai", "openai-chat", "openai-compatible"}
SUPPORTED_PROVIDER_PROTOCOLS = OPENAI_COMPATIBLE_PROTOCOLS | {"anthropic"}

from app.backend.schemas.model import (
    ModelCreateRequest,
    ModelControlUpdate,
    ModelDefinition,
    ProviderConnectionTestResult,
    ProviderCreateRequest,
    ProviderControlUpdate,
    ProviderDefinition,
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
    load_provider_secrets,
    load_provider_overrides,
    save_provider_secrets,
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

    def list_custom_models(self) -> list[ModelSummary]:
        """Return user-created models only for the control center."""
        return [
            model for model in get_model_registry_service().list_models()
            if model.is_custom
        ]

    def list_providers(self) -> list[ProviderSummary]:
        """Return the currently effective editable provider list."""
        return get_model_registry_service().list_providers()

    def list_custom_providers(self) -> list[ProviderSummary]:
        """Return user-created providers only for the API management UI."""
        return [
            provider for provider in get_model_registry_service().list_providers()
            if provider.is_custom
        ]

    def create_model(self, payload: ModelCreateRequest) -> ModelSummary:
        """Create a user-managed model definition."""
        model_id = self._normalize_required_string(payload.model_id, "model_id")
        overrides = load_model_overrides()
        registry = get_model_registry_service()
        if registry.get_model(model_id) is not None or model_id in overrides.custom_models:
            raise ModelControlError(f"Model '{model_id}' already exists.")
        if registry.get_provider(payload.provider_id) is None:
            raise ModelControlError(f"Unknown provider '{payload.provider_id}'.")

        model = ModelDefinition(
            model_id=model_id,
            display_name=self._normalize_required_string(
                payload.display_name,
                "display_name",
            ),
            provider_id=self._normalize_required_string(payload.provider_id, "provider_id"),
            upstream_model=self._normalize_required_string(
                payload.upstream_model,
                "upstream_model",
            ),
            priority=payload.priority,
            enabled=payload.enabled,
            supported_preset_modes=self._clean_string_list(payload.supported_preset_modes),
            supported_task_types=self._clean_string_list(payload.supported_task_types),
            supported_roles=self._clean_string_list(payload.supported_roles),
        )
        overrides.custom_models[model.model_id] = model
        save_model_overrides(overrides)
        self._clear_related_caches()
        created = get_model_registry_service().get_model(model.model_id)
        if created is None:
            raise ModelControlError(f"Created model '{model.model_id}' could not be loaded.")
        return next(
            item for item in get_model_registry_service().list_models()
            if item.model_id == model.model_id
        )

    def create_provider(self, payload: ProviderCreateRequest) -> ProviderSummary:
        """Create a user-managed provider definition."""
        provider_id = self._normalize_required_string(payload.provider_id, "provider_id")
        overrides = load_provider_overrides()
        registry = get_model_registry_service()
        if registry.get_provider(provider_id) is not None or provider_id in overrides.custom_providers:
            raise ModelControlError(f"Provider '{provider_id}' already exists.")

        protocol = self._validate_protocol(payload.protocol)
        metadata: dict[str, str] = {"protocol": protocol}
        api_key_env = self._normalize_optional_string(payload.api_key_env)
        if api_key_env:
            metadata["api_key_env"] = api_key_env
        anthropic_url = self._normalize_optional_url(payload.anthropic_api_base_url)
        if anthropic_url:
            metadata["anthropic_api_base_url"] = anthropic_url

        provider = ProviderDefinition(
            provider_id=provider_id,
            display_name=self._normalize_required_string(
                payload.display_name,
                "display_name",
            ),
            description=self._normalize_optional_string(payload.description) or "用户自定义模型服务商",
            enabled=payload.enabled,
            api_base_url=self._normalize_optional_url(payload.api_base_url),
            metadata=metadata,
        )
        overrides.custom_providers[provider.provider_id] = provider
        save_provider_overrides(overrides)
        self._persist_api_key(provider.provider_id, payload.api_key, clear_if_blank=False)
        self._clear_related_caches()
        created = get_model_registry_service().get_provider_summary(provider.provider_id)
        if created is None:
            raise ModelControlError(
                f"Created provider '{provider.provider_id}' could not be loaded."
            )
        return created

    def update_model(
        self,
        model_id: str,
        payload: ModelControlUpdate,
    ) -> ModelSummary:
        """Persist editable fields for one model and return the merged view."""
        seed_catalog = load_model_catalog()
        overrides = load_model_overrides()
        is_seed_model = any(model.model_id == model_id for model in seed_catalog.models)
        is_custom_model = model_id in overrides.custom_models
        if not is_seed_model and not is_custom_model:
            raise ModelControlError(f"Unknown model '{model_id}'.")

        if is_custom_model:
            custom_model = overrides.custom_models[model_id]
            update_payload: dict[str, object] = {}
            if payload.display_name is not None:
                update_payload["display_name"] = self._normalize_required_string(
                    payload.display_name,
                    "display_name",
                )
            if payload.provider_id is not None:
                if get_model_registry_service().get_provider(payload.provider_id) is None:
                    raise ModelControlError(f"Unknown provider '{payload.provider_id}'.")
                update_payload["provider_id"] = self._normalize_required_string(
                    payload.provider_id,
                    "provider_id",
                )
            if payload.upstream_model is not None:
                update_payload["upstream_model"] = self._normalize_required_string(
                    payload.upstream_model,
                    "upstream_model",
                )
            if payload.priority is not None:
                update_payload["priority"] = payload.priority
            if payload.enabled is not None:
                update_payload["enabled"] = payload.enabled
            if payload.supported_preset_modes is not None:
                update_payload["supported_preset_modes"] = self._clean_string_list(
                    payload.supported_preset_modes,
                )
            if payload.supported_task_types is not None:
                update_payload["supported_task_types"] = self._clean_string_list(
                    payload.supported_task_types,
                )
            if payload.supported_roles is not None:
                update_payload["supported_roles"] = self._clean_string_list(
                    payload.supported_roles,
                )
            overrides.custom_models[model_id] = custom_model.model_copy(
                update=update_payload,
            )
        else:
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
        overrides = load_provider_overrides()
        is_seed_provider = any(
            provider.provider_id == provider_id for provider in seed_catalog.providers
        )
        is_custom_provider = provider_id in overrides.custom_providers
        if not is_seed_provider and not is_custom_provider:
            raise ModelControlError(f"Unknown provider '{provider_id}'.")

        entry = overrides.providers.get(provider_id, ProviderOverrideEntry())
        fields_set = payload.model_fields_set

        if is_custom_provider:
            custom_provider = overrides.custom_providers[provider_id]
            provider_update: dict[str, object] = {}
            metadata = dict(custom_provider.metadata)

            if "display_name" in fields_set:
                provider_update["display_name"] = self._normalize_required_string(
                    payload.display_name,
                    "display_name",
                )
            if "description" in fields_set:
                provider_update["description"] = (
                    self._normalize_optional_string(payload.description)
                    or "用户自定义模型服务商"
                )
            if "enabled" in fields_set:
                provider_update["enabled"] = payload.enabled
            if "api_base_url" in fields_set:
                provider_update["api_base_url"] = self._normalize_optional_url(
                    payload.api_base_url,
                )
            if "api_key_env" in fields_set:
                api_key_env = self._normalize_optional_string(payload.api_key_env)
                if api_key_env:
                    metadata["api_key_env"] = api_key_env
                else:
                    metadata.pop("api_key_env", None)
            if "protocol" in fields_set:
                protocol = self._normalize_optional_string(payload.protocol)
                if protocol:
                    metadata["protocol"] = self._validate_protocol(protocol)
                else:
                    metadata.pop("protocol", None)
            if "anthropic_api_base_url" in fields_set:
                anthropic_url = self._normalize_optional_url(
                    payload.anthropic_api_base_url,
                )
                if anthropic_url:
                    metadata["anthropic_api_base_url"] = anthropic_url
                else:
                    metadata.pop("anthropic_api_base_url", None)
            provider_update["metadata"] = metadata
            overrides.custom_providers[provider_id] = custom_provider.model_copy(
                update=provider_update,
            )
        else:
            if "enabled" in fields_set:
                entry.enabled = payload.enabled
            if "api_base_url" in fields_set:
                entry.api_base_url = self._normalize_optional_url(payload.api_base_url)
            if "api_key_env" in fields_set:
                entry.api_key_env = self._normalize_optional_string(payload.api_key_env)
            if "protocol" in fields_set:
                protocol = self._normalize_optional_string(payload.protocol)
                if protocol:
                    entry.protocol = self._validate_protocol(protocol)
                else:
                    entry.protocol = None
            if "anthropic_api_base_url" in fields_set:
                entry.anthropic_api_base_url = self._normalize_optional_url(
                    payload.anthropic_api_base_url
                )

            if entry.model_dump(exclude_none=True):
                overrides.providers[provider_id] = entry
            else:
                overrides.providers.pop(provider_id, None)

        if "api_key" in fields_set:
            self._persist_api_key(provider_id, payload.api_key, clear_if_blank=True)

        save_provider_overrides(overrides)
        self._clear_related_caches()

        updated = get_model_registry_service().get_provider_summary(provider_id)
        if updated is None:
            raise ModelControlError(f"Updated provider '{provider_id}' could not be loaded.")
        return updated

    def delete_model(self, model_id: str) -> None:
        """Delete a user-managed model definition."""
        overrides = load_model_overrides()
        if model_id not in overrides.custom_models:
            raise ModelControlError(f"Model '{model_id}' is not a user-created model.")
        overrides.custom_models.pop(model_id, None)
        overrides.models.pop(model_id, None)
        save_model_overrides(overrides)
        self._clear_related_caches()

    def delete_provider(self, provider_id: str) -> None:
        """Delete a user-managed provider and its user-created models."""
        provider_overrides = load_provider_overrides()
        if provider_id not in provider_overrides.custom_providers:
            raise ModelControlError(
                f"Provider '{provider_id}' is not a user-created provider."
            )
        provider_overrides.custom_providers.pop(provider_id, None)
        provider_overrides.providers.pop(provider_id, None)
        save_provider_overrides(provider_overrides)

        model_overrides = load_model_overrides()
        removed_model_ids = {
            model_id
            for model_id, model in model_overrides.custom_models.items()
            if model.provider_id == provider_id
        }
        model_overrides.custom_models = {
            model_id: model
            for model_id, model in model_overrides.custom_models.items()
            if model_id not in removed_model_ids
        }
        model_overrides.models = {
            model_id: override
            for model_id, override in model_overrides.models.items()
            if model_id not in removed_model_ids
        }
        save_model_overrides(model_overrides)

        secrets = load_provider_secrets()
        secrets.api_keys.pop(provider_id, None)
        save_provider_secrets(secrets)
        self._clear_related_caches()

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

        secrets = load_provider_secrets()
        api_key = secrets.api_keys.get(provider_id)
        if not api_key and summary.api_key_env:
            api_key = os.getenv(summary.api_key_env)
        if not api_key:
            return self._provider_test_result(
                summary,
                ok=False,
                status="missing_api_key",
                detail=(
                    f"Environment variable '{summary.api_key_env}' is not set."
                    if summary.api_key_env
                    else "Provider API key is not configured."
                ),
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
    def _normalize_required_string(cls, value: str | None, field_name: str) -> str:
        """Normalize and require a non-empty editable string."""
        normalized = cls._normalize_optional_string(value)
        if normalized is None:
            raise ModelControlError(f"{field_name} is required.")
        return normalized

    @classmethod
    def _validate_protocol(cls, value: str | None) -> str:
        """Normalize and validate provider protocol names."""
        protocol = cls._normalize_required_string(value, "protocol").lower()
        if protocol not in SUPPORTED_PROVIDER_PROTOCOLS:
            raise ModelControlError(
                f"Unsupported provider protocol '{value}'. "
                f"Supported protocols: {', '.join(sorted(SUPPORTED_PROVIDER_PROTOCOLS))}."
            )
        return protocol

    @classmethod
    def _clean_string_list(cls, values: list[str]) -> list[str]:
        """Normalize comma-split user strings into stable lists."""
        return [
            item
            for item in (cls._normalize_optional_string(value) for value in values)
            if item is not None
        ]

    @classmethod
    def _normalize_optional_url(cls, value: str | None) -> str | None:
        """Normalize and validate optional provider URLs."""
        normalized = cls._normalize_optional_string(value)
        if normalized is None:
            return None
        if not normalized.startswith(("http://", "https://")):
            raise ModelControlError("Provider URLs must start with http:// or https://.")
        return normalized

    @classmethod
    def _persist_api_key(
        cls,
        provider_id: str,
        api_key: str | None,
        *,
        clear_if_blank: bool,
    ) -> None:
        """Store or clear a local provider API key without returning it."""
        normalized = cls._normalize_optional_string(api_key)
        if normalized is None and not clear_if_blank:
            return
        secrets = load_provider_secrets()
        if normalized is None:
            secrets.api_keys.pop(provider_id, None)
        else:
            secrets.api_keys[provider_id] = normalized
        save_provider_secrets(secrets)

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
