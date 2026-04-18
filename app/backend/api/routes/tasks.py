"""Task submission endpoints."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.backend.schemas.task import TaskErrorResponse, TaskRequest, TaskResponse
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
