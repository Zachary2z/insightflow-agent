def test_question_understanding_extracts_complete_top_product_intent():
    from question_understanding.router import understand_question

    result = understand_question("最近 30 天销售额最高的 5 个商品是什么？")

    assert result["success"] is True
    assert result["strategy"] == "template"
    assert result["intent"]["metric"] == "gmv"
    assert result["intent"]["dimension"] == "product"
    assert result["intent"]["time_range"] == {"type": "last_n_days", "value": 30, "raw_text": "最近 30 天"}
    assert result["intent"]["operation"] == "top_n"
    assert result["intent"]["limit"] == 5
    assert "paid_orders" in result["intent"]["filters"]
    assert result["missing_slots"] == []
    assert result["clarification_questions"] == []
    assert result["risk_flags"] == []
    assert "sql" not in result
    assert "generated_sql" not in result


def test_question_understanding_clarifies_ambiguous_business_review_request():
    from question_understanding.router import understand_question

    result = understand_question("帮我看看销售情况")

    assert result["success"] is True
    assert result["strategy"] == "clarify"
    assert result["intent"]["metric"] == "gmv"
    assert result["intent"]["dimension"] == ""
    assert result["intent"]["time_range"] == {}
    assert result["intent"]["operation"] == "summary"
    assert set(result["missing_slots"]) == {"dimension", "time_range"}
    assert result["clarification_questions"] == ["请补充分析维度和时间范围，例如：最近90天按门店看销售额。"]


def test_question_understanding_rejects_sensitive_export_request():
    from question_understanding.router import understand_question

    result = understand_question("帮我导出所有用户的手机号和邮箱")

    assert result["success"] is True
    assert result["strategy"] == "reject"
    assert "sensitive_field" in result["risk_flags"]
    assert "bulk_export" in result["risk_flags"]
    assert result["rejection_reason"] == "Request asks for sensitive fields or unsafe data access."
    assert result["clarification_questions"] == []


def test_question_understanding_rejects_unsafe_write_request():
    from question_understanding.router import understand_question

    result = understand_question("删除所有取消订单的数据")

    assert result["strategy"] == "reject"
    assert "unsafe_operation" in result["risk_flags"]
    assert result["intent"]["operation"] == "unsafe_write"
    assert result["missing_slots"] == []


def test_question_understanding_routes_complete_non_template_question_to_llm_candidate():
    from question_understanding.router import understand_question

    result = understand_question("最近 30 天按用户分析复购率趋势")

    assert result["success"] is True
    assert result["strategy"] == "llm_candidate"
    assert result["intent"]["metric"] == "repurchase_rate"
    assert result["intent"]["dimension"] == "user"
    assert result["intent"]["time_range"]["type"] == "last_n_days"
    assert result["intent"]["operation"] == "trend"
    assert result["missing_slots"] == []
    assert result["risk_flags"] == []


def test_question_understanding_routes_channel_roi_budget_question_without_clarification():
    from question_understanding.router import understand_question

    result = understand_question("分析最近 90 天各渠道收入、投放成本和 ROI，告诉我哪个渠道应该加预算，并生成图表。")

    assert result["success"] is True
    assert result["strategy"] == "llm_candidate"
    assert result["intent"]["metric"] == "gmv"
    assert result["intent"]["dimension"] == "channel"
    assert result["intent"]["time_range"] == {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"}
    assert result["intent"]["operation"] == "comparison"
    assert result["missing_slots"] == []
    assert result["clarification_questions"] == []


def test_question_understanding_builds_complete_chinese_analysis_task_contract():
    from question_understanding.router import understand_question

    result = understand_question("最近90天按门店比较销售额")

    assert result["success"] is True
    assert result["strategy"] == "llm_candidate"
    task = result["analysis_task"]
    assert task["task_type"] == "compare"
    assert task["metrics"] == ["销售额"]
    assert task["dimensions"] == ["门店"]
    assert task["time_range"] == {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"}
    assert task["missing_slots"] == []
    assert task["resolved_question"] == "最近90天按门店比较销售额"
    assert task["output_language"] == "zh"
    assert task["confidence"] == "high"
    assert result["missing_slots"] == []
    assert result["clarification_questions"] == []


def test_question_understanding_clarifies_incomplete_recommendation_task_without_rejecting():
    from question_understanding.router import understand_question

    result = understand_question("帮我分析渠道表现，看看哪个渠道该加预算")

    assert result["success"] is True
    assert result["strategy"] == "clarify"
    assert result["risk_flags"] == []
    assert result["rejection_reason"] == ""
    task = result["analysis_task"]
    assert task["task_type"] == "recommendation"
    assert task["dimensions"] == ["渠道"]
    assert task["metrics"] == []
    assert task["time_range"] is None
    assert task["decision_goal"] == "判断哪个渠道该加预算"
    assert set(task["missing_slots"]) == {"metric", "time_range"}
    assert task["output_language"] == "zh"
    assert set(result["missing_slots"]) == {"metric", "time_range"}


def test_question_understanding_maps_english_raw_headers_to_chinese_task_slots():
    from question_understanding.router import understand_question

    workspace_context = {
        "semantic_metrics": [
            {
                "name": "sum_Sales Amount",
                "label": "销售额",
                "field": "store_ops.Sales Amount",
                "aliases": ["Sales Amount", "sales amount", "销售额"],
            }
        ],
        "semantic_dimensions": [
            {
                "name": "Store Name",
                "label": "门店",
                "field": "store_ops.Store Name",
                "aliases": ["Store Name", "store name", "门店"],
            }
        ],
    }

    result = understand_question("Compare Sales Amount by Store Name in last 90 days", workspace_context=workspace_context)

    task = result["analysis_task"]
    assert task["task_type"] == "compare"
    assert task["metrics"] == ["销售额"]
    assert task["dimensions"] == ["门店"]
    assert task["time_range"] == {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"}
    assert task["missing_slots"] == []
    assert task["output_language"] == "zh"


def test_question_understanding_output_language_is_always_zh_for_english_questions():
    from question_understanding.router import understand_question

    result = understand_question("Summarize channel performance")

    assert result["analysis_task"]["output_language"] == "zh"
    assert all("English" not in question for question in result["clarification_questions"])


def test_question_understanding_agent_writes_state_and_trace_without_sql():
    from agents.question_understanding import run_question_understanding_agent
    from agents.supervisor import initialize_run

    state = initialize_run(
        "最近 30 天销售额最高的 5 个商品是什么？",
        run_id="run_question_understanding_test",
        session_id="session_question_understanding_test",
    )

    result = run_question_understanding_agent(state)

    assert result["question_understanding"]["strategy"] == "template"
    assert result["intent_slots"]["metric"] == "gmv"
    assert result["routing_strategy"] == "template"
    assert "generated_sql" not in result
    assert result["trace"][-1]["node"] == "question_understanding_agent"
    assert result["trace"][-1]["tool_name"] == "question_understanding_router"
    assert result["trace"][-1]["status"] == "success"


def test_question_understanding_does_not_implement_sql_planning_router_fields():
    from question_understanding.router import understand_question

    result = understand_question("最近 30 天销售额最高的 5 个商品是什么？")

    assert result["strategy"] == "template"
    assert "matched_template" not in result
    assert "confidence" not in result
    assert "sql" not in result
    assert "selected_tables" not in result
