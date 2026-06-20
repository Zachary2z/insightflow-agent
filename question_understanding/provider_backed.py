from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from question_understanding.router import understand_question


_BLOCKED_FIELDS = {"sql", "generated_sql", "matched_template", "confidence", "selected_tables"}


def _strip_forbidden_fields(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key not in _BLOCKED_FIELDS}


def _fallback_result(
    question: str,
    *,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    fallback = _strip_forbidden_fields(understand_question(question))
    return {
        **fallback,
        "source": "deterministic",
        "provider_called": provider_called,
        "fallback_used": provider_called,
        "provider_error": provider_error,
        "validation_error": validation_error,
    }


def _provider_result(content: dict[str, Any], provider_response: dict[str, Any]) -> dict[str, Any]:
    normalized = _strip_forbidden_fields(content)
    risk_flags = normalized.get("risk_flags", [])
    if risk_flags:
        normalized["strategy"] = "reject"
        normalized["rejection_reason"] = "Request asks for sensitive fields or unsafe data access."
    else:
        normalized["rejection_reason"] = ""

    return {
        "success": True,
        **normalized,
        "source": "provider",
        "provider_called": True,
        "fallback_used": False,
        "provider_error": "",
        "validation_error": "",
        "model": provider_response.get("model", ""),
        "prompt_id": provider_response.get("prompt_id", "question_understanding"),
        "prompt_version": provider_response.get("prompt_version", ""),
        "usage": provider_response.get("usage", {}),
        "latency_ms": provider_response.get("latency_ms", 0),
    }


def understand_question_with_provider(
    question: str,
    provider: LLMProvider | None = None,
    deterministic_fallback: bool = True,
) -> dict[str, Any]:
    if provider is None:
        return _fallback_result(question, provider_called=False)

    rendered = DEFAULT_PROMPT_REGISTRY.render("question_understanding", {"user_question": question})
    if not rendered.get("success"):
        if deterministic_fallback:
            return _fallback_result(question, provider_called=False, provider_error=rendered.get("error", ""))
        return {
            "success": False,
            "source": "provider",
            "provider_called": False,
            "fallback_used": False,
            "provider_error": rendered.get("error", ""),
            "validation_error": "",
            "error": rendered.get("error", ""),
        }

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "question_understanding_agent"},
    )
    provider_response = run_validated_llm_request(provider, request)
    if provider_response.get("success"):
        return _provider_result(provider_response.get("content", {}), provider_response)

    error = provider_response.get("error", "")
    error_type = provider_response.get("error_type", "")
    if not deterministic_fallback:
        return {
            "success": False,
            "source": "provider",
            "provider_called": True,
            "fallback_used": False,
            "provider_error": error,
            "validation_error": error if error_type == "llm_schema_validation_error" else "",
            "error": error,
            "error_type": error_type,
        }

    if error_type == "llm_schema_validation_error":
        return _fallback_result(question, provider_called=True, validation_error=error)
    return _fallback_result(question, provider_called=True, provider_error=error)
