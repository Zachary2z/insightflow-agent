import sqlite3

from fastapi.testclient import TestClient

from api.app import create_app
from workspaces.store import WorkspaceStore


def test_workspace_api_create_profile_semantic_and_run(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    app = create_app(workspace_store=store)
    client = TestClient(app)

    created = client.post("/api/workspaces", json={"name": "API Workspace"}).json()
    workspace_id = created["workspace_id"]
    workspace = store.get_workspace(workspace_id)
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE orders (channel TEXT, revenue REAL)")
        conn.execute("INSERT INTO orders VALUES ('email', 100.0)")

    profile = client.post(f"/api/workspaces/{workspace_id}/profile").json()
    assert profile["success"] is True
    assert profile["profile"]["tables"][0]["table_name"] == "orders"

    semantic = client.post(f"/api/workspaces/{workspace_id}/semantic-layer/draft").json()
    assert semantic["success"] is True
    assert "metrics" in semantic["semantic_layer"]

    run = client.post(
        f"/api/workspaces/{workspace_id}/runs",
        json={
            "user_question": "按渠道汇总收入",
            "initial_sql": "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel LIMIT 20",
        },
    ).json()
    assert run["success"] is True
    assert run["workspace_id"] == workspace_id
