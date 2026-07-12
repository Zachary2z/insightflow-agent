from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from observability.context import CORRELATION_FIELDS, get_correlation_context, is_valid_correlation_id
from observability.redaction import classify_error, safe_category, sanitize_observability_fields


EVENT_NAMES = frozenset(
    {
        "http_request_started",
        "http_request_completed",
        "workflow_run_started",
        "workflow_run_completed",
        "agent_node_started",
        "agent_node_completed",
        "llm_request_completed",
        "sql_validation_completed",
        "sql_execution_completed",
        "evidence_validation_completed",
        "chart_generation_completed",
        "report_generation_completed",
        "document_export_completed",
        "external_publish_completed",
        "trace_persist_completed",
    }
)
LEVELS = frozenset({"debug", "info", "warning", "error", "critical"})
STATUSES = frozenset(
    {"started", "success", "completed", "failed", "error", "warning", "skipped", "timeout", "rejected", "unknown"}
)

EventLevel = Literal["debug", "info", "warning", "error", "critical"]
EventStatus = Literal[
    "started", "success", "completed", "failed", "error", "warning", "skipped", "timeout", "rejected", "unknown"
]


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _validated_timestamp(value: str | None) -> str:
    if value is None:
        return _utc_timestamp()
    if type(value) is not str:
        raise ValueError("timestamp must be UTC ISO 8601")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("timestamp must be UTC ISO 8601") from None
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("timestamp must be UTC ISO 8601")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ObservabilityEvent:
    timestamp: str
    level: EventLevel
    event: str
    request_id: str | None = None
    run_id: str | None = None
    session_id: str | None = None
    workspace_id: str | None = None
    report_id: str | None = None
    node: str | None = None
    tool_name: str | None = None
    operation: str | None = None
    provider: str | None = None
    status: EventStatus | None = None
    error_type: str | None = None
    latency_ms: int | None = None
    retry_count: int | None = None
    event_count: int | None = None
    http_method: str | None = None
    route: str | None = None
    status_code: int | None = None
    status_class: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return sanitize_observability_fields(
            {key: value for key, value in asdict(self).items() if value is not None}
        )


def _non_negative_integer(name: str, value: object | None) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def build_observability_event(
    event: str,
    *,
    level: EventLevel = "info",
    status: EventStatus | None = None,
    timestamp: str | None = None,
    error: BaseException | type[BaseException] | None = None,
    **fields: object,
) -> dict[str, Any]:
    """Build one bounded JSON-safe event; unknown fields are silently discarded."""
    if type(event) is not str or event not in EVENT_NAMES:
        raise ValueError("Unsupported observability event")
    if type(level) is not str or level not in LEVELS:
        raise ValueError("Unsupported observability level")
    if status is not None and (type(status) is not str or status not in STATUSES):
        raise ValueError("Unsupported observability status")

    correlation = get_correlation_context()
    for field in CORRELATION_FIELDS:
        explicit = fields.get(field)
        if field not in correlation and is_valid_correlation_id(explicit):
            correlation[field] = explicit

    categories: dict[str, str | None] = {}
    for field in ("node", "tool_name", "operation", "provider"):
        categories[field] = safe_category(fields.get(field))

    explicit_error_type = safe_category(fields.get("error_type"))
    error_type = classify_error(error) if error is not None else explicit_error_type
    record = ObservabilityEvent(
        timestamp=_validated_timestamp(timestamp),
        level=level,
        event=event,
        request_id=correlation.get("request_id"),
        run_id=correlation.get("run_id"),
        session_id=correlation.get("session_id"),
        workspace_id=correlation.get("workspace_id"),
        report_id=correlation.get("report_id"),
        node=categories["node"],
        tool_name=categories["tool_name"],
        operation=categories["operation"],
        provider=categories["provider"],
        status=status,
        error_type=error_type,
        latency_ms=_non_negative_integer("latency_ms", fields.get("latency_ms")),
        retry_count=_non_negative_integer("retry_count", fields.get("retry_count")),
        event_count=_non_negative_integer("event_count", fields.get("event_count")),
        http_method=fields.get("http_method"),
        route=fields.get("route"),
        status_code=fields.get("status_code"),
        status_class=fields.get("status_class"),
    )
    return record.to_dict()
