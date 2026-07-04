from __future__ import annotations

from typing import Any

from agents.insight_claim_typer import run_insight_claim_typer_agent
from llm_ops.provider import LLMProvider
from tools.evidence_tool import validate_evidence
from tools.trace_logger import append_trace
from workspaces.analysis_contracts import AnalysisTask, AuditResult, QuestionEvidencePack


def audit_question_evidence(
    *,
    question: str,
    task: AnalysisTask | dict[str, Any] | None,
    evidence_pack: QuestionEvidencePack | dict[str, Any] | None,
    candidate_claims: list[str] | None = None,
    evidence_result: dict[str, Any] | None = None,
    execution_result: dict[str, Any] | None = None,
    business_context: dict[str, Any] | None = None,
    metric_context: dict[str, Any] | None = None,
    provider: LLMProvider | None = None,
) -> AuditResult:
    del question
    pack = _pack(evidence_pack, task=task)
    execution = execution_result or _execution_from_pack(pack)
    claims = _clean_claims(candidate_claims)
    validation = evidence_result or {}
    if claims and not validation:
        validation, _claim_typing_result = _validate_claims(
            state={},
            claims=claims,
            execution_result=execution,
            business_context=business_context,
            metric_context=metric_context,
            provider=provider,
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
    *,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    claims = _candidate_claims(state)
    claim_typing_result: dict[str, Any] = {}
    evidence_result = state.get("evidence_result") if isinstance(state.get("evidence_result"), dict) else None
    if provider and claims and not evidence_result:
        state = run_insight_claim_typer_agent(
            {
                **state,
                "claims_to_validate": claims,
                "execution_result": state.get("execution_result") if isinstance(state.get("execution_result"), dict) else {},
                "business_context": state.get("business_context") if isinstance(state.get("business_context"), dict) else {},
                "metric_context": state.get("metric_context") if isinstance(state.get("metric_context"), dict) else {},
            },
            provider=provider,
        )
        evidence_result = dict(state.get("evidence_result") or {})
        claim_typing_result = dict(state.get("claim_typing_result") or {})
    audit = audit_question_evidence(
        question=str(state.get("user_question") or state.get("original_question") or ""),
        task=state.get("analysis_task_contract") or state.get("analysis_task"),
        evidence_pack=state.get("question_evidence_pack"),
        candidate_claims=claims,
        evidence_result=evidence_result,
        execution_result=state.get("execution_result") if isinstance(state.get("execution_result"), dict) else None,
        business_context=state.get("business_context") if isinstance(state.get("business_context"), dict) else None,
        metric_context=state.get("metric_context") if isinstance(state.get("metric_context"), dict) else None,
        provider=provider,
    )
    updated = {
        **state,
        "audit_result": audit.to_dict(),
    }
    if claim_typing_result:
        updated["claim_typing_result"] = claim_typing_result
    return append_trace(
        updated,
        {
            "node": "evidence_auditor_agent",
            "tool_name": "provider_insight_claim_typer" if provider and claims else "validate_evidence",
            "tool_input_summary": f"{len(claims)} candidate claims",
            "tool_output_summary": (
                f"{len(audit.supported_facts)} supported facts, "
                f"{len(audit.reasonable_inferences)} inferences, "
                f"{len(audit.unsupported_claims)} unsupported"
            ),
            "status": "success" if audit.confidence != "low" or audit.supported_facts else "error",
            "latency_ms": 0,
            "provider_called": bool(provider and claims),
            "fallback_used": False,
        },
    )


def _validate_claims(
    *,
    state: dict[str, Any],
    claims: list[str],
    execution_result: dict[str, Any],
    business_context: dict[str, Any] | None,
    metric_context: dict[str, Any] | None,
    provider: LLMProvider | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if provider is None:
        return (
            validate_evidence(
                claims=claims,
                execution_result=execution_result,
                business_context=business_context,
                metric_context=metric_context,
            ),
            {},
        )
    typed = run_insight_claim_typer_agent(
        {
            **state,
            "claims_to_validate": claims,
            "execution_result": execution_result,
            "business_context": business_context or {},
            "metric_context": metric_context or {},
        },
        provider=provider,
    )
    return dict(typed.get("evidence_result") or {}), dict(typed.get("claim_typing_result") or {})


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
    return all(any(abs(claim_number - row_number) < 0.000001 for row_number in row_numbers) for claim_number in claim_numbers)


def _numbers(value: Any) -> list[float]:
    import re

    numbers = []
    for match in re.findall(r"-?\d+(?:\.\d+)?", str(value).replace(",", "")):
        try:
            numbers.append(float(match))
        except ValueError:
            continue
    return numbers


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
