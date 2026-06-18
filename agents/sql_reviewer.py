from __future__ import annotations

from typing import Any

from tools.sql_validator import validate_sql
from tools.trace_logger import append_trace


def run_sql_reviewer(state: dict[str, Any]) -> dict[str, Any]:
    sql = state.get("generated_sql") or state.get("fixed_sql") or ""
    result = validate_sql(sql, state.get("database_schema", {}), state.get("metric_context"))
    updated = {
        **state,
        "review_result": result,
        "generated_sql": result.get("normalized_sql") or sql,
    }
    if not result.get("approved"):
        updated["status"] = "review_rejected"

    trace_event = dict(result.get("trace_event", {}))
    trace_event["node"] = "sql_reviewer_agent"
    return append_trace(updated, trace_event)
