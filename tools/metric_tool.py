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
    capabilities = dict(semantic_layer.get("available_analysis_capabilities") or {})
    raw_metrics = semantic_layer.get("metrics") or []
    if isinstance(raw_metrics, dict):
        raw_metrics = raw_metrics.values()
    base_metrics = [_normalize_registry_metric(item) for item in raw_metrics if isinstance(item, dict)]
    metrics = {metric["name"]: metric for metric in base_metrics if metric.get("name")}
    warnings: list[str] = []

    revenue_metrics = _metrics_with_meaning(base_metrics, ("revenue_like", "sales_like", "gmv_like"))
    spend_metrics = _metrics_with_meaning(base_metrics, ("spend_like", "ad_spend_like", "marketing_spend_like"))
    cost_metrics = _metrics_with_meaning(base_metrics, ("cost_like",), exclude_meanings=("spend_like",))
    order_count_metrics = _metrics_with_meaning(base_metrics, ("order_count_like", "count_like"))
    revenue_spend_pair = _first_compatible_metric_pair(revenue_metrics, spend_metrics, semantic_layer)
    revenue_cost_pair = _first_compatible_metric_pair(revenue_metrics, cost_metrics, semantic_layer)
    revenue_order_pair = _first_compatible_metric_pair(revenue_metrics, order_count_metrics, semantic_layer)

    if revenue_spend_pair:
        revenue, spend = revenue_spend_pair
        _add_derived_metric(
            metrics,
            name="roas",
            business_label="广告投入产出比",
            formula=f'1.0 * {revenue["formula"]} / NULLIF({spend["formula"]}, 0)',
            unit="ratio",
            source_fields=[*revenue["source_fields"], *spend["source_fields"]],
            description="ROAS = revenue / spend. This is not net return.",
        )
        _add_derived_metric(
            metrics,
            name="net_return",
            business_label="净投放回报率",
            formula=f'1.0 * ({revenue["formula"]} - {spend["formula"]}) / NULLIF({spend["formula"]}, 0)',
            unit="percentage",
            source_fields=[*revenue["source_fields"], *spend["source_fields"]],
            description="Net return = (revenue - spend) / spend. This is not ROAS.",
        )
    elif revenue_metrics and spend_metrics:
        warnings.append(
            "ROAS 和净投放回报率需要收入和投放字段位于同一可分析粒度，"
            "或存在可确认关联字段，当前证据不足，未生成。"
        )
    else:
        warnings.append("ROAS 和净投放回报率需要同时存在收入类字段和花费类字段，当前证据不足，未生成。")

    if revenue_cost_pair:
        revenue, cost = revenue_cost_pair
        _add_derived_metric(
            metrics,
            name="margin_rate",
            business_label="利润率",
            formula=f'1.0 * ({revenue["formula"]} - {cost["formula"]}) / NULLIF({revenue["formula"]}, 0)',
            unit="percentage",
            source_fields=[*revenue["source_fields"], *cost["source_fields"]],
            description="Margin-like rate = (revenue - cost) / revenue.",
        )
    elif revenue_metrics and cost_metrics:
        warnings.append(
            "利润率需要收入和成本字段位于同一可分析粒度，或存在可确认关联字段，当前证据不足，未生成。"
        )
    else:
        warnings.append("利润率需要同时存在收入类字段和成本类字段，当前证据不足，未生成。")

    if revenue_order_pair:
        revenue, order_count = revenue_order_pair
        _add_derived_metric(
            metrics,
            name="average_order_value",
            business_label="客单价",
            formula=f'1.0 * {revenue["formula"]} / NULLIF({order_count["formula"]}, 0)',
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
        "available_analysis_capabilities": capabilities,
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
        "field": field,
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
        _field_column(item.get("field")),
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


def _metrics_with_meaning(
    metrics: list[dict[str, Any]],
    meanings: tuple[str, ...],
    *,
    exclude_meanings: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    meaning_set = set(meanings)
    excluded = set(exclude_meanings)
    return [
        metric
        for metric in metrics
        if metric.get("formula")
        and meaning_set & set(metric.get("meanings") or [])
        and not (excluded & set(metric.get("meanings") or []))
    ]


def _first_compatible_metric_pair(
    left_metrics: list[dict[str, Any]],
    right_metrics: list[dict[str, Any]],
    semantic_layer: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for left in left_metrics:
        for right in right_metrics:
            if _can_combine_metrics(left, right, semantic_layer):
                return left, right
    return None


def _field_table(field: str) -> str:
    parts = [part.strip().strip('"') for part in str(field or "").split(".") if part.strip()]
    return parts[0] if len(parts) >= 2 else ""


def _field_column(field: Any) -> str:
    parts = [part.strip().strip('"') for part in str(field or "").split(".") if part.strip()]
    return parts[-1] if parts else ""


def _metric_tables(metric: dict[str, Any]) -> set[str]:
    tables = {_field_table(str(metric.get("field") or ""))}
    tables.update(_field_table(str(field)) for field in metric.get("source_fields") or [])
    return {table for table in tables if table}


def _same_table(metric_a: dict[str, Any], metric_b: dict[str, Any]) -> bool:
    tables_a = _metric_tables(metric_a)
    tables_b = _metric_tables(metric_b)
    return bool(tables_a and tables_b and tables_a & tables_b)


def _has_safe_relationship(metric_a: dict[str, Any], metric_b: dict[str, Any], semantic_layer: dict[str, Any]) -> bool:
    tables_a = _metric_tables(metric_a)
    tables_b = _metric_tables(metric_b)
    if not tables_a or not tables_b:
        return False
    for relationship in _relationship_items(semantic_layer):
        left_table = str(relationship.get("left_table") or _field_table(str(relationship.get("left_field") or "")))
        right_table = str(relationship.get("right_table") or _field_table(str(relationship.get("right_field") or "")))
        if not left_table or not right_table:
            continue
        if (left_table in tables_a and right_table in tables_b) or (
            left_table in tables_b and right_table in tables_a
        ):
            return True
    return False


def _relationship_items(semantic_layer: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in ("relationships", "join_paths"):
        raw_items = semantic_layer.get(key) or []
        if isinstance(raw_items, dict):
            raw_items = raw_items.values()
        items.extend(item for item in raw_items if isinstance(item, dict))
    return items


def _can_combine_metrics(metric_a: dict[str, Any], metric_b: dict[str, Any], semantic_layer: dict[str, Any]) -> bool:
    if _same_table(metric_a, metric_b):
        return True
    if _has_safe_relationship(metric_a, metric_b, semantic_layer):
        return True
    return False


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
