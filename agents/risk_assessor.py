from __future__ import annotations

from typing import Any

from tools.action_tool import create_email_draft, create_metric_alert, create_task
from tools.audit_logger import log_audit_event
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


def _execute_action(db_path: str, state: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    action_type = action.get("action_type")
    payload = {**action, "run_id": state.get("run_id", "run_unknown")}
    if action_type == "create_task":
        return create_task(db_path, payload)
    if action_type == "create_metric_alert":
        return create_metric_alert(db_path, payload)
    if action_type == "create_email_draft":
        return create_email_draft(db_path, payload)
    return {
        "success": False,
        "action_type": action_type,
        "record_id": "",
        "error": f"Unsupported action_type: {action_type}",
    }


def run_action_executor_agent(state: dict[str, Any]) -> dict[str, Any]:
    db_path = str(state.get("action_db_path"))
    risk_assessment = state.get("risk_assessment", {})
    approval_status = state.get("approval_status", "")

    if risk_assessment.get("requires_approval") and approval_status != "approved":
        execution_result = {
            "success": False,
            "created_count": 0,
            "error": "approval required before action execution",
        }
        audit_result = log_audit_event(
            db_path,
            {
                "run_id": state.get("run_id", "run_unknown"),
                "event_type": "approval_blocked",
                "actor": "approval_gate",
                "payload": {
                    "approval_status": approval_status,
                    "actions": risk_assessment.get("actions", []),
                },
            },
        )
        updated = {
            **state,
            "created_actions": [],
            "action_execution_result": execution_result,
            "audit_log_result": audit_result,
            "audit_log_id": audit_result.get("audit_log_id", ""),
            "status": "waiting_for_approval",
        }
        return append_trace(
            updated,
            {
                "node": "approval_gate",
                "tool_name": "log_audit_event",
                "tool_input_summary": "approval required",
                "tool_output_summary": execution_result["error"],
                "status": "error",
                "latency_ms": 0,
                "error_type": "approval_required",
                "error": execution_result["error"],
            },
        )

    created_actions = []
    failed_actions = []
    for action in risk_assessment.get("actions", state.get("action_plan", {}).get("actions", [])):
        result = _execute_action(db_path, state, action)
        if result.get("success"):
            created_actions.append(
                {
                    "action_type": result.get("action_type") or action.get("action_type"),
                    "record_id": result.get("record_id"),
                    "source_action_id": action.get("action_id"),
                }
            )
        else:
            failed_actions.append({**action, "error": result.get("error", "action failed")})

    execution_result = {
        "success": not failed_actions,
        "created_count": len(created_actions),
        "failed_actions": failed_actions,
    }
    audit_result = log_audit_event(
        db_path,
        {
            "run_id": state.get("run_id", "run_unknown"),
            "event_type": "action_execution",
            "actor": "action_executor_agent",
            "payload": {
                "approval_status": approval_status,
                "created_actions": created_actions,
                "failed_actions": failed_actions,
            },
        },
    )
    updated = {
        **state,
        "created_actions": created_actions,
        "action_execution_result": execution_result,
        "audit_log_result": audit_result,
        "audit_log_id": audit_result.get("audit_log_id", ""),
        "status": "actions_executed" if execution_result["success"] else "action_execution_failed",
    }
    return append_trace(
        updated,
        {
            "node": "action_executor_agent",
            "tool_name": "create_task/create_metric_alert/create_email_draft",
            "tool_input_summary": f"{len(risk_assessment.get('actions', []))} actions",
            "tool_output_summary": f"{len(created_actions)} created",
            "status": "success" if execution_result["success"] else "error",
            "latency_ms": 0,
        },
    )
