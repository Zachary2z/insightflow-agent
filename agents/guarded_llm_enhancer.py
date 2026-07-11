from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from sql_planning.comparison_scope import widen_sql_for_comparison_scope
from tools.sql_validator import validate_sql
from tools.trace_logger import append_trace


def _sql_prompt_variables(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_question": state.get("user_question", ""),
        "schema_text": state.get("schema_text", ""),
        "workspace_context": state.get("workspace_context", {}),
        "metric_context": state.get("metric_context", {}),
        "business_context": state.get("business_context", {}),
        "current_deterministic_sql": state.get("generated_sql", ""),
    }


def _provider_payload(state: dict[str, Any], provider: LLMProvider) -> dict[str, Any]:
    rendered = DEFAULT_PROMPT_REGISTRY.render("guarded_sql_candidate", _sql_prompt_variables(state))
    if not rendered.get("success"):
        return {
            "success": False,
            "content": None,
            "error": rendered.get("error", ""),
            "error_type": "prompt_render_error",
        }

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "guarded_sql_candidate_agent"},
    )
    result = run_validated_llm_request(provider, request)
    if not result.get("success"):
        raise ValueError(result.get("error", "provider request failed"))
    return result.get("content", {})


def _fallback_sql_enhancement(reason: str, provider_called: bool) -> dict[str, Any]:
    return {
        "success": True if not provider_called else False,
        "provider_called": provider_called,
        "fallback_used": True,
        "accepted": False,
        "accepted_sql": "",
        "candidates": [],
        "error": reason,
    }


def _candidate_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("sql_candidates", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _is_schema_mismatch_review(review_result: dict[str, Any]) -> bool:
    checks = review_result.get("checks") if isinstance(review_result.get("checks"), dict) else {}
    issues = " ".join(str(issue) for issue in review_result.get("issues") or []).lower()
    has_schema_issue = (
        checks.get("tables_exist") is False
        or checks.get("columns_exist") is False
        or "unknown table" in issues
        or "unknown column" in issues
        or "no such table" in issues
        or "no such column" in issues
    )
    if not has_schema_issue:
        return False
    return bool(
        checks.get("select_only")
        and checks.get("single_statement")
        and checks.get("no_dangerous_keywords")
        and checks.get("sensitive_fields_blocked")
    )


def run_guarded_sql_candidate_agent(
    state: dict[str, Any],
    llm_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    deterministic_sql = state.get("generated_sql", "")
    if not llm_provider:
        enhancement = _fallback_sql_enhancement("llm_provider is not configured", provider_called=False)
        updated = {**state, "llm_sql_enhancement": enhancement}
        return append_trace(
            updated,
            {
                "node": "guarded_sql_candidate_agent",
                "tool_name": "",
                "tool_input_summary": state.get("user_question", ""),
                "tool_output_summary": "deterministic SQL retained; provider not configured",
                "status": "success",
                "latency_ms": 0,
            },
        )

    candidates = []
    accepted_sql = ""
    schema_mismatch_sql = ""
    error = ""
    comparison_scope_adjustment: dict[str, Any] = {}
    try:
        payload = _provider_payload(state, llm_provider)
        for item in _candidate_items(payload):
            candidate_sql = str(item.get("sql", "")).strip()
            review_result = validate_sql(candidate_sql, state.get("database_schema", {}), state.get("metric_context"))
            candidate_record = {
                "sql": candidate_sql,
                "rationale": str(item.get("rationale", "")).strip(),
                "review_result": review_result,
                "accepted": False,
            }
            if not accepted_sql and review_result.get("approved"):
                normalized_sql = review_result.get("normalized_sql") or candidate_sql
                widened_sql, adjustment = widen_sql_for_comparison_scope(
                    normalized_sql,
                    question=state.get("user_question", ""),
                    analysis_task=state.get("analysis_task") or {},
                    question_understanding=state.get("question_understanding") or {},
                )
                if adjustment.get("applied"):
                    adjusted_review = validate_sql(
                        widened_sql,
                        state.get("database_schema", {}),
                        state.get("metric_context"),
                    )
                    candidate_record["original_review_result"] = review_result
                    candidate_record["review_result"] = adjusted_review
                    candidate_record["comparison_scope_adjustment"] = adjustment
                    review_result = adjusted_review
                    comparison_scope_adjustment = adjustment
                if review_result.get("approved"):
                    accepted_sql = review_result.get("normalized_sql") or widened_sql
                    candidate_record["accepted"] = True
            elif not accepted_sql and not schema_mismatch_sql and _is_schema_mismatch_review(review_result):
                schema_mismatch_sql = candidate_sql
                candidate_record["requires_schema_repair"] = True
            candidates.append(candidate_record)
        if not accepted_sql:
            error = "no approved sql candidates"
    except Exception as exc:
        error = str(exc)

    accepted = bool(accepted_sql)
    enhancement = {
        "success": accepted,
        "provider_called": True,
        "fallback_used": not accepted,
        "accepted": accepted,
        "accepted_sql": accepted_sql,
        "candidates": candidates,
        "error": error,
    }
    if comparison_scope_adjustment:
        enhancement["comparison_scope_adjustment"] = comparison_scope_adjustment
    updated = {
        **state,
        "llm_sql_enhancement": enhancement,
        "generated_sql": accepted_sql if accepted else (schema_mismatch_sql or deterministic_sql),
    }
    if comparison_scope_adjustment:
        updated["comparison_scope_adjustment"] = comparison_scope_adjustment
    if accepted:
        updated["sql_reason"] = "Guarded LLM SQL candidate accepted after validate_sql approval."
    elif schema_mismatch_sql:
        updated["sql_reason"] = "Guarded LLM SQL candidate requires SQL Reviewer schema repair review."

    return append_trace(
        updated,
        {
            "node": "guarded_sql_candidate_agent",
            "tool_name": "llm_sql_candidate_provider",
            "tool_input_summary": state.get("user_question", ""),
            "tool_output_summary": f"accepted={accepted} candidates={len(candidates)}",
            "status": "success" if accepted else "error",
            "latency_ms": 0,
            "error_type": None if accepted else "llm_sql_candidate_rejected",
            "error": error or None,
            "provider_called": True,
            "fallback_used": not accepted,
        },
    )
