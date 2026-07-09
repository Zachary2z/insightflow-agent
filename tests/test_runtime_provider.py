def test_question_understanding_provider_flag_parses_opt_in_values():
    from llm_ops.runtime_provider import (
        provider_clarification_router_enabled,
        provider_business_answer_enabled,
        provider_question_understanding_enabled,
        provider_report_composer_enabled,
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
    assert provider_business_answer_enabled({}) is False
    assert provider_business_answer_enabled({"INSIGHTFLOW_USE_PROVIDER_BUSINESS_ANSWER": "0"}) is False
    assert provider_business_answer_enabled({"INSIGHTFLOW_USE_PROVIDER_BUSINESS_ANSWER": "1"}) is True
    assert provider_business_answer_enabled({"INSIGHTFLOW_USE_PROVIDER_BUSINESS_ANSWER": "on"}) is True
    assert provider_report_composer_enabled({}) is False
    assert provider_report_composer_enabled({"INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER": "0"}) is False
    assert provider_report_composer_enabled({"INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER": "1"}) is True
    assert provider_report_composer_enabled({"INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER": "yes"}) is True


def test_build_question_understanding_provider_preserves_no_key_baseline(tmp_path, monkeypatch):
    from llm_ops.runtime_provider import (
        build_clarification_provider,
        build_business_answer_provider,
        build_question_understanding_provider,
        build_report_composer_provider,
    )

    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING", "1")
    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER", "1")
    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_BUSINESS_ANSWER", "1")
    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    assert build_question_understanding_provider(env_path=tmp_path / "missing.env") is None
    assert build_clarification_provider(env_path=tmp_path / "missing.env") is None
    assert build_business_answer_provider(env_path=tmp_path / "missing.env") is None
    assert build_report_composer_provider(env_path=tmp_path / "missing.env") is None


def test_build_question_understanding_provider_returns_none_when_runtime_flag_disabled(tmp_path, monkeypatch):
    from llm_ops.runtime_provider import (
        build_clarification_provider,
        build_business_answer_provider,
        build_question_understanding_provider,
        build_report_composer_provider,
    )

    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING", raising=False)
    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER", raising=False)
    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_BUSINESS_ANSWER", raising=False)
    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-not-used")

    assert build_question_understanding_provider(env_path=tmp_path / "missing.env") is None
    assert build_clarification_provider(env_path=tmp_path / "missing.env") is None
    assert build_business_answer_provider(env_path=tmp_path / "missing.env") is None
    assert build_report_composer_provider(env_path=tmp_path / "missing.env") is None


def test_product_live_mode_can_be_enabled_from_env_file(tmp_path, monkeypatch):
    from llm_ops.runtime_provider import (
        build_business_answer_provider,
        build_question_understanding_provider,
        build_report_composer_provider,
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
    assert build_business_answer_provider(env_path=env_path, env={}) is not None
    assert build_report_composer_provider(env_path=env_path, env={}) is not None


def test_removed_old_answer_provider_surfaces_are_not_exported():
    import llm_ops.runtime_provider as runtime_provider

    removed_names = {
        "provider_insight_drafting_enabled",
        "provider_answer_reviewer_enabled",
        "provider_final_answer_composer_enabled",
        "build_insight_drafting_provider",
        "build_answer_reviewer_provider",
        "build_final_answer_composer_provider",
    }

    assert removed_names.isdisjoint(set(dir(runtime_provider)))
