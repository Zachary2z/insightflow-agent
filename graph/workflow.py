from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.question_understanding import run_question_understanding_agent
from agents.supervisor import initialize_run
from graph.nodes import (
    clarification_node,
    early_response_node,
    error_fix_node,
    fail_response_node,
    insight_node,
    metric_node,
    route_after_execute,
    route_after_fix,
    route_after_clarification,
    route_after_review,
    save_trace_node,
    schema_node,
    sql_executor_node,
    sql_generator_node,
    sql_reviewer_node,
)
from graph.state import AgentState
from llm_ops.provider import LLMProvider
from llm_ops.runtime_provider import build_clarification_provider, build_question_understanding_provider


def build_workflow(
    question_understanding_provider: LLMProvider | None = None,
    clarification_provider: LLMProvider | None = None,
):
    workflow = StateGraph(AgentState)
    workflow.add_node(
        "question_understanding",
        lambda state: run_question_understanding_agent(dict(state), provider=question_understanding_provider),
    )
    workflow.add_node(
        "clarification",
        lambda state: clarification_node(dict(state), provider=clarification_provider),
    )
    workflow.add_node("schema", schema_node)
    workflow.add_node("metric", metric_node)
    workflow.add_node("generate", sql_generator_node)
    workflow.add_node("review", sql_reviewer_node)
    workflow.add_node("execute", sql_executor_node)
    workflow.add_node("fix", error_fix_node)
    workflow.add_node("insight", insight_node)
    workflow.add_node("fail", fail_response_node)
    workflow.add_node("early_response", early_response_node)
    workflow.add_node("save_trace", save_trace_node)

    workflow.add_edge(START, "question_understanding")
    workflow.add_edge("question_understanding", "clarification")
    workflow.add_conditional_edges(
        "clarification",
        route_after_clarification,
        {"early_response": "early_response", "schema": "schema"},
    )
    workflow.add_edge("schema", "metric")
    workflow.add_edge("metric", "generate")
    workflow.add_edge("generate", "review")
    workflow.add_conditional_edges("review", route_after_review, {"execute": "execute", "fail": "fail"})
    workflow.add_conditional_edges("execute", route_after_execute, {"insight": "insight", "fix": "fix", "fail": "fail"})
    workflow.add_conditional_edges("fix", route_after_fix, {"review": "review", "fail": "fail"})
    workflow.add_edge("insight", "save_trace")
    workflow.add_edge("fail", "save_trace")
    workflow.add_edge("early_response", "save_trace")
    workflow.add_edge("save_trace", END)
    return workflow.compile()


def run_workflow(
    user_question: str,
    db_path: str | Path = "data/ecommerce.db",
    trace_dir: str | Path = "logs/traces",
    run_id: str | None = None,
    session_id: str | None = None,
    initial_sql: str | None = None,
    question_understanding_provider: LLMProvider | None = None,
    clarification_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    state = initialize_run(user_question, run_id=run_id, session_id=session_id)
    state["db_path"] = db_path
    state["trace_dir"] = trace_dir
    state["execution_result"] = {}
    state["review_retry_count"] = 0
    if initial_sql:
        state["initial_sql"] = initial_sql

    question_provider = question_understanding_provider or build_question_understanding_provider()
    clarify_provider = clarification_provider or build_clarification_provider()
    app = build_workflow(
        question_understanding_provider=question_provider,
        clarification_provider=clarify_provider,
    )
    return dict(app.invoke(state))
