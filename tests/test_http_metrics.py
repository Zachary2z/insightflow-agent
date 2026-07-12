from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from prometheus_client import CollectorRegistry
from prometheus_client.parser import text_string_to_metric_families

from api.app import create_app


def _samples(text, name):
    return [sample for family in text_string_to_metric_families(text) for sample in family.samples if sample.name == name]


def test_metrics_endpoint_uses_prometheus_content_type_and_excludes_itself(tmp_path):
    app = create_app(metrics_registry=CollectorRegistry())
    with TestClient(app) as client:
        assert client.get("/health/live?private=query-value").status_code == 200
        response = client.get("/metrics")
    assert response.headers["content-type"].startswith("text/plain; version=")
    samples = _samples(response.text, "insightflow_http_requests_total")
    assert any(sample.labels == {"method": "GET", "route": "/health/live", "status_class": "2xx"} for sample in samples)
    assert not any(sample.labels.get("route") == "/metrics" for sample in samples)
    assert "private" not in response.text and "query-value" not in response.text


def test_http_template_status_classes_and_in_progress_cleanup():
    app = create_app(metrics_registry=CollectorRegistry())

    @app.get("/probe/{item_id}")
    def probe(item_id: str):
        if item_id == "bad":
            raise HTTPException(500, "dynamic-sensitive-exception")
        return {"ok": True}

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/probe/id-123").status_code == 200
        assert client.get("/probe/bad").status_code == 500
        text = client.get("/metrics").text
    samples = _samples(text, "insightflow_http_requests_total")
    assert any(s.labels == {"method": "GET", "route": "/probe/{item_id}", "status_class": "2xx"} for s in samples)
    assert any(s.labels == {"method": "GET", "route": "/probe/{item_id}", "status_class": "5xx"} for s in samples)
    gauges = _samples(text, "insightflow_http_requests_in_progress")
    assert all(s.value == 0 for s in gauges)
    assert "id-123" not in text and "dynamic-sensitive-exception" not in text


def test_multiple_apps_are_isolated():
    first = create_app()
    second = create_app()
    with TestClient(first) as client:
        client.get("/health/live")
        assert 'route="/health/live"' in client.get("/metrics").text
    with TestClient(second) as client:
        assert 'route="/health/live"' not in client.get("/metrics").text


def test_broken_metrics_preserve_http_response_request_id_and_log_counts():
    class BrokenMetrics:
        def __getattribute__(self, _name):
            raise RuntimeError("metrics unavailable")

    events = []
    app = create_app(metrics=BrokenMetrics(), event_emitter=lambda event, **fields: events.append((event, fields)))
    with TestClient(app) as client:
        response = client.get("/health/live", headers={"X-Request-ID": "req_metrics_failure"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "insightflow-api"}
    assert response.headers["X-Request-ID"] == "req_metrics_failure"
    assert [name for name, _ in events] == ["http_request_started", "http_request_completed"]


def test_broken_metrics_do_not_replace_original_http_exception():
    class BrokenMetrics:
        def __getattribute__(self, _name):
            raise RuntimeError("metrics unavailable")

    original = RuntimeError("original business exception")
    app = create_app(metrics=BrokenMetrics())

    @app.get("/explode")
    def explode():
        raise original

    with TestClient(app) as client, pytest.raises(RuntimeError) as caught:
        client.get("/explode")
    assert caught.value is original


@pytest.mark.parametrize("method_name", ["inc", "dec"])
def test_in_progress_gauge_failure_preserves_response_and_non_negative_gauge(monkeypatch, method_name):
    metrics = create_app(metrics_registry=CollectorRegistry()).state.metrics
    metrics.register_http_routes(["/health/live"])
    child = metrics.http_in_progress.labels(method="GET", route="/health/live")
    monkeypatch.setattr(child, method_name, lambda: (_ for _ in ()).throw(RuntimeError("gauge failed")))
    app = create_app(metrics=metrics)
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        text = client.get("/metrics").text
    gauges = [s for s in _samples(text, "insightflow_http_requests_in_progress") if s.labels == {"method": "GET", "route": "/health/live"}]
    assert gauges and gauges[0].value == 0
    assert any(s.labels == {"method": "GET", "route": "/health/live", "status_class": "2xx"} for s in _samples(text, "insightflow_http_requests_total"))
