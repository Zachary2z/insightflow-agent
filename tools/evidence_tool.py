from __future__ import annotations

import re
from time import perf_counter
from typing import Any

from workspaces.time_range_defaults import full_range_default_note
from workspaces.answer_evidence import business_field_label
from observability.metrics import safely_get_metrics, safely_inc
from observability.logging import emit_observability_event, safely_emit


MISSING_DATA_TERMS = {
    "ad_impressions": "ad_impressions",
    "ctr": "ctr",
    "conversion_rate": "conversion_rate",
    "inventory": "inventory",
    "stock": "inventory",
    "库存": "inventory",
}

HYPOTHESIS_MARKERS = ("可能", "假设", "需要", "进一步验证", "无法验证", "might", "may", "hypothesis")

DEFAULT_BUSINESS_ALIASES = {
    "store_name": "门店",
    "store": "门店",
    "team_name": "团队",
    "ticket_count": "工单数",
    "avg_response_minutes": "平均响应时长",
    "response_minutes": "响应时长",
    "响应时长": "平均响应时长",
    "avg_resolution_hours": "平均解决时长",
    "resolution_hours": "解决时长",
    "total_revenue": "总收入",
    "sum_revenue": "总收入",
    "sales_amount": "销售额",
    "total_sales": "总销售额",
    "total_spend": "投放成本",
    "spend": "投放成本",
    "cost": "成本",
    "margin_rate": "利润率",
    "net_return": "净投放回报率",
    "repeat_rate": "复购率",
    "repurchase_rate": "复购率",
    "retention_rate": "留存率",
    "paid_amount": "成交金额",
    "total_amount": "成交金额",
    "transaction_amount": "成交金额",
    "quantity": "销量",
    "quantity_sold": "销量",
    "total_quantity": "销量",
    "sales_quantity": "销量",
    "customer_count": "客户数",
    "category_name": "品类",
}


def _normalize(text: Any) -> str:
    return str(text).lower().replace(" ", "")


def _trace_event(
    claim_count: int,
    supported_count: int,
    hypothesis_count: int,
    blocked_count: int,
    status: str,
    latency_ms: int,
    error: str | None = None,
) -> dict[str, Any]:
    summary = f"{supported_count} supported, {hypothesis_count} hypotheses, {blocked_count} blocked"
    event = {
        "tool_name": "validate_evidence",
        "tool_input_summary": f"{claim_count} claims",
        "tool_output_summary": summary,
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "evidence_validation_error"
        event["error"] = error
    return event


def _failure(started_at: float, claim_count: int, error: str) -> dict[str, Any]:
    latency_ms = int((perf_counter() - started_at) * 1000)
    result = {
        "success": False,
        "data_supported_findings": [],
        "hypotheses": [],
        "unsupported_claims_blocked": [],
        "unsupported_claim_rate": 0.0,
        "error": error,
        "trace_event": _trace_event(claim_count, 0, 0, 0, "error", latency_ms, error),
    }
    safely_inc(safely_get_metrics(), "evidence_validations", {"status": "error", "reason_category": "validation"})
    safely_emit(
        emit_observability_event,
        "evidence_validation_completed",
        operation="evidence_validation",
        status="error",
        error_type="validation",
        latency_ms=latency_ms,
    )
    return result


def _clean_claims(claims: list[str] | None) -> list[str]:
    if not claims:
        return []
    return [str(claim).strip() for claim in claims if str(claim).strip()]


def _extract_numbers(text: str) -> list[float]:
    numbers = []
    for match in re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", "")):
        try:
            numbers.append(float(match))
        except ValueError:
            continue
    return numbers


def _format_row(columns: list[str], row: list[Any]) -> str:
    return ", ".join(f"{column}={value}" for column, value in zip(columns, row, strict=False))


def _row_supports_claim(claim: str, execution_result: dict[str, Any] | None) -> str | None:
    if not execution_result or not execution_result.get("success"):
        return None

    claim_numbers = _extract_numbers(claim)
    if not claim_numbers:
        return None

    columns = execution_result.get("columns", [])
    rows = execution_result.get("rows", [])
    normalized_claim = _normalize(claim)

    for row in rows:
        row_text = _format_row(columns, row)
        dimension_values = [
            str(value)
            for value in row
            if not isinstance(value, int | float) or isinstance(value, bool)
        ]
        has_dimension_match = any(
            _normalize(value) in normalized_claim
            for value in dimension_values
            if len(_normalize(value)) >= 2
        )
        row_numbers = [
            float(value)
            for value in row
            if isinstance(value, int | float) and not isinstance(value, bool)
        ]
        has_number_match = any(
            abs(claim_number - row_number) < 0.000001
            for claim_number in claim_numbers
            for row_number in row_numbers
        )
        if has_dimension_match and has_number_match:
            return f"SQL result row: {row_text}"

    return None


def _business_context_supports_claim(claim: str, business_context: dict[str, Any] | None) -> str | None:
    if not business_context:
        return None

    normalized_claim = _normalize(claim)
    for rule in business_context.get("matched_rules", []):
        title = str(rule.get("title") or rule.get("id") or "business_rule")
        content = _normalize(rule.get("content", ""))
        if "paid" in normalized_claim and "paid" in content:
            return f"Business rule: {title}"
        if "gmv" in normalized_claim and "gmv" in content:
            return f"Business rule: {title}"

    return None


def _needs_more_data(claim: str) -> list[str]:
    normalized_claim = _normalize(claim)
    needed = []
    for term, canonical in MISSING_DATA_TERMS.items():
        if _normalize(term) in normalized_claim and canonical not in needed:
            needed.append(canonical)
    return needed


def _is_hypothesis(claim: str) -> bool:
    normalized_claim = _normalize(claim)
    return any(_normalize(marker) in normalized_claim for marker in HYPOTHESIS_MARKERS)


def build_evidence_payload(
    *,
    task: dict[str, Any] | None,
    execution_result: dict[str, Any] | None,
    metric_registry: dict[str, Any] | None = None,
    sql: str = "",
    filters: list[str] | None = None,
    business_aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    task = task or {}
    execution_result = execution_result or {}
    metric_registry = metric_registry or {}
    columns = [str(column) for column in execution_result.get("columns") or []]
    rows = list(execution_result.get("rows") or [])
    registry_warnings = [str(item) for item in metric_registry.get("warnings") or [] if str(item).strip()]
    comparison_scope = _comparison_scope(task, rows)
    warnings = [*registry_warnings]
    time_default_note = full_range_default_note(task.get("time_range") or task.get("time_scope") or {})
    if time_default_note:
        warnings.append(time_default_note)
    if not comparison_scope["sufficient"]:
        warnings.append(
            f"比较范围不足：{task.get('task_type') or 'analysis'} 类问题至少需要 "
            f"{comparison_scope['required_min_rows']} 行同口径候选对象，当前只有 {comparison_scope['row_count']} 行。"
        )

    aliases = _business_aliases(columns, metric_registry=metric_registry, overrides=business_aliases or {})
    display_values = [_display_row(row, columns, aliases, metric_registry) for row in rows]
    formulas = dict(metric_registry.get("formulas") or {})
    data_limits = _data_limits_for_requested_metrics(
        requested_metrics=list(task.get("metrics") or []),
        columns=columns,
        aliases=aliases,
        metric_registry=metric_registry,
        task=task,
    )
    evidence_requirements = _evidence_requirements(task, comparison_scope=comparison_scope, data_limits=data_limits)
    result_rows = _result_rows(rows, columns, aliases, metric_registry)
    derived_metrics = _derived_metrics(rows, columns, aliases, metric_registry, task=task)
    formula_metadata = _formula_metadata(metric_registry)
    chart_metric_keys = _requested_numeric_metric_keys(
        [_row_pairs_for_payload(row, columns) for row in rows],
        aliases,
        metric_registry,
        task=task,
    )

    return {
        "evidence_pack_version": "p23.shared.v1",
        "evidence_pack_kind": "shared_fact_payload",
        "task_type": str(task.get("task_type") or ""),
        "intent": {
            "task_type": str(task.get("task_type") or ""),
            "decision_goal": str(task.get("decision_goal") or ""),
        },
        "metrics": list(task.get("metrics") or []),
        "dimensions": list(task.get("dimensions") or []),
        "time_scope": task.get("time_range") or task.get("time_scope") or {},
        "time_range": task.get("time_range") or task.get("time_scope") or {},
        "filters": list(filters if filters is not None else task.get("filters") or []),
        "evidence_requirements": evidence_requirements,
        "comparison_scope": comparison_scope,
        "columns": columns,
        "rows": rows,
        "result_rows": result_rows,
        "derived_metrics": derived_metrics,
        "formulas": formulas,
        "formula_metadata": formula_metadata,
        "chart_data": _chart_data(rows, columns, preferred_metric_keys=chart_metric_keys),
        "warnings": list(dict.fromkeys(warnings)),
        "data_limits": data_limits,
        "display_values": display_values,
        "formatted_values": display_values,
        "technical_refs": {
            "sql": "technical_details.sql",
            "raw_rows": "technical_details.raw_rows",
        },
    }


def _comparison_scope(task: dict[str, Any], rows: list[Any]) -> dict[str, Any]:
    task_type = str(task.get("task_type") or "").lower()
    row_count = len(rows)
    required_min_rows = 2 if task_type in {"rank", "compare", "recommendation"} else 1
    return {
        "type": "peer_comparison" if task_type in {"rank", "compare", "recommendation"} else "result_set",
        "row_count": row_count,
        "required_min_rows": required_min_rows,
        "retained_rows": row_count,
        "sufficient": row_count >= required_min_rows,
    }


def _evidence_requirements(
    task: dict[str, Any],
    *,
    comparison_scope: dict[str, Any],
    data_limits: list[str],
) -> list[dict[str, Any]]:
    dimensions = [str(item) for item in task.get("dimensions") or [] if str(item).strip()]
    metrics = [str(item) for item in task.get("metrics") or [] if str(item).strip()]
    filters = [str(item) for item in task.get("filters") or [] if str(item).strip()]
    return [
        {
            "time_range": task.get("time_range") or task.get("time_scope") or {},
            "metrics": metrics,
            "dimensions": dimensions,
            "filters": filters,
            "group_by": list(task.get("group_by") or dimensions),
            "comparison_scope": comparison_scope,
            "calculation_type": str(task.get("calculation_type") or _calculation_type(task)),
            "missing_evidence": list(data_limits),
        }
    ]


def _calculation_type(task: dict[str, Any]) -> str:
    explicit = str(task.get("desired_calculation") or "").strip()
    if explicit:
        return explicit
    task_type = str(task.get("task_type") or "").lower()
    if task_type == "rank":
        return "ranking"
    if task_type == "trend":
        return "trend"
    if task_type == "compare":
        return "comparison"
    if task_type == "recommendation":
        return "recommendation"
    return task_type or "summary"


def _business_aliases(
    columns: list[str],
    *,
    metric_registry: dict[str, Any],
    overrides: dict[str, str],
) -> dict[str, str]:
    aliases = dict(DEFAULT_BUSINESS_ALIASES)
    aliases.update({str(key): str(value) for key, value in overrides.items() if str(key).strip() and str(value).strip()})
    for metric_name, metric in (metric_registry.get("metrics") or {}).items():
        if not isinstance(metric, dict):
            continue
        label = str(metric.get("business_label") or metric.get("label") or "").strip()
        name = str(metric.get("name") or metric_name or "").strip()
        if name and label:
            aliases[name] = label
    return {column: aliases.get(column, business_field_label(column, chinese=True)) for column in columns}


def _display_row(
    row: Any,
    columns: list[str],
    aliases: dict[str, str],
    metric_registry: dict[str, Any],
) -> dict[str, str]:
    pairs = _row_pairs_for_payload(row, columns)
    display: dict[str, str] = {}
    for key, value in pairs:
        label = aliases.get(key, key)
        display[label] = _format_business_value(value, key=key, label=label, metric_registry=metric_registry)
    return display


def _result_rows(
    rows: list[Any],
    columns: list[str],
    aliases: dict[str, str],
    metric_registry: dict[str, Any],
) -> list[dict[str, Any]]:
    result = []
    for index, row in enumerate(rows):
        pairs = _row_pairs_for_payload(row, columns)
        dimensions = []
        metrics = []
        for key, value in pairs:
            entry = {
                "key": key,
                "label": aliases.get(key, key),
                "value": value,
                "display_value": _format_business_value(
                    value,
                    key=key,
                    label=aliases.get(key, key),
                    metric_registry=metric_registry,
                ),
            }
            if _to_number(value) is None:
                dimensions.append(entry)
            else:
                metrics.append(entry)
        result.append(
            {
                "row_index": index,
                "dimensions": dimensions,
                "metrics": metrics,
            }
        )
    return result


def _derived_metrics(
    rows: list[Any],
    columns: list[str],
    aliases: dict[str, str],
    metric_registry: dict[str, Any],
    *,
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    pairs_by_row = [_row_pairs_for_payload(row, columns) for row in rows]
    metric_keys = _requested_numeric_metric_keys(pairs_by_row, aliases, metric_registry, task=task)
    if not metric_keys:
        return []

    derived = []
    for metric_key in metric_keys:
        derived.extend(_derived_metrics_for_key(rows, pairs_by_row, aliases, task=task, metric_key=metric_key))
    return derived


def _derived_metrics_for_key(
    rows: list[Any],
    pairs_by_row: list[list[tuple[str, Any]]],
    aliases: dict[str, str],
    *,
    task: dict[str, Any],
    metric_key: str,
) -> list[dict[str, Any]]:
    metric_label = aliases.get(metric_key, metric_key)
    values = [_to_number(dict(pairs).get(metric_key)) for pairs in pairs_by_row]
    derived = []
    total = sum(value for value in values if value is not None)
    if total:
        derived.append(
            {
                "metric_id": f"{metric_key}_share",
                "label": f"{metric_label}占比",
                "formula": f"{metric_key} / SUM({metric_key})",
                "source_columns": [metric_key],
                "unit": "percentage",
                "values": [
                    {
                        "row_index": index,
                        "value": None if value is None else value / total,
                        "display_value": "-" if value is None else f"{(value / total) * 100:.1f}%",
                    }
                    for index, value in enumerate(values)
                ],
            }
        )

    ranked_values = sorted(
        [(index, value) for index, value in enumerate(values) if value is not None],
        key=lambda item: item[1],
        reverse=True,
    )
    if ranked_values:
        ranks = {index: rank for rank, (index, _value) in enumerate(ranked_values, start=1)}
        derived.append(
            {
                "metric_id": f"{metric_key}_rank",
                "label": f"{metric_label}排名",
                "formula": f"RANK() OVER (ORDER BY {metric_key} DESC)",
                "source_columns": [metric_key],
                "unit": "rank",
                "values": [
                    {
                        "row_index": index,
                        "value": ranks.get(index),
                        "display_value": f"第 {ranks[index]} 名" if index in ranks else "-",
                    }
                    for index in range(len(rows))
                ],
            }
        )

    if str(task.get("task_type") or "").lower() == "trend" and len(values) >= 2 and values[0] not in (None, 0):
        first = values[0]
        last = values[-1]
        if first is not None and last is not None:
            change = (last - first) / abs(first)
            derived.append(
                {
                    "metric_id": f"{metric_key}_period_change",
                    "label": f"{metric_label}趋势变化",
                    "formula": f"({metric_key}_last - {metric_key}_first) / ABS({metric_key}_first)",
                    "source_columns": [metric_key],
                    "unit": "percentage",
                    "values": [
                        {
                            "row_index": len(values) - 1,
                            "value": change,
                            "display_value": f"{change * 100:.1f}%",
                        }
                    ],
                }
            )
    return derived


def _requested_numeric_metric_keys(
    pairs_by_row: list[list[tuple[str, Any]]],
    aliases: dict[str, str],
    metric_registry: dict[str, Any],
    *,
    task: dict[str, Any],
) -> list[str]:
    numeric_keys = _numeric_columns(pairs_by_row)
    if not numeric_keys:
        return []

    requested = [str(metric).strip() for metric in task.get("metrics") or [] if str(metric).strip()]
    matched: list[str] = []
    for metric in requested:
        key = _match_requested_metric_key(
            metric,
            numeric_keys=numeric_keys,
            aliases=aliases,
            metric_registry=metric_registry,
        )
        if key and key not in matched:
            matched.append(key)

    return matched or numeric_keys[:1]


def _numeric_columns(pairs_by_row: list[list[tuple[str, Any]]]) -> list[str]:
    numeric_keys: list[str] = []
    for pairs in pairs_by_row:
        for key, value in pairs:
            if _to_number(value) is not None and key not in numeric_keys:
                numeric_keys.append(key)
    return numeric_keys


def _match_requested_metric_key(
    requested_metric: str,
    *,
    numeric_keys: list[str],
    aliases: dict[str, str],
    metric_registry: dict[str, Any],
) -> str:
    requested = _normalize_metric_token(requested_metric)
    if not requested:
        return ""

    candidates_by_key = {
        key: _metric_key_candidates(key, aliases=aliases, metric_registry=metric_registry)
        for key in numeric_keys
    }
    for key, candidates in candidates_by_key.items():
        if requested in candidates:
            return key
    for key, candidates in candidates_by_key.items():
        if any(requested in candidate or candidate in requested for candidate in candidates if candidate):
            return key
    return ""


def _metric_key_candidates(
    key: str,
    *,
    aliases: dict[str, str],
    metric_registry: dict[str, Any],
) -> set[str]:
    candidates = {
        _normalize_metric_token(key),
        _normalize_metric_token(aliases.get(key, "")),
    }
    key_leaf = key.split(".")[-1]
    candidates.add(_normalize_metric_token(key_leaf))
    for metric_id, metric in (metric_registry.get("metrics") or {}).items():
        if not isinstance(metric, dict):
            continue
        values = [
            metric_id,
            metric.get("name"),
            metric.get("business_label"),
            metric.get("label"),
            *(metric.get("aliases") or []),
            *(metric.get("source_fields") or []),
        ]
        normalized_values = {_normalize_metric_token(value) for value in values}
        source_leafs = {
            _normalize_metric_token(str(value).split(".")[-1])
            for value in metric.get("source_fields") or []
        }
        if _normalize_metric_token(key) in normalized_values | source_leafs:
            candidates.update(normalized_values)
            candidates.update(source_leafs)
    return {candidate for candidate in candidates if candidate}


def _formula_metadata(metric_registry: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = metric_registry.get("metrics") or {}
    formulas = metric_registry.get("formulas") or {}
    metadata: list[dict[str, Any]] = []
    for metric_id, formula in formulas.items():
        metric = metrics.get(metric_id) if isinstance(metrics, dict) else {}
        metric = metric if isinstance(metric, dict) else {}
        metadata.append(
            {
                "metric_id": str(metric_id),
                "label": str(metric.get("business_label") or metric.get("label") or metric_id),
                "formula": str(formula),
                "source_columns": [str(item) for item in metric.get("source_fields") or []],
                "unit": str(metric.get("unit") or ""),
                "derived": str(metric_id) in {"roas", "net_return", "margin_rate", "average_order_value"},
            }
        )
    return metadata


def _data_limits_for_requested_metrics(
    *,
    requested_metrics: list[Any],
    columns: list[str],
    aliases: dict[str, str],
    metric_registry: dict[str, Any],
    task: dict[str, Any],
) -> list[str]:
    available = _supported_metric_tokens(columns=columns, aliases=aliases, metric_registry=metric_registry)
    for metric_id, metric in (metric_registry.get("metrics") or {}).items():
        if not isinstance(metric, dict):
            continue
        available.update(_metric_token_aliases(metric_id))
        available.update(_metric_token_aliases(metric.get("name") or ""))
        available.update(_metric_token_aliases(metric.get("business_label") or metric.get("label") or ""))
    limits = []
    for metric in requested_metrics:
        metric_text = str(metric or "").strip()
        normalized = _normalize_metric_token(metric_text)
        supported = _metric_supported(metric_text, available)
        capability_limit = _capability_limit_for_requested_metric(
            metric_text,
            capabilities=metric_registry.get("available_analysis_capabilities") or {},
        )
        if capability_limit and not supported:
            limits.append(capability_limit)
        if normalized and not supported:
            limits.append(f"请求的指标 {metric_text} 未在当前证据字段或指标注册表中找到，未计算。")
    limits.extend(
        _capability_limits_for_task(
            metric_registry.get("available_analysis_capabilities") or {},
            metric_registry,
            requested_metrics,
            task=task,
            available=available,
        )
    )
    return list(dict.fromkeys(limits))


def _supported_metric_tokens(
    *,
    columns: list[str],
    aliases: dict[str, str],
    metric_registry: dict[str, Any],
) -> set[str]:
    tokens: set[str] = set()
    for column in columns:
        tokens.update(_metric_token_aliases(column))
        tokens.update(_metric_token_aliases(column.split(".")[-1]))
    for key, label in aliases.items():
        tokens.update(_metric_token_aliases(key))
        tokens.update(_metric_token_aliases(label))
    for metric_id, metric in (metric_registry.get("metrics") or {}).items():
        if not isinstance(metric, dict):
            continue
        values = [
            metric_id,
            metric.get("name"),
            metric.get("business_label"),
            metric.get("label"),
            metric.get("field"),
            *(metric.get("source_fields") or []),
            *(metric.get("aliases") or []),
        ]
        for value in values:
            tokens.update(_metric_token_aliases(value))
    return {token for token in tokens if token}


def _metric_supported(metric_text: str, available: set[str]) -> bool:
    candidates = _metric_token_aliases(metric_text)
    if candidates & available:
        return True
    return any(
        candidate in available_token or available_token in candidate
        for candidate in candidates
        for available_token in available
        if len(candidate) >= 2 and len(available_token) >= 2
    )


def _capability_limit_for_requested_metric(metric_text: str, *, capabilities: dict[str, Any]) -> str:
    normalized = _normalize_metric_token(metric_text)
    if normalized in {"利润", "利润率", "margin", "marginrate", "profit"} and capabilities.get("can_calculate_profit") is False:
        return f"请求的指标 {metric_text} 需要收入字段和成本字段，当前证据不足，未计算。"
    if normalized in {"roi", "roas", "投入产出", "投入产出比"} and capabilities.get("can_calculate_roi") is False:
        return f"请求的指标 {metric_text} 需要收入字段和投放/花费字段，当前证据不足，未计算。"
    return ""


def _capability_limits_for_task(
    capabilities: dict[str, Any],
    metric_registry: dict[str, Any],
    requested_metrics: list[Any],
    *,
    task: dict[str, Any],
    available: set[str],
) -> list[str]:
    limits: list[str] = []
    warnings_text = "\n".join(str(item) for item in metric_registry.get("warnings") or [])
    requested_text = " ".join(str(metric) for metric in requested_metrics)
    profit_supported = any(_metric_supported(metric, available) for metric in ("利润", "利润率", "margin_rate"))
    roi_supported = any(_metric_supported(metric, available) for metric in ("ROI", "ROAS", "roi", "roas"))
    if (
        capabilities.get("can_calculate_profit") is False
        and not profit_supported
        and ("利润" in requested_text or "成本字段" in warnings_text)
    ):
        limits.append("利润、利润率需要成本字段；当前证据不足，未计算。")
    if capabilities.get("can_calculate_roi") is False and not roi_supported and (
        "ROI" in requested_text.upper() or "ROAS" in requested_text.upper() or "花费类字段" in warnings_text
    ):
        limits.append("ROI/ROAS 需要收入字段和投放/花费字段；当前证据不足，未计算。")
    time_range = task.get("time_range") or task.get("time_scope") or {}
    if task.get("requires_time_field") and capabilities.get("can_analyze_trends") is False:
        raw_time = ""
        if isinstance(time_range, dict):
            raw_time = str(time_range.get("raw_text") or "")
        limits.append(f"{raw_time or '请求的时间范围'} 需要时间字段；当前证据不足，未应用该时间范围或趋势分析。")
    if task.get("requires_join") and capabilities.get("can_join_tables") is False:
        limits.append("跨表分析需要可确认的关联字段；当前证据不足，未做跨表投入产出分析。")
    return limits


def _normalize_metric_token(value: Any) -> str:
    return re.sub(r"[\s_\-（）()，,。.:：/]+", "", str(value or "").lower())


def _metric_token_aliases(value: Any) -> set[str]:
    raw_text = str(value or "")
    token = _normalize_metric_token(raw_text)
    if not token:
        return set()
    aliases = {token}
    for part in re.split(r"[\s_\-（）()，,。.:：/]+", raw_text):
        part_token = _normalize_metric_token(part)
        if len(part_token) >= 2:
            aliases.add(part_token)
    synonym_groups = (
        ("复购率", "复购", "repeatrate", "repurchaserate", "repeatpurchaserate"),
        ("成交金额", "成交额", "销售额", "收入", "营收", "paidamount", "totalamount", "transactionamount", "salesamount", "revenue", "gmv"),
        ("销量", "销售量", "quantity", "quantitysold", "totalquantity", "salesquantity", "qtysold"),
        ("客户数", "customercount", "customers", "usercount"),
        ("投放", "投放金额", "投放成本", "花费", "广告费", "spend", "adspend", "marketingspend", "cost"),
        ("roi", "roas", "投入产出", "投入产出比"),
        ("利润", "利润率", "margin", "marginrate", "profit"),
    )
    for group in synonym_groups:
        normalized_group = {_normalize_metric_token(item) for item in group}
        if token in normalized_group:
            aliases.update(normalized_group)
    return aliases


def _chart_data(rows: list[Any], columns: list[str], *, preferred_metric_keys: list[str] | None = None) -> dict[str, Any]:
    pairs_by_row = [_row_pairs_for_payload(row, columns) for row in rows]
    x_axis = ""
    y_axis = ""
    preferred_metrics = list(preferred_metric_keys or [])
    for pairs in pairs_by_row:
        for key, value in pairs:
            if not x_axis and _to_number(value) is None:
                x_axis = key
            if not y_axis and key in preferred_metrics and _to_number(value) is not None:
                y_axis = key
        if x_axis and y_axis:
            break
    for pairs in pairs_by_row:
        for key, value in pairs:
            if not y_axis and _to_number(value) is not None:
                y_axis = key
        if x_axis and y_axis:
            break
    return {
        "columns": columns,
        "rows": rows,
        "x_axis": x_axis,
        "y_axis": y_axis,
    }


def _row_pairs_for_payload(row: Any, columns: list[str]) -> list[tuple[str, Any]]:
    if isinstance(row, dict):
        return [(str(key), value) for key, value in row.items()]
    if isinstance(row, (list, tuple)):
        return [(column, row[index]) for index, column in enumerate(_unique_columns(columns)) if index < len(row)]
    return []


def _unique_columns(columns: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    unique: list[str] = []
    for column in columns:
        counts[column] = counts.get(column, 0) + 1
        unique.append(column if counts[column] == 1 else f"{column}_{counts[column]}")
    return unique


def _format_business_value(value: Any, *, key: str, label: str = "", metric_registry: dict[str, Any]) -> str:
    if value is None:
        return "-"
    number = _to_number(value)
    if number is None:
        return str(value)
    unit = _unit_for_key(key, metric_registry, label=label)
    if unit == "percentage":
        return f"{number * 100:.1f}%"
    if unit == "currency" and abs(number) >= 10000:
        return f"{number / 10000:.1f} 万"
    if float(number).is_integer():
        return str(int(number))
    return f"{number:.4f}".rstrip("0").rstrip(".")


def _unit_for_key(key: str, metric_registry: dict[str, Any], *, label: str = "") -> str:
    metrics = metric_registry.get("metrics") or {}
    metric = metrics.get(key) if isinstance(metrics, dict) else None
    if isinstance(metric, dict) and metric.get("unit"):
        return str(metric["unit"])
    lowered = f"{key} {label}".lower()
    if any(marker in lowered for marker in ("rate", "margin", "net_return", "roi")) and "roas" not in lowered:
        return "percentage"
    if any(
        marker in lowered
        for marker in ("revenue", "sales", "amount", "spend", "cost", "gmv", "收入", "销售额", "成本", "花费")
    ):
        return "currency"
    return "number"


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
    return None


def validate_evidence(
    claims: list[str] | None,
    execution_result: dict[str, Any] | None,
    business_context: dict[str, Any] | None = None,
    metric_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started_at = perf_counter()
    del metric_context

    cleaned_claims = _clean_claims(claims)
    if not cleaned_claims:
        return _failure(started_at, 0, "claims are required for evidence validation")

    data_supported_findings = []
    hypotheses = []
    unsupported_claims_blocked = []

    for claim in cleaned_claims:
        evidence = _row_supports_claim(claim, execution_result) or _business_context_supports_claim(claim, business_context)
        if evidence:
            data_supported_findings.append(
                {
                    "claim": claim,
                    "evidence": evidence,
                    "confidence": 0.95,
                }
            )
            continue

        if _is_hypothesis(claim):
            hypotheses.append(
                {
                    "claim": claim,
                    "reason": "Claim is framed as a hypothesis or references data not present in current evidence.",
                    "needs_more_data": _needs_more_data(claim),
                }
            )
            continue

        unsupported_claims_blocked.append(claim)

    latency_ms = int((perf_counter() - started_at) * 1000)
    metric_status = "success" if not unsupported_claims_blocked else "rejected"
    result = {
        "success": True,
        "data_supported_findings": data_supported_findings,
        "hypotheses": hypotheses,
        "unsupported_claims_blocked": unsupported_claims_blocked,
        "unsupported_claim_rate": len(unsupported_claims_blocked) / len(cleaned_claims),
        "trace_event": _trace_event(
            len(cleaned_claims),
            len(data_supported_findings),
            len(hypotheses),
            len(unsupported_claims_blocked),
            "success",
            latency_ms,
        ),
    }
    safely_inc(
        safely_get_metrics(),
        "evidence_validations",
        {"status": metric_status, "reason_category": "validation" if unsupported_claims_blocked else "not_required"},
    )
    safely_emit(
        emit_observability_event,
        "evidence_validation_completed",
        operation="evidence_validation",
        status=metric_status,
        error_type="validation" if unsupported_claims_blocked else None,
        latency_ms=latency_ms,
    )
    return result
