import sqlite3

from llm_ops.provider import MockLLMProvider
from workspaces.analysis_runner import run_workspace_analysis
from workspaces.profiler import profile_workspace_database
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


def test_workspace_analysis_uses_workspace_database_and_run_artifact_paths(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Analysis Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE orders (channel TEXT, revenue REAL)")
        conn.executemany("INSERT INTO orders VALUES (?, ?)", [("email", 100.0), ("paid_search", 200.0)])
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="按渠道汇总收入",
        initial_sql="SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel LIMIT 20",
        providers={
            "question_understanding": MockLLMProvider(
                {
                    "strategy": "llm_candidate",
                    "intent": {
                        "metric": "revenue",
                        "dimension": "channel",
                        "time_range": None,
                        "filters": [],
                        "operation": "comparison",
                        "limit": 20,
                    },
                    "missing_slots": [],
                    "clarification_questions": [],
                    "risk_flags": [],
                    "reason": "Clear workspace analysis question.",
                }
            )
        },
    )

    assert result["workspace_id"] == workspace["workspace_id"]
    assert result["execution_result"]["success"] is True
    assert result["trace_path"].startswith(str(tmp_path / "workspaces" / workspace["workspace_id"] / "runs"))
    assert result["final_answer"]
    assert result["product_result"]["workspace_id"] == workspace["workspace_id"]
    assert result["product_result"]["business_answer"]["headline"]
    assert result["product_result"]["technical_details"]["sql"] == result["generated_sql"]
    assert result["business_answer"] == result["product_result"]["business_answer"]
