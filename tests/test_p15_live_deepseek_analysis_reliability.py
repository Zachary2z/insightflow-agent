import os
from datetime import date, timedelta
from pathlib import Path

import pytest

from llm_ops.deepseek_provider import load_deepseek_config
from llm_ops.runtime_provider import (
    product_live_mode_enabled,
    provider_insight_drafting_enabled,
    provider_question_understanding_enabled,
    provider_sql_candidate_enabled,
    provider_sql_planning_enabled,
)
from workspaces.analysis_runner import run_workspace_analysis, run_workspace_analysis_continuation
from workspaces.importers import import_csv
from workspaces.profiler import profile_workspace_database
from workspaces.run_store import WorkspaceRunStore
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


ORIGINAL_QUESTION = "给我一下最近30天几个渠道的数据"
CLARIFICATION_ANSWER = "都看"
RAW_SQL_REVIEW_MARKERS = ("Unknown table", "Unknown column")
STALE_ECOMMERCE_SQL_TERMS = ("products", "order_items", "product_name", "quantity * unit_price")


def _require_live_deepseek() -> None:
    if os.getenv("INSIGHTFLOW_LIVE_DEEPSEEK_TESTS") != "1":
        pytest.skip("Live DeepSeek tests are opt-in.")
    if not product_live_mode_enabled():
        pytest.skip("Set INSIGHTFLOW_PRODUCT_LIVE_MODE=1 for P15 product live regression.")
    if not provider_question_understanding_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1.")
    if not provider_sql_planning_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1.")
    if not provider_sql_candidate_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1.")
    if not provider_insight_drafting_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING=1.")
    config = load_deepseek_config(require_api_key=True)
    if not config.success:
        pytest.skip("Set DEEPSEEK_API_KEY to run the live P15 DeepSeek regression.")


def _prepared_channel_workspace(tmp_path: Path) -> tuple[WorkspaceStore, str]:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    channels = {
        "paid_search": {"daily_revenue": 1480, "daily_spend": 320, "customers": ["c_001", "c_002", "c_003"]},
        "email": {"daily_revenue": 940, "daily_spend": 85, "customers": ["c_004", "c_005"]},
        "social": {"daily_revenue": 790, "daily_spend": 235, "customers": ["c_006", "c_007"]},
        "affiliate": {"daily_revenue": 560, "daily_spend": 165, "customers": ["c_008", "c_009"]},
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
    for offset in range(0, 60, 3):
        current_day = today - timedelta(days=offset)
        recency_factor = 1.15 if offset < 30 else 0.72
        for channel, config in channels.items():
            customer = config["customers"][offset % len(config["customers"])]
            revenue = round(config["daily_revenue"] * recency_factor + (offset % 5) * 27, 2)
            spend = round(config["daily_spend"] * recency_factor + (offset % 4) * 11, 2)
            order_rows.append(f"o_{order_id:04d},{customer},{channel},{current_day.isoformat()},{revenue}")
            spend_rows.append(f"s_{spend_id:04d},{channel},{current_day.isoformat()},{spend}")
            order_id += 1
            spend_id += 1

    (dataset_dir / "orders.csv").write_text("\n".join(order_rows), encoding="utf-8")
    (dataset_dir / "marketing_spend.csv").write_text("\n".join(spend_rows), encoding="utf-8")
    (dataset_dir / "customers.csv").write_text("\n".join(customer_rows), encoding="utf-8")

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P15 Live DeepSeek Reliability")
    workspace_id = workspace["workspace_id"]
    import_csv(store, workspace_id, dataset_dir / "orders.csv")
    import_csv(store, workspace_id, dataset_dir / "marketing_spend.csv")
    import_csv(store, workspace_id, dataset_dir / "customers.csv")
    profile = profile_workspace_database(store, workspace_id)
    semantic_layer = generate_semantic_layer_draft(store, workspace_id, profile)
    assert {table["table_name"] for table in profile["tables"]} >= {"orders", "marketing_spend", "customers"}
    assert semantic_layer["metrics"]
    return store, workspace_id


def _combined_answer(product_result: dict) -> str:
    answer = product_result.get("business_answer") or {}
    return f"{answer.get('headline') or ''}\n{answer.get('direct_answer') or ''}"


def _assert_no_raw_reviewer_wall(text: str) -> None:
    assert not any(marker in text for marker in RAW_SQL_REVIEW_MARKERS)


def _assert_provider_product_path(result: dict) -> None:
    assert result["question_understanding"]["provider_called"] is True
    if result.get("status") == "waiting_for_clarification":
        assert result["clarification_result"]["provider_called"] is True
        return
    assert result["sql_planning"]["provider_called"] is True
    if result.get("llm_sql_enhancement"):
        assert result["llm_sql_enhancement"]["provider_called"] is True
    if result.get("insight"):
        assert result["insight"]["provider_called"] is True


def _assert_completed_product_result(result: dict, *, continued: bool) -> None:
    product_result = result["product_result"]
    answer_text = _combined_answer(product_result)
    thread = product_result["question_thread"]

    assert result["status"] == "completed"
    assert len(answer_text.strip()) >= 30
    assert any("\u4e00" <= char <= "\u9fff" for char in answer_text)
    assert "SELECT " not in answer_text.upper()
    _assert_no_raw_reviewer_wall(answer_text)
    assert product_result["evidence"]["table_preview"]["rows"]
    assert thread["original_question"] == ORIGINAL_QUESTION
    assert "original_question" in thread
    assert "clarification_answer" in thread
    assert "resolved_question" in thread
    if continued:
        assert thread["clarification_answer"] == CLARIFICATION_ANSWER
        assert ORIGINAL_QUESTION in thread["resolved_question"]
        assert CLARIFICATION_ANSWER in thread["resolved_question"]

    sql = str(result.get("generated_sql") or "")
    lowered_sql = sql.lower()
    assert sql.strip()
    assert not any(term in lowered_sql for term in STALE_ECOMMERCE_SQL_TERMS)


def _assert_failed_product_result(result: dict) -> None:
    product_result = result["product_result"]
    answer_text = _combined_answer(product_result)

    assert result["status"] == "failed"
    assert "不存在的表或字段" in answer_text or "未能安全执行" in answer_text
    _assert_no_raw_reviewer_wall(answer_text)
    assert "SELECT " not in answer_text.upper()
    assert product_result["technical_details"]["validation_logs"]


def test_live_deepseek_p15_clarification_answer_continues_and_history_restores_product_result(tmp_path):
    _require_live_deepseek()
    store, workspace_id = _prepared_channel_workspace(tmp_path)
    run_store = WorkspaceRunStore(store)

    first_result = run_workspace_analysis(
        store=store,
        workspace_id=workspace_id,
        user_question=ORIGINAL_QUESTION,
    )
    _assert_provider_product_path(first_result)

    first_history = run_store.list_runs(workspace_id)
    assert any(run["run_id"] == first_result["run_id"] for run in first_history)
    assert any(run["question"] == ORIGINAL_QUESTION for run in first_history)
    first_detail = run_store.load_run_response(workspace_id, first_result["run_id"])
    assert first_detail["product_result"]["question_thread"]["original_question"] == ORIGINAL_QUESTION

    continued = first_result["status"] == "waiting_for_clarification"
    if continued:
        first_thread = first_result["product_result"]["question_thread"]
        assert first_thread["pending_run_id"]
        assert first_thread["clarification_question"]
        assert any(run["status"] == "waiting_for_clarification" for run in first_history)
        final_result = run_workspace_analysis_continuation(
            store=store,
            workspace_id=workspace_id,
            pending_run_id=first_thread["pending_run_id"],
            clarification_answer=CLARIFICATION_ANSWER,
        )
        _assert_provider_product_path(final_result)
    else:
        final_result = first_result

    assert final_result["status"] in {"completed", "failed"}
    if final_result["status"] == "completed":
        _assert_completed_product_result(final_result, continued=continued)
    else:
        _assert_failed_product_result(final_result)

    history = run_store.list_runs(workspace_id)
    statuses = {run["status"] for run in history}
    assert final_result["status"] in statuses
    assert any(run["run_id"] == final_result["run_id"] for run in history)
    assert any(run["question"] == ORIGINAL_QUESTION for run in history)

    detail = run_store.load_run_response(workspace_id, final_result["run_id"])
    assert detail["product_result"]["status"] == final_result["product_result"]["status"]
    assert detail["product_result"]["business_answer"] == final_result["product_result"]["business_answer"]
    assert detail["product_result"]["question_thread"]["original_question"] == ORIGINAL_QUESTION
    if final_result["status"] == "completed":
        assert detail["product_result"]["evidence"]["table_preview"]["rows"]
    if continued:
        assert detail["product_result"]["question_thread"]["clarification_answer"] == CLARIFICATION_ANSWER
