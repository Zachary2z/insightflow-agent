import sqlite3

import pandas as pd

from workspaces.importers import import_csv, import_excel, import_sqlite
from workspaces.store import WorkspaceStore


def test_import_csv_creates_table_and_source_metadata(tmp_path):
    csv_path = tmp_path / "Monthly Sales.csv"
    csv_path.write_text(
        "order_id,order_date,revenue,channel\n"
        "1,2026-01-01,120.5,paid_search\n"
        "2,2026-01-02,98.0,email\n",
        encoding="utf-8",
    )
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("CSV Workspace")

    result = import_csv(store, workspace["workspace_id"], csv_path)

    assert result["success"] is True
    assert result["data_version"] == 2
    assert store.get_workspace(workspace["workspace_id"])["data_version"] == 2
    assert result["imported_tables"] == ["monthly_sales"]
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        rows = conn.execute("SELECT order_id, revenue FROM monthly_sales ORDER BY order_id").fetchall()
    assert rows == [(1, 120.5), (2, 98.0)]


def test_import_csv_preserves_chinese_business_headers_for_profiling(tmp_path):
    csv_path = tmp_path / "门店经营.csv"
    csv_path.write_text(
        "日期,门店,营业额,客诉数量,满意度评分,工单状态\n"
        "2026-01-01,上海一店,1200.5,3,4.6,已关闭\n",
        encoding="utf-8",
    )
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Chinese CSV Workspace")

    result = import_csv(store, workspace["workspace_id"], csv_path)

    assert result["success"] is True
    table_name = result["imported_tables"][0]
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        columns = [row[1] for row in conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()]
    assert columns == ["日期", "门店", "营业额", "客诉数量", "满意度评分", "工单状态"]


def test_import_excel_creates_one_table_per_sheet(tmp_path):
    excel_path = tmp_path / "ops.xlsx"
    with pd.ExcelWriter(excel_path) as writer:
        pd.DataFrame({"customer_id": [1], "segment": ["enterprise"]}).to_excel(
            writer,
            sheet_name="Customers",
            index=False,
        )
        pd.DataFrame({"ticket_id": [10], "customer_id": [1]}).to_excel(
            writer,
            sheet_name="Support Tickets",
            index=False,
        )
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Excel Workspace")

    result = import_excel(store, workspace["workspace_id"], excel_path)

    assert result["success"] is True
    assert result["data_version"] == 2
    assert store.get_workspace(workspace["workspace_id"])["data_version"] == 2
    assert result["imported_tables"] == ["customers", "support_tickets"]


def test_import_sqlite_copies_user_tables(tmp_path):
    source_db = tmp_path / "source.db"
    with sqlite3.connect(source_db) as conn:
        conn.execute("CREATE TABLE invoices (invoice_id INTEGER, amount REAL)")
        conn.execute("INSERT INTO invoices VALUES (1, 250.0)")
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("SQLite Workspace")

    result = import_sqlite(store, workspace["workspace_id"], source_db)

    assert result["success"] is True
    assert result["data_version"] == 2
    assert store.get_workspace(workspace["workspace_id"])["data_version"] == 2
    assert result["imported_tables"] == ["invoices"]
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        assert conn.execute("SELECT amount FROM invoices").fetchone()[0] == 250.0
