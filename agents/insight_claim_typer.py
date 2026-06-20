from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from tools.evidence_tool import validate_evidence
from tools.trace_logger import append_trace


def _candidate_claims(state: dict[str, Any]) -> list[str]:
    explicit = [str(claim).strip() for claim in state.get("claims_to_validate", []) if str(claim).strip()]
    if explicit:
        return explicit

    final_answer = str(state.get("final_answer", "")).strip()
    if not final_answer:
        return []

    claims = []
    for line in final_answer.splitlines():
        line = line.strip()
        if not line or line.startswith("基于 execution_result"):
            continue
        claims.append(line.lstrip("0123456789. "))
    return claims or [final_answer]


def _summary_from_evidence(evidence_result: dict[str, Any]) -> str:
    lines = []
    for item in evidence_result.get("data_supported_findings", []):
        lines.append(f"- {item.get('claim', '')}")
    for item in evidence_result.get("hypotheses", []):
        lines.append(f"- {item.get('claim', '')}")
    return "\n".join(lines)


def _fallback_result(
    state: dict[str, Any],
    claims: list[str],
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    evidence_result = validate_evidence(
        claims=claims,
        execution_result=state.get("execution_result"),
        business_context=state.get("business_context"),
        metric_context=state.get("metric_context"),
    )
    return {
        "success": evidence_result.get("success", False) and not provider_called,
        "source": "deterministic",
        "provider_called": provider_called,
        "fallback_used": True,
        "typed_claims": [
            {"claim": claim, "claim_type": "data_supported_finding", "rationale": "Deterministic fallback before Evidence Validator."}
            for claim in claims
        ],
        "risk_flags": [],
        "evidence_result": evidence_result,
        "guarded_summary": _summary_from_evidence(evidence_result),
        "provider_error": provider_error,
        "validation_error": validation_error,
    }


def _provider_result(state: dict[str, Any], provider: LLMProvider, claims: list[str]) -> dict[str, Any]:
    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "insight_claim_typer",
        {
            "user_question": state.get("user_question", ""),
            "candidate_claims": claims,
            "execution_result": state.get("execution_result", {}),
            "business_context": state.get("business_context", {}),
            "metric_context": state.get("metric_context", {}),
        },
    )
    if not rendered.get("success"):
        return _fallback_result(state, claims, provider_called=True, provider_error=rendered.get("error", ""))

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "insight_claim_typer_agent"},
    )
    response = run_validated_llm_request(provider, request)
    if not response.get("success"):
        if response.get("error_type") == "llm_schema_validation_error":
            return _fallback_result(state, claims, provider_called=True, validation_error=response.get("error", ""))
        return _fallback_result(state, claims, provider_called=True, provider_error=response.get("error", ""))

    content = response.get("content", {})
    typed_claims = content.get("typed_claims", [])
    evidence_claims = [item["claim"] for item in typed_claims]
    evidence_result = validate_evidence(
        claims=evidence_claims,
        execution_result=state.get("execution_result"),
        business_context=state.get("business_context"),
        metric_context=state.get("metric_context"),
    )
    return {
        "success": evidence_result.get("success", False),
        "source": "provider",
        "provider_called": True,
        "fallback_used": False,
        "typed_claims": typed_claims,
        "risk_flags": content.get("risk_flags", []),
        "evidence_result": evidence_result,
        "guarded_summary": _summary_from_evidence(evidence_result),
        "provider_error": "",
        "validation_error": "",
        "model": response.get("model", ""),
        "prompt_id": response.get("prompt_id", "insight_claim_typer"),
        "prompt_version": response.get("prompt_version", ""),
        "usage": response.get("usage", {}),
        "latency_ms": response.get("latency_ms", 0),
    }


def run_insight_claim_typer_agent(
    state: dict[str, Any],
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    claims = _candidate_claims(state)
    provider_called = provider is not None
    result = _provider_result(state, provider, claims) if provider else _fallback_result(
        state,
        claims,
        provider_called=False,
    )
    updated = {
        **state,
        "claim_typing_result": result,
        "evidence_result": result.get("evidence_result", {}),
    }
    return append_trace(
        updated,
        {
            "node": "insight_claim_typer_agent",
            "tool_name": "provider_insight_claim_typer" if provider_called else "",
            "tool_input_summary": f"{len(claims)} candidate claims",
            "tool_output_summary": (
                f"{len(result.get('evidence_result', {}).get('data_supported_findings', []))} supported, "
                f"{len(result.get('evidence_result', {}).get('hypotheses', []))} hypotheses, "
                f"{len(result.get('evidence_result', {}).get('unsupported_claims_blocked', []))} blocked"
            ),
            "status": "success" if result.get("success") else "error",
            "latency_ms": result.get("latency_ms", 0),
            "error_type": "claim_typing_error" if not result.get("success") else None,
            "error": result.get("validation_error") or result.get("provider_error") or None,
            "provider_called": provider_called,
            "fallback_used": bool(result.get("fallback_used")),
        },
    )
