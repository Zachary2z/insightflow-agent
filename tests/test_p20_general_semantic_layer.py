import yaml

from agents.schema_repair import _semantic_layer_hints


def test_schema_repair_reads_workspace_yaml_semantic_layer_without_json_error(tmp_path):
    semantic_layer_path = tmp_path / "semantic_layer.yaml"
    semantic_layer_path.write_text(
        yaml.safe_dump(
            {
                "workspace_id": "store-workspace",
                "tables": [{"table_name": "store_operations"}],
                "metrics": [{"name": "sum_sales_amount", "field": "store_operations.sales_amount"}],
                "dimensions": [{"name": "store_name", "field": "store_operations.store_name"}],
                "time_fields": [{"name": "business_date", "field": "store_operations.business_date"}],
                "entities": [],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    hints = _semantic_layer_hints(
        {
            "semantic_layer_path": str(semantic_layer_path),
            "metric_context": {"matched_metrics": ["sum_sales_amount"]},
        }
    )

    assert "semantic_layer_error" not in hints
    assert hints["semantic_layer_path"] == str(semantic_layer_path)
    assert hints["semantic_layer"]["tables"][0]["table_name"] == "store_operations"
    assert hints["semantic_layer"]["metrics"][0]["field"] == "store_operations.sales_amount"
    assert hints["semantic_layer"]["time_fields"][0]["field"] == "store_operations.business_date"


def test_chinese_questions_match_english_and_mixed_workspace_headers_without_inventing_demo_fields(tmp_path):
    import sqlite3

    from tools.metric_tool import retrieve_metric_definition
    from workspaces.profiler import profile_workspace_database
    from workspaces.semantic_draft import generate_semantic_layer_draft
    from workspaces.store import WorkspaceStore

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Chinese Alias Workspace")
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
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    sales = retrieve_metric_definition("按门店看销售额", semantic_layer_path=workspace["semantic_layer_path"])
    cost = retrieve_metric_definition("按门店看成本", semantic_layer_path=workspace["semantic_layer_path"])
    score = retrieve_metric_definition("按门店看满意度", semantic_layer_path=workspace["semantic_layer_path"])

    assert sales["matched_metrics"] == ["sum_Sales Amount"]
    assert sales["semantic_context"]["matched_dimensions"] == ["Store Name"]
    assert cost["matched_metrics"] == ["sum_Cost Amount"]
    assert cost["semantic_context"]["matched_dimensions"] == ["Store Name"]
    assert score["matched_metrics"] == ["avg_Score (NPS)"]
    assert score["semantic_context"]["matched_dimensions"] == ["Store Name"]
    serialized = yaml.safe_dump(
        {
            "sales": sales["metrics"],
            "cost": cost["metrics"],
            "score": score["metrics"],
        },
        allow_unicode=True,
    ).lower()
    assert "channel" not in serialized
    assert "orders" not in serialized
    assert "roi" not in serialized
