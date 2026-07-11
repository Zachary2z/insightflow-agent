from __future__ import annotations

import json
import re
from typing import Any

from workspaces.safe_output import safe_int, safe_text


SAFE_TOOL_CALL_FIELDS = {"operation", "command_name", "success", "elapsed_ms", "exit_code"}


def safe_cli_text(value: Any) -> str:
    text = safe_text(value, strict_cli=True)
    if "\n" in text:
        text = " ".join(part.strip() for part in text.splitlines() if part.strip())
    return text


def safe_command_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return safe_cli_text(re.split(r"[/\\]+", text)[-1])


def safe_cli_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(text for text in (safe_cli_text(item) for item in value) if text))


def safe_tool_call(value: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key in SAFE_TOOL_CALL_FIELDS:
        if key not in value:
            continue
        item = value.get(key)
        if key == "success":
            cleaned[key] = bool(item)
        elif key in {"elapsed_ms", "exit_code"}:
            cleaned[key] = safe_int(item)
        else:
            safe = safe_command_name(item) if key == "command_name" else safe_cli_text(item)
            if safe:
                cleaned[key] = safe
    return cleaned


def build_tool_call(
    *,
    operation: str,
    command_name: str,
    default_command_name: str,
    success: bool,
    exit_code: int,
    elapsed_ms: int,
) -> dict[str, Any]:
    return {
        "operation": safe_cli_text(operation),
        "command_name": safe_command_name(command_name) or default_command_name,
        "success": bool(success),
        "elapsed_ms": safe_int(elapsed_ms),
        "exit_code": int(exit_code or 0),
    }


def parse_json_object(value: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value or "")
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def first_text(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        text = safe_cli_text(data.get(key))
        if text:
            return text
    return ""
