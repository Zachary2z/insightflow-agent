from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.analysis_planner import run_analysis_planner_agent
from agents.error_fixer import run_error_fix_agent
from agents.clarification_router import run_clarification_router_agent
from agents.insight_claim_typer import run_insight_claim_typer_agent
from agents.insight_agent import run_insight_agent
from agents.guarded_llm_enhancer import run_guarded_sql_candidate_agent
from agents.metric_agent import run_metric_agent
from agents.schema_agent import run_schema_agent
from agents.schema_repair import is_schema_mismatch_review, run_schema_repair_agent
from agents.sql_planning_router import run_sql_planning_router_agent
from agents.sql_generator import run_sql_generator
from agents.sql_reviewer import run_sql_reviewer
from agents.visualization_agent import run_visualization_agent
from tools.sql_executor import run_sql
from tools.trace_logger import append_trace, save_trace

from graph.state import AgentState


def _artifact_dir(state: dict, child: str) -> str:
    base = state.get("run_artifact_dir")
    if base:
        path = Path(base) / child
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    return f"reports/{child}"


def schema_node(state: AgentState) -> AgentState:
    return run_schema_agent(dict(state), state["db_path"])


def metric_node(state: AgentState) -> AgentState:
    if state.get("workspace_id"):
        metric_context = {
            "success": True,
            "source": "workspace_semantic_layer",
            "matched_metrics": [],
            "metrics": {},
            "semantic_layer_path": state.get("semantic_layer_path"),
            "profile_path": state.get("profile_path"),
        }
        updated = {**state, "metric_context": metric_context}
        return append_trace(
            updated,
            {
                "node": "metric_agent",
                "tool_name": "workspace_semantic_layer",
                "tool_input_summary": state.get("semantic_layer_path") or "",
                "tool_output_summary": "workspace semantic context attached",
                "status": "success",
                "latency_ms": 0,
            },
        )
    return run_metric_agent(dict(state))


def route_after_metric(state: AgentState) -> str:
    planning = state.get("sql_planning", {})
    if planning.get("source") == "provider" and planning.get("strategy") == "llm_candidate":
        return "guarded_candidate"
    return "generate"


def clarification_node(state: AgentState, provider=None) -> AgentState:
    return run_clarification_router_agent(dict(state), provider=provider)


def sql_planning_node(state: AgentState, provider=None) -> AgentState:
    return run_sql_planning_router_agent(dict(state), provider=provider)


def analysis_planner_node(state: AgentState, provider=None) -> AgentState:
    return run_analysis_planner_agent(dict(state), provider=provider)


def early_response_node(state: AgentState) -> AgentState:
    strategy = state.get("routing_strategy", "")
    if strategy == "clarify":
        questions = state.get("clarification_questions", [])
        answer = "需要补充信息后才能继续分析：" + " ".join(questions)
        status = "waiting_for_clarification"
        error_type = None
    elif strategy == "reject":
        reason = state.get("question_understanding", {}).get("rejection_reason") or "Request rejected before SQL generation."
        answer = f"请求包含敏感字段或不安全操作，已在 SQL 生成前拒绝。原因：{reason}"
        status = "failed"
        error_type = "question_understanding_rejected"
    else:
        answer = "Workflow stopped before SQL generation."
        status = "failed"
        error_type = "workflow_stopped_before_sql"

    updated = {
        **state,
        "status": status,
        "question_thread_status": status,
        "clarification_question": (state.get("clarification_questions") or [""])[0],
        "final_answer": answer,
        "data_used": False,
    }
    return append_trace(
        updated,
        {
            "node": "early_response_node",
            "tool_name": "",
            "tool_input_summary": state.get("user_question", ""),
            "tool_output_summary": answer[:200],
            "status": "success" if status == "waiting_for_clarification" else "error",
            "latency_ms": 0,
            "error_type": error_type,
        },
    )


def sql_generator_node(state: AgentState) -> AgentState:
    if state.get("initial_sql"):
        output = {
            "success": True,
            "sql": state["initial_sql"],
            "tables": [],
            "metrics": [],
            "reason": "Initial SQL supplied for workflow execution.",
        }
        updated = {
            **state,
            "sql_generation": output,
            "generated_sql": state["initial_sql"],
            "sql_reason": output["reason"],
            "selected_tables": [],
            "selected_metrics": [],
        }
        return append_trace(
            updated,
            {
                "node": "sql_generator_agent",
                "tool_name": "",
                "tool_input_summary": state.get("user_question", ""),
                "tool_output_summary": state["initial_sql"][:200],
                "status": "success",
                "latency_ms": 0,
            },
        )
    return run_sql_generator(dict(state))


def guarded_sql_candidate_node(state: AgentState, provider=None) -> AgentState:
    if state.get("sql_routing_strategy") != "llm_candidate":
        return dict(state)
    return run_guarded_sql_candidate_agent(dict(state), llm_provider=provider)


def sql_reviewer_node(state: AgentState) -> AgentState:
    updated = run_sql_reviewer(dict(state))
    if updated.get("schema_repair_pending_review"):
        review_result = updated.get("review_result", {})
        repair = dict(updated.get("schema_repair") or {})
        approved = bool(review_result.get("approved"))
        repair.update(
            {
                "reviewed": True,
                "succeeded": approved,
                "review_status": "approved" if approved else "rejected",
                "repair_rejection_reasons": list(review_result.get("issues") or []),
            }
        )
        updated["schema_repair"] = repair
        updated["schema_repair_succeeded"] = approved
        updated["schema_repair_pending_review"] = False
        if not approved:
            updated["schema_repair_reason"] = "; ".join(str(issue) for issue in review_result.get("issues") or [])
    return updated


def schema_repair_node(state: AgentState, provider=None) -> AgentState:
    return run_schema_repair_agent(dict(state), provider=provider)


def sql_executor_node(state: AgentState) -> AgentState:
    sql = state.get("generated_sql", "")
    result = run_sql(state["db_path"], sql)
    updated = {
        **state,
        "execution_result": result,
        "error_message": result.get("error", ""),
    }
    if result.get("success"):
        updated["status"] = "executed"
    else:
        updated["status"] = "execution_error"

    trace_event = dict(result.get("trace_event", {}))
    trace_event["node"] = "sql_executor_node"
    trace_event["retry_count"] = updated.get("retry_count", 0)
    return append_trace(updated, trace_event)


def error_fix_node(state: AgentState) -> AgentState:
    fixed = run_error_fix_agent(dict(state))
    if fixed.get("fixed_sql"):
        fixed["generated_sql"] = fixed["fixed_sql"]
    return fixed


def insight_node(
    state: AgentState,
    provider=None,
    answer_reviewer_provider=None,
    final_answer_composer_provider=None,
) -> AgentState:
    updated = run_insight_agent(
        dict(state),
        provider=provider,
        answer_reviewer_provider=answer_reviewer_provider,
        final_answer_composer_provider=final_answer_composer_provider,
    )
    updated["status"] = "completed" if updated.get("insight", {}).get("success") else "failed"
    updated["data_used"] = updated.get("insight", {}).get("data_used", False)
    return updated


def claim_typing_node(state: AgentState, provider=None) -> AgentState:
    if state.get("status") != "completed":
        return dict(state)
    return run_insight_claim_typer_agent(dict(state), provider=provider)


def visualization_agent_node(state: AgentState, provider=None) -> AgentState:
    if state.get("status") != "completed":
        return dict(state)
    return run_visualization_agent(dict(state), provider=provider, output_dir=_artifact_dir(state, "charts"))


def fail_response_node(state: AgentState) -> AgentState:
    if state.get("review_result") and not state["review_result"].get("approved"):
        issues = "; ".join(state["review_result"].get("issues", []))
        answer = f"SQL 审核未通过，已停止执行。原因：{issues}"
        error_type = "sql_review_rejected"
    elif state.get("execution_result") and not state["execution_result"].get("success"):
        answer = f"SQL 执行失败：{state['execution_result'].get('error', 'unknown error')}"
        error_type = "sql_execution_failed"
    else:
        answer = state.get("error_message") or "Workflow failed before producing a data-backed answer."
        error_type = "workflow_failed"

    updated = {
        **state,
        "status": "failed",
        "final_answer": answer,
        "data_used": False,
    }
    return append_trace(
        updated,
        {
            "node": "fail_response_node",
            "tool_name": "",
            "tool_input_summary": state.get("user_question", ""),
            "tool_output_summary": answer[:200],
            "status": "error",
            "latency_ms": 0,
            "error_type": error_type,
            "retry_count": state.get("retry_count", 0),
        },
    )


def save_trace_node(state: AgentState) -> AgentState:
    result = save_trace(
        state["run_id"],
        state.get("trace", []),
        trace_dir=state.get("trace_dir", Path("logs/traces")),
        session_id=state.get("session_id"),
        user_question=state.get("user_question"),
        status=state.get("status", "unknown"),
        question_thread={
            "original_question": state.get("original_question") or state.get("user_question") or "",
            "clarification_question": state.get("clarification_question") or "",
            "clarification_answer": state.get("clarification_answer") or "",
            "resolved_question": state.get("resolved_question") or "",
            "pending_run_id": state.get("pending_run_id") or "",
            "status": state.get("question_thread_status") or state.get("status", "unknown"),
        },
    )
    updated = {
        **state,
        "trace_save_result": result,
        "trace_path": result.get("trace_path", ""),
    }
    if not result.get("success") and updated.get("status") == "completed":
        updated["status"] = "trace_save_failed"
    return updated


def route_after_review(state: AgentState) -> str:
    if state.get("review_result", {}).get("approved"):
        return "execute"
    if (
        is_schema_mismatch_review(state.get("review_result"))
        and not state.get("schema_repair_attempted")
    ):
        return "schema_repair"
    return "fail"


def route_after_schema_repair(state: AgentState) -> str:
    if state.get("schema_repair_pending_review") and state.get("generated_sql"):
        return "review"
    return "fail"


def route_after_execute(state: AgentState) -> str:
    if state.get("execution_result", {}).get("success"):
        return "insight"
    if int(state.get("retry_count") or 0) < 1:
        return "fix"
    return "fail"


def route_after_fix(state: AgentState) -> str:
    if state.get("sql_fix", {}).get("success"):
        return "review"
    return "fail"


def route_after_clarification(state: AgentState) -> str:
    if state.get("initial_sql"):
        return "schema"
    if state.get("routing_strategy") == "reject":
        return "early_response"
    if state.get("routing_strategy") == "clarify" and _has_continuation_context(state):
        return "schema"
    if (
        state.get("routing_strategy") == "clarify"
        and state.get("clarification_result", {}).get("provider_called")
        and state.get("clarification_result", {}).get("requires_clarification") is False
    ):
        return "schema"
    if state.get("routing_strategy") == "clarify" and state.get("stop_for_clarification"):
        return "early_response"
    if (
        state.get("routing_strategy") == "clarify"
        and state.get("question_understanding", {}).get("source") == "provider_unavailable"
    ):
        return "early_response"
    if state.get("routing_strategy") == "clarify" and state.get("clarification_result", {}).get("provider_called"):
        return "early_response"
    return "schema"


def route_after_sql_planning(state: AgentState) -> str:
    if state.get("initial_sql"):
        return "schema"
    planning = state.get("sql_planning", {})
    if (
        planning.get("source") == "provider"
        and planning.get("strategy") == "clarify"
        and _has_continuation_context(state)
    ):
        return "schema"
    if planning.get("source") in {"provider", "provider_unavailable"} and planning.get("strategy") in {"clarify", "reject"}:
        return "early_response"
    return "schema"


def _has_continuation_context(state: AgentState) -> bool:
    return bool(
        state.get("pending_run_id")
        and state.get("clarification_answer")
        and state.get("resolved_question")
        and not state.get("stop_for_clarification")
    )
