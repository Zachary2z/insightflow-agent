from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    success: bool
    run_id: str
    session_id: str
    user_question: str
    task_type: str
    report_type: str
    report_plan: dict[str, Any]
    report_sections: list[dict[str, Any]]
    report_sub_tasks: list[dict[str, Any]]
    clarification_questions: list[str]

    db_path: str | Path
    trace_dir: str | Path
    initial_sql: str

    database_schema: dict[str, Any]
    schema_text: str

    metric_context: dict[str, Any]
    business_context: dict[str, Any]
    evidence_result: dict[str, Any]
    claims_to_validate: list[str]
    chart_result: dict[str, Any]
    chart_path: str
    chart_paths: list[str]
    report_result: dict[str, Any]
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

    execution_result: dict[str, Any]
    error_message: str
    sql_fix: dict[str, Any]
    fixed_sql: str
    retry_count: int

    insight: dict[str, Any]
    final_answer: str
    data_used: bool

    trace: list[dict[str, Any]]
    trace_save_result: dict[str, Any]
    trace_path: str
    status: str
