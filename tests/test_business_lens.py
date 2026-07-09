from question_understanding.business_lens import build_business_lens
from question_understanding.router import understand_question


def _context():
    return {
        "semantic_metrics": [
            {
                "name": "sum_revenue",
                "label": "收入",
                "table": "orders",
                "field": "orders.revenue",
                "aliases": ["收入", "营收", "销售额", "revenue"],
                "business_meaning_candidates": ["revenue_like", "amount_like"],
            },
            {
                "name": "sum_spend",
                "label": "投放花费",
                "table": "marketing_spend",
                "field": "marketing_spend.spend",
                "aliases": ["投放花费", "投放金额", "广告费", "spend"],
                "business_meaning_candidates": ["spend_like", "cost_like", "amount_like"],
            },
            {
                "name": "avg_satisfaction_score",
                "label": "满意度",
                "table": "support_tickets",
                "field": "support_tickets.satisfaction_score",
                "aliases": ["满意度", "评分", "NPS"],
                "business_meaning_candidates": ["rating_like"],
            },
        ],
        "semantic_dimensions": [
            {
                "name": "channel",
                "label": "渠道",
                "table": "orders",
                "field": "orders.channel",
                "aliases": ["渠道", "channel"],
            },
            {
                "name": "channel",
                "label": "渠道",
                "table": "marketing_spend",
                "field": "marketing_spend.channel",
                "aliases": ["渠道", "channel"],
            },
            {
                "name": "issue_type",
                "label": "问题类型",
                "table": "support_tickets",
                "field": "support_tickets.issue_type",
                "aliases": ["问题类型", "工单类型"],
            },
            {
                "name": "region",
                "label": "区域",
                "table": "customers",
                "field": "customers.region",
                "aliases": ["区域", "地区"],
            },
        ],
        "semantic_time_fields": [
            {
                "name": "order_date",
                "label": "下单日期",
                "table": "orders",
                "field": "orders.order_date",
                "enabled": True,
                "aliases": ["下单日期", "订单日期"],
            },
            {
                "name": "spend_date",
                "label": "投放日期",
                "table": "marketing_spend",
                "field": "marketing_spend.spend_date",
                "enabled": True,
                "aliases": ["投放日期"],
            },
            {
                "name": "ticket_date",
                "label": "工单日期",
                "table": "support_tickets",
                "field": "support_tickets.ticket_date",
                "enabled": True,
                "aliases": ["工单日期"],
            },
            {
                "name": "registration_date",
                "label": "注册日期",
                "table": "customers",
                "field": "customers.registration_date",
                "enabled": True,
                "aliases": ["注册日期", "新增日期"],
            },
        ],
        "tables": [
            {
                "table_name": "orders",
                "columns": [
                    {"name": "order_date", "value_range": {"min": "2026-01-01", "max": "2026-06-30"}},
                    {"name": "customer_id", "roles": {"id": True}},
                ],
            },
            {
                "table_name": "marketing_spend",
                "columns": [
                    {"name": "spend_date", "value_range": {"min": "2026-01-01", "max": "2026-06-30"}},
                ],
            },
            {
                "table_name": "support_tickets",
                "columns": [
                    {"name": "ticket_date", "value_range": {"min": "2026-01-01", "max": "2026-06-30"}},
                ],
            },
            {
                "table_name": "customers",
                "columns": [
                    {"name": "customer_id", "roles": {"id": True}},
                    {"name": "registration_date", "value_range": {"min": "2026-01-01", "max": "2026-06-30"}},
                ],
            },
        ],
    }


def _lens(question: str):
    understanding = understand_question(question, workspace_context=_context())
    return build_business_lens(
        question,
        analysis_task=understanding["analysis_task"],
        workspace_context=_context(),
    ).to_dict()


def _lens_with_context(question: str, context: dict):
    understanding = understand_question(question, workspace_context=context)
    return build_business_lens(
        question,
        analysis_task=understanding["analysis_task"],
        workspace_context=context,
    ).to_dict()


def _context_without_profile_ranges():
    context = _context()
    for table in context["tables"]:
        for column in table["columns"]:
            if column["name"] in {"order_date", "spend_date"}:
                column.pop("value_range", None)
    return context


def test_revenue_question_binds_revenue_metric_to_order_date():
    lens = _lens("最近90天哪个渠道收入最高？")

    assert lens["needs_clarification"] is False
    metric = lens["metrics"][0]
    assert metric["metric_role"] == "revenue_like"
    assert metric["source_table"] == "orders"
    assert metric["source_field"] == "revenue"
    assert metric["time_field"] == "order_date"
    assert lens["time_range"] == {"type": "last_n_days", "value": 90, "raw_text": "最近 90 天"}


def test_spend_question_binds_spend_metric_to_spend_date():
    lens = _lens("哪个渠道投放花费最高？")

    metric = lens["metrics"][0]
    assert lens["needs_clarification"] is False
    assert metric["metric_role"] == "spend_like"
    assert metric["source_table"] == "marketing_spend"
    assert metric["source_field"] == "spend"
    assert metric["time_field"] == "spend_date"


def test_support_question_binds_satisfaction_metric_to_ticket_date():
    lens = _lens("哪个问题类型满意度最低？")

    metric = lens["metrics"][0]
    dimension = lens["dimensions"][0]
    assert lens["needs_clarification"] is False
    assert metric["metric_role"] == "support_like"
    assert metric["source_table"] == "support_tickets"
    assert metric["source_field"] == "satisfaction_score"
    assert metric["time_field"] == "ticket_date"
    assert dimension["source_field"] == "issue_type"


def test_customer_registration_question_uses_registration_date_or_clear_limit():
    lens = _lens("哪个区域新增客户最多？")

    if lens["needs_clarification"]:
        assert lens["data_limits"]
        assert "订单" not in "\n".join(lens["data_limits"])
    else:
        metric = lens["metrics"][0]
        assert metric["metric_role"] == "customer_registration_count"
        assert metric["source_table"] == "customers"
        assert metric["source_field"] == "customer_id"
        assert metric["time_field"] == "registration_date"


def test_cross_table_revenue_and_spend_keep_per_metric_time_fields_without_clarification():
    lens = _lens("各渠道投放花费和收入表现怎么样？")

    by_role = {metric["metric_role"]: metric for metric in lens["metrics"]}
    assert lens["needs_clarification"] is False
    assert {"revenue_like", "spend_like"}.issubset(by_role)
    assert by_role["revenue_like"]["source_table"] == "orders"
    assert by_role["revenue_like"]["time_field"] == "order_date"
    assert by_role["spend_like"]["source_table"] == "marketing_spend"
    assert by_role["spend_like"]["time_field"] == "spend_date"
    assert "收入按下单日期" in lens["time_policy_note"]
    assert "投放花费按投放日期" in lens["time_policy_note"]
    assert "完整数据范围" in lens["time_policy_note"]


def test_missing_profile_range_does_not_default_to_empty_full_data_range():
    lens = _lens_with_context("哪个渠道收入最高？", _context_without_profile_ranges())

    assert lens["time_range"] == {}
    assert lens["needs_clarification"] is True
    assert "时间范围" in lens["clarification_question"]
    assert "数据画像" in "\n".join(lens["data_limits"])
    assert "默认使用" not in lens["time_policy_note"]
    assert "完整数据范围" not in lens["time_policy_note"]


def test_cross_table_missing_one_profile_range_does_not_default_any_metric_to_empty_full_range():
    context = _context()
    for table in context["tables"]:
        if table["table_name"] == "marketing_spend":
            table["columns"] = [{"name": "spend_date", "value_range": {"min": "2026-01-01"}}]

    lens = _lens_with_context("各渠道投放花费和收入表现怎么样？", context)

    by_role = {metric["metric_role"]: metric for metric in lens["metrics"]}
    assert by_role["revenue_like"]["time_field"] == "order_date"
    assert by_role["spend_like"]["time_field"] == "spend_date"
    assert lens["time_range"] == {}
    assert lens["needs_clarification"] is True
    assert "各指标完整数据范围" not in lens.get("time_range", {}).get("raw_text", "")
    assert "默认使用" not in lens["time_policy_note"]
    assert "marketing_spend.spend_date" in "\n".join(lens["data_limits"])


def test_broad_channel_performance_question_clarifies_business_focus():
    lens = _lens("各渠道表现怎么样？")

    assert lens["needs_clarification"] is True
    assert "收入" in lens["clarification_question"]
    assert "投放效率" in lens["clarification_question"]
    assert "客服体验" in lens["clarification_question"]


def test_store_level_question_prefers_store_compatible_metric_sources():
    context = {
        "semantic_metrics": [
            {
                "name": "sum_channel_revenue",
                "label": "收入",
                "table": "channel_spend",
                "field": "channel_spend.revenue",
                "aliases": ["收入", "销售额", "revenue"],
                "business_meaning_candidates": ["revenue_like", "amount_like"],
            },
            {
                "name": "sum_store_sales",
                "label": "销售额",
                "table": "store_sales",
                "field": "store_sales.sales_amount",
                "aliases": ["销售额", "收入", "sales"],
                "business_meaning_candidates": ["revenue_like", "amount_like"],
            },
            {
                "name": "avg_store_satisfaction",
                "label": "满意度",
                "table": "store_sales",
                "field": "store_sales.satisfaction_score",
                "aliases": ["满意度", "评分"],
                "business_meaning_candidates": ["rating_like"],
            },
        ],
        "semantic_dimensions": [
            {
                "name": "channel",
                "label": "渠道",
                "table": "channel_spend",
                "field": "channel_spend.channel",
                "aliases": ["渠道"],
            },
            {
                "name": "store_name",
                "label": "门店",
                "table": "store_sales",
                "field": "store_sales.store_name",
                "aliases": ["门店", "店铺"],
            },
        ],
        "semantic_time_fields": [
            {
                "name": "spend_date",
                "label": "投放日期",
                "table": "channel_spend",
                "field": "channel_spend.spend_date",
                "enabled": True,
            },
            {
                "name": "sale_date",
                "label": "销售日期",
                "table": "store_sales",
                "field": "store_sales.sale_date",
                "enabled": True,
            },
        ],
        "tables": [
            {
                "table_name": "channel_spend",
                "columns": [{"name": "spend_date", "value_range": {"min": "2026-04-01", "max": "2026-06-30"}}],
            },
            {
                "table_name": "store_sales",
                "columns": [{"name": "sale_date", "value_range": {"min": "2026-04-01", "max": "2026-06-30"}}],
            },
        ],
    }

    lens = build_business_lens(
        "结合门店销售额和满意度，哪个门店下一步最值得优先复盘？",
        analysis_task={
            "task_type": "recommendation",
            "metrics": ["销售额", "满意度"],
            "dimensions": ["门店"],
            "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近90天"},
            "missing_slots": [],
        },
        workspace_context=context,
    ).to_dict()

    by_role = {metric["metric_role"]: metric for metric in lens["metrics"]}

    assert lens["needs_clarification"] is False
    assert by_role["revenue_like"]["source_table"] == "store_sales"
    assert by_role["revenue_like"]["source_field"] == "sales_amount"
    assert by_role["support_like"]["source_table"] == "store_sales"
    assert lens["dimensions"][0]["source_table"] == "store_sales"


def test_contribution_question_does_not_bind_router_inferred_spend_to_unrelated_table():
    context = {
        "semantic_metrics": [
            {
                "name": "sum_product_revenue",
                "label": "销售额",
                "table": "product_sales",
                "field": "product_sales.revenue",
                "aliases": ["销售额", "成交金额", "金额"],
                "business_meaning_candidates": ["revenue_like", "amount_like"],
            },
            {
                "name": "sum_channel_spend",
                "label": "投放成本",
                "table": "channel_spend",
                "field": "channel_spend.spend",
                "aliases": ["投放成本", "投放金额", "金额"],
                "business_meaning_candidates": ["spend_like", "cost_like", "amount_like"],
            },
        ],
        "semantic_dimensions": [
            {
                "name": "product_category",
                "label": "品类",
                "table": "product_sales",
                "field": "product_sales.category",
                "aliases": ["品类", "商品品类"],
            },
            {
                "name": "channel",
                "label": "渠道",
                "table": "channel_spend",
                "field": "channel_spend.channel",
                "aliases": ["渠道"],
            },
        ],
        "semantic_time_fields": [
            {
                "name": "sales_month",
                "label": "销售月份",
                "table": "product_sales",
                "field": "product_sales.sales_month",
                "enabled": True,
            },
            {
                "name": "spend_date",
                "label": "投放日期",
                "table": "channel_spend",
                "field": "channel_spend.spend_date",
                "enabled": True,
            },
        ],
        "tables": [
            {
                "table_name": "product_sales",
                "columns": [{"name": "sales_month", "value_range": {"min": "2026-04", "max": "2026-06"}}],
            },
            {
                "table_name": "channel_spend",
                "columns": [{"name": "spend_date", "value_range": {"min": "2026-04-01", "max": "2026-06-30"}}],
            },
        ],
    }

    lens = build_business_lens(
        "最近90天按品类看成交金额贡献和占比。",
        analysis_task={
            "task_type": "rank",
            "metrics": ["销售额", "投放成本"],
            "dimensions": ["品类"],
            "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近90天"},
            "missing_slots": [],
        },
        workspace_context=context,
    ).to_dict()

    assert [metric["metric_role"] for metric in lens["metrics"]] == ["revenue_like"]
    assert lens["metrics"][0]["source_table"] == "product_sales"
    assert lens["dimensions"][0]["source_table"] == "product_sales"
    assert "channel_spend" not in str(lens)
