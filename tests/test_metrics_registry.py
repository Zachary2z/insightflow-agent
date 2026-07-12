from prometheus_client import CollectorRegistry
from prometheus_client.parser import text_string_to_metric_families

from observability.metrics import InsightFlowMetrics, create_metrics


def test_independent_registries_can_repeat_without_duplicate_registration():
    first = create_metrics(CollectorRegistry())
    second = create_metrics(CollectorRegistry())
    first.inc(first.runs, {"route": "fast", "status": "success"})

    assert b'insightflow_runs_total{route="fast",status="success"} 1.0' in first.exposition()
    assert b'insightflow_runs_total{route="fast",status="success"}' not in second.exposition()
    assert list(text_string_to_metric_families(first.exposition().decode()))


def test_recording_failure_is_isolated(monkeypatch):
    metrics = InsightFlowMetrics(CollectorRegistry())
    child = metrics.runs.labels(route="fast", status="success")

    monkeypatch.setattr(child, "inc", lambda *_: (_ for _ in ()).throw(RuntimeError("sensitive failure")))
    metrics.inc(metrics.runs, {"route": "fast", "status": "success"})


def test_exposition_contains_every_stable_metric_family():
    text = InsightFlowMetrics(CollectorRegistry()).exposition().decode()
    expected = {
        "insightflow_http_requests", "insightflow_http_request_duration_seconds",
        "insightflow_http_requests_in_progress", "insightflow_runs",
        "insightflow_run_duration_seconds", "insightflow_node_executions",
        "insightflow_node_duration_seconds", "insightflow_clarifications",
        "insightflow_retries", "insightflow_llm_requests", "insightflow_llm_duration_seconds",
        "insightflow_llm_tokens", "insightflow_llm_fallbacks", "insightflow_sql_validations",
        "insightflow_sql_executions", "insightflow_sql_duration_seconds",
        "insightflow_evidence_validations", "insightflow_evidence_tasks",
        "insightflow_chart_generations", "insightflow_report_generations",
        "insightflow_document_exports", "insightflow_external_publishes",
        "insightflow_external_publish_duration_seconds",
        "insightflow_runtime_storage_usage_ratio",
    }
    assert expected <= {family.name for family in text_string_to_metric_families(text)}
