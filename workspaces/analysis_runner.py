from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from graph.workflow import run_workflow
from workspaces.product_result_builder import build_product_analysis_result
from workspaces.store import WorkspaceStore


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
    product_result = build_product_analysis_result(result, workspace_id=workspace_id)
    result["product_result"] = product_result
    result["question_thread"] = product_result["question_thread"]
    result["business_answer"] = product_result["business_answer"]
    result["evidence"] = product_result["evidence"]
    result["chart_artifacts"] = product_result["chart_artifacts"]
    result["technical_details"] = product_result["technical_details"]
    return result
