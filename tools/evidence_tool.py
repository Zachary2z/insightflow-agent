from __future__ import annotations

import re
from time import perf_counter
from typing import Any


MISSING_DATA_TERMS = {
    "ad_impressions": "ad_impressions",
    "ctr": "ctr",
    "conversion_rate": "conversion_rate",
    "inventory": "inventory",
    "stock": "inventory",
    "库存": "inventory",
}

HYPOTHESIS_MARKERS = ("可能", "假设", "需要", "进一步验证", "无法验证", "might", "may", "hypothesis")


def _normalize(text: Any) -> str:
    return str(text).lower().replace(" ", "")


def _trace_event(
    claim_count: int,
    supported_count: int,
    hypothesis_count: int,
    blocked_count: int,
    status: str,
    latency_ms: int,
    error: str | None = None,
) -> dict[str, Any]:
    summary = f"{supported_count} supported, {hypothesis_count} hypotheses, {blocked_count} blocked"
    event = {
        "tool_name": "validate_evidence",
        "tool_input_summary": f"{claim_count} claims",
        "tool_output_summary": summary,
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "evidence_validation_error"
        event["error"] = error
    return event


def _failure(started_at: float, claim_count: int, error: str) -> dict[str, Any]:
    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": False,
        "data_supported_findings": [],
        "hypotheses": [],
        "unsupported_claims_blocked": [],
        "unsupported_claim_rate": 0.0,
        "error": error,
        "trace_event": _trace_event(claim_count, 0, 0, 0, "error", latency_ms, error),
    }


def _clean_claims(claims: list[str] | None) -> list[str]:
    if not claims:
        return []
    return [str(claim).strip() for claim in claims if str(claim).strip()]


def _extract_numbers(text: str) -> list[float]:
    numbers = []
    for match in re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", "")):
        try:
            numbers.append(float(match))
        except ValueError:
            continue
    return numbers


def _format_row(columns: list[str], row: list[Any]) -> str:
    return ", ".join(f"{column}={value}" for column, value in zip(columns, row, strict=False))


def _row_supports_claim(claim: str, execution_result: dict[str, Any] | None) -> str | None:
    if not execution_result or not execution_result.get("success"):
        return None

    claim_numbers = _extract_numbers(claim)
    if not claim_numbers:
        return None

    columns = execution_result.get("columns", [])
    rows = execution_result.get("rows", [])
    normalized_claim = _normalize(claim)

    for row in rows:
        row_text = _format_row(columns, row)
        dimension_values = [
            str(value)
            for value in row
            if not isinstance(value, int | float) or isinstance(value, bool)
        ]
        has_dimension_match = any(
            _normalize(value) in normalized_claim
            for value in dimension_values
            if len(_normalize(value)) >= 2
        )
        row_numbers = [
            float(value)
            for value in row
            if isinstance(value, int | float) and not isinstance(value, bool)
        ]
        has_number_match = any(
            abs(claim_number - row_number) < 0.000001
            for claim_number in claim_numbers
            for row_number in row_numbers
        )
        if has_dimension_match and has_number_match:
            return f"SQL result row: {row_text}"

    return None


def _business_context_supports_claim(claim: str, business_context: dict[str, Any] | None) -> str | None:
    if not business_context:
        return None

    normalized_claim = _normalize(claim)
    for rule in business_context.get("matched_rules", []):
        title = str(rule.get("title") or rule.get("id") or "business_rule")
        content = _normalize(rule.get("content", ""))
        if "paid" in normalized_claim and "paid" in content:
            return f"Business rule: {title}"
        if "gmv" in normalized_claim and "gmv" in content:
            return f"Business rule: {title}"

    return None


def _needs_more_data(claim: str) -> list[str]:
    normalized_claim = _normalize(claim)
    needed = []
    for term, canonical in MISSING_DATA_TERMS.items():
        if _normalize(term) in normalized_claim and canonical not in needed:
            needed.append(canonical)
    return needed


def _is_hypothesis(claim: str) -> bool:
    normalized_claim = _normalize(claim)
    return any(_normalize(marker) in normalized_claim for marker in HYPOTHESIS_MARKERS)


def validate_evidence(
    claims: list[str] | None,
    execution_result: dict[str, Any] | None,
    business_context: dict[str, Any] | None = None,
    metric_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started_at = perf_counter()
    del metric_context

    cleaned_claims = _clean_claims(claims)
    if not cleaned_claims:
        return _failure(started_at, 0, "claims are required for evidence validation")

    data_supported_findings = []
    hypotheses = []
    unsupported_claims_blocked = []

    for claim in cleaned_claims:
        evidence = _row_supports_claim(claim, execution_result) or _business_context_supports_claim(claim, business_context)
        if evidence:
            data_supported_findings.append(
                {
                    "claim": claim,
                    "evidence": evidence,
                    "confidence": 0.95,
                }
            )
            continue

        if _is_hypothesis(claim):
            hypotheses.append(
                {
                    "claim": claim,
                    "reason": "Claim is framed as a hypothesis or references data not present in current evidence.",
                    "needs_more_data": _needs_more_data(claim),
                }
            )
            continue

        unsupported_claims_blocked.append(claim)

    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": True,
        "data_supported_findings": data_supported_findings,
        "hypotheses": hypotheses,
        "unsupported_claims_blocked": unsupported_claims_blocked,
        "unsupported_claim_rate": len(unsupported_claims_blocked) / len(cleaned_claims),
        "trace_event": _trace_event(
            len(cleaned_claims),
            len(data_supported_findings),
            len(hypotheses),
            len(unsupported_claims_blocked),
            "success",
            latency_ms,
        ),
    }
