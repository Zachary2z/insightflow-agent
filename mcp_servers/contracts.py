from __future__ import annotations

from typing import Any


def build_contract(server_name: str, tools: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "server_name": server_name,
        "protocol_style": "mcp-style-json-tool-contract",
        "tools": tools,
    }


def tool_contract(
    name: str,
    description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    safety: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "safety": safety or {},
    }


def wrap_success(server_name: str, tool_name: str, result: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "success": bool(result.get("success", True)),
        "mcp_server": server_name,
        "tool_name": tool_name,
        "result": result,
        **extra,
    }


def wrap_failure(
    server_name: str,
    tool_name: str,
    error: str,
    result: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "success": False,
        "mcp_server": server_name,
        "tool_name": tool_name,
        "error": error,
        "result": result or {},
        **extra,
    }

