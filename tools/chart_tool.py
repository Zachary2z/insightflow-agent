from __future__ import annotations

from pathlib import Path
from typing import Any

from visualization.chart_renderer import DEFAULT_ADVANCED_CHART_DIR, render_chart


DEFAULT_CHART_DIR = DEFAULT_ADVANCED_CHART_DIR


def generate_chart(
    data: dict[str, Any],
    chart_spec: dict[str, Any],
    output_dir: str | Path = DEFAULT_CHART_DIR,
) -> dict[str, Any]:
    execution_result = {
        "success": True,
        "columns": list(data.get("columns") or []),
        "rows": list(data.get("rows") or []),
        "row_count": len(data.get("rows") or []),
    }
    result = render_chart(execution_result, chart_spec, output_dir=output_dir)
    trace_event = dict(result.get("trace_event", {}))
    trace_event["tool_name"] = "generate_chart"
    return {
        **result,
        "trace_event": trace_event,
    }
