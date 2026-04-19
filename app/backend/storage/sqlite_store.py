"""SQLite-backed persistence helpers for task history and approvals."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SQLiteStore:
    """Small SQLite wrapper used by Phase 8 history services."""

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        """Create the database schema when it does not yet exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS task_runs (
                    task_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    task_type TEXT,
                    preset_mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider TEXT,
                    message TEXT NOT NULL,
                    output_text TEXT NOT NULL DEFAULT '',
                    error_message TEXT,
                    repo_path TEXT,
                    request_payload TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    requires_approval INTEGER NOT NULL DEFAULT 0,
                    approval_status TEXT,
                    coordinator_model_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stage_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    stage_order INTEGER NOT NULL,
                    stage_id TEXT NOT NULL,
                    stage_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    model TEXT NOT NULL,
                    provider TEXT,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    output_text TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES task_runs(task_id)
                );

                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    actions_json TEXT NOT NULL DEFAULT '[]',
                    decision_comment TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES task_runs(task_id)
                );
                """
            )

    def upsert_task_run(self, record: dict[str, Any]) -> None:
        """Insert or update one task row."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO task_runs (
                    task_id,
                    prompt,
                    task_type,
                    preset_mode,
                    status,
                    provider,
                    message,
                    output_text,
                    error_message,
                    repo_path,
                    request_payload,
                    metadata_json,
                    requires_approval,
                    approval_status,
                    coordinator_model_id,
                    created_at,
                    updated_at
                ) VALUES (
                    :task_id,
                    :prompt,
                    :task_type,
                    :preset_mode,
                    :status,
                    :provider,
                    :message,
                    :output_text,
                    :error_message,
                    :repo_path,
                    :request_payload,
                    :metadata_json,
                    :requires_approval,
                    :approval_status,
                    :coordinator_model_id,
                    :created_at,
                    :updated_at
                )
                ON CONFLICT(task_id) DO UPDATE SET
                    prompt = excluded.prompt,
                    task_type = excluded.task_type,
                    preset_mode = excluded.preset_mode,
                    status = excluded.status,
                    provider = excluded.provider,
                    message = excluded.message,
                    output_text = excluded.output_text,
                    error_message = excluded.error_message,
                    repo_path = excluded.repo_path,
                    request_payload = excluded.request_payload,
                    metadata_json = excluded.metadata_json,
                    requires_approval = excluded.requires_approval,
                    approval_status = excluded.approval_status,
                    coordinator_model_id = excluded.coordinator_model_id,
                    updated_at = excluded.updated_at
                """,
                record,
            )

    def replace_stage_runs(self, task_id: str, records: list[dict[str, Any]]) -> None:
        """Replace all stage rows for one task."""
        with self._connect() as connection:
            connection.execute("DELETE FROM stage_runs WHERE task_id = ?", (task_id,))
            if not records:
                return
            connection.executemany(
                """
                INSERT INTO stage_runs (
                    task_id,
                    stage_order,
                    stage_id,
                    stage_name,
                    role,
                    model,
                    provider,
                    status,
                    summary,
                    output_text,
                    metadata_json,
                    error_message,
                    created_at
                ) VALUES (
                    :task_id,
                    :stage_order,
                    :stage_id,
                    :stage_name,
                    :role,
                    :model,
                    :provider,
                    :status,
                    :summary,
                    :output_text,
                    :metadata_json,
                    :error_message,
                    :created_at
                )
                """,
                records,
            )

    def upsert_approval(self, record: dict[str, Any]) -> None:
        """Insert or update one approval row."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO approvals (
                    approval_id,
                    task_id,
                    status,
                    risk_level,
                    summary,
                    actions_json,
                    decision_comment,
                    created_at,
                    updated_at
                ) VALUES (
                    :approval_id,
                    :task_id,
                    :status,
                    :risk_level,
                    :summary,
                    :actions_json,
                    :decision_comment,
                    :created_at,
                    :updated_at
                )
                ON CONFLICT(task_id) DO UPDATE SET
                    approval_id = excluded.approval_id,
                    status = excluded.status,
                    risk_level = excluded.risk_level,
                    summary = excluded.summary,
                    actions_json = excluded.actions_json,
                    decision_comment = excluded.decision_comment,
                    updated_at = excluded.updated_at
                """,
                record,
            )

    def list_task_runs(self, status: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
        """Return recent task rows."""
        query = "SELECT * FROM task_runs"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY datetime(created_at) DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._normalize_task_row(row) for row in rows]

    def get_task_run(self, task_id: str) -> dict[str, Any] | None:
        """Fetch one task row by id."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM task_runs WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return self._normalize_task_row(row) if row is not None else None

    def get_stage_runs(self, task_id: str) -> list[dict[str, Any]]:
        """Fetch persisted stages for one task."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM stage_runs
                WHERE task_id = ?
                ORDER BY stage_order ASC, id ASC
                """,
                (task_id,),
            ).fetchall()
        return [self._normalize_stage_row(row) for row in rows]

    def get_approval(self, task_id: str) -> dict[str, Any] | None:
        """Fetch one approval row by task id."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM approvals WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return self._normalize_approval_row(row) if row is not None else None

    def list_pending_approvals(self) -> list[dict[str, Any]]:
        """Return all pending approvals ordered by creation time."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM approvals
                WHERE status = 'pending'
                ORDER BY datetime(created_at) DESC
                """
            ).fetchall()
        return [self._normalize_approval_row(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _normalize_task_row(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        payload["request_payload"] = json.loads(payload["request_payload"])
        payload["metadata_json"] = json.loads(payload["metadata_json"])
        payload["requires_approval"] = bool(payload["requires_approval"])
        return payload

    @staticmethod
    def _normalize_stage_row(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        payload["metadata_json"] = json.loads(payload["metadata_json"])
        return payload

    @staticmethod
    def _normalize_approval_row(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        payload["actions_json"] = json.loads(payload["actions_json"])
        return payload
