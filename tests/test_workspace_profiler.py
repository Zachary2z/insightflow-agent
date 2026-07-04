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


def test_profiler_recognizes_p24_store_product_and_support_business_roles(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P24 Profile Coverage")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            'CREATE TABLE "门店销售" ('
            '"下单时间" TEXT, '
            '"门店编号" TEXT, '
            '"门店" TEXT, '
            '"城市" TEXT, '
            '"GMV" REAL, '
            '"实付金额" REAL, '
            '"销量" INTEGER)'
        )
        conn.execute(
            'CREATE TABLE "商品销售" ('
            '"日期" TEXT, '
            '"商品编号" TEXT, '
            '"商品" TEXT, '
            '"品类" TEXT, '
            '"成交金额" REAL, '
            '"订单数" INTEGER, '
            '"件数" INTEGER, '
            '"采购成本" REAL)'
        )
        conn.execute(
            'CREATE TABLE "客服工单" ('
            '"创建时间" TEXT, '
            '"工单编号" TEXT, '
            '"客户编号" TEXT, '
            '"团队" TEXT, '
            '"工单数" INTEGER, '
            '"平均响应分钟" REAL, '
            '"解决状态" TEXT)'
        )
        conn.executemany(
            'INSERT INTO "门店销售" VALUES (?, ?, ?, ?, ?, ?, ?)',
            [
                ("2026-06-01", "S001", "上海旗舰店", "上海", 32000.0, 30100.0, 128),
                ("2026-06-02", "S002", "深圳湾店", "深圳", 18000.0, 17100.0, 76),
            ],
        )
        conn.executemany(
            'INSERT INTO "商品销售" VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            [
                ("2026-06-01", "P001", "咖啡豆", "食品", 8600.0, 42, 118, 3900.0),
                ("2026-06-02", "P002", "保温杯", "日用品", 7200.0, 31, 64, 2800.0),
            ],
        )
        conn.executemany(
            'INSERT INTO "客服工单" VALUES (?, ?, ?, ?, ?, ?, ?)',
            [
                ("2026-06-01", "T001", "C001", "华东客服组", 86, 18.0, "已解决"),
                ("2026-06-02", "T002", "C002", "华南客服组", 71, 24.0, "处理中"),
            ],
        )

    profile = profile_workspace_database(store, workspace["workspace_id"])
    tables = {
        table["table_name"]: {column["name"]: column for column in table["columns"]}
        for table in profile["tables"]
    }

    store_sales = tables["门店销售"]
    assert store_sales["下单时间"]["field_role"] == "time"
    assert store_sales["门店编号"]["field_role"] == "id"
    assert store_sales["门店"]["field_role"] == "dimension"
    assert store_sales["城市"]["field_role"] == "dimension"
    assert "revenue_like" in store_sales["GMV"]["business_meaning_candidates"]
    assert "revenue_like" in store_sales["实付金额"]["business_meaning_candidates"]
    assert "count_like" in store_sales["销量"]["business_meaning_candidates"]

    product_sales = tables["商品销售"]
    assert product_sales["商品编号"]["field_role"] == "id"
    assert product_sales["商品"]["field_role"] == "dimension"
    assert product_sales["品类"]["field_role"] == "dimension"
    assert "revenue_like" in product_sales["成交金额"]["business_meaning_candidates"]
    assert "order_count_like" in product_sales["订单数"]["business_meaning_candidates"]
    assert "count_like" in product_sales["件数"]["business_meaning_candidates"]
    assert "cost_like" in product_sales["采购成本"]["business_meaning_candidates"]

    support = tables["客服工单"]
    assert support["创建时间"]["field_role"] == "time"
    assert support["工单编号"]["field_role"] == "id"
    assert support["客户编号"]["field_role"] == "id"
    assert support["团队"]["field_role"] == "dimension"
    assert "ticket_count_like" in support["工单数"]["business_meaning_candidates"]
    assert "duration_like" in support["平均响应分钟"]["business_meaning_candidates"]
    assert support["解决状态"]["field_role"] == "status"
