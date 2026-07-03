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


def build_metric_registry(semantic_layer: dict[str, Any] | None) -> dict[str, Any]:
    """Build a workspace metric registry without inventing unsupported derived metrics."""
    semantic_layer = semantic_layer or {}
    raw_metrics = semantic_layer.get("metrics") or []
    if isinstance(raw_metrics, dict):
        raw_metrics = raw_metrics.values()
    base_metrics = [_normalize_registry_metric(item) for item in raw_metrics if isinstance(item, dict)]
    metrics = {metric["name"]: metric for metric in base_metrics if metric.get("name")}
    warnings: list[str] = []

    revenue = _first_metric_with_meaning(base_metrics, ("revenue_like", "sales_like", "gmv_like"))
    spend = _first_metric_with_meaning(base_metrics, ("spend_like", "ad_spend_like", "marketing_spend_like"))
    cost = _first_metric_with_meaning(base_metrics, ("cost_like",), exclude_meanings=("spend_like",))
    order_count = _first_metric_with_meaning(base_metrics, ("order_count_like", "count_like"))

    if revenue and spend:
        _add_derived_metric(
            metrics,
            name="roas",
            business_label="广告投入产出比",
            formula=f'{revenue["formula"]} / NULLIF({spend["formula"]}, 0)',
            unit="ratio",
            source_fields=[*revenue["source_fields"], *spend["source_fields"]],
            description="ROAS = revenue / spend. This is not net return.",
        )
        _add_derived_metric(
            metrics,
            name="net_return",
            business_label="净投放回报率",
            formula=f'({revenue["formula"]} - {spend["formula"]}) / NULLIF({spend["formula"]}, 0)',
            unit="percentage",
            source_fields=[*revenue["source_fields"], *spend["source_fields"]],
            description="Net return = (revenue - spend) / spend. This is not ROAS.",
        )
    else:
        warnings.append("ROAS 和净投放回报率需要同时存在收入类字段和花费类字段，当前证据不足，未生成。")

    if revenue and cost:
        _add_derived_metric(
            metrics,
            name="margin_rate",
            business_label="利润率",
            formula=f'({revenue["formula"]} - {cost["formula"]}) / NULLIF({revenue["formula"]}, 0)',
            unit="percentage",
            source_fields=[*revenue["source_fields"], *cost["source_fields"]],
            description="Margin-like rate = (revenue - cost) / revenue.",
        )
    else:
        warnings.append("利润率需要同时存在收入类字段和成本类字段，当前证据不足，未生成。")

    if revenue and order_count:
        _add_derived_metric(
            metrics,
            name="average_order_value",
            business_label="客单价",
            formula=f'{revenue["formula"]} / NULLIF({order_count["formula"]}, 0)',
            unit="currency",
            source_fields=[*revenue["source_fields"], *order_count["source_fields"]],
            description="Average order value = revenue / order count.",
        )
    else:
        warnings.append("客单价需要同时存在收入类字段和订单数字段，当前证据不足，未生成。")

    return {
        "success": True,
        "metrics": metrics,
        "formulas": {name: metric["formula"] for name, metric in metrics.items() if metric.get("formula")},
        "warnings": warnings,
    }


def _normalize_registry_metric(item: dict[str, Any]) -> dict[str, Any]:
    name = str(item.get("name") or item.get("id") or item.get("field") or "").strip()
    field = str(item.get("field") or "").strip()
    source_fields = [str(value) for value in item.get("source_fields") or [] if str(value).strip()]
    if field and field not in source_fields:
        source_fields.append(field)
    formula = str(item.get("formula") or "").strip()
    if not formula and field:
        formula = f"SUM({_quote_field_reference(field)})"
    unit = str(item.get("unit") or _unit_for_metric(item)).strip() or "number"
    meanings = _metric_meanings(item)
    return {
        "name": name,
        "business_label": str(item.get("business_label") or item.get("label") or item.get("name") or name),
        "formula": formula,
        "unit": unit,
        "source_fields": source_fields,
        "warnings": list(item.get("warnings") or []),
        "meanings": sorted(meanings),
    }


def _metric_meanings(item: dict[str, Any]) -> set[str]:
    raw_values: list[Any] = [
        item.get("business_meaning"),
        item.get("semantic_type"),
        item.get("field_role"),
        item.get("name"),
        item.get("label"),
        item.get("field"),
        *(item.get("aliases") or []),
        *(item.get("business_meaning_candidates") or []),
    ]
    compact = " ".join(str(value or "").lower() for value in raw_values)
    meanings: set[str] = set()
    if any(marker in compact for marker in ("revenue_like", "sales_like", "gmv_like", "revenue", "sales amount", "销售额", "收入", "营收")):
        meanings.add("revenue_like")
    if any(marker in compact for marker in ("spend_like", "ad_spend", "marketing_spend", "spend", "花费", "投放", "广告费")):
        meanings.add("spend_like")
    if any(marker in compact for marker in ("cost_like", "cost", "成本", "费用")):
        meanings.add("cost_like")
    if any(marker in compact for marker in ("order_count_like", "order count", "order_count", "订单数", "订单量")):
        meanings.add("order_count_like")
    if "count_like" in compact and not meanings:
        meanings.add("count_like")
    return meanings


def _unit_for_metric(item: dict[str, Any]) -> str:
    text = " ".join(str(value or "").lower() for value in [item.get("name"), item.get("label"), item.get("field")])
    if any(marker in text for marker in ("rate", "率", "margin", "roi", "return")):
        return "percentage"
    if any(marker in text for marker in ("revenue", "sales", "spend", "cost", "amount", "gmv", "收入", "销售额", "成本", "花费", "金额")):
        return "currency"
    return "number"


def _quote_field_reference(field: str) -> str:
    parts = [part.strip() for part in field.split(".") if part.strip()]
    if not parts:
        return field
    return ".".join(f'"{part.replace(chr(34), chr(34) + chr(34))}"' for part in parts)


def _first_metric_with_meaning(
    metrics: list[dict[str, Any]],
    meanings: tuple[str, ...],
    *,
    exclude_meanings: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    meaning_set = set(meanings)
    excluded = set(exclude_meanings)
    for metric in metrics:
        metric_meanings = set(metric.get("meanings") or [])
        if metric.get("formula") and meaning_set & metric_meanings and not (excluded & metric_meanings):
            return metric
    return None


def _add_derived_metric(
    metrics: dict[str, dict[str, Any]],
    *,
    name: str,
    business_label: str,
    formula: str,
    unit: str,
    source_fields: list[str],
    description: str,
) -> None:
    metrics[name] = {
        "name": name,
        "business_label": business_label,
        "formula": formula,
        "unit": unit,
        "source_fields": list(dict.fromkeys(source_fields)),
        "warnings": [],
        "description": description,
    }


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
        metric_registry = build_metric_registry(loaded_semantic_layer["semantic_layer"])
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
                "metric_registry": metric_registry,
                "formulas": metric_registry.get("formulas", {}),
                "warnings": metric_registry.get("warnings", []),
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
            "metric_registry": metric_registry,
            "formulas": metric_registry.get("formulas", {}),
            "warnings": metric_registry.get("warnings", []),
            "trace_event": _trace_event(question, matched_metrics, "success", latency_ms),
        }

    path = Path(metrics_path)
    use_semantic_layer = path.resolve() == DEFAULT_METRICS_PATH.resolve()
    if use_semantic_layer:
        semantic_context = retrieve_semantic_context(question)
        latency_ms = int((perf_counter() - started_at) * 1000)
        if semantic_context.get("success"):
            metric_registry = build_metric_registry({"metrics": semantic_context.get("metrics", {})})
            matched_metrics = semantic_context.get("matched_metrics", [])
            if not matched_metrics:
                error = f"No metric definition matched question: {question}"
                return {
                    "success": False,
                    "question": question,
                    "matched_metrics": [],
                    "metrics": {},
                    "semantic_context": semantic_context,
                    "metric_registry": metric_registry,
                    "formulas": metric_registry.get("formulas", {}),
                    "warnings": metric_registry.get("warnings", []),
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
                "metric_registry": metric_registry,
                "formulas": metric_registry.get("formulas", {}),
                "warnings": metric_registry.get("warnings", []),
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
    metric_registry = build_metric_registry({"metrics": selected})
    return {
        "success": True,
        "question": question,
        "matched_metrics": matched_metrics,
        "metrics": selected,
        "metrics_path": str(Path(metrics_path)),
        "metric_registry": metric_registry,
        "formulas": metric_registry.get("formulas", {}),
        "warnings": metric_registry.get("warnings", []),
        "trace_event": _trace_event(question, matched_metrics, "success", latency_ms),
    }
