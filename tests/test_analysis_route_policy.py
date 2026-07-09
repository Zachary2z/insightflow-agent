import pytest


@pytest.mark.parametrize(
    ("question", "expected_route"),
    [
        ("最近90天销售额最高的门店是谁？", "fast_fact"),
        ("最近90天总销售额是多少？", "fast_fact"),
        ("最近30天各渠道收入排名", "fast_fact"),
        ("本月按周看订单量趋势怎么样？", "fast_fact"),
        ("最近90天各渠道收入表现怎么样？", "standard_analysis"),
        ("哪个门店最值得复盘，为什么？", "clarify"),
        ("哪个渠道应该加预算？", "clarify"),
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


def test_local_fast_fact_candidate_route_allows_safe_total_without_dimension():
    from question_understanding.route_policy import classify_analysis_route
    from question_understanding.router import understand_question

    question = "最近30天总销售额是多少？"
    understanding = understand_question(question)
    task = dict(understanding["analysis_task"])
    task["missing_slots"] = []
    task["local_fast_fact_gate"] = {"decision": "fast_fact_candidate"}

    route = classify_analysis_route(
        question,
        analysis_task=task,
        missing_slots=[],
        risk_flags=[],
    )

    assert route["route"] == "fast_fact"
    assert route["fast_path_eligible"] is True
    assert route["requires_full_chain"] is False
    assert "H1" not in route["reason"]
    assert "完整分析链路" not in route["reason"]


def test_route_policy_deduplicates_provider_metric_and_dimension_aliases_for_fast_fact():
    from question_understanding.route_policy import classify_analysis_route

    route = classify_analysis_route(
        "最近90天哪个渠道收入金额最高？",
        analysis_task={
            "task_type": "rank",
            "metrics": ["销售额", "sum_sales_amount"],
            "dimensions": ["channel_name", "渠道"],
            "time_range": {"relative": "last_90_days"},
            "missing_slots": [],
        },
        missing_slots=[],
        risk_flags=[],
    )

    assert route["route"] == "fast_fact"
    assert route["fast_path_eligible"] is True
    assert route["disqualifiers"] == []


def test_route_policy_deduplicates_provider_sum_revenue_alias_for_fast_fact():
    from question_understanding.route_policy import classify_analysis_route

    route = classify_analysis_route(
        "最近90天哪个渠道收入最高？",
        analysis_task={
            "task_type": "rank",
            "metrics": ["销售额", "sum_revenue"],
            "dimensions": ["channel_name", "渠道名称", "渠道"],
            "time_range": {"start": "2026-03-14", "end": "2026-06-12"},
            "missing_slots": [],
        },
        missing_slots=[],
        risk_flags=[],
    )

    assert route["route"] == "fast_fact"
    assert route["fast_path_eligible"] is True
    assert route["disqualifiers"] == []


def test_route_policy_keeps_simple_fact_and_scope_wording_on_fast_fact():
    from question_understanding.route_policy import classify_analysis_route

    route = classify_analysis_route(
        "最近30天哪个渠道收入最高？只回答事实和口径。",
        analysis_task={
            "task_type": "rank",
            "metrics": ["收入"],
            "dimensions": ["渠道"],
            "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近30天"},
            "missing_slots": [],
            "business_lens": {
                "metrics": [
                    {
                        "label": "收入",
                        "source_table": "business_facts",
                        "source_field": "amount",
                        "metric_role": "revenue_like",
                    }
                ],
                "dimensions": [
                    {"label": "渠道", "source_table": "business_facts", "source_field": "channel_label"}
                ],
            },
        },
        missing_slots=[],
        risk_flags=[],
    )

    assert route["route"] == "fast_fact"
    assert route["fast_path_eligible"] is True
    assert route["disqualifiers"] == []


def test_route_policy_local_fast_fact_gate_overrides_extra_lens_complexity_for_simple_fact():
    from question_understanding.route_policy import classify_analysis_route

    route = classify_analysis_route(
        "最近30天哪个渠道收入最高？只回答事实。",
        analysis_task={
            "task_type": "rank",
            "metrics": ["收入"],
            "dimensions": ["渠道"],
            "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近30天"},
            "missing_slots": [],
            "local_fast_fact_gate": {"decision": "fast_fact_candidate"},
            "business_lens": {
                "metrics": [
                    {"label": "收入", "source_table": "channel_performance", "source_field": "revenue"},
                    {"label": "投放花费", "source_table": "channel_performance", "source_field": "ad_spend"},
                    {"label": "ROI", "source_table": "channel_performance", "source_field": "roas"},
                ],
                "dimensions": [
                    {"label": "渠道", "source_table": "channel_performance", "source_field": "channel_name"}
                ],
            },
        },
        missing_slots=[],
        risk_flags=[],
    )

    assert route["route"] == "fast_fact"
    assert route["fast_path_eligible"] is True
    assert route["disqualifiers"] == []


def test_route_policy_keeps_budget_advice_and_external_actions_out_of_fast_fact():
    from question_understanding.route_policy import classify_analysis_route
    from question_understanding.router import understand_question

    advice = "最近30天哪个渠道最值得加预算？请给证据和风险边界。"
    advice_understanding = understand_question(advice)

    advice_route = classify_analysis_route(
        advice,
        analysis_task=advice_understanding["analysis_task"],
        missing_slots=[],
        risk_flags=[],
    )

    external = "把预算调整到私域社群并发送通知。"
    external_route = classify_analysis_route(
        external,
        analysis_task={
            "task_type": "compare",
            "metrics": [],
            "dimensions": [],
            "time_range": None,
            "missing_slots": [],
        },
        missing_slots=[],
        risk_flags=["external_action"],
    )

    assert advice_route["route"] == "deep_judgment"
    assert advice_route["fast_path_eligible"] is False
    assert external_route["route"] != "fast_fact"
    assert external_route["fast_path_eligible"] is False
    assert "risk_flags" in external_route["disqualifiers"]


def test_route_policy_does_not_force_deep_only_because_advice_wording_is_present():
    from question_understanding.route_policy import classify_analysis_route

    route = classify_analysis_route(
        "最近30天各渠道收入排名，并给一句复盘建议。",
        analysis_task={
            "task_type": "rank",
            "metrics": ["收入"],
            "dimensions": ["渠道"],
            "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近30天"},
            "missing_slots": [],
            "business_lens": {
                "metrics": [
                    {
                        "label": "收入",
                        "source_table": "orders",
                        "source_field": "revenue",
                        "metric_role": "revenue_like",
                    }
                ],
                "dimensions": [{"label": "渠道", "source_table": "orders", "source_field": "channel"}],
            },
            "evidence_task_plan": {
                "tasks": [
                    {
                        "task_id": "revenue_by_channel",
                        "purpose": "core_fact",
                        "metrics": ["收入"],
                        "dimensions": ["渠道"],
                    }
                ]
            },
        },
        missing_slots=[],
        risk_flags=[],
    )

    assert route["route"] == "standard_analysis"
    assert route["fast_path_eligible"] is False
    assert "keyword" not in " ".join(route["disqualifiers"]).lower()


def test_route_policy_uses_evidence_complexity_even_without_judgment_keywords():
    from question_understanding.route_policy import classify_analysis_route

    route = classify_analysis_route(
        "最近30天按渠道比较收入和投放花费。",
        analysis_task={
            "task_type": "compare",
            "metrics": ["收入", "投放花费"],
            "dimensions": ["渠道"],
            "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近30天"},
            "missing_slots": [],
            "business_lens": {
                "metrics": [
                    {
                        "label": "收入",
                        "source_table": "orders",
                        "source_field": "revenue",
                        "metric_role": "revenue_like",
                    },
                    {
                        "label": "投放花费",
                        "source_table": "marketing_spend",
                        "source_field": "spend",
                        "metric_role": "spend_like",
                    },
                ],
                "dimensions": [
                    {"label": "渠道", "source_table": "orders", "source_field": "channel"},
                    {"label": "渠道", "source_table": "marketing_spend", "source_field": "channel"},
                ],
            },
            "evidence_task_plan": {
                "tasks": [
                    {
                        "task_id": "revenue_by_channel",
                        "purpose": "core_fact",
                        "metrics": ["收入"],
                        "dimensions": ["渠道"],
                    },
                    {
                        "task_id": "spend_by_channel",
                        "purpose": "core_fact",
                        "metrics": ["投放花费"],
                        "dimensions": ["渠道"],
                    },
                ]
            },
        },
        missing_slots=[],
        risk_flags=[],
    )

    assert route["route"] == "deep_judgment"
    assert "evidence_task_count" in route["disqualifiers"]
    assert "source_table_count" in route["disqualifiers"]
