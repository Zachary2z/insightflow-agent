from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def ecommerce_schema():
    from tools.schema_tool import get_database_schema

    return get_database_schema(DB_PATH)


def sales_metric_context():
    from tools.metric_tool import retrieve_metric_definition

    return retrieve_metric_definition("最近 30 天销售额最高的 5 个商品是什么？")


def test_validate_sql_approves_safe_metric_aware_select():
    from tools.sql_validator import validate_sql

    sql = """
        SELECT
            p.product_name,
            SUM(oi.quantity * oi.unit_price) AS sales
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        WHERE o.status = 'paid'
        GROUP BY p.product_name
        ORDER BY sales DESC
        LIMIT 5
    """

    result = validate_sql(sql, ecommerce_schema(), sales_metric_context())

    assert result["approved"] is True
    assert result["risk_level"] == "low"
    assert result["issues"] == []
    assert result["checks"]["select_only"] is True
    assert result["checks"]["single_statement"] is True
    assert result["checks"]["tables_exist"] is True
    assert result["checks"]["columns_exist"] is True
    assert result["checks"]["has_limit"] is True
    assert result["checks"]["sensitive_fields_blocked"] is True
    assert result["checks"]["metric_formula_correct"] is True
    assert result["checks"]["paid_filter_included"] is True
    assert result["trace_event"]["tool_name"] == "validate_sql"
    assert result["trace_event"]["status"] == "success"


def test_validate_sql_rejects_dangerous_non_select():
    from tools.sql_validator import validate_sql

    result = validate_sql("DELETE FROM orders WHERE status = 'cancelled'", ecommerce_schema())

    assert result["approved"] is False
    assert result["risk_level"] == "high"
    assert result["checks"]["select_only"] is False
    assert result["checks"]["no_dangerous_keywords"] is False
    assert "Only SELECT queries are allowed" in result["issues"]


def test_validate_sql_rejects_multiple_statements():
    from tools.sql_validator import validate_sql

    result = validate_sql("SELECT * FROM users LIMIT 5; SELECT * FROM orders LIMIT 5;", ecommerce_schema())

    assert result["approved"] is False
    assert result["risk_level"] == "high"
    assert result["checks"]["single_statement"] is False
    assert "Multiple SQL statements are not allowed" in result["issues"]


def test_validate_sql_detects_unknown_table_and_column():
    from tools.sql_validator import validate_sql

    table_result = validate_sql("SELECT * FROM payments LIMIT 5", ecommerce_schema())
    column_result = validate_sql("SELECT oi.price FROM order_items oi LIMIT 5", ecommerce_schema())

    assert table_result["approved"] is False
    assert table_result["checks"]["tables_exist"] is False
    assert "Unknown table: payments" in table_result["issues"]
    assert column_result["approved"] is False
    assert column_result["checks"]["columns_exist"] is False
    assert "Unknown column: oi.price" in column_result["issues"]


def test_validate_sql_auto_adds_limit_for_safe_select():
    from tools.sql_validator import validate_sql

    result = validate_sql("SELECT id, order_date FROM orders", ecommerce_schema())

    assert result["approved"] is True
    assert result["checks"]["has_limit"] is True
    assert result["checks"]["limit_added"] is True
    assert "LIMIT missing; appended LIMIT 100" in result["issues"]
    assert result["normalized_sql"].endswith("LIMIT 100")


def test_validate_sql_blocks_sensitive_fields_even_when_query_is_select():
    from tools.sql_validator import validate_sql

    result = validate_sql("SELECT name, email FROM users LIMIT 10", ecommerce_schema())

    assert result["approved"] is False
    assert result["risk_level"] == "high"
    assert result["checks"]["sensitive_fields_blocked"] is False
    assert "Sensitive field access is not allowed: email" in result["issues"]


def test_validate_sql_detects_metric_formula_and_paid_filter_errors():
    from tools.sql_validator import validate_sql

    wrong_formula = """
        SELECT SUM(o.total_amount) AS sales
        FROM orders o
        WHERE o.status = 'paid'
        LIMIT 5
    """
    missing_filter = """
        SELECT SUM(oi.quantity * oi.unit_price) AS sales
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        LIMIT 5
    """

    formula_result = validate_sql(wrong_formula, ecommerce_schema(), sales_metric_context())
    filter_result = validate_sql(missing_filter, ecommerce_schema(), sales_metric_context())

    assert formula_result["approved"] is False
    assert formula_result["checks"]["metric_formula_correct"] is False
    assert "GMV formula must use order_items.quantity * order_items.unit_price" in formula_result["issues"]
    assert filter_result["approved"] is False
    assert filter_result["checks"]["paid_filter_included"] is False
    assert "GMV queries must include orders.status = 'paid'" in filter_result["issues"]


def test_validate_sql_rejects_non_sqlite_interval_syntax():
    from tools.sql_validator import validate_sql

    sql = """
        SELECT channel, SUM(revenue) AS total_revenue
        FROM orders
        WHERE order_date >= (SELECT MAX(order_date) FROM orders) - INTERVAL '90' DAY
        GROUP BY channel
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    schema = {
        "tables": [
            {
                "table_name": "orders",
                "columns": [
                    {"name": "channel"},
                    {"name": "revenue"},
                    {"name": "order_date"},
                ],
            }
        ]
    }

    result = validate_sql(sql, schema)

    assert result["approved"] is False
    assert result["checks"]["sqlite_compatible"] is False
    assert any("SQLite does not support INTERVAL date arithmetic" in issue for issue in result["issues"])
