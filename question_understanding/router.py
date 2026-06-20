from __future__ import annotations

import re
from typing import Any


def _compact(text: str) -> str:
    return text.lower().replace(" ", "")


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
    match = re.search(r"最近\s*(\d+)\s*天", question)
    if match:
        days = int(match.group(1))
        return {"type": "last_n_days", "value": days, "raw_text": f"最近 {days} 天"}

    match = re.search(r"最近\s*(\d+)\s*个?月", question)
    if match:
        months = int(match.group(1))
        return {"type": "last_n_months", "value": months, "raw_text": f"最近 {months} 个月"}

    if _contains(question, "本周", "这周"):
        return {"type": "this_week", "raw_text": "本周"}
    if _contains(question, "本月", "这个月"):
        return {"type": "this_month", "raw_text": "本月"}
    if _contains(question, "季度", "本季度"):
        return {"type": "quarter", "raw_text": "季度"}
    return {}


def _extract_metric(question: str) -> str:
    if _contains(question, "复购率", "复购"):
        return "repurchase_rate"
    if _contains(question, "客单价", "aov", "平均订单金额"):
        return "aov"
    if _contains(question, "订单量", "订单数", "订单数量", "ordercount"):
        return "order_count"
    if _contains(question, "销售额", "gmv", "成交额", "收入", "销售情况"):
        return "gmv"
    if _contains(question, "销量", "销售量"):
        return "product_sales"
    return ""


def _extract_dimension(question: str) -> str:
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
    if _contains(question, "对比", "比较", "环比", "同比"):
        return "comparison"
    if _contains(question, "最高", "最多", "top", "前"):
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
    required = ["metric", "dimension", "time_range", "operation"]
    return [slot for slot in required if not intent.get(slot)]


def _clarification_questions(missing: list[str]) -> list[str]:
    questions = []
    if "metric" in missing:
        questions.append("请确认要分析的指标，例如 GMV、订单量、客单价或复购率？")
    if "dimension" in missing:
        questions.append("请确认要按哪个维度分析，例如商品、品类、城市或用户？")
    if "time_range" in missing:
        questions.append("请确认分析时间范围，例如最近 30 天、本周、本月或最近 3 个月？")
    if "operation" in missing:
        questions.append("请确认分析方式，例如 Top N、趋势、对比、下降原因或概览？")
    return questions


def _is_stable_template_intent(intent: dict[str, Any]) -> bool:
    stable_dimensions = {"product", "category", "city"}
    stable_metrics = {"gmv", "order_count", "product_sales"}
    stable_operations = {"top_n", "summary"}
    return (
        intent.get("metric") in stable_metrics
        and intent.get("dimension") in stable_dimensions
        and intent.get("operation") in stable_operations
    )


def understand_question(question: str) -> dict[str, Any]:
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

    if intent["risk_flags"]:
        return {
            "success": True,
            "strategy": "reject",
            "intent": intent,
            "missing_slots": [],
            "clarification_questions": [],
            "risk_flags": intent["risk_flags"],
            "rejection_reason": "Request asks for sensitive fields or unsafe data access.",
            "reason": "Question understanding rejected the request before SQL planning.",
        }

    missing = _missing_slots(intent)
    if missing:
        return {
            "success": True,
            "strategy": "clarify",
            "intent": intent,
            "missing_slots": missing,
            "clarification_questions": _clarification_questions(missing),
            "risk_flags": [],
            "rejection_reason": "",
            "reason": "Question is missing required intent slots.",
        }

    strategy = "template" if _is_stable_template_intent(intent) else "llm_candidate"
    return {
        "success": True,
        "strategy": strategy,
        "intent": intent,
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
