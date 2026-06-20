from __future__ import annotations

from typing import Any

from question_understanding.router import understand_question
from tools.trace_logger import append_trace


def run_question_understanding_agent(state: dict[str, Any]) -> dict[str, Any]:
    question = state.get("user_question", "")
    result = understand_question(question)
    updated = {
        **state,
        "question_understanding": result,
        "intent_slots": result.get("intent", {}),
        "routing_strategy": result.get("strategy", ""),
    }
    return append_trace(
        updated,
        {
            "node": "question_understanding_agent",
            "tool_name": "question_understanding_router",
            "tool_input_summary": question,
            "tool_output_summary": f"strategy={result.get('strategy')} missing={','.join(result.get('missing_slots', []))}",
            "status": "success" if result.get("success") else "error",
            "latency_ms": 0,
            "error_type": None if result.get("success") else "question_understanding_error",
            "error": result.get("error") or None,
        },
    )
