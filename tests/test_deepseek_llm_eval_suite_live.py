import pytest


def test_live_deepseek_llm_eval_suite_validates_provider_output():
    from llm_ops.deepseek_provider import DeepSeekProvider, load_deepseek_config
    from llm_ops.eval_smoke import run_llm_smoke_eval

    config = load_deepseek_config(require_api_key=True)
    if not config.live_tests_enabled or not config.success:
        pytest.skip("Set INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 with DEEPSEEK_API_KEY to run this live eval test.")

    result = run_llm_smoke_eval(
        [
            {
                "case_id": "live_question_understanding_schema",
                "prompt_id": "question_understanding",
                "variables": {"user_question": "最近 30 天销售额最高的 5 个商品是什么？"},
                "expected_keys": ["strategy", "intent", "missing_slots", "clarification_questions", "risk_flags"],
                "validate_output": True,
                "expected_success": True,
            }
        ],
        provider=DeepSeekProvider(config),
        model=config.model,
    )

    assert result["success"] is True
    assert result["passed"] == 1
    assert result["cases"][0]["provider_result"]["model"] == config.model
    assert result["cases"][0]["validation_enabled"] is True
