from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from tools.trace_logger import append_trace


LLMProvider = Callable[[dict[str, Any]], dict[str, Any] | str]


def _section_templates() -> dict[str, dict[str, Any]]:
    from agents.report_supervisor import plan_business_review_sections

    return {
        section["section_id"]: section
        for section in plan_business_review_sections("")
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


def _fallback_plan(reason: str, provider_called: bool) -> dict[str, Any]:
    sections = list(_section_templates().values())
    return {
        "success": False if provider_called else True,
        "report_type": "weekly_business_report",
        "sections": [{"section_id": section["section_id"]} for section in sections],
        "fallback_used": True,
        "provider_called": provider_called,
        "requires_clarification": False,
        "clarification_questions": [],
        "error": reason,
    }


def _clarification_plan(payload: dict[str, Any], provider_called: bool) -> dict[str, Any]:
    questions = [
        str(question).strip()
        for question in payload.get("clarification_questions", [])
        if str(question).strip()
    ]
    return {
        "success": True,
        "report_type": "weekly_business_report",
        "sections": [],
        "fallback_used": False,
        "provider_called": provider_called,
        "requires_clarification": True,
        "clarification_questions": questions,
        "error": "",
    }


def _validated_provider_plan(payload: dict[str, Any], provider_called: bool) -> dict[str, Any]:
    if payload.get("requires_clarification"):
        return _clarification_plan(payload, provider_called)

    templates = _section_templates()
    sections = []
    seen = set()
    for section in payload.get("sections", []):
        section_id = str(section.get("section_id", "")).strip()
        if section_id in templates and section_id not in seen:
            sections.append({"section_id": section_id, "rationale": str(section.get("rationale", "")).strip()})
            seen.add(section_id)

    if not sections:
        return _fallback_plan("no allowed sections in provider response", provider_called)

    return {
        "success": True,
        "report_type": "weekly_business_report",
        "sections": sections,
        "fallback_used": False,
        "provider_called": provider_called,
        "requires_clarification": False,
        "clarification_questions": [],
        "error": "",
    }


def _sections_from_plan(report_plan: dict[str, Any]) -> list[dict[str, Any]]:
    templates = _section_templates()
    sections = []
    for item in report_plan.get("sections", []):
        section_id = item.get("section_id")
        if section_id in templates:
            sections.append(dict(templates[section_id]))
    return sections


def run_report_planner_agent(
    state: dict[str, Any],
    llm_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    templates = _section_templates()
    allowed_section_ids = list(templates)
    provider_called = llm_provider is not None

    if not llm_provider:
        report_plan = _fallback_plan("llm_provider is not configured", provider_called=False)
    else:
        prompt = _planner_prompt(state, allowed_section_ids)
        try:
            payload = _parse_provider_response(llm_provider(prompt))
            report_plan = _validated_provider_plan(payload, provider_called=True)
        except Exception as exc:
            report_plan = _fallback_plan(str(exc), provider_called=True)

    sections = [] if report_plan.get("requires_clarification") else _sections_from_plan(report_plan)
    updated = {
        **state,
        "report_plan": report_plan,
        "report_sections": sections,
    }
    if report_plan.get("requires_clarification"):
        updated["status"] = "report_plan_needs_clarification"

    return append_trace(
        updated,
        {
            "node": "report_planner_agent",
            "tool_name": "llm_report_planner" if provider_called else "",
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
        },
    )
