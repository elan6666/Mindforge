"""Registry access for providers and models."""

from functools import lru_cache
import os
from typing import cast

from app.backend.schemas.model import (
    ModelCatalog,
    ModelDefinition,
    ModelOverrideEntry,
    ModelSummary,
    ProviderDefinition,
    ProviderOverrideEntry,
    ProviderSummary,
)
from app.backend.services.model_loader import (
    load_model_catalog,
    load_model_overrides,
    load_provider_secrets,
    load_provider_overrides,
)


class ModelRegistryError(ValueError):
    """Raised when the YAML-backed model registry is invalid."""


class ModelRegistryService:
    """Provide provider/model lookup over the YAML registry."""

    def __init__(self) -> None:
        self._custom_provider_ids: set[str] = set()
        self._custom_model_ids: set[str] = set()
        self._catalog = self._build_catalog()
        self._providers = {
            provider.provider_id: provider for provider in self._catalog.providers
        }
        self._models = {model.model_id: model for model in self._catalog.models}
        if self._catalog.routing.default_model_id not in self._models:
            raise ModelRegistryError(
                "Default model configured in routing rules is missing from the registry."
            )

    @property
    def catalog(self) -> ModelCatalog:
        """Return the underlying parsed catalog."""
        return self._catalog

    def list_providers(self) -> list[ProviderSummary]:
        """Return lightweight provider entries."""
        return [
            self._to_provider_summary(
                provider,
                is_custom=provider.provider_id in self._custom_provider_ids,
            )
            for provider in self._providers.values()
        ]

    def list_models(self) -> list[ModelSummary]:
        """Return lightweight model entries."""
        return [
            ModelSummary(
                model_id=model.model_id,
                display_name=model.display_name,
                provider_id=model.provider_id,
                upstream_model=model.upstream_model,
                priority=model.priority,
                enabled=model.enabled,
                supported_preset_modes=model.supported_preset_modes,
                supported_task_types=model.supported_task_types,
                supported_roles=model.supported_roles,
                is_custom=model.model_id in self._custom_model_ids,
            )
            for model in self._models.values()
        ]

    def get_provider(self, provider_id: str) -> ProviderDefinition | None:
        """Look up a provider by id."""
        return self._providers.get(provider_id)

    def get_provider_summary(self, provider_id: str) -> ProviderSummary | None:
        """Look up a provider by id and return its editable API-facing view."""
        provider = self.get_provider(provider_id)
        if provider is None:
            return None
        return self._to_provider_summary(
            provider,
            is_custom=provider.provider_id in self._custom_provider_ids,
        )

    def get_model(self, model_id: str) -> ModelDefinition | None:
        """Look up a model by id."""
        return self._models.get(model_id)

    def iter_enabled_models(self) -> list[ModelDefinition]:
        """Return models whose provider and model are both enabled."""
        enabled_models: list[ModelDefinition] = []
        for model in self._models.values():
            provider = self.get_provider(model.provider_id)
            if provider is None:
                continue
            if model.enabled and provider.enabled and model.priority != "disabled":
                enabled_models.append(model)
        return enabled_models

    def iter_enabled_custom_models(self) -> list[ModelDefinition]:
        """Return enabled user-created models only."""
        return [
            model
            for model in self.iter_enabled_models()
            if model.model_id in self._custom_model_ids
        ]

    def _build_catalog(self) -> ModelCatalog:
        """Load the seed catalog and layer mutable local overrides on top."""
        catalog = load_model_catalog()
        model_overrides = load_model_overrides()
        provider_overrides = load_provider_overrides()
        self._custom_provider_ids = set(provider_overrides.custom_providers)
        self._custom_model_ids = set(model_overrides.custom_models)

        merged_providers: list[ProviderDefinition] = []
        for provider in catalog.providers:
            override = provider_overrides.providers.get(provider.provider_id)
            if override is None:
                merged_providers.append(provider)
                continue
            merged_providers.append(self._apply_provider_override(provider, override))

        for provider_id, provider in provider_overrides.custom_providers.items():
            override = provider_overrides.providers.get(provider_id)
            merged_providers.append(
                self._apply_provider_override(provider, override)
                if override is not None
                else provider
            )

        if (
            not model_overrides.models
            and not model_overrides.custom_models
            and not provider_overrides.providers
            and not provider_overrides.custom_providers
        ):
            return catalog

        merged_models: list[ModelDefinition] = []
        for model in catalog.models:
            override = model_overrides.models.get(model.model_id)
            if override is None:
                merged_models.append(model)
                continue
            merged_models.append(self._apply_override(model, override))

        for model_id, model in model_overrides.custom_models.items():
            override = model_overrides.models.get(model_id)
            merged_models.append(
                self._apply_override(model, override)
                if override is not None
                else model
            )
        return ModelCatalog(
            providers=merged_providers,
            models=merged_models,
            routing=catalog.routing,
        )

    @classmethod
    def _to_provider_summary(
        cls,
        provider: ProviderDefinition,
        *,
        is_custom: bool = False,
    ) -> ProviderSummary:
        """Convert a provider definition into the API-facing editable view."""
        api_key_env = cls._provider_api_key_env(provider)
        secrets = load_provider_secrets()
        return ProviderSummary(
            provider_id=provider.provider_id,
            display_name=provider.display_name,
            description=provider.description,
            enabled=provider.enabled,
            api_base_url=provider.api_base_url,
            api_key_env=api_key_env,
            api_key_configured=bool(secrets.api_keys.get(provider.provider_id))
            or bool(api_key_env and os.getenv(api_key_env)),
            protocol=cls._provider_protocol(provider),
            anthropic_api_base_url=cls._provider_anthropic_api_base_url(provider),
            is_custom=is_custom,
        )

    @staticmethod
    def _provider_api_key_env(provider: ProviderDefinition) -> str:
        """Return the explicit or conventional environment variable for a provider."""
        configured = provider.metadata.get("api_key_env")
        if configured:
            return str(configured)
        return f"{provider.provider_id.upper().replace('-', '_')}_API_KEY"

    @staticmethod
    def _provider_protocol(provider: ProviderDefinition) -> str:
        """Return the transport protocol for a provider."""
        return str(provider.metadata.get("protocol", "openai")).lower()

    @staticmethod
    def _provider_anthropic_api_base_url(provider: ProviderDefinition) -> str | None:
        """Return the Anthropic-compatible base URL when configured."""
        configured = provider.metadata.get("anthropic_api_base_url")
        if configured:
            return str(configured)
        return None

    @staticmethod
    def _apply_override(
        model: ModelDefinition,
        override: ModelOverrideEntry,
    ) -> ModelDefinition:
        """Return a model definition patched with local editable fields."""
        update_payload: dict[str, object] = {}
        if override.priority is not None:
            update_payload["priority"] = override.priority
        if override.enabled is not None:
            update_payload["enabled"] = override.enabled
        return cast(ModelDefinition, model.model_copy(update=update_payload))

    @staticmethod
    def _apply_provider_override(
        provider: ProviderDefinition,
        override: ProviderOverrideEntry,
    ) -> ProviderDefinition:
        """Return a provider definition patched with local editable fields."""
        update_payload: dict[str, object] = {}
        metadata = dict(provider.metadata)

        if override.enabled is not None:
            update_payload["enabled"] = override.enabled
        if override.api_base_url is not None:
            update_payload["api_base_url"] = override.api_base_url
        if override.api_key_env is not None:
            metadata["api_key_env"] = override.api_key_env
        if override.protocol is not None:
            metadata["protocol"] = override.protocol
        if override.anthropic_api_base_url is not None:
            metadata["anthropic_api_base_url"] = override.anthropic_api_base_url
        if metadata != provider.metadata:
            update_payload["metadata"] = metadata

        return cast(ProviderDefinition, provider.model_copy(update=update_payload))


@lru_cache(maxsize=1)
def get_model_registry_service() -> ModelRegistryService:
    """Return a cached model registry service."""
    return ModelRegistryService()


def clear_model_registry_service_cache() -> None:
    """Clear the cached registry service after mutable config changes."""
    get_model_registry_service.cache_clear()
