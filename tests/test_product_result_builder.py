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
    assert isinstance(answer["headline"], str)
    assert isinstance(answer["direct_answer"], str)
    assert isinstance(answer["why"], str)
    assert isinstance(answer["evidence_bullets"], list)
    assert isinstance(answer["recommendations"], list)
    assert isinstance(answer["caveats"], list)
    assert answer["confidence"] in {"low", "medium", "high"}


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


def test_empty_business_answer_returns_single_p16_contract():
    from workspaces.product_models import PRODUCT_RESULT_VERSION, empty_business_answer

    answer = empty_business_answer()

    assert PRODUCT_RESULT_VERSION == "p16.v1"
    _assert_new_business_answer_shape(answer)
    assert answer == {
        "headline": "",
        "direct_answer": "",
        "why": "",
        "evidence_bullets": [],
        "recommendations": [],
        "caveats": [],
        "confidence": "medium",
    }


def test_product_result_builder_splits_business_and_technical_fields():
    from workspaces.product_result_builder import build_product_analysis_result

    workspace_root = "/tmp/ws"
    raw = {
        "run_id": "run_1",
        "status": "completed",
        "workspace_root": workspace_root,
        "user_question": "哪个渠道该加预算？",
        "question_understanding": {
            "strategy": "llm_candidate",
            "intent": {"metric": "revenue", "dimension": "channel"},
        },
        "final_answer": "建议加大 paid_search，因为收入最高且 ROI 领先。",
        "generated_sql": "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
        "execution_result": {
            "success": True,
            "columns": ["channel", "revenue"],
            "rows": [["paid_search", 200.0]],
        },
        "evidence_result": {
            "data_supported_findings": [{"claim": "paid_search revenue is 200.0"}],
            "validation_status": "validated",
        },
        "visualization_trace": {
            "artifact_path": "/tmp/ws/runs/run_1/charts/channel.png",
            "provider_called": True,
            "chart_spec": {
                "title": "渠道收入",
                "unit": "元",
                "business_annotation": "paid_search 收入领先。",
            },
        },
        "trace_path": "/tmp/ws/runs/run_1/trace.json",
        "insight": {"source": "deterministic", "provider_called": False},
    }

    product = build_product_analysis_result(raw, workspace_id="ws_1", workspace_root=workspace_root)

    assert product["version"] == "p16.v1"
    assert product["workspace_id"] == "ws_1"
    assert product["run_id"] == "run_1"
    assert product["status"] == "completed"
    assert product["question_thread"]["original_question"] == "哪个渠道该加预算？"
    assert product["question_thread"]["system_understanding"]
    answer = product["business_answer"]
    _assert_new_business_answer_shape(answer)
    assert answer["headline"]
    assert answer["direct_answer"] == raw["final_answer"]
    assert "paid_search" in answer["why"]
    assert answer["evidence_bullets"] == ["第 1 行：渠道 为 paid_search，收入 为 200.0。"]
    assert answer["recommendations"] == [raw["final_answer"]]
    assert "raw_rows" not in product["business_answer"]
    assert "summary" not in answer
    assert "next_actions" not in answer
    assert "source" not in answer
    assert "quality_flags" not in answer
    assert "SELECT channel" not in _business_answer_text(answer)
    assert "provider_called" not in _business_answer_text(answer)
    assert product["evidence"]["table_preview"]["columns"] == ["channel", "revenue"]
    assert product["evidence"]["table_preview"]["rows"] == [["paid_search", 200.0]]
    assert product["evidence"]["evidence_notes"] == ["paid_search revenue is 200.0"]
    assert product["evidence"]["validation_status"] == "validated"
    assert product["chart_artifacts"][0]["path"].endswith("channel.png")
    assert product["chart_artifacts"][0]["path"] == "runs/run_1/charts/channel.png"
    assert product["chart_artifacts"][0]["url"] == "/api/workspaces/ws_1/artifacts/runs/run_1/charts/channel.png"
    assert product["chart_artifacts"][0]["unit"] == "元"
    assert product["chart_artifacts"][0]["business_annotation"] == "paid_search 收入领先。"
    assert product["technical_details"]["sql"].startswith("SELECT channel")
    assert product["technical_details"]["raw_rows"] == [["paid_search", 200.0]]
    assert product["technical_details"]["trace_path"].endswith("trace.json")
    assert product["technical_details"]["provider_metadata"]["insight"]["source"] == "deterministic"
    assert "sql" not in product["business_answer"]
    assert "trace_path" not in product["business_answer"]
    assert "provider_metadata" not in product["business_answer"]


def test_business_answer_rebuilds_internal_report_prompt_leaks():
    from workspaces.product_result_builder import build_business_answer

    raw = {
        "status": "completed",
        "user_question": (
            "这是自动报告内部 section，不是用户澄清轮次。"
            "本节意图提示：metric=收入; dimension=渠道。"
            "本节问题：汇总最近 90 天收入最高的渠道。"
        ),
        "business_answer": {
            "headline": "已完成问题「这是自动报告内部 section」的查询。",
            "direct_answer": "本节问题：汇总最近 90 天收入最高的渠道。email 收入最高。",
            "why": "本节意图提示：metric=收入; dimension=渠道。",
            "evidence_bullets": ["email 收入为 44548.53。"],
            "recommendations": [],
            "caveats": [],
            "confidence": "medium",
        },
        "final_answer": "已完成问题「这是自动报告内部 section」的查询，共返回 1 行结果。",
        "execution_result": {
            "success": True,
            "columns": ["channel", "total_revenue"],
            "rows": [["email", 44548.53]],
        },
        "evidence_result": {},
    }

    answer = build_business_answer(raw)
    text = _business_answer_text(answer)

    assert "这是自动报告内部 section" not in text
    assert "本节意图提示" not in text
    assert "本节问题" not in text
    assert "原问题" not in text
    assert "email" in text


def test_chinese_business_answer_rebuilds_english_evidence_notes_from_rows():
    from workspaces.product_result_builder import build_business_answer

    raw = {
        "status": "completed",
        "user_question": "最近 90 天收入最高的渠道是哪个？",
        "final_answer": "最近 90 天收入最高的渠道是 email，收入为 44548.53。",
        "execution_result": {
            "success": True,
            "columns": ["channel", "total_revenue"],
            "rows": [["email", 44548.53]],
        },
        "evidence_result": {
            "data_supported_findings": [
                {"claim": "email channel total revenue is $44,548.53 in recent 90 days"}
            ]
        },
    }

    answer = build_business_answer(raw)

    assert answer["evidence_bullets"] == ["第 1 行：渠道 为 email，总收入 为 44548.53。"]
    assert "total revenue is" not in _business_answer_text(answer)


def test_product_result_builder_handles_clarification_and_chart_paths():
    from workspaces.product_result_builder import build_product_analysis_result

    workspace_root = "/tmp/ws"
    raw = {
        "run_id": "run_2",
        "status": "waiting_for_clarification",
        "workspace_root": workspace_root,
        "user_question": "帮我分析渠道表现",
        "question_understanding": {"strategy": "clarify", "reason": "time range missing"},
        "clarification_questions": ["你希望分析哪个时间范围？"],
        "clarification_answer": "最近 90 天",
        "resolved_question": "分析最近 90 天各渠道表现并给出预算建议。",
        "pending_run_id": "pending_1",
        "execution_result": {"columns": ["channel"], "rows": [["email"]]},
        "chart_paths": ["/tmp/ws/runs/run_2/charts/channel.png"],
    }

    product = build_product_analysis_result(raw, workspace_id="ws_1", workspace_root=workspace_root)

    assert product["question_thread"] == {
        "original_question": "帮我分析渠道表现",
        "system_understanding": "系统已识别：当前问题还需要补充更多分析条件。",
        "clarification_question": "你希望分析哪个时间范围？",
        "clarification_answer": "最近 90 天",
        "resolved_question": "分析最近 90 天各渠道表现并给出预算建议。",
        "pending_run_id": "pending_1",
        "status": "waiting_for_clarification",
    }
    assert product["chart_artifacts"][0]["path"].endswith("channel.png")
    assert product["chart_artifacts"][0]["url"] == "/api/workspaces/ws_1/artifacts/runs/run_2/charts/channel.png"
    assert product["chart_artifacts"][0]["rendering_status"] == "rendered"


def test_product_result_builder_continuation_thread_preserves_resolved_business_intent():
    from workspaces.product_result_builder import build_product_analysis_result

    raw = {
        "run_id": "run_3",
        "status": "completed",
        "original_question": "帮我分析渠道表现，看看哪个渠道该加预算。",
        "question_understanding": {"strategy": "clarify", "reason": "time range missing"},
        "clarification_questions": ["你希望分析哪个时间范围？"],
        "clarification_answer": "最近 90 天",
        "resolved_question": "分析最近 90 天各渠道的收入、订单数、投放成本和 ROI，并给出预算调整建议。",
        "pending_run_id": "pending_1",
        "final_answer": "建议优先增加 paid_search 预算。",
    }

    product = build_product_analysis_result(raw, workspace_id="ws_1")
    thread = product["question_thread"]

    assert thread["status"] == "completed"
    assert thread["original_question"] == "帮我分析渠道表现，看看哪个渠道该加预算。"
    assert thread["clarification_answer"] == "最近 90 天"
    assert "渠道" in thread["resolved_question"]
    assert "预算" in thread["resolved_question"]
    assert "最近 90 天" in thread["resolved_question"]


def test_product_result_builder_turns_schema_review_failure_into_business_answer():
    from workspaces.product_result_builder import build_product_analysis_result

    raw = {
        "run_id": "run_failed",
        "status": "failed",
        "user_question": "按商品看看最近 30 天收入",
        "final_answer": (
            "Review rejected before execution: Unknown table: products; "
            "Unknown column: order_items.quantity"
        ),
        "generated_sql": "SELECT p.product_name FROM products p LIMIT 20",
        "review_result": {
            "approved": False,
            "issues": ["Unknown table: products", "Unknown column: order_items.quantity"],
        },
        "schema_repair": {
            "attempted": True,
            "succeeded": False,
            "repair_rejection_reasons": ["Unknown table: products"],
        },
    }

    product = build_product_analysis_result(raw, workspace_id="ws_1")
    answer = product["business_answer"]

    _assert_new_business_answer_shape(answer)
    assert answer["headline"] == "当前数据无法支持这次查询"
    assert "不存在的表或字段" in answer["direct_answer"]
    assert "没有执行未通过审核的 SQL" in " ".join(answer["caveats"])
    assert "Unknown table" not in _business_answer_text(answer)
    assert "Unknown column" not in _business_answer_text(answer)
    assert any("当前数据已包含" in item for item in answer["recommendations"])
    assert any(log["name"] == "review_result" for log in product["technical_details"]["validation_logs"])
    assert any(log["name"] == "schema_repair" for log in product["technical_details"]["validation_logs"])
    assert "Unknown table: products" in str(product["technical_details"]["validation_logs"])


def test_product_result_builder_preserves_clean_provider_business_answer():
    from workspaces.product_result_builder import build_business_answer

    provider_answer = {
        "headline": "email 渠道收入最高",
        "direct_answer": "最近 90 天 email 渠道收入最高，达到 44548.53。",
        "why": "证据显示 email 渠道收入为 44548.53，高于其他渠道。",
        "evidence_bullets": ["email 渠道收入为 44548.53。"],
        "recommendations": ["复盘 email 渠道的转化动作，并评估是否扩大有效触达。"],
        "caveats": ["当前结论只覆盖本次查询返回的数据。"],
        "confidence": "high",
    }

    answer = build_business_answer(
        {
            "user_question": "最近90天哪个渠道收入最高？",
            "business_answer": provider_answer,
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["email", 44548.53]],
            },
            "evidence_result": {
                "validation_status": "validated",
                "data_supported_findings": [{"claim": "email 渠道收入为 44548.53。"}],
            },
        }
    )

    assert answer == provider_answer


def test_clean_provider_business_answer_gets_minimum_recommendation_and_caveat():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近90天哪个渠道收入最高，为什么？",
            "business_answer": {
                "headline": "email 渠道收入最高",
                "direct_answer": "最近 90 天 email 渠道收入最高，达到 44548.53。",
                "why": "证据显示 email 渠道收入为 44548.53，高于其他渠道。",
                "evidence_bullets": ["email 渠道收入为 44548.53。"],
                "recommendations": [],
                "caveats": [],
                "confidence": "high",
            },
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["email", 44548.53]],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_new_business_answer_shape(answer)
    assert answer["recommendations"]
    assert answer["caveats"]
    assert "email" in " ".join(answer["recommendations"])
    assert any("本次查询" in caveat or "时间范围" in caveat for caveat in answer["caveats"])


def test_product_result_builder_rejects_provider_business_answer_with_technical_leak():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "哪个渠道收入最高？",
            "business_answer": {
                "headline": "email 渠道收入最高",
                "direct_answer": "建议看 email。trace_id=abc123 provider_metadata={model: deepseek}",
                "why": "SELECT channel, SUM(revenue) FROM orders GROUP BY channel",
                "evidence_bullets": ["email 渠道收入为 100。"],
                "recommendations": ["继续看 prompt_tokens 和 latency_ms。"],
                "caveats": [],
                "confidence": "medium",
            },
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["email", 100.0]],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_new_business_answer_shape(answer)
    business_text = _business_answer_text(answer)
    assert "trace_id" not in business_text
    assert "provider_metadata" not in business_text
    assert "SELECT" not in business_text
    assert "prompt_tokens" not in business_text
    assert "latency_ms" not in business_text
    assert answer["direct_answer"].startswith("已完成本轮查询")


def test_product_result_builder_rewrites_english_answer_for_chinese_question_from_evidence():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_language_answer",
            "status": "completed",
            "user_question": "最近90天哪个渠道收入最高？为什么？",
            "final_answer": (
                "Based on the data, email is the top revenue channel for the last 90 days, "
                "bringing in $44,548.53."
            ),
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["email", 44548.53]],
                "row_count": 1,
            },
            "business_answer": {
                "headline": "Based on the data, email is the top revenue channel.",
                "summary": (
                    "Based on the data, email is the top revenue channel for the last 90 days, "
                    "bringing in $44,548.53."
                ),
            },
            "insight": {"source": "provider"},
        },
        workspace_id="ws_language_answer",
    )

    answer = product["business_answer"]
    _assert_new_business_answer_shape(answer)
    assert answer["headline"].startswith("已完成本轮查询")
    assert answer["direct_answer"].startswith("已完成本轮查询")
    assert "证据表第一行显示" in answer["why"]
    assert "Based on the data" not in answer["headline"]
    assert "Based on the data" not in answer["direct_answer"]
    assert "Based on the data" not in answer["why"]


def test_product_result_builder_headline_does_not_split_decimal_values():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "final_answer": (
                "为了提高整体收益，建议优先增加对email渠道的投入，因其ROI（0.379）最高，"
                "且花费相对较低。相反，paid_search渠道ROI最低。"
            )
        }
    )

    assert "ROI（0.379）" in answer["headline"]
    assert not answer["headline"].endswith("ROI（0.")


def test_business_answer_with_weak_or_missing_evidence_does_not_force_recommendations():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "哪个渠道该加预算？",
            "final_answer": "建议加大 paid_search 预算。",
            "execution_result": {"success": True, "columns": ["channel"], "rows": []},
            "evidence_result": {"validation_status": "not_validated", "data_supported_findings": []},
        }
    )

    _assert_new_business_answer_shape(answer)
    assert answer["recommendations"] == []
    assert answer["confidence"] == "low"
    assert answer["caveats"]
    assert any("证据" in caveat or "数据" in caveat for caveat in answer["caveats"])


def test_budget_question_evidence_fallback_does_not_force_first_row_when_metrics_conflict():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "分析最近 90 天各渠道收入、投放成本和 ROI，告诉我哪个渠道应该加预算，并生成图表。",
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue", "spend", "roi"],
                "rows": [
                    ["email", 23534.0, 2290.5, 10.27],
                    ["paid_search", 34848.0, 9703.5, 3.59],
                    ["social", 18191.0, 5748.0, 3.21],
                    ["affiliate", 12931.0, 4134.5, 3.13],
                ],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_new_business_answer_shape(answer)
    text = _business_answer_text(answer)
    assert "当前证据不足以支持该结论" in text
    assert "email" not in " ".join(answer["recommendations"])
    assert answer["confidence"] == "low"
    assert any("证据" in caveat or "口径" in caveat for caveat in answer["caveats"])


def test_product_result_builder_localizes_common_metric_fields_in_main_answer():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近 90 天哪个渠道收入最高？请带上订单数、客单价和投放成本。",
            "final_answer": "已完成本轮查询。",
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue", "order_count", "avg_order_value", "total_spend"],
                "rows": [["email", 44548.53, 120, 371.24, 2290.5]],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    text = _business_answer_text(answer)
    assert "渠道 为 email" in text
    assert "总收入 为 44548.53" in text
    assert "订单数 为 120" in text
    assert "客单价 为 371.24" in text
    assert "投放成本 为 2290.5" in text
    assert "total_revenue" not in text
    assert "order_count" not in text
    assert "avg_order_value" not in text
    assert "total_spend" not in text


def test_product_result_builder_uses_english_fallback_for_english_question():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "Which channel has the highest total_revenue?",
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue", "order_count", "avg_order_value"],
                "rows": [["email", 44548.53, 120, 371.24]],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    text = _business_answer_text(answer)
    assert answer["direct_answer"].startswith("The query returned 1 row")
    assert "The first evidence row shows:" in answer["why"]
    assert answer["evidence_bullets"] == [
        "Row 1: channel is email, total revenue is 44548.53, order count is 120, average order value is 371.24."
    ]
    assert "total revenue" in text
    assert "order count" in text
    assert "average order value" in text
    assert "证据表第一行显示" not in text
    assert "第 1 行" not in text
    assert "总收入" not in text
    assert "订单数" not in text
    assert "客单价" not in text
