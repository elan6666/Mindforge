"""User-editable model control service for Phase 7."""

from functools import lru_cache

from app.backend.schemas.model import (
    ModelControlUpdate,
    ModelOverrideEntry,
    ModelSummary,
    ModelOverridesDocument,
)
from app.backend.services.model_loader import load_model_catalog, load_model_overrides, save_model_overrides
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

    def get_overrides_document(self) -> ModelOverridesDocument:
        """Expose the raw overrides document for debugging or future UI use."""
        return load_model_overrides()

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
