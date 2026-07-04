from __future__ import annotations

import os
import re
import tempfile
import warnings
from pathlib import Path
from time import perf_counter
from typing import Any

from visualization.chart_registry import fallback_chart_type, is_supported_chart_type
from visualization.chart_validator import validate_chart_spec


DEFAULT_ADVANCED_CHART_DIR = Path(__file__).resolve().parents[1] / "reports" / "charts"

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "insightflow_matplotlib"))
import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib import font_manager


CJK_FONT_FALLBACKS = [
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "Microsoft YaHei",
    "PingFang SC",
    "SimHei",
    "Arial Unicode MS",
    "DejaVu Sans",
]


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


def _configure_fonts() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    selected = [font for font in CJK_FONT_FALLBACKS if font in available]
    if "DejaVu Sans" not in selected:
        selected.append("DejaVu Sans")
    plt.rcParams["font.sans-serif"] = selected
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False


def _y_label(spec: dict[str, Any]) -> str:
    unit = str(spec.get("unit") or "").strip()
    return f"{spec['y']} ({unit})" if unit else spec["y"]


def _format_value(value: float, unit: str) -> str:
    label = f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"
    return f"{label}{unit}" if unit else label


def _add_bar_value_labels(bars: Any, values: list[float], unit: str) -> None:
    axis = plt.gca()
    max_value = max(values) if values else 0
    offset = max_value * 0.015 if max_value else 0.05
    for bar, value in zip(bars, values, strict=False):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + offset,
            _format_value(value, unit),
            ha="center",
            va="bottom",
            fontsize=8,
        )


def _add_point_value_labels(x_values: list[Any], y_values: list[float], unit: str) -> None:
    axis = plt.gca()
    for x_value, y_value in zip(x_values, y_values, strict=False):
        axis.annotate(
            _format_value(y_value, unit),
            (x_value, y_value),
            textcoords="offset points",
            xytext=(0, 6),
            ha="center",
            fontsize=8,
        )


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


def _draw_supported_chart(spec: dict[str, Any], columns: list[str], rows: list[list[Any]]) -> None:
    chart_type = spec["chart_type"]
    x_values = [str(value) for value in _values(columns, rows, spec["x"])]
    y_values = _numeric_values(columns, rows, spec["y"])
    unit = str(spec.get("unit") or "")
    show_value_labels = bool(spec.get("value_label", False))

    if chart_type in {"ranked_bar", "funnel"}:
        bars = plt.bar(x_values, y_values, color="#2563eb")
        if show_value_labels:
            _add_bar_value_labels(bars, y_values, unit)
        plt.xticks(rotation=30, ha="right")
    elif chart_type == "line":
        plt.plot(x_values, y_values, marker="o", color="#2563eb")
        if show_value_labels:
            _add_point_value_labels(x_values, y_values, unit)
        plt.xticks(rotation=30, ha="right")
    elif chart_type == "grouped_bar":
        series_values = [str(value) for value in _values(columns, rows, spec["series"])]
        labels = [f"{x}\n{series}" for x, series in zip(x_values, series_values, strict=False)]
        bars = plt.bar(labels, y_values, color="#2563eb")
        if show_value_labels:
            _add_bar_value_labels(bars, y_values, unit)
        plt.xticks(rotation=30, ha="right")
    elif chart_type == "dual_axis_line":
        secondary_values = _numeric_values(columns, rows, spec["y_secondary"])
        axis = plt.gca()
        axis.plot(x_values, y_values, marker="o", color="#2563eb", label=spec["y"])
        if show_value_labels:
            _add_point_value_labels(x_values, y_values, unit)
        axis.set_ylabel(_y_label(spec))
        secondary_axis = axis.twinx()
        secondary_axis.plot(x_values, secondary_values, marker="s", color="#dc2626", label=spec["y_secondary"])
        secondary_axis.set_ylabel(spec["y_secondary"])
        plt.xticks(rotation=30, ha="right")
    elif chart_type == "heatmap":
        x_categories = list(dict.fromkeys(x_values))
        y_categories = list(dict.fromkeys(str(value) for value in _values(columns, rows, spec["series"])))
        matrix = [[0.0 for _ in x_categories] for _ in y_categories]
        series_values = [str(value) for value in _values(columns, rows, spec["series"])]
        for x_value, y_value, metric in zip(x_values, series_values, y_values, strict=False):
            matrix[y_categories.index(y_value)][x_categories.index(x_value)] = metric
        plt.imshow(matrix, aspect="auto", cmap="Blues")
        plt.xticks(range(len(x_categories)), x_categories, rotation=30, ha="right")
        plt.yticks(range(len(y_categories)), y_categories)
        plt.colorbar(label=spec["y"])
    elif chart_type in {"scatter", "risk_matrix"}:
        x_metric = _numeric_values(columns, rows, spec["x"])
        y_metric = _numeric_values(columns, rows, spec["y"])
        color = "#2563eb" if chart_type == "scatter" else "#dc2626"
        plt.scatter(x_metric, y_metric, color=color)
        if chart_type == "risk_matrix" and x_metric and y_metric:
            plt.axvline(sum(x_metric) / len(x_metric), color="#6b7280", linestyle="--", linewidth=1)
            plt.axhline(sum(y_metric) / len(y_metric), color="#6b7280", linestyle="--", linewidth=1)

    plt.title(spec.get("title") or f"{chart_type.title()} Chart")
    if chart_type != "dual_axis_line":
        plt.xlabel(spec["x"])
        plt.ylabel(_y_label(spec))


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


def render_chart(
    execution_result: dict[str, Any],
    chart_spec: dict[str, Any],
    output_dir: str | Path = DEFAULT_ADVANCED_CHART_DIR,
) -> dict[str, Any]:
    started_at = perf_counter()
    columns = [str(column) for column in execution_result.get("columns") or []]
    rows = list(execution_result.get("rows") or [])
    raw_chart_type = str(chart_spec.get("chart_type", "")).strip().lower()
    _configure_fonts()

    if not is_supported_chart_type(raw_chart_type):
        fallback_type = fallback_chart_type(columns, rows)
        reason = f"Unsupported chart_type: {raw_chart_type}"
        if fallback_type == "table":
            return _table_fallback(execution_result, reason, started_at)
        chart_spec = {
            **chart_spec,
            "chart_type": "ranked_bar",
            "title": chart_spec.get("title") or "Fallback Bar Chart",
            "x": chart_spec.get("x") or (columns[0] if columns else ""),
            "y": chart_spec.get("y") or (columns[1] if len(columns) > 1 else ""),
            "y_secondary": "",
            "series": "",
            "required_columns": [column for column in [columns[0] if columns else "", columns[1] if len(columns) > 1 else ""] if column],
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
        plt.figure(figsize=(8, 5.2))
        _draw_supported_chart(validated, columns, rows)
        annotation = str(validated.get("business_annotation") or "").strip()
        if annotation:
            plt.figtext(0.08, 0.03, annotation, ha="left", va="bottom", fontsize=9, wrap=True)
        plt.tight_layout(rect=(0, 0.1, 1, 1) if annotation else None)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r".*Glyph .* missing from font.*")
            warnings.filterwarnings("ignore", message=r".*missing from current font.*")
            plt.savefig(chart_path, dpi=160)
        plt.close()
    except Exception as exc:
        plt.close()
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
