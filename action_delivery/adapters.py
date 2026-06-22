from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter
from typing import Any

from action_delivery.policy import validate_action_delivery_tool
from tools.action_tool import create_email_draft, create_metric_alert, create_task


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return slug.strip("_") or "action"


def _failure(action: dict[str, Any], delivery_tool_id: str, error: str, started_at: float) -> dict[str, Any]:
    return {
        "success": False,
        "action_type": action.get("action_type", ""),
        "delivery_tool_id": delivery_tool_id,
        "record_id": "",
        "artifact_url": "",
        "external_tool_called": False,
        "error": error,
        "latency_ms": int((perf_counter() - started_at) * 1000),
    }


def _local_sqlite(db_path: str | Path, state: dict[str, Any], action: dict[str, Any], started_at: float) -> dict[str, Any]:
    action_type = action.get("action_type")
    payload = {**action, "run_id": state.get("run_id", "run_unknown")}
    if action_type == "create_task":
        result = create_task(db_path, payload)
    elif action_type == "create_metric_alert":
        result = create_metric_alert(db_path, payload)
    elif action_type == "create_email_draft":
        result = create_email_draft(db_path, payload)
    else:
        return _failure(action, "local_sqlite", f"Unsupported action_type: {action_type}", started_at)

    return {
        **result,
        "delivery_tool_id": "local_sqlite",
        "tool_type": "local_action_store",
        "artifact_url": "",
        "external_tool_called": False,
        "latency_ms": int((perf_counter() - started_at) * 1000),
    }


def _jira_ticket_mock(state: dict[str, Any], action: dict[str, Any], started_at: float) -> dict[str, Any]:
    ticket_slug = _safe_slug(str(action.get("action_id") or action.get("title") or "ticket"))
    artifact_url = f"mock://jira/{state.get('run_id', 'run_unknown')}/{ticket_slug}"
    return {
        "success": True,
        "action_type": action.get("action_type", "create_task"),
        "delivery_tool_id": "jira_ticket_mock",
        "tool_type": "mock_external_ticketing",
        "record_id": f"jira_{ticket_slug}",
        "artifact_url": artifact_url,
        "external_tool_called": True,
        "requires_network": False,
        "requires_api_key": False,
        "status": "created",
        "latency_ms": int((perf_counter() - started_at) * 1000),
    }


def execute_action_delivery(
    *,
    db_path: str | Path,
    state: dict[str, Any],
    action: dict[str, Any],
) -> dict[str, Any]:
    started_at = perf_counter()
    delivery_tool_id = str(action.get("delivery_tool_id") or "local_sqlite").strip()
    policy = validate_action_delivery_tool(delivery_tool_id, action)
    if not policy.get("success"):
        return {
            **_failure(action, delivery_tool_id, policy.get("validation_error", "action delivery rejected"), started_at),
            "policy_result": policy,
        }

    if delivery_tool_id == "local_sqlite":
        result = _local_sqlite(db_path, state, action, started_at)
    elif delivery_tool_id == "jira_ticket_mock":
        result = _jira_ticket_mock(state, action, started_at)
    else:
        result = _failure(action, delivery_tool_id, f"Unknown action delivery tool: {delivery_tool_id}", started_at)
    return {**result, "policy_result": policy}
