from __future__ import annotations

from typing import Any

from action_delivery.tool_catalog import get_action_delivery_tool


def validate_action_delivery_tool(delivery_tool_id: str, action: dict[str, Any]) -> dict[str, Any]:
    tool_id = str(delivery_tool_id or "").strip()
    tool = get_action_delivery_tool(tool_id)
    if tool is None:
        return {
            "success": False,
            "delivery_tool_id": tool_id,
            "validation_error": f"Unknown action delivery tool: {tool_id}",
        }

    action_type = str(action.get("action_type", "")).strip()
    if tool_id == "jira_ticket_mock" and action_type != "create_task":
        return {
            "success": False,
            "delivery_tool_id": tool_id,
            "validation_error": "jira_ticket_mock only supports create_task actions",
        }

    return {
        "success": True,
        "delivery_tool_id": tool.tool_id,
        "tool_type": tool.tool_type,
        "is_mock": tool.is_mock,
        "requires_network": tool.requires_network,
        "requires_api_key": tool.requires_api_key,
        "validation_error": "",
    }
