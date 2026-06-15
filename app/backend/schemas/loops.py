"""Schemas for portable Mindforge Loop definitions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LoopRole(BaseModel):
    """One expert role participating in a Loop."""

    role_id: str
    name: str
    responsibility: str
    default_model_policy: str = "auto"


class LoopStep(BaseModel):
    """One repeatable stage in a Loop."""

    step_id: str
    title: str
    owner_role: str
    instruction: str
    evidence_required: list[str] = Field(default_factory=list)
    expected_output: str = ""


class LoopArtifactSpec(BaseModel):
    """Artifact shape a Loop should produce or update."""

    title: str
    format: str = "markdown"
    purpose: str = ""


class LoopDefinition(BaseModel):
    """Portable workflow definition, designed to round-trip as loop.md."""

    loop_id: str
    name: str
    description: str
    forge_id: str = "code-forge"
    version: str = "1.0.0"
    status: str = "ready"
    trigger_phrases: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    roles: list[LoopRole] = Field(default_factory=list)
    steps: list[LoopStep] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    evidence_rules: list[str] = Field(default_factory=list)
    artifact_outputs: list[LoopArtifactSpec] = Field(default_factory=list)
    evaluation_rubric: list[str] = Field(default_factory=list)
    memory_policy: str = "Record final artifact, loop version, evidence, model routing, and next improvement."
    approval_checkpoints: list[str] = Field(default_factory=list)
    improvement_count: int = 0
    updated_at: str
    source: str = "default"
    loop_md: str | None = None


class LoopUpsertRequest(BaseModel):
    """Create or update a Loop definition."""

    loop: LoopDefinition


class LoopImportRequest(BaseModel):
    """Import a Loop from portable markdown."""

    content: str = Field(..., min_length=1)


class LoopMarkdownExport(BaseModel):
    """Portable loop.md payload."""

    loop_id: str
    filename: str
    content: str


class LoopImproveRequest(BaseModel):
    """Request an improvement pass for a Loop after a run."""

    task_id: str | None = None
    note: str | None = None


class LoopRunTrace(BaseModel):
    """Task metadata trace attached when a Loop runs."""

    loop_id: str
    loop_name: str
    version: str
    forge_id: str
    status: str
    roles: list[dict[str, Any]] = Field(default_factory=list)
    stages: list[dict[str, Any]] = Field(default_factory=list)
    evidence_rules: list[str] = Field(default_factory=list)
    artifact_outputs: list[dict[str, Any]] = Field(default_factory=list)
    improvement_count: int = 0
    completed_at: str | None = None
