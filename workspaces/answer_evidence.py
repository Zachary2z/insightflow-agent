from __future__ import annotations

from typing import Any


BUSINESS_FIELD_LABELS_ZH = {
    "store_name": "门店",
    "store": "门店",
    "shop_name": "门店",
    "sales_amount": "销售额",
    "total_sales": "总销售额",
    "satisfaction_score": "满意度",
    "score_nps": "满意度",
    "team_name": "团队",
    "issue_type": "客服问题",
    "ticket_count": "工单数",
    "avg_response_minutes": "平均响应时长",
    "response_minutes": "响应时长",
    "avg_resolution_hours": "平均解决时长",
    "resolution_hours": "解决时长",
    "total_revenue": "总收入",
    "sum_revenue": "总收入",
    "revenue": "收入",
    "gmv": "销售额",
    "order_count": "订单数",
    "orders": "订单数",
    "avg_order_value": "客单价",
    "avg_revenue_per_order": "客单价",
    "average_order_value": "客单价",
    "total_spend": "投放成本",
    "marketing_spend": "投放成本",
    "ad_spend": "投放成本",
    "spend": "投放成本",
    "cost": "成本",
    "roi": "ROI",
    "roas": "ROAS",
    "channel": "渠道",
    "segment": "客户分群",
    "customer_segment": "客户分群",
    "product": "商品",
    "product_name": "商品",
    "category": "品类",
    "region": "区域",
}

BUSINESS_FIELD_LABELS_EN = {
    "store_name": "store",
    "store": "store",
    "shop_name": "store",
    "sales_amount": "sales amount",
    "total_sales": "total sales",
    "satisfaction_score": "satisfaction score",
    "score_nps": "satisfaction score",
    "team_name": "team",
    "issue_type": "issue type",
    "ticket_count": "ticket count",
    "avg_response_minutes": "average response time",
    "response_minutes": "response time",
    "avg_resolution_hours": "average resolution time",
    "resolution_hours": "resolution time",
    "total_revenue": "total revenue",
    "sum_revenue": "total revenue",
    "revenue": "revenue",
    "gmv": "GMV",
    "order_count": "order count",
    "orders": "orders",
    "avg_order_value": "average order value",
    "avg_revenue_per_order": "average order value",
    "average_order_value": "average order value",
    "total_spend": "spend",
    "marketing_spend": "spend",
    "ad_spend": "spend",
    "spend": "spend",
    "cost": "cost",
    "roi": "ROI",
    "roas": "ROAS",
    "channel": "channel",
    "segment": "segment",
    "customer_segment": "segment",
    "product": "product",
    "product_name": "product",
    "category": "category",
    "region": "region",
}


def business_field_labels(*, chinese: bool) -> dict[str, str]:
    return BUSINESS_FIELD_LABELS_ZH if chinese else BUSINESS_FIELD_LABELS_EN


def business_field_label(key: Any, *, chinese: bool) -> str:
    text = str(key or "").strip()
    if not text:
        return ""
    return business_field_labels(chinese=chinese).get(text.lower(), text)


def rows_as_dicts(execution_result: dict[str, Any]) -> list[dict[str, Any]]:
    columns = [str(column) for column in execution_result.get("columns") or []]
    rows: list[dict[str, Any]] = []
    for row in execution_result.get("rows") or []:
        if isinstance(row, dict):
            rows.append({str(key): value for key, value in row.items() if str(key).strip()})
        elif isinstance(row, (list, tuple)):
            rows.append(
                {
                    column: row[index]
                    for index, column in enumerate(columns)
                    if column.strip() and index < len(row)
                }
            )
    return rows


def entity_key(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        for key, value in row.items():
            if not is_number(value):
                return key
    return ""


def entity_values(rows: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for row in rows:
        for value in row.values():
            if is_number(value):
                continue
            text = str(value or "").strip()
            if text and text not in values:
                values.append(text)
    return values


def metric_keys(rows: list[dict[str, Any]], execution_result: dict[str, Any] | None = None) -> list[str]:
    metrics: list[str] = []
    for row in rows:
        for key, value in row.items():
            if is_number(value) and key not in metrics:
                metrics.append(key)
    if metrics or execution_result is None:
        return metrics
    return [str(column) for column in execution_result.get("columns") or [] if str(column).strip()]


def primary_entity(rows: list[dict[str, Any]], *, entity_key_value: str, metric_key_values: list[str]) -> str:
    if not rows or not entity_key_value:
        return ""
    metric = metric_key_values[0] if metric_key_values else ""
    if not metric:
        return str(rows[0].get(entity_key_value) or "").strip()
    candidates = []
    for row in rows:
        entity = str(row.get(entity_key_value) or "").strip()
        value = to_number(row.get(metric))
        if entity and value is not None:
            candidates.append((entity, value))
    if not candidates:
        return str(rows[0].get(entity_key_value) or "").strip()
    return max(candidates, key=lambda item: item[1])[0]


def row_bullets(rows: list[dict[str, Any]], *, chinese: bool, limit: int = 3) -> list[str]:
    return business_row_sentences(rows, chinese=chinese, limit=limit)


def business_row_sentences(rows: list[dict[str, Any]], *, chinese: bool, limit: int = 3) -> list[str]:
    entity_key_value = entity_key(rows)
    metric_key_values = metric_keys(rows)
    if not rows or not entity_key_value or not metric_key_values:
        ending = "。" if chinese else "."
        return [row_summary(row, chinese=chinese) + ending for row in rows[:limit] if row]

    primary_metric = metric_key_values[0]
    ranked = _rank_rows_by_metric(rows, entity_key_value=entity_key_value, metric=primary_metric)
    if not ranked:
        return [row_summary(row, chinese=chinese) + "。" for row in rows[:limit] if row]

    metric_label = business_field_label(primary_metric, chinese=True)
    metric_unit = _metric_unit(primary_metric)
    if not chinese:
        metric_label = business_field_label(primary_metric, chinese=False)
        comparison_parts = []
        for entity, value, _row in ranked[:limit]:
            formatted = _format_business_value(value, metric=primary_metric, unit="")
            if not comparison_parts:
                comparison_parts.append(f"{entity} has the highest {metric_label} at {formatted}")
            else:
                comparison_parts.append(f"{entity} has {formatted}")
        return ["; ".join(comparison_parts) + "."]

    comparison_parts = []
    for entity, value, _row in ranked[:limit]:
        formatted = _format_business_value(value, metric=primary_metric, unit=metric_unit)
        if not comparison_parts:
            comparison_parts.append(f"{_entity_metric_text(entity, metric_label)}最高，为 {formatted}")
        else:
            comparison_parts.append(f"{_entity_value_text(entity)}为 {formatted}")

    bullets = ["；".join(comparison_parts) + "。"]
    leader_entity, _leader_value, leader_row = ranked[0]
    for metric in metric_key_values[1:limit]:
        value = to_number(leader_row.get(metric))
        if value is None:
            continue
        label = business_field_label(metric, chinese=True)
        unit = _metric_unit(metric)
        bullets.append(f"{_entity_value_text(leader_entity)}的{label}为 {_format_business_value(value, metric=metric, unit=unit)}。")
    return bullets[:limit]


def business_evidence_sentence(rows: list[dict[str, Any]], *, chinese: bool) -> str:
    bullets = business_row_sentences(rows, chinese=chinese, limit=3)
    return bullets[0] if bullets else ""


def reason_hypothesis_context(user_question: str, rows: list[dict[str, Any]], *, chinese: bool) -> str:
    if not chinese:
        return "available evidence only confirms the result, not the cause"
    text = " ".join(
        [
            str(user_question or ""),
            " ".join(str(key) for row in rows[:3] for key in row.keys()),
            " ".join(str(value) for row in rows[:3] for value in row.values() if not is_number(value)),
        ]
    ).lower()
    if any(marker in text for marker in ("issue", "ticket", "客服", "工单", "响应", "处理", "退款", "物流")):
        return "问题发生频次、处理复杂度或服务流程"
    if any(marker in text for marker in ("channel", "渠道", "投放", "预算", "spend", "cost", "roi", "roas")):
        return "流量质量、投放成本、转化效率或复购"
    if any(marker in text for marker in ("store", "门店", "sales", "销售", "客单", "区域", "满意度")):
        return "客流、客单价、商品结构或区域需求"
    return "需求规模、客户结构、运营承接或资源配置"


def _rank_rows_by_metric(
    rows: list[dict[str, Any]],
    *,
    entity_key_value: str,
    metric: str,
) -> list[tuple[str, float, dict[str, Any]]]:
    ranked: list[tuple[str, float, dict[str, Any]]] = []
    for row in rows:
        entity = str(row.get(entity_key_value) or "").strip()
        value = to_number(row.get(metric))
        if entity and value is not None:
            ranked.append((entity, value, row))
    return sorted(ranked, key=lambda item: item[1], reverse=True)


def _metric_unit(metric: str) -> str:
    lowered = str(metric or "").lower()
    if "ticket" in lowered or "工单" in lowered:
        return "件"
    if ("order" in lowered and "count" in lowered) or lowered in {"orders", "订单数"}:
        return "单"
    if "minute" in lowered or "分钟" in lowered:
        return "分钟"
    if "hour" in lowered or "小时" in lowered:
        return "小时"
    if "rate" in lowered or "share" in lowered:
        return "%"
    return ""


def _entity_metric_text(entity: str, metric_label: str) -> str:
    if _ends_with_ascii(entity) and metric_label:
        return f"{entity} {metric_label}"
    return f"{entity}{metric_label}"


def _entity_value_text(entity: str) -> str:
    if _ends_with_ascii(entity):
        return f"{entity} "
    return entity


def _ends_with_ascii(text: str) -> bool:
    value = str(text or "").strip()
    return bool(value) and value[-1].isascii()


def _format_business_value(value: float, *, metric: str, unit: str) -> str:
    if float(value).is_integer():
        formatted = f"{int(value)}"
    else:
        formatted = f"{value:.2f}".rstrip("0").rstrip(".")
    if unit == "%" and 0 <= value <= 1:
        formatted = f"{value * 100:.1f}".rstrip("0").rstrip(".")
    return f"{formatted} {unit}".rstrip()


def row_summary(row: dict[str, Any], *, chinese: bool) -> str:
    relation = " 为 " if chinese else " is "
    separator = "，" if chinese else ", "
    pairs = [f"{business_field_label(key, chinese=chinese)}{relation}{value}" for key, value in list(row.items())[:5]]
    return separator.join(pairs) if pairs else ("当前证据没有可展示字段" if chinese else "no displayable fields")


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(text or ""))


def is_number(value: Any) -> bool:
    return to_number(value) is not None


def to_number(value: Any) -> float | None:
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
