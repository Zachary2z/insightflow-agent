import pytest


def test_live_deepseek_question_understanding_enters_core_workflow(tmp_path):
    from graph.workflow import run_workflow
    from llm_ops.deepseek_provider import load_deepseek_config
    from llm_ops.runtime_provider import provider_question_understanding_enabled

    config = load_deepseek_config(require_api_key=True)
    if not config.live_tests_enabled or not config.success or not provider_question_understanding_enabled():
        pytest.skip(
            "Set INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 and "
            "INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 with DEEPSEEK_API_KEY to run this live workflow test."
        )

    result = run_workflow(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path="data/ecommerce.db",
        trace_dir=tmp_path,
        run_id="run_live_deepseek_question_understanding",
        session_id="session_live_deepseek_question_understanding",
    )

    understanding = result["question_understanding"]
    assert result["status"] == "completed"
    assert understanding["provider_called"] is True
    assert understanding["fallback_used"] is False
    assert understanding["source"] == "provider"
    assert understanding["intent"]["metric"] == "gmv"
    assert understanding["intent"]["dimension"] == "product"
    assert "matched_template" not in understanding
    assert "sql" not in understanding
    assert result["generated_sql"].lower().startswith("select")

    provider_events = [
        event
        for event in result["trace"]
        if event.get("node") == "question_understanding_agent"
        and event.get("tool_name") == "provider_backed_question_understanding"
    ]
    assert provider_events
    assert provider_events[0]["provider_called"] is True
    assert provider_events[0]["fallback_used"] is False
