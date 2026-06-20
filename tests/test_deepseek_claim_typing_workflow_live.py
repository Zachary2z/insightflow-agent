import pytest


def test_live_deepseek_claim_typing_enters_core_workflow(tmp_path):
    from graph.workflow import run_workflow
    from llm_ops.deepseek_provider import load_deepseek_config
    from llm_ops.runtime_provider import provider_claim_typing_enabled

    config = load_deepseek_config(require_api_key=True)
    if not config.live_tests_enabled or not config.success or not provider_claim_typing_enabled():
        pytest.skip(
            "Set INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 and "
            "INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING=1 with DEEPSEEK_API_KEY to run this live workflow test."
        )

    result = run_workflow(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path="data/ecommerce.db",
        trace_dir=tmp_path,
        run_id="run_live_deepseek_claim_typing",
        session_id="session_live_deepseek_claim_typing",
    )

    typing = result["claim_typing_result"]
    assert result["status"] == "completed"
    assert typing["provider_called"] is True
    assert typing["source"] == "provider"
    assert typing["fallback_used"] is False
    assert "evidence_result" in typing
    assert any(
        event.get("node") == "insight_claim_typer_agent"
        and event.get("tool_name") == "provider_insight_claim_typer"
        for event in result["trace"]
    )
