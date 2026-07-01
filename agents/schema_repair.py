from __future__ import annotations

import json
from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from semantic_layer.loader import load_workspace_semantic_layer
from tools.trace_logger import append_trace


_SCHEMA_MISMATCH_MARKERS = (
    "unknown table",
    "unknown column",
    "no such table",
    "no such column",
    "missing table",
    "missing column",
)


def is_schema_mismatch_review(review_result: dict[str, Any] | None) -> bool:
    if not isinstance(review_result, dict) or review_result.get("approved"):
        return False
    checks = review_result.get("checks") if isinstance(review_result.get("checks"), dict) else {}
    issues = " ".join(str(issue) for issue in review_result.get("issues") or []).lower()
    return bool(
        checks.get("tables_exist") is False
        or checks.get("columns_exist") is False
        or any(marker in issues for marker in _SCHEMA_MISMATCH_MARKERS)
    )


def run_schema_repair_agent(state: dict[str, Any], provider: LLMProvider | None = None) -> dict[str, Any]:
    rejected_sql = str(state.get("generated_sql") or "")
    review_result = state.get("review_result") if isinstance(state.get("review_result"), dict) else {}
    rejection_reasons = [str(issue) for issue in review_result.get("issues") or [] if str(issue).strip()]
    repair_context = _repair_context(state, rejected_sql, rejection_reasons)
    repair = {
        "attempted": True,
        "succeeded": False,
        "reason": "; ".join(rejection_reasons),
        "rejected_sql_summary": _summary(rejected_sql),
        "repaired_sql_summary": "",
        "rejection_reasons": rejection_reasons,
        "semantic_layer_hints": repair_context["semantic_layer_hints"],
    }
    base_update = {
        **state,
        "schema_repair_attempted": True,
        "schema_repair_succeeded": False,
        "schema_repair_reason": repair["reason"],
        "schema_repair": repair,
        "schema_repair_pending_review": False,
    }

    if not provider:
        return append_trace(
            base_update,
            _trace_event(
                repair,
                node="schema_repair_agent",
                tool_name="llm_sql_candidate_provider",
                tool_input_summary=_summary(rejected_sql),
                tool_output_summary="schema repair skipped; provider not configured",
                status="error",
                latency_ms=0,
                error_type="schema_repair_provider_unavailable",
            ),
        )

    rendered = DEFAULT_PROMPT_REGISTRY.render("guarded_sql_candidate", _prompt_variables(state, repair_context))
    if not rendered.get("success"):
        repair["error"] = rendered.get("error", "")
        return append_trace(
            {**base_update, "schema_repair": repair},
            _trace_event(
                repair,
                node="schema_repair_agent",
                tool_name="llm_sql_candidate_provider",
                tool_input_summary=_summary(rejected_sql),
                tool_output_summary=rendered.get("error", ""),
                status="error",
                latency_ms=0,
                error_type="prompt_render_error",
                error=rendered.get("error", ""),
            ),
        )

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "schema_repair_agent"},
    )
    provider_result = run_validated_llm_request(provider, request)
    trace_event = dict(provider_result.get("trace_event") or {})
    trace_event["node"] = "schema_repair_agent"
    trace_event["tool_name"] = "llm_sql_candidate_provider"

    if not provider_result.get("success"):
        repair["error"] = str(provider_result.get("error") or "")
        trace_event["tool_output_summary"] = repair["error"]
        trace_event.update(_repair_trace_metadata(repair))
        return append_trace({**base_update, "schema_repair": repair}, trace_event)

    candidates = provider_result.get("content", {}).get("sql_candidates") or []
    first_candidate = candidates[0] if candidates else {}
    repaired_sql = str(first_candidate.get("sql") or "").strip() if isinstance(first_candidate, dict) else ""
    repair["repaired_sql_summary"] = _summary(repaired_sql)
    repair["candidate_count"] = len(candidates)
    repair["rationale"] = str(first_candidate.get("rationale") or "") if isinstance(first_candidate, dict) else ""
    updated = {
        **base_update,
        "schema_repair": repair,
        "schema_repair_pending_review": bool(repaired_sql),
    }
    if repaired_sql:
        updated["generated_sql"] = repaired_sql
        updated["sql_reason"] = "Provider repaired schema-mismatch SQL; SQL Reviewer must approve before execution."
    trace_event["tool_output_summary"] = f"schema repair candidate_count={len(candidates)}"
    trace_event["status"] = "success" if repaired_sql else "error"
    trace_event.update(_repair_trace_metadata(repair))
    if not repaired_sql:
        trace_event["error_type"] = "schema_repair_empty_candidate"
    return append_trace(updated, trace_event)


def _prompt_variables(state: dict[str, Any], repair_context: dict[str, Any]) -> dict[str, Any]:
    business_context = state.get("business_context") if isinstance(state.get("business_context"), dict) else {}
    workspace_context = state.get("workspace_context") if isinstance(state.get("workspace_context"), dict) else {}
    return {
        "user_question": _repair_instruction(repair_context),
        "schema_text": state.get("schema_text", ""),
        "workspace_context": {**workspace_context, "schema_repair": repair_context},
        "metric_context": state.get("metric_context", {}),
        "business_context": {**business_context, "schema_repair": repair_context},
        "current_deterministic_sql": repair_context["rejected_sql"],
    }


def _repair_context(state: dict[str, Any], rejected_sql: str, rejection_reasons: list[str]) -> dict[str, Any]:
    return {
        "original_user_question": state.get("original_question") or state.get("user_question") or "",
        "rejected_sql": rejected_sql,
        "reviewer_rejection_reasons": rejection_reasons,
        "current_workspace_database_schema": state.get("schema_text", ""),
        "semantic_layer_hints": _semantic_layer_hints(state),
    }


def _repair_instruction(repair_context: dict[str, Any]) -> str:
    return (
        "Repair the rejected SQL using only the current workspace database schema. "
        "Return one SQLite SELECT candidate. "
        f"Original user question: {repair_context['original_user_question']}\n"
        f"Rejected SQL: {repair_context['rejected_sql']}\n"
        f"Reviewer rejection reasons: {repair_context['reviewer_rejection_reasons']}\n"
        f"Current workspace database schema:\n{repair_context['current_workspace_database_schema']}\n"
        f"Semantic layer hints: {json.dumps(repair_context['semantic_layer_hints'], ensure_ascii=False, sort_keys=True)}"
    )


def _semantic_layer_hints(state: dict[str, Any]) -> dict[str, Any]:
    hints: dict[str, Any] = {
        "metric_context": state.get("metric_context") if isinstance(state.get("metric_context"), dict) else {},
    }
    path_text = state.get("semantic_layer_path")
    if isinstance(path_text, str) and path_text:
        loaded = load_workspace_semantic_layer(path_text)
        if loaded.get("success"):
            payload = loaded["semantic_layer"]
            hints["semantic_layer"] = {
                key: payload.get(key)
                for key in ("metrics", "dimensions", "entities", "time_fields", "tables", "relationships")
                if key in payload
            }
        else:
            hints["semantic_layer_error"] = loaded.get("error", "semantic layer could not be read")
        hints["semantic_layer_path"] = path_text
    return hints


def _summary(sql: str, limit: int = 240) -> str:
    normalized = " ".join(str(sql or "").split())
    return normalized[:limit]


def _trace_event(repair: dict[str, Any], **event: Any) -> dict[str, Any]:
    return {**event, **_repair_trace_metadata(repair)}


def _repair_trace_metadata(repair: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_repair_attempted": repair.get("attempted", False),
        "schema_repair_succeeded": repair.get("succeeded", False),
        "schema_repair_reason": repair.get("reason", ""),
        "rejected_sql_summary": repair.get("rejected_sql_summary", ""),
        "repaired_sql_summary": repair.get("repaired_sql_summary", ""),
    }
