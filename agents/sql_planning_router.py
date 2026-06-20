from __future__ import annotations

from typing import Any

from llm_ops.provider import LLMProvider
from question_understanding.router import understand_question
from sql_planning.provider_backed import plan_sql_strategy_with_provider
from sql_planning.router import plan_sql_strategy
from tools.trace_logger import append_trace


def run_sql_planning_router_agent(state: dict[str, Any], provider: LLMProvider | None = None) -> dict[str, Any]:
    understanding = state.get("question_understanding") or understand_question(state.get("user_question", ""))
    if provider is None:
        planning = plan_sql_strategy(understanding)
        planning.update(
            {
                "source": "deterministic",
                "provider_called": False,
                "fallback_used": False,
                "provider_error": "",
                "validation_error": "",
            }
        )
    else:
        planning = plan_sql_strategy_with_provider(
            {**understanding, "question": state.get("user_question", "")},
            provider=provider,
        )
    updated = {
        **state,
        "question_understanding": understanding,
        "sql_planning": planning,
        "sql_routing_strategy": planning.get("strategy", ""),
        "matched_template": planning.get("matched_template", ""),
    }
    return append_trace(
        updated,
        {
            "node": "sql_planning_router_agent",
            "tool_name": "sql_planning_router",
            "tool_input_summary": state.get("user_question", ""),
            "tool_output_summary": (
                f"strategy={planning.get('strategy')} template={planning.get('matched_template', '')} "
                f"provider_called={planning.get('provider_called', False)} "
                f"fallback_used={planning.get('fallback_used', False)}"
            ),
            "status": "success" if planning.get("success") else "error",
            "latency_ms": 0,
            "error_type": None if planning.get("success") else "sql_planning_router_error",
            "error": planning.get("error") or None,
            "provider_called": bool(planning.get("provider_called", False)),
            "fallback_used": bool(planning.get("fallback_used", False)),
        },
    )
