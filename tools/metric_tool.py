from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter
from typing import Any

import yaml

from semantic_layer.loader import DEFAULT_SEMANTIC_PATHS
from semantic_layer.loader import load_workspace_semantic_layer
from semantic_layer.retriever import retrieve_semantic_context


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
    return re.sub(r"[\s_\-]+", "", str(text).lower())


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

    # Keep the base sales-amount metric first when legacy definitions match multiple sales metrics.
    if "gmv" in matched:
        matched.remove("gmv")
        matched.insert(0, "gmv")

    return matched


def _workspace_candidates(item: dict[str, Any]) -> list[str]:
    aliases = item.get("aliases", [])
    return [
        str(item.get("name", "")),
        str(item.get("label", "")),
        str(item.get("field", "")).split(".")[-1],
        *[str(alias) for alias in aliases],
    ]


def _workspace_matches(question: str, item: dict[str, Any]) -> bool:
    normalized_question = _normalize(question)
    return any(_normalize(candidate) in normalized_question for candidate in _workspace_candidates(item) if candidate)


def _workspace_semantic_context(question: str, semantic_layer: dict[str, Any]) -> dict[str, Any]:
    metrics = [item for item in semantic_layer.get("metrics", []) if isinstance(item, dict)]
    dimensions = [item for item in semantic_layer.get("dimensions", []) if isinstance(item, dict)]
    entities = [item for item in semantic_layer.get("entities", []) if isinstance(item, dict)]
    time_fields = [item for item in semantic_layer.get("time_fields", []) if isinstance(item, dict)]
    matched_metrics = [str(item.get("name")) for item in metrics if item.get("name") and _workspace_matches(question, item)]
    matched_dimensions = [
        str(item.get("name")) for item in dimensions if item.get("name") and _workspace_matches(question, item)
    ]
    matched_entities = [str(item.get("name")) for item in entities if item.get("name") and _workspace_matches(question, item)]
    matched_time_fields = [
        str(item.get("name")) for item in time_fields if item.get("name") and _workspace_matches(question, item)
    ]
    return {
        "success": True,
        "source": "workspace_semantic_layer",
        "matched_metrics": matched_metrics,
        "matched_dimensions": matched_dimensions,
        "matched_entities": matched_entities,
        "matched_time_fields": matched_time_fields,
        "metrics": {str(item["name"]): item for item in metrics if item.get("name") in matched_metrics},
        "dimensions": {str(item["name"]): item for item in dimensions if item.get("name") in matched_dimensions},
        "entities": {str(item["name"]): item for item in entities if item.get("name") in matched_entities},
        "time_fields": {str(item["name"]): item for item in time_fields if item.get("name") in matched_time_fields},
    }


def retrieve_metric_definition(
    question: str,
    metrics_path: str | Path = DEFAULT_METRICS_PATH,
    semantic_layer_path: str | Path | None = None,
) -> dict[str, Any]:
    started_at = perf_counter()
    if semantic_layer_path:
        loaded_semantic_layer = load_workspace_semantic_layer(semantic_layer_path)
        latency_ms = int((perf_counter() - started_at) * 1000)
        if not loaded_semantic_layer.get("success"):
            error = loaded_semantic_layer.get("error", "Failed to load workspace semantic layer.")
            return {
                "success": False,
                "source": "workspace_semantic_layer",
                "question": question,
                "matched_metrics": [],
                "metrics": {},
                "error": error,
                "trace_event": _trace_event(question, [], "error", latency_ms, error),
            }
        semantic_context = _workspace_semantic_context(question, loaded_semantic_layer["semantic_layer"])
        matched_metrics = semantic_context["matched_metrics"]
        if not matched_metrics:
            error = f"No metric definition matched question: {question}"
            return {
                "success": False,
                "source": "workspace_semantic_layer",
                "question": question,
                "matched_metrics": [],
                "metrics": {},
                "semantic_context": semantic_context,
                "semantic_layer_path": str(semantic_layer_path),
                "error": error,
                "trace_event": _trace_event(question, [], "error", latency_ms, error),
            }
        return {
            "success": True,
            "source": "workspace_semantic_layer",
            "question": question,
            "matched_metrics": matched_metrics,
            "metrics": semantic_context["metrics"],
            "semantic_context": semantic_context,
            "semantic_layer_path": str(semantic_layer_path),
            "trace_event": _trace_event(question, matched_metrics, "success", latency_ms),
        }

    path = Path(metrics_path)
    use_semantic_layer = path.resolve() == DEFAULT_METRICS_PATH.resolve()
    if use_semantic_layer:
        semantic_context = retrieve_semantic_context(question)
        latency_ms = int((perf_counter() - started_at) * 1000)
        if semantic_context.get("success"):
            matched_metrics = semantic_context.get("matched_metrics", [])
            if not matched_metrics:
                error = f"No metric definition matched question: {question}"
                return {
                    "success": False,
                    "question": question,
                    "matched_metrics": [],
                    "metrics": {},
                    "semantic_context": semantic_context,
                    "error": error,
                    "trace_event": _trace_event(question, [], "error", latency_ms, error),
                }
            return {
                "success": True,
                "question": question,
                "matched_metrics": matched_metrics,
                "metrics": semantic_context.get("metrics", {}),
                "metrics_path": str(DEFAULT_SEMANTIC_PATHS["metrics"]),
                "semantic_context": semantic_context,
                "trace_event": _trace_event(question, matched_metrics, "success", latency_ms),
            }

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
