import pytest


def test_live_deepseek_provider_smoke_is_explicitly_opted_in():
    from llm_ops.deepseek_provider import DeepSeekProvider, load_deepseek_config
    from llm_ops.provider import LLMRequest
    from llm_ops.structured_output import run_validated_llm_request

    config = load_deepseek_config(require_api_key=True)
    if not config.live_tests_enabled or not config.success:
        pytest.skip("Set INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 with DEEPSEEK_API_KEY to run this live smoke test.")

    result = run_validated_llm_request(
        DeepSeekProvider(config),
        LLMRequest(
            prompt='Return exactly this JSON: {"claims": ["DeepSeek live smoke OK"]}',
            prompt_id="guarded_insight_claims",
            prompt_version="v1",
            model=config.model,
            metadata={"node": "deepseek_live_smoke"},
        ),
    )

    assert result["success"] is True
    assert result["content"]["claims"]
    assert result["trace_event"]["model"] == config.model
