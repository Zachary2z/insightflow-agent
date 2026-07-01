from __future__ import annotations

import re
from typing import Any


ALLOWED_TASK_TYPES = {"compare", "rank", "trend", "summary", "anomaly", "recommendation", "report", "clarification"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}


def compact_text(value: Any) -> str:
    return re.sub(r"[\s_\-（）()。,.，:：]+", "", str(value or "").lower())


def contains_any(text: str, keywords: list[str] | tuple[str, ...]) -> bool:
    compact = compact_text(text)
    return any(compact_text(keyword) in compact for keyword in keywords)


def normalize_analysis_task(
    question: str,
    *,
    intent: dict[str, Any] | None = None,
    workspace_context: dict[str, Any] | None = None,
    provider_task: dict[str, Any] | None = None,
) -> dict[str, Any]:
    intent = intent or {}
    provider_task = provider_task or {}

    metrics = _dedupe(
        [
            *_semantic_matches(question, workspace_context, key="semantic_metrics"),
            *_normalize_metric_values(intent.get("metric")),
            *_normalize_metric_values(provider_task.get("metrics")),
            *_question_metric_matches(question),
        ]
    )
    dimensions = _dedupe(
        [
            *_semantic_matches(question, workspace_context, key="semantic_dimensions"),
            *_normalize_dimension_values(intent.get("dimension")),
            *_normalize_dimension_values(provider_task.get("dimensions")),
            *_question_dimension_matches(question),
        ]
    )

    time_range = _normalize_time_range(
        provider_task.get("time_range")
        if provider_task.get("time_range") not in (None, {}, "")
        else intent.get("time_range")
    )
    if time_range is None:
        time_range = extract_time_range(question)

    task_type = _normalize_task_type(provider_task.get("task_type") or intent.get("operation") or "", question)
    filters = _normalize_string_list(provider_task.get("filters"))
    if not filters:
        filters = _normalize_string_list(intent.get("filters"))
    decision_goal = _decision_goal(question, provider_task.get("decision_goal"))

    missing_slots = _missing_slots(task_type=task_type, metrics=metrics, dimensions=dimensions, time_range=time_range)
    confidence = _confidence(provider_task.get("confidence"), missing_slots)
    resolved_question = str(provider_task.get("resolved_question") or question or "").strip()

    return {
        "task_type": task_type if task_type in ALLOWED_TASK_TYPES else "summary",
        "dimensions": dimensions,
        "metrics": metrics,
        "time_range": time_range,
        "filters": filters,
        "decision_goal": decision_goal,
        "missing_slots": missing_slots,
        "defaults_applied": _normalize_string_list(provider_task.get("defaults_applied")),
        "resolved_question": resolved_question,
        "output_language": "zh",
        "confidence": confidence,
    }


def extract_time_range(question: str) -> dict[str, Any] | None:
    match = re.search(r"最近\s*(\d+)\s*天", question)
    if not match:
        match = re.search(r"last\s*(\d+)\s*days?", question, flags=re.IGNORECASE)
    if match:
        days = int(match.group(1))
        return {"type": "last_n_days", "value": days, "raw_text": f"最近 {days} 天"}

    match = re.search(r"最近\s*(\d+)\s*个?月", question)
    if not match:
        match = re.search(r"last\s*(\d+)\s*months?", question, flags=re.IGNORECASE)
    if match:
        months = int(match.group(1))
        return {"type": "last_n_months", "value": months, "raw_text": f"最近 {months} 个月"}

    if contains_any(question, ("本周", "这周", "this week")):
        return {"type": "this_week", "raw_text": "本周"}
    if contains_any(question, ("本月", "这个月", "this month")):
        return {"type": "this_month", "raw_text": "本月"}
    if contains_any(question, ("本季度", "这个季度", "this quarter")):
        return {"type": "this_quarter", "raw_text": "本季度"}
    return None


def build_clarification_questions(missing_slots: list[str]) -> list[str]:
    missing = set(missing_slots)
    if {"metric", "time_range"} <= missing:
        return ["请补充要分析的指标和时间范围，例如：最近90天看销售额。"]
    if {"dimension", "time_range"} <= missing:
        return ["请补充分析维度和时间范围，例如：最近90天按门店看销售额。"]
    if missing == {"metric", "dimension"}:
        return ["请补充要分析的指标和维度，例如：按门店看销售额。"]
    if "metric" in missing:
        return ["请补充要分析的指标，例如销售额、订单量、成本或满意度。"]
    if "dimension" in missing:
        return ["请补充分析维度，例如门店、渠道、产品、品类、城市或客户。"]
    if "time_range" in missing:
        return ["请补充时间范围，例如最近90天。"]
    return []


def strategy_for_task(task: dict[str, Any], *, risk_flags: list[str] | None = None) -> str:
    if risk_flags:
        return "reject"
    if task.get("missing_slots"):
        return "clarify"
    if task.get("task_type") == "rank" and task.get("dimensions") and task.get("metrics"):
        return "template"
    return "llm_candidate"


def legacy_metric_id(metric_label: str) -> str:
    compact = compact_text(metric_label)
    if compact in {"销售额", "收入", "营收", "成交额", "gmv", "sales", "salesamount", "revenue"}:
        return "gmv"
    if compact in {"订单量", "订单数", "订单数量", "ordercount"}:
        return "order_count"
    if compact in {"客单价", "aov", "平均订单金额"}:
        return "aov"
    if compact in {"复购率", "复购", "repurchaserate"}:
        return "repurchase_rate"
    if compact in {"销量", "销售量", "productsales"}:
        return "product_sales"
    return metric_label


def legacy_dimension_id(dimension_label: str) -> str:
    compact = compact_text(dimension_label)
    mapping = {
        "商品": "product",
        "产品": "product",
        "product": "product",
        "品类": "category",
        "类别": "category",
        "category": "category",
        "城市": "city",
        "city": "city",
        "用户": "user",
        "客户": "user",
        "user": "user",
        "渠道": "channel",
        "channel": "channel",
        "门店": "store",
        "店铺": "store",
        "storename": "store",
        "store": "store",
    }
    return mapping.get(compact, dimension_label)


def _normalize_task_type(value: Any, question: str) -> str:
    compact = compact_text(value)
    if contains_any(question, ("加预算", "减少预算", "优化", "建议", "推荐", "该", "should")):
        return "recommendation"
    if contains_any(question, ("异常", "异常门店", "波动", "anomaly")):
        return "anomaly"
    if contains_any(question, ("趋势", "走势", "变化", "trend")) or compact == "trend":
        return "trend"
    if contains_any(question, ("最高", "最低", "最多", "排名", "top", "rank")) or compact in {"topn", "rank"}:
        return "rank"
    if contains_any(question, ("对比", "比较", "compare", "comparison")) or compact in {"comparison", "compare"}:
        return "compare"
    if contains_any(question, ("报告", "report")):
        return "report"
    return "summary"


def _decision_goal(question: str, provider_goal: Any) -> str | None:
    goal = str(provider_goal or "").strip()
    if goal:
        return goal
    if contains_any(question, ("加预算", "增加预算")):
        return "判断哪个渠道该加预算"
    if contains_any(question, ("减少预算", "降预算")):
        return "判断哪里应减少预算"
    if contains_any(question, ("优化产品", "产品优化")):
        return "判断哪些产品需要优化"
    if contains_any(question, ("关注异常门店", "异常门店")):
        return "识别需要关注的异常门店"
    return None


def _missing_slots(
    *,
    task_type: str,
    metrics: list[str],
    dimensions: list[str],
    time_range: dict[str, Any] | None,
) -> list[str]:
    if task_type == "report":
        return []
    missing = []
    if not metrics:
        missing.append("metric")
    if task_type in {"compare", "rank", "trend", "anomaly", "recommendation", "summary"} and not dimensions:
        missing.append("dimension")
    if not time_range:
        missing.append("time_range")
    return missing


def _confidence(value: Any, missing_slots: list[str]) -> str:
    text = str(value or "").strip().lower()
    if text in ALLOWED_CONFIDENCE:
        return text
    return "medium" if missing_slots else "high"


def _semantic_matches(question: str, workspace_context: dict[str, Any] | None, *, key: str) -> list[str]:
    if not workspace_context:
        return []
    matched = []
    normalized_question = compact_text(question)
    for item in workspace_context.get(key, []) or []:
        if not isinstance(item, dict):
            continue
        candidates = [
            item.get("name", ""),
            item.get("label", ""),
            str(item.get("field", "")).split(".")[-1],
            *list(item.get("aliases") or []),
        ]
        if any(compact_text(candidate) and compact_text(candidate) in normalized_question for candidate in candidates):
            label = _chinese_label(item)
            if label:
                matched.append(label)
    return matched


def _chinese_label(item: dict[str, Any]) -> str:
    for candidate in [item.get("label"), *(item.get("aliases") or []), item.get("name"), item.get("field")]:
        text = str(candidate or "").strip()
        if text and _contains_cjk(text):
            return text
    return str(item.get("label") or item.get("name") or "").strip()


def _normalize_metric_values(value: Any) -> list[str]:
    return [_metric_label(item) for item in _normalize_string_list(value) if _metric_label(item)]


def _normalize_dimension_values(value: Any) -> list[str]:
    return [_dimension_label(item) for item in _normalize_string_list(value) if _dimension_label(item)]


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [part.strip() for part in re.split(r"[,，、/]", value) if part.strip()]
        return parts or ([value.strip()] if value.strip() else [])
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _question_metric_matches(question: str) -> list[str]:
    candidates = [
        (("销售额", "成交额", "收入", "营收", "gmv", "sales amount", "sales", "revenue"), "销售额"),
        (("花费", "费用", "成本", "投放成本", "spend", "cost"), "花费"),
        (("roi", "roas"), "ROI"),
        (("订单量", "订单数", "订单数量", "order count"), "订单量"),
        (("客单价", "平均订单金额", "aov"), "客单价"),
        (("复购率", "复购"), "复购率"),
        (("满意度", "评分", "nps", "score"), "满意度"),
        (("销量", "销售量"), "销量"),
    ]
    return [label for keywords, label in candidates if contains_any(question, keywords)]


def _question_dimension_matches(question: str) -> list[str]:
    candidates = [
        (("门店", "店铺", "store name", "store"), "门店"),
        (("渠道", "channel"), "渠道"),
        (("商品", "产品", "product"), "商品"),
        (("品类", "类别", "category"), "品类"),
        (("城市", "city"), "城市"),
        (("客户", "用户", "customer", "user"), "客户"),
    ]
    return [label for keywords, label in candidates if contains_any(question, keywords)]


def _metric_label(value: Any) -> str:
    compact = compact_text(value)
    mapping = {
        "gmv": "销售额",
        "sales": "销售额",
        "salesamount": "销售额",
        "revenue": "销售额",
        "收入": "销售额",
        "营收": "销售额",
        "成交额": "销售额",
        "销售额": "销售额",
        "cost": "花费",
        "spend": "花费",
        "花费": "花费",
        "费用": "花费",
        "成本": "花费",
        "投放成本": "花费",
        "ordercount": "订单量",
        "订单量": "订单量",
        "订单数": "订单量",
        "aov": "客单价",
        "客单价": "客单价",
        "repurchaserate": "复购率",
        "复购率": "复购率",
        "productsales": "销量",
        "销量": "销量",
        "roi": "ROI",
        "roas": "ROI",
        "scorenps": "满意度",
        "nps": "满意度",
    }
    return mapping.get(compact, str(value or "").strip())


def _dimension_label(value: Any) -> str:
    compact = compact_text(value)
    mapping = {
        "product": "商品",
        "商品": "商品",
        "产品": "商品",
        "category": "品类",
        "品类": "品类",
        "类别": "品类",
        "city": "城市",
        "城市": "城市",
        "user": "客户",
        "customer": "客户",
        "客户": "客户",
        "用户": "客户",
        "channel": "渠道",
        "渠道": "渠道",
        "store": "门店",
        "storename": "门店",
        "门店": "门店",
        "店铺": "门店",
    }
    return mapping.get(compact, str(value or "").strip())


def _normalize_time_range(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict) and value:
        normalized = dict(value)
        if normalized.get("type") == "last_n_days" and normalized.get("value"):
            normalized["raw_text"] = f"最近 {int(normalized['value'])} 天"
        if normalized.get("type") == "last_n_months" and normalized.get("value"):
            normalized["raw_text"] = f"最近 {int(normalized['value'])} 个月"
        return normalized
    return None


def _dedupe(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        key = compact_text(text)
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(text or ""))
