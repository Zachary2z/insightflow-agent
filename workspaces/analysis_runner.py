from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from graph.workflow import run_workflow
from observability.context import correlation_scope, get_correlation_context
from observability.logging import EventEmitter, emit_observability_event, safely_emit
from observability.metrics import InsightFlowMetrics, normalize_analysis_route, safe_metrics_scope, safely_get_metrics, safely_inc, safely_observe
from observability.redaction import classify_error
from question_understanding.resolved_question import build_resolved_question
from workspaces.analysis_thread_memory import (
    build_completed_follow_up_question,
    build_or_update_thread_memory,
)
from workspaces.product_result_builder import build_product_analysis_result
from workspaces.run_store import WorkspaceRunStore, normalize_question_for_reuse
from workspaces.store import WorkspaceStore


def _record_workflow_metric(
    metrics: InsightFlowMetrics,
    route: object,
    status: str,
    duration_seconds: float,
) -> None:
    try:
        labels = {"route": normalize_analysis_route(route), "status": status}
        safely_inc(metrics, "runs", labels)
        safely_observe(metrics, "run_duration", duration_seconds, labels)
        if status == "clarification":
            safely_inc(metrics, "clarifications", {"reason_category": "missing_context"})
    except BaseException:
        return


def _safe_analysis_route(result: object) -> object:
    try:
        return result.get("analysis_route") if type(result) is dict else None
    except BaseException:
        return None


def submit_workspace_analysis_run(
    store: WorkspaceStore,
    workspace_id: str,
    user_question: str,
    initial_sql: str | None = None,
    force_reanalysis: bool = False,
) -> dict:
    workspace = store.get_workspace(workspace_id)
    data_version = int(workspace.get("data_version") or 1)
    normalized_question = normalize_question_for_reuse(user_question)
    if not force_reanalysis and not initial_sql:
        matched = _find_cache_candidate(
            store,
            workspace_id,
            data_version=data_version,
            normalized_question=normalized_question,
        )
        if matched:
            return _cache_candidate_response(
                matched,
                workspace_id=workspace_id,
                data_version=data_version,
                normalized_question=normalized_question,
            )
    return create_workspace_analysis_run_shell(
        store=store,
        workspace_id=workspace_id,
        user_question=user_question,
        initial_sql=initial_sql,
        data_version=data_version,
        normalized_question=normalized_question,
    )


def create_workspace_analysis_run_shell(
    store: WorkspaceStore,
    workspace_id: str,
    user_question: str,
    initial_sql: str | None = None,
    data_version: int | None = None,
    normalized_question: str | None = None,
    run_id: str | None = None,
) -> dict:
    workspace = store.get_workspace(workspace_id)
    resolved_run_id = run_id or f"run_{uuid4().hex[:8]}"
    run_dir = Path(workspace["root_path"]) / "runs" / resolved_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    created_at = _now_iso()
    result = {
        "status": "running",
        "run_id": resolved_run_id,
        "workspace_id": workspace_id,
        "workspace_root": workspace["root_path"],
        "workspace_run_dir": str(run_dir),
        "trace_path": str(run_dir / f"{resolved_run_id}.json"),
        "original_question": user_question,
        "initial_sql": initial_sql or "",
        "data_version": int(data_version if data_version is not None else workspace.get("data_version") or 1),
        "normalized_question": normalized_question or normalize_question_for_reuse(user_question),
        "created_at": created_at,
        "saved_at": created_at,
        "execution_result": {},
        "trace": [],
    }
    result = _with_product_result(result, workspace_id=workspace_id)
    _persist_workspace_run_result(result)
    return result


def execute_workspace_analysis_job(
    store: WorkspaceStore,
    workspace_id: str,
    run_id: str,
    user_question: str,
    initial_sql: str | None = None,
    providers: dict | None = None,
    event_emitter: EventEmitter = emit_observability_event,
    metrics: InsightFlowMetrics | None = None,
) -> dict:
    started_at = perf_counter()
    selected_metrics = safely_get_metrics(metrics)
    with safe_metrics_scope(selected_metrics), correlation_scope(workspace_id=workspace_id, run_id=run_id):
        context = get_correlation_context()
        safely_emit(
            event_emitter,
            "workflow_run_started",
            request_id=context.get("request_id"),
            workspace_id=workspace_id,
            run_id=run_id,
            operation="analysis",
            status="started",
        )
        try:
            result = _execute_workspace_analysis_job(
                store=store,
                workspace_id=workspace_id,
                run_id=run_id,
                user_question=user_question,
                initial_sql=initial_sql,
                providers=providers,
            )
        except Exception as exc:
            elapsed_seconds = max(0.0, perf_counter() - started_at)
            safely_emit(
                event_emitter,
                "workflow_run_completed",
                request_id=context.get("request_id"),
                workspace_id=workspace_id,
                run_id=run_id,
                operation="analysis",
                status="error",
                error_type=classify_error(exc),
                latency_ms=max(0, int(elapsed_seconds * 1000)),
            )
            _record_workflow_metric(selected_metrics, None, "error", elapsed_seconds)
            raise
        succeeded = result.get("status") != "failed"
        metric_status = "clarification" if result.get("status") == "waiting_for_clarification" else ("success" if succeeded else "error")
        elapsed_seconds = max(0.0, perf_counter() - started_at)
        safely_emit(
            event_emitter,
            "workflow_run_completed",
            request_id=context.get("request_id"),
            workspace_id=workspace_id,
            run_id=run_id,
            operation="analysis",
            status="success" if succeeded else "error",
            error_type=None if succeeded else "workflow_failed",
            latency_ms=max(0, int(elapsed_seconds * 1000)),
        )
        _record_workflow_metric(selected_metrics, _safe_analysis_route(result), metric_status, elapsed_seconds)
        return result


def _execute_workspace_analysis_job(
    store: WorkspaceStore,
    workspace_id: str,
    run_id: str,
    user_question: str,
    initial_sql: str | None = None,
    providers: dict | None = None,
) -> dict:
    try:
        return run_workspace_analysis(
            store=store,
            workspace_id=workspace_id,
            user_question=user_question,
            initial_sql=initial_sql,
            providers=providers,
            force_reanalysis=True,
            run_id=run_id,
        )
    except Exception as exc:
        workspace = store.get_workspace(workspace_id)
        run_dir = Path(workspace["root_path"]) / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "status": "failed",
            "run_id": run_id,
            "workspace_id": workspace_id,
            "workspace_root": workspace["root_path"],
            "workspace_run_dir": str(run_dir),
            "trace_path": str(run_dir / f"{run_id}.json"),
            "original_question": user_question,
            "initial_sql": initial_sql or "",
            "data_version": int(workspace.get("data_version") or 1),
            "normalized_question": normalize_question_for_reuse(user_question),
            "saved_at": _now_iso(),
            "error_message": str(exc),
            "execution_result": {},
            "trace": [],
        }
        result = _with_product_result(result, workspace_id=workspace_id)
        _persist_workspace_run_result(result)
        return result


def _with_product_result(result: dict, *, workspace_id: str) -> dict:
    product_result = build_product_analysis_result(
        result,
        workspace_id=workspace_id,
        workspace_root=result.get("workspace_root") or _workspace_root_from_result(result),
    )
    result["product_result"] = product_result
    result["question_thread"] = product_result["question_thread"]
    result["analysis_route"] = product_result["analysis_route"]
    result["progress_steps"] = product_result["progress_steps"]
    result["business_answer"] = product_result["business_answer"]
    result["evidence"] = product_result["evidence"]
    result["chart_artifacts"] = product_result["chart_artifacts"]
    result["technical_details"] = product_result["technical_details"]
    return result


def _with_thread_memory(
    result: dict,
    *,
    thread_id: str,
    user_input: str,
    original_question: str,
    previous_memory: dict | None = None,
) -> dict:
    result["analysis_thread_memory"] = build_or_update_thread_memory(
        result,
        thread_id=thread_id,
        user_input=user_input,
        original_question=original_question,
        previous_memory=previous_memory,
    )
    return result


def _persist_workspace_run_result(result: dict) -> None:
    trace_path = result.get("trace_path")
    run_id = result.get("run_id")
    if trace_path:
        path = Path(trace_path)
    elif result.get("workspace_run_dir") and run_id:
        path = Path(result["workspace_run_dir"]) / f"{run_id}.json"
    else:
        return

    saved_at = result.get("saved_at") or ""
    if not saved_at and path.exists():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(previous, dict):
                saved_at = str(previous.get("saved_at") or "")
        except (OSError, json.JSONDecodeError):
            saved_at = ""

    payload = dict(result)
    if saved_at:
        payload["saved_at"] = saved_at
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def run_workspace_analysis(
    store: WorkspaceStore,
    workspace_id: str,
    user_question: str,
    initial_sql: str | None = None,
    providers: dict | None = None,
    force_reanalysis: bool = False,
    run_id: str | None = None,
) -> dict:
    workspace = store.get_workspace(workspace_id)
    data_version = int(workspace.get("data_version") or 1)
    normalized_question = normalize_question_for_reuse(user_question)
    if not force_reanalysis and not initial_sql:
        matched = _find_cache_candidate(
            store,
            workspace_id,
            data_version=data_version,
            normalized_question=normalized_question,
        )
        if matched:
            return _cache_candidate_response(
                matched,
                workspace_id=workspace_id,
                data_version=data_version,
                normalized_question=normalized_question,
            )
    resolved_run_id = run_id or f"run_{uuid4().hex[:8]}"
    run_dir = Path(workspace["root_path"]) / "runs" / resolved_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    provider_map = providers or {}
    result = run_workflow(
        user_question=user_question,
        db_path=workspace["analysis_db_path"],
        trace_dir=run_dir,
        run_id=resolved_run_id,
        initial_sql=initial_sql,
        workspace_id=workspace_id,
        workspace_root=workspace["root_path"],
        profile_path=workspace["profile_path"],
        semantic_layer_path=workspace["semantic_layer_path"],
        run_artifact_dir=run_dir,
        data_version=data_version,
        stop_for_clarification=True,
        question_understanding_provider=provider_map.get("question_understanding"),
        clarification_provider=provider_map.get("clarification"),
        sql_planning_provider=provider_map.get("sql_planning"),
        visualization_agent_provider=provider_map.get("visualization_agent"),
        sql_candidate_provider=provider_map.get("sql_candidate"),
        business_answer_provider=provider_map.get("business_answer"),
    )
    result["workspace_id"] = workspace_id
    result["workspace_run_dir"] = str(run_dir)
    result["original_question"] = user_question
    result["data_version"] = data_version
    result["normalized_question"] = normalized_question
    if result.get("status") == "waiting_for_clarification":
        clarification_question = _first_text(result.get("clarification_questions"))
        result["clarification_question"] = clarification_question
        result["question_thread_status"] = "waiting_for_clarification"
    result = _with_thread_memory(
        result,
        thread_id=resolved_run_id,
        user_input=user_question,
        original_question=user_question,
    )
    result = _with_product_result(result, workspace_id=workspace_id)
    _persist_workspace_run_result(result)
    return result


def run_workspace_analysis_follow_up(
    store: WorkspaceStore,
    workspace_id: str,
    run_id: str,
    message: str,
    providers: dict | None = None,
    event_emitter: EventEmitter = emit_observability_event,
    metrics: InsightFlowMetrics | None = None,
) -> dict:
    started_at = perf_counter()
    selected_metrics = safely_get_metrics(metrics)
    with safe_metrics_scope(selected_metrics), correlation_scope(workspace_id=workspace_id, run_id=run_id):
        context = get_correlation_context()
        safely_emit(
            event_emitter,
            "workflow_run_started",
            request_id=context.get("request_id"),
            workspace_id=workspace_id,
            run_id=run_id,
            operation="analysis_follow_up",
            status="started",
        )
        try:
            result = _run_workspace_analysis_follow_up(
                store=store,
                workspace_id=workspace_id,
                run_id=run_id,
                message=message,
                providers=providers,
            )
        except Exception as exc:
            elapsed_seconds = max(0.0, perf_counter() - started_at)
            safely_emit(
                event_emitter,
                "workflow_run_completed",
                request_id=context.get("request_id"),
                workspace_id=workspace_id,
                run_id=run_id,
                operation="analysis_follow_up",
                status="error",
                error_type=classify_error(exc),
                latency_ms=max(0, int(elapsed_seconds * 1000)),
            )
            _record_workflow_metric(selected_metrics, None, "error", elapsed_seconds)
            raise
        succeeded = result.get("status") != "failed"
        metric_status = "clarification" if result.get("status") == "waiting_for_clarification" else ("success" if succeeded else "error")
        elapsed_seconds = max(0.0, perf_counter() - started_at)
        safely_emit(
            event_emitter,
            "workflow_run_completed",
            request_id=context.get("request_id"),
            workspace_id=workspace_id,
            run_id=run_id,
            operation="analysis_follow_up",
            status="success" if succeeded else "error",
            error_type=None if succeeded else "workflow_failed",
            latency_ms=max(0, int(elapsed_seconds * 1000)),
        )
        _record_workflow_metric(selected_metrics, _safe_analysis_route(result), metric_status, elapsed_seconds)
        return result


def _run_workspace_analysis_follow_up(
    store: WorkspaceStore,
    workspace_id: str,
    run_id: str,
    message: str,
    providers: dict | None = None,
) -> dict:
    workspace = store.get_workspace(workspace_id)
    existing_response = WorkspaceRunStore(store).load_run_response(workspace_id, run_id)
    existing = existing_response.get("result") if isinstance(existing_response.get("result"), dict) else {}
    memory = existing.get("analysis_thread_memory") if isinstance(existing.get("analysis_thread_memory"), dict) else {}
    if not memory:
        memory = build_or_update_thread_memory(
            existing,
            thread_id=run_id,
            user_input=str(existing.get("original_question") or ""),
            original_question=str(existing.get("original_question") or ""),
        )

    original_question = str(memory.get("original_question") or existing.get("original_question") or "")
    latest_status = str(memory.get("latest_status") or existing.get("status") or "")
    if latest_status == "waiting_for_clarification":
        resolved_question = build_resolved_question(
            original_question=original_question,
            clarification_answer=message,
            clarification_context=memory.get("pending_clarification") if isinstance(memory.get("pending_clarification"), dict) else {},
        )
    else:
        resolved_question = build_completed_follow_up_question(memory=memory, message=message)

    data_version = int(workspace.get("data_version") or 1)
    run_dir = Path(workspace["root_path"]) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    provider_map = providers or {}
    result = run_workflow(
        user_question=resolved_question,
        db_path=workspace["analysis_db_path"],
        trace_dir=run_dir,
        run_id=run_id,
        workspace_id=workspace_id,
        workspace_root=workspace["root_path"],
        profile_path=workspace["profile_path"],
        semantic_layer_path=workspace["semantic_layer_path"],
        run_artifact_dir=run_dir,
        data_version=data_version,
        original_question=original_question,
        clarification_question=str((memory.get("pending_clarification") or {}).get("clarification_question") or ""),
        clarification_answer=message if latest_status == "waiting_for_clarification" else "",
        resolved_question=resolved_question,
        stop_for_clarification=True,
        question_understanding_provider=provider_map.get("question_understanding"),
        clarification_provider=provider_map.get("clarification"),
        sql_planning_provider=provider_map.get("sql_planning"),
        visualization_agent_provider=provider_map.get("visualization_agent"),
        sql_candidate_provider=provider_map.get("sql_candidate"),
        business_answer_provider=provider_map.get("business_answer"),
    )
    result["workspace_id"] = workspace_id
    result["workspace_run_dir"] = str(run_dir)
    result["original_question"] = original_question
    result["data_version"] = data_version
    result["normalized_question"] = normalize_question_for_reuse(resolved_question)
    result["resolved_question"] = resolved_question
    result["created_at"] = existing.get("created_at") or existing.get("saved_at") or _now_iso()
    result["saved_at"] = _now_iso()
    if latest_status == "waiting_for_clarification":
        result["clarification_answer"] = message
    if result.get("status") == "waiting_for_clarification":
        result["clarification_question"] = _first_text(result.get("clarification_questions"))
        result["question_thread_status"] = "waiting_for_clarification"
    else:
        result["question_thread_status"] = result.get("status", "unknown")
    result = _with_thread_memory(
        result,
        thread_id=run_id,
        user_input=message,
        original_question=original_question,
        previous_memory=memory,
    )
    result = _with_product_result(result, workspace_id=workspace_id)
    _persist_workspace_run_result(result)
    return result


def _first_text(value) -> str:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item
    if isinstance(value, str):
        return value
    return ""


def _workspace_root_from_result(result: dict) -> str:
    run_dir = result.get("workspace_run_dir")
    if not run_dir:
        return ""
    path = Path(run_dir)
    if path.name.startswith("run_") and path.parent.name == "runs":
        return str(path.parent.parent)
    return ""


def _find_cache_candidate(
    store: WorkspaceStore,
    workspace_id: str,
    *,
    data_version: int,
    normalized_question: str,
) -> dict | None:
    try:
        return WorkspaceRunStore(store).find_reusable_run(
            workspace_id,
            data_version=data_version,
            normalized_question=normalized_question,
        )
    except Exception:
        return None


def _cache_candidate_response(
    matched: dict,
    *,
    workspace_id: str,
    data_version: int,
    normalized_question: str,
) -> dict:
    return {
        "status": "cache_candidate",
        "matched_run_id": matched["run_id"],
        "message": "已找到同一数据版本下的历史分析",
        "workspace_id": workspace_id,
        "data_version": data_version,
        "normalized_question": normalized_question,
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
