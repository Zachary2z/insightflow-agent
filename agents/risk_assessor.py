from __future__ import annotations

from typing import Any

from tools.trace_logger import append_trace


APPROVAL_REQUIRED_ACTIONS = {
    "create_task",
    "create_metric_alert",
    "create_email_draft",
    "export_large_result",
    "schedule_followup_run",
}


def _assess_action(action: dict[str, Any]) -> dict[str, Any]:
    action_type = str(action.get("action_type", ""))
    requires_approval = action_type in APPROVAL_REQUIRED_ACTIONS
    return {
        **action,
        "requires_approval": requires_approval,
        "risk_level": "medium" if requires_approval else "low",
        "risk_reason": "Action changes external operational state and requires approval." if requires_approval else "",
    }


def run_risk_assessor_agent(state: dict[str, Any]) -> dict[str, Any]:
    actions = state.get("action_plan", {}).get("actions", [])
    assessed_actions = [_assess_action(action) for action in actions]
    requires_approval = any(action["requires_approval"] for action in assessed_actions)
    risk_assessment = {
        "success": True,
        "requires_approval": requires_approval,
        "actions": assessed_actions,
    }
    updated = {
        **state,
        "risk_assessment": risk_assessment,
        "approval_status": "waiting_for_approval" if requires_approval else "not_required",
        "status": "waiting_for_approval" if requires_approval else "approval_not_required",
    }
    return append_trace(
        updated,
        {
            "node": "risk_assessor_agent",
            "tool_name": "",
            "tool_input_summary": f"{len(actions)} actions",
            "tool_output_summary": f"requires_approval={requires_approval}",
            "status": "success",
            "latency_ms": 0,
        },
    )


def run_action_executor_agent(state: dict[str, Any]) -> dict[str, Any]:
    from agents.action_executor import run_action_executor_agent as _run_action_executor_agent

    return _run_action_executor_agent(state)
