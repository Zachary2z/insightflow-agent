from __future__ import annotations

from typing import Any

from workspaces.answer_evidence import business_field_label, is_number, rows_as_dicts


MAX_FAST_FACT_EVIDENCE_ROWS = 5


def build_fast_fact_context_pack(
    *,
    user_question: str,
    analysis_route: dict[str, Any] | None,
    analysis_task: dict[str, Any] | None,
    fact_payload: dict[str, Any] | None,
    evidence_result: dict[str, Any] | None,
    execution_result: dict[str, Any] | None,
    metric_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the compact evidence contract used only by the fast_fact answer path."""
    route = str((analysis_route or {}).get("route") or "")
    if route and route != "fast_fact":
        return {}

    task = analysis_task or {}
    payload = fact_payload or {}
    execution = execution_result or {}
    registry = metric_registry or {}
    rows = _payload_rows(payload, execution)
    display_rows = _display_rows(payload, rows)
    metric_ids = _metric_ids(rows, execution, payload)
    dimension_ids = _dimension_ids(rows, metric_ids, task)

    return {
        "user_question": str(user_question or ""),
        "route": "fast_fact",
        "task_type": str(task.get("task_type") or payload.get("task_type") or ""),
        "metrics": _metric_contexts(task, payload, registry, metric_ids),
        "dimensions": _dimension_contexts(task, payload, dimension_ids),
        "time_range": _time_range(task.get("time_range") or payload.get("time_scope") or {}),
        "comparison_scope": dict(payload.get("comparison_scope") or _comparison_scope(rows)),
        "key_evidence_rows": _key_evidence_rows(
            rows=rows,
            display_rows=display_rows,
            metric_ids=metric_ids,
            dimension_ids=dimension_ids,
            metric_registry=registry,
        ),
        "formulas": dict(payload.get("formulas") or registry.get("formulas") or {}),
        "caveats": _caveats(payload, evidence_result),
        "warnings": _warnings(payload, registry),
        "data_limits": _data_limits(payload, execution),
        "evidence_validation": _evidence_validation(evidence_result),
    }


def _payload_rows(payload: dict[str, Any], execution_result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = rows_as_dicts(execution_result)
    if rows:
        return rows
    payload_rows = payload.get("rows") or []
    columns = [str(column) for column in payload.get("columns") or []]
    return rows_as_dicts({"columns": columns, "rows": payload_rows, "success": bool(payload_rows)})


def _display_rows(payload: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    display = payload.get("display_values") or payload.get("formatted_values") or []
    if isinstance(display, list) and display:
        return [dict(item) for item in display[: len(rows) or None] if isinstance(item, dict)]
    return [{business_field_label(key, chinese=True): value for key, value in row.items()} for row in rows]


def _metric_ids(rows: list[dict[str, Any]], execution_result: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for row in rows:
        for key, value in row.items():
            if is_number(value) and key not in ids:
                ids.append(key)
    if ids:
        return ids
    for column in execution_result.get("columns") or payload.get("columns") or []:
        text = str(column).strip()
        if text and text not in ids:
            ids.append(text)
    return ids


def _dimension_ids(rows: list[dict[str, Any]], metric_ids: list[str], task: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for row in rows:
        for key, value in row.items():
            if key in metric_ids:
                continue
            if not is_number(value) and key not in ids:
                ids.append(key)
    if ids:
        return ids
    return [str(item) for item in task.get("dimensions") or [] if str(item).strip()]


def _metric_contexts(
    task: dict[str, Any],
    payload: dict[str, Any],
    registry: dict[str, Any],
    metric_ids: list[str],
) -> list[dict[str, Any]]:
    task_labels = [str(item).strip() for item in task.get("metrics") or payload.get("metrics") or [] if str(item).strip()]
    contexts = []
    for index, metric_id in enumerate(metric_ids or task_labels):
        metric = _registry_metric(registry, metric_id, task_labels[index] if index < len(task_labels) else "")
        label = (
            str(metric.get("business_label") or metric.get("label") or "").strip()
            or (task_labels[index] if index < len(task_labels) else "")
            or business_field_label(metric_id, chinese=True)
        )
        contexts.append(
            {
                "id": metric_id,
                "label": label,
                "unit": str(metric.get("unit") or _unit_for_metric(metric_id)),
                "formula": str(metric.get("formula") or (payload.get("formulas") or {}).get(metric_id) or ""),
            }
        )
    return contexts


def _dimension_contexts(task: dict[str, Any], payload: dict[str, Any], dimension_ids: list[str]) -> list[dict[str, Any]]:
    task_labels = [
        str(item).strip() for item in task.get("dimensions") or payload.get("dimensions") or [] if str(item).strip()
    ]
    contexts = []
    for index, dimension_id in enumerate(dimension_ids or task_labels):
        label = task_labels[index] if index < len(task_labels) else business_field_label(dimension_id, chinese=True)
        contexts.append({"id": dimension_id, "label": label})
    return contexts


def _time_range(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        display = str(value.get("raw_text") or "").strip()
        if not display and value.get("type") == "last_n_days" and value.get("value"):
            display = f"最近 {value['value']} 天"
        if not display and value.get("type") == "this_month":
            display = "本月"
        start = str(value.get("start") or "").strip()
        end = str(value.get("end") or "").strip()
        if not display and start and end:
            display = f"{start} 至 {end}"
        return {
            "display": display,
            "type": str(value.get("type") or ""),
            "start": start,
            "end": end,
            "value": value.get("value"),
        }
    text = str(value or "").strip()
    return {"display": text, "type": "", "start": "", "end": "", "value": None}


def _key_evidence_rows(
    *,
    rows: list[dict[str, Any]],
    display_rows: list[dict[str, Any]],
    metric_ids: list[str],
    dimension_ids: list[str],
    metric_registry: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence_rows = []
    for index, row in enumerate(rows[:MAX_FAST_FACT_EVIDENCE_ROWS]):
        display = display_rows[index] if index < len(display_rows) else {}
        evidence_rows.append(
            {
                "position": index + 1,
                "dimensions": [
                    {
                        "id": dimension_id,
                        "label": business_field_label(dimension_id, chinese=True),
                        "value": row.get(dimension_id),
                        "display_value": _display_value(display, dimension_id, row.get(dimension_id)),
                    }
                    for dimension_id in dimension_ids
                    if dimension_id in row
                ],
                "metrics": [
                    {
                        "id": metric_id,
                        "label": _metric_label(metric_registry, metric_id),
                        "value": row.get(metric_id),
                        "display_value": _display_value(
                            display,
                            metric_id,
                            row.get(metric_id),
                            label=_metric_label(metric_registry, metric_id),
                        ),
                        "unit": _metric_unit(metric_registry, metric_id),
                    }
                    for metric_id in metric_ids
                    if metric_id in row
                ],
            }
        )
    return evidence_rows


def _display_value(display_row: dict[str, Any], raw_key: str, fallback: Any, *, label: str = "") -> str:
    explicit_label = str(label or "").strip()
    default_label = business_field_label(raw_key, chinese=True)
    for key in (explicit_label, default_label, raw_key):
        if key in display_row:
            return str(display_row[key])
    return str(fallback)


def _registry_metric(registry: dict[str, Any], metric_id: str, label: str = "") -> dict[str, Any]:
    metrics = registry.get("metrics") if isinstance(registry.get("metrics"), dict) else {}
    direct = metrics.get(metric_id)
    if isinstance(direct, dict):
        return direct
    if label:
        for metric in metrics.values():
            if isinstance(metric, dict) and label in {
                str(metric.get("business_label") or ""),
                str(metric.get("label") or ""),
                str(metric.get("name") or ""),
            }:
                return metric
    return {}


def _metric_label(registry: dict[str, Any], metric_id: str) -> str:
    metric = _registry_metric(registry, metric_id)
    return str(metric.get("business_label") or metric.get("label") or "").strip() or business_field_label(metric_id, chinese=True)


def _metric_unit(registry: dict[str, Any], metric_id: str) -> str:
    metric = _registry_metric(registry, metric_id)
    return str(metric.get("unit") or _unit_for_metric(metric_id))


def _unit_for_metric(metric_id: str) -> str:
    lowered = str(metric_id or "").lower()
    if any(marker in lowered for marker in ("rate", "ratio", "roi", "return", "margin")) and "roas" not in lowered:
        return "percentage"
    if any(marker in lowered for marker in ("sales", "revenue", "amount", "spend", "cost", "gmv")):
        return "currency"
    return "number"


def _comparison_scope(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "result_set",
        "row_count": len(rows),
        "required_min_rows": 1,
        "retained_rows": len(rows),
        "sufficient": bool(rows),
    }


def _warnings(payload: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    warnings = [
        str(item).strip()
        for item in [*(payload.get("warnings") or []), *(registry.get("warnings") or [])]
        if str(item).strip()
    ]
    return list(dict.fromkeys(warnings))


def _caveats(payload: dict[str, Any], evidence_result: dict[str, Any] | None) -> list[str]:
    caveats = ["结论基于当前已导入数据和本次查询范围。"]
    caveats.extend(_warnings(payload, {}))
    validation = _evidence_validation(evidence_result)
    if validation["status"] not in {"validated", "passed"}:
        caveats.append("当前证据未完全通过校验，结论应作为低置信度参考。")
    return list(dict.fromkeys(caveats))


def _data_limits(payload: dict[str, Any], execution_result: dict[str, Any]) -> dict[str, Any]:
    comparison = payload.get("comparison_scope") if isinstance(payload.get("comparison_scope"), dict) else {}
    row_count = int(comparison.get("row_count") or len(execution_result.get("rows") or payload.get("rows") or []))
    retained = min(row_count, MAX_FAST_FACT_EVIDENCE_ROWS)
    return {
        "row_count": row_count,
        "retained_evidence_rows": retained,
        "truncated": bool(execution_result.get("truncated")) or row_count > retained,
    }


def _evidence_validation(evidence_result: dict[str, Any] | None) -> dict[str, Any]:
    evidence = evidence_result or {}
    status = str(evidence.get("validation_status") or evidence.get("status") or "").lower()
    if not status and evidence.get("success"):
        status = "validated"
    return {
        "status": status or "not_validated",
        "success": bool(evidence.get("success")) or status in {"validated", "passed"},
        "supported_count": len(evidence.get("data_supported_findings") or []),
        "unsupported_count": len(evidence.get("unsupported_claims_blocked") or []),
    }
