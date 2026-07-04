from __future__ import annotations

from typing import Any

from llm_ops.provider import LLMProvider
from question_understanding.route_policy import classify_analysis_route
from workspaces.analysis_contracts import AnalysisTask, CoordinatorDecision
from workspaces.data_understanding_agent import understand_data_question


_SAFETY_RISK_FLAGS = {"unsafe_operation", "sensitive_field", "bulk_export"}


def coordinate_analysis_question(
    question: str,
    *,
    provider: LLMProvider | None = None,
    clarification_provider: LLMProvider | None = None,
    workspace_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data_understanding = understand_data_question(
        question,
        provider=provider,
        clarification_provider=clarification_provider,
        workspace_context=workspace_context,
    )
    task = data_understanding["analysis_task"]
    understanding = data_understanding["question_understanding"]
    legacy_route = classify_analysis_route(
        question,
        analysis_task=data_understanding["analysis_task_dict"],
        missing_slots=understanding.get("missing_slots") or [],
        risk_flags=understanding.get("risk_flags") or [],
    )
    decision = coordinate_analysis(
        question,
        task,
        understanding=understanding,
        legacy_route=legacy_route,
    )
    task.route_hint = decision.route
    return {
        **data_understanding,
        "analysis_task": task,
        "coordinator_decision": decision,
        "analysis_route": legacy_route,
    }


def coordinate_analysis(
    question: str,
    task: AnalysisTask,
    *,
    understanding: dict[str, Any] | None = None,
    legacy_route: dict[str, Any] | None = None,
) -> CoordinatorDecision:
    understanding = understanding or {}
    legacy_route = legacy_route or {}
    if understanding.get("strategy") == "reject" or _has_safety_risk(understanding.get("risk_flags")):
        return CoordinatorDecision(
            route="reject",
            required_agents=["数据理解"],
            reason=_reject_reason(understanding),
            user_language="zh",
        )
    if task.missing_slots:
        return CoordinatorDecision(
            route="clarify",
            required_agents=["数据理解"],
            reason=f"问题缺少关键槽位（{ '、'.join(task.missing_slots) }），需要先追问。",
            user_language="zh",
        )

    route = str(legacy_route.get("route") or "standard_analysis")
    if route == "report":
        route = "deep_judgment"
    if route not in {"fast_fact", "standard_analysis", "deep_judgment"}:
        route = "standard_analysis"

    if route == "fast_fact":
        return CoordinatorDecision(
            route="fast_fact",
            required_agents=["数据理解", "证据查询", "证据审计", "业务回答"],
            reason="问题槽位完整且属于低风险事实型分析，可走轻量事实链路。",
            user_language="zh",
        )
    if route == "deep_judgment":
        return CoordinatorDecision(
            route="deep_judgment",
            required_agents=["数据理解", "证据查询", "证据审计", "业务回答"],
            reason="问题包含原因、建议、复盘或综合权衡，需要完整证据和业务判断。",
            user_language="zh",
        )
    return CoordinatorDecision(
        route="standard_analysis",
        required_agents=["数据理解", "证据查询", "证据审计", "业务回答"],
        reason="问题槽位完整，需要常规分析链路生成业务答案。",
        user_language="zh",
    )


def _reject_reason(understanding: dict[str, Any]) -> str:
    reason = str(understanding.get("rejection_reason") or "").strip()
    if reason:
        return f"请求涉及敏感字段或不安全操作，已拒绝：{reason}"
    return "请求不适合在分析工作台继续执行，已拒绝。"


def _has_safety_risk(risk_flags: Any) -> bool:
    return any(str(flag) in _SAFETY_RISK_FLAGS for flag in risk_flags or [])


__all__ = ["coordinate_analysis", "coordinate_analysis_question"]
