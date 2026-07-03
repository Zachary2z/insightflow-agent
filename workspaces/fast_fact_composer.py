from __future__ import annotations

from typing import Any

from workspaces.answer_evidence import business_field_label, is_number, row_summary, rows_as_dicts, to_number


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


def compose_fast_fact_answer(
    *,
    user_question: str,
    analysis_route: dict[str, Any] | None,
    analysis_task: dict[str, Any] | None,
    execution_result: dict[str, Any],
    evidence_result: dict[str, Any] | None = None,
    fact_payload: dict[str, Any] | None = None,
    context_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del analysis_route
    pack = context_pack if isinstance(context_pack, dict) else {}
    if pack.get("key_evidence_rows"):
        return _compose_from_context_pack(pack)

    task = analysis_task or {}
    payload = fact_payload or {}
    rows = rows_as_dicts(execution_result)
    display_rows = _display_rows(payload, rows)
    task_type = str(task.get("task_type") or payload.get("task_type") or "summary")
    time_text = _time_text(task.get("time_range") or payload.get("time_scope") or {})
    metric_label = _metric_label(task, payload, rows)
    dimension_label = _dimension_label(task, rows)

    if not execution_result.get("success") or not rows:
        direct_answer = f"{time_text}当前查询没有返回可用于回答的事实数据。".strip()
        headline = "当前查询没有返回数据"
        confidence = "low"
    elif task_type == "rank":
        direct_answer = _ranking_answer(
            time_text=time_text,
            rows=rows,
            display_rows=display_rows,
            metric_label=metric_label,
            dimension_label=dimension_label,
        )
        headline = direct_answer
        confidence = "high" if _evidence_validated(evidence_result) else "medium"
    elif task_type == "trend":
        direct_answer = _trend_answer(
            time_text=time_text,
            rows=rows,
            display_rows=display_rows,
            metric_label=metric_label,
        )
        headline = direct_answer
        confidence = "high" if _evidence_validated(evidence_result) else "medium"
    else:
        direct_answer = _summary_answer(time_text=time_text, rows=rows, display_rows=display_rows, metric_label=metric_label)
        headline = direct_answer
        confidence = "high" if _evidence_validated(evidence_result) else "medium"

    evidence_bullets = [_display_summary(row) for row in display_rows[:3]]
    caveats = ["结论基于当前已导入数据和本次查询范围。"]
    warnings = [str(item) for item in payload.get("warnings") or [] if str(item).strip()]
    caveats.extend(warnings[:2])

    return {
        "headline": _shorten(headline),
        "direct_answer": direct_answer,
        "why": "该结论来自已通过 SQL 审核并完成证据校验的查询结果。",
        "evidence_bullets": evidence_bullets,
        "recommendations": [],
        "caveats": list(dict.fromkeys(caveats)),
        "confidence": confidence,
    }


def _compose_from_context_pack(pack: dict[str, Any]) -> dict[str, Any]:
    task_type = str(pack.get("task_type") or "summary")
    rows = [row for row in pack.get("key_evidence_rows") or [] if isinstance(row, dict)]
    time_text = str((pack.get("time_range") or {}).get("display") or "").replace(" ", "").strip()
    metric_label = _pack_metric_label(pack, rows)
    dimension_label = _pack_dimension_label(pack, rows)
    validation = pack.get("evidence_validation") if isinstance(pack.get("evidence_validation"), dict) else {}
    confidence = "high" if validation.get("success") else "medium"

    if not rows:
        direct_answer = f"{time_text}当前查询没有返回可用于回答的事实数据。".strip()
        headline = "当前查询没有返回数据"
        confidence = "low"
    elif task_type == "rank":
        first = rows[0]
        entity = _pack_first_dimension_value(first)
        value = _pack_first_metric_value(first)
        comparison = pack.get("comparison_scope") if isinstance(pack.get("comparison_scope"), dict) else {}
        row_count = int(comparison.get("row_count") or len(rows))
        prefix = time_text if time_text else "本次查询"
        direct_answer = f"{prefix}{metric_label}最高的是「{entity}」，{metric_label}为 {value}。对比范围：共统计 {row_count} 个{dimension_label}。"
        headline = direct_answer
    elif task_type == "trend":
        first_value = _pack_first_metric_raw_value(rows[0])
        last_value = _pack_first_metric_raw_value(rows[-1])
        direction = "整体持平"
        if first_value is not None and last_value is not None:
            if last_value > first_value:
                direction = "整体上升"
            elif last_value < first_value:
                direction = "整体下降"
        prefix = time_text if time_text else "本次查询"
        direct_answer = (
            f"{prefix}{metric_label}趋势{direction}，从 {_pack_first_metric_value(rows[0])} "
            f"变化到 {_pack_first_metric_value(rows[-1])}。趋势范围：共统计 {len(rows)} 个时间点。"
        )
        headline = direct_answer
    else:
        first = rows[0]
        prefix = time_text if time_text else "本次查询"
        direct_answer = f"{prefix}{metric_label}为 {_pack_first_metric_value(first)}。"
        headline = direct_answer

    evidence_bullets = [_pack_evidence_summary(row) for row in rows[:3]]
    caveats = [
        str(item).strip()
        for item in [*(pack.get("caveats") or []), *(pack.get("warnings") or [])]
        if str(item).strip()
    ]
    if not caveats:
        caveats = ["结论基于当前已导入数据和本次查询范围。"]
    return {
        "headline": _shorten(headline),
        "direct_answer": direct_answer,
        "why": "该结论来自轻量事实上下文包中的已校验证据。",
        "evidence_bullets": evidence_bullets,
        "recommendations": [],
        "caveats": list(dict.fromkeys(caveats)),
        "confidence": confidence,
    }


def _pack_metric_label(pack: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    metrics = pack.get("metrics") if isinstance(pack.get("metrics"), list) else []
    for metric in metrics:
        if isinstance(metric, dict) and str(metric.get("label") or "").strip():
            return str(metric["label"]).strip()
    if rows:
        metric_items = rows[0].get("metrics") if isinstance(rows[0].get("metrics"), list) else []
        if metric_items and isinstance(metric_items[0], dict):
            return str(metric_items[0].get("label") or "指标")
    return "指标"


def _pack_dimension_label(pack: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    dimensions = pack.get("dimensions") if isinstance(pack.get("dimensions"), list) else []
    for dimension in dimensions:
        if isinstance(dimension, dict) and str(dimension.get("label") or "").strip():
            return str(dimension["label"]).strip()
    if rows:
        dimension_items = rows[0].get("dimensions") if isinstance(rows[0].get("dimensions"), list) else []
        if dimension_items and isinstance(dimension_items[0], dict):
            return str(dimension_items[0].get("label") or "对象")
    return "对象"


def _pack_first_dimension_value(row: dict[str, Any]) -> str:
    dimensions = row.get("dimensions") if isinstance(row.get("dimensions"), list) else []
    for item in dimensions:
        if isinstance(item, dict):
            value = str(item.get("display_value") or item.get("value") or "").strip()
            if value:
                return value
    return ""


def _pack_first_metric_value(row: dict[str, Any]) -> str:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), list) else []
    for item in metrics:
        if isinstance(item, dict):
            value = str(item.get("display_value") or item.get("value") or "").strip()
            if value:
                return value
    return ""


def _pack_first_metric_raw_value(row: dict[str, Any]) -> float | None:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), list) else []
    for item in metrics:
        if isinstance(item, dict):
            return to_number(item.get("value"))
    return None


def _pack_evidence_summary(row: dict[str, Any]) -> str:
    parts = []
    for item in row.get("dimensions") or []:
        if isinstance(item, dict) and (item.get("label") or item.get("display_value")):
            parts.append(f"{item.get('label') or '维度'} 为 {item.get('display_value') or item.get('value')}")
    for item in row.get("metrics") or []:
        if isinstance(item, dict) and (item.get("label") or item.get("display_value")):
            parts.append(f"{item.get('label') or '指标'} 为 {item.get('display_value') or item.get('value')}")
    return "，".join(parts) + "。" if parts else "当前证据行没有可展示字段。"


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


def _display_rows(fact_payload: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    display = fact_payload.get("display_values") or fact_payload.get("formatted_values") or []
    if isinstance(display, list) and display:
        return [dict(item) for item in display if isinstance(item, dict)]
    return [{business_field_label(key, chinese=True): value for key, value in row.items()} for row in rows]


def _time_text(time_scope: Any) -> str:
    if isinstance(time_scope, dict):
        raw = str(time_scope.get("raw_text") or "").replace(" ", "").strip()
        if raw:
            return raw
        if time_scope.get("type") == "last_n_days" and time_scope.get("value"):
            return f"最近{time_scope['value']}天"
        if time_scope.get("type") == "this_month":
            return "本月"
    text = str(time_scope or "").replace(" ", "").strip()
    return text


def _metric_label(task: dict[str, Any], payload: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    metrics = [str(item).strip() for item in task.get("metrics") or payload.get("metrics") or [] if str(item).strip()]
    if metrics:
        return metrics[0]
    metric_key = _first_metric_key(rows[0]) if rows else ""
    return business_field_label(metric_key, chinese=True) if metric_key else "指标"


def _dimension_label(task: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    dimensions = [str(item).strip() for item in task.get("dimensions") or [] if str(item).strip()]
    if dimensions:
        return dimensions[0]
    entity_key = ""
    for row in rows:
        entity_key = _first_entity_key(row)
        if entity_key:
            break
    return business_field_label(entity_key, chinese=True) if entity_key else "对象"


def _ranking_answer(
    *,
    time_text: str,
    rows: list[dict[str, Any]],
    display_rows: list[dict[str, Any]],
    metric_label: str,
    dimension_label: str,
) -> str:
    first = rows[0]
    display_first = display_rows[0] if display_rows else {}
    entity = _first_entity(first) or _first_display_entity(display_first)
    value = _first_display_metric_value(display_first) or str(first.get(_first_metric_key(first)) or "")
    prefix = f"{time_text}" if time_text else "本次查询"
    comparison = f"对比范围：共统计 {len(rows)} 个{dimension_label}。"
    return f"{prefix}{metric_label}最高的是「{entity}」，{metric_label}为 {value}。{comparison}"


def _summary_answer(*, time_text: str, rows: list[dict[str, Any]], display_rows: list[dict[str, Any]], metric_label: str) -> str:
    first = rows[0]
    display_first = display_rows[0] if display_rows else {}
    value = _first_display_metric_value(display_first) or str(first.get(_first_metric_key(first)) or "")
    prefix = f"{time_text}" if time_text else "本次查询"
    return f"{prefix}{metric_label}为 {value}。"


def _trend_answer(
    *,
    time_text: str,
    rows: list[dict[str, Any]],
    display_rows: list[dict[str, Any]],
    metric_label: str,
) -> str:
    metric_key = _first_metric_key(rows[0])
    first_value = to_number(rows[0].get(metric_key)) if metric_key else None
    last_value = to_number(rows[-1].get(metric_key)) if metric_key else None
    first_display = _first_display_metric_value(display_rows[0] if display_rows else {})
    last_display = _first_display_metric_value(display_rows[-1] if display_rows else {})
    direction = "整体持平"
    if first_value is not None and last_value is not None:
        if last_value > first_value:
            direction = "整体上升"
        elif last_value < first_value:
            direction = "整体下降"
    prefix = f"{time_text}" if time_text else "本次查询"
    return f"{prefix}{metric_label}趋势{direction}，从 {first_display} 变化到 {last_display}。趋势范围：共统计 {len(rows)} 个时间点。"


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


def _first_display_entity(display_row: dict[str, Any]) -> str:
    for value in display_row.values():
        if not is_number(value) and str(value or "").strip():
            return str(value)
    return ""


def _first_display_metric_value(display_row: dict[str, Any]) -> str:
    for value in display_row.values():
        if is_number(value):
            return str(value)
    values = list(display_row.values())
    return str(values[-1]) if values else ""


def _display_summary(display_row: dict[str, Any]) -> str:
    return row_summary(display_row, chinese=True)


def _evidence_validated(evidence_result: dict[str, Any] | None) -> bool:
    if not evidence_result:
        return False
    status = str(evidence_result.get("validation_status") or evidence_result.get("status") or "").lower()
    return bool(evidence_result.get("success")) or status == "validated"


def _shorten(text: str, limit: int = 120) -> str:
    normalized = " ".join(str(text or "").split())
    return normalized[:limit]
