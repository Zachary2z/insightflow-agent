from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry
from prometheus_client.parser import text_string_to_metric_families

from api.app import create_app
from llm_ops.provider import LLMRequest, run_llm_request
from observability.context import correlation_scope
from observability.events import build_observability_event
from observability.metrics import InsightFlowMetrics, metrics_scope
from observability.trace_sink import (
    CompositeTraceSink,
    LocalJsonTraceSink,
    StructuredLogTraceSink,
    TraceDocument,
    TracePersistRequest,
)
from tools.evidence_tool import validate_evidence
from tools.sql_executor import run_sql
from tools.sql_validator import validate_sql
from workspaces.store import WorkspaceStore


HOSTILE = (
    "Authorization: Bearer synthetic-token-do-not-leak "
    "SELECT secret FROM customers Prompt=/Users/private/workspace "
    "provider payload raw rows"
)


def _samples(metrics: InsightFlowMetrics, name: str):
    return [
        sample
        for family in text_string_to_metric_families(metrics.exposition().decode())
        for sample in family.samples
        if sample.name == name
    ]


def _serialized(events: list[dict]) -> str:
    return json.dumps(events, ensure_ascii=False)


def _capture(events: list[dict], event: str, fields: dict) -> None:
    events.append(build_observability_event(event, **fields))


def _assert_no_sensitive_content(value: str) -> None:
    for forbidden in (
        "synthetic-token-do-not-leak",
        "SELECT secret",
        "Prompt=",
        "/Users/private",
        "provider payload",
        "raw rows",
    ):
        assert forbidden not in value


def test_api_handler_exception_is_safe_correlated_logged_and_counted():
    events: list[dict] = []
    metrics = InsightFlowMetrics(CollectorRegistry())
    app = create_app(metrics=metrics, event_emitter=lambda event, **fields: events.append({"event": event, **fields}))

    @app.get("/failure-injection/{item_id}")
    def explode(item_id: str):
        raise RuntimeError(f"{HOSTILE} item={item_id}")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/failure-injection/customer-991?token=synthetic-token-do-not-leak",
            headers={"X-Request-ID": "req_failure_safe"},
        )

    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    completed = [event for event in events if event["event"] == "http_request_completed"]
    assert len(completed) == 1
    assert completed[0]["request_id"] == "req_failure_safe"
    assert completed[0]["route"] == "/failure-injection/{item_id}"
    assert completed[0]["status"] == "error"
    assert completed[0]["error_type"] == "internal_error"
    assert any(
        sample.labels == {
            "method": "GET",
            "route": "/failure-injection/{item_id}",
            "status_class": "5xx",
        }
        for sample in _samples(metrics, "insightflow_http_requests_total")
    )
    _assert_no_sensitive_content(_serialized(events) + metrics.exposition().decode() + response.text)


def test_provider_timeout_emits_bounded_event_metric_and_preserves_safe_failure(monkeypatch):
    class TimeoutProvider:
        model = "private-dynamic-model"

        def generate(self, _request):
            raise TimeoutError(HOSTILE)

    events: list[dict] = []
    metrics = InsightFlowMetrics(CollectorRegistry())
    monkeypatch.setattr(
        "llm_ops.provider.safely_emit",
        lambda _emitter, event, **fields: _capture(events, event, fields),
    )
    monkeypatch.setattr("llm_ops.provider.emit_observability_event", object())

    with correlation_scope(request_id="req_provider", run_id="run_provider", workspace_id="workspace_provider"):
        with metrics_scope(metrics):
            result = run_llm_request(
                TimeoutProvider(),
                LLMRequest(f"private prompt {HOSTILE}", "question_understanding", "private-version"),
            )

    assert result["success"] is False
    assert result["error_type"] == "llm_provider_error"
    assert len(events) == 1
    assert events[0]["event"] == "llm_request_completed"
    assert events[0]["request_id"] == "req_provider"
    assert events[0]["run_id"] == "run_provider"
    assert events[0]["workspace_id"] == "workspace_provider"
    assert events[0]["operation"] == "question_understanding"
    assert events[0]["provider"] == "other"
    assert events[0]["status"] == "timeout" and events[0]["error_type"] == "timeout"
    assert events[0]["latency_ms"] == result["latency_ms"]
    assert any(
        sample.labels == {"provider": "other", "operation": "question_understanding", "status": "timeout"}
        for sample in _samples(metrics, "insightflow_llm_requests_total")
    )
    _assert_no_sensitive_content(_serialized(events) + metrics.exposition().decode())


def test_sql_rejection_and_execution_failure_emit_events_metrics_and_safe_results(tmp_path, monkeypatch):
    events: list[dict] = []
    monkeypatch.setattr(
        "tools.sql_validator.safely_emit",
        lambda _emitter, event, **fields: _capture(events, event, fields),
    )
    monkeypatch.setattr("tools.sql_validator.emit_observability_event", object())
    monkeypatch.setattr(
        "tools.sql_executor.safely_emit",
        lambda _emitter, event, **fields: _capture(events, event, fields),
    )
    monkeypatch.setattr("tools.sql_executor.emit_observability_event", object())
    metrics = InsightFlowMetrics(CollectorRegistry())
    schema = {"tables": [{"table_name": "facts", "columns": [{"name": "value"}]}]}

    with correlation_scope(request_id="req_sql", run_id="run_sql", workspace_id="workspace_sql"):
        with metrics_scope(metrics):
            rejected = validate_sql(f"DELETE FROM facts; -- {HOSTILE}", schema)
            failed = run_sql(tmp_path / "missing.sqlite", f"SELECT secret FROM facts -- {HOSTILE}")

    assert rejected["approved"] is False and rejected["risk_level"] == "high"
    assert failed["success"] is False and failed["rows"] == []
    assert [event["event"] for event in events] == ["sql_validation_completed", "sql_execution_completed"]
    assert all(event["request_id"] == "req_sql" and event["run_id"] == "run_sql" for event in events)
    assert events[0]["status"] == "rejected" and events[0]["error_type"] == "validation"
    assert events[1]["status"] == "error" and events[1]["error_type"] == "execution"
    assert any(s.labels == {"status": "rejected", "risk_level": "high"} for s in _samples(metrics, "insightflow_sql_validations_total"))
    assert any(s.labels == {"status": "error", "error_type": "execution"} for s in _samples(metrics, "insightflow_sql_executions_total"))
    _assert_no_sensitive_content(_serialized(events) + metrics.exposition().decode())


def test_evidence_failure_emits_bounded_event_and_metric(monkeypatch):
    events: list[dict] = []
    monkeypatch.setattr(
        "tools.evidence_tool.safely_emit",
        lambda _emitter, event, **fields: _capture(events, event, fields),
    )
    monkeypatch.setattr("tools.evidence_tool.emit_observability_event", object())
    metrics = InsightFlowMetrics(CollectorRegistry())

    with correlation_scope(request_id="req_evidence", run_id="run_evidence", workspace_id="workspace_evidence"):
        with metrics_scope(metrics):
            result = validate_evidence([], {"success": False, "error": HOSTILE, "rows": [[HOSTILE]]})

    assert result["success"] is False
    assert len(events) == 1
    assert events[0]["event"] == "evidence_validation_completed"
    assert events[0]["request_id"] == "req_evidence" and events[0]["run_id"] == "run_evidence"
    assert events[0]["operation"] == "evidence_validation"
    assert events[0]["status"] == "error" and events[0]["error_type"] == "validation"
    assert events[0]["latency_ms"] == result["trace_event"]["latency_ms"]
    assert any(
        sample.labels == {"status": "error", "reason_category": "validation"}
        for sample in _samples(metrics, "insightflow_evidence_validations_total")
    )
    _assert_no_sensitive_content(_serialized(events) + metrics.exposition().decode())


def test_chart_exception_is_observable_without_replacing_original_error(monkeypatch):
    from agents import visualization_agent

    original = RuntimeError(HOSTILE)
    events: list[dict] = []
    metrics = InsightFlowMetrics(CollectorRegistry())
    monkeypatch.setattr(visualization_agent, "_run_visualization_agent", lambda *_args, **_kwargs: (_ for _ in ()).throw(original))
    monkeypatch.setattr(
        visualization_agent,
        "safely_emit",
        lambda _emitter, event, **fields: _capture(events, event, fields),
    )
    monkeypatch.setattr(visualization_agent, "emit_observability_event", object())

    with correlation_scope(request_id="req_chart", run_id="run_chart", workspace_id="workspace_chart"):
        with metrics_scope(metrics), pytest.raises(RuntimeError) as caught:
            visualization_agent.run_visualization_agent({"run_id": "run_chart"})

    assert caught.value is original
    assert len(events) == 1
    assert events[0]["event"] == "chart_generation_completed"
    assert events[0]["request_id"] == "req_chart" and events[0]["run_id"] == "run_chart"
    assert events[0]["operation"] == "visualization"
    assert events[0]["status"] == "error" and events[0]["error_type"] == "internal_error"
    assert any(
        sample.labels == {"chart_type": "other", "status": "error"}
        for sample in _samples(metrics, "insightflow_chart_generations_total")
    )
    _assert_no_sensitive_content(_serialized(events) + metrics.exposition().decode())


def test_report_failure_is_safe_correlated_and_does_not_leak_exception(tmp_path):
    events: list[dict] = []
    metrics = InsightFlowMetrics(CollectorRegistry())
    store = WorkspaceStore(tmp_path / "workspaces")

    def fail_report(**_kwargs):
        raise RuntimeError(HOSTILE)

    app = create_app(
        workspace_store=store,
        report_runner=fail_report,
        metrics=metrics,
        event_emitter=lambda event, **fields: events.append({"event": event, **fields}),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        workspace_id = client.post("/api/workspaces", json={"name": "P38 failure"}).json()["workspace_id"]
        response = client.post(
            f"/api/workspaces/{workspace_id}/reports",
            headers={"X-Request-ID": "req_report_failure"},
            json={"report_type": "business_review", "report_goal": HOSTILE},
        )

    assert response.status_code == 500 and response.text == "Internal Server Error"
    report_event = next(event for event in events if event["event"] == "report_generation_completed")
    assert report_event["request_id"] == "req_report_failure"
    assert report_event["workspace_id"] == workspace_id
    assert report_event["status"] == "error" and report_event["error_type"] == "internal_error"
    assert any(s.labels == {"status": "error"} for s in _samples(metrics, "insightflow_report_generations_total"))
    _assert_no_sensitive_content(_serialized(events) + metrics.exposition().decode() + response.text)


def test_unwritable_local_trace_still_emits_safe_structured_sink_event(tmp_path):
    blocked_root = tmp_path / "blocked"
    blocked_root.write_text("not a directory", encoding="utf-8")
    events: list[dict] = []
    sink = CompositeTraceSink(
        [
            LocalJsonTraceSink(blocked_root),
            StructuredLogTraceSink(emitter=lambda event, **fields: events.append({"event": event, **fields})),
        ]
    )

    with correlation_scope(request_id="req_trace", workspace_id="workspace_trace"):
        result = sink.persist(
            TracePersistRequest(
                document=TraceDocument(
                    run_id="run_trace",
                    session_id="session_trace",
                    user_question=HOSTILE,
                    trace=({"tool_output_summary": HOSTILE},),
                    saved_at="2026-07-12T00:00:00Z",
                )
            )
        )

    assert [child.success for child in result.results] == [False, True]
    assert result.results[0].error_type in {"io_error", "internal_error"}
    assert events[0]["event"] == "trace_persist_completed"
    assert events[0]["run_id"] == "run_trace" and events[0]["session_id"] == "session_trace"
    assert events[0]["status"] == "error"
    _assert_no_sensitive_content(_serialized(events) + repr(result))


def test_many_boundary_ids_do_not_create_metric_labels_or_leak_headers():
    metrics = InsightFlowMetrics(CollectorRegistry())
    app = create_app(metrics=metrics)
    request_ids = [f"req_random_{index:04d}" for index in range(200)]
    with TestClient(app) as client:
        for request_id in request_ids:
            response = client.get("/health/live", headers={"X-Request-ID": request_id, "Authorization": HOSTILE})
            assert response.status_code == 200 and response.headers["X-Request-ID"] == request_id

    exposition = metrics.exposition().decode()
    http_samples = _samples(metrics, "insightflow_http_requests_total")
    assert len(http_samples) == 1
    assert http_samples[0].labels == {"method": "GET", "route": "/health/live", "status_class": "2xx"}
    assert http_samples[0].value == 200
    assert all(request_id not in exposition for request_id in request_ids)
    _assert_no_sensitive_content(exposition)
