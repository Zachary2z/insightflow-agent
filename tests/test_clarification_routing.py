from graph.nodes import route_after_clarification


def test_clarification_router_asks_chinese_question_for_missing_metric_and_time_range() -> None:
    from question_understanding.clarification import clarify_with_provider
    from question_understanding.router import understand_question

    understanding = understand_question("帮我分析渠道表现，看看哪个渠道该加预算")
    result = clarify_with_provider("帮我分析渠道表现，看看哪个渠道该加预算", understanding)

    assert result["success"] is True
    assert result["requires_clarification"] is True
    assert set(result["missing_slots"]) == {"metric", "time_range"}
    assert result["clarification_questions"] == ["请补充要分析的指标和时间范围，例如：最近90天看销售额。"]
    assert result["analysis_task"]["output_language"] == "zh"


def test_partial_continuation_answer_still_stops_for_missing_time_range() -> None:
    route = route_after_clarification(
        {
            "routing_strategy": "clarify",
            "stop_for_clarification": False,
            "pending_run_id": "pending_123",
            "clarification_answer": "花费",
            "resolved_question": "帮我分析渠道表现，看看哪个渠道该加预算。补充条件：花费。",
            "question_understanding": {"source": "provider", "strategy": "clarify"},
            "clarification_result": {
                "provider_called": True,
                "requires_clarification": True,
                "missing_slots": ["time_range"],
                "clarification_questions": ["请补充时间范围，例如最近90天。"],
            },
        }
    )

    assert route == "early_response"


def test_complete_continuation_answer_can_resume_analysis() -> None:
    route = route_after_clarification(
        {
            "routing_strategy": "clarify",
            "stop_for_clarification": False,
            "pending_run_id": "pending_123",
            "clarification_answer": "最近 90 天",
            "resolved_question": "帮我分析渠道表现，看看哪个渠道该加预算。补充条件：花费，最近 90 天。",
            "question_understanding": {"source": "deterministic", "strategy": "llm_candidate"},
            "clarification_result": {
                "provider_called": False,
                "requires_clarification": False,
                "missing_slots": [],
                "clarification_questions": [],
            },
        }
    )

    assert route == "schema"


def test_provider_clarification_router_can_clear_initial_clarify_route() -> None:
    route = route_after_clarification(
        {
            "routing_strategy": "clarify",
            "stop_for_clarification": True,
            "question_understanding": {"source": "provider_unavailable", "strategy": "clarify"},
            "clarification_result": {
                "provider_called": True,
                "requires_clarification": False,
                "missing_slots": [],
                "clarification_questions": [],
            },
        }
    )

    assert route == "schema"
