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
    provider_visualization_agent_enabled,
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
        "safety_boundary": "Evidence Validator before visualization/report output",
    },
    {
        "label": "Visualization Agent Delivery",
        "phase": "P8",
        "status": "provider-optional",
        "entrypoint": "agents.visualization_agent.run_visualization_agent()",
        "requires_api_key": "optional",
        "safety_boundary": "Chart Validator, delivery policy, external visualization adapters",
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
    ("Visualization Agent", "visualization_decision", "Chooses chart/delivery only; validators and policies execute tools"),
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
    {"boundary": "Chart Validator", "status": "mandatory before visualization delivery", "owner": "visualization.chart_validator"},
    {"boundary": "Tool Policy", "status": "mandatory before external delivery adapters", "owner": "visualization_delivery/action_delivery"},
    {"boundary": "Approval Gate", "status": "mandatory for action creation", "owner": "tools.approval_tool"},
    {"boundary": "Audit Logger", "status": "mandatory for action workflow", "owner": "tools.audit_logger"},
    {"boundary": "Trace Logger", "status": "mandatory", "owner": "tools.trace_logger"},
]

RUN_DETAIL_SECTIONS: list[dict[str, str]] = [
    {
        "id": "ask",
        "title": "01 · Ask",
        "summary": "Business question, selected run context, and provider mode.",
    },
    {
        "id": "executive_answer",
        "title": "02 · Executive Answer",
        "summary": "Final answer, workflow status, row count, evidence status, and safety status.",
    },
    {
        "id": "data",
        "title": "03 · Data",
        "summary": "Generated SQL, SQL review, execution table, and repair details.",
    },
    {
        "id": "visualization_delivery",
        "title": "04 · Visualization Delivery",
        "summary": "Visualization Agent decision, delivery tool, artifact, and data hygiene.",
    },
    {
        "id": "evidence_report",
        "title": "05 · Evidence & Report",
        "summary": "Evidence Validator results, unsupported claims, chart paths, and report outputs.",
    },
    {
        "id": "action_approval",
        "title": "06 · Action & Approval",
        "summary": "Action drafts, risk assessment, approval state, created actions, and audit id.",
    },
    {
        "id": "trace_system",
        "title": "07 · Trace & System Details",
        "summary": "Agent pipeline, tool calls, validator gates, artifacts, source metadata, and trace JSON.",
    },
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


def _step_kind(event: dict[str, Any]) -> str:
    node = str(event.get("node", "") or "").lower()
    tool_name = str(event.get("tool_name", "") or "")
    if "validator" in node or tool_name in {"validate_sql"}:
        return "validator_gate"
    if "approval" in node or "audit" in node:
        return "approval_audit_gate"
    if tool_name:
        return "tool_call"
    return "agent_decision"


def build_agent_pipeline(state: dict[str, Any]) -> list[dict[str, Any]]:
    pipeline = []
    for index, event in enumerate(state.get("trace", []) or [], start=1):
        pipeline.append(
            {
                "step": index,
                "agent": str(event.get("node", "") or ""),
                "kind": _step_kind(event),
                "tool_name": str(event.get("tool_name", "") or ""),
                "status": str(event.get("status", "") or ""),
                "provider_called": bool(event.get("provider_called", False)),
                "fallback_used": bool(event.get("fallback_used", False)),
                "prompt_id": str(event.get("prompt_id", "") or event.get("provider_prompt_id", "") or ""),
                "validation_error": str(event.get("validation_error", "") or ""),
                "provider_error": str(event.get("provider_error", "") or ""),
                "error": str(event.get("error", "") or ""),
            }
        )
    return pipeline


def _tool_category(tool_name: str) -> str:
    if tool_name in {"get_database_schema", "retrieve_metric_definition"}:
        return "context_tool"
    if tool_name in {"validate_sql", "run_sql"}:
        return "sql_tool"
    if "chart" in tool_name or "visualization" in tool_name:
        return "visualization_tool"
    if "audit" in tool_name or "approval" in tool_name:
        return "approval_audit_tool"
    return "tool"


def _delivery_tool_cards(state: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    delivery_results = []
    visualization_delivery = state.get("visualization_delivery_result", {})
    if isinstance(visualization_delivery, dict) and visualization_delivery:
        delivery_results.append(visualization_delivery)
    action_execution = state.get("action_execution_result", {})
    if isinstance(action_execution, dict):
        delivery_results.extend(action_execution.get("delivery_results", []) or [])

    for result in delivery_results:
        if not isinstance(result, dict):
            continue
        cards.append(
            {
                "tool_name": str(result.get("delivery_tool_id", "") or ""),
                "tool_category": "delivery_adapter",
                "delivery_tool_id": str(result.get("delivery_tool_id", "") or ""),
                "tool_type": str(result.get("tool_type", "") or ""),
                "status": "success" if result.get("success") else "error",
                "external_tool_called": bool(result.get("external_tool_called", False)),
                "artifact": str(result.get("artifact_url", "") or result.get("artifact_path", "") or ""),
                "policy_status": "passed" if (result.get("policy_result", {}) or {}).get("success", False) else "failed",
                "error": str(result.get("error", "") or (result.get("policy_result", {}) or {}).get("validation_error", "") or ""),
            }
        )
    return cards


def build_tool_call_cards(state: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for event in state.get("trace", []) or []:
        tool_name = str(event.get("tool_name", "") or "")
        if not tool_name:
            continue
        cards.append(
            {
                "tool_name": tool_name,
                "tool_category": _tool_category(tool_name),
                "delivery_tool_id": "",
                "tool_type": "",
                "status": str(event.get("status", "") or ""),
                "external_tool_called": bool(event.get("external_tool_called", False)),
                "artifact": "",
                "policy_status": "",
                "error": str(event.get("error", "") or ""),
            }
        )
    cards.extend(_delivery_tool_cards(state))
    return cards


def _gate_status_from_bool(value: Any) -> str:
    if value is True:
        return "passed"
    if value is False:
        return "failed"
    return "not run"


def build_validator_gates(state: dict[str, Any]) -> list[dict[str, Any]]:
    review = state.get("review_result", {}) or {}
    evidence = state.get("evidence_result", {}) or {}
    visualization = state.get("visualization_decision", {}) or {}
    delivery_cards = _delivery_tool_cards(state)
    policy_failures = [card for card in delivery_cards if card["policy_status"] == "failed"]
    policy_seen = bool(delivery_cards)
    approval_status = str(state.get("approval_status", "") or "not run")
    return [
        {
            "gate": "SQL Validator",
            "owner": "validate_sql() / SQL Reviewer",
            "status": _gate_status_from_bool(review.get("approved")) if review else "not run",
            "detail": str(review.get("reason", "") or review.get("error", "") or ""),
        },
        {
            "gate": "Evidence Validator",
            "owner": "agents.evidence_validator",
            "status": _gate_status_from_bool(evidence.get("success")) if evidence else "not run",
            "detail": f"unsupported_claim_rate={evidence.get('unsupported_claim_rate', '')}" if evidence else "",
        },
        {
            "gate": "Chart Validator",
            "owner": "visualization.chart_validator",
            "status": "failed" if visualization.get("validation_error") else ("passed" if visualization else "not run"),
            "detail": str(visualization.get("validation_error", "") or visualization.get("delivery_tool_id", "") or ""),
        },
        {
            "gate": "Tool Policy",
            "owner": "visualization_delivery/action_delivery policy",
            "status": "failed" if policy_failures else ("passed" if policy_seen else "not run"),
            "detail": "; ".join(card["error"] for card in policy_failures if card["error"]),
        },
        {
            "gate": "Approval Gate",
            "owner": "tools.approval_tool",
            "status": approval_status,
            "detail": "required" if (state.get("risk_assessment", {}) or {}).get("requires_approval") else "",
        },
        {
            "gate": "Audit Logger",
            "owner": "tools.audit_logger",
            "status": "passed" if state.get("audit_log_id") else "not run",
            "detail": str(state.get("audit_log_id", "") or ""),
        },
    ]


def build_artifact_panel(state: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = []
    for artifact_type, location in [
        ("report", state.get("report_path", "") or state.get("weekly_report_path", "")),
        ("trace", state.get("trace_path", "")),
        ("audit", state.get("audit_log_id", "")),
    ]:
        if location:
            artifacts.append({"artifact_type": artifact_type, "location": str(location), "source": "state"})

    for path in state.get("chart_paths") or ([state["chart_path"]] if state.get("chart_path") else []):
        artifacts.append({"artifact_type": "chart", "location": str(path), "source": "chart"})

    for result in [state.get("visualization_delivery_result", {}) or {}]:
        location = result.get("artifact_url") or result.get("artifact_path")
        if location:
            artifacts.append(
                {
                    "artifact_type": str(result.get("tool_type", "") or result.get("delivery_tool_id", "") or "visualization"),
                    "location": str(location),
                    "source": "visualization_delivery",
                }
            )

    action_execution = state.get("action_execution_result", {}) or {}
    for result in action_execution.get("delivery_results", []) or []:
        if not isinstance(result, dict):
            continue
        location = result.get("artifact_url") or result.get("artifact_path")
        if location:
            artifacts.append(
                {
                    "artifact_type": str(result.get("tool_type", "") or result.get("delivery_tool_id", "") or "action_delivery"),
                    "location": str(location),
                    "source": "action_delivery",
                }
            )
    return artifacts


def build_visualization_delivery_summary(state: dict[str, Any]) -> dict[str, Any]:
    raw_decision = state.get("visualization_decision", {}) or {}
    raw_delivery = state.get("visualization_delivery_result", {}) or {}
    decision = raw_decision if isinstance(raw_decision, dict) else {}
    delivery = raw_delivery if isinstance(raw_delivery, dict) else {}
    raw_chart_spec = decision.get("chart_spec", {}) or {}
    chart_spec = raw_chart_spec if isinstance(raw_chart_spec, dict) else {}
    artifact = str(delivery.get("artifact_url", "") or delivery.get("artifact_path", "") or "")
    return {
        "provider_called": bool(decision.get("provider_called", False)),
        "fallback_used": bool(decision.get("fallback_used", False)),
        "prompt_id": str(decision.get("prompt_id", "") or ""),
        "delivery_tool_id": str(decision.get("delivery_tool_id", "") or delivery.get("delivery_tool_id", "") or ""),
        "tool_reason": str(decision.get("tool_reason", "") or ""),
        "chart_type": str(chart_spec.get("chart_type", "") or delivery.get("chart_type", "") or ""),
        "external_tool_called": bool(delivery.get("external_tool_called", False)),
        "tool_type": str(delivery.get("tool_type", "") or ""),
        "artifact": artifact,
        "data_row_count": int(delivery.get("data_row_count") or decision.get("data_row_count") or 0),
        "fabricated_data": bool(delivery.get("fabricated_data", False)),
        "validation_error": str(decision.get("validation_error", "") or ""),
        "provider_error": str(decision.get("provider_error", "") or ""),
    }


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
        "visualization_delivery": build_visualization_delivery_summary(state),
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
        "agent_pipeline": build_agent_pipeline(state),
        "tool_call_cards": build_tool_call_cards(state),
        "validator_gates": build_validator_gates(state),
        "artifact_panel": build_artifact_panel(state),
        "sources": build_source_cards(state),
        "safety_boundaries": list(SAFETY_BOUNDARIES),
        "run_sections": [dict(section) for section in RUN_DETAIL_SECTIONS],
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
        "visualization_agent": provider_visualization_agent_enabled(values),
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
