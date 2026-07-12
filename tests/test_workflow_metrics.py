import pytest
from prometheus_client import CollectorRegistry
from prometheus_client.parser import text_string_to_metric_families

import graph.workflow as workflow
from graph.workflow import MAX_RETRY_DELTA_PER_NODE, _observed_node
from observability.metrics import InsightFlowMetrics, metrics_scope
from workspaces.analysis_runner import _record_workflow_metric


def _sample(text, name, labels):
    return next(s for f in text_string_to_metric_families(text) for s in f.samples if s.name == name and s.labels == labels)


def test_workflow_routes_and_clarification_are_bounded():
    metrics = InsightFlowMetrics(CollectorRegistry())
    _record_workflow_metric(metrics, {"route": "fast_fact"}, "success", 0.25)
    _record_workflow_metric(metrics, {"route": "malicious-run-id"}, "clarification", 0.5)
    text = metrics.exposition().decode()
    assert _sample(text, "insightflow_runs_total", {"route": "fast", "status": "success"}).value == 1
    assert _sample(text, "insightflow_runs_total", {"route": "unknown", "status": "clarification"}).value == 1


def test_node_success_error_timeout_and_retry_count_once():
    metrics = InsightFlowMetrics(CollectorRegistry())
    with metrics_scope(metrics):
        assert _observed_node("evidence_agent", lambda state: {"retry_count": 1})({"retry_count": 0})
        try:
            _observed_node("business_answer", lambda _: (_ for _ in ()).throw(ValueError("private")))({})
        except ValueError:
            pass
        try:
            _observed_node("save_trace", lambda _: (_ for _ in ()).throw(TimeoutError("private")))({})
        except TimeoutError:
            pass
    text = metrics.exposition().decode()
    assert _sample(text, "insightflow_node_executions_total", {"node": "evidence_agent", "status": "success"}).value == 1
    assert _sample(text, "insightflow_node_executions_total", {"node": "business_answer", "status": "error"}).value == 1
    assert _sample(text, "insightflow_node_executions_total", {"node": "save_trace", "status": "timeout"}).value == 1
    assert "private" not in text


def test_non_integer_retry_does_not_block_business_regression():
    called = False
    expected = {"status": "completed", "value": 7}

    def business(_state):
        nonlocal called
        called = True
        return expected

    result = _observed_node("evidence_agent", business)({"retry_count": "model-produced-value"})
    assert called is True
    assert result is expected


def test_hostile_review_retry_is_never_coerced_or_rendered():
    class Hostile:
        def __int__(self):
            raise AssertionError("__int__ must not run")
        def __str__(self):
            raise AssertionError("__str__ must not run")
        def __repr__(self):
            raise AssertionError("__repr__ must not run")

    expected = {"status": "completed"}
    assert _observed_node("evidence_agent", lambda _: expected)({"review_retry_count": Hostile()}) is expected


def test_hostile_result_retry_and_status_are_fail_safe():
    class Hostile:
        def __int__(self):
            raise AssertionError("__int__ must not run")
        def __str__(self):
            raise AssertionError("__str__ must not run")
        def __repr__(self):
            raise AssertionError("__repr__ must not run")

    metrics = InsightFlowMetrics(CollectorRegistry())
    expected = {"retry_count": "not-an-int", "status": Hostile()}
    with metrics_scope(metrics):
        assert _observed_node("evidence_agent", lambda _: expected)({"retry_count": 0}) is expected
    text = metrics.exposition().decode()
    assert _sample(text, "insightflow_node_executions_total", {"node": "evidence_agent", "status": "unknown"}).value == 1
    assert not any(s.name == "insightflow_retries_total" for f in text_string_to_metric_families(text) for s in f.samples)


def test_get_metrics_failure_does_not_block_business(monkeypatch):
    expected = {"status": "completed"}
    monkeypatch.setattr(workflow, "get_metrics", lambda: (_ for _ in ()).throw(RuntimeError("metrics lookup")))
    assert _observed_node("evidence_agent", lambda _: expected)({}) is expected


@pytest.mark.parametrize("collector_name,method_name", [("node_executions", "inc"), ("node_duration", "observe")])
def test_collector_failure_does_not_change_node_result(monkeypatch, collector_name, method_name):
    metrics = InsightFlowMetrics(CollectorRegistry())
    collector = getattr(metrics, collector_name)
    child = collector.labels(node="evidence_agent", status="success")
    monkeypatch.setattr(child, method_name, lambda *_: (_ for _ in ()).throw(RuntimeError("metrics failed")))
    expected = {"status": "completed"}
    with metrics_scope(metrics):
        assert _observed_node("evidence_agent", lambda _: expected)({}) is expected


def test_metrics_failure_never_replaces_original_business_exception(monkeypatch):
    original = RuntimeError("original business failure")
    monkeypatch.setattr(workflow, "get_metrics", lambda: object())

    def fail(_state):
        raise original

    with pytest.raises(RuntimeError) as caught:
        _observed_node("evidence_agent", fail)({})
    assert caught.value is original


def test_timeout_is_reraised_and_recorded_without_replacement(monkeypatch):
    metrics = InsightFlowMetrics(CollectorRegistry())
    original = TimeoutError("original timeout")

    def fail(_state):
        raise original

    with metrics_scope(metrics), pytest.raises(TimeoutError) as caught:
        _observed_node("save_trace", fail)({})
    assert caught.value is original
    text = metrics.exposition().decode()
    assert _sample(text, "insightflow_node_executions_total", {"node": "save_trace", "status": "timeout"}).value == 1

    monkeypatch.setattr(workflow, "get_metrics", lambda: object())
    with pytest.raises(TimeoutError) as failed_metrics:
        _observed_node("save_trace", fail)({})
    assert failed_metrics.value is original


def test_trace_save_failed_is_error_not_success():
    metrics = InsightFlowMetrics(CollectorRegistry())
    with metrics_scope(metrics):
        result = _observed_node("save_trace", lambda _: {"status": "trace_save_failed"})({})
    assert result == {"status": "trace_save_failed"}
    text = metrics.exposition().decode()
    assert _sample(text, "insightflow_node_executions_total", {"node": "save_trace", "status": "error"}).value == 1
    assert not any(
        s.name == "insightflow_node_executions_total" and s.labels == {"node": "save_trace", "status": "success"}
        for family in text_string_to_metric_families(text)
        for s in family.samples
    )


def test_retry_delta_is_capped_and_uses_fixed_operation():
    metrics = InsightFlowMetrics(CollectorRegistry())
    expected = {"status": "completed", "retry_count": 10**12, "error_type": "sql_execution_error"}
    with metrics_scope(metrics):
        assert _observed_node("evidence_agent", lambda _: expected)({"retry_count": 0}) is expected
    text = metrics.exposition().decode()
    sample = _sample(text, "insightflow_retries_total", {"operation": "sql_execution", "error_type": "execution"})
    assert sample.value == MAX_RETRY_DELTA_PER_NODE


def test_single_retry_increments_once_with_allowlisted_operation():
    metrics = InsightFlowMetrics(CollectorRegistry())
    with metrics_scope(metrics):
        _observed_node("evidence_agent", lambda _: {"status": "completed", "retry_count": 1})({"retry_count": 0})
    text = metrics.exposition().decode()
    assert _sample(text, "insightflow_retries_total", {"operation": "sql_execution", "error_type": "none"}).value == 1
