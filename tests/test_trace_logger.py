import json
from datetime import datetime


def test_append_trace_adds_run_context_and_required_fields_without_mutating_state():
    from tools.trace_logger import append_trace

    state = {
        "run_id": "run_001",
        "session_id": "session_001",
        "user_question": "最近 30 天销售额最高的 5 个商品是什么？",
        "trace": [],
    }
    event = {
        "node": "sql_executor",
        "tool_name": "run_sql",
        "tool_input_summary": "SELECT 1",
        "tool_output_summary": "1 row returned",
        "status": "success",
        "latency_ms": 12,
    }

    updated = append_trace(state, event)

    assert updated is not state
    assert state["trace"] == []
    assert len(updated["trace"]) == 1

    trace_event = updated["trace"][0]
    assert trace_event["run_id"] == "run_001"
    assert trace_event["session_id"] == "session_001"
    assert trace_event["node"] == "sql_executor"
    assert trace_event["tool_name"] == "run_sql"
    assert trace_event["tool_input_summary"] == "SELECT 1"
    assert trace_event["tool_output_summary"] == "1 row returned"
    assert trace_event["status"] == "success"
    assert trace_event["latency_ms"] == 12
    assert trace_event["error_type"] is None
    assert trace_event["retry_count"] == 0
    assert datetime.fromisoformat(trace_event["timestamp"].replace("Z", "+00:00"))


def test_append_trace_preserves_failure_and_retry_details():
    from tools.trace_logger import append_trace

    state = {"run_id": "run_fix", "session_id": "session_fix", "trace": []}
    event = {
        "node": "error_fix_agent",
        "tool_name": "run_sql",
        "tool_input_summary": "SELECT oi.price FROM order_items oi",
        "tool_output_summary": "no such column: oi.price",
        "status": "error",
        "latency_ms": 5,
        "error_type": "sql_execution_error",
        "retry_count": 1,
    }

    updated = append_trace(state, event)

    trace_event = updated["trace"][0]
    assert trace_event["status"] == "error"
    assert trace_event["error_type"] == "sql_execution_error"
    assert trace_event["retry_count"] == 1


def test_save_trace_writes_complete_trace_json(tmp_path):
    from tools.trace_logger import save_trace

    trace = [
        {
            "run_id": "run_001",
            "session_id": "session_001",
            "node": "schema_agent",
            "tool_name": "get_database_schema",
            "tool_input_summary": "db_path=data/ecommerce.db",
            "tool_output_summary": "5 tables loaded",
            "status": "success",
            "latency_ms": 10,
            "error_type": None,
            "retry_count": 0,
            "timestamp": "2026-06-19T00:00:00Z",
        }
    ]

    result = save_trace("run_001", trace, trace_dir=tmp_path, session_id="session_001", status="success")

    assert result["success"] is True
    assert result["run_id"] == "run_001"
    assert result["event_count"] == 1
    assert result["trace_path"].endswith("run_001.json")

    saved = json.loads((tmp_path / "run_001.json").read_text(encoding="utf-8"))
    assert saved["run_id"] == "run_001"
    assert saved["session_id"] == "session_001"
    assert saved["status"] == "success"
    assert saved["event_count"] == 1
    assert saved["trace"] == trace


def test_save_trace_returns_structured_error_when_write_fails(tmp_path):
    from tools.trace_logger import save_trace

    blocked_path = tmp_path / "not_a_directory"
    blocked_path.write_text("occupied", encoding="utf-8")

    result = save_trace("run_001", [], trace_dir=blocked_path)

    assert result["success"] is False
    assert result["run_id"] == "run_001"
    assert result["trace_path"] == ""
    assert "Failed to save trace" in result["error"]
    assert result["trace_event"]["status"] == "error"
