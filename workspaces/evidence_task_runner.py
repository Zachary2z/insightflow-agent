from __future__ import annotations

import os
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from llm_ops.provider import LLMProvider
from observability.metrics import normalize_analysis_route, safely_get_metrics, safely_inc
from tools.trace_logger import append_trace
from workspaces.analysis_contracts import AnalysisTask, QuestionEvidencePack, WorkbenchToolCall
from workspaces.evidence_agent import run_evidence_agent_question_mode
from workspaces.evidence_tasks import EvidenceTask, EvidenceTaskPlan, EvidenceTaskResult
from workspaces.question_evidence_ledger import (
    build_question_evidence_ledger,
    empty_question_evidence_ledger,
    merge_question_evidence_ledgers,
)


@dataclass
class _TaskRun:
    task: EvidenceTask
    state: dict[str, Any]
    result: EvidenceTaskResult
    pack: QuestionEvidencePack
    ledger: dict[str, Any]


def run_evidence_task_plan(
    state: dict[str, Any],
    *,
    sql_planning_provider: LLMProvider | None = None,
    sql_candidate_provider: LLMProvider | None = None,
    max_parallel_evidence_tasks: int | None = None,
) -> dict[str, Any]:
    plan = _plan(state)
    tasks = sorted(plan.tasks, key=lambda item: (item.priority, item.task_id))[: plan.max_evidence_tasks]
    if not tasks:
        return _without_tasks(state, plan)

    workers = _parallel_limit(plan, max_parallel_evidence_tasks)
    runs = _run_tasks(
        state,
        tasks=tasks,
        max_workers=workers,
        sql_planning_provider=sql_planning_provider,
        sql_candidate_provider=sql_candidate_provider,
    )
    return _merge_task_runs(state, plan=plan, runs=runs, max_workers=workers)


def _run_tasks(
    state: dict[str, Any],
    *,
    tasks: list[EvidenceTask],
    max_workers: int,
    sql_planning_provider: LLMProvider | None,
    sql_candidate_provider: LLMProvider | None,
) -> list[_TaskRun]:
    if max_workers <= 1 or len(tasks) == 1:
        return [
            _run_one_task(
                state,
                task,
                sql_planning_provider=sql_planning_provider,
                sql_candidate_provider=sql_candidate_provider,
            )
            for task in tasks
        ]

    runs: list[_TaskRun] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                copy_context().run,
                _run_one_task,
                state,
                task,
                sql_planning_provider=sql_planning_provider,
                sql_candidate_provider=sql_candidate_provider,
            ): task
            for task in tasks
        }
        for future in as_completed(futures):
            runs.append(future.result())
    return sorted(runs, key=lambda item: (item.task.priority, item.task.task_id))


def _run_one_task(
    base_state: dict[str, Any],
    task: EvidenceTask,
    *,
    sql_planning_provider: LLMProvider | None,
    sql_candidate_provider: LLMProvider | None,
) -> _TaskRun:
    task_state = _task_state(base_state, task)
    result_state = run_evidence_agent_question_mode(
        task_state,
        sql_planning_provider=sql_planning_provider,
        sql_candidate_provider=sql_candidate_provider,
    )
    pack = QuestionEvidencePack.from_dict(result_state.get("question_evidence_pack") or {})
    status = "executed" if result_state.get("execution_result", {}).get("success") else "failed"
    data_limits = _task_data_limits(task=task, result_state=result_state, pack=pack)
    tool_calls = [
        WorkbenchToolCall.from_dict(call)
        for call in result_state.get("workbench_tool_calls") or []
        if isinstance(call, dict)
    ]
    ledger = build_question_evidence_ledger(
        question_evidence_pack=pack,
        execution_result=result_state.get("execution_result") if isinstance(result_state.get("execution_result"), dict) else {},
        evidence_validation=result_state.get("evidence_result") if isinstance(result_state.get("evidence_result"), dict) else {},
        chart_artifacts=[],
        fact_payload={},
        source_pack_id=f"question_evidence_pack:{task.task_id}",
        task_id=task.task_id,
    )
    task_result = EvidenceTaskResult(
        task_id=task.task_id,
        status=status,
        rows=pack.rows if status == "executed" else [],
        columns=pack.columns if status == "executed" else [],
        evidence_refs=list(ledger.get("evidence_refs") or []),
        data_limits=data_limits,
        tool_calls=tool_calls,
    )
    return _TaskRun(task=task, state=result_state, result=task_result, pack=pack, ledger=ledger)


def _merge_task_runs(
    state: dict[str, Any],
    *,
    plan: EvidenceTaskPlan,
    runs: list[_TaskRun],
    max_workers: int,
) -> dict[str, Any]:
    successful = [run for run in runs if run.result.status == "executed"]
    successful_core = [run for run in successful if run.task.purpose == "core_fact"]
    task_limits = _task_limits(plan, runs)
    merged_pack = _merged_pack(state, runs=successful, data_limits=task_limits)
    merged_execution = _merged_execution(successful)
    merged_ledger = merge_question_evidence_ledgers(
        [run.ledger for run in successful],
        data_limits=task_limits,
    )
    task_results = [run.result.to_dict() for run in runs]
    tool_calls = _merged_tool_calls(runs)
    trace = _merged_trace(state, runs)
    failed_core = bool([run for run in runs if run.task.purpose == "core_fact"]) and not successful_core
    status = "failed" if failed_core or not successful else "executed"
    metrics = safely_get_metrics()
    metric_route = normalize_analysis_route(plan.route)
    for run in runs:
        safely_inc(metrics, "evidence_tasks", {"status": "success" if run.result.status == "executed" else "error", "route": metric_route})
    updated = {
        **state,
        "status": status,
        "data_used": bool(successful and not failed_core),
        "execution_result": merged_execution,
        "question_evidence_pack": merged_pack.to_dict(),
        "question_evidence_ledger": merged_ledger,
        "evidence_task_results": task_results,
        "workbench_tool_calls": [call.to_dict() for call in tool_calls],
        "trace": trace,
        "evidence_task_runner": {
            "status": status,
            "task_count": len(runs),
            "executed_task_count": len(successful),
            "max_parallel_evidence_tasks": max_workers,
        },
        "generated_sql": "",
        "review_result": {},
    }
    if failed_core:
        updated["error_message"] = "核心证据任务全部失败，当前数据不足以生成可靠业务结论。"
    return append_trace(
        updated,
        {
            "node": "evidence_task_runner",
            "tool_name": "evidence_task_runner",
            "tool_input_summary": f"tasks={len(runs)} max_parallel={max_workers}",
            "tool_output_summary": f"executed={len(successful)} failed={len(runs) - len(successful)}",
            "status": "success" if status == "executed" else "error",
            "latency_ms": 0,
            "provider_called": False,
            "fallback_used": False,
        },
    )


def _without_tasks(state: dict[str, Any], plan: EvidenceTaskPlan) -> dict[str, Any]:
    task = _analysis_task(state)
    limits = plan.data_limits or ["当前问题没有可执行的证据任务。"]
    safely_inc(safely_get_metrics(), "evidence_tasks", {"status": "skipped", "route": normalize_analysis_route(plan.route)})
    return append_trace(
        {
            **state,
            "status": "failed",
            "data_used": False,
            "error_message": "当前问题没有可执行的证据任务。",
            "execution_result": {"success": False, "columns": [], "rows": [], "row_count": 0, "error": "no evidence tasks"},
            "question_evidence_pack": QuestionEvidencePack(task=task, data_limits=limits).to_dict(),
            "question_evidence_ledger": empty_question_evidence_ledger(task=task, data_limits=limits),
            "evidence_task_results": [],
            "evidence_task_runner": {
                "status": "failed",
                "task_count": 0,
                "executed_task_count": 0,
                "max_parallel_evidence_tasks": _parallel_limit(plan, None),
            },
        },
        {
            "node": "evidence_task_runner",
            "tool_name": "evidence_task_runner",
            "tool_input_summary": "tasks=0",
            "tool_output_summary": "no executable evidence tasks",
            "status": "error",
            "latency_ms": 0,
        },
    )


def _task_state(base_state: dict[str, Any], task: EvidenceTask) -> dict[str, Any]:
    analysis_task = _analysis_task(base_state)
    task_contract = AnalysisTask(
        resolved_question=task.question or analysis_task.resolved_question,
        metrics=list(task.metrics or analysis_task.metrics),
        dimensions=list(task.dimensions or analysis_task.dimensions),
        time_range=dict(analysis_task.time_range or {}),
        filters=list(analysis_task.filters or []),
        decision_goal=analysis_task.decision_goal,
        missing_slots=[],
        clarification_question="",
        route_hint=analysis_task.route_hint or str((base_state.get("analysis_route") or {}).get("route") or ""),
        business_lens=dict(analysis_task.business_lens or {}),
        evidence_task_plan=dict(analysis_task.evidence_task_plan or base_state.get("evidence_task_plan") or {}),
    )
    state = {
        **base_state,
        "user_question": task.question or base_state.get("user_question", ""),
        "resolved_question": task.question or base_state.get("resolved_question", ""),
        "analysis_task": task_contract.to_dict(),
        "analysis_task_contract": task_contract.to_dict(),
        "evidence_task": task.to_dict(),
        "execution_result": {},
        "review_result": {},
        "generated_sql": "",
        "sql_generation": {},
        "llm_sql_enhancement": {},
        "schema_repair_attempted": False,
        "schema_repair_succeeded": False,
        "schema_repair_reason": "",
        "schema_repair": {},
        "schema_repair_pending_review": False,
        "retry_count": 0,
        "review_retry_count": 0,
        "trace": [],
    }
    state.pop("initial_sql", None)
    return state


def _merged_pack(state: dict[str, Any], *, runs: list[_TaskRun], data_limits: list[str]) -> QuestionEvidencePack:
    return QuestionEvidencePack(
        task=_analysis_task(state),
        sql="",
        rows=_merged_pack_rows(runs),
        columns=_merged_columns(runs),
        metrics=_unique([metric for run in runs for metric in run.pack.metrics]),
        chart_candidates=[candidate for run in runs for candidate in run.pack.chart_candidates],
        tool_calls=_merged_tool_calls(runs),
        data_limits=data_limits,
    )


def _merged_pack_rows(runs: list[_TaskRun]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in runs:
        for row in run.pack.rows:
            rows.append({"task_id": run.task.task_id, "task_purpose": run.task.purpose, **dict(row)})
    return rows


def _merged_execution(runs: list[_TaskRun]) -> dict[str, Any]:
    if not runs:
        return {"success": False, "columns": [], "rows": [], "row_count": 0, "error": "no successful evidence tasks"}
    columns = _merged_columns(runs)
    row_dicts = _merged_pack_rows(runs)
    rows = [[row.get(column) for column in columns] for row in row_dicts]
    return {
        "success": True,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": any(bool(run.state.get("execution_result", {}).get("truncated")) for run in runs),
        "error": "",
        "execution_time_ms": sum(int(run.state.get("execution_result", {}).get("execution_time_ms") or 0) for run in runs),
    }


def _merged_columns(runs: list[_TaskRun]) -> list[str]:
    columns = ["task_id", "task_purpose"]
    for run in runs:
        for column in run.pack.columns:
            if column not in columns:
                columns.append(column)
    return columns


def _task_limits(plan: EvidenceTaskPlan, runs: list[_TaskRun]) -> list[str]:
    limits = [str(item) for item in plan.data_limits if str(item).strip()]
    for run in runs:
        if run.result.status == "executed":
            limits.extend(str(item) for item in run.result.data_limits if str(item).strip())
            continue
        detail = "；".join(str(item) for item in run.result.data_limits if str(item).strip())
        if detail:
            limits.append(f"证据任务 {run.task.task_id} 未能完成：{detail}")
        else:
            limits.append(f"证据任务 {run.task.task_id} 未能完成。")
    return _unique(limits)


def _task_data_limits(
    *,
    task: EvidenceTask,
    result_state: dict[str, Any],
    pack: QuestionEvidencePack,
) -> list[str]:
    limits = [*task.data_limits, *pack.data_limits]
    review = result_state.get("review_result") if isinstance(result_state.get("review_result"), dict) else {}
    limits.extend(str(issue) for issue in review.get("issues") or [] if str(issue).strip())
    enhancement = result_state.get("llm_sql_enhancement") if isinstance(result_state.get("llm_sql_enhancement"), dict) else {}
    for candidate in enhancement.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        candidate_review = candidate.get("review_result") if isinstance(candidate.get("review_result"), dict) else {}
        limits.extend(str(issue) for issue in candidate_review.get("issues") or [] if str(issue).strip())
    error = str(result_state.get("error_message") or "").strip()
    if error:
        limits.append(error)
    return _unique(limits)


def _merged_tool_calls(runs: list[_TaskRun]) -> list[WorkbenchToolCall]:
    calls: list[WorkbenchToolCall] = []
    seen: set[str] = set()
    for run in runs:
        for call in run.result.tool_calls:
            marker = "|".join([run.task.task_id, call.tool_name, call.purpose, call.output_summary, call.status])
            if marker in seen:
                continue
            seen.add(marker)
            calls.append(
                WorkbenchToolCall(
                    tool_name=call.tool_name,
                    purpose=f"{run.task.task_id}: {call.purpose}" if call.purpose else run.task.task_id,
                    input_summary=call.input_summary,
                    output_summary=call.output_summary,
                    status=call.status,
                )
            )
    return calls


def _merged_trace(state: dict[str, Any], runs: list[_TaskRun]) -> list[dict[str, Any]]:
    trace = [dict(event) for event in state.get("trace") or [] if isinstance(event, dict)]
    for run in runs:
        for event in run.state.get("trace") or []:
            if not isinstance(event, dict):
                continue
            trace.append({**event, "evidence_task_id": run.task.task_id})
    return trace


def _plan(state: dict[str, Any]) -> EvidenceTaskPlan:
    raw = state.get("evidence_task_plan")
    if not isinstance(raw, dict) or not raw:
        raw_task = state.get("analysis_task") if isinstance(state.get("analysis_task"), dict) else {}
        raw = raw_task.get("evidence_task_plan") if isinstance(raw_task.get("evidence_task_plan"), dict) else {}
    return EvidenceTaskPlan.from_dict(raw or {"route": str((state.get("analysis_route") or {}).get("route") or "standard_analysis")})


def _analysis_task(state: dict[str, Any]) -> AnalysisTask:
    for key in ("analysis_task_contract", "analysis_task"):
        value = state.get(key)
        if isinstance(value, AnalysisTask):
            return value
        if isinstance(value, dict):
            return AnalysisTask.from_dict(value)
    return AnalysisTask(resolved_question=str(state.get("resolved_question") or state.get("user_question") or ""))


def _parallel_limit(plan: EvidenceTaskPlan, configured: int | None) -> int:
    raw = configured or _env_parallel_limit() or plan.max_parallel_evidence_tasks or 3
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 3
    return max(1, min(value, max(1, plan.max_evidence_tasks or len(plan.tasks) or 1)))


def _env_parallel_limit() -> int | None:
    value = os.getenv("INSIGHTFLOW_MAX_PARALLEL_EVIDENCE_TASKS", "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _unique(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


__all__ = ["run_evidence_task_plan"]
