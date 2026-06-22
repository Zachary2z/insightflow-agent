import yaml

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
