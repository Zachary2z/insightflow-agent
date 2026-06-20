from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from llm_ops.deepseek_provider import DEFAULT_DEEPSEEK_BASE_URL, DEFAULT_DEEPSEEK_MODEL, normalize_deepseek_model
from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.runtime_provider import (
    provider_action_drafter_enabled,
    provider_business_review_planner_enabled,
    provider_claim_typing_enabled,
    provider_clarification_router_enabled,
    provider_question_understanding_enabled,
    provider_report_writer_enabled,
    provider_sql_candidate_enabled,
    provider_sql_planning_enabled,
)


CAPABILITY_CATALOG: list[dict[str, Any]] = [
    {
        "label": "SQL Analysis",
        "phase": "P0",
        "status": "available",
        "entrypoint": "run_demo_question() -> run_workflow()",
        "requires_api_key": "no",
        "safety_boundary": "validate_sql(), SQL Reviewer, run_sql(), Trace Logger",
    },
    {
        "label": "Evidence-backed Report",
        "phase": "P1",
        "status": "available",
        "entrypoint": "run_report_generation_demo()",
        "requires_api_key": "no",
        "safety_boundary": "Evidence Validator before Chart/Report output",
    },
    {
        "label": "Weekly Business Review",
        "phase": "P2",
        "status": "provider-optional",
        "entrypoint": "run_weekly_review_demo()",
        "requires_api_key": "optional",
        "safety_boundary": "Allowlisted sections; SQL review/execution per subtask",
    },
    {
        "label": "Approval-gated Action Workflow",
        "phase": "P2",
        "status": "provider-optional",
        "entrypoint": "run_action_workflow_demo()",
        "requires_api_key": "optional",
        "safety_boundary": "Risk Assessor, Approval Gate, Action Executor, Audit Logger",
    },
    {
        "label": "MCP Tool Layer",
        "phase": "P3",
        "status": "available",
        "entrypoint": "build_mcp_contract_summary()",
        "requires_api_key": "no",
        "safety_boundary": "External contracts wrap existing safe tools only",
    },
    {
        "label": "FastAPI Async Run API",
        "phase": "P3",
        "status": "local-api",
        "entrypoint": "build_async_run_api_summary()",
        "requires_api_key": "no",
        "safety_boundary": "RunManager calls run_workflow(), trace/events are read-only",
    },
    {
        "label": "Trace Dashboard",
        "phase": "P3",
        "status": "available",
        "entrypoint": "build_trace_dashboard_summary()",
        "requires_api_key": "no",
        "safety_boundary": "Observability reads traces, eval summaries, approvals, audit logs",
    },
    {
        "label": "LLM Provider & PromptOps",
        "phase": "P3",
        "status": "provider-optional",
        "entrypoint": "build_llm_ops_summary()",
        "requires_api_key": "optional",
        "safety_boundary": "Structured output validation and deterministic fallback",
    },
    {
        "label": "Template Mining & Eval",
        "phase": "P3",
        "status": "available",
        "entrypoint": "sql_planning.feedback / llm_ops.eval_smoke",
        "requires_api_key": "no",
        "safety_boundary": "Recommendations are never auto-applied",
    },
]

SOURCE_FIELDS: list[tuple[str, str, str]] = [
    ("Question Understanding", "question_understanding", "Does not generate or execute SQL"),
    ("Clarification Router", "clarification_result", "Stops incomplete provider clarification before SQL"),
    ("SQL Planning Router", "sql_planning", "Routes source but cannot return executable SQL directly"),
    ("Guarded SQL Candidate", "llm_sql_enhancement", "Accepted candidates still require validate_sql() and SQL Reviewer"),
    ("Report Planner", "report_plan", "Selects allowlisted report sections only"),
    ("Claim Typing", "claim_typing_result", "Advisory only; Evidence Validator decides final evidence"),
    ("Report Writer", "report_writer_result", "Can polish only Evidence Validator-approved material"),
    ("Action Drafter", "action_draft_result", "Cannot create actions or bypass approval/audit"),
]

SAFETY_BOUNDARIES = [
    {"boundary": "validate_sql()", "status": "mandatory", "owner": "SQL Reviewer"},
    {"boundary": "SQL Reviewer", "status": "mandatory", "owner": "graph.review"},
    {"boundary": "SQL Execution", "status": "tool-owned", "owner": "run_sql()"},
    {"boundary": "Evidence Validator", "status": "mandatory before reports/actions", "owner": "agents.evidence_validator"},
    {"boundary": "Approval Gate", "status": "mandatory for action creation", "owner": "tools.approval_tool"},
    {"boundary": "Audit Logger", "status": "mandatory for action workflow", "owner": "tools.audit_logger"},
    {"boundary": "Trace Logger", "status": "mandatory", "owner": "tools.trace_logger"},
]


def build_capability_overview() -> list[dict[str, Any]]:
    return [dict(item) for item in CAPABILITY_CATALOG]


def _source_label(source: str, provider_called: bool, fallback_used: bool) -> str:
    if provider_called and fallback_used:
        return "Deterministic fallback"
    if provider_called:
        return "DeepSeek Provider"
    if source == "provider":
        return "DeepSeek Provider"
    return "Deterministic baseline"


def _source_card(module: str, state_key: str, boundary: str, payload: dict[str, Any]) -> dict[str, Any]:
    provider_called = bool(payload.get("provider_called", False))
    fallback_used = bool(payload.get("fallback_used", False))
    source = str(payload.get("source", "deterministic") or "deterministic")
    validation_error = str(payload.get("validation_error", "") or "")
    provider_error = str(payload.get("provider_error", "") or payload.get("error", "") or "")
    validation_status = "failed" if validation_error else "passed"
    if not provider_called and not payload:
        validation_status = "not applicable"
    return {
        "module": module,
        "state_key": state_key,
        "source": source,
        "source_label": _source_label(source, provider_called, fallback_used),
        "provider_called": provider_called,
        "fallback_used": fallback_used,
        "prompt_id": str(payload.get("prompt_id", "") or payload.get("provider_prompt_id", "") or ""),
        "prompt_version": str(payload.get("prompt_version", "") or ""),
        "validation_status": validation_status,
        "validation_error": validation_error,
        "provider_error": provider_error,
        "boundary": boundary,
    }


def build_source_cards(state: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for module, state_key, boundary in SOURCE_FIELDS:
        payload = state.get(state_key, {})
        cards.append(_source_card(module, state_key, boundary, payload if isinstance(payload, dict) else {}))
    return cards


def build_trace_timeline(state_or_trace: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    events = state_or_trace if isinstance(state_or_trace, list) else state_or_trace.get("trace", [])
    timeline = []
    for event in events:
        timeline.append(
            {
                "node": str(event.get("node", "") or ""),
                "tool_name": str(event.get("tool_name", "") or ""),
                "status": str(event.get("status", "") or ""),
                "latency_ms": int(event.get("latency_ms") or 0),
                "retry_count": int(event.get("retry_count") or 0),
                "provider_called": bool(event.get("provider_called", False)),
                "fallback_used": bool(event.get("fallback_used", False)),
                "error_type": str(event.get("error_type", "") or ""),
                "error": str(event.get("error", "") or ""),
            }
        )
    return timeline


def _rows_as_records(execution_result: dict[str, Any]) -> list[dict[str, Any]]:
    columns = execution_result.get("columns", [])
    rows = execution_result.get("rows", [])
    return [dict(zip(columns, row, strict=False)) for row in rows]


def build_run_detail_view_model(state: dict[str, Any]) -> dict[str, Any]:
    execution_result = state.get("execution_result", {}) or {}
    evidence_result = state.get("evidence_result", {}) or {}
    return {
        "question": state.get("user_question", ""),
        "status": state.get("status", "not_started"),
        "answer": state.get("final_answer", ""),
        "intent": state.get("intent_slots", {}) or state.get("question_understanding", {}).get("intent", {}),
        "clarification_questions": state.get("clarification_questions", []),
        "sql": state.get("generated_sql", ""),
        "sql_reason": state.get("sql_reason", ""),
        "review_result": state.get("review_result", {}),
        "execution_result": execution_result,
        "execution_rows": _rows_as_records(execution_result),
        "sql_fix": state.get("sql_fix", {}),
        "evidence": evidence_result,
        "chart_paths": state.get("chart_paths") or ([state["chart_path"]] if state.get("chart_path") else []),
        "report_path": state.get("report_path", "") or state.get("weekly_report_path", ""),
        "report_sections": state.get("report_sections", []),
        "report_sub_tasks": state.get("report_sub_tasks", []),
        "action": {
            "plan": state.get("action_plan", {}),
            "risk_assessment": state.get("risk_assessment", {}),
            "approval_status": state.get("approval_status", ""),
            "created_actions": state.get("created_actions", []),
            "verification": state.get("action_verification_result", {}),
            "audit_log_id": state.get("audit_log_id", ""),
        },
        "trace_path": state.get("trace_path", ""),
        "trace_timeline": build_trace_timeline(state),
        "sources": build_source_cards(state),
        "safety_boundaries": list(SAFETY_BOUNDARIES),
    }


def _load_env_values(env_path: str | Path = ".env", env: dict[str, str] | None = None) -> dict[str, str]:
    if env is not None:
        return {key: str(value) for key, value in env.items()}
    path = Path(env_path)
    file_values = {key: str(value or "") for key, value in dotenv_values(path).items()} if path.exists() else {}
    return {**file_values, **os.environ}


def build_llm_ops_summary(env: dict[str, str] | None = None, env_path: str | Path = ".env") -> dict[str, Any]:
    values = _load_env_values(env_path=env_path, env=env)
    configured = bool(str(values.get("DEEPSEEK_API_KEY", "")).strip())
    model = normalize_deepseek_model(str(values.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)))
    runtime_switches = {
        "question_understanding": provider_question_understanding_enabled(values),
        "clarification_router": provider_clarification_router_enabled(values),
        "sql_planning_router": provider_sql_planning_enabled(values),
        "guarded_sql_candidate": provider_sql_candidate_enabled(values),
        "business_review_planner": provider_business_review_planner_enabled(values),
        "report_writer": provider_report_writer_enabled(values),
        "insight_claim_typer": provider_claim_typing_enabled(values),
        "action_drafter": provider_action_drafter_enabled(values),
    }
    prompts = [
        {
            "prompt_id": prompt["prompt_id"],
            "prompt_version": prompt["prompt_version"],
            "description": prompt["description"],
        }
        for prompt in DEFAULT_PROMPT_REGISTRY.list_prompts().values()
    ]
    return {
        "provider": {
            "name": "DeepSeek",
            "configured": configured,
            "status": "configured / provider optional" if configured else "deterministic / not configured",
            "model": model,
            "base_url": str(values.get("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL) or DEFAULT_DEEPSEEK_BASE_URL),
            "api_key": "configured" if configured else "not configured",
        },
        "runtime_switches": runtime_switches,
        "deterministic_baseline": {
            "available": True,
            "requires_api_key": False,
            "status": "active when provider switch/key is absent or validation fails",
        },
        "prompt_registry": prompts,
    }


def build_llm_runtime_participation(states: list[dict[str, Any]]) -> dict[str, Any]:
    cards = [card for state in states for card in build_source_cards(state)]
    provider_called_count = sum(1 for card in cards if card["provider_called"])
    fallback_used_count = sum(1 for card in cards if card["fallback_used"])
    validation_errors = [card for card in cards if card["validation_error"]]
    provider_errors = [card for card in cards if card["provider_error"]]
    return {
        "provider_called_count": provider_called_count,
        "fallback_used_count": fallback_used_count,
        "validation_error_count": len(validation_errors),
        "provider_error_count": len(provider_errors),
        "validation_errors": validation_errors,
        "provider_errors": provider_errors,
    }


def build_observability_view_model(summary: dict[str, Any]) -> dict[str, Any]:
    eval_metrics = summary.get("eval_metrics", {}) or {}
    approval_records = summary.get("approval_records", []) or []
    audit_logs = summary.get("audit_logs", []) or []
    return {
        "metrics": {
            "trace_count": summary.get("trace_count", 0),
            "event_count": summary.get("event_count", 0),
            "sql_fix_count": summary.get("sql_fix_count", 0),
            "eval_pass_rate": eval_metrics.get("pass_rate", 0.0),
            "approval_count": len(approval_records),
            "audit_log_count": len(audit_logs),
        },
        "node_latency": [
            {"node": node, **values}
            for node, values in (summary.get("agent_node_latency_ms", {}) or {}).items()
        ],
        "tool_call_counts": [
            {"tool_name": tool_name, "count": count}
            for tool_name, count in (summary.get("tool_call_counts", {}) or {}).items()
        ],
        "failure_distribution": [
            {"failure_type": failure_type, "count": count}
            for failure_type, count in (summary.get("failure_type_distribution", {}) or {}).items()
        ],
        "approval_records": approval_records,
        "audit_logs": audit_logs,
        "load_errors": summary.get("load_errors", []) or [],
        "raw": summary,
    }
