"""Task submission endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.backend.schemas.history import TaskHistoryDetail
from app.backend.schemas.task import (
    LoopStageRetryRequest,
    TaskErrorResponse,
    TaskRequest,
    TaskResponse,
)
from app.backend.services.task_service import TaskService, get_task_service

router = APIRouter()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_200_OK)
def submit_task(
    payload: TaskRequest,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse | JSONResponse:
    """Submit a task through the normalized service layer."""
    result = service.submit(payload)
    if result.status == "failed" and result.error_message:
        error_payload = TaskErrorResponse(
            message=result.message,
            error_message=result.error_message,
            metadata=result.data.metadata,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_payload.model_dump(),
        )
    return result


@router.post(
    "/{task_id}/loops/stages/{stage_id}/retry",
    response_model=TaskHistoryDetail,
    status_code=status.HTTP_200_OK,
)
def retry_loop_stage(
    task_id: str,
    stage_id: str,
    payload: LoopStageRetryRequest,
    service: TaskService = Depends(get_task_service),
) -> TaskHistoryDetail:
    """Retry one stage from a persisted Loop run."""
    try:
        return service.retry_loop_stage(task_id, stage_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
