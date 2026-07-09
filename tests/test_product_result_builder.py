import json

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


def _assert_missing_business_answer(answer):
    _assert_new_business_answer_shape(answer)
    text = _business_answer_text(answer)
    assert "业务回答缺失" in text or "Business answer missing" in text
    assert answer["confidence"] == "low"
    assert answer["evidence_bullets"] == []
    assert answer["recommendations"] == []


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
        "business_answer": {
            "headline": "paid_search 收入领先",
            "direct_answer": "建议加大 paid_search，因为收入最高且 ROI 领先。",
            "why": "这是业务回答代理根据证据账本生成的结论。",
            "evidence_bullets": ["paid_search 收入为 200.0。"],
            "recommendations": ["继续验证 paid_search 的 ROI。"],
            "caveats": ["当前结论只基于本轮证据账本。"],
            "confidence": "medium",
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
        "business_answer_generation": {"source": "deterministic", "provider_called": False},
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
    assert answer == raw["business_answer"]
    assert raw["final_answer"] not in answer["recommendations"]
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
    assert product["technical_details"]["provider_metadata"]["business_answer_generation"]["source"] == "deterministic"
    assert "sql" not in product["business_answer"]
    assert "trace_path" not in product["business_answer"]
    assert "provider_metadata" not in product["business_answer"]


def test_product_result_builder_preserves_existing_business_answer_without_consistency_rewrite():
    from workspaces.product_result_builder import build_product_analysis_result

    business_answer = {
        "headline": "按收入领先，但预算建议需要补证据",
        "direct_answer": "最近90天收入最高的是私域社群，收入为 300000.0；是否加预算还需要投放成本证据。",
        "why": "业务回答代理已基于证据账本说明收入事实和数据边界。",
        "evidence_bullets": ["私域社群收入为 300000.0。"],
        "recommendations": ["补齐投放成本后再判断预算动作。"],
        "caveats": ["当前结论只基于证据账本。"],
        "confidence": "medium",
    }

    product = build_product_analysis_result(
        {
            "run_id": "run_preserve_business_answer",
            "status": "completed",
            "user_question": "最近90天哪个渠道最值得加预算？",
            "business_answer": business_answer,
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["私域社群", 300000.0], ["搜索广告", 120000.0]],
            },
            "evidence_result": {"validation_status": "validated"},
        },
        workspace_id="ws_preserve_business_answer",
    )

    assert product["business_answer"] == business_answer


def test_product_result_builder_does_not_generate_business_answer_from_rows_when_missing():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_missing_business_answer",
            "status": "completed",
            "user_question": "最近90天哪个渠道收入最高？",
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["私域社群", 300000.0], ["搜索广告", 120000.0]],
            },
            "evidence_result": {"validation_status": "validated"},
        },
        workspace_id="ws_missing_business_answer",
    )

    answer_text = _business_answer_text(product["business_answer"])
    assert "私域社群" not in answer_text
    assert "300000" not in answer_text
    assert "最高" not in answer_text
    assert "排在第一" not in answer_text
    assert "业务回答缺失" in answer_text or "回答生成失败" in answer_text
    assert product["business_answer"]["confidence"] == "low"


def test_chart_skip_artifact_payload_hides_internal_chart_selection_details():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_chart_skip",
            "status": "completed",
            "user_question": "结合收入和客服问题生成图表",
            "business_answer": {
                "headline": "证据对象不适合合并画图",
                "direct_answer": "收入按渠道统计，客服问题按负责人和问题类型统计，不能合并为一张图。",
                "why": "两个证据组的业务对象和颗粒度不同。",
                "evidence_bullets": ["渠道收入和客服问题分别形成证据。"],
                "recommendations": ["分别查看收入证据和客服压力证据。"],
                "caveats": ["本轮不生成混合图表。"],
                "confidence": "medium",
            },
            "visualization_delivery_result": {
                "success": False,
                "rendering_status": "skipped",
                "skip_reason": "收入证据和客服压力证据的业务对象不同，不能在同一张图中混合。",
                "chart_input_source": "question_evidence_ledger.evidence_groups",
                "task_id": "core_fact_income_channel",
                "raw_sql": "SELECT * FROM orders",
                "provider_metadata": {"model": "internal"},
            },
            "visualization_trace": {
                "rendering_status": "skipped",
                "skip_reason": "收入证据和客服压力证据的业务对象不同，不能在同一张图中混合。",
                "chart_input_source": "question_evidence_ledger.evidence_groups",
            },
            "execution_result": {"success": True, "columns": ["task_id", "channel", "revenue"], "rows": []},
        },
        workspace_id="ws_chart_skip",
    )

    artifacts = product["chart_artifacts"]
    payload_text = json.dumps(artifacts, ensure_ascii=False)
    assert len(artifacts) == 1
    assert artifacts[0]["rendering_status"] == "skipped"
    assert artifacts[0]["skip_reason"] == "收入证据和客服压力证据的业务对象不同，不能在同一张图中混合。"
    assert "SELECT" not in payload_text
    assert "task_id" not in payload_text
    assert "core_fact_income_channel" not in payload_text
    assert "provider_metadata" not in payload_text


def test_product_result_builder_exposes_fact_payload_only_outside_main_answer():
    from workspaces.product_result_builder import build_product_analysis_result

    raw = {
        "run_id": "run_fact_payload",
        "status": "completed",
        "workspace_root": "/tmp/ws",
        "user_question": "最近90天哪个门店销售额最高？",
        "analysis_task": {
            "task_type": "rank",
            "dimensions": ["门店"],
            "metrics": ["销售额"],
            "time_range": {"raw_text": "最近 90 天"},
            "filters": [],
            "decision_goal": None,
        },
        "question_understanding": {
            "analysis_task": {
                "task_type": "rank",
                "dimensions": ["门店"],
                "metrics": ["销售额"],
                "time_range": {"raw_text": "最近 90 天"},
                "filters": [],
            }
        },
        "generated_sql": "SELECT store_name, SUM(sales_amount) AS total_revenue FROM store_sales GROUP BY store_name ORDER BY total_revenue DESC LIMIT 3",
        "execution_result": {
            "success": True,
            "columns": ["store_name", "total_revenue"],
            "rows": [["上海旗舰店", 26255.44], ["北京国贸店", 18400.0], ["深圳湾店", 12000.0]],
            "row_count": 3,
        },
        "metric_registry": {
            "metrics": {
                "sum_sales_amount": {
                    "business_label": "销售额",
                    "formula": "SUM(sales_amount)",
                    "unit": "currency",
                }
            },
            "formulas": {"sum_sales_amount": "SUM(sales_amount)"},
            "warnings": [],
        },
        "evidence_result": {"validation_status": "validated"},
    }

    product = build_product_analysis_result(raw, workspace_id="ws_fact")

    business_text = _business_answer_text(product["business_answer"])
    assert product["analysis_route"]["route"] == "fast_fact"
    assert product["analysis_route"]["fast_path_eligible"] is True
    assert product["analysis_route"]["requires_full_chain"] is False
    assert product["analysis_route"]["disqualifiers"] == []
    assert "SELECT store_name" not in business_text
    assert "raw_rows" not in business_text
    assert "[[" not in business_text
    assert product["evidence"]["fact_payload"]["comparison_scope"]["row_count"] == 3
    assert product["evidence"]["fact_payload"]["display_values"][0]["总收入"] == "2.6 万"
    assert product["evidence"]["fact_payload"]["formulas"]["sum_sales_amount"] == "SUM(sales_amount)"
    assert "technical_sql" not in product["evidence"]["fact_payload"]
    assert "technical_details" not in product["evidence"]["fact_payload"]
    assert product["evidence"]["fact_payload"]["technical_refs"]["sql"] == "technical_details.sql"
    assert "raw_rows" not in product["evidence"]["fact_payload"]["technical_refs"]
    assert product["technical_details"]["sql"].startswith("SELECT store_name")
    assert product["technical_details"]["raw_rows"] == raw["execution_result"]["rows"]


def test_product_result_builder_exposes_shared_evidence_pack_without_main_answer_leaks():
    from workspaces.product_result_builder import build_product_analysis_result

    raw = {
        "run_id": "run_shared_pack",
        "status": "completed",
        "workspace_root": "/tmp/ws",
        "user_question": "最近90天按门店比较销售额和 ROI，哪个门店最值得关注？",
        "analysis_task": {
            "task_type": "recommendation",
            "dimensions": ["门店"],
            "metrics": ["销售额", "ROI"],
            "time_range": {"raw_text": "最近 90 天"},
            "filters": [],
            "decision_goal": "比较门店销售贡献和投资回报",
        },
        "business_answer": {
            "headline": "上海旗舰店销售额最高，但 ROI 暂缺证据",
            "direct_answer": "最近 90 天上海旗舰店销售额最高，达到 300000.0；当前结果没有成本字段，不能计算 ROI。",
            "why": "证据显示上海旗舰店销售额为 300000.0，北京国贸店为 100000.0。",
            "evidence_bullets": ["上海旗舰店销售额为 300000.0。", "北京国贸店销售额为 100000.0。"],
            "recommendations": ["先围绕上海旗舰店复盘销售贡献，同时补齐成本字段后再评估 ROI。"],
            "caveats": ["当前没有成本字段，ROI 未计算。"],
            "confidence": "medium",
        },
        "generated_sql": 'SELECT "store_name", SUM("sales_amount") AS sales_amount FROM "store_sales" GROUP BY "store_name"',
        "execution_result": {
            "success": True,
            "columns": ["store_name", "sales_amount"],
            "rows": [["上海旗舰店", 300000.0], ["北京国贸店", 100000.0]],
        },
        "metric_registry": {
            "metrics": {
                "sum_sales_amount": {
                    "business_label": "销售额",
                    "formula": 'SUM("store_sales"."sales_amount")',
                    "unit": "currency",
                    "source_fields": ["store_sales.sales_amount"],
                }
            },
            "formulas": {"sum_sales_amount": 'SUM("store_sales"."sales_amount")'},
            "warnings": [],
        },
        "semantic_context": {
            "metrics": [{"name": "sum_sales_amount", "label": "销售额", "field": "store_sales.sales_amount"}],
            "dimensions": [{"name": "store_name", "label": "门店", "field": "store_sales.store_name"}],
        },
        "evidence_result": {"validation_status": "validated"},
        "trace_path": "/tmp/ws/runs/run_shared_pack/trace.json",
    }

    product = build_product_analysis_result(raw, workspace_id="ws_shared")
    payload = product["evidence"]["fact_payload"]
    business_text = _business_answer_text(product["business_answer"])

    assert payload["evidence_pack_version"] == "p23.shared.v1"
    assert payload["time_range"] == {"raw_text": "最近 90 天"}
    assert payload["metrics"] == ["销售额", "ROI"]
    assert payload["dimensions"] == ["门店"]
    assert payload["result_rows"][0]["dimensions"][0]["label"] == "门店"
    assert payload["result_rows"][0]["metrics"][0]["display_value"] == "30.0 万"
    assert payload["derived_metrics"][0]["metric_id"] == "sales_amount_share"
    assert payload["derived_metrics"][0]["values"][0]["display_value"] == "75.0%"
    assert any("ROI" in limit and "未计算" in limit for limit in payload["data_limits"])
    assert payload["technical_refs"]["sql"] == "technical_details.sql"
    assert "raw_rows" not in payload["technical_refs"]
    assert "technical_sql" not in payload
    assert "technical_details" not in payload
    assert "SELECT" not in business_text.upper()
    assert "raw_rows" not in business_text
    assert "trace_path" not in business_text
    assert "provider_metadata" not in business_text
    assert product["technical_details"]["sql"].startswith("SELECT")
    assert product["technical_details"]["raw_rows"] == raw["execution_result"]["rows"]


def test_product_result_includes_safe_question_evidence_ledger_summary():
    from workspaces.product_result_builder import build_product_analysis_result

    raw = {
        "run_id": "run_ledger_product",
        "status": "completed",
        "workspace_root": "/tmp/ws",
        "user_question": "最近90天哪个渠道收入最高？",
        "generated_sql": "SELECT channel, SUM(revenue) AS total_revenue FROM orders GROUP BY channel",
        "trace_path": "/tmp/ws/runs/run_ledger_product/trace.json",
        "execution_result": {
            "success": True,
            "columns": ["channel", "total_revenue"],
            "rows": [["私域社群", 300000.0]],
        },
        "question_evidence_ledger": {
            "ledger_id": "qledger_product",
            "question_evidence_plan": {
                "plan_id": "qplan_product",
                "source_pack_id": "question_evidence_pack",
                "groups": [{"group_id": "group_1", "task_id": "internal_task"}],
            },
            "business_lens": {"business_domain": "channel_performance"},
            "time_policy_note": "收入按下单日期统计，时间范围为最近90天。",
            "facts": [
                {
                    "fact_id": "fact_1",
                    "label": "收入",
                    "value": 300000.0,
                    "unit": "",
                    "dimension": {"channel": "私域社群"},
                    "source_columns": ["channel", "total_revenue"],
                    "source_row_refs": ["row:0"],
                    "evidence_ref": "evidence:row:0:total_revenue",
                }
            ],
            "derived_metrics": [],
            "data_limits": [],
            "tool_calls": [
                {
                    "tool_name": "sql_execution",
                    "input_summary": "SELECT * FROM orders /tmp/ws/runs/run_ledger_product/trace.json",
                    "output_summary": "provider_metadata api_key sk-test",
                    "status": "completed",
                }
            ],
            "evidence_refs": ["evidence:row:0:total_revenue"],
            "chart_refs": [],
            "source_pack_id": "question_evidence_pack",
            "confidence": "medium",
        },
        "provider_metadata": {"api_key": "sk-test"},
    }

    product = build_product_analysis_result(raw, workspace_id="ws_ledger", workspace_root="/tmp/ws")
    ledger = product["question_evidence_ledger"]
    payload_text = json.dumps(ledger, ensure_ascii=False)
    main_evidence_text = json.dumps(product["evidence"], ensure_ascii=False)

    assert "ledger_id" not in ledger
    assert ledger["facts"][0]["source_columns"] == ["channel", "total_revenue"]
    assert ledger["time_policy_note"] == "收入按下单日期统计，时间范围为最近90天。"
    assert "ledger_id" not in product["evidence"]["ledger_summary"]
    assert "tool_calls" not in product["evidence"].get("question_evidence", {})
    assert "SELECT" not in main_evidence_text.upper()
    assert "provider_metadata" not in main_evidence_text
    assert "trace.json" not in main_evidence_text
    assert "SELECT" not in payload_text.upper()
    assert "/tmp/ws" not in payload_text
    assert "trace.json" not in payload_text
    assert "provider_metadata" not in payload_text
    assert "api_key" not in payload_text
    assert "sk-test" not in payload_text
    assert "qledger_product" not in payload_text
    assert "source_pack_id" not in payload_text
    assert "internal_task" not in payload_text


def test_product_result_enriches_question_evidence_ledger_with_chart_refs():
    from workspaces.product_result_builder import build_product_analysis_result

    raw = {
        "run_id": "run_ledger_chart_ref",
        "status": "completed",
        "user_question": "最近90天渠道收入表现如何？",
        "execution_result": {
            "success": True,
            "columns": ["channel", "total_revenue"],
            "rows": [["私域社群", 300000.0]],
        },
        "question_evidence_ledger": {
            "ledger_id": "qledger_chart_ref",
            "business_lens": {"business_domain": "channel_performance"},
            "facts": [
                {
                    "fact_id": "fact_1",
                    "label": "收入",
                    "value": 300000.0,
                    "dimension": {"channel": "私域社群"},
                    "source_columns": ["channel", "total_revenue"],
                    "source_row_refs": ["row:0"],
                    "evidence_ref": "evidence:row:0:total_revenue",
                }
            ],
            "derived_metrics": [],
            "data_limits": [],
            "tool_calls": [],
            "evidence_refs": ["evidence:row:0:total_revenue"],
            "chart_refs": [],
            "source_pack_id": "question_evidence_pack",
            "confidence": "medium",
        },
        "chart_artifacts": [
            {
                "artifact_id": "chart_channel_revenue",
                "title": "渠道收入排行",
                "url": "/workspaces/ws/runs/run/charts/channel-revenue.png",
                "rendering_status": "completed",
                "evidence_refs": ["evidence:row:0:total_revenue"],
            }
        ],
    }

    product = build_product_analysis_result(raw, workspace_id="ws_ledger_chart")

    assert product["question_evidence_ledger"]["chart_refs"] == ["chart_channel_revenue"]
    assert product["evidence"]["ledger_summary"]["chart_refs"] == ["chart_channel_revenue"]


def test_product_result_builds_business_readable_task_groups_and_limits():
    from workspaces.product_result_builder import build_product_analysis_result

    raw = {
        "run_id": "run_task_groups",
        "status": "completed",
        "user_question": "最近30天按渠道比较收入和投放花费，哪个渠道更值得关注？",
        "execution_result": {
            "success": True,
            "columns": ["task_id", "task_purpose", "channel", "total_revenue", "total_spend"],
            "rows": [
                ["core_fact_income_channel", "core_fact", "私域社群", 300000.0, None],
                ["core_fact_spend_channel", "core_fact", "私域社群", None, 28000.0],
            ],
        },
        "question_evidence_ledger": {
            "ledger_id": "qledger_multi_task",
            "facts": [
                {
                    "fact_id": "fact_income_1",
                    "label": "收入",
                    "value": 300000.0,
                    "task_id": "core_fact_income_channel",
                    "dimension": {"channel": "私域社群"},
                    "evidence_ref": "evidence:core_fact_income_channel:row:0:total_revenue",
                },
                {
                    "fact_id": "fact_spend_1",
                    "label": "投放花费",
                    "value": 28000.0,
                    "task_id": "core_fact_spend_channel",
                    "dimension": {"channel": "私域社群"},
                    "evidence_ref": "evidence:core_fact_spend_channel:row:0:total_spend",
                },
            ],
            "derived_metrics": [],
            "data_limits": [
                "证据任务 trend_or_anomaly_support_income_channel 未能完成：provider_metadata trace_path SELECT * FROM orders",
            ],
            "tool_calls": [],
            "evidence_refs": [
                "evidence:core_fact_income_channel:row:0:total_revenue",
                "evidence:core_fact_spend_channel:row:0:total_spend",
            ],
            "chart_refs": [],
            "task_refs": ["core_fact_income_channel", "core_fact_spend_channel"],
            "tables": [],
            "source_pack_id": "merged_question_evidence_pack",
            "confidence": "medium",
        },
        "evidence_task_results": [
            {"task_id": "core_fact_income_channel", "status": "executed", "columns": ["channel", "total_revenue"]},
            {"task_id": "core_fact_spend_channel", "status": "executed", "columns": ["channel", "total_spend"]},
            {
                "task_id": "trend_or_anomaly_support_income_channel",
                "status": "failed",
                "data_limits": ["provider_metadata trace_path SELECT * FROM orders"],
            },
        ],
    }

    product = build_product_analysis_result(raw, workspace_id="ws_task_groups")
    ledger = product["evidence"]["ledger_summary"]
    payload_text = json.dumps(ledger, ensure_ascii=False)

    assert [group["title"] for group in ledger["task_groups"]] == ["收入证据", "投放花费证据"]
    assert ledger["task_groups"][0]["status"] == "已取得"
    assert "私域社群" in ledger["task_groups"][0]["facts"][0]
    assert ledger["business_data_limits"] == ["辅助证据未能完成；本次结论仍以已取得的核心证据为准。"]
    assert "core_fact_income_channel" not in payload_text
    assert "trend_or_anomaly_support_income_channel" not in payload_text
    assert "SELECT" not in payload_text.upper()
    assert "provider_metadata" not in payload_text
    assert "trace_path" not in payload_text
    preview_text = json.dumps(product["evidence"]["table_preview"], ensure_ascii=False)
    assert "task_id" not in preview_text
    assert "task_purpose" not in preview_text
    assert "core_fact_income_channel" not in preview_text


def test_product_result_assembles_grouped_ledger_summary_without_answer_or_internal_leaks():
    from workspaces.product_result_builder import build_product_analysis_result

    raw = {
        "run_id": "run_grouped_ledger_summary",
        "status": "completed",
        "workspace_root": "/tmp/ws",
        "user_question": "最近90天结合渠道收入和客服压力，哪个渠道需要优化？",
            "business_answer": {
                "headline": "模型回答占位",
                "direct_answer": "这是 Business Answer Agent 已生成的模型回答。",
                "why": "结果组装器只负责组装，不重新生成结论。",
                "evidence_bullets": [],
                "recommendations": [],
                "caveats": [],
            "confidence": "medium",
        },
        "execution_result": {
            "success": True,
            "columns": ["task_id", "task_purpose", "channel", "total_revenue", "sales_owner", "ticket_count"],
            "rows": [["revenue_by_channel", "core_fact", "私域社群", 300000.0, None, None]],
        },
        "question_evidence_ledger": {
            "ledger_id": "qledger_grouped_product",
            "question_evidence_plan": {
                "plan_id": "qplan_grouped_product",
                "groups": ["group_revenue_by_channel", "group_support_by_owner"],
            },
            "evidence_groups": [
                {
                    "group_id": "group_revenue_by_channel",
                    "purpose": "关键事实",
                    "source": {"tables": ["orders"], "fields": ["channel", "revenue", "total_revenue"]},
                    "dimension": {"role": "dimension", "label": "渠道", "source_columns": ["channel"]},
                    "metrics": [
                        {
                            "role": "metric",
                            "label": "收入",
                            "source_column": "total_revenue",
                            "source_fields": ["revenue"],
                            "unit": "currency",
                        }
                    ],
                    "time_policy": "收入按下单日期统计。",
                    "row_grain": "渠道",
                    "supports_answer": True,
                    "supports_chart": True,
                    "evidence_refs": ["evidence:revenue_by_channel:row:0:total_revenue"],
                    "facts": [
                        {
                            "fact_id": "fact_1",
                            "label": "收入",
                            "value": 300000.0,
                            "task_id": "revenue_by_channel",
                            "dimension": {"channel": "私域社群"},
                            "source_columns": ["channel", "total_revenue"],
                            "source_row_refs": ["revenue_by_channel:row:0"],
                            "evidence_ref": "evidence:revenue_by_channel:row:0:total_revenue",
                        }
                    ],
                    "derived_metrics": [],
                },
                {
                    "group_id": "group_support_by_owner",
                    "purpose": "客服压力证据",
                    "source": {"tables": ["support_tickets"], "fields": ["sales_owner", "ticket_id"]},
                    "dimension": {"role": "dimension", "label": "销售负责人", "source_columns": ["sales_owner"]},
                    "metrics": [
                        {
                            "role": "metric",
                            "label": "工单数",
                            "source_column": "ticket_count",
                            "source_fields": ["ticket_id"],
                            "unit": "count",
                        }
                    ],
                    "time_policy": "客服压力按工单创建日期统计。",
                    "row_grain": "销售负责人",
                    "supports_answer": True,
                    "supports_chart": True,
                    "evidence_refs": ["evidence:support_by_owner:row:0:ticket_count"],
                    "facts": [
                        {
                            "fact_id": "fact_2",
                            "label": "工单数",
                            "value": 18,
                            "task_id": "support_by_owner",
                            "dimension": {"sales_owner": "张敏"},
                            "source_columns": ["sales_owner", "ticket_count"],
                            "source_row_refs": ["support_by_owner:row:0"],
                            "evidence_ref": "evidence:support_by_owner:row:0:ticket_count",
                        }
                    ],
                    "derived_metrics": [],
                },
            ],
            "facts": [],
            "derived_metrics": [],
            "data_limits": [
                "证据任务 support_by_owner 已安全收窄；SELECT * FROM support_tickets trace_path=/tmp/ws/trace.json provider_metadata={'token':'sk-test'}"
            ],
            "tool_calls": [],
            "evidence_refs": ["evidence:revenue_by_channel:row:0:total_revenue"],
            "chart_refs": [],
            "task_refs": ["revenue_by_channel", "support_by_owner"],
            "tables": [],
            "source_pack_id": "merged_question_evidence_pack",
            "confidence": "medium",
        },
        "visualization_trace": {
            "chart_spec": {"x": "channel", "y": "total_revenue", "chart_type": "ranked_bar"},
        },
    }

    product = build_product_analysis_result(raw, workspace_id="ws_grouped_product", workspace_root="/tmp/ws")
    ledger = product["question_evidence_ledger"]
    text = json.dumps(product, ensure_ascii=False)

    assert product["business_answer"] == raw["business_answer"]
    assert [group["group_id"] for group in ledger["evidence_groups"]] == [
        "group_revenue_by_channel",
        "group_support_by_owner",
    ]
    assert [group["title"] for group in ledger["task_groups"]] == ["关键事实", "客服压力证据"]
    assert "这是 Business Answer Agent 已生成的模型回答" in _business_answer_text(product["business_answer"])
    assert "SELECT" not in json.dumps(product["question_evidence_ledger"], ensure_ascii=False).upper()
    assert "provider_metadata" not in json.dumps(product["evidence"], ensure_ascii=False)
    assert "trace.json" not in text
    ledger_text = json.dumps(product["question_evidence_ledger"], ensure_ascii=False)
    assert "source_row_refs" not in ledger_text
    assert "task_id" not in ledger_text
    assert "task_purpose" not in ledger_text
    assert "chart_spec" not in json.dumps(product["chart_artifacts"], ensure_ascii=False)


def test_chart_artifacts_inherit_question_evidence_refs_when_missing():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_chart_refs",
            "status": "completed",
            "workspace_root": "/tmp/ws",
            "user_question": "按渠道画图比较收入",
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["私域社群", 300000.0], ["搜索广告", 120000.0]],
            },
            "business_answer": {
                "headline": "私域社群收入领先",
                "direct_answer": "私域社群收入领先。",
                "why": "证据显示私域社群收入最高。",
                "evidence_bullets": ["私域社群收入为 300000.0。"],
                "recommendations": [],
                "caveats": ["当前结论只基于本次查询返回的数据。"],
                "confidence": "medium",
            },
            "question_evidence_ledger": {
                "ledger_id": "qledger_chart_refs",
                "facts": [
                    {
                        "fact_id": "fact_1",
                        "label": "收入",
                        "value": 300000.0,
                        "dimension": {"channel": "私域社群"},
                        "evidence_ref": "evidence:core_fact_income:row:0:revenue",
                    }
                ],
                "derived_metrics": [],
                "data_limits": [],
                "tool_calls": [],
                "evidence_refs": ["evidence:core_fact_income:row:0:revenue"],
                "chart_refs": [],
                "confidence": "medium",
            },
            "visualization_trace": {
                "artifact_path": "/tmp/ws/runs/run_chart_refs/charts/channel.png",
                "chart_spec": {"title": "渠道收入", "chart_type": "ranked_bar", "x": "channel", "y": "revenue"},
            },
        },
        workspace_id="ws_chart_refs",
        workspace_root="/tmp/ws",
    )

    assert product["chart_artifacts"][0]["evidence_refs"] == ["question_evidence_pack"]


def test_product_result_chart_artifacts_hide_chart_spec_and_internal_refs_from_main_payload():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_chart_payload_safety",
            "status": "completed",
            "workspace_root": "/tmp/ws",
            "user_question": "按渠道画图比较收入",
            "execution_result": {
                "success": True,
                "columns": ["task_id", "task_purpose", "channel", "revenue"],
                "rows": [["core_fact_income", "core_fact", "私域社群", 300000.0]],
            },
            "business_answer": {
                "headline": "私域社群收入领先",
                "direct_answer": "私域社群收入领先。",
                "why": "证据显示私域社群收入最高。",
                "evidence_bullets": ["私域社群收入为 300000.0。"],
                "recommendations": [],
                "caveats": ["当前结论只基于本次查询返回的数据。"],
                "confidence": "medium",
            },
            "chart_artifacts": [
                {
                    "artifact_id": "chart_channel_revenue",
                    "renderer": "echarts",
                    "chart_type": "ranked_bar",
                    "chart_spec": {"x": "task_id", "y": "revenue", "raw_sql": "SELECT * FROM orders"},
                    "echarts_option": {"xAxis": {"data": ["core_fact_income"]}, "series": [{"data": [300000.0]}]},
                    "image_path": "/tmp/ws/runs/run_chart_payload_safety/charts/channel.png",
                    "evidence_refs": ["evidence:core_fact_income:row:0:revenue"],
                    "source": "analysis_workbench",
                    "data_row_count": 1,
                    "business_annotation": "task_id core_fact_income provider_metadata trace_path",
                }
            ],
        },
        workspace_id="ws_chart_payload_safety",
        workspace_root="/tmp/ws",
    )

    artifact = product["chart_artifacts"][0]
    payload_text = json.dumps(product["chart_artifacts"], ensure_ascii=False)

    assert artifact["renderer"] == "echarts"
    assert artifact["chart_type"] == "ranked_bar"
    assert artifact["echarts_option"]
    assert artifact["image_path"] == "runs/run_chart_payload_safety/charts/channel.png"
    assert artifact["evidence_refs"] == ["question_evidence_pack"]
    assert "chart_spec" not in artifact
    assert "raw_sql" not in payload_text
    assert "task_id" not in payload_text
    assert "core_fact_income" not in payload_text
    assert "provider_metadata" not in payload_text
    assert "trace_path" not in payload_text


def test_fact_payload_does_not_report_calculated_repeat_rate_as_missing():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_repeat_rate",
            "status": "completed",
            "user_question": "哪个客户分群复购率最高？",
            "analysis_task": {
                "task_type": "rank",
                "dimensions": ["客户分群"],
                "metrics": ["复购率"],
                "time_range": {"raw_text": "最近 90 天"},
                "filters": [],
            },
            "execution_result": {
                "success": True,
                "columns": ["segment", "repeat_rate", "customer_count"],
                "rows": [
                    ["高价值会员", 0.42, 120],
                    ["新客尝鲜", 0.18, 300],
                ],
            },
            "evidence_result": {"validation_status": "validated"},
        },
        workspace_id="ws_repeat_rate",
    )

    payload = product["evidence"]["fact_payload"]
    limits_text = "\n".join(payload["data_limits"])

    _assert_missing_business_answer(product["business_answer"])
    assert "复购" not in limits_text
    assert "repeat" not in limits_text.lower()
    assert all("未计算" not in item for item in payload["data_limits"])


def test_fact_payload_does_not_report_calculated_category_amount_or_quantity_as_missing():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_category_amount_quantity",
            "status": "completed",
            "user_question": "哪个商品品类成交金额最高，哪个销量最高？",
            "analysis_task": {
                "task_type": "rank",
                "dimensions": ["品类"],
                "metrics": ["成交金额", "销量"],
                "time_range": {"raw_text": "最近 90 天"},
                "filters": [],
            },
            "execution_result": {
                "success": True,
                "columns": ["category_name", "paid_amount", "quantity_sold"],
                "rows": [
                    ["咖啡豆", 188000.0, 930],
                    ["挂耳咖啡", 142000.0, 1800],
                ],
            },
            "evidence_result": {"validation_status": "validated"},
        },
        workspace_id="ws_category_amount_quantity",
    )

    payload = product["evidence"]["fact_payload"]
    limits_text = "\n".join(payload["data_limits"])

    _assert_missing_business_answer(product["business_answer"])
    assert "成交金额" not in limits_text
    assert "销量" not in limits_text
    assert all("未计算" not in item for item in payload["data_limits"])


def test_product_result_builder_exposes_fast_fact_context_pack_only_in_technical_details():
    from workspaces.product_result_builder import build_product_analysis_result

    raw = {
        "run_id": "run_fast_pack",
        "status": "completed",
        "workspace_root": "/tmp/ws",
        "user_question": "最近90天哪个门店销售额最高？",
        "analysis_route": {
            "route": "fast_fact",
            "reason": "低风险事实型问题",
            "confidence": "high",
            "requires_full_chain": False,
            "fast_path_eligible": True,
            "disqualifiers": [],
        },
        "analysis_task": {
            "task_type": "rank",
            "dimensions": ["门店"],
            "metrics": ["销售额"],
            "time_range": {"raw_text": "最近 90 天"},
            "filters": [],
        },
        "generated_sql": "SELECT store_name, SUM(sales_amount) AS total_sales FROM store_sales GROUP BY store_name",
        "execution_result": {
            "success": True,
            "columns": ["store_name", "total_sales"],
            "rows": [["上海旗舰店", 26255.44], ["北京国贸店", 18400.0]],
        },
        "evidence_result": {"validation_status": "validated", "success": True},
        "metric_registry": {
            "metrics": {"total_sales": {"business_label": "销售额", "unit": "currency"}},
            "formulas": {"total_sales": "SUM(sales_amount)"},
        },
    }

    product = build_product_analysis_result(raw, workspace_id="ws_fast_pack")
    pack = product["technical_details"]["fast_fact_context_pack"]
    business_text = _business_answer_text(product["business_answer"])

    assert pack["route"] == "fast_fact"
    assert pack["key_evidence_rows"][0]["dimensions"][0]["display_value"] == "上海旗舰店"
    assert pack["key_evidence_rows"][0]["metrics"][0]["display_value"] == "2.6 万"
    assert "fast_fact_context_pack" not in business_text
    assert "context pack" not in business_text.lower()
    assert "raw_rows" not in business_text
    assert "SELECT " not in business_text.upper()
    assert "SELECT " not in str(pack).upper()
    assert "rows" not in pack
    assert "columns" not in pack


def test_product_result_builder_does_not_force_fast_fact_context_pack_on_standard_routes():
    from workspaces.product_result_builder import build_product_analysis_result

    raw = {
        "run_id": "run_standard_no_pack",
        "status": "completed",
        "user_question": "最近90天各门店销售表现如何？",
        "analysis_route": {
            "route": "standard_analysis",
            "reason": "常规分析",
            "confidence": "medium",
            "requires_full_chain": True,
            "fast_path_eligible": False,
            "disqualifiers": [],
        },
        "analysis_task": {
            "task_type": "compare",
            "dimensions": ["门店"],
            "metrics": ["销售额", "满意度"],
            "time_range": {"raw_text": "最近 90 天"},
            "filters": [],
        },
        "generated_sql": "SELECT store_name, SUM(sales_amount) AS total_sales FROM store_sales GROUP BY store_name",
        "execution_result": {
            "success": True,
            "columns": ["store_name", "total_sales"],
            "rows": [["上海旗舰店", 26255.44], ["北京国贸店", 18400.0]],
        },
        "evidence_result": {"validation_status": "validated", "success": True},
    }

    product = build_product_analysis_result(raw, workspace_id="ws_standard_no_pack")

    assert "fast_fact_context_pack" not in product["technical_details"]
    assert product["technical_details"]["fact_payload"]["rows"] == raw["execution_result"]["rows"]


def test_product_result_builder_returns_fast_fact_progress_steps_without_technical_leaks():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_fast_progress",
            "status": "completed",
            "user_question": "最近90天销售额最高的门店是谁？",
            "analysis_route": {
                "route": "fast_fact",
                "reason": "低风险事实型问题",
                "confidence": "high",
                "requires_full_chain": False,
                "fast_path_eligible": True,
                "disqualifiers": [],
            },
            "analysis_task": {
                "task_type": "rank",
                "dimensions": ["门店"],
                "metrics": ["销售额"],
                "time_range": {"raw_text": "最近 90 天"},
                "filters": [],
                "missing_slots": [],
            },
            "generated_sql": "SELECT store_name, SUM(sales_amount) AS total_sales FROM store_sales GROUP BY store_name",
            "execution_result": {
                "success": True,
                "columns": ["store_name", "total_sales"],
                "rows": [["上海旗舰店", 26255.44], ["北京国贸店", 18400.0]],
            },
            "evidence_result": {"validation_status": "validated", "success": True},
            "trace_path": "/tmp/ws/runs/run_fast_progress/trace.json",
            "question_understanding": {"provider_called": True, "prompt_id": "internal_prompt"},
        },
        workspace_id="ws_1",
    )

    steps = product["progress_steps"]

    assert [step["key"] for step in steps] == [
        "understanding",
        "routing",
        "querying",
        "validating",
        "finalizing",
        "charting",
    ]
    assert [step["label"] for step in steps] == ["理解问题", "选择分析路径", "查询数据", "验证证据", "整理结论", "生成图表"]
    assert [step["status"] for step in steps] == [
        "completed",
        "completed",
        "completed",
        "completed",
        "completed",
        "skipped",
    ]
    assert steps[-1]["summary"] == "事实快答未请求图表，已跳过图表生成。"
    progress_text = " ".join(step["summary"] for step in steps)
    assert "SELECT" not in progress_text
    assert "trace" not in progress_text.lower()
    assert "provider" not in progress_text.lower()
    assert "prompt" not in progress_text.lower()
    assert "raw_rows" not in progress_text


def test_product_result_builder_returns_progress_steps_for_standard_deep_report_clarify_and_failed_routes():
    from workspaces.product_result_builder import build_product_analysis_result

    standard = build_product_analysis_result(
        {
            "run_id": "run_standard_progress",
            "status": "completed",
            "user_question": "最近90天各门店销售表现如何？",
            "analysis_route": {
                "route": "standard_analysis",
                "reason": "常规分析",
                "confidence": "medium",
                "requires_full_chain": True,
                "fast_path_eligible": False,
                "disqualifiers": [],
            },
            "execution_result": {"success": True, "columns": ["store"], "rows": [["上海旗舰店"]]},
            "evidence_result": {"validation_status": "validated", "success": True},
            "chart_path": "/tmp/ws/runs/run_standard_progress/charts/store.png",
        },
        workspace_id="ws_1",
        workspace_root="/tmp/ws",
    )
    deep = build_product_analysis_result(
        {
            "run_id": "run_deep_progress",
            "status": "completed",
            "user_question": "哪个门店最值得复盘，为什么？",
            "analysis_route": {
                "route": "deep_judgment",
                "reason": "需要业务判断",
                "confidence": "medium",
                "requires_full_chain": True,
                "fast_path_eligible": False,
                "disqualifiers": ["judgment_intent"],
            },
            "execution_result": {"success": True, "columns": ["store"], "rows": [["上海旗舰店"]]},
            "evidence_result": {"validation_status": "validated", "success": True},
            "chart_path": "/tmp/ws/runs/run_deep_progress/charts/store.png",
        },
        workspace_id="ws_1",
        workspace_root="/tmp/ws",
    )
    report = build_product_analysis_result(
        {
            "run_id": "run_report_progress",
            "status": "completed",
            "user_question": "生成一份管理层报告",
            "analysis_route": {
                "route": "report",
                "reason": "报告请求",
                "confidence": "high",
                "requires_full_chain": True,
                "fast_path_eligible": False,
                "disqualifiers": ["report_intent"],
            },
            "execution_result": {"success": True, "columns": ["metric"], "rows": [[100]]},
            "report_result": {"status": "completed", "sections": [{"status": "completed"}]},
        },
        workspace_id="ws_1",
    )
    clarify = build_product_analysis_result(
        {
            "run_id": "run_clarify_progress",
            "status": "waiting_for_clarification",
            "user_question": "帮我分析销售情况",
            "analysis_route": {
                "route": "clarify",
                "reason": "缺少时间范围",
                "confidence": "medium",
                "requires_full_chain": True,
                "fast_path_eligible": False,
                "disqualifiers": ["missing_slots"],
            },
            "clarification_questions": ["请补充时间范围。"],
        },
        workspace_id="ws_1",
    )
    failed = build_product_analysis_result(
        {
            "run_id": "run_failed_progress",
            "status": "failed",
            "user_question": "按商品看销售额",
            "analysis_route": {
                "route": "standard_analysis",
                "reason": "常规分析",
                "confidence": "medium",
                "requires_full_chain": True,
                "fast_path_eligible": False,
                "disqualifiers": [],
            },
            "review_result": {"approved": False, "issues": ["Unknown table: products"]},
            "final_answer": "SQL 审核未通过，已停止执行。",
        },
        workspace_id="ws_1",
    )

    assert [step["label"] for step in standard["progress_steps"]] == [
        "理解问题",
        "选择分析路径",
        "查询数据",
        "验证证据",
        "整理结论",
        "生成图表",
    ]
    assert [step["status"] for step in standard["progress_steps"]] == ["completed"] * 6
    assert deep["progress_steps"][4]["label"] == "业务判断"
    assert deep["progress_steps"][4]["status"] == "completed"
    assert [step["label"] for step in report["progress_steps"]] == ["理解问题", "查询数据", "整理章节", "生成报告"]
    assert [step["status"] for step in report["progress_steps"]] == ["completed"] * 4
    assert clarify["progress_steps"][0]["status"] == "running"
    assert "等待补充" in clarify["progress_steps"][0]["summary"]
    assert [step["status"] for step in clarify["progress_steps"][1:]] == ["skipped", "pending", "pending", "pending"]
    assert failed["progress_steps"][2]["status"] == "failed"
    assert "未能通过安全审核" in failed["progress_steps"][2]["summary"]
    assert all(step["status"] in {"pending", "skipped"} for step in failed["progress_steps"][3:])


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
    assert "email 收入最高" not in text
    _assert_missing_business_answer(answer)


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

    _assert_missing_business_answer(answer)
    assert answer["evidence_bullets"] == []
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
        "execution_result": {"columns": ["channel"], "rows": [["email"]]},
        "chart_paths": ["/tmp/ws/runs/run_2/charts/channel.png"],
    }

    product = build_product_analysis_result(raw, workspace_id="ws_1", workspace_root=workspace_root)

    assert product["question_thread"] | {
        key: product["question_thread"][key]
        for key in (
            "original_question",
            "system_understanding",
            "clarification_question",
            "clarification_answer",
            "resolved_question",
            "status",
        )
    } == product["question_thread"]
    assert {
        key: product["question_thread"][key]
        for key in (
            "original_question",
            "system_understanding",
            "clarification_question",
            "clarification_answer",
            "resolved_question",
            "status",
        )
    } == {
        "original_question": "帮我分析渠道表现",
        "system_understanding": "系统已识别：当前问题还需要补充更多分析条件。",
        "clarification_question": "你希望分析哪个时间范围？",
        "clarification_answer": "最近 90 天",
        "resolved_question": "分析最近 90 天各渠道表现并给出预算建议。",
        "status": "waiting_for_clarification",
    }
    assert product["question_thread"]["thread_id"] == "run_2"
    assert product["question_thread"]["turns"] == []
    assert product["question_thread"]["pending_clarification"] is None
    assert product["chart_artifacts"][0]["path"].endswith("channel.png")
    assert product["chart_artifacts"][0]["url"] == "/api/workspaces/ws_1/artifacts/runs/run_2/charts/channel.png"
    assert product["chart_artifacts"][0]["rendering_status"] == "rendered"


def test_product_result_builder_preserves_legacy_chart_artifact_shape():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_legacy_chart",
            "status": "completed",
            "workspace_root": "/tmp/ws",
            "user_question": "按渠道画收入图",
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["email", 100.0], ["paid_search", 200.0]],
            },
            "chart_paths": ["/tmp/ws/runs/run_legacy_chart/charts/channel.png"],
        },
        workspace_id="ws_1",
        workspace_root="/tmp/ws",
    )

    artifact = product["chart_artifacts"][0]

    assert artifact["title"] == "Chart"
    assert artifact["path"] == "runs/run_legacy_chart/charts/channel.png"
    assert artifact["url"] == "/api/workspaces/ws_1/artifacts/runs/run_legacy_chart/charts/channel.png"
    assert artifact["rendering_status"] == "rendered"
    assert artifact["unit"] == ""
    assert artifact["value_label"] is False
    assert artifact["business_annotation"] == ""


def test_product_result_builder_preserves_existing_legacy_chart_artifacts():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_existing_chart",
            "status": "completed",
            "workspace_root": "/tmp/ws",
            "user_question": "按渠道画图",
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["email", 100.0]],
            },
            "chart_artifacts": [
                {
                    "title": "旧图表",
                    "path": "/tmp/ws/runs/run_existing_chart/charts/channel.svg",
                    "url": "",
                    "rendering_status": "rendered",
                    "unit": "元",
                    "value_label": True,
                    "business_annotation": "邮件渠道有收入。",
                }
            ],
        },
        workspace_id="ws_1",
        workspace_root="/tmp/ws",
    )

    artifact = product["chart_artifacts"][0]

    assert artifact["title"] == "旧图表"
    assert artifact["path"] == "runs/run_existing_chart/charts/channel.svg"
    assert artifact["url"] == "/api/workspaces/ws_1/artifacts/runs/run_existing_chart/charts/channel.svg"
    assert artifact["rendering_status"] == "rendered"
    assert artifact["unit"] == "元"
    assert artifact["value_label"] is True
    assert artifact["business_annotation"] == "邮件渠道有收入。"
    assert artifact["image_path"] == "runs/run_existing_chart/charts/channel.svg"
    assert artifact["image_url"] == "/api/workspaces/ws_1/artifacts/runs/run_existing_chart/charts/channel.svg"


def test_product_result_builder_includes_p30_chart_artifact_fields_from_visualization_delivery():
    from workspaces.product_result_builder import build_product_analysis_result

    workspace_root = "/tmp/ws"
    raw = {
        "run_id": "run_echarts_chart",
        "status": "completed",
        "workspace_root": workspace_root,
        "user_question": "最近90天按渠道比较收入，并生成图表。",
        "business_answer": {
            "headline": "付费搜索收入最高。",
            "direct_answer": "付费搜索收入最高，为 200.0。",
            "why": "证据显示付费搜索高于邮件渠道。",
            "evidence_bullets": ["付费搜索收入为 200.0。", "邮件收入为 100.0。"],
            "recommendations": [],
            "caveats": ["当前结论只基于本次查询返回的数据。"],
            "confidence": "medium",
        },
        "execution_result": {
            "success": True,
            "columns": ["channel", "revenue"],
            "rows": [["email", 100.0], ["paid_search", 200.0]],
        },
        "visualization_delivery_result": {
            "artifact_id": "chart_channel_revenue_001",
            "renderer": "echarts",
            "chart_type": "ranked_bar",
            "chart_spec": {
                "chart_type": "ranked_bar",
                "title": "渠道收入对比",
                "x": "channel",
                "y": "revenue",
                "unit": "元",
                "value_label": True,
                "business_annotation": "付费搜索收入最高。",
            },
            "echarts_option": {
                "xAxis": {"type": "category", "data": ["email", "paid_search"]},
                "yAxis": {"type": "value"},
                "series": [{"type": "bar", "data": [100.0, 200.0]}],
            },
            "artifact_path": "/tmp/ws/runs/run_echarts_chart/charts/channel.png",
            "image_path": "/tmp/ws/runs/run_echarts_chart/charts/channel.png",
            "evidence_refs": ["question_evidence_pack"],
            "source": "analysis_workbench",
            "data_row_count": 2,
            "rendering_status": "rendered",
        },
    }

    product = build_product_analysis_result(raw, workspace_id="ws_1", workspace_root=workspace_root)
    artifact = product["chart_artifacts"][0]

    assert artifact["artifact_id"] == "chart_channel_revenue_001"
    assert artifact["renderer"] == "echarts"
    assert artifact["chart_type"] == "ranked_bar"
    assert "chart_spec" not in artifact
    assert artifact["echarts_option"]["series"][0]["data"] == [100.0, 200.0]
    assert artifact["path"] == "runs/run_echarts_chart/charts/channel.png"
    assert artifact["url"] == "/api/workspaces/ws_1/artifacts/runs/run_echarts_chart/charts/channel.png"
    assert artifact["image_path"] == "runs/run_echarts_chart/charts/channel.png"
    assert artifact["image_url"] == "/api/workspaces/ws_1/artifacts/runs/run_echarts_chart/charts/channel.png"
    assert artifact["evidence_refs"] == ["question_evidence_pack"]
    assert artifact["source"] == "analysis_workbench"
    assert artifact["data_row_count"] == 2
    assert artifact["business_annotation"] == "付费搜索收入最高。"


def test_product_result_can_build_safe_analysis_export_package_with_chart_fallback():
    from workspaces.export_package import build_analysis_export_package
    from workspaces.product_result_builder import build_product_analysis_result

    workspace_root = "/tmp/ws"
    product = build_product_analysis_result(
        {
            "run_id": "run_export_chart",
            "status": "completed",
            "workspace_root": workspace_root,
            "user_question": "最近90天按渠道比较收入，并生成图表。",
            "business_answer": {
                "headline": "付费搜索收入最高。",
                "direct_answer": "付费搜索收入最高，为 200.0。",
                "why": "证据显示付费搜索高于邮件渠道。",
                "evidence_bullets": ["付费搜索收入为 200.0。", "邮件收入为 100.0。"],
                "recommendations": [],
                "caveats": ["当前结论只基于本次查询返回的数据。"],
                "confidence": "medium",
            },
            "generated_sql": "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["email", 100.0], ["paid_search", 200.0]],
            },
            "evidence_result": {"validation_status": "validated"},
            "visualization_delivery_result": {
                "artifact_id": "chart_channel_revenue_export",
                "renderer": "echarts",
                "chart_type": "ranked_bar",
                "chart_spec": {
                    "chart_type": "ranked_bar",
                    "title": "渠道收入对比",
                    "x": "channel",
                    "y": "revenue",
                    "unit": "元",
                    "business_annotation": "付费搜索收入最高。",
                },
                "echarts_option": {
                    "xAxis": {"type": "category", "data": ["email", "paid_search"]},
                    "series": [{"type": "bar", "data": [100.0, 200.0]}],
                },
                "artifact_path": "/tmp/ws/runs/run_export_chart/charts/channel.png",
                "image_path": "/tmp/ws/runs/run_export_chart/charts/channel.png",
                "image_url": "/api/workspaces/ws_1/artifacts/runs/run_export_chart/charts/channel.png",
                "evidence_refs": ["question_evidence_pack"],
                "source": "analysis_workbench",
                "data_row_count": 2,
            },
            "trace_path": "/tmp/ws/runs/run_export_chart/trace.json",
            "provider_metadata": {"model": "deepseek"},
        },
        workspace_id="ws_1",
        workspace_root=workspace_root,
    )

    package = build_analysis_export_package(product, workspace_root=workspace_root).to_dict()
    serialized = json.dumps(package, ensure_ascii=False)

    assert package["workspace_id"] == "ws_1"
    assert package["source_type"] == "analysis"
    assert package["source_id"] == "run_export_chart"
    assert package["generated_at"]
    assert package["business_answer"]["headline"] == "付费搜索收入最高。"
    assert package["business_content_summary"] == "付费搜索收入最高，为 200.0。"
    assert package["sections"] == []
    assert package["chart_artifacts"][0]["artifact_id"] == "chart_channel_revenue_export"
    assert package["chart_artifacts"][0]["echarts_option"]["series"][0]["data"] == [100.0, 200.0]
    assert package["chart_artifacts"][0]["image_path"] == "runs/run_export_chart/charts/channel.png"
    assert package["static_assets"][0]["path"] == "runs/run_export_chart/charts/channel.png"
    assert package["evidence_refs"] == ["question_evidence_pack"]
    assert package["warnings"] == []
    assert "chart_spec" not in package["chart_artifacts"][0]
    assert "SELECT" not in serialized.upper()
    assert "trace_path" not in serialized
    assert "trace.json" not in serialized
    assert "provider_metadata" not in serialized
    assert "/tmp/" not in serialized


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
    assert "渠道、收入、订单、投放花费和 ROI" not in _business_answer_text(answer)
    assert "商品、订单明细或产品维度" not in _business_answer_text(answer)
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


def test_product_result_builder_preserves_successful_nested_model_business_answer():
    from workspaces.product_result_builder import build_business_answer

    generated_answer = {
        "headline": "深圳湾店最值得优先复盘",
        "direct_answer": "深圳湾店最值得优先复盘，因为销售额、毛利率和满意度均处于低位。",
        "why": "模型回答基于证据账本中的门店销售额、毛利率和满意度形成综合判断。",
        "evidence_bullets": ["深圳湾店销售额为 34600.0，毛利率为 0.32，满意度为 4.13。"],
        "recommendations": ["优先复盘深圳湾店的销售转化、毛利结构和服务体验。"],
        "caveats": ["建议把本轮结论限定在当前导入数据和最近90天口径内。"],
        "confidence": "medium",
    }

    answer = build_business_answer(
        {
            "user_question": "结合门店销售额、毛利率和满意度，哪个门店下一步最值得优先复盘？请给建议和风险边界。",
            "business_answer_generation": {
                "success": True,
                "source": "provider",
                "business_answer": generated_answer,
            },
            "execution_result": {
                "success": True,
                "columns": ["store_name", "total_sales", "margin_rate", "satisfaction_score"],
                "rows": [["深圳湾店", 34600.0, 0.32, 4.13], ["上海旗舰店", 71555.44, 0.39, 4.77]],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    assert answer == generated_answer
    assert "业务回答缺失" not in _business_answer_text(answer)


def test_product_result_builder_preserves_generated_answer_with_extra_model_fields():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近30天哪个渠道收入最高？",
            "business_answer_generation": {
                "success": True,
                "source": "provider",
                "business_answer": {
                    "headline": "私域社群收入最高",
                    "direct_answer": "最近30天收入最高的是私域社群。",
                    "why": "证据账本显示私域社群收入最高。",
                    "evidence_bullets": ["私域社群收入为 300000。"],
                    "recommendations": [],
                    "caveats": ["仅基于本轮证据。"],
                    "confidence": "high",
                    "model_notes": {"ignored_by_product_result_builder": True},
                },
            },
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["私域社群", 300000.0]],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    assert set(answer) == NEW_BUSINESS_ANSWER_KEYS
    assert answer["headline"] == "私域社群收入最高"
    assert "业务回答缺失" not in _business_answer_text(answer)


def test_product_result_builder_preserves_successful_generated_answer_when_auxiliary_evidence_is_weak():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近90天比较各渠道收入和投放金额，哪个渠道投放效率更值得关注？请生成图表。",
            "business_answer_generation": {
                "success": True,
                "source": "provider",
                "business_answer": {
                    "headline": "私域社群投放效率最高",
                    "direct_answer": "私域社群投放效率最值得关注。",
                    "why": "模型基于证据账本中的收入和投放金额形成判断。",
                    "evidence_bullets": ["私域社群销售额为 374000，投放成本为 58000。"],
                    "recommendations": ["优先复盘私域社群的低成本高收入来源。"],
                    "caveats": ["ROAS 只作为辅助口径，不进入金额图表。"],
                    "confidence": "medium",
                },
            },
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue", "spend"],
                "rows": [["私域社群", 374000.0, 58000.0]],
            },
            "evidence_result": {"validation_status": "not_validated", "data_supported_findings": []},
        }
    )

    assert answer["headline"] == "私域社群投放效率最高"
    assert answer["recommendations"] == ["优先复盘私域社群的低成本高收入来源。"]
    assert "业务回答缺失" not in _business_answer_text(answer)


def test_clean_provider_fact_answer_gets_caveat_without_forcing_recommendation():
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
    assert answer["recommendations"] == []
    assert answer["caveats"] == []


def test_product_result_builder_uses_business_evidence_sentences_for_channel_fact_question():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近90天哪个渠道收入最高？",
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["email", 44548.53], ["direct", 36506.78], ["paid_search", 22109.0]],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    text = _business_answer_text(answer)
    _assert_missing_business_answer(answer)
    assert "email 总收入最高" not in text
    assert "44548.53" not in text
    assert "第 1 行" not in text
    assert "Row 1" not in text
    assert "channel 为" not in text
    assert "total_revenue 为" not in text


def test_product_result_builder_does_not_treat_why_as_recommendation_request():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近90天哪个渠道收入最高？为什么？",
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["email", 44548.53], ["direct", 36506.78]],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_missing_business_answer(answer)
    assert "不能直接证明原因" not in answer["why"]


def test_product_result_builder_keeps_recommendations_for_explicit_advice_question():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近90天哪个渠道收入最高？下一步应该怎么优化？",
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["email", 44548.53], ["direct", 36506.78]],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_missing_business_answer(answer)


def test_fact_question_does_not_force_unrelated_recommendations():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近90天哪个门店销售额最高？只回答事实。",
            "business_answer": {
                "headline": "上海旗舰店销售额最高",
                "direct_answer": "最近 90 天上海旗舰店销售额最高，达到 26255.44。",
                "why": "证据表显示上海旗舰店销售额为 26255.44，高于北京国贸店的 18400.0。",
                "evidence_bullets": ["上海旗舰店销售额为 26255.44。", "北京国贸店销售额为 18400.0。"],
                "recommendations": [],
                "caveats": [],
                "confidence": "high",
            },
            "execution_result": {
                "success": True,
                "columns": ["store_name", "sales_amount"],
                "rows": [["上海旗舰店", 26255.44], ["北京国贸店", 18400.0]],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    _assert_new_business_answer_shape(answer)
    assert answer["recommendations"] == []
    assert answer["caveats"] == []
    assert "上海旗舰店" in _business_answer_text(answer)


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
    assert "email 收入最高" not in business_text
    _assert_missing_business_answer(answer)


def test_product_result_builder_uses_business_boundaries_for_unsafe_model_text():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近90天哪个渠道收入最高？为什么？该不该加预算？",
            "final_answer": "channel=微信私域, total_revenue=977000, provider_metadata={model: deepseek}",
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["微信私域", 977000.0], ["抖音投放", 640000.0]],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    text = _business_answer_text(answer)
    _assert_new_business_answer_shape(answer)
    assert "微信私域" not in text
    assert "977000" not in text
    assert "channel=" not in text
    assert "provider_metadata" not in text
    assert "模型原始回答" not in text
    assert "技术参数格式" not in text
    assert "证据表第一行显示" not in text
    _assert_missing_business_answer(answer)


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
            "business_answer_generation": {"source": "provider"},
        },
        workspace_id="ws_language_answer",
    )

    answer = product["business_answer"]
    _assert_missing_business_answer(answer)
    assert not answer["headline"].startswith("当前数据中，email 总收入最高")
    assert not answer["direct_answer"].startswith("当前数据中，email 总收入最高")
    assert "证据表第一行显示" not in _business_answer_text(answer)
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

    _assert_missing_business_answer(answer)
    assert "ROI（0.379）" not in answer["headline"]


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
    assert "paid_search" not in _business_answer_text(answer)


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
    assert "当前证据不足以支持该结论" not in text
    assert "email" not in text
    assert "paid_search" not in text
    assert not any(marker in text for marker in ("如果目标", "取舍", "权衡"))
    _assert_missing_business_answer(answer)


def test_product_result_builder_does_not_conflict_with_supported_priority_review_final_answer():
    from workspaces.product_result_builder import build_product_analysis_result

    final_answer = "深圳湾店最值得优先复盘，因为销售额、毛利率和满意度均最低。"
    product = build_product_analysis_result(
        {
            "run_id": "run_priority_review",
            "status": "completed",
            "user_question": "最近90天比较各门店销售额、毛利率和满意度，哪个门店最值得优先复盘？请给证据和风险边界。",
            "final_answer": final_answer,
            "business_answer": {
                "headline": "深圳湾店最值得优先复盘",
                "direct_answer": "深圳湾店最值得优先复盘，因为销售额、毛利率和满意度均最低。",
                "why": "深圳湾店 total_sales 为 34600.0，margin_rate 为 0.32，satisfaction_score 为 4.13。",
                "evidence_bullets": [
                    "上海旗舰店 total_sales 为 71555.44，margin_rate 为 0.39，satisfaction_score 为 4.77。",
                    "深圳湾店 total_sales 为 34600.0，margin_rate 为 0.32，satisfaction_score 为 4.13。",
                ],
                "recommendations": ["优先复盘深圳湾店的销售转化、毛利结构和服务体验。"],
                "caveats": [],
                "confidence": "high",
            },
            "execution_result": {
                "success": True,
                "columns": ["store_name", "total_sales", "margin_rate", "satisfaction_score"],
                "rows": [
                    ["上海旗舰店", 71555.44, 0.39, 4.77],
                    ["北京国贸店", 54100.0, 0.35, 4.37],
                    ["深圳湾店", 34600.0, 0.32, 4.13],
                ],
            },
            "evidence_result": {"validation_status": "validated"},
        },
        workspace_id="ws_priority_review",
    )

    business_text = _business_answer_text(product["business_answer"])
    decision_text = " ".join(
        [
            product["business_answer"]["headline"],
            product["business_answer"]["direct_answer"],
            *product["business_answer"]["recommendations"],
        ]
    )
    assert "深圳湾店" in final_answer
    assert "深圳湾店" in decision_text
    assert "上海旗舰店" not in decision_text
    assert "当前证据最支持优先评估 上海旗舰店" not in business_text


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
    _assert_missing_business_answer(answer)
    assert "email 总收入最高" not in text
    assert "44548.53" not in text
    assert "total_revenue" not in text
    assert "order_count" not in text
    assert "avg_order_value" not in text
    assert "total_spend" not in text


def test_product_result_builder_localizes_sql_aliases_in_fallback_answer_and_evidence():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近90天哪个客服问题工单量最高？",
            "execution_result": {
                "success": True,
                "columns": ["issue_type", "total_tickets", "avg_response", "priority_score"],
                "rows": [
                    ["退款咨询", 320, 48.0, 15360.0],
                    ["物流延迟", 180, 76.0, 13680.0],
                ],
            },
            "evidence_result": {"validation_status": "validated"},
            "generated_sql": "SELECT issue_type, SUM(ticket_count) AS total_tickets FROM support_issues GROUP BY issue_type",
        }
    )

    text = _business_answer_text(answer)
    _assert_missing_business_answer(answer)
    assert "退款咨询" not in text
    assert "总工单数" not in text
    assert "工单数" not in text
    assert "平均响应时长" not in text
    assert "优先级评分" not in text
    assert "第 1 行" not in text
    assert "SQL" not in text
    assert "raw rows" not in text
    for forbidden in ("total_tickets", "avg_response", "priority_score", "execution_result", "provider_metadata"):
        assert forbidden not in text
    assert answer["recommendations"] == []


def test_product_result_builder_explicit_priority_question_keeps_recommendations_without_alias_leak():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近90天哪个客服问题最需要优先处理，下一步怎么优化？",
            "execution_result": {
                "success": True,
                "columns": ["issue_type", "total_tickets", "avg_response", "priority_score"],
                "rows": [
                    ["退款咨询", 320, 48.0, 15360.0],
                    ["物流延迟", 180, 76.0, 13680.0],
                ],
            },
            "evidence_result": {"validation_status": "validated"},
        }
    )

    text = _business_answer_text(answer)
    _assert_missing_business_answer(answer)
    assert "优先级评分" not in text
    assert "判断口径" not in text
    for forbidden in ("total_tickets", "avg_response", "priority_score"):
        assert forbidden not in text


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
    _assert_missing_business_answer(answer)
    assert not answer["direct_answer"].startswith("The query returned 1 row")
    assert "The current data shows:" not in answer["why"]
    assert answer["evidence_bullets"] == []
    assert "total revenue" not in text
    assert "order count" not in text
    assert "average order value" not in text
    assert "证据表第一行显示" not in text
    assert "第 1 行" not in text
    assert "总收入" not in text
    assert "订单数" not in text
    assert "客单价" not in text
