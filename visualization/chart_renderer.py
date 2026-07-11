from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter
from typing import Any

from visualization.chart_registry import fallback_chart_type, is_supported_chart_type
from visualization.chart_validator import validate_chart_spec
from visualization.static_renderer import render_static_chart_file


DEFAULT_ADVANCED_CHART_DIR = Path(__file__).resolve().parents[1] / "reports" / "charts"


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return safe.strip("_") or "chart"


def _column_index(columns: list[str], column: str) -> int:
    if column not in columns:
        raise ValueError(f"Column not found for chart: {column}")
    return columns.index(column)


def _values(columns: list[str], rows: list[list[Any]], column: str) -> list[Any]:
    index = _column_index(columns, column)
    return [row[index] for row in rows]


def _numeric_values(columns: list[str], rows: list[list[Any]], column: str) -> list[float]:
    return [float(value) for value in _values(columns, rows, column)]


def _trace_event(chart_type: str, output: str, status: str, latency_ms: int, error: str = "") -> dict[str, Any]:
    event = {
        "tool_name": "render_visualization_chart",
        "tool_input_summary": f"chart_type={chart_type}",
        "tool_output_summary": output[:200],
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "visualization_render_error"
        event["error"] = error
    return event


def _table_fallback(execution_result: dict[str, Any], reason: str, started_at: float) -> dict[str, Any]:
    latency_ms = int((perf_counter() - started_at) * 1000)
    columns = list(execution_result.get("columns") or [])
    rows = list(execution_result.get("rows") or [])
    return {
        "success": True,
        "chart_type": "table",
        "chart_path": "",
        "fallback_used": True,
        "fallback_reason": reason,
        "table": {"columns": columns, "rows": rows},
        "data_row_count": len(rows),
        "rendered_rows": rows,
        "fabricated_data": False,
        "trace_event": _trace_event("table", reason, "success", latency_ms),
    }


def _static_series(spec: dict[str, Any], columns: list[str], rows: list[list[Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    chart_type = spec["chart_type"]
    x_values = [str(value) for value in _values(columns, rows, spec["x"])]
    y_values = _numeric_values(columns, rows, spec["y"])
    if chart_type in {"grouped_bar", "heatmap"}:
        series_values = [str(value) for value in _values(columns, rows, spec["series"])]
        labels = list(dict.fromkeys(x_values))
        names = list(dict.fromkeys(series_values))
        values_by_series = {
            name: {x: value for x, series_name, value in zip(x_values, series_values, y_values, strict=False) if series_name == name}
            for name in names
        }
        return labels, [
            {"name": name, "values": [values_by_series[name].get(label, 0.0) for label in labels]}
            for name in names
        ]
    if chart_type == "dual_axis_line":
        return x_values, [
            {"name": spec["y"], "values": y_values},
            {"name": spec["y_secondary"], "values": _numeric_values(columns, rows, spec["y_secondary"])},
        ]
    return x_values, [{"name": spec["y"], "values": y_values}]


def render_chart(
    execution_result: dict[str, Any],
    chart_spec: dict[str, Any],
    output_dir: str | Path = DEFAULT_ADVANCED_CHART_DIR,
) -> dict[str, Any]:
    started_at = perf_counter()
    columns = [str(column) for column in execution_result.get("columns") or []]
    rows = list(execution_result.get("rows") or [])
    raw_chart_type = str(chart_spec.get("chart_type", "")).strip().lower()

    if not is_supported_chart_type(raw_chart_type):
        reason = f"Unsupported chart_type: {raw_chart_type}"
        if fallback_chart_type(columns, rows) == "table":
            return _table_fallback(execution_result, reason, started_at)
        chart_spec = {
            **chart_spec,
            "chart_type": "ranked_bar",
            "title": chart_spec.get("title") or "Fallback Bar Chart",
            "x": chart_spec.get("x") or (columns[0] if columns else ""),
            "y": chart_spec.get("y") or (columns[1] if len(columns) > 1 else ""),
            "y_secondary": "",
            "series": "",
            "required_columns": [column for column in columns[:2] if column],
        }
        fallback_used = True
        fallback_reason = reason
    else:
        fallback_used = bool(chart_spec.get("fallback_used", False))
        fallback_reason = str(chart_spec.get("fallback_reason", "") or "")

    validated = validate_chart_spec(chart_spec, execution_result)
    if not validated.get("success"):
        return _table_fallback(execution_result, validated.get("validation_error", "chart validation failed"), started_at)

    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        run_id = str(validated.get("run_id", "run_unknown"))
        filename = _safe_filename(f"{run_id}_{validated['chart_type']}_{validated['x']}_{validated['y']}") + ".png"
        chart_path = output_path / filename
        labels, series = _static_series(validated, columns, rows)
        render_static_chart_file(
            chart_path,
            title=str(validated.get("title") or f"{validated['chart_type'].title()} Chart"),
            labels=labels,
            series=series,
            chart_type=validated["chart_type"],
            annotation=str(validated.get("business_annotation") or "").strip(),
            unit=str(validated.get("unit") or "").strip(),
            show_value_labels=bool(validated.get("value_label", False)),
        )
    except Exception as exc:
        return _table_fallback(execution_result, str(exc), started_at)

    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": True,
        "chart_type": validated["chart_type"],
        "chart_path": str(chart_path),
        "chart_spec": validated,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "data_row_count": len(rows),
        "rendered_rows": rows,
        "fabricated_data": False,
        "trace_event": _trace_event(validated["chart_type"], str(chart_path), "success", latency_ms),
    }
