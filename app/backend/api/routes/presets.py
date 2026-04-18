"""Preset discovery endpoints."""

from fastapi import APIRouter, Depends

from app.backend.schemas.preset import PresetSummary
from app.backend.services.preset_service import PresetService, get_preset_service

router = APIRouter()


@router.get("", response_model=list[PresetSummary])
def list_presets(
    service: PresetService = Depends(get_preset_service),
) -> list[PresetSummary]:
    """Return all available preset summaries."""
    return service.list_presets()

