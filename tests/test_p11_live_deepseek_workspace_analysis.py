import os

import pytest

from llm_ops.deepseek_provider import load_deepseek_config
from llm_ops.runtime_provider import (
    provider_question_understanding_enabled,
    provider_sql_candidate_enabled,
    provider_sql_planning_enabled,
    provider_visualization_agent_enabled,
)
from workspaces.analysis_runner import run_workspace_analysis
from workspaces.importers import import_csv
from workspaces.profiler import profile_workspace_database
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore
from workspaces.synthetic_data import generate_general_business_dataset


pytestmark = pytest.mark.skipif(
    os.getenv("INSIGHTFLOW_LIVE_DEEPSEEK_TESTS") != "1",
    reason="Live DeepSeek tests are opt-in.",
)


def _require_live_deepseek_workspace_flags() -> None:
    config = load_deepseek_config(require_api_key=True)
    if not config.success:
        pytest.skip("Set DEEPSEEK_API_KEY to run the live P11 workspace acceptance test.")
    if not provider_question_understanding_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1.")
    if not provider_sql_planning_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1.")
    if not provider_sql_candidate_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1.")
    if not provider_visualization_agent_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1.")


def _provider_trace(result: dict, node: str) -> dict:
    for event in result.get("trace", []):
        if event.get("node") == node and event.get("provider_called") is True:
            return event
    return {}


def test_live_deepseek_analyzes_uploaded_workspace_data(tmp_path):
    _require_live_deepseek_workspace_flags()

    dataset_dir = tmp_path / "dataset"
    generate_general_business_dataset(dataset_dir, months=12)
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Live DeepSeek Workspace")
    import_csv(store, workspace["workspace_id"], dataset_dir / "orders.csv")
    import_csv(store, workspace["workspace_id"], dataset_dir / "customers.csv")
    import_csv(store, workspace["workspace_id"], dataset_dir / "marketing_spend.csv")
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question=(
            "使用 SQLite 的 orders 表，字段包含 order_id、order_date、customer_id、revenue、channel、status。"
            "请按 channel 分组，计算 SUM(revenue) AS total_revenue，按 total_revenue 降序返回前 5 个渠道。"
            "问题信息完整，不需要澄清。"
        ),
    )

    assert semantic_layer["metrics"]
    assert result["status"] == "completed"
    assert result["execution_result"]["success"] is True
    assert result["execution_result"]["row_count"] > 0
    assert result["review_result"]["approved"] is True
    assert result["question_understanding"]["provider_called"] is True
    assert result["sql_planning"]["provider_called"] is True
    assert result["sql_planning"]["strategy"] == "llm_candidate"
    assert result["llm_sql_enhancement"]["provider_called"] is True
    assert result["visualization_trace"]["provider_called"] is True
    assert _provider_trace(result, "question_understanding_agent")
    assert _provider_trace(result, "sql_planning_router_agent")
    assert _provider_trace(result, "guarded_sql_candidate_agent")
    assert _provider_trace(result, "visualization_agent")
    assert result.get("trace_path")
    assert result.get("workspace_run_dir")
