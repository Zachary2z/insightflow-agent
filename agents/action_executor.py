from __future__ import annotations

from typing import Any

from action_delivery.adapters import execute_action_delivery
from tools.audit_logger import log_audit_event
from tools.trace_logger import append_trace


def run_action_executor_agent(state: dict[str, Any]) -> dict[str, Any]:
    db_path = str(state.get("action_db_path"))
    risk_assessment = state.get("risk_assessment", {})
    approval_status = state.get("approval_status", "")

    if risk_assessment.get("requires_approval") and approval_status != "approved":
        execution_result = {
            "success": False,
            "created_count": 0,
            "external_tool_called": False,
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
    delivery_results = []
    for action in risk_assessment.get("actions", state.get("action_plan", {}).get("actions", [])):
        result = execute_action_delivery(db_path=db_path, state=state, action=action)
        delivery_results.append(result)
        if result.get("success"):
            created_actions.append(
                {
                    "action_type": result.get("action_type") or action.get("action_type"),
                    "delivery_tool_id": result.get("delivery_tool_id", action.get("delivery_tool_id", "local_sqlite")),
                    "tool_type": result.get("tool_type", ""),
                    "record_id": result.get("record_id"),
                    "artifact_url": result.get("artifact_url", ""),
                    "external_tool_called": bool(result.get("external_tool_called", False)),
                    "source_action_id": action.get("action_id"),
                }
            )
        else:
            failed_actions.append({**action, "error": result.get("error", "action failed")})

    execution_result = {
        "success": not failed_actions,
        "created_count": len(created_actions),
        "failed_actions": failed_actions,
        "delivery_results": delivery_results,
        "external_tool_called": any(result.get("external_tool_called") for result in delivery_results),
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
            "tool_name": "action_delivery_adapter",
            "tool_input_summary": f"{len(risk_assessment.get('actions', []))} actions",
            "tool_output_summary": f"{len(created_actions)} created",
            "status": "success" if execution_result["success"] else "error",
            "latency_ms": 0,
            "external_tool_called": bool(execution_result["external_tool_called"]),
        },
    )
