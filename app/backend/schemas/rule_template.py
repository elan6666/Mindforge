"""Schemas for rule templates and coordinator-driven template selection."""

from pydantic import BaseModel, Field


class RuleAssignment(BaseModel):
    """One role/responsibility assignment inside a rule template."""

    role: str = Field(..., min_length=1)
    responsibility: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)


class RuleTemplateDefinition(BaseModel):
    """Stored rule template for one preset/scenario."""

    template_id: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    preset_mode: str = Field(..., min_length=1)
    task_types: list[str] = Field(default_factory=list)
    default_coordinator_model_id: str = Field(..., min_length=1)
    enabled: bool = True
    is_default: bool = False
    trigger_keywords: list[str] = Field(default_factory=list)
    assignments: list[RuleAssignment] = Field(default_factory=list)
    notes: str = ""


class RuleTemplateCatalog(BaseModel):
    """Collection of stored rule templates."""

    templates: list[RuleTemplateDefinition] = Field(default_factory=list)


class RuleTemplateSummary(BaseModel):
    """Lightweight UI view of a rule template."""

    template_id: str
    display_name: str
    description: str
    preset_mode: str
    task_types: list[str] = Field(default_factory=list)
    default_coordinator_model_id: str
    enabled: bool
    is_default: bool
    trigger_keywords: list[str] = Field(default_factory=list)
    assignments: list[RuleAssignment] = Field(default_factory=list)
    notes: str = ""


class RuleTemplateUpsert(BaseModel):
    """Create/update payload for rule templates."""

    template_id: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    preset_mode: str = Field(..., min_length=1)
    task_types: list[str] = Field(default_factory=list)
    default_coordinator_model_id: str = Field(..., min_length=1)
    enabled: bool = True
    is_default: bool = False
    trigger_keywords: list[str] = Field(default_factory=list)
    assignments: list[RuleAssignment] = Field(default_factory=list)
    notes: str = ""


class RuleTemplateSelection(BaseModel):
    """Coordinator-resolved template selection for one task."""

    template_id: str
    display_name: str
    preset_mode: str
    selection_source: str
    coordinator_model_id: str
    matched_keywords: list[str] = Field(default_factory=list)
    role_model_overrides: dict[str, str] = Field(default_factory=dict)
