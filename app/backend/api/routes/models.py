"""Provider and model registry discovery endpoints."""

from fastapi import APIRouter, Depends

from app.backend.schemas.model import ModelSummary, ProviderSummary
from app.backend.services.model_registry_service import (
    ModelRegistryService,
    get_model_registry_service,
)

router = APIRouter()


@router.get("/providers", response_model=list[ProviderSummary])
def list_providers(
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> list[ProviderSummary]:
    """Return configured provider definitions."""
    return service.list_providers()


@router.get("/models", response_model=list[ModelSummary])
def list_models(
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> list[ModelSummary]:
    """Return configured model definitions."""
    return service.list_models()

