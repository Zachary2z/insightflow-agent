from __future__ import annotations

import json
from datetime import datetime

import pytest

from observability.context import correlation_scope
from observability.events import build_observability_event


def test_event_automatically_merges_current_context_and_serializes():
    with correlation_scope(request_id="req_event", run_id="run_event", workspace_id="workspace_event"):
        event = build_observability_event(
            "workflow_run_completed",
            status="success",
            operation="analysis",
            latency_ms=12,
            retry_count=0,
        )
    assert event["request_id"] == "req_event"
    assert event["run_id"] == "run_event"
    assert event["workspace_id"] == "workspace_event"
    assert json.loads(json.dumps(event)) == event


def test_event_timestamp_is_utc_iso_8601():
    event = build_observability_event("http_request_started", status="started")
    assert event["timestamp"].endswith("Z")
    parsed = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
    assert parsed.utcoffset().total_seconds() == 0


def test_unknown_fields_are_dropped():
    event = build_observability_event(
        "sql_execution_completed",
        status="success",
        sql="SELECT secret FROM customer",
        prompt="private prompt",
        arbitrary={"nested": "value"},
    )
    assert "sql" not in event
    assert "prompt" not in event
    assert "arbitrary" not in event


def test_scalar_event_fields_reject_nested_collections():
    event = build_observability_event(
        "llm_request_completed",
        status="success",
        operation=["SELECT * FROM customer", ".env contents"],
        provider={"provider": "provider payload", "status": "Bearer synthetic-token-do-not-leak"},
    )
    assert "operation" not in event
    assert "provider" not in event
    serialized = json.dumps(event)
    for forbidden in ("SELECT", "customer", ".env", "provider payload", "synthetic-token"):
        assert forbidden not in serialized


def test_valid_scalar_event_fields_still_serialize():
    event = build_observability_event(
        "llm_request_completed",
        status="success",
        operation="business_answer",
        provider="deepseek",
        latency_ms=10,
        retry_count=1,
    )
    assert event["operation"] == "business_answer"
    assert event["provider"] == "deepseek"
    assert json.loads(json.dumps(event)) == event


@pytest.mark.parametrize("field", ["latency_ms", "retry_count", "event_count"])
def test_negative_numeric_fields_are_rejected(field):
    with pytest.raises(ValueError):
        build_observability_event("agent_node_completed", **{field: -1})


def test_unsafe_explicit_request_id_cannot_override_context():
    with correlation_scope(request_id="req_safe"):
        event = build_observability_event(
            "http_request_completed",
            request_id="../../unsafe",
            status="completed",
        )
    assert event["request_id"] == "req_safe"


def test_unsafe_explicit_request_id_is_dropped_without_context():
    event = build_observability_event("http_request_completed", request_id="<unsafe>")
    assert "request_id" not in event


@pytest.mark.parametrize(
    ("field", "value"),
    [("event", "invented_event"), ("level", "verbose"), ("status", "invented_status")],
)
def test_event_level_and_status_use_controlled_values(field, value):
    kwargs = {field: value}
    if field == "event":
        with pytest.raises(ValueError):
            build_observability_event(value)
    else:
        with pytest.raises(ValueError):
            build_observability_event("http_request_completed", **kwargs)


@pytest.mark.parametrize(
    ("field", "value"),
    [("event", ["http_request_completed"]), ("level", {"level": "info"}), ("status", ["success"])],
)
def test_event_level_and_status_reject_collection_types(field, value):
    if field == "event":
        with pytest.raises(ValueError):
            build_observability_event(value)
    else:
        with pytest.raises(ValueError):
            build_observability_event("http_request_completed", **{field: value})


def test_raw_exception_is_reduced_to_controlled_type():
    secret = "health-secret-do-not-leak"
    event = build_observability_event(
        "external_publish_completed",
        status="error",
        error=PermissionError(f"Bearer synthetic-token-do-not-leak {secret} /Users/private/file"),
    )
    serialized = json.dumps(event)
    assert event["error_type"] == "permission_denied"
    assert secret not in serialized
    assert "Bearer" not in serialized
    assert "/Users/" not in serialized


def test_http_fields_use_controlled_scalar_schema():
    event = build_observability_event(
        "http_request_completed",
        http_method="GET",
        route="/api/workspaces/{workspace_id}/reports/{report_id}",
        status_code=200,
        status_class="2xx",
        status="success",
    )
    assert event["http_method"] == "GET"
    assert event["route"] == "/api/workspaces/{workspace_id}/reports/{report_id}"
    assert event["status_code"] == 200
    assert event["status_class"] == "2xx"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("http_method", "CUSTOM"),
        ("route", "/api/workspaces/real-id?secret=yes"),
        ("route", {"path": "/health/live"}),
        ("status_code", 99),
        ("status_code", 600),
        ("status_code", "200"),
        ("status_class", "200"),
    ],
)
def test_invalid_http_fields_fail_closed(field, value):
    event = build_observability_event("http_request_completed", **{field: value})
    assert field not in event


def test_trace_event_allows_non_negative_event_count():
    event = build_observability_event(
        "trace_persist_completed",
        status="success",
        operation="trace_persist",
        event_count=3,
    )

    assert event["event_count"] == 3
