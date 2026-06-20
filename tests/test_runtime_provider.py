def test_question_understanding_provider_flag_parses_opt_in_values():
    from llm_ops.runtime_provider import (
        provider_business_review_planner_enabled,
        provider_clarification_router_enabled,
        provider_question_understanding_enabled,
    )

    assert provider_question_understanding_enabled({}) is False
    assert provider_question_understanding_enabled({"INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING": "0"}) is False
    assert provider_question_understanding_enabled({"INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING": "1"}) is True
    assert provider_question_understanding_enabled({"INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING": "true"}) is True
    assert provider_question_understanding_enabled({"INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING": "yes"}) is True
    assert provider_clarification_router_enabled({}) is False
    assert provider_clarification_router_enabled({"INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER": "0"}) is False
    assert provider_clarification_router_enabled({"INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER": "1"}) is True
    assert provider_clarification_router_enabled({"INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER": "true"}) is True
    assert provider_business_review_planner_enabled({}) is False
    assert provider_business_review_planner_enabled({"INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER": "0"}) is False
    assert provider_business_review_planner_enabled({"INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER": "1"}) is True
    assert provider_business_review_planner_enabled({"INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER": "yes"}) is True


def test_build_question_understanding_provider_preserves_no_key_baseline(tmp_path, monkeypatch):
    from llm_ops.runtime_provider import (
        build_business_review_planner_provider,
        build_clarification_provider,
        build_question_understanding_provider,
    )

    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING", "1")
    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER", "1")
    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    assert build_question_understanding_provider(env_path=tmp_path / "missing.env") is None
    assert build_clarification_provider(env_path=tmp_path / "missing.env") is None
    assert build_business_review_planner_provider(env_path=tmp_path / "missing.env") is None


def test_build_question_understanding_provider_returns_none_when_runtime_flag_disabled(tmp_path, monkeypatch):
    from llm_ops.runtime_provider import (
        build_business_review_planner_provider,
        build_clarification_provider,
        build_question_understanding_provider,
    )

    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING", raising=False)
    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER", raising=False)
    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-not-used")

    assert build_question_understanding_provider(env_path=tmp_path / "missing.env") is None
    assert build_clarification_provider(env_path=tmp_path / "missing.env") is None
    assert build_business_review_planner_provider(env_path=tmp_path / "missing.env") is None
