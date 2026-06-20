import pytest


def test_live_deepseek_business_review_planner_enters_report_supervisor(tmp_path):
    from agents.report_supervisor import run_report_supervisor_agent
    from agents.supervisor import initialize_run
    from llm_ops.deepseek_provider import load_deepseek_config
    from llm_ops.runtime_provider import provider_business_review_planner_enabled

    config = load_deepseek_config(require_api_key=True)
    if not config.live_tests_enabled or not config.success or not provider_business_review_planner_enabled():
        pytest.skip(
            "Set INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 and "
            "INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER=1 with DEEPSEEK_API_KEY to run this live workflow test."
        )

    state = initialize_run(
        "帮我生成本月电商经营复盘，重点看 GMV、Top 商品和下月建议。",
        run_id="run_live_deepseek_business_review_planner",
        session_id="session_live_deepseek_business_review_planner",
    )
    state["db_path"] = "data/ecommerce.db"
    state["trace_dir"] = tmp_path / "traces"

    result = run_report_supervisor_agent(
        state,
        report_dir=tmp_path / "markdown",
        chart_dir=tmp_path / "charts",
    )

    assert result["status"] in {"business_review_report_completed", "business_review_report_completed_with_subtask_errors"}
    assert result["report_plan"]["provider_called"] is True
    assert result["report_plan"]["source"] == "provider"
    assert result["report_plan"]["fallback_used"] is False
    assert result["report_sections"]
    assert all(section["sql"].lower().startswith("select") for section in result["report_sections"])
    assert result["weekly_report_path"]

    planner_events = [
        event
        for event in result["trace"]
        if event.get("node") == "report_planner_agent"
        and event.get("tool_name") == "provider_business_review_planner"
    ]
    assert planner_events
    assert planner_events[0]["provider_called"] is True
