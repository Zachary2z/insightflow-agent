from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.testclient import TestClient

from api.app import create_app
from api.health import ReadinessChecker, ReadinessPaths
from workspaces.store import WorkspaceStore


def _app(tmp_path: Path, events: list[dict], emitter=None):
    store = WorkspaceStore(tmp_path / "workspaces")
    checker = ReadinessChecker(
        ReadinessPaths(
            workspace_root=store.root_dir,
            report_root=tmp_path / "reports",
            trace_root=tmp_path / "traces",
        )
    )

    def collect(event, **fields):
        events.append({"event": event, **fields})

    app = create_app(
        workspace_store=store,
        readiness_checker=checker,
        event_emitter=emitter or collect,
    )

    @app.get("/_test/rejected/{item_id}")
    def rejected(item_id: str):
        raise HTTPException(status_code=409, detail=item_id)

    @app.get("/_test/stream/{item_id}")
    def stream(item_id: str):
        return StreamingResponse(iter([b"first", b"second"]), media_type="text/plain")

    @app.get("/_test/handled-5xx")
    def handled_5xx():
        return JSONResponse(status_code=503, content={"detail": "temporarily unavailable"})

    @app.get("/_test/stream-error/{item_id}")
    def stream_error(item_id: str):
        async def body():
            yield b"first"
            raise TimeoutError(
                f"Bearer synthetic-token-do-not-leak {item_id} SELECT * FROM customer /Users/private/project"
            )

        return StreamingResponse(body(), media_type="text/plain")

    @app.get("/_test/server-error/{item_id}")
    def server_error(item_id: str):
        raise RuntimeError(f"Bearer synthetic-token-do-not-leak {item_id} /Users/private/project")

    return app


def _request_events(events: list[dict], request_id: str) -> list[dict]:
    return [event for event in events if event.get("request_id") == request_id]


def test_normal_200_emits_one_success_completion(tmp_path):
    events: list[dict] = []
    with TestClient(_app(tmp_path, events)) as client:
        response = client.get("/health/live", headers={"X-Request-ID": "req_ok"})

    assert response.status_code == 200
    request_events = _request_events(events, "req_ok")
    assert [event["event"] for event in request_events] == ["http_request_started", "http_request_completed"]
    assert request_events[-1]["status"] == "success"
    assert request_events[-1]["status_code"] == 200
    assert request_events[-1]["status_class"] == "2xx"
    assert "error_type" not in request_events[-1]


def test_http_emits_exactly_started_and_completed_with_route_template(tmp_path):
    events: list[dict] = []
    hostile_id = "real-user-id-health-secret-do-not-leak"
    with TestClient(_app(tmp_path, events)) as client:
        response = client.get(
            f"/_test/rejected/{hostile_id}?token=Bearer%20synthetic-token-do-not-leak",
            headers={"X-Request-ID": "req_http", "Authorization": "Bearer synthetic-token-do-not-leak"},
        )

    request_events = _request_events(events, "req_http")
    assert [event["event"] for event in request_events] == ["http_request_started", "http_request_completed"]
    assert request_events[0] == {
        "event": "http_request_started",
        "request_id": "req_http",
        "http_method": "GET",
        "status": "started",
    }
    assert request_events[1]["route"] == "/_test/rejected/{item_id}"
    assert request_events[1]["status_code"] == 409
    assert request_events[1]["status_class"] == "4xx"
    assert request_events[1]["status"] == "rejected"
    assert request_events[1]["latency_ms"] >= 0
    serialized = json.dumps(request_events)
    for forbidden in (hostile_id, "token", "Authorization", "synthetic-token"):
        assert forbidden not in serialized
    assert response.status_code == 409
    assert response.headers["x-request-id"] == "req_http"


def test_404_uses_unmatched_and_streaming_is_not_buffered(tmp_path):
    events: list[dict] = []
    with TestClient(_app(tmp_path, events)) as client:
        missing = client.get("/missing/private-id", headers={"X-Request-ID": "req_missing"})
        streamed = client.get("/_test/stream/private-id", headers={"X-Request-ID": "req_stream"})

    assert missing.status_code == 404
    assert _request_events(events, "req_missing")[-1]["route"] == "unmatched"
    assert streamed.content == b"firstsecond"
    assert _request_events(events, "req_stream")[-1]["route"] == "/_test/stream/{item_id}"


def test_emitter_failure_does_not_change_response(tmp_path):
    def fail(*_args, **_kwargs):
        raise RuntimeError("health-secret-do-not-leak")

    with TestClient(_app(tmp_path, [], emitter=fail)) as client:
        response = client.get("/health/live", headers={"X-Request-ID": "req_safe"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req_safe"


def test_handled_5xx_emits_error_with_real_status(tmp_path):
    events: list[dict] = []
    with TestClient(_app(tmp_path, events)) as client:
        response = client.get("/_test/handled-5xx", headers={"X-Request-ID": "req_5xx"})

    assert response.status_code == 503
    completed = _request_events(events, "req_5xx")[-1]
    assert completed["status"] == "error"
    assert completed["status_code"] == 503
    assert completed["status_class"] == "5xx"
    assert "error_type" not in completed


def test_unhandled_exception_emits_one_safe_5xx_completion_and_propagates(tmp_path):
    events: list[dict] = []
    app = _app(tmp_path, events)
    with TestClient(app) as client:
        try:
            client.get("/_test/server-error/private-id", headers={"X-Request-ID": "req_error"})
        except RuntimeError:
            pass
        else:
            raise AssertionError("original downstream exception must propagate")

    request_events = _request_events(events, "req_error")
    assert [event["event"] for event in request_events] == ["http_request_started", "http_request_completed"]
    completed = request_events[-1]
    assert completed["route"] == "/_test/server-error/{item_id}"
    assert completed["status_code"] == 500
    assert completed["status_class"] == "5xx"
    assert completed["status"] == "error"
    assert completed["error_type"] == "internal_error"
    serialized = json.dumps(completed)
    for forbidden in ("private-id", "synthetic-token", "/Users/private"):
        assert forbidden not in serialized


def test_streaming_exception_after_response_start_is_error_and_preserves_sent_status(tmp_path):
    events: list[dict] = []
    app = _app(tmp_path, events)

    with TestClient(app) as client:
        with pytest.raises(TimeoutError):
            client.get("/_test/stream-error/private-id", headers={"X-Request-ID": "req_stream_error"})

    request_events = _request_events(events, "req_stream_error")
    assert [event["event"] for event in request_events] == ["http_request_started", "http_request_completed"]
    completed = request_events[-1]
    assert completed["route"] == "/_test/stream-error/{item_id}"
    assert completed["status"] == "error"
    assert completed["status_code"] == 200
    assert completed["status_class"] == "2xx"
    assert completed["error_type"] == "timeout"
    serialized = json.dumps(request_events)
    for forbidden in ("private-id", "synthetic-token", "SELECT", "customer", "/Users/private"):
        assert forbidden not in serialized


def test_emitter_failure_does_not_replace_original_downstream_exception(tmp_path):
    def fail(*_args, **_kwargs):
        raise OSError("emitter failure should be swallowed")

    with TestClient(_app(tmp_path, [], emitter=fail)) as client:
        with pytest.raises(RuntimeError, match="synthetic-token-do-not-leak"):
            client.get("/_test/server-error/private-id", headers={"X-Request-ID": "req_original"})
