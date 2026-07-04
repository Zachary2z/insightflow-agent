from __future__ import annotations


def _valid_provider_plan() -> dict:
    return {
        "scenario_type": "gmv_decline_diagnosis",
        "analysis_steps": [
            {
                "step_id": "gmv_trend",
                "question": "Compare Cameras GMV over current and previous periods.",
                "required_metrics": ["gmv"],
                "required_dimensions": ["category", "time"],
                "candidate_tables": ["orders", "order_items", "products", "categories"],
            },
            {
                "step_id": "refund_pressure",
                "question": "Check whether Cameras refund rate increased.",
                "required_metrics": ["refund_rate"],
                "required_dimensions": ["category", "time"],
                "candidate_tables": ["refund_requests", "orders", "order_items", "products", "categories"],
            },
        ],
    }


def test_provider_backed_analysis_planner_accepts_valid_structured_output():
    from agents.analysis_planner import plan_analysis
    from llm_ops.provider import MockLLMProvider

    result = plan_analysis(
        "为什么 Cameras 最近 GMV 下滑？",
        provider=MockLLMProvider(_valid_provider_plan()),
    )

    assert result["success"] is True
    assert result["source"] == "provider"
    assert result["scenario_type"] == "gmv_decline_diagnosis"
    assert result["analysis_steps"] == _valid_provider_plan()["analysis_steps"]
    assert result["provider_called"] is True
    assert result["fallback_used"] is False
    assert result["prompt_id"] == "analysis_planner"
    assert result["validation_error"] == ""
    assert result["provider_error"] == ""
    assert "sql" not in result
    assert "final_claims" not in result
    assert "action_payload" not in result


def test_provider_backed_analysis_planner_rejects_sql_final_claims_and_action_payloads():
    from agents.analysis_planner import plan_analysis
    from llm_ops.provider import MockLLMProvider

    invalid_payload = {
        **_valid_provider_plan(),
        "sql": "SELECT * FROM orders LIMIT 10",
        "final_claims": ["Cameras declined because stockout caused it."],
        "action_payload": {"action_type": "create_task", "title": "Restock Cameras"},
    }

    result = plan_analysis(
        "为什么 Cameras 最近 GMV 下滑？",
        provider=MockLLMProvider(invalid_payload),
    )

    assert result["success"] is True
    assert result["source"] == "deterministic"
    assert result["scenario_type"] == "gmv_decline_diagnosis"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["validation_error"]
    assert "sql" not in result
    assert "final_claims" not in result
    assert "action_payload" not in result


def test_provider_backed_analysis_planner_falls_back_on_malformed_json_without_crashing():
    from agents.analysis_planner import plan_analysis
    from llm_ops.provider import MockLLMProvider

    result = plan_analysis(
        "Paid Search GMV 很高但 ROI 变差了吗？",
        provider=MockLLMProvider('{"scenario_type": "marketing_roi_review",'),
    )

    assert result["success"] is True
    assert result["source"] == "deterministic"
    assert result["scenario_type"] == "marketing_roi_review"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["provider_error"]
    assert result["validation_error"] == ""


def test_provider_none_keeps_analysis_planner_no_key_baseline():
    from agents.analysis_planner import plan_analysis

    result = plan_analysis("Cameras 是否存在缺货和库存风险？", provider=None)

    assert result["success"] is True
    assert result["source"] == "deterministic"
    assert result["scenario_type"] == "inventory_risk_analysis"
    assert result["provider_called"] is False
    assert result["fallback_used"] is False
    assert result["prompt_id"] == ""


def test_analysis_planner_agent_accepts_provider_and_traces_fallback_flags():
    from agents.analysis_planner import run_analysis_planner_agent
    from agents.supervisor import initialize_run
    from llm_ops.provider import MockLLMProvider

    state = initialize_run(
        "为什么 Cameras 最近 GMV 下滑？",
        run_id="run_provider_analysis_planner_test",
        session_id="session_provider_analysis_planner_test",
    )

    result = run_analysis_planner_agent(state, provider=MockLLMProvider(_valid_provider_plan()))

    assert result["analysis_plan"]["source"] == "provider"
    assert result["analysis_plan"]["provider_called"] is True
    assert result["analysis_plan"]["fallback_used"] is False
    assert result["analysis_plan"]["prompt_id"] == "analysis_planner"
    assert result["trace"][-1]["node"] == "analysis_planner_agent"
    assert result["trace"][-1]["provider_called"] is True
    assert result["trace"][-1]["fallback_used"] is False
