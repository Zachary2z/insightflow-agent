from __future__ import annotations


REVIEW_KEYS = {
    "status",
    "language",
    "supported_entities",
    "unsupported_entities",
    "supported_metrics",
    "unsupported_metrics",
    "issues",
    "revision_instructions",
    "confidence",
}


def _draft_answer(**overrides):
    answer = {
        "headline": "Alpha is the best option",
        "direct_answer": "Prioritize Alpha because it leads on the returned metric.",
        "why": "Alpha has score_value 91.0.",
        "evidence_bullets": ["Alpha score_value is 91.0.", "Beta score_value is 83.0."],
        "recommendations": ["Prioritize Alpha for the next resource decision."],
        "caveats": [],
        "confidence": "high",
    }
    answer.update(overrides)
    return answer


def _execution_result(columns=None, rows=None):
    return {
        "success": True,
        "columns": columns or ["entity_name", "score_value"],
        "rows": rows or [["Alpha", 91.0], ["Beta", 83.0]],
        "row_count": len(rows or [["Alpha", 91.0], ["Beta", 83.0]]),
    }


def _answer_text(answer: dict) -> str:
    return " ".join(
        [
            str(answer.get("headline") or ""),
            str(answer.get("direct_answer") or ""),
            str(answer.get("why") or ""),
            *[str(item) for item in answer.get("evidence_bullets") or []],
            *[str(item) for item in answer.get("recommendations") or []],
            *[str(item) for item in answer.get("caveats") or []],
        ]
    )


def test_answer_reviewer_structured_output_accepts_contract_shape():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "answer_reviewer",
        {
            "status": "revise",
            "language": "en",
            "supported_entities": ["Alpha"],
            "unsupported_entities": ["Gamma"],
            "supported_metrics": ["score_value"],
            "unsupported_metrics": [],
            "issues": [
                {
                    "type": "entity_mismatch",
                    "message": "Gamma is not present in the returned evidence.",
                    "affected_fields": ["recommendations"],
                }
            ],
            "revision_instructions": ["Remove Gamma or mark it as an unverified hypothesis."],
            "confidence": "medium",
        },
    )

    assert result["success"] is True
    assert set(result["content"]) == REVIEW_KEYS
    assert result["content"]["issues"][0]["type"] == "entity_mismatch"


def test_answer_reviewer_structured_output_rejects_final_answer_fields():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "answer_reviewer",
        {
            "status": "accept",
            "language": "en",
            "supported_entities": ["Alpha"],
            "unsupported_entities": [],
            "supported_metrics": ["score_value"],
            "unsupported_metrics": [],
            "issues": [],
            "revision_instructions": [],
            "confidence": "high",
            "business_answer": _draft_answer(),
        },
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "business_answer" in result["error"]


def test_reviewer_flags_draft_entity_not_present_in_evidence():
    from agents.answer_reviewer import review_answer

    review = review_answer(
        user_question="Which entity should we prioritize?",
        execution_result=_execution_result(),
        evidence_result={"validation_status": "validated"},
        draft_business_answer=_draft_answer(
            headline="Gamma is the best option",
            direct_answer="Prioritize Gamma because it looks strongest.",
            recommendations=["Prioritize Gamma for the next resource decision."],
        ),
    )

    assert set(review) == REVIEW_KEYS
    assert review["status"] in {"revise", "downgrade_to_insufficient_evidence"}
    assert "Gamma" in review["unsupported_entities"]
    assert any(issue["type"] in {"entity_mismatch", "unsupported_claim"} for issue in review["issues"])


def test_reviewer_flags_metric_not_present_in_execution_or_evidence():
    from agents.answer_reviewer import review_answer

    review = review_answer(
        user_question="Which entity should we prioritize?",
        execution_result=_execution_result(columns=["entity_name", "score_value"], rows=[["Alpha", 91.0], ["Beta", 83.0]]),
        evidence_result={"validation_status": "validated"},
        draft_business_answer=_draft_answer(
            direct_answer="Prioritize Alpha because margin_rate is strongest.",
            why="Alpha has margin_rate 0.42.",
            evidence_bullets=["Alpha margin_rate is 0.42."],
            recommendations=["Use margin_rate as the priority metric."],
        ),
    )

    assert review["status"] in {"revise", "downgrade_to_insufficient_evidence"}
    assert "margin_rate" in review["unsupported_metrics"]
    assert any(issue["type"] == "metric_mismatch" for issue in review["issues"])


def test_reviewer_flags_missing_tradeoff_when_metrics_point_to_different_leaders():
    from agents.answer_reviewer import review_answer

    review = review_answer(
        user_question="Which entity is best across score and efficiency?",
        execution_result=_execution_result(
            columns=["entity_name", "score_value", "efficiency_rate"],
            rows=[["Alpha", 91.0, 0.20], ["Beta", 83.0, 0.42]],
        ),
        evidence_result={"validation_status": "validated"},
        draft_business_answer=_draft_answer(
            headline="Alpha is clearly the best entity",
            direct_answer="Alpha is the best entity overall.",
            why="Alpha has the highest score_value.",
            evidence_bullets=["Alpha score_value is 91.0.", "Beta efficiency_rate is 0.42."],
            recommendations=["Prioritize Alpha."],
        ),
    )

    assert review["status"] == "revise"
    assert any(issue["type"] == "tradeoff_missing" for issue in review["issues"])
    assert any("tradeoff" in instruction.lower() or "decision basis" in instruction.lower() for instruction in review["revision_instructions"])


def test_reviewer_accepts_answer_aligned_with_evidence():
    from agents.answer_reviewer import review_answer

    answer = _draft_answer()
    review = review_answer(
        user_question="Which entity should we prioritize?",
        execution_result=_execution_result(),
        evidence_result={"validation_status": "validated", "data_supported_findings": [{"claim": "Alpha score_value is 91.0."}]},
        draft_business_answer=answer,
    )

    assert review["status"] == "accept"
    assert review["unsupported_entities"] == []
    assert review["unsupported_metrics"] == []
    assert review["issues"] == []
    assert "Alpha" in review["supported_entities"]
    assert "score_value" in review["supported_metrics"]


def test_reviewer_does_not_expose_provider_parameter():
    import inspect

    from agents.answer_reviewer import review_answer

    assert "provider" not in inspect.signature(review_answer).parameters
