from __future__ import annotations

from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qsl, urlsplit


_SECRET_QUERY_KEYS = {
    "api_key",
    "apikey",
    "access_key",
    "access_token",
    "token",
    "secret",
    "password",
    "key",
}
_BASE_INTERNAL_PATTERN = re.compile(
    r"\b(?:raw_sql|generated_sql|raw_rows|trace_path|trace_id|provider_metadata|api_key|apikey|"
    r"access_key|access_token|secret|password|database_path|analysis\.db|task_id|task_purpose|debug_id|"
    r"prompt(?:_id|_text|_version)?|completion_tokens|prompt_tokens)\b",
    re.IGNORECASE,
)
_CLI_INTERNAL_PATTERN = re.compile(r"\b(?:raw\s*stdout|raw\s*stderr|stdout|stderr|rows|token)\b", re.IGNORECASE)


def contains_sensitive_text(
    value: Any,
    *,
    strict_cli: bool = False,
    block_artifact_files: bool = False,
) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    lowered = text.lower()
    if re.search(r"\b(?:select|with|insert|update|delete|drop|alter|create|pragma)\b", text, re.IGNORECASE):
        return True
    if re.search(r"(^|[=/\s])(?:/users/|/tmp/|~[/\\])", lowered):
        return True
    if _BASE_INTERNAL_PATTERN.search(lowered):
        return True
    if strict_cli and (_CLI_INTERNAL_PATTERN.search(lowered) or lowered == "trace.json" or lowered.endswith("/trace.json")):
        return True
    if re.search(r"\bsk-[A-Za-z0-9_-]+", text):
        return True
    if block_artifact_files:
        parsed_path = urlsplit(text).path.lower()
        if parsed_path == "trace.json" or parsed_path.endswith((".db", "/trace.json")):
            return True
    return False


def safe_text(
    value: Any,
    *,
    strict_cli: bool = False,
    block_artifact_files: bool = False,
) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, int | float):
        text = str(value)
    else:
        text = str(value).strip()
    return "" if contains_sensitive_text(text, strict_cli=strict_cli, block_artifact_files=block_artifact_files) else text


def unsafe_relative_path(value: str) -> bool:
    text = str(value or "").strip()
    return text.startswith("~") or any(part == ".." for part in Path(text).parts)


def safe_workspace_path(value: Any, *, workspace_root: str | Path | None) -> str:
    text = safe_text(value)
    if not text or unsafe_relative_path(text):
        return ""
    path = Path(text)
    if not path.is_absolute():
        return path.as_posix()
    if not workspace_root:
        return ""
    try:
        return path.resolve().relative_to(Path(workspace_root).resolve()).as_posix()
    except (OSError, ValueError):
        return ""


def safe_relative_path(value: Any) -> str:
    text = safe_text(value, block_artifact_files=True)
    if not text or "://" in text or text.startswith("/api/") or unsafe_relative_path(text):
        return ""
    path = Path(text)
    return "" if path.is_absolute() else path.as_posix()


def url_has_secret_marker(value: str) -> bool:
    lower = str(value or "").lower()
    if any(marker in lower for marker in ("api_key=", "access_token=", "token=", "secret=", "password=")):
        return True
    try:
        parsed = urlsplit(value)
    except ValueError:
        return True
    return any(key.lower() in _SECRET_QUERY_KEYS for key, _ in parse_qsl(parsed.query, keep_blank_values=True))


def safe_url(value: Any, *, allow_api: bool = True, strict_cli: bool = False) -> str:
    text = safe_text(value, strict_cli=strict_cli)
    if not text or url_has_secret_marker(text):
        return ""
    if text.startswith("http://") or text.startswith("https://") or (allow_api and text.startswith("/api/")):
        return text
    return ""


def safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0
