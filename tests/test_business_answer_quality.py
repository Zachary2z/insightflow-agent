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


def _assert_new_business_answer_shape(answer):
    assert set(answer) == NEW_BUSINESS_ANSWER_KEYS


def _business_answer_text(answer):
    return " ".join(
        [
            answer["headline"],
            answer["direct_answer"],
            answer["why"],
            *answer["evidence_bullets"],
            *answer["recommendations"],
            *answer["caveats"],
        ]
    )


def test_business_answer_rejects_raw_key_value_dump():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "final_answer": "1. channel=paid_search, revenue=200.0, order_count=10\n"
            "2. channel=email, revenue=100.0, order_count=5",
            "insight": {"source": "deterministic", "fallback_used": True},
        }
    )

    _assert_new_business_answer_shape(answer)
    assert answer["headline"] != "channel=paid_search, revenue=200.0, order_count=10"
    assert "channel=" not in _business_answer_text(answer)
    assert "revenue=" not in _business_answer_text(answer)
    assert answer["confidence"] == "low"
    assert answer["caveats"]


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

    _assert_new_business_answer_shape(product["business_answer"])
    business_text = _business_answer_text(product["business_answer"])
    assert "channel=" not in business_text
    assert "revenue=" not in business_text
    assert "order_count=" not in business_text
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
            "rows": [["paid_search", 200.0], ["organic", 120.0]],
            "row_count": 2,
        },
        "trace": [],
    }
    provider = MockLLMProvider(
        {
            "candidate_claims": ["paid_search revenue is 200.0", "organic revenue is 120.0"],
            "business_answer": {
                "headline": "建议优先加码 paid_search",
                "direct_answer": "建议优先加码 paid_search，因为它在当前对比中贡献了最高收入 200.0。",
                "why": "证据显示 paid_search 贡献收入 200.0，高于 organic 的 120.0。",
                "evidence_bullets": ["paid_search 收入为 200.0。", "organic 收入为 120.0。"],
                "recommendations": ["优先复盘 paid_search 的投放效率。"],
                "caveats": [],
                "confidence": "high",
            },
        }
    )

    result = run_insight_agent(state, provider=provider)

    assert result["insight"]["source"] == "provider"
    _assert_new_business_answer_shape(result["business_answer"])
    assert result["business_answer"]["headline"].startswith("建议")
    assert result["business_answer"]["direct_answer"].startswith("建议")
    assert result["business_answer"]["confidence"]
    assert "channel=" not in result["final_answer"]
    assert result["final_answer"] == result["business_answer"]["direct_answer"]
    assert "channel=" not in _business_answer_text(result["business_answer"])


def test_insight_agent_reviews_and_composes_provider_draft_before_final_answer():
    from agents.insight_agent import run_insight_agent

    state = {
        "run_id": "run_reviewed_answer",
        "session_id": "session_reviewed_answer",
        "user_question": "Which entity should we prioritize?",
        "execution_result": {
            "success": True,
            "columns": ["entity_name", "score_value"],
            "rows": [["Alpha", 91.0], ["Beta", 83.0]],
            "row_count": 2,
        },
        "evidence_result": {"validation_status": "validated"},
        "trace": [],
    }
    draft_provider = MockLLMProvider(
        {
            "candidate_claims": ["Alpha score_value is 91.0", "Beta score_value is 83.0"],
            "business_answer": {
                "headline": "Gamma wins on margin_rate",
                "direct_answer": "Prioritize Gamma because margin_rate is strongest.",
                "why": "Gamma margin_rate is 0.42.",
                "evidence_bullets": ["Gamma margin_rate is 0.42."],
                "recommendations": ["Move resources to Gamma using margin_rate."],
                "caveats": [],
                "confidence": "high",
            },
        }
    )
    reviewer_provider = MockLLMProvider(
        {
            "status": "revise",
            "language": "en",
            "supported_entities": ["Alpha", "Beta"],
            "unsupported_entities": ["Gamma"],
            "supported_metrics": ["score_value"],
            "unsupported_metrics": ["margin_rate"],
            "issues": [
                {
                    "type": "entity_mismatch",
                    "message": "Gamma is absent from the execution/evidence rows.",
                    "affected_fields": ["headline", "direct_answer", "recommendations"],
                },
                {
                    "type": "metric_mismatch",
                    "message": "margin_rate is absent from the execution/evidence rows.",
                    "affected_fields": ["why", "evidence_bullets"],
                },
            ],
            "revision_instructions": ["Remove Gamma and margin_rate; use returned evidence only."],
            "confidence": "high",
        }
    )
    composer_provider = MockLLMProvider(
        {
            "headline": "Alpha is the supported priority",
            "direct_answer": "Prioritize Alpha because the returned evidence ranks it first on score_value.",
            "why": "The result rows show Alpha at 91.0 versus Beta at 83.0.",
            "evidence_bullets": ["Alpha score_value is 91.0.", "Beta score_value is 83.0."],
            "recommendations": ["Use Alpha as the next review focus and keep tracking score_value."],
            "caveats": ["This only uses the current query result."],
            "confidence": "medium",
        }
    )

    result = run_insight_agent(
        state,
        provider=draft_provider,
        answer_reviewer_provider=reviewer_provider,
        final_answer_composer_provider=composer_provider,
    )

    _assert_new_business_answer_shape(result["business_answer"])
    business_text = _business_answer_text(result["business_answer"])
    assert result["insight"]["answer_review"]["status"] == "revise"
    assert result["insight"]["answer_composition"]["source"] == "provider"
    assert "Gamma" not in business_text
    assert "margin_rate" not in business_text
    assert "Alpha" in business_text
    assert result["final_answer"] == result["business_answer"]["direct_answer"]


def test_chinese_question_rejects_english_provider_business_summary():
    from agents.insight_agent import run_insight_agent

    state = {
        "run_id": "run_provider_language",
        "session_id": "session_provider_language",
        "user_question": "最近90天哪个渠道收入最高？为什么？",
        "execution_result": {
            "success": True,
            "columns": ["channel", "total_revenue"],
            "rows": [["email", 44548.53]],
            "row_count": 1,
        },
        "trace": [],
    }
    provider = MockLLMProvider(
        {
            "candidate_claims": ["email total revenue is 44548.53"],
            "business_answer": {
                "headline": "Email is the top revenue channel",
                "direct_answer": (
                    "Based on the data, email is the top revenue channel for the last 90 days, "
                    "bringing in $44,548.53."
                ),
                "why": "The first evidence row shows email at 44548.53 total revenue.",
                "evidence_bullets": ["email total revenue is 44548.53."],
                "recommendations": ["Review the email channel plan."],
                "caveats": [],
                "confidence": "medium",
            },
        }
    )

    result = run_insight_agent(state, provider=provider)

    assert result["insight"]["fallback_used"] is True
    assert result["insight"]["validation_error"]
    assert "输出语言" in result["insight"]["validation_error"]
    _assert_new_business_answer_shape(result["business_answer"])
    assert "当前数据中" in result["business_answer"]["direct_answer"]
    assert "email 总收入最高" in result["business_answer"]["direct_answer"]
    assert "Based on the data" not in _business_answer_text(result["business_answer"])


def test_chinese_question_localizes_english_system_understanding():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_language_thread",
            "status": "completed",
            "user_question": "最近90天哪个渠道收入最高？为什么？",
            "question_understanding": {
                "strategy": "llm_candidate",
                "intent": {
                    "metric": "revenue",
                    "dimension": "channel",
                    "time_range": {"type": "last_n_days", "value": 90},
                },
                "reason": (
                    "User explicitly asks for the channel with highest revenue in the last 90 days."
                ),
            },
            "final_answer": "email 渠道收入最高。",
        },
        workspace_id="ws_language",
    )

    understanding = product["question_thread"]["system_understanding"]
    assert understanding.startswith("系统已识别")
    assert "收入" in understanding
    assert "渠道" in understanding
    assert "最近 90 天" in understanding
    assert "User explicitly" not in understanding


def test_business_answer_without_evidence_does_not_extract_plain_guidance_as_recommendation():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "final_answer": (
                "Based on the past 90 days data, email has the highest ROI. "
                "A balanced approach might be to increase email budget while optimizing paid search spend."
            ),
            "insight": {"source": "provider"},
        }
    )

    _assert_new_business_answer_shape(answer)
    assert answer["recommendations"] == []
    assert answer["confidence"] == "low"
    assert answer["caveats"]


def test_insight_drafter_validation_rejects_draft_summary_only_output():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "insight_drafter",
        {
            "candidate_claims": ["paid_search revenue is 200.0"],
            "draft_summary": "建议优先加码 paid_search，因为它贡献了最高收入 200.0。",
        },
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "business_answer" in result["error"]


def test_insight_drafter_validation_rejects_extra_old_draft_summary_field():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "insight_drafter",
        {
            "candidate_claims": ["paid_search revenue is 200.0"],
            "draft_summary": "建议优先加码 paid_search。",
            "business_answer": {
                "headline": "建议优先加码 paid_search",
                "direct_answer": "建议优先加码 paid_search，因为它贡献了最高收入 200.0。",
                "why": "证据显示 paid_search 收入为 200.0。",
                "evidence_bullets": ["paid_search 收入为 200.0。"],
                "recommendations": ["复盘 paid_search 的投放效率。"],
                "caveats": [],
                "confidence": "high",
            },
        },
        schema_context={"user_question": "哪个渠道该加预算？"},
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "draft_summary" in result["error"]


def test_insight_drafter_validation_rejects_english_business_answer_for_chinese_question():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "insight_drafter",
        {
            "candidate_claims": ["email total revenue is 44548.53"],
            "business_answer": {
                "headline": "Email is the top revenue channel",
                "direct_answer": "Email is the top revenue channel in the last 90 days.",
                "why": "The evidence row shows email revenue is 44548.53.",
                "evidence_bullets": ["email total revenue is 44548.53."],
                "recommendations": ["Increase email budget."],
                "caveats": [],
                "confidence": "medium",
            },
        },
        schema_context={"user_question": "最近90天哪个渠道收入最高？"},
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "中文问题" in result["error"]


def test_insight_drafter_validation_rejects_partially_english_business_fields_for_chinese_question():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "insight_drafter",
        {
            "candidate_claims": ["email total revenue is 44548.53"],
            "business_answer": {
                "headline": "email 渠道收入最高",
                "direct_answer": "Email is the top revenue channel in the last 90 days.",
                "why": "The evidence row shows email revenue is 44548.53.",
                "evidence_bullets": ["email 渠道收入为 44548.53。"],
                "recommendations": ["Increase email budget."],
                "caveats": [],
                "confidence": "medium",
            },
        },
        schema_context={"user_question": "最近90天哪个渠道收入最高？"},
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "business_answer.direct_answer" in result["error"]
    assert "中文" in result["error"]


def test_insight_drafter_validation_allows_english_business_terms_inside_chinese_sentences():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "insight_drafter",
        {
            "candidate_claims": ["email ROI 为 0.38"],
            "business_answer": {
                "headline": "email 渠道的 ROI 最高",
                "direct_answer": "建议优先复盘 email 渠道，因为它的 ROI 为 0.38。",
                "why": "证据显示 email 在当前结果中 ROI 领先，且 paid_search 可作为对比渠道。",
                "evidence_bullets": ["email 的 ROI 为 0.38。", "paid_search 的 ROI 低于 email。"],
                "recommendations": ["继续观察 email 的预算效率，并对比 paid_search 的转化质量。"],
                "caveats": ["当前结论只覆盖本次返回数据。"],
                "confidence": "medium",
            },
        },
        schema_context={"user_question": "最近90天哪个渠道 ROI 最高？"},
    )

    assert result["success"] is True
    assert result["content"]["business_answer"]["headline"] == "email 渠道的 ROI 最高"


def test_insight_drafter_validation_rejects_sql_trace_and_provider_metadata_in_business_fields():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "insight_drafter",
        {
            "candidate_claims": ["paid_search revenue is 200.0"],
            "business_answer": {
                "headline": "建议优先加码 paid_search",
                "direct_answer": "建议优先加码 paid_search。trace_id=abc123 provider_metadata={model: deepseek}",
                "why": "SELECT channel, SUM(revenue) FROM orders GROUP BY channel",
                "evidence_bullets": ["paid_search 收入为 200.0。"],
                "recommendations": [],
                "caveats": [],
                "confidence": "medium",
            },
        },
        schema_context={"user_question": "哪个渠道该加预算？"},
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "technical" in result["error"] or "技术" in result["error"]


def test_insight_drafter_validation_rejects_raw_parameter_dump_in_business_answer():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "insight_drafter",
        {
            "candidate_claims": ["paid_search revenue is 200.0"],
            "business_answer": {
                "headline": "建议优先加码 paid_search",
                "direct_answer": "channel=paid_search, revenue=200.0, order_count=10",
                "why": "证据显示 paid_search 收入最高。",
                "evidence_bullets": ["paid_search 收入为 200.0。"],
                "recommendations": [],
                "caveats": [],
                "confidence": "medium",
            },
        },
        schema_context={"user_question": "哪个渠道该加预算？"},
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "raw parameter" in result["error"]


def test_product_result_builder_rejects_mixed_language_provider_business_answer_for_chinese_question():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近90天哪个渠道收入最高？",
            "business_answer": {
                "headline": "email 渠道收入最高",
                "direct_answer": "Email is the top revenue channel in the last 90 days.",
                "why": "The evidence row shows email revenue is 44548.53.",
                "evidence_bullets": ["email 渠道收入为 44548.53。"],
                "recommendations": ["Increase email budget."],
                "caveats": [],
                "confidence": "medium",
            },
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["email", 44548.53]],
            },
        }
    )

    _assert_new_business_answer_shape(answer)
    assert "Email is the top revenue channel" not in _business_answer_text(answer)
    assert "The evidence row shows" not in _business_answer_text(answer)
    assert "Increase email budget" not in _business_answer_text(answer)
    assert answer["direct_answer"].startswith("当前数据中")
    assert "email 总收入最高" in answer["direct_answer"]
