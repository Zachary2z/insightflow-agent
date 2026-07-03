import os
from pathlib import Path

import pytest

from llm_ops.deepseek_provider import load_deepseek_config
from llm_ops.runtime_provider import (
    product_live_mode_enabled,
    provider_question_understanding_enabled,
    provider_sql_candidate_enabled,
    provider_sql_planning_enabled,
)
from workspaces.analysis_runner import run_workspace_analysis
from workspaces.importers import import_csv
from workspaces.profiler import profile_workspace_database
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


pytestmark = pytest.mark.skipif(
    os.getenv("INSIGHTFLOW_LIVE_DEEPSEEK_TESTS") != "1",
    reason="Live DeepSeek tests are opt-in.",
)


def _require_live_deepseek_p20() -> None:
    if not product_live_mode_enabled():
        pytest.skip("Set INSIGHTFLOW_PRODUCT_LIVE_MODE=1 for P20 live acceptance.")
    if not provider_question_understanding_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1.")
    if not provider_sql_planning_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1.")
    if not provider_sql_candidate_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1.")
    config = load_deepseek_config(require_api_key=True)
    if not config.success:
        pytest.skip("Set DEEPSEEK_API_KEY to run P20 live DeepSeek acceptance.")


def _prepare_store_sales_workspace(tmp_path: Path) -> tuple[WorkspaceStore, str]:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dataset_dir / "store_sales.csv"
    csv_path.write_text(
        "\n".join(
            [
                "store_name,business_date,city,sales_amount,gross_margin,satisfaction_score",
                "上海旗舰店,2026-04-01,上海,21500,0.37,4.8",
                "上海旗舰店,2026-05-01,上海,23800,0.39,4.7",
                "上海旗舰店,2026-06-01,上海,26255.44,0.41,4.8",
                "北京国贸店,2026-04-01,北京,17600,0.34,4.3",
                "北京国贸店,2026-05-01,北京,18100,0.35,4.4",
                "北京国贸店,2026-06-01,北京,18400,0.36,4.4",
                "深圳湾店,2026-04-01,深圳,11000,0.31,4.1",
                "深圳湾店,2026-05-01,深圳,11600,0.32,4.2",
                "深圳湾店,2026-06-01,深圳,12000,0.33,4.1",
            ]
        ),
        encoding="utf-8",
    )
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P20 Live DeepSeek Store Acceptance")
    import_csv(store, workspace["workspace_id"], csv_path)
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    assert profile["tables"]
    assert semantic_layer["metrics"]
    assert semantic_layer["dimensions"]
    return store, workspace["workspace_id"]


def _business_answer_text(result: dict) -> str:
    answer = result["product_result"]["business_answer"]
    return "\n".join(
        [
            answer["headline"],
            answer["direct_answer"],
            answer["why"],
            *answer["evidence_bullets"],
            *answer["recommendations"],
            *answer["caveats"],
        ]
    )


def test_live_deepseek_p20_store_analysis_uses_provider_chain_and_chinese_evidence(tmp_path):
    _require_live_deepseek_p20()
    store, workspace_id = _prepare_store_sales_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace_id,
        user_question="最近90天比较各门店销售额、毛利率和满意度，哪个门店最值得优先复盘？请给证据和风险边界。",
    )

    answer_text = _business_answer_text(result)
    assert result["status"] == "completed"
    assert result["question_understanding"]["provider_called"] is True
    assert result["question_understanding"]["source"] == "provider"
    assert result["sql_planning"]["provider_called"] is True
    assert result["sql_planning"]["source"] == "provider"
    assert result["execution_result"]["success"] is True
    assert result["execution_result"]["rows"]
    assert any("\u4e00" <= char <= "\u9fff" for char in answer_text)
    assert "SELECT " not in answer_text.upper()
    assert "provider_called" not in answer_text
    assert "参数" not in answer_text
    assert result["product_result"]["evidence"]["fact_payload"]["rows"] == result["execution_result"]["rows"]
