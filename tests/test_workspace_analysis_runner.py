import sqlite3

from llm_ops.provider import MockLLMProvider
from workspaces.analysis_runner import run_workspace_analysis
from workspaces.profiler import profile_workspace_database
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


def _create_ecommerce_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Clarification Analysis Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE orders (id INTEGER, status TEXT)")
        conn.execute("CREATE TABLE order_items (order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price REAL)")
        conn.execute("CREATE TABLE products (id INTEGER, product_name TEXT)")
        conn.executemany("INSERT INTO orders VALUES (?, ?)", [(1, "paid"), (2, "paid")])
        conn.executemany("INSERT INTO products VALUES (?, ?)", [(1, "A"), (2, "B")])
        conn.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?)", [(1, 1, 2, 100.0), (2, 2, 1, 50.0)])
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace


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


def test_workspace_analysis_persists_pending_clarification_run(tmp_path):
    store, workspace = _create_ecommerce_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="帮我看看销售情况",
    )

    assert result["status"] == "waiting_for_clarification"
    assert result["pending_run_id"].startswith("pending_")
    thread = result["product_result"]["question_thread"]
    assert thread["status"] == "waiting_for_clarification"
    assert thread["original_question"] == "帮我看看销售情况"
    assert thread["clarification_question"]
    assert thread["pending_run_id"] == result["pending_run_id"]
    assert "generated_sql" not in result


def test_workspace_analysis_continuation_resolves_question_and_calls_workflow(tmp_path):
    from workspaces.analysis_runner import run_workspace_analysis_continuation

    store, workspace = _create_ecommerce_workspace(tmp_path)
    pending = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="帮我看看销售情况",
    )

    result = run_workspace_analysis_continuation(
        store=store,
        workspace_id=workspace["workspace_id"],
        pending_run_id=pending["pending_run_id"],
        clarification_answer="按商品，最近 90 天，看 Top 5",
    )

    assert result["status"] == "completed"
    assert result["execution_result"]["success"] is True
    assert result["generated_sql"].lower().startswith("select")
    trace_nodes = [event["node"] for event in result["trace"]]
    assert "sql_generator_agent" in trace_nodes
    assert "sql_reviewer_agent" in trace_nodes
    assert "sql_executor_node" in trace_nodes
    thread = result["product_result"]["question_thread"]
    assert thread["status"] == "completed"
    assert thread["original_question"] == "帮我看看销售情况"
    assert thread["clarification_answer"] == "按商品，最近 90 天，看 Top 5"
    assert "最近 90 天" in thread["resolved_question"]
    assert "商品" in thread["resolved_question"]
