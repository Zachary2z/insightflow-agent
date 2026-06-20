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

    blocked_top_level = {"sql", "generated_sql", "sql_candidates", "final_claims", "claims"}
    leaked = sorted(blocked_top_level & set(content))
    if leaked:
        return _error("report_planner", f"report_planner must not return blocked fields: {', '.join(leaked)}")

    sections = content.get("sections", [])
    if not isinstance(sections, list):
        return _error("report_planner", "sections must be a list")

    allowed = set(schema_context.get("allowed_section_ids", []))
    normalized_sections = []
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            return _error("report_planner", f"sections[{index}] must be an object")
        leaked = sorted(blocked_top_level & set(section))
        if leaked:
            return _error("report_planner", f"sections[{index}] must not return blocked fields: {', '.join(leaked)}")
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
        "report_type": str(content.get("report_type") or schema_context.get("report_type") or "").strip(),
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


def _validate_report_writer(content: Any, schema_context: dict[str, Any]) -> dict[str, Any]:
    prompt_id = "report_writer"
    if not isinstance(content, dict):
        return _error(prompt_id, "report_writer output must be an object")

    blocked_fields = {"sql", "generated_sql", "sql_candidates", "candidate_sql", "final_claims", "claims"}
    leaked = sorted(blocked_fields & set(content))
    if leaked:
        return _error(prompt_id, f"report_writer must not return blocked fields: {', '.join(leaked)}")

    summary_ok, executive_summary, message = _string_list(content.get("executive_summary", []), "executive_summary")
    if not summary_ok:
        return _error(prompt_id, message)
    if not isinstance(content.get("business_narrative", ""), str):
        return _error(prompt_id, "business_narrative must be a string")
    steps_ok, next_steps, message = _string_list(content.get("next_steps", []), "next_steps")
    if not steps_ok:
        return _error(prompt_id, message)
    supported_ok, used_supported_claims, message = _string_list(
        content.get("used_supported_claims", []),
        "used_supported_claims",
    )
    if not supported_ok:
        return _error(prompt_id, message)
    hypotheses_ok, used_hypotheses, message = _string_list(content.get("used_hypotheses", []), "used_hypotheses")
    if not hypotheses_ok:
        return _error(prompt_id, message)
    unsupported_ok, unsupported_claims, message = _string_list(
        content.get("unsupported_claims", []),
        "unsupported_claims",
    )
    if not unsupported_ok:
        return _error(prompt_id, message)
    if unsupported_claims:
        return _error(prompt_id, "unsupported_claims must be empty")

    allowed_supported = set(schema_context.get("verified_findings", []))
    unexpected_supported = [claim for claim in used_supported_claims if allowed_supported and claim not in allowed_supported]
    if unexpected_supported:
        return _error(prompt_id, f"used_supported_claims contains unverified claims: {unexpected_supported[0]}")

    allowed_hypotheses = set(schema_context.get("verified_hypotheses", []))
    unexpected_hypotheses = [claim for claim in used_hypotheses if allowed_hypotheses and claim not in allowed_hypotheses]
    if unexpected_hypotheses:
        return _error(prompt_id, f"used_hypotheses contains unverified claims: {unexpected_hypotheses[0]}")

    business_narrative = content.get("business_narrative", "").strip()
    combined_text = "\n".join([*executive_summary, business_narrative, *next_steps])
    for blocked_claim in schema_context.get("blocked_unsupported_claims", []):
        blocked_text = str(blocked_claim).strip()
        if blocked_text and blocked_text in combined_text:
            return _error(prompt_id, f"report_writer included blocked unsupported claim: {blocked_text}")

    return _ok(
        prompt_id,
        {
            "executive_summary": executive_summary,
            "business_narrative": business_narrative,
            "next_steps": next_steps,
            "used_supported_claims": used_supported_claims,
            "used_hypotheses": used_hypotheses,
            "unsupported_claims": [],
        },
    )


def _validate_insight_claim_typer(content: Any) -> dict[str, Any]:
    prompt_id = "insight_claim_typer"
    if not isinstance(content, dict):
        return _error(prompt_id, "insight_claim_typer output must be an object")

    blocked_fields = {"sql", "generated_sql", "sql_candidates", "candidate_sql", "final_answer"}
    leaked = sorted(blocked_fields & set(content))
    if leaked:
        return _error(prompt_id, f"insight_claim_typer must not return blocked fields: {', '.join(leaked)}")

    typed_claims = content.get("typed_claims", [])
    if not isinstance(typed_claims, list):
        return _error(prompt_id, "typed_claims must be a list")

    normalized_claims = []
    allowed_types = {"data_supported_finding", "hypothesis", "unsupported"}
    for index, item in enumerate(typed_claims):
        if not isinstance(item, dict):
            return _error(prompt_id, f"typed_claims[{index}] must be an object")
        claim = str(item.get("claim", "")).strip()
        if not claim:
            return _error(prompt_id, f"typed_claims[{index}].claim is required")
        claim_type = str(item.get("claim_type", "")).strip()
        if claim_type not in allowed_types:
            return _error(prompt_id, f"typed_claims[{index}].claim_type must be one of {', '.join(sorted(allowed_types))}")
        normalized_claims.append(
            {
                "claim": claim,
                "claim_type": claim_type,
                "rationale": str(item.get("rationale", "")).strip(),
            }
        )

    risk_ok, risk_flags, message = _string_list(content.get("risk_flags", []), "risk_flags")
    if not risk_ok:
        return _error(prompt_id, message)

    return _ok(prompt_id, {"typed_claims": normalized_claims, "risk_flags": risk_flags})


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


def _validate_sql_planning_router(content: Any) -> dict[str, Any]:
    prompt_id = "sql_planning_router"
    if not isinstance(content, dict):
        return _error(prompt_id, "sql_planning_router output must be an object")

    blocked_fields = {"sql", "generated_sql", "sql_candidates", "candidate_sql", "selected_tables"}
    leaked = sorted(blocked_fields & set(content))
    if leaked:
        return _error(prompt_id, f"sql_planning_router must not return SQL fields: {', '.join(leaked)}")

    strategy = str(content.get("strategy", "")).strip()
    if strategy not in {"template", "llm_candidate", "clarify", "reject"}:
        return _error(prompt_id, "strategy must be one of template, llm_candidate, clarify, reject")

    matched_template = str(content.get("matched_template") or "").strip()
    allowed_templates = {
        "",
        "top_products_gmv",
        "top_categories_gmv",
        "city_gmv_summary",
        "city_order_count_summary",
    }
    if matched_template not in allowed_templates:
        return _error(prompt_id, f"matched_template is not allowed: {matched_template}")
    if strategy != "template":
        matched_template = ""

    confidence = content.get("confidence", 0.0)
    if not isinstance(confidence, int | float):
        return _error(prompt_id, "confidence must be a number")
    confidence = float(confidence)
    if confidence < 0 or confidence > 1:
        return _error(prompt_id, "confidence must be between 0 and 1")

    missing_ok, missing_slots, message = _string_list(content.get("missing_slots", []), "missing_slots")
    if not missing_ok:
        return _error(prompt_id, message)
    questions_ok, clarification_questions, message = _string_list(
        content.get("clarification_questions", []),
        "clarification_questions",
    )
    if not questions_ok:
        return _error(prompt_id, message)
    risk_ok, risk_flags, message = _string_list(content.get("risk_flags", []), "risk_flags")
    if not risk_ok:
        return _error(prompt_id, message)

    return _ok(
        prompt_id,
        {
            "strategy": strategy,
            "matched_template": matched_template,
            "confidence": confidence,
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
    if prompt_id == "report_writer":
        return _validate_report_writer(content, context)
    if prompt_id == "insight_claim_typer":
        return _validate_insight_claim_typer(content)
    if prompt_id == "question_understanding":
        return _validate_question_understanding(content)
    if prompt_id == "clarification_router":
        return _validate_clarification_router(content)
    if prompt_id == "sql_planning_router":
        return _validate_sql_planning_router(content)
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
