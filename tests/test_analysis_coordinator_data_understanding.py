from workspaces.analysis_contracts import AnalysisTask, CoordinatorDecision


def test_coordinator_data_understanding_handles_complete_chinese_question():
    from workspaces.analysis_coordinator import coordinate_analysis_question

    result = coordinate_analysis_question("最近90天按门店比较销售额")

    task = result["analysis_task"]
    decision = result["coordinator_decision"]

    assert isinstance(task, AnalysisTask)
    assert isinstance(decision, CoordinatorDecision)
    assert task.resolved_question == "最近90天按门店比较销售额"
    assert task.metrics == ["销售额"]
    assert task.dimensions == ["门店"]
    assert task.time_range == {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"}
    assert task.missing_slots == []
    assert task.clarification_question == ""
    assert task.business_lens["needs_clarification"] is False
    assert decision.route in {"fast_fact", "standard_analysis"}
    assert decision.user_language == "zh"
    assert "数据理解" in decision.required_agents


def test_coordinator_clarifies_missing_slots_with_chinese_question():
    from workspaces.analysis_coordinator import coordinate_analysis_question

    result = coordinate_analysis_question("帮我分析渠道表现，看看哪个渠道该加预算")

    task = result["analysis_task"]
    decision = result["coordinator_decision"]

    assert set(task.missing_slots) == {"metric", "time_range"}
    assert task.clarification_question == "请补充要分析的指标和时间范围，例如：最近90天看销售额。"
    assert task.route_hint == "clarify"
    assert decision.route == "clarify"
    assert decision.required_agents == ["数据理解"]
    assert "追问" in decision.reason


def test_data_understanding_merges_clarification_answer_into_resolved_question():
    from workspaces.data_understanding_agent import continue_data_question

    result = continue_data_question(
        original_question="帮我看看销售情况",
        clarification_answer="按商品，最近90天，看 Top 5",
        clarification_context={
            "clarification_question": "请补充分析维度和时间范围。",
            "question_understanding": {"missing_slots": ["dimension", "time_range"]},
        },
    )

    task = result["analysis_task"]

    assert isinstance(task, AnalysisTask)
    assert "帮我看看销售情况" in task.resolved_question
    assert "按商品，最近90天，看 Top 5" in task.resolved_question
    assert "追问" not in task.resolved_question
    assert task.missing_slots == []
    assert task.clarification_question == ""


def test_data_understanding_uses_full_data_time_range_when_safe():
    from workspaces.analysis_coordinator import coordinate_analysis_question

    workspace_context = {
        "semantic_metrics": [
            {
                "name": "sum_sales_amount",
                "label": "销售额",
                "field": "store_sales.sales_amount",
                "aliases": ["销售额"],
            }
        ],
        "semantic_dimensions": [
            {
                "name": "store_name",
                "label": "门店",
                "field": "store_sales.store_name",
                "aliases": ["门店"],
            }
        ],
        "semantic_time_fields": [
            {
                "name": "business_date",
                "label": "业务日期",
                "field": "store_sales.business_date",
                "enabled": True,
            }
        ],
        "tables": [
            {
                "table_name": "store_sales",
                "columns": [
                    {
                        "name": "business_date",
                        "value_range": {"min": "2025-01-15", "max": "2026-06-30"},
                    }
                ],
            }
        ],
    }

    result = coordinate_analysis_question("哪个门店销售额最高？", workspace_context=workspace_context)
    task = result["analysis_task"]

    assert task.time_range["type"] == "full_data_range"
    assert task.time_range["raw_text"] == "完整数据时间范围：2025-01-15 至 2026-06-30"
    assert "完整可用时间范围" in task.resolved_question
    assert task.missing_slots == []
    assert task.business_lens["metrics"][0]["time_field"] == "business_date"
    assert result["coordinator_decision"].route == "fast_fact"


def test_data_understanding_does_not_default_full_data_range_without_profile_range():
    from workspaces.analysis_coordinator import coordinate_analysis_question

    workspace_context = {
        "semantic_metrics": [
            {
                "name": "sum_revenue",
                "label": "收入",
                "table": "orders",
                "field": "orders.revenue",
                "aliases": ["收入"],
                "business_meaning_candidates": ["revenue_like", "amount_like"],
            }
        ],
        "semantic_dimensions": [
            {
                "name": "channel",
                "label": "渠道",
                "table": "orders",
                "field": "orders.channel",
                "aliases": ["渠道"],
            }
        ],
        "semantic_time_fields": [
            {
                "name": "order_date",
                "label": "下单日期",
                "table": "orders",
                "field": "orders.order_date",
                "enabled": True,
            }
        ],
        "tables": [
            {
                "table_name": "orders",
                "columns": [{"name": "order_date"}],
            }
        ],
    }

    result = coordinate_analysis_question("哪个渠道收入最高？", workspace_context=workspace_context)
    task = result["analysis_task"]

    assert task.business_lens["metrics"][0]["time_field"] == "order_date"
    assert task.business_lens["time_range"] == {}
    assert task.time_range == {}
    assert "time_range" in task.missing_slots
    assert "time_range" in result["question_understanding"]["missing_slots"]
    assert result["coordinator_decision"].route == "clarify"
    assert "时间范围" in task.clarification_question


def test_data_understanding_business_lens_allows_cross_table_metric_time_fields():
    from workspaces.analysis_coordinator import coordinate_analysis_question

    workspace_context = {
        "semantic_metrics": [
            {
                "name": "sum_revenue",
                "label": "收入",
                "table": "orders",
                "field": "orders.revenue",
                "aliases": ["收入", "营收", "revenue"],
                "business_meaning_candidates": ["revenue_like", "amount_like"],
            },
            {
                "name": "sum_spend",
                "label": "投放花费",
                "table": "marketing_spend",
                "field": "marketing_spend.spend",
                "aliases": ["投放花费", "投放金额", "spend"],
                "business_meaning_candidates": ["spend_like", "cost_like", "amount_like"],
            },
        ],
        "semantic_dimensions": [
            {"name": "channel", "label": "渠道", "table": "orders", "field": "orders.channel", "aliases": ["渠道"]},
            {
                "name": "channel",
                "label": "渠道",
                "table": "marketing_spend",
                "field": "marketing_spend.channel",
                "aliases": ["渠道"],
            },
        ],
        "semantic_time_fields": [
            {"name": "order_date", "label": "下单日期", "table": "orders", "field": "orders.order_date", "enabled": True},
            {
                "name": "spend_date",
                "label": "投放日期",
                "table": "marketing_spend",
                "field": "marketing_spend.spend_date",
                "enabled": True,
            },
        ],
        "tables": [
            {
                "table_name": "orders",
                "columns": [{"name": "order_date", "value_range": {"min": "2026-01-01", "max": "2026-06-30"}}],
            },
            {
                "table_name": "marketing_spend",
                "columns": [{"name": "spend_date", "value_range": {"min": "2026-01-01", "max": "2026-06-30"}}],
            },
        ],
    }

    result = coordinate_analysis_question("各渠道投放花费和收入表现怎么样？", workspace_context=workspace_context)
    task = result["analysis_task"]
    metrics = {metric["metric_role"]: metric for metric in task.business_lens["metrics"]}

    assert task.missing_slots == []
    assert "date_field" not in result["question_understanding"]["missing_slots"]
    assert task.business_lens["needs_clarification"] is False
    assert metrics["revenue_like"]["time_field"] == "order_date"
    assert metrics["spend_like"]["time_field"] == "spend_date"
    assert "收入按下单日期" in task.business_lens["time_policy_note"]
    assert "投放花费按投放日期" in task.business_lens["time_policy_note"]
    assert result["coordinator_decision"].route != "clarify"


def test_coordinator_keeps_simple_fact_route_lightweight():
    from workspaces.analysis_coordinator import coordinate_analysis_question

    result = coordinate_analysis_question("最近90天总销售额是多少？")

    decision = result["coordinator_decision"]

    assert decision.route == "fast_fact"
    assert "答案复核" not in decision.required_agents
    assert "报告撰写" not in decision.required_agents
    assert decision.required_agents == ["数据理解", "证据查询", "证据审计", "业务回答"]


def test_route_policy_treats_semantic_metric_id_and_business_label_as_one_fast_fact_metric():
    from question_understanding.route_policy import classify_analysis_route

    route = classify_analysis_route(
        "最近90天哪个门店销售额最高？",
        analysis_task={
            "task_type": "rank",
            "metrics": ["sum_sales_amount", "销售额"],
            "dimensions": ["门店"],
            "time_range": {"type": "relative", "value": 90, "unit": "day"},
        },
    )

    assert route["route"] == "fast_fact"
    assert route["disqualifiers"] == []


def test_coordinator_routes_complex_diagnosis_to_full_business_agents():
    from workspaces.analysis_coordinator import coordinate_analysis_question

    result = coordinate_analysis_question("最近90天销售额、满意度综合看哪个门店最值得复盘，为什么？")

    decision = result["coordinator_decision"]

    assert decision.route in {"standard_analysis", "deep_judgment"}
    assert decision.route != "fast_fact"
    assert "证据查询" in decision.required_agents
    assert "证据审计" in decision.required_agents
    assert "业务回答" in decision.required_agents


def test_coordinator_does_not_reject_business_caveat_risk_flags():
    from workspaces.analysis_coordinator import coordinate_analysis

    decision = coordinate_analysis(
        "最近90天按门店比较销售额",
        AnalysisTask(
            resolved_question="最近90天按门店比较销售额",
            metrics=["销售额"],
            dimensions=["门店"],
            time_range={"raw_text": "最近 90 天"},
        ),
        understanding={"strategy": "llm_candidate", "risk_flags": ["数据量有限"]},
        route_policy_result={"route": "standard_analysis"},
    )

    assert decision.route == "standard_analysis"
    assert "拒绝" not in decision.reason
