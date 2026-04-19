"""Approval endpoints for blocking task execution."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.backend.schemas.approval import ApprovalDecisionRequest, ApprovalRecord
from app.backend.schemas.task import TaskResponse
from app.backend.services.approval_service import (
    ApprovalError,
    ApprovalService,
    get_approval_service,
)
from app.backend.services.task_service import TaskService, get_task_service

router = APIRouter()


@router.get("/pending", response_model=list[ApprovalRecord])
def list_pending_approvals(
    service: ApprovalService = Depends(get_approval_service),
) -> list[ApprovalRecord]:
    """Return pending approvals only."""
    return service.list_pending()


@router.post("/{task_id}/approve", response_model=TaskResponse)
def approve_task(
    task_id: str,
    payload: ApprovalDecisionRequest,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Approve a pending task and continue execution."""
    try:
        return service.approve(task_id, comment=payload.comment)
    except ApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{task_id}/reject", response_model=TaskResponse)
def reject_task(
    task_id: str,
    payload: ApprovalDecisionRequest,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Reject a pending task and mark it as closed."""
    try:
        return service.reject(task_id, comment=payload.comment)
    except ApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
