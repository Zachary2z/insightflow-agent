import json

from workspaces.report_models import (
    ReportArtifactRecord,
    ReportDocument,
    ReportDocumentSection,
    ReportEvidenceChart,
    ReportEvidenceFact,
    ReportEvidencePack,
    ReportRecord,
)


def _serialized(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _assert_no_export_leaks(package):
    serialized = _serialized(package)
    forbidden = [
        "SELECT ",
        "DROP ",
        "generated_sql",
        "raw_sql",
        "raw_rows",
        "trace_path",
        "trace.json",
        "provider_metadata",
        "api_key",
        "sk-live",
        "analysis.db",
        "database_path",
        "task_id",
        "task_purpose",
        "debug_id",
        "prompt",
        "/Users/",
        "/tmp/",
    ]
    for term in forbidden:
        assert term not in serialized


def test_report_export_package_includes_document_charts_static_assets_and_evidence_refs():
    from workspaces.export_package import build_report_export_package

    workspace_root = "/tmp/workspaces/ws_export"
    report = ReportRecord(
        report_id="report_1",
        workspace_id="ws_export",
        report_type="business_review",
        report_goal="生成经营复盘报告",
        title="经营复盘报告",
        status="completed",
        markdown_path=f"{workspace_root}/reports/report_1/report.md",
        json_path=f"{workspace_root}/reports/report_1/report.json",
        trace_path=f"{workspace_root}/reports/report_1/trace.json",
        document=ReportDocument(
            title="经营复盘报告",
            time_range="最近90天",
            data_sources=["orders"],
            opening_summary="私域社群收入领先。",
            sections=[
                ReportDocumentSection(
                    section_id="overview",
                    title="经营概览",
                    body="私域社群收入为 180000。",
                    evidence_refs=["fact_channel_revenue"],
                    chart_refs=["chart_channel_revenue"],
                )
            ],
        ),
        evidence_pack=ReportEvidencePack(
            facts=[
                ReportEvidenceFact(
                    fact_id="fact_channel_revenue",
                    label="渠道收入",
                    value=180000,
                    display_value="18.0 万",
                    source_chapter_id="overview",
                    evidence_ref="table_channel_revenue",
                )
            ],
            charts=[
                ReportEvidenceChart(
                    chart_id="chart_channel_revenue",
                    title="渠道收入对比",
                    source_chapter_id="overview",
                    artifact_id="artifact_chart_channel_revenue",
                )
            ],
            technical_details={
                "generated_sql": "SELECT channel, SUM(revenue) FROM orders GROUP BY channel",
                "trace_path": f"{workspace_root}/reports/report_1/trace.json",
            },
        ),
        chart_artifacts=[
            {
                "artifact_id": "artifact_chart_channel_revenue",
                "title": "渠道收入对比",
                "renderer": "echarts",
                "chart_type": "ranked_bar",
                "echarts_option": {"series": [{"type": "bar", "data": [180000.0]}]},
                "path": "reports/report_1/artifacts/channel.svg",
                "url": "/api/workspaces/ws_export/artifacts/reports/report_1/artifacts/channel.svg",
                "image_path": "reports/report_1/artifacts/channel.svg",
                "image_url": "/api/workspaces/ws_export/artifacts/reports/report_1/artifacts/channel.svg",
                "rendering_status": "rendered",
                "business_annotation": "私域社群收入最高。",
                "evidence_refs": ["table_channel_revenue", "fact_channel_revenue"],
                "source": "report_center",
                "data_row_count": 3,
                "chart_spec": {"x": "channel", "y": "revenue"},
            }
        ],
        artifacts=[
            ReportArtifactRecord(
                artifact_id="artifact_markdown_report_1",
                artifact_type="markdown_report",
                title="Markdown 报告",
                relative_path="reports/report_1/report.md",
                download_url="/api/workspaces/ws_export/reports/report_1/download",
                evidence_ids=["fact_channel_revenue"],
                chart_ids=["chart_channel_revenue"],
            ),
            ReportArtifactRecord(
                artifact_id="artifact_document_report_1",
                artifact_type="report_document",
                title="报告文档记录",
                relative_path="reports/report_1/report.json",
                evidence_ids=["fact_channel_revenue"],
                chart_ids=["chart_channel_revenue"],
            ),
        ],
        provider_metadata={"model": "deepseek", "api_key": "secret"},
    )

    package = build_report_export_package(report, workspace_root=workspace_root).to_dict()

    assert package["workspace_id"] == "ws_export"
    assert package["source_type"] == "report"
    assert package["source_id"] == "report_1"
    assert package["generated_at"]
    assert package["language"] == "zh"
    assert package["document"]["opening_summary"] == "私域社群收入领先。"
    assert package["business_content_summary"] == "私域社群收入领先。"
    assert [section["title"] for section in package["sections"]] == ["经营概览"]
    assert package["action_recommendations"] == []
    assert package["data_boundaries"] == []
    assert package["markdown_path"] == "reports/report_1/report.md"
    assert package["document_path"] == "reports/report_1/report.json"
    assert package["chart_artifacts"][0]["echarts_option"]["series"][0]["data"] == [180000.0]
    assert package["chart_artifacts"][0]["image_path"].endswith("channel.svg")
    assert package["chart_artifacts"][0]["chart_ids"] == ["chart_channel_revenue"]
    assert package["chart_artifacts"][0]["chart_id"] == "chart_channel_revenue"
    assert package["chart_artifacts"][0]["source_chapter_id"] == "overview"
    assert "chart_spec" not in package["chart_artifacts"][0]
    assert package["static_assets"][0]["path"] == "reports/report_1/artifacts/channel.svg"
    assert package["evidence_summary"]["fact_count"] == 1
    assert "table_channel_revenue" in package["evidence_refs"]
    assert "fact_channel_revenue" in package["evidence_refs"]
    assert package["warnings"] == []
    _assert_no_export_leaks(package)


def test_report_export_package_preserves_custom_report_document_order_not_fixed_template():
    from workspaces.export_package import build_report_export_package

    report = ReportRecord(
        report_id="report_custom",
        workspace_id="ws_custom",
        report_type="business_review",
        report_goal="生成客服履约报告",
        title="客服履约报告",
        status="completed",
        document=ReportDocument(
            title="客服履约报告",
            time_range="最近30天",
            data_sources=["support_tickets"],
            opening_summary="退款咨询需要优先处理。",
            sections=[
                ReportDocumentSection(section_id="tickets", title="工单量概览", body="退款咨询工单最多。"),
                ReportDocumentSection(section_id="types", title="投诉类型分布", body="退款咨询占比最高。"),
                ReportDocumentSection(section_id="sla", title="响应时效", body="平均响应时长偏高。"),
                ReportDocumentSection(section_id="priority", title="优先处理建议", body="先处理退款咨询。"),
            ],
            action_recommendations=["先降低退款咨询响应时长。"],
            data_boundaries=["当前缺少满意度字段。"],
        ),
    )

    package = build_report_export_package(report).to_dict()

    assert package["source_type"] == "report"
    assert package["title"] == "客服履约报告"
    assert package["business_content_summary"] == "退款咨询需要优先处理。"
    assert [section["title"] for section in package["sections"]] == [
        "工单量概览",
        "投诉类型分布",
        "响应时效",
        "优先处理建议",
    ]
    assert "经营概览" not in [section["title"] for section in package["sections"]]
    assert "渠道表现" not in [section["title"] for section in package["sections"]]
    assert package["action_recommendations"] == ["先降低退款咨询响应时长。"]
    assert package["data_boundaries"] == ["当前缺少满意度字段。"]
    _assert_no_export_leaks(package)


def test_analysis_export_package_preserves_echarts_and_static_fallback_without_technical_leaks():
    from workspaces.export_package import build_analysis_export_package

    product_result = {
        "workspace_id": "ws_export",
        "run_id": "run_1",
        "status": "completed",
        "business_answer": {
            "headline": "私域社群收入最高",
            "direct_answer": "最近90天私域社群收入最高。",
            "why": "证据表显示私域社群收入为 180000。",
            "evidence_bullets": ["私域社群收入为 180000。"],
            "recommendations": ["继续跟踪收入和投放效率。"],
            "caveats": ["当前结论只基于本次查询返回的数据。"],
            "confidence": "medium",
        },
        "evidence": {
            "question_evidence": {
                "columns": ["channel", "revenue"],
                "rows": [["私域社群", 180000]],
                "tool_calls": [{"tool_name": "sql_executor", "sql": "SELECT * FROM orders"}],
            },
            "fact_payload": {
                "technical_refs": {"sql": "technical_details.sql"},
                "result_rows": [{"evidence_ref": "question_evidence_pack"}],
            },
        },
        "chart_artifacts": [
            {
                "artifact_id": "chart_run_1_ranked_bar",
                "title": "渠道收入对比",
                "renderer": "echarts",
                "chart_type": "ranked_bar",
                "echarts_option": {"series": [{"type": "bar", "data": [180000.0]}]},
                "image_path": "runs/run_1/charts/channel.png",
                "image_url": "/api/workspaces/ws_export/artifacts/runs/run_1/charts/channel.png",
                "path": "runs/run_1/charts/channel.png",
                "url": "/api/workspaces/ws_export/artifacts/runs/run_1/charts/channel.png",
                "rendering_status": "rendered",
                "business_annotation": "私域社群收入最高。",
                "evidence_refs": ["question_evidence_pack"],
                "source": "analysis_workbench",
                "data_row_count": 1,
                "chart_spec": {"x": "channel", "y": "revenue"},
            }
        ],
        "technical_details": {
            "sql": "SELECT channel, SUM(revenue) FROM orders GROUP BY channel",
            "trace_path": "/tmp/workspaces/ws_export/runs/run_1/trace.json",
            "provider_metadata": {"model": "deepseek"},
        },
    }

    package = build_analysis_export_package(product_result).to_dict()

    assert package["workspace_id"] == "ws_export"
    assert package["source_type"] == "analysis"
    assert package["source_id"] == "run_1"
    assert package["generated_at"]
    assert package["business_answer"]["headline"] == "私域社群收入最高"
    assert package["business_content_summary"] == "最近90天私域社群收入最高。"
    assert package["sections"] == []
    assert package["action_recommendations"] == ["继续跟踪收入和投放效率。"]
    assert package["data_boundaries"] == ["当前结论只基于本次查询返回的数据。"]
    assert package["evidence_summary"]["refs"] == ["question_evidence_pack"]
    assert package["chart_artifacts"][0]["echarts_option"]["series"][0]["data"] == [180000.0]
    assert package["chart_artifacts"][0]["image_path"] == "runs/run_1/charts/channel.png"
    assert package["static_assets"][0]["url"].endswith("/runs/run_1/charts/channel.png")
    assert package["evidence_refs"] == ["question_evidence_pack"]
    assert package["warnings"] == []
    _assert_no_export_leaks(package)


def test_analysis_export_package_does_not_synthesize_missing_business_answer_or_report_sections():
    from workspaces.export_package import build_analysis_export_package

    product_result = {
        "workspace_id": "ws_export",
        "run_id": "run_missing_answer",
        "status": "completed",
        "business_answer": {
            "headline": "业务回答缺失",
            "direct_answer": "业务回答缺失：当前没有可安全展示的模型业务回答。",
            "why": "Product Result Builder only assembles payloads.",
            "evidence_bullets": [],
            "recommendations": [],
            "caveats": ["可以重新生成回答。"],
            "confidence": "low",
        },
        "evidence": {
            "table_preview": {"columns": ["channel", "revenue"], "rows": [["私域社群", 300000.0]]},
            "ledger_summary": {"facts": [{"label": "收入", "value": 300000.0}]},
        },
    }

    package = build_analysis_export_package(product_result).to_dict()
    payload_text = _serialized(package)

    assert package["source_type"] == "analysis"
    assert package["business_answer"]["headline"] == "业务回答缺失"
    assert package["business_content_summary"].startswith("业务回答缺失")
    assert package["sections"] == []
    assert "私域社群收入最高" not in payload_text
    assert "经营概览" not in payload_text
    _assert_no_export_leaks(package)


def test_analysis_export_package_warns_when_chart_has_no_static_fallback():
    from workspaces.export_package import build_analysis_export_package

    product_result = {
        "workspace_id": "ws_export",
        "run_id": "run_option_only",
        "business_answer": {
            "headline": "已有图表",
            "direct_answer": "图表可以在 Web 中交互查看。",
            "why": "基于本次证据生成。",
            "evidence_bullets": [],
            "recommendations": [],
            "caveats": [],
            "confidence": "medium",
        },
        "chart_artifacts": [
            {
                "artifact_id": "chart_option_only",
                "title": "渠道收入对比",
                "renderer": "echarts",
                "chart_type": "ranked_bar",
                "echarts_option": {"series": [{"type": "bar", "data": [1.0]}]},
                "rendering_status": "rendered",
                "evidence_refs": ["question_evidence_pack"],
                "source": "analysis_workbench",
                "data_row_count": 1,
            }
        ],
    }

    package = build_analysis_export_package(product_result).to_dict()

    assert package["chart_artifacts"][0]["echarts_option"]
    assert package["static_assets"] == []
    assert any("chart_option_only" in warning and "静态" in warning for warning in package["warnings"])
    _assert_no_export_leaks(package)


def test_analysis_export_package_generates_static_svg_for_option_only_chart_when_workspace_root_exists(tmp_path):
    from workspaces.export_package import build_analysis_export_package

    product_result = {
        "workspace_id": "ws_export",
        "run_id": "run_option_only",
        "business_answer": {
            "headline": "已有图表",
            "direct_answer": "图表可以导出为静态 SVG。",
            "why": "基于已有 ECharts option。",
            "evidence_bullets": [],
            "recommendations": [],
            "caveats": [],
            "confidence": "medium",
        },
        "chart_artifacts": [
            {
                "artifact_id": "chart_option_only",
                "title": "渠道收入对比",
                "renderer": "echarts",
                "chart_type": "ranked_bar",
                "echarts_option": {
                    "xAxis": {"type": "category", "data": ["私域社群", "直播间"]},
                    "series": [{"type": "bar", "name": "收入", "data": [180000.0, 90000.0]}],
                },
                "rendering_status": "rendered",
                "evidence_refs": ["question_evidence_pack"],
                "source": "analysis_workbench",
                "data_row_count": 2,
            }
        ],
    }

    package = build_analysis_export_package(product_result, workspace_root=tmp_path).to_dict()

    assert package["chart_artifacts"][0]["image_path"] == "exports/charts/chart_option_only.svg"
    assert package["static_assets"][0]["path"] == "exports/charts/chart_option_only.svg"
    assert package["static_assets"][0]["generated"] is True
    assert (tmp_path / "exports/charts/chart_option_only.svg").exists()
    assert package["warnings"] == []
    _assert_no_export_leaks(package)


def test_export_package_rejects_traversal_paths_and_secret_urls():
    from workspaces.export_package import build_analysis_export_package

    package = build_analysis_export_package(
        {
            "workspace_id": "ws_export",
            "run_id": "run_secret_asset",
            "business_answer": {
                "headline": "图表需要补充静态导出",
                "direct_answer": "Web 图表可用，但静态资产不安全。",
                "why": "导出包应过滤不安全路径和 URL。",
                "evidence_bullets": [],
                "recommendations": [],
                "caveats": [],
                "confidence": "medium",
            },
            "chart_artifacts": [
                {
                    "artifact_id": "chart_secret_asset",
                    "title": "不安全图表",
                    "renderer": "echarts",
                    "chart_type": "ranked_bar",
                    "echarts_option": {"series": [{"type": "bar", "data": [1.0]}]},
                    "path": "../secret/chart.png",
                    "image_path": "~/secret/chart.png",
                    "url": "https://example.com/chart.png?api_key=secret",
                    "image_url": "/api/workspaces/ws_export/artifacts/chart.png?token=secret",
                    "rendering_status": "rendered",
                    "evidence_refs": ["question_evidence_pack"],
                    "source": "analysis_workbench",
                    "data_row_count": 1,
                }
            ],
        },
        workspace_root="/tmp/workspaces/ws_export",
    ).to_dict()

    assert package["chart_artifacts"][0]["echarts_option"]
    assert package["chart_artifacts"][0]["path"] == "exports/charts/chart_secret_asset.svg"
    assert package["chart_artifacts"][0]["image_path"] == "exports/charts/chart_secret_asset.svg"
    assert "url" not in package["chart_artifacts"][0]
    assert "image_url" not in package["chart_artifacts"][0]
    assert package["static_assets"][0]["path"] == "exports/charts/chart_secret_asset.svg"
    assert package["static_assets"][0]["generated"] is True
    assert package["warnings"] == []
    _assert_no_export_leaks(package)


def test_export_package_strips_sensitive_fields_from_body_and_evidence_summary():
    from workspaces.export_package import build_analysis_export_package

    package = build_analysis_export_package(
        {
            "workspace_id": "ws_export",
            "run_id": "run_sensitive",
            "created_at": "2026-07-07T00:00:00Z",
            "business_answer": {
                "headline": "渠道收入结论",
                "direct_answer": "SELECT * FROM orders; sk-live-secret prompt text",
                "why": "trace_path=/Users/me/project/trace.json provider_metadata model=deepseek",
                "evidence_bullets": ["raw_rows: [[1,2]]", "可展示证据：收入已验证。"],
                "recommendations": ["task_id=core_fact_income 不应外露", "优先复核收入证据。"],
                "caveats": ["database_path=/tmp/workspaces/ws/analysis.db", "当前缺少利润数据。"],
                "confidence": "medium",
            },
            "evidence": {
                "ledger_summary": {
                    "facts": [{"label": "收入", "value": 100, "task_id": "core_fact_income"}],
                    "data_limits": ["provider_metadata api_key=secret", "当前缺少利润数据。"],
                    "refs": ["question_evidence_pack"],
                },
                "fact_payload": {
                    "technical_refs": {"sql": "technical_details.sql"},
                    "result_rows": [{"evidence_ref": "question_evidence_pack", "raw_rows": [[1, 2]]}],
                },
            },
            "technical_details": {
                "sql": "SELECT * FROM orders",
                "raw_rows": [[1, 2]],
                "trace_path": "/Users/me/project/trace.json",
                "provider_metadata": {"api_key": "sk-live-secret"},
                "debug": {"database_path": "/tmp/workspaces/ws/analysis.db"},
            },
        }
    ).to_dict()

    payload_text = _serialized(package)

    assert package["business_answer"]["headline"] == "渠道收入结论"
    assert package["business_answer"]["direct_answer"] == ""
    assert package["business_answer"]["why"] == ""
    assert package["business_answer"]["evidence_bullets"] == ["可展示证据：收入已验证。"]
    assert package["business_answer"]["recommendations"] == ["优先复核收入证据。"]
    assert package["business_answer"]["caveats"] == ["当前缺少利润数据。"]
    assert package["evidence_summary"]["data_limits"] == ["当前缺少利润数据。"]
    assert "question_evidence_pack" in package["evidence_refs"]
    assert "SELECT" not in payload_text.upper()
    _assert_no_export_leaks(package)


def test_legacy_png_svg_chart_artifacts_enter_export_package_with_source_ids_distinct():
    from workspaces.export_package import build_analysis_export_package, build_report_export_package

    analysis_package = build_analysis_export_package(
        {
            "workspace_id": "ws_export",
            "run_id": "run_legacy",
            "business_answer": {
                "headline": "旧图表可导出",
                "direct_answer": "旧 PNG 图表保留静态导出。",
                "why": "图表已有静态文件。",
                "evidence_bullets": [],
                "recommendations": [],
                "caveats": [],
                "confidence": "medium",
            },
            "chart_artifacts": [
                {
                    "title": "旧 PNG 图表",
                    "path": "runs/run_legacy/charts/legacy.png",
                    "url": "/api/workspaces/ws_export/artifacts/runs/run_legacy/charts/legacy.png",
                    "rendering_status": "rendered",
                    "business_annotation": "旧图表说明。",
                }
            ],
        }
    ).to_dict()
    report_package = build_report_export_package(
        {
            "workspace_id": "ws_export",
            "report_id": "report_legacy",
            "title": "旧报告",
            "created_at": "2026-07-06T00:00:00Z",
            "document": {"title": "旧报告", "opening_summary": "旧 SVG 图表保留静态导出。"},
            "chart_artifacts": [
                {
                    "title": "旧 SVG 图表",
                    "path": "reports/report_legacy/artifacts/legacy.svg",
                    "url": "/api/workspaces/ws_export/artifacts/reports/report_legacy/artifacts/legacy.svg",
                    "rendering_status": "rendered",
                    "business_annotation": "旧图表说明。",
                    "evidence_refs": ["legacy_evidence"],
                }
            ],
        }
    ).to_dict()

    assert analysis_package["source_type"] == "analysis"
    assert analysis_package["source_id"] == "run_legacy"
    assert report_package["source_type"] == "report"
    assert report_package["source_id"] == "report_legacy"
    assert analysis_package["chart_artifacts"][0]["renderer"] == "image"
    assert analysis_package["chart_artifacts"][0]["image_path"].endswith(".png")
    assert report_package["chart_artifacts"][0]["renderer"] == "image"
    assert report_package["chart_artifacts"][0]["image_path"].endswith(".svg")
    assert report_package["evidence_refs"] == ["legacy_evidence"]
    _assert_no_export_leaks(analysis_package)
    _assert_no_export_leaks(report_package)
