from __future__ import annotations

import re
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
    "efficiency": "效率指标",
    "profit": "毛利润",
    "gross_profit": "毛利润",
    "margin": "利润率",
    "profit_margin": "利润率",
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
    "efficiency": "efficiency",
    "profit": "profit",
    "gross_profit": "gross profit",
    "margin": "margin",
    "profit_margin": "profit margin",
    "repeat_rate": "repeat purchase rate",
    "repurchase_rate": "repeat purchase rate",
    "retention_rate": "retention rate",
    "paid_amount": "transaction amount",
    "total_amount": "transaction amount",
    "transaction_amount": "transaction amount",
    "quantity": "quantity sold",
    "quantity_sold": "quantity sold",
    "total_quantity": "quantity sold",
    "sales_quantity": "quantity sold",
    "customer_count": "customer count",
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
    lowered = text.lower()
    exact = business_field_labels(chinese=chinese).get(lowered)
    if exact:
        return exact
    dynamic = _dynamic_business_field_label(lowered, chinese=chinese)
    return dynamic or text


def localize_business_field_names(text: Any, *, chinese: bool) -> str:
    """Replace SQL-style aliases in product-facing text with business labels."""

    value = str(text or "")
    if not value:
        return ""

    def replace(match: re.Match[str]) -> str:
        raw = match.group(0)
        label = business_field_label(raw, chinese=chinese)
        return label if label and label != raw else raw

    return re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\b", replace, value)


def rows_as_dicts(execution_result: dict[str, Any]) -> list[dict[str, Any]]:
    columns = _unique_columns([str(column) for column in execution_result.get("columns") or []])
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


def _unique_columns(columns: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    unique: list[str] = []
    for column in columns:
        counts[column] = counts.get(column, 0) + 1
        unique.append(column if counts[column] == 1 else f"{column}_{counts[column]}")
    return unique


def entity_key(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        for key, value in row.items():
            if _is_internal_entity_key(key) or _is_internal_entity_value(value):
                continue
            if not is_number(value):
                return key
    return ""


def entity_values(rows: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for row in rows:
        for key, value in row.items():
            if _is_internal_entity_key(key) or _is_internal_entity_value(value):
                continue
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
            if _is_internal_entity_key(key):
                continue
            if is_number(value) and key not in metrics:
                metrics.append(key)
    if metrics or execution_result is None:
        return metrics
    return [str(column) for column in execution_result.get("columns") or [] if str(column).strip()]


def _is_internal_entity_key(key: Any) -> bool:
    return str(key or "").strip().lower() in {"task_id", "task_purpose"}


def _is_internal_entity_value(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    return any(
        marker in text
        for marker in (
            "corefact",
            "core_fact",
            "explanationsupport",
            "explanation_support",
            "trendoranomalysupport",
            "trend_or_anomaly_support",
            "task_id",
            "task_purpose",
        )
    )


def _dynamic_business_field_label(lowered: str, *, chinese: bool) -> str:
    tokens = _field_tokens(lowered)
    token_set = set(tokens)
    if not tokens:
        return ""
    if "roi" in token_set:
        return "ROI"
    if "roas" in token_set:
        return "ROAS"
    has_total = bool(token_set & {"total", "sum", "summed"})
    has_avg = bool(token_set & {"avg", "average", "mean"})
    if "priority" in token_set and "score" in token_set:
        return "优先级评分" if chinese else "priority score"
    if ("ticket" in token_set or "tickets" in token_set or "issue" in token_set or "issues" in token_set) and (
        has_total or "count" in token_set or "volume" in token_set
    ):
        if chinese:
            return "总工单数" if has_total else "工单数"
        return "total tickets" if has_total else "ticket count"
    if has_avg and "response" in token_set:
        return "平均响应时长" if chinese else "average response time"
    if has_avg and "resolution" in token_set:
        return "平均解决时长" if chinese else "average resolution time"
    if (has_total or "sum" in token_set) and ("revenue" in token_set or "income" in token_set):
        return "总收入" if chinese else "total revenue"
    if (has_total or "sum" in token_set) and ("sales" in token_set or "gmv" in token_set):
        return "总销售额" if chinese else "total sales"
    if has_avg and "order" in token_set and (
        "revenue" in token_set or "value" in token_set or "amount" in token_set
    ):
        return "客单价" if chinese else "average order value"
    if "order" in token_set and ("count" in token_set or has_total):
        return "订单数" if chinese else "order count"
    if "spend" in token_set:
        return "投放成本" if chinese else "spend"
    if "cost" in token_set:
        return "成本" if chinese else "cost"
    if "conversion" in token_set and "rate" in token_set:
        return "转化率" if chinese else "conversion rate"
    if ("repeat" in token_set or "repurchase" in token_set) and "rate" in token_set:
        return "复购率" if chinese else "repeat purchase rate"
    if "retention" in token_set and "rate" in token_set:
        return "留存率" if chinese else "retention rate"
    if "paid" in token_set and "amount" in token_set:
        return "成交金额" if chinese else "transaction amount"
    if "transaction" in token_set and "amount" in token_set:
        return "成交金额" if chinese else "transaction amount"
    if ("quantity" in token_set or "qty" in token_set) and ("sold" in token_set or has_total):
        return "销量" if chinese else "quantity sold"
    if "satisfaction" in token_set and "score" in token_set:
        return "满意度" if chinese else "satisfaction score"
    if "score" in token_set:
        return "评分" if chinese else ""
    return ""


def _field_tokens(value: str) -> list[str]:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower())
    return [token for token in normalized.split("_") if token]


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
