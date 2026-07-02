from __future__ import annotations

import re
from time import perf_counter
from typing import Any

from workspaces.answer_evidence import business_field_label


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
    return {
        "success": False,
        "data_supported_findings": [],
        "hypotheses": [],
        "unsupported_claims_blocked": [],
        "unsupported_claim_rate": 0.0,
        "error": error,
        "trace_event": _trace_event(claim_count, 0, 0, 0, "error", latency_ms, error),
    }


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
    )
    result_rows = _result_rows(rows, columns, aliases, metric_registry)
    derived_metrics = _derived_metrics(rows, columns, aliases, metric_registry, task=task)
    formula_metadata = _formula_metadata(metric_registry)

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
        "comparison_scope": comparison_scope,
        "columns": columns,
        "rows": rows,
        "result_rows": result_rows,
        "derived_metrics": derived_metrics,
        "formulas": formulas,
        "formula_metadata": formula_metadata,
        "chart_data": _chart_data(rows, columns),
        "warnings": list(dict.fromkeys(warnings)),
        "data_limits": data_limits,
        "display_values": display_values,
        "formatted_values": display_values,
        "technical_sql": str(sql or ""),
        "technical_refs": {
            "sql": "technical_details.sql",
            "raw_rows": "technical_details.raw_rows",
        },
        "technical_details": {
            "sql": str(sql or ""),
            "row_count": len(rows),
            "truncated": bool(execution_result.get("truncated")),
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
    metric_key = _first_numeric_column(pairs_by_row)
    if not metric_key:
        return []

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


def _first_numeric_column(pairs_by_row: list[list[tuple[str, Any]]]) -> str:
    for pairs in pairs_by_row:
        for key, value in pairs:
            if _to_number(value) is not None:
                return key
    return ""


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
) -> list[str]:
    available = {_normalize_metric_token(column) for column in columns}
    available.update(_normalize_metric_token(label) for label in aliases.values())
    for metric_id, metric in (metric_registry.get("metrics") or {}).items():
        if not isinstance(metric, dict):
            continue
        available.add(_normalize_metric_token(metric_id))
        available.add(_normalize_metric_token(metric.get("name") or ""))
        available.add(_normalize_metric_token(metric.get("business_label") or metric.get("label") or ""))
    limits = []
    for metric in requested_metrics:
        metric_text = str(metric or "").strip()
        normalized = _normalize_metric_token(metric_text)
        if normalized and normalized not in available:
            limits.append(f"请求的指标 {metric_text} 未在当前证据字段或指标注册表中找到，未计算。")
    return list(dict.fromkeys(limits))


def _normalize_metric_token(value: Any) -> str:
    return re.sub(r"[\s_\-]+", "", str(value or "").lower())


def _chart_data(rows: list[Any], columns: list[str]) -> dict[str, Any]:
    pairs_by_row = [_row_pairs_for_payload(row, columns) for row in rows]
    x_axis = ""
    y_axis = ""
    for pairs in pairs_by_row:
        for key, value in pairs:
            if not x_axis and _to_number(value) is None:
                x_axis = key
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
        return [(column, row[index]) for index, column in enumerate(columns) if index < len(row)]
    return []


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
    return {
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
