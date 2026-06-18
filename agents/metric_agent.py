from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.metric_tool import DEFAULT_METRICS_PATH, retrieve_metric_definition
from tools.trace_logger import append_trace


def run_metric_agent(
    state: dict[str, Any],
    metrics_path: str | Path = DEFAULT_METRICS_PATH,
) -> dict[str, Any]:
    result = retrieve_metric_definition(state.get("user_question", ""), metrics_path)
    updated = {
        **state,
        "metric_context": result,
        "selected_metrics": result.get("matched_metrics", []),
    }
    if not result.get("success"):
        updated["metric_warning"] = result.get("error", "")

    trace_event = dict(result.get("trace_event", {}))
    trace_event["node"] = "metric_agent"
    return append_trace(updated, trace_event)
