from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import (
    LLMProvider,
    LLMRequest,
    provider_error_fields,
    provider_failure,
    provider_metadata,
)
from llm_ops.structured_output import run_validated_llm_request
from question_understanding.router import understand_question
from question_understanding.task_contract import (
    build_clarification_questions,
    canonical_dimension_id,
    canonical_metric_id,
    normalize_analysis_task,
    strategy_for_task,
)


_BLOCKED_FIELDS = {"sql", "generated_sql", "matched_template", "confidence", "selected_tables"}
_UNSAFE_TERMS = ("删除", "更新", "写入", "插入", "drop", "delete", "update", "insert")
_SENSITIVE_TERMS = ("手机号", "电话", "邮箱", "email", "phone", "地址", "身份证", "payment")
_BULK_TERMS = ("导出所有", "全部用户", "所有用户", "批量导出")
_SAFETY_RISK_FLAGS = {"unsafe_operation", "sensitive_field", "bulk_export", "external_action"}
_OPERATION_ALIASES = {
    "最高": "top_n",
    "最多": "top_n",
    "排名": "top_n",
    "top": "top_n",
    "top n": "top_n",
    "ranking": "top_n",
    "rank": "top_n",
    "top_n": "top_n",
    "趋势": "trend",
    "走势": "trend",
    "trend": "trend",
    "下降": "decline",
    "下滑": "decline",
    "decline": "decline",
    "对比": "comparison",
    "比较": "comparison",
    "预算": "comparison",
    "预算建议": "comparison",
    "加预算": "comparison",
    "建议": "comparison",
    "推荐": "comparison",
    "roi": "comparison",
    "roas": "comparison",
    "comparison": "comparison",
    "明细": "drilldown",
    "详情": "drilldown",
    "drilldown": "drilldown",
    "总结": "summary",
    "概览": "summary",
    "summary": "summary",
    "unsafe_write": "unsafe_write",
}


def _strip_forbidden_fields(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key not in _BLOCKED_FIELDS}


def _normalize_slot(value: Any, aliases: dict[str, str]) -> str:
    text = str(value or "").strip()
    return aliases.get(text.lower(), aliases.get(text, text))


def _safety_risk_flags(risk_flags: list[Any]) -> list[str]:
    return [str(flag) for flag in risk_flags if str(flag) in _SAFETY_RISK_FLAGS]


def _normalize_provider_content(
    content: dict[str, Any],
    *,
    question: str,
    workspace_context: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = dict(content)
    intent = dict(normalized.get("intent", {}))
    intent["metric"] = canonical_metric_id(str(intent.get("metric") or "").strip())
    intent["dimension"] = canonical_dimension_id(str(intent.get("dimension") or "").strip())
    intent["operation"] = _normalize_slot(intent.get("operation"), _OPERATION_ALIASES)
    if "risk_flags" not in intent or intent.get("risk_flags") is None:
        intent["risk_flags"] = []
    normalized["intent"] = intent
    provider_task = normalized.get("analysis_task") if isinstance(normalized.get("analysis_task"), dict) else {}
    task = normalize_analysis_task(
        question,
        intent=intent,
        workspace_context=workspace_context,
        provider_task=provider_task,
    )
    risk_flags = list(normalized.get("risk_flags") or intent.get("risk_flags") or [])
    normalized["analysis_task"] = task
    normalized["missing_slots"] = list(task.get("missing_slots", []))
    normalized["clarification_questions"] = build_clarification_questions(normalized["missing_slots"], task=task)
    normalized["strategy"] = strategy_for_task(task, risk_flags=_safety_risk_flags(risk_flags))
    normalized["risk_flags"] = risk_flags
    return normalized


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    normalized = text.lower().replace(" ", "")
    return any(term.lower().replace(" ", "") in normalized for term in terms)


def _safety_guard_result(question: str) -> dict[str, Any] | None:
    risk_flags = []
    if _contains(question, _UNSAFE_TERMS):
        risk_flags.append("unsafe_operation")
    if _contains(question, _SENSITIVE_TERMS):
        risk_flags.append("sensitive_field")
    if _contains(question, _BULK_TERMS):
        risk_flags.append("bulk_export")
    if not risk_flags:
        return None
    intent = {
        "metric": "",
        "dimension": "",
        "time_range": None,
        "filters": [],
        "operation": "unsafe_write" if "unsafe_operation" in risk_flags else "",
        "limit": None,
        "risk_flags": risk_flags,
    }
    return {
        "success": True,
        "strategy": "reject",
        "intent": intent,
        "missing_slots": [],
        "clarification_questions": [],
        "risk_flags": risk_flags,
        "rejection_reason": "Request asks for sensitive fields or unsafe data access.",
        "reason": "Safety guard rejected the request before provider question understanding.",
        "source": "safety_guard",
        "provider_called": False,
        "fallback_used": False,
        "provider_error": "",
        "validation_error": "",
    }


def _fallback_result(
    question: str,
    *,
    provider_called: bool,
    workspace_context: dict[str, Any] | None = None,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    fallback = _strip_forbidden_fields(understand_question(question, workspace_context=workspace_context))
    return {
        **fallback,
        "source": "deterministic",
        "provider_called": provider_called,
        "fallback_used": provider_called,
        "provider_error": provider_error,
        "validation_error": validation_error,
    }


def _provider_unavailable_result(
    *,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    return {
        "success": True,
        "strategy": "clarify",
        "intent": {
            "metric": "",
            "dimension": "",
            "time_range": None,
            "filters": [],
            "operation": "",
            "limit": None,
            "risk_flags": [],
        },
        "missing_slots": ["provider_output"],
        "clarification_questions": ["Provider question understanding is unavailable; please retry with a configured provider."],
        "risk_flags": [],
        "rejection_reason": "",
        "reason": "Provider question understanding failed; deterministic business keyword routing was not used.",
        "source": "provider_unavailable",
        "provider_called": provider_called,
        "fallback_used": provider_called,
        "provider_error": provider_error,
        "validation_error": validation_error,
    }


def _provider_result(
    content: dict[str, Any],
    provider_response: dict[str, Any],
    *,
    question: str,
    workspace_context: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = _strip_forbidden_fields(
        _normalize_provider_content(content, question=question, workspace_context=workspace_context)
    )
    risk_flags = normalized.get("risk_flags", [])
    if _safety_risk_flags(risk_flags):
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
        **provider_metadata(provider_response, default_prompt_id="question_understanding"),
    }


def understand_question_with_provider(
    question: str,
    provider: LLMProvider | None = None,
    deterministic_fallback: bool = True,
    workspace_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safety_result = _safety_guard_result(question)
    if safety_result is not None:
        return safety_result

    if provider is None:
        return _fallback_result(question, provider_called=False, workspace_context=workspace_context)

    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "question_understanding",
        {
            "user_question": question,
            "workspace_context": workspace_context or {},
        },
    )
    if not rendered.get("success"):
        if deterministic_fallback:
            return _fallback_result(
                question,
                provider_called=False,
                workspace_context=workspace_context,
                provider_error=rendered.get("error", ""),
            )
        return provider_failure(rendered.get("error", ""), provider_called=False)

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "question_understanding_agent"},
    )
    provider_response = run_validated_llm_request(provider, request)
    if provider_response.get("success"):
        return _provider_result(
            provider_response.get("content", {}),
            provider_response,
            question=question,
            workspace_context=workspace_context,
        )

    error = provider_response.get("error", "")
    error_type = provider_response.get("error_type", "")
    if not deterministic_fallback:
        return provider_failure(error, provider_called=True, error_type=error_type)

    return _provider_unavailable_result(provider_called=True, **provider_error_fields(error, error_type))
