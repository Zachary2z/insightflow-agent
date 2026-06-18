from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.schema_tool import get_database_schema
from tools.trace_logger import append_trace


def run_schema_agent(state: dict[str, Any], db_path: str | Path) -> dict[str, Any]:
    result = get_database_schema(db_path)
    updated = {
        **state,
        "database_schema": result,
        "schema_text": result.get("schema_text", ""),
    }
    if not result.get("success"):
        updated["status"] = "schema_error"
        updated["error_message"] = result.get("error", "")

    trace_event = dict(result.get("trace_event", {}))
    trace_event["node"] = "schema_agent"
    return append_trace(updated, trace_event)
