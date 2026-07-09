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
        pytest.skip("Set INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 and DEEPSEEK_API_KEY to run P33 live acceptance.")
    if product_flag not in {"1", "true", "yes", "on"}:
        pytest.skip("Set INSIGHTFLOW_PRODUCT_LIVE_MODE=1 to run P33 live acceptance.")
    if not config.success:
        pytest.skip("DEEPSEEK_API_KEY is required to run P33 live acceptance.")
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


def _create_p33_workspace(tmp_path):
    from workspaces.profiler import profile_workspace_database
    from workspaces.semantic_draft import generate_semantic_layer_draft
    from workspaces.store import WorkspaceStore

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P33 Live Acceptance Workspace")
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


def test_p33_live_deepseek_analysis_workbench_and_report_acceptance(tmp_path):
    from workspaces.analysis_runner import run_workspace_analysis, run_workspace_analysis_follow_up
    from workspaces.report_runner import run_workspace_report

    config = _live_product_config_or_skip()
    providers = _build_counting_providers()
    required = {
        "question_understanding",
        "sql_planning",
        "sql_candidate",
        "business_answer",
        "visualization_agent",
        "report_composer",
    }
    missing = sorted(required.difference(providers))
    if missing:
        pytest.skip(f"DeepSeek providers unavailable for P33 live acceptance: {missing}")

    store, workspace = _create_p33_workspace(tmp_path)
    analysis_providers = {
        "question_understanding": providers["question_understanding"],
        "sql_planning": providers["sql_planning"],
        "sql_candidate": providers["sql_candidate"],
        "business_answer": providers["business_answer"],
        "visualization_agent": providers["visualization_agent"],
    }

    cases = []
    fast_fact = _timed_analysis(
        store,
        workspace["workspace_id"],
        "最近30天哪个渠道收入最高？只回答事实。",
        providers=analysis_providers,
    )
    cases.append(("fast_fact", fast_fact))

    standard = _timed_analysis(
        store,
        workspace["workspace_id"],
        "最近90天各渠道收入表现怎么样？",
        providers=analysis_providers,
    )
    cases.append(("standard_one_table", standard))

    deep = _timed_analysis(
        store,
        workspace["workspace_id"],
        "结合收入、投放花费和 ROI，哪个渠道最值得加预算？",
        providers=analysis_providers,
    )
    cases.append(("deep_multi_evidence", deep))

    follow_started = time.perf_counter()
    follow_result = run_workspace_analysis_follow_up(
        store,
        workspace["workspace_id"],
        standard["result"]["run_id"],
        "为什么？需要注意什么？",
        providers=analysis_providers,
    )
    follow = {"result": follow_result, "elapsed_ms": int((time.perf_counter() - follow_started) * 1000)}
    cases.append(("same_thread_follow_up", follow))

    chart = _timed_analysis(
        store,
        workspace["workspace_id"],
        "最近90天按渠道比较收入和投放花费，用图表展示。",
        providers=analysis_providers,
    )
    cases.append(("explicit_chart_request", chart))

    report_goal = "生成一份最近90天渠道经营复盘报告，覆盖收入结构、投放花费、ROI、关键风险和下一步建议。"
    report_started = time.perf_counter()
    report_result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        report_goal,
        providers={"report_composer": providers["report_composer"]},
    )
    report_elapsed_ms = int((time.perf_counter() - report_started) * 1000)

    summary = {
        "model": config.model,
        "analysis_cases": {
            label: _analysis_case_summary(label, item["result"], elapsed_ms=item["elapsed_ms"])
            for label, item in cases
        },
        "report_center": _report_summary(report_goal, report_result, elapsed_ms=report_elapsed_ms),
    }
    print("P33_LIVE_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))

    assert fast_fact["result"]["status"] == "completed", summary
    assert fast_fact["result"]["analysis_route"]["route"] == "fast_fact", summary
    assert fast_fact["result"]["product_result"]["chart_artifacts"] == [], summary
    assert _provider_called(fast_fact["result"], "business_answer_agent"), summary

    assert standard["result"]["status"] == "completed", summary
    assert standard["result"]["analysis_route"]["route"] == "standard_analysis", summary
    assert standard["result"]["execution_result"]["success"] is True, summary

    assert deep["result"]["status"] == "completed", summary
    assert deep["result"]["analysis_route"]["route"] == "deep_judgment", summary
    assert deep["result"]["execution_result"]["success"] is True, summary

    assert follow_result["status"] == "completed", summary
    assert follow_result["run_id"] == standard["result"]["run_id"], summary
    assert len(follow_result["analysis_thread_memory"]["turns"]) >= 2, summary
    assert _business_answer_is_natural_product_answer(follow_result), summary
    assert _main_payload_has_no_internal_leaks(follow_result), summary

    assert chart["result"]["status"] == "completed", summary
    assert chart["result"]["product_result"]["chart_artifacts"], summary
    assert any(item.get("renderer") == "echarts" for item in chart["result"]["product_result"]["chart_artifacts"]), summary

    assert report_result["success"] is True, summary
    assert report_result["report"]["provider_metadata"]["generation_flow"] == "ledger_backed_report_center", summary
    assert providers["report_composer"].requests, summary

    for _, item in cases:
        assert _main_payload_has_no_internal_leaks(item["result"]), summary
        assert _business_answer_is_natural_product_answer(item["result"]), summary


def _timed_analysis(store, workspace_id: str, question: str, *, providers: dict) -> dict:
    from workspaces.analysis_runner import run_workspace_analysis

    started = time.perf_counter()
    result = run_workspace_analysis(
        store,
        workspace_id,
        question,
        providers=providers,
        force_reanalysis=True,
    )
    return {"result": result, "elapsed_ms": int((time.perf_counter() - started) * 1000)}


def _analysis_case_summary(label: str, result: dict, *, elapsed_ms: int) -> dict:
    charts = result.get("product_result", {}).get("chart_artifacts") or []
    return {
        "label": label,
        "question": result.get("original_question") or result.get("user_question"),
        "route": (result.get("analysis_route") or {}).get("route"),
        "provider_called": [event.get("node") for event in result.get("trace") or [] if event.get("provider_called")],
        "elapsed_ms": elapsed_ms,
        "answer_summary": str((result.get("business_answer") or {}).get("direct_answer") or result.get("final_answer") or "")[:180],
        "evidence_summary": {
            "row_count": (result.get("execution_result") or {}).get("row_count"),
            "columns": list((result.get("execution_result") or {}).get("columns") or [])[:6],
            "fact_count": len((result.get("question_evidence_ledger") or {}).get("facts") or []),
            "data_limits": list((result.get("question_evidence_ledger") or {}).get("data_limits") or [])[:3],
        },
        "chart": {
            "generated": bool(charts),
            "renderers": [chart.get("renderer") for chart in charts],
            "sources": [chart.get("source") for chart in charts],
        },
        "leak_free_main_payload": _main_payload_has_no_internal_leaks(result),
    }


def _report_summary(goal: str, result: dict, *, elapsed_ms: int) -> dict:
    report = result["report"]
    charts = report.get("chart_artifacts") or []
    return {
        "question": goal,
        "route": report.get("provider_metadata", {}).get("generation_flow"),
        "provider_called": bool(report.get("provider_metadata", {}).get("provider_supplied")),
        "elapsed_ms": elapsed_ms,
        "answer_summary": str((report.get("document") or {}).get("opening_summary") or "")[:180],
        "evidence_summary": {
            "table_count": len((report.get("evidence_pack") or {}).get("tables") or []),
            "fact_count": len((report.get("evidence_pack") or {}).get("facts") or []),
            "data_limits": list((report.get("evidence_pack") or {}).get("data_limits") or [])[:3],
        },
        "chart": {
            "generated": bool(charts),
            "renderers": [chart.get("renderer") for chart in charts],
            "sources": [chart.get("source") for chart in charts],
        },
    }


def _provider_called(result: dict, node: str) -> bool:
    return any(event.get("node") == node and event.get("provider_called") for event in result.get("trace") or [])


def _main_payload_has_no_internal_leaks(result: dict) -> bool:
    product = dict(result.get("product_result") or {})
    product.pop("technical_details", None)
    serialized = json.dumps(product, ensure_ascii=False)
    forbidden = ("SELECT ", "raw_rows", "task_id", "task_purpose", "trace_path", "provider_metadata", "chart_spec")
    return not any(marker in serialized for marker in forbidden)


def _business_answer_is_not_generation_failure(result: dict) -> bool:
    return _business_answer_is_natural_product_answer(result)


def _business_answer_is_natural_product_answer(result: dict) -> bool:
    answer = result.get("business_answer") if isinstance(result.get("business_answer"), dict) else {}
    text = " ".join(
        [
            str(answer.get("headline") or ""),
            str(answer.get("direct_answer") or ""),
            str(answer.get("why") or ""),
        ]
    )
    forbidden = (
        "业务回答缺失",
        "业务回答生成失败",
        "没有可安全展示",
        "Business answer missing",
        "Answer generation failed",
        "no safe model-written business answer",
    )
    return bool(text.strip()) and any("\u4e00" <= char <= "\u9fff" for char in text) and not any(
        marker in text for marker in forbidden
    )
