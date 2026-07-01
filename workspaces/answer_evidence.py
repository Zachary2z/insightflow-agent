from __future__ import annotations

from typing import Any


BUSINESS_FIELD_LABELS_ZH = {
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


def business_field_label(key: Any, *, chinese: bool) -> str:
    text = str(key or "").strip()
    if not text:
        return ""
    if chinese:
        return BUSINESS_FIELD_LABELS_ZH.get(text.lower(), text)
    return text


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
    bullets = []
    for index, row in enumerate(rows[:limit], start=1):
        summary = row_summary(row, chinese=chinese)
        bullets.append(f"第 {index} 行：{summary}。" if chinese else f"Row {index}: {summary}.")
    return bullets


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
