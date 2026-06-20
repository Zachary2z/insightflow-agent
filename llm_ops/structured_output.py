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
