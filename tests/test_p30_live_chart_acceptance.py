import json
import os
import sqlite3
import time

import pytest


def _live_product_config_or_skip():
    from llm_ops.deepseek_provider import load_deepseek_config

    live_flag = str(os.environ.get("INSIGHTFLOW_LIVE_DEEPSEEK_TESTS", "")).strip().lower()
    product_flag = str(os.environ.get("INSIGHTFLOW_PRODUCT_LIVE_MODE", "")).strip().lower()
    config = load_deepseek_config(require_api_key=True)
    if live_flag not in {"1", "true", "yes", "on"}:
        pytest.skip(
            "Set INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1, INSIGHTFLOW_PRODUCT_LIVE_MODE=1, "
            "and DEEPSEEK_API_KEY to run P30 live chart acceptance."
        )
    if product_flag not in {"1", "true", "yes", "on"}:
        pytest.skip("Set INSIGHTFLOW_PRODUCT_LIVE_MODE=1 to run P30 live chart acceptance.")
    if not config.success:
        pytest.skip("DEEPSEEK_API_KEY is required to run P30 live chart acceptance.")
    return config


class _CountingProvider:
    def __init__(self, name, provider):
        self.name = name
        self.provider = provider
        self.model = getattr(provider, "model", "unknown")
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return self.provider.generate(request)


def _build_counting_providers():
    from llm_ops.runtime_provider import (
        build_business_answer_provider,
        build_question_understanding_provider,
        build_report_composer_provider,
        build_sql_candidate_provider,
        build_sql_planning_provider,
        build_visualization_agent_provider,
    )

    builders = {
        "question_understanding": build_question_understanding_provider,
        "sql_planning": build_sql_planning_provider,
        "sql_candidate": build_sql_candidate_provider,
        "business_answer": build_business_answer_provider,
        "visualization_agent": build_visualization_agent_provider,
        "report_composer": build_report_composer_provider,
    }
    providers = {}
    for name, builder in builders.items():
        provider = builder()
        if provider is not None:
            providers[name] = _CountingProvider(name, provider)
    return providers


def _create_live_workspace(tmp_path):
    from workspaces.profiler import profile_workspace_database
    from workspaces.semantic_draft import generate_semantic_layer_draft
    from workspaces.store import WorkspaceStore

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P30 Live DeepSeek Chart Workspace")
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


def test_p30_live_deepseek_analysis_report_chart_and_export_acceptance(tmp_path):
    from workspaces.analysis_runner import run_workspace_analysis
    from workspaces.export_package import build_analysis_export_package, build_report_export_package
    from workspaces.report_runner import run_workspace_report

    config = _live_product_config_or_skip()
    providers = _build_counting_providers()
    required = {"question_understanding", "sql_planning", "sql_candidate", "business_answer", "visualization_agent", "report_composer"}
    missing = sorted(required.difference(providers))
    if missing:
        pytest.skip(f"DeepSeek providers unavailable for P30 live chart acceptance: {missing}")

    store, workspace = _create_live_workspace(tmp_path)

    analysis_question = "最近90天按渠道比较收入并生成图表。"
    analysis_started = time.perf_counter()
    analysis = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question=analysis_question,
        providers={
            "question_understanding": providers["question_understanding"],
            "sql_planning": providers["sql_planning"],
            "sql_candidate": providers["sql_candidate"],
            "business_answer": providers["business_answer"],
            "visualization_agent": providers["visualization_agent"],
        },
        force_reanalysis=True,
    )
    analysis_elapsed_ms = int((time.perf_counter() - analysis_started) * 1000)
    analysis_package = build_analysis_export_package(
        analysis["product_result"],
        workspace_root=workspace["root_path"],
    ).to_dict()
    analysis_charts = analysis["product_result"]["chart_artifacts"]

    report_goal = "生成一份最近90天经营复盘报告，关注收入结构、客户分群和趋势变化。"
    report_started = time.perf_counter()
    report_result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        report_goal,
        providers={"report_composer": providers["report_composer"]},
    )
    report_elapsed_ms = int((time.perf_counter() - report_started) * 1000)
    report = report_result["report"]
    report_package = build_report_export_package(report, workspace_root=workspace["root_path"]).to_dict()
    report_charts = report["chart_artifacts"]

    live_summary = {
        "model": config.model,
        "analysis": {
            "question": analysis_question,
            "route": analysis["analysis_route"]["route"],
            "provider_calls": {
                name: len(provider.requests)
                for name, provider in providers.items()
                if name != "report_composer"
            },
            "chart_count": len(analysis_charts),
            "chart_artifacts": [_chart_summary(chart) for chart in analysis_charts],
            "export_package": _package_summary(analysis_package),
            "elapsed_ms": analysis_elapsed_ms,
        },
        "report": {
            "question": report_goal,
            "path": report["provider_metadata"]["generation_flow"],
            "provider_calls": {"report_composer": len(providers["report_composer"].requests)},
            "chart_count": len(report_charts),
            "chart_artifacts": [_chart_summary(chart) for chart in report_charts],
            "export_package": _package_summary(report_package),
            "elapsed_ms": report_elapsed_ms,
        },
    }
    print("P30_LIVE_SUMMARY=" + json.dumps(live_summary, ensure_ascii=False, sort_keys=True))

    assert analysis["status"] == "completed", live_summary
    assert sum(live_summary["analysis"]["provider_calls"].values()) > 0, live_summary
    assert analysis["execution_result"]["success"] is True, live_summary
    assert analysis_charts, live_summary
    assert any(chart.get("renderer") == "echarts" for chart in analysis_charts), live_summary
    assert any(chart.get("echarts_option") for chart in analysis_charts), live_summary
    assert any(chart.get("image_path") or chart.get("image_url") for chart in analysis_charts), live_summary
    assert analysis_package["chart_artifacts"], live_summary
    assert analysis_package["static_assets"], live_summary
    assert analysis_package["evidence_refs"], live_summary

    assert report_result["success"] is True, live_summary
    assert providers["report_composer"].requests, live_summary
    assert report_charts, live_summary
    assert all(chart.get("source") == "report_center" for chart in report_charts), live_summary
    assert any(chart.get("echarts_option") for chart in report_charts), live_summary
    assert any(chart.get("image_path") or chart.get("image_url") for chart in report_charts), live_summary
    assert report_package["chart_artifacts"], live_summary
    assert report_package["static_assets"], live_summary
    assert report_package["evidence_refs"], live_summary


def _chart_summary(chart):
    return {
        "artifact_id": chart.get("artifact_id"),
        "renderer": chart.get("renderer"),
        "source": chart.get("source"),
        "has_echarts_option": bool(chart.get("echarts_option")),
        "has_static_fallback": bool(chart.get("image_path") or chart.get("image_url") or chart.get("path") or chart.get("url")),
        "evidence_refs": list(chart.get("evidence_refs") or []),
        "data_row_count": chart.get("data_row_count"),
    }


def _package_summary(package):
    return {
        "source_type": package["source_type"],
        "chart_count": len(package["chart_artifacts"]),
        "static_asset_count": len(package["static_assets"]),
        "evidence_ref_count": len(package["evidence_refs"]),
        "warnings": list(package["warnings"]),
    }
