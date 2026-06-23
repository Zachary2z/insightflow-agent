import os
import sqlite3
from pathlib import Path

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
    os.environ["INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER"] = "0"
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


def _trace_node(result: dict, node: str) -> dict:
    for event in result.get("trace", []):
        if event.get("node") == node:
            return event
    return {}


def _flatten_execution_values(result: dict) -> set[str]:
    values = set()
    for row in result.get("execution_result", {}).get("rows", []):
        for value in row:
            values.add(str(value))
    return values


def test_live_deepseek_analyzes_uploaded_workspace_data(tmp_path):
    _require_live_deepseek_workspace_flags()

    dataset_dir = tmp_path / "dataset"
    generate_general_business_dataset(dataset_dir, months=12)
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Live DeepSeek Workspace")
    workspace_db = Path(workspace["analysis_db_path"])
    import_csv(store, workspace["workspace_id"], dataset_dir / "orders.csv")
    import_csv(store, workspace["workspace_id"], dataset_dir / "customers.csv")
    import_csv(store, workspace["workspace_id"], dataset_dir / "marketing_spend.csv")
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    with sqlite3.connect(workspace_db) as conn:
        workspace_channels = {
            row[0]
            for row in conn.execute("SELECT DISTINCT channel FROM orders ORDER BY channel").fetchall()
        }

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question=(
            "以这份数据的最近 90 天为周期，收入最高的前 5 个获客渠道分别是谁？"
            "请给我一个可用于经营复盘的结论，并生成一张便于对比的图表。"
        ),
    )

    assert semantic_layer["metrics"]
    assert semantic_layer["dimensions"]
    assert result["status"] == "completed"
    assert result.get("initial_sql") in (None, "")
    assert result["database_schema"]["db_path"] == str(workspace_db)
    assert result["database_schema"]["db_path"].endswith("/analysis.db")
    assert "data/ecommerce.db" not in result["database_schema"]["db_path"]
    assert result["execution_result"]["success"] is True
    assert result["execution_result"]["row_count"] > 0
    assert result["review_result"]["approved"] is True
    assert result["generated_sql"]
    assert result["llm_sql_enhancement"]["accepted"] is True
    assert any(
        candidate["accepted"] and candidate["review_result"]["approved"]
        for candidate in result["llm_sql_enhancement"]["candidates"]
    )
    assert set(_flatten_execution_values(result)) & workspace_channels
    assert result["final_answer"].strip()
    assert any(str(value) in result["final_answer"] for value in _flatten_execution_values(result))
    assert result["question_understanding"]["provider_called"] is True
    assert result["question_understanding"]["source"] == "provider"
    assert result["sql_planning"]["provider_called"] is True
    assert result["sql_planning"]["source"] == "provider"
    assert result["sql_planning"]["strategy"] == "llm_candidate"
    assert result["llm_sql_enhancement"]["provider_called"] is True
    assert result["visualization_trace"]["provider_called"] is True
    assert result["visualization_trace"]["external_tool_called"] is True
    artifact_path = Path(result["visualization_trace"]["artifact_path"])
    run_dir = Path(result["workspace_run_dir"])
    assert artifact_path.exists()
    assert artifact_path.is_relative_to(run_dir)
    assert _provider_trace(result, "question_understanding_agent")
    assert _provider_trace(result, "sql_planning_router_agent")
    assert _provider_trace(result, "guarded_sql_candidate_agent")
    assert _provider_trace(result, "visualization_agent")
    assert _trace_node(result, "sql_reviewer_agent")
    assert _trace_node(result, "sql_executor_node")
    assert result.get("trace_path")
    assert Path(result["trace_path"]).exists()
    assert Path(result["trace_path"]).is_relative_to(run_dir)
