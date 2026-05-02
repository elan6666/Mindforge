"""Project space endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.backend.schemas.project_space import (
    ProjectSpaceContext,
    ProjectSpaceSummary,
    ProjectSpaceUpsert,
)
from app.backend.services.project_space_service import (
    ProjectSpaceService,
    get_project_space_service,
)

router = APIRouter()


@router.get("", response_model=list[ProjectSpaceSummary])
def list_project_spaces(
    service: ProjectSpaceService = Depends(get_project_space_service),
) -> list[ProjectSpaceSummary]:
    """List configured project spaces."""
    return service.list_spaces()


@router.post("", response_model=ProjectSpaceSummary, status_code=status.HTTP_201_CREATED)
def upsert_project_space(
    payload: ProjectSpaceUpsert,
    service: ProjectSpaceService = Depends(get_project_space_service),
) -> ProjectSpaceSummary:
    """Create or update a project space."""
    return service.upsert_space(payload)


@router.get("/{project_id}", response_model=ProjectSpaceSummary)
def get_project_space(
    project_id: str,
    service: ProjectSpaceService = Depends(get_project_space_service),
) -> ProjectSpaceSummary:
    """Return one project space."""
    space = service.get_space(project_id)
    if space is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown project space '{project_id}'.",
        )
    return space


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_space(
    project_id: str,
    service: ProjectSpaceService = Depends(get_project_space_service),
) -> None:
    """Delete one project space."""
    if not service.delete_space(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown project space '{project_id}'.",
        )


@router.get("/{project_id}/context", response_model=ProjectSpaceContext)
def get_project_context(
    project_id: str,
    query: str = "",
    service: ProjectSpaceService = Depends(get_project_space_service),
) -> ProjectSpaceContext:
    """Preview prompt-ready project context for one task query."""
    return service.prompt_context(project_id, query=query)
