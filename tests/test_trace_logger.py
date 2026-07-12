import json
from datetime import datetime
from pathlib import Path

import pytest


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


def test_trace_sink_protocol_and_result_are_injectable(tmp_path):
    from observability.trace_sink import TracePersistRequest, TraceSink, TraceSinkResult
    from tools.trace_logger import save_trace

    class RecordingSink:
        name = "recording"

        def __init__(self):
            self.requests = []

        def persist(self, request):
            self.requests.append(request)
            return TraceSinkResult(
                sink_name=self.name,
                success=True,
                latency_ms=4,
                event_count=request.document.event_count,
            )

    sink = RecordingSink()
    assert isinstance(sink, TraceSink)
    result = save_trace("run_injected", [{"status": "success"}], trace_dir=tmp_path, sink=sink)

    assert result["success"] is True
    assert result["trace_path"] == ""
    assert result["event_count"] == 1
    assert isinstance(sink.requests[0], TracePersistRequest)
    assert sink.requests[0].document.run_id == "run_injected"


def test_local_json_trace_sink_preserves_complete_legacy_contract(tmp_path):
    from observability.trace_sink import LocalJsonTraceSink, TraceDocument, TracePersistRequest

    document = TraceDocument(
        run_id="run_contract",
        session_id="session_contract",
        user_question="敏感问题仍只存在本地 Trace",
        status="completed",
        question_thread={"resolved_question": "本地兼容内容"},
        trace=({"node": "business_answer", "status": "success"},),
        saved_at="2026-07-11T00:00:00Z",
    )
    result = LocalJsonTraceSink(tmp_path).persist(TracePersistRequest(document=document))

    assert result.success is True
    saved = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    assert saved == {
        "run_id": "run_contract",
        "session_id": "session_contract",
        "user_question": "敏感问题仍只存在本地 Trace",
        "status": "completed",
        "question_thread": {"resolved_question": "本地兼容内容"},
        "event_count": 1,
        "trace": [{"node": "business_answer", "status": "success"}],
        "saved_at": "2026-07-11T00:00:00Z",
    }


@pytest.mark.parametrize("run_id", ["../escape", "/tmp/escape", "nested/run", "nested\\run"])
def test_local_json_trace_sink_sanitizes_malicious_run_id_inside_root(tmp_path, run_id):
    from tools.trace_logger import save_trace

    result = save_trace(run_id, [], trace_dir=tmp_path)

    assert result["success"] is True
    path = Path(result["trace_path"])
    assert path.parent.resolve() == tmp_path.resolve()
    assert path.is_file()


def test_local_json_trace_sink_rejects_symlink_root_escape(tmp_path):
    from tools.trace_logger import save_trace

    outside = tmp_path / "outside"
    outside.mkdir()
    linked_root = tmp_path / "linked"
    linked_root.symlink_to(outside, target_is_directory=True)

    result = save_trace("run_symlink", [], trace_dir=linked_root)

    assert result["success"] is False
    assert result["trace_path"] == ""
    assert not (outside / "run_symlink.json").exists()
    assert str(outside) not in result["trace_event"].get("error", "")


def test_local_json_trace_sink_rejects_symlink_parent_escape(tmp_path):
    from tools.trace_logger import save_trace

    outside = tmp_path / "outside"
    outside.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(outside, target_is_directory=True)

    result = save_trace("run_parent_symlink", [], trace_dir=linked_parent / "traces")

    assert result["success"] is False
    assert not (outside / "traces" / "run_parent_symlink.json").exists()


def test_atomic_write_failure_leaves_no_final_or_temporary_trace(tmp_path, monkeypatch):
    import observability.trace_sink as trace_sink
    from tools.trace_logger import save_trace

    def fail_replace(_source, _target):
        raise OSError("Bearer synthetic-token-do-not-leak /Users/private/trace")

    monkeypatch.setattr(trace_sink.os, "replace", fail_replace)
    result = save_trace("run_atomic", [{"status": "success"}], trace_dir=tmp_path)

    assert result["success"] is False
    assert not (tmp_path / "run_atomic.json").exists()
    assert list(tmp_path.glob("*.tmp")) == []
    assert "synthetic-token" not in json.dumps(result["trace_event"])
    assert "/Users/" not in json.dumps(result["trace_event"])


def test_structured_log_trace_sink_emits_only_compact_allowlisted_fields():
    from observability.redaction import OBSERVABILITY_FIELD_ALLOWLIST
    from observability.trace_sink import StructuredLogTraceSink, TraceDocument, TracePersistRequest

    captured = []
    document = TraceDocument(
        run_id="run_safe",
        session_id="session_safe",
        user_question="Prompt token=synthetic-token-do-not-leak",
        status="completed",
        question_thread={"sql": "SELECT secret FROM users"},
        trace=({"tool_input_summary": "Rows /Users/private/file", "provider_payload": {"secret": "x"}},),
        saved_at="2026-07-11T00:00:00Z",
    )

    result = StructuredLogTraceSink(emitter=lambda event, **fields: captured.append((event, fields))).persist(
        TracePersistRequest(document=document)
    )

    assert result.success is True
    assert captured == [
        (
            "trace_persist_completed",
            {
                "run_id": "run_safe",
                "session_id": "session_safe",
                "operation": "trace_persist",
                "status": "success",
                "error_type": None,
                "latency_ms": result.latency_ms,
                "event_count": 1,
            },
        )
    ]
    assert set(captured[0][1]) <= OBSERVABILITY_FIELD_ALLOWLIST
    serialized = json.dumps(captured)
    for forbidden in ("Prompt", "SELECT", "Rows", "provider_payload", "synthetic-token", "/Users/", "trace_path"):
        assert forbidden not in serialized


def test_structured_log_trace_sink_classifies_emitter_failure_without_leaking_message():
    from observability.trace_sink import StructuredLogTraceSink, TraceDocument, TracePersistRequest

    def fail(_event, **_fields):
        raise OSError("SELECT token=synthetic-token-do-not-leak /Users/private/path")

    result = StructuredLogTraceSink(emitter=fail).persist(
        TracePersistRequest(document=TraceDocument(run_id="run_log_fail", trace=(), saved_at="2026-07-11T00:00:00Z"))
    )

    assert result.success is False
    assert result.error_type == "io_error"
    assert "synthetic-token" not in repr(result)
    assert "/Users/" not in repr(result)


def test_composite_trace_sink_isolates_results_and_continues_after_exception():
    from observability.trace_sink import CompositeTraceSink, TraceDocument, TracePersistRequest, TraceSinkResult

    calls = []

    class RaisingSink:
        name = "raising"

        def persist(self, request):
            calls.append(self.name)
            raise RuntimeError("Prompt SELECT secret /Users/private")

    class SuccessfulSink:
        name = "successful"

        def persist(self, request):
            calls.append(self.name)
            return TraceSinkResult(self.name, True, 1, request.document.event_count)

    result = CompositeTraceSink([RaisingSink(), SuccessfulSink()]).persist(
        TracePersistRequest(document=TraceDocument(run_id="run_composite", trace=(), saved_at="2026-07-11T00:00:00Z"))
    )

    assert calls == ["raising", "successful"]
    assert [child.success for child in result.results] == [False, True]
    assert result.results[0].error_type == "internal_error"
    assert "Prompt" not in repr(result)
    assert "/Users/" not in repr(result)


def test_save_trace_uses_local_result_when_auxiliary_sink_fails(tmp_path):
    from observability.trace_sink import CompositeTraceSink, LocalJsonTraceSink, StructuredLogTraceSink
    from tools.trace_logger import save_trace

    def fail(_event, **_fields):
        raise OSError("secret-do-not-leak")

    sink = CompositeTraceSink([LocalJsonTraceSink(tmp_path), StructuredLogTraceSink(emitter=fail)])
    result = save_trace("run_aux_fail", [], trace_dir=tmp_path, sink=sink)

    assert result["success"] is True
    assert Path(result["trace_path"]).is_file()


def test_save_trace_keeps_local_failure_semantics_when_auxiliary_succeeds(tmp_path):
    from observability.trace_sink import CompositeTraceSink, LocalJsonTraceSink, StructuredLogTraceSink
    from tools.trace_logger import save_trace

    blocked = tmp_path / "blocked"
    blocked.write_text("occupied", encoding="utf-8")
    captured = []
    sink = CompositeTraceSink(
        [LocalJsonTraceSink(blocked), StructuredLogTraceSink(emitter=lambda event, **fields: captured.append(fields))]
    )

    result = save_trace("run_local_fail", [], trace_dir=blocked, sink=sink)

    assert result["success"] is False
    assert captured[0]["status"] == "error"
    assert captured[0]["error_type"] == "io_error"


def test_composite_local_and_structured_sinks_both_succeed(tmp_path):
    from observability.trace_sink import CompositeTraceSink, LocalJsonTraceSink, StructuredLogTraceSink
    from tools.trace_logger import save_trace

    captured = []
    sink = CompositeTraceSink(
        [LocalJsonTraceSink(tmp_path), StructuredLogTraceSink(emitter=lambda event, **fields: captured.append(fields))]
    )

    result = save_trace("run_both", [{"status": "success"}], trace_dir=tmp_path, sink=sink)

    assert result["success"] is True
    assert Path(result["trace_path"]).is_file()
    assert captured[0]["event_count"] == 1


def test_nested_composite_preserves_successful_local_compatibility_result(tmp_path):
    from observability.trace_sink import CompositeTraceSink, LocalJsonTraceSink, StructuredLogTraceSink
    from tools.trace_logger import save_trace

    def fail(_event, **_fields):
        raise OSError("auxiliary failure")

    nested = CompositeTraceSink(
        [CompositeTraceSink([LocalJsonTraceSink(tmp_path), StructuredLogTraceSink(emitter=fail)])]
    )

    result = save_trace("run_nested_local", [], trace_dir=tmp_path, sink=nested)

    assert result["success"] is True
    assert Path(result["trace_path"]).is_file()


def test_nested_composite_propagates_outer_local_failure_to_structured_event(tmp_path):
    from observability.trace_sink import CompositeTraceSink, LocalJsonTraceSink, StructuredLogTraceSink
    from tools.trace_logger import save_trace

    blocked = tmp_path / "blocked"
    blocked.write_text("occupied", encoding="utf-8")
    captured = []
    nested = CompositeTraceSink(
        [
            LocalJsonTraceSink(blocked),
            CompositeTraceSink(
                [StructuredLogTraceSink(emitter=lambda event, **fields: captured.append(fields))]
            ),
        ]
    )

    result = save_trace("run_nested_failure", [], trace_dir=blocked, sink=nested)

    assert result["success"] is False
    assert captured[0]["status"] == "error"
    assert captured[0]["error_type"] == "io_error"


def test_unknown_default_sink_configuration_falls_back_to_local(tmp_path, monkeypatch):
    from tools.trace_logger import save_trace

    monkeypatch.setenv("INSIGHTFLOW_TRACE_SINKS", "pkg.DynamicSink")

    result = save_trace("run_safe_default", [], trace_dir=tmp_path)

    assert result["success"] is True
    assert Path(result["trace_path"]).is_file()


def test_save_trace_isolates_an_injected_sink_exception_without_leaking_details(tmp_path):
    from tools.trace_logger import save_trace

    class RaisingSink:
        name = "raising"

        def persist(self, _request):
            raise OSError("SELECT secret token=synthetic-token-do-not-leak /Users/private/path")

    result = save_trace("run_raising", [], trace_dir=tmp_path, sink=RaisingSink())

    assert result["success"] is False
    serialized = json.dumps(result)
    assert "synthetic-token" not in serialized
    assert "SELECT secret" not in serialized
    assert "/Users/" not in serialized


def test_save_trace_node_preserves_answer_and_success_semantics(tmp_path):
    from graph.nodes import save_trace_node

    state = {
        "run_id": "run_node_success",
        "status": "completed",
        "final_answer": "业务答案保持不变",
        "trace": [],
        "trace_dir": tmp_path,
    }

    result = save_trace_node(state)

    assert result["status"] == "completed"
    assert result["final_answer"] == "业务答案保持不变"
    assert result["trace_save_result"]["success"] is True


def test_save_trace_node_preserves_answer_and_existing_failure_semantics(tmp_path):
    from graph.nodes import save_trace_node

    blocked = tmp_path / "blocked"
    blocked.write_text("occupied", encoding="utf-8")
    state = {
        "run_id": "run_node_failure",
        "status": "completed",
        "final_answer": "即使 Trace 失败也保留答案",
        "trace": [],
        "trace_dir": blocked,
    }

    result = save_trace_node(state)

    assert result["status"] == "trace_save_failed"
    assert result["final_answer"] == "即使 Trace 失败也保留答案"
    assert result["trace_save_result"]["success"] is False
