from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import create_app
from workspaces.store import WorkspaceStore


def test_workspace_artifact_endpoint_reads_chart_inside_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Artifact API")
    chart_path = store.resolve_workspace_path(workspace["workspace_id"], "runs/run_1/charts/channel.png")
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    chart_path.write_bytes(b"\x89PNG\r\n\x1a\nfake-png")

    client = TestClient(create_app(workspace_store=store))
    response = client.get(f"/api/workspaces/{workspace['workspace_id']}/artifacts/runs/run_1/charts/channel.png")

    assert response.status_code == 200
    assert response.content == b"\x89PNG\r\n\x1a\nfake-png"
    assert response.headers["content-type"].startswith("image/png")


def test_workspace_artifact_endpoint_rejects_path_traversal(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Artifact Escape")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")

    client = TestClient(create_app(workspace_store=store))
    response = client.get(f"/api/workspaces/{workspace['workspace_id']}/artifacts/../outside.png")

    assert response.status_code in {400, 404}


def test_workspace_artifact_endpoint_returns_404_for_missing_artifact(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Missing Artifact")

    client = TestClient(create_app(workspace_store=store))
    response = client.get(f"/api/workspaces/{workspace['workspace_id']}/artifacts/runs/run_1/charts/missing.png")

    assert response.status_code == 404
