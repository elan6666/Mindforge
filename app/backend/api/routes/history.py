"""Task history query endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.backend.schemas.history import TaskHistoryDetail, TaskHistorySummary
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
