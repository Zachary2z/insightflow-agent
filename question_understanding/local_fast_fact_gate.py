from __future__ import annotations

from typing import Any

from question_understanding.task_contract import canonical_dimension_id, canonical_metric_id, compact_text, contains_any


_FACT_TASK_TYPES = {"summary", "rank", "trend"}
_OVERRIDABLE_FALSE_RISK_FLAGS = {"unsafe_operation"}
_HARD_RISK_FLAGS = {"sensitive_field", "bulk_export", "external_action"}
_JUDGMENT_TERMS = (
    "为什么",
    "原因",
    "诊断",
    "建议",
    "推荐",
    "应该",
    "值得",
    "最值得",
    "优先",
    "复盘",
    "加预算",
    "减预算",
    "预算建议",
    "策略",
    "优化",
    "风险边界",
    "证据和风险",
    "tradeoff",
    "recommend",
    "should",
    "budget",
)
_REPORT_TERMS = ("报告", "管理层汇报", "复盘报告", "report")
_MULTI_METRIC_TERMS = ("综合", "权衡", "同时看", "tradeoff")
_TREND_GRAIN_TERMS = (
    "按天",
    "按日",
    "每天",
    "每日",
    "按周",
    "每周",
    "周趋势",
    "按月",
    "每月",
    "月趋势",
    "daily",
    "weekly",
    "monthly",
)
_UNSAFE_OPERATION_TERMS = ("删除", "更新", "写入", "插入", "drop", "delete", "update", "insert")
_ANALYSIS_ADVICE_TERMS = (
    "分析",
    "比较",
    "为什么",
    "原因",
    "诊断",
    "建议",
    "推荐",
    "应该",
    "值得",
    "复盘",
    "证据",
    "风险边界",
    "加预算",
    "减预算",
    "预算",
)


def true_external_action_risk_flags(question: str) -> list[str]:
    compact = compact_text(question)
    if not compact:
        return []
    external_markers = (
        "发送通知",
        "发通知",
        "发送消息",
        "发消息",
        "发送给",
        "发布",
        "推送",
        "创建工单",
        "新建工单",
        "提交工单",
        "写入系统",
        "同步到",
    )
    budget_action_markers = (
        "把预算调整",
        "将预算调整",
        "预算调整到",
        "调整预算到",
        "把预算调到",
        "将预算调到",
        "真正调整预算",
    )
    if any(compact_text(marker) in compact for marker in (*external_markers, *budget_action_markers)):
        return ["external_action"]
    return []


def provider_false_unsafe_operation_is_relaxable(question: str, risk_flags: list[str] | None) -> bool:
    flags = [str(flag) for flag in risk_flags or [] if str(flag)]
    if "unsafe_operation" not in flags:
        return False
    if any(flag in _HARD_RISK_FLAGS for flag in flags):
        return False
    if true_external_action_risk_flags(question):
        return False
    if contains_any(question, _UNSAFE_OPERATION_TERMS):
        return False
    return contains_any(question, _ANALYSIS_ADVICE_TERMS)


def evaluate_local_fast_fact_gate(
    question: str,
    *,
    analysis_task: dict[str, Any] | None,
    risk_flags: list[str] | None = None,
    workspace_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task = analysis_task or {}
    flags = [str(flag) for flag in risk_flags or [] if str(flag)]
    if true_external_action_risk_flags(question):
        return _blocked("external_action")
    if any(flag in _HARD_RISK_FLAGS for flag in flags):
        return _blocked("hard_risk")
    if flags and any(flag not in _OVERRIDABLE_FALSE_RISK_FLAGS for flag in flags):
        return _blocked("risk_flags")
    if _has_disqualifying_intent(question, task):
        return _blocked("judgment_or_report_intent")

    task_type = str(task.get("task_type") or "summary")
    if task_type not in _FACT_TASK_TYPES:
        return _blocked("unsupported_task_type")

    missing_slots = [str(slot) for slot in task.get("missing_slots") or [] if str(slot)]
    if missing_slots:
        return _blocked("missing_slots")

    metrics = _canonical_unique(task.get("metrics") or [], canonical_metric_id)
    dimensions = _canonical_unique(task.get("dimensions") or [], canonical_dimension_id)
    if len(metrics) != 1:
        return _blocked("metric_count")
    if task_type == "rank" and len(dimensions) != 1:
        return _blocked("rank_dimension_count")
    if task_type in {"summary", "trend"} and len(dimensions) > 1:
        return _blocked("dimension_count")
    if task_type == "trend" and not _trend_grain_is_clear(question, dimensions):
        return _blocked("trend_grain")
    if not task.get("time_range"):
        return _blocked("time_range")
    if not _workspace_supports_metric(metrics[0], workspace_context):
        return _blocked("metric_not_supported")
    if dimensions and not _workspace_supports_dimension(dimensions[0], question, workspace_context):
        return _blocked("dimension_not_supported")

    return {
        "accepted": True,
        "decision": "fast_fact_candidate",
        "reason": "本地规则确认这是低风险单指标事实问题。",
        "task_type": task_type,
        "metrics": metrics,
        "dimensions": dimensions,
        "overrode_risk_flags": [flag for flag in flags if flag in _OVERRIDABLE_FALSE_RISK_FLAGS],
    }


def _blocked(reason: str) -> dict[str, Any]:
    return {"accepted": False, "decision": "not_fast_fact", "reason": reason}


def _has_disqualifying_intent(question: str, task: dict[str, Any]) -> bool:
    if contains_any(question, _REPORT_TERMS) or str(task.get("task_type") or "") == "report":
        return True
    if contains_any(question, _JUDGMENT_TERMS) or task.get("decision_goal"):
        return True
    if contains_any(question, _MULTI_METRIC_TERMS):
        return True
    return len(_canonical_unique(task.get("metrics") or [], canonical_metric_id)) > 1


def _trend_grain_is_clear(question: str, dimensions: list[str]) -> bool:
    if contains_any(question, _TREND_GRAIN_TERMS):
        return True
    return any(compact_text(dimension) in {"日期", "时间", "date", "time", "week", "month"} for dimension in dimensions)


def _canonical_unique(values: list[Any], canonicalizer) -> list[str]:
    result: list[str] = []
    seen = set()
    for value in values:
        label = str(canonicalizer(str(value or "")) or "").strip()
        key = compact_text(label)
        if label and key not in seen:
            seen.add(key)
            result.append(label)
    return result


def _workspace_supports_metric(metric: str, workspace_context: dict[str, Any] | None) -> bool:
    if not workspace_context or not workspace_context.get("workspace_data_source_selected"):
        return True
    metric_key = compact_text(metric)
    for item in workspace_context.get("semantic_metrics") or []:
        if not isinstance(item, dict):
            continue
        candidates = _semantic_candidates(item)
        if any(metric_key and metric_key in candidate for candidate in candidates):
            return True
        canonical = canonical_metric_id(metric)
        if canonical == "gmv" and _looks_like_amount_metric(item, candidates):
            return True
        if canonical == "order_count" and any("count" in candidate or "数量" in candidate for candidate in candidates):
            return True
    return False


def _workspace_supports_dimension(
    dimension: str,
    question: str,
    workspace_context: dict[str, Any] | None,
) -> bool:
    if not workspace_context or not workspace_context.get("workspace_data_source_selected"):
        return True
    dimension_key = compact_text(dimension)
    canonical = canonical_dimension_id(dimension)
    tokens = {
        "channel": ("channel", "渠道"),
        "store": ("store", "shop", "门店", "店铺"),
        "user": ("customer", "user", "segment", "客户", "用户", "分群"),
        "product": ("product", "商品", "产品"),
        "category": ("category", "品类", "类别"),
        "city": ("city", "城市"),
        "team": ("team", "团队"),
    }.get(canonical, (dimension_key,))
    question_key = compact_text(question)
    for item in workspace_context.get("semantic_dimensions") or []:
        if not isinstance(item, dict):
            continue
        candidates = _semantic_candidates(item)
        if any(dimension_key and dimension_key in candidate for candidate in candidates):
            return True
        if any(compact_text(token) in candidate for token in tokens for candidate in candidates):
            return True
        if "分群" in question_key and any("segment" in candidate for candidate in candidates):
            return True
    return False


def _semantic_candidates(item: dict[str, Any]) -> list[str]:
    values = [
        item.get("name", ""),
        item.get("label", ""),
        item.get("field", ""),
        item.get("table", ""),
        *list(item.get("aliases") or []),
        *list(item.get("business_meaning_candidates") or []),
    ]
    return [compact_text(value) for value in values if compact_text(value)]


def _looks_like_amount_metric(item: dict[str, Any], candidates: list[str]) -> bool:
    meanings = [compact_text(value) for value in item.get("business_meaning_candidates") or []]
    if any(value in {"revenuelike", "amountlike"} for value in meanings):
        return True
    return any(token in candidate for candidate in candidates for token in ("sales", "revenue", "amount", "gmv", "收入", "销售额"))


__all__ = ["evaluate_local_fast_fact_gate", "true_external_action_risk_flags"]
