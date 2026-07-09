from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.evidence_planning import run_evidence_planning_agent
from agents.evidence_validator import run_evidence_validator_agent
from agents.error_fixer import run_error_fix_agent
from agents.guarded_llm_enhancer import run_guarded_sql_candidate_agent
from agents.metric_agent import run_metric_agent
from agents.schema_agent import run_schema_agent
from agents.schema_repair import is_schema_mismatch_review, run_schema_repair_agent
from agents.sql_generator import run_sql_generator
from agents.sql_reviewer import run_sql_reviewer
from llm_ops.provider import LLMProvider
from tools.sql_executor import run_sql
from tools.trace_logger import append_trace
from workspaces.analysis_contracts import AnalysisTask, QuestionEvidencePack, WorkbenchToolCall
from workspaces.product_result_builder import build_evidence
from workspaces.question_evidence_ledger import build_question_evidence_ledger
from workspaces.question_evidence_cache import (
    load_question_evidence_cache,
    save_question_evidence_cache,
    with_question_evidence_cache_identity,
)


def run_evidence_agent_question_mode(
    state: dict[str, Any],
    *,
    sql_planning_provider: LLMProvider | None = None,
    sql_candidate_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    updated = with_question_evidence_cache_identity(dict(state))
    tool_calls: list[WorkbenchToolCall] = []
    cached = load_question_evidence_cache(updated)
    if cached:
        return _with_cached_pack(updated, cached)

    if not updated.get("initial_sql"):
        updated = run_evidence_planning_agent(updated, provider=sql_planning_provider)
        _record(
            tool_calls,
            "evidence_planning",
            "一次性规划本轮问题需要的指标、维度、查询策略和证据边界",
            updated.get("user_question", ""),
            _planning_summary(updated.get("evidence_planning")),
            _status(updated.get("evidence_planning")),
        )
        if _planning_stops_before_evidence(updated):
            updated["evidence_agent_early_response"] = True
            return _with_pack(updated, tool_calls, status="failed")

    updated = run_schema_agent(updated, updated["db_path"])
    _record(
        tool_calls,
        "schema_lookup",
        "读取当前工作区数据库结构",
        _workspace_summary(updated),
        _schema_summary(updated.get("database_schema")),
        _status(updated.get("database_schema")),
    )
    if updated.get("status") == "schema_error":
        return _with_pack(updated, tool_calls, status="failed")

    updated = run_metric_agent(updated)
    updated = _normalize_metric_context_for_question_mode(updated)
    _record(
        tool_calls,
        "metric_lookup",
        "匹配当前问题可用的业务指标和公式",
        updated.get("user_question", ""),
        _metric_summary(updated.get("metric_context")),
        _status(updated.get("metric_context"), default="completed"),
    )

    updated = _build_sql_candidate(updated, provider=sql_candidate_provider)
    _record(
        tool_calls,
        "sql_candidate_builder",
        "构造只读 SQL 候选，LLM 输出仅作为候选",
        _candidate_input_summary(updated),
        _candidate_output_summary(updated),
        "completed" if updated.get("generated_sql") else "failed",
    )
    if not updated.get("generated_sql"):
        updated["error_message"] = updated.get("error_message") or "未能生成可审核的 SQL 候选。"

    updated = _review(updated, tool_calls, purpose="审核 SQL 候选，未通过不得执行")
    if not _review_approved(updated):
        if is_schema_mismatch_review(updated.get("review_result")) and not updated.get("schema_repair_attempted"):
            updated = run_schema_repair_agent(updated, provider=sql_candidate_provider)
            _record(
                tool_calls,
                "schema_repair",
                "对 schema mismatch SQL 做一次候选修复",
                _review_issue_summary(updated.get("schema_repair")),
                _schema_repair_summary(updated.get("schema_repair")),
                "completed" if updated.get("schema_repair_pending_review") else "failed",
            )
            if updated.get("schema_repair_pending_review") and updated.get("generated_sql"):
                updated = _review(updated, tool_calls, purpose="重新审核 schema repair 候选，未通过不得执行")
        if not _review_approved(updated):
            return _with_pack(updated, tool_calls, status="failed")

    updated = _execute_reviewed_sql(updated, tool_calls)
    if updated.get("execution_result", {}).get("success"):
        return _with_pack(updated, tool_calls, status="executed")

    updated = _fix_once_after_execution_error(updated, tool_calls)
    return _with_pack(
        updated,
        tool_calls,
        status="executed" if updated.get("execution_result", {}).get("success") else "failed",
    )


def _build_sql_candidate(state: dict[str, Any], *, provider: LLMProvider | None) -> dict[str, Any]:
    if state.get("initial_sql"):
        output = {
            "success": True,
            "sql": state["initial_sql"],
            "tables": [],
            "metrics": [],
            "reason": "Initial SQL supplied for workflow execution.",
        }
        return append_trace(
            {
                **state,
                "sql_generation": output,
                "generated_sql": state["initial_sql"],
                "sql_reason": output["reason"],
                "selected_tables": [],
                "selected_metrics": [],
            },
            {
                "node": "sql_generator_agent",
                "tool_name": "",
                "tool_input_summary": state.get("user_question", ""),
                "tool_output_summary": "initial SQL candidate supplied",
                "status": "success",
                "latency_ms": 0,
            },
        )

    planning = state.get("sql_planning") if isinstance(state.get("sql_planning"), dict) else {}
    if planning.get("source") == "provider" and planning.get("strategy") == "llm_candidate":
        return run_guarded_sql_candidate_agent(state, llm_provider=provider)
    generated = run_sql_generator(state)
    if generated.get("sql_routing_strategy") == "llm_candidate":
        return run_guarded_sql_candidate_agent(generated, llm_provider=provider)
    return generated


def _normalize_metric_context_for_question_mode(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("workspace_id") or state.get("semantic_layer_path"):
        return state
    context = state.get("metric_context") if isinstance(state.get("metric_context"), dict) else {}
    if context.get("matched_metrics") != ["gmv"]:
        return state
    task_metrics = [str(item).lower() for item in (state.get("analysis_task") or {}).get("metrics") or []]
    if any(metric in {"gmv", "category_gmv"} for metric in task_metrics):
        return state
    return {
        **state,
        "metric_context": {**context, "success": False, "matched_metrics": [], "metric_registry": {}},
        "metric_registry": {},
        "selected_metrics": [],
    }


def _review(state: dict[str, Any], tool_calls: list[WorkbenchToolCall], *, purpose: str) -> dict[str, Any]:
    updated = run_sql_reviewer(state)
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
    _record(
        tool_calls,
        "sql_review",
        purpose,
        "SQL candidate held for deterministic review",
        _review_summary(updated.get("review_result")),
        "completed" if _review_approved(updated) else "failed",
    )
    return updated


def _execute_reviewed_sql(state: dict[str, Any], tool_calls: list[WorkbenchToolCall]) -> dict[str, Any]:
    if not _review_approved(state):
        return state
    sql = state.get("generated_sql", "")
    result = run_sql(state["db_path"], sql)
    updated = {
        **state,
        "execution_result": result,
        "error_message": result.get("error", ""),
        "status": "executed" if result.get("success") else "execution_error",
    }
    trace_event = dict(result.get("trace_event", {}))
    trace_event["node"] = "sql_executor_node"
    trace_event["retry_count"] = updated.get("retry_count", 0)
    updated = append_trace(updated, trace_event)
    _record(
        tool_calls,
        "sql_execution",
        "执行已通过 SQL review 的只读查询",
        "review approved SQL",
        _execution_summary(result),
        "completed" if result.get("success") else "failed",
    )
    return updated


def _fix_once_after_execution_error(state: dict[str, Any], tool_calls: list[WorkbenchToolCall]) -> dict[str, Any]:
    if int(state.get("retry_count") or 0) >= 1:
        return state
    fixed = run_error_fix_agent(state)
    _record(
        tool_calls,
        "sql_fix",
        "SQL 执行失败后做一次确定性修复候选",
        _execution_summary(state.get("execution_result")),
        _sql_fix_summary(fixed.get("sql_fix")),
        "completed" if fixed.get("sql_fix", {}).get("success") else "failed",
    )
    if not fixed.get("sql_fix", {}).get("success"):
        return fixed
    fixed["generated_sql"] = fixed.get("fixed_sql", "")
    reviewed = _review(fixed, tool_calls, purpose="重新审核 execution fix 候选，未通过不得执行")
    if not _review_approved(reviewed):
        return reviewed
    return _execute_reviewed_sql(reviewed, tool_calls)


def _with_pack(
    state: dict[str, Any],
    tool_calls: list[WorkbenchToolCall],
    *,
    status: str,
) -> dict[str, Any]:
    updated = {**state, "status": status}
    pack = _build_question_evidence_pack(updated, tool_calls)
    updated["question_evidence_pack"] = pack.to_dict()
    updated["workbench_tool_calls"] = [call.to_dict() for call in tool_calls]
    updated = _validate_pack_evidence(updated, pack, status=status)
    updated["question_evidence_ledger"] = _build_question_ledger(updated, pack)
    save_question_evidence_cache(updated)
    _drop_cache_identity(updated)
    return updated


def _with_cached_pack(state: dict[str, Any], cached: dict[str, Any]) -> dict[str, Any]:
    cache_call = WorkbenchToolCall(
        tool_name="question_evidence_cache",
        purpose="复用同一数据版本、语义层和规范化问题的已审核证据",
        input_summary=str(state.get("user_question") or "")[:200],
        output_summary="复用了已通过 SQL review 和 SQL execution 的 QuestionEvidencePack",
        status="completed",
    )
    pack = QuestionEvidencePack.from_dict(cached.get("question_evidence_pack") or {})
    pack.tool_calls = [
        *pack.tool_calls,
        cache_call,
    ]
    tool_calls = [call.to_dict() for call in pack.tool_calls]
    updated = {
        **state,
        "status": "executed",
        "generated_sql": str(cached.get("generated_sql") or ""),
        "review_result": dict(cached.get("review_result") or {}),
        "execution_result": dict(cached.get("execution_result") or {}),
        "metric_context": dict(cached.get("metric_context") or {}),
        "selected_metrics": list(cached.get("selected_metrics") or []),
        "question_evidence_pack": pack.to_dict(),
        "workbench_tool_calls": tool_calls,
        "question_evidence_ledger": _build_question_ledger(
            {
                **state,
                "execution_result": dict(cached.get("execution_result") or {}),
                "evidence_result": dict(cached.get("evidence_result") or {}),
                "chart_artifacts": list(cached.get("chart_artifacts") or []),
            },
            pack,
        ),
        "question_evidence_cache": {
            "hit": True,
            "cache_key": str(cached.get("cache_key") or ""),
            "reason": "同一工作区、数据版本、语义层和规范化问题命中证据缓存。",
        },
    }
    _drop_cache_identity(updated)
    return append_trace(
        updated,
        {
            "node": "question_evidence_cache",
            "tool_name": "question_evidence_cache",
            "tool_input_summary": cache_call.input_summary,
            "tool_output_summary": cache_call.output_summary,
            "status": "success",
            "latency_ms": 0,
            "provider_called": False,
            "fallback_used": False,
        },
    )


def _drop_cache_identity(state: dict[str, Any]) -> None:
    state.pop("_question_evidence_cache_key", None)
    state.pop("_question_evidence_cache_normalized_task", None)


def _build_question_evidence_pack(
    state: dict[str, Any],
    tool_calls: list[WorkbenchToolCall],
) -> QuestionEvidencePack:
    execution = state.get("execution_result") if isinstance(state.get("execution_result"), dict) else {}
    evidence = build_evidence(state)
    fact_payload = evidence.get("fact_payload") if isinstance(evidence.get("fact_payload"), dict) else {}
    data_limits = _unique_text(
        [
            *[str(item) for item in fact_payload.get("warnings") or []],
            *[str(item) for item in fact_payload.get("data_limits") or []],
            *_review_data_limits(state),
            *_execution_data_limits(execution),
        ]
    )
    return QuestionEvidencePack(
        task=_analysis_task(state),
        sql=str(state.get("generated_sql") or ""),
        rows=_rows_as_dicts(execution),
        columns=[str(column) for column in execution.get("columns") or []],
        metrics=_pack_metrics(state, fact_payload),
        chart_candidates=_chart_candidates(execution),
        tool_calls=tool_calls,
        data_limits=data_limits,
    )


def _build_question_ledger(state: dict[str, Any], pack: QuestionEvidencePack) -> dict[str, Any]:
    evidence = build_evidence(state)
    fact_payload = evidence.get("fact_payload") if isinstance(evidence.get("fact_payload"), dict) else {}
    return build_question_evidence_ledger(
        question_evidence_pack=pack,
        execution_result=state.get("execution_result") if isinstance(state.get("execution_result"), dict) else {},
        evidence_validation=state.get("evidence_result") if isinstance(state.get("evidence_result"), dict) else {},
        chart_artifacts=state.get("chart_artifacts") if isinstance(state.get("chart_artifacts"), list) else [],
        fact_payload=fact_payload,
    )


def _validate_pack_evidence(
    state: dict[str, Any],
    pack: QuestionEvidencePack,
    *,
    status: str,
) -> dict[str, Any]:
    if status != "executed" or not pack.rows:
        return state
    claims = _row_fact_claims(pack)
    if not claims:
        return state
    validated = run_evidence_validator_agent({**state, "claims_to_validate": claims})
    evidence_result = dict(validated.get("evidence_result") or {})
    if evidence_result.get("success"):
        evidence_result.setdefault("validation_status", "validated")
        validated["evidence_result"] = evidence_result
    return validated


def _row_fact_claims(pack: QuestionEvidencePack, *, limit: int = 5) -> list[str]:
    claims: list[str] = []
    for row in pack.rows[:limit]:
        parts = [
            f"{column} 为 {row.get(column)}"
            for column in pack.columns
            if row.get(column) is not None and str(row.get(column)).strip()
        ]
        if parts:
            claims.append("，".join(parts) + "。")
    return claims


def _analysis_task(state: dict[str, Any]) -> AnalysisTask:
    for key in ("analysis_task_contract", "analysis_task"):
        value = state.get(key)
        if isinstance(value, AnalysisTask):
            task = value
            break
        if isinstance(value, dict):
            task = AnalysisTask.from_dict(value)
            break
    else:
        task = AnalysisTask(resolved_question=str(state.get("resolved_question") or state.get("user_question") or ""))
    if not task.resolved_question:
        task.resolved_question = str(state.get("resolved_question") or state.get("user_question") or "")
    if not task.metrics:
        task.metrics = [str(item) for item in (state.get("analysis_task") or {}).get("metrics") or [] if str(item)]
    if not task.dimensions:
        task.dimensions = [str(item) for item in (state.get("analysis_task") or {}).get("dimensions") or [] if str(item)]
    return task


def _rows_as_dicts(execution: dict[str, Any]) -> list[dict[str, Any]]:
    columns = _unique_columns([str(column) for column in execution.get("columns") or []])
    rows: list[dict[str, Any]] = []
    for row in execution.get("rows") or []:
        if isinstance(row, dict):
            rows.append(dict(row))
        elif isinstance(row, (list, tuple)):
            rows.append({columns[index]: value for index, value in enumerate(row) if index < len(columns)})
    return rows


def _unique_columns(columns: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    unique: list[str] = []
    for column in columns:
        counts[column] = counts.get(column, 0) + 1
        unique.append(column if counts[column] == 1 else f"{column}_{counts[column]}")
    return unique


def _pack_metrics(state: dict[str, Any], fact_payload: dict[str, Any]) -> list[str]:
    task = _analysis_task(state)
    return _unique_text(
        [
            *task.metrics,
            *[str(item) for item in fact_payload.get("metrics") or []],
            *[str(item) for item in state.get("selected_metrics") or []],
        ]
    )


def _chart_candidates(execution: dict[str, Any]) -> list[dict[str, Any]]:
    columns = [str(column) for column in execution.get("columns") or []]
    if len(columns) < 2 or not execution.get("rows"):
        return []
    return [{"chart_type": "bar", "columns": columns[:2], "status": "candidate"}]


def _planning_stops_before_evidence(state: dict[str, Any]) -> bool:
    planning = state.get("sql_planning") if isinstance(state.get("sql_planning"), dict) else {}
    if planning.get("source") in {"provider", "provider_unavailable"} and planning.get("strategy") in {
        "clarify",
        "reject",
    }:
        state["routing_strategy"] = str(planning.get("strategy") or "")
        state["error_message"] = str(planning.get("reason") or planning.get("error") or "SQL planning stopped.")
        return True
    return False


def _review_approved(state: dict[str, Any]) -> bool:
    review = state.get("review_result") if isinstance(state.get("review_result"), dict) else {}
    return bool(review.get("approved"))


def _review_data_limits(state: dict[str, Any]) -> list[str]:
    review = state.get("review_result") if isinstance(state.get("review_result"), dict) else {}
    if review.get("approved") is not False:
        return []
    issues = "；".join(str(issue) for issue in review.get("issues") or [] if str(issue).strip())
    return [f"SQL 审核未通过，本轮未执行查询：{issues}" if issues else "SQL 审核未通过，本轮未执行查询。"]


def _execution_data_limits(execution: dict[str, Any]) -> list[str]:
    if not execution or execution.get("success") is not False:
        return []
    error = str(execution.get("error") or "").strip()
    return [f"SQL 执行失败：{error}" if error else "SQL 执行失败。"]


def _record(
    calls: list[WorkbenchToolCall],
    tool_name: str,
    purpose: str,
    input_summary: Any,
    output_summary: Any,
    status: str,
) -> None:
    calls.append(
        WorkbenchToolCall(
            tool_name=tool_name,
            purpose=purpose,
            input_summary=str(input_summary or "")[:200],
            output_summary=str(output_summary or "")[:200],
            status=status or "completed",
        )
    )


def _status(payload: Any, *, default: str = "failed") -> str:
    if isinstance(payload, dict) and payload.get("success") is False:
        return "failed"
    return "completed" if isinstance(payload, dict) or default == "completed" else default


def _workspace_summary(state: dict[str, Any]) -> str:
    path = Path(str(state.get("db_path") or ""))
    return f"workspace_id={state.get('workspace_id') or ''} db={path.name}"


def _schema_summary(schema: Any) -> str:
    if not isinstance(schema, dict):
        return ""
    return f"tables={len(schema.get('tables') or [])}"


def _metric_summary(metric_context: Any) -> str:
    if not isinstance(metric_context, dict):
        return ""
    return f"matched_metrics={len(metric_context.get('matched_metrics') or [])}"


def _planning_summary(planning: Any) -> str:
    if not isinstance(planning, dict):
        return ""
    strategy = planning.get("query_strategy", planning.get("strategy", ""))
    scenario = planning.get("scenario_type", "")
    return f"strategy={strategy} scenario={scenario} missing={len(planning.get('missing_evidence') or [])}"


def _candidate_input_summary(state: dict[str, Any]) -> str:
    if state.get("initial_sql"):
        return "initial SQL supplied by caller"
    return f"strategy={state.get('sql_routing_strategy', '')}"


def _candidate_output_summary(state: dict[str, Any]) -> str:
    generation = state.get("sql_generation") if isinstance(state.get("sql_generation"), dict) else {}
    enhancement = state.get("llm_sql_enhancement") if isinstance(state.get("llm_sql_enhancement"), dict) else {}
    if enhancement:
        return f"llm_candidate accepted={enhancement.get('accepted', False)}"
    if generation:
        return f"generated={bool(generation.get('success'))} tables={len(generation.get('tables') or [])}"
    return f"generated={bool(state.get('generated_sql'))}"


def _review_summary(review: Any) -> str:
    if not isinstance(review, dict):
        return ""
    return f"approved={bool(review.get('approved'))} issues={len(review.get('issues') or [])}"


def _review_issue_summary(repair: Any) -> str:
    if not isinstance(repair, dict):
        return ""
    return str(repair.get("reason") or "")[:200]


def _schema_repair_summary(repair: Any) -> str:
    if not isinstance(repair, dict):
        return ""
    return f"candidate={bool(repair.get('repaired_sql_summary'))}"


def _execution_summary(execution: Any) -> str:
    if not isinstance(execution, dict):
        return ""
    if execution.get("success"):
        return f"rows={execution.get('row_count', 0)} columns={len(execution.get('columns') or [])}"
    return str(execution.get("error") or "")


def _sql_fix_summary(sql_fix: Any) -> str:
    if not isinstance(sql_fix, dict):
        return ""
    return f"success={bool(sql_fix.get('success'))} retry_count={sql_fix.get('retry_count', 0)}"


def _unique_text(items: list[str]) -> list[str]:
    ordered: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in ordered:
            ordered.append(text)
    return ordered


__all__ = ["run_evidence_agent_question_mode"]
