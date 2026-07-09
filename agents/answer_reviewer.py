from __future__ import annotations

import re
from typing import Any

from llm_ops.structured_output import validate_prompt_output
from workspaces.answer_evidence import (
    contains_cjk,
    entity_key,
    entity_values,
    metric_keys,
    rows_as_dicts,
    to_number,
)


REVIEW_KEYS = {
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

_DECISION_MARKERS = (
    "建议",
    "优先",
    "最值得",
    "应该",
    "投入",
    "加预算",
    "prioritize",
    "recommend",
    "should",
    "best",
    "winner",
)
_TRADEOFF_MARKERS = ("取舍", "权衡", "口径", "如果目标", "tradeoff", "decision basis", "depends on")
_ASCII_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "because",
    "best",
    "by",
    "current",
    "evidence",
    "for",
    "is",
    "it",
    "next",
    "option",
    "prioritize",
    "recommend",
    "resource",
    "strongest",
    "the",
    "this",
    "use",
    "using",
    "validator",
    "which",
    "wins",
}
_KNOWN_METRIC_ACRONYMS = {
    "AOV",
    "CAC",
    "CPA",
    "CPC",
    "CPM",
    "CTR",
    "CVR",
    "GMV",
    "ROI",
    "ROAS",
}
_METRIC_ALIASES = {
    "roi": {"roas", "return_on_ad_spend", "net_return"},
    "roas": {"roi", "return_on_ad_spend"},
}


def review_answer(
    *,
    user_question: str,
    execution_result: dict[str, Any],
    evidence_result: dict[str, Any] | None = None,
    draft_business_answer: dict[str, Any],
    profile_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del profile_context
    return _deterministic_review(
        user_question=user_question,
        execution_result=execution_result,
        evidence_result=evidence_result or {},
        draft_business_answer=draft_business_answer,
    )


def _deterministic_review(
    *,
    user_question: str,
    execution_result: dict[str, Any],
    evidence_result: dict[str, Any],
    draft_business_answer: dict[str, Any],
) -> dict[str, Any]:
    rows = rows_as_dicts(execution_result)
    language = "zh" if contains_cjk(user_question) or contains_cjk(_answer_text(draft_business_answer)) else "en"
    supported_entities = entity_values(rows)
    supported_metrics = metric_keys(rows, execution_result)
    execution_columns = [str(column) for column in execution_result.get("columns") or [] if str(column).strip()]
    answer_text = _answer_text(draft_business_answer)

    issues: list[dict[str, Any]] = []
    instructions: list[str] = []
    unsupported_entities = _unsupported_entity_mentions(answer_text, supported_entities, supported_metrics)
    unsupported_metrics = _unsupported_metric_mentions(
        answer_text,
        [*supported_metrics, *execution_columns],
        supported_entities,
    )

    if _weak_evidence(execution_result, evidence_result):
        issues.append(
            {
                "type": "insufficient_evidence",
                "message": "Execution/evidence rows are missing or not sufficient to support a final business answer.",
                "affected_fields": ["headline", "direct_answer", "why", "recommendations"],
            }
        )
        instructions.append("Downgrade the final answer and explain that evidence is insufficient.")

    if unsupported_entities:
        issues.append(
            {
                "type": "entity_mismatch",
                "message": "The draft names entities that are absent from the execution/evidence rows.",
                "affected_fields": _affected_fields_for_values(draft_business_answer, unsupported_entities),
            }
        )
        instructions.append("Remove unsupported entities or label them as unverified hypotheses.")

    if unsupported_metrics:
        issues.append(
            {
                "type": "metric_mismatch",
                "message": "The draft uses metrics that are absent from the execution/evidence rows.",
                "affected_fields": _affected_fields_for_values(draft_business_answer, unsupported_metrics),
            }
        )
        instructions.append("Remove unsupported metrics and ground the answer in returned metrics.")

    if _has_missing_tradeoff(user_question=user_question, answer_text=answer_text, rows=rows):
        issues.append(
            {
                "type": "tradeoff_missing",
                "message": "Multiple returned metrics point to different leaders, but the draft forces one conclusion.",
                "affected_fields": ["headline", "direct_answer", "recommendations"],
            }
        )
        instructions.append("State the metric tradeoff and decision basis before naming a single priority.")

    if _weak_evidence(execution_result, evidence_result):
        status = "downgrade_to_insufficient_evidence"
        confidence = "low"
    elif issues:
        status = "revise"
        confidence = "medium"
    else:
        status = "accept"
        confidence = "high"

    review = {
        "status": status,
        "language": language,
        "supported_entities": supported_entities,
        "unsupported_entities": unsupported_entities,
        "supported_metrics": supported_metrics,
        "unsupported_metrics": unsupported_metrics,
        "issues": issues,
        "revision_instructions": list(dict.fromkeys(instructions)),
        "confidence": confidence,
    }
    validation = validate_prompt_output("answer_reviewer", review)
    if validation.get("success"):
        return validation["content"]
    return _empty_review(language=language)


def _empty_review(*, language: str) -> dict[str, Any]:
    return {
        "status": "downgrade_to_insufficient_evidence",
        "language": language if language in {"zh", "en"} else "en",
        "supported_entities": [],
        "unsupported_entities": [],
        "supported_metrics": [],
        "unsupported_metrics": [],
        "issues": [
            {
                "type": "insufficient_evidence",
                "message": "Answer review could not validate the draft against evidence.",
                "affected_fields": ["direct_answer"],
            }
        ],
        "revision_instructions": ["Downgrade to an evidence-insufficient answer."],
        "confidence": "low",
    }


def _unsupported_entity_mentions(text: str, supported_entities: list[str], supported_metrics: list[str]) -> list[str]:
    supported = set(supported_entities)
    supported_entity_parts = {
        part
        for entity in supported_entities
        for part in re.findall(r"\b[A-Za-z][A-Za-z0-9_-]*\b", entity)
    }
    supported_metric_labels = {metric.lower() for metric in supported_metrics}
    candidates = []
    for token in re.findall(r"\b[A-Z][A-Za-z0-9_-]{1,40}\b", text):
        if _is_supported_metric_token(token, supported_metric_labels):
            continue
        if (
            token in supported
            or token in supported_entity_parts
            or token.lower() in supported_metric_labels
            or token.lower() in _ASCII_STOPWORDS
        ):
            continue
        if token not in candidates:
            candidates.append(token)
    return candidates


def _is_supported_metric_token(token: str, supported_metric_labels: set[str]) -> bool:
    normalized = str(token or "").strip()
    if not normalized:
        return False
    upper = normalized.upper()
    lower = normalized.lower()
    if upper in _KNOWN_METRIC_ACRONYMS:
        return True
    if lower in supported_metric_labels:
        return True
    return bool(_METRIC_ALIASES.get(lower, set()) & supported_metric_labels)


def _unsupported_metric_mentions(text: str, supported_metrics: list[str], supported_entities: list[str]) -> list[str]:
    supported = set(supported_metrics)
    entities = set(supported_entities)
    candidates = []
    for token in re.findall(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", text):
        if token in supported or token in entities:
            continue
        if token not in candidates:
            candidates.append(token)
    return candidates


def _has_missing_tradeoff(*, user_question: str, answer_text: str, rows: list[dict[str, Any]]) -> bool:
    if len(rows) < 2:
        return False
    if _has_tradeoff_language(answer_text):
        return False
    if not (_has_decision_language(user_question) or _has_decision_language(answer_text)):
        return False
    entity_key_value = entity_key(rows)
    if not entity_key_value:
        return False
    metrics = [key for key in metric_keys(rows, {"columns": []}) if key != entity_key_value]
    if len(metrics) < 2:
        return False
    leaders = {
        leader
        for metric in metrics
        for leader in [_metric_leader(rows, entity_key_value=entity_key_value, metric=metric)]
        if leader
    }
    return len(leaders) > 1


def _metric_leader(rows: list[dict[str, Any]], *, entity_key_value: str, metric: str) -> str:
    candidates: list[tuple[str, float]] = []
    for row in rows:
        entity = str(row.get(entity_key_value) or "").strip()
        value = to_number(row.get(metric))
        if entity and value is not None:
            candidates.append((entity, value))
    if not candidates:
        return ""
    return max(candidates, key=lambda item: item[1])[0]


def _affected_fields_for_values(answer: dict[str, Any], values: list[str]) -> list[str]:
    affected = []
    for field in ("headline", "direct_answer", "why"):
        if any(value in str(answer.get(field) or "") for value in values):
            affected.append(field)
    for field in ("evidence_bullets", "recommendations", "caveats"):
        if any(value in " ".join(str(item) for item in answer.get(field) or []) for value in values):
            affected.append(field)
    return affected or ["direct_answer"]


def _answer_text(answer: dict[str, Any]) -> str:
    return " ".join(
        [
            str(answer.get("headline") or ""),
            str(answer.get("direct_answer") or ""),
            str(answer.get("why") or ""),
            *[str(item) for item in answer.get("evidence_bullets") or []],
            *[str(item) for item in answer.get("recommendations") or []],
            *[str(item) for item in answer.get("caveats") or []],
        ]
    )


def _has_decision_language(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in _DECISION_MARKERS)


def _has_tradeoff_language(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in _TRADEOFF_MARKERS)


def _weak_evidence(execution_result: dict[str, Any], evidence_result: dict[str, Any]) -> bool:
    if not execution_result or execution_result.get("success") is False:
        return True
    if not execution_result.get("rows"):
        return True
    validation_status = str(evidence_result.get("validation_status") or evidence_result.get("status") or "").lower()
    return validation_status in {"failed", "not_validated", "rejected"} and not evidence_result.get(
        "data_supported_findings"
    )
