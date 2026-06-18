import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def table_count(db_path: Path, table_name: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def test_seed_database_creates_required_tables_and_minimum_rows(tmp_path):
    from data.seed_data import seed_database

    db_path = tmp_path / "ecommerce.db"

    result = seed_database(db_path)

    assert result["success"] is True
    assert db_path.exists()
    assert table_count(db_path, "users") >= 100
    assert table_count(db_path, "orders") >= 500
    assert table_count(db_path, "order_items") >= 1000
    assert table_count(db_path, "products") >= 30
    assert table_count(db_path, "categories") >= 5


def test_seed_database_schema_matches_p0_contract(tmp_path):
    from data.seed_data import seed_database

    db_path = tmp_path / "ecommerce.db"
    seed_database(db_path)

    expected_columns = {
        "users": ["id", "name", "city", "gender", "age", "created_at"],
        "orders": ["id", "user_id", "order_date", "status", "total_amount"],
        "order_items": ["id", "order_id", "product_id", "quantity", "unit_price"],
        "products": ["id", "product_name", "category_id", "price", "created_at"],
        "categories": ["id", "category_name"],
    }

    with sqlite3.connect(db_path) as conn:
        for table_name, columns in expected_columns.items():
            rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            assert [row[1] for row in rows] == columns


def test_seed_database_has_status_and_date_coverage(tmp_path):
    from data.seed_data import seed_database

    db_path = tmp_path / "ecommerce.db"
    seed_database(db_path)

    with sqlite3.connect(db_path) as conn:
        statuses = {
            row[0]
            for row in conn.execute("SELECT DISTINCT status FROM orders").fetchall()
        }
        day_span = conn.execute(
            "SELECT julianday(MAX(order_date)) - julianday(MIN(order_date)) FROM orders"
        ).fetchone()[0]

    assert statuses == {"paid", "cancelled", "refunded"}
    assert day_span >= 180
    assert day_span <= 366


def test_seed_database_supports_basic_gmv_query(tmp_path):
    from data.seed_data import seed_database

    db_path = tmp_path / "ecommerce.db"
    seed_database(db_path)

    query = """
        SELECT
            p.product_name,
            SUM(oi.quantity * oi.unit_price) AS gmv
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        WHERE o.status = 'paid'
        GROUP BY p.product_name
        ORDER BY gmv DESC
        LIMIT 5
    """

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query).fetchall()

    assert len(rows) == 5
    assert rows[0][1] > 0


def test_seed_script_cli_can_create_database(tmp_path):
    db_path = tmp_path / "cli_ecommerce.db"

    result = subprocess.run(
        [sys.executable, str(ROOT / "data" / "seed_data.py"), "--db-path", str(db_path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert db_path.exists()
    assert table_count(db_path, "orders") >= 500
