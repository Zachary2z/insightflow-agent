from pathlib import Path
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from workspaces.report_models import (
    ReportArtifactRecord,
    ReportDocument,
    ReportDocumentSection,
    ReportEvidenceFact,
    ReportEvidenceChart,
    ReportEvidencePack,
    ReportEvidenceTable,
    ReportPlan,
    ReportToolCallRecord,
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
            tables=[
                ReportEvidenceTable(
                    table_id="table_revenue",
                    title="渠道收入证据表",
                    columns=["渠道", "收入"],
                    rows=[{"渠道": "付费搜索", "收入": "200.00"}],
                    source_chapter_id="overview",
                    description="发布到飞书时应保留的报告证据表。",
                    evidence_ref="query_revenue_by_dimension",
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
        report.artifacts = [
            ReportArtifactRecord(
                artifact_id="artifact_markdown_report_api",
                artifact_type="markdown_report",
                title="Markdown 报告",
                download_url=f"/api/workspaces/{workspace_id}/reports/{report.report_id}/download",
                source="report_markdown",
                evidence_ids=["ledger_fact_revenue_total"],
                chart_ids=["revenue_chart_intent"],
            )
        ]
        report.chart_artifacts = [
            {
                "artifact_id": "revenue_chart_intent",
                "title": "收入结构图表",
                "renderer": "echarts",
                "chart_type": "bar",
                "echarts_option": {
                    "xAxis": {"type": "category", "data": ["付费搜索"]},
                    "yAxis": {"type": "value"},
                    "series": [{"type": "bar", "name": "收入", "data": [200.0]}],
                },
                "rendering_status": "rendered",
                "source": "report_center",
                "evidence_refs": ["revenue_total"],
            }
        ]
        report.tool_calls = [
            ReportToolCallRecord(
                tool_call_id="tool_call_markdown_report_api",
                tool_name="report_markdown_renderer",
                input_summary="渲染 Markdown 报告：最近90天经营复盘报告",
                referenced_evidence_ids=["ledger_fact_revenue_total"],
                output_artifact_ids=["artifact_markdown_report_api"],
                status="completed",
            )
        ]
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
    assert payload["report"]["evidence_pack"]["tables"][0]["title"] == "渠道收入证据表"
    assert payload["report"]["document"]["sections"][0]["body"].startswith("付费搜索贡献")
    assert payload["report"]["validation"]["status"] == "passed"
    assert payload["report"]["artifacts"][0]["artifact_type"] == "markdown_report"
    assert payload["report"]["artifacts"][0]["source"] == "report_markdown"
    assert payload["report"]["tool_calls"][0]["tool_name"] == "report_markdown_renderer"
    assert "SELECT" not in payload["report"]["tool_calls"][0]["input_summary"].upper()
    for obsolete_field in [
        "sections",
        "executive_summary",
        "key_findings",
        "action_priorities",
        "chart_and_evidence",
        "risks_and_limits",
    ]:
        assert obsolete_field not in payload["report"]
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
    assert payload["report"]["document"]["opening_summary"].startswith("管理层摘要")
    assert payload["report"]["document"]["action_recommendations"] == ["先补齐成本和转化率后再判断预算。"]
    assert payload["report"]["document"]["data_boundaries"] == ["当前为 API 合同测试数据。"]
    assert payload["report"]["artifacts"][0]["evidence_ids"] == ["ledger_fact_revenue_total"]
    assert payload["report"]["tool_calls"][0]["output_artifact_ids"] == ["artifact_markdown_report_api"]
    for obsolete_field in ["executive_summary", "key_findings", "action_priorities", "risks_and_limits"]:
        assert obsolete_field not in payload["report"]


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
    assert "渠道收入证据表" in response.text
    assert "| 渠道 | 收入 |" in response.text
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


def test_export_report_word_docx_returns_safe_download_metadata(tmp_path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)
    created = _create_report(client, workspace_id)

    response = client.post(
        f"/api/workspaces/{workspace_id}/reports/{created['report_id']}/export"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["workspace_id"] == workspace_id
    assert payload["report_id"] == created["report_id"]
    assert payload["document_path"].endswith(".docx")
    assert not Path(payload["document_path"]).is_absolute()
    assert payload["download_name"].endswith(".docx")
    assert payload["download_url"].startswith(
        f"/api/workspaces/{workspace_id}/artifacts/exports/documents/"
    )
    assert payload["download_url"].endswith(".docx")
    assert payload["artifact"]["artifact_type"] == "word_document"
    assert payload["artifact"]["relative_path"] == payload["document_path"]
    document_path = tmp_path / "workspaces" / workspace_id / payload["document_path"]
    assert document_path.exists()

    download = client.get(payload["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    response_text = response.text
    forbidden = [
        "SELECT channel",
        "raw_rows",
        "provider_metadata",
        "api_key",
        "trace.json",
        "analysis.db",
        "database_path",
        "prompt",
        "task_id",
        str(tmp_path),
    ]
    for term in forbidden:
        assert term not in response_text


def test_export_report_word_docx_returns_svg_placeholder_warning(tmp_path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)
    created = _create_report(client, workspace_id)

    response = client.post(
        f"/api/workspaces/{workspace_id}/reports/{created['report_id']}/export"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert any("SVG" in warning or "占位" in warning for warning in payload["warnings"])
    assert (tmp_path / "workspaces" / workspace_id / payload["document_path"]).exists()


def test_export_report_word_docx_returns_404_for_missing_report(tmp_path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)

    response = client.post(
        f"/api/workspaces/{workspace_id}/reports/report_missing/export"
    )

    assert response.status_code == 404
    assert "Report not found" in response.json()["detail"]


def test_publish_report_to_feishu_returns_result_and_persists_safe_artifact(tmp_path, monkeypatch):
    import api.app as api_app
    from workspaces.external_publishing import ExternalPublishResult

    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)
    created = _create_report(client, workspace_id)
    publisher_calls = []

    class FakePublisher:
        def publish_report(self, package):
            publisher_calls.append(package.to_dict())
            return ExternalPublishResult(
                platform="feishu",
                status="published",
                title="最近90天经营复盘报告",
                url="https://example.feishu.cn/docx/doccn123",
                document_id="doccn123",
                external_id="doccn123",
                created_at="2026-07-08T10:00:00+00:00",
                inserted_chart_count=2,
                failed_chart_count=1,
                sheet_url="https://example.feishu.cn/sheets/shtcn123",
                sheet_id="shtcn123",
                spreadsheet_token="shtcn123",
                written_table_count=3,
                native_chart_count=1,
                sheet_warnings=["图表「不清晰图表」无法安全映射为飞书原生图表，已跳过。"],
                warnings=["飞书文档已创建，但 1 张图表未插入。"],
                tool_calls=[
                    {
                        "operation": "create_document",
                        "command_name": "lark-cli",
                        "success": True,
                        "elapsed_ms": 12,
                        "exit_code": 0,
                        "stdout": "token=secret",
                    }
                ],
            )

    monkeypatch.setattr(api_app, "_build_feishu_publisher", lambda **kwargs: FakePublisher())

    response = client.post(
        f"/api/workspaces/{workspace_id}/reports/{created['report_id']}/publish/feishu"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["publish_result"]["status"] == "published"
    assert payload["publish_result"]["url"] == "https://example.feishu.cn/docx/doccn123"
    assert payload["publish_result"]["inserted_chart_count"] == 2
    assert payload["publish_result"]["failed_chart_count"] == 1
    assert payload["publish_result"]["sheet_url"] == "https://example.feishu.cn/sheets/shtcn123"
    assert payload["publish_result"]["spreadsheet_token"] == "shtcn123"
    assert payload["publish_result"]["written_table_count"] == 3
    assert payload["publish_result"]["native_chart_count"] == 1
    assert payload["publish_result"]["sheet_warnings"] == ["图表「不清晰图表」无法安全映射为飞书原生图表，已跳过。"]
    assert payload["publish_result"]["tool_calls"] == [
        {
            "operation": "create_document",
            "command_name": "lark-cli",
            "success": True,
            "elapsed_ms": 12,
            "exit_code": 0,
        }
    ]
    assert publisher_calls[0]["package_version"] == "p34.export_package.v1"
    assert publisher_calls[0]["source_type"] == "report"
    assert publisher_calls[0]["source_id"] == created["report_id"]

    detail = client.get(f"/api/workspaces/{workspace_id}/reports/{created['report_id']}").json()
    saved = detail["report"]["external_publish_results"]["feishu"]
    assert saved["status"] == "published"
    assert saved["document_id"] == "doccn123"
    assert saved["inserted_chart_count"] == 2
    assert saved["failed_chart_count"] == 1
    assert saved["sheet_url"] == "https://example.feishu.cn/sheets/shtcn123"
    assert saved["sheet_id"] == "shtcn123"
    assert saved["spreadsheet_token"] == "shtcn123"
    assert saved["written_table_count"] == 3
    assert saved["native_chart_count"] == 1
    assert saved["sheet_warnings"] == ["图表「不清晰图表」无法安全映射为飞书原生图表，已跳过。"]
    assert saved["warnings"] == ["飞书文档已创建，但 1 张图表未插入。"]
    saved_text = response.text + saved.__repr__()
    for forbidden in [
        "token=secret",
        "stdout",
        "stderr",
        "raw_sql",
        "raw_rows",
        "SELECT channel",
        "trace.json",
        "provider_metadata",
        "prompt",
        str(tmp_path),
    ]:
        assert forbidden not in saved_text


def test_p36_acceptance_report_center_publishes_existing_report_to_feishu_with_png_chart(tmp_path, monkeypatch):
    import api.app as api_app
    from workspaces.feishu_publisher import CliFeishuPublisher, CommandExecutionResult

    class QueueRunner:
        def __init__(self):
            self.calls = []

        def run(self, command, *, input_text=None, timeout_seconds=60):
            self.calls.append({"command": list(command), "input_text": input_text})
            if command[2] == "+create":
                return CommandExecutionResult(
                    exit_code=0,
                    stdout=json.dumps(
                        {
                            "ok": True,
                            "provider_metadata": {"prompt_tokens": 999},
                            "data": {
                                "document": {
                                    "document_id": "doccn_p36_acceptance",
                                    "url": "https://example.feishu.cn/docx/doccn_p36_acceptance",
                                }
                            },
                        }
                    ),
                    stderr="stdout token=secret raw_sql=SELECT * FROM orders trace_path=/Users/me/trace.json",
                    elapsed_ms=10,
                    command_name="lark-cli",
                )
            if command[2] == "+media-insert":
                return CommandExecutionResult(
                    exit_code=0,
                    stdout=json.dumps({"ok": True, "raw_rows": [[1]], "token": "secret"}),
                    stderr="/Users/me/chart.png prompt_tokens=123",
                    elapsed_ms=4,
                    command_name="lark-cli",
                )
            raise AssertionError(f"unexpected command: {command}")

    client, store, calls = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)
    created = _create_report(client, workspace_id)
    report_id = created["report_id"]
    workspace = store.get_workspace(workspace_id)
    workspace_root = Path(workspace["root_path"])
    chart_path = workspace_root / "reports" / report_id / "artifacts" / "channel.png"
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    chart_path.write_bytes(b"png")

    report_store = WorkspaceReportStore(store)
    report = report_store.load_report(workspace_id, report_id)
    original_document = report.document.to_dict()
    report.chart_artifacts = [
        {
            "artifact_id": "revenue_chart_intent",
            "title": "收入结构图表",
            "renderer": "image",
            "chart_type": "bar",
            "image_path": f"reports/{report_id}/artifacts/channel.png",
            "path": f"reports/{report_id}/artifacts/channel.png",
            "rendering_status": "rendered",
            "source": "report_center",
            "evidence_refs": ["revenue_total"],
        }
    ]
    report_store.save_report(report, event_type="test_png_chart_ready")

    runner = QueueRunner()
    monkeypatch.setattr(
        api_app,
        "_build_feishu_publisher",
        lambda **kwargs: CliFeishuPublisher(
            runner=runner,
            cli_binary="lark-cli",
            workspace_root=kwargs["workspace_root"],
            cli_working_dir=tmp_path,
        ),
    )
    monkeypatch.setattr(api_app, "build_report_composer_provider", lambda: (_ for _ in ()).throw(AssertionError("LLM provider must not be called")))

    def fail_sql_connect(*args, **kwargs):
        raise AssertionError("publish path must not execute SQL")

    monkeypatch.setattr(sqlite3, "connect", fail_sql_connect)

    response = client.post(f"/api/workspaces/{workspace_id}/reports/{report_id}/publish/feishu")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    result = payload["publish_result"]
    assert result["status"] == "published"
    assert result["url"] == "https://example.feishu.cn/docx/doccn_p36_acceptance"
    assert result["document_id"] == "doccn_p36_acceptance"
    assert result["inserted_chart_count"] == 1
    assert result["failed_chart_count"] == 0
    assert [call["command"][2] for call in runner.calls] == ["+create", "+media-insert"]
    assert runner.calls[0]["command"][1:7] == ["docs", "+create", "--doc-format", "markdown", "--title", "最近90天经营复盘报告"]
    create_content = runner.calls[0]["command"][-1]
    assert "# 最近90天经营复盘报告" not in create_content
    assert "时间范围：最近90天" in create_content
    assert "数据来源：订单" in create_content
    assert "管理层摘要：本报告基于当前工作区证据生成。" in create_content
    assert "**证据表：渠道收入证据表**" in create_content
    assert "### 证据表" not in create_content
    assert "**图表：收入结构图表**" in create_content
    assert create_content.index("## 经营概览") < create_content.index("**证据表：渠道收入证据表**") < create_content.index("**图表：收入结构图表**")
    assert "| 渠道 | 收入 |" in create_content
    assert "| 付费搜索 | 200.00 |" in create_content
    assert runner.calls[1]["command"] == [
        "lark-cli",
        "docs",
        "+media-insert",
        "--doc",
        "doccn_p36_acceptance",
        "--file",
        chart_path.relative_to(tmp_path).as_posix(),
        "--type",
        "image",
        "--selection-with-ellipsis",
        "图表：收入结构图表",
        "--align",
        "center",
        "--caption",
        "收入结构图表",
        "--width",
        "800",
    ]
    assert len(calls) == 1

    detail = client.get(f"/api/workspaces/{workspace_id}/reports/{report_id}").json()
    saved_report = detail["report"]
    assert saved_report["document"] == original_document
    assert saved_report["external_publish_results"]["feishu"] == result
    assert not result.get("business_answer")
    payload_text = json.dumps(payload, ensure_ascii=False)
    for forbidden in [
        "stdout",
        "stderr",
        "/Users/",
        str(tmp_path),
        "SELECT",
        "raw_sql",
        "raw_rows",
        "trace",
        "provider_metadata",
        "prompt",
        "prompt_tokens",
        "token=secret",
        "secret",
    ]:
        assert forbidden not in payload_text


def test_publish_report_to_feishu_returns_failed_result_without_500(tmp_path, monkeypatch):
    import api.app as api_app
    from workspaces.external_publishing import ExternalPublishResult

    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)
    created = _create_report(client, workspace_id)

    class FakePublisher:
        def publish_report(self, package):
            return ExternalPublishResult(
                platform="feishu",
                status="failed",
                title="最近90天经营复盘报告",
                warnings=["飞书 CLI 未登录，请先运行 lark-cli auth login。"],
            )

    monkeypatch.setattr(api_app, "_build_feishu_publisher", lambda **kwargs: FakePublisher())

    response = client.post(
        f"/api/workspaces/{workspace_id}/reports/{created['report_id']}/publish/feishu"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["publish_result"]["status"] == "failed"
    assert payload["publish_result"]["warnings"] == ["飞书 CLI 未登录，请先运行 lark-cli auth login。"]

    detail = client.get(f"/api/workspaces/{workspace_id}/reports/{created['report_id']}").json()
    assert detail["report"]["external_publish_results"]["feishu"]["status"] == "failed"


def test_publish_report_to_feishu_returns_404_for_missing_report(tmp_path):
    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)

    response = client.post(
        f"/api/workspaces/{workspace_id}/reports/report_missing/publish/feishu"
    )

    assert response.status_code == 404
    assert "Report not found" in response.json()["detail"]


def test_export_report_word_docx_returns_clear_error_when_file_is_missing(tmp_path, monkeypatch):
    import api.app as api_app

    client, _, _ = _client_with_fake_report_runner(tmp_path)
    workspace_id = _create_workspace(client)
    created = _create_report(client, workspace_id)
    monkeypatch.setattr(
        api_app,
        "export_report_docx",
        lambda *args, **kwargs: {
            "success": True,
            "document_path": "exports/documents/missing.docx",
            "download_name": "missing.docx",
            "warnings": [],
            "artifact": {"artifact_type": "word_document"},
        },
    )

    response = client.post(
        f"/api/workspaces/{workspace_id}/reports/{created['report_id']}/export"
    )

    assert response.status_code == 500
    assert "file was not created" in response.json()["detail"]


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
