from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from tools.trace_logger import append_trace


def _claim_texts(items: list[Any]) -> list[str]:
    claims = []
    for item in items:
        if isinstance(item, dict):
            claim = str(item.get("claim", "")).strip()
        else:
            claim = str(item).strip()
        if claim:
            claims.append(claim)
    return claims


def _evidence_inputs(state: dict[str, Any]) -> dict[str, list[str]]:
    evidence = state.get("evidence_result", {})
    return {
        "evidence_findings": _claim_texts(evidence.get("data_supported_findings", [])),
        "evidence_hypotheses": _claim_texts(evidence.get("hypotheses", [])),
        "blocked_unsupported_claims": _claim_texts(evidence.get("unsupported_claims_blocked", [])),
    }


def _fallback_result(
    state: dict[str, Any],
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    actions = list(state.get("action_plan", {}).get("actions", []))
    return {
        "success": bool(actions) and not provider_called,
        "source": "deterministic" if actions else "provider_unavailable",
        "provider_called": provider_called,
        "fallback_used": True,
        "actions": actions,
        "risk_flags": [],
        "provider_error": provider_error,
        "validation_error": validation_error,
    }


def _provider_result(state: dict[str, Any], provider: LLMProvider) -> dict[str, Any]:
    evidence_inputs = _evidence_inputs(state)
    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "action_drafter",
        {
            "user_question": state.get("user_question", ""),
            "existing_actions": state.get("action_plan", {}).get("actions", []),
            **evidence_inputs,
        },
    )
    if not rendered.get("success"):
        return _fallback_result(state, provider_called=True, provider_error=rendered.get("error", ""))

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "action_drafter_agent"},
    )
    schema_context = {
        "allowed_claims": [*evidence_inputs["evidence_findings"], *evidence_inputs["evidence_hypotheses"]],
        "blocked_unsupported_claims": evidence_inputs["blocked_unsupported_claims"],
    }
    last_provider_error = ""
    last_validation_error = ""
    response = {}
    for _attempt in range(2):
        response = run_validated_llm_request(provider, request, schema_context=schema_context)
        if response.get("success"):
            break
        if response.get("error_type") == "llm_schema_validation_error":
            last_validation_error = response.get("error", "")
            last_provider_error = ""
        else:
            last_provider_error = response.get("error", "")
            last_validation_error = ""
    if not response.get("success"):
        return _fallback_result(
            state,
            provider_called=True,
            provider_error=last_provider_error,
            validation_error=last_validation_error,
        )

    content = response.get("content", {})
    return {
        "success": True,
        "source": "provider",
        "provider_called": True,
        "fallback_used": False,
        "actions": content.get("actions", []),
        "risk_flags": content.get("risk_flags", []),
        "provider_error": "",
        "validation_error": "",
        "model": response.get("model", ""),
        "prompt_id": response.get("prompt_id", "action_drafter"),
        "prompt_version": response.get("prompt_version", ""),
        "usage": response.get("usage", {}),
        "latency_ms": response.get("latency_ms", 0),
    }


def run_action_drafter_agent(
    state: dict[str, Any],
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    result = _provider_result(state, provider) if provider else _fallback_result(state, provider_called=False)
    action_plan = {
        **state.get("action_plan", {}),
        "success": bool(result.get("actions")) and not result.get("validation_error") and not result.get("provider_error"),
        "source": result.get("source", state.get("action_plan", {}).get("source", "")),
        "provider_called": result.get("provider_called", False),
        "fallback_used": result.get("fallback_used", False),
        "provider_error": result.get("provider_error", ""),
        "validation_error": result.get("validation_error", ""),
        "actions": result.get("actions", state.get("action_plan", {}).get("actions", [])),
    }
    updated = {
        **state,
        "action_plan": action_plan,
        "action_draft_result": result,
        "status": "action_plan_created" if action_plan.get("success") else "action_plan_provider_unavailable",
    }
    return append_trace(
        updated,
        {
            "node": "action_drafter_agent",
            "tool_name": "provider_action_drafter" if provider else "",
            "tool_input_summary": state.get("user_question", ""),
            "tool_output_summary": f"{len(action_plan.get('actions', []))} drafted actions",
            "status": "success" if not result.get("validation_error") and not result.get("provider_error") else "error",
            "latency_ms": result.get("latency_ms", 0),
            "error_type": "action_draft_validation_error" if result.get("validation_error") else None,
            "error": result.get("validation_error") or result.get("provider_error") or None,
            "provider_called": bool(provider),
            "fallback_used": bool(result.get("fallback_used")),
        },
    )
