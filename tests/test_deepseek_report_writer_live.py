import pytest


def test_live_deepseek_report_writer_enters_report_supervisor(tmp_path):
    from agents.report_supervisor import run_report_supervisor_agent
    from agents.supervisor import initialize_run
    from llm_ops.deepseek_provider import load_deepseek_config
    from llm_ops.runtime_provider import provider_report_writer_enabled

    config = load_deepseek_config(require_api_key=True)
    if not config.live_tests_enabled or not config.success or not provider_report_writer_enabled():
        pytest.skip(
            "Set INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 and "
            "INSIGHTFLOW_USE_PROVIDER_REPORT_WRITER=1 with DEEPSEEK_API_KEY to run this live workflow test."
        )

    state = initialize_run(
        "帮我生成本月电商经营复盘，重点看 GMV 和 Top 商品。",
        run_id="run_live_deepseek_report_writer",
        session_id="session_live_deepseek_report_writer",
    )
    state["db_path"] = "data/ecommerce.db"
    state["trace_dir"] = tmp_path / "traces"

    result = run_report_supervisor_agent(
        state,
        report_dir=tmp_path / "markdown",
        chart_dir=tmp_path / "charts",
    )

    assert result["status"] in {"business_review_report_completed", "business_review_report_completed_with_subtask_errors"}
    assert result["report_writer_result"]["provider_called"] is True
    assert result["report_writer_result"]["source"] == "provider"
    assert result["report_writer_result"]["fallback_used"] is False
    assert result["weekly_report_path"]

    writer_events = [
        event
        for event in result["trace"]
        if event.get("node") == "report_writer_agent" and event.get("tool_name") == "provider_report_writer"
    ]
    assert writer_events
    assert writer_events[0]["provider_called"] is True
