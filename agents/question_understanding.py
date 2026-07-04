from __future__ import annotations

from typing import Any

from llm_ops.provider import LLMProvider
from tools.trace_logger import append_trace
from workspaces.analysis_coordinator import coordinate_analysis_question
from workspaces.context_summary import build_workspace_context_summary


def run_question_understanding_agent(
    state: dict[str, Any],
    provider: LLMProvider | None = None,
    clarification_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    question = state.get("user_question", "")
    workspace_context = state.get("workspace_context") or build_workspace_context_summary(
        profile_path=state.get("profile_path"),
        semantic_layer_path=state.get("semantic_layer_path"),
    )
    coordination = coordinate_analysis_question(
        question,
        provider=provider,
        clarification_provider=clarification_provider,
        workspace_context=workspace_context,
    )
    result = coordination["question_understanding"]
    analysis_route = coordination["analysis_route"]
    analysis_task = coordination["analysis_task"]
    coordinator_decision = coordination["coordinator_decision"]
    result = {**result, "analysis_route": analysis_route}
    updated = {
        **state,
        "workspace_context": workspace_context,
        "data_understanding": {
            "analysis_task": analysis_task.to_dict(),
            "clarification_result": coordination.get("clarification_result") or {},
            "resolved_question": analysis_task.resolved_question,
        },
        "coordinator_decision": coordinator_decision.to_dict(),
        "analysis_task_contract": analysis_task.to_dict(),
        "question_understanding": result,
        "analysis_task": coordination.get("analysis_task_dict") or result.get("analysis_task", {}),
        "analysis_route": analysis_route,
        "intent_slots": result.get("intent", {}),
        "routing_strategy": result.get("strategy", ""),
    }
    provider_called = bool(result.get("provider_called", False))
    fallback_used = bool(result.get("fallback_used", False))
    return append_trace(
        updated,
        {
            "node": "question_understanding_agent",
            "tool_name": "provider_backed_question_understanding" if provider_called else "question_understanding_router",
            "tool_input_summary": question,
            "tool_output_summary": (
                f"strategy={result.get('strategy')} missing={','.join(result.get('missing_slots', []))} "
                f"route={analysis_route.get('route')} coordinator={coordinator_decision.route} "
                f"provider_called={provider_called} fallback_used={fallback_used}"
            ),
            "status": "success" if result.get("success") else "error",
            "latency_ms": 0,
            "error_type": None if result.get("success") else "question_understanding_error",
            "error": result.get("error") or None,
            "provider_called": provider_called,
            "fallback_used": fallback_used,
        },
    )
