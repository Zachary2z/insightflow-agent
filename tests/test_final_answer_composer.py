from __future__ import annotations


BUSINESS_ANSWER_KEYS = {
    "headline",
    "direct_answer",
    "why",
    "evidence_bullets",
    "recommendations",
    "caveats",
    "confidence",
}


def _draft_answer(**overrides):
    answer = {
        "headline": "Alpha is the best option",
        "direct_answer": "Prioritize Alpha because it leads on score_value.",
        "why": "Alpha has score_value 91.0.",
        "evidence_bullets": ["Alpha score_value is 91.0.", "Beta score_value is 83.0."],
        "recommendations": ["Prioritize Alpha for the next resource decision."],
        "caveats": [],
        "confidence": "high",
    }
    answer.update(overrides)
    return answer


def _review(status="accept", **overrides):
    review = {
        "status": status,
        "language": "en",
        "supported_entities": ["Alpha", "Beta"],
        "unsupported_entities": [],
        "supported_metrics": ["score_value"],
        "unsupported_metrics": [],
        "issues": [],
        "revision_instructions": [],
        "confidence": "high",
    }
    review.update(overrides)
    return review


def _execution_result():
    return {
        "success": True,
        "columns": ["entity_name", "score_value"],
        "rows": [["Alpha", 91.0], ["Beta", 83.0]],
        "row_count": 2,
    }


def _assert_shape(answer: dict) -> None:
    assert set(answer) == BUSINESS_ANSWER_KEYS
    assert isinstance(answer["headline"], str)
    assert isinstance(answer["direct_answer"], str)
    assert isinstance(answer["why"], str)
    assert isinstance(answer["evidence_bullets"], list)
    assert isinstance(answer["recommendations"], list)
    assert isinstance(answer["caveats"], list)
    assert answer["confidence"] in {"low", "medium", "high"}


def _answer_text(answer: dict) -> str:
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


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(text or ""))


def test_composer_structured_output_accepts_p16_business_answer_contract():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "final_answer_composer",
        {
            "headline": "Alpha remains the priority",
            "direct_answer": "Prioritize Alpha because the returned evidence ranks it first.",
            "why": "The result rows show Alpha at 91.0 versus Beta at 83.0.",
            "evidence_bullets": ["Alpha score_value is 91.0.", "Beta score_value is 83.0."],
            "recommendations": ["Use Alpha as the next review focus."],
            "caveats": ["This only uses the current query result."],
            "confidence": "high",
        },
        schema_context={"user_question": "Which entity should we prioritize?"},
    )

    assert result["success"] is True
    assert set(result["content"]) == BUSINESS_ANSWER_KEYS


def test_composer_structured_output_rejects_reviewer_json_and_internal_fields():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "final_answer_composer",
        {
            "headline": "Alpha remains the priority",
            "direct_answer": "Reviewer status is revise, prompt_id=answer_reviewer, SQL SELECT * FROM t",
            "why": "The review JSON says unsupported_entities=[]",
            "evidence_bullets": ["Alpha score_value is 91.0."],
            "recommendations": [],
            "caveats": [],
            "confidence": "medium",
            "reviewer_result": _review(),
        },
        schema_context={"user_question": "Which entity should we prioritize?"},
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "reviewer_result" in result["error"] or "technical" in result["error"]


def test_composer_accept_keeps_usable_draft_and_normalizes_shape():
    from agents.final_answer_composer import compose_final_answer

    answer = compose_final_answer(
        user_question="Which entity should we prioritize?",
        execution_result=_execution_result(),
        evidence_result={"validation_status": "validated"},
        draft_business_answer={**_draft_answer(), "extra_field": "remove me"},
        reviewer_result=_review("accept"),
    )

    _assert_shape(answer)
    assert answer["direct_answer"].startswith("Prioritize Alpha")
    assert "extra_field" not in answer
    assert "Alpha" in _answer_text(answer)


def test_composer_revise_removes_unsupported_entity_and_metric():
    from agents.final_answer_composer import compose_final_answer

    answer = compose_final_answer(
        user_question="Which entity should we prioritize?",
        execution_result=_execution_result(),
        evidence_result={"validation_status": "validated"},
        draft_business_answer=_draft_answer(
            headline="Gamma wins on margin_rate",
            direct_answer="Prioritize Gamma because margin_rate is strongest.",
            why="Gamma has margin_rate 0.42.",
            evidence_bullets=["Gamma margin_rate is 0.42."],
            recommendations=["Prioritize Gamma using margin_rate."],
        ),
        reviewer_result=_review(
            "revise",
            unsupported_entities=["Gamma"],
            unsupported_metrics=["margin_rate"],
            issues=[
                {
                    "type": "entity_mismatch",
                    "message": "Gamma is not in the evidence.",
                    "affected_fields": ["headline", "direct_answer", "recommendations"],
                },
                {
                    "type": "metric_mismatch",
                    "message": "margin_rate is not in the evidence.",
                    "affected_fields": ["why", "evidence_bullets"],
                },
            ],
            revision_instructions=["Remove unsupported entity and metric claims."],
            confidence="medium",
        ),
    )

    _assert_shape(answer)
    text = _answer_text(answer)
    assert "Gamma" not in text
    assert "margin_rate" not in text
    assert "Alpha" in text
    assert "score_value" in text


def test_composer_downgrade_says_evidence_is_insufficient():
    from agents.final_answer_composer import compose_final_answer

    answer = compose_final_answer(
        user_question="Which entity should we prioritize?",
        execution_result=_execution_result(),
        evidence_result={"validation_status": "validated"},
        draft_business_answer=_draft_answer(
            headline="Gamma is the priority",
            direct_answer="Prioritize Gamma immediately.",
            recommendations=["Move resources to Gamma."],
        ),
        reviewer_result=_review(
            "downgrade_to_insufficient_evidence",
            unsupported_entities=["Gamma"],
            issues=[
                {
                    "type": "insufficient_evidence",
                    "message": "The recommended entity is absent from evidence.",
                    "affected_fields": ["direct_answer", "recommendations"],
                }
            ],
            revision_instructions=["Downgrade to insufficient evidence."],
            confidence="low",
        ),
    )

    _assert_shape(answer)
    text = _answer_text(answer)
    assert "insufficient" in text.lower() or "not enough evidence" in text.lower()
    assert "Gamma" not in answer["headline"] + answer["direct_answer"] + " ".join(answer["recommendations"])
    assert answer["confidence"] == "low"


def test_composer_uses_chinese_for_chinese_question():
    from agents.final_answer_composer import compose_final_answer

    answer = compose_final_answer(
        user_question="哪个对象最值得优先关注？",
        execution_result={
            "success": True,
            "columns": ["entity_name", "score_value"],
            "rows": [["Alpha", 91.0], ["Beta", 83.0]],
        },
        evidence_result={"validation_status": "validated"},
        draft_business_answer=_draft_answer(
            headline="Alpha 最值得优先关注",
            direct_answer="建议优先关注 Alpha，因为它的 score_value 最高。",
            why="证据显示 Alpha score_value 为 91.0。",
            evidence_bullets=["Alpha score_value 为 91.0。", "Beta score_value 为 83.0。"],
            recommendations=["优先复盘 Alpha。"],
            caveats=["当前只基于本次查询返回的数据。"],
        ),
        reviewer_result=_review("accept", language="zh"),
    )

    _assert_shape(answer)
    assert _contains_cjk(answer["headline"] + answer["direct_answer"] + answer["why"])


def test_composer_output_does_not_leak_reviewer_prompt_trace_or_sql():
    from agents.final_answer_composer import compose_final_answer

    answer = compose_final_answer(
        user_question="Which entity should we prioritize?",
        execution_result=_execution_result(),
        evidence_result={"validation_status": "validated"},
        draft_business_answer=_draft_answer(
            direct_answer="Prioritize Alpha. prompt_id=answer_reviewer trace_path=/tmp/trace SELECT * FROM internal_table",
            why="reviewer_result says accept.",
        ),
        reviewer_result=_review("accept"),
    )

    text = _answer_text(answer)
    assert "prompt_id" not in text
    assert "trace_path" not in text
    assert "SELECT" not in text
    assert "reviewer_result" not in text
