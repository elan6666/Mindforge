"""Approval decision helpers for high-risk task gates."""

from functools import lru_cache

from app.backend.schemas.approval import ApprovalRecord, ApprovalRequirement
from app.backend.schemas.model import ModelSelection
from app.backend.schemas.preset import PresetDefinition
from app.backend.schemas.rule_template import RuleTemplateSelection
from app.backend.schemas.task import TaskRequest
from app.backend.services.history_service import HistoryService, get_history_service


class ApprovalError(ValueError):
    """Raised when approval state changes are invalid."""


class ApprovalService:
    """Evaluate and mutate approval requirements."""

    def __init__(self, history_service: HistoryService) -> None:
        self.history_service = history_service

    def evaluate_requirement(
        self,
        payload: TaskRequest,
        preset: PresetDefinition,
        task_model_selection: ModelSelection,
        rule_template_selection: RuleTemplateSelection | None,
    ) -> ApprovalRequirement:
        """Return whether the task should stop at an approval gate."""
        metadata = payload.metadata
        actions = [
            str(item)
            for item in (
                metadata.get("approval_actions")
                or metadata.get("high_risk_actions")
                or []
            )
            if str(item).strip()
        ]
        execution_mode = str(metadata.get("execution_mode") or "").strip().lower()
        if execution_mode in {"write", "shell", "batch-write"} and execution_mode not in actions:
            actions.append(execution_mode)
        explicit_requires_approval = bool(metadata.get("requires_approval"))
        required = explicit_requires_approval or bool(actions)
        if not required:
            return ApprovalRequirement(required=False)

        risk_level = str(metadata.get("risk_level") or "high")
        summary = str(metadata.get("approval_summary") or "").strip()
        if not summary:
            summary = (
                f"High-risk task requires approval before execution. "
                f"Preset: {preset.display_name}. Coordinator model: {task_model_selection.display_name}."
            )
            if rule_template_selection is not None:
                summary += f" Rule template: {rule_template_selection.display_name}."
        if not actions:
            actions = ["high-risk execution"]
        return ApprovalRequirement(
            required=True,
            risk_level=risk_level,
            summary=summary,
            actions=actions,
        )

    def list_pending(self) -> list[ApprovalRecord]:
        """Return pending approvals."""
        return self.history_service.list_pending_approvals()

    def approve(self, task_id: str, comment: str | None = None) -> ApprovalRecord:
        """Mark a pending approval as approved."""
        detail = self.history_service.get_task_detail(task_id)
        if detail is None:
            raise ApprovalError(f"Unknown task '{task_id}'.")
        if detail.approval is None:
            raise ApprovalError(f"Task '{task_id}' has no approval record.")
        if detail.approval.status != "pending":
            raise ApprovalError(f"Task '{task_id}' is not waiting for approval.")
        return self.history_service.update_approval(task_id, status="approved", comment=comment)

    def reject(self, task_id: str, comment: str | None = None) -> ApprovalRecord:
        """Mark a pending approval as rejected."""
        detail = self.history_service.get_task_detail(task_id)
        if detail is None:
            raise ApprovalError(f"Unknown task '{task_id}'.")
        if detail.approval is None:
            raise ApprovalError(f"Task '{task_id}' has no approval record.")
        if detail.approval.status != "pending":
            raise ApprovalError(f"Task '{task_id}' is not waiting for approval.")
        return self.history_service.update_approval(task_id, status="rejected", comment=comment)


@lru_cache(maxsize=1)
def get_approval_service() -> ApprovalService:
    """Return cached approval service."""
    return ApprovalService(get_history_service())


def clear_approval_service_cache() -> None:
    """Clear cached approval service after storage-path changes."""
    get_approval_service.cache_clear()
