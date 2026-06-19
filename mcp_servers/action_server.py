from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp_servers.contracts import build_contract, tool_contract, wrap_failure, wrap_success
from tools.action_tool import create_email_draft, create_metric_alert, create_task


SERVER_NAME = "action-mcp-server"


def get_tool_contract() -> dict[str, Any]:
    return build_contract(
        SERVER_NAME,
        [
            tool_contract(
                name="create_task",
                description="Create an operational task after human approval has been recorded upstream.",
                input_schema={"type": "object", "required": ["db_path", "task", "approval_status"]},
                output_schema={"type": "object", "required": ["success", "result"]},
                safety={"approval_status_must_be": "approved"},
            ),
            tool_contract(
                name="create_metric_alert",
                description="Create a metric alert after human approval has been recorded upstream.",
                input_schema={"type": "object", "required": ["db_path", "alert", "approval_status"]},
                output_schema={"type": "object", "required": ["success", "result"]},
                safety={"approval_status_must_be": "approved"},
            ),
            tool_contract(
                name="create_email_draft",
                description="Create an email draft after human approval has been recorded upstream.",
                input_schema={"type": "object", "required": ["db_path", "draft", "approval_status"]},
                output_schema={"type": "object", "required": ["success", "result"]},
                safety={"approval_status_must_be": "approved"},
            ),
        ],
    )


def _approval_allows_action(approval_status: str) -> tuple[bool, str]:
    if approval_status == "approved":
        return True, ""
    return False, "approval required before action execution"


def mcp_create_task(db_path: str | Path, task: dict[str, Any], approval_status: str) -> dict[str, Any]:
    allowed, error = _approval_allows_action(approval_status)
    if not allowed:
        return wrap_failure(SERVER_NAME, "create_task", error, approval_status=approval_status)
    result = create_task(db_path, task)
    if not result.get("success"):
        return wrap_failure(SERVER_NAME, "create_task", str(result.get("error", "task creation failed")), result)
    return wrap_success(SERVER_NAME, "create_task", result, approval_status=approval_status)


def mcp_create_metric_alert(db_path: str | Path, alert: dict[str, Any], approval_status: str) -> dict[str, Any]:
    allowed, error = _approval_allows_action(approval_status)
    if not allowed:
        return wrap_failure(SERVER_NAME, "create_metric_alert", error, approval_status=approval_status)
    result = create_metric_alert(db_path, alert)
    if not result.get("success"):
        return wrap_failure(SERVER_NAME, "create_metric_alert", str(result.get("error", "alert creation failed")), result)
    return wrap_success(SERVER_NAME, "create_metric_alert", result, approval_status=approval_status)


def mcp_create_email_draft(db_path: str | Path, draft: dict[str, Any], approval_status: str) -> dict[str, Any]:
    allowed, error = _approval_allows_action(approval_status)
    if not allowed:
        return wrap_failure(SERVER_NAME, "create_email_draft", error, approval_status=approval_status)
    result = create_email_draft(db_path, draft)
    if not result.get("success"):
        return wrap_failure(SERVER_NAME, "create_email_draft", str(result.get("error", "draft creation failed")), result)
    return wrap_success(SERVER_NAME, "create_email_draft", result, approval_status=approval_status)
