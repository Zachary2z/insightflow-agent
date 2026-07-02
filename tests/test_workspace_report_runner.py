import json
import sqlite3
from pathlib import Path

import yaml

from workspaces.report_models import (
    EvidenceRequirement,
    ReportChapterPlan,
    ReportDocument,
    ReportDocumentSection,
    ReportEvidenceFact,
    ReportEvidencePack,
    ReportPlan,
    ReportValidationResult,
)
from workspaces.report_runner import run_workspace_report
from workspaces.store import WorkspaceStore


def _create_workspace_with_orders(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Report Runner Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE orders (order_date TEXT, channel TEXT, revenue REAL)"
        )
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?)",
            [
                ("2026-01-01", "email", 100.0),
                ("2026-01-02", "paid_search", 200.0),
                ("2026-01-03", "organic", 150.0),
            ],
        )
    return store, workspace


def test_report_contract_serializes_plan_evidence_document_and_validation():
    plan = ReportPlan(
        title="最近90天经营复盘报告",
        report_style="经营复盘",
        time_range="最近90天",
        data_sources=["orders"],
        chapters=[
            ReportChapterPlan(
                chapter_id="overview",
                title="经营概览",
                purpose="说明整体收入结构。",
                evidence_requirements=[
                    EvidenceRequirement(
                        requirement_id="revenue_total",
                        chapter_id="overview",
                        description="汇总收入。",
                    )
                ],
            )
        ],
    )
    evidence = ReportEvidencePack(
        facts=[
            ReportEvidenceFact(
                fact_id="revenue_total",
                label="总收入",
                value=450.0,
                display_value="450.00",
                source_chapter_id="overview",
                evidence_ref="table_orders",
            )
        ]
    )
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="本报告基于当前工作区数据生成经营复盘。",
        sections=[
            ReportDocumentSection(
                section_id="overview",
                title="经营概览",
                body="当前样例数据收入合计为 450.00，细分指标证据仍需进一步采集。",
                evidence_refs=["revenue_total"],
            )
        ],
        action_recommendations=["补充更多业务维度后再做资源投入判断。"],
        data_boundaries=["当前仅基于样例数据和工作区画像。"],
    )
    validation = ReportValidationResult(status="passed", checked_facts=["revenue_total"])

    assert plan.to_dict()["chapters"][0]["evidence_requirements"][0]["description"] == "汇总收入。"
    assert evidence.to_dict()["facts"][0]["display_value"] == "450.00"
    assert document.to_dict()["sections"][0]["body"].startswith("当前样例数据")
    assert validation.to_dict() == {
        "status": "passed",
        "checked_facts": ["revenue_total"],
        "warnings": [],
        "unsupported_claims": [],
    }


def test_report_runner_uses_report_document_contract_and_chinese_default_title(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成一份最近90天经营复盘报告，关注收入结构和行动建议。",
        section_runner=lambda **_: (_ for _ in ()).throw(AssertionError("旧 section runner 不应被调用")),
    )

    report = result["report"]
    assert result["success"] is True
    assert report["status"] == "completed"
    assert report["title"] == "最近90天经营复盘报告"
    assert report["title"] != "Business Review"
    assert report["plan"]["title"] == report["title"]
    assert report["evidence_pack"]["facts"]
    assert report["document"]["title"] == report["title"]
    assert report["document"]["opening_summary"]
    assert report["document"]["sections"][0]["body"]
    assert report["validation"]["status"] == "passed"
    assert report["sections"] == []


def test_report_markdown_renders_document_body_without_stitched_section_labels(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "生成中文收入趋势报告。",
    )

    markdown = Path(result["report"]["markdown_path"]).read_text(encoding="utf-8")
    business_body = markdown.split("## 技术附录", 1)[0]

    assert "# 最近90天经营复盘报告" in markdown
    assert "## 报告正文" in markdown
    assert "## 数据边界" in markdown
    assert "章节业务答案" not in business_body
    assert "#### 结论" not in business_body
    assert "#### 直接回答" not in business_body
    assert "#### 为什么" not in business_body
    assert "#### 建议动作" not in business_body
    assert "置信度" not in business_body
    assert "Business Review" not in business_body
    assert "Overall Performance" not in business_body
    assert "Evidence Backed Recommendations" not in business_body


def test_report_main_body_does_not_expose_engineering_phase_terms(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成经营复盘报告。",
    )

    report = result["report"]
    markdown = Path(report["markdown_path"]).read_text(encoding="utf-8")
    main_markdown = markdown.split("## 技术附录", 1)[0]
    document_text = json.dumps(
        {
            "opening_summary": report["document"]["opening_summary"],
            "sections": report["document"]["sections"],
            "action_recommendations": report["document"]["action_recommendations"],
            "data_boundaries": report["document"]["data_boundaries"],
        },
        ensure_ascii=False,
    )
    forbidden_terms = [
        "H1",
        "H2",
        "H3",
        "pipeline",
        "ReportDocument",
        "ReportPlan",
        "ReportEvidencePack",
        "工程",
        "开发阶段",
    ]

    for term in forbidden_terms:
        assert term not in main_markdown
        assert term not in document_text


def test_report_main_path_does_not_call_run_workspace_analysis_for_sections(tmp_path):
    import workspaces.report_runner as report_runner

    store, workspace = _create_workspace_with_orders(tmp_path)

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "channel_performance",
        "生成渠道表现报告。",
    )

    assert not hasattr(report_runner, "run_workspace_analysis")
    assert result["success"] is True
    assert result["report"]["document"]["sections"]


def test_existing_semantic_layer_is_not_overwritten(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    existing_semantic = {
        "workspace_id": workspace["workspace_id"],
        "metrics": [{"name": "reviewed_revenue", "formula": "SUM(orders.revenue)"}],
        "dimensions": [],
        "time_fields": [],
        "entities": [],
        "join_paths": [],
    }
    Path(workspace["semantic_layer_path"]).write_text(
        yaml.safe_dump(existing_semantic, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成经营复盘报告。",
    )

    loaded = yaml.safe_load(
        Path(workspace["semantic_layer_path"]).read_text(encoding="utf-8")
    )
    assert loaded["metrics"][0]["name"] == "reviewed_revenue"


def test_report_json_keeps_technical_details_outside_document_body(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成经营复盘报告。",
    )

    saved = json.loads(Path(result["report"]["json_path"]).read_text(encoding="utf-8"))
    document_text = json.dumps(saved["document"], ensure_ascii=False)
    appendix_text = json.dumps(saved["document"]["technical_appendix"], ensure_ascii=False)

    assert "SELECT" not in document_text
    assert "raw_rows" not in document_text
    assert "provider_metadata" not in document_text
    assert "trace" not in document_text
    assert "plan" in appendix_text
    assert "evidence_pack" in appendix_text
