from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.context_tool import retrieve_business_context
from tools.trace_logger import append_trace


def run_context_retriever_agent(
    state: dict[str, Any],
    context_paths: dict[str, str | Path] | None = None,
) -> dict[str, Any]:
    result = retrieve_business_context(state.get("user_question", ""), context_paths)
    updated = {
        **state,
        "business_context": result,
    }
    if not result.get("success"):
        updated["context_warning"] = result.get("error", "")

    trace_event = dict(result.get("trace_event", {}))
    trace_event["node"] = "context_retriever_agent"
    return append_trace(updated, trace_event)
