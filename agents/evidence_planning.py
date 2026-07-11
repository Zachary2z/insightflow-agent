from __future__ import annotations

from typing import Any

from agents.analysis_planner import plan_analysis
from llm_ops.provider import LLMProvider
from question_understanding.router import understand_question
from sql_planning.provider_backed import plan_sql_strategy_with_provider
from sql_planning.router import plan_sql_strategy
from tools.trace_logger import append_trace


def run_evidence_planning_agent(state: dict[str, Any], provider: LLMProvider | None = None) -> dict[str, Any]:
    understanding = state.get("question_understanding") or understand_question(state.get("user_question", ""))
    question = str(state.get("user_question") or "")
    if provider is None:
        sql_planning = plan_sql_strategy(understanding)
        sql_planning.update(
            {
                "source": "deterministic",
                "provider_called": False,
                "fallback_used": False,
                "provider_error": "",
                "validation_error": "",
            }
        )
    else:
        sql_planning = plan_sql_strategy_with_provider({**understanding, "question": question}, provider=provider)

    analysis_plan = plan_analysis(question)
    evidence_planning = _build_evidence_planning(
        state,
        understanding=understanding,
        sql_planning=sql_planning,
        analysis_plan=analysis_plan,
    )
    updated = {
        **state,
        "question_understanding": understanding,
        "evidence_planning": evidence_planning,
        "sql_planning": sql_planning,
        "sql_routing_strategy": sql_planning.get("strategy", ""),
        "matched_template": sql_planning.get("matched_template", ""),
        "analysis_plan": analysis_plan,
        "scenario_type": analysis_plan.get("scenario_type", ""),
        "analysis_steps": analysis_plan.get("analysis_steps", []),
    }
    return append_trace(
        updated,
        {
            "node": "evidence_planning_agent",
            "tool_name": "evidence_planning",
            "tool_input_summary": question,
            "tool_output_summary": (
                f"strategy={evidence_planning.get('query_strategy')} "
                f"scenario={evidence_planning.get('scenario_type')} "
                f"provider_called={evidence_planning.get('provider_called', False)} "
                f"fallback_used={evidence_planning.get('fallback_used', False)}"
            ),
            "status": "success" if evidence_planning.get("success") else "error",
            "latency_ms": 0,
            "error_type": None if evidence_planning.get("success") else "evidence_planning_error",
            "error": evidence_planning.get("error") or None,
            "provider_called": bool(evidence_planning.get("provider_called", False)),
            "fallback_used": bool(evidence_planning.get("fallback_used", False)),
            "prompt_id": evidence_planning.get("prompt_id", ""),
        },
    )


def _build_evidence_planning(
    state: dict[str, Any],
    *,
    understanding: dict[str, Any],
    sql_planning: dict[str, Any],
    analysis_plan: dict[str, Any],
) -> dict[str, Any]:
    task = _task(state, understanding)
    provider_called = bool(sql_planning.get("provider_called", False))
    fallback_used = bool(sql_planning.get("fallback_used", False))
    missing_evidence = _unique_text(
        [
            *[str(slot) for slot in sql_planning.get("missing_slots") or []],
            *[str(item) for item in sql_planning.get("risk_flags") or []],
            *[str(item) for item in task.get("missing_slots") or []],
        ]
    )
    return {
        "success": bool(sql_planning.get("success", True) and analysis_plan.get("success", True)),
        "source": sql_planning.get("source", "deterministic"),
        "provider_called": provider_called,
        "fallback_used": fallback_used,
        "provider_error": str(sql_planning.get("provider_error") or analysis_plan.get("provider_error") or ""),
        "validation_error": str(sql_planning.get("validation_error") or analysis_plan.get("validation_error") or ""),
        "prompt_id": str(sql_planning.get("prompt_id") or ""),
        "task_type": str(task.get("task_type") or ""),
        "metrics": _str_list(task.get("metrics")),
        "dimensions": _str_list(task.get("dimensions")),
        "time_range": dict(task.get("time_range") or {}),
        "filters": _str_list(task.get("filters")),
        "comparison_scope": _comparison_scope(task, understanding),
        "query_strategy": str(sql_planning.get("strategy") or ""),
        "chart_intent": _chart_intent(state, task),
        "missing_evidence": missing_evidence,
        "data_limits": missing_evidence,
        "scenario_type": str(analysis_plan.get("scenario_type") or ""),
        "analysis_steps": list(analysis_plan.get("analysis_steps") or []),
        "sql_planning": sql_planning,
    }


def _task(state: dict[str, Any], understanding: dict[str, Any]) -> dict[str, Any]:
    for key in ("analysis_task", "analysis_task_contract"):
        value = state.get(key)
        if isinstance(value, dict) and value:
            return dict(value)
    task = understanding.get("analysis_task") if isinstance(understanding.get("analysis_task"), dict) else {}
    return dict(task)


def _comparison_scope(task: dict[str, Any], understanding: dict[str, Any]) -> dict[str, Any]:
    task_type = str(task.get("task_type") or "")
    intent = understanding.get("intent") if isinstance(understanding.get("intent"), dict) else {}
    operation = str(intent.get("operation") or task.get("calculation_type") or "")
    if task_type in {"rank", "trend"} or operation in {"top_n", "comparison", "recommendation"}:
        return {"type": "peer_comparison", "required": True}
    return {"type": "single_metric", "required": False}


def _chart_intent(state: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    question = str(state.get("user_question") or state.get("original_question") or "")
    explicit = any(marker in question for marker in ("图表", "画图", "作图", "可视化", "趋势图", "柱状图", "折线图"))
    task_type = str(task.get("task_type") or "")
    if explicit:
        return {"requested": True, "kind": "explicit"}
    if task_type == "trend":
        return {"requested": False, "kind": "trend_candidate"}
    if task_type == "rank" and task.get("dimensions"):
        return {"requested": False, "kind": "comparison_candidate"}
    return {"requested": False, "kind": ""}


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _unique_text(items: list[str]) -> list[str]:
    ordered: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in ordered:
            ordered.append(text)
    return ordered


__all__ = ["run_evidence_planning_agent"]
