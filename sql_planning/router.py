from __future__ import annotations

from typing import Any


TEMPLATE_MATCHES = {
    ("gmv", "product", "top_n"): ("top_products_gmv", 0.94, "Stable Top-N product GMV template matched."),
    ("gmv", "category", "top_n"): ("top_categories_gmv", 0.94, "Stable Top-N category GMV template matched."),
    ("gmv", "city", "summary"): ("city_gmv_summary", 0.9, "Stable city GMV summary template matched."),
    ("order_count", "city", "summary"): ("city_order_count_summary", 0.86, "Stable city order-count summary template matched."),
}


def _base_result(understanding: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": True,
        "strategy": understanding.get("strategy", ""),
        "matched_template": "",
        "confidence": 0.0,
        "template_variables": {},
        "missing_slots": list(understanding.get("missing_slots", [])),
        "clarification_questions": list(understanding.get("clarification_questions", [])),
        "risk_flags": list(understanding.get("risk_flags", [])),
        "rejection_reason": understanding.get("rejection_reason", ""),
        "reason": understanding.get("reason", ""),
        "intent": dict(understanding.get("intent", {})),
        "validation_policy": {"must_validate_sql_before_execution": True},
    }


def _template_variables(intent: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric": intent.get("metric", ""),
        "dimension": intent.get("dimension", ""),
        "operation": intent.get("operation", ""),
        "limit": intent.get("limit"),
        "time_range": intent.get("time_range", {}),
        "filters": list(intent.get("filters", [])),
    }


def _template_match(intent: dict[str, Any]) -> tuple[str, float, str] | None:
    key = (intent.get("metric", ""), intent.get("dimension", ""), intent.get("operation", ""))
    return TEMPLATE_MATCHES.get(key)


def plan_sql_strategy(question_understanding: dict[str, Any]) -> dict[str, Any]:
    result = _base_result(question_understanding)
    strategy = question_understanding.get("strategy", "")

    if strategy in {"clarify", "reject"}:
        return result

    intent = dict(question_understanding.get("intent", {}))
    match = _template_match(intent)
    if strategy == "template" and match:
        template_id, confidence, reason = match
        result.update(
            {
                "strategy": "template",
                "matched_template": template_id,
                "confidence": confidence,
                "template_variables": _template_variables(intent),
                "reason": reason,
            }
        )
        return result

    result.update(
        {
            "strategy": "llm_candidate",
            "matched_template": "",
            "confidence": 0.62,
            "candidate_policy": {
                "provider_prompt_id": "guarded_sql_candidate",
                "must_validate_sql_before_execution": True,
                "fallback_strategy": "clarify_or_deterministic_baseline",
            },
            "reason": "Complete intent is not covered by a deterministic SQL template.",
        }
    )
    return result
