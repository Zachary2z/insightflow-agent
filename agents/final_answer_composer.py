from __future__ import annotations

import re
from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request, validate_prompt_output
from workspaces.answer_evidence import (
    business_field_label,
    business_field_labels,
    contains_cjk,
    entity_key,
    metric_keys,
    primary_entity,
    row_bullets,
    row_summary,
    rows_as_dicts,
    to_number,
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
    normalized = _normalize_answer(draft_business_answer, chinese=chinese)
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
    if _review_has_issue(reviewer_result, "tradeoff_missing"):
        tradeoff_answer = _tradeoff_answer(
            user_question=user_question,
            execution_result=execution_result,
            reviewer_result=reviewer_result,
            chinese=chinese,
        )
        if tradeoff_answer:
            return tradeoff_answer

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
            "caveats": _composer_caveats(reviewer_result, chinese=True),
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
            "caveats": _composer_caveats(reviewer_result, chinese=False),
            "confidence": confidence,
        }
    return _validate_or_empty(answer, user_question=user_question)


def _tradeoff_answer(
    *,
    user_question: str,
    execution_result: dict[str, Any],
    reviewer_result: dict[str, Any],
    chinese: bool,
) -> dict[str, Any]:
    rows = rows_as_dicts(execution_result)
    entity_key_value = entity_key(rows)
    metric_key_values = metric_keys(rows)
    if not rows or not entity_key_value or len(metric_key_values) < 2:
        return {}

    revenue_metric = _first_metric(metric_key_values, {"total_revenue", "sum_revenue", "revenue", "gmv"})
    efficiency_metric = _first_metric(metric_key_values, {"roi", "roas"})
    revenue_leader = _metric_leader(rows, entity_key_value=entity_key_value, metric=revenue_metric) if revenue_metric else ""
    efficiency_leader = (
        _metric_leader(rows, entity_key_value=entity_key_value, metric=efficiency_metric)
        if efficiency_metric
        else ""
    )
    if not revenue_leader or not efficiency_leader or revenue_leader == efficiency_leader:
        return {}

    confidence = str(reviewer_result.get("confidence") or "medium")
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"
    evidence_bullets = row_bullets(rows, chinese=chinese)
    revenue_label = business_field_label(revenue_metric, chinese=chinese)
    efficiency_label = business_field_label(efficiency_metric, chinese=chinese)
    revenue_value = _metric_value(rows, entity_key_value=entity_key_value, entity=revenue_leader, metric=revenue_metric)
    efficiency_value = _metric_value(rows, entity_key_value=entity_key_value, entity=efficiency_leader, metric=efficiency_metric)

    if chinese:
        answer = {
            "headline": "收入规模与投放效率指向不同渠道",
            "direct_answer": (
                f"不能只按单一赢家判断：{revenue_label}最高的是 {revenue_leader}"
                f"（{revenue_value}），但 {efficiency_label} 最高的是 {efficiency_leader}"
                f"（{efficiency_value}）。如果目标是扩大收入规模，优先复盘 {revenue_leader}；"
                f"如果目标是提升投放效率，优先复盘 {efficiency_leader}，并建议进一步验证其预算可扩量。"
            ),
            "why": (
                f"本轮数据同时返回了{revenue_label}和{efficiency_label}，两个指标的领先渠道不同，"
                "因此更适合按目标做取舍，而不是把排名直接解释为因果结论。"
            ),
            "evidence_bullets": evidence_bullets,
            "recommendations": [
                f"规模目标：优先复盘 {revenue_leader} 的预算承接能力和订单来源。",
                f"效率目标：建议进一步验证 {efficiency_leader} 的可扩量空间，再决定是否加预算。",
            ],
            "caveats": _dedupe(
                [
                    "当前结论只基于本次返回的指标，不能证明加预算一定带来增量增长。",
                    *_composer_caveats(reviewer_result, chinese=True),
                ]
            ),
            "confidence": confidence,
        }
    else:
        answer = {
            "headline": "Scale and efficiency point to different channels",
            "direct_answer": (
                f"There is no single winner across metrics: {revenue_leader} leads on {revenue_label} "
                f"({revenue_value}), while {efficiency_leader} leads on {efficiency_label} ({efficiency_value}). "
                f"Prioritize {revenue_leader} for scale, or validate {efficiency_leader} further if efficiency is the goal."
            ),
            "why": (
                f"The returned rows include both {revenue_label} and {efficiency_label}, and they point to different leaders."
            ),
            "evidence_bullets": evidence_bullets,
            "recommendations": [
                f"For scale, review {revenue_leader}'s budget capacity and order sources.",
                f"For efficiency, validate whether {efficiency_leader} can scale before increasing budget.",
            ],
            "caveats": _dedupe(
                [
                    "The current evidence does not prove that additional budget will cause incremental growth.",
                    *_composer_caveats(reviewer_result, chinese=False),
                ]
            ),
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


def _review_has_issue(reviewer_result: dict[str, Any], issue_type: str) -> bool:
    return any(
        str(issue.get("type") or "") == issue_type
        for issue in reviewer_result.get("issues") or []
        if isinstance(issue, dict)
    )


def _first_metric(metrics: list[str], candidates: set[str]) -> str:
    for metric in metrics:
        if metric.lower() in candidates:
            return metric
    return ""


def _metric_leader(rows: list[dict[str, Any]], *, entity_key_value: str, metric: str) -> str:
    ranked: list[tuple[str, float]] = []
    for row in rows:
        entity = str(row.get(entity_key_value) or "").strip()
        value = to_number(row.get(metric))
        if entity and value is not None:
            ranked.append((entity, value))
    if not ranked:
        return ""
    return max(ranked, key=lambda item: item[1])[0]


def _metric_value(rows: list[dict[str, Any]], *, entity_key_value: str, entity: str, metric: str) -> Any:
    for row in rows:
        if str(row.get(entity_key_value) or "").strip() == entity:
            return row.get(metric)
    return ""


def _composer_caveats(reviewer_result: dict[str, Any], *, chinese: bool) -> list[str]:
    caveats = []
    if reviewer_result.get("unsupported_entities"):
        caveats.append(
            "已移除缺少证据支撑的对象表述。"
            if chinese
            else "Unsupported entity claims were removed."
        )
    if reviewer_result.get("unsupported_metrics"):
        caveats.append(
            "当前结果未包含部分决策指标，只能基于已返回指标判断。"
            if chinese
            else "Some decision metrics are not present in the returned result."
        )
    if not caveats:
        caveats.append(
            "当前结论只基于本次查询返回的数据。"
            if chinese
            else "This conclusion only uses the current query result."
        )
    return _dedupe(caveats)


def _normalize_answer(answer: dict[str, Any], *, chinese: bool) -> dict[str, Any]:
    normalized = empty_business_answer()
    normalized.update(
        {
            "headline": _clean_text(answer.get("headline"), chinese=chinese),
            "direct_answer": _clean_text(answer.get("direct_answer"), chinese=chinese),
            "why": _clean_text(answer.get("why"), chinese=chinese),
            "evidence_bullets": [
                _clean_text(item, chinese=chinese)
                for item in answer.get("evidence_bullets") or []
                if _clean_text(item, chinese=chinese)
            ],
            "recommendations": [
                _clean_text(item, chinese=chinese)
                for item in answer.get("recommendations") or []
                if _clean_text(item, chinese=chinese)
            ],
            "caveats": [
                _clean_text(item, chinese=chinese)
                for item in answer.get("caveats") or []
                if _clean_text(item, chinese=chinese)
            ],
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


def _clean_text(value: Any, *, chinese: bool) -> str:
    text = str(value or "").strip()
    text = re.sub(r"```sql\s*.*?```", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\b(?:SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|PRAGMA)\b.+", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\b(?:trace_id|trace_path|prompt_id|provider_metadata)\s*=\s*\S+", "", text, flags=re.IGNORECASE)
    for raw_key, label in sorted(business_field_labels(chinese=chinese).items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"\b{re.escape(raw_key)}\b", label, text, flags=re.IGNORECASE)
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
