from workspaces.analysis_contracts import AnalysisTask
from workspaces.evidence_tasks import (
    EvidenceTaskPlan,
    plan_evidence_tasks,
)


def _revenue_spend_lens():
    return {
        "business_domain": "channel_performance",
        "metrics": [
            {
                "label": "收入",
                "source_table": "orders",
                "source_field": "revenue",
                "time_field": "order_date",
                "metric_role": "revenue_like",
            },
            {
                "label": "投放花费",
                "source_table": "marketing_spend",
                "source_field": "spend",
                "time_field": "spend_date",
                "metric_role": "spend_like",
            },
        ],
        "dimensions": [
            {"label": "渠道", "source_table": "orders", "source_field": "channel"},
            {"label": "渠道", "source_table": "marketing_spend", "source_field": "channel"},
        ],
        "time_range": {"type": "full_data_range", "raw_text": "各指标完整数据范围"},
        "time_policy_note": "收入按下单日期统计，投放花费按投放日期统计；用户未指定时间范围，默认使用各指标各自完整数据范围。",
        "data_limits": [],
    }


def test_fast_fact_question_creates_one_high_priority_one_sql_task():
    task = AnalysisTask(
        resolved_question="最近90天哪个渠道收入最高？",
        metrics=["收入"],
        dimensions=["渠道"],
        time_range={"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"},
        route_hint="fast_fact",
        business_lens={
            "metrics": [
                {
                    "label": "收入",
                    "source_table": "orders",
                    "source_field": "revenue",
                    "time_field": "order_date",
                    "metric_role": "revenue_like",
                }
            ],
            "dimensions": [{"label": "渠道", "source_table": "orders", "source_field": "channel"}],
            "time_policy_note": "收入按下单日期统计，时间范围为最近90天。",
        },
    )

    plan = plan_evidence_tasks(task, route="fast_fact")

    assert plan.route == "fast_fact"
    assert plan.max_evidence_tasks == 4
    assert plan.max_parallel_evidence_tasks == 3
    assert len(plan.tasks) == 1
    assert plan.tasks[0].priority == 1
    assert plan.tasks[0].purpose == "core_fact"
    assert plan.tasks[0].sql_policy["max_sql_statements"] == 1
    assert plan.tasks[0].sql_policy["review_before_execution"] is True
    assert plan.tasks[0].sql_policy["parallel_review_and_execution_allowed"] is False


def test_revenue_spend_question_creates_revenue_spend_and_efficiency_tasks():
    task = AnalysisTask(
        resolved_question="各渠道投放花费和收入表现怎么样？",
        metrics=["收入", "投放花费"],
        dimensions=["渠道"],
        route_hint="standard_analysis",
        business_lens=_revenue_spend_lens(),
    )

    plan = plan_evidence_tasks(task, route="standard_analysis")
    purposes = [item.purpose for item in plan.tasks]
    metric_groups = [item.metrics for item in plan.tasks]

    assert 3 <= len(plan.tasks) <= 4
    assert purposes[:2] == ["core_fact", "core_fact"]
    assert "explanation_support" in purposes
    assert ["收入"] in metric_groups
    assert ["投放花费"] in metric_groups
    assert any(set(group) == {"收入", "投放花费"} for group in metric_groups)
    assert [item.priority for item in plan.tasks] == sorted(item.priority for item in plan.tasks)


def test_max_task_count_is_capped_at_four_and_defaults_parallel_to_three():
    lens = _revenue_spend_lens()
    lens["metrics"] = [
        *lens["metrics"],
        {"label": "订单量", "source_table": "orders", "source_field": "order_id", "time_field": "order_date"},
        {"label": "客单价", "source_table": "orders", "source_field": "revenue", "time_field": "order_date"},
        {"label": "复购率", "source_table": "orders", "source_field": "customer_id", "time_field": "order_date"},
    ]
    task = AnalysisTask(
        resolved_question="按渠道综合比较收入、投放花费、订单量、客单价和复购率。",
        metrics=["收入", "投放花费", "订单量", "客单价", "复购率"],
        dimensions=["渠道"],
        route_hint="deep_judgment",
        business_lens=lens,
    )

    plan = plan_evidence_tasks(task, route="deep_judgment")

    assert len(plan.tasks) == 4
    assert plan.max_evidence_tasks == 4
    assert plan.max_parallel_evidence_tasks == 3
    assert plan.data_limits


def test_unsupported_broad_question_produces_clarification_plan_not_fake_tasks():
    task = AnalysisTask(
        resolved_question="各渠道表现怎么样？",
        metrics=[],
        dimensions=["渠道"],
        route_hint="standard_analysis",
        business_lens={
            "needs_clarification": True,
            "clarification_question": "你更关注收入、投放效率、客服体验还是综合表现？请补充要分析的指标口径。",
            "data_limits": ["当前问题没有足够明确的业务指标。"],
        },
    )

    plan = plan_evidence_tasks(task, route="standard_analysis")

    assert plan.status == "needs_clarification"
    assert plan.tasks == []
    assert "指标" in plan.needs_clarification
    assert plan.data_limits == ["当前问题没有足够明确的业务指标。"]


def test_task_plan_round_trips_as_analysis_task_metadata():
    task = AnalysisTask(
        resolved_question="各渠道投放花费和收入表现怎么样？",
        metrics=["收入", "投放花费"],
        dimensions=["渠道"],
        route_hint="standard_analysis",
        business_lens=_revenue_spend_lens(),
    )
    plan = plan_evidence_tasks(task, route="standard_analysis")
    task.evidence_task_plan = plan.to_dict()

    restored = AnalysisTask.from_dict(task.to_dict())
    restored_plan = EvidenceTaskPlan.from_dict(restored.evidence_task_plan)

    assert restored_plan.route == "standard_analysis"
    assert len(restored_plan.tasks) >= 3
    assert restored_plan.tasks[0].sql_policy["max_sql_statements"] == 1
