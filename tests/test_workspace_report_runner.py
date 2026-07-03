import json
import sqlite3
import inspect
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


def _create_workspace_with_chartable_recent_orders(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Report Runner Chart Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            """
            CREATE TABLE orders (
                order_date TEXT,
                product_category TEXT,
                customer_segment TEXT,
                revenue REAL,
                order_count INTEGER
            )
            """
        )
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
            [
                ("2026-04-01", "企业SaaS订阅", "成长型团队", 120000.0, 12),
                ("2026-05-01", "数据分析服务", "高价值企业", 86000.0, 8),
                ("2026-06-01", "企业SaaS订阅", "高价值企业", 148000.0, 11),
                ("2026-06-15", "运营代投服务", "成长型团队", 76000.0, 6),
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


def test_report_contract_serializes_artifacts_and_tool_call_records():
    from workspaces.report_models import ReportArtifactRecord, ReportToolCallRecord

    artifact = ReportArtifactRecord(
        artifact_id="artifact_chart_revenue_structure_chart",
        artifact_type="chart",
        title="收入结构图表",
        relative_path="reports/report_1/artifacts/revenue_structure_chart.svg",
        source="local_renderer",
        evidence_ids=["ledger_fact_revenue_total"],
        ledger_metric_ids=["ledger_metric_revenue_by_dimension_收入_total"],
        chart_ids=["revenue_structure_chart"],
        status="completed",
    )
    tool_call = ReportToolCallRecord(
        tool_call_id="tool_call_chart_revenue_structure_chart",
        tool_name="local_chart_renderer",
        input_summary="渲染图表：收入结构图表",
        referenced_evidence_ids=["ledger_fact_revenue_total"],
        output_artifact_ids=["artifact_chart_revenue_structure_chart"],
        status="completed",
    )

    assert artifact.to_dict()["artifact_type"] == "chart"
    assert artifact.to_dict()["source"] == "local_renderer"
    assert artifact.to_dict()["evidence_ids"] == ["ledger_fact_revenue_total"]
    assert artifact.to_dict()["ledger_metric_ids"] == ["ledger_metric_revenue_by_dimension_收入_total"]
    assert tool_call.to_dict()["tool_name"] == "local_chart_renderer"
    assert "SELECT" not in tool_call.to_dict()["input_summary"].upper()


def test_report_runner_uses_report_document_contract_and_chinese_default_title(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成一份最近90天经营复盘报告，关注收入结构和行动建议。",
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
    assert any(artifact["artifact_type"] == "markdown_report" for artifact in report["artifacts"])
    assert any(artifact["artifact_type"] == "report_document" for artifact in report["artifacts"])
    assert any(call["tool_name"] == "report_markdown_renderer" for call in report["tool_calls"])
    assert "sections" not in report
    assert "executive_summary" not in report
    assert "key_findings" not in report
    assert "action_priorities" not in report
    assert "chart_and_evidence" not in report
    assert "risks_and_limits" not in report


def test_report_runner_signature_removes_removed_section_compatibility():
    import workspaces.report_runner as report_runner

    signature = inspect.signature(run_workspace_report)
    removed_parameter = "section" + "_" + "runner"
    removed_type = "Section" + "Runner"

    assert removed_parameter not in signature.parameters
    assert not hasattr(report_runner, removed_type)


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

    assert "# 最近90天趋势变化报告" in markdown
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
    assert "workspace_table_count" not in business_body
    assert "workspace_profile" not in business_body
    assert "证据来自当前工作区数据画像" in business_body


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
    assert "run_workspace_analysis(" not in Path(report_runner.__file__).read_text(encoding="utf-8")
    assert result["success"] is True
    assert result["report"]["document"]["sections"]


def test_report_runner_calls_report_composer_and_validator_modules(tmp_path, monkeypatch):
    import workspaces.report_runner as report_runner

    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = {"composer": 0, "validator": 0}

    def fake_compose_report_document(*, plan, evidence_pack, evidence_ledger=None, provider=None):
        calls["composer"] += 1
        assert plan.title == "最近90天经营复盘报告"
        assert evidence_pack.facts
        assert evidence_ledger is not None
        assert evidence_ledger.ledger_version == "p23.report_ledger.v1"
        assert provider == "fake-report-provider"
        return ReportDocument(
            title=plan.title,
            time_range=plan.time_range,
            data_sources=plan.data_sources,
            opening_summary="这是由新报告撰写器生成的完整中文摘要。",
            sections=[
                ReportDocumentSection(
                    section_id="overview",
                    title="经营概览",
                    body="新报告撰写器基于证据生成正文。",
                    evidence_refs=["workspace_table_count"],
                )
            ],
            action_recommendations=["继续沿用证据驱动报告链路。"],
            data_boundaries=["当前为 runner 调用链测试。"],
        )

    def fake_validate_report_document(*, document, plan, evidence_pack, evidence_ledger=None):
        calls["validator"] += 1
        assert document.opening_summary.startswith("这是由新报告撰写器")
        assert plan.title == document.title
        assert evidence_pack.facts
        assert evidence_ledger is not None
        return ReportValidationResult(
            status="passed",
            checked_facts=["workspace_table_count"],
        )

    monkeypatch.setattr(report_runner, "compose_report_document", fake_compose_report_document)
    monkeypatch.setattr(report_runner, "validate_report_document", fake_validate_report_document)

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成一份最近90天经营复盘报告。",
        providers={"report_composer": "fake-report-provider"},
    )

    assert result["success"] is True
    assert calls == {"composer": 1, "validator": 1}
    assert result["report"]["document"]["opening_summary"].startswith("这是由新报告撰写器")


def test_report_runner_records_local_artifact_and_tool_call_readiness(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成一份最近90天经营复盘报告，关注收入结构和行动建议。",
    )

    report = result["report"]
    artifacts = report["artifacts"]
    tool_calls = report["tool_calls"]
    chart_artifacts = [artifact for artifact in artifacts if artifact["artifact_type"] == "chart"]
    markdown_artifact = next(artifact for artifact in artifacts if artifact["artifact_type"] == "markdown_report")
    document_artifact = next(artifact for artifact in artifacts if artifact["artifact_type"] == "report_document")
    serialized_public_records = json.dumps({"artifacts": artifacts, "tool_calls": tool_calls}, ensure_ascii=False)

    assert all(artifact["source"] == "local_renderer" for artifact in chart_artifacts)
    assert all(artifact["evidence_ids"] or artifact["ledger_metric_ids"] for artifact in chart_artifacts)
    assert markdown_artifact["source"] == "report_markdown"
    assert markdown_artifact["download_url"].endswith(f"/api/workspaces/{workspace['workspace_id']}/reports/{report['report_id']}/download")
    assert markdown_artifact["evidence_ids"]
    assert document_artifact["artifact_type"] == "report_document"
    assert document_artifact["source"] == "report_markdown"
    if chart_artifacts:
        assert any(call["tool_name"] == "local_chart_renderer" for call in tool_calls)
    assert any(call["tool_name"] == "report_markdown_renderer" for call in tool_calls)
    assert all(call["referenced_evidence_ids"] for call in tool_calls)
    assert all(call["output_artifact_ids"] for call in tool_calls)
    assert "future_external_tool" not in serialized_public_records
    assert "SELECT" not in serialized_public_records.upper()
    assert "raw_rows" not in serialized_public_records
    assert "query_id" not in serialized_public_records
    assert "trace" not in serialized_public_records
    assert "provider_metadata" not in serialized_public_records
    assert report["document"]["technical_appendix"]["artifact_summary"]["artifact_count"] == len(artifacts)
    assert report["document"]["technical_appendix"]["ledger_reference_summary"]["evidence_ids"]


def test_report_runner_persists_chart_artifacts_from_evidence_pack(tmp_path):
    store, workspace = _create_workspace_with_chartable_recent_orders(tmp_path)

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成一份最近90天经营复盘报告，关注收入结构、客户分群和趋势变化。",
    )

    report = result["report"]
    evidence_charts = [
        chart
        for chart in report["evidence_pack"]["charts"]
        if chart.get("path") or chart.get("url")
    ]
    chart_artifacts = [
        artifact
        for artifact in report["artifacts"]
        if artifact["artifact_type"] == "chart"
    ]
    chart_tool_calls = [
        tool_call
        for tool_call in report["tool_calls"]
        if tool_call["tool_name"] == "local_chart_renderer"
    ]
    evidence_chart_ids = {chart["chart_id"] for chart in evidence_charts}
    artifact_ids = {artifact["artifact_id"] for artifact in chart_artifacts}

    assert len(report["evidence_pack"]["charts"]) > 0
    assert evidence_charts
    assert chart_artifacts
    assert all(artifact["evidence_ids"] or artifact["ledger_metric_ids"] for artifact in chart_artifacts)
    assert all(set(artifact["chart_ids"]).issubset(evidence_chart_ids) for artifact in chart_artifacts)
    assert chart_tool_calls
    assert all(set(tool_call["output_artifact_ids"]).issubset(artifact_ids) for tool_call in chart_tool_calls)
    assert report["document"]["technical_appendix"]["artifact_summary"]["chart_count"] == len(chart_artifacts)


def test_report_runner_composes_once_without_section_business_answers(tmp_path, monkeypatch):
    import workspaces.report_runner as report_runner

    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = {"composer": 0}

    def fake_compose_report_document(*, plan, evidence_pack, evidence_ledger=None, provider=None):
        calls["composer"] += 1
        evidence_text = json.dumps(evidence_pack.to_dict(), ensure_ascii=False)
        assert "business_answer" not in evidence_text
        assert "直接回答" not in evidence_text
        assert "章节业务答案" not in evidence_text
        assert evidence_ledger is not None
        return ReportDocument(
            title=plan.title,
            time_range=plan.time_range,
            data_sources=plan.data_sources,
            opening_summary="完整报告正文由报告撰写器一次性生成。",
            sections=[
                ReportDocumentSection(
                    section_id="overview",
                    title="经营概览",
                    body="这不是逐章节分析回答拼接出来的正文。",
                    evidence_refs=["workspace_table_count"],
                )
            ],
            action_recommendations=["继续使用报告证据包生成整篇报告。"],
            data_boundaries=["当前为 one-pass runner 回归测试。"],
        )

    monkeypatch.setattr(report_runner, "compose_report_document", fake_compose_report_document)

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成一份最近90天经营复盘报告。",
    )
    report_text = json.dumps(result["report"], ensure_ascii=False)

    assert calls["composer"] == 1
    assert "完整报告正文由报告撰写器一次性生成" in report_text
    assert "business_answer" not in report_text
    assert "章节业务答案" not in report_text
    assert "直接回答" not in report_text
    assert "sections" not in result["report"]


def test_report_runner_repairs_unsupported_facts_once_and_completes(tmp_path, monkeypatch):
    import workspaces.report_runner as report_runner

    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = {"compose": 0, "repair": 0, "validate": 0}

    def fake_compose_report_document(*, plan, evidence_pack, evidence_ledger=None, provider=None):
        calls["compose"] += 1
        assert evidence_ledger is not None
        return ReportDocument(
            title=plan.title,
            time_range=plan.time_range,
            data_sources=plan.data_sources,
            opening_summary="最近90天总收入为 99.9 万。",
            sections=[],
            action_recommendations=[],
            data_boundaries=[],
        )

    def fake_repair_report_document(*, document, plan, evidence_pack, evidence_ledger, unsupported_claims, provider=None):
        calls["repair"] += 1
        assert unsupported_claims == ["正文数字缺少证据支持：99.9 万"]
        return ReportDocument(
            title=plan.title,
            time_range=plan.time_range,
            data_sources=plan.data_sources,
            opening_summary="报告已删除缺少证据支持的收入数字。",
            sections=[],
            action_recommendations=["补齐口径后再做预算判断。"],
            data_boundaries=["已自动修正缺少账本支持的硬事实。"],
        )

    def fake_validate_report_document(*, document, plan, evidence_pack, evidence_ledger=None):
        calls["validate"] += 1
        if calls["validate"] == 1:
            return ReportValidationResult(status="warning", unsupported_claims=["正文数字缺少证据支持：99.9 万"])
        return ReportValidationResult(status="passed", checked_facts=["ledger_fact_workspace_table_count"])

    monkeypatch.setattr(report_runner, "compose_report_document", fake_compose_report_document)
    monkeypatch.setattr(report_runner, "repair_report_document", fake_repair_report_document)
    monkeypatch.setattr(report_runner, "validate_report_document", fake_validate_report_document)

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成一份最近90天经营复盘报告。",
    )

    report = result["report"]
    assert result["success"] is True
    assert report["status"] == "completed"
    assert calls == {"compose": 1, "repair": 1, "validate": 2}
    assert report["validation"]["unsupported_claims"] == []
    assert report["provider_metadata"]["repair_attempted"] is True
    assert report["document"]["technical_appendix"]["repair"]["attempted"] is True
    assert report["provider_metadata"]["generation_flow"] == "ledger_backed_report_center"


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
    document_text = json.dumps(
        {
            "opening_summary": saved["document"]["opening_summary"],
            "sections": saved["document"]["sections"],
            "action_recommendations": saved["document"]["action_recommendations"],
            "data_boundaries": saved["document"]["data_boundaries"],
        },
        ensure_ascii=False,
    )
    appendix_text = json.dumps(saved["document"]["technical_appendix"], ensure_ascii=False)

    assert "SELECT" not in document_text
    assert "raw_rows" not in document_text
    assert "provider_metadata" not in document_text
    assert "trace" not in document_text
    assert "plan" in appendix_text
    assert "evidence_pack" in appendix_text
