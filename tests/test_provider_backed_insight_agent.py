from llm_ops.provider import MockLLMProvider


NEW_BUSINESS_ANSWER_KEYS = {
    "headline",
    "direct_answer",
    "why",
    "evidence_bullets",
    "recommendations",
    "caveats",
    "confidence",
}


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
                "business_answer": {
                    "headline": "建议优先加码 paid_search",
                    "direct_answer": "建议优先加码 paid_search，因为它贡献了最高收入 200.0。",
                    "why": "证据显示 paid_search 的收入为 200.0。",
                    "evidence_bullets": ["paid_search 收入为 200.0。"],
                    "recommendations": ["优先复盘 paid_search 的投放和转化动作。"],
                    "caveats": [],
                    "confidence": "high",
                },
            }
        ),
    )

    assert result["insight"]["source"] == "provider"
    assert set(result["business_answer"]) == NEW_BUSINESS_ANSWER_KEYS
    assert result["business_answer"] == {
        "headline": "建议优先加码 paid_search",
        "direct_answer": "建议优先加码 paid_search，因为它贡献了最高收入 200.0。",
        "why": "证据显示 paid_search 的收入为 200.0。",
        "evidence_bullets": ["paid_search 收入为 200.0。"],
        "recommendations": ["优先复盘 paid_search 的投放和转化动作。"],
        "caveats": ["当前结论只基于本次查询返回的数据。"],
        "confidence": "high",
    }
    assert result["final_answer"] == result["business_answer"]["direct_answer"]
    assert "channel=" not in result["final_answer"]
    assert "channel=" not in " ".join(
        [
            result["business_answer"]["headline"],
            result["business_answer"]["direct_answer"],
            result["business_answer"]["why"],
            *result["business_answer"]["evidence_bullets"],
            *result["business_answer"]["recommendations"],
            *result["business_answer"]["caveats"],
        ]
    )


def test_provider_backed_insight_agent_adds_exact_evidence_anchor():
    from agents.insight_agent import run_insight_agent

    state = {
        "run_id": "run_provider_backed_insight_anchor",
        "session_id": "session_provider_backed_insight_anchor",
        "user_question": "收入最高的获客渠道是谁？",
        "execution_result": {
            "success": True,
            "columns": ["channel", "total_revenue"],
            "rows": [["email", 44548.53]],
            "row_count": 1,
        },
        "trace": [],
    }

    result = run_insight_agent(
        state,
        provider=MockLLMProvider(
            {
                "candidate_claims": ["email 渠道收入最高，为 44548.53。"],
                "business_answer": {
                    "headline": "email 是收入最高渠道",
                    "direct_answer": "收入最高的渠道值得优先复盘其投放和转化动作。",
                    "why": "当前证据显示 email 渠道收入最高。",
                    "evidence_bullets": ["email 渠道收入最高，为 44548.53。"],
                    "recommendations": ["复盘 email 的投放和转化动作。"],
                    "caveats": [],
                    "confidence": "medium",
                },
            }
        ),
    )

    assert result["final_answer"] == result["business_answer"]["direct_answer"]
    assert "email" in " ".join(result["business_answer"]["evidence_bullets"])
    assert "44548.53" in " ".join(result["business_answer"]["evidence_bullets"])
    assert "channel=" not in result["final_answer"]
