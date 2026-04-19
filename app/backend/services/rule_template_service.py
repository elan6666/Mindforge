"""Rule template storage and mutation service for Phase 7."""

from functools import lru_cache

from app.backend.schemas.rule_template import (
    RuleTemplateCatalog,
    RuleTemplateDefinition,
    RuleTemplateSummary,
    RuleTemplateUpsert,
)
from app.backend.services.model_registry_service import get_model_registry_service
from app.backend.services.rule_template_loader import (
    load_rule_template_catalog,
    save_rule_template_catalog,
)


class RuleTemplateError(ValueError):
    """Raised when template storage or validation fails."""


class RuleTemplateService:
    """Persist and query structured rule templates."""

    def list_templates(self) -> list[RuleTemplateSummary]:
        """Return current rule templates."""
        return [
            RuleTemplateSummary(**template.model_dump())
            for template in load_rule_template_catalog().templates
        ]

    def get_template(self, template_id: str) -> RuleTemplateDefinition | None:
        """Look up one rule template by id."""
        return next(
            (
                template
                for template in load_rule_template_catalog().templates
                if template.template_id == template_id
            ),
            None,
        )

    def upsert_template(
        self,
        payload: RuleTemplateUpsert,
    ) -> RuleTemplateSummary:
        """Create or update one rule template."""
        self._validate_template(payload)
        catalog = load_rule_template_catalog()
        templates = [
            template
            for template in catalog.templates
            if template.template_id != payload.template_id
        ]
        template = RuleTemplateDefinition(**payload.model_dump())
        templates.append(template)
        catalog = self._normalize_defaults(
            RuleTemplateCatalog(templates=templates),
            preset_mode=payload.preset_mode,
            template_id=payload.template_id,
            is_default=payload.is_default,
        )
        save_rule_template_catalog(catalog)
        self._clear_related_caches()
        return RuleTemplateSummary(**template.model_dump())

    def delete_template(self, template_id: str) -> None:
        """Delete one rule template by id."""
        catalog = load_rule_template_catalog()
        templates = [
            template
            for template in catalog.templates
            if template.template_id != template_id
        ]
        if len(templates) == len(catalog.templates):
            raise RuleTemplateError(f"Unknown rule template '{template_id}'.")
        save_rule_template_catalog(RuleTemplateCatalog(templates=templates))
        self._clear_related_caches()

    def list_matching_templates(
        self,
        *,
        preset_mode: str,
        task_type: str | None,
    ) -> list[RuleTemplateDefinition]:
        """Return enabled templates that match the current task scope."""
        matches: list[RuleTemplateDefinition] = []
        for template in load_rule_template_catalog().templates:
            if not template.enabled:
                continue
            if template.preset_mode != preset_mode:
                continue
            if task_type and template.task_types and task_type not in template.task_types:
                continue
            matches.append(template)
        return matches

    @staticmethod
    def _validate_template(payload: RuleTemplateUpsert) -> None:
        """Ensure models referenced by a template exist in the registry."""
        registry = get_model_registry_service()
        if registry.get_model(payload.default_coordinator_model_id) is None:
            raise RuleTemplateError(
                f"Unknown coordinator model '{payload.default_coordinator_model_id}'."
            )
        for assignment in payload.assignments:
            if registry.get_model(assignment.model_id) is None:
                raise RuleTemplateError(
                    f"Unknown model '{assignment.model_id}' in assignment '{assignment.role}'."
                )

    @staticmethod
    def _normalize_defaults(
        catalog: RuleTemplateCatalog,
        *,
        preset_mode: str,
        template_id: str,
        is_default: bool,
    ) -> RuleTemplateCatalog:
        """Ensure at most one default template exists per preset."""
        if not is_default:
            return catalog
        normalized: list[RuleTemplateDefinition] = []
        for template in catalog.templates:
            if template.preset_mode == preset_mode:
                normalized.append(
                    template.model_copy(
                        update={"is_default": template.template_id == template_id}
                    )
                )
            else:
                normalized.append(template)
        return RuleTemplateCatalog(templates=normalized)

    @staticmethod
    def _clear_related_caches() -> None:
        """Reset cached services after template changes."""
        from app.backend.services.coordinator_selection_service import (
            clear_coordinator_selection_service_cache,
        )
        from app.backend.services.task_service import clear_task_service_cache

        clear_rule_template_service_cache()
        clear_coordinator_selection_service_cache()
        clear_task_service_cache()


@lru_cache(maxsize=1)
def get_rule_template_service() -> RuleTemplateService:
    """Return a cached rule template service."""
    return RuleTemplateService()


def clear_rule_template_service_cache() -> None:
    """Clear the cached template service after mutations."""
    get_rule_template_service.cache_clear()
