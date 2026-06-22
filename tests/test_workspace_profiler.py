import sqlite3

from workspaces.profiler import profile_workspace_database
from workspaces.store import WorkspaceStore


def test_profiler_identifies_column_roles_and_stats(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Profile Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE orders (order_id INTEGER, order_date TEXT, revenue REAL, channel TEXT, customer_id INTEGER)"
        )
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
            [
                (1, "2026-01-01", 100.0, "email", 10),
                (2, "2026-01-02", 150.0, "paid_search", 11),
                (3, "2026-01-03", None, "email", 10),
            ],
        )

    profile = profile_workspace_database(store, workspace["workspace_id"])

    orders = profile["tables"][0]
    columns = {column["name"]: column for column in orders["columns"]}
    assert orders["table_name"] == "orders"
    assert orders["row_count"] == 3
    assert columns["order_date"]["role_candidates"]["time"] is True
    assert columns["revenue"]["role_candidates"]["measure"] is True
    assert columns["channel"]["role_candidates"]["dimension"] is True
    assert columns["customer_id"]["role_candidates"]["id"] is True
    assert columns["revenue"]["null_count"] == 1
