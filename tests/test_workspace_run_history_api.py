import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from workspaces.store import WorkspaceStore


def _client_and_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    app = create_app(workspace_store=store)
    client = TestClient(app)
    workspace = client.post("/api/workspaces", json={"name": "Run History Workspace"}).json()
    return client, store, workspace


def _write_run(workspace: dict, run_id: str, payload: dict) -> Path:
    run_dir = Path(workspace["root_path"]) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{run_id}.json"
    body = {
        "run_id": run_id,
        "status": "completed",
        "saved_at": "2026-06-29T10:00:00Z",
        **payload,
    }
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_list_workspace_runs_includes_all_statuses_and_sorts_latest_first(tmp_path):
    client, _store, workspace = _client_and_workspace(tmp_path)
    workspace_id = workspace["workspace_id"]
    _write_run(
        workspace,
        "run_oldcomplete",
        {
            "status": "completed",
            "saved_at": "2026-06-29T10:00:00Z",
            "question_thread": {"original_question": "按渠道汇总收入", "status": "completed"},
            "product_result": {
                "status": "completed",
                "question_thread": {"original_question": "按渠道汇总收入"},
                "business_answer": {"headline": "邮件渠道收入最高"},
                "chart_artifacts": [{"path": "runs/run_oldcomplete/charts/channel.png"}],
            },
        },
    )
    _write_run(
        workspace,
        "run_newfailed",
        {
            "status": "failed",
            "saved_at": "2026-06-29T12:00:00Z",
            "original_question": "分析不存在字段",
            "review_result": {
                "approved": False,
                "reasons": ["Unknown table: order_items. Available tables: orders, marketing_spend, customers"],
            },
            "trace": [
                {
                    "node": "fail_response_node",
                    "tool_output_summary": "SQL review rejected: Unknown table: order_items",
                    "status": "error",
                }
            ],
        },
    )
    _write_run(
        workspace,
        "run_midclarify",
        {
            "status": "waiting_for_clarification",
            "saved_at": "2026-06-29T11:00:00Z",
            "question_thread": {
                "original_question": "帮我看看销售情况",
                "clarification_question": "你希望分析哪个时间范围？",
                "pending_run_id": "pending_123",
                "status": "waiting_for_clarification",
            },
        },
    )

    response = client.get(f"/api/workspaces/{workspace_id}/runs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == workspace_id
    summaries = payload["runs"]
    assert [run["run_id"] for run in summaries] == ["run_newfailed", "run_midclarify", "run_oldcomplete"]
    assert [run["status"] for run in summaries] == ["failed", "waiting_for_clarification", "completed"]
    failed, waiting, completed = summaries
    assert failed["question"] == "分析不存在字段"
    assert failed["headline"] == "当前数据无法支持这次查询"
    assert failed["failure_reason"] == "系统尝试使用当前工作区中不存在的表或字段，因此没有执行查询。"
    assert waiting["requires_clarification"] is True
    assert waiting["question"] == "帮我看看销售情况"
    assert completed["headline"] == "邮件渠道收入最高"
    assert completed["has_chart"] is True


def test_get_workspace_run_returns_result_and_product_result(tmp_path):
    client, _store, workspace = _client_and_workspace(tmp_path)
    workspace_id = workspace["workspace_id"]
    _write_run(
        workspace,
        "run_detail1",
        {
            "status": "completed",
            "saved_at": "2026-06-29T10:00:00Z",
            "original_question": "按渠道汇总收入",
            "final_answer": "邮件渠道收入最高。",
            "generated_sql": "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
            "execution_result": {"success": True, "columns": ["channel", "revenue"], "rows": [["email", 100.0]]},
            "product_result": {
                "status": "completed",
                "question_thread": {"original_question": "按渠道汇总收入"},
                "business_answer": {"headline": "邮件渠道收入最高", "summary": "邮件渠道收入最高。"},
                "evidence": {"table_preview": {"columns": ["channel", "revenue"], "rows": [["email", 100.0]]}},
            },
        },
    )

    response = client.get(f"/api/workspaces/{workspace_id}/runs/run_detail1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["workspace_id"] == workspace_id
    assert payload["run_id"] == "run_detail1"
    assert payload["result"]["generated_sql"].startswith("SELECT channel")
    assert payload["result"]["execution_result"]["rows"] == [["email", 100.0]]
    assert payload["product_result"]["business_answer"]["headline"] == "邮件渠道收入最高"


def test_get_workspace_run_builds_product_result_for_older_run_json(tmp_path):
    client, _store, workspace = _client_and_workspace(tmp_path)
    workspace_id = workspace["workspace_id"]
    _write_run(
        workspace,
        "run_legacy1",
        {
            "status": "completed",
            "user_question": "哪个渠道收入最高？",
            "final_answer": "邮件渠道收入最高。",
            "execution_result": {"success": True, "columns": ["channel"], "rows": [["email"]]},
        },
    )

    response = client.get(f"/api/workspaces/{workspace_id}/runs/run_legacy1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_result"]["question_thread"]["original_question"] == "哪个渠道收入最高？"
    assert payload["product_result"]["business_answer"]["headline"] == "邮件渠道收入最高。"
    assert payload["result"]["product_result"]["business_answer"]["summary"] == "邮件渠道收入最高。"


def test_workspace_run_history_returns_404_for_missing_workspace_or_run(tmp_path):
    client, _store, workspace = _client_and_workspace(tmp_path)

    missing_workspace = client.get("/api/workspaces/missing/runs")
    missing_run = client.get(f"/api/workspaces/{workspace['workspace_id']}/runs/run_missing")

    assert missing_workspace.status_code == 404
    assert missing_run.status_code == 404


def test_workspace_run_history_rejects_unsafe_run_ids_and_path_escape(tmp_path):
    client, _store, workspace = _client_and_workspace(tmp_path)
    workspace_id = workspace["workspace_id"]
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"run_id": "run_secret", "status": "completed"}), encoding="utf-8")
    _write_run(workspace, "run_safe1", {"status": "completed", "user_question": "安全 run"})

    unsafe = client.get(f"/api/workspaces/{workspace_id}/runs/run_..")
    escaped = client.get(f"/api/workspaces/{workspace_id}/runs/run_%2E%2E%2Foutside")
    safe = client.get(f"/api/workspaces/{workspace_id}/runs/run_safe1")

    assert unsafe.status_code == 404
    assert escaped.status_code == 404
    assert safe.status_code == 200
    assert safe.json()["run_id"] == "run_safe1"


def test_failed_runs_without_business_answer_or_evidence_are_not_filtered(tmp_path):
    client, _store, workspace = _client_and_workspace(tmp_path)
    workspace_id = workspace["workspace_id"]
    _write_run(
        workspace,
        "run_failed1",
        {
            "status": "failed",
            "saved_at": "2026-06-29T13:00:00Z",
            "user_question": "分析不存在的商品明细",
            "error_message": "SQL review rejected",
        },
    )

    response = client.get(f"/api/workspaces/{workspace_id}/runs")

    assert response.status_code == 200
    assert response.json()["runs"] == [
        {
            "run_id": "run_failed1",
            "status": "failed",
            "question": "分析不存在的商品明细",
            "headline": "本次查询未能安全执行",
            "created_at": None,
            "saved_at": "2026-06-29T13:00:00Z",
            "has_chart": False,
            "requires_clarification": False,
            "failure_reason": "系统在执行前发现查询不符合当前数据或安全校验要求，因此已停止本轮分析。",
        }
    ]


def test_old_failed_run_with_raw_product_result_is_sanitized_in_history_and_detail(tmp_path):
    client, _store, workspace = _client_and_workspace(tmp_path)
    workspace_id = workspace["workspace_id"]
    raw_summary = "SQL 审核未通过，已停止执行。原因：Unknown table: products; Unknown column: product_name"
    _write_run(
        workspace,
        "run_rawwall1",
        {
            "status": "failed",
            "saved_at": "2026-06-29T16:00:00Z",
            "original_question": "分析最近 30 天商品表现",
            "final_answer": raw_summary,
            "review_result": {
                "approved": False,
                "issues": ["Unknown table: products", "Unknown column: product_name"],
            },
            "product_result": {
                "version": "p13.v1",
                "status": "failed",
                "question_thread": {
                    "original_question": "分析最近 30 天商品表现",
                    "status": "failed",
                },
                "business_answer": {
                    "headline": "SQL 审核未通过",
                    "summary": raw_summary,
                    "confidence": "low",
                },
                "evidence": {"table_preview": {"columns": [], "rows": []}},
                "chart_artifacts": [],
                "technical_details": {
                    "validation_logs": [
                        {
                            "name": "review_result",
                            "value": {
                                "approved": False,
                                "issues": ["Unknown table: products", "Unknown column: product_name"],
                            },
                        }
                    ]
                },
            },
        },
    )

    history = client.get(f"/api/workspaces/{workspace_id}/runs")
    detail = client.get(f"/api/workspaces/{workspace_id}/runs/run_rawwall1")

    assert history.status_code == 200
    summary = history.json()["runs"][0]
    assert summary["headline"] == "当前数据无法支持这次查询"
    assert summary["failure_reason"] == "系统尝试使用当前工作区中不存在的表或字段，因此没有执行查询。"
    assert "Unknown table" not in summary["headline"]
    assert "Unknown column" not in summary["failure_reason"]

    assert detail.status_code == 200
    product_result = detail.json()["product_result"]
    answer = product_result["business_answer"]
    assert answer["headline"] == "当前数据无法支持这次查询"
    assert "不存在的表或字段" in answer["summary"]
    assert "Unknown table" not in answer["headline"]
    assert "Unknown column" not in answer["summary"]
    assert "Unknown table: products" in str(product_result["technical_details"]["validation_logs"])
    assert detail.json()["result"]["product_result"]["business_answer"] == answer


def test_only_waiting_runs_require_clarification_when_pending_id_is_retained(tmp_path):
    client, _store, workspace = _client_and_workspace(tmp_path)
    workspace_id = workspace["workspace_id"]
    _write_run(
        workspace,
        "run_donepending",
        {
            "status": "completed",
            "saved_at": "2026-06-29T15:00:00Z",
            "question_thread": {
                "original_question": "继续分析后的完成 run",
                "pending_run_id": "pending_123",
                "status": "completed",
            },
        },
    )
    _write_run(
        workspace,
        "run_failpending",
        {
            "status": "failed",
            "saved_at": "2026-06-29T14:00:00Z",
            "question_thread": {
                "original_question": "继续分析后的失败 run",
                "pending_run_id": "pending_123",
                "status": "failed",
            },
            "error_message": "SQL review rejected",
        },
    )
    _write_run(
        workspace,
        "run_waitpending",
        {
            "status": "waiting_for_clarification",
            "saved_at": "2026-06-29T13:00:00Z",
            "question_thread": {
                "original_question": "真正等待澄清的 run",
                "pending_run_id": "pending_123",
                "status": "waiting_for_clarification",
            },
        },
    )

    response = client.get(f"/api/workspaces/{workspace_id}/runs")

    assert response.status_code == 200
    summaries = {run["run_id"]: run for run in response.json()["runs"]}
    assert summaries["run_donepending"]["requires_clarification"] is False
    assert summaries["run_failpending"]["requires_clarification"] is False
    assert summaries["run_waitpending"]["requires_clarification"] is True
