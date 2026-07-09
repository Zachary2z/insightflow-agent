from __future__ import annotations

from typing import Any

from tools.evidence_tool import validate_evidence
from tools.trace_logger import append_trace
from workspaces.analysis_contracts import AnalysisTask, AuditResult, QuestionEvidencePack
from workspaces.question_evidence_ledger import (
    ledger_supported_fact_texts,
    ledger_supports_claim,
)


def audit_question_evidence(
    *,
    question: str,
    task: AnalysisTask | dict[str, Any] | None,
    evidence_pack: QuestionEvidencePack | dict[str, Any] | None,
    candidate_claims: list[str] | None = None,
    evidence_result: dict[str, Any] | None = None,
    execution_result: dict[str, Any] | None = None,
    question_evidence_ledger: dict[str, Any] | None = None,
    business_context: dict[str, Any] | None = None,
    metric_context: dict[str, Any] | None = None,
) -> AuditResult:
    del question
    pack = _pack(evidence_pack, task=task)
    ledger = question_evidence_ledger if isinstance(question_evidence_ledger, dict) else {}
    execution = execution_result or _execution_from_pack(pack)
    claims = _clean_claims(candidate_claims)
    if ledger and (ledger.get("facts") or ledger.get("derived_metrics")):
        return _audit_with_ledger(claims=claims, ledger=ledger, pack=pack, evidence_result=evidence_result or {})
    validation = evidence_result or {}
    if claims and not validation:
        validation = _validate_claims(
            claims=claims,
            execution_result=execution,
            business_context=business_context,
            metric_context=metric_context,
        )

    supported = _unique(
        [
            *[
                str(item.get("claim") or "")
                for item in validation.get("data_supported_findings") or []
                if isinstance(item, dict)
            ],
            *_facts_from_pack(pack),
        ]
    )
    inferences = _unique(
        [
            str(item.get("claim") or item.get("reason") or "")
            for item in validation.get("hypotheses") or []
            if isinstance(item, dict)
        ]
    )
    unsupported_candidates = _unique([str(item) for item in validation.get("unsupported_claims_blocked") or []])
    pack_supported_claims = [claim for claim in unsupported_candidates if _pack_supports_claim(pack, claim)]
    unsupported = [claim for claim in unsupported_candidates if claim not in pack_supported_claims]
    supported = _unique([*supported, *pack_supported_claims])
    limits = _unique(
        [
            *pack.data_limits,
            *[str(item) for item in validation.get("data_limits") or []],
            *[str(item) for item in validation.get("warnings") or []],
        ]
    )
    return AuditResult(
        supported_facts=supported,
        reasonable_inferences=inferences,
        unsupported_claims=unsupported,
        data_limits=limits,
        confidence=_confidence(supported=supported, unsupported=unsupported, data_limits=limits),
    )


def run_evidence_auditor_agent(
    state: dict[str, Any],
) -> dict[str, Any]:
    typed_claims = _typed_claims(state)
    deterministic_groups = _deterministic_claim_groups(state)
    hard_facts = _typed_category_claims(typed_claims, {"hard_fact"}) or deterministic_groups["hard_fact"]
    inferences = _typed_category_claims(
        typed_claims,
        {"business_inference", "recommendation"},
    ) or deterministic_groups["business_inference"]
    data_limits = _typed_category_claims(typed_claims, {"data_limit"}) or deterministic_groups["data_limit"]
    evidence_result = state.get("evidence_result") if isinstance(state.get("evidence_result"), dict) else None
    audit = audit_question_evidence(
        question=str(state.get("user_question") or state.get("original_question") or ""),
        task=state.get("analysis_task_contract") or state.get("analysis_task"),
        evidence_pack=state.get("question_evidence_pack"),
        candidate_claims=hard_facts,
        evidence_result=evidence_result,
        execution_result=state.get("execution_result") if isinstance(state.get("execution_result"), dict) else None,
        question_evidence_ledger=state.get("question_evidence_ledger") if isinstance(state.get("question_evidence_ledger"), dict) else None,
        business_context=state.get("business_context") if isinstance(state.get("business_context"), dict) else None,
        metric_context=state.get("metric_context") if isinstance(state.get("metric_context"), dict) else None,
    )
    if inferences:
        audit.reasonable_inferences = _unique([*audit.reasonable_inferences, *inferences])
    if data_limits:
        audit.data_limits = _unique([*audit.data_limits, *data_limits])
        audit.confidence = _confidence(
            supported=audit.supported_facts,
            unsupported=audit.unsupported_claims,
            data_limits=audit.data_limits,
        )
    updated = {
        **state,
        "audit_result": audit.to_dict(),
    }
    return append_trace(
        updated,
        {
            "node": "evidence_auditor_agent",
            "tool_name": "validate_evidence",
            "tool_input_summary": f"{len(hard_facts)} hard-fact claims",
            "tool_output_summary": (
                f"{len(audit.supported_facts)} supported facts, "
                f"{len(audit.reasonable_inferences)} inferences, "
                f"{len(audit.unsupported_claims)} unsupported"
            ),
            "status": "success" if audit.confidence != "low" or audit.supported_facts else "error",
            "latency_ms": 0,
            "provider_called": False,
            "fallback_used": False,
        },
    )


def _audit_with_ledger(
    *,
    claims: list[str],
    ledger: dict[str, Any],
    pack: QuestionEvidencePack,
    evidence_result: dict[str, Any],
) -> AuditResult:
    ledger_facts = ledger_supported_fact_texts(ledger)
    supported_claims = [claim for claim in claims if ledger_supports_claim(ledger, claim)]
    unsupported = [
        claim
        for claim in claims
        if claim not in supported_claims and (_numbers(claim) or _looks_like_rank_or_named_fact(claim))
    ]
    inferences = _unique(
        [
            str(item.get("claim") or item.get("reason") or "")
            for item in evidence_result.get("hypotheses") or []
            if isinstance(item, dict)
        ]
    )
    limits = _unique(
        [
            *[str(item) for item in ledger.get("data_limits") or []],
            *pack.data_limits,
            *[str(item) for item in evidence_result.get("data_limits") or []],
            *[str(item) for item in evidence_result.get("warnings") or []],
        ]
    )
    supported = _unique([*ledger_facts, *supported_claims])
    return AuditResult(
        supported_facts=supported,
        reasonable_inferences=inferences,
        unsupported_claims=unsupported,
        data_limits=limits,
        confidence=_confidence(supported=supported, unsupported=unsupported, data_limits=limits),
    )


def _validate_claims(
    *,
    claims: list[str],
    execution_result: dict[str, Any],
    business_context: dict[str, Any] | None,
    metric_context: dict[str, Any] | None,
) -> dict[str, Any]:
    return validate_evidence(
        claims=claims,
        execution_result=execution_result,
        business_context=business_context,
        metric_context=metric_context,
    )


def _candidate_claims(state: dict[str, Any]) -> list[str]:
    explicit = _clean_claims(state.get("claims_to_validate"))
    if explicit:
        return explicit
    answer = state.get("business_answer") if isinstance(state.get("business_answer"), dict) else {}
    claims = [
        str(answer.get("headline") or ""),
        str(answer.get("direct_answer") or ""),
        str(answer.get("why") or ""),
        *[str(item) for item in answer.get("evidence_bullets") or []],
        *[str(item) for item in answer.get("recommendations") or []],
        *[str(item) for item in answer.get("caveats") or []],
    ]
    return _clean_claims(claims)


def _deterministic_claim_groups(state: dict[str, Any]) -> dict[str, list[str]]:
    answer = state.get("business_answer") if isinstance(state.get("business_answer"), dict) else {}
    if not answer:
        explicit = _candidate_claims(state)
        return {"hard_fact": explicit, "business_inference": [], "data_limit": []}
    hard_facts = _clean_claims(answer.get("evidence_bullets"))
    inferences = _clean_claims(
        [
            str(answer.get("headline") or ""),
            str(answer.get("direct_answer") or ""),
            str(answer.get("why") or ""),
            *[str(item) for item in answer.get("recommendations") or []],
        ]
    )
    data_limits = _data_limit_claims_from_caveats(answer.get("caveats"))
    if not hard_facts:
        hard_facts = _clean_claims(state.get("claims_to_validate")) or _claims_with_numbers(inferences)
        inferences = [claim for claim in inferences if claim not in hard_facts]
    return {
        "hard_fact": hard_facts,
        "business_inference": inferences,
        "data_limit": data_limits,
    }


def _typed_claims(state: dict[str, Any]) -> list[dict[str, str]]:
    value = state.get("candidate_claims_typed")
    if not isinstance(value, list):
        return []
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim") or "").strip()
        category = str(item.get("category") or item.get("claim_type") or "").strip()
        if claim and category:
            normalized.append({"claim": claim, "category": category})
    return normalized


def _typed_category_claims(typed_claims: list[dict[str, str]], categories: set[str]) -> list[str]:
    return _unique(
        [
            item["claim"]
            for item in typed_claims
            if item.get("category") in categories and item.get("claim")
        ]
    )


def _pack(
    value: QuestionEvidencePack | dict[str, Any] | None,
    *,
    task: AnalysisTask | dict[str, Any] | None,
) -> QuestionEvidencePack:
    if isinstance(value, QuestionEvidencePack):
        return value
    if isinstance(value, dict) and value:
        return QuestionEvidencePack.from_dict(value)
    return QuestionEvidencePack(task=_task(task))


def _task(value: AnalysisTask | dict[str, Any] | None) -> AnalysisTask:
    if isinstance(value, AnalysisTask):
        return value
    if isinstance(value, dict):
        return AnalysisTask.from_dict(value)
    return AnalysisTask(resolved_question="")


def _execution_from_pack(pack: QuestionEvidencePack) -> dict[str, Any]:
    rows = []
    for row in pack.rows:
        rows.append([row.get(column) for column in pack.columns])
    return {
        "success": bool(pack.rows),
        "columns": list(pack.columns),
        "rows": rows,
        "row_count": len(rows),
    }


def _facts_from_pack(pack: QuestionEvidencePack, *, limit: int = 5) -> list[str]:
    facts: list[str] = []
    for row in pack.rows[:limit]:
        pairs = [
            f"{column} 为 {row.get(column)}"
            for column in pack.columns
            if row.get(column) is not None and str(row.get(column)).strip()
        ]
        if pairs:
            facts.append("，".join(pairs) + "。")
    return facts


def _pack_supports_claim(pack: QuestionEvidencePack, claim: str) -> bool:
    claim_numbers = _numbers(claim)
    if not claim_numbers:
        return False
    row_numbers = [
        number
        for row in pack.rows
        for value in row.values()
        for number in _numbers(value)
    ]
    if not row_numbers:
        return False
    if not all(any(abs(claim_number - row_number) < 0.000001 for row_number in row_numbers) for claim_number in claim_numbers):
        return False
    normalized_claim = _normalize_text(claim)
    dimension_values = [
        _normalize_text(value)
        for row in pack.rows
        for value in row.values()
        if not _numbers(value) and len(_normalize_text(value)) >= 2
    ]
    mentioned_dimensions = [value for value in dimension_values if value and value in normalized_claim]
    unknown_dimension_markers = _unknown_dimension_markers(normalized_claim, dimension_values, pack.columns)
    if unknown_dimension_markers:
        return False
    return bool(mentioned_dimensions) or not dimension_values


def _numbers(value: Any) -> list[float]:
    import re

    numbers = []
    for match in re.findall(r"-?\d+(?:\.\d+)?", str(value).replace(",", "")):
        try:
            numbers.append(float(match))
        except ValueError:
            continue
    return numbers


def _claims_with_numbers(values: list[str]) -> list[str]:
    return [value for value in values if _numbers(value)]


def _data_limit_claims_from_caveats(value: Any) -> list[str]:
    return [claim for claim in _clean_claims(value) if _looks_like_data_limit_claim(claim)]


def _looks_like_rank_or_named_fact(claim: str) -> bool:
    normalized = _normalize_text(claim)
    markers = (
        "最高",
        "最低",
        "第一",
        "第1",
        "领先",
        "排名",
        "top",
        "highest",
        "lowest",
        "rank",
        "leads",
        "leader",
    )
    return any(_normalize_text(marker) in normalized for marker in markers)


def _looks_like_data_limit_claim(claim: str) -> bool:
    normalized = _normalize_text(claim)
    markers = (
        "缺少",
        "缺失",
        "未提供",
        "没有提供",
        "无法验证",
        "证据不足",
        "证据不充分",
        "数据不足",
        "数据缺口",
        "缺乏数据",
        "缺乏证据",
        "未覆盖",
        "不能覆盖",
        "不支持",
        "未支持",
        "无法支持",
        "未计算",
        "missing",
        "not provided",
        "unavailable",
        "not available",
        "insufficient evidence",
        "insufficient data",
        "limited evidence",
        "limited data",
        "unsupported",
        "not supported",
        "cannot verify",
        "can't verify",
        "not covered",
        "not calculated",
        "data gap",
        "evidence gap",
    )
    return any(_normalize_text(marker) in normalized for marker in markers)


def _normalize_text(value: Any) -> str:
    import re

    return re.sub(r"[\s,，.。:：;；!！?？()（）_-]+", "", str(value or "").lower())


def _unknown_dimension_markers(normalized_claim: str, dimension_values: list[str], columns: list[str]) -> list[str]:
    import re

    column_tokens = {_normalize_text(column) for column in columns}
    known_values = {value for value in dimension_values if value}
    markers: list[str] = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_]{1,}", normalized_claim):
        normalized = _normalize_text(token)
        if normalized in column_tokens or normalized in known_values:
            continue
        if any(normalized in value or value in normalized for value in known_values):
            continue
        markers.append(normalized)
    return markers


def _confidence(*, supported: list[str], unsupported: list[str], data_limits: list[str]) -> str:
    if unsupported:
        return "low" if not supported else "medium"
    if supported and not data_limits:
        return "high"
    if supported:
        return "medium"
    return "low"


def _clean_claims(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = ["audit_question_evidence", "run_evidence_auditor_agent"]
