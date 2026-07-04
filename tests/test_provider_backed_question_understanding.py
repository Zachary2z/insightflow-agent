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


def test_provider_backed_question_understanding_keeps_business_caveats_without_rejecting():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    payload = _valid_provider_payload()
    payload["strategy"] = "llm_candidate"
    payload["intent"] = {
        **payload["intent"],
        "metric": ["销售额", "毛利率", "满意度"],
        "dimension": "门店",
        "operation": "比较",
        "risk_flags": ["数据量有限", "时间窗口覆盖所有数据"],
    }
    payload["risk_flags"] = ["数据量有限", "时间窗口覆盖所有数据"]
    payload["analysis_task"] = {
        "task_type": "compare",
        "dimensions": ["门店"],
        "metrics": ["销售额", "毛利率", "满意度"],
        "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"},
        "filters": [],
        "decision_goal": "找出最值得优先复盘的门店",
        "missing_slots": [],
        "defaults_applied": [],
        "resolved_question": "比较各门店最近90天的销售额、毛利率和满意度",
        "output_language": "zh",
        "confidence": "high",
    }

    result = understand_question_with_provider(
        "比较各门店最近90天的销售额、毛利率和满意度，推荐最值得复盘的门店",
        provider=MockLLMProvider(payload),
    )

    assert result["source"] == "provider"
    assert result["provider_called"] is True
    assert result["strategy"] == "llm_candidate"
    assert result["risk_flags"] == ["数据量有限", "时间窗口覆盖所有数据"]
    assert result["rejection_reason"] == ""


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


def test_provider_backed_question_understanding_keeps_roas_separate_from_roi():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    payload = _valid_provider_payload()
    payload["strategy"] = "llm_candidate"
    payload["intent"] = {
        **payload["intent"],
        "metric": "roas",
        "dimension": "渠道",
        "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"},
        "operation": "排名",
        "limit": None,
    }

    result = understand_question_with_provider(
        "最近90天各渠道 ROAS 最高的是谁？",
        provider=MockLLMProvider(payload),
    )

    assert result["source"] == "provider"
    assert result["intent"]["metric"] == "roas"
    assert result["analysis_task"]["metrics"] == ["ROAS"]
    assert "ROI" not in result["analysis_task"]["metrics"]
    assert result["missing_slots"] == []


def test_provider_backed_question_understanding_normalizes_net_return_aliases():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    for provider_metric in ("net_return", "net ROI", "net_roi", "netroi", "净投放回报率"):
        payload = _valid_provider_payload()
        payload["strategy"] = "llm_candidate"
        payload["intent"] = {
            **payload["intent"],
            "metric": provider_metric,
            "dimension": "渠道",
            "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"},
            "operation": "排名",
            "limit": None,
        }

        result = understand_question_with_provider(
            "最近90天各渠道净投放回报率最高的是谁？",
            provider=MockLLMProvider(payload),
        )

        assert result["source"] == "provider"
        assert result["intent"]["metric"] == "net_return"
        assert result["analysis_task"]["metrics"] == ["净投放回报率"]
        assert "ROI" not in result["analysis_task"]["metrics"]
        assert result["missing_slots"] == []


def test_provider_backed_question_understanding_does_not_double_count_net_roi_question_aliases():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    for provider_metric, question in (
        ("net ROI", "最近90天各渠道 net ROI 最高的是谁？"),
        ("net_roi", "最近90天各渠道 net_roi 最高的是谁？"),
        ("netroi", "最近90天各渠道 netroi 最高的是谁？"),
    ):
        payload = _valid_provider_payload()
        payload["strategy"] = "llm_candidate"
        payload["intent"] = {
            **payload["intent"],
            "metric": provider_metric,
            "dimension": "渠道",
            "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"},
            "operation": "排名",
            "limit": None,
        }

        result = understand_question_with_provider(
            question,
            provider=MockLLMProvider(payload),
        )

        assert result["source"] == "provider"
        assert result["intent"]["metric"] == "net_return"
        assert result["analysis_task"]["metrics"] == ["净投放回报率"]
        assert "ROI" not in result["analysis_task"]["metrics"]
        assert result["missing_slots"] == []


def test_provider_backed_question_understanding_keeps_explicit_net_return_and_roi_metric_string():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    payload = _valid_provider_payload()
    payload["strategy"] = "llm_candidate"
    payload["intent"] = {
        **payload["intent"],
        "metric": "net_return, ROI",
        "dimension": "渠道",
        "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"},
        "operation": "排名",
        "limit": None,
    }

    result = understand_question_with_provider(
        "最近90天各渠道净投放回报率和 ROI 分别最高的是谁？",
        provider=MockLLMProvider(payload),
    )

    assert result["source"] == "provider"
    assert result["analysis_task"]["metrics"] == ["净投放回报率", "ROI"]
    assert result["missing_slots"] == []


def test_provider_backed_question_understanding_keeps_explicit_net_return_roas_and_roi_provider_task():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    payload = _valid_provider_payload()
    payload["strategy"] = "llm_candidate"
    payload["intent"] = {
        **payload["intent"],
        "metric": "net_return",
        "dimension": "渠道",
        "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"},
        "operation": "排名",
        "limit": None,
    }
    payload["analysis_task"] = {
        "task_type": "rank",
        "dimensions": ["渠道"],
        "metrics": ["net_return", "ROAS", "ROI"],
        "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"},
    }

    result = understand_question_with_provider(
        "最近90天各渠道净投放回报率、ROAS 和 ROI 分别最高的是谁？",
        provider=MockLLMProvider(payload),
    )

    assert result["source"] == "provider"
    assert result["analysis_task"]["metrics"] == ["净投放回报率", "ROAS", "ROI"]
    assert result["missing_slots"] == []


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


def test_provider_backed_question_understanding_normalizes_analysis_task_defaults_and_language():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    payload = _valid_provider_payload()
    payload["strategy"] = "llm_candidate"
    payload["intent"] = {
        "metric": "Sales Amount",
        "dimension": "Store Name",
        "time_range": {"type": "last_n_days", "value": 90, "raw_text": "last 90 days"},
        "filters": None,
        "operation": "comparison",
        "limit": None,
        "risk_flags": None,
    }
    payload["analysis_task"] = {
        "task_type": "compare",
        "dimensions": None,
        "metrics": None,
        "time_range": None,
        "filters": None,
        "decision_goal": None,
        "missing_slots": None,
        "defaults_applied": None,
        "resolved_question": None,
        "output_language": "en",
        "confidence": None,
    }

    result = understand_question_with_provider(
        "Compare Sales Amount by Store Name in last 90 days",
        provider=MockLLMProvider(payload),
        workspace_context={
            "semantic_metrics": [
                {
                    "name": "sum_Sales Amount",
                    "label": "销售额",
                    "field": "store_ops.Sales Amount",
                    "aliases": ["Sales Amount", "sales amount", "销售额"],
                }
            ],
            "semantic_dimensions": [
                {
                    "name": "Store Name",
                    "label": "门店",
                    "field": "store_ops.Store Name",
                    "aliases": ["Store Name", "store name", "门店"],
                }
            ],
        },
    )

    assert result["source"] == "provider"
    assert result["analysis_task"]["metrics"] == ["销售额"]
    assert result["analysis_task"]["dimensions"] == ["门店"]
    assert result["analysis_task"]["filters"] == []
    assert result["analysis_task"]["missing_slots"] == []
    assert result["analysis_task"]["defaults_applied"] == []
    assert result["analysis_task"]["resolved_question"] == "Compare Sales Amount by Store Name in last 90 days"
    assert result["analysis_task"]["output_language"] == "zh"
    assert result["analysis_task"]["confidence"] == "high"


def test_provider_backed_question_understanding_cannot_bypass_missing_slot_rules():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.provider_backed import understand_question_with_provider

    payload = _valid_provider_payload()
    payload["strategy"] = "llm_candidate"
    payload["intent"] = {
        "metric": "",
        "dimension": "渠道",
        "time_range": None,
        "filters": [],
        "operation": "比较",
        "limit": None,
        "risk_flags": [],
    }
    payload["missing_slots"] = []
    payload["clarification_questions"] = []

    result = understand_question_with_provider(
        "帮我分析渠道表现，看看哪个渠道该加预算",
        provider=MockLLMProvider(payload),
    )

    assert result["source"] == "provider"
    assert result["strategy"] == "clarify"
    assert set(result["missing_slots"]) == {"metric", "time_range"}
    assert result["analysis_task"]["task_type"] == "recommendation"
    assert result["analysis_task"]["dimensions"] == ["渠道"]
    assert result["analysis_task"]["metrics"] == []
    assert set(result["analysis_task"]["missing_slots"]) == {"metric", "time_range"}
    assert result["clarification_questions"] == ["请补充要分析的指标和时间范围，例如：最近90天看销售额。"]


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
