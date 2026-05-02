"""Task history query endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.backend.schemas.history import (
    CanvasArtifactUpdate,
    TaskHistoryDetail,
    TaskHistorySummary,
)
from app.backend.services.history_service import HistoryService, get_history_service

router = APIRouter()


@router.get("/tasks", response_model=list[TaskHistorySummary])
def list_history_tasks(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=30, ge=1, le=100),
    service: HistoryService = Depends(get_history_service),
) -> list[TaskHistorySummary]:
    """Return recent task history rows."""
    return service.list_tasks(status=status_filter, limit=limit)


@router.get("/tasks/{task_id}", response_model=TaskHistoryDetail)
def get_history_task_detail(
    task_id: str,
    service: HistoryService = Depends(get_history_service),
) -> TaskHistoryDetail:
    """Return one task history detail record."""
    detail = service.get_task_detail(task_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown task '{task_id}'.",
        )
    return detail


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_task(
    task_id: str,
    service: HistoryService = Depends(get_history_service),
) -> None:
    """Delete one task history row."""
    if not service.delete_task(task_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown task '{task_id}'.",
        )


@router.patch(
    "/tasks/{task_id}/canvas-artifacts/{artifact_id}",
    response_model=TaskHistoryDetail,
)
def update_canvas_artifact(
    task_id: str,
    artifact_id: str,
    payload: CanvasArtifactUpdate,
    service: HistoryService = Depends(get_history_service),
) -> TaskHistoryDetail:
    """Update one editable canvas artifact in task history."""
    try:
        detail = service.update_canvas_artifact(
            task_id,
            artifact_id,
            content=payload.content,
            title=payload.title,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown task '{task_id}'.",
        )
    return detail


@router.get("/conversations/{conversation_id}/tasks", response_model=list[TaskHistoryDetail])
def list_conversation_task_details(
    conversation_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    service: HistoryService = Depends(get_history_service),
) -> list[TaskHistoryDetail]:
    """Return all persisted task turns for one conversation."""
    details = service.list_conversation_tasks(conversation_id, limit=limit)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown conversation '{conversation_id}'.",
        )
    return details


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation_history(
    conversation_id: str,
    service: HistoryService = Depends(get_history_service),
) -> None:
    """Delete all task turns in one conversation."""
    if service.delete_conversation(conversation_id) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown conversation '{conversation_id}'.",
        )
