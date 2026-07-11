from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest, provider_error_fields, provider_failure, provider_metadata
from llm_ops.structured_output import run_validated_llm_request
from sql_planning.router import plan_sql_strategy


_BLOCKED_FIELDS = {"sql", "generated_sql", "sql_candidates", "candidate_sql", "selected_tables"}


def _fallback_result(
    understanding: dict[str, Any],
    *,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    deterministic = plan_sql_strategy(understanding)
    return {
        **deterministic,
        "source": "deterministic",
        "provider_called": provider_called,
        "fallback_used": provider_called,
        "provider_error": provider_error,
        "validation_error": validation_error,
    }


def _provider_unavailable_result(
    understanding: dict[str, Any],
    *,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    return {
        "success": True,
        "strategy": "clarify",
        "matched_template": "",
        "confidence": 0.0,
        "template_variables": {},
        "missing_slots": ["sql_planning_provider"],
        "clarification_questions": ["Provider SQL planning is unavailable; please retry with a configured provider."],
        "risk_flags": list(understanding.get("risk_flags", [])),
        "rejection_reason": "",
        "reason": "Provider SQL planning failed; deterministic template routing was not used.",
        "intent": dict(understanding.get("intent", {})),
        "validation_policy": {"must_validate_sql_before_execution": True},
        "source": "provider_unavailable",
        "provider_called": provider_called,
        "fallback_used": provider_called,
        "provider_error": provider_error,
        "validation_error": validation_error,
    }


def _candidate_policy() -> dict[str, Any]:
    return {
        "provider_prompt_id": "guarded_sql_candidate",
        "must_validate_sql_before_execution": True,
        "fallback_strategy": "deterministic_sql_generator",
    }


def _provider_result(content: dict[str, Any], understanding: dict[str, Any], provider_response: dict[str, Any]) -> dict[str, Any]:
    intent = dict(understanding.get("intent", {}))
    strategy = content.get("strategy", understanding.get("strategy", ""))
    matched_template = content.get("matched_template", "") if strategy == "template" else ""
    result = {
        "success": True,
        "strategy": strategy,
        "matched_template": matched_template,
        "confidence": content.get("confidence", 0.0),
        "template_variables": {
            "metric": intent.get("metric", ""),
            "dimension": intent.get("dimension", ""),
            "operation": intent.get("operation", ""),
            "limit": intent.get("limit"),
            "time_range": intent.get("time_range", {}),
            "filters": list(intent.get("filters", [])),
        }
        if strategy == "template"
        else {},
        "missing_slots": list(content.get("missing_slots", understanding.get("missing_slots", []))),
        "clarification_questions": list(
            content.get("clarification_questions", understanding.get("clarification_questions", []))
        ),
        "risk_flags": content.get("risk_flags", understanding.get("risk_flags", [])),
        "rejection_reason": understanding.get("rejection_reason", ""),
        "reason": content.get("reason", understanding.get("reason", "")),
        "intent": intent,
        "validation_policy": {"must_validate_sql_before_execution": True},
        "source": "provider",
        "provider_called": True,
        "fallback_used": False,
        "provider_error": "",
        "validation_error": "",
        **provider_metadata(provider_response, default_prompt_id="sql_planning_router"),
    }
    if strategy == "llm_candidate":
        result["candidate_policy"] = _candidate_policy()
    return {key: value for key, value in result.items() if key not in _BLOCKED_FIELDS}


def plan_sql_strategy_with_provider(
    question_understanding: dict[str, Any],
    provider: LLMProvider | None = None,
    deterministic_fallback: bool = True,
) -> dict[str, Any]:
    if provider is None:
        return _fallback_result(question_understanding, provider_called=False)

    deterministic_plan = plan_sql_strategy(question_understanding)
    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "sql_planning_router",
        {
            "user_question": question_understanding.get("question", ""),
            "question_understanding": question_understanding,
            "deterministic_plan": deterministic_plan,
        },
    )
    if not rendered.get("success"):
        if deterministic_fallback:
            return _fallback_result(
                question_understanding,
                provider_called=False,
                provider_error=rendered.get("error", ""),
            )
        return provider_failure(rendered.get("error", ""), provider_called=False)

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "sql_planning_router_agent"},
    )
    provider_response = run_validated_llm_request(provider, request)
    if provider_response.get("success"):
        provider_plan = _provider_result(provider_response.get("content", {}), question_understanding, provider_response)
        if (
            provider_plan.get("strategy") == "clarify"
            and deterministic_plan.get("strategy") != "clarify"
            and not question_understanding.get("missing_slots")
        ):
            return {
                **deterministic_plan,
                "source": "provider_normalized",
                "provider_called": True,
                "fallback_used": True,
                "provider_error": "",
                "validation_error": "",
                "reason": "Provider requested clarification, but normalized analysis task is complete; using deterministic SQL planning.",
            }
        return provider_plan

    error = provider_response.get("error", "")
    error_type = provider_response.get("error_type", "")
    if not deterministic_fallback:
        return provider_failure(error, provider_called=True, error_type=error_type)

    return _provider_unavailable_result(
        question_understanding,
        provider_called=True,
        **provider_error_fields(error, error_type),
    )
