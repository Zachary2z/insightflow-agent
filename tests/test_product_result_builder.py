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

    assert product["version"] == "p13.v1"
    assert product["workspace_id"] == "ws_1"
    assert product["run_id"] == "run_1"
    assert product["status"] == "completed"
    assert product["question_thread"]["original_question"] == "哪个渠道该加预算？"
    assert product["question_thread"]["system_understanding"]
    assert product["business_answer"]["headline"]
    assert product["business_answer"]["summary"] == raw["final_answer"]
    assert product["business_answer"]["source"] == "deterministic"
    assert product["business_answer"]["quality_flags"] == []
    assert "raw_rows" not in product["business_answer"]
    assert "SELECT channel" not in product["business_answer"]["summary"]
    assert "provider_called" not in product["business_answer"]["summary"]
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
        "system_understanding": "time range missing",
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

    assert answer["headline"] == "当前数据无法支持这次查询"
    assert "不存在的表或字段" in answer["summary"]
    assert "Unknown table" not in answer["summary"]
    assert "Unknown column" not in answer["summary"]
    assert any("渠道、收入、订单、投放花费和 ROI" in action for action in answer["next_actions"])
    assert any(log["name"] == "review_result" for log in product["technical_details"]["validation_logs"])
    assert any(log["name"] == "schema_repair" for log in product["technical_details"]["validation_logs"])
    assert "Unknown table: products" in str(product["technical_details"]["validation_logs"])
