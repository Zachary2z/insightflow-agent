from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.app import create_app
from api.health import ReadinessChecker, ReadinessPaths
from observability.context import get_correlation_context
from observability.middleware import CorrelationMiddleware, select_request_id
from workspaces.store import WorkspaceStore


def _app(tmp_path: Path):
    store = WorkspaceStore(tmp_path / "workspaces")
    checker = ReadinessChecker(
        ReadinessPaths(
            workspace_root=store.root_dir,
            report_root=tmp_path / "reports",
            trace_root=tmp_path / "logs" / "traces",
        )
    )
    app = create_app(workspace_store=store, readiness_checker=checker)

    @app.get("/_test/context")
    def read_context():
        return get_correlation_context()

    @app.get("/_test/business-4xx")
    def business_failure():
        raise HTTPException(status_code=409, detail="conflict")

    return app


def _assert_generated(request_id: str) -> None:
    assert request_id.startswith("req_")
    assert 1 <= len(request_id) <= 64
    assert request_id.replace("_", "").isalnum()


def test_missing_request_id_is_generated_and_not_added_to_body(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        response = client.get("/health/live")
    _assert_generated(response.headers["x-request-id"])
    assert response.json() == {"status": "ok", "service": "insightflow-api"}


def test_safe_client_request_id_is_preserved(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        response = client.get("/health/live", headers={"X-Request-ID": "client.safe_ID-1"})
    assert response.headers["x-request-id"] == "client.safe_ID-1"


@pytest.mark.parametrize(
    "candidate",
    [
        "has space",
        "../private/path",
        "SELECT-from-users",
        "<script>alert</script>",
        "line\nbreak",
        "sk-synthetic-do-not-leak",
        "x" * 65,
        "",
    ],
)
def test_unsafe_client_request_ids_are_replaced(candidate):
    selected = select_request_id(candidate)
    _assert_generated(selected)
    assert selected != candidate


@pytest.mark.parametrize(
    "candidate",
    [
        "has space",
        "../private/path",
        "SELECT-from-users",
        "<script>",
        "sk-synthetic-do-not-leak",
        "x" * 65,
    ],
)
def test_unsafe_http_request_ids_are_not_reflected(tmp_path, candidate):
    with TestClient(_app(tmp_path)) as client:
        response = client.get("/health/live", headers={"X-Request-ID": candidate})
    _assert_generated(response.headers["x-request-id"])
    assert response.headers["x-request-id"] != candidate


def test_health_ready_workspace_openapi_404_and_business_4xx_have_header(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        responses = [
            client.get("/health/ready"),
            client.post("/api/workspaces", json={"name": "Correlation"}),
            client.get("/openapi.json"),
            client.get("/missing"),
            client.get("/_test/business-4xx"),
        ]
    assert [response.status_code for response in responses] == [200, 200, 200, 404, 409]
    for response in responses:
        _assert_generated(response.headers["x-request-id"])
        assert "request_id" not in response.json()


def test_correlation_middleware_wraps_cors_preflight(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        response = client.options(
            "/health/live",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "X-Request-ID": "req_preflight",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["x-request-id"] == "req_preflight"


def test_consecutive_generated_request_ids_are_distinct(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        first = client.get("/health/live").headers["x-request-id"]
        second = client.get("/health/live").headers["x-request-id"]
    assert first != second


def test_request_context_is_visible_downstream_and_reset_after_response(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        response = client.get("/_test/context", headers={"X-Request-ID": "req_visible"})
        assert response.json() == {"request_id": "req_visible"}
        assert get_correlation_context() == {}
    assert get_correlation_context() == {}


def test_concurrent_requests_do_not_share_request_ids(tmp_path):
    app = _app(tmp_path)

    def request(request_id: str) -> tuple[str, str]:
        with TestClient(app) as client:
            response = client.get("/_test/context", headers={"X-Request-ID": request_id})
            return response.headers["x-request-id"], response.json()["request_id"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(request, ["req_parallel_a", "req_parallel_b"]))
    assert results == [
        ("req_parallel_a", "req_parallel_a"),
        ("req_parallel_b", "req_parallel_b"),
    ]
    assert get_correlation_context() == {}


def test_middleware_resets_context_when_downstream_raises():
    async def failing_app(scope, receive, send):
        assert get_correlation_context() == {"request_id": "req_failure"}
        raise RuntimeError("synthetic downstream failure")

    async def exercise():
        middleware = CorrelationMiddleware(failing_app)

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(_message):
            return None

        with pytest.raises(RuntimeError):
            await middleware(
                {
                    "type": "http",
                    "method": "GET",
                    "path": "/failure",
                    "headers": [(b"x-request-id", b"req_failure")],
                },
                receive,
                send,
            )

    asyncio.run(exercise())
    assert get_correlation_context() == {}
