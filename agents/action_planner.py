from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.action_drafter import run_action_drafter_agent
from llm_ops.provider import LLMProvider
from llm_ops.runtime_provider import build_action_drafter_provider
from tools.action_tool import DEFAULT_ACTION_DB_PATH
from tools.trace_logger import append_trace


def _primary_finding(state: dict[str, Any]) -> str:
    findings = state.get("evidence_result", {}).get("data_supported_findings", [])
    if findings:
        return str(findings[0].get("claim", "需要运营跟进的异常指标"))
    return "需要运营跟进的异常指标"


def run_action_planner_agent(
    state: dict[str, Any],
    action_db_path: str | Path | None = None,
    action_draft_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    provider = action_draft_provider or build_action_drafter_provider()
    action_plan = state.get("action_plan") or {
        "success": False,
        "plan_type": "business_action_plan",
        "actions": [],
        "source": "provider_unavailable",
        "source_finding": _primary_finding(state),
        "provider_called": provider is not None,
        "fallback_used": True,
        "provider_error": "llm_provider is not configured" if provider is None else "",
        "validation_error": "",
    }
    updated = {
        **state,
        "action_plan": action_plan,
        "action_db_path": action_db_path or state.get("action_db_path") or DEFAULT_ACTION_DB_PATH,
        "status": "action_plan_created" if action_plan.get("success") else "action_plan_provider_unavailable",
    }
    planned = append_trace(
        updated,
        {
            "node": "action_planner_agent",
            "tool_name": "",
            "tool_input_summary": state.get("user_question", ""),
            "tool_output_summary": (
                "provider action planning requested"
                if provider and not action_plan.get("actions")
                else f"{len(action_plan.get('actions', []))} actions planned"
            ),
            "status": "success" if provider or action_plan.get("success") else "error",
            "latency_ms": 0,
            "provider_called": bool(provider),
            "fallback_used": bool(action_plan.get("fallback_used", False)),
        },
    )
    return run_action_drafter_agent(planned, provider=provider)
