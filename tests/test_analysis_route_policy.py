import pytest


@pytest.mark.parametrize(
    ("question", "expected_route"),
    [
        ("最近90天销售额最高的门店是谁？", "fast_fact"),
        ("最近90天总销售额是多少？", "fast_fact"),
        ("最近30天各渠道收入排名", "fast_fact"),
        ("本月订单量趋势怎么样？", "fast_fact"),
        ("哪个门店最值得复盘，为什么？", "deep_judgment"),
        ("哪个渠道应该加预算？", "deep_judgment"),
        ("生成一份管理层报告", "report"),
    ],
)
def test_conservative_route_policy_classifies_required_examples(question, expected_route):
    from question_understanding.route_policy import classify_analysis_route
    from question_understanding.router import understand_question

    understanding = understand_question(question)

    route = classify_analysis_route(
        question,
        analysis_task=understanding["analysis_task"],
        missing_slots=understanding["missing_slots"],
        risk_flags=understanding["risk_flags"],
    )

    assert route["route"] == expected_route
    assert route["confidence"] in {"low", "medium", "high"}
    assert isinstance(route["reason"], str) and route["reason"]
    assert set(route) == {
        "route",
        "reason",
        "confidence",
        "requires_full_chain",
        "fast_path_eligible",
        "disqualifiers",
    }
    assert route["fast_path_eligible"] is (expected_route == "fast_fact")
    assert route["requires_full_chain"] is (expected_route != "fast_fact")


def test_conservative_route_policy_clarifies_incomplete_plain_analysis_request():
    from question_understanding.route_policy import classify_analysis_route
    from question_understanding.router import understand_question

    understanding = understand_question("帮我分析门店表现")

    route = classify_analysis_route(
        "帮我分析门店表现",
        analysis_task=understanding["analysis_task"],
        missing_slots=understanding["missing_slots"],
        risk_flags=understanding["risk_flags"],
    )

    assert route["route"] == "clarify"
    assert route["fast_path_eligible"] is False
    assert route["requires_full_chain"] is True
    assert "missing_slots" in route["disqualifiers"]


def test_conservative_route_policy_does_not_fast_path_multi_metric_tradeoff():
    from question_understanding.route_policy import classify_analysis_route
    from question_understanding.router import understand_question

    question = "销售额、毛利率、满意度综合看哪个门店最好？"
    understanding = understand_question(question)

    route = classify_analysis_route(
        question,
        analysis_task=understanding["analysis_task"],
        missing_slots=understanding["missing_slots"],
        risk_flags=understanding["risk_flags"],
    )

    assert route["route"] in {"standard_analysis", "deep_judgment"}
    assert route["route"] != "fast_fact"
    assert route["fast_path_eligible"] is False
    assert route["requires_full_chain"] is True
    assert any(disqualifier in route["disqualifiers"] for disqualifier in ("multi_metric", "judgment_intent"))


def test_question_understanding_agent_adds_analysis_route_to_state():
    from agents.question_understanding import run_question_understanding_agent
    from agents.supervisor import initialize_run

    state = initialize_run(
        "最近90天销售额最高的门店是谁？",
        run_id="run_analysis_route_state_test",
        session_id="session_analysis_route_state_test",
    )

    result = run_question_understanding_agent(state)

    assert result["analysis_route"]["route"] == "fast_fact"
    assert result["analysis_route"]["fast_path_eligible"] is True
    assert result["question_understanding"]["analysis_route"] == result["analysis_route"]
