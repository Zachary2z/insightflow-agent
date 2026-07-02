from pathlib import Path

import pytest

from workspaces.report_models import (
    ReportDocument,
    ReportDocumentSection,
    ReportEvidenceFact,
    ReportEvidencePack,
    ReportPlan,
    ReportRecord,
    ReportValidationResult,
)
from workspaces.report_store import ReportNotFoundError, WorkspaceReportStore
from workspaces.store import WorkspaceStore


def _create_workspace(tmp_path):
    workspace_store = WorkspaceStore(root_dir=tmp_path / "workspaces")
    workspace = workspace_store.create_workspace("Report Workspace")
    return workspace_store, workspace


def _sample_report(workspace_id: str) -> ReportRecord:
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
                value=300.0,
                display_value="300.00",
                source_chapter_id="overview",
                evidence_ref="profile_table",
            )
        ],
        data_limits=["当前缺少 ROI、利润和转化率，不能直接推导预算加码。"],
    )
    validation = ReportValidationResult(status="passed", checked_facts=["revenue_total"])
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="本报告基于当前工作区证据生成经营复盘。",
        sections=[
            ReportDocumentSection(
                section_id="overview",
                title="经营概览",
                body="付费搜索和邮件贡献主要收入，后续应补齐效率和利润证据。",
                evidence_refs=["revenue_total"],
            )
        ],
        action_recommendations=["优先补齐 ROI、利润和转化率后再判断预算。"],
        data_boundaries=["当前缺少 ROI、利润和转化率，不能直接推导预算加码。"],
        technical_appendix={
            "plan": plan.to_dict(),
            "evidence_pack": evidence_pack.to_dict(),
            "validation": validation.to_dict(),
        },
    )
    return ReportRecord(
        report_id="report_test1234",
        workspace_id=workspace_id,
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告。",
        title=plan.title,
        status="completed",
        plan=plan,
        evidence_pack=evidence_pack,
        document=document,
        validation=validation,
        executive_summary=[document.opening_summary],
        key_findings=[document.sections[0].body],
        action_priorities=list(document.action_recommendations),
        risks_and_limits=list(document.data_boundaries),
        sections=[],
    )


def test_report_store_creates_report_directory_layout(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)

    created = report_store.create_report_record(
        workspace_id=workspace["workspace_id"],
        report_type="business_review",
        report_goal="生成经营复盘报告。",
        title="最近90天经营复盘报告",
    )

    report_dir = Path(workspace["root_path"]) / "reports" / created.report_id
    assert report_dir.is_dir()
    assert (report_dir / "artifacts").is_dir()
    assert created.json_path == str(report_dir / "report.json")
    assert created.markdown_path == str(report_dir / "report.md")
    assert created.trace_path == str(report_dir / "trace.json")
    assert created.artifact_dir == str(report_dir / "artifacts")


def test_report_store_saves_and_loads_report_document_json(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)
    report = _sample_report(workspace["workspace_id"])

    saved = report_store.save_report(report)
    loaded = report_store.load_report(workspace["workspace_id"], report.report_id)

    assert Path(saved.json_path).is_file()
    assert loaded.to_dict() == saved.to_dict()
    assert loaded.plan.title == "最近90天经营复盘报告"
    assert loaded.evidence_pack.facts[0].fact_id == "revenue_total"
    assert loaded.document.sections[0].title == "经营概览"
    assert loaded.validation.status == "passed"
    assert loaded.sections == []


def test_report_store_renders_document_markdown_without_stitched_section_body(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)
    report = _sample_report(workspace["workspace_id"])

    saved = report_store.save_report(report)
    markdown = Path(saved.markdown_path).read_text(encoding="utf-8")

    assert markdown.startswith("# 最近90天经营复盘报告")
    assert "## 开篇摘要" in markdown
    assert "本报告基于当前工作区证据生成经营复盘。" in markdown
    assert "## 报告正文" in markdown
    assert "### 经营概览" in markdown
    assert "付费搜索和邮件贡献主要收入" in markdown
    assert "## 行动建议" in markdown
    assert "优先补齐 ROI、利润和转化率后再判断预算。" in markdown
    assert "## 数据边界" in markdown
    assert "当前缺少 ROI、利润和转化率" in markdown
    business_body = markdown.split("## 技术附录", 1)[0]
    appendix = markdown.split("## 技术附录", 1)[1]
    assert "章节业务答案" not in business_body
    assert "#### 结论" not in business_body
    assert "#### 直接回答" not in business_body
    assert "#### 为什么" not in business_body
    assert "#### 建议动作" not in business_body
    assert "置信度" not in business_body
    assert "```sql" not in business_body
    assert "<details>" in appendix
    assert "ReportPlan" not in business_body
    assert "evidence_pack" in appendix
    assert "revenue_total" in appendix


def test_report_store_rejects_report_paths_outside_report_directory(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)
    report = _sample_report(workspace["workspace_id"])
    report.markdown_path = str(tmp_path / "outside.md")

    with pytest.raises(ValueError, match="Report file path is outside report directory"):
        report_store.save_report(report)


def test_report_store_load_missing_report_raises_clear_error(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)

    with pytest.raises(ReportNotFoundError, match="Report not found"):
        report_store.load_report(workspace["workspace_id"], "missing_report")
