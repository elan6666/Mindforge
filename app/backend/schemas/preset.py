"""Schemas for preset template definitions and discovery responses."""

from typing import Any

from pydantic import BaseModel, Field


class PresetDefinition(BaseModel):
    """Validated preset template loaded from configuration files."""

    preset_mode: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    agent_roles: list[str] = Field(default_factory=list)
    execution_flow: list[str] = Field(default_factory=list)
    default_models: dict[str, str] = Field(default_factory=dict)
    requires_repo_analysis: bool = False
    requires_approval: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PresetSummary(BaseModel):
    """Lightweight preset description exposed by the discovery API."""

    preset_mode: str
    display_name: str
    description: str
    requires_repo_analysis: bool
    requires_approval: bool

