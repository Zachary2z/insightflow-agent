from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_semantic_layer_loads_metrics_dimensions_entities_and_join_paths():
    from semantic_layer.loader import load_semantic_layer

    result = load_semantic_layer()

    assert result["success"] is True
    assert result["metrics_path"].endswith("semantic_layer/metrics.yaml")
    assert {
        "gmv",
        "net_gmv",
        "order_count",
        "aov",
        "refund_rate",
        "conversion_rate",
        "checkout_conversion_rate",
        "cac",
        "roi",
    }.issubset(result["metrics"])
    assert {"product", "category", "city", "channel", "campaign", "promotion"}.issubset(
        result["dimensions"]
    )
    assert {
        "product",
        "category",
        "city",
        "channel",
        "campaign",
        "promotion",
        "inventory",
        "refund",
        "review",
        "traffic_session",
    }.issubset(result["entities"])
    assert any(
        path["id"] == "refund_requests_to_category"
        and path["tables"] == ["refund_requests", "orders", "order_items", "products", "categories"]
        for path in result["join_paths"].values()
    )


def test_semantic_retriever_resolves_metric_aliases_to_gmv():
    from semantic_layer.retriever import retrieve_semantic_context

    for question in ["销售额趋势怎么看？", "GMV 最高的商品是什么？", "收入按城市拆分"]:
        result = retrieve_semantic_context(question)

        assert result["success"] is True
        assert result["matched_metrics"][0] == "gmv"
        assert result["metrics"]["gmv"]["formula"] == "SUM(order_items.quantity * order_items.unit_price)"


def test_semantic_retriever_returns_refund_rate_category_join_path():
    from semantic_layer.retriever import retrieve_semantic_context

    result = retrieve_semantic_context("refund_rate by category，重点看退款率最高的品类")

    assert result["success"] is True
    assert "refund_rate" in result["matched_metrics"]
    assert "category" in result["matched_dimensions"]
    assert {"refund", "order", "product", "category"}.issubset(result["matched_entities"])
    assert "refund_requests_to_category" in result["matched_join_paths"]
    join_path = result["join_paths"]["refund_requests_to_category"]
    assert join_path["tables"] == ["refund_requests", "orders", "order_items", "products", "categories"]
    assert join_path["joins"][0] == "refund_requests.order_id = orders.id"
    assert join_path["purpose"] == "Analyze refunds by product or category using paid order context."


def test_metric_tool_uses_semantic_layer_for_new_metrics_and_keeps_legacy_shape():
    from tools.metric_tool import retrieve_metric_definition

    result = retrieve_metric_definition("Paid Search 的 ROI 和 CAC 是否变差？")

    assert result["success"] is True
    assert result["matched_metrics"] == ["cac", "roi"]
    assert result["metrics"]["roi"]["formula"] == (
        "SUM(campaign_daily_metrics.attributed_gmv) / SUM(campaign_daily_metrics.spend)"
    )
    assert result["metrics"]["cac"]["required_tables"] == [
        "campaign_daily_metrics",
        "marketing_campaigns",
    ]
    assert "campaign" in result["semantic_context"]["matched_entities"]
    assert "marketing_campaigns_to_campaign_daily_metrics" in result["semantic_context"]["matched_join_paths"]
    assert result["trace_event"]["tool_name"] == "retrieve_metric_definition"


def test_metric_tool_still_supports_explicit_legacy_metrics_file(tmp_path):
    from tools.metric_tool import retrieve_metric_definition

    metrics_path = tmp_path / "metrics.yaml"
    metrics_path.write_text(
        """
custom_metric:
  name: "自定义指标"
  aliases:
    - "自定义指标"
  formula: "COUNT(*)"
  required_filters: []
  required_tables:
    - "orders"
  description: "Temporary legacy metric."
""",
        encoding="utf-8",
    )

    result = retrieve_metric_definition("帮我看自定义指标", metrics_path=metrics_path)

    assert result["success"] is True
    assert result["matched_metrics"] == ["custom_metric"]
    assert result["metrics"]["custom_metric"]["formula"] == "COUNT(*)"
    assert result["metrics_path"] == str(metrics_path)


def test_business_context_includes_semantic_context_without_replacing_markdown_matches():
    from tools.context_tool import retrieve_business_context

    result = retrieve_business_context("上海 checkout conversion rate 为什么下降？")

    assert result["success"] is True
    assert "checkout_conversion_rate" in result["semantic_context"]["matched_metrics"]
    assert "city" in result["semantic_context"]["matched_dimensions"]
    assert "traffic_session" in result["semantic_context"]["matched_entities"]
    assert "traffic_sessions_by_city_channel_category" in result["semantic_context"]["matched_join_paths"]
    assert result["matched_rules"]
    assert result["matched_table_docs"]


def test_workspace_semantic_layer_loader_reads_yaml_and_json_single_file(tmp_path):
    import json

    from semantic_layer.loader import load_workspace_semantic_layer

    payload = {
        "workspace_id": "workspace-1",
        "metrics": [{"name": "sum_sales_amount", "field": "store.sales_amount"}],
        "dimensions": [{"name": "store_name", "field": "store.store_name"}],
        "time_fields": [{"name": "business_date", "field": "store.business_date"}],
        "entities": [{"name": "store_id", "field": "store.store_id"}],
        "tables": [{"table_name": "store"}],
    }
    yaml_path = tmp_path / "semantic_layer.yaml"
    json_path = tmp_path / "semantic_layer.json"
    yaml_path.write_text(
        """
workspace_id: workspace-1
metrics:
  - name: sum_sales_amount
    field: store.sales_amount
dimensions:
  - name: store_name
    field: store.store_name
time_fields:
  - name: business_date
    field: store.business_date
entities:
  - name: store_id
    field: store.store_id
tables:
  - table_name: store
""",
        encoding="utf-8",
    )
    json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    yaml_result = load_workspace_semantic_layer(yaml_path)
    json_result = load_workspace_semantic_layer(json_path)

    assert yaml_result["success"] is True
    assert json_result["success"] is True
    assert yaml_result["semantic_layer"]["metrics"][0]["name"] == "sum_sales_amount"
    assert json_result["semantic_layer"]["dimensions"][0]["field"] == "store.store_name"
    assert yaml_result["metric_map"]["sum_sales_amount"]["field"] == "store.sales_amount"
    assert json_result["dimension_map"]["store_name"]["field"] == "store.store_name"


def test_workspace_semantic_layer_loader_rejects_missing_file(tmp_path):
    from semantic_layer.loader import load_workspace_semantic_layer

    result = load_workspace_semantic_layer(tmp_path / "missing.yaml")

    assert result["success"] is False
    assert "not found" in result["error"]
