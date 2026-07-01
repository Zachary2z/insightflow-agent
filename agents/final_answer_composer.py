from __future__ import annotations

import re
from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request, validate_prompt_output
from workspaces.answer_evidence import (
    contains_cjk,
    entity_key,
    metric_keys,
    primary_entity,
    row_bullets,
    row_summary,
    rows_as_dicts,
)
from workspaces.product_models import empty_business_answer


def compose_final_answer(
    *,
    user_question: str,
    execution_result: dict[str, Any],
    evidence_result: dict[str, Any] | None = None,
    draft_business_answer: dict[str, Any],
    reviewer_result: dict[str, Any],
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    return compose_final_answer_result(
        user_question=user_question,
        execution_result=execution_result,
        evidence_result=evidence_result or {},
        draft_business_answer=draft_business_answer,
        reviewer_result=reviewer_result,
        provider=provider,
    )["business_answer"]


def compose_final_answer_result(
    *,
    user_question: str,
    execution_result: dict[str, Any],
    evidence_result: dict[str, Any] | None = None,
    draft_business_answer: dict[str, Any],
    reviewer_result: dict[str, Any],
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    if provider is not None:
        provider_answer = _provider_compose(
            provider=provider,
            user_question=user_question,
            execution_result=execution_result,
            evidence_result=evidence_result or {},
            draft_business_answer=draft_business_answer,
            reviewer_result=reviewer_result,
        )
        if provider_answer:
            return {"business_answer": provider_answer, "source": "provider", "provider_called": True, "error": ""}

    answer = _deterministic_compose(
        user_question=user_question,
        execution_result=execution_result,
        draft_business_answer=draft_business_answer,
        reviewer_result=reviewer_result,
    )
    return {
        "business_answer": answer,
        "source": "deterministic",
        "provider_called": provider is not None,
        "error": "" if provider is None else "provider result unavailable or invalid",
    }


def _provider_compose(
    *,
    provider: LLMProvider,
    user_question: str,
    execution_result: dict[str, Any],
    evidence_result: dict[str, Any],
    draft_business_answer: dict[str, Any],
    reviewer_result: dict[str, Any],
) -> dict[str, Any]:
    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "final_answer_composer",
        {
            "user_question": user_question,
            "execution_result": execution_result,
            "evidence_result": evidence_result,
            "draft_business_answer": draft_business_answer,
            "reviewer_result": reviewer_result,
        },
    )
    if not rendered.get("success"):
        return {}
    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "final_answer_composer"},
    )
    response = run_validated_llm_request(
        provider,
        request,
        schema_context={
            "user_question": user_question,
            "execution_result": execution_result,
            "evidence_result": evidence_result,
            "draft_business_answer": draft_business_answer,
            "reviewer_result": reviewer_result,
        },
    )
    content = response.get("content")
    return content if response.get("success") and isinstance(content, dict) else {}


def _deterministic_compose(
    *,
    user_question: str,
    execution_result: dict[str, Any],
    draft_business_answer: dict[str, Any],
    reviewer_result: dict[str, Any],
) -> dict[str, Any]:
    language = str(reviewer_result.get("language") or "")
    chinese = language == "zh" or _needs_chinese_response(user_question)
    normalized = _normalize_answer(draft_business_answer)
    status = str(reviewer_result.get("status") or "downgrade_to_insufficient_evidence")
    unsupported_values = [
        *[str(item) for item in reviewer_result.get("unsupported_entities") or []],
        *[str(item) for item in reviewer_result.get("unsupported_metrics") or []],
    ]

    if status == "accept" and not _has_blocked_text(normalized) and not _contains_any(_answer_text(normalized), unsupported_values):
        return _validate_or_rebuild(normalized, user_question=user_question, execution_result=execution_result)
    if status == "downgrade_to_insufficient_evidence":
        return _insufficient_answer(
            user_question=user_question,
            execution_result=execution_result,
            reviewer_result=reviewer_result,
            chinese=chinese,
        )
    return _evidence_based_answer(
        user_question=user_question,
        execution_result=execution_result,
        reviewer_result=reviewer_result,
        chinese=chinese,
    )


def _validate_or_rebuild(answer: dict[str, Any], *, user_question: str, execution_result: dict[str, Any]) -> dict[str, Any]:
    validation = validate_prompt_output(
        "final_answer_composer",
        answer,
        schema_context={"user_question": user_question, "execution_result": execution_result},
    )
    if validation.get("success"):
        return validation["content"]
    return _evidence_based_answer(
        user_question=user_question,
        execution_result=execution_result,
        reviewer_result={
            "status": "revise",
            "language": "zh" if _needs_chinese_response(user_question) else "en",
            "unsupported_entities": [],
            "unsupported_metrics": [],
            "issues": [],
            "confidence": "medium",
        },
        chinese=_needs_chinese_response(user_question),
    )


def _evidence_based_answer(
    *,
    user_question: str,
    execution_result: dict[str, Any],
    reviewer_result: dict[str, Any],
    chinese: bool,
) -> dict[str, Any]:
    rows = rows_as_dicts(execution_result)
    if not rows:
        return _insufficient_answer(
            user_question=user_question,
            execution_result=execution_result,
            reviewer_result=reviewer_result,
            chinese=chinese,
        )
    entity_key_value = entity_key(rows)
    metric_key_values = metric_keys(rows)
    primary = primary_entity(rows, entity_key_value=entity_key_value, metric_key_values=metric_key_values)
    first_row_summary = row_summary(rows[0], chinese=chinese)
    evidence_bullets = row_bullets(rows, chinese=chinese)
    confidence = "medium" if str(reviewer_result.get("confidence")) == "high" else str(
        reviewer_result.get("confidence") or "medium"
    )
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"

    if chinese:
        entity_text = primary or "当前第一行对象"
        answer = {
            "headline": f"当前证据支持优先关注 {entity_text}",
            "direct_answer": f"当前证据支持优先关注 {entity_text}，因为本轮返回结果中它的可用指标表现靠前。",
            "why": f"执行结果第一行显示：{first_row_summary}。",
            "evidence_bullets": evidence_bullets,
            "recommendations": [f"围绕 {entity_text} 做下一步复盘，并继续跟踪本轮返回的同口径指标。"],
            "caveats": _dedupe(["已移除 reviewer 标记为缺少证据支撑的实体、指标或表述。"]),
            "confidence": confidence,
        }
    else:
        entity_text = primary or "the first returned entity"
        answer = {
            "headline": f"The current evidence supports focusing on {entity_text}",
            "direct_answer": (
                f"Focus on {entity_text} for now because the returned evidence ranks it first on the available metrics."
            ),
            "why": f"The first result row shows: {first_row_summary}.",
            "evidence_bullets": evidence_bullets,
            "recommendations": [f"Use {entity_text} as the next review focus and keep tracking the returned metrics."],
            "caveats": _dedupe(["Unsupported entities, metrics, or claims from the draft were removed."]),
            "confidence": confidence,
        }
    return _validate_or_empty(answer, user_question=user_question)


def _insufficient_answer(
    *,
    user_question: str,
    execution_result: dict[str, Any],
    reviewer_result: dict[str, Any],
    chinese: bool,
) -> dict[str, Any]:
    rows = rows_as_dicts(execution_result)
    bullets = row_bullets(rows, chinese=chinese) if rows else []
    unsupported_entities = [str(item) for item in reviewer_result.get("unsupported_entities") or [] if str(item).strip()]
    unsupported_metrics = [str(item) for item in reviewer_result.get("unsupported_metrics") or [] if str(item).strip()]
    if chinese:
        caveat = "当前证据不足以支持原结论。"
        if unsupported_entities or unsupported_metrics:
            caveat += "缺少证据支撑的对象或指标已从最终回答中移除。"
        answer = {
            "headline": "当前证据不足以支持该结论",
            "direct_answer": "当前证据不足以支持该结论，需要补充可验证的同口径数据后再判断。",
            "why": "Reviewer 发现原草稿中的关键对象、指标或判断没有足够执行结果支撑。",
            "evidence_bullets": bullets,
            "recommendations": ["先补充能够覆盖目标对象和指标的同口径证据，再生成确定性建议。"],
            "caveats": [caveat],
            "confidence": "low",
        }
    else:
        caveat = "The current evidence is insufficient for the original conclusion."
        if unsupported_entities or unsupported_metrics:
            caveat += " Unsupported entities or metrics were removed from the final answer."
        answer = {
            "headline": "Current evidence is insufficient for that conclusion",
            "direct_answer": "There is not enough evidence to support that conclusion yet.",
            "why": "The review found that key entities, metrics, or claims in the draft are not supported by the returned result.",
            "evidence_bullets": bullets,
            "recommendations": ["Add comparable evidence covering the target entities and metrics before making a decision."],
            "caveats": [caveat],
            "confidence": "low",
        }
    return _validate_or_empty(answer, user_question=user_question)


def _normalize_answer(answer: dict[str, Any]) -> dict[str, Any]:
    normalized = empty_business_answer()
    normalized.update(
        {
            "headline": _clean_text(answer.get("headline")),
            "direct_answer": _clean_text(answer.get("direct_answer")),
            "why": _clean_text(answer.get("why")),
            "evidence_bullets": [_clean_text(item) for item in answer.get("evidence_bullets") or [] if _clean_text(item)],
            "recommendations": [_clean_text(item) for item in answer.get("recommendations") or [] if _clean_text(item)],
            "caveats": [_clean_text(item) for item in answer.get("caveats") or [] if _clean_text(item)],
            "confidence": str(answer.get("confidence") or "medium"),
        }
    )
    if normalized["confidence"] not in {"low", "medium", "high"}:
        normalized["confidence"] = "medium"
    return normalized


def _validate_or_empty(answer: dict[str, Any], *, user_question: str) -> dict[str, Any]:
    validation = validate_prompt_output(
        "final_answer_composer",
        answer,
        schema_context={"user_question": user_question},
    )
    if validation.get("success"):
        return validation["content"]
    fallback = empty_business_answer()
    fallback.update(
        {
            "headline": "当前证据不足以支持该结论" if _needs_chinese_response(user_question) else "Current evidence is insufficient",
            "direct_answer": (
                "当前证据不足以生成可靠业务结论。"
                if _needs_chinese_response(user_question)
                else "The current evidence is insufficient for a reliable business answer."
            ),
            "why": (
                "最终回答校验未通过，已降级为证据不足。"
                if _needs_chinese_response(user_question)
                else "Final answer validation failed, so the answer was downgraded."
            ),
            "caveats": ["需要补充更多可验证数据。"] if _needs_chinese_response(user_question) else ["More verifiable data is needed."],
            "confidence": "low",
        }
    )
    return fallback


def _answer_text(answer: dict[str, Any]) -> str:
    return " ".join(
        [
            answer["headline"],
            answer["direct_answer"],
            answer["why"],
            *answer["evidence_bullets"],
            *answer["recommendations"],
            *answer["caveats"],
        ]
    )


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"```sql\s*.*?```", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\b(?:SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|PRAGMA)\b.+", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\b(?:trace_id|trace_path|prompt_id|provider_metadata)\s*=\s*\S+", "", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def _has_blocked_text(answer: dict[str, Any]) -> bool:
    lowered = _answer_text(answer).lower()
    blocked = (
        "select ",
        "with ",
        "insert ",
        "update ",
        "delete ",
        "trace_id",
        "trace_path",
        "prompt_id",
        "provider_metadata",
        "reviewer_result",
    )
    return any(marker in lowered for marker in blocked)


def _contains_any(text: str, values: list[str]) -> bool:
    return any(value and value in text for value in values)


def _needs_chinese_response(question: str) -> bool:
    if not contains_cjk(question):
        return False
    lowered = str(question or "").lower()
    return not any(marker in lowered for marker in ("用英文", "英文回答", "answer in english", "in english"))


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
