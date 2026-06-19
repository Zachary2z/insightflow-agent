from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4


DEFAULT_ACTION_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "action_ops.db"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _trace_event(tool_name: str, summary: str, status: str, latency_ms: int, error: str | None = None) -> dict[str, Any]:
    event = {
        "tool_name": tool_name,
        "tool_input_summary": summary[:200],
        "tool_output_summary": status if not error else error[:200],
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "action_tool_error"
        event["error"] = error
    return event


def ensure_action_tables(db_path: str | Path = DEFAULT_ACTION_DB_PATH) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                owner TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_alerts (
                alert_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                condition TEXT NOT NULL,
                threshold TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_drafts (
                draft_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _failure(tool_name: str, started_at: float, summary: str, error: str) -> dict[str, Any]:
    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": False,
        "error": error,
        "trace_event": _trace_event(tool_name, summary, "error", latency_ms, error),
    }


def create_task(db_path: str | Path, task: dict[str, Any]) -> dict[str, Any]:
    started_at = perf_counter()
    summary = f"run_id={task.get('run_id', '')} title={task.get('title', '')}"
    try:
        ensure_action_tables(db_path)
        task_id = task.get("task_id") or _new_id("task")
        payload_json = json.dumps(task, ensure_ascii=False, sort_keys=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO tasks (task_id, run_id, title, description, owner, priority, status, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    str(task.get("run_id", "run_unknown")),
                    str(task.get("title", "")),
                    str(task.get("description", "")),
                    str(task.get("owner", "运营团队")),
                    str(task.get("priority", "medium")),
                    "created",
                    payload_json,
                ),
            )
    except Exception as exc:
        return _failure("create_task", started_at, summary, str(exc))

    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": True,
        "action_type": "create_task",
        "task_id": task_id,
        "record_id": task_id,
        "status": "created",
        "trace_event": _trace_event("create_task", summary, "success", latency_ms),
    }


def create_metric_alert(db_path: str | Path, alert: dict[str, Any]) -> dict[str, Any]:
    started_at = perf_counter()
    summary = f"run_id={alert.get('run_id', '')} metric={alert.get('metric_name', '')}"
    try:
        ensure_action_tables(db_path)
        alert_id = alert.get("alert_id") or _new_id("alert")
        payload_json = json.dumps(alert, ensure_ascii=False, sort_keys=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO metric_alerts (alert_id, run_id, metric_name, condition, threshold, description, status, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert_id,
                    str(alert.get("run_id", "run_unknown")),
                    str(alert.get("metric_name", "")),
                    str(alert.get("condition", "below")),
                    str(alert.get("threshold", "")),
                    str(alert.get("description", "")),
                    "created",
                    payload_json,
                ),
            )
    except Exception as exc:
        return _failure("create_metric_alert", started_at, summary, str(exc))

    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": True,
        "action_type": "create_metric_alert",
        "alert_id": alert_id,
        "record_id": alert_id,
        "status": "created",
        "trace_event": _trace_event("create_metric_alert", summary, "success", latency_ms),
    }


def create_email_draft(db_path: str | Path, draft: dict[str, Any]) -> dict[str, Any]:
    started_at = perf_counter()
    summary = f"run_id={draft.get('run_id', '')} subject={draft.get('subject', '')}"
    try:
        ensure_action_tables(db_path)
        draft_id = draft.get("draft_id") or _new_id("draft")
        payload_json = json.dumps(draft, ensure_ascii=False, sort_keys=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO email_drafts (draft_id, run_id, recipient, subject, body, status, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft_id,
                    str(draft.get("run_id", "run_unknown")),
                    str(draft.get("recipient", "")),
                    str(draft.get("subject", "")),
                    str(draft.get("body", "")),
                    "created",
                    payload_json,
                ),
            )
    except Exception as exc:
        return _failure("create_email_draft", started_at, summary, str(exc))

    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": True,
        "action_type": "create_email_draft",
        "draft_id": draft_id,
        "record_id": draft_id,
        "status": "created",
        "trace_event": _trace_event("create_email_draft", summary, "success", latency_ms),
    }


def _record_exists(conn: sqlite3.Connection, action_type: str, record_id: str) -> bool:
    table_and_column = {
        "create_task": ("tasks", "task_id"),
        "create_metric_alert": ("metric_alerts", "alert_id"),
        "create_email_draft": ("email_drafts", "draft_id"),
    }.get(action_type)
    if not table_and_column:
        return False
    table, column = table_and_column
    return conn.execute(f"SELECT 1 FROM {table} WHERE {column} = ? LIMIT 1", (record_id,)).fetchone() is not None


def verify_action_execution(db_path: str | Path, created_actions: list[dict[str, Any]]) -> dict[str, Any]:
    started_at = perf_counter()
    summary = f"{len(created_actions)} actions"
    try:
        ensure_action_tables(db_path)
        verified_actions = []
        missing_actions = []
        with sqlite3.connect(db_path) as conn:
            for action in created_actions:
                action_type = str(action.get("action_type", ""))
                record_id = str(action.get("record_id", ""))
                if record_id and _record_exists(conn, action_type, record_id):
                    verified_actions.append({**action, "verified": True})
                else:
                    missing_actions.append({**action, "verified": False})
    except Exception as exc:
        return _failure("verify_action_execution", started_at, summary, str(exc))

    latency_ms = int((perf_counter() - started_at) * 1000)
    success = not missing_actions
    return {
        "success": success,
        "verified_actions": verified_actions,
        "missing_actions": missing_actions,
        "trace_event": _trace_event(
            "verify_action_execution",
            summary,
            "success" if success else "error",
            latency_ms,
            None if success else "one or more actions were not found",
        ),
    }
