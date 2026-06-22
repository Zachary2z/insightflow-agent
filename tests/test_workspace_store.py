from pathlib import Path

from workspaces.store import WorkspaceStore


def test_workspace_store_creates_expected_layout(tmp_path):
    store = WorkspaceStore(root_dir=tmp_path / "workspaces")

    workspace = store.create_workspace(name="Finance Uploads")

    assert workspace["workspace_id"]
    assert workspace["name"] == "Finance Uploads"
    workspace_dir = tmp_path / "workspaces" / workspace["workspace_id"]
    assert workspace_dir.exists()
    assert (workspace_dir / "workspace.json").exists()
    assert (workspace_dir / "raw" / "uploaded_files").is_dir()
    assert (workspace_dir / "runs").is_dir()
    assert workspace["analysis_db_path"].endswith("analysis.db")
    assert workspace["profile_path"].endswith("profile.json")
    assert workspace["semantic_layer_path"].endswith("semantic_layer.yaml")


def test_workspace_store_rejects_artifact_path_escape(tmp_path):
    store = WorkspaceStore(root_dir=tmp_path / "workspaces")
    workspace = store.create_workspace(name="Safe Paths")

    safe_path = store.resolve_workspace_path(workspace["workspace_id"], "runs/run_1/result.json")
    assert str(safe_path).startswith(str(tmp_path / "workspaces" / workspace["workspace_id"]))

    try:
        store.resolve_workspace_path(workspace["workspace_id"], "../outside.json")
    except ValueError as exc:
        assert "outside workspace" in str(exc)
    else:
        raise AssertionError("Expected path escape to be rejected")


def test_workspace_store_lists_and_loads_metadata(tmp_path):
    store = WorkspaceStore(root_dir=tmp_path / "workspaces")
    created = store.create_workspace(name="Ops")

    loaded = store.get_workspace(created["workspace_id"])
    listed = store.list_workspaces()

    assert loaded["workspace_id"] == created["workspace_id"]
    assert listed == [loaded]
