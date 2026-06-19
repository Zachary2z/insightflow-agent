from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from tools.approval_tool import ensure_approval_table
from tools.action_tool import DEFAULT_ACTION_DB_PATH


def _trace_event(summary: str, status: str, latency_ms: int, error: str | None = None) -> dict[str, Any]:
    event = {
        "tool_name": "log_audit_event",
        "tool_input_summary": summary[:200],
        "tool_output_summary": status if not error else error[:200],
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "audit_logger_error"
        event["error"] = error
    return event


def ensure_audit_table(db_path: str | Path = DEFAULT_ACTION_DB_PATH) -> None:
    ensure_approval_table(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                audit_log_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def log_audit_event(db_path: str | Path, event: dict[str, Any]) -> dict[str, Any]:
    started_at = perf_counter()
    summary = f"run_id={event.get('run_id', '')} event_type={event.get('event_type', '')}"
    try:
        ensure_audit_table(db_path)
        audit_log_id = event.get("audit_log_id") or f"audit_{uuid4().hex[:12]}"
        payload = event.get("payload", {})
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (audit_log_id, run_id, event_type, actor, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    audit_log_id,
                    str(event.get("run_id", "run_unknown")),
                    str(event.get("event_type", "")),
                    str(event.get("actor", "system")),
                    payload_json,
                ),
            )
    except Exception as exc:
        latency_ms = int((perf_counter() - started_at) * 1000)
        return {
            "success": False,
            "audit_log_id": "",
            "error": str(exc),
            "trace_event": _trace_event(summary, "error", latency_ms, str(exc)),
        }

    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": True,
        "audit_log_id": audit_log_id,
        "trace_event": _trace_event(summary, "success", latency_ms),
    }
