from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from tools.trace_logger import append_trace


LegacyCallableProvider = Callable[[dict[str, Any]], dict[str, Any] | str]


def _section_templates(user_question: str = "") -> dict[str, dict[str, Any]]:
    from agents.report_supervisor import plan_business_review_sections

    return {
        section["section_id"]: section
        for section in plan_business_review_sections(user_question)
    }


def _planner_prompt(state: dict[str, Any], allowed_section_ids: list[str]) -> dict[str, Any]:
    return {
        "task": "controlled_report_planning",
        "user_question": state.get("user_question", ""),
        "report_type": "weekly_business_report",
        "allowed_section_ids": allowed_section_ids,
        "output_schema": {
            "report_type": "weekly_business_report",
            "sections": [{"section_id": "one allowed id", "rationale": "short reason"}],
            "requires_clarification": False,
            "clarification_questions": [],
        },
        "must_not_generate_sql": True,
        "must_not_execute_sql": True,
        "must_not_generate_final_claims": True,
        "constraints": [
            "must_not_generate_sql",
            "must_not_execute_sql",
            "must_not_generate_final_claims",
            "must_only_select_allowed_section_ids",
        ],
    }


def _parse_provider_response(response: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(response, str):
        return json.loads(response)
    if isinstance(response, dict):
        return response
    raise ValueError("provider response must be a dict or JSON string")


def _provider_unavailable_plan(
    reason: str,
    provider_called: bool,
    user_question: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    templates = _section_templates(user_question)
    report_type = next(iter(templates.values())).get("report_type", "weekly_business_report") if templates else "weekly_business_report"
    return {
        "success": False,
        "report_type": report_type,
        "sections": [],
        "fallback_used": True,
        "provider_called": provider_called,
        "source": "provider_unavailable",
        "requires_clarification": False,
        "clarification_questions": [],
        "error": reason,
        "provider_error": reason if provider_called else "",
        "validation_error": validation_error,
    }


def _clarification_plan(payload: dict[str, Any], provider_called: bool) -> dict[str, Any]:
    questions = [
        str(question).strip()
        for question in payload.get("clarification_questions", [])
        if str(question).strip()
    ]
    return {
        "success": True,
        "report_type": str(payload.get("report_type") or "weekly_business_report"),
        "sections": [],
        "fallback_used": False,
        "provider_called": provider_called,
        "source": "provider" if provider_called else "deterministic",
        "requires_clarification": True,
        "clarification_questions": questions,
        "error": "",
        "provider_error": "",
        "validation_error": "",
    }


def _validated_provider_plan(payload: dict[str, Any], provider_called: bool, user_question: str = "") -> dict[str, Any]:
    if payload.get("requires_clarification"):
        return _clarification_plan(payload, provider_called)

    templates = _section_templates(user_question)
    sections = []
    seen = set()
    for section in payload.get("sections", []):
        section_id = str(section.get("section_id", "")).strip()
        if section_id in templates and section_id not in seen:
            sections.append({"section_id": section_id, "rationale": str(section.get("rationale", "")).strip()})
            seen.add(section_id)

    if not sections:
        return _provider_unavailable_plan(
            "no allowed sections in provider response",
            provider_called,
            user_question=user_question,
            validation_error="no allowed sections in provider response",
        )

    return {
        "success": True,
        "report_type": str(payload.get("report_type") or next(iter(templates.values())).get("report_type", "weekly_business_report")),
        "sections": sections,
        "fallback_used": False,
        "provider_called": provider_called,
        "source": "provider" if provider_called else "deterministic",
        "requires_clarification": False,
        "clarification_questions": [],
        "error": "",
        "provider_error": "",
        "validation_error": "",
    }


def _sections_from_plan(report_plan: dict[str, Any], user_question: str = "") -> list[dict[str, Any]]:
    templates = _section_templates(user_question)
    sections = []
    for item in report_plan.get("sections", []):
        section_id = item.get("section_id")
        if section_id in templates:
            sections.append(dict(templates[section_id]))
    return sections


def _promptops_provider_plan(
    state: dict[str, Any],
    provider: LLMProvider,
    allowed_section_ids: list[str],
) -> dict[str, Any]:
    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "report_planner",
        {
            "user_question": state.get("user_question", ""),
            "allowed_section_ids": allowed_section_ids,
        },
    )
    if not rendered.get("success"):
        return _provider_unavailable_plan(
            rendered.get("error", ""),
            provider_called=True,
            user_question=state.get("user_question", ""),
        )

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "report_planner_agent"},
    )
    response = run_validated_llm_request(
        provider,
        request,
        schema_context={
            "allowed_section_ids": allowed_section_ids,
            "report_type": _provider_unavailable_plan("", provider_called=False, user_question=state.get("user_question", "")).get("report_type"),
        },
    )
    if response.get("success"):
        plan = _validated_provider_plan(response.get("content", {}), provider_called=True, user_question=state.get("user_question", ""))
        plan.update(
            {
                "model": response.get("model", ""),
                "prompt_id": response.get("prompt_id", "report_planner"),
                "prompt_version": response.get("prompt_version", ""),
                "usage": response.get("usage", {}),
                "latency_ms": response.get("latency_ms", 0),
            }
        )
        return plan

    fallback = _provider_unavailable_plan(response.get("error", ""), provider_called=True, user_question=state.get("user_question", ""))
    if response.get("error_type") == "llm_schema_validation_error":
        fallback["validation_error"] = response.get("error", "")
        fallback["provider_error"] = ""
    return fallback


def run_report_planner_agent(
    state: dict[str, Any],
    llm_provider: LLMProvider | LegacyCallableProvider | None = None,
) -> dict[str, Any]:
    question = state.get("user_question", "")
    templates = _section_templates(question)
    allowed_section_ids = list(templates)
    provider_called = llm_provider is not None

    if not llm_provider:
        report_plan = _provider_unavailable_plan("llm_provider is not configured", provider_called=False, user_question=question)
    elif hasattr(llm_provider, "generate"):
        report_plan = _promptops_provider_plan(state, llm_provider, allowed_section_ids)
    else:
        prompt = _planner_prompt(state, allowed_section_ids)
        try:
            payload = _parse_provider_response(llm_provider(prompt))
            report_plan = _validated_provider_plan(payload, provider_called=True, user_question=question)
        except Exception as exc:
            report_plan = _provider_unavailable_plan(str(exc), provider_called=True, user_question=question)

    sections = [] if report_plan.get("requires_clarification") or not report_plan.get("success") else _sections_from_plan(report_plan, question)
    updated = {
        **state,
        "report_plan": report_plan,
        "report_sections": sections,
    }
    if report_plan.get("requires_clarification"):
        updated["status"] = "report_plan_needs_clarification"
    elif not report_plan.get("success"):
        updated["status"] = "report_plan_provider_unavailable"

    return append_trace(
        updated,
        {
            "node": "report_planner_agent",
            "tool_name": "provider_business_review_planner" if provider_called else "",
            "tool_input_summary": state.get("user_question", ""),
            "tool_output_summary": (
                "requires clarification"
                if report_plan.get("requires_clarification")
                else f"planned {len(sections)} sections fallback={report_plan.get('fallback_used')}"
            ),
            "status": "success" if report_plan.get("success") else "error",
            "latency_ms": 0,
            "error_type": "report_plan_validation_error" if report_plan.get("error") and provider_called else None,
            "error": report_plan.get("error") or None,
            "provider_called": provider_called,
            "fallback_used": bool(report_plan.get("fallback_used")),
        },
    )
