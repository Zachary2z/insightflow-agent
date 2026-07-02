def test_question_understanding_provider_flag_parses_opt_in_values():
    from llm_ops.runtime_provider import (
        provider_answer_reviewer_enabled,
        provider_clarification_router_enabled,
        provider_claim_typing_enabled,
        provider_final_answer_composer_enabled,
        provider_insight_drafting_enabled,
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
    assert provider_claim_typing_enabled({}) is False
    assert provider_claim_typing_enabled({"INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING": "0"}) is False
    assert provider_claim_typing_enabled({"INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING": "1"}) is True
    assert provider_claim_typing_enabled({"INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING": "true"}) is True
    assert provider_insight_drafting_enabled({}) is False
    assert provider_insight_drafting_enabled({"INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING": "0"}) is False
    assert provider_insight_drafting_enabled({"INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING": "1"}) is True
    assert provider_insight_drafting_enabled({"INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING": "on"}) is True
    assert provider_answer_reviewer_enabled({}) is False
    assert provider_answer_reviewer_enabled({"INSIGHTFLOW_USE_PROVIDER_ANSWER_REVIEWER": "0"}) is False
    assert provider_answer_reviewer_enabled({"INSIGHTFLOW_USE_PROVIDER_ANSWER_REVIEWER": "1"}) is True
    assert provider_final_answer_composer_enabled({}) is False
    assert provider_final_answer_composer_enabled({"INSIGHTFLOW_USE_PROVIDER_FINAL_ANSWER_COMPOSER": "0"}) is False
    assert provider_final_answer_composer_enabled({"INSIGHTFLOW_USE_PROVIDER_FINAL_ANSWER_COMPOSER": "on"}) is True


def test_build_question_understanding_provider_preserves_no_key_baseline(tmp_path, monkeypatch):
    from llm_ops.runtime_provider import (
        build_answer_reviewer_provider,
        build_claim_typing_provider,
        build_clarification_provider,
        build_final_answer_composer_provider,
        build_insight_drafting_provider,
        build_question_understanding_provider,
    )

    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING", "1")
    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER", "1")
    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING", "1")
    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING", "1")
    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_ANSWER_REVIEWER", "1")
    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_FINAL_ANSWER_COMPOSER", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    assert build_question_understanding_provider(env_path=tmp_path / "missing.env") is None
    assert build_clarification_provider(env_path=tmp_path / "missing.env") is None
    assert build_claim_typing_provider(env_path=tmp_path / "missing.env") is None
    assert build_insight_drafting_provider(env_path=tmp_path / "missing.env") is None
    assert build_answer_reviewer_provider(env_path=tmp_path / "missing.env") is None
    assert build_final_answer_composer_provider(env_path=tmp_path / "missing.env") is None


def test_build_question_understanding_provider_returns_none_when_runtime_flag_disabled(tmp_path, monkeypatch):
    from llm_ops.runtime_provider import (
        build_answer_reviewer_provider,
        build_claim_typing_provider,
        build_clarification_provider,
        build_final_answer_composer_provider,
        build_insight_drafting_provider,
        build_question_understanding_provider,
    )

    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING", raising=False)
    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER", raising=False)
    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING", raising=False)
    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING", raising=False)
    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_ANSWER_REVIEWER", raising=False)
    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_FINAL_ANSWER_COMPOSER", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-not-used")

    assert build_question_understanding_provider(env_path=tmp_path / "missing.env") is None
    assert build_clarification_provider(env_path=tmp_path / "missing.env") is None
    assert build_claim_typing_provider(env_path=tmp_path / "missing.env") is None
    assert build_insight_drafting_provider(env_path=tmp_path / "missing.env") is None
    assert build_answer_reviewer_provider(env_path=tmp_path / "missing.env") is None
    assert build_final_answer_composer_provider(env_path=tmp_path / "missing.env") is None


def test_product_live_mode_can_be_enabled_from_env_file(tmp_path, monkeypatch):
    from llm_ops.runtime_provider import (
        build_insight_drafting_provider,
        build_answer_reviewer_provider,
        build_final_answer_composer_provider,
        build_question_understanding_provider,
        build_sql_candidate_provider,
        product_live_mode_enabled,
    )

    monkeypatch.delenv("INSIGHTFLOW_PRODUCT_LIVE_MODE", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "INSIGHTFLOW_PRODUCT_LIVE_MODE=1",
                "DEEPSEEK_API_KEY=sk-test-from-file",
                "DEEPSEEK_MODEL=deepseek-v4-flash",
            ]
        ),
        encoding="utf-8",
    )

    assert product_live_mode_enabled(env_path=env_path, env={}) is True
    assert build_question_understanding_provider(env_path=env_path, env={}) is not None
    assert build_sql_candidate_provider(env_path=env_path, env={}) is not None
    assert build_insight_drafting_provider(env_path=env_path, env={}) is not None
    assert build_answer_reviewer_provider(env_path=env_path, env={}) is not None
    assert build_final_answer_composer_provider(env_path=env_path, env={}) is not None
