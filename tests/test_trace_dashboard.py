import json
from pathlib import Path


def _write_trace(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_trace_dashboard_summarizes_agent_tool_sql_and_eval_metrics(tmp_path):
    from dashboard.trace_dashboard import build_trace_dashboard

    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    _write_trace(
        trace_dir / "run_success.json",
        {
            "run_id": "run_success",
            "status": "completed",
            "trace": [
                {"node": "schema_agent", "tool_name": "get_database_schema", "latency_ms": 5, "status": "success"},
                {"node": "sql_reviewer_agent", "tool_name": "validate_sql", "latency_ms": 7, "status": "success"},
                {"node": "sql_executor_node", "tool_name": "run_sql", "latency_ms": 11, "status": "success"},
                {"node": "insight_agent", "tool_name": "", "latency_ms": 3, "status": "success"},
            ],
        },
    )
    _write_trace(
        trace_dir / "run_repaired.json",
        {
            "run_id": "run_repaired",
            "status": "completed",
            "trace": [
                {"node": "sql_executor_node", "tool_name": "run_sql", "latency_ms": 14, "status": "error", "error_type": "sql_execution_error"},
                {"node": "error_fix_agent", "tool_name": "", "latency_ms": 2, "status": "success", "retry_count": 1},
                {"node": "sql_executor_node", "tool_name": "run_sql", "latency_ms": 9, "status": "success", "retry_count": 1},
            ],
        },
    )
    _write_trace(
        trace_dir / "run_failed.json",
        {
            "run_id": "run_failed",
            "status": "failed",
            "trace": [
                {"node": "sql_reviewer_agent", "tool_name": "validate_sql", "latency_ms": 4, "status": "error", "error_type": "sql_review_rejected"}
            ],
        },
    )

    dashboard = build_trace_dashboard(
        trace_dir=trace_dir,
        eval_summary={
            "total_cases": 20,
            "passed_cases": 20,
            "failed_cases": 0,
            "pass_rate": 1.0,
            "failure_type_distribution": {"none": 12, "review_rejected": 7, "execution_failed": 1},
        },
    )

    assert dashboard["success"] is True
    assert dashboard["trace_count"] == 3
    assert dashboard["run_status_counts"] == {"completed": 2, "failed": 1}
    assert dashboard["agent_node_latency_ms"]["sql_executor_node"]["count"] == 3
    assert dashboard["agent_node_latency_ms"]["sql_executor_node"]["total"] == 34
    assert dashboard["agent_node_latency_ms"]["sql_executor_node"]["average"] == 11.33
    assert dashboard["tool_call_counts"]["run_sql"] == 3
    assert dashboard["tool_call_counts"]["validate_sql"] == 2
    assert dashboard["sql_execution_latency_ms"] == {"count": 3, "total": 34, "average": 11.33}
    assert dashboard["sql_fix_count"] == 1
    assert dashboard["failure_type_distribution"] == {"none": 12, "review_rejected": 7, "execution_failed": 1}
    assert dashboard["eval_metrics"]["pass_rate"] == 1.0


def test_trace_dashboard_reports_bad_trace_files_without_crashing(tmp_path):
    from dashboard.trace_dashboard import build_trace_dashboard

    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    (trace_dir / "bad.json").write_text("{bad json", encoding="utf-8")

    dashboard = build_trace_dashboard(trace_dir=trace_dir)

    assert dashboard["success"] is True
    assert dashboard["trace_count"] == 0
    assert dashboard["load_errors"][0]["trace_path"].endswith("bad.json")
    assert "Expecting property name" in dashboard["load_errors"][0]["error"]
