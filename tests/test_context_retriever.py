from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _base_state():
    from agents.supervisor import initialize_run

    return initialize_run(
        "最近 30 天销售额最高的 5 个商品是什么？",
        run_id="run_context_test",
        session_id="session_context_test",
    )


def test_context_retriever_agent_writes_business_context_and_trace():
    from agents.context_retriever import run_context_retriever_agent

    state = run_context_retriever_agent(_base_state())

    assert state["business_context"]["success"] is True
    assert state["business_context"]["matched_rules"]
    assert state["business_context"]["matched_table_docs"]
    assert state["business_context"]["matched_sql_examples"]
    assert state["trace"][-1]["node"] == "context_retriever_agent"
    assert state["trace"][-1]["tool_name"] == "retrieve_business_context"
    assert state["trace"][-1]["status"] == "success"


def test_context_retriever_agent_handles_tool_failure_without_crashing(tmp_path):
    from agents.context_retriever import run_context_retriever_agent

    state = run_context_retriever_agent(
        _base_state(),
        context_paths={
            "business_rules": tmp_path / "missing_rules.md",
            "table_docs": ROOT / "data" / "table_docs.md",
            "sql_examples": ROOT / "data" / "sql_examples.json",
        },
    )

    assert state["business_context"]["success"] is False
    assert "missing_rules.md" in state["business_context"]["error"]
    assert state["trace"][-1]["node"] == "context_retriever_agent"
    assert state["trace"][-1]["status"] == "error"
