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


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(text or ""))


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
        "why": "当前数据中，segment 为 成长型团队，total_revenue 为 2798216.93，order_count 为 628。",
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
        and "当前数据中，segment 为 成长型团队" in answer["why"]
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
        "why": "当前数据中，channel 为 自然流量，roi 为 16.22。",
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


def test_recommendation_entity_realigns_to_ranked_evidence_entity_for_chinese_question():
    from workspaces.product_result_builder import build_business_answer

    execution_result = {
        "success": True,
        "columns": ["market", "total_value", "conversion_rate"],
        "rows": [
            ["北区", 980000.0, 0.18],
            ["南区", 420000.0, 0.11],
        ],
    }
    provider_answer = {
        "headline": "建议优先投入南区",
        "direct_answer": "建议优先投入南区，因为它最值得加资源。",
        "why": "当前数据中，market 为 北区，total_value 为 980000.0，conversion_rate 为 0.18。",
        "evidence_bullets": [
            "北区 total_value 为 980000.0，conversion_rate 为 0.18。",
            "南区 total_value 为 420000.0，conversion_rate 为 0.11。",
        ],
        "recommendations": ["把下一轮资源优先给南区。"],
        "caveats": [],
        "confidence": "high",
    }

    answer = build_business_answer(
        {
            "user_question": "最近 90 天哪个市场最值得加资源？",
            "business_answer": provider_answer,
            "execution_result": execution_result,
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_business_answer_shape(answer)
    decision_text = " ".join([answer["headline"], answer["direct_answer"], answer["why"], *answer["recommendations"]])
    assert "北区" in answer["direct_answer"]
    assert "北区" in answer["why"]
    assert "北区" in " ".join(answer["recommendations"])
    assert "南区" not in decision_text
    assert "当前证据不足以支持该结论" not in decision_text
    assert _contains_cjk(answer["headline"] + answer["direct_answer"] + answer["why"])


def test_unsupported_recommendation_entity_is_downgraded_to_insufficient_evidence():
    from workspaces.product_result_builder import build_business_answer

    execution_result = {
        "success": True,
        "columns": ["region", "score_value"],
        "rows": [
            ["华北", 91.0],
            ["华南", 83.0],
        ],
    }
    provider_answer = {
        "headline": "建议优先投入华东",
        "direct_answer": "建议优先投入华东，因为它表现最好。",
        "why": "当前数据中，region 为 华北，score_value 为 91.0。",
        "evidence_bullets": ["华北 score_value 为 91.0。", "华南 score_value 为 83.0。"],
        "recommendations": ["把预算加到华东。"],
        "caveats": [],
        "confidence": "high",
    }

    answer = build_business_answer(
        {
            "user_question": "哪个区域最值得加预算？",
            "business_answer": provider_answer,
            "execution_result": execution_result,
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_business_answer_shape(answer)
    text = _answer_text(answer)
    assert "当前证据不足以支持该结论" in text
    assert "华东" not in answer["headline"] + answer["direct_answer"] + " ".join(answer["recommendations"])
    assert answer["confidence"] == "low"
    assert any("证据" in caveat for caveat in answer["caveats"])


def test_why_and_evidence_entities_are_aligned_with_supported_decision_entity():
    from workspaces.product_result_builder import build_business_answer

    execution_result = {
        "success": True,
        "columns": ["market", "score_value"],
        "rows": [
            ["北区", 91.0],
            ["南区", 72.0],
        ],
    }
    provider_answer = {
        "headline": "建议优先投入北区",
        "direct_answer": "建议优先投入北区，因为它在当前结果中表现最好。",
        "why": "南区更值得投入，因为它后续增长空间更大。",
        "evidence_bullets": ["南区 score_value 为 72.0，但更值得追加资源。"],
        "recommendations": ["把下一轮资源优先给北区。"],
        "caveats": [],
        "confidence": "high",
    }

    answer = build_business_answer(
        {
            "user_question": "最近 90 天哪个市场最值得加资源？",
            "business_answer": provider_answer,
            "execution_result": execution_result,
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_business_answer_shape(answer)
    aligned_text = " ".join(
        [
            answer["direct_answer"],
            answer["why"],
            *answer["evidence_bullets"],
            *answer["recommendations"],
        ]
    )
    if "当前证据不足以支持该结论" not in _answer_text(answer):
        assert "北区" in answer["direct_answer"]
        assert "北区" in answer["why"]
        assert "北区" in " ".join(answer["evidence_bullets"])
        assert "北区" in " ".join(answer["recommendations"])
        assert "南区更值得" not in aligned_text
        assert "南区 score_value" not in aligned_text
    else:
        assert answer["confidence"] == "low"
        assert not answer["recommendations"] or all("北区" not in item and "南区" not in item for item in answer["recommendations"])


def test_plain_why_and_evidence_entity_conflict_is_corrected_or_downgraded():
    from workspaces.product_result_builder import build_business_answer

    execution_result = {
        "success": True,
        "columns": ["market", "score_value"],
        "rows": [
            ["北区", 91.0],
            ["南区", 72.0],
        ],
    }
    provider_answer = {
        "headline": "建议优先投入北区",
        "direct_answer": "建议优先投入北区，因为它在当前结果中表现最好。",
        "why": "当前数据中，market 为 南区，score_value 为 72.0。",
        "evidence_bullets": ["南区 score_value 为 72.0。"],
        "recommendations": ["把下一轮资源优先给北区。"],
        "caveats": [],
        "confidence": "high",
    }

    answer = build_business_answer(
        {
            "user_question": "最近 90 天哪个市场最值得加资源？",
            "business_answer": provider_answer,
            "execution_result": execution_result,
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_business_answer_shape(answer)
    text = _answer_text(answer)
    if "当前证据不足以支持该结论" in text:
        assert answer["confidence"] == "low"
    else:
        assert "北区" in answer["why"]
        assert "北区" in " ".join(answer["evidence_bullets"])
        assert "北区" in " ".join(answer["recommendations"])
    assert answer["why"] != provider_answer["why"]
    assert answer["evidence_bullets"] != provider_answer["evidence_bullets"]
    assert not (
        "建议优先投入北区" in " ".join([answer["headline"], answer["direct_answer"], *answer["recommendations"]])
        and answer["why"] == provider_answer["why"]
        and answer["evidence_bullets"] == provider_answer["evidence_bullets"]
    )


def test_plain_english_why_and_evidence_entity_conflict_is_corrected_or_downgraded():
    from workspaces.product_result_builder import build_business_answer

    execution_result = {
        "success": True,
        "columns": ["market", "score_value"],
        "rows": [
            ["North", 91.0],
            ["South", 72.0],
        ],
    }
    provider_answer = {
        "headline": "Recommend prioritizing North",
        "direct_answer": "Recommend prioritizing North because it performs best in the current result.",
        "why": "The first evidence row shows: market is South and score_value is 72.0.",
        "evidence_bullets": ["South score_value is 72.0."],
        "recommendations": ["Prioritize North for the next resource decision."],
        "caveats": [],
        "confidence": "high",
    }

    answer = build_business_answer(
        {
            "user_question": "Which market is worth prioritizing for the next resource decision?",
            "business_answer": provider_answer,
            "execution_result": execution_result,
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_business_answer_shape(answer)
    text = _answer_text(answer)
    assert not _contains_cjk(text)
    if "Current evidence is insufficient for that conclusion" in text:
        assert answer["confidence"] == "low"
    else:
        assert "North" in answer["why"]
        assert "North" in " ".join(answer["evidence_bullets"])
        assert "North" in " ".join(answer["recommendations"])
    assert answer["why"] != provider_answer["why"]
    assert answer["evidence_bullets"] != provider_answer["evidence_bullets"]
    assert not (
        "North" in " ".join([answer["headline"], answer["direct_answer"], *answer["recommendations"]])
        and answer["why"] == provider_answer["why"]
        and answer["evidence_bullets"] == provider_answer["evidence_bullets"]
    )


def test_unsupported_decision_entity_not_in_execution_result_is_downgraded_even_when_wording_varies():
    from workspaces.product_result_builder import build_business_answer

    execution_result = {
        "success": True,
        "columns": ["region", "score_value"],
        "rows": [
            ["华北", 91.0],
            ["华南", 83.0],
        ],
    }
    provider_answer = {
        "headline": "华东是唯一应该追加预算的区域",
        "direct_answer": "华东是唯一应该追加预算的区域，因为它最值得增长投入。",
        "why": "华东增长质量最好。",
        "evidence_bullets": ["华东 score_value 为 99.0。"],
        "recommendations": ["下一轮预算集中投向华东。"],
        "caveats": [],
        "confidence": "high",
    }

    answer = build_business_answer(
        {
            "user_question": "哪个区域最值得加预算？",
            "business_answer": provider_answer,
            "execution_result": execution_result,
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_business_answer_shape(answer)
    assert "当前证据不足以支持该结论" in _answer_text(answer)
    assert "华东" not in answer["headline"] + answer["direct_answer"] + answer["why"] + " ".join(answer["recommendations"])
    assert answer["confidence"] == "low"


def test_multi_metric_tradeoff_is_not_forced_to_first_row_alignment():
    from workspaces.product_result_builder import build_business_answer

    execution_result = {
        "success": True,
        "columns": ["market", "total_value", "conversion_rate"],
        "rows": [
            ["北区", 980000.0, 0.18],
            ["南区", 420000.0, 0.31],
        ],
    }
    provider_answer = {
        "headline": "北区收入规模更大，但南区转化率更高",
        "direct_answer": "如果看收入规模，北区领先；如果看转化率，南区更强，需要按判断口径取舍。",
        "why": "北区 total_value 为 980000.0，南区 conversion_rate 为 0.31。",
        "evidence_bullets": [
            "北区 total_value 为 980000.0。",
            "南区 conversion_rate 为 0.31。",
        ],
        "recommendations": ["先明确是追求规模还是效率，再决定资源倾斜对象。"],
        "caveats": ["不同指标指向不同对象。"],
        "confidence": "medium",
    }

    answer = build_business_answer(
        {
            "user_question": "最近 90 天哪个市场最值得重点投入？请同时看收入和转化率。",
            "business_answer": provider_answer,
            "execution_result": execution_result,
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_business_answer_shape(answer)
    text = _answer_text(answer)
    assert "北区" in text
    assert "南区" in text
    assert any(marker in text for marker in ("取舍", "口径", "不同指标"))
    assert "当前证据最支持优先评估 北区" not in text


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
