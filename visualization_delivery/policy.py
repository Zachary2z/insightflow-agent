from __future__ import annotations

from typing import Any

from visualization_delivery.tool_catalog import get_delivery_tool


def validate_delivery_tool(delivery_tool_id: str, *, execution_result: dict[str, Any]) -> dict[str, Any]:
    tool_id = str(delivery_tool_id or "").strip()
    tool = get_delivery_tool(tool_id)
    if tool is None:
        return {
            "success": False,
            "delivery_tool_id": tool_id,
            "validation_error": f"Unknown delivery tool: {tool_id}",
        }
    if not execution_result or not execution_result.get("success"):
        return {
            "success": False,
            "delivery_tool_id": tool_id,
            "validation_error": "execution_result must be successful before visualization delivery",
        }
    return {
        "success": True,
        "delivery_tool_id": tool.tool_id,
        "tool_type": tool.tool_type,
        "requires_network": tool.requires_network,
        "requires_api_key": tool.requires_api_key,
        "is_mock": tool.is_mock,
        "validation_error": "",
    }
