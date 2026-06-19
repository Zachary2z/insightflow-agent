from __future__ import annotations

import re
from typing import Any

from tools.evidence_tool import validate_evidence
from tools.trace_logger import append_trace


def _claims_from_final_answer(final_answer: str) -> list[str]:
    claims = []
    for line in final_answer.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^\d+[\.\)]\s*(.+)$", stripped)
        if match:
            claims.append(match.group(1).strip())
    return claims


def _claims_to_validate(state: dict[str, Any]) -> list[str]:
    explicit_claims = state.get("claims_to_validate")
    if explicit_claims is not None:
        return [str(claim).strip() for claim in explicit_claims if str(claim).strip()]
    return _claims_from_final_answer(state.get("final_answer", ""))


def run_evidence_validator_agent(state: dict[str, Any]) -> dict[str, Any]:
    result = validate_evidence(
        claims=_claims_to_validate(state),
        execution_result=state.get("execution_result"),
        business_context=state.get("business_context"),
        metric_context=state.get("metric_context"),
    )
    updated = {
        **state,
        "evidence_result": result,
    }
    if not result.get("success"):
        updated["evidence_warning"] = result.get("error", "")

    trace_event = dict(result.get("trace_event", {}))
    trace_event["node"] = "evidence_validator_agent"
    return append_trace(updated, trace_event)
