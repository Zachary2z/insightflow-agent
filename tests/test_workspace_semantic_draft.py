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
    assert draft["metrics"][0]["formula"] == 'SUM("orders"."revenue")'
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


def test_semantic_draft_quotes_mixed_identifiers_and_adds_chinese_business_aliases(tmp_path):
    import sqlite3

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Mixed Header Semantic")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            'CREATE TABLE store_ops ('
            '"Store Name" TEXT, '
            '"Sales Amount" REAL, '
            '"Cost Amount" REAL, '
            '"Score (NPS)" REAL, '
            '"Order Date" TEXT)'
        )
        conn.executemany(
            'INSERT INTO store_ops VALUES (?, ?, ?, ?, ?)',
            [
                ("上海一店", 1200.5, 700.0, 62.0, "2026-01-01"),
                ("深圳二店", 980.0, 620.0, 55.0, "2026-01-02"),
            ],
        )

    profile = profile_workspace_database(store, workspace["workspace_id"])
    draft = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    metrics = {metric["field"]: metric for metric in draft["metrics"]}
    dimensions = {dimension["field"]: dimension for dimension in draft["dimensions"]}
    time_fields = {field["field"]: field for field in draft["time_fields"]}

    assert metrics["store_ops.Sales Amount"]["formula"] == 'SUM("store_ops"."Sales Amount")'
    assert metrics["store_ops.Cost Amount"]["formula"] == 'SUM("store_ops"."Cost Amount")'
    assert metrics["store_ops.Score (NPS)"]["formula"] == 'AVG("store_ops"."Score (NPS)")'
    assert time_fields["store_ops.Order Date"]["field"] == "store_ops.Order Date"

    assert {"销售额", "收入", "营收"}.issubset(metrics["store_ops.Sales Amount"]["aliases"])
    assert {"成本", "费用", "支出"}.issubset(metrics["store_ops.Cost Amount"]["aliases"])
    assert {"满意度", "评分", "得分"}.issubset(metrics["store_ops.Score (NPS)"]["aliases"])
    assert {"门店", "店铺"}.issubset(dimensions["store_ops.Store Name"]["aliases"])
    assert metrics["store_ops.Sales Amount"]["label"] == "销售额"
    assert metrics["store_ops.Cost Amount"]["label"] == "成本"
    assert metrics["store_ops.Score (NPS)"]["label"] == "满意度"
    assert dimensions["store_ops.Store Name"]["label"] == "门店"


def test_semantic_draft_maps_p24_business_datasets_to_chinese_semantics_and_limits(tmp_path):
    import sqlite3

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P24 General Semantic")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            'CREATE TABLE "门店销售" ('
            '"下单时间" TEXT, "门店编号" TEXT, "门店" TEXT, "城市" TEXT, '
            '"GMV" REAL, "实付金额" REAL, "销量" INTEGER)'
        )
        conn.execute(
            'CREATE TABLE "商品销售" ('
            '"日期" TEXT, "商品编号" TEXT, "商品" TEXT, "品类" TEXT, '
            '"成交金额" REAL, "订单数" INTEGER, "件数" INTEGER, "采购成本" REAL)'
        )
        conn.execute(
            'CREATE TABLE "客服工单" ('
            '"创建时间" TEXT, "工单编号" TEXT, "客户编号" TEXT, "团队" TEXT, '
            '"工单数" INTEGER, "平均响应分钟" REAL, "解决状态" TEXT)'
        )
        conn.executemany(
            'INSERT INTO "门店销售" VALUES (?, ?, ?, ?, ?, ?, ?)',
            [("2026-06-01", "S001", "上海旗舰店", "上海", 32000.0, 30100.0, 128)],
        )
        conn.executemany(
            'INSERT INTO "商品销售" VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            [("2026-06-01", "P001", "咖啡豆", "食品", 8600.0, 42, 118, 3900.0)],
        )
        conn.executemany(
            'INSERT INTO "客服工单" VALUES (?, ?, ?, ?, ?, ?, ?)',
            [("2026-06-01", "T001", "C001", "华东客服组", 86, 18.0, "已解决")],
        )

    profile = profile_workspace_database(store, workspace["workspace_id"])
    draft = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    metrics = {metric["field"]: metric for metric in draft["metrics"]}
    dimensions = {dimension["field"]: dimension for dimension in draft["dimensions"]}
    time_fields = {field["field"]: field for field in draft["time_fields"]}
    entities = {entity["field"]: entity for entity in draft["entities"]}

    assert {"销售额", "收入", "成交金额"}.issubset(metrics["商品销售.成交金额"]["aliases"])
    assert metrics["商品销售.成交金额"]["label"] == "销售额"
    assert {"订单数", "订单量"}.issubset(metrics["商品销售.订单数"]["aliases"])
    assert metrics["商品销售.订单数"]["label"] == "订单数"
    assert {"成本", "采购成本"}.issubset(metrics["商品销售.采购成本"]["aliases"])
    assert {"销售额", "GMV"}.issubset(metrics["门店销售.GMV"]["aliases"])
    assert {"销售额", "实付金额"}.issubset(metrics["门店销售.实付金额"]["aliases"])
    assert {"销量", "数量"}.issubset(metrics["门店销售.销量"]["aliases"])
    assert {"工单数", "工单量"}.issubset(metrics["客服工单.工单数"]["aliases"])
    assert metrics["客服工单.平均响应分钟"]["label"] == "响应时长"

    assert {"门店销售.下单时间", "商品销售.日期", "客服工单.创建时间"}.issubset(time_fields)
    assert {"门店销售.门店", "门店销售.城市", "商品销售.商品", "商品销售.品类", "客服工单.团队"}.issubset(
        dimensions
    )
    assert {"门店销售.门店编号", "商品销售.商品编号", "客服工单.工单编号", "客服工单.客户编号"}.issubset(entities)
    assert draft["field_roles"]["商品销售.成交金额"] == "metric"
    assert draft["field_roles"]["客服工单.解决状态"] == "status"
    assert draft["available_analysis_capabilities"]["can_analyze_trends"] is True
    assert draft["available_analysis_capabilities"]["can_calculate_profit"] is True
    assert draft["available_analysis_capabilities"]["can_calculate_roi"] is False
    assert any("投放" in limit and "ROI" in limit for limit in draft["data_limits"])
    assert not any(metric["field"].endswith(".channel") for metric in draft["metrics"])
    assert not any(metric["field"].endswith(".revenue") for metric in draft["metrics"])


def test_semantic_draft_records_missing_time_cost_and_relationship_limits_without_inventing_fields(tmp_path):
    import sqlite3

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P24 Missing Limits")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute('CREATE TABLE "区域销售" ("地区" TEXT, "收入金额" REAL)')
        conn.executemany('INSERT INTO "区域销售" VALUES (?, ?)', [("华东", 98000.0), ("华南", 76000.0)])

    profile = profile_workspace_database(store, workspace["workspace_id"])
    draft = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    metric_fields = {metric["field"] for metric in draft["metrics"]}
    assert metric_fields == {"区域销售.收入金额"}
    assert draft["available_analysis_capabilities"]["can_analyze_trends"] is False
    assert draft["available_analysis_capabilities"]["can_calculate_profit"] is False
    assert draft["available_analysis_capabilities"]["can_calculate_roi"] is False
    assert draft["available_analysis_capabilities"]["can_join_tables"] is False
    limits_text = "\n".join(draft["data_limits"])
    assert "时间字段" in limits_text
    assert "成本字段" in limits_text
    assert "ROI" in limits_text
    assert "关联字段" in limits_text
    serialized = yaml.safe_dump(draft, allow_unicode=True)
    assert "order_date" not in serialized
    assert "channel" not in serialized
    assert "spend" not in serialized
