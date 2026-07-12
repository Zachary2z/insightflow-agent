from pathlib import Path

from prometheus_client import CollectorRegistry
from prometheus_client.parser import text_string_to_metric_families

from api.app import _record_delivery_metric
from agents.visualization_agent import run_visualization_agent
from llm_ops.provider import LLMRequest, MockLLMProvider, run_llm_request
from llm_ops.structured_output import run_validated_llm_request
from observability.metrics import InsightFlowMetrics, metrics_scope
from tools.evidence_tool import validate_evidence
from tools.sql_executor import run_sql
from tools.sql_validator import validate_sql


def _labels(text, sample_name):
    return [s.labels for f in text_string_to_metric_families(text) for s in f.samples if s.name == sample_name]


def test_llm_sql_and_evidence_metrics_cover_success_and_failure(tmp_path):
    metrics = InsightFlowMetrics(CollectorRegistry())
    db = tmp_path / "safe.sqlite"
    import sqlite3
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE facts (value INTEGER)")
        connection.execute("INSERT INTO facts VALUES (7)")
    with metrics_scope(metrics):
        run_llm_request(
            MockLLMProvider({"answer": "ok", "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5}}),
            LLMRequest("prompt-secret", "question_understanding", "v1"),
        )
        validate_sql("SELECT value FROM facts", {"tables": [{"table_name": "facts", "columns": [{"name": "value"}]}]})
        validate_sql("DELETE FROM facts", {"tables": [{"table_name": "facts", "columns": [{"name": "value"}]}]})
        run_sql(db, "SELECT value FROM facts")
        run_sql(db, "SELECT missing FROM facts")
        validate_evidence(["value is 7"], {"success": True, "columns": ["value"], "rows": [[7]]})
        validate_evidence([], None)
    text = metrics.exposition().decode()
    assert {"provider": "mock", "operation": "question_understanding", "status": "success"} in _labels(text, "insightflow_llm_requests_total")
    assert {"provider": "mock", "operation": "question_understanding", "token_type": "total"} in _labels(text, "insightflow_llm_tokens_total")
    assert {"status": "success", "risk_level": "low"} in _labels(text, "insightflow_sql_validations_total")
    assert {"status": "rejected", "risk_level": "high"} in _labels(text, "insightflow_sql_validations_total")
    assert "prompt-secret" not in text and str(db) not in text and "missing" not in text


def test_llm_timeout_is_normalized():
    class TimeoutProvider:
        model = "dynamic-private-model"
        def generate(self, request):
            raise TimeoutError("bearer private-token")
    metrics = InsightFlowMetrics(CollectorRegistry())
    with metrics_scope(metrics):
        result = run_llm_request(TimeoutProvider(), LLMRequest("private-prompt", "unknown-op", "private-version"))
    assert not result["success"]
    text = metrics.exposition().decode()
    assert {"provider": "other", "operation": "other", "status": "timeout"} in _labels(text, "insightflow_llm_requests_total")
    assert "private-token" not in text and "dynamic-private-model" not in text


def test_schema_failure_records_bounded_fallback_reason():
    metrics = InsightFlowMetrics(CollectorRegistry())
    request = LLMRequest("private-prompt", "question_understanding", "private-version")
    with metrics_scope(metrics):
        result = run_validated_llm_request(MockLLMProvider({"unexpected": "private-value"}), request)
    assert not result["success"]
    text = metrics.exposition().decode()
    assert {"operation": "question_understanding", "reason_category": "schema_error"} in _labels(text, "insightflow_llm_fallbacks_total")
    assert "private-value" not in text


def test_report_export_and_publish_delivery_metrics():
    metrics = InsightFlowMetrics(CollectorRegistry())
    _record_delivery_metric(metrics, "report_generation", "success", 0.1)
    _record_delivery_metric(metrics, "report_generation", "error", 0.1)
    _record_delivery_metric(metrics, "document_export", "success", 0.2)
    _record_delivery_metric(metrics, "document_export", "error", 0.2)
    _record_delivery_metric(metrics, "external_publish", "success", 0.3)
    _record_delivery_metric(metrics, "external_publish", "error", 0.3)
    text = metrics.exposition().decode()
    assert {"status": "success"} in _labels(text, "insightflow_report_generations_total")
    assert {"format": "docx", "status": "error"} in _labels(text, "insightflow_document_exports_total")
    assert {"platform": "feishu", "status": "success"} in _labels(text, "insightflow_external_publishes_total")


def test_broken_metrics_preserve_sql_llm_evidence_chart_and_delivery_results(tmp_path):
    class BrokenMetrics:
        def __getattribute__(self, _name):
            raise RuntimeError("metrics unavailable")

    db = tmp_path / "safe.sqlite"
    import sqlite3
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE facts (value INTEGER)")
        connection.execute("INSERT INTO facts VALUES (7)")
    schema = {"tables": [{"table_name": "facts", "columns": [{"name": "value"}]}]}

    baseline_validation = validate_sql("SELECT value FROM facts", schema)
    baseline_sql = run_sql(db, "SELECT value FROM facts")
    baseline_llm = run_llm_request(MockLLMProvider({"answer": "ok"}), LLMRequest("prompt", "question_understanding", "v1"))
    baseline_evidence = validate_evidence(["value is 7"], {"success": True, "columns": ["value"], "rows": [[7]]})
    chart_state = {"execution_result": {"success": False}}
    baseline_chart = run_visualization_agent(chart_state)

    with metrics_scope(BrokenMetrics()):
        failed_metrics_validation = validate_sql("SELECT value FROM facts", schema)
        failed_metrics_sql = run_sql(db, "SELECT value FROM facts")
        failed_metrics_llm = run_llm_request(MockLLMProvider({"answer": "ok"}), LLMRequest("prompt", "question_understanding", "v1"))
        failed_metrics_evidence = validate_evidence(["value is 7"], {"success": True, "columns": ["value"], "rows": [[7]]})
        assert run_visualization_agent(chart_state) == baseline_chart
        _record_delivery_metric(BrokenMetrics(), "report_generation", "success", 0.1)
        _record_delivery_metric(BrokenMetrics(), "document_export", "success", 0.1)
        _record_delivery_metric(BrokenMetrics(), "external_publish", "success", 0.1)
    assert {k: v for k, v in failed_metrics_validation.items() if k != "trace_event"} == {k: v for k, v in baseline_validation.items() if k != "trace_event"}
    assert {k: v for k, v in failed_metrics_sql.items() if k not in {"execution_time_ms", "trace_event"}} == {k: v for k, v in baseline_sql.items() if k not in {"execution_time_ms", "trace_event"}}
    assert {k: v for k, v in failed_metrics_llm.items() if k not in {"latency_ms", "trace_event"}} == {k: v for k, v in baseline_llm.items() if k not in {"latency_ms", "trace_event"}}
    assert {k: v for k, v in failed_metrics_evidence.items() if k != "trace_event"} == {k: v for k, v in baseline_evidence.items() if k != "trace_event"}
