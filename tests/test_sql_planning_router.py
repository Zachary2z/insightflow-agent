def test_sql_planning_routes_stable_top_product_intent_to_template():
    from question_understanding.router import understand_question
    from sql_planning.router import plan_sql_strategy

    understanding = understand_question("最近 30 天销售额最高的 5 个商品是什么？")
    result = plan_sql_strategy(understanding)

    assert result["success"] is True
    assert result["strategy"] == "template"
    assert result["matched_template"] == "top_products_gmv"
    assert result["confidence"] >= 0.9
    assert result["template_variables"] == {
        "metric": "gmv",
        "dimension": "product",
        "operation": "top_n",
        "limit": 5,
        "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近 30 天"},
        "filters": ["paid_orders"],
    }
    assert result["missing_slots"] == []
    assert result["clarification_questions"] == []
    assert result["risk_flags"] == []
    assert result["validation_policy"]["must_validate_sql_before_execution"] is True
    assert "sql" not in result
    assert "generated_sql" not in result


def test_sql_planning_routes_category_and_city_intents_to_templates():
    from question_understanding.router import understand_question
    from sql_planning.router import plan_sql_strategy

    category = plan_sql_strategy(understand_question("最近 3 个月销售额最高的 10 个品类是什么？"))
    city = plan_sql_strategy(understand_question("本月每个城市的总销售额情况"))

    assert category["strategy"] == "template"
    assert category["matched_template"] == "top_categories_gmv"
    assert category["template_variables"]["limit"] == 10
    assert city["strategy"] == "template"
    assert city["matched_template"] == "city_gmv_summary"


def test_sql_planning_preserves_clarify_and_reject_routes():
    from question_understanding.router import understand_question
    from sql_planning.router import plan_sql_strategy

    clarify = plan_sql_strategy(understand_question("帮我看看销售情况"))
    reject = plan_sql_strategy(understand_question("帮我导出所有用户的手机号和邮箱"))

    assert clarify["strategy"] == "clarify"
    assert clarify["matched_template"] == ""
    assert clarify["confidence"] == 0.0
    assert "dimension" in clarify["missing_slots"]
    assert clarify["clarification_questions"]
    assert reject["strategy"] == "reject"
    assert reject["matched_template"] == ""
    assert reject["risk_flags"] == ["sensitive_field", "bulk_export"]
    assert reject["rejection_reason"] == "Request asks for sensitive fields or unsafe data access."


def test_sql_planning_routes_complete_non_template_intent_to_guarded_llm_candidate():
    from question_understanding.router import understand_question
    from sql_planning.router import plan_sql_strategy

    result = plan_sql_strategy(understand_question("最近 30 天按用户、按月分析复购率趋势"))

    assert result["success"] is True
    assert result["strategy"] == "llm_candidate"
    assert result["matched_template"] == ""
    assert 0 < result["confidence"] < 0.8
    assert result["candidate_policy"] == {
        "provider_prompt_id": "guarded_sql_candidate",
        "must_validate_sql_before_execution": True,
        "fallback_strategy": "clarify_or_deterministic_baseline",
    }
    assert result["reason"] == "Complete intent is not covered by a deterministic SQL template."
    assert "sql" not in result
    assert "generated_sql" not in result


def test_sql_planning_llm_candidate_route_never_calls_provider_or_returns_sql():
    from sql_planning.router import plan_sql_strategy

    understanding = {
        "success": True,
        "strategy": "llm_candidate",
        "intent": {
            "metric": "aov",
            "dimension": "channel",
            "time_range": {"type": "this_month", "raw_text": "本月"},
            "filters": ["paid_orders"],
            "operation": "comparison",
            "limit": None,
            "risk_flags": [],
        },
        "missing_slots": [],
        "clarification_questions": [],
        "risk_flags": [],
    }

    result = plan_sql_strategy(understanding)

    assert result["strategy"] == "llm_candidate"
    assert result["candidate_policy"]["provider_prompt_id"] == "guarded_sql_candidate"
    assert "provider_result" not in result
    assert "llm_response" not in result
    assert "sql" not in result
    assert "generated_sql" not in result
