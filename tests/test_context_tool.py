from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_retrieve_business_context_matches_rules_docs_and_sql_examples():
    from tools.context_tool import retrieve_business_context

    result = retrieve_business_context("最近 30 天销售额最高的 5 个商品是什么？")

    assert result["success"] is True
    assert result["question"] == "最近 30 天销售额最高的 5 个商品是什么？"
    assert result["matched_rules"]
    assert result["matched_table_docs"]
    assert result["matched_sql_examples"]
    assert any("paid" in rule["content"] for rule in result["matched_rules"])
    assert any(doc["table_name"] == "orders" for doc in result["matched_table_docs"])
    assert any(doc["table_name"] == "order_items" for doc in result["matched_table_docs"])
    assert any("SUM(oi.quantity * oi.unit_price)" in example["sql"] for example in result["matched_sql_examples"])
    assert "business rules" in result["context_summary"]
    assert result["trace_event"]["tool_name"] == "retrieve_business_context"
    assert result["trace_event"]["status"] == "success"


def test_retrieve_business_context_returns_empty_matches_for_unknown_question():
    from tools.context_tool import retrieve_business_context

    result = retrieve_business_context("帮我分析用户喜欢什么颜色")

    assert result["success"] is True
    assert result["matched_rules"] == []
    assert result["matched_table_docs"] == []
    assert result["matched_sql_examples"] == []
    assert result["context_summary"] == "No business context matched."
    assert result["trace_event"]["tool_output_summary"] == "0 rules, 0 table docs, 0 sql examples"


def test_retrieve_business_context_handles_missing_context_file(tmp_path):
    from tools.context_tool import retrieve_business_context

    result = retrieve_business_context(
        "最近 30 天销售额最高的 5 个商品是什么？",
        context_paths={
            "business_rules": tmp_path / "missing_rules.md",
            "table_docs": ROOT / "data" / "table_docs.md",
            "sql_examples": ROOT / "data" / "sql_examples.json",
        },
    )

    assert result["success"] is False
    assert "missing_rules.md" in result["error"]
    assert result["matched_rules"] == []
    assert result["matched_table_docs"] == []
    assert result["matched_sql_examples"] == []
    assert result["trace_event"]["status"] == "error"
    assert result["trace_event"]["error_type"] == "context_load_error"
