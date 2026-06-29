from graph.nodes import route_after_clarification, route_after_sql_planning


def test_continuation_does_not_stop_for_second_provider_clarification() -> None:
    route = route_after_clarification(
        {
            "routing_strategy": "clarify",
            "stop_for_clarification": False,
            "pending_run_id": "pending_123",
            "clarification_answer": "最近 90 天，按渠道比较收入、投放成本和 ROI。",
            "resolved_question": "帮我分析渠道表现。补充回答：最近 90 天，按渠道比较收入、投放成本和 ROI。",
            "question_understanding": {"source": "provider", "strategy": "clarify"},
            "clarification_result": {
                "provider_called": True,
                "requires_clarification": True,
                "clarification_questions": ["还需要确认时间范围。"],
            },
        }
    )

    assert route == "schema"


def test_continuation_does_not_stop_for_provider_sql_planning_clarification() -> None:
    route = route_after_sql_planning(
        {
            "routing_strategy": "clarify",
            "stop_for_clarification": False,
            "pending_run_id": "pending_123",
            "clarification_answer": "最近 90 天，按渠道比较收入、投放成本和 ROI。",
            "resolved_question": "帮我分析渠道表现。补充回答：最近 90 天，按渠道比较收入、投放成本和 ROI。",
            "sql_planning": {
                "source": "provider",
                "strategy": "clarify",
                "reason": "Provider asked for more context.",
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
