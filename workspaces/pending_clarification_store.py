from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from workspaces.models import utc_now_iso
from workspaces.store import WorkspaceStore


class PendingClarificationNotFoundError(FileNotFoundError):
    pass


class PendingClarificationStore:
    def __init__(self, workspace_store: WorkspaceStore):
        self.workspace_store = workspace_store

    def create_pending_run(
        self,
        *,
        workspace_id: str,
        run_id: str,
        original_question: str,
        question_understanding: dict[str, Any],
        clarification_question: str,
        raw_result: dict[str, Any],
        missing_fields: list[str] | None = None,
        options: list[str] | None = None,
    ) -> dict[str, Any]:
        pending_run_id = f"pending_{uuid4().hex[:8]}"
        now = utc_now_iso()
        record = {
            "pending_run_id": pending_run_id,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "original_question": original_question,
            "system_understanding": _system_understanding(question_understanding),
            "question_understanding": question_understanding,
            "clarification_question": clarification_question,
            "missing_fields": list(missing_fields or question_understanding.get("missing_slots") or []),
            "options": list(options or []),
            "raw_result": _json_safe(raw_result),
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "clarification_answer": "",
            "resolved_question": "",
            "error": "",
        }
        self._write(workspace_id, pending_run_id, record)
        return record

    def load_pending_run(self, workspace_id: str, pending_run_id: str) -> dict[str, Any]:
        path = self._path(workspace_id, pending_run_id)
        if not path.exists():
            raise PendingClarificationNotFoundError(f"Pending clarification run not found: {pending_run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def complete_pending_run(
        self,
        *,
        workspace_id: str,
        pending_run_id: str,
        clarification_answer: str,
        resolved_question: str,
    ) -> dict[str, Any]:
        record = self.load_pending_run(workspace_id, pending_run_id)
        record.update(
            {
                "status": "completed",
                "clarification_answer": clarification_answer,
                "resolved_question": resolved_question,
                "updated_at": utc_now_iso(),
            }
        )
        self._write(workspace_id, pending_run_id, record)
        return record

    def mark_running(
        self,
        *,
        workspace_id: str,
        pending_run_id: str,
        clarification_answer: str,
        resolved_question: str,
    ) -> dict[str, Any]:
        record = self.load_pending_run(workspace_id, pending_run_id)
        record.update(
            {
                "status": "running",
                "clarification_answer": clarification_answer,
                "resolved_question": resolved_question,
                "error": "",
                "updated_at": utc_now_iso(),
            }
        )
        self._write(workspace_id, pending_run_id, record)
        return record

    def mark_pending_for_more_info(
        self,
        *,
        workspace_id: str,
        pending_run_id: str,
        clarification_answer: str,
        resolved_question: str,
        question_understanding: dict[str, Any],
        clarification_question: str,
        raw_result: dict[str, Any],
        missing_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        record = self.load_pending_run(workspace_id, pending_run_id)
        record.update(
            {
                "status": "pending",
                "clarification_answer": clarification_answer,
                "resolved_question": resolved_question,
                "question_understanding": question_understanding,
                "system_understanding": _system_understanding(question_understanding),
                "clarification_question": clarification_question,
                "missing_fields": list(missing_fields or question_understanding.get("missing_slots") or []),
                "raw_result": _json_safe(raw_result),
                "error": "",
                "updated_at": utc_now_iso(),
            }
        )
        self._write(workspace_id, pending_run_id, record)
        return record

    def mark_failed(
        self,
        *,
        workspace_id: str,
        pending_run_id: str,
        error: str,
    ) -> dict[str, Any]:
        record = self.load_pending_run(workspace_id, pending_run_id)
        record.update(
            {
                "status": "failed",
                "error": error,
                "updated_at": utc_now_iso(),
            }
        )
        self._write(workspace_id, pending_run_id, record)
        return record

    def _path(self, workspace_id: str, pending_run_id: str) -> Path:
        safe_id = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in pending_run_id)
        return self.workspace_store.resolve_workspace_path(workspace_id, Path("pending_runs") / f"{safe_id}.json")

    def _write(self, workspace_id: str, pending_run_id: str, record: dict[str, Any]) -> None:
        path = self._path(workspace_id, pending_run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def _system_understanding(question_understanding: dict[str, Any]) -> str:
    reason = question_understanding.get("reason")
    if reason:
        return str(reason)
    intent = question_understanding.get("intent")
    if isinstance(intent, dict) and intent:
        parts = [f"{key}={value}" for key, value in intent.items() if value not in (None, "", [])]
        if parts:
            return ", ".join(parts)
    if question_understanding:
        return json.dumps(question_understanding, ensure_ascii=False, sort_keys=True)
    return ""


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
