from __future__ import annotations

from typing import Any

from tools.trace_logger import append_trace


def _column_exists(schema: dict[str, Any], table_name: str, column_name: str) -> bool:
    for table in schema.get("tables", []):
        if table.get("table_name") != table_name:
            continue
        return any(column.get("name") == column_name for column in table.get("columns", []))
    return False


def _fix_known_column_error(sql: str, error: str, schema: dict[str, Any]) -> tuple[str, str] | None:
    if "no such column" not in error.lower():
        return None
    if "oi.price" in sql and _column_exists(schema, "order_items", "unit_price"):
        return (
            sql.replace("oi.price", "oi.unit_price"),
            "order_items has no price column; use unit_price for item price.",
        )
    if "order_items.price" in sql and _column_exists(schema, "order_items", "unit_price"):
        return (
            sql.replace("order_items.price", "order_items.unit_price"),
            "order_items has no price column; use unit_price for item price.",
        )
    return None


def _fix_known_runtime_error(sql: str, error: str) -> tuple[str, str] | None:
    if "no such function: missing_price" in error.lower() and "missing_price(oi.unit_price)" in sql:
        return (
            sql.replace("missing_price(oi.unit_price)", "oi.unit_price"),
            "SQLite reported missing_price as an unknown function; use oi.unit_price directly.",
        )
    return None


def run_error_fix_agent(state: dict[str, Any]) -> dict[str, Any]:
    retry_count = int(state.get("retry_count") or 0)
    sql = state.get("generated_sql", "")
    execution_result = state.get("execution_result", {})
    error = execution_result.get("error") or state.get("error_message", "")

    if retry_count >= 1:
        output = {
            "success": False,
            "fixed_sql": "",
            "fix_reason": "Maximum retry count reached.",
            "retry_count": retry_count,
            "error": "Error Fix Agent only retries once in P0.",
        }
        status = "error"
    else:
        fix = _fix_known_column_error(sql, error, state.get("database_schema", {}))
        if fix is None:
            fix = _fix_known_runtime_error(sql, error)
        if fix is None:
            output = {
                "success": False,
                "fixed_sql": "",
                "fix_reason": "No deterministic P0 fix rule matched the SQL error.",
                "retry_count": retry_count,
                "error": error or "Unknown SQL execution error",
            }
            status = "error"
        else:
            fixed_sql, fix_reason = fix
            output = {
                "success": True,
                "fixed_sql": fixed_sql,
                "fix_reason": fix_reason,
                "retry_count": retry_count + 1,
            }
            status = "success"

    updated = {
        **state,
        "sql_fix": output,
        "fixed_sql": output.get("fixed_sql", ""),
        "retry_count": output["retry_count"],
    }
    return append_trace(
        updated,
        {
            "node": "error_fix_agent",
            "tool_name": "",
            "tool_input_summary": sql[:200],
            "tool_output_summary": output.get("fix_reason", ""),
            "status": status,
            "latency_ms": 0,
            "error_type": None if output.get("success") else "sql_fix_error",
            "retry_count": output["retry_count"],
        },
    )
