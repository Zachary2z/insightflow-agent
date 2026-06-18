from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

import yaml


DEFAULT_METRICS_PATH = Path(__file__).resolve().parents[1] / "data" / "metrics.yaml"


def _summarize_metrics(metric_ids: list[str]) -> str:
    if not metric_ids:
        return "no metric matched"
    return ", ".join(metric_ids)


def _trace_event(
    question: str,
    metric_ids: list[str],
    status: str,
    latency_ms: int,
    error: str | None = None,
) -> dict[str, Any]:
    event = {
        "tool_name": "retrieve_metric_definition",
        "tool_input_summary": question[:120],
        "tool_output_summary": _summarize_metrics(metric_ids),
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "metric_not_found"
        event["error"] = error
    return event


def load_metric_definitions(metrics_path: str | Path = DEFAULT_METRICS_PATH) -> dict[str, Any]:
    path = Path(metrics_path)
    if not path.exists():
        return {
            "success": False,
            "metrics": {},
            "error": f"Metrics file not found: {path}",
        }

    try:
        with path.open("r", encoding="utf-8") as file:
            metrics = yaml.safe_load(file) or {}
    except Exception as exc:
        return {
            "success": False,
            "metrics": {},
            "error": f"Failed to load metrics file: {exc}",
        }

    if not isinstance(metrics, dict):
        return {
            "success": False,
            "metrics": {},
            "error": "Metrics file must contain a mapping of metric ids to definitions.",
        }

    return {
        "success": True,
        "metrics": metrics,
        "metrics_path": str(path),
    }


def _normalize(text: str) -> str:
    return text.lower().replace(" ", "")


def _metric_matches(question: str, metric_id: str, definition: dict[str, Any]) -> bool:
    normalized_question = _normalize(question)
    aliases = definition.get("aliases", [])
    candidates = [metric_id, definition.get("name", ""), *aliases]
    return any(_normalize(str(candidate)) in normalized_question for candidate in candidates if candidate)


def _ordered_matches(question: str, metrics: dict[str, Any]) -> list[str]:
    matched = [
        metric_id
        for metric_id, definition in metrics.items()
        if isinstance(definition, dict) and _metric_matches(question, metric_id, definition)
    ]

    # Product/category questions often still require GMV context for sales amount semantics.
    if "gmv" in matched:
        matched.remove("gmv")
        matched.insert(0, "gmv")

    return matched


def retrieve_metric_definition(
    question: str,
    metrics_path: str | Path = DEFAULT_METRICS_PATH,
) -> dict[str, Any]:
    started_at = perf_counter()
    loaded = load_metric_definitions(metrics_path)
    if not loaded["success"]:
        latency_ms = int((perf_counter() - started_at) * 1000)
        return {
            "success": False,
            "question": question,
            "matched_metrics": [],
            "metrics": {},
            "error": loaded["error"],
            "trace_event": _trace_event(question, [], "error", latency_ms, loaded["error"]),
        }

    metrics = loaded["metrics"]
    matched_metrics = _ordered_matches(question, metrics)
    latency_ms = int((perf_counter() - started_at) * 1000)

    if not matched_metrics:
        error = f"No metric definition matched question: {question}"
        return {
            "success": False,
            "question": question,
            "matched_metrics": [],
            "metrics": {},
            "error": error,
            "trace_event": _trace_event(question, [], "error", latency_ms, error),
        }

    selected = {metric_id: metrics[metric_id] for metric_id in matched_metrics}
    return {
        "success": True,
        "question": question,
        "matched_metrics": matched_metrics,
        "metrics": selected,
        "metrics_path": str(Path(metrics_path)),
        "trace_event": _trace_event(question, matched_metrics, "success", latency_ms),
    }
