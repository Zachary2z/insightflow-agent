from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.question_understanding import run_question_understanding_agent
from agents.supervisor import initialize_run
from graph.nodes import (
    analysis_planner_node,
    clarification_node,
    claim_typing_node,
    early_response_node,
    error_fix_node,
    fail_response_node,
    guarded_sql_candidate_node,
    insight_node,
    metric_node,
    route_after_execute,
    route_after_fix,
    route_after_clarification,
    route_after_sql_planning,
    route_after_review,
    save_trace_node,
    schema_node,
    sql_planning_node,
    sql_executor_node,
    sql_generator_node,
    sql_reviewer_node,
    visualization_planner_node,
)
from graph.state import AgentState
from llm_ops.provider import LLMProvider
from llm_ops.runtime_provider import (
    build_analysis_planner_provider,
    build_clarification_provider,
    build_claim_typing_provider,
    build_question_understanding_provider,
    build_visualization_planner_provider,
    build_sql_candidate_provider,
    build_sql_planning_provider,
)


def build_workflow(
    question_understanding_provider: LLMProvider | None = None,
    clarification_provider: LLMProvider | None = None,
    sql_planning_provider: LLMProvider | None = None,
    analysis_planner_provider: LLMProvider | None = None,
    visualization_planner_provider: LLMProvider | None = None,
    sql_candidate_provider: LLMProvider | None = None,
    claim_typing_provider: LLMProvider | None = None,
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
    workflow.add_node(
        "sql_planning",
        lambda state: sql_planning_node(dict(state), provider=sql_planning_provider),
    )
    workflow.add_node(
        "analysis_planner",
        lambda state: analysis_planner_node(dict(state), provider=analysis_planner_provider),
    )
    workflow.add_node("schema", schema_node)
    workflow.add_node("metric", metric_node)
    workflow.add_node("generate", sql_generator_node)
    workflow.add_node(
        "guarded_candidate",
        lambda state: guarded_sql_candidate_node(dict(state), provider=sql_candidate_provider),
    )
    workflow.add_node("review", sql_reviewer_node)
    workflow.add_node("execute", sql_executor_node)
    workflow.add_node("fix", error_fix_node)
    workflow.add_node("insight", insight_node)
    workflow.add_node(
        "claim_typing",
        lambda state: claim_typing_node(dict(state), provider=claim_typing_provider),
    )
    workflow.add_node(
        "visualization_planner",
        lambda state: visualization_planner_node(dict(state), provider=visualization_planner_provider),
    )
    workflow.add_node("fail", fail_response_node)
    workflow.add_node("early_response", early_response_node)
    workflow.add_node("save_trace", save_trace_node)

    workflow.add_edge(START, "question_understanding")
    workflow.add_edge("question_understanding", "clarification")
    workflow.add_conditional_edges(
        "clarification",
        route_after_clarification,
        {"early_response": "early_response", "schema": "sql_planning"},
    )
    workflow.add_conditional_edges(
        "sql_planning",
        route_after_sql_planning,
        {"early_response": "early_response", "schema": "analysis_planner"},
    )
    workflow.add_edge("analysis_planner", "schema")
    workflow.add_edge("schema", "metric")
    workflow.add_edge("metric", "generate")
    workflow.add_edge("generate", "guarded_candidate")
    workflow.add_edge("guarded_candidate", "review")
    workflow.add_conditional_edges("review", route_after_review, {"execute": "execute", "fail": "fail"})
    workflow.add_conditional_edges("execute", route_after_execute, {"insight": "insight", "fix": "fix", "fail": "fail"})
    workflow.add_conditional_edges("fix", route_after_fix, {"review": "review", "fail": "fail"})
    workflow.add_edge("insight", "claim_typing")
    workflow.add_edge("claim_typing", "visualization_planner")
    workflow.add_edge("visualization_planner", "save_trace")
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
    sql_planning_provider: LLMProvider | None = None,
    analysis_planner_provider: LLMProvider | None = None,
    visualization_planner_provider: LLMProvider | None = None,
    sql_candidate_provider: LLMProvider | None = None,
    claim_typing_provider: LLMProvider | None = None,
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
    planning_provider = sql_planning_provider or build_sql_planning_provider()
    planner_provider = analysis_planner_provider or build_analysis_planner_provider()
    viz_provider = visualization_planner_provider or build_visualization_planner_provider()
    candidate_provider = sql_candidate_provider or build_sql_candidate_provider()
    typing_provider = claim_typing_provider or build_claim_typing_provider()
    app = build_workflow(
        question_understanding_provider=question_provider,
        clarification_provider=clarify_provider,
        sql_planning_provider=planning_provider,
        analysis_planner_provider=planner_provider,
        visualization_planner_provider=viz_provider,
        sql_candidate_provider=candidate_provider,
        claim_typing_provider=typing_provider,
    )
    return dict(app.invoke(state))
