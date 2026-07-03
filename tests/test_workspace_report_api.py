from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from workspaces.report_models import (
    ReportDocument,
    ReportDocumentSection,
    ReportEvidenceFact,
    ReportEvidenceChart,
    ReportEvidencePack,
    ReportPlan,
    ReportValidationResult,
)
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
        plan = ReportPlan(
            title="最近90天经营复盘报告",
            report_style="经营复盘",
            time_range="最近90天",
            data_sources=["orders"],
        )
        evidence_pack = ReportEvidencePack(
            facts=[
                ReportEvidenceFact(
                    fact_id="revenue_total",
                    label="总收入",
                    value=200.0,
                    display_value="200.00",
                    source_chapter_id="overview",
                    evidence_ref="table_revenue",
                )
            ],
            charts=[
                ReportEvidenceChart(
                    chart_id="revenue_chart_intent",
                    title="收入结构图表",
                    source_chapter_id="overview",
                    chart_type="bar",
                    description="图表意图：展示收入结构。",
                    evidence_ref="query_revenue_by_dimension",
                )
            ],
            technical_details={
                "queries": [
                    {
                        "query_id": "query_revenue_by_dimension",
                        "sql": "SELECT channel, SUM(revenue) FROM orders GROUP BY channel",
                        "raw_rows": [["paid_search", 200.0]],
                        "provider_metadata": {"model": "deepseek"},
                        "trace": ["sql_reviewer"],
                    }
                ]
            },
        )
        validation = ReportValidationResult(status="passed", checked_facts=["revenue_total"])
        document = ReportDocument(
            title=plan.title,
            time_range=plan.time_range,
            data_sources=plan.data_sources,
            opening_summary="管理层摘要：本报告基于当前工作区证据生成。",
            sections=[
                ReportDocumentSection(
                    section_id="overview",
                    title="经营概览",
                    body="付费搜索贡献了当前样例收入，是后续复盘的证据线索。",
                    evidence_refs=["revenue_total"],
                    chart_refs=["revenue_chart_intent"],
                )
            ],
            action_recommendations=["先补齐成本和转化率后再判断预算。"],
            data_boundaries=["当前为 API 合同测试数据。"],
            technical_appendix={
                "plan": plan.to_dict(),
                "evidence_pack": evidence_pack.to_dict(),
                "validation": validation.to_dict(),
            },
        )
        report = WorkspaceReportStore(store).create_report_record(
            workspace_id=workspace_id,
            report_type=report_type,
            report_goal=report_goal.strip(),
            title=plan.title,
            status="running",
        )
        report.status = "completed"
        report.plan = plan
        report.evidence_pack = evidence_pack
        report.document = document
        report.validation = validation
        report.executive_summary = [document.opening_summary]
        report.key_findings = [document.sections[0].body]
        report.action_priorities = list(document.action_recommendations)
        report.risks_and_limits = list(document.data_boundaries)
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


def test_create_report_returns_persisted_report_document(tmp_path):
    client, _, calls = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)

    payload = _create_report(client, workspace_id)

    assert payload["success"] is True
    assert payload["workspace_id"] == workspace_id
    assert payload["report"]["status"] == "completed"
    assert payload["report"]["title"] == "最近90天经营复盘报告"
    assert payload["report"]["title"] != "Business Review"
    assert payload["report"]["plan"]["title"] == "最近90天经营复盘报告"
    assert payload["report"]["evidence_pack"]["facts"][0]["fact_id"] == "revenue_total"
    assert payload["report"]["document"]["sections"][0]["body"].startswith("付费搜索贡献")
    assert payload["report"]["validation"]["status"] == "passed"
    assert payload["report"]["sections"] == []
    assert calls == [
        {
            "workspace_id": workspace_id,
            "report_type": "business_review",
            "report_goal": "Create a leadership report focused on revenue.",
            "providers": None,
        }
    ]


def test_create_report_passes_report_composer_provider_to_runner(tmp_path, monkeypatch):
    import api.app as api_app

    fake_provider = object()
    monkeypatch.setattr(api_app, "build_report_composer_provider", lambda: fake_provider)
    client, _, calls = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)

    payload = _create_report(client, workspace_id)

    assert payload["success"] is True
    assert calls[0]["providers"] == {"report_composer": fake_provider}


def test_create_report_keeps_no_key_mode_when_report_composer_provider_unavailable(tmp_path, monkeypatch):
    import api.app as api_app

    monkeypatch.setattr(api_app, "build_report_composer_provider", lambda: None)
    client, _, calls = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)

    payload = _create_report(client, workspace_id)

    assert payload["success"] is True
    assert calls[0]["providers"] is None


def test_list_reports_returns_workspace_reports(tmp_path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)
    created = _create_report(client, workspace_id)

    response = client.get(f"/api/workspaces/{workspace_id}/reports")

    assert response.status_code == 200
    reports = response.json()["reports"]
    assert [report["report_id"] for report in reports] == [created["report_id"]]
    assert reports[0]["title"] == "最近90天经营复盘报告"


def test_get_report_detail_returns_report_document(tmp_path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)
    created = _create_report(client, workspace_id)

    response = client.get(
        f"/api/workspaces/{workspace_id}/reports/{created['report_id']}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["report"]["report_id"] == created["report_id"]
    assert payload["report"]["executive_summary"] == ["管理层摘要：本报告基于当前工作区证据生成。"]
    assert payload["report"]["key_findings"] == ["付费搜索贡献了当前样例收入，是后续复盘的证据线索。"]
    assert payload["report"]["action_priorities"] == ["先补齐成本和转化率后再判断预算。"]
    assert payload["report"]["risks_and_limits"] == ["当前为 API 合同测试数据。"]
    assert payload["report"]["document"]["opening_summary"].startswith("管理层摘要")


def test_download_report_markdown_returns_document_markdown_file(tmp_path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)
    created = _create_report(client, workspace_id)

    response = client.get(
        f"/api/workspaces/{workspace_id}/reports/{created['report_id']}/download"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert f'filename="{created["report_id"]}.md"' in response.headers["content-disposition"]
    assert "# 最近90天经营复盘报告" in response.text
    assert "## 开篇摘要" in response.text
    assert "## 报告正文" in response.text
    assert "### 经营概览" in response.text
    assert "待生成图表：收入结构图表" in response.text
    assert "## 行动建议" in response.text
    assert "## 数据边界" in response.text
    assert "## 技术附录" in response.text
    assert "章节业务答案" not in response.text
    assert "#### 直接回答" not in response.text
    assert "```sql" not in response.text
    assert "query_revenue_by_dimension" not in response.text
    assert "SELECT channel" not in response.text
    assert "raw_rows" not in response.text
    assert "provider_metadata" not in response.text
    assert "trace" not in response.text


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
