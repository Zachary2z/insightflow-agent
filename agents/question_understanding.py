from __future__ import annotations

from typing import Any

from llm_ops.provider import LLMProvider
from question_understanding.provider_backed import understand_question_with_provider
from question_understanding.route_policy import classify_analysis_route
from question_understanding.router import understand_question
from tools.trace_logger import append_trace
from workspaces.context_summary import build_workspace_context_summary


def run_question_understanding_agent(state: dict[str, Any], provider: LLMProvider | None = None) -> dict[str, Any]:
    question = state.get("user_question", "")
    workspace_context = state.get("workspace_context") or build_workspace_context_summary(
        profile_path=state.get("profile_path"),
        semantic_layer_path=state.get("semantic_layer_path"),
    )
    result = (
        understand_question_with_provider(question, provider=provider, workspace_context=workspace_context)
        if provider is not None
        else understand_question(question, workspace_context=workspace_context)
    )
    analysis_route = classify_analysis_route(
        question,
        analysis_task=result.get("analysis_task") or {},
        missing_slots=result.get("missing_slots") or [],
        risk_flags=result.get("risk_flags") or [],
    )
    result = {**result, "analysis_route": analysis_route}
    updated = {
        **state,
        "workspace_context": workspace_context,
        "question_understanding": result,
        "analysis_task": result.get("analysis_task", {}),
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
                f"route={analysis_route.get('route')} "
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
