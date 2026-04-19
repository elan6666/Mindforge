"""Resolve execution-time model selections."""

from functools import lru_cache

from app.backend.schemas.model import ModelDefinition, ModelPriority, ModelSelection
from app.backend.services.model_registry_service import (
    ModelRegistryError,
    ModelRegistryService,
    get_model_registry_service,
)

PRIORITY_ORDER = {
    ModelPriority.HIGH: 0,
    ModelPriority.MEDIUM: 1,
    ModelPriority.LOW: 2,
    ModelPriority.DISABLED: 3,
}


class ModelRoutingError(ValueError):
    """Raised when a model selection cannot be resolved safely."""


class ModelRoutingService:
    """Resolve single-pass and role-based model selections."""

    def __init__(self, registry: ModelRegistryService) -> None:
        self.registry = registry

    def resolve_for_task(
        self,
        *,
        preset_mode: str,
        task_type: str | None,
        explicit_model: str | None = None,
    ) -> ModelSelection:
        """Resolve a model for a single-pass task."""
        candidate_chain = [
            ("explicit-task-override", explicit_model),
            ("task-type-default", self.registry.catalog.routing.task_type_defaults.get(task_type or "")),
            ("preset-default", self.registry.catalog.routing.preset_defaults.get(preset_mode)),
            ("global-default", self.registry.catalog.routing.default_model_id),
        ]
        return self._resolve_from_candidates(
            candidate_chain=candidate_chain,
            preset_mode=preset_mode,
            task_type=task_type,
            role=None,
        )

    def resolve_for_role(
        self,
        *,
        preset_mode: str,
        task_type: str | None,
        role: str,
        explicit_model: str | None = None,
        preset_default_model: str | None = None,
    ) -> ModelSelection:
        """Resolve a model for one orchestration stage."""
        role_defaults = self.registry.catalog.routing.role_defaults.get(preset_mode, {})
        candidate_chain = [
            ("explicit-role-override", explicit_model),
            ("routing-role-default", role_defaults.get(role)),
            ("preset-role-default", preset_default_model),
            ("task-type-default", self.registry.catalog.routing.task_type_defaults.get(task_type or "")),
            ("preset-default", self.registry.catalog.routing.preset_defaults.get(preset_mode)),
            ("global-default", self.registry.catalog.routing.default_model_id),
        ]
        return self._resolve_from_candidates(
            candidate_chain=candidate_chain,
            preset_mode=preset_mode,
            task_type=task_type,
            role=role,
        )

    def _resolve_from_candidates(
        self,
        *,
        candidate_chain: list[tuple[str, str | None]],
        preset_mode: str,
        task_type: str | None,
        role: str | None,
    ) -> ModelSelection:
        """Return the first valid routed model or a priority-based fallback."""
        for source, model_id in candidate_chain:
            if not model_id:
                continue
            model = self._require_enabled_model(model_id, source=source)
            if source.startswith("explicit-") or self._model_supports_scope(
                model,
                preset_mode=preset_mode,
                task_type=task_type,
                role=role,
            ):
                return self._to_selection(model, selection_source=source)

        fallback = self._priority_fallback(
            preset_mode=preset_mode,
            task_type=task_type,
            role=role,
        )
        if fallback is None:
            raise ModelRoutingError("No enabled model matches the current routing scope.")
        return self._to_selection(fallback, selection_source="priority-fallback")

    def _priority_fallback(
        self,
        *,
        preset_mode: str,
        task_type: str | None,
        role: str | None,
    ) -> ModelDefinition | None:
        """Return the best enabled model ordered by priority."""
        candidates = [
            model
            for model in self.registry.iter_enabled_models()
            if self._model_supports_scope(
                model,
                preset_mode=preset_mode,
                task_type=task_type,
                role=role,
            )
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda model: PRIORITY_ORDER[model.priority])[0]

    def _require_enabled_model(self, model_id: str, *, source: str) -> ModelDefinition:
        """Ensure a candidate model exists and is enabled."""
        model = self.registry.get_model(model_id)
        if model is None:
            raise ModelRoutingError(
                f"Model '{model_id}' referenced by {source} is not registered."
            )
        provider = self.registry.get_provider(model.provider_id)
        if provider is None:
            raise ModelRegistryError(
                f"Provider '{model.provider_id}' referenced by model '{model_id}' is missing."
            )
        if not provider.enabled:
            raise ModelRoutingError(
                f"Model '{model_id}' cannot be used because provider '{provider.provider_id}' is disabled."
            )
        if not model.enabled or model.priority == ModelPriority.DISABLED:
            raise ModelRoutingError(f"Model '{model_id}' is disabled.")
        return model

    @staticmethod
    def _model_supports_scope(
        model: ModelDefinition,
        *,
        preset_mode: str,
        task_type: str | None,
        role: str | None,
    ) -> bool:
        """Check whether a model can be used for the current scope."""
        if model.supported_preset_modes and preset_mode not in model.supported_preset_modes:
            return False
        if task_type and model.supported_task_types and task_type not in model.supported_task_types:
            return False
        if role and model.supported_roles and role not in model.supported_roles:
            return False
        return True

    @staticmethod
    def _to_selection(model: ModelDefinition, *, selection_source: str) -> ModelSelection:
        """Convert a registry model entry into an execution-time selection."""
        return ModelSelection(
            model_id=model.model_id,
            display_name=model.display_name,
            provider_id=model.provider_id,
            upstream_model=model.upstream_model,
            priority=model.priority,
            selection_source=selection_source,
        )


@lru_cache(maxsize=1)
def get_model_routing_service() -> ModelRoutingService:
    """Return a cached model routing service."""
    return ModelRoutingService(get_model_registry_service())


def clear_model_routing_service_cache() -> None:
    """Clear cached model routing service after mutable config changes."""
    get_model_routing_service.cache_clear()
