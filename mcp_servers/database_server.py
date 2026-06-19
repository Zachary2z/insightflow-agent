from __future__ import annotations

import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Any

from mcp_servers.contracts import build_contract, tool_contract, wrap_failure, wrap_success
from tools.metric_tool import retrieve_metric_definition
from tools.schema_tool import get_database_schema
from tools.sql_executor import run_sql
from tools.sql_validator import validate_sql


SERVER_NAME = "database-mcp-server"


def get_tool_contract() -> dict[str, Any]:
    return build_contract(
        SERVER_NAME,
        [
            tool_contract(
                name="get_database_schema",
                description="Return the SQLite database schema as structured tables and readable text.",
                input_schema={"type": "object", "required": ["db_path"], "properties": {"db_path": {"type": "string"}}},
                output_schema={"type": "object", "required": ["success", "result"]},
            ),
            tool_contract(
                name="get_sample_rows",
                description="Return a small read-only sample from an existing user table.",
                input_schema={
                    "type": "object",
                    "required": ["db_path", "table_name"],
                    "properties": {
                        "db_path": {"type": "string"},
                        "table_name": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                    },
                },
                output_schema={"type": "object", "required": ["success", "result"]},
                safety={"read_only": True, "table_must_exist_in_schema": True},
            ),
            tool_contract(
                name="run_sql",
                description="Review and execute one read-only SQL query against the configured database.",
                input_schema={
                    "type": "object",
                    "required": ["db_path", "sql"],
                    "properties": {
                        "db_path": {"type": "string"},
                        "sql": {"type": "string"},
                        "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 30},
                        "max_rows": {"type": "integer", "minimum": 1, "maximum": 500},
                    },
                },
                output_schema={"type": "object", "required": ["success", "review_result", "result"]},
                safety={"internal_review_required": True, "read_only": True, "single_statement": True},
            ),
        ],
    )


def mcp_get_database_schema(db_path: str | Path) -> dict[str, Any]:
    result = get_database_schema(db_path)
    if not result.get("success"):
        return wrap_failure(SERVER_NAME, "get_database_schema", str(result.get("error", "schema load failed")), result)
    return wrap_success(SERVER_NAME, "get_database_schema", result)


def _schema_table_names(schema: dict[str, Any]) -> set[str]:
    return {str(table.get("table_name", "")) for table in schema.get("tables", [])}


def mcp_get_sample_rows(db_path: str | Path, table_name: str, limit: int = 5) -> dict[str, Any]:
    started_at = perf_counter()
    schema = get_database_schema(db_path)
    if not schema.get("success"):
        return wrap_failure(SERVER_NAME, "get_sample_rows", str(schema.get("error", "schema load failed")))

    if table_name not in _schema_table_names(schema):
        return wrap_failure(SERVER_NAME, "get_sample_rows", f"Unknown table: {table_name}")

    sample_limit = max(1, min(int(limit), 20))
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(f'SELECT * FROM "{table_name}" LIMIT ?', (sample_limit,))
            columns = [description[0] for description in cursor.description or []]
            rows = [list(row) for row in cursor.fetchall()]
    except Exception as exc:
        return wrap_failure(SERVER_NAME, "get_sample_rows", str(exc))

    latency_ms = int((perf_counter() - started_at) * 1000)
    return wrap_success(
        SERVER_NAME,
        "get_sample_rows",
        {
            "success": True,
            "table_name": table_name,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "limit": sample_limit,
            "latency_ms": latency_ms,
        },
    )


def mcp_run_sql(
    db_path: str | Path,
    sql: str,
    timeout_seconds: int = 5,
    max_rows: int = 100,
    metric_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    schema = get_database_schema(db_path)
    if not schema.get("success"):
        return wrap_failure(
            SERVER_NAME,
            "run_sql",
            str(schema.get("error", "schema load failed")),
            review_result={},
        )

    resolved_metric_context = metric_context or retrieve_metric_definition(sql)
    review_result = validate_sql(sql, schema=schema, metric_context=resolved_metric_context)
    if not review_result.get("approved"):
        error = "; ".join(str(issue) for issue in review_result.get("issues", [])) or "SQL review failed"
        return wrap_failure(SERVER_NAME, "run_sql", error, review_result=review_result)

    execution_result = run_sql(
        db_path=db_path,
        sql=str(review_result.get("normalized_sql", sql)),
        timeout_seconds=timeout_seconds,
        max_rows=max_rows,
    )
    if not execution_result.get("success"):
        return wrap_failure(
            SERVER_NAME,
            "run_sql",
            str(execution_result.get("error", "SQL execution failed")),
            execution_result,
            review_result=review_result,
        )
    return wrap_success(SERVER_NAME, "run_sql", execution_result, review_result=review_result)

