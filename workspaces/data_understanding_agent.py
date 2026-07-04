from __future__ import annotations

from typing import Any

from llm_ops.provider import LLMProvider
from question_understanding.clarification import clarify_with_provider
from question_understanding.provider_backed import understand_question_with_provider
from question_understanding.resolved_question import build_resolved_question
from question_understanding.router import understand_question
from question_understanding.task_contract import build_clarification_questions, strategy_for_task
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
    understanding = _normalize_workbench_understanding(question, understanding)
    clarification_result = _clarification_result(
        question=question,
        understanding=understanding,
        provider=clarification_provider,
    )
    task = _analysis_task_from_understanding(understanding, clarification_result=clarification_result)
    return {
        "success": bool(understanding.get("success", True)),
        "analysis_task": task,
        "analysis_task_dict": _legacy_task_dict(understanding),
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


def _normalize_workbench_understanding(question: str, understanding: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(understanding)
    task = dict(normalized.get("analysis_task") or {})
    missing_slots = _workbench_missing_slots(task, question=question)
    task["missing_slots"] = missing_slots
    normalized["analysis_task"] = task
    normalized["missing_slots"] = missing_slots
    normalized["clarification_questions"] = build_clarification_questions(missing_slots, task=task)

    if normalized.get("strategy") != "reject":
        normalized["strategy"] = strategy_for_task(task, risk_flags=normalized.get("risk_flags") or [])
    if normalized["strategy"] == "clarify":
        normalized["reason"] = normalized.get("reason") or "问题缺少继续分析所需的关键信息。"
    elif not missing_slots:
        normalized["reason"] = normalized.get("reason") or "问题槽位完整，可以继续分析。"
    normalized["resolved_question"] = str(task.get("resolved_question") or question or "").strip()
    return normalized


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
    raw_task = _legacy_task_dict(understanding)
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
    )


def _legacy_task_dict(understanding: dict[str, Any]) -> dict[str, Any]:
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
