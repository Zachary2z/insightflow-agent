def test_prompt_registry_renders_versioned_prompt_with_safety_contract():
    from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY

    result = DEFAULT_PROMPT_REGISTRY.render(
        "guarded_sql_candidate",
        {
            "user_question": "最近 30 天销售额最高的 5 个商品是什么？",
            "schema_text": "orders(id, status), order_items(order_id, quantity, unit_price)",
            "workspace_context": {},
            "metric_context": {"metric_name": "gmv"},
            "business_context": {"time_window": "last_30_days"},
            "current_deterministic_sql": "SELECT 1",
        },
    )

    assert result["success"] is True
    assert result["prompt_id"] == "guarded_sql_candidate"
    assert result["prompt_version"] == "v1"
    assert "最近 30 天" in result["prompt"]
    assert "orders" in result["prompt"]
    assert "validate_sql" in result["prompt"]
    assert result["metadata"]["required_variables"] == [
        "user_question",
        "schema_text",
        "workspace_context",
        "metric_context",
        "business_context",
        "current_deterministic_sql",
    ]
    assert "must_not_execute_sql" in result["metadata"]["safety_contract"]
    assert "must_not_bypass_validate_sql" in result["metadata"]["safety_contract"]


def test_prompt_registry_renders_report_writer_prompt_with_evidence_boundary():
    from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY

    result = DEFAULT_PROMPT_REGISTRY.render(
        "report_writer",
        {
            "user_question": "帮我生成经营复盘。",
            "verified_findings": ["Laptop Pro 14 的 GMV 为 511248.56"],
            "verified_hypotheses": ["可能需要进一步验证广告流量变化"],
            "blocked_unsupported_claims": ["库存不足是导致销量下降的主要原因"],
            "sql_records": ["SELECT product_name, gmv FROM product_gmv LIMIT 5"],
            "chart_paths": ["reports/charts/example.png"],
            "trace_path": "logs/traces/example.json",
        },
    )

    assert result["success"] is True
    assert result["prompt_id"] == "report_writer"
    assert result["prompt_version"] == "v1"
    assert "Evidence-backed report writing" in result["prompt"]
    assert "must_not_add_unsupported_claims" in result["metadata"]["safety_contract"]
    assert "库存不足" in result["prompt"]


def test_prompt_registry_renders_insight_claim_typer_prompt_with_evidence_boundary():
    from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY

    result = DEFAULT_PROMPT_REGISTRY.render(
        "insight_claim_typer",
        {
            "user_question": "最近 30 天销售额最高的商品是什么？",
            "candidate_claims": ["Laptop Pro 14 的 GMV 为 511248.56"],
            "execution_result": {"columns": ["product_name", "gmv"], "rows": [["Laptop Pro 14", 511248.56]]},
            "business_context": {},
            "metric_context": {"metric_name": "gmv"},
        },
    )

    assert result["success"] is True
    assert result["prompt_id"] == "insight_claim_typer"
    assert "typed_claims" in result["prompt"]
    assert "must_not_bypass_evidence_validator" in result["metadata"]["safety_contract"]


def test_prompt_registry_renders_action_drafter_prompt_with_approval_boundary():
    from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY

    result = DEFAULT_PROMPT_REGISTRY.render(
        "action_drafter",
        {
            "user_question": "请为运营团队创建跟进任务和邮件草稿。",
            "evidence_findings": ["Cameras 的 GMV 变化为 -12000.0"],
            "evidence_hypotheses": ["可能需要进一步验证广告流量和转化率数据。"],
            "blocked_unsupported_claims": ["库存不足是确定原因"],
            "existing_actions": [{"action_id": "action_follow_up_task", "action_type": "create_task"}],
        },
    )

    assert result["success"] is True
    assert result["prompt_id"] == "action_drafter"
    assert "create_email_draft" in result["prompt"]
    assert "must_not_bypass_approval_gate" in result["metadata"]["safety_contract"]
    assert "库存不足" in result["prompt"]


def test_question_understanding_prompt_distinguishes_delivery_from_unsafe_operations():
    from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY

    result = DEFAULT_PROMPT_REGISTRY.render(
        "question_understanding",
        {
            "user_question": "最近 30 天销售额最高的 5 个商品是什么？请生成适合财务复核的可视化交付物。",
            "workspace_context": {},
        },
    )

    assert result["success"] is True
    assert "chart/report/export/draft delivery" in result["prompt"]
    assert "not unsafe_operation" in result["prompt"]
    assert "sending externally" in result["prompt"]


def test_prompt_registry_returns_structured_error_for_missing_variables():
    from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY

    result = DEFAULT_PROMPT_REGISTRY.render(
        "report_planner",
        {
            "user_question": "帮我生成经营复盘。",
        },
    )

    assert result["success"] is False
    assert result["prompt_id"] == "report_planner"
    assert result["prompt_version"] == "v1"
    assert "missing required variables" in result["error"]
    assert "allowed_section_ids" in result["missing_variables"]


def test_provider_runner_returns_json_compatible_trace_metadata():
    from llm_ops.provider import LLMRequest, MockLLMProvider, run_llm_request

    provider = MockLLMProvider({"sections": [{"section_id": "weekly_gmv"}]})
    request = LLMRequest(
        prompt="Return allowed report sections.",
        prompt_id="report_planner",
        prompt_version="v1",
        model="mock-free",
        metadata={"node": "report_planner_agent"},
    )

    result = run_llm_request(provider, request)

    assert result["success"] is True
    assert result["content"] == {"sections": [{"section_id": "weekly_gmv"}]}
    assert result["model"] == "mock-free"
    assert result["prompt_id"] == "report_planner"
    assert result["prompt_version"] == "v1"
    assert result["usage"]["input_tokens"] > 0
    assert result["usage"]["output_tokens"] > 0
    assert result["usage"]["estimated_cost_usd"] == 0.0
    assert result["latency_ms"] >= 0
    assert result["trace_event"]["tool_name"] == "llm_provider"
    assert result["trace_event"]["model"] == "mock-free"
    assert result["trace_event"]["prompt_id"] == "report_planner"
    assert result["trace_event"]["prompt_version"] == "v1"


def test_provider_runner_catches_provider_errors_without_crashing():
    from llm_ops.provider import LLMRequest, run_llm_request

    class FailingProvider:
        model = "mock-failing"

        def generate(self, request):
            raise RuntimeError("provider unavailable")

    result = run_llm_request(
        FailingProvider(),
        LLMRequest(
            prompt="Generate SQL candidate.",
            prompt_id="guarded_sql_candidate",
            prompt_version="v1",
            model="mock-failing",
        ),
    )

    assert result["success"] is False
    assert result["content"] is None
    assert result["error"] == "provider unavailable"
    assert result["trace_event"]["status"] == "error"
    assert result["trace_event"]["error_type"] == "llm_provider_error"


def test_llm_smoke_eval_runs_mock_cases_and_reports_failures():
    from llm_ops.eval_smoke import run_llm_smoke_eval
    from llm_ops.provider import MockLLMProvider

    result = run_llm_smoke_eval(
        [
            {
                "case_id": "planner_sections",
                "prompt_id": "report_planner",
                "variables": {
                    "user_question": "帮我生成本周经营周报。",
                    "allowed_section_ids": ["weekly_gmv", "top_products"],
                },
                "expected_keys": ["sections"],
            },
            {
                "case_id": "missing_expected_key",
                "prompt_id": "guarded_insight_claims",
                "variables": {
                    "user_question": "总结 GMV。",
                    "execution_result": {"columns": ["gmv"], "rows": [[100]]},
                    "business_context": {},
                    "metric_context": {},
                    "current_final_answer": "GMV 为 100。",
                },
                "expected_keys": ["claims"],
            },
        ],
        provider=MockLLMProvider({"sections": [{"section_id": "weekly_gmv"}]}),
    )

    assert result["success"] is False
    assert result["total_cases"] == 2
    assert result["passed"] == 1
    assert result["failed"] == 1
    assert result["cases"][0]["success"] is True
    assert result["cases"][1]["success"] is False
    assert "missing expected keys" in result["cases"][1]["error"]
