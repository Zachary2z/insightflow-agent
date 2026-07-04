from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    success: bool
    run_id: str
    session_id: str
    user_question: str
    original_question: str
    clarification_question: str
    clarification_answer: str
    resolved_question: str
    pending_run_id: str
    question_thread_status: str
    stop_for_clarification: bool
    task_type: str
    report_type: str
    report_plan: dict[str, Any]
    report_sections: list[dict[str, Any]]
    report_sub_tasks: list[dict[str, Any]]
    clarification_questions: list[str]
    llm_sql_enhancement: dict[str, Any]
    llm_insight_enhancement: dict[str, Any]
    claim_typing_result: dict[str, Any]
    question_understanding: dict[str, Any]
    analysis_task: dict[str, Any]
    analysis_task_contract: dict[str, Any]
    analysis_route: dict[str, Any]
    question_evidence_pack: dict[str, Any]
    question_evidence_cache: dict[str, Any]
    workbench_tool_calls: list[dict[str, Any]]
    evidence_agent_early_response: bool
    fast_fact_context_pack: dict[str, Any]
    intent_slots: dict[str, Any]
    routing_strategy: str
    clarification_result: dict[str, Any]
    sql_planning: dict[str, Any]
    sql_routing_strategy: str
    comparison_scope_adjustment: dict[str, Any]
    analysis_plan: dict[str, Any]
    scenario_type: str
    analysis_steps: list[dict[str, Any]]
    visualization_decision: dict[str, Any]
    visualization_plan: dict[str, Any]
    visualization_delivery_result: dict[str, Any]
    visualization_trace: dict[str, Any]
    llm_sql_enhancement: dict[str, Any]
    action_plan: dict[str, Any]
    risk_assessment: dict[str, Any]
    approval_status: str
    approval_record: dict[str, Any]
    created_actions: list[dict[str, Any]]
    action_execution_result: dict[str, Any]
    action_verification_result: dict[str, Any]
    audit_log_result: dict[str, Any]
    audit_log_id: str
    action_db_path: str | Path

    db_path: str | Path
    trace_dir: str | Path
    initial_sql: str
    workspace_id: str | None
    workspace_root: str | None
    profile_path: str | None
    semantic_layer_path: str | None
    workspace_context: dict[str, Any]
    run_artifact_dir: str | None
    data_version: int

    database_schema: dict[str, Any]
    schema_text: str

    metric_context: dict[str, Any]
    business_context: dict[str, Any]
    evidence_result: dict[str, Any]
    audit_result: dict[str, Any]
    claims_to_validate: list[str]
    chart_result: dict[str, Any]
    chart_path: str
    chart_paths: list[str]
    report_result: dict[str, Any]
    report_writer_result: dict[str, Any]
    report_path: str
    weekly_report_result: dict[str, Any]
    weekly_report_path: str
    selected_tables: list[str]
    selected_metrics: list[str]

    sql_generation: dict[str, Any]
    generated_sql: str
    sql_reason: str
    review_result: dict[str, Any]
    review_retry_count: int
    schema_repair_attempted: bool
    schema_repair_succeeded: bool
    schema_repair_reason: str
    schema_repair: dict[str, Any]
    schema_repair_pending_review: bool

    execution_result: dict[str, Any]
    error_message: str
    sql_fix: dict[str, Any]
    fixed_sql: str
    retry_count: int

    insight: dict[str, Any]
    answer_review: dict[str, Any]
    answer_composition: dict[str, Any]
    business_answer: dict[str, Any]
    final_answer: str
    data_used: bool

    trace: list[dict[str, Any]]
    trace_save_result: dict[str, Any]
    trace_path: str
    status: str
