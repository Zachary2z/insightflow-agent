from pathlib import Path

import pytest

from workspaces.report_models import ReportRecord, ReportSection
from workspaces.report_store import ReportNotFoundError, WorkspaceReportStore
from workspaces.store import WorkspaceStore


def _business_answer() -> dict:
    return {
        "headline": "付费搜索和邮件贡献主要收入",
        "direct_answer": "本节显示付费搜索收入最高，邮件渠道也有稳定贡献。",
        "why": "证据表按渠道汇总后，paid_search 收入为 200.0，email 收入为 100.0。",
        "evidence_bullets": [
            "paid_search 收入为 200.0。",
            "email 收入为 100.0。",
        ],
        "recommendations": ["优先复盘付费搜索的投放效率。"],
        "caveats": ["当前只基于预览结果。"],
        "confidence": "high",
    }


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
            "管理层摘要：付费搜索是收入主线，邮件渠道提供稳定补充。",
        ],
        key_findings=[
            "关键发现：付费搜索收入最高，邮件渠道次之，收入贡献存在明显梯队。",
        ],
        action_priorities=[
            "行动优先级：先复盘付费搜索投放效率，再验证邮件渠道是否可扩量。",
        ],
        chart_and_evidence=[
            "图表：渠道收入对比，单位：元。注释：付费搜索贡献主要收入。路径：artifacts/section_revenue_by_channel.png",
        ],
        risks_and_limits=[
            "风险边界：当前报告缺少 ROI、利润和转化率，不能直接推导预算加码。",
        ],
        sections=[
            ReportSection(
                section_id="section_revenue_by_channel",
                title="Revenue by Channel",
                purpose="Compare revenue contribution across channels.",
                status="completed",
                question="Which channels generated the most revenue?",
                business_answer=_business_answer(),
                sql="SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
                columns=["channel", "revenue"],
                rows_preview=[
                    {"channel": "paid_search", "revenue": 200.0},
                    {"channel": "email", "revenue": 100.0},
                ],
                artifact_paths=["artifacts/section_revenue_by_channel.png"],
                business_artifacts=[
                    {
                        "type": "chart",
                        "title": "渠道收入对比",
                        "path": "artifacts/section_revenue_by_channel.png",
                        "unit": "元",
                        "business_annotation": "付费搜索贡献主要收入。",
                    }
                ],
                evidence_notes=[
                    "Preview is based on grouped rows returned by the workspace database.",
                ],
                provider_metadata={"sql_planning": {"model": "deepseek-chat", "calls": 1}},
                trace_nodes=["trace://section_revenue_by_channel/sql"],
            )
        ],
    )


def _english_business_answer() -> dict:
    return {
        "headline": "Paid search leads revenue",
        "direct_answer": "Paid search has the highest revenue in this section.",
        "why": "The evidence table shows paid_search revenue is 200.0.",
        "evidence_bullets": ["paid_search revenue is 200.0."],
        "recommendations": ["Review paid search efficiency before increasing spend."],
        "caveats": ["ROI and profit are not available in this section."],
        "confidence": "high",
    }


def _english_report(workspace_id: str) -> ReportRecord:
    return ReportRecord(
        report_id="report_english1234",
        workspace_id=workspace_id,
        report_type="business_review",
        report_goal="Create an English leadership report for revenue.",
        title="Leadership Business Review",
        status="completed",
        executive_summary=["Executive summary: Paid search is the revenue lead."],
        key_findings=["Key findings: Paid search has the highest revenue."],
        action_priorities=["Action priorities: Review paid search efficiency."],
        chart_and_evidence=[
            "Chart: Revenue by channel; unit: USD; annotation: Paid search leads revenue; link: artifacts/revenue_by_channel.png.",
        ],
        risks_and_limits=["Risks and limits: ROI and profit are not available."],
        sections=[
            ReportSection(
                section_id="revenue_by_channel",
                title="Revenue by Channel",
                purpose="Compare revenue contribution across channels.",
                status="completed",
                question="Which channels generated the most revenue?",
                business_answer=_english_business_answer(),
                columns=["channel", "revenue"],
                rows_preview=[{"channel": "paid_search", "revenue": 200.0}],
                artifact_paths=["artifacts/revenue_by_channel.png"],
                business_artifacts=[
                    {
                        "type": "chart",
                        "title": "Revenue by channel",
                        "path": "artifacts/revenue_by_channel.png",
                        "unit": "USD",
                        "business_annotation": "Paid search leads revenue.",
                    }
                ],
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
    assert loaded.sections[0].business_answer["headline"] == "付费搜索和邮件贡献主要收入"
    assert loaded.sections[0].rows_preview[0]["channel"] == "paid_search"


def test_report_store_renders_markdown_with_required_report_details(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)
    report = _sample_report(workspace["workspace_id"])

    saved = report_store.save_report(report)
    markdown = Path(saved.markdown_path).read_text(encoding="utf-8")

    assert markdown.startswith("# Leadership Business Review")
    assert "## 报告目标" in markdown
    assert "Summarize revenue and channel performance for leadership." in markdown
    assert "## 管理层摘要" in markdown
    assert "- 管理层摘要：付费搜索是收入主线，邮件渠道提供稳定补充。" in markdown
    assert "## 关键发现" in markdown
    assert "- 关键发现：付费搜索收入最高，邮件渠道次之，收入贡献存在明显梯队。" in markdown
    assert "## 行动优先级" in markdown
    assert "- 行动优先级：先复盘付费搜索投放效率，再验证邮件渠道是否可扩量。" in markdown
    assert "## 图表与证据" in markdown
    assert "![渠道收入对比](artifacts/section_revenue_by_channel.png)" in markdown
    assert "单位：元" in markdown
    assert "付费搜索贡献主要收入。" in markdown
    assert "## 风险与边界" in markdown
    assert "- 风险边界：当前报告缺少 ROI、利润和转化率，不能直接推导预算加码。" in markdown
    assert markdown.index("## 管理层摘要") < markdown.index("## 技术附录")
    assert "## 章节业务答案" in markdown
    assert "### Revenue by Channel" in markdown
    assert "#### 结论" in markdown
    assert "付费搜索和邮件贡献主要收入" in markdown
    assert "#### 直接回答" in markdown
    assert "本节显示付费搜索收入最高，邮件渠道也有稳定贡献。" in markdown
    assert "#### 为什么" in markdown
    assert "#### 关键证据" in markdown
    assert "- paid_search 收入为 200.0。" in markdown
    assert "#### 建议动作" in markdown
    assert "- 优先复盘付费搜索的投放效率。" in markdown
    assert "#### 限制说明" in markdown
    assert "- 当前只基于预览结果。" in markdown
    assert "#### 置信度" in markdown
    assert "high" in markdown
    business_body = markdown.split("## 技术附录", 1)[0]
    appendix = markdown.split("## 技术附录", 1)[1]
    assert "Paid search led revenue in the previewed result." not in business_body
    assert "Preview is based on grouped rows" not in business_body
    assert "Compare revenue contribution across channels." not in business_body
    assert "Which channels generated the most revenue?" not in business_body
    assert "SELECT channel" not in business_body
    assert "deepseek-chat" not in business_body
    assert "trace://section_revenue_by_channel/sql" not in business_body
    assert "## 技术附录" in markdown
    assert "<details>" in appendix
    assert "<summary>Revenue by Channel</summary>" in appendix
    assert "```sql\nSELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel\n```" in appendix
    assert "| channel | revenue |" in appendix
    assert "| paid_search | 200.0 |" in appendix
    assert "deepseek-chat" in appendix
    assert "trace://section_revenue_by_channel/sql" in appendix
    assert "deepseek-chat" in markdown


def test_report_store_renders_english_markdown_business_labels_without_chinese_labels(tmp_path):
    workspace_store, workspace = _create_workspace(tmp_path)
    report_store = WorkspaceReportStore(workspace_store)
    report = _english_report(workspace["workspace_id"])

    saved = report_store.save_report(report)
    markdown = Path(saved.markdown_path).read_text(encoding="utf-8")
    business_body = markdown.split("## Technical Appendix", 1)[0]

    assert "## Executive Summary" in markdown
    assert "## Key Findings" in markdown
    assert "## Action Priorities" in markdown
    assert "## Chart And Evidence" in markdown
    assert "## Risks And Limits" in markdown
    assert "#### Conclusion" in markdown
    assert "#### Direct Answer" in markdown
    assert "#### Why" in markdown
    assert "#### Key Evidence" in markdown
    assert "#### Recommended Actions" in markdown
    assert "#### Limits" in markdown
    assert "#### Confidence" in markdown
    assert "#### Charts And Evidence" in markdown
    assert "- Chart title: Revenue by channel" in markdown
    assert "- Unit: USD" in markdown
    assert "- Business annotation: Paid search leads revenue." in markdown
    assert "- Chart link: artifacts/revenue_by_channel.png" in markdown
    for chinese_label in ("结论", "直接回答", "图表标题", "业务注释", "关键证据", "建议动作", "限制说明", "置信度"):
        assert chinese_label not in business_body


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
