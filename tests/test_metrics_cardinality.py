from prometheus_client import CollectorRegistry
from prometheus_client.parser import text_string_to_metric_families

from observability.metrics import InsightFlowMetrics


def test_random_sensitive_values_collapse_in_actual_exposition():
    metrics = InsightFlowMetrics(CollectorRegistry())
    secrets = []
    for index in range(250):
        secret = f"secret-{index}-SELECT-star-/private/path-model-{index}"
        secrets.append(secret)
        metrics.inc(metrics.llm_requests, {"provider": secret, "operation": secret, "status": secret})
        metrics.inc(metrics.sql_executions, {"status": secret, "error_type": secret})
        metrics.inc(metrics.chart_generations, {"chart_type": secret, "status": secret})
    text = metrics.exposition().decode()
    samples = [s for f in text_string_to_metric_families(text) for s in f.samples if s.name.endswith("_total")]
    relevant = [s for s in samples if s.name in {"insightflow_llm_requests_total", "insightflow_sql_executions_total", "insightflow_chart_generations_total"}]
    assert len(relevant) == 3
    assert all(secret not in text for secret in secrets)


def test_http_registry_rejects_unregistered_dynamic_paths():
    metrics = InsightFlowMetrics(CollectorRegistry())
    for index in range(100):
        metrics.record_http_completed("GET", f"/users/id-{index}", 200, 0.01)
    text = metrics.exposition().decode()
    samples = [s for f in text_string_to_metric_families(text) for s in f.samples if s.name == "insightflow_http_requests_total"]
    assert len(samples) == 1
    assert samples[0].labels["route"] == "unknown"
    assert "id-99" not in text


def test_hostile_label_objects_are_not_stringified():
    class Hostile:
        def __str__(self):
            raise AssertionError("labels must not stringify business objects")

    metrics = InsightFlowMetrics(CollectorRegistry())
    metrics.inc(metrics.llm_requests, {"provider": Hostile(), "operation": Hostile(), "status": Hostile()})
    text = metrics.exposition().decode()
    assert 'provider="other"' in text
    assert 'operation="other"' in text
    assert 'status="unknown"' in text
