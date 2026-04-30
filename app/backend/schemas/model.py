"""Schemas for provider/model registry and routing decisions."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ModelPriority(StrEnum):
    """Supported priority levels for backend model routing."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DISABLED = "disabled"


class ProviderDefinition(BaseModel):
    """One configured upstream provider."""

    provider_id: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    enabled: bool = True
    api_base_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelDefinition(BaseModel):
    """One configured model entry in the registry."""

    model_id: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    provider_id: str = Field(..., min_length=1)
    upstream_model: str = Field(..., min_length=1)
    priority: ModelPriority = ModelPriority.MEDIUM
    enabled: bool = True
    supported_preset_modes: list[str] = Field(default_factory=list)
    supported_task_types: list[str] = Field(default_factory=list)
    supported_roles: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoutingRules(BaseModel):
    """Static backend routing rules for the MVP registry."""

    default_model_id: str = Field(..., min_length=1)
    preset_defaults: dict[str, str] = Field(default_factory=dict)
    task_type_defaults: dict[str, str] = Field(default_factory=dict)
    role_defaults: dict[str, dict[str, str]] = Field(default_factory=dict)


class ModelCatalog(BaseModel):
    """Full YAML-backed model catalog."""

    providers: list[ProviderDefinition] = Field(default_factory=list)
    models: list[ModelDefinition] = Field(default_factory=list)
    routing: RoutingRules


class ProviderSummary(BaseModel):
    """Lightweight provider view exposed by the API."""

    provider_id: str
    display_name: str
    description: str
    enabled: bool
    api_base_url: str | None = None
    api_key_env: str | None = None
    api_key_configured: bool = False
    protocol: str = "openai"
    anthropic_api_base_url: str | None = None


class ModelSummary(BaseModel):
    """Lightweight model view exposed by the API."""

    model_id: str
    display_name: str
    provider_id: str
    upstream_model: str
    priority: ModelPriority
    enabled: bool
    supported_preset_modes: list[str] = Field(default_factory=list)
    supported_task_types: list[str] = Field(default_factory=list)
    supported_roles: list[str] = Field(default_factory=list)


class ModelControlUpdate(BaseModel):
    """Editable model control fields exposed by the Phase 7 UI."""

    priority: ModelPriority | None = None
    enabled: bool | None = None


class ProviderControlUpdate(BaseModel):
    """Editable provider control fields exposed by the Provider/API UI."""

    enabled: bool | None = None
    api_base_url: str | None = None
    api_key_env: str | None = None
    protocol: str | None = None
    anthropic_api_base_url: str | None = None


class ModelOverrideEntry(BaseModel):
    """Persisted mutable override for one model entry."""

    priority: ModelPriority | None = None
    enabled: bool | None = None


class ProviderOverrideEntry(BaseModel):
    """Persisted mutable override for one provider entry."""

    enabled: bool | None = None
    api_base_url: str | None = None
    api_key_env: str | None = None
    protocol: str | None = None
    anthropic_api_base_url: str | None = None


class ModelOverridesDocument(BaseModel):
    """Local writable overrides layered on top of the seed catalog."""

    models: dict[str, ModelOverrideEntry] = Field(default_factory=dict)


class ProviderOverridesDocument(BaseModel):
    """Local writable provider overrides layered on top of the seed catalog."""

    providers: dict[str, ProviderOverrideEntry] = Field(default_factory=dict)


class ProviderConnectionTestResult(BaseModel):
    """Result of a provider connectivity check."""

    provider_id: str
    ok: bool
    status: str
    detail: str
    protocol: str
    api_base_url: str | None = None
    api_key_env: str | None = None
    api_key_configured: bool = False
    upstream_status: int | None = None


class ModelSelection(BaseModel):
    """Resolved model selection used at execution time."""

    model_id: str
    display_name: str
    provider_id: str
    upstream_model: str
    priority: ModelPriority
    selection_source: str
