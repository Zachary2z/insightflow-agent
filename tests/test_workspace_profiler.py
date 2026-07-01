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
    assert columns["order_date"]["value_range"] == {"min": "2026-01-01", "max": "2026-01-03"}
    assert columns["revenue"]["role_candidates"]["measure"] is True
    assert columns["channel"]["role_candidates"]["dimension"] is True
    assert columns["customer_id"]["role_candidates"]["id"] is True
    assert columns["revenue"]["null_count"] == 1


def test_profiler_outputs_general_business_field_profile_for_chinese_store_data(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Chinese Store Profile")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            'CREATE TABLE "门店经营" ('
            '"日期" TEXT, '
            '"门店ID" TEXT, '
            '"门店" TEXT, '
            '"营业额" REAL, '
            '"客诉数量" INTEGER, '
            '"满意度评分" REAL, '
            '"工单状态" TEXT, '
            '"备注" TEXT)'
        )
        conn.executemany(
            'INSERT INTO "门店经营" VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            [
                ("2026-01-01", "S001", "上海一店", 1200.5, 3, 4.6, "已关闭", "早餐高峰"),
                ("2026-01-02", "S002", "深圳二店", 980.0, 5, 4.1, "处理中", "配送延迟"),
                ("2026-01-03", "S001", "上海一店", 1350.0, 2, 4.8, "已关闭", "复购活动"),
            ],
        )

    profile = profile_workspace_database(store, workspace["workspace_id"])

    table = profile["tables"][0]
    columns = {column["name"]: column for column in table["columns"]}
    assert table["table_name"] == "门店经营"
    assert columns["日期"]["inferred_type"] == "time"
    assert columns["日期"]["field_role"] == "time"
    assert "date_like" in columns["日期"]["business_meaning_candidates"]
    assert columns["营业额"]["field_role"] == "metric"
    assert {"amount_like", "revenue_like"}.issubset(columns["营业额"]["business_meaning_candidates"])
    assert {"sum", "avg", "count"}.issubset(columns["营业额"]["suitable_aggregations"])
    assert columns["客诉数量"]["field_role"] == "metric"
    assert "count_like" in columns["客诉数量"]["business_meaning_candidates"]
    assert columns["满意度评分"]["field_role"] == "metric"
    assert "rating_like" in columns["满意度评分"]["business_meaning_candidates"]
    assert "avg" in columns["满意度评分"]["suitable_aggregations"]
    assert columns["工单状态"]["field_role"] == "status"
    assert "status" in columns["工单状态"]["business_meaning_candidates"]
    assert columns["工单状态"]["suitable_group_by"] is True
    assert columns["门店"]["field_role"] == "dimension"
    assert columns["门店"]["suitable_group_by"] is True
    assert columns["门店ID"]["field_role"] == "id"
