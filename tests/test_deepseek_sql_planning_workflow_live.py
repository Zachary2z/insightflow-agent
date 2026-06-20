import pytest


def test_live_deepseek_sql_planning_and_candidate_enter_core_workflow(tmp_path):
    from graph.workflow import run_workflow
    from llm_ops.deepseek_provider import load_deepseek_config
    from llm_ops.runtime_provider import (
        provider_sql_candidate_enabled,
        provider_sql_planning_enabled,
    )

    config = load_deepseek_config(require_api_key=True)
    if (
        not config.live_tests_enabled
        or not config.success
        or not provider_sql_planning_enabled()
        or not provider_sql_candidate_enabled()
    ):
        pytest.skip(
            "Set INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1, INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1, "
            "and INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 with DEEPSEEK_API_KEY to run this live workflow test."
        )

    result = run_workflow(
        "本月各城市客单价对比",
        db_path="data/ecommerce.db",
        trace_dir=tmp_path,
        run_id="run_live_deepseek_sql_planning",
        session_id="session_live_deepseek_sql_planning",
    )

    planning = result["sql_planning"]
    enhancement = result["llm_sql_enhancement"]
    assert result["status"] == "completed"
    assert planning["provider_called"] is True
    assert planning["fallback_used"] is False
    assert planning["source"] == "provider"
    assert "sql" not in planning
    assert "generated_sql" not in planning
    assert enhancement["provider_called"] is True
    assert "run_sql" not in enhancement
    assert result["review_result"]["approved"] is True
    assert result["execution_result"]["success"] is True

    provider_nodes = [
        event
        for event in result["trace"]
        if event.get("node") in {"sql_planning_router_agent", "guarded_sql_candidate_agent"}
    ]
    assert any(event.get("provider_called") is True for event in provider_nodes)
