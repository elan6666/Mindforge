"""Loop Library endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.backend.schemas.loops import (
    LoopDefinition,
    LoopImportRequest,
    LoopImproveRequest,
    LoopMarkdownExport,
    LoopUpsertRequest,
)
from app.backend.services.loop_service import LoopService, get_loop_service

router = APIRouter()


@router.get("", response_model=list[LoopDefinition])
def list_loops(service: LoopService = Depends(get_loop_service)) -> list[LoopDefinition]:
    """List portable Loop definitions."""
    return service.list_loops()


@router.get("/{loop_id}", response_model=LoopDefinition)
def get_loop(loop_id: str, service: LoopService = Depends(get_loop_service)) -> LoopDefinition:
    """Return one Loop definition."""
    loop = service.get_loop(loop_id)
    if loop is None:
        raise HTTPException(status_code=404, detail=f"Unknown loop '{loop_id}'.")
    return loop


@router.put("/{loop_id}", response_model=LoopDefinition)
def upsert_loop(
    loop_id: str,
    payload: LoopUpsertRequest,
    service: LoopService = Depends(get_loop_service),
) -> LoopDefinition:
    """Create or update a Loop definition."""
    loop = payload.loop.model_copy(update={"loop_id": loop_id})
    return service.upsert_loop(loop)


@router.post("/import", response_model=LoopDefinition, status_code=status.HTTP_201_CREATED)
def import_loop(
    payload: LoopImportRequest,
    service: LoopService = Depends(get_loop_service),
) -> LoopDefinition:
    """Import a Loop from loop.md content."""
    return service.import_markdown(payload)


@router.get("/{loop_id}/markdown", response_model=LoopMarkdownExport)
def export_loop_markdown(
    loop_id: str,
    service: LoopService = Depends(get_loop_service),
) -> LoopMarkdownExport:
    """Export a Loop as portable loop.md content."""
    exported = service.export_markdown(loop_id)
    if exported is None:
        raise HTTPException(status_code=404, detail=f"Unknown loop '{loop_id}'.")
    return exported


@router.post("/{loop_id}/improve", response_model=LoopDefinition)
def improve_loop(
    loop_id: str,
    payload: LoopImproveRequest,
    service: LoopService = Depends(get_loop_service),
) -> LoopDefinition:
    """Record one improvement pass for a Loop."""
    loop = service.improve_loop(loop_id, payload)
    if loop is None:
        raise HTTPException(status_code=404, detail=f"Unknown loop '{loop_id}'.")
    return loop
