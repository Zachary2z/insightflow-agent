import json
from pathlib import Path
from types import SimpleNamespace


class _FakeUsage:
    prompt_tokens = 12
    completion_tokens = 8
    total_tokens = 20

    def model_dump(self):
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class _FakeChatCompletions:
    def __init__(self, content='{"claims": ["GMV 为 100"]}'):
        self.content = content
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content=self.content),
                )
            ],
            usage=_FakeUsage(),
        )


class _FakeClient:
    def __init__(self, content='{"claims": ["GMV 为 100"]}'):
        self.chat = SimpleNamespace(completions=_FakeChatCompletions(content))


def test_deepseek_config_loads_from_env_file_without_leaking_secret(tmp_path, monkeypatch):
    from llm_ops.deepseek_provider import load_deepseek_config

    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DEEPSEEK_API_KEY=sk-test-secret",
                "DEEPSEEK_BASE_URL=https://api.deepseek.com",
                "DEEPSEEK_MODEL=DeepSeekv4pro",
                "INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)

    config = load_deepseek_config(env_path=env_path)

    assert config.success is True
    assert config.api_key == "sk-test-secret"
    assert config.base_url == "https://api.deepseek.com"
    assert config.model == "deepseek-v4-pro"
    assert config.live_tests_enabled is True
    assert "sk-test-secret" not in repr(config)
    assert config.safe_dict() == {
        "success": True,
        "api_key_present": True,
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-pro",
        "live_tests_enabled": True,
        "error": "",
    }


def test_deepseek_config_keeps_no_key_baseline_non_blocking(tmp_path, monkeypatch):
    from llm_ops.deepseek_provider import load_deepseek_config

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    config = load_deepseek_config(env_path=tmp_path / "missing.env", require_api_key=False)

    assert config.success is True
    assert config.api_key == ""
    assert config.base_url == "https://api.deepseek.com"
    assert config.model == "deepseek-v4-pro"
    assert config.live_tests_enabled is False

    required = load_deepseek_config(env_path=tmp_path / "missing.env", require_api_key=True)
    assert required.success is False
    assert required.api_key == ""
    assert required.error == "DEEPSEEK_API_KEY is required"


def test_deepseek_provider_uses_json_response_format_without_token_cap():
    from llm_ops.deepseek_provider import DeepSeekConfig, DeepSeekProvider
    from llm_ops.provider import LLMRequest

    client = _FakeClient('{"claims": ["GMV 为 100"]}')
    provider = DeepSeekProvider(
        DeepSeekConfig(
            api_key="sk-test-secret",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-pro",
        ),
        client=client,
    )

    content = provider.generate(
        LLMRequest(
            prompt="Return JSON claims.",
            prompt_id="guarded_insight_claims",
            prompt_version="v1",
            model=provider.model,
        )
    )

    call = client.chat.completions.calls[0]
    assert json.loads(content) == {"claims": ["GMV 为 100"]}
    assert call["model"] == "deepseek-v4-pro"
    assert call["temperature"] == 0
    assert call["response_format"] == {"type": "json_object"}
    assert "max_tokens" not in call
    assert "sk-test-secret" not in str(call)


def test_structured_output_accepts_report_planner_objects_and_rejects_string_lists():
    from llm_ops.structured_output import validate_prompt_output

    accepted = validate_prompt_output(
        "report_planner",
        {
            "sections": [{"section_id": "weekly_gmv", "rationale": "Core metric."}],
            "requires_clarification": False,
            "clarification_questions": [],
        },
        schema_context={"allowed_section_ids": ["weekly_gmv", "top_products"]},
    )
    rejected = validate_prompt_output(
        "report_planner",
        {"sections": ["weekly_gmv", "top_products"]},
        schema_context={"allowed_section_ids": ["weekly_gmv", "top_products"]},
    )

    assert accepted["success"] is True
    assert accepted["content"]["sections"] == [{"section_id": "weekly_gmv", "rationale": "Core metric."}]
    assert accepted["content"]["requires_clarification"] is False
    assert rejected["success"] is False
    assert rejected["error_type"] == "llm_schema_validation_error"
    assert "sections[0] must be an object" in rejected["error"]


def test_report_planner_prompt_describes_strict_section_object_schema():
    from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY

    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "report_planner",
        {
            "user_question": "帮我生成本周经营周报。",
            "allowed_section_ids": ["weekly_gmv", "top_products"],
        },
    )

    assert rendered["success"] is True
    assert "sections must be an array of objects" in rendered["prompt"]
    assert "string lists are invalid" in rendered["prompt"]


def test_validated_request_returns_structured_error_for_schema_mismatch():
    from llm_ops.provider import LLMRequest, MockLLMProvider
    from llm_ops.structured_output import run_validated_llm_request

    result = run_validated_llm_request(
        MockLLMProvider({"sections": ["weekly_gmv"]}),
        LLMRequest(
            prompt="Return report plan.",
            prompt_id="report_planner",
            prompt_version="v1",
            model="mock-free",
        ),
        schema_context={"allowed_section_ids": ["weekly_gmv"]},
    )

    assert result["success"] is False
    assert result["content"] is None
    assert result["error_type"] == "llm_schema_validation_error"
    assert result["trace_event"]["status"] == "error"
    assert result["trace_event"]["error_type"] == "llm_schema_validation_error"


def test_malformed_json_returns_structured_error_without_crashing():
    from llm_ops.provider import LLMRequest, MockLLMProvider, run_llm_request

    result = run_llm_request(
        MockLLMProvider('{"sections": ['),
        LLMRequest(
            prompt="Return report plan.",
            prompt_id="report_planner",
            prompt_version="v1",
            model="mock-free",
        ),
    )

    assert result["success"] is False
    assert result["content"] is None
    assert result["error_type"] == "llm_malformed_json_error"
    assert result["trace_event"]["error_type"] == "llm_malformed_json_error"


def test_live_deepseek_smoke_is_opt_in(monkeypatch):
    from llm_ops.deepseek_provider import live_deepseek_tests_enabled

    monkeypatch.delenv("INSIGHTFLOW_LIVE_DEEPSEEK_TESTS", raising=False)
    assert live_deepseek_tests_enabled({}) is False
    assert live_deepseek_tests_enabled({"INSIGHTFLOW_LIVE_DEEPSEEK_TESTS": "0"}) is False
    assert live_deepseek_tests_enabled({"INSIGHTFLOW_LIVE_DEEPSEEK_TESTS": "1"}) is True
