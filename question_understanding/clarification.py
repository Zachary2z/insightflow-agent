from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest, provider_error_fields, provider_failure, provider_metadata
from llm_ops.structured_output import run_validated_llm_request
from question_understanding.task_contract import build_clarification_questions


_BLOCKED_FIELDS = {"sql", "generated_sql", "matched_template", "confidence", "selected_tables"}


def _strip_forbidden_fields(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key not in _BLOCKED_FIELDS}


def _fallback_result(
    understanding: dict[str, Any],
    *,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    task = dict(understanding.get("analysis_task") or {})
    missing_slots = list(task.get("missing_slots") or understanding.get("missing_slots", []))
    clarification_questions = build_clarification_questions(missing_slots, task=task) or list(
        understanding.get("clarification_questions", [])
    )
    return {
        "success": True,
        "requires_clarification": understanding.get("strategy") == "clarify",
        "analysis_task": task,
        "missing_slots": missing_slots,
        "clarification_questions": clarification_questions,
        "risk_flags": list(understanding.get("risk_flags", [])),
        "reason": understanding.get("reason", ""),
        "source": "deterministic",
        "provider_called": provider_called,
        "fallback_used": provider_called,
        "provider_error": provider_error,
        "validation_error": validation_error,
    }


def _provider_result(content: dict[str, Any], provider_response: dict[str, Any]) -> dict[str, Any]:
    normalized = _strip_forbidden_fields(content)
    return {
        "success": True,
        **normalized,
        "source": "provider",
        "provider_called": True,
        "fallback_used": False,
        "provider_error": "",
        "validation_error": "",
        **provider_metadata(provider_response, default_prompt_id="clarification_router"),
    }


def clarify_with_provider(
    question: str,
    understanding: dict[str, Any],
    provider: LLMProvider | None = None,
    deterministic_fallback: bool = True,
) -> dict[str, Any]:
    if provider is None:
        return _fallback_result(understanding, provider_called=False)

    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "clarification_router",
        {
            "user_question": question,
            "missing_slots": understanding.get("missing_slots", []),
            "current_intent": understanding.get("intent", {}),
            "deterministic_questions": understanding.get("clarification_questions", []),
        },
    )
    if not rendered.get("success"):
        if deterministic_fallback:
            return _fallback_result(understanding, provider_called=False, provider_error=rendered.get("error", ""))
        return provider_failure(rendered.get("error", ""), provider_called=False)

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "clarification_router_agent"},
    )
    provider_response = run_validated_llm_request(provider, request)
    if provider_response.get("success"):
        return _provider_result(provider_response.get("content", {}), provider_response)

    error = provider_response.get("error", "")
    error_type = provider_response.get("error_type", "")
    if not deterministic_fallback:
        return provider_failure(error, provider_called=True, error_type=error_type)

    return _fallback_result(understanding, provider_called=True, **provider_error_fields(error, error_type))
