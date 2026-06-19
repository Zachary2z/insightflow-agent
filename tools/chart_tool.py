from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any


DEFAULT_CHART_DIR = Path(__file__).resolve().parents[1] / "reports" / "charts"
SUPPORTED_CHART_TYPES = {"bar", "line", "pie"}

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "insightflow_matplotlib"))
import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt


def _trace_event(
    chart_type: str,
    chart_path: str,
    status: str,
    latency_ms: int,
    error: str | None = None,
) -> dict[str, Any]:
    summary = chart_path if chart_path else error or "chart not generated"
    event = {
        "tool_name": "generate_chart",
        "tool_input_summary": f"chart_type={chart_type}",
        "tool_output_summary": summary[:200],
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "chart_generation_error"
        event["error"] = error
    return event


def _failure(started_at: float, chart_type: str, error: str) -> dict[str, Any]:
    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": False,
        "chart_type": chart_type,
        "chart_path": "",
        "error": error,
        "trace_event": _trace_event(chart_type, "", "error", latency_ms, error),
    }


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return safe.strip("_") or "chart"


def _column_index(columns: list[str], column: str) -> int:
    if column not in columns:
        raise ValueError(f"Column not found for chart: {column}")
    return columns.index(column)


def _series(data: dict[str, Any], x_column: str, y_column: str) -> tuple[list[Any], list[float]]:
    columns = data.get("columns") or []
    rows = data.get("rows") or []
    if not columns or not rows:
        raise ValueError("Chart data requires non-empty columns and rows.")

    x_index = _column_index(columns, x_column)
    y_index = _column_index(columns, y_column)
    x_values = [row[x_index] for row in rows]
    y_values = [float(row[y_index]) for row in rows]
    return x_values, y_values


def _draw_chart(chart_type: str, x_values: list[Any], y_values: list[float], x_column: str, y_column: str, title: str) -> None:
    if chart_type == "bar":
        plt.bar([str(value) for value in x_values], y_values, color="#2563eb")
        plt.xticks(rotation=30, ha="right")
    elif chart_type == "line":
        plt.plot([str(value) for value in x_values], y_values, marker="o", color="#2563eb")
        plt.xticks(rotation=30, ha="right")
    elif chart_type == "pie":
        plt.pie(y_values, labels=[str(value) for value in x_values], autopct="%1.1f%%")
    plt.title(title or f"{chart_type.title()} Chart")
    if chart_type != "pie":
        plt.xlabel(x_column)
        plt.ylabel(y_column)


def generate_chart(
    data: dict[str, Any],
    chart_spec: dict[str, Any],
    output_dir: str | Path = DEFAULT_CHART_DIR,
) -> dict[str, Any]:
    started_at = perf_counter()
    chart_type = str(chart_spec.get("chart_type", "")).lower()
    if chart_type not in SUPPORTED_CHART_TYPES:
        return _failure(started_at, chart_type, f"Unsupported chart_type: {chart_type}")

    x_column = str(chart_spec.get("x", ""))
    y_column = str(chart_spec.get("y", ""))
    title = str(chart_spec.get("title", ""))
    run_id = str(chart_spec.get("run_id", "run_unknown"))

    try:
        x_values, y_values = _series(data, x_column, y_column)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        filename = _safe_filename(f"{run_id}_{chart_type}_{x_column}_{y_column}") + ".png"
        chart_path = output_path / filename

        plt.figure(figsize=(8, 4.5))
        _draw_chart(chart_type, x_values, y_values, x_column, y_column, title)
        plt.tight_layout()
        plt.savefig(chart_path, dpi=160)
        plt.close()
    except Exception as exc:
        plt.close()
        return _failure(started_at, chart_type, str(exc))

    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": True,
        "chart_type": chart_type,
        "chart_path": str(chart_path),
        "chart_spec": {
            "chart_type": chart_type,
            "x": x_column,
            "y": y_column,
            "title": title,
            "run_id": run_id,
        },
        "trace_event": _trace_event(chart_type, str(chart_path), "success", latency_ms),
    }
