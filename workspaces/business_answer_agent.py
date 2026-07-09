from __future__ import annotations

import re
from typing import Any

from agents.answer_reviewer import review_answer
from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider
from llm_ops.provider import LLMRequest
from llm_ops.provider import run_llm_request
from llm_ops.structured_output import validate_prompt_output
from tools.trace_logger import append_trace
from workspaces.evidence_auditor import run_evidence_auditor_agent
from workspaces.product_models import empty_business_answer
from workspaces.question_evidence_ledger import (
    build_answer_input_ledger,
    ledger_supports_claim,
)


def run_business_answer_agent(
    state: dict[str, Any],
    *,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    execution_result = state.get("execution_result") if isinstance(state.get("execution_result"), dict) else {}
    retry_used = False
    if provider and execution_result.get("success"):
        output = _provider_output(state, provider, execution_result)
    else:
        output = _fallback_output(
            state,
            execution_result,
            provider_called=provider is not None,
            provider_error="" if provider is None else "provider requires successful execution_result",
        )

    candidate_claims, typed_claims = _normalize_claims(output.get("candidate_claims"))
    checked = _deterministic_check_and_repair(
        state=state,
        draft_business_answer=output["business_answer"],
        execution_result=execution_result,
        typed_candidate_claims=typed_claims,
    )
    if (
        provider
        and execution_result.get("success")
        and output.get("provider_called")
        and (output.get("source") == "provider" or output.get("validation_error"))
        and _is_generation_failed_answer(checked)
    ):
        retry_output = _provider_output(
            state,
            provider,
            execution_result,
            retry_feedback=(
                "safe-review retry: the previous draft failed product safety review. "
                "Rewrite the answer from the evidence ledger only. Use fact_text, business_object, label, value, and unit; "
                "do not mention SQL, column names, task ids, provider metadata, or unsupported metrics."
            ),
        )
        retry_claims, retry_typed_claims = _normalize_claims(retry_output.get("candidate_claims"))
        retry_checked = _deterministic_check_and_repair(
            state=state,
            draft_business_answer=retry_output["business_answer"],
            execution_result=execution_result,
            typed_candidate_claims=retry_typed_claims,
        )
        if retry_output.get("source") == "provider" and not _is_generation_failed_answer(retry_checked):
            output = retry_output
            candidate_claims = retry_claims
            typed_claims = retry_typed_claims
            checked = retry_checked
            retry_used = True
    checks = state.get("_business_answer_checks") if isinstance(state.get("_business_answer_checks"), dict) else {}
    business_answer = _normalize_business_answer(checked, chinese=_needs_chinese_response(state.get("user_question", "")))
    business_answer = _apply_ledger_boundaries(
        business_answer,
        state.get("question_evidence_ledger") if isinstance(state.get("question_evidence_ledger"), dict) else {},
    )
    final_answer = business_answer.get("direct_answer") or business_answer.get("headline") or ""
    generation = {
        **output,
        "business_answer": business_answer,
        "final_answer": final_answer,
        "candidate_claims": candidate_claims,
        "typed_candidate_claims": typed_claims,
        "retry_used": retry_used,
        "deterministic_check": {
            "review_status": (checks.get("answer_review") or {}).get("status", ""),
            "composition_source": (checks.get("answer_composition") or {}).get("source", ""),
        },
    }
    answered = append_trace(
        {
            **state,
            "business_answer_generation": generation,
            "business_answer": business_answer,
            "final_answer": final_answer,
            "claims_to_validate": candidate_claims,
            "candidate_claims": candidate_claims,
            "candidate_claims_typed": typed_claims,
            "status": "completed" if execution_result.get("success") else "failed",
            "data_used": bool(output.get("data_used")),
        },
        {
            "node": "business_answer_agent",
            "tool_name": "provider_business_answer" if output.get("provider_called") else "",
            "tool_input_summary": f"row_count={execution_result.get('row_count', len(execution_result.get('rows') or []))}",
            "tool_output_summary": final_answer[:200],
            "status": "success" if output.get("success") else "error",
            "latency_ms": output.get("latency_ms", 0),
            "error_type": None if output.get("success") else "business_answer_error",
            "provider_called": bool(output.get("provider_called")),
            "fallback_used": bool(output.get("fallback_used")),
            "prompt_id": output.get("prompt_id", "business_answer"),
            "validation_error": output.get("validation_error", ""),
            "provider_error": output.get("provider_error", ""),
        },
    )
    audited = run_evidence_auditor_agent(answered)
    audited["status"] = "completed" if execution_result.get("success") else "failed"
    audited["data_used"] = bool(output.get("data_used"))
    return audited


def _apply_ledger_boundaries(answer: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    if not ledger:
        return answer
    updated = dict(answer)
    caveats = [str(item) for item in updated.get("caveats") or [] if str(item).strip()]
    note = _scrub_business_limit(str(ledger.get("time_policy_note") or "").strip())
    if note and note not in " ".join([str(updated.get("direct_answer") or ""), *caveats]):
        caveats.append(note)
    for limit in _business_data_limits(ledger):
        text = str(limit or "").strip()
        if text and text not in caveats:
            caveats.append(text)
    updated["caveats"] = list(dict.fromkeys(caveats))
    if ledger.get("confidence") == "low":
        updated["confidence"] = "low"
    return updated


def _business_data_limits(ledger: dict[str, Any]) -> list[str]:
    raw_limits = [str(item).strip() for item in ledger.get("data_limits") or [] if str(item).strip()]
    limits: list[str] = []
    if any("证据任务" in item for item in raw_limits):
        if ledger.get("facts") or ledger.get("derived_metrics"):
            limits.append("部分辅助证据未能完成；本次结论仍以已取得的核心证据为准。")
        else:
            limits.append("核心证据未能完整取得，因此当前数据不足以支持确定结论。")
    for item in raw_limits:
        if _looks_internal_limit(item):
            continue
        cleaned = _scrub_business_limit(item)
        if cleaned and cleaned not in limits:
            limits.append(cleaned)
    return limits


def _scrub_business_limit(text: str) -> str:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"按\s*[A-Za-z_][A-Za-z0-9_.]*\s*统计", "按业务日期统计", cleaned)
    replacements = {
        "business_date": "业务日期",
        "avg_response_minutes": "平均响应时长",
        "ticket_count": "工单数",
        "total_tickets": "总工单数",
        "avg_response": "平均响应时长",
        "priority_score": "优先级评分",
    }
    for raw, label in replacements.items():
        cleaned = re.sub(rf"\b{re.escape(raw)}\b", label, cleaned, flags=re.IGNORECASE)
    return cleaned


def _looks_internal_limit(text: str) -> bool:
    lowered = str(text or "").lower()
    if "证据任务" in text:
        return True
    return any(
        marker in lowered
        for marker in (
            "select ",
            "with ",
            "trace_path",
            "provider_metadata",
            "api_key",
            "core_fact",
            "trend_or_anomaly_support",
            "explanation_support",
        )
    )


def _provider_output(
    state: dict[str, Any],
    provider: LLMProvider,
    execution_result: dict[str, Any],
    *,
    retry_feedback: str = "",
) -> dict[str, Any]:
    answer_input_ledger = build_answer_input_ledger(
        state.get("question_evidence_ledger") if isinstance(state.get("question_evidence_ledger"), dict) else {}
    )
    if not answer_input_ledger.get("evidence_groups"):
        return _fallback_output(
            state,
            execution_result,
            provider_called=True,
            provider_error="answer-safe grouped evidence ledger is empty",
        )
    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "business_answer",
        {
            "user_question": state.get("user_question", ""),
            "question_evidence_ledger": answer_input_ledger,
        },
    )
    if not rendered.get("success"):
        return _fallback_output(
            state,
            execution_result,
            provider_called=True,
            provider_error=rendered.get("error", ""),
        )

    request = LLMRequest(
        prompt=rendered["prompt"] + (f"\n\n{retry_feedback}" if retry_feedback else ""),
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={
            "node": "business_answer_agent",
            "retry_feedback": retry_feedback,
            "schema_context": {
                "user_question": state.get("user_question", ""),
                "question_evidence_ledger": answer_input_ledger,
            },
        },
    )
    schema_context = {
        "user_question": state.get("user_question", ""),
        "question_evidence_ledger": answer_input_ledger,
    }
    response = run_llm_request(provider, request)
    if not response.get("success"):
        return _fallback_output(
            state,
            execution_result,
            provider_called=True,
            provider_error=response.get("error", ""),
        )

    validation = validate_prompt_output("business_answer", response.get("content"), schema_context)
    validation_error = ""
    if not validation.get("success"):
        validation_error = str(validation.get("error") or "")
        coerced_content = _coerce_provider_business_answer_content(response.get("content"))
        if coerced_content is not None:
            validation = validate_prompt_output("business_answer", coerced_content, schema_context)
    if not validation.get("success"):
        return _fallback_output(
            state,
            execution_result,
            provider_called=True,
            validation_error=validation_error or str(validation.get("error") or ""),
        )

    content = validation.get("content") if isinstance(validation.get("content"), dict) else {}
    provider_answer = content.get("business_answer") if isinstance(content.get("business_answer"), dict) else {}
    return {
        "success": True,
        "source": "provider",
        "provider_called": True,
        "fallback_used": False,
        "final_answer": str(provider_answer.get("direct_answer") or ""),
        "business_answer": provider_answer,
        "candidate_claims": content.get("candidate_claims", []),
        "data_used": True,
        "error": "",
        "provider_error": "",
        "validation_error": validation_error,
        "prompt_id": response.get("prompt_id", "business_answer"),
        "prompt_version": response.get("prompt_version", ""),
        "model": response.get("model", ""),
        "usage": response.get("usage", {}),
        "latency_ms": response.get("latency_ms", 0),
    }


def _coerce_provider_business_answer_content(content: Any) -> dict[str, Any] | None:
    if not isinstance(content, dict):
        return None
    answer = content.get("business_answer")
    if not isinstance(answer, dict):
        return None
    normalized_answer = {
        "headline": str(answer.get("headline") or "").strip(),
        "direct_answer": str(answer.get("direct_answer") or "").strip(),
        "why": str(answer.get("why") or "").strip(),
        "evidence_bullets": _coerce_text_list(answer.get("evidence_bullets")),
        "recommendations": _coerce_text_list(answer.get("recommendations")),
        "caveats": _coerce_text_list(answer.get("caveats")),
        "confidence": str(answer.get("confidence") or "medium").strip().lower(),
    }
    if normalized_answer["confidence"] not in {"low", "medium", "high"}:
        normalized_answer["confidence"] = "medium"
    return {
        "candidate_claims": _coerce_candidate_claims(content.get("candidate_claims"), normalized_answer),
        "business_answer": normalized_answer,
    }


def _coerce_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _coerce_candidate_claims(value: Any, answer: dict[str, Any]) -> list[Any]:
    if isinstance(value, list):
        cleaned = [item for item in value if str(item).strip()]
        if cleaned:
            return cleaned
    claims: list[Any] = []
    direct_answer = str(answer.get("direct_answer") or "").strip()
    if direct_answer:
        claims.append({"claim": direct_answer, "category": "business_inference"})
    for item in answer.get("evidence_bullets") or []:
        claims.append({"claim": str(item), "category": "hard_fact"})
    for item in answer.get("caveats") or []:
        claims.append({"claim": str(item), "category": "data_limit"})
    return claims


def _fallback_output(
    state: dict[str, Any],
    execution_result: dict[str, Any],
    *,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    answer = _answer_generation_failed(
        user_question=str(state.get("user_question") or ""),
        chinese=_needs_chinese_response(state.get("user_question", "")),
    )
    return {
        "success": False,
        "source": "provider_unavailable",
        "provider_called": provider_called,
        "fallback_used": True,
        "final_answer": answer.get("direct_answer") or "",
        "business_answer": answer,
        "candidate_claims": [],
        "data_used": bool(execution_result.get("success")),
        "error": "" if execution_result.get("success") else execution_result.get("error", "execution_result failed"),
        "provider_error": provider_error,
        "validation_error": validation_error,
        "prompt_id": "business_answer",
    }


def _is_generation_failed_answer(answer: dict[str, Any]) -> bool:
    text = " ".join(_claims_from_answer(answer))
    return any(
        marker in text
        for marker in (
            "业务回答生成失败",
            "业务回答缺失",
            "Answer generation failed",
            "Business answer missing",
        )
    )


def _deterministic_check_and_repair(
    *,
    state: dict[str, Any],
    draft_business_answer: dict[str, Any],
    execution_result: dict[str, Any],
    typed_candidate_claims: list[dict[str, str]],
) -> dict[str, Any]:
    chinese = _needs_chinese_response(state.get("user_question", ""))
    normalized = _normalize_business_answer(draft_business_answer, chinese=chinese)
    review = review_answer(
        user_question=state.get("user_question", ""),
        execution_result=execution_result,
        evidence_result=state.get("evidence_result") or {},
        draft_business_answer=draft_business_answer,
        profile_context={
            "business_context": state.get("business_context") or {},
            "metric_context": state.get("metric_context") or {},
            "workspace_context": state.get("workspace_context") or {},
        },
    )
    composition = _repair_provider_answer(
        user_question=str(state.get("user_question") or ""),
        draft_business_answer=normalized,
        reviewer_result=review,
        chinese=chinese,
        ledger=state.get("question_evidence_ledger") if isinstance(state.get("question_evidence_ledger"), dict) else {},
        context_pack=state.get("fast_fact_context_pack") if isinstance(state.get("fast_fact_context_pack"), dict) else {},
        execution_success=bool(execution_result.get("success")),
        typed_candidate_claims=typed_candidate_claims,
    )
    state.setdefault("_business_answer_checks", {})
    state["_business_answer_checks"] = {"answer_review": review, "answer_composition": composition}
    return composition["business_answer"]


def _repair_provider_answer(
    *,
    user_question: str,
    draft_business_answer: dict[str, Any],
    reviewer_result: dict[str, Any],
    chinese: bool,
    ledger: dict[str, Any],
    context_pack: dict[str, Any],
    execution_success: bool,
    typed_candidate_claims: list[dict[str, str]],
) -> dict[str, Any]:
    status = str(reviewer_result.get("status") or "")
    unsupported_values = _unique_text(
        [
            *_unsupported_values(reviewer_result),
            *_unsupported_hard_fact_fragments(ledger=ledger, typed_candidate_claims=typed_candidate_claims),
        ]
    )
    answer_text = _answer_text(draft_business_answer)
    if status == "accept" and not unsupported_values and not _contains_internal_leak(answer_text):
        return {
            "business_answer": draft_business_answer,
            "source": "provider_preserved",
            "provider_called": False,
            "error": "",
        }

    if status == "downgrade_to_insufficient_evidence" or _primary_answer_has_internal_text(draft_business_answer):
        del ledger, context_pack, execution_success
        return {
            "business_answer": _answer_generation_failed(user_question=user_question, chinese=chinese),
            "source": "scrubbed_provider_answer",
            "provider_called": False,
            "error": "",
        }

    scrubbed = _scrub_answer_items(
        draft_business_answer,
        unsupported_values=unsupported_values,
        chinese=chinese,
    )
    if not scrubbed.get("direct_answer") or _contains_internal_leak(_answer_text(scrubbed)):
        scrubbed = _answer_generation_failed(user_question=user_question, chinese=chinese)
    return {
        "business_answer": scrubbed,
        "source": "scrubbed_provider_answer",
        "provider_called": False,
        "error": "",
    }


def _answer_generation_failed(*, user_question: str, chinese: bool) -> dict[str, Any]:
    del user_question
    if chinese:
        return _normalize_business_answer(
            {
                "headline": "业务回答生成失败",
                "direct_answer": "业务回答生成失败：当前没有可用的模型回答可安全展示，且系统不会从原始查询行拼接最终业务结论。",
                "why": "为避免把未验证或内部字段包装成结论，本轮只保留证据、图表和技术明细。",
                "evidence_bullets": [],
                "recommendations": [],
                "caveats": ["请重新生成回答，或查看证据区确认本轮可用事实。"],
                "confidence": "low",
            },
            chinese=True,
        )
    return _normalize_business_answer(
        {
            "headline": "Answer generation failed",
            "direct_answer": "Answer generation failed: no safe model-written answer is available, and raw rows are not used to compose the final conclusion.",
            "why": "The system avoids turning unsupported facts or internal fields into a business conclusion.",
            "evidence_bullets": [],
            "recommendations": [],
            "caveats": ["Regenerate the answer or inspect the evidence section for available facts."],
            "confidence": "low",
        },
        chinese=False,
    )


def _normalize_business_answer(answer: dict[str, Any], *, chinese: bool) -> dict[str, Any]:
    normalized = empty_business_answer()
    normalized.update(
        {
            "headline": _clean_business_text(answer.get("headline"), chinese=chinese),
            "direct_answer": _clean_business_text(answer.get("direct_answer"), chinese=chinese),
            "why": _clean_business_text(answer.get("why"), chinese=chinese),
            "evidence_bullets": [
                _clean_business_text(item, chinese=chinese)
                for item in answer.get("evidence_bullets") or []
                if _clean_business_text(item, chinese=chinese)
            ],
            "recommendations": [
                _clean_business_text(item, chinese=chinese)
                for item in answer.get("recommendations") or []
                if _clean_business_text(item, chinese=chinese)
            ],
            "caveats": [
                _clean_business_text(item, chinese=chinese)
                for item in answer.get("caveats") or []
                if _clean_business_text(item, chinese=chinese)
            ],
            "confidence": str(answer.get("confidence") or "medium"),
        }
    )
    if normalized["confidence"] not in {"low", "medium", "high"}:
        normalized["confidence"] = "medium"
    return normalized


def _scrub_answer_items(
    answer: dict[str, Any],
    *,
    unsupported_values: list[str],
    chinese: bool,
) -> dict[str, Any]:
    scrubbed = dict(answer)
    for field in ("headline", "direct_answer", "why"):
        scrubbed[field] = _scrub_unsupported_text(
            str(scrubbed.get(field) or ""),
            unsupported_values=unsupported_values,
            chinese=chinese,
        )
    if not str(scrubbed.get("why") or "").strip():
        scrubbed["why"] = (
            "结论仅保留已验证证据支持的部分；未被证据支持的解释已移除。"
            if chinese
            else "The answer keeps only the parts supported by validated evidence; unsupported explanation text was removed."
        )
    for field in ("evidence_bullets", "recommendations", "caveats"):
        cleaned_items = []
        for item in scrubbed.get(field) or []:
            cleaned = _scrub_unsupported_text(str(item), unsupported_values=unsupported_values, chinese=chinese)
            if cleaned:
                cleaned_items.append(cleaned)
        scrubbed[field] = cleaned_items
    caveat = "已移除未被证据支持或包含内部字段的表述。" if chinese else "Unsupported or internal-field statements were removed."
    scrubbed["caveats"] = list(dict.fromkeys([*scrubbed.get("caveats", []), caveat]))
    scrubbed["confidence"] = "low" if str(scrubbed.get("confidence")) == "low" else "medium"
    return _normalize_business_answer(scrubbed, chinese=chinese)


def _primary_answer_has_internal_text(answer: dict[str, Any]) -> bool:
    return any(_contains_internal_leak(str(answer.get(field) or "")) for field in ("headline", "direct_answer"))


def _unsupported_values(reviewer_result: dict[str, Any]) -> list[str]:
    return [
        str(item)
        for item in [
            *list(reviewer_result.get("unsupported_entities") or []),
            *list(reviewer_result.get("unsupported_metrics") or []),
        ]
        if str(item).strip()
    ]


def _unsupported_hard_fact_fragments(
    *,
    ledger: dict[str, Any],
    typed_candidate_claims: list[dict[str, str]],
) -> list[str]:
    fragments: list[str] = []
    if not ledger or not typed_candidate_claims:
        return fragments
    for item in typed_candidate_claims:
        if item.get("category") != "hard_fact":
            continue
        claim = str(item.get("claim") or "").strip()
        if not claim or ledger_supports_claim(ledger, claim):
            continue
        if _claim_numbers(claim) or _contains_internal_leak(claim):
            fragments.append(claim)
            fragments.extend(_claim_numbers(claim))
    return _unique_text(fragments)


def _scrub_unsupported_text(text: str, *, unsupported_values: list[str], chinese: bool) -> str:
    value = str(text or "").strip()
    if not value or _contains_internal_leak(value):
        return ""
    if not _contains_any(value, unsupported_values):
        return value
    segments = re.split(r"([。！？；;]|(?<!\d)[.!?](?!\d))", value)
    cleaned_segments: list[str] = []
    for index in range(0, len(segments), 2):
        segment = segments[index].strip()
        punctuation = segments[index + 1] if index + 1 < len(segments) else ""
        if not segment:
            continue
        clauses = re.split(r"([，,])", segment)
        cleaned_clauses: list[str] = []
        for clause_index in range(0, len(clauses), 2):
            clause = clauses[clause_index].strip()
            delimiter = clauses[clause_index + 1] if clause_index + 1 < len(clauses) else ""
            if not clause or _contains_any(clause, unsupported_values) or _contains_internal_leak(clause):
                continue
            cleaned_clauses.append(clause + delimiter)
        cleaned = "".join(cleaned_clauses).rstrip("，, ")
        if cleaned and not _contains_any(cleaned, unsupported_values):
            cleaned_segments.append(cleaned + punctuation)
    cleaned_text = "".join(cleaned_segments).strip()
    if cleaned_text:
        return cleaned_text
    return "" if chinese else ""


def _claim_numbers(value: Any) -> list[str]:
    numbers = []
    normalized_text = str(value or "")
    for match in re.finditer(r"(?<![\d.])(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*([万亿]?)(?!\s*[天日年月])(?!\d)", normalized_text):
        normalized = match.group(1).replace(",", "")
        unit = match.group(2)
        if unit == "万":
            normalized = _scale_number_text(normalized, 10000)
        elif unit == "亿":
            normalized = _scale_number_text(normalized, 100000000)
        if normalized not in numbers:
            numbers.append(normalized)
    return numbers


def _scale_number_text(value: str, scale: int) -> str:
    try:
        scaled = float(value) * scale
    except ValueError:
        return value
    if scaled.is_integer():
        return str(int(scaled))
    return str(scaled)


def _unique_text(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in unique:
            unique.append(text)
    return unique


def _answer_text(answer: dict[str, Any]) -> str:
    return " ".join(_claims_from_answer(answer))


def _contains_any(text: str, values: list[str]) -> bool:
    lowered = str(text or "").lower()
    text_numbers = set(_claim_numbers(text))
    for value in values:
        candidate = str(value or "").strip()
        if not candidate:
            continue
        candidate_numbers = _claim_numbers(candidate)
        if candidate_numbers:
            if any(number in text_numbers for number in candidate_numbers):
                return True
            continue
        if candidate.lower() in lowered:
            return True
    return False


def _contains_internal_leak(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(
        marker in lowered
        for marker in (
            "select ",
            "with ",
            "task_id",
            "task_purpose",
            "trace_id",
            "trace_path",
            "provider_metadata",
            "raw_rows",
            "prompt_id",
            "prompt_version",
            "corefact",
            "explanationsupport",
            "trend_or_anomaly_support",
            "core_fact",
            "explanation_support",
        )
    )


def _clean_business_text(text: Any, *, chinese: bool) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    if _contains_internal_leak(value):
        return ""
    if chinese:
        return " ".join(value.split())
    return " ".join(value.split())


def _needs_chinese_response(question: Any) -> bool:
    text = str(question or "")
    if not any("\u4e00" <= char <= "\u9fff" for char in text):
        return False
    lowered = text.lower()
    return not any(marker in lowered for marker in ("用英文", "英文回答", "answer in english", "in english"))


def _normalize_claims(value: Any) -> tuple[list[str], list[dict[str, str]]]:
    raw_items = value if isinstance(value, list) else []
    claim_texts: list[str] = []
    typed: list[dict[str, str]] = []
    for item in raw_items:
        if isinstance(item, dict):
            claim = str(item.get("claim") or "").strip()
            category = str(item.get("category") or item.get("claim_type") or "").strip()
        else:
            claim = str(item).strip()
            category = ""
        if not claim:
            continue
        if claim not in claim_texts:
            claim_texts.append(claim)
        if category:
            typed.append({"claim": claim, "category": category})
    return claim_texts, typed


def _claims_from_answer(answer: dict[str, Any]) -> list[str]:
    return [
        str(answer.get("headline") or ""),
        str(answer.get("direct_answer") or ""),
        str(answer.get("why") or ""),
        *[str(item) for item in answer.get("evidence_bullets") or []],
        *[str(item) for item in answer.get("recommendations") or []],
        *[str(item) for item in answer.get("caveats") or []],
    ]


__all__ = ["run_business_answer_agent"]
