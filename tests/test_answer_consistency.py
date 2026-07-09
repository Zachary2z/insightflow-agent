from __future__ import annotations

import importlib.util


BUSINESS_ANSWER_KEYS = {
    "headline",
    "direct_answer",
    "why",
    "evidence_bullets",
    "recommendations",
    "caveats",
    "confidence",
}


def _business_answer_text(answer: dict) -> str:
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


def _valid_business_answer(**overrides) -> dict:
    answer = {
        "headline": "北区收入领先",
        "direct_answer": "北区收入领先，但预算动作需要补充成本证据。",
        "why": "BusinessAnswerAgent 已基于证据账本说明收入事实和边界。",
        "evidence_bullets": ["北区收入为 980000.0。"],
        "recommendations": ["补齐成本和转化数据后再判断预算动作。"],
        "caveats": ["当前结论只基于证据账本。"],
        "confidence": "medium",
    }
    answer.update(overrides)
    return answer


def test_answer_consistency_rewriter_module_is_removed():
    assert importlib.util.find_spec("workspaces.answer_consistency") is None


def test_final_answer_composer_module_is_removed():
    assert importlib.util.find_spec("agents.final_answer_composer") is None


def test_safe_chart_annotation_scrubs_internal_runtime_leaks():
    from workspaces.chart_annotation_safety import safe_chart_annotation

    safe = safe_chart_annotation(
        annotation="北区收入领先，建议结合成本继续观察。",
        business_answer=_valid_business_answer(),
        execution_result={"success": True, "rows": [["北区", 980000.0]]},
    )
    leaked = safe_chart_annotation(
        annotation="task_id=core_fact trace_path=/tmp/run SELECT * FROM internal_table",
        business_answer=_valid_business_answer(),
        execution_result={"success": True, "rows": [["北区", 980000.0]]},
    )

    assert safe == "北区收入领先，建议结合成本继续观察。"
    assert leaked == ""


def test_product_result_builder_preserves_provider_answer_without_row_rewrite():
    from workspaces.product_result_builder import build_product_analysis_result

    provider_answer = _valid_business_answer(
        headline="建议优先投入南区",
        direct_answer="建议优先投入南区，因为模型判断其后续增长空间更大。",
        why="BusinessAnswerAgent 基于证据账本做出了该判断。",
        evidence_bullets=["北区收入为 980000.0。", "南区收入为 420000.0。"],
        recommendations=["把下一轮资源优先给南区。"],
        confidence="medium",
    )

    product = build_product_analysis_result(
        {
            "run_id": "run_no_rewrite",
            "status": "completed",
            "user_question": "最近 90 天哪个市场最值得加资源？",
            "business_answer": provider_answer,
            "execution_result": {
                "success": True,
                "columns": ["market", "total_value"],
                "rows": [["北区", 980000.0], ["南区", 420000.0]],
            },
            "evidence_result": {"validation_status": "validated"},
        },
        workspace_id="ws_no_rewrite",
    )

    assert set(product["business_answer"]) == BUSINESS_ANSWER_KEYS
    assert product["business_answer"] == provider_answer


def test_product_result_builder_missing_answer_does_not_compose_from_raw_rows():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_missing_answer",
            "status": "completed",
            "user_question": "最近 90 天哪个市场收入最高？",
            "execution_result": {
                "success": True,
                "columns": ["market", "total_value"],
                "rows": [["北区", 980000.0], ["南区", 420000.0]],
            },
            "evidence_result": {"validation_status": "validated"},
        },
        workspace_id="ws_missing_answer",
    )

    text = _business_answer_text(product["business_answer"])
    assert "北区" not in text
    assert "南区" not in text
    assert "980000" not in text
    assert "排在第一" not in text
    assert "业务回答缺失" in text
    assert product["business_answer"]["confidence"] == "low"


def test_chart_annotation_safety_does_not_realign_or_generate_business_advice():
    from workspaces.chart_annotation_safety import safe_chart_annotation

    annotation = safe_chart_annotation(
        annotation="南区更适合加资源。",
        business_answer=_valid_business_answer(direct_answer="北区收入领先。"),
        execution_result={
            "success": True,
            "columns": ["market", "total_value"],
            "rows": [["北区", 980000.0], ["南区", 420000.0]],
        },
    )

    assert annotation == "南区更适合加资源。"
