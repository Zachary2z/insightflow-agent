from __future__ import annotations

import json

import yaml
from fastapi.testclient import TestClient

from api.app import create_app
from workspaces.store import WorkspaceStore


def test_workspace_settings_returns_readiness_and_safety_status(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Settings Workspace")
    workspace_id = workspace["workspace_id"]
    workspace["sources"] = [
        {
            "source_id": "src_1",
            "source_type": "csv",
            "name": "orders.csv",
            "imported_tables": ["orders"],
        }
    ]
    store.save_workspace(workspace)
    profile = {
        "workspace_id": workspace_id,
        "tables": [
            {
                "table_name": "orders",
                "row_count": 10,
                "columns": [
                    {"name": "revenue", "role_candidates": {"measure": True}},
                    {"name": "channel", "role_candidates": {"dimension": True}},
                ],
            }
        ],
    }
    semantic_layer = {
        "workspace_id": workspace_id,
        "metrics": [{"name": "sum_revenue"}],
        "dimensions": [{"name": "channel"}],
        "entities": [],
        "time_fields": [],
    }
    (tmp_path / "workspaces" / workspace_id / "profile.json").write_text(
        json.dumps(profile, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "workspaces" / workspace_id / "semantic_layer.yaml").write_text(
        yaml.safe_dump(semantic_layer, allow_unicode=True),
        encoding="utf-8",
    )
    client = TestClient(create_app(workspace_store=store))

    response = client.get(f"/api/workspaces/{workspace_id}/settings")

    assert response.status_code == 200
    settings = response.json()
    assert settings["workspace_id"] == workspace_id
    assert settings["data_sources"]["sources"][0]["name"] == "orders.csv"
    assert settings["data_sources"]["sources"][0]["imported_tables"] == ["orders"]
    assert settings["profile"]["status"] == "ready"
    assert settings["profile"]["tables"][0]["table_name"] == "orders"
    assert settings["profile"]["tables"][0]["row_count"] == 10
    assert settings["profile"]["tables"][0]["columns"][0]["name"] == "revenue"
    assert settings["semantic_layer"]["status"] == "ready"
    assert settings["semantic_layer"]["metrics"][0]["name"] == "sum_revenue"
    assert settings["semantic_layer"]["dimensions"][0]["name"] == "channel"
    assert "model_mode" in settings
    assert settings["safety"]["sql_review"] == "enabled"
    assert settings["safety"]["sensitive_field_blocking"] == "enabled"
    assert settings["safety"]["trace_available"] == "enabled"
    assert settings["safety"]["technical_details_policy"] == "collapsed_by_default"


def test_workspace_settings_handles_missing_profile_and_semantic_layer(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace_id = store.create_workspace("Missing Settings Workspace")["workspace_id"]
    client = TestClient(create_app(workspace_store=store))

    response = client.get(f"/api/workspaces/{workspace_id}/settings")

    assert response.status_code == 200
    settings = response.json()
    assert settings["profile"]["status"] == "missing"
    assert settings["semantic_layer"]["status"] == "missing"


def test_workspace_settings_returns_404_for_unknown_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    client = TestClient(create_app(workspace_store=store))

    response = client.get("/api/workspaces/missing/settings")

    assert response.status_code == 404
