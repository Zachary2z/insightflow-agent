from __future__ import annotations

from typing import Any

from llm_ops.provider import LLMProvider
from question_understanding.clarification import clarify_with_provider
from tools.trace_logger import append_trace


def run_clarification_router_agent(state: dict[str, Any], provider: LLMProvider | None = None) -> dict[str, Any]:
    understanding = state.get("question_understanding", {})
    question = state.get("user_question", "")
    data_understanding = state.get("data_understanding") if isinstance(state.get("data_understanding"), dict) else {}
    precomputed = (
        data_understanding.get("clarification_result")
        if isinstance(data_understanding.get("clarification_result"), dict)
        else {}
    )

    if precomputed:
        result = dict(precomputed)
    elif understanding.get("strategy") != "clarify":
        result = {
            "success": True,
            "requires_clarification": False,
            "missing_slots": list(understanding.get("missing_slots", [])),
            "clarification_questions": list(understanding.get("clarification_questions", [])),
            "risk_flags": list(understanding.get("risk_flags", [])),
            "reason": "No clarification required.",
            "source": "deterministic",
            "provider_called": False,
            "fallback_used": False,
            "provider_error": "",
            "validation_error": "",
        }
    else:
        result = clarify_with_provider(question, understanding, provider=provider)

    updated = {
        **state,
        "clarification_result": result,
        "clarification_questions": result.get("clarification_questions", []),
    }
    provider_called = bool(result.get("provider_called", False))
    fallback_used = bool(result.get("fallback_used", False))
    return append_trace(
        updated,
        {
            "node": "clarification_router_agent",
            "tool_name": "provider_backed_clarification_router" if provider_called else "clarification_router",
            "tool_input_summary": question,
            "tool_output_summary": (
                f"requires_clarification={result.get('requires_clarification')} "
                f"missing={','.join(result.get('missing_slots', []))} "
                f"provider_called={provider_called} fallback_used={fallback_used}"
            ),
            "status": "success" if result.get("success") else "error",
            "latency_ms": 0,
            "error_type": None if result.get("success") else "clarification_router_error",
            "error": result.get("error") or result.get("provider_error") or result.get("validation_error") or None,
            "provider_called": provider_called,
            "fallback_used": fallback_used,
        },
    )
