from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
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


def _candidate_policy() -> dict[str, Any]:
    return {
        "provider_prompt_id": "guarded_sql_candidate",
        "must_validate_sql_before_execution": True,
        "fallback_strategy": "deterministic_sql_generator",
    }


def _provider_result(content: dict[str, Any], understanding: dict[str, Any], provider_response: dict[str, Any]) -> dict[str, Any]:
    deterministic = plan_sql_strategy(understanding)
    strategy = content.get("strategy", deterministic.get("strategy", ""))
    matched_template = content.get("matched_template", "") if strategy == "template" else ""
    result = {
        **deterministic,
        "strategy": strategy,
        "matched_template": matched_template,
        "confidence": content.get("confidence", 0.0),
        "risk_flags": content.get("risk_flags", deterministic.get("risk_flags", [])),
        "reason": content.get("reason", deterministic.get("reason", "")),
        "source": "provider",
        "provider_called": True,
        "fallback_used": False,
        "provider_error": "",
        "validation_error": "",
        "model": provider_response.get("model", ""),
        "prompt_id": provider_response.get("prompt_id", "sql_planning_router"),
        "prompt_version": provider_response.get("prompt_version", ""),
        "usage": provider_response.get("usage", {}),
        "latency_ms": provider_response.get("latency_ms", 0),
    }
    if strategy == "llm_candidate":
        result["candidate_policy"] = _candidate_policy()
    if strategy in {"clarify", "reject"}:
        result["missing_slots"] = content.get("missing_slots", deterministic.get("missing_slots", []))
        result["clarification_questions"] = content.get(
            "clarification_questions",
            deterministic.get("clarification_questions", []),
        )
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
        metadata={"node": "sql_planning_router_agent"},
    )
    provider_response = run_validated_llm_request(provider, request)
    if provider_response.get("success"):
        return _provider_result(provider_response.get("content", {}), question_understanding, provider_response)

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
        return _fallback_result(question_understanding, provider_called=True, validation_error=error)
    return _fallback_result(question_understanding, provider_called=True, provider_error=error)
