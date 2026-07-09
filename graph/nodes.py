from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.clarification_router import run_clarification_router_agent
from agents.evidence_validator import run_evidence_validator_agent
from agents.visualization_agent import run_visualization_agent
from tools.trace_logger import append_trace, save_trace
from workspaces.context_pack_builder import build_fast_fact_context_pack
from workspaces.business_answer_agent import run_business_answer_agent
from workspaces.evidence_agent import run_evidence_agent_question_mode
from workspaces.evidence_task_runner import run_evidence_task_plan
from workspaces.fast_fact_claims import build_fast_fact_claims
from workspaces.product_result_builder import build_evidence

from graph.state import AgentState


def _artifact_dir(state: dict, child: str) -> str:
    base = state.get("run_artifact_dir")
    if base:
        path = Path(base) / child
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    return f"reports/{child}"


def clarification_node(state: AgentState, provider=None) -> AgentState:
    return run_clarification_router_agent(dict(state), provider=provider)


def evidence_agent_node(
    state: AgentState,
    sql_planning_provider=None,
    sql_candidate_provider=None,
) -> AgentState:
    if _should_run_evidence_task_runner(state):
        return run_evidence_task_plan(
            dict(state),
            sql_planning_provider=sql_planning_provider,
            sql_candidate_provider=sql_candidate_provider,
        )
    return run_evidence_agent_question_mode(
        dict(state),
        sql_planning_provider=sql_planning_provider,
        sql_candidate_provider=sql_candidate_provider,
    )


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


def fast_fact_node(state: AgentState) -> AgentState:
    evidence = build_evidence(dict(state))
    fact_payload = evidence.get("fact_payload") if isinstance(evidence.get("fact_payload"), dict) else {}
    claims = build_fast_fact_claims(
        analysis_task=state.get("analysis_task") or {},
        execution_result=state.get("execution_result") or {},
        fact_payload=fact_payload,
    )
    validated = run_evidence_validator_agent({**dict(state), "claims_to_validate": claims})
    evidence_result = dict(validated.get("evidence_result") or {})
    if evidence_result.get("success"):
        evidence_result.setdefault("validation_status", "validated")

    fast_fact_context_pack = build_fast_fact_context_pack(
        user_question=state.get("user_question", ""),
        analysis_route=state.get("analysis_route") or {},
        analysis_task=state.get("analysis_task") or {},
        fact_payload=fact_payload,
        evidence_result=evidence_result,
        execution_result=state.get("execution_result") or {},
        metric_registry=state.get("metric_registry") or state.get("metric_context") or {},
    )
    updated = {
        **validated,
        "status": "executed",
        "data_used": True,
        "fast_fact_context_pack": fast_fact_context_pack,
        "fast_fact_result": {
            "success": True,
            "fact_payload": fact_payload,
            "context_pack": fast_fact_context_pack,
            "claims_to_validate": claims,
            "answer_contract": "provider_or_llm_from_question_evidence_ledger",
        },
    }
    return append_trace(
        updated,
        {
            "node": "fast_fact_evidence_preparer",
            "tool_name": "",
            "tool_input_summary": f"route={(state.get('analysis_route') or {}).get('route', '')}",
            "tool_output_summary": "prepared fast-fact evidence for ledger-only answer generation",
            "status": "success",
            "latency_ms": 0,
            "provider_called": False,
            "fallback_used": False,
        },
    )


def business_answer_node(
    state: AgentState,
    provider=None,
) -> AgentState:
    updated = run_business_answer_agent(
        dict(state),
        provider=provider,
    )
    return updated


def visualization_agent_node(state: AgentState, provider=None) -> AgentState:
    if state.get("status") != "completed":
        return dict(state)
    try:
        return run_visualization_agent(dict(state), provider=provider, output_dir=_artifact_dir(state, "charts"))
    except Exception as exc:
        return append_trace(
            {
                **dict(state),
                "chart_warning": str(exc),
                "visualization_delivery_result": {},
                "visualization_trace": {},
            },
            {
                "node": "visualization_agent",
                "tool_name": "external_visualization_tool",
                "tool_input_summary": "chart generation after business answer",
                "tool_output_summary": str(exc)[:200],
                "status": "error",
                "latency_ms": 0,
                "error_type": "visualization_delivery_error",
                "error": str(exc),
                "provider_called": False,
                "fallback_used": False,
            },
        )


def fail_response_node(state: AgentState) -> AgentState:
    if state.get("evidence_task_results"):
        answer = state.get("error_message") or "核心证据任务全部失败，当前数据不足以生成可靠业务结论。"
        error_type = "evidence_task_core_failed"
    elif state.get("review_result") and not state["review_result"].get("approved"):
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


def route_after_evidence_agent(state: AgentState) -> str:
    if state.get("execution_result", {}).get("success"):
        if (state.get("analysis_route") or {}).get("route") == "fast_fact":
            return "fast_fact"
        return "business_answer"
    if state.get("evidence_agent_early_response"):
        return "early_response"
    return "fail"


def _should_run_evidence_task_runner(state: AgentState) -> bool:
    if state.get("initial_sql"):
        return False
    route = (state.get("analysis_route") or {}).get("route")
    if route == "fast_fact":
        return False
    plan = state.get("evidence_task_plan") if isinstance(state.get("evidence_task_plan"), dict) else {}
    if not plan:
        task = state.get("analysis_task") if isinstance(state.get("analysis_task"), dict) else {}
        plan = task.get("evidence_task_plan") if isinstance(task.get("evidence_task_plan"), dict) else {}
    tasks = plan.get("tasks") if isinstance(plan, dict) else []
    if not isinstance(tasks, list):
        return False
    core_tasks = [task for task in tasks if isinstance(task, dict) and task.get("purpose") == "core_fact"]
    if len(core_tasks) < 2:
        return False
    source_tables = _core_task_source_tables(state, core_tasks)
    return len(source_tables) > 1


def _core_task_source_tables(state: AgentState, core_tasks: list[dict[str, Any]]) -> set[str]:
    analysis_task = state.get("analysis_task") if isinstance(state.get("analysis_task"), dict) else {}
    lens = analysis_task.get("business_lens") if isinstance(analysis_task.get("business_lens"), dict) else {}
    metric_tables: dict[str, str] = {}
    for metric in lens.get("metrics") or []:
        if not isinstance(metric, dict):
            continue
        label = str(metric.get("label") or "").strip()
        table = str(metric.get("source_table") or "").strip()
        if label and table:
            metric_tables[label] = table
    tables: set[str] = set()
    for task in core_tasks:
        for metric in task.get("metrics") or []:
            table = metric_tables.get(str(metric))
            if table:
                tables.add(table)
    return tables


def route_after_answer_for_visualization(state: AgentState) -> str:
    if _should_run_visualization(state):
        return "visualization_agent"
    return "save_trace"


def route_after_clarification(state: AgentState) -> str:
    if state.get("initial_sql"):
        return "schema"
    if state.get("routing_strategy") == "reject":
        return "early_response"
    if (
        state.get("routing_strategy") == "clarify"
        and state.get("clarification_result", {}).get("requires_clarification") is True
    ):
        return "early_response"
    if (
        state.get("routing_strategy") == "clarify"
        and _has_continuation_context(state)
        and not state.get("clarification_result", {}).get("missing_slots")
    ):
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


def _has_continuation_context(state: AgentState) -> bool:
    return bool(
        state.get("clarification_answer")
        and state.get("resolved_question")
        and not state.get("stop_for_clarification")
    )


def _should_run_visualization(state: AgentState) -> bool:
    if state.get("status") != "completed":
        return False
    execution = state.get("execution_result") if isinstance(state.get("execution_result"), dict) else {}
    if not execution.get("success"):
        return False
    question = str(state.get("user_question") or state.get("original_question") or "")
    if _explicit_chart_request(question):
        return True
    route = state.get("analysis_route") if isinstance(state.get("analysis_route"), dict) else {}
    if route.get("route") == "fast_fact":
        return False
    task = state.get("analysis_task") if isinstance(state.get("analysis_task"), dict) else {}
    if str(task.get("task_type") or "") != "trend":
        return _chartable_complex_comparison(question, execution)
    return _row_count(execution) >= 2


def _explicit_chart_request(question: str) -> bool:
    lowered = str(question or "").lower()
    return any(
        marker in lowered
        for marker in (
            "图表",
            "画图",
            "作图",
            "可视化",
            "趋势图",
            "柱状图",
            "折线图",
            "chart",
            "visualization",
            "visualise",
            "visualize",
        )
    )


def _chartable_complex_comparison(question: str, execution: dict[str, Any]) -> bool:
    if _row_count(execution) < 2:
        return False
    compact = "".join(str(question or "").lower().split())
    comparison_intent = any(marker in compact for marker in ("比较", "对比", "差异", "difference", "compare"))
    focus_intent = any(
        marker in compact
        for marker in ("值得关注", "优先关注", "最值得", "需要优先", "优先复盘", "风险边界", "priority")
    )
    return focus_intent and (comparison_intent or "复盘" in compact or "建议" in compact)


def _row_count(execution: dict[str, Any]) -> int:
    return int(execution.get("row_count") or len(execution.get("rows") or []))
