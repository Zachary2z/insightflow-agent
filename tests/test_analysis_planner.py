from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def _assert_plan_contract(result: dict, scenario_type: str) -> None:
    assert result["success"] is True
    assert result["scenario_type"] == scenario_type
    assert result["provider_called"] is False
    assert result["fallback_used"] is False
    assert result["prompt_id"] == ""
    assert result["validation_error"] == ""
    assert result["provider_error"] == ""
    assert result["analysis_steps"]
    for step in result["analysis_steps"]:
        assert step["step_id"]
        assert step["question"]
        assert isinstance(step["required_metrics"], list)
        assert isinstance(step["required_dimensions"], list)
        assert isinstance(step["candidate_tables"], list)
        assert step["candidate_tables"]
        assert "sql" not in step
        assert "final_claims" not in step
        assert "action_payload" not in step


def test_deterministic_planner_supports_required_scenario_types():
    from agents.analysis_planner import plan_analysis

    examples = {
        "quick_metric_lookup": "最近 30 天 GMV 是多少？",
        "gmv_decline_diagnosis": "为什么 Cameras 最近 GMV 下滑？",
        "marketing_roi_review": "Paid Search GMV 很高但 ROI 变差了吗？",
        "inventory_risk_analysis": "Cameras 是否存在缺货和库存风险？",
        "refund_anomaly_analysis": "Cameras 退款率为什么异常升高？",
        "promotion_review": "618 促销是否拉低客单价和净 GMV 质量？",
        "customer_segment_analysis": "上海客户分层和转化表现是否异常？",
        "general_non_template_analysis": "帮我从商品质量和履约角度分析近期业务风险",
    }

    for scenario_type, question in examples.items():
        result = plan_analysis(question)
        _assert_plan_contract(result, scenario_type)


def test_deterministic_planner_uses_semantic_metrics_dimensions_and_tables():
    from agents.analysis_planner import plan_analysis

    result = plan_analysis("为什么 Cameras 最近 GMV 下滑？")

    assert result["scenario_type"] == "gmv_decline_diagnosis"
    steps = {step["step_id"]: step for step in result["analysis_steps"]}
    assert {"gmv_trend", "refund_pressure", "inventory_pressure"}.issubset(steps)
    assert steps["gmv_trend"]["required_metrics"] == ["gmv"]
    assert {"category", "time"}.issubset(steps["gmv_trend"]["required_dimensions"])
    assert {"orders", "order_items", "products", "categories"}.issubset(
        steps["gmv_trend"]["candidate_tables"]
    )
    assert "refund_rate" in steps["refund_pressure"]["required_metrics"]
    assert "refund_requests" in steps["refund_pressure"]["candidate_tables"]
    assert "stockout_rate" in steps["inventory_pressure"]["required_metrics"]
    assert "inventory_snapshots" in steps["inventory_pressure"]["candidate_tables"]


def test_analysis_planner_agent_writes_state_and_trace_without_sql():
    from agents.analysis_planner import run_analysis_planner_agent
    from agents.supervisor import initialize_run

    state = initialize_run(
        "为什么 Cameras 最近 GMV 下滑？",
        run_id="run_analysis_planner_agent_test",
        session_id="session_analysis_planner_agent_test",
    )

    result = run_analysis_planner_agent(state)

    assert result["analysis_plan"]["scenario_type"] == "gmv_decline_diagnosis"
    assert result["analysis_steps"] == result["analysis_plan"]["analysis_steps"]
    assert "generated_sql" not in result
    assert result["trace"][-1]["node"] == "analysis_planner_agent"
    assert result["trace"][-1]["tool_name"] == "scenario_analysis_planner"
    assert result["trace"][-1]["provider_called"] is False
    assert result["trace"][-1]["fallback_used"] is False


def test_core_workflow_adds_analysis_planner_trace_without_bypassing_sql_boundaries(tmp_path):
    from graph.workflow import run_workflow

    result = run_workflow(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_analysis_planner_workflow",
        session_id="session_analysis_planner_workflow",
    )

    assert result["status"] == "completed"
    assert result["analysis_plan"]["scenario_type"] == "quick_metric_lookup"
    assert result["review_result"]["approved"] is True
    assert result["execution_result"]["success"] is True
    trace_nodes = [event["node"] for event in result["trace"]]
    assert trace_nodes.index("analysis_planner_agent") < trace_nodes.index("schema_agent")
    assert trace_nodes.index("sql_reviewer_agent") < trace_nodes.index("sql_executor_node")
