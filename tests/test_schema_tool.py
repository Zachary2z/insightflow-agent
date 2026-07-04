import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def table_by_name(schema: dict, table_name: str) -> dict:
    return next(table for table in schema["tables"] if table["table_name"] == table_name)


def test_get_database_schema_reads_ecommerce_tables_and_columns():
    from tools.schema_tool import get_database_schema

    result = get_database_schema(DB_PATH)

    assert result["success"] is True
    assert result["table_count"] >= 5
    assert {
        "categories",
        "order_items",
        "orders",
        "products",
        "users",
    }.issubset({table["table_name"] for table in result["tables"]})
    assert [table["table_name"] for table in result["tables"]] == sorted(
        table["table_name"] for table in result["tables"]
    )

    orders = table_by_name(result, "orders")
    assert orders["columns"] == [
        {"name": "id", "type": "INTEGER", "primary_key": True, "not_null": False},
        {"name": "user_id", "type": "INTEGER", "primary_key": False, "not_null": True},
        {"name": "order_date", "type": "TEXT", "primary_key": False, "not_null": True},
        {"name": "status", "type": "TEXT", "primary_key": False, "not_null": True},
        {"name": "total_amount", "type": "REAL", "primary_key": False, "not_null": True},
    ]
    assert orders["foreign_keys"] == [
        {
            "column": "user_id",
            "references_table": "users",
            "references_column": "id",
        }
    ]


def test_get_database_schema_formats_prompt_friendly_schema_text():
    from tools.schema_tool import get_database_schema

    result = get_database_schema(DB_PATH)

    assert "Table orders:" in result["schema_text"]
    assert "- id INTEGER PRIMARY KEY" in result["schema_text"]
    assert "- user_id INTEGER NOT NULL" in result["schema_text"]
    assert "Foreign keys: user_id -> users.id" in result["schema_text"]
    assert result["trace_event"]["tool_name"] == "get_database_schema"
    assert result["trace_event"]["status"] == "success"
    assert result["trace_event"]["tool_output_summary"] == (
        f"{result['table_count']} tables loaded"
    )


def test_get_database_schema_handles_empty_database(tmp_path):
    from tools.schema_tool import get_database_schema

    db_path = tmp_path / "empty.db"
    with sqlite3.connect(db_path):
        pass

    result = get_database_schema(db_path)

    assert result["success"] is True
    assert result["tables"] == []
    assert result["table_count"] == 0
    assert result["schema_text"] == "No user tables found."


def test_get_database_schema_returns_error_for_missing_database(tmp_path):
    from tools.schema_tool import get_database_schema

    db_path = tmp_path / "missing.db"

    result = get_database_schema(db_path)

    assert result["success"] is False
    assert result["tables"] == []
    assert "not found" in result["error"]
    assert result["trace_event"]["status"] == "error"
