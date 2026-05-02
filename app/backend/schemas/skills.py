"""Schemas for local skill discovery and prompt loading."""

from pydantic import BaseModel, Field


class SkillSummary(BaseModel):
    """Public metadata for one discovered skill."""

    skill_id: str
    name: str
    description: str = ""
    path: str
    source_root: str
    enabled: bool = True
    trust_level: str = "local"
    notes: str = ""


class SkillDetail(SkillSummary):
    """Full skill payload used by the runtime prompt loader."""

    content_excerpt: str


class SkillSettingsUpdate(BaseModel):
    """Mutable user-controlled Skill settings."""

    enabled: bool | None = None
    trust_level: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=500)
