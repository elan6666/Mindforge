"""Coordinator-driven rule-template selection."""

from functools import lru_cache

from app.backend.schemas.rule_template import RuleTemplateDefinition, RuleTemplateSelection
from app.backend.services.rule_template_service import (
    RuleTemplateService,
    get_rule_template_service,
)


class CoordinatorSelectionError(ValueError):
    """Raised when a requested rule-template selection is invalid."""


class CoordinatorSelectionService:
    """Select rule templates based on explicit choice or simple prompt analysis."""

    def __init__(self, templates: RuleTemplateService) -> None:
        self.templates = templates

    def select_template(
        self,
        *,
        prompt: str,
        preset_mode: str,
        task_type: str | None,
        explicit_template_id: str | None = None,
    ) -> RuleTemplateSelection | None:
        """Resolve the most appropriate rule template for a task."""
        if explicit_template_id:
            template = self.templates.get_template(explicit_template_id)
            if template is None:
                raise CoordinatorSelectionError(
                    f"Unknown rule template '{explicit_template_id}'."
                )
            if not template.enabled:
                raise CoordinatorSelectionError(
                    f"Rule template '{explicit_template_id}' is disabled."
                )
            return self._to_selection(
                template,
                selection_source="explicit-template",
                matched_keywords=[],
            )

        candidates = self.templates.list_matching_templates(
            preset_mode=preset_mode,
            task_type=task_type,
        )
        if not candidates:
            return None

        prompt_lower = prompt.lower()
        scored: list[tuple[int, RuleTemplateDefinition, list[str]]] = []
        for template in candidates:
            matched_keywords = [
                keyword
                for keyword in template.trigger_keywords
                if keyword.lower() in prompt_lower
            ]
            score = len(matched_keywords)
            if template.is_default:
                score += 1
            scored.append((score, template, matched_keywords))

        scored.sort(key=lambda item: item[0], reverse=True)
        top_score, top_template, matched_keywords = scored[0]
        selection_source = (
            "heuristic-keyword-match" if top_score > 0 else "preset-default-template"
        )
        return self._to_selection(
            top_template,
            selection_source=selection_source,
            matched_keywords=matched_keywords,
        )

    @staticmethod
    def _to_selection(
        template: RuleTemplateDefinition,
        *,
        selection_source: str,
        matched_keywords: list[str],
    ) -> RuleTemplateSelection:
        """Convert a stored template into a task-scoped selection payload."""
        return RuleTemplateSelection(
            template_id=template.template_id,
            display_name=template.display_name,
            preset_mode=template.preset_mode,
            selection_source=selection_source,
            coordinator_model_id=template.default_coordinator_model_id,
            matched_keywords=matched_keywords,
            role_model_overrides={
                assignment.role: assignment.model_id for assignment in template.assignments
            },
        )


@lru_cache(maxsize=1)
def get_coordinator_selection_service() -> CoordinatorSelectionService:
    """Return a cached coordinator selection service."""
    return CoordinatorSelectionService(get_rule_template_service())


def clear_coordinator_selection_service_cache() -> None:
    """Clear cached coordinator selection service."""
    get_coordinator_selection_service.cache_clear()
