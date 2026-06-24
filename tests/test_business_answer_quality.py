from llm_ops.provider import MockLLMProvider


def test_business_answer_rejects_raw_key_value_dump():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "final_answer": "1. channel=paid_search, revenue=200.0, order_count=10\n"
            "2. channel=email, revenue=100.0, order_count=5",
            "insight": {"source": "deterministic", "fallback_used": True},
        }
    )

    assert answer["headline"] != "channel=paid_search, revenue=200.0, order_count=10"
    assert answer["quality_flags"] == ["raw_parameter_dump_detected"]
    assert "channel=" not in answer["summary"]
    assert "revenue=" not in answer["summary"]


def test_business_answer_keeps_raw_rows_out_of_product_fields():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_quality",
            "status": "completed",
            "final_answer": "channel=paid_search, revenue=200.0, order_count=10",
            "generated_sql": "SELECT channel, SUM(revenue) FROM orders GROUP BY channel",
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue", "order_count"],
                "rows": [["paid_search", 200.0, 10]],
            },
            "insight": {"source": "deterministic"},
        },
        workspace_id="ws_quality",
    )

    business_text = " ".join(
        [
            product["business_answer"]["headline"],
            product["business_answer"]["summary"],
            *product["business_answer"]["recommendations"],
            *product["business_answer"]["next_actions"],
        ]
    )
    assert "channel=" not in business_text
    assert "SELECT" not in business_text
    assert "provider_metadata" not in product["business_answer"]
    assert product["technical_details"]["raw_rows"] == [["paid_search", 200.0, 10]]


def test_provider_insight_output_becomes_recommendation_first_business_answer():
    from agents.insight_agent import run_insight_agent

    state = {
        "run_id": "run_provider_answer",
        "session_id": "session_provider_answer",
        "user_question": "哪个渠道该加预算？",
        "execution_result": {
            "success": True,
            "columns": ["channel", "revenue"],
            "rows": [["paid_search", 200.0]],
            "row_count": 1,
        },
        "trace": [],
    }
    provider = MockLLMProvider(
        {
            "candidate_claims": ["paid_search revenue is 200.0"],
            "draft_summary": "建议优先加码 paid_search，因为它贡献了最高收入 200.0。",
        }
    )

    result = run_insight_agent(state, provider=provider)

    assert result["insight"]["source"] == "provider"
    assert result["business_answer"]["headline"].startswith("建议")
    assert result["business_answer"]["summary"].startswith("建议")
    assert result["business_answer"]["confidence"]
    assert result["business_answer"]["quality_flags"] == []
    assert "channel=" not in result["final_answer"]
    assert "channel=" not in result["business_answer"]["summary"]


def test_insight_drafter_validation_rejects_raw_parameter_dump():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "insight_drafter",
        {
            "candidate_claims": ["paid_search revenue is 200.0"],
            "draft_summary": "channel=paid_search, revenue=200.0, order_count=10",
        },
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "raw parameter" in result["error"]
