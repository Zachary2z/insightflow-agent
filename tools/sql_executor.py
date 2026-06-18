from __future__ import annotations

import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Any

import sqlglot
from sqlglot import exp
import sqlparse


def _trace_event(sql: str, status: str, latency_ms: int, summary: str, error: str | None = None) -> dict[str, Any]:
    event = {
        "tool_name": "run_sql",
        "tool_input_summary": sql[:120],
        "tool_output_summary": summary,
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "sql_execution_error"
        event["error"] = error
    return event


def _failure(sql: str, error: str, started_at: float) -> dict[str, Any]:
    execution_time_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": False,
        "columns": [],
        "rows": [],
        "row_count": 0,
        "truncated": False,
        "error": error,
        "execution_time_ms": execution_time_ms,
        "trace_event": _trace_event(sql, "error", execution_time_ms, error, error),
    }


def _is_single_select(sql: str) -> tuple[bool, str | None]:
    statements = [statement for statement in sqlparse.split(sql) if statement.strip()]
    if len(statements) != 1:
        return False, "Multiple SQL statements are not allowed"

    try:
        expression = sqlglot.parse_one(sql, read="sqlite")
    except Exception as exc:
        return False, f"SQL parse error: {exc}"

    if not isinstance(expression, exp.Select):
        return False, "Only SELECT queries are allowed"

    return True, None


def _timed_out(started_at: float, timeout_seconds: int) -> bool:
    return perf_counter() - started_at > timeout_seconds


def run_sql(
    db_path: str | Path,
    sql: str,
    timeout_seconds: int = 5,
    max_rows: int = 100,
) -> dict[str, Any]:
    started_at = perf_counter()
    path = Path(db_path)

    if not path.exists():
        return _failure(sql, f"Database file not found: {path}", started_at)

    is_select, validation_error = _is_single_select(sql)
    if not is_select:
        return _failure(sql, validation_error or "Only SELECT queries are allowed", started_at)

    try:
        with sqlite3.connect(path) as conn:
            conn.execute("PRAGMA query_only = ON")

            def progress_handler() -> int:
                return 1 if _timed_out(started_at, timeout_seconds) else 0

            conn.set_progress_handler(progress_handler, 1000)
            cursor = conn.execute(sql)
            columns = [description[0] for description in cursor.description or []]
            fetched_rows = cursor.fetchmany(max_rows + 1)
            truncated = len(fetched_rows) > max_rows
            rows = [list(row) for row in fetched_rows[:max_rows]]
    except Exception as exc:
        return _failure(sql, str(exc), started_at)

    execution_time_ms = int((perf_counter() - started_at) * 1000)
    row_count = len(rows)
    return {
        "success": True,
        "columns": columns,
        "rows": rows,
        "row_count": row_count,
        "truncated": truncated,
        "execution_time_ms": execution_time_ms,
        "trace_event": _trace_event(sql, "success", execution_time_ms, f"{row_count} rows returned"),
    }
