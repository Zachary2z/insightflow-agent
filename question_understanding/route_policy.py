from __future__ import annotations

from typing import Any, Literal, TypedDict

from question_understanding.task_contract import compact_text, contains_any


AnalysisRouteName = Literal["clarify", "fast_fact", "standard_analysis", "deep_judgment", "report"]


class AnalysisRoute(TypedDict):
    route: AnalysisRouteName
    reason: str
    confidence: str
    requires_full_chain: bool
    fast_path_eligible: bool
    disqualifiers: list[str]


_REPORT_TERMS = ("报告", "管理层汇报", "管理层报告", "复盘报告", "report")
_JUDGMENT_TERMS = (
    "为什么",
    "原因",
    "诊断",
    "应该",
    "建议",
    "推荐",
    "优先级",
    "优先",
    "复盘",
    "值得",
    "加预算",
    "减预算",
    "减少预算",
    "投放策略",
    "综合",
    "should",
    "recommend",
    "priority",
    "budget",
)
_FACT_TASK_TYPES = {"rank", "summary", "trend"}


def classify_analysis_route(
    question: str,
    *,
    analysis_task: dict[str, Any] | None = None,
    missing_slots: list[str] | None = None,
    risk_flags: list[str] | None = None,
) -> AnalysisRoute:
    task = analysis_task or {}
    task_type = str(task.get("task_type") or "summary")
    task_missing = list(missing_slots if missing_slots is not None else task.get("missing_slots") or [])
    blocking_missing = _blocking_missing(task_type, task_missing, task=task)
    disqualifiers = _disqualifiers(question, task=task, blocking_missing=blocking_missing, risk_flags=risk_flags)
    confidence = _route_confidence(task, blocking_missing=blocking_missing, disqualifiers=disqualifiers)

    if task_type == "report" or contains_any(question, _REPORT_TERMS):
        return _route(
            "report",
            reason="识别为报告或管理层汇报请求，需要完整报告/分析链路。",
            confidence=confidence,
            disqualifiers=["report_intent", *[item for item in disqualifiers if item != "report_intent"]],
        )

    if _is_deep_judgment(question, task=task, disqualifiers=disqualifiers):
        return _route(
            "deep_judgment",
            reason="问题包含建议、原因、预算、复盘或综合权衡意图，需要完整判断链路。",
            confidence=confidence,
            disqualifiers=disqualifiers or ["judgment_intent"],
        )

    if blocking_missing:
        return _route(
            "clarify",
            reason="缺少继续分析所需的关键槽位，需要先追问。",
            confidence="medium" if confidence == "high" else confidence,
            disqualifiers=["missing_slots", *disqualifiers],
        )

    if _is_fast_fact_candidate(task_type, task, disqualifiers):
        return {
            "route": "fast_fact",
            "reason": "低风险事实型问题，可生成快速事实元数据；H1 仍沿用完整分析链路。",
            "confidence": confidence,
            "requires_full_chain": False,
            "fast_path_eligible": True,
            "disqualifiers": [],
        }

    return _route(
        "standard_analysis",
        reason="问题需要常规分析链路产出业务发现和图表支持。",
        confidence=confidence,
        disqualifiers=disqualifiers,
    )


def _route(
    route: AnalysisRouteName,
    *,
    reason: str,
    confidence: str,
    disqualifiers: list[str] | None = None,
) -> AnalysisRoute:
    return {
        "route": route,
        "reason": reason,
        "confidence": confidence,
        "requires_full_chain": True,
        "fast_path_eligible": False,
        "disqualifiers": list(dict.fromkeys(disqualifiers or [])),
    }


def _blocking_missing(task_type: str, missing_slots: list[str], *, task: dict[str, Any]) -> list[str]:
    missing = [str(slot) for slot in missing_slots if str(slot)]
    if task_type == "trend":
        missing = [slot for slot in missing if slot != "dimension"]
    if task_type == "summary" and task.get("metrics") and task.get("time_range"):
        missing = [slot for slot in missing if slot != "dimension"]
    return missing


def _disqualifiers(
    question: str,
    *,
    task: dict[str, Any],
    blocking_missing: list[str],
    risk_flags: list[str] | None,
) -> list[str]:
    disqualifiers: list[str] = []
    if blocking_missing:
        disqualifiers.append("missing_slots")
    if risk_flags:
        disqualifiers.append("risk_flags")
    if contains_any(question, _REPORT_TERMS) or task.get("task_type") == "report":
        disqualifiers.append("report_intent")
    if contains_any(question, _JUDGMENT_TERMS) or task.get("decision_goal"):
        disqualifiers.append("judgment_intent")
    if len(_route_metrics(task)) > 1 or contains_any(question, ("综合", "权衡", "tradeoff")):
        disqualifiers.append("multi_metric")
    return list(dict.fromkeys(disqualifiers))


def _is_deep_judgment(question: str, *, task: dict[str, Any], disqualifiers: list[str]) -> bool:
    if task.get("task_type") == "recommendation" or task.get("decision_goal"):
        return True
    if "judgment_intent" in disqualifiers:
        return True
    if "multi_metric" in disqualifiers and contains_any(question, ("最好", "最值得", "应该", "建议", "推荐", "综合")):
        return True
    return False


def _is_fast_fact_candidate(task_type: str, task: dict[str, Any], disqualifiers: list[str]) -> bool:
    if disqualifiers:
        return False
    if task_type not in _FACT_TASK_TYPES:
        return False
    if len(_route_metrics(task)) != 1:
        return False
    dimensions = task.get("dimensions") or []
    if task_type == "rank" and len(dimensions) != 1:
        return False
    if task_type == "summary" and len(dimensions) > 1:
        return False
    if task_type == "trend" and len(dimensions) > 1:
        return False
    return bool(task.get("time_range"))


def _route_metrics(task: dict[str, Any]) -> list[str]:
    metrics = []
    seen = set()
    for metric in task.get("metrics") or []:
        label = _canonical_metric(metric)
        if label and label not in seen:
            seen.add(label)
            metrics.append(label)
    return metrics


def _canonical_metric(metric: Any) -> str:
    compact = compact_text(metric)
    if compact in {"数量", "次数", "单量", "件数", "订单数", "订单量", "ordercount", "sumordercount"}:
        return "订单量"
    if compact in {
        "收入",
        "营收",
        "销售额",
        "成交额",
        "gmv",
        "sales",
        "salesamount",
        "sumsalesamount",
        "totalsales",
        "totalrevenue",
        "sumrevenue",
    }:
        return "销售额"
    return compact


def _route_confidence(
    task: dict[str, Any],
    *,
    blocking_missing: list[str],
    disqualifiers: list[str],
) -> str:
    confidence = str(task.get("confidence") or "medium").lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"
    if blocking_missing and confidence == "high":
        confidence = "medium"
    if "risk_flags" in disqualifiers:
        confidence = "low"
    if compact_text(task.get("task_type")) == "report":
        confidence = "high" if confidence != "low" else confidence
    return confidence
