from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Literal, Protocol
from urllib.parse import parse_qsl, urlsplit

from workspaces.export_package import EXPORT_PACKAGE_VERSION, SOURCE_REPORT
from workspaces.models import utc_now_iso


PublishStatus = Literal["published", "warning", "failed"]
SAFE_TOOL_CALL_FIELDS = {"operation", "command_name", "success", "elapsed_ms", "exit_code"}


@dataclass
class ExternalPublishResult:
    platform: str
    status: PublishStatus
    title: str
    url: str | None = None
    document_id: str | None = None
    external_id: str | None = None
    created_at: str | None = None
    inserted_chart_count: int = 0
    failed_chart_count: int = 0
    warnings: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_safe_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["platform"] = _safe_text(data.get("platform")) or "external"
        data["status"] = data["status"] if data.get("status") in {"published", "warning", "failed"} else "failed"
        data["title"] = _safe_text(data.get("title"))
        data["url"] = _safe_url(data.get("url"))
        data["document_id"] = _safe_text(data.get("document_id")) or None
        data["external_id"] = _safe_text(data.get("external_id")) or None
        data["created_at"] = _safe_text(data.get("created_at")) or None
        data["inserted_chart_count"] = _safe_int(data.get("inserted_chart_count"))
        data["failed_chart_count"] = _safe_int(data.get("failed_chart_count"))
        data["warnings"] = _safe_text_list(data.get("warnings"))
        data["tool_calls"] = [_safe_tool_call(item) for item in data.get("tool_calls") or [] if isinstance(item, dict)]
        return data


class FeishuPublisher(Protocol):
    def publish_report(self, package: Any) -> ExternalPublishResult:
        ...


def failed_publish_result(
    *,
    platform: str,
    title: str = "",
    warning: str,
    tool_calls: list[dict[str, Any]] | None = None,
) -> ExternalPublishResult:
    return ExternalPublishResult(
        platform=platform,
        status="failed",
        title=title,
        created_at=utc_now_iso(),
        warnings=[warning],
        tool_calls=tool_calls or [],
    )


def export_package_to_dict(package: Any) -> dict[str, Any]:
    if isinstance(package, dict):
        return dict(package)
    to_dict = getattr(package, "to_dict", None)
    if callable(to_dict):
        data = to_dict()
        return data if isinstance(data, dict) else {}
    return {}


def is_report_export_package(package: Any) -> bool:
    data = export_package_to_dict(package)
    return (
        bool(data)
        and data.get("package_version") == EXPORT_PACKAGE_VERSION
        and data.get("source_type") == SOURCE_REPORT
    )


def safe_warning(value: Any) -> str:
    return _safe_text(value)


def safe_command_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    name = re.split(r"[/\\]+", text)[-1]
    return _safe_text(name)


def _safe_tool_call(value: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key in SAFE_TOOL_CALL_FIELDS:
        if key not in value:
            continue
        item = value.get(key)
        if key == "success":
            cleaned[key] = bool(item)
        elif key in {"elapsed_ms", "exit_code"}:
            cleaned[key] = _safe_int(item)
        else:
            safe = safe_command_name(item) if key == "command_name" else _safe_text(item)
            if safe:
                cleaned[key] = safe
    return cleaned


def _safe_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys([text for text in (_safe_text(item) for item in value) if text]))


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    text = str(value).strip()
    return "" if _contains_sensitive_text(text) else text


def _safe_url(value: Any) -> str | None:
    text = _safe_text(value)
    if not text:
        return None
    if _url_has_secret_marker(text):
        return None
    if text.startswith("http://") or text.startswith("https://") or text.startswith("/api/"):
        return text
    return None


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _url_has_secret_marker(value: str) -> bool:
    secret_keys = {"api_key", "apikey", "access_key", "access_token", "token", "secret", "password", "key"}
    lower = value.lower()
    if any(marker in lower for marker in ("api_key=", "access_token=", "token=", "secret=", "password=")):
        return True
    try:
        parsed = urlsplit(value)
    except ValueError:
        return True
    return any(key.lower() in secret_keys for key, _ in parse_qsl(parsed.query, keep_blank_values=True))


def _contains_sensitive_text(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    lowered = text.lower()
    if re.search(r"\b(?:select|with|insert|update|delete|drop|alter|create|pragma)\b", text, re.IGNORECASE):
        return True
    if re.search(r"(^|[=/\s])(?:/users/|/tmp/|~[/\\])", lowered):
        return True
    if re.search(
        r"\b(?:raw\s*stdout|raw\s*stderr|stdout|stderr|raw_sql|generated_sql|raw_rows|rows|trace_path|trace_id|provider_metadata|api_key|apikey|access_key|access_token|token|secret|password|database_path|analysis\.db|debug_id|prompt(?:_id|_text|_version)?|completion_tokens|prompt_tokens)\b",
        lowered,
    ):
        return True
    if lowered == "trace.json" or lowered.endswith("/trace.json"):
        return True
    if re.search(r"\bsk-[A-Za-z0-9_-]+", text):
        return True
    return False
