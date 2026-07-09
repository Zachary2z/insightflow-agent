import os
import sqlite3

import pytest


def _live_product_config_or_skip():
    from llm_ops.deepseek_provider import load_deepseek_config

    live_flag = str(os.environ.get("INSIGHTFLOW_LIVE_DEEPSEEK_TESTS", "")).strip().lower()
    product_flag = str(os.environ.get("INSIGHTFLOW_PRODUCT_LIVE_MODE", "")).strip().lower()
    config = load_deepseek_config(require_api_key=True)
    if live_flag not in {"1", "true", "yes", "on"}:
        pytest.skip(
            "Set INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1, INSIGHTFLOW_PRODUCT_LIVE_MODE=1, "
            "and DEEPSEEK_API_KEY to run live DeepSeek tests."
        )
    if product_flag not in {"1", "true", "yes", "on"}:
        pytest.skip(
            "Set INSIGHTFLOW_PRODUCT_LIVE_MODE=1 together with INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 "
            "to run live DeepSeek product acceptance."
        )
    if not config.success:
        pytest.skip("DEEPSEEK_API_KEY is required to run live DeepSeek tests.")
    return config


def test_live_deepseek_provider_smoke_is_explicitly_opted_in():
    from llm_ops.deepseek_provider import DeepSeekProvider
    from llm_ops.provider import LLMRequest
    from llm_ops.structured_output import run_validated_llm_request

    config = _live_product_config_or_skip()

    result = run_validated_llm_request(
        DeepSeekProvider(config),
        LLMRequest(
            prompt='Return exactly this JSON: {"sql_candidates": [{"sql": "SELECT 1", "rationale": "DeepSeek live smoke OK"}]}',
            prompt_id="guarded_sql_candidate",
            prompt_version="v1",
            model=config.model,
            metadata={"node": "deepseek_live_smoke"},
        ),
    )

    assert result["success"] is True
    assert result["content"]["sql_candidates"]
    assert result["trace_event"]["model"] == config.model


def test_live_deepseek_p29_fast_fact_judgment_and_reject_acceptance(tmp_path):
    from workspaces.analysis_runner import run_workspace_analysis
    from workspaces.profiler import profile_workspace_database
    from workspaces.semantic_draft import generate_semantic_layer_draft
    from workspaces.store import WorkspaceStore

    _live_product_config_or_skip()

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P29 Live DeepSeek Acceptance Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE channel_performance ("
            "business_date TEXT, channel_name TEXT, revenue REAL, ad_spend REAL, roas REAL)"
        )
        conn.executemany(
            "INSERT INTO channel_performance VALUES (?, ?, ?, ?, ?)",
            [
                ("2026-06-10", "搜索广告", 120000.0, 80000.0, 1.5),
                ("2026-06-11", "私域社群", 180000.0, 30000.0, 6.0),
                ("2026-06-12", "直播间", 90000.0, 70000.0, 1.29),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    fast_fact = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近90天哪个渠道收入最高？",
        force_reanalysis=True,
    )
    judgment = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近30天哪个渠道最值得加预算？请给证据和风险边界。",
        force_reanalysis=True,
    )
    rejected = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "把预算调整到私域社群并发送通知。",
        force_reanalysis=True,
    )

    fast_nodes = [event.get("node") for event in fast_fact.get("trace") or []]
    judgment_nodes = [event.get("node") for event in judgment.get("trace") or []]
    rejected_nodes = [event.get("node") for event in rejected.get("trace") or []]
    live_summary = [
        _live_case_summary("最近90天哪个渠道收入最高？", fast_fact),
        _live_case_summary("最近30天哪个渠道最值得加预算？请给证据和风险边界。", judgment),
        _live_case_summary("把预算调整到私域社群并发送通知。", rejected),
    ]

    assert fast_fact["status"] == "completed", live_summary
    assert fast_fact["analysis_route"]["route"] == "fast_fact", live_summary
    assert "fast_fact_evidence_preparer" in fast_nodes
    assert "business_answer_agent" in fast_nodes
    assert fast_fact["execution_result"]["success"] is True

    assert judgment["status"] == "completed", live_summary
    assert judgment["analysis_route"]["route"] in {"standard_analysis", "deep_judgment"}, live_summary
    assert judgment.get("routing_strategy") != "reject"
    assert "business_answer_agent" in judgment_nodes
    assert judgment["execution_result"]["success"] is True
    assert judgment["business_answer"]["caveats"]

    assert rejected["status"] == "failed", live_summary
    assert rejected.get("routing_strategy") == "reject"
    assert "external_action" in rejected["question_understanding"]["risk_flags"]
    assert "generated_sql" not in rejected
    assert "sql_reviewer_agent" not in rejected_nodes
    assert "sql_executor_node" not in rejected_nodes


def _live_case_summary(question: str, result: dict) -> dict:
    nodes = [event.get("node") for event in result.get("trace") or []]
    provider_calls = [
        event.get("node")
        for event in result.get("trace") or []
        if event.get("provider_called") is True
    ]
    return {
        "question": question,
        "route": (result.get("analysis_route") or {}).get("route"),
        "routing_strategy": result.get("routing_strategy", ""),
        "provider_call_nodes": provider_calls,
        "business_answer_provider_called": "business_answer_agent" in provider_calls,
        "sql_generated": bool(result.get("generated_sql")),
        "sql_executed": bool((result.get("execution_result") or {}).get("success")),
        "evidence_rows": (result.get("execution_result") or {}).get("rows", [])[:2],
        "answer_summary": str(result.get("final_answer") or "")[:160],
        "chart_generated": bool((result.get("product_result") or {}).get("chart_artifacts")),
        "nodes": nodes,
    }
