import yaml

from workspaces.profiler import profile_workspace_database
from workspaces.semantic_draft import generate_semantic_layer_draft, save_semantic_layer
from workspaces.store import WorkspaceStore


def test_semantic_draft_generates_metrics_dimensions_and_time_fields(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Semantic Workspace")
    profile = {
        "workspace_id": workspace["workspace_id"],
        "tables": [
            {
                "table_name": "orders",
                "row_count": 2,
                "columns": [
                    {
                        "name": "order_date",
                        "role_candidates": {"time": True, "measure": False, "dimension": False, "id": False},
                    },
                    {
                        "name": "revenue",
                        "role_candidates": {"time": False, "measure": True, "dimension": False, "id": False},
                    },
                    {
                        "name": "channel",
                        "role_candidates": {"time": False, "measure": False, "dimension": True, "id": False},
                    },
                ],
            }
        ],
    }

    draft = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    assert draft["metrics"][0]["name"] == "sum_revenue"
    assert draft["metrics"][0]["formula"] == "SUM(orders.revenue)"
    assert draft["dimensions"][0]["name"] == "channel"
    assert draft["time_fields"][0]["field"] == "orders.order_date"


def test_save_semantic_layer_persists_user_review(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Reviewed Semantic")
    semantic_layer = {
        "workspace_id": workspace["workspace_id"],
        "metrics": [{"name": "revenue", "formula": "SUM(orders.revenue)", "enabled": True}],
        "dimensions": [],
        "time_fields": [],
        "entities": [],
        "join_paths": [],
    }

    saved = save_semantic_layer(store, workspace["workspace_id"], semantic_layer)

    assert saved["success"] is True
    loaded = yaml.safe_load(open(workspace["semantic_layer_path"], encoding="utf-8"))
    assert loaded["metrics"][0]["name"] == "revenue"


def test_semantic_draft_uses_actual_non_channel_workspace_fields(tmp_path):
    import sqlite3

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Store Operations Semantic")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            'CREATE TABLE store_operations ('
            'business_date TEXT, store_id TEXT, store_name TEXT, '
            'sales_amount REAL, ticket_count INTEGER, satisfaction_score REAL, ticket_status TEXT)'
        )
        conn.executemany(
            "INSERT INTO store_operations VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("2026-01-01", "S001", "Shanghai", 1200.5, 12, 4.6, "closed"),
                ("2026-01-02", "S002", "Shenzhen", 980.0, 18, 4.2, "open"),
            ],
        )

    profile = profile_workspace_database(store, workspace["workspace_id"])
    draft = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    metric_names = {metric["name"] for metric in draft["metrics"]}
    dimension_names = {dimension["name"] for dimension in draft["dimensions"]}
    time_names = {field["name"] for field in draft["time_fields"]}
    assert {"sum_sales_amount", "avg_satisfaction_score", "sum_ticket_count"}.issubset(metric_names)
    assert {"store_name", "ticket_status"}.issubset(dimension_names)
    assert "business_date" in time_names
    assert draft["tables"][0]["table_name"] == "store_operations"
    assert draft["field_roles"]["store_operations.sales_amount"] == "metric"
    assert "sales amount" in draft["semantic_aliases"]["store_operations.sales_amount"]
    assert "store_operations.business_date" in draft["available_analysis_capabilities"]["time_fields"]
    assert "store_operations.store_name" in draft["available_analysis_capabilities"]["groupable_dimensions"]


def test_semantic_draft_does_not_invent_revenue_metric_when_revenue_field_is_absent(tmp_path):
    import sqlite3

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Inventory Semantic")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE inventory_snapshots (snapshot_date TEXT, sku TEXT, warehouse TEXT, stock_qty INTEGER, reorder_level INTEGER)"
        )
        conn.executemany(
            "INSERT INTO inventory_snapshots VALUES (?, ?, ?, ?, ?)",
            [
                ("2026-01-01", "A100", "North", 20, 10),
                ("2026-01-02", "B200", "South", 5, 12),
            ],
        )

    profile = profile_workspace_database(store, workspace["workspace_id"])
    draft = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    serialized_metrics = yaml.safe_dump(draft["metrics"], allow_unicode=True).lower()
    assert "revenue" not in serialized_metrics
    assert {metric["field"] for metric in draft["metrics"]} >= {
        "inventory_snapshots.stock_qty",
        "inventory_snapshots.reorder_level",
    }


def test_semantic_draft_supports_chinese_fields_and_relationship_candidates(tmp_path):
    import sqlite3

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Chinese Relationship Semantic")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute('CREATE TABLE "客户" ("客户ID" TEXT, "客户分群" TEXT)')
        conn.execute('CREATE TABLE "工单" ("工单ID" TEXT, "客户ID" TEXT, "创建日期" TEXT, "处理时长" REAL, "状态" TEXT)')
        conn.executemany('INSERT INTO "客户" VALUES (?, ?)', [("C001", "高价值"), ("C002", "新客")])
        conn.executemany(
            'INSERT INTO "工单" VALUES (?, ?, ?, ?, ?)',
            [
                ("T001", "C001", "2026-01-01", 2.5, "已关闭"),
                ("T002", "C002", "2026-01-02", 5.0, "处理中"),
            ],
        )

    profile = profile_workspace_database(store, workspace["workspace_id"])
    draft = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    assert any(metric["field"] == "工单.处理时长" for metric in draft["metrics"])
    assert any(dimension["field"] == "客户.客户分群" for dimension in draft["dimensions"])
    assert any(field["field"] == "工单.创建日期" for field in draft["time_fields"])
    assert any(
        relationship["left_field"] == "客户.客户ID" and relationship["right_field"] == "工单.客户ID"
        for relationship in draft["relationships"]
    )
