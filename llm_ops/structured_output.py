from __future__ import annotations

import re
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


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(text or ""))


def _requires_cjk_response(schema_context: dict[str, Any]) -> bool:
    user_question = str(schema_context.get("user_question") or "")
    if not _contains_cjk(user_question):
        return False
    lowered = user_question.lower()
    return not any(marker in lowered for marker in ("用英文", "英文回答", "answer in english", "in english"))


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
        if isinstance(item, str):
            item = {"sql": item, "rationale": ""}
        if not isinstance(item, dict):
            return _error("guarded_sql_candidate", f"sql_candidates[{index}] must be an object")
        sql = str(item.get("sql") or item.get("query") or item.get("sql_query") or "").strip()
        if not sql:
            return _error("guarded_sql_candidate", f"sql_candidates[{index}].sql is required")
        rationale = str(item.get("rationale") or item.get("reason") or "").strip()
        normalized.append({"sql": sql, "rationale": rationale})
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


def _validate_answer_reviewer(content: Any) -> dict[str, Any]:
    prompt_id = "answer_reviewer"
    if not isinstance(content, dict):
        return _error(prompt_id, "answer_reviewer output must be an object")

    allowed_keys = {
        "status",
        "language",
        "supported_entities",
        "unsupported_entities",
        "supported_metrics",
        "unsupported_metrics",
        "issues",
        "revision_instructions",
        "confidence",
    }
    extra_keys = sorted(set(content) - allowed_keys)
    if extra_keys:
        return _error(prompt_id, f"answer_reviewer must not return unsupported fields: {', '.join(extra_keys)}")

    status = str(content.get("status", "")).strip()
    if status not in {"accept", "revise", "downgrade_to_insufficient_evidence"}:
        return _error(
            prompt_id,
            "status must be one of accept, revise, downgrade_to_insufficient_evidence",
        )
    language = str(content.get("language", "")).strip()
    if language not in {"zh", "en"}:
        return _error(prompt_id, "language must be one of zh, en")
    confidence = str(content.get("confidence", "")).strip()
    if confidence not in {"low", "medium", "high"}:
        return _error(prompt_id, "confidence must be one of low, medium, high")

    normalized: dict[str, Any] = {"status": status, "language": language, "confidence": confidence}
    for field in (
        "supported_entities",
        "unsupported_entities",
        "supported_metrics",
        "unsupported_metrics",
        "revision_instructions",
    ):
        ok, items, message = _string_list(content.get(field, []), field)
        if not ok:
            return _error(prompt_id, message)
        normalized[field] = items

    issues = content.get("issues", [])
    if not isinstance(issues, list):
        return _error(prompt_id, "issues must be a list")
    allowed_issue_types = {
        "entity_mismatch",
        "metric_mismatch",
        "insufficient_evidence",
        "tradeoff_missing",
        "unsupported_claim",
    }
    normalized_issues = []
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            return _error(prompt_id, f"issues[{index}] must be an object")
        issue_type = str(issue.get("type", "")).strip()
        if issue_type not in allowed_issue_types:
            return _error(
                prompt_id,
                f"issues[{index}].type must be one of {', '.join(sorted(allowed_issue_types))}",
            )
        message = str(issue.get("message", "")).strip()
        if not message:
            return _error(prompt_id, f"issues[{index}].message is required")
        fields_ok, affected_fields, fields_message = _string_list(issue.get("affected_fields", []), "affected_fields")
        if not fields_ok:
            return _error(prompt_id, f"issues[{index}].{fields_message}")
        normalized_issues.append(
            {
                "type": issue_type,
                "message": message,
                "affected_fields": affected_fields,
            }
        )
    normalized["issues"] = normalized_issues

    return _ok(
        prompt_id,
        {
            "status": normalized["status"],
            "language": normalized["language"],
            "supported_entities": normalized["supported_entities"],
            "unsupported_entities": normalized["unsupported_entities"],
            "supported_metrics": normalized["supported_metrics"],
            "unsupported_metrics": normalized["unsupported_metrics"],
            "issues": normalized["issues"],
            "revision_instructions": normalized["revision_instructions"],
            "confidence": normalized["confidence"],
        },
    )


def _validate_final_answer_composer(content: Any, schema_context: dict[str, Any]) -> dict[str, Any]:
    prompt_id = "final_answer_composer"
    if not isinstance(content, dict):
        return _error(prompt_id, "final_answer_composer output must be an object")

    allowed_keys = {
        "headline",
        "direct_answer",
        "why",
        "evidence_bullets",
        "recommendations",
        "caveats",
        "confidence",
    }
    extra_keys = sorted(set(content) - allowed_keys)
    if extra_keys:
        return _error(prompt_id, f"final_answer_composer must not return unsupported fields: {', '.join(extra_keys)}")

    normalized_answer: dict[str, Any] = {}
    for field in ("headline", "direct_answer", "why"):
        value = content.get(field)
        if not isinstance(value, str):
            return _error(prompt_id, f"{field} must be a string")
        value = value.strip()
        if not value:
            return _error(prompt_id, f"{field} must not be empty")
        normalized_answer[field] = value

    for field in ("evidence_bullets", "recommendations", "caveats"):
        ok, items, message = _string_list(content.get(field), field)
        if not ok:
            return _error(prompt_id, message)
        normalized_answer[field] = items

    confidence = str(content.get("confidence", "")).strip()
    if confidence not in {"low", "medium", "high"}:
        return _error(prompt_id, "confidence must be one of low, medium, high")
    normalized_answer["confidence"] = confidence

    business_text_fields = [
        normalized_answer["headline"],
        normalized_answer["direct_answer"],
        normalized_answer["why"],
        *normalized_answer["evidence_bullets"],
        *normalized_answer["recommendations"],
        *normalized_answer["caveats"],
    ]
    for field_text in business_text_fields:
        if _contains_internal_prompt_leak(field_text):
            return _error(prompt_id, "business_answer fields must not contain internal prompt text")
        if _contains_technical_leak(field_text):
            return _error(prompt_id, "business_answer fields must not contain technical SQL, trace, or provider metadata")
        if _looks_like_raw_parameter_dump(field_text):
            return _error(prompt_id, "business_answer fields must not contain raw parameter dumps")
        lowered = field_text.lower()
        if "reviewer_result" in lowered or "unsupported_entities=" in lowered:
            return _error(prompt_id, "business_answer fields must not expose reviewer internals")

    if _requires_cjk_response(schema_context):
        language_error = _cjk_business_answer_language_error(normalized_answer)
        if language_error:
            return _error(prompt_id, language_error)

    return _ok(prompt_id, normalized_answer)


def _validate_insight_drafter(content: Any, schema_context: dict[str, Any]) -> dict[str, Any]:
    prompt_id = "insight_drafter"
    if not isinstance(content, dict):
        return _error(prompt_id, "insight_drafter output must be an object")

    blocked_fields = {
        "sql",
        "generated_sql",
        "sql_candidates",
        "candidate_sql",
        "final_claims",
        "claims",
        "final_answer",
        "action_payload",
        "actions",
        "created_actions",
        "approval_status",
        "credentials",
        "credential",
        "secrets",
        "secret",
        "api_key",
        "token",
        "password",
    }
    leaked = sorted(blocked_fields & set(content))
    if leaked:
        return _error(prompt_id, f"insight_drafter must not return blocked fields: {', '.join(leaked)}")

    claims_ok, candidate_claims, message = _string_list(content.get("candidate_claims", []), "candidate_claims")
    if not claims_ok:
        return _error(prompt_id, message)
    if not candidate_claims:
        return _error(prompt_id, "candidate_claims must not be empty")

    business_answer = content.get("business_answer")
    if not isinstance(business_answer, dict):
        return _error(prompt_id, "business_answer is required and must be an object")
    extra_top_level = sorted(set(content) - {"candidate_claims", "business_answer"})
    if extra_top_level:
        return _error(
            prompt_id,
            f"insight_drafter must not return unsupported top-level fields: {', '.join(extra_top_level)}",
        )

    allowed_keys = {
        "headline",
        "direct_answer",
        "why",
        "evidence_bullets",
        "recommendations",
        "caveats",
        "confidence",
    }
    extra_keys = sorted(set(business_answer) - allowed_keys)
    if extra_keys:
        return _error(prompt_id, f"business_answer contains unsupported fields: {', '.join(extra_keys)}")

    normalized_answer: dict[str, Any] = {}
    for field in ("headline", "direct_answer", "why"):
        if field not in business_answer:
            return _error(prompt_id, f"business_answer.{field} is required")
        value = business_answer.get(field)
        if not isinstance(value, str):
            return _error(prompt_id, f"business_answer.{field} must be a string")
        value = value.strip()
        if not value:
            return _error(prompt_id, f"business_answer.{field} must not be empty")
        normalized_answer[field] = value

    for field in ("evidence_bullets", "recommendations", "caveats"):
        if field not in business_answer:
            return _error(prompt_id, f"business_answer.{field} is required")
        ok, items, message = _string_list(business_answer.get(field), f"business_answer.{field}")
        if not ok:
            return _error(prompt_id, message)
        normalized_answer[field] = items

    confidence = str(business_answer.get("confidence", "")).strip()
    if confidence not in {"low", "medium", "high"}:
        return _error(prompt_id, "business_answer.confidence must be one of low, medium, high")
    normalized_answer["confidence"] = confidence

    business_text_fields = [
        normalized_answer["headline"],
        normalized_answer["direct_answer"],
        normalized_answer["why"],
        *normalized_answer["evidence_bullets"],
        *normalized_answer["recommendations"],
        *normalized_answer["caveats"],
    ]
    for field_text in business_text_fields:
        if _contains_internal_prompt_leak(field_text):
            return _error(prompt_id, "business_answer fields must not contain internal report section prompt text")
        if _contains_technical_leak(field_text):
            return _error(prompt_id, "business_answer fields must not contain technical SQL, trace, or provider metadata")
        if _looks_like_raw_parameter_dump(field_text):
            return _error(prompt_id, "business_answer fields must not contain raw parameter dumps")

    if _requires_cjk_response(schema_context):
        language_error = _cjk_business_answer_language_error(normalized_answer)
        if language_error:
            return _error(prompt_id, language_error)

    if _schema_context_has_weak_evidence(schema_context):
        if normalized_answer["recommendations"]:
            return _error(prompt_id, "business_answer.recommendations must be empty when evidence is weak")
        if not normalized_answer["caveats"]:
            return _error(prompt_id, "business_answer.caveats is required when evidence is weak or limited")

    if _schema_context_has_single_row_action_limit(schema_context, normalized_answer):
        return _error(
            prompt_id,
            "business_answer must not recommend budget or resource changes without sufficient comparative evidence",
        )

    return _ok(prompt_id, {"candidate_claims": candidate_claims, "business_answer": normalized_answer})


def _looks_like_raw_parameter_dump(text: str) -> bool:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return False
    dump_lines = 0
    for line in lines:
        stripped = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line)
        assignments = re.findall(r"\b[A-Za-z_][\w. -]*\s*=", stripped)
        if len(assignments) >= 2 or (assignments and "," in stripped):
            dump_lines += 1
    return dump_lines >= max(1, len(lines) // 2)


def _contains_technical_leak(text: str) -> bool:
    value = str(text or "")
    if re.search(r"\b(?:SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|PRAGMA)\b", value, re.IGNORECASE):
        return True
    technical_markers = (
        "trace_id",
        "trace id",
        "trace_path",
        "provider_metadata",
        "provider_called",
        "prompt_id",
        "prompt_version",
        "latency_ms",
        "completion_tokens",
        "prompt_tokens",
        "raw_rows",
    )
    lowered = value.lower()
    return any(marker in lowered for marker in technical_markers)


def _contains_internal_prompt_leak(text: str) -> bool:
    lowered = str(text or "").lower()
    markers = (
        "这是自动报告内部 section",
        "自动报告内部 section",
        "本节意图提示",
        "本节问题",
        "本节目的",
        "internal section",
    )
    return any(marker in lowered for marker in markers)


def _cjk_business_answer_language_error(answer: dict[str, Any]) -> str:
    for field in ("headline", "direct_answer", "why"):
        if not _contains_cjk(str(answer.get(field) or "")):
            return f"输出语言必须跟随用户问题；中文问题下 business_answer.{field} 必须包含中文"
    for field in ("evidence_bullets", "recommendations", "caveats"):
        for index, item in enumerate(answer.get(field) or []):
            if str(item).strip() and not _contains_cjk(str(item)):
                return (
                    "输出语言必须跟随用户问题；中文问题下 "
                    f"business_answer.{field}[{index}] 必须包含中文"
                )
    return ""


def _schema_context_has_weak_evidence(schema_context: dict[str, Any]) -> bool:
    execution_result = schema_context.get("execution_result")
    if not isinstance(execution_result, dict):
        return False
    if not execution_result or execution_result.get("success") is False:
        return True
    if not execution_result.get("rows"):
        return True
    evidence_result = schema_context.get("evidence_result")
    if isinstance(evidence_result, dict):
        validation_status = str(evidence_result.get("validation_status") or evidence_result.get("status") or "").lower()
        notes = evidence_result.get("data_supported_findings") or evidence_result.get("evidence_notes") or []
        if validation_status in {"failed", "not_validated", "rejected"} and not notes:
            return True
    return False


def _schema_context_has_single_row_action_limit(
    schema_context: dict[str, Any],
    answer: dict[str, Any],
) -> bool:
    execution_result = schema_context.get("execution_result")
    if not isinstance(execution_result, dict):
        return False
    rows = execution_result.get("rows") or []
    if len(rows) != 1:
        return False
    recommendations = [str(item).strip() for item in answer.get("recommendations") or [] if str(item).strip()]
    return any(_is_budget_or_resource_action_recommendation(item) for item in recommendations)


def _is_budget_or_resource_action_recommendation(text: str) -> bool:
    lowered = str(text or "").lower()
    if not lowered or _is_evidence_gathering_recommendation(lowered):
        return False
    action_markers = (
        "加预算",
        "增加预算",
        "减少预算",
        "削减预算",
        "降低预算",
        "转移预算",
        "转向",
        "加大投放",
        "增加投放",
        "减少投放",
        "削减投放",
        "降低投放",
        "资源倾斜",
        "投入资源",
        "increase budget",
        "reduce budget",
        "cut budget",
        "shift budget",
        "allocate budget",
        "move budget",
        "increase spend",
        "reduce spend",
        "cut spend",
        "shift spend",
        "shift resources",
        "allocate resources",
        "move resources",
    )
    return any(marker in lowered for marker in action_markers)


def _is_evidence_gathering_recommendation(text: str) -> bool:
    markers = (
        "补充",
        "获取",
        "增加同口径",
        "更多",
        "完整",
        "对比数据",
        "对比证据",
        "比较证据",
        "再判断",
        "再决定",
        "add complete comparison evidence",
        "get more",
        "gather more",
        "collect more",
        "comparison evidence",
        "before deciding",
    )
    return any(marker in text for marker in markers)


def _nullable_string(value: Any, field_name: str) -> tuple[bool, str, str]:
    if value is None:
        return True, "", ""
    if isinstance(value, str):
        return True, value.strip(), ""
    return False, "", f"{field_name} must be a string or null"


def _nullable_string_or_joined_list(value: Any, field_name: str) -> tuple[bool, str, str]:
    if isinstance(value, list):
        items = []
        for index, item in enumerate(value):
            if not isinstance(item, str):
                return False, "", f"{field_name}[{index}] must be a string"
            item = item.strip()
            if item:
                items.append(item)
        return True, ", ".join(items), ""
    ok, text, message = _nullable_string(value, field_name)
    if not ok:
        return False, "", f"{field_name} must be a string, string array, or null"
    return True, text, ""


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


def _string_or_string_list(value: Any, field_name: str) -> tuple[bool, list[str], str]:
    if value is None:
        return True, [], ""
    if isinstance(value, str):
        item = value.strip()
        return True, [item] if item else [], ""
    if isinstance(value, dict):
        normalized = []
        for key, enabled in value.items():
            if enabled:
                item = str(key).strip()
                if item:
                    normalized.append(item)
        return True, normalized, ""
    return _string_list(value, field_name)


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

    ok, metric, message = _nullable_string_or_joined_list(intent.get("metric"), "intent.metric")
    if not ok:
        return _error(prompt_id, message)
    ok, dimension, message = _nullable_string_or_joined_list(intent.get("dimension"), "intent.dimension")
    if not ok:
        return _error(prompt_id, message)
    ok, operation, message = _nullable_string_or_joined_list(intent.get("operation"), "intent.operation")
    if not ok:
        return _error(prompt_id, message)

    time_range = intent.get("time_range")
    if time_range is not None and not isinstance(time_range, dict):
        return _error(prompt_id, "intent.time_range must be an object or null")

    filters_ok, filters, message = _string_or_string_list(intent.get("filters"), "intent.filters")
    if not filters_ok:
        return _error(prompt_id, message)

    limit = intent.get("limit")
    if limit is not None and not isinstance(limit, int):
        return _error(prompt_id, "intent.limit must be an int or null")

    intent_risk_ok, intent_risk_flags, message = _string_or_string_list(intent.get("risk_flags", []), "intent.risk_flags")
    if not intent_risk_ok:
        return _error(prompt_id, message)

    missing_ok, missing_slots, message = _string_or_string_list(content.get("missing_slots"), "missing_slots")
    if not missing_ok:
        return _error(prompt_id, message)
    questions_ok, clarification_questions, message = _string_or_string_list(
        content.get("clarification_questions"),
        "clarification_questions",
    )
    if not questions_ok:
        return _error(prompt_id, message)
    risk_ok, risk_flags, message = _string_or_string_list(content.get("risk_flags", []), "risk_flags")
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

    requires_clarification = bool(content.get("requires_clarification", True))
    missing_ok, missing_slots, message = _string_list(content.get("missing_slots"), "missing_slots")
    if not missing_ok:
        return _error(prompt_id, message)
    questions_ok, clarification_questions, message = _string_list(
        content.get("clarification_questions"),
        "clarification_questions",
    )
    if not questions_ok:
        return _error(prompt_id, message)
    if requires_clarification and not clarification_questions:
        return _error(prompt_id, "clarification_questions must contain at least one question")
    risk_ok, risk_flags, message = _string_list(content.get("risk_flags"), "risk_flags")
    if not risk_ok:
        return _error(prompt_id, message)

    if not requires_clarification:
        missing_slots = []
        clarification_questions = []

    return _ok(
        prompt_id,
        {
            "requires_clarification": requires_clarification,
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


def _validate_analysis_planner(content: Any) -> dict[str, Any]:
    prompt_id = "analysis_planner"
    if not isinstance(content, dict):
        return _error(prompt_id, "analysis_planner output must be an object")

    blocked_fields = {
        "sql",
        "generated_sql",
        "sql_candidates",
        "candidate_sql",
        "final_claims",
        "claims",
        "final_answer",
        "action_payload",
        "actions",
        "created_actions",
        "approval_status",
    }
    leaked = sorted(blocked_fields & set(content))
    if leaked:
        return _error(prompt_id, f"analysis_planner must not return blocked fields: {', '.join(leaked)}")

    scenario_type = str(content.get("scenario_type", "")).strip()
    allowed_scenario_types = {
        "quick_metric_lookup",
        "gmv_decline_diagnosis",
        "marketing_roi_review",
        "inventory_risk_analysis",
        "refund_anomaly_analysis",
        "promotion_review",
        "customer_segment_analysis",
        "general_non_template_analysis",
    }
    if scenario_type not in allowed_scenario_types:
        return _error(prompt_id, f"scenario_type is not supported: {scenario_type}")

    analysis_steps = content.get("analysis_steps", [])
    if not isinstance(analysis_steps, list) or not analysis_steps:
        return _error(prompt_id, "analysis_steps must be a non-empty list")

    normalized_steps = []
    for index, step in enumerate(analysis_steps):
        if not isinstance(step, dict):
            return _error(prompt_id, f"analysis_steps[{index}] must be an object")
        leaked = sorted(blocked_fields & set(step))
        if leaked:
            return _error(prompt_id, f"analysis_steps[{index}] must not return blocked fields: {', '.join(leaked)}")

        step_id = str(step.get("step_id", "")).strip()
        question = str(step.get("question", "")).strip()
        if not step_id:
            return _error(prompt_id, f"analysis_steps[{index}].step_id is required")
        if not question:
            return _error(prompt_id, f"analysis_steps[{index}].question is required")

        metrics_ok, required_metrics, message = _string_list(
            step.get("required_metrics", []),
            f"analysis_steps[{index}].required_metrics",
        )
        if not metrics_ok:
            return _error(prompt_id, message)
        dimensions_ok, required_dimensions, message = _string_list(
            step.get("required_dimensions", []),
            f"analysis_steps[{index}].required_dimensions",
        )
        if not dimensions_ok:
            return _error(prompt_id, message)
        tables_ok, candidate_tables, message = _string_list(
            step.get("candidate_tables", []),
            f"analysis_steps[{index}].candidate_tables",
        )
        if not tables_ok:
            return _error(prompt_id, message)
        if not required_metrics:
            return _error(prompt_id, f"analysis_steps[{index}].required_metrics must not be empty")
        if not candidate_tables:
            return _error(prompt_id, f"analysis_steps[{index}].candidate_tables must not be empty")

        normalized_steps.append(
            {
                "step_id": step_id,
                "question": question,
                "required_metrics": required_metrics,
                "required_dimensions": required_dimensions,
                "candidate_tables": candidate_tables,
            }
        )

    return _ok(prompt_id, {"scenario_type": scenario_type, "analysis_steps": normalized_steps})


def _validate_visualization_chart_spec(content: Any, schema_context: dict[str, Any]) -> dict[str, Any]:
    prompt_id = "visualization_agent"
    if not isinstance(content, dict):
        return _error(prompt_id, "chart_spec must be an object")

    blocked_fields = {
        "sql",
        "generated_sql",
        "sql_candidates",
        "candidate_sql",
        "final_claims",
        "claims",
        "final_answer",
        "action_payload",
        "actions",
        "created_actions",
        "approval_status",
    }
    leaked = sorted(blocked_fields & set(content))
    if leaked:
        return _error(prompt_id, f"chart_spec must not return blocked fields: {', '.join(leaked)}")

    chart_type = str(content.get("chart_type", "")).strip().lower()
    allowed_chart_types = {
        "ranked_bar",
        "line",
        "grouped_bar",
        "dual_axis_line",
        "funnel",
        "heatmap",
        "scatter",
        "risk_matrix",
    }
    if chart_type not in allowed_chart_types:
        return _error(prompt_id, f"chart_type is not supported: {chart_type}")

    title = str(content.get("title", "")).strip()
    x = str(content.get("x", "")).strip()
    y = str(content.get("y", "")).strip()
    y_secondary = str(content.get("y_secondary", "") or "").strip()
    series = str(content.get("series", "") or "").strip()
    if not title:
        return _error(prompt_id, "title is required")
    if not x:
        return _error(prompt_id, "x is required")
    if not y:
        return _error(prompt_id, "y is required")

    required_ok, required_columns, message = _string_list(content.get("required_columns", []), "required_columns")
    if not required_ok:
        return _error(prompt_id, message)
    explanation_ok, explanation_basis, message = _string_or_string_list(
        content.get("explanation_basis", []),
        "explanation_basis",
    )
    if not explanation_ok:
        return _error(prompt_id, message)
    if not explanation_basis:
        return _error(prompt_id, "explanation_basis must not be empty")

    all_referenced = list(dict.fromkeys([*required_columns, x, y, y_secondary, series]))
    all_referenced = [column for column in all_referenced if column]
    allowed_columns = set(schema_context.get("execution_columns", []))
    missing = [column for column in all_referenced if allowed_columns and column not in allowed_columns]
    if missing:
        return _error(prompt_id, f"chart_spec referenced missing execution columns: {', '.join(missing)}")

    unit = str(content.get("unit", "") or "").strip()
    value_label = bool(content.get("value_label", False))
    business_annotation = str(content.get("business_annotation", "") or "").strip()

    return _ok(
        prompt_id,
        {
            "chart_type": chart_type,
            "title": title,
            "x": x,
            "y": y,
            "y_secondary": y_secondary,
            "series": series,
            "required_columns": all_referenced,
            "explanation_basis": explanation_basis,
            "unit": unit,
            "value_label": value_label,
            "business_annotation": business_annotation,
        },
    )


def _blocked_key_paths(value: Any, blocked_fields: set[str], prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            normalized_key = key_text.strip().lower()
            if normalized_key in blocked_fields:
                paths.append(path)
            paths.extend(_blocked_key_paths(child, blocked_fields, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_blocked_key_paths(child, blocked_fields, f"{prefix}[{index}]"))
    return paths


def _validate_visualization_agent(content: Any, schema_context: dict[str, Any]) -> dict[str, Any]:
    prompt_id = "visualization_agent"
    if not isinstance(content, dict):
        return _error(prompt_id, "visualization_agent output must be an object")

    blocked_fields = {
        "sql",
        "generated_sql",
        "sql_candidates",
        "candidate_sql",
        "final_claims",
        "claims",
        "final_answer",
        "action_payload",
        "actions",
        "created_actions",
        "approval_status",
        "credentials",
        "credential",
        "secrets",
        "secret",
        "api_key",
        "token",
        "password",
        "fabricated_rows",
        "fabricated_metrics",
    }
    leaked = _blocked_key_paths(content, blocked_fields)
    if leaked:
        return _error(prompt_id, f"visualization_agent must not return blocked fields: {', '.join(sorted(leaked))}")

    chart_spec = content.get("chart_spec")
    if not isinstance(chart_spec, dict):
        return _error(prompt_id, "chart_spec must be an object")

    chart_validation = _validate_visualization_chart_spec(chart_spec, schema_context)
    if not chart_validation.get("success"):
        return _error(prompt_id, chart_validation.get("error", "chart_spec validation failed"))

    delivery_tool_id = str(content.get("delivery_tool_id", "")).strip()
    allowed_tools = set(schema_context.get("delivery_tool_ids", []))
    if not delivery_tool_id:
        return _error(prompt_id, "delivery_tool_id is required")
    if allowed_tools and delivery_tool_id not in allowed_tools:
        return _error(prompt_id, f"delivery_tool_id is not allowed: {delivery_tool_id}")

    tool_reason = str(content.get("tool_reason", "")).strip()
    if not tool_reason:
        return _error(prompt_id, "tool_reason is required")

    return _ok(
        prompt_id,
        {
            "chart_spec": chart_validation["content"],
            "delivery_tool_id": delivery_tool_id,
            "tool_reason": tool_reason,
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
    if prompt_id == "answer_reviewer":
        return _validate_answer_reviewer(content)
    if prompt_id == "final_answer_composer":
        return _validate_final_answer_composer(content, context)
    if prompt_id == "insight_drafter":
        return _validate_insight_drafter(content, context)
    if prompt_id == "question_understanding":
        return _validate_question_understanding(content)
    if prompt_id == "clarification_router":
        return _validate_clarification_router(content)
    if prompt_id == "sql_planning_router":
        return _validate_sql_planning_router(content)
    if prompt_id == "analysis_planner":
        return _validate_analysis_planner(content)
    if prompt_id == "visualization_agent":
        return _validate_visualization_agent(content, context)
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
