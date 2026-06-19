from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.chart_tool import DEFAULT_CHART_DIR, generate_chart
from tools.trace_logger import append_trace


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _infer_chart_type(question: str, columns: list[str]) -> str:
    normalized = question.lower().replace(" ", "")
    lower_columns = [column.lower() for column in columns]
    if any(term in normalized for term in ("趋势", "每月", "按月", "月份", "trend")):
        return "line"
    if any(term in column for column in lower_columns for term in ("month", "date", "day")):
        return "line"
    if any(term in normalized for term in ("占比", "比例", "share", "percent")):
        return "pie"
    return "bar"


def _infer_x_y(execution_result: dict[str, Any]) -> tuple[str, str]:
    columns = execution_result.get("columns") or []
    rows = execution_result.get("rows") or []
    if len(columns) < 2 or not rows:
        raise ValueError("execution_result needs at least two columns and one row for chart generation")

    x_column = columns[0]
    y_column = ""
    for index, column in enumerate(columns[1:], start=1):
        if any(_is_number(row[index]) for row in rows if len(row) > index):
            y_column = column
            break

    if not y_column:
        raise ValueError("Could not infer numeric y column for chart generation")

    return x_column, y_column


def _chart_failure(error: str) -> dict[str, Any]:
    return {
        "success": False,
        "chart_type": "",
        "chart_path": "",
        "error": error,
        "trace_event": {
            "tool_name": "generate_chart",
            "tool_input_summary": "chart_type=",
            "tool_output_summary": error,
            "status": "error",
            "latency_ms": 0,
            "error_type": "chart_generation_error",
            "error": error,
        },
    }


def _build_chart_spec(state: dict[str, Any], execution_result: dict[str, Any]) -> dict[str, Any]:
    if state.get("chart_spec"):
        return dict(state["chart_spec"])

    columns = execution_result.get("columns") or []
    x_column, y_column = _infer_x_y(execution_result)
    chart_type = _infer_chart_type(state.get("user_question", ""), columns)
    return {
        "chart_type": chart_type,
        "x": x_column,
        "y": y_column,
        "title": f"{chart_type.title()} Chart: {y_column} by {x_column}",
        "run_id": state.get("run_id", "run_unknown"),
    }


def run_chart_agent(
    state: dict[str, Any],
    output_dir: str | Path = DEFAULT_CHART_DIR,
) -> dict[str, Any]:
    execution_result = state.get("execution_result")
    if not execution_result or not execution_result.get("success"):
        result = _chart_failure("execution_result is required for chart generation")
    else:
        try:
            chart_spec = _build_chart_spec(state, execution_result)
            data = {
                "columns": execution_result.get("columns", []),
                "rows": execution_result.get("rows", []),
            }
            result = generate_chart(data, chart_spec, output_dir=output_dir)
        except Exception as exc:
            result = _chart_failure(str(exc))

    chart_path = result.get("chart_path", "") if result.get("success") else ""
    chart_paths = list(state.get("chart_paths") or [])
    if chart_path:
        chart_paths.append(chart_path)

    updated = {
        **state,
        "chart_result": result,
        "chart_path": chart_path,
        "chart_paths": chart_paths,
    }
    if not result.get("success"):
        updated["chart_warning"] = result.get("error", "")

    trace_event = dict(result.get("trace_event", {}))
    trace_event["node"] = "chart_agent"
    return append_trace(updated, trace_event)
