from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from workspaces.report_models import ReportRecord, ReportSection
from workspaces.report_store import WorkspaceReportStore
from workspaces.store import WorkspaceStore


SUPPORTED_REPORT_TYPES = {"business_review", "channel_performance", "revenue_trend"}


def _client_with_fake_report_runner(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    calls = []

    def fake_report_runner(store, workspace_id, report_type, report_goal, providers=None):
        if report_type not in SUPPORTED_REPORT_TYPES:
            raise ValueError(f"Unsupported report_type: {report_type}")
        if not report_goal or not report_goal.strip():
            raise ValueError("report_goal is required")

        workspace = store.get_workspace(workspace_id)
        calls.append(
            {
                "workspace_id": workspace_id,
                "report_type": report_type,
                "report_goal": report_goal,
                "providers": providers,
            }
        )
        report = ReportRecord(
            report_id=f"report_fake_{len(calls)}",
            workspace_id=workspace_id,
            report_type=report_type,
            report_goal=report_goal.strip(),
            title="Fake Business Review",
            status="completed",
            executive_summary=["Revenue is concentrated in paid search."],
            sections=[
                ReportSection(
                    section_id="revenue_by_channel",
                    title="Revenue by Channel",
                    purpose="Compare channels.",
                    status="completed",
                    question="Which channels led revenue?",
                    summary="Paid search led revenue.",
                    sql="SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
                    columns=["channel", "revenue"],
                    rows_preview=[{"channel": "paid_search", "revenue": 200.0}],
                    evidence_notes=["Result preview comes from workspace data."],
                )
            ],
        )
        saved = WorkspaceReportStore(store).save_report(report)
        assert Path(workspace["root_path"]) in Path(saved.markdown_path).parents
        return {
            "success": True,
            "workspace_id": workspace_id,
            "report_id": saved.report_id,
            "report": saved.to_dict(),
        }

    app = create_app(workspace_store=store, report_runner=fake_report_runner)
    return TestClient(app), store, calls


def _create_workspace(client: TestClient) -> str:
    response = client.post("/api/workspaces", json={"name": "Report API Workspace"})
    assert response.status_code == 200
    return response.json()["workspace_id"]


def _create_report(client: TestClient, workspace_id: str) -> dict:
    response = client.post(
        f"/api/workspaces/{workspace_id}/reports",
        json={
            "report_type": "business_review",
            "report_goal": "Create a leadership report focused on revenue.",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_create_report_returns_persisted_report(tmp_path):
    client, _, calls = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)

    payload = _create_report(client, workspace_id)

    assert payload["success"] is True
    assert payload["workspace_id"] == workspace_id
    assert payload["report_id"] == "report_fake_1"
    assert payload["report"]["report_id"] == "report_fake_1"
    assert payload["report"]["status"] == "completed"
    assert payload["report"]["sections"][0]["sql"].startswith("SELECT channel")
    assert calls == [
        {
            "workspace_id": workspace_id,
            "report_type": "business_review",
            "report_goal": "Create a leadership report focused on revenue.",
            "providers": None,
        }
    ]


def test_list_reports_returns_workspace_reports(tmp_path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)
    created = _create_report(client, workspace_id)

    response = client.get(f"/api/workspaces/{workspace_id}/reports")

    assert response.status_code == 200
    reports = response.json()["reports"]
    assert [report["report_id"] for report in reports] == [created["report_id"]]
    assert reports[0]["title"] == "Fake Business Review"


def test_get_report_detail_returns_report(tmp_path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)
    created = _create_report(client, workspace_id)

    response = client.get(
        f"/api/workspaces/{workspace_id}/reports/{created['report_id']}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["report"]["report_id"] == created["report_id"]
    assert payload["report"]["executive_summary"] == [
        "Revenue is concentrated in paid search."
    ]


def test_download_report_markdown_returns_markdown_file(tmp_path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)
    created = _create_report(client, workspace_id)

    response = client.get(
        f"/api/workspaces/{workspace_id}/reports/{created['report_id']}/download"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert f'filename="{created["report_id"]}.md"' in response.headers["content-disposition"]
    assert "# Fake Business Review" in response.text
    assert "```sql\nSELECT channel" in response.text


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        (
            "post",
            "/api/workspaces/missing/reports",
            {"report_type": "business_review", "report_goal": "Create report."},
        ),
        ("get", "/api/workspaces/missing/reports", None),
        ("get", "/api/workspaces/missing/reports/report_missing", None),
        ("get", "/api/workspaces/missing/reports/report_missing/download", None),
    ],
)
def test_report_api_returns_404_for_missing_workspace(tmp_path, method, path, json):
    client, _, _ = _client_with_fake_report_runner(tmp_path)

    if json is None:
        response = getattr(client, method)(path)
    else:
        response = getattr(client, method)(path, json=json)

    assert response.status_code == 404
    assert "Workspace not found" in response.json()["detail"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/workspaces/{workspace_id}/reports/report_missing",
        "/api/workspaces/{workspace_id}/reports/report_missing/download",
    ],
)
def test_report_api_returns_404_for_missing_report(tmp_path, path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)

    response = client.get(path.format(workspace_id=workspace_id))

    assert response.status_code == 404
    assert "Report not found" in response.json()["detail"]


def test_create_report_rejects_unsupported_report_type(tmp_path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)

    response = client.post(
        f"/api/workspaces/{workspace_id}/reports",
        json={"report_type": "unknown_report", "report_goal": "Create report."},
    )

    assert response.status_code == 400
    assert "Unsupported report_type" in response.json()["detail"]


def test_create_report_rejects_blank_report_goal(tmp_path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)

    response = client.post(
        f"/api/workspaces/{workspace_id}/reports",
        json={"report_type": "business_review", "report_goal": "   "},
    )

    assert response.status_code == 400
    assert "report_goal is required" in response.json()["detail"]
