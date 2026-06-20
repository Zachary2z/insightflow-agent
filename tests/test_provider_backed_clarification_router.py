from __future__ import annotations

from pathlib import Path


def _clarification_payload() -> dict:
    return {
        "requires_clarification": True,
        "missing_slots": ["dimension", "time_range"],
        "clarification_questions": [
            "你想按商品、品类、城市还是用户维度看销售情况？",
            "时间范围是最近 30 天、本周、本月，还是自定义时间？",
        ],
        "risk_flags": [],
        "reason": "Need dimension and time range before SQL generation.",
    }


def test_provider_backed_clarification_uses_valid_provider_output():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.router import understand_question
    from question_understanding.clarification import clarify_with_provider

    understanding = understand_question("帮我看看销售情况")
    result = clarify_with_provider(
        "帮我看看销售情况",
        understanding,
        provider=MockLLMProvider(_clarification_payload()),
    )

    assert result["success"] is True
    assert result["source"] == "provider"
    assert result["provider_called"] is True
    assert result["fallback_used"] is False
    assert result["requires_clarification"] is True
    assert result["missing_slots"] == ["dimension", "time_range"]
    assert result["clarification_questions"] == _clarification_payload()["clarification_questions"]
    assert "sql" not in result
    assert "generated_sql" not in result
    assert "matched_template" not in result


def test_provider_backed_clarification_falls_back_on_malformed_json():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.router import understand_question
    from question_understanding.clarification import clarify_with_provider

    understanding = understand_question("帮我看看销售情况")
    result = clarify_with_provider(
        "帮我看看销售情况",
        understanding,
        provider=MockLLMProvider('{"clarification_questions": ['),
    )

    assert result["success"] is True
    assert result["source"] == "deterministic"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["provider_error"]
    assert result["missing_slots"] == ["dimension", "time_range"]
    assert result["clarification_questions"] == understanding["clarification_questions"]


def test_provider_backed_clarification_falls_back_on_schema_mismatch():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.router import understand_question
    from question_understanding.clarification import clarify_with_provider

    understanding = understand_question("帮我看看销售情况")
    result = clarify_with_provider(
        "帮我看看销售情况",
        understanding,
        provider=MockLLMProvider({"clarification_questions": "请选择时间"}),
    )

    assert result["success"] is True
    assert result["source"] == "deterministic"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["validation_error"]
    assert result["clarification_questions"] == understanding["clarification_questions"]


def test_clarification_none_keeps_deterministic_baseline():
    from question_understanding.router import understand_question
    from question_understanding.clarification import clarify_with_provider

    understanding = understand_question("帮我看看销售情况")
    result = clarify_with_provider("帮我看看销售情况", understanding, provider=None)

    assert result["success"] is True
    assert result["source"] == "deterministic"
    assert result["provider_called"] is False
    assert result["fallback_used"] is False
    assert result["missing_slots"] == ["dimension", "time_range"]
    assert result["clarification_questions"] == understanding["clarification_questions"]


def test_core_workflow_stops_for_provider_backed_clarification_before_sql(tmp_path):
    from graph.workflow import run_workflow
    from llm_ops.provider import MockLLMProvider

    result = run_workflow(
        "帮我看看销售情况",
        db_path="data/ecommerce.db",
        trace_dir=tmp_path,
        run_id="run_provider_clarification_runtime",
        session_id="session_provider_clarification_runtime",
        clarification_provider=MockLLMProvider(_clarification_payload()),
    )

    assert result["status"] == "waiting_for_clarification"
    assert result["clarification_result"]["source"] == "provider"
    assert result["clarification_result"]["provider_called"] is True
    assert result["clarification_result"]["fallback_used"] is False
    assert result["clarification_questions"] == _clarification_payload()["clarification_questions"]
    assert "generated_sql" not in result
    assert result["execution_result"] == {}
    trace_nodes = [event["node"] for event in result["trace"]]
    assert "clarification_router_agent" in trace_nodes
    assert "schema_agent" not in trace_nodes
    assert "sql_generator_agent" not in trace_nodes
    assert result["trace"][-1]["node"] == "early_response_node"
    assert Path(result["trace_path"]).is_file()


def test_core_workflow_clarification_no_key_baseline_preserves_sql_workflow(tmp_path, monkeypatch):
    from graph.workflow import run_workflow

    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    result = run_workflow(
        "帮我看看销售情况",
        db_path="data/ecommerce.db",
        trace_dir=tmp_path,
        run_id="run_no_key_clarification_runtime",
        session_id="session_no_key_clarification_runtime",
    )

    assert result["status"] == "completed"
    assert result["clarification_result"]["source"] == "deterministic"
    assert result["clarification_result"]["provider_called"] is False
    assert result["clarification_questions"]
    assert result["generated_sql"].lower().startswith("select")
    assert result["execution_result"]["success"] is True
    assert [event["node"] for event in result["trace"]].count("clarification_router_agent") == 1


def test_core_workflow_rejects_unsafe_question_before_sql_generation(tmp_path):
    from graph.workflow import run_workflow

    result = run_workflow(
        "帮我导出所有用户的手机号和邮箱",
        db_path="data/ecommerce.db",
        trace_dir=tmp_path,
        run_id="run_reject_before_sql",
        session_id="session_reject_before_sql",
    )

    assert result["status"] == "failed"
    assert result["routing_strategy"] == "reject"
    assert "sensitive_field" in result["question_understanding"]["risk_flags"]
    assert "generated_sql" not in result
    trace_nodes = [event["node"] for event in result["trace"]]
    assert "schema_agent" not in trace_nodes
    assert "sql_generator_agent" not in trace_nodes
