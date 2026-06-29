from __future__ import annotations


def _valid_provider_payload() -> dict:
    return {
        "strategy": "template",
        "intent": {
            "metric": "gmv",
            "dimension": "category",
            "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近 30 天"},
            "filters": ["paid_orders"],
            "operation": "top_n",
            "limit": 5,
            "risk_flags": [],
        },
        "missing_slots": [],
        "clarification_questions": [],
        "risk_flags": [],
        "reason": "Provider extracted a complete BI intent.",
    }


def _runtime_provider_payload() -> dict:
    payload = _valid_provider_payload()
    payload["intent"] = {
        **payload["intent"],
        "dimension": "product",
    }
    return payload


def test_provider_backed_question_understanding_uses_valid_provider_output():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    result = understand_question_with_provider(
        "最近 30 天销售额最高的 5 个品类是什么？",
        provider=MockLLMProvider(_valid_provider_payload()),
    )

    assert result["success"] is True
    assert result["source"] == "provider"
    assert result["provider_called"] is True
    assert result["fallback_used"] is False
    assert result["strategy"] == "template"
    assert result["intent"] == _valid_provider_payload()["intent"]
    assert result["missing_slots"] == []
    assert result["clarification_questions"] == []
    assert result["risk_flags"] == []
    assert "sql" not in result
    assert "generated_sql" not in result
    assert "matched_template" not in result


def test_provider_backed_question_understanding_falls_back_on_malformed_json():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    result = understand_question_with_provider(
        "最近 30 天销售额最高的 5 个商品是什么？",
        provider=MockLLMProvider('{"strategy": "template", "intent": '),
    )

    assert result["success"] is True
    assert result["source"] == "provider_unavailable"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["provider_error"]
    assert result["strategy"] == "clarify"
    assert result["intent"]["metric"] == ""
    assert result["intent"]["dimension"] == ""
    assert "sql" not in result
    assert "matched_template" not in result


def test_provider_backed_question_understanding_falls_back_on_schema_mismatch():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    invalid_payload = _valid_provider_payload()
    invalid_payload["intent"] = {**invalid_payload["intent"], "limit": "five"}

    result = understand_question_with_provider(
        "最近 30 天销售额最高的 5 个商品是什么？",
        provider=MockLLMProvider(invalid_payload),
    )

    assert result["success"] is True
    assert result["source"] == "provider_unavailable"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["validation_error"]
    assert result["strategy"] == "clarify"
    assert result["intent"]["dimension"] == ""


def test_provider_none_keeps_deterministic_no_key_baseline():
    from question_understanding.provider_backed import understand_question_with_provider

    result = understand_question_with_provider("最近 30 天销售额最高的 5 个商品是什么？", provider=None)

    assert result["success"] is True
    assert result["source"] == "deterministic"
    assert result["provider_called"] is False
    assert result["fallback_used"] is False
    assert result["strategy"] == "template"
    assert result["intent"]["metric"] == "gmv"
    assert result["intent"]["dimension"] == "product"


def test_provider_backed_question_understanding_preserves_unsafe_risk_flags_as_reject():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    payload = _valid_provider_payload()
    payload["strategy"] = "template"
    payload["intent"] = {
        **payload["intent"],
        "risk_flags": ["sensitive_field", "bulk_export"],
    }
    payload["risk_flags"] = ["sensitive_field", "bulk_export"]

    result = understand_question_with_provider(
        "帮我导出所有用户的手机号和邮箱",
        provider=MockLLMProvider(payload),
    )

    assert result["success"] is True
    assert result["source"] == "safety_guard"
    assert result["provider_called"] is False
    assert result["fallback_used"] is False
    assert result["strategy"] == "reject"
    assert result["risk_flags"] == ["sensitive_field", "bulk_export"]
    assert result["intent"]["risk_flags"] == ["sensitive_field", "bulk_export"]
    assert result["rejection_reason"] == "Request asks for sensitive fields or unsafe data access."


def test_provider_backed_question_understanding_never_returns_sql_or_planning_fields():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    payload = {
        **_valid_provider_payload(),
        "sql": "SELECT * FROM users",
        "generated_sql": "SELECT * FROM users",
        "matched_template": "top_categories_gmv",
    }

    result = understand_question_with_provider(
        "最近 30 天销售额最高的 5 个品类是什么？",
        provider=MockLLMProvider(payload),
    )

    assert result["source"] == "provider"
    assert "sql" not in result
    assert "generated_sql" not in result
    assert "matched_template" not in result
    assert "confidence" not in result
    assert "selected_tables" not in result


def test_provider_backed_question_understanding_normalizes_provider_slot_aliases():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    payload = _valid_provider_payload()
    payload["intent"] = {
        **payload["intent"],
        "metric": "sales",
        "dimension": "商品",
        "operation": "最高",
    }

    result = understand_question_with_provider(
        "最近 30 天销售额最高的 5 个商品是什么？",
        provider=MockLLMProvider(payload),
    )

    assert result["source"] == "provider"
    assert result["intent"]["metric"] == "gmv"
    assert result["intent"]["dimension"] == "product"
    assert result["intent"]["operation"] == "top_n"


def test_provider_backed_question_understanding_treats_missing_intent_risk_flags_as_empty():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    payload = _valid_provider_payload()
    payload["intent"] = dict(payload["intent"])
    payload["intent"].pop("risk_flags")

    result = understand_question_with_provider(
        "以这份数据的最近 90 天为周期，收入最高的前 5 个获客渠道分别是谁？",
        provider=MockLLMProvider(payload),
    )

    assert result["source"] == "provider"
    assert result["risk_flags"] == []
    assert result["intent"]["risk_flags"] == []


def test_provider_backed_question_understanding_accepts_live_multi_metric_shape():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    payload = _valid_provider_payload()
    payload["strategy"] = "llm_candidate"
    payload["intent"] = {
        **payload["intent"],
        "metric": ["收入", "投放成本", "ROI"],
        "dimension": "渠道",
        "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"},
        "operation": "比较",
        "limit": None,
    }

    result = understand_question_with_provider(
        "分析最近 90 天各渠道收入、投放成本和 ROI，告诉我哪个渠道应该加预算，并生成图表。",
        provider=MockLLMProvider(payload),
    )

    assert result["source"] == "provider"
    assert result["fallback_used"] is False
    assert result["strategy"] == "llm_candidate"
    assert result["intent"]["metric"] == "收入, 投放成本, ROI"
    assert result["intent"]["dimension"] == "channel"
    assert result["intent"]["operation"] == "comparison"
    assert result["missing_slots"] == []


def test_provider_backed_question_understanding_includes_workspace_context_in_prompt():
    from question_understanding.provider_backed import understand_question_with_provider

    captured = {}

    class CapturingProvider:
        model = "mock-free"

        def generate(self, request):
            captured["prompt"] = request.prompt
            return _valid_provider_payload()

    result = understand_question_with_provider(
        "以这份数据的最近 90 天为周期，收入最高的前 5 个获客渠道分别是谁？",
        provider=CapturingProvider(),
        workspace_context={
            "workspace_data_source_selected": True,
            "guidance": ["Use the current workspace analysis database; do not ask for a data source."],
            "tables": [{"table_name": "orders", "columns": [{"name": "order_date", "value_range": {"max": "2025-12-26"}}]}],
        },
    )

    assert result["source"] == "provider"
    assert "Workspace context" in captured["prompt"]
    assert "current workspace analysis database" in captured["prompt"]
    assert "2025-12-26" in captured["prompt"]


def test_question_understanding_agent_accepts_provider_and_traces_fallback_flags():
    from agents.question_understanding import run_question_understanding_agent
    from agents.supervisor import initialize_run
    from llm_ops.provider import MockLLMProvider

    state = initialize_run(
        "最近 30 天销售额最高的 5 个品类是什么？",
        run_id="run_provider_question_understanding_test",
        session_id="session_provider_question_understanding_test",
    )

    result = run_question_understanding_agent(state, provider=MockLLMProvider(_valid_provider_payload()))

    assert result["question_understanding"]["source"] == "provider"
    assert result["question_understanding"]["provider_called"] is True
    assert result["question_understanding"]["fallback_used"] is False
    assert result["intent_slots"]["dimension"] == "category"
    assert result["routing_strategy"] == "template"
    assert "generated_sql" not in result
    assert result["trace"][-1]["node"] == "question_understanding_agent"
    assert result["trace"][-1]["tool_name"] == "provider_backed_question_understanding"
    assert result["trace"][-1]["provider_called"] is True
    assert result["trace"][-1]["fallback_used"] is False


def test_core_workflow_uses_provider_backed_question_understanding_when_provider_is_supplied(tmp_path):
    from graph.workflow import run_workflow
    from llm_ops.provider import MockLLMProvider

    result = run_workflow(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path="data/ecommerce.db",
        trace_dir=tmp_path,
        run_id="run_provider_runtime_question_understanding",
        session_id="session_provider_runtime_question_understanding",
        question_understanding_provider=MockLLMProvider(_runtime_provider_payload()),
    )

    assert result["status"] == "completed"
    assert result["question_understanding"]["source"] == "provider"
    assert result["question_understanding"]["provider_called"] is True
    assert result["question_understanding"]["fallback_used"] is False
    assert result["intent_slots"]["metric"] == "gmv"
    assert result["routing_strategy"] == "template"

    provider_events = [
        event
        for event in result["trace"]
        if event.get("node") == "question_understanding_agent"
        and event.get("tool_name") == "provider_backed_question_understanding"
    ]
    assert provider_events
    assert provider_events[0]["provider_called"] is True
    assert provider_events[0]["fallback_used"] is False
    assert "generated_sql" in result


def test_core_workflow_env_opt_in_without_api_key_keeps_deterministic_baseline(tmp_path, monkeypatch):
    from graph.workflow import run_workflow

    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    result = run_workflow(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path="data/ecommerce.db",
        trace_dir=tmp_path,
        run_id="run_no_key_runtime_question_understanding",
        session_id="session_no_key_runtime_question_understanding",
    )

    assert result["status"] == "completed"
    assert result["question_understanding"]["strategy"] == "template"
    assert result["intent_slots"]["metric"] == "gmv"
    assert result["routing_strategy"] == "template"
    assert result["question_understanding"].get("source", "deterministic") == "deterministic"
    assert not any(
        event.get("tool_name") == "provider_backed_question_understanding"
        for event in result["trace"]
    )
