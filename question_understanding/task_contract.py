from __future__ import annotations

import re
from typing import Any

from workspaces.time_range_defaults import full_range_default_note, resolve_time_default


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
    task_type = _normalize_task_type(provider_task.get("task_type") or intent.get("operation") or "", question)
    if time_range is None:
        time_range = extract_time_range(question)

    filters = _normalize_string_list(provider_task.get("filters"))
    if not filters:
        filters = _normalize_string_list(intent.get("filters"))
    decision_goal = _decision_goal(question, provider_task.get("decision_goal"))
    defaults_applied = _normalize_string_list(provider_task.get("defaults_applied"))
    time_field_candidates: list[dict[str, str]] = []
    specialized_missing_slots: list[str] = []
    resolved_question = str(provider_task.get("resolved_question") or question or "").strip()

    if time_range is None:
        default_decision = resolve_time_default(
            text=question,
            workspace_context=workspace_context,
            task_type=task_type,
        )
        if default_decision.get("action") == "apply":
            time_range = dict(default_decision.get("time_range") or {})
            default_note = str(default_decision.get("default_note") or "")
            if default_note:
                defaults_applied.append(default_note)
                resolved_question = _resolved_with_default_time(resolved_question or question, default_note)
        elif default_decision.get("action") == "clarify":
            missing_slot = str(default_decision.get("missing_slot") or "").strip()
            if missing_slot:
                specialized_missing_slots.append(missing_slot)
            time_field_candidates = [
                dict(item)
                for item in default_decision.get("candidates") or []
                if isinstance(item, dict)
            ]
    else:
        trend_decision = resolve_time_default(
            text=question,
            workspace_context=workspace_context,
            task_type=task_type,
        )
        if trend_decision.get("action") == "clarify" and trend_decision.get("missing_slot") == "time_grain":
            specialized_missing_slots.append("time_grain")

    missing_slots = _missing_slots(task_type=task_type, metrics=metrics, dimensions=dimensions, time_range=time_range)
    if specialized_missing_slots:
        missing_slots = [slot for slot in missing_slots if slot != "time_range"]
        missing_slots = _dedupe([*missing_slots, *specialized_missing_slots])
    confidence = _confidence(provider_task.get("confidence"), missing_slots)

    metrics = _order_metrics_for_calculation(metrics, _calculation_type(task_type, question))

    return {
        "task_type": task_type if task_type in ALLOWED_TASK_TYPES else "summary",
        "dimensions": dimensions,
        "metrics": metrics,
        "time_range": time_range,
        "filters": filters,
        "group_by": dimensions,
        "calculation_type": _calculation_type(task_type, question),
        "requires_time_field": bool(time_range),
        "requires_join": contains_any(question, ("跨表", "关联", "投放回报", "ROAS", "roi", "ROI")),
        "decision_goal": decision_goal,
        "missing_slots": missing_slots,
        "defaults_applied": _dedupe(defaults_applied),
        "time_field_candidates": time_field_candidates,
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


def build_clarification_questions(missing_slots: list[str], task: dict[str, Any] | None = None) -> list[str]:
    missing = set(missing_slots)
    task = task or {}
    if "date_field" in missing:
        candidates = [
            str(item.get("name") or item.get("field") or "").strip()
            for item in task.get("time_field_candidates") or []
            if isinstance(item, dict) and str(item.get("name") or item.get("field") or "").strip()
        ]
        if candidates:
            return [f"当前数据里有多个可能的时间字段（{ '、'.join(candidates) }），你希望按哪个时间字段分析？"]
        return ["当前数据里有多个可能的时间字段，你希望按哪个时间字段分析？"]
    if "time_grain" in missing:
        return ["你希望按天、周还是月查看趋势？是否使用完整数据范围？"]
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


def canonical_metric_id(metric_label: str) -> str:
    compact = compact_text(metric_label)
    if compact in {"roas"}:
        return "roas"
    if compact in {"roi"}:
        return "roi"
    if compact in {"netreturn", "netroi", "净投放回报率", "净回报率", "净投放回报"}:
        return "net_return"
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


def canonical_dimension_id(dimension_label: str) -> str:
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
    if compact in {"recommendation", "recommend", "advise", "priority", "prioritize"} or contains_any(
        question,
        ("加预算", "减少预算", "优化", "建议", "推荐", "应该", "优先", "最需要", "值得", "关注", "复盘", "should"),
    ):
        return "recommendation"
    if contains_any(question, ("异常", "异常门店", "波动", "anomaly")):
        return "anomaly"
    if contains_any(question, ("趋势", "走势", "变化", "trend")) or compact == "trend":
        return "trend"
    if contains_any(question, ("最高", "最低", "最多", "排名", "贡献最大", "top", "rank")) or compact in {"topn", "rank"}:
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
    if contains_any(question, ("优先处理", "最需要处理", "最需要优先", "最值得关注", "优先复盘")):
        return "判断哪个对象需要优先关注或处理"
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
    if task_type in {"compare", "rank", "anomaly", "recommendation", "summary"} and not dimensions:
        missing.append("dimension")
    if not time_range:
        missing.append("time_range")
    return missing


def _resolved_with_default_time(question: str, default_note: str) -> str:
    note = full_range_default_note({"type": "full_data_range", **_extract_start_end(default_note)})
    return f"{question}（{note or default_note}）"


def _extract_start_end(text: str) -> dict[str, str]:
    match = re.search(r"(\d{4}[-/]\d{1,2}(?:[-/]\d{1,2})?)\s*至\s*(\d{4}[-/]\d{1,2}(?:[-/]\d{1,2})?)", text)
    if not match:
        return {}
    return {"start": match.group(1), "end": match.group(2)}


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
    net_return_keywords = ("净投放回报率", "净回报率", "net return", "net_return", "net roi", "netroi")
    candidates = [
        (("roas",), "ROAS"),
        (("roi",), "ROI"),
        (("销售额", "成交额", "收入", "营收", "gmv", "sales amount", "sales", "revenue"), "销售额"),
        (("花费", "费用", "成本", "投放成本", "spend", "cost"), "花费"),
        (("订单量", "订单数", "订单数量", "order count"), "订单量"),
        (("客单价", "平均订单金额", "aov"), "客单价"),
        (("复购率", "复购"), "复购率"),
        (("响应效率", "响应时长", "平均响应", "response time", "response minutes"), "平均响应时长"),
        (("满意度", "评分", "nps", "score"), "满意度"),
        (("销量", "销售量"), "销量"),
    ]
    has_net_return = contains_any(question, net_return_keywords)
    matches = ["净投放回报率"] if has_net_return else []
    for keywords, label in candidates:
        if label == "ROI" and has_net_return and not _question_contains_plain_roi(question):
            continue
        if contains_any(question, keywords):
            matches.append(label)
    return matches


def _question_contains_plain_roi(question: str) -> bool:
    compact = compact_text(question)
    compact = compact.replace(compact_text("net roi"), "")
    return "roi" in compact


def _question_dimension_matches(question: str) -> list[str]:
    candidates = [
        (("门店", "店铺", "store name", "store"), "门店"),
        (("渠道", "channel"), "渠道"),
        (("商品", "产品", "product"), "商品"),
        (("品类", "类别", "category"), "品类"),
        (("城市", "city"), "城市"),
        (("客户", "用户", "customer", "user"), "客户"),
        (("客服团队", "团队", "team"), "团队"),
    ]
    return [label for keywords, label in candidates if contains_any(question, keywords)]


def _metric_label(value: Any) -> str:
    compact = compact_text(value)
    mapping = {
        "roas": "ROAS",
        "roi": "ROI",
        "netreturn": "净投放回报率",
        "netroi": "净投放回报率",
        "净投放回报率": "净投放回报率",
        "净回报率": "净投放回报率",
        "净投放回报": "净投放回报率",
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
        "响应效率": "平均响应时长",
        "响应时长": "平均响应时长",
        "平均响应时长": "平均响应时长",
        "avgresponseminutes": "平均响应时长",
        "productsales": "销量",
        "销量": "销量",
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
        "team": "团队",
        "团队": "团队",
        "客服团队": "团队",
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


def _calculation_type(task_type: str, question: str) -> str:
    if contains_any(question, ("贡献", "占比", "份额", "share", "contribution")):
        return "contribution"
    if contains_any(question, ("响应效率", "响应时长", "处理效率", "满意度", "客服运营")):
        return "operational_efficiency"
    if contains_any(question, ("roas", "roi", "投放回报", "投产比", "净投放回报")):
        return "investment_efficiency"
    if task_type == "rank":
        return "ranking"
    if task_type == "trend":
        return "trend"
    if task_type == "compare":
        return "comparison"
    return task_type or "summary"


def _order_metrics_for_calculation(metrics: list[str], calculation_type: str) -> list[str]:
    if calculation_type != "operational_efficiency":
        return metrics
    priority = {"平均响应时长": 0, "响应时长": 0, "满意度": 1, "工单数": 2, "工单量": 2}
    return sorted(metrics, key=lambda item: (priority.get(item, 99), metrics.index(item)))


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
