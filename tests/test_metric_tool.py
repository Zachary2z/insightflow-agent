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
