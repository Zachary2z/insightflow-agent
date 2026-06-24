from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from graph.workflow import run_workflow
from question_understanding.resolved_question import build_resolved_question
from workspaces.pending_clarification_store import PendingClarificationStore
from workspaces.product_result_builder import build_product_analysis_result
from workspaces.store import WorkspaceStore


def _with_product_result(result: dict, *, workspace_id: str) -> dict:
    product_result = build_product_analysis_result(result, workspace_id=workspace_id)
    result["product_result"] = product_result
    result["question_thread"] = product_result["question_thread"]
    result["business_answer"] = product_result["business_answer"]
    result["evidence"] = product_result["evidence"]
    result["chart_artifacts"] = product_result["chart_artifacts"]
    result["technical_details"] = product_result["technical_details"]
    return result


def run_workspace_analysis(
    store: WorkspaceStore,
    workspace_id: str,
    user_question: str,
    initial_sql: str | None = None,
    providers: dict | None = None,
) -> dict:
    workspace = store.get_workspace(workspace_id)
    run_id = f"run_{uuid4().hex[:8]}"
    run_dir = Path(workspace["root_path"]) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    provider_map = providers or {}
    result = run_workflow(
        user_question=user_question,
        db_path=workspace["analysis_db_path"],
        trace_dir=run_dir,
        run_id=run_id,
        initial_sql=initial_sql,
        workspace_id=workspace_id,
        workspace_root=workspace["root_path"],
        profile_path=workspace["profile_path"],
        semantic_layer_path=workspace["semantic_layer_path"],
        run_artifact_dir=run_dir,
        stop_for_clarification=True,
        question_understanding_provider=provider_map.get("question_understanding"),
        clarification_provider=provider_map.get("clarification"),
        sql_planning_provider=provider_map.get("sql_planning"),
        analysis_planner_provider=provider_map.get("analysis_planner"),
        visualization_agent_provider=provider_map.get("visualization_agent"),
        sql_candidate_provider=provider_map.get("sql_candidate"),
        insight_drafting_provider=provider_map.get("insight_drafting"),
        claim_typing_provider=provider_map.get("claim_typing"),
    )
    result["workspace_id"] = workspace_id
    result["workspace_run_dir"] = str(run_dir)
    result["original_question"] = user_question
    if result.get("status") == "waiting_for_clarification":
        clarification_question = _first_text(result.get("clarification_questions"))
        pending = PendingClarificationStore(store).create_pending_run(
            workspace_id=workspace_id,
            run_id=run_id,
            original_question=user_question,
            question_understanding=result.get("question_understanding") or {},
            clarification_question=clarification_question,
            raw_result=result,
            missing_fields=(result.get("clarification_result") or {}).get("missing_slots")
            or (result.get("question_understanding") or {}).get("missing_slots")
            or [],
        )
        result["pending_run_id"] = pending["pending_run_id"]
        result["clarification_question"] = clarification_question
        result["system_understanding"] = pending["system_understanding"]
        result["question_thread_status"] = "waiting_for_clarification"
    return _with_product_result(result, workspace_id=workspace_id)


def run_workspace_analysis_continuation(
    store: WorkspaceStore,
    workspace_id: str,
    pending_run_id: str,
    clarification_answer: str,
    providers: dict | None = None,
) -> dict:
    workspace = store.get_workspace(workspace_id)
    pending_store = PendingClarificationStore(store)
    pending = pending_store.load_pending_run(workspace_id, pending_run_id)
    if pending.get("status") != "pending":
        raise ValueError(f"Pending clarification run is not pending: {pending_run_id}")

    resolved_question = build_resolved_question(
        original_question=pending.get("original_question", ""),
        clarification_answer=clarification_answer,
        clarification_context=pending,
    )
    pending_store.complete_pending_run(
        workspace_id=workspace_id,
        pending_run_id=pending_run_id,
        clarification_answer=clarification_answer,
        resolved_question=resolved_question,
    )

    run_id = f"run_{uuid4().hex[:8]}"
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
        original_question=pending.get("original_question", ""),
        clarification_question=pending.get("clarification_question", ""),
        clarification_answer=clarification_answer,
        resolved_question=resolved_question,
        pending_run_id=pending_run_id,
        stop_for_clarification=False,
        question_understanding_provider=provider_map.get("question_understanding"),
        clarification_provider=provider_map.get("clarification"),
        sql_planning_provider=provider_map.get("sql_planning"),
        analysis_planner_provider=provider_map.get("analysis_planner"),
        visualization_agent_provider=provider_map.get("visualization_agent"),
        sql_candidate_provider=provider_map.get("sql_candidate"),
        insight_drafting_provider=provider_map.get("insight_drafting"),
        claim_typing_provider=provider_map.get("claim_typing"),
    )
    result["workspace_id"] = workspace_id
    result["workspace_run_dir"] = str(run_dir)
    result["original_question"] = pending.get("original_question", "")
    result["system_understanding"] = pending.get("system_understanding", "")
    result["pending_question_understanding"] = pending.get("question_understanding") or {}
    result["clarification_question"] = pending.get("clarification_question", "")
    result["clarification_answer"] = clarification_answer
    result["resolved_question"] = resolved_question
    result["pending_run_id"] = pending_run_id
    result["question_thread_status"] = result.get("status", "unknown")
    return _with_product_result(result, workspace_id=workspace_id)


def _first_text(value) -> str:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item
    if isinstance(value, str):
        return value
    return ""
