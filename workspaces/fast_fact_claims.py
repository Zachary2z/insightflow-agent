from __future__ import annotations

from typing import Any

from workspaces.answer_evidence import business_field_label, is_number, rows_as_dicts


def build_fast_fact_claims(
    *,
    analysis_task: dict[str, Any] | None,
    execution_result: dict[str, Any],
    fact_payload: dict[str, Any] | None = None,
) -> list[str]:
    rows = rows_as_dicts(execution_result)
    if not rows:
        return []
    task_type = str((analysis_task or {}).get("task_type") or (fact_payload or {}).get("task_type") or "")
    if task_type == "trend":
        return [_claim_from_row(row) for row in rows[:3] if _claim_from_row(row)]
    return [_claim_from_row(rows[0])] if _claim_from_row(rows[0]) else []


def _claim_from_row(row: dict[str, Any]) -> str:
    entity = _first_entity(row)
    metric_key = _first_metric_key(row)
    if not metric_key:
        return ""
    metric = business_field_label(metric_key, chinese=True)
    value = row.get(metric_key)
    if entity:
        return f"{entity} {metric}为 {value}"
    return f"{metric}为 {value}"


def _first_metric_key(row: dict[str, Any]) -> str:
    for key, value in row.items():
        if is_number(value):
            return key
    return ""


def _first_entity_key(row: dict[str, Any]) -> str:
    for key, value in row.items():
        if not is_number(value) and str(value or "").strip():
            return key
    return ""


def _first_entity(row: dict[str, Any]) -> str:
    key = _first_entity_key(row)
    return str(row.get(key) or "").strip() if key else ""


__all__ = ["build_fast_fact_claims"]
