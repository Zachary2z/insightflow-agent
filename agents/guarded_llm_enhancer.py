from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from tools.evidence_tool import validate_evidence
from tools.sql_validator import validate_sql
from tools.trace_logger import append_trace


LegacyCallableProvider = Callable[[dict[str, Any]], dict[str, Any] | str]


def _parse_provider_response(response: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(response, str):
        return json.loads(response)
    if isinstance(response, dict):
        return response
    raise ValueError("provider response must be a dict or JSON string")


def _sql_prompt(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": "guarded_sql_candidate_generation",
        "user_question": state.get("user_question", ""),
        "schema_text": state.get("schema_text", ""),
        "workspace_context": state.get("workspace_context", {}),
        "metric_context": state.get("metric_context", {}),
        "business_context": state.get("business_context", {}),
        "current_deterministic_sql": state.get("generated_sql", ""),
        "output_schema": {
            "sql_candidates": [
                {
                    "sql": "single SELECT statement only",
                    "rationale": "short reason grounded in schema and metric context",
                }
            ]
        },
        "must_validate_sql": True,
        "must_not_execute_sql": True,
        "must_not_access_sensitive_fields": True,
        "must_not_use_dml_or_ddl": True,
    }


def _sql_prompt_variables(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_question": state.get("user_question", ""),
        "schema_text": state.get("schema_text", ""),
        "workspace_context": state.get("workspace_context", {}),
        "metric_context": state.get("metric_context", {}),
        "business_context": state.get("business_context", {}),
        "current_deterministic_sql": state.get("generated_sql", ""),
    }


def _provider_payload_from_llm_provider(state: dict[str, Any], provider: LLMProvider) -> dict[str, Any]:
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
    return run_validated_llm_request(provider, request)


def _provider_payload(state: dict[str, Any], provider: LLMProvider | LegacyCallableProvider) -> dict[str, Any]:
    if hasattr(provider, "generate"):
        result = _provider_payload_from_llm_provider(state, provider)
        if not result.get("success"):
            raise ValueError(result.get("error", "provider request failed"))
        return result.get("content", {})
    return _parse_provider_response(provider(_sql_prompt(state)))


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
    llm_provider: LLMProvider | LegacyCallableProvider | None = None,
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
                accepted_sql = review_result.get("normalized_sql") or candidate_sql
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
    updated = {
        **state,
        "llm_sql_enhancement": enhancement,
        "generated_sql": accepted_sql if accepted else (schema_mismatch_sql or deterministic_sql),
    }
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
            "template_mining_event": {
                "strategy": state.get("sql_routing_strategy", ""),
                "success": accepted,
                "accepted": accepted,
                "provider_called": True,
                "candidate_count": len(candidates),
                "intent": dict(state.get("sql_planning", {}).get("intent", {})),
                "user_question": state.get("user_question", ""),
            },
        },
    )


def _insight_prompt(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": "guarded_insight_polishing",
        "user_question": state.get("user_question", ""),
        "execution_result": state.get("execution_result", {}),
        "business_context": state.get("business_context", {}),
        "metric_context": state.get("metric_context", {}),
        "current_final_answer": state.get("final_answer", ""),
        "output_schema": {
            "claims": ["claim that can be checked by Evidence Validator"],
            "polished_summary": "optional prose; unsupported claims will be ignored",
        },
        "must_validate_evidence": True,
        "must_not_add_unsupported_claims": True,
    }


def _clean_claims(payload: dict[str, Any]) -> list[str]:
    claims = payload.get("claims", [])
    if not isinstance(claims, list):
        return []
    return [str(claim).strip() for claim in claims if str(claim).strip()]


def _summary_from_evidence(evidence_result: dict[str, Any]) -> str:
    lines = []
    for item in evidence_result.get("data_supported_findings", []):
        lines.append(f"- {item.get('claim', '')}")
    for item in evidence_result.get("hypotheses", []):
        lines.append(f"- {item.get('claim', '')}")
    return "\n".join(lines) if lines else ""


def _fallback_insight_enhancement(reason: str, provider_called: bool) -> dict[str, Any]:
    return {
        "success": True if not provider_called else False,
        "provider_called": provider_called,
        "fallback_used": True,
        "data_supported_findings": [],
        "hypotheses": [],
        "unsupported_claims_blocked": [],
        "guarded_summary": "",
        "error": reason,
    }


def run_guarded_insight_enhancer_agent(
    state: dict[str, Any],
    llm_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    if not llm_provider:
        enhancement = _fallback_insight_enhancement("llm_provider is not configured", provider_called=False)
        updated = {**state, "llm_insight_enhancement": enhancement}
        return append_trace(
            updated,
            {
                "node": "guarded_insight_enhancer_agent",
                "tool_name": "",
                "tool_input_summary": state.get("user_question", ""),
                "tool_output_summary": "deterministic insight retained; provider not configured",
                "status": "success",
                "latency_ms": 0,
            },
        )

    try:
        payload = _parse_provider_response(llm_provider(_insight_prompt(state)))
        evidence_result = validate_evidence(
            claims=_clean_claims(payload),
            execution_result=state.get("execution_result"),
            business_context=state.get("business_context"),
            metric_context=state.get("metric_context"),
        )
        enhancement = {
            "success": evidence_result.get("success", False),
            "provider_called": True,
            "fallback_used": False,
            "data_supported_findings": evidence_result.get("data_supported_findings", []),
            "hypotheses": evidence_result.get("hypotheses", []),
            "unsupported_claims_blocked": evidence_result.get("unsupported_claims_blocked", []),
            "guarded_summary": _summary_from_evidence(evidence_result),
            "error": evidence_result.get("error", ""),
        }
    except Exception as exc:
        enhancement = _fallback_insight_enhancement(str(exc), provider_called=True)

    updated = {**state, "llm_insight_enhancement": enhancement}
    return append_trace(
        updated,
        {
            "node": "guarded_insight_enhancer_agent",
            "tool_name": "llm_insight_provider",
            "tool_input_summary": state.get("user_question", ""),
            "tool_output_summary": (
                f"{len(enhancement.get('data_supported_findings', []))} supported, "
                f"{len(enhancement.get('hypotheses', []))} hypotheses, "
                f"{len(enhancement.get('unsupported_claims_blocked', []))} blocked"
            ),
            "status": "success" if enhancement.get("success") else "error",
            "latency_ms": 0,
            "error_type": None if enhancement.get("success") else "llm_insight_enhancement_error",
            "error": enhancement.get("error") or None,
        },
    )
