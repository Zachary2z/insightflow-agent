from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from tools.trace_logger import append_trace


def _new_id(prefix: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}_{uuid4().hex[:8]}"


def initialize_run(
    user_question: str,
    run_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    state = {
        "success": True,
        "run_id": run_id or _new_id("run"),
        "session_id": session_id or _new_id("session"),
        "user_question": user_question,
        "task_type": "sql_analysis",
        "status": "initialized",
        "retry_count": 0,
        "trace": [],
    }
    return append_trace(
        state,
        {
            "node": "supervisor_agent",
            "tool_name": "",
            "tool_input_summary": user_question,
            "tool_output_summary": "initialized sql_analysis run",
            "status": "success",
            "latency_ms": 0,
        },
    )
