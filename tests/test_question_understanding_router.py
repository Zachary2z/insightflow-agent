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
    assert result["clarification_questions"] == [
        "请确认要按哪个维度分析，例如商品、品类、城市或用户？",
        "请确认分析时间范围，例如最近 30 天、本周、本月或最近 3 个月？",
    ]


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
