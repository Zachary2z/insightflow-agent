from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def test_run_sql_executes_select_and_returns_structured_rows():
    from tools.sql_executor import run_sql

    sql = """
        SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        WHERE o.status = 'paid'
        GROUP BY p.product_name
        ORDER BY gmv DESC
        LIMIT 5
    """

    result = run_sql(DB_PATH, sql)

    assert result["success"] is True
    assert result["columns"] == ["product_name", "gmv"]
    assert len(result["rows"]) == 5
    assert result["row_count"] == 5
    assert result["rows"][0][1] > 0
    assert result["execution_time_ms"] >= 0
    assert result["trace_event"]["tool_name"] == "run_sql"
    assert result["trace_event"]["status"] == "success"


def test_run_sql_caps_rows_to_max_rows():
    from tools.sql_executor import run_sql

    result = run_sql(DB_PATH, "SELECT id, order_date FROM orders ORDER BY id", max_rows=3)

    assert result["success"] is True
    assert result["row_count"] == 3
    assert len(result["rows"]) == 3
    assert result["truncated"] is True


def test_run_sql_rejects_non_select_without_executing():
    from tools.sql_executor import run_sql

    result = run_sql(DB_PATH, "DELETE FROM orders WHERE status = 'cancelled'")

    assert result["success"] is False
    assert "Only SELECT queries are allowed" in result["error"]
    assert result["columns"] == []
    assert result["rows"] == []
    assert result["trace_event"]["status"] == "error"


def test_run_sql_returns_database_error_without_raising():
    from tools.sql_executor import run_sql

    result = run_sql(DB_PATH, "SELECT oi.price FROM order_items oi LIMIT 5")

    assert result["success"] is False
    assert "no such column" in result["error"].lower()
    assert result["columns"] == []
    assert result["rows"] == []


def test_run_sql_returns_error_for_missing_database(tmp_path):
    from tools.sql_executor import run_sql

    result = run_sql(tmp_path / "missing.db", "SELECT 1")

    assert result["success"] is False
    assert "Database file not found" in result["error"]


def test_run_sql_rejects_multiple_statements():
    from tools.sql_executor import run_sql

    result = run_sql(DB_PATH, "SELECT 1; SELECT 2;")

    assert result["success"] is False
    assert "Multiple SQL statements are not allowed" in result["error"]
