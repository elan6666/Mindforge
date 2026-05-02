"""Skill registry endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.backend.schemas.skills import SkillDetail, SkillSettingsUpdate, SkillSummary
from app.backend.services.skill_registry_service import (
    SkillRegistryService,
    get_skill_registry_service,
)

router = APIRouter()


@router.get("", response_model=list[SkillSummary])
def list_skills(
    service: SkillRegistryService = Depends(get_skill_registry_service),
) -> list[SkillSummary]:
    """List local SKILL.md entries available to Mindforge."""
    return service.list_skills()


@router.get("/{skill_id}", response_model=SkillDetail)
def get_skill(
    skill_id: str,
    service: SkillRegistryService = Depends(get_skill_registry_service),
) -> SkillDetail:
    """Return one skill with bounded content excerpt."""
    detail = service.get_skill(skill_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown skill '{skill_id}'.",
        )
    return detail


@router.patch("/{skill_id}", response_model=SkillSummary)
def update_skill_settings(
    skill_id: str,
    payload: SkillSettingsUpdate,
    service: SkillRegistryService = Depends(get_skill_registry_service),
) -> SkillSummary:
    """Update one Skill's enablement, trust level, or notes."""
    summary = service.update_skill_settings(skill_id, payload)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown skill '{skill_id}'.",
        )
    return summary
