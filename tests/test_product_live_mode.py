def test_product_live_mode_enables_product_safe_provider_flags(monkeypatch):
    from llm_ops.runtime_provider import (
        product_live_mode_enabled,
        provider_clarification_router_enabled,
        provider_business_answer_enabled,
        provider_question_understanding_enabled,
        provider_sql_candidate_enabled,
        provider_sql_planning_enabled,
        provider_visualization_agent_enabled,
    )

    env = {"INSIGHTFLOW_PRODUCT_LIVE_MODE": "1"}

    assert product_live_mode_enabled(env) is True
    assert provider_question_understanding_enabled(env) is True
    assert provider_clarification_router_enabled(env) is True
    assert provider_sql_planning_enabled(env) is True
    assert provider_sql_candidate_enabled(env) is True
    assert provider_business_answer_enabled(env) is True
    assert provider_visualization_agent_enabled(env) is True


def test_product_live_mode_preserves_explicit_provider_flags():
    from llm_ops.runtime_provider import provider_business_answer_enabled

    assert provider_business_answer_enabled({"INSIGHTFLOW_USE_PROVIDER_BUSINESS_ANSWER": "1"}) is True
    assert (
        provider_business_answer_enabled(
            {
                "INSIGHTFLOW_PRODUCT_LIVE_MODE": "0",
                "INSIGHTFLOW_USE_PROVIDER_BUSINESS_ANSWER": "1",
            }
        )
        is True
    )


def test_product_live_no_key_mode_returns_none_without_error(tmp_path, monkeypatch):
    from llm_ops.runtime_provider import build_business_answer_provider

    monkeypatch.setenv("INSIGHTFLOW_PRODUCT_LIVE_MODE", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    assert build_business_answer_provider(env_path=tmp_path / "missing.env") is None
