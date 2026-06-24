from llm_ops.provider import MockLLMProvider


def test_provider_backed_insight_agent_generates_business_answer_not_parameter_dump():
    from agents.insight_agent import run_insight_agent

    state = {
        "run_id": "run_provider_backed_insight",
        "session_id": "session_provider_backed_insight",
        "user_question": "哪个渠道该加预算？",
        "execution_result": {
            "success": True,
            "columns": ["channel", "revenue"],
            "rows": [["paid_search", 200.0]],
            "row_count": 1,
        },
        "trace": [],
    }

    result = run_insight_agent(
        state,
        provider=MockLLMProvider(
            {
                "candidate_claims": ["paid_search revenue is 200.0"],
                "draft_summary": "建议优先加码 paid_search，因为它贡献了最高收入 200.0。",
            }
        ),
    )

    assert result["insight"]["source"] == "provider"
    assert result["business_answer"]["headline"].startswith("建议")
    assert result["business_answer"]["summary"].startswith("建议")
    assert result["final_answer"] == result["business_answer"]["summary"]
    assert "channel=" not in result["final_answer"]
