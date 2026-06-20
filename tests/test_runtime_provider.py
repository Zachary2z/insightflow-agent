def test_question_understanding_provider_flag_parses_opt_in_values():
    from llm_ops.runtime_provider import provider_question_understanding_enabled

    assert provider_question_understanding_enabled({}) is False
    assert provider_question_understanding_enabled({"INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING": "0"}) is False
    assert provider_question_understanding_enabled({"INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING": "1"}) is True
    assert provider_question_understanding_enabled({"INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING": "true"}) is True
    assert provider_question_understanding_enabled({"INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING": "yes"}) is True


def test_build_question_understanding_provider_preserves_no_key_baseline(tmp_path, monkeypatch):
    from llm_ops.runtime_provider import build_question_understanding_provider

    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    provider = build_question_understanding_provider(env_path=tmp_path / "missing.env")

    assert provider is None


def test_build_question_understanding_provider_returns_none_when_runtime_flag_disabled(tmp_path, monkeypatch):
    from llm_ops.runtime_provider import build_question_understanding_provider

    monkeypatch.delenv("INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-not-used")

    provider = build_question_understanding_provider(env_path=tmp_path / "missing.env")

    assert provider is None
