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


def _assert_business_answer_shape(answer: dict) -> None:
    assert set(answer) == BUSINESS_ANSWER_KEYS
    assert answer["confidence"] in {"low", "medium", "high"}


def test_multi_metric_best_question_returns_tradeoff_instead_of_conflicting_single_winner():
    from workspaces.product_result_builder import build_business_answer

    execution_result = {
        "success": True,
        "columns": ["segment", "total_revenue", "order_count", "avg_revenue_per_order"],
        "rows": [
            ["成长型团队", 2798216.93, 628, 4455.76],
            ["高价值企业", 2158510.79, 340, 6348.56],
        ],
    }
    provider_answer = {
        "headline": "高价值企业最值得重点运营",
        "direct_answer": "高价值企业最值得重点运营，因为它的客单价最高。",
        "why": "证据表第一行显示：segment 为 成长型团队，total_revenue 为 2798216.93，order_count 为 628。",
        "evidence_bullets": [
            "成长型团队收入为 2798216.93，订单量为 628。",
            "高价值企业客单价为 6348.56。",
        ],
        "recommendations": ["优先把运营资源投入高价值企业。"],
        "caveats": [],
        "confidence": "high",
    }

    answer = build_business_answer(
        {
            "user_question": "按客户分群看收入、订单量和客单价，哪个分群最值得重点运营？",
            "business_answer": provider_answer,
            "execution_result": execution_result,
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_business_answer_shape(answer)
    text = _answer_text(answer)
    assert "成长型团队" in text
    assert "高价值企业" in text
    assert any(marker in text for marker in ("取舍", "权衡", "口径", "如果目标", "按收入", "按客单价"))
    assert "total_revenue=" not in text
    assert "order_count=" not in text
    assert "avg_revenue_per_order=" not in text
    assert "e+" not in text.lower()
    assert "按 收入 看" not in text
    assert " 领先" not in text
    assert "2,798,216.93" in text
    assert any(marker in text for marker in ("收入", "total_revenue"))
    assert any(marker in text for marker in ("订单", "order_count"))
    assert any(marker in text for marker in ("客单价", "avg_revenue_per_order"))
    assert not (
        "高价值企业最值得重点运营" in answer["headline"] + answer["direct_answer"]
        and "证据表第一行显示：segment 为 成长型团队" in answer["why"]
        and not any(marker in text for marker in ("取舍", "权衡", "口径", "如果目标"))
    )


def test_english_tradeoff_answer_uses_english_metric_labels_and_readable_numbers():
    from workspaces.product_result_builder import build_business_answer

    execution_result = {
        "success": True,
        "columns": ["segment", "total_revenue", "order_count", "avg_revenue_per_order"],
        "rows": [
            ["Growth Team", 2798216.93, 628, 4455.76],
            ["Enterprise", 2158510.79, 340, 6348.56],
        ],
    }
    provider_answer = {
        "headline": "Enterprise is the best segment to prioritize",
        "direct_answer": "Enterprise is the best segment because average revenue per order is highest.",
        "why": "The first evidence row shows segment Growth Team and total_revenue 2798216.93.",
        "evidence_bullets": [
            "Growth Team revenue is 2798216.93 and order count is 628.",
            "Enterprise average revenue per order is 6348.56.",
        ],
        "recommendations": ["Prioritize Enterprise."],
        "caveats": [],
        "confidence": "high",
    }

    answer = build_business_answer(
        {
            "user_question": "By segment, which segment is best to prioritize across revenue, orders, and average order revenue?",
            "business_answer": provider_answer,
            "execution_result": execution_result,
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_business_answer_shape(answer)
    text = _answer_text(answer)
    assert "Growth Team" in text
    assert "Enterprise" in text
    assert "2,798,216.93" in text
    assert "e+" not in text.lower()
    assert "收入" not in text
    assert "订单数" not in text
    assert "客单价" not in text
    assert "By revenue" in text
    assert "By orders" in text
    assert "By average order revenue" in text


def test_budget_reduction_question_with_single_row_does_not_generate_unsupported_recommendation():
    from workspaces.product_result_builder import build_business_answer

    execution_result = {
        "success": True,
        "columns": ["channel", "total_revenue", "total_spend", "roi"],
        "rows": [["自然流量", 452191.41, 26255.44, 16.22]],
    }
    provider_answer = {
        "headline": "自然流量 ROI 最高，付费渠道应减少预算",
        "direct_answer": "当前返回结果显示自然流量 ROI 最高，因此应减少付费渠道预算。",
        "why": "证据表第一行显示：channel 为 自然流量，roi 为 16.22。",
        "evidence_bullets": ["自然流量 ROI 为 16.22。"],
        "recommendations": ["减少付费渠道预算，并把预算转向自然流量。"],
        "caveats": [],
        "confidence": "high",
    }

    answer = build_business_answer(
        {
            "user_question": "最近90天哪个渠道 ROI 最高，哪个渠道应该减少预算？",
            "business_answer": provider_answer,
            "execution_result": execution_result,
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_business_answer_shape(answer)
    assert "自然流量" in answer["direct_answer"] + answer["why"] + " ".join(answer["evidence_bullets"])
    unsupported_action_text = " ".join(answer["recommendations"])
    assert not any(marker in unsupported_action_text for marker in ("减少", "降低", "转向", "削减", "加大", "增加"))
    assert any(marker in unsupported_action_text for marker in ("补充", "完整", "更多", "对比")) or answer["recommendations"] == []
    assert any(
        marker in " ".join(answer["caveats"])
        for marker in ("比较证据不足", "对比证据不足", "只有 1 行", "仅返回 1 行", "不足以判断")
    )


def test_chart_annotation_is_sanitized_when_it_names_a_different_winner():
    from workspaces.product_result_builder import build_product_analysis_result

    raw = {
        "run_id": "run_chart_conflict",
        "status": "completed",
        "workspace_root": "/tmp/ws",
        "user_question": "按客户分群看收入、订单量和客单价，哪个分群最值得重点运营？",
        "business_answer": {
            "headline": "成长型团队在规模上领先，但高价值企业客单价更高",
            "direct_answer": "如果按收入和订单规模，成长型团队更值得优先运营；如果按高客单价扩展，高价值企业需要单独评估。",
            "why": "证据显示成长型团队收入和订单量领先，高价值企业客单价领先。",
            "evidence_bullets": [
                "成长型团队收入为 2798216.93，订单量为 628。",
                "高价值企业客单价为 6348.56。",
            ],
            "recommendations": ["先明确重点运营口径，再决定资源倾斜对象。"],
            "caveats": ["不同指标指向不同分群，不能只用单一最高值下结论。"],
            "confidence": "medium",
        },
        "execution_result": {
            "success": True,
            "columns": ["segment", "total_revenue", "order_count", "avg_revenue_per_order"],
            "rows": [
                ["成长型团队", 2798216.93, 628, 4455.76],
                ["高价值企业", 2158510.79, 340, 6348.56],
            ],
        },
        "visualization_trace": {
            "artifact_path": "/tmp/ws/runs/run_chart_conflict/charts/segments.png",
            "chart_spec": {
                "title": "客户分群指标对比",
                "business_annotation": "高价值企业最值得重点运营，应该优先投入资源。",
            },
        },
    }

    product = build_product_analysis_result(raw, workspace_id="ws_1", workspace_root="/tmp/ws")
    annotation = product["chart_artifacts"][0]["business_annotation"]

    assert annotation
    assert not (
        "高价值企业" in annotation
        and any(marker in annotation for marker in ("最值得", "最佳", "应该", "建议", "优先投入"))
        and "成长型团队" not in annotation
    )
