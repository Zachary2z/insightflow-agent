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


def test_guarded_sql_candidate_normalizes_safe_sql_string_and_alias_shapes():
    from llm_ops.structured_output import validate_prompt_output

    string_result = validate_prompt_output(
        "guarded_sql_candidate",
        {
            "sql_candidates": [
                "SELECT city, COUNT(*) AS order_count FROM orders GROUP BY city LIMIT 20",
            ]
        },
    )
    alias_result = validate_prompt_output(
        "guarded_sql_candidate",
        {
            "sql_candidates": [
                {
                    "query": "SELECT product_name, SUM(gmv) AS gmv FROM product_sales GROUP BY product_name LIMIT 5",
                    "reason": "Top product GMV candidate.",
                }
            ]
        },
    )

    assert string_result["success"] is True
    assert string_result["content"]["sql_candidates"] == [
        {
            "sql": "SELECT city, COUNT(*) AS order_count FROM orders GROUP BY city LIMIT 20",
            "rationale": "",
        }
    ]
    assert alias_result["success"] is True
    assert alias_result["content"]["sql_candidates"] == [
        {
            "sql": "SELECT product_name, SUM(gmv) AS gmv FROM product_sales GROUP BY product_name LIMIT 5",
            "rationale": "Top product GMV candidate.",
        }
    ]


def test_question_understanding_normalizes_string_list_fields():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "question_understanding",
        {
            "strategy": "llm_candidate",
            "intent": {
                "metric": "收入",
                "dimension": "渠道",
                "time_range": {"raw_text": "最近"},
                "filters": "",
                "operation": "对比",
                "limit": None,
                "risk_flags": "",
            },
            "missing_slots": "",
            "clarification_questions": "",
            "risk_flags": "",
            "reason": "Natural business question is complete enough for SQL candidate planning.",
        },
    )

    assert result["success"] is True
    assert result["content"]["intent"]["filters"] == []
    assert result["content"]["intent"]["risk_flags"] == []
    assert result["content"]["missing_slots"] == []
    assert result["content"]["clarification_questions"] == []
    assert result["content"]["risk_flags"] == []


def test_question_understanding_accepts_multi_metric_array_from_provider():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "question_understanding",
        {
            "strategy": "llm_candidate",
            "intent": {
                "metric": ["收入", "投放成本", "ROI"],
                "dimension": "渠道",
                "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"},
                "filters": [],
                "operation": "对比",
                "limit": None,
                "risk_flags": [],
            },
            "missing_slots": [],
            "clarification_questions": [],
            "risk_flags": [],
            "reason": "Multiple requested metrics are complete enough for guarded SQL candidate planning.",
        },
    )

    assert result["success"] is True
    assert result["content"]["intent"]["metric"] == "收入, 投放成本, ROI"
    assert result["content"]["missing_slots"] == []


def test_question_understanding_normalizes_null_list_fields_to_empty_lists():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "question_understanding",
        {
            "strategy": "llm_candidate",
            "intent": {
                "metric": ["收入", "投放成本", "ROI"],
                "dimension": "渠道",
                "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"},
                "filters": None,
                "operation": "对比",
                "limit": None,
                "risk_flags": None,
            },
            "missing_slots": None,
            "clarification_questions": None,
            "risk_flags": None,
            "reason": "DeepSeek sometimes returns null instead of an empty array.",
        },
    )

    assert result["success"] is True
    assert result["content"]["intent"]["filters"] == []
    assert result["content"]["missing_slots"] == []
    assert result["content"]["clarification_questions"] == []
    assert result["content"]["risk_flags"] == []


def test_question_understanding_normalizes_object_list_fields_from_provider():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "question_understanding",
        {
            "strategy": "llm_candidate",
            "intent": {
                "metric": "收入",
                "dimension": "渠道",
                "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"},
                "filters": {"paid_orders": True, "ignore_me": False},
                "operation": "对比",
                "limit": 5,
                "risk_flags": {},
            },
            "missing_slots": {"metric": False, "time_range": False},
            "clarification_questions": {},
            "risk_flags": {},
            "reason": "DeepSeek sometimes returns keyed objects instead of empty arrays.",
        },
    )

    assert result["success"] is True
    assert result["content"]["intent"]["filters"] == ["paid_orders"]
    assert result["content"]["missing_slots"] == []
    assert result["content"]["clarification_questions"] == []
    assert result["content"]["risk_flags"] == []


def test_clarification_router_accepts_no_clarification_decision():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "clarification_router",
        {
            "requires_clarification": False,
            "missing_slots": [],
            "clarification_questions": [],
            "risk_flags": [],
            "reason": "The user already supplied metric, dimension, time range, and decision objective.",
        },
    )

    assert result["success"] is True
    assert result["content"]["requires_clarification"] is False
    assert result["content"]["clarification_questions"] == []


def test_visualization_agent_normalizes_explanation_basis_string():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "visualization_agent",
        {
            "chart_spec": {
                "chart_type": "ranked_bar",
                "title": "Top products",
                "x": "product_name",
                "y": "gmv",
                "y_secondary": "",
                "series": "",
                "required_columns": ["product_name", "gmv"],
                "explanation_basis": "supported_findings",
            },
            "delivery_tool_id": "local_renderer",
            "tool_reason": "Quick local review.",
        },
        schema_context={
            "execution_columns": ["product_name", "gmv"],
            "delivery_tool_ids": ["local_renderer", "excel_exporter", "powerbi_publisher_mock"],
        },
    )

    assert result["success"] is True
    assert result["content"]["chart_spec"]["explanation_basis"] == ["supported_findings"]


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
