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
    fast_fact_node,
    guarded_sql_candidate_node,
    insight_node,
    metric_node,
    route_after_metric,
    route_after_execute,
    route_after_fix,
    route_after_clarification,
    route_after_sql_planning,
    route_after_review,
    route_after_schema_repair,
    save_trace_node,
    schema_node,
    schema_repair_node,
    sql_planning_node,
    sql_executor_node,
    sql_generator_node,
    sql_reviewer_node,
    visualization_agent_node,
)
from graph.state import AgentState
from llm_ops.provider import LLMProvider
from llm_ops.runtime_provider import (
    build_analysis_planner_provider,
    build_answer_reviewer_provider,
    build_clarification_provider,
    build_final_answer_composer_provider,
    build_claim_typing_provider,
    build_insight_drafting_provider,
    build_question_understanding_provider,
    build_visualization_agent_provider,
    build_sql_candidate_provider,
    build_sql_planning_provider,
)


def build_workflow(
    question_understanding_provider: LLMProvider | None = None,
    clarification_provider: LLMProvider | None = None,
    sql_planning_provider: LLMProvider | None = None,
    analysis_planner_provider: LLMProvider | None = None,
    visualization_agent_provider: LLMProvider | None = None,
    sql_candidate_provider: LLMProvider | None = None,
    insight_drafting_provider: LLMProvider | None = None,
    answer_reviewer_provider: LLMProvider | None = None,
    final_answer_composer_provider: LLMProvider | None = None,
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
    workflow.add_node(
        "schema_repair",
        lambda state: schema_repair_node(dict(state), provider=sql_candidate_provider),
    )
    workflow.add_node("execute", sql_executor_node)
    workflow.add_node("fast_fact", fast_fact_node)
    workflow.add_node("fix", error_fix_node)
    workflow.add_node(
        "insight",
        lambda state: insight_node(
            dict(state),
            provider=insight_drafting_provider,
            answer_reviewer_provider=answer_reviewer_provider,
            final_answer_composer_provider=final_answer_composer_provider,
        ),
    )
    workflow.add_node(
        "claim_typing",
        lambda state: claim_typing_node(dict(state), provider=claim_typing_provider),
    )
    workflow.add_node(
        "visualization_agent",
        lambda state: visualization_agent_node(dict(state), provider=visualization_agent_provider),
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
    workflow.add_conditional_edges(
        "metric",
        route_after_metric,
        {"guarded_candidate": "guarded_candidate", "generate": "generate"},
    )
    workflow.add_edge("generate", "guarded_candidate")
    workflow.add_edge("guarded_candidate", "review")
    workflow.add_conditional_edges(
        "review",
        route_after_review,
        {"execute": "execute", "schema_repair": "schema_repair", "fail": "fail"},
    )
    workflow.add_conditional_edges("schema_repair", route_after_schema_repair, {"review": "review", "fail": "fail"})
    workflow.add_conditional_edges(
        "execute",
        route_after_execute,
        {"insight": "insight", "fast_fact": "fast_fact", "fix": "fix", "fail": "fail"},
    )
    workflow.add_conditional_edges("fix", route_after_fix, {"review": "review", "fail": "fail"})
    workflow.add_edge("fast_fact", "save_trace")
    workflow.add_edge("insight", "claim_typing")
    workflow.add_edge("claim_typing", "visualization_agent")
    workflow.add_edge("visualization_agent", "save_trace")
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
    original_question: str | None = None,
    clarification_question: str | None = None,
    clarification_answer: str | None = None,
    resolved_question: str | None = None,
    pending_run_id: str | None = None,
    stop_for_clarification: bool = False,
    workspace_id: str | None = None,
    workspace_root: str | Path | None = None,
    profile_path: str | Path | None = None,
    semantic_layer_path: str | Path | None = None,
    run_artifact_dir: str | Path | None = None,
    question_understanding_provider: LLMProvider | None = None,
    clarification_provider: LLMProvider | None = None,
    sql_planning_provider: LLMProvider | None = None,
    analysis_planner_provider: LLMProvider | None = None,
    visualization_agent_provider: LLMProvider | None = None,
    sql_candidate_provider: LLMProvider | None = None,
    insight_drafting_provider: LLMProvider | None = None,
    answer_reviewer_provider: LLMProvider | None = None,
    final_answer_composer_provider: LLMProvider | None = None,
    claim_typing_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    state = initialize_run(user_question, run_id=run_id, session_id=session_id)
    state["original_question"] = original_question or user_question
    state["clarification_question"] = clarification_question or ""
    state["clarification_answer"] = clarification_answer or ""
    state["resolved_question"] = resolved_question or ""
    state["pending_run_id"] = pending_run_id or ""
    state["question_thread_status"] = ""
    state["stop_for_clarification"] = stop_for_clarification
    state["db_path"] = db_path
    state["trace_dir"] = trace_dir
    state["execution_result"] = {}
    state["review_retry_count"] = 0
    state["schema_repair_attempted"] = False
    state["schema_repair_succeeded"] = False
    state["schema_repair_reason"] = ""
    state["schema_repair"] = {}
    state["schema_repair_pending_review"] = False
    state["workspace_id"] = workspace_id
    state["workspace_root"] = str(workspace_root) if workspace_root else None
    state["profile_path"] = str(profile_path) if profile_path else None
    state["semantic_layer_path"] = str(semantic_layer_path) if semantic_layer_path else None
    state["run_artifact_dir"] = str(run_artifact_dir) if run_artifact_dir else None
    if initial_sql:
        state["initial_sql"] = initial_sql

    question_provider = question_understanding_provider or build_question_understanding_provider()
    clarify_provider = clarification_provider or build_clarification_provider()
    planning_provider = sql_planning_provider or build_sql_planning_provider()
    planner_provider = analysis_planner_provider or build_analysis_planner_provider()
    viz_provider = visualization_agent_provider or build_visualization_agent_provider()
    candidate_provider = sql_candidate_provider or build_sql_candidate_provider()
    insight_provider = insight_drafting_provider or build_insight_drafting_provider()
    reviewer_provider = answer_reviewer_provider or build_answer_reviewer_provider()
    composer_provider = final_answer_composer_provider or build_final_answer_composer_provider()
    typing_provider = claim_typing_provider or build_claim_typing_provider()
    app = build_workflow(
        question_understanding_provider=question_provider,
        clarification_provider=clarify_provider,
        sql_planning_provider=planning_provider,
        analysis_planner_provider=planner_provider,
        visualization_agent_provider=viz_provider,
        sql_candidate_provider=candidate_provider,
        insight_drafting_provider=insight_provider,
        answer_reviewer_provider=reviewer_provider,
        final_answer_composer_provider=composer_provider,
        claim_typing_provider=typing_provider,
    )
    return dict(app.invoke(state))
