"""Registry access for providers and models."""

from functools import lru_cache
from typing import cast

from app.backend.schemas.model import (
    ModelCatalog,
    ModelDefinition,
    ModelOverrideEntry,
    ModelSummary,
    ProviderDefinition,
    ProviderSummary,
)
from app.backend.services.model_loader import load_model_catalog, load_model_overrides


class ModelRegistryError(ValueError):
    """Raised when the YAML-backed model registry is invalid."""


class ModelRegistryService:
    """Provide provider/model lookup over the YAML registry."""

    def __init__(self) -> None:
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
            ProviderSummary(
                provider_id=provider.provider_id,
                display_name=provider.display_name,
                description=provider.description,
                enabled=provider.enabled,
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
            )
            for model in self._models.values()
        ]

    def get_provider(self, provider_id: str) -> ProviderDefinition | None:
        """Look up a provider by id."""
        return self._providers.get(provider_id)

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

    def _build_catalog(self) -> ModelCatalog:
        """Load the seed catalog and layer mutable local overrides on top."""
        catalog = load_model_catalog()
        overrides = load_model_overrides()
        if not overrides.models:
            return catalog

        merged_models: list[ModelDefinition] = []
        for model in catalog.models:
            override = overrides.models.get(model.model_id)
            if override is None:
                merged_models.append(model)
                continue
            merged_models.append(self._apply_override(model, override))
        return ModelCatalog(
            providers=catalog.providers,
            models=merged_models,
            routing=catalog.routing,
        )

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


@lru_cache(maxsize=1)
def get_model_registry_service() -> ModelRegistryService:
    """Return a cached model registry service."""
    return ModelRegistryService()


def clear_model_registry_service_cache() -> None:
    """Clear the cached registry service after mutable config changes."""
    get_model_registry_service.cache_clear()
