from __future__ import annotations

from typing import Any

from tools.action_tool import verify_action_execution
from tools.audit_logger import log_audit_event
from tools.trace_logger import append_trace


def run_action_verifier_agent(state: dict[str, Any]) -> dict[str, Any]:
    db_path = state.get("action_db_path")
    created_actions = state.get("created_actions", [])
    verification_result = verify_action_execution(db_path, created_actions)
    audit_result = log_audit_event(
        db_path,
        {
            "run_id": state.get("run_id", "run_unknown"),
            "event_type": "action_verification",
            "actor": "action_verifier_agent",
            "payload": {
                "verified_actions": verification_result.get("verified_actions", []),
                "missing_actions": verification_result.get("missing_actions", []),
            },
        },
    )
    updated = {
        **state,
        "action_verification_result": verification_result,
        "audit_log_result": audit_result,
        "audit_log_id": audit_result.get("audit_log_id", ""),
        "status": "actions_verified" if verification_result.get("success") else "action_verification_failed",
    }
    return append_trace(
        updated,
        {
            "node": "action_verifier_agent",
            "tool_name": "verify_action_execution",
            "tool_input_summary": f"{len(created_actions)} actions",
            "tool_output_summary": (
                f"{len(verification_result.get('verified_actions', []))} verified, "
                f"{len(verification_result.get('missing_actions', []))} missing"
            ),
            "status": "success" if verification_result.get("success") else "error",
            "latency_ms": 0,
            "error_type": None if verification_result.get("success") else "action_verification_failed",
        },
    )
