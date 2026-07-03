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
    assert answer["recommendations"]
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
    assert product["technical_details"]["provider_metadata"]["insight"]["source"] == "deterministic"
    assert "sql" not in product["business_answer"]
    assert "trace_path" not in product["business_answer"]
    assert "provider_metadata" not in product["business_answer"]


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
    assert "technical_sql" not in payload
    assert "technical_details" not in payload
    assert "SELECT" not in business_text.upper()
    assert "raw_rows" not in business_text
    assert "trace_path" not in business_text
    assert "provider_metadata" not in business_text
    assert product["technical_details"]["sql"].startswith("SELECT")
    assert product["technical_details"]["raw_rows"] == raw["execution_result"]["rows"]


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
    assert steps[-1]["summary"] == "事实快答不生成图表。"
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
    assert answer["caveats"]
    assert any("本次查询" in caveat or "时间范围" in caveat for caveat in answer["caveats"])


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
    assert answer["caveats"]
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
    assert answer["direct_answer"].startswith("已完成本轮查询")


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
    assert "微信私域" in text
    assert "977000" in text
    assert "channel=" not in text
    assert "provider_metadata" not in text
    assert "模型原始回答" not in text
    assert "技术参数格式" not in text
    assert "证据表第一行显示" not in text
    assert any("当前结论" in caveat or "数据" in caveat for caveat in answer["caveats"])


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
    assert "当前证据不足以支持该结论" not in text
    assert "email" in text
    assert "paid_search" in text
    assert any(marker in text for marker in ("如果目标", "取舍", "口径", "权衡"))
    assert answer["recommendations"]
    assert answer["confidence"] in {"medium", "high"}
    assert any("预算" in caveat or "口径" in caveat or "本次查询" in caveat for caveat in answer["caveats"])


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
    assert "The current data shows:" in answer["why"]
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
