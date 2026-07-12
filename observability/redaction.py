from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Callable


MAX_TEXT_LENGTH = 256
MAX_CATEGORY_LENGTH = 64
MAX_IDENTIFIER_LENGTH = 64

OBSERVABILITY_FIELDS = (
    "timestamp",
    "level",
    "event",
    "request_id",
    "run_id",
    "session_id",
    "workspace_id",
    "report_id",
    "node",
    "tool_name",
    "operation",
    "provider",
    "status",
    "error_type",
    "latency_ms",
    "retry_count",
    "event_count",
    "http_method",
    "route",
    "status_code",
    "status_class",
)
OBSERVABILITY_FIELD_ALLOWLIST = frozenset(OBSERVABILITY_FIELDS)

_IDENTIFIER_FIELDS = frozenset(
    {"request_id", "run_id", "session_id", "workspace_id", "report_id"}
)
_CATEGORY_FIELDS = frozenset(
    {"level", "event", "node", "tool_name", "operation", "provider", "status", "error_type"}
)
_NON_NEGATIVE_INTEGER_FIELDS = frozenset({"latency_ms", "retry_count", "event_count"})

HTTP_METHODS = frozenset({"CONNECT", "DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT", "TRACE"})
HTTP_STATUS_CLASSES = frozenset({"1xx", "2xx", "3xx", "4xx", "5xx"})

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_SAFE_CATEGORY = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_SAFE_ROUTE = re.compile(r"^/(?:[A-Za-z0-9._~-]+|\{[A-Za-z_][A-Za-z0-9_]*(?::path)?\})(?:/(?:[A-Za-z0-9._~-]+|\{[A-Za-z_][A-Za-z0-9_]*(?::path)?\}))*$")
_SQL_LIKE_IDENTIFIER = re.compile(
    r"(?i)(?:^|[._-])(?:select|insert|update|delete|drop|alter|create|union)(?:$|[._-])"
)
_SQL_CONTENT_PATTERN = re.compile(
    r"(?is)(?:\bselect\b.+\bfrom\b|\binsert\s+into\b|\bupdate\b.+\bset\b|"
    r"\bdelete\s+from\b|\bdrop\s+(?:table|database)\b|\balter\s+table\b|"
    r"\bcreate\s+(?:table|database)\b|\bpragma\b|\bunion\s+(?:all\s+)?select\b)"
)
_SECRET_PATTERN = re.compile(
    r"(?i)(?:(?:authorization|api[_-]?key|password|passwd|secret|token|cookie)"
    r"\s*(?:[:=]\s*|\s+)[^\s]+|bearer\s+[A-Za-z0-9._~+/=-]+|"
    r"\bsk-[A-Za-z0-9_-]{8,}|secret-do-not-leak|synthetic-token-do-not-leak)"
)
_PROHIBITED_CONTENT_PATTERN = re.compile(
    r"(?i)(?:\bprompt\b|\bsystem\s+message\b|\bmessages?\b|\braw\s+rows?\b|"
    r"\bprovider\s+(?:request|response|payload)\b|"
    r"(?:^|[\s/\\:=])\.env(?:$|[\s/\\:=]))"
)
_UNIX_PATH_PATTERN = re.compile(
    r"(?i)/(?:Users|home|app|tmp|var|private)(?:/|\\)[^\s]*"
)
_WINDOWS_PATH_PATTERN = re.compile(
    r"(?i)(?:^|[\s=])(?:[A-Z]:\\|\\\\)[^\s]+"
)
_FILE_URI_PATTERN = re.compile(r"(?i)\bfile:(?://)?[/\\][^\s]*")


def safe_truncate(value: object, *, max_length: int = MAX_TEXT_LENGTH) -> str | None:
    """Bound trusted primitive text without invoking arbitrary object methods."""
    if type(value) is not str or max_length < 1:
        return None
    return value[:max_length]


def is_secret_like(value: object) -> bool:
    return type(value) is not str or _SECRET_PATTERN.search(value) is not None


def is_sql_like(value: object) -> bool:
    return type(value) is str and _SQL_CONTENT_PATTERN.search(value) is not None


def is_path_like(value: object) -> bool:
    if type(value) is not str:
        return False
    return any(
        pattern.search(value) is not None
        for pattern in (_UNIX_PATH_PATTERN, _WINDOWS_PATH_PATTERN, _FILE_URI_PATTERN)
    )


def is_prohibited_text(value: object) -> bool:
    if type(value) is not str:
        return True
    return (
        is_secret_like(value)
        or is_sql_like(value)
        or is_path_like(value)
        or _PROHIBITED_CONTENT_PATTERN.search(value) is not None
    )


def safe_identifier(value: object) -> str | None:
    if type(value) is not str or _SAFE_IDENTIFIER.fullmatch(value) is None:
        return None
    if _SQL_LIKE_IDENTIFIER.search(value) is not None or is_prohibited_text(value):
        return None
    return value


def safe_category(value: object, *, max_length: int = MAX_CATEGORY_LENGTH) -> str | None:
    if type(value) is not str or not value or len(value) > max_length:
        return None
    if _SAFE_CATEGORY.fullmatch(value) is None or is_prohibited_text(value):
        return None
    return value


def safe_utc_timestamp(value: object) -> str | None:
    if type(value) is not str or len(value) > MAX_TEXT_LENGTH or is_prohibited_text(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        return None
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def safe_non_negative_integer(value: object) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def safe_http_method(value: object) -> str | None:
    return value if type(value) is str and value in HTTP_METHODS else None


def safe_route(value: object) -> str | None:
    if value == "unmatched":
        return "unmatched"
    if type(value) is not str or len(value) > MAX_TEXT_LENGTH or "?" in value:
        return None
    return value if _SAFE_ROUTE.fullmatch(value) is not None and not is_prohibited_text(value) else None


def safe_status_code(value: object) -> int | None:
    return value if type(value) is int and 100 <= value <= 599 else None


def safe_status_class(value: object) -> str | None:
    return value if type(value) is str and value in HTTP_STATUS_CLASSES else None


def classify_error(error: BaseException | type[BaseException] | None) -> str | None:
    """Convert exception type only; exception text/repr is intentionally ignored."""
    if error is None:
        return None
    error_type = error if isinstance(error, type) and issubclass(error, BaseException) else type(error)
    categories: tuple[tuple[type[BaseException], str], ...] = (
        (TimeoutError, "timeout"),
        (PermissionError, "permission_denied"),
        (FileNotFoundError, "not_found"),
        (ConnectionError, "connection_error"),
        (ValueError, "validation_error"),
        (TypeError, "type_error"),
        (OSError, "io_error"),
    )
    for exception_class, category in categories:
        if issubclass(error_type, exception_class):
            return category
    return "internal_error"


def _field_sanitizer(field: str) -> Callable[[object], object | None]:
    if field in _IDENTIFIER_FIELDS:
        return safe_identifier
    if field in _CATEGORY_FIELDS:
        return safe_category
    if field == "timestamp":
        return safe_utc_timestamp
    if field in _NON_NEGATIVE_INTEGER_FIELDS:
        return safe_non_negative_integer
    if field == "http_method":
        return safe_http_method
    if field == "route":
        return safe_route
    if field == "status_code":
        return safe_status_code
    if field == "status_class":
        return safe_status_class
    raise KeyError(field)


def sanitize_observability_fields(fields: Mapping[object, object]) -> dict[str, Any]:
    """Validate the fixed scalar event schema; collections and objects fail closed."""
    if not isinstance(fields, Mapping):
        return {}
    result: dict[str, Any] = {}
    for field in OBSERVABILITY_FIELDS:
        try:
            value = fields[field]
        except KeyError:
            continue
        except Exception:
            continue
        try:
            sanitized = _field_sanitizer(field)(value)
        except Exception:
            continue
        if sanitized is not None:
            result[field] = sanitized
    return result


redact_observability_data = sanitize_observability_fields
