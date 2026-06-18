from __future__ import annotations

import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Any


def _trace_event(
    db_path: str | Path,
    table_count: int,
    status: str,
    latency_ms: int,
    error: str | None = None,
) -> dict[str, Any]:
    event = {
        "tool_name": "get_database_schema",
        "tool_input_summary": f"db_path={db_path}",
        "tool_output_summary": f"{table_count} tables loaded",
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "schema_load_error"
        event["error"] = error
    return event


def _get_user_table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows]


def _get_columns(conn: sqlite3.Connection, table_name: str) -> list[dict[str, Any]]:
    rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return [
        {
            "name": row[1],
            "type": row[2],
            "primary_key": bool(row[5]),
            "not_null": bool(row[3]),
        }
        for row in rows
    ]


def _get_foreign_keys(conn: sqlite3.Connection, table_name: str) -> list[dict[str, str]]:
    rows = conn.execute(f'PRAGMA foreign_key_list("{table_name}")').fetchall()
    return [
        {
            "column": row[3],
            "references_table": row[2],
            "references_column": row[4],
        }
        for row in rows
    ]


def _format_column(column: dict[str, Any]) -> str:
    parts = [column["name"], column["type"]]
    if column["primary_key"]:
        parts.append("PRIMARY KEY")
    if column["not_null"]:
        parts.append("NOT NULL")
    return "- " + " ".join(parts)


def _format_schema_text(tables: list[dict[str, Any]]) -> str:
    if not tables:
        return "No user tables found."

    sections = []
    for table in tables:
        lines = [f"Table {table['table_name']}:"]
        lines.extend(_format_column(column) for column in table["columns"])
        if table["foreign_keys"]:
            relationships = [
                f"{fk['column']} -> {fk['references_table']}.{fk['references_column']}"
                for fk in table["foreign_keys"]
            ]
            lines.append("Foreign keys: " + ", ".join(relationships))
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def get_database_schema(db_path: str | Path) -> dict[str, Any]:
    started_at = perf_counter()
    path = Path(db_path)

    if not path.exists():
        latency_ms = int((perf_counter() - started_at) * 1000)
        error = f"Database file not found: {path}"
        return {
            "success": False,
            "db_path": str(path),
            "tables": [],
            "table_count": 0,
            "schema_text": "",
            "error": error,
            "trace_event": _trace_event(path, 0, "error", latency_ms, error),
        }

    try:
        with sqlite3.connect(path) as conn:
            table_names = _get_user_table_names(conn)
            tables = [
                {
                    "table_name": table_name,
                    "columns": _get_columns(conn, table_name),
                    "foreign_keys": _get_foreign_keys(conn, table_name),
                }
                for table_name in table_names
            ]
    except Exception as exc:
        latency_ms = int((perf_counter() - started_at) * 1000)
        error = f"Failed to read database schema: {exc}"
        return {
            "success": False,
            "db_path": str(path),
            "tables": [],
            "table_count": 0,
            "schema_text": "",
            "error": error,
            "trace_event": _trace_event(path, 0, "error", latency_ms, error),
        }

    latency_ms = int((perf_counter() - started_at) * 1000)
    table_count = len(tables)
    return {
        "success": True,
        "db_path": str(path),
        "tables": tables,
        "table_count": table_count,
        "schema_text": _format_schema_text(tables),
        "trace_event": _trace_event(path, table_count, "success", latency_ms),
    }
