from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from tools.action_tool import DEFAULT_ACTION_DB_PATH, ensure_action_tables


def _trace_event(status: str, summary: str, latency_ms: int, error: str | None = None) -> dict[str, Any]:
    event = {
        "tool_name": "record_approval",
        "tool_input_summary": summary[:200],
        "tool_output_summary": status if not error else error[:200],
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "approval_tool_error"
        event["error"] = error
    return event


def ensure_approval_table(db_path: str | Path = DEFAULT_ACTION_DB_PATH) -> None:
    ensure_action_tables(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                approval_status TEXT NOT NULL,
                approved_by TEXT NOT NULL,
                reason TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def record_approval(db_path: str | Path, approval: dict[str, Any]) -> dict[str, Any]:
    started_at = perf_counter()
    summary = f"run_id={approval.get('run_id', '')} status={approval.get('approval_status', '')}"
    try:
        ensure_approval_table(db_path)
        approval_id = approval.get("approval_id") or f"approval_{uuid4().hex[:12]}"
        approval_status = str(approval.get("approval_status", "pending"))
        payload_json = json.dumps(approval, ensure_ascii=False, sort_keys=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO approvals (approval_id, run_id, approval_status, approved_by, reason, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    str(approval.get("run_id", "run_unknown")),
                    approval_status,
                    str(approval.get("approved_by", "")),
                    str(approval.get("reason", "")),
                    payload_json,
                ),
            )
    except Exception as exc:
        latency_ms = int((perf_counter() - started_at) * 1000)
        return {
            "success": False,
            "approval_id": "",
            "approval_status": "",
            "error": str(exc),
            "trace_event": _trace_event("error", summary, latency_ms, str(exc)),
        }

    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": True,
        "approval_id": approval_id,
        "approval_status": approval_status,
        "approved_by": str(approval.get("approved_by", "")),
        "trace_event": _trace_event("success", summary, latency_ms),
    }
