from __future__ import annotations

from typing import Any

from llm_ops.provider import LLMProvider
from question_understanding.clarification import clarify_with_provider
from question_understanding.business_lens import build_business_lens
from question_understanding.local_fast_fact_gate import (
    evaluate_local_fast_fact_gate,
    provider_false_unsafe_operation_is_relaxable,
    true_external_action_risk_flags,
)
from question_understanding.provider_backed import understand_question_with_provider
from question_understanding.resolved_question import build_resolved_question
from question_understanding.router import understand_question
from question_understanding.task_contract import SAFETY_RISK_FLAGS, build_clarification_questions, strategy_for_task
from workspaces.analysis_contracts import AnalysisTask


def understand_data_question(
    question: str,
    *,
    provider: LLMProvider | None = None,
    clarification_provider: LLMProvider | None = None,
    workspace_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    understanding = (
        understand_question_with_provider(question, provider=provider, workspace_context=workspace_context)
        if provider is not None
        else understand_question(question, workspace_context=workspace_context)
    )
    understanding = _normalize_workbench_understanding(question, understanding, workspace_context=workspace_context)
    clarification_result = _clarification_result(
        question=question,
        understanding=understanding,
        provider=clarification_provider,
    )
    task = _analysis_task_from_understanding(understanding, clarification_result=clarification_result)
    return {
        "success": bool(understanding.get("success", True)),
        "analysis_task": task,
        "analysis_task_dict": _task_dict_from_understanding(understanding),
        "question_understanding": understanding,
        "clarification_result": clarification_result,
        "resolved_question": task.resolved_question,
    }


def continue_data_question(
    *,
    original_question: str,
    clarification_answer: str,
    clarification_context: dict[str, Any] | None = None,
    provider: LLMProvider | None = None,
    clarification_provider: LLMProvider | None = None,
    workspace_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_question = build_resolved_question(
        original_question=original_question,
        clarification_answer=clarification_answer,
        clarification_context=clarification_context,
    )
    return understand_data_question(
        resolved_question,
        provider=provider,
        clarification_provider=clarification_provider,
        workspace_context=workspace_context,
    )


def _normalize_workbench_understanding(
    question: str,
    understanding: dict[str, Any],
    *,
    workspace_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = dict(understanding)
    task = dict(normalized.get("analysis_task") or {})
    business_lens = build_business_lens(
        question,
        analysis_task=task,
        workspace_context=workspace_context,
    )
    task["business_lens"] = business_lens.to_dict()
    if not task.get("time_range") and business_lens.time_range and not business_lens.needs_clarification:
        task["time_range"] = dict(business_lens.time_range)
    missing_slots = _workbench_missing_slots(task, question=question)
    if not business_lens.needs_clarification and business_lens.time_range:
        missing_slots = [slot for slot in missing_slots if slot not in {"date_field", "time_range"}]
    task["missing_slots"] = missing_slots
    normalized["analysis_task"] = task
    normalized["business_lens"] = business_lens.to_dict()
    normalized["missing_slots"] = missing_slots
    normalized["clarification_questions"] = build_clarification_questions(missing_slots, task=task)

    external_risk_flags = true_external_action_risk_flags(question)
    if external_risk_flags:
        _apply_external_action_rejection(normalized, task, external_risk_flags)
    else:
        gate = evaluate_local_fast_fact_gate(
            question,
            analysis_task=task,
            risk_flags=normalized.get("risk_flags") or [],
            workspace_context=workspace_context,
        )
        if gate.get("accepted"):
            _apply_local_fast_fact_candidate(normalized, task, gate)
        elif provider_false_unsafe_operation_is_relaxable(question, normalized.get("risk_flags") or []):
            _apply_relaxed_provider_unsafe_operation(normalized)
        elif normalized.get("strategy") == "reject" and not _has_safety_risk(normalized.get("risk_flags") or []):
            _apply_relaxed_business_boundary_risk(normalized)

    if normalized.get("strategy") != "reject":
        normalized["strategy"] = strategy_for_task(task, risk_flags=normalized.get("risk_flags") or [])
    if normalized["strategy"] == "clarify":
        normalized["reason"] = normalized.get("reason") or "问题缺少继续分析所需的关键信息。"
    elif not missing_slots:
        normalized["reason"] = normalized.get("reason") or "问题槽位完整，可以继续分析。"
    normalized["resolved_question"] = str(task.get("resolved_question") or question or "").strip()
    return normalized


def _apply_external_action_rejection(
    normalized: dict[str, Any],
    task: dict[str, Any],
    risk_flags: list[str],
) -> None:
    merged_flags = _unique_text([*[str(flag) for flag in normalized.get("risk_flags") or []], *risk_flags])
    intent = dict(normalized.get("intent") or {})
    intent["risk_flags"] = merged_flags
    normalized["intent"] = intent
    normalized["risk_flags"] = merged_flags
    normalized["strategy"] = "reject"
    normalized["rejection_reason"] = "Request asks the product to perform a real external action."
    normalized["reason"] = "真实外部动作请求在 SQL 生成前拒绝。"
    task["missing_slots"] = []
    normalized["missing_slots"] = []
    normalized["clarification_questions"] = []


def _apply_local_fast_fact_candidate(
    normalized: dict[str, Any],
    task: dict[str, Any],
    gate: dict[str, Any],
) -> None:
    task["missing_slots"] = []
    task["local_fast_fact_gate"] = {
        "decision": gate.get("decision", "fast_fact_candidate"),
        "reason": gate.get("reason", ""),
        "task_type": gate.get("task_type", ""),
        "metrics": list(gate.get("metrics") or []),
        "dimensions": list(gate.get("dimensions") or []),
    }
    normalized["analysis_task"] = task
    normalized["missing_slots"] = []
    normalized["clarification_questions"] = []
    normalized["local_fast_fact_gate"] = {
        **task["local_fast_fact_gate"],
        "overrode_risk_flags": list(gate.get("overrode_risk_flags") or []),
    }
    risk_flags = [str(flag) for flag in normalized.get("risk_flags") or [] if str(flag)]
    if risk_flags and set(risk_flags) <= {"unsafe_operation"}:
        intent = dict(normalized.get("intent") or {})
        intent["risk_flags"] = []
        normalized["intent"] = intent
        normalized["risk_flags"] = []
    normalized["strategy"] = ""
    normalized["rejection_reason"] = ""
    normalized["reason"] = "本地 Fast Fact Gate 确认为安全事实型问题。"


def _apply_relaxed_provider_unsafe_operation(normalized: dict[str, Any]) -> None:
    risk_flags = [str(flag) for flag in normalized.get("risk_flags") or [] if str(flag) != "unsafe_operation"]
    intent = dict(normalized.get("intent") or {})
    intent["risk_flags"] = [str(flag) for flag in intent.get("risk_flags") or [] if str(flag) != "unsafe_operation"]
    normalized["intent"] = intent
    normalized["risk_flags"] = risk_flags
    normalized["strategy"] = ""
    normalized["rejection_reason"] = ""
    normalized["reason"] = "本地安全检查确认这是分析建议问题，不执行真实外部动作。"


def _apply_relaxed_business_boundary_risk(normalized: dict[str, Any]) -> None:
    normalized["strategy"] = ""
    normalized["rejection_reason"] = ""
    normalized["reason"] = "本地安全检查确认风险标记不是外部动作、敏感访问、批量导出或写入删除操作。"


def _has_safety_risk(risk_flags: list[Any]) -> bool:
    return any(str(flag) in SAFETY_RISK_FLAGS for flag in risk_flags or [])


def _unique_text(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _workbench_missing_slots(task: dict[str, Any], *, question: str) -> list[str]:
    task_type = str(task.get("task_type") or "")
    missing = [str(slot) for slot in task.get("missing_slots") or [] if str(slot)]
    if (
        task_type == "summary"
        and task.get("metrics")
        and task.get("time_range")
        and _allows_summary_without_dimension(question)
    ):
        missing = [slot for slot in missing if slot != "dimension"]
    if task_type == "trend":
        missing = [slot for slot in missing if slot != "dimension"]
    return list(dict.fromkeys(missing))


def _allows_summary_without_dimension(question: str) -> bool:
    compact = "".join(str(question or "").lower().split())
    return any(marker in compact for marker in ("总", "多少", "合计", "汇总", "overall", "total"))


def _clarification_result(
    *,
    question: str,
    understanding: dict[str, Any],
    provider: LLMProvider | None,
) -> dict[str, Any]:
    if understanding.get("strategy") == "clarify":
        return clarify_with_provider(question, understanding, provider=provider)
    return {
        "success": True,
        "requires_clarification": False,
        "missing_slots": list(understanding.get("missing_slots") or []),
        "clarification_questions": list(understanding.get("clarification_questions") or []),
        "risk_flags": list(understanding.get("risk_flags") or []),
        "reason": "无需追问，可以继续分析。",
        "source": "deterministic",
        "provider_called": False,
        "fallback_used": False,
        "provider_error": "",
        "validation_error": "",
    }


def _analysis_task_from_understanding(
    understanding: dict[str, Any],
    *,
    clarification_result: dict[str, Any],
) -> AnalysisTask:
    raw_task = _task_dict_from_understanding(understanding)
    clarification_question = _first_text(clarification_result.get("clarification_questions")) or _first_text(
        understanding.get("clarification_questions")
    )
    route_hint = "clarify" if raw_task.get("missing_slots") else str(understanding.get("strategy") or "")
    return AnalysisTask(
        resolved_question=str(raw_task.get("resolved_question") or understanding.get("resolved_question") or ""),
        metrics=[str(item) for item in raw_task.get("metrics") or [] if str(item).strip()],
        dimensions=[str(item) for item in raw_task.get("dimensions") or [] if str(item).strip()],
        time_range=dict(raw_task.get("time_range") or {}),
        filters=[str(item) for item in raw_task.get("filters") or [] if str(item).strip()],
        decision_goal=str(raw_task.get("decision_goal") or ""),
        missing_slots=[str(item) for item in raw_task.get("missing_slots") or [] if str(item).strip()],
        clarification_question=clarification_question,
        route_hint=route_hint,
        business_lens=dict(raw_task.get("business_lens") or {}),
    )


def _task_dict_from_understanding(understanding: dict[str, Any]) -> dict[str, Any]:
    task = dict(understanding.get("analysis_task") or {})
    if task.get("time_range") is None:
        task["time_range"] = None
    return task


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            text = str(item or "").strip()
            if text:
                return text
    text = str(value or "").strip()
    return text


__all__ = ["continue_data_question", "understand_data_question"]
