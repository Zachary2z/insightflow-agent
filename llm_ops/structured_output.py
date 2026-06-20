from __future__ import annotations

from typing import Any

from llm_ops.provider import LLMProvider, LLMRequest, run_llm_request


def _error(prompt_id: str, message: str) -> dict[str, Any]:
    return {
        "success": False,
        "prompt_id": prompt_id,
        "content": None,
        "error": message,
        "error_type": "llm_schema_validation_error",
    }


def _ok(prompt_id: str, content: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": True,
        "prompt_id": prompt_id,
        "content": content,
        "error": "",
        "error_type": "",
    }


def _validate_report_planner(content: Any, schema_context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(content, dict):
        return _error("report_planner", "report_planner output must be an object")

    sections = content.get("sections", [])
    if not isinstance(sections, list):
        return _error("report_planner", "sections must be a list")

    allowed = set(schema_context.get("allowed_section_ids", []))
    normalized_sections = []
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            return _error("report_planner", f"sections[{index}] must be an object")
        section_id = str(section.get("section_id", "")).strip()
        if not section_id:
            return _error("report_planner", f"sections[{index}].section_id is required")
        if allowed and section_id not in allowed:
            return _error("report_planner", f"sections[{index}].section_id is not allowed: {section_id}")
        normalized_sections.append(
            {
                "section_id": section_id,
                "rationale": str(section.get("rationale", "")).strip(),
            }
        )

    clarification_questions = content.get("clarification_questions", [])
    if not isinstance(clarification_questions, list):
        return _error("report_planner", "clarification_questions must be a list")

    normalized = {
        "sections": normalized_sections,
        "requires_clarification": bool(content.get("requires_clarification", False)),
        "clarification_questions": [str(question).strip() for question in clarification_questions if str(question).strip()],
    }
    return _ok("report_planner", normalized)


def _validate_guarded_sql_candidate(content: Any) -> dict[str, Any]:
    if not isinstance(content, dict):
        return _error("guarded_sql_candidate", "guarded_sql_candidate output must be an object")

    candidates = content.get("sql_candidates", [])
    if not isinstance(candidates, list):
        return _error("guarded_sql_candidate", "sql_candidates must be a list")

    normalized = []
    for index, item in enumerate(candidates):
        if not isinstance(item, dict):
            return _error("guarded_sql_candidate", f"sql_candidates[{index}] must be an object")
        sql = str(item.get("sql", "")).strip()
        if not sql:
            return _error("guarded_sql_candidate", f"sql_candidates[{index}].sql is required")
        normalized.append({"sql": sql, "rationale": str(item.get("rationale", "")).strip()})
    return _ok("guarded_sql_candidate", {"sql_candidates": normalized})


def _validate_guarded_insight_claims(content: Any) -> dict[str, Any]:
    if not isinstance(content, dict):
        return _error("guarded_insight_claims", "guarded_insight_claims output must be an object")

    claims = content.get("claims", [])
    if not isinstance(claims, list):
        return _error("guarded_insight_claims", "claims must be a list")
    if not all(isinstance(claim, str) for claim in claims):
        return _error("guarded_insight_claims", "claims must contain only strings")
    return _ok("guarded_insight_claims", {"claims": [claim.strip() for claim in claims if claim.strip()]})


def _nullable_string(value: Any, field_name: str) -> tuple[bool, str, str]:
    if value is None:
        return True, "", ""
    if isinstance(value, str):
        return True, value.strip(), ""
    return False, "", f"{field_name} must be a string or null"


def _string_list(value: Any, field_name: str) -> tuple[bool, list[str], str]:
    if not isinstance(value, list):
        return False, [], f"{field_name} must be a list"
    normalized = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            return False, [], f"{field_name}[{index}] must be a string"
        item = item.strip()
        if item:
            normalized.append(item)
    return True, normalized, ""


def _validate_question_understanding(content: Any) -> dict[str, Any]:
    prompt_id = "question_understanding"
    if not isinstance(content, dict):
        return _error(prompt_id, "question_understanding output must be an object")

    strategy = str(content.get("strategy", "")).strip()
    if strategy not in {"template", "llm_candidate", "clarify", "reject"}:
        return _error(prompt_id, "strategy must be one of template, llm_candidate, clarify, reject")

    intent = content.get("intent")
    if not isinstance(intent, dict):
        return _error(prompt_id, "intent must be an object")

    ok, metric, message = _nullable_string(intent.get("metric"), "intent.metric")
    if not ok:
        return _error(prompt_id, message)
    ok, dimension, message = _nullable_string(intent.get("dimension"), "intent.dimension")
    if not ok:
        return _error(prompt_id, message)
    ok, operation, message = _nullable_string(intent.get("operation"), "intent.operation")
    if not ok:
        return _error(prompt_id, message)

    time_range = intent.get("time_range")
    if time_range is not None and not isinstance(time_range, dict):
        return _error(prompt_id, "intent.time_range must be an object or null")

    filters_ok, filters, message = _string_list(intent.get("filters"), "intent.filters")
    if not filters_ok:
        return _error(prompt_id, message)

    limit = intent.get("limit")
    if limit is not None and not isinstance(limit, int):
        return _error(prompt_id, "intent.limit must be an int or null")

    intent_risk_ok, intent_risk_flags, message = _string_list(intent.get("risk_flags"), "intent.risk_flags")
    if not intent_risk_ok:
        return _error(prompt_id, message)

    missing_ok, missing_slots, message = _string_list(content.get("missing_slots"), "missing_slots")
    if not missing_ok:
        return _error(prompt_id, message)
    questions_ok, clarification_questions, message = _string_list(
        content.get("clarification_questions"),
        "clarification_questions",
    )
    if not questions_ok:
        return _error(prompt_id, message)
    risk_ok, risk_flags, message = _string_list(content.get("risk_flags"), "risk_flags")
    if not risk_ok:
        return _error(prompt_id, message)

    normalized_risk_flags = list(dict.fromkeys([*intent_risk_flags, *risk_flags]))
    normalized_intent = {
        "metric": metric,
        "dimension": dimension,
        "time_range": time_range,
        "filters": filters,
        "operation": operation,
        "limit": limit,
        "risk_flags": normalized_risk_flags,
    }
    return _ok(
        prompt_id,
        {
            "strategy": strategy,
            "intent": normalized_intent,
            "missing_slots": missing_slots,
            "clarification_questions": clarification_questions,
            "risk_flags": normalized_risk_flags,
            "reason": str(content.get("reason", "")).strip(),
        },
    )


def _validate_clarification_router(content: Any) -> dict[str, Any]:
    prompt_id = "clarification_router"
    if not isinstance(content, dict):
        return _error(prompt_id, "clarification_router output must be an object")

    missing_ok, missing_slots, message = _string_list(content.get("missing_slots"), "missing_slots")
    if not missing_ok:
        return _error(prompt_id, message)
    questions_ok, clarification_questions, message = _string_list(
        content.get("clarification_questions"),
        "clarification_questions",
    )
    if not questions_ok:
        return _error(prompt_id, message)
    if not clarification_questions:
        return _error(prompt_id, "clarification_questions must contain at least one question")
    risk_ok, risk_flags, message = _string_list(content.get("risk_flags"), "risk_flags")
    if not risk_ok:
        return _error(prompt_id, message)

    return _ok(
        prompt_id,
        {
            "requires_clarification": bool(content.get("requires_clarification", True)),
            "missing_slots": missing_slots,
            "clarification_questions": clarification_questions,
            "risk_flags": risk_flags,
            "reason": str(content.get("reason", "")).strip(),
        },
    )


def validate_prompt_output(
    prompt_id: str,
    content: Any,
    schema_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = schema_context or {}
    if prompt_id == "report_planner":
        return _validate_report_planner(content, context)
    if prompt_id == "guarded_sql_candidate":
        return _validate_guarded_sql_candidate(content)
    if prompt_id == "guarded_insight_claims":
        return _validate_guarded_insight_claims(content)
    if prompt_id == "question_understanding":
        return _validate_question_understanding(content)
    if prompt_id == "clarification_router":
        return _validate_clarification_router(content)
    return _error(prompt_id, f"unknown prompt schema: {prompt_id}")


def run_validated_llm_request(
    provider: LLMProvider,
    request: LLMRequest,
    schema_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provider_result = run_llm_request(provider, request)
    if not provider_result.get("success"):
        return provider_result

    validation = validate_prompt_output(request.prompt_id, provider_result.get("content"), schema_context)
    if validation.get("success"):
        return {**provider_result, "content": validation["content"], "error_type": ""}

    trace_event = dict(provider_result["trace_event"])
    trace_event.update(
        {
            "status": "error",
            "error_type": validation["error_type"],
            "error": validation["error"],
            "tool_output_summary": validation["error"],
        }
    )
    return {
        **provider_result,
        "success": False,
        "content": None,
        "error": validation["error"],
        "error_type": validation["error_type"],
        "trace_event": trace_event,
    }
