"""SQLite-backed task history persistence service."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from uuid import uuid4

from app.backend.core.config import Settings, get_settings
from app.backend.schemas.approval import ApprovalRecord, ApprovalRequirement
from app.backend.schemas.history import (
    StageHistoryRecord,
    TaskHistoryDetail,
    TaskHistorySummary,
)
from app.backend.schemas.task import TaskRequest, TaskResponse
from app.backend.storage.sqlite_store import SQLiteStore


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class HistoryService:
    """Persist and query task/stage execution history."""

    def __init__(self, settings: Settings) -> None:
        self.store = SQLiteStore(settings.sqlite_db_path)
        self.store.initialize()

    def create_pending_task(
        self,
        task_id: str,
        request: TaskRequest,
        metadata: dict[str, object],
        approval_requirement: ApprovalRequirement,
    ) -> ApprovalRecord:
        """Persist a newly gated task waiting for approval."""
        timestamp = _utc_now()
        self.store.upsert_task_run(
            {
                "task_id": task_id,
                "prompt": request.prompt,
                "task_type": request.task_type,
                "preset_mode": metadata.get("resolved_preset_mode") or request.preset_mode or "default",
                "status": "pending_approval",
                "provider": "mindforge-approval-gate",
                "message": "Task is waiting for approval.",
                "output_text": "",
                "error_message": None,
                "repo_path": request.repo_path,
                "request_payload": json.dumps(request.model_dump(mode="json")),
                "metadata_json": json.dumps(metadata),
                "requires_approval": 1,
                "approval_status": "pending",
                "coordinator_model_id": (
                    metadata.get("task_model_selection", {}) or {}
                ).get("model_id"),
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )
        approval = ApprovalRecord(
            approval_id=str(uuid4()),
            task_id=task_id,
            status="pending",
            risk_level=approval_requirement.risk_level,
            summary=approval_requirement.summary,
            actions=approval_requirement.actions,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.store.upsert_approval(
            {
                "approval_id": approval.approval_id,
                "task_id": approval.task_id,
                "status": approval.status,
                "risk_level": approval.risk_level,
                "summary": approval.summary,
                "actions_json": json.dumps(approval.actions),
                "decision_comment": approval.decision_comment,
                "created_at": approval.created_at,
                "updated_at": approval.updated_at,
            }
        )
        return approval

    def record_task_result(
        self,
        task_id: str,
        request: TaskRequest,
        response: TaskResponse,
    ) -> None:
        """Persist a completed, failed, or rejected task response."""
        current = self.store.get_task_run(task_id)
        approval = self.store.get_approval(task_id)
        timestamp = _utc_now()
        metadata = dict(response.data.metadata)
        self.store.upsert_task_run(
            {
                "task_id": task_id,
                "prompt": request.prompt,
                "task_type": request.task_type,
                "preset_mode": metadata.get("resolved_preset_mode") or request.preset_mode or "default",
                "status": response.status,
                "provider": response.data.provider,
                "message": response.message,
                "output_text": response.data.output,
                "error_message": response.error_message,
                "repo_path": request.repo_path,
                "request_payload": json.dumps(request.model_dump(mode="json")),
                "metadata_json": json.dumps(metadata),
                "requires_approval": 1 if approval is not None else int((current or {}).get("requires_approval", False)),
                "approval_status": approval["status"] if approval is not None else None,
                "coordinator_model_id": (
                    metadata.get("task_model_selection", {}) or {}
                ).get("model_id"),
                "created_at": (current or {}).get("created_at", timestamp),
                "updated_at": timestamp,
            }
        )
        stages = (
            metadata.get("orchestration", {}) or {}
        ).get("stages", [])
        self.store.replace_stage_runs(
            task_id,
            [
                {
                    "task_id": task_id,
                    "stage_order": stage["order"],
                    "stage_id": stage["stage_id"],
                    "stage_name": stage["stage_name"],
                    "role": stage["role"],
                    "model": stage["model"],
                    "provider": stage.get("provider"),
                    "status": stage["status"],
                    "summary": stage["summary"],
                    "output_text": stage["output"],
                    "metadata_json": json.dumps(stage.get("metadata", {})),
                    "error_message": stage.get("error_message"),
                    "created_at": timestamp,
                }
                for stage in stages
            ],
        )

    def list_tasks(self, status: str | None = None, limit: int = 30) -> list[TaskHistorySummary]:
        """Return recent task history rows."""
        return [
            self._task_summary_from_row(row)
            for row in self.store.list_task_runs(status=status, limit=limit)
        ]

    def list_conversation_tasks(
        self,
        conversation_id: str,
        *,
        limit: int = 200,
    ) -> list[TaskHistoryDetail]:
        """Return task turns belonging to one conversation, oldest first."""
        rows = [
            row
            for row in self.store.list_task_runs(limit=limit)
            if self._conversation_id_from_row(row) == conversation_id
        ]
        rows.sort(key=lambda row: row["created_at"])
        details = [self.get_task_detail(row["task_id"]) for row in rows]
        return [detail for detail in details if detail is not None]

    def delete_task(self, task_id: str) -> bool:
        """Delete a single task history row."""
        return self.store.delete_task_run(task_id)

    def delete_conversation(self, conversation_id: str) -> int:
        """Delete every task turn belonging to one conversation."""
        task_ids = [
            str(row["task_id"])
            for row in self.store.list_all_task_runs()
            if self._conversation_id_from_row(row) == conversation_id
        ]
        return self.store.delete_task_runs(task_ids)

    def update_canvas_artifact(
        self,
        task_id: str,
        artifact_id: str,
        *,
        content: object,
        title: str | None = None,
    ) -> TaskHistoryDetail | None:
        """Update one editable canvas artifact stored in task metadata."""
        current = self.store.get_task_run(task_id)
        if current is None:
            return None
        metadata = dict(current["metadata_json"])
        artifacts = metadata.get("canvas_artifacts")
        if not isinstance(artifacts, list):
            raise ValueError(f"Task '{task_id}' has no canvas artifacts.")

        timestamp = _utc_now()
        updated = False
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            if str(artifact.get("artifact_id")) != artifact_id:
                continue
            if artifact.get("editable") is False:
                raise PermissionError(f"Canvas artifact '{artifact_id}' is read-only.")
            versions = artifact.get("versions")
            if not isinstance(versions, list):
                previous_updated_at = str(
                    artifact.get("updated_at") or current["updated_at"] or timestamp
                )
                versions = [
                    {
                        "version": int(artifact.get("version") or 1),
                        "title": str(artifact.get("title") or ""),
                        "content": artifact.get("content"),
                        "updated_at": previous_updated_at,
                        "source": artifact.get("source") or "existing",
                    }
                ]
            next_version = max(
                [
                    int(version.get("version") or 0)
                    for version in versions
                    if isinstance(version, dict)
                ]
                or [0]
            ) + 1
            artifact["content"] = content
            if title is not None:
                artifact["title"] = title
            artifact["updated_at"] = timestamp
            artifact["version"] = next_version
            versions.append(
                {
                    "version": next_version,
                    "title": str(artifact.get("title") or ""),
                    "content": content,
                    "updated_at": timestamp,
                    "source": "manual-edit",
                }
            )
            artifact["versions"] = versions[-25:]
            updated = True
            break
        if not updated:
            raise ValueError(f"Unknown canvas artifact '{artifact_id}'.")

        metadata["canvas_artifacts"] = artifacts
        self.store.upsert_task_run(
            {
                "task_id": current["task_id"],
                "prompt": current["prompt"],
                "task_type": current["task_type"],
                "preset_mode": current["preset_mode"],
                "status": current["status"],
                "provider": current["provider"],
                "message": current["message"],
                "output_text": current["output_text"],
                "error_message": current["error_message"],
                "repo_path": current["repo_path"],
                "request_payload": json.dumps(current["request_payload"]),
                "metadata_json": json.dumps(metadata),
                "requires_approval": int(current["requires_approval"]),
                "approval_status": current["approval_status"],
                "coordinator_model_id": current["coordinator_model_id"],
                "created_at": current["created_at"],
                "updated_at": timestamp,
            }
        )
        return self.get_task_detail(task_id)

    def get_task_detail(self, task_id: str) -> TaskHistoryDetail | None:
        """Return one task detail including persisted stages and approval."""
        row = self.store.get_task_run(task_id)
        if row is None:
            return None
        approval_row = self.store.get_approval(task_id)
        return TaskHistoryDetail(
            task_id=row["task_id"],
            prompt=row["prompt"],
            preset_mode=row["preset_mode"],
            task_type=row["task_type"],
            status=row["status"],
            provider=row["provider"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            requires_approval=row["requires_approval"],
            approval_status=row["approval_status"],
            repo_path=row["repo_path"],
            message=row["message"],
            output=row["output_text"],
            error_message=row["error_message"],
            request_payload=row["request_payload"],
            metadata=row["metadata_json"],
            stages=[
                StageHistoryRecord(
                    order=stage["stage_order"],
                    stage_id=stage["stage_id"],
                    stage_name=stage["stage_name"],
                    role=stage["role"],
                    model=stage["model"],
                    provider=stage["provider"],
                    status=stage["status"],
                    summary=stage["summary"],
                    output=stage["output_text"],
                    metadata=stage["metadata_json"],
                    error_message=stage["error_message"],
                    created_at=stage["created_at"],
                )
                for stage in self.store.get_stage_runs(task_id)
            ],
            approval=(
                ApprovalRecord(
                    approval_id=approval_row["approval_id"],
                    task_id=approval_row["task_id"],
                    status=approval_row["status"],
                    risk_level=approval_row["risk_level"],
                    summary=approval_row["summary"],
                    actions=approval_row["actions_json"],
                    decision_comment=approval_row["decision_comment"],
                    created_at=approval_row["created_at"],
                    updated_at=approval_row["updated_at"],
                )
                if approval_row is not None
                else None
            ),
        )

    @staticmethod
    def _conversation_id_from_row(row: dict[str, object]) -> str | None:
        metadata = row.get("metadata_json")
        if isinstance(metadata, dict) and isinstance(metadata.get("conversation_id"), str):
            return metadata["conversation_id"]
        request_payload = row.get("request_payload")
        if isinstance(request_payload, dict) and isinstance(
            request_payload.get("conversation_id"),
            str,
        ):
            return request_payload["conversation_id"]
        return None

    def _task_summary_from_row(self, row: dict[str, object]) -> TaskHistorySummary:
        metadata = row.get("metadata_json")
        conversation_turn_count = None
        if isinstance(metadata, dict) and isinstance(
            metadata.get("conversation_turn_count"),
            int,
        ):
            conversation_turn_count = metadata["conversation_turn_count"]
        conversation_id = self._conversation_id_from_row(row)
        if conversation_turn_count is None and conversation_id:
            if isinstance(metadata, dict) and isinstance(
                metadata.get("conversation_history"),
                list,
            ):
                conversation_turn_count = len(metadata["conversation_history"]) + 1
            else:
                conversation_turn_count = 1
        return TaskHistorySummary(
            task_id=str(row["task_id"]),
            prompt=str(row["prompt"]),
            preset_mode=str(row["preset_mode"]),
            task_type=row["task_type"] if isinstance(row["task_type"], str) else None,
            status=str(row["status"]),
            provider=row["provider"] if isinstance(row["provider"], str) else None,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            requires_approval=bool(row["requires_approval"]),
            approval_status=(
                row["approval_status"]
                if isinstance(row["approval_status"], str)
                else None
            ),
            conversation_id=conversation_id,
            conversation_turn_count=conversation_turn_count,
        )

    def list_pending_approvals(self) -> list[ApprovalRecord]:
        """Return pending approvals only."""
        return [
            ApprovalRecord(
                approval_id=row["approval_id"],
                task_id=row["task_id"],
                status=row["status"],
                risk_level=row["risk_level"],
                summary=row["summary"],
                actions=row["actions_json"],
                decision_comment=row["decision_comment"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in self.store.list_pending_approvals()
        ]

    def update_approval(
        self,
        task_id: str,
        *,
        status: str,
        comment: str | None = None,
    ) -> ApprovalRecord:
        """Update approval status for one task."""
        row = self.store.get_approval(task_id)
        if row is None:
            raise ValueError(f"Task '{task_id}' has no approval record.")
        updated = ApprovalRecord(
            approval_id=row["approval_id"],
            task_id=task_id,
            status=status,
            risk_level=row["risk_level"],
            summary=row["summary"],
            actions=row["actions_json"],
            decision_comment=comment,
            created_at=row["created_at"],
            updated_at=_utc_now(),
        )
        self.store.upsert_approval(
            {
                "approval_id": updated.approval_id,
                "task_id": updated.task_id,
                "status": updated.status,
                "risk_level": updated.risk_level,
                "summary": updated.summary,
                "actions_json": json.dumps(updated.actions),
                "decision_comment": updated.decision_comment,
                "created_at": updated.created_at,
                "updated_at": updated.updated_at,
            }
        )
        current = self.store.get_task_run(task_id)
        if current is not None:
            self.store.upsert_task_run(
                {
                    "task_id": current["task_id"],
                    "prompt": current["prompt"],
                    "task_type": current["task_type"],
                    "preset_mode": current["preset_mode"],
                    "status": current["status"],
                    "provider": current["provider"],
                    "message": current["message"],
                    "output_text": current["output_text"],
                    "error_message": current["error_message"],
                    "repo_path": current["repo_path"],
                    "request_payload": json.dumps(current["request_payload"]),
                    "metadata_json": json.dumps(current["metadata_json"]),
                    "requires_approval": int(current["requires_approval"]),
                    "approval_status": updated.status,
                    "coordinator_model_id": current["coordinator_model_id"],
                    "created_at": current["created_at"],
                    "updated_at": updated.updated_at,
                }
            )
        return updated


@lru_cache(maxsize=1)
def get_history_service() -> HistoryService:
    """Return cached history service."""
    return HistoryService(get_settings())


def clear_history_service_cache() -> None:
    """Clear cached history service after storage-path changes."""
    get_history_service.cache_clear()
