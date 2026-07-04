from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "data" / "metrics.yaml"


def test_retrieve_metric_definition_matches_sales_question():
    from tools.metric_tool import retrieve_metric_definition

    result = retrieve_metric_definition("最近 30 天销售额最高的 5 个商品是什么？")

    assert result["success"] is True
    assert result["matched_metrics"] == ["gmv", "product_sales"]
    assert result["metrics"]["gmv"]["formula"] == "SUM(order_items.quantity * order_items.unit_price)"
    assert "orders.status = 'paid'" in result["metrics"]["gmv"]["required_filters"]
    assert result["trace_event"]["tool_name"] == "retrieve_metric_definition"
    assert result["trace_event"]["status"] == "success"


def test_retrieve_metric_definition_matches_order_count_and_aov():
    from tools.metric_tool import retrieve_metric_definition

    result = retrieve_metric_definition("最近 6 个月每个月的订单量和客单价是多少？")

    assert result["success"] is True
    assert result["matched_metrics"] == ["order_count", "aov"]
    assert result["metrics"]["order_count"]["formula"] == "COUNT(DISTINCT orders.id)"
    assert "SUM(order_items.quantity * order_items.unit_price)" in result["metrics"]["aov"]["formula"]


def test_retrieve_metric_definition_matches_category_gmv():
    from tools.metric_tool import retrieve_metric_definition

    result = retrieve_metric_definition("最近 3 个月销售额最高的品类是什么？")

    assert result["success"] is True
    assert result["matched_metrics"] == ["gmv", "category_gmv"]
    assert result["metrics"]["category_gmv"]["group_by"] == ["categories.category_name"]


def test_retrieve_metric_definition_returns_error_for_unknown_metric():
    from tools.metric_tool import retrieve_metric_definition

    result = retrieve_metric_definition("帮我分析用户喜欢什么颜色")

    assert result["success"] is False
    assert result["matched_metrics"] == []
    assert result["metrics"] == {}
    assert "No metric definition matched" in result["error"]
    assert result["trace_event"]["status"] == "error"


def test_load_metric_definitions_handles_missing_file(tmp_path):
    from tools.metric_tool import load_metric_definitions

    result = load_metric_definitions(tmp_path / "missing.yaml")

    assert result["success"] is False
    assert result["metrics"] == {}
    assert "not found" in result["error"]


def test_retrieve_metric_definition_can_use_workspace_semantic_layer(tmp_path):
    import yaml

    from tools.metric_tool import retrieve_metric_definition

    semantic_layer_path = tmp_path / "semantic_layer.yaml"
    semantic_layer_path.write_text(
        yaml.safe_dump(
            {
                "workspace_id": "store-workspace",
                "metrics": [
                    {
                        "name": "sum_sales_amount",
                        "label": "SUM Sales Amount",
                        "field": "store_operations.sales_amount",
                        "formula": "SUM(store_operations.sales_amount)",
                        "aliases": ["sales amount", "营业额"],
                    }
                ],
                "dimensions": [
                    {
                        "name": "store_name",
                        "field": "store_operations.store_name",
                        "aliases": ["store name", "门店"],
                    }
                ],
                "time_fields": [],
                "entities": [],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = retrieve_metric_definition("按门店看营业额", semantic_layer_path=semantic_layer_path)

    assert result["success"] is True
    assert result["source"] == "workspace_semantic_layer"
    assert result["matched_metrics"] == ["sum_sales_amount"]
    assert result["metrics"]["sum_sales_amount"]["field"] == "store_operations.sales_amount"
    assert result["semantic_context"]["matched_dimensions"] == ["store_name"]


def test_metric_registry_distinguishes_roas_net_return_and_margin_formulas():
    from tools.metric_tool import build_metric_registry

    semantic_layer = {
        "metrics": [
            {
                "name": "sum_revenue",
                "label": "销售额",
                "field": "campaigns.revenue",
                "formula": 'SUM("campaigns"."revenue")',
                "business_meaning": "revenue_like",
                "source_fields": ["campaigns.revenue"],
            },
            {
                "name": "sum_spend",
                "label": "投放成本",
                "field": "campaigns.spend",
                "formula": 'SUM("campaigns"."spend")',
                "business_meaning": "spend_like",
                "source_fields": ["campaigns.spend"],
            },
            {
                "name": "sum_cost",
                "label": "成本",
                "field": "campaigns.cost",
                "formula": 'SUM("campaigns"."cost")',
                "business_meaning": "cost_like",
                "source_fields": ["campaigns.cost"],
            },
        ]
    }

    result = build_metric_registry(semantic_layer)

    assert result["success"] is True
    formulas = result["formulas"]
    assert formulas["roas"] == '1.0 * SUM("campaigns"."revenue") / NULLIF(SUM("campaigns"."spend"), 0)'
    assert formulas["net_return"] == (
        '1.0 * (SUM("campaigns"."revenue") - SUM("campaigns"."spend")) '
        '/ NULLIF(SUM("campaigns"."spend"), 0)'
    )
    assert formulas["margin_rate"] == (
        '1.0 * (SUM("campaigns"."revenue") - SUM("campaigns"."cost")) '
        '/ NULLIF(SUM("campaigns"."revenue"), 0)'
    )
    assert result["metrics"]["roas"]["business_label"] == "广告投入产出比"
    assert result["metrics"]["net_return"]["business_label"] == "净投放回报率"
    assert result["metrics"]["margin_rate"]["business_label"] == "利润率"
    assert result["metrics"]["roas"]["source_fields"] == ["campaigns.revenue", "campaigns.spend"]
    assert result["metrics"]["net_return"]["source_fields"] == ["campaigns.revenue", "campaigns.spend"]
    assert result["metrics"]["margin_rate"]["source_fields"] == ["campaigns.revenue", "campaigns.cost"]


def test_metric_registry_does_not_invent_derived_metrics_without_source_fields():
    from tools.metric_tool import build_metric_registry

    semantic_layer = {
        "metrics": [
            {
                "name": "sum_ticket_count",
                "label": "工单数",
                "field": "support_tickets.ticket_id",
                "formula": 'COUNT("support_tickets"."ticket_id")',
                "business_meaning": "count_like",
                "source_fields": ["support_tickets.ticket_id"],
            },
            {
                "name": "avg_resolution_hours",
                "label": "平均解决时长",
                "field": "support_tickets.resolution_hours",
                "formula": 'AVG("support_tickets"."resolution_hours")',
                "business_meaning": "duration_like",
                "source_fields": ["support_tickets.resolution_hours"],
            },
        ]
    }

    result = build_metric_registry(semantic_layer)

    assert result["success"] is True
    assert "roas" not in result["metrics"]
    assert "net_return" not in result["metrics"]
    assert "margin_rate" not in result["metrics"]
    assert "average_order_value" not in result["metrics"]
    assert any("ROAS" in warning for warning in result["warnings"])


def test_metric_registry_can_register_average_order_value_when_sources_exist():
    from tools.metric_tool import build_metric_registry

    semantic_layer = {
        "metrics": [
            {
                "name": "sum_sales_amount",
                "label": "销售额",
                "field": "stores.Sales Amount",
                "formula": 'SUM("stores"."Sales Amount")',
                "business_meaning": "revenue_like",
                "source_fields": ["stores.Sales Amount"],
            },
            {
                "name": "count_orders",
                "label": "订单数",
                "field": "stores.order_id",
                "formula": 'COUNT("stores"."order_id")',
                "business_meaning": "order_count_like",
                "source_fields": ["stores.order_id"],
            },
        ]
    }

    result = build_metric_registry(semantic_layer)

    assert result["metrics"]["average_order_value"]["formula"] == (
        '1.0 * SUM("stores"."Sales Amount") / NULLIF(COUNT("stores"."order_id"), 0)'
    )
    assert result["metrics"]["average_order_value"]["unit"] == "currency"


def test_metric_registry_uses_general_chinese_business_meanings_for_derived_limits():
    from tools.metric_tool import build_metric_registry

    semantic_layer = {
        "metrics": [
            {
                "name": "sum_成交金额",
                "label": "销售额",
                "field": "商品销售.成交金额",
                "formula": 'SUM("商品销售"."成交金额")',
                "business_meaning_candidates": ["revenue_like", "amount_like"],
                "aliases": ["成交金额", "收入金额", "销售额"],
            },
            {
                "name": "sum_订单数",
                "label": "订单数",
                "field": "商品销售.订单数",
                "formula": 'SUM("商品销售"."订单数")',
                "business_meaning_candidates": ["order_count_like", "count_like"],
                "aliases": ["订单数", "订单量"],
            },
            {
                "name": "sum_采购成本",
                "label": "采购成本",
                "field": "商品销售.采购成本",
                "formula": 'SUM("商品销售"."采购成本")',
                "business_meaning_candidates": ["cost_like", "amount_like"],
                "aliases": ["采购成本", "成本"],
            },
        ]
    }

    result = build_metric_registry(semantic_layer)

    formulas = result["formulas"]
    assert formulas["margin_rate"] == (
        '1.0 * (SUM("商品销售"."成交金额") - SUM("商品销售"."采购成本")) '
        '/ NULLIF(SUM("商品销售"."成交金额"), 0)'
    )
    assert formulas["average_order_value"] == (
        '1.0 * SUM("商品销售"."成交金额") / NULLIF(SUM("商品销售"."订单数"), 0)'
    )
    assert "roas" not in result["metrics"]
    assert any("ROAS" in warning and "花费类字段" in warning for warning in result["warnings"])


def test_metric_registry_blocks_cross_table_roas_without_safe_relationship():
    from tools.metric_tool import build_metric_registry

    semantic_layer = {
        "metrics": [
            {
                "name": "sum_收入金额",
                "label": "收入",
                "field": "销售表.收入金额",
                "formula": 'SUM("销售表"."收入金额")',
                "business_meaning_candidates": ["revenue_like", "amount_like"],
                "source_fields": ["销售表.收入金额"],
            },
            {
                "name": "sum_投放金额",
                "label": "投放金额",
                "field": "投放表.投放金额",
                "formula": 'SUM("投放表"."投放金额")',
                "business_meaning_candidates": ["spend_like", "cost_like", "amount_like"],
                "source_fields": ["投放表.投放金额"],
            },
        ],
        "relationships": [],
        "available_analysis_capabilities": {
            "can_join_tables": False,
            "can_calculate_roi": False,
            "can_calculate_profit": False,
        },
    }

    result = build_metric_registry(semantic_layer)

    assert result["available_analysis_capabilities"]["can_join_tables"] is False
    assert result["available_analysis_capabilities"]["can_calculate_roi"] is False
    assert "roas" not in result["metrics"]
    assert "net_return" not in result["metrics"]
    assert "roas" not in result["formulas"]
    assert "net_return" not in result["formulas"]
    assert any("ROAS" in warning and "可确认关联字段" in warning for warning in result["warnings"])


def test_metric_registry_allows_same_table_roas_and_net_return():
    from tools.metric_tool import build_metric_registry

    semantic_layer = {
        "metrics": [
            {
                "name": "sum_revenue",
                "label": "收入",
                "field": "campaigns.revenue",
                "formula": 'SUM("campaigns"."revenue")',
                "business_meaning_candidates": ["revenue_like"],
                "source_fields": ["campaigns.revenue"],
            },
            {
                "name": "sum_spend",
                "label": "投放金额",
                "field": "campaigns.spend",
                "formula": 'SUM("campaigns"."spend")',
                "business_meaning_candidates": ["spend_like", "cost_like"],
                "source_fields": ["campaigns.spend"],
            },
        ],
        "available_analysis_capabilities": {
            "can_join_tables": False,
            "can_calculate_roi": True,
        },
    }

    result = build_metric_registry(semantic_layer)

    assert result["available_analysis_capabilities"]["can_calculate_roi"] is True
    assert result["formulas"]["roas"] == '1.0 * SUM("campaigns"."revenue") / NULLIF(SUM("campaigns"."spend"), 0)'
    assert result["formulas"]["net_return"] == (
        '1.0 * (SUM("campaigns"."revenue") - SUM("campaigns"."spend")) '
        '/ NULLIF(SUM("campaigns"."spend"), 0)'
    )


def test_metric_registry_allows_cross_table_roas_with_relationship():
    from tools.metric_tool import build_metric_registry

    semantic_layer = {
        "metrics": [
            {
                "name": "sum_revenue",
                "label": "收入",
                "field": "sales.revenue",
                "formula": 'SUM("sales"."revenue")',
                "business_meaning_candidates": ["revenue_like"],
                "source_fields": ["sales.revenue"],
            },
            {
                "name": "sum_spend",
                "label": "投放金额",
                "field": "campaign_spend.spend",
                "formula": 'SUM("campaign_spend"."spend")',
                "business_meaning_candidates": ["spend_like", "cost_like"],
                "source_fields": ["campaign_spend.spend"],
            },
        ],
        "relationships": [
            {
                "left_table": "sales",
                "left_field": "sales.campaign_id",
                "right_table": "campaign_spend",
                "right_field": "campaign_spend.campaign_id",
            }
        ],
        "available_analysis_capabilities": {
            "can_join_tables": True,
            "can_calculate_roi": True,
        },
    }

    result = build_metric_registry(semantic_layer)

    assert "roas" in result["metrics"]
    assert "net_return" in result["metrics"]
    assert result["available_analysis_capabilities"]["can_join_tables"] is True


def test_metric_registry_does_not_use_global_join_capability_for_unrelated_cross_table_roas():
    from tools.metric_tool import build_metric_registry

    semantic_layer = {
        "metrics": [
            {
                "name": "sum_revenue",
                "label": "收入",
                "field": "sales.revenue",
                "formula": 'SUM("sales"."revenue")',
                "business_meaning_candidates": ["revenue_like"],
                "source_fields": ["sales.revenue"],
            },
            {
                "name": "sum_spend",
                "label": "投放金额",
                "field": "ad_spend.spend",
                "formula": 'SUM("ad_spend"."spend")',
                "business_meaning_candidates": ["spend_like", "cost_like"],
                "source_fields": ["ad_spend.spend"],
            },
        ],
        "relationships": [
            {
                "left_table": "customers",
                "left_field": "customers.customer_id",
                "right_table": "orders",
                "right_field": "orders.customer_id",
            }
        ],
        "available_analysis_capabilities": {
            "can_join_tables": True,
            "can_calculate_roi": True,
        },
    }

    result = build_metric_registry(semantic_layer)

    assert result["available_analysis_capabilities"]["can_join_tables"] is True
    assert "roas" not in result["metrics"]
    assert "net_return" not in result["metrics"]
    assert "roas" not in result["formulas"]
    assert "net_return" not in result["formulas"]
    assert any("ROAS" in warning and "可确认关联字段" in warning for warning in result["warnings"])


def test_metric_registry_does_not_use_global_join_capability_for_unrelated_cross_table_margin_rate():
    from tools.metric_tool import build_metric_registry

    semantic_layer = {
        "metrics": [
            {
                "name": "sum_revenue",
                "label": "收入",
                "field": "sales.revenue",
                "formula": 'SUM("sales"."revenue")',
                "business_meaning_candidates": ["revenue_like"],
                "source_fields": ["sales.revenue"],
            },
            {
                "name": "sum_cost",
                "label": "成本",
                "field": "cost_snapshots.cost_amount",
                "formula": 'SUM("cost_snapshots"."cost_amount")',
                "business_meaning_candidates": ["cost_like"],
                "source_fields": ["cost_snapshots.cost_amount"],
            },
        ],
        "relationships": [
            {
                "left_table": "customers",
                "left_field": "customers.customer_id",
                "right_table": "orders",
                "right_field": "orders.customer_id",
            }
        ],
        "available_analysis_capabilities": {
            "can_join_tables": True,
            "can_calculate_profit": True,
        },
    }

    result = build_metric_registry(semantic_layer)

    assert result["available_analysis_capabilities"]["can_join_tables"] is True
    assert "margin_rate" not in result["metrics"]
    assert "margin_rate" not in result["formulas"]
    assert any("利润率" in warning and "可确认关联字段" in warning for warning in result["warnings"])


def test_metric_registry_uses_same_table_revenue_spend_pair_when_other_revenue_metrics_exist():
    from tools.metric_tool import build_metric_registry

    semantic_layer = {
        "metrics": [
            {
                "name": "sum_store_sales",
                "label": "门店销售额",
                "field": "store_sales.sales_amount",
                "formula": 'SUM("store_sales"."sales_amount")',
                "business_meaning_candidates": ["revenue_like"],
                "source_fields": ["store_sales.sales_amount"],
            },
            {
                "name": "sum_channel_revenue",
                "label": "渠道收入",
                "field": "channel_spend.revenue_amount",
                "formula": 'SUM("channel_spend"."revenue_amount")',
                "business_meaning_candidates": ["revenue_like"],
                "source_fields": ["channel_spend.revenue_amount"],
            },
            {
                "name": "sum_channel_spend",
                "label": "投放金额",
                "field": "channel_spend.spend_amount",
                "formula": 'SUM("channel_spend"."spend_amount")',
                "business_meaning_candidates": ["spend_like", "cost_like"],
                "source_fields": ["channel_spend.spend_amount"],
            },
            {
                "name": "sum_product_quantity",
                "label": "销量",
                "field": "product_sales.quantity",
                "formula": 'SUM("product_sales"."quantity")',
                "business_meaning_candidates": ["count_like"],
                "source_fields": ["product_sales.quantity"],
            },
        ],
        "relationships": [],
        "available_analysis_capabilities": {"can_join_tables": False, "can_calculate_roi": True},
    }

    result = build_metric_registry(semantic_layer)

    assert result["metrics"]["roas"]["formula"] == (
        '1.0 * SUM("channel_spend"."revenue_amount") / NULLIF(SUM("channel_spend"."spend_amount"), 0)'
    )
    assert result["metrics"]["net_return"]["formula"] == (
        '1.0 * (SUM("channel_spend"."revenue_amount") - SUM("channel_spend"."spend_amount")) '
        '/ NULLIF(SUM("channel_spend"."spend_amount"), 0)'
    )
    assert "average_order_value" not in result["metrics"]
