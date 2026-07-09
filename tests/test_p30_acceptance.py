import json
import sqlite3
from pathlib import Path

from workspaces.analysis_runner import run_workspace_analysis
from workspaces.export_package import build_analysis_export_package, build_report_export_package
from workspaces.profiler import profile_workspace_database
from workspaces.report_runner import run_workspace_report
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


def _create_p30_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P30 Acceptance Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            """
            CREATE TABLE channel_performance (
                business_date TEXT,
                channel_name TEXT,
                customer_segment TEXT,
                revenue REAL,
                ad_spend REAL,
                roas REAL
            )
            """
        )
        conn.executemany(
            "INSERT INTO channel_performance VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("2026-04-20", "搜索广告", "新客", 120000.0, 80000.0, 1.5),
                ("2026-06-10", "私域社群", "高价值会员", 180000.0, 30000.0, 6.0),
                ("2026-06-12", "直播间", "成长型客户", 90000.0, 70000.0, 1.29),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace


def _assert_no_markdown_leaks(markdown: str):
    forbidden = [
        "echarts_option",
        "chart_spec",
        "raw SQL",
        "raw_sql",
        "generated_sql",
        "SELECT ",
        "trace",
        "provider_metadata",
    ]
    for term in forbidden:
        assert term not in markdown


def test_p30_acceptance_chart_artifacts_report_reuse_export_packages_and_fallback_warnings(tmp_path):
    store, workspace = _create_p30_workspace(tmp_path)

    chart_result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个渠道收入最高？给我画图。",
    )
    chart_artifacts = chart_result["product_result"]["chart_artifacts"]
    chart_artifact = chart_artifacts[0]

    assert chart_result["status"] == "completed"
    assert chart_result["analysis_route"]["route"] == "fast_fact"
    assert chart_artifacts
    assert chart_artifact["renderer"] == "echarts"
    assert chart_artifact["echarts_option"]["series"]
    assert chart_artifact["image_path"]
    assert chart_artifact["image_url"]
    assert chart_artifact["evidence_refs"] == ["question_evidence_pack"]
    assert chart_artifact["source"] == "analysis_workbench"

    no_chart_result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个渠道收入最高？",
        force_reanalysis=True,
    )

    assert no_chart_result["status"] == "completed"
    assert no_chart_result["analysis_route"]["route"] == "fast_fact"
    assert no_chart_result["product_result"]["chart_artifacts"] == []

    report_result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成一份最近90天经营复盘报告，关注收入结构、客户分群和趋势变化。",
    )
    report = report_result["report"]
    report_chart_artifacts = report["chart_artifacts"]

    assert report_result["success"] is True
    assert report_chart_artifacts
    assert all(chart["source"] == "report_center" for chart in report_chart_artifacts)
    assert any(chart["renderer"] == "echarts" for chart in report_chart_artifacts)
    assert all(chart.get("image_path") or chart.get("image_url") for chart in report_chart_artifacts)
    assert all(chart.get("evidence_refs") for chart in report_chart_artifacts)

    markdown = Path(report["markdown_path"]).read_text(encoding="utf-8")
    _assert_no_markdown_leaks(markdown)

    report_package = build_report_export_package(report, workspace_root=workspace["root_path"]).to_dict()
    assert report_package["source_type"] == "report"
    assert report_package["chart_artifacts"]
    assert report_package["static_assets"]
    assert report_package["evidence_refs"]
    assert "chart_spec" not in json.dumps(report_package["chart_artifacts"], ensure_ascii=False)

    analysis_package = build_analysis_export_package(
        chart_result["product_result"],
        workspace_root=workspace["root_path"],
    ).to_dict()
    assert analysis_package["source_type"] == "analysis"
    assert analysis_package["chart_artifacts"]
    assert analysis_package["static_assets"]
    assert analysis_package["evidence_refs"] == ["question_evidence_pack"]

    option_only_product = dict(chart_result["product_result"])
    option_only_chart = {
        key: value
        for key, value in chart_artifact.items()
        if key not in {"path", "url", "image_path", "image_url"}
    }
    option_only_product["chart_artifacts"] = [option_only_chart]
    option_only_package = build_analysis_export_package(
        option_only_product,
        workspace_root=workspace["root_path"],
    ).to_dict()

    assert option_only_package["chart_artifacts"][0]["echarts_option"]
    assert option_only_package["static_assets"]
    assert option_only_package["static_assets"][0]["path"].endswith(".svg")
    assert option_only_package["warnings"] == []
