import sqlite3
import time
from io import BytesIO
from pathlib import Path
import json

import pandas as pd
from fastapi.testclient import TestClient

from api.app import create_app
from workspaces.profiler import profile_workspace_database
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


def _wait_for_run_status(client: TestClient, workspace_id: str, run_id: str, statuses: set[str]) -> dict:
    deadline = time.time() + 5
    last_payload: dict | None = None
    while time.time() < deadline:
        response = client.get(f"/api/workspaces/{workspace_id}/runs/{run_id}")
        assert response.status_code == 200
        last_payload = response.json()
        status = str(last_payload["product_result"]["status"])
        if status in statuses:
            return last_payload
        time.sleep(0.05)
    raise AssertionError(f"Run {run_id} did not reach {statuses}; last payload: {last_payload}")


def _seed_ecommerce_workspace(store: WorkspaceStore, workspace_id: str) -> None:
    workspace = store.get_workspace(workspace_id)
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE orders (id INTEGER, status TEXT)")
        conn.execute("CREATE TABLE order_items (order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price REAL)")
        conn.execute("CREATE TABLE products (id INTEGER, product_name TEXT)")
        conn.executemany("INSERT INTO orders VALUES (?, ?)", [(1, "paid"), (2, "paid")])
        conn.executemany("INSERT INTO products VALUES (?, ?)", [(1, "A"), (2, "B")])
        conn.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?)", [(1, 1, 2, 100.0), (2, 2, 1, 50.0)])
    profile = profile_workspace_database(store, workspace_id)
    generate_semantic_layer_draft(store, workspace_id, profile)


def _write_run(workspace: dict, run_id: str, payload: dict) -> None:
    run_dir = Path(workspace["root_path"]) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "run_id": run_id,
        "workspace_id": workspace["workspace_id"],
        "workspace_root": workspace["root_path"],
        "workspace_run_dir": str(run_dir),
        "trace_path": str(run_dir / f"{run_id}.json"),
        "saved_at": "2026-07-06T10:00:00Z",
        **payload,
    }
    (run_dir / f"{run_id}.json").write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")


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
    assert run["status"] == "running"
    assert run["run_id"].startswith("run_")

    detail = _wait_for_run_status(client, workspace_id, run["run_id"], {"completed"})
    assert detail["result"]["final_answer"]
    assert detail["product_result"]["business_answer"]["headline"]
    assert detail["product_result"]["technical_details"]["sql"] == detail["result"]["generated_sql"]


def test_workspace_api_follow_up_continues_waiting_clarification_in_same_run(tmp_path, monkeypatch):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Clarification API Workspace")
    workspace_id = workspace["workspace_id"]
    _seed_ecommerce_workspace(store, workspace_id)
    _write_run(
        workspace,
        "run_thread1",
        {
            "status": "waiting_for_clarification",
            "original_question": "帮我看看销售情况",
            "analysis_thread_memory": {
                "thread_id": "run_thread1",
                "original_question": "帮我看看销售情况",
                "turns": [
                    {
                        "turn_id": "turn_1",
                        "user_input": "帮我看看销售情况",
                        "resolved_question": "帮我看看销售情况",
                        "status": "waiting_for_clarification",
                        "answer_summary": "需要补充信息后才能继续分析。",
                        "business_lens": {},
                        "evidence_refs": [],
                        "created_at": "2026-07-06T10:00:00Z",
                    }
                ],
                "current_business_lens": {},
                "evidence_refs": [],
                "answer_summary": "需要补充信息后才能继续分析。",
                "pending_clarification": {
                    "clarification_question": "请补充时间范围，例如最近90天。",
                    "missing_fields": ["time_range"],
                },
                "latest_status": "waiting_for_clarification",
                "latest_resolved_question": "帮我看看销售情况",
            },
            "clarification_question": "请补充时间范围，例如最近90天。",
            "execution_result": {},
            "trace": [],
        },
    )

    def completed_workflow(*, run_id, user_question, trace_dir, workspace_root, **kwargs):
        assert run_id == "run_thread1"
        assert "帮我看看销售情况" in user_question
        assert "按商品，最近 90 天，看 Top 5" in user_question
        return {
            "status": "completed",
            "run_id": run_id,
            "workspace_root": workspace_root,
            "trace_path": str(trace_dir / f"{run_id}.json"),
            "analysis_task": {"resolved_question": user_question, "business_lens": {"metrics": [{"label": "销售额"}]}},
            "business_answer": {
                "headline": "商品销售额 Top 5 已完成",
                "direct_answer": "最近 90 天商品销售额 Top 5 已完成。",
                "why": "证据表返回了商品销售额。",
                "evidence_bullets": ["已按商品汇总销售额。"],
                "recommendations": [],
                "caveats": [],
                "confidence": "medium",
            },
            "execution_result": {"success": True, "columns": ["product_name", "revenue"], "rows": [["A", 200.0]]},
            "trace": [],
        }

    monkeypatch.setattr("workspaces.analysis_runner.run_workflow", completed_workflow)
    app = create_app(workspace_store=store)
    client = TestClient(app)

    continuation_response = client.post(
        f"/api/workspaces/{workspace_id}/runs/run_thread1/follow-ups",
        json={"message": "按商品，最近 90 天，看 Top 5"},
    )

    assert continuation_response.status_code == 200
    continuation = continuation_response.json()
    assert continuation["success"] is True
    assert continuation["product_result"]["status"] == "completed"
    assert continuation["run_id"] == "run_thread1"
    thread = continuation["product_result"]["question_thread"]
    assert thread["thread_id"] == "run_thread1"
    assert thread["original_question"] == "帮我看看销售情况"
    assert thread["clarification_answer"] == "按商品，最近 90 天，看 Top 5"
    assert "最近 90 天" in thread["resolved_question"]
    assert len(thread["turns"]) == 2
    assert continuation["result"]["execution_result"]["success"] is True


def test_workspace_api_follow_up_works_for_completed_run(tmp_path, monkeypatch):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Completed Follow-up API Workspace")
    workspace_id = workspace["workspace_id"]
    _seed_ecommerce_workspace(store, workspace_id)
    _write_run(
        workspace,
        "run_done1",
        {
            "status": "completed",
            "original_question": "帮我分析最近90天哪些渠道收益比较好",
            "analysis_thread_memory": {
                "thread_id": "run_done1",
                "original_question": "帮我分析最近90天哪些渠道收益比较好",
                "turns": [
                    {
                        "turn_id": "turn_1",
                        "user_input": "帮我分析最近90天哪些渠道收益比较好",
                        "resolved_question": "分析最近 90 天各渠道收益表现。",
                        "status": "completed",
                        "answer_summary": "email 渠道收入最高。",
                        "business_lens": {"business_domain": "channel_performance", "metrics": [{"label": "收入"}]},
                        "evidence_refs": ["question_evidence_pack"],
                        "created_at": "2026-07-06T10:00:00Z",
                    }
                ],
                "current_business_lens": {"business_domain": "channel_performance", "metrics": [{"label": "收入"}]},
                "evidence_refs": ["question_evidence_pack"],
                "answer_summary": "email 渠道收入最高。",
                "pending_clarification": None,
                "latest_status": "completed",
                "latest_resolved_question": "分析最近 90 天各渠道收益表现。",
            },
            "business_answer": {
                "headline": "email 渠道收入最高",
                "direct_answer": "email 渠道收入最高。",
                "why": "证据表显示 email 收入最高。",
                "evidence_bullets": ["email 收入最高。"],
                "recommendations": [],
                "caveats": [],
                "confidence": "medium",
            },
            "execution_result": {"success": True, "columns": ["channel"], "rows": [["email"]]},
            "trace": [],
        },
    )

    def follow_up_workflow(*, run_id, user_question, trace_dir, workspace_root, **kwargs):
        assert run_id == "run_done1"
        assert "email 渠道收入最高" in user_question
        assert "为什么 email 渠道收益最好" in user_question
        return {
            "status": "completed",
            "run_id": run_id,
            "workspace_root": workspace_root,
            "trace_path": str(trace_dir / f"{run_id}.json"),
            "analysis_task": {"resolved_question": user_question, "business_lens": {"metrics": [{"label": "客单价"}]}},
            "business_answer": {
                "headline": "email 的客单价更高",
                "direct_answer": "email 渠道收益高主要来自客单价。",
                "why": "本轮证据补充了客单价比较。",
                "evidence_bullets": ["email 客单价更高。"],
                "recommendations": [],
                "caveats": [],
                "confidence": "medium",
            },
            "execution_result": {"success": True, "columns": ["channel"], "rows": [["email"]]},
            "trace": [],
        }

    monkeypatch.setattr("workspaces.analysis_runner.run_workflow", follow_up_workflow)
    app = create_app(workspace_store=store)
    client = TestClient(app)

    response = client.post(
        f"/api/workspaces/{workspace_id}/runs/run_done1/follow-ups",
        json={"message": "为什么 email 渠道收益最好？"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run_done1"
    assert payload["product_result"]["business_answer"]["headline"] == "email 的客单价更高"
    assert len(payload["product_result"]["question_thread"]["turns"]) == 2


def test_workspace_api_old_pending_run_id_duplicate_run_behavior_is_removed(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    app = create_app(workspace_store=store)
    client = TestClient(app)
    created = client.post("/api/workspaces", json={"name": "Old Pending API Workspace"}).json()

    response = client.post(
        f"/api/workspaces/{created['workspace_id']}/runs",
        json={"pending_run_id": "pending_missing", "clarification_answer": "最近 90 天"},
    )

    assert response.status_code in {400, 422}
    history = client.get(f"/api/workspaces/{created['workspace_id']}/runs").json()["runs"]
    assert history == []


def test_workspace_api_rejects_run_without_question_or_clarification_answer(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    app = create_app(workspace_store=store)
    client = TestClient(app)
    created = client.post("/api/workspaces", json={"name": "Invalid Run API Workspace"}).json()

    response = client.post(f"/api/workspaces/{created['workspace_id']}/runs", json={"user_question": ""})

    assert response.status_code in {400, 422}


def test_workspace_api_allows_local_nextjs_origin(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    app = create_app(workspace_store=store)
    client = TestClient(app)

    response = client.options(
        "/api/workspaces",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_workspace_source_api_imports_csv_excel_sqlite_and_lists_sources(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    app = create_app(workspace_store=store)
    client = TestClient(app)

    workspace = client.post("/api/workspaces", json={"name": "Source API Workspace"}).json()
    workspace_id = workspace["workspace_id"]

    csv_response = client.post(
        f"/api/workspaces/{workspace_id}/sources/upload",
        files={"file": ("Monthly Sales.csv", b"order_id,revenue\n1,120.5\n2,98.0\n", "text/csv")},
    )
    assert csv_response.status_code == 200
    csv_payload = csv_response.json()
    assert csv_payload["success"] is True
    assert csv_payload["imported_tables"] == ["monthly_sales"]
    assert csv_payload["source"]["source_type"] == "csv"
    with sqlite3.connect(store.get_workspace(workspace_id)["analysis_db_path"]) as conn:
        rows = conn.execute("SELECT order_id, revenue FROM monthly_sales ORDER BY order_id").fetchall()
    assert rows == [(1, 120.5), (2, 98.0)]

    excel_bytes = BytesIO()
    with pd.ExcelWriter(excel_bytes) as writer:
        pd.DataFrame({"customer_id": [1], "segment": ["enterprise"]}).to_excel(
            writer,
            sheet_name="Customers",
            index=False,
        )
        pd.DataFrame({"ticket_id": [10], "customer_id": [1]}).to_excel(
            writer,
            sheet_name="Support Tickets",
            index=False,
        )
    excel_response = client.post(
        f"/api/workspaces/{workspace_id}/sources/upload",
        files={
            "file": (
                "ops.xlsx",
                excel_bytes.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert excel_response.status_code == 200
    excel_payload = excel_response.json()
    assert excel_payload["success"] is True
    assert excel_payload["imported_tables"] == ["customers", "support_tickets"]
    assert excel_payload["source"]["source_type"] == "excel"

    source_db = tmp_path / "source.db"
    with sqlite3.connect(source_db) as conn:
        conn.execute("CREATE TABLE invoices (invoice_id INTEGER, amount REAL)")
        conn.execute("INSERT INTO invoices VALUES (1, 250.0)")
    sqlite_response = client.post(
        f"/api/workspaces/{workspace_id}/sources/sqlite",
        json={"sqlite_path": str(source_db)},
    )
    assert sqlite_response.status_code == 200
    sqlite_payload = sqlite_response.json()
    assert sqlite_payload["success"] is True
    assert sqlite_payload["imported_tables"] == ["invoices"]
    assert sqlite_payload["source"]["source_type"] == "sqlite"
    with sqlite3.connect(store.get_workspace(workspace_id)["analysis_db_path"]) as conn:
        assert conn.execute("SELECT amount FROM invoices").fetchone()[0] == 250.0

    sources_response = client.get(f"/api/workspaces/{workspace_id}/sources")
    assert sources_response.status_code == 200
    sources = sources_response.json()["sources"]
    assert [source["source_type"] for source in sources] == ["csv", "excel", "sqlite"]
    assert [source["imported_tables"] for source in sources] == [
        ["monthly_sales"],
        ["customers", "support_tickets"],
        ["invoices"],
    ]


def test_workspace_source_upload_rejects_unsupported_file_type(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    app = create_app(workspace_store=store)
    client = TestClient(app)
    workspace = client.post("/api/workspaces", json={"name": "Unsupported Upload"}).json()

    response = client.post(
        f"/api/workspaces/{workspace['workspace_id']}/sources/upload",
        files={"file": ("notes.txt", b"not tabular data", "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


def test_workspace_source_api_returns_404_for_missing_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    app = create_app(workspace_store=store)
    client = TestClient(app)

    upload_response = client.post(
        "/api/workspaces/missing/sources/upload",
        files={"file": ("Monthly Sales.csv", b"order_id,revenue\n1,120.5\n", "text/csv")},
    )
    sqlite_response = client.post(
        "/api/workspaces/missing/sources/sqlite",
        json={"sqlite_path": str(tmp_path / "missing.db")},
    )
    list_response = client.get("/api/workspaces/missing/sources")

    assert upload_response.status_code == 404
    assert sqlite_response.status_code == 404
    assert list_response.status_code == 404


def test_workspace_sqlite_source_returns_400_for_unreadable_database(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    app = create_app(workspace_store=store)
    client = TestClient(app)
    workspace = client.post("/api/workspaces", json={"name": "Bad SQLite"}).json()
    bad_db = tmp_path / "not_sqlite.db"
    bad_db.write_text("not a sqlite database", encoding="utf-8")

    missing_response = client.post(
        f"/api/workspaces/{workspace['workspace_id']}/sources/sqlite",
        json={"sqlite_path": str(tmp_path / "missing.db")},
    )
    unreadable_response = client.post(
        f"/api/workspaces/{workspace['workspace_id']}/sources/sqlite",
        json={"sqlite_path": str(bad_db)},
    )

    assert missing_response.status_code == 400
    assert "SQLite" in missing_response.json()["detail"]
    assert unreadable_response.status_code == 400
    assert "SQLite" in unreadable_response.json()["detail"]
