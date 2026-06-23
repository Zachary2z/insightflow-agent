from pathlib import Path

import pytest

from workspaces.report_models import ReportRecord, ReportSection
from workspaces.report_store import ReportNotFoundError, WorkspaceReportStore
from workspaces.store import WorkspaceStore


def _create_workspace(tmp_path):
    workspace_store = WorkspaceStore(root_dir=tmp_path / "workspaces")
    workspace = workspace_store.create_workspace("Report Workspace")
    return workspace_store, workspace


def _sample_report(workspace_id: str) -> ReportRecord:
    return ReportRecord(
        report_id="report_test1234",
        workspace_id=workspace_id,
        report_type="business_review",
        report_goal="Summarize revenue and channel performance for leadership.",
        title="Leadership Business Review",
        status="completed",
        executive_summary=[
            "Revenue is concentrated in paid search and email.",
            "Channel mix should be reviewed next month.",
        ],
        sections=[
            ReportSection(
                section_id="section_revenue_by_channel",
                title="Revenue by Channel",
                purpose="Compare revenue contribution across channels.",
                status="completed",
                question="Which channels generated the most revenue?",
                summary="Paid search led revenue in the previewed result.",
                sql="SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
                columns=["channel", "revenue"],
                rows_preview=[
                    {"channel": "paid_search", "revenue": 200.0},
                    {"channel": "email", "revenue": 100.0},
                ],
                artifact_paths=["artifacts/section_revenue_by_channel.png"],
                evidence_notes=[
                    "Preview is based on grouped rows returned by the workspace database.",
                ],
                provider_metadata={"sql_planning": {"model": "deepseek-chat", "calls": 1}},
                trace_nodes=["trace://section_revenue_by_channel/sql"],
            )
        ],
    )


def test_report_store_creates_report_directory_layout(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)

    created = report_store.create_report_record(
        workspace_id=workspace["workspace_id"],
        report_type="business_review",
        report_goal="Create a leadership business review.",
        title="Leadership Business Review",
    )

    report_dir = Path(workspace["root_path"]) / "reports" / created.report_id
    assert report_dir.is_dir()
    assert (report_dir / "artifacts").is_dir()
    assert created.json_path == str(report_dir / "report.json")
    assert created.markdown_path == str(report_dir / "report.md")
    assert created.trace_path == str(report_dir / "trace.json")
    assert created.artifact_dir == str(report_dir / "artifacts")


def test_report_store_saves_and_loads_canonical_report_json(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)
    report = _sample_report(workspace["workspace_id"])

    saved = report_store.save_report(report)
    loaded = report_store.load_report(workspace["workspace_id"], report.report_id)

    assert Path(saved.json_path).is_file()
    assert loaded.to_dict() == saved.to_dict()
    assert loaded.sections[0].rows_preview[0]["channel"] == "paid_search"


def test_report_store_renders_markdown_with_required_report_details(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)
    report = _sample_report(workspace["workspace_id"])

    saved = report_store.save_report(report)
    markdown = Path(saved.markdown_path).read_text(encoding="utf-8")

    assert markdown.startswith("# Leadership Business Review")
    assert "## Report Metadata" in markdown
    assert f"- Workspace ID: `{workspace['workspace_id']}`" in markdown
    assert "## Report Goal" in markdown
    assert "Summarize revenue and channel performance for leadership." in markdown
    assert "## Executive Summary" in markdown
    assert "- Revenue is concentrated in paid search and email." in markdown
    assert "## Sections" in markdown
    assert "### Revenue by Channel" in markdown
    assert "```sql\nSELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel\n```" in markdown
    assert "| channel | revenue |" in markdown
    assert "| paid_search | 200.0 |" in markdown
    assert "- `artifacts/section_revenue_by_channel.png`" in markdown
    assert "Preview is based on grouped rows" in markdown
    assert "## Trace" in markdown
    assert f"- Trace path: `{saved.trace_path}`" in markdown
    assert "## Provider Metadata Summary" in markdown
    assert "deepseek-chat" in markdown


def test_report_store_lists_reports_newest_first(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)
    first = report_store.save_report(_sample_report(workspace["workspace_id"]))
    second = _sample_report(workspace["workspace_id"])
    second.report_id = "report_second"
    second.title = "Second Report"
    saved_second = report_store.save_report(second)

    reports = report_store.list_reports(workspace["workspace_id"])

    assert [report.report_id for report in reports] == [saved_second.report_id, first.report_id]


def test_report_store_raises_clear_error_for_missing_report(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)

    with pytest.raises(ReportNotFoundError, match="Report not found: missing_report"):
        report_store.load_report(workspace["workspace_id"], "missing_report")


def test_report_store_rejects_artifact_dir_outside_report_directory(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)
    report = _sample_report(workspace["workspace_id"])
    report.artifact_dir = str(tmp_path / "outside-artifacts")

    with pytest.raises(ValueError, match="outside report directory"):
        report_store.save_report(report)
