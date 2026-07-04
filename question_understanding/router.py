from __future__ import annotations

import re
from typing import Any

from question_understanding.task_contract import (
    build_clarification_questions,
    extract_time_range,
    legacy_dimension_id,
    legacy_metric_id,
    normalize_analysis_task,
    strategy_for_task,
)


def _compact(text: str) -> str:
    return re.sub(r"[\s_\-（）()。,.，:：]+", "", text.lower())


def _contains(text: str, *keywords: str) -> bool:
    compact = _compact(text)
    return any(_compact(keyword) in compact for keyword in keywords)


def _extract_limit(question: str) -> int | None:
    top_match = re.search(r"(top|前|最高的?|最低的?|排名前)\s*(\d+)", question, flags=re.IGNORECASE)
    if top_match:
        return int(top_match.group(2))
    if _contains(question, "top5", "前五"):
        return 5
    if _contains(question, "top10", "前十"):
        return 10
    return None


def _extract_time_range(question: str) -> dict[str, Any]:
    return extract_time_range(question) or {}


def _extract_metric(question: str) -> str:
    if _contains(question, "净投放回报率", "净回报率", "net return", "net_return", "net roi", "netroi"):
        return "net_return"
    if _contains(question, "复购率", "复购"):
        return "repurchase_rate"
    if _contains(question, "客单价", "aov", "平均订单金额"):
        return "aov"
    if _contains(question, "订单量", "订单数", "订单数量", "ordercount"):
        return "order_count"
    if _contains(question, "销售额", "gmv", "成交额", "收入", "销售情况", "贡献", "占比", "支付金额", "paid amount"):
        return "gmv"
    if _contains(question, "花费", "费用", "成本", "投放成本", "spend", "cost"):
        return "spend"
    if _contains(question, "roas"):
        return "roas"
    if _contains(question, "roi"):
        return "roi"
    if _contains(question, "销量", "销售量"):
        return "product_sales"
    return ""


def _extract_dimension(question: str) -> str:
    if _contains(question, "门店", "店铺", "store", "store name"):
        return "store"
    if _contains(question, "商品", "产品", "product"):
        return "product"
    if _contains(question, "品类", "类别", "category"):
        return "category"
    if _contains(question, "城市", "city"):
        return "city"
    if _contains(question, "用户", "客户", "user"):
        return "user"
    if _contains(question, "渠道", "channel"):
        return "channel"
    return ""


def _extract_operation(question: str) -> str:
    if _contains(question, "删除", "更新", "写入", "插入", "drop", "delete", "update", "insert"):
        return "unsafe_write"
    if _contains(question, "趋势", "变化", "走势"):
        return "trend"
    if _contains(question, "下降", "下滑", "降低", "跌"):
        return "decline"
    if _contains(question, "roi", "roas", "投放成本", "加预算", "预算建议", "预算", "推荐", "建议"):
        return "comparison"
    if _contains(question, "对比", "比较", "环比", "同比"):
        return "comparison"
    if _contains(question, "最高", "最多", "贡献最大", "占比", "top", "前"):
        return "top_n"
    if _contains(question, "明细", "详情", "drilldown"):
        return "drilldown"
    if _contains(question, "看看", "总结", "概览", "情况"):
        return "summary"
    return ""


def _extract_filters(question: str, metric: str) -> list[str]:
    filters = []
    if metric in {"gmv", "order_count", "aov", "product_sales", "repurchase_rate"}:
        filters.append("paid_orders")
    if _contains(question, "不含退款", "排除退款", "剔除退款", "excluding refunds"):
        filters.append("exclude_refunds")
    if _contains(question, "新用户", "新客"):
        filters.append("new_users")
    return filters


def _risk_flags(question: str) -> list[str]:
    flags = []
    if _contains(question, "删除", "更新", "写入", "插入", "drop", "delete", "update", "insert"):
        flags.append("unsafe_operation")
    if _contains(question, "手机号", "电话", "邮箱", "email", "phone", "地址", "身份证", "payment"):
        flags.append("sensitive_field")
    if _contains(question, "导出所有", "全部用户", "所有用户", "批量导出"):
        flags.append("bulk_export")
    return flags


def _missing_slots(intent: dict[str, Any]) -> list[str]:
    required = ["metric", "dimension", "time_range"]
    return [slot for slot in required if not intent.get(slot)]


def _clarification_questions(missing: list[str], task: dict[str, Any] | None = None) -> list[str]:
    return build_clarification_questions(missing, task=task)


def _is_stable_template_intent(intent: dict[str, Any]) -> bool:
    stable_dimensions = {"product", "category", "city"}
    stable_metrics = {"gmv", "order_count", "product_sales"}
    stable_operations = {"top_n", "summary"}
    return (
        intent.get("metric") in stable_metrics
        and intent.get("dimension") in stable_dimensions
        and intent.get("operation") in stable_operations
    )


def understand_question(question: str, workspace_context: dict[str, Any] | None = None) -> dict[str, Any]:
    metric = _extract_metric(question)
    dimension = _extract_dimension(question)
    operation = _extract_operation(question)
    intent = {
        "metric": metric,
        "dimension": dimension,
        "time_range": _extract_time_range(question),
        "filters": _extract_filters(question, metric),
        "operation": operation,
        "limit": _extract_limit(question),
        "risk_flags": _risk_flags(question),
    }
    task = normalize_analysis_task(question, intent=intent, workspace_context=workspace_context)
    if task["metrics"] and not intent["metric"]:
        intent["metric"] = legacy_metric_id(task["metrics"][0])
    if task["dimensions"] and not intent["dimension"]:
        intent["dimension"] = legacy_dimension_id(task["dimensions"][0])
    if task["time_range"] and not intent["time_range"]:
        intent["time_range"] = task["time_range"]
    if not intent["operation"]:
        intent["operation"] = {
            "compare": "comparison",
            "rank": "top_n",
            "trend": "trend",
            "recommendation": "comparison",
            "summary": "summary",
            "anomaly": "comparison",
            "report": "summary",
        }.get(task["task_type"], "summary")

    if intent["risk_flags"]:
        return {
            "success": True,
            "strategy": "reject",
            "intent": intent,
            "analysis_task": task,
            "missing_slots": [],
            "clarification_questions": [],
            "risk_flags": intent["risk_flags"],
            "rejection_reason": "Request asks for sensitive fields or unsafe data access.",
            "reason": "Question understanding rejected the request before SQL planning.",
        }

    missing = task["missing_slots"]
    if missing:
        return {
            "success": True,
            "strategy": "clarify",
            "intent": intent,
            "analysis_task": task,
            "missing_slots": missing,
            "clarification_questions": _clarification_questions(missing, task),
            "risk_flags": [],
            "rejection_reason": "",
            "reason": "Question is missing required intent slots.",
        }

    strategy = "template" if _is_stable_template_intent(intent) else strategy_for_task(task)
    return {
        "success": True,
        "strategy": strategy,
        "intent": intent,
        "analysis_task": task,
        "missing_slots": [],
        "clarification_questions": [],
        "risk_flags": [],
        "rejection_reason": "",
        "reason": (
            "Question matches a stable deterministic intent pattern."
            if strategy == "template"
            else "Question is complete but not covered by stable deterministic intent patterns."
        ),
    }
