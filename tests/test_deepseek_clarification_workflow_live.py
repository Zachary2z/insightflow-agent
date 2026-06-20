import pytest


def test_live_deepseek_clarification_enters_core_workflow_before_sql(tmp_path):
    from graph.workflow import run_workflow
    from llm_ops.deepseek_provider import load_deepseek_config
    from llm_ops.runtime_provider import provider_clarification_router_enabled

    config = load_deepseek_config(require_api_key=True)
    if not config.live_tests_enabled or not config.success or not provider_clarification_router_enabled():
        pytest.skip(
            "Set INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 and "
            "INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER=1 with DEEPSEEK_API_KEY to run this live workflow test."
        )

    result = run_workflow(
        "帮我看看销售情况",
        db_path="data/ecommerce.db",
        trace_dir=tmp_path,
        run_id="run_live_deepseek_clarification",
        session_id="session_live_deepseek_clarification",
    )

    clarification = result["clarification_result"]
    assert result["status"] == "waiting_for_clarification"
    assert clarification["provider_called"] is True
    assert clarification["fallback_used"] is False
    assert clarification["source"] == "provider"
    assert clarification["requires_clarification"] is True
    assert clarification["clarification_questions"]
    assert "generated_sql" not in result
    assert result["execution_result"] == {}

    provider_events = [
        event
        for event in result["trace"]
        if event.get("node") == "clarification_router_agent"
        and event.get("tool_name") == "provider_backed_clarification_router"
    ]
    assert provider_events
    assert provider_events[0]["provider_called"] is True
    assert provider_events[0]["fallback_used"] is False
