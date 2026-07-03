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
    if response.get("success") and isinstance(content, dict):
        return _polish_answer(
            content,
            user_question=user_question,
            execution_result=execution_result,
            reviewer_result=reviewer_result,
        )
    return {}


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
        if _can_rebuild_supported_answer_from_rows(
            execution_result=execution_result,
            reviewer_result=reviewer_result,
        ):
            return _evidence_based_answer(
                user_question=user_question,
                execution_result=execution_result,
                reviewer_result={**reviewer_result, "status": "revise", "confidence": "medium"},
                chinese=chinese,
            )
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


def _can_rebuild_supported_answer_from_rows(
    *,
    execution_result: dict[str, Any],
    reviewer_result: dict[str, Any],
) -> bool:
    if reviewer_result.get("unsupported_entities") or reviewer_result.get("unsupported_metrics"):
        return False
    rows = rows_as_dicts(execution_result)
    if len(rows) < 2:
        return False
    return bool(entity_key(rows) and metric_keys(rows))


def _validate_or_rebuild(answer: dict[str, Any], *, user_question: str, execution_result: dict[str, Any]) -> dict[str, Any]:
    validation = validate_prompt_output(
        "final_answer_composer",
        answer,
        schema_context={"user_question": user_question, "execution_result": execution_result},
    )
    if validation.get("success"):
        return _polish_answer(
            validation["content"],
            user_question=user_question,
            execution_result=execution_result,
            reviewer_result={},
        )
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
        wants_recommendations = _should_include_recommendations(user_question)
        metric_labels = _metric_labels(metric_key_values, chinese=True)
        metric_text = "、".join(metric_labels) if metric_labels else "可用指标"
        why_text = (
            f"当前证据显示，{entity_text} 在本次返回的{metric_text}中表现靠前。"
            "如果要解释背后的业务原因，可以把它作为合理假设：可能与触达效率、需求规模、客户信任或运营承接有关，"
            "但这些原因仍需要转化率、复购、成本或更细分过程数据进一步验证。"
            if _asks_why(user_question)
            else f"当前数据中，{entity_text} 的结果靠前：{first_row_summary}。"
        )
        recommendations = (
            _composer_recommendations(
                entity_text,
                user_question=user_question,
                execution_result=execution_result,
                chinese=True,
            )
            if wants_recommendations
            else []
        )
        direct_answer = (
            f"在当前证据下，建议优先关注 {entity_text}；它在本次返回的{metric_text}中表现靠前。"
            if wants_recommendations
            else f"本轮结果显示 {entity_text} 排在第一，因为它在本次查询返回的{metric_text}中表现靠前。"
        )
        headline = (
            f"当前证据支持优先关注 {entity_text}"
            if wants_recommendations
            else f"当前证据显示 {entity_text} 排名靠前"
        )
        answer = {
            "headline": headline,
            "direct_answer": direct_answer,
            "why": why_text,
            "evidence_bullets": evidence_bullets,
            "recommendations": recommendations,
            "caveats": _composer_caveats(
                reviewer_result,
                user_question=user_question,
                execution_result=execution_result,
                chinese=True,
            ),
            "confidence": confidence,
        }
    else:
        entity_text = primary or "the first returned entity"
        answer = {
            "headline": f"The current evidence supports focusing on {entity_text}",
            "direct_answer": (
                f"Focus on {entity_text} for now because the returned evidence ranks it first on the available metrics."
            ),
            "why": f"The current data puts {entity_text} ahead on the returned metrics: {first_row_summary}.",
            "evidence_bullets": evidence_bullets,
            "recommendations": [f"Use {entity_text} as the next review focus and keep tracking the returned metrics."],
            "caveats": _composer_caveats(
                reviewer_result,
                user_question=user_question,
                execution_result=execution_result,
                chinese=False,
            ),
            "confidence": confidence,
        }
    return _validate_or_empty(answer, user_question=user_question)


def _should_include_recommendations(user_question: str) -> bool:
    text = str(user_question or "").lower()
    if any(marker in text for marker in ("只回答事实", "不用建议", "不需要建议", "不要建议", "只看事实")):
        return False
    return any(
        marker in text
        for marker in (
            "建议",
            "推荐",
            "应该",
            "该",
            "值得",
            "优先",
            "加预算",
            "减少预算",
            "优化",
            "关注",
            "下一步",
            "action",
            "recommend",
            "should",
            "prioritize",
            "budget",
        )
    )


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
            "why": "当前返回数据不足以支撑原草稿里的关键对象、指标或判断，因此需要补充同口径证据后再下结论。",
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


def _composer_caveats(
    reviewer_result: dict[str, Any],
    *,
    user_question: str = "",
    execution_result: dict[str, Any] | None = None,
    chinese: bool,
) -> list[str]:
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
    caveats.extend(_missing_data_caveats(user_question, execution_result or {}, chinese=chinese))
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


def _polish_answer(
    answer: dict[str, Any],
    *,
    user_question: str,
    execution_result: dict[str, Any],
    reviewer_result: dict[str, Any],
) -> dict[str, Any]:
    chinese = _needs_chinese_response(user_question) or str(reviewer_result.get("language") or "") == "zh"
    polished = _normalize_answer(answer, chinese=chinese)
    caveats = polished["caveats"] + _missing_data_caveats(user_question, execution_result, chinese=chinese)
    if not caveats:
        caveats = _composer_caveats(
            reviewer_result,
            user_question=user_question,
            execution_result=execution_result,
            chinese=chinese,
        )
    polished["caveats"] = _dedupe(caveats)
    polished["recommendations"] = _remove_repeated_recommendations(
        polished["direct_answer"],
        polished["recommendations"],
    )
    return polished


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
    text = _remove_template_debug_phrases(text, chinese=chinese)
    for raw_key, label in sorted(business_field_labels(chinese=chinese).items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"\b{re.escape(raw_key)}\b", label, text, flags=re.IGNORECASE)
    return " ".join(text.split())


def _remove_template_debug_phrases(text: str, *, chinese: bool) -> str:
    cleaned = str(text or "")
    if chinese:
        cleaned = cleaned.replace("证据表" + "第一行显示：", "当前数据中，")
        cleaned = cleaned.replace("执行结果第一行显示：", "当前数据中，")
        cleaned = cleaned.replace("本轮排序" + "证据中，", "")
        cleaned = re.sub(r"基于\s*" + r"execution_result[。；;,.，]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace("execution_result", "本次返回数据")
    else:
        cleaned = cleaned.replace("The first evidence row shows:", "The current data shows:")
        cleaned = cleaned.replace("The first result row shows:", "The current data shows:")
        cleaned = re.sub(r"based on\s*execution_result[.;, ]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace("execution_result", "returned data")
    return cleaned.strip()


def _metric_labels(metrics: list[str], *, chinese: bool) -> list[str]:
    labels = []
    for metric in metrics:
        label = business_field_label(metric, chinese=chinese)
        if label and label not in labels:
            labels.append(label)
    return labels


def _asks_why(question: str) -> bool:
    lowered = str(question or "").lower()
    return any(marker in lowered for marker in ("为什么", "原因", "why", "because"))


def _composer_recommendations(
    entity: str,
    *,
    user_question: str,
    execution_result: dict[str, Any],
    chinese: bool,
) -> list[str]:
    missing = _missing_data_caveats(user_question, execution_result, chinese=chinese)
    lowered = str(user_question or "").lower()
    if chinese:
        if any(marker in lowered for marker in ("预算", "投放", "加码")):
            if missing:
                return [
                    f"短期不建议只凭当前收入结果直接大幅加预算；如要继续加码 {entity}，先补充成本、转化率、复购或 ROI 数据后再判断投入效率。"
                ]
            return [f"可以把 {entity} 作为预算复盘对象，并继续监控同口径收入、成本和转化表现。"]
        return [f"建议将 {entity} 作为优先复盘对象，并继续用同口径数据跟踪后续变化。"]
    if missing:
        return [f"Treat {entity} as the review focus, but add cost, conversion, repeat-purchase, or ROI data before scaling budget."]
    return [f"Use {entity} as the next review focus and keep tracking the returned metrics."]


def _missing_data_caveats(
    user_question: str,
    execution_result: dict[str, Any],
    *,
    chinese: bool,
) -> list[str]:
    question = str(user_question or "").lower()
    columns = {str(column).lower() for column in execution_result.get("columns") or []}
    joined_columns = " ".join(columns)
    caveats: list[str] = []
    asks_roi = "roi" in question or "roas" in question or "投产" in question or "回报" in question
    has_cost = any(marker in joined_columns for marker in ("cost", "spend", "花费", "成本", "投放"))
    if asks_roi and not has_cost:
        caveats.append(
            "当前证据没有成本或投放花费数据，因此不能直接判断 ROI 或投放效率是否领先。"
            if chinese
            else "The returned evidence does not include cost or spend, so ROI or efficiency leadership cannot be concluded."
        )
    asks_conversion = any(marker in question for marker in ("转化率", "conversion", "复购", "repeat"))
    has_conversion = any(marker in joined_columns for marker in ("conversion", "repeat", "retention", "转化", "复购"))
    if asks_conversion and not has_conversion:
        caveats.append(
            "当前证据没有转化率、复购或留存数据，相关原因判断只能作为假设，需要进一步验证。"
            if chinese
            else "The returned evidence does not include conversion, repeat-purchase, or retention data, so causal interpretation is a hypothesis."
        )
    return _dedupe(caveats)


def _remove_repeated_recommendations(direct_answer: str, recommendations: list[str]) -> list[str]:
    direct = " ".join(str(direct_answer or "").split())
    kept: list[str] = []
    for item in recommendations:
        text = " ".join(str(item or "").split())
        if not text or text == direct:
            continue
        if text not in kept:
            kept.append(text)
    return kept


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
