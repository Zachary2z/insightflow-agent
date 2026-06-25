import os
from datetime import date, timedelta
from pathlib import Path

import pytest

from llm_ops.deepseek_provider import load_deepseek_config
from llm_ops.runtime_provider import product_live_mode_enabled
from workspaces.analysis_runner import run_workspace_analysis, run_workspace_analysis_continuation
from workspaces.importers import import_csv
from workspaces.profiler import profile_workspace_database
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


def _require_live_deepseek() -> None:
    if os.getenv("INSIGHTFLOW_LIVE_DEEPSEEK_TESTS") != "1":
        pytest.skip("Live DeepSeek tests are opt-in.")
    if not product_live_mode_enabled():
        pytest.skip("Set INSIGHTFLOW_PRODUCT_LIVE_MODE=1 for product live acceptance.")
    config = load_deepseek_config(require_api_key=True)
    if not config.success:
        pytest.skip("Set DEEPSEEK_API_KEY to run the live P13 product acceptance test.")


def _prepared_business_workspace(tmp_path: Path) -> tuple[WorkspaceStore, str, dict, dict]:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    channels = {
        "paid_search": {"daily_revenue": 1450, "daily_spend": 310, "customers": ["c_001", "c_002", "c_003"]},
        "email": {"daily_revenue": 980, "daily_spend": 90, "customers": ["c_004", "c_005"]},
        "social": {"daily_revenue": 760, "daily_spend": 240, "customers": ["c_006", "c_007"]},
        "affiliate": {"daily_revenue": 520, "daily_spend": 170, "customers": ["c_008", "c_009"]},
    }

    customer_rows = [
        "customer_id,segment,city,signup_date",
        "c_001,enterprise,Shanghai,2025-08-01",
        "c_002,mid_market,Beijing,2025-09-15",
        "c_003,consumer,Shenzhen,2025-11-20",
        "c_004,enterprise,Hangzhou,2025-10-11",
        "c_005,consumer,Chengdu,2025-12-04",
        "c_006,mid_market,Guangzhou,2025-07-19",
        "c_007,consumer,Nanjing,2026-01-05",
        "c_008,mid_market,Suzhou,2025-06-24",
        "c_009,consumer,Wuhan,2026-02-18",
    ]
    order_rows = ["order_id,customer_id,channel,order_date,revenue"]
    spend_rows = ["spend_id,channel,spend_date,spend"]
    order_id = 1
    spend_id = 1
    for offset in range(0, 120, 5):
        current_day = today - timedelta(days=offset)
        recency_factor = 1.25 if offset < 90 else 0.55
        for channel, config in channels.items():
            customer = config["customers"][offset % len(config["customers"])]
            revenue = round(config["daily_revenue"] * recency_factor + (offset % 4) * 35, 2)
            spend = round(config["daily_spend"] * recency_factor + (offset % 3) * 12, 2)
            order_rows.append(f"o_{order_id:04d},{customer},{channel},{current_day.isoformat()},{revenue}")
            spend_rows.append(f"s_{spend_id:04d},{channel},{current_day.isoformat()},{spend}")
            order_id += 1
            spend_id += 1

    (dataset_dir / "orders.csv").write_text("\n".join(order_rows), encoding="utf-8")
    (dataset_dir / "marketing_spend.csv").write_text("\n".join(spend_rows), encoding="utf-8")
    (dataset_dir / "customers.csv").write_text("\n".join(customer_rows), encoding="utf-8")

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P13 Live DeepSeek Product Acceptance")
    workspace_id = workspace["workspace_id"]
    import_csv(store, workspace_id, dataset_dir / "orders.csv")
    import_csv(store, workspace_id, dataset_dir / "marketing_spend.csv")
    import_csv(store, workspace_id, dataset_dir / "customers.csv")
    profile = profile_workspace_database(store, workspace_id)
    semantic_layer = generate_semantic_layer_draft(store, workspace_id, profile)
    return store, workspace_id, profile, semantic_layer


def _assert_business_answer_readable(answer: dict) -> None:
    headline = str(answer.get("headline") or "").strip()
    summary = str(answer.get("summary") or "").strip()
    combined = f"{headline}\n{summary}"

    assert len(headline) >= 8
    assert len(summary) >= 40
    assert "channel=" not in combined
    assert "revenue=" not in combined
    assert "order_count=" not in combined
    assert not summary.lstrip().startswith("1.")
    assert "SELECT " not in combined.upper()
    assert answer.get("confidence")
    assert (
        "建议" in combined
        or answer.get("next_actions")
        or answer.get("recommendations")
    )


def _assert_provider_chain(result: dict) -> None:
    assert result["question_understanding"]["provider_called"] is True
    assert result["sql_planning"]["provider_called"] is True
    assert result["llm_sql_enhancement"]["provider_called"] is True
    assert result["insight"]["provider_called"] is True
    assert result["visualization_trace"]["provider_called"] is True
    assert result["execution_result"]["success"] is True
    assert result["generated_sql"].strip()
    assert result.get("product_result")


def test_live_deepseek_product_analysis_completes_with_business_answer_and_chart(tmp_path):
    _require_live_deepseek()
    store, workspace_id, profile, semantic_layer = _prepared_business_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace_id,
        user_question="分析最近 90 天各渠道收入、投放成本和 ROI，告诉我哪个渠道应该加预算，并生成图表。",
    )

    product_result = result["product_result"]
    assert profile["tables"]
    assert semantic_layer["metrics"]
    assert result["status"] == "completed"
    _assert_provider_chain(result)
    _assert_business_answer_readable(product_result["business_answer"])
    assert product_result["evidence"]["table_preview"]["rows"]
    assert product_result["chart_artifacts"]
    assert product_result["chart_artifacts"][0]["url"].startswith("/api/workspaces/")
    assert product_result["technical_details"]["sql"].strip()
    answer_text = (
        f"{product_result['business_answer']['headline']}\n"
        f"{product_result['business_answer']['summary']}"
    )
    assert "SELECT " not in answer_text.upper()


def test_live_deepseek_clarification_continuation_completes_product_flow(tmp_path):
    _require_live_deepseek()
    store, workspace_id, _, _ = _prepared_business_workspace(tmp_path)

    first_result = run_workspace_analysis(
        store=store,
        workspace_id=workspace_id,
        user_question="帮我分析渠道表现",
    )

    first_thread = first_result["product_result"]["question_thread"]
    assert first_result["status"] == "waiting_for_clarification"
    assert first_thread["pending_run_id"]
    assert first_thread["clarification_question"]

    continuation = run_workspace_analysis_continuation(
        store=store,
        workspace_id=workspace_id,
        pending_run_id=first_thread["pending_run_id"],
        clarification_answer="最近 90 天，按渠道比较收入、投放成本和 ROI，并给出预算建议。",
    )

    thread = continuation["product_result"]["question_thread"]
    resolved_question = thread["resolved_question"]
    assert continuation["status"] == "completed"
    assert thread["original_question"] == "帮我分析渠道表现"
    assert thread["clarification_answer"] == "最近 90 天，按渠道比较收入、投放成本和 ROI，并给出预算建议。"
    assert resolved_question
    assert "最近 90 天" in resolved_question
    assert "渠道" in resolved_question
    assert "ROI" in resolved_question or "roi" in resolved_question.lower()
    _assert_business_answer_readable(continuation["product_result"]["business_answer"])
    _assert_provider_chain(continuation)


def test_product_live_mode_no_key_still_runs_deterministic_sql_path(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_PRODUCT_LIVE_MODE", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    store, workspace_id, _, _ = _prepared_business_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace_id,
        user_question="用已给 SQL 汇总最近渠道收入。",
        initial_sql=(
            "SELECT channel, SUM(revenue) AS revenue "
            "FROM orders "
            "GROUP BY channel "
            "ORDER BY revenue DESC"
        ),
    )

    assert result["execution_result"]["success"] is True
    assert result["product_result"]
    assert result["product_result"]["evidence"]["table_preview"]["rows"]
