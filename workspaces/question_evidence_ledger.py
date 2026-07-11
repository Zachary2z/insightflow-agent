from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from workspaces.analysis_contracts import AnalysisTask, QuestionEvidencePack, WorkbenchToolCall


@dataclass
class QuestionEvidenceFact:
    fact_id: str
    label: str
    value: Any
    task_id: str = ""
    unit: str = ""
    dimension: dict[str, Any] = field(default_factory=dict)
    source_columns: list[str] = field(default_factory=list)
    source_row_refs: list[str] = field(default_factory=list)
    evidence_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuestionDerivedMetric:
    metric_id: str
    label: str
    formula: str
    value: Any
    task_id: str = ""
    source_fact_ids: list[str] = field(default_factory=list)
    source_columns: list[str] = field(default_factory=list)
    evidence_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuestionEvidenceMetricRole:
    role: str
    label: str
    source_column: str
    source_fields: list[str] = field(default_factory=list)
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuestionEvidenceGroup:
    group_id: str
    purpose: str
    source: dict[str, Any]
    dimension: dict[str, Any]
    metrics: list[dict[str, Any]]
    time_policy: str
    row_grain: str
    supports_answer: bool
    supports_chart: bool
    evidence_refs: list[str] = field(default_factory=list)
    facts: list[dict[str, Any]] = field(default_factory=list)
    derived_metrics: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_question_evidence_ledger(
    *,
    question_evidence_pack: QuestionEvidencePack | dict[str, Any] | None,
    execution_result: dict[str, Any] | None = None,
    evidence_validation: dict[str, Any] | None = None,
    chart_artifacts: list[dict[str, Any]] | None = None,
    fact_payload: dict[str, Any] | None = None,
    source_pack_id: str = "question_evidence_pack",
    task_id: str = "",
) -> dict[str, Any]:
    pack = _pack(question_evidence_pack)
    execution = execution_result if isinstance(execution_result, dict) else {}
    validation = evidence_validation if isinstance(evidence_validation, dict) else {}
    rows = pack.rows or _rows_as_dicts(execution)
    columns = pack.columns or [str(column) for column in execution.get("columns") or []]
    facts = _facts(pack=pack, rows=rows, columns=columns, task_id=task_id)
    derived_metrics = _derived_metrics(fact_payload or {}, facts=facts, task_id=task_id)
    data_limits = _data_limits(pack, validation)
    evidence_groups = _evidence_groups(
        pack=pack,
        facts=facts,
        derived_metrics=derived_metrics,
        columns=columns,
        task_id=task_id,
    )
    question_evidence_plan = _question_evidence_plan(
        pack=pack,
        groups=evidence_groups,
        source_pack_id=source_pack_id,
    )
    evidence_refs = _unique(
        [
            *[fact["evidence_ref"] for fact in facts if fact.get("evidence_ref")],
            *[metric["evidence_ref"] for metric in derived_metrics if metric.get("evidence_ref")],
        ]
    )
    chart_refs = _chart_refs(chart_artifacts or [])
    ledger = {
        "ledger_id": _ledger_id(pack=pack, facts=facts, data_limits=data_limits),
        "question_evidence_plan": question_evidence_plan,
        "evidence_groups": evidence_groups,
        "business_lens": _safe_dict(pack.task.business_lens),
        "time_policy_note": _time_policy_note(pack.task),
        "facts": facts,
        "derived_metrics": derived_metrics,
        "data_limits": data_limits,
        "tool_calls": [_safe_tool_call(call) for call in pack.tool_calls],
        "evidence_refs": evidence_refs,
        "chart_refs": chart_refs,
        "task_refs": _task_refs(task_id, facts, derived_metrics, data_limits),
        "tables": _tables_from_pack(pack=pack, task_id=task_id),
        "source_pack_id": source_pack_id,
        "confidence": _confidence(facts=facts, derived_metrics=derived_metrics, data_limits=data_limits, validation=validation),
    }
    return sanitize_question_evidence_ledger(ledger)


def merge_question_evidence_ledgers(
    ledgers: list[dict[str, Any]],
    *,
    data_limits: list[str] | None = None,
    source_pack_id: str = "merged_question_evidence_pack",
) -> dict[str, Any]:
    valid_ledgers = [sanitize_question_evidence_ledger(ledger) for ledger in ledgers if isinstance(ledger, dict)]
    if not valid_ledgers:
        groups: list[dict[str, Any]] = []
        return sanitize_question_evidence_ledger(
            {
                "ledger_id": _merged_ledger_id(facts=[], data_limits=data_limits or []),
                "question_evidence_plan": _merged_question_evidence_plan(groups),
                "evidence_groups": groups,
                "facts": [],
                "derived_metrics": [],
                "data_limits": _unique([str(item) for item in data_limits or [] if str(item).strip()]),
                "tool_calls": [],
                "evidence_refs": [],
                "chart_refs": [],
                "task_refs": [],
                "tables": [],
                "source_pack_id": source_pack_id,
                "confidence": "low",
            }
        )

    facts = _merge_items(valid_ledgers, "facts")
    derived_metrics = _merge_items(valid_ledgers, "derived_metrics")
    evidence_groups = _merge_groups(valid_ledgers)
    merged_limits = _unique(
        [
            *[str(item) for ledger in valid_ledgers for item in ledger.get("data_limits") or []],
            *[str(item) for item in data_limits or []],
        ]
    )
    tool_calls = _merge_tool_calls(valid_ledgers)
    evidence_refs = _unique([str(item) for ledger in valid_ledgers for item in ledger.get("evidence_refs") or []])
    chart_refs = _unique([str(item) for ledger in valid_ledgers for item in ledger.get("chart_refs") or []])
    task_refs = _unique([str(item) for ledger in valid_ledgers for item in ledger.get("task_refs") or []])
    tables = _merge_tables(valid_ledgers)
    first = valid_ledgers[0]
    confidence = "low" if not facts and not derived_metrics else ("medium" if merged_limits else _best_confidence(valid_ledgers))
    return sanitize_question_evidence_ledger(
        {
            "ledger_id": _merged_ledger_id(facts=facts, data_limits=merged_limits),
            "question_evidence_plan": _merged_question_evidence_plan(evidence_groups),
            "evidence_groups": evidence_groups,
            "business_lens": first.get("business_lens") or {},
            "time_policy_note": first.get("time_policy_note") or "",
            "facts": facts,
            "derived_metrics": derived_metrics,
            "data_limits": merged_limits,
            "tool_calls": tool_calls,
            "evidence_refs": evidence_refs,
            "chart_refs": chart_refs,
            "task_refs": task_refs,
            "tables": tables,
            "source_pack_id": source_pack_id,
            "confidence": confidence,
        }
    )


def empty_question_evidence_ledger(
    *,
    task: AnalysisTask | dict[str, Any] | None = None,
    data_limits: list[str] | None = None,
) -> dict[str, Any]:
    resolved_task = task if isinstance(task, AnalysisTask) else AnalysisTask.from_dict(task or {})
    return sanitize_question_evidence_ledger(
        {
            "ledger_id": _ledger_id(pack=QuestionEvidencePack(task=resolved_task), facts=[], data_limits=data_limits or []),
            "question_evidence_plan": _merged_question_evidence_plan([]),
            "evidence_groups": [],
            "business_lens": _safe_dict(resolved_task.business_lens),
            "time_policy_note": _time_policy_note(resolved_task),
            "facts": [],
            "derived_metrics": [],
            "data_limits": _unique([str(item) for item in data_limits or [] if str(item).strip()]),
            "tool_calls": [],
            "evidence_refs": [],
            "chart_refs": [],
            "task_refs": [],
            "tables": [],
            "source_pack_id": "question_evidence_pack",
            "confidence": "low",
        }
    )


def sanitize_question_evidence_ledger(value: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        return {}
    allowed = {
        "ledger_id",
        "question_evidence_plan",
        "evidence_groups",
        "business_lens",
        "time_policy_note",
        "facts",
        "derived_metrics",
        "data_limits",
        "tool_calls",
        "evidence_refs",
        "chart_refs",
        "task_refs",
        "tables",
        "source_pack_id",
        "source_refs",
        "confidence",
    }
    return {
        key: _sanitize(value.get(key))
        for key in allowed
        if key in value
    }


def build_answer_input_ledger(value: dict[str, Any] | None) -> dict[str, Any]:
    """Project the persisted question ledger into the only shape allowed in answer prompts."""
    ledger = sanitize_question_evidence_ledger(value)
    if not ledger:
        return {}
    groups = _answer_evidence_groups(_ledger_groups(ledger))
    evidence_refs = _unique(
        [
            *[
                str(ref)
                for group in groups
                if isinstance(group, dict)
                for ref in group.get("evidence_refs") or []
            ],
        ]
    )
    answer_input = {
        "business_lens": _answer_business_lens(ledger.get("business_lens") if isinstance(ledger.get("business_lens"), dict) else {}),
        "time_policy_note": str(ledger.get("time_policy_note") or "").strip(),
        "evidence_groups": groups,
        "data_limits": _answer_data_limits(ledger.get("data_limits") or []),
        "evidence_refs": evidence_refs,
        "chart_refs": [str(item) for item in ledger.get("chart_refs") or [] if str(item).strip()],
        "confidence": str(ledger.get("confidence") or "medium") if str(ledger.get("confidence") or "") in {"low", "medium", "high"} else "medium",
    }
    return _sanitize(answer_input)


def build_grouped_chart_candidate(value: dict[str, Any] | None, *, question: str = "") -> dict[str, Any]:
    """Select one coherent grouped-ledger chart candidate with business labels only."""
    ledger = sanitize_question_evidence_ledger(value)
    source = "question_evidence_ledger.evidence_groups"
    if not ledger:
        return _chart_candidate_failure("缺少可用于图表的分组证据。")

    groups = [group for group in _ledger_groups(ledger) if group.get("supports_chart")]
    if not groups:
        return _chart_candidate_failure("缺少可用于图表的分组证据。")

    bundles = [_chart_bundle_from_group(group) for group in groups]
    bundles = [bundle for bundle in bundles if bundle.get("entries")]
    if not bundles:
        return _chart_candidate_failure("分组证据中没有可用于图表的数值指标。")

    if len(bundles) == 1:
        return _candidate_from_bundles(bundles, question=question, source=source)

    comparable = _comparable_chart_bundles(bundles)
    if not comparable.get("success"):
        return _chart_candidate_failure(str(comparable.get("reason") or "多个证据组不能在同一张图中混合。"))
    return _candidate_from_bundles(bundles, question=question, source=source)


def build_chart_safe_table(value: dict[str, Any] | None) -> dict[str, Any]:
    """Project one coherent evidence group into a chart-safe table with business labels only."""
    candidate = build_grouped_chart_candidate(value)
    if not candidate.get("success"):
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "source": "question_evidence_ledger.evidence_groups",
            "reason": str(candidate.get("reason") or ""),
        }
    return {
        key: candidate[key]
        for key in ("success", "source", "columns", "rows", "row_count", "units", "evidence_refs")
        if key in candidate
    }


def _chart_candidate_failure(reason: str) -> dict[str, Any]:
    return {
        "success": False,
        "source": "question_evidence_ledger.evidence_groups",
        "reason": reason,
        "columns": [],
        "rows": [],
        "row_count": 0,
    }


def _chart_bundle_from_group(group: dict[str, Any]) -> dict[str, Any]:
    entries = _chart_entries_from_group(group)
    metric_labels = _unique([entry["label"] for entry in entries])
    units = {label: _display_unit(_metric_unit(group, label) or _entry_unit(entries, label)) for label in metric_labels}
    dimension = group.get("dimension") if isinstance(group.get("dimension"), dict) else {}
    return {
        "group_id": str(group.get("group_id") or ""),
        "purpose": str(group.get("purpose") or ""),
        "dimension_label": _safe_business_label(dimension.get("label") or group.get("row_grain") or "对象"),
        "dimension_signature": _dimension_signature(group),
        "row_grain": _safe_business_label(group.get("row_grain") or dimension.get("label") or "对象"),
        "metric_labels": metric_labels,
        "units": units,
        "entries": entries,
        "evidence_refs": [str(ref) for ref in group.get("evidence_refs") or [] if str(ref).strip()],
        "time_policy": str(group.get("time_policy") or ""),
    }


def _entry_unit(entries: list[dict[str, Any]], label: str) -> str:
    for entry in entries:
        if entry.get("label") == label and entry.get("unit"):
            return str(entry.get("unit") or "")
    return ""


def _dimension_signature(group: dict[str, Any]) -> str:
    dimension = group.get("dimension") if isinstance(group.get("dimension"), dict) else {}
    columns = [str(column) for column in dimension.get("source_columns") or [] if str(column).strip()]
    if columns:
        return "|".join(columns)
    return _normalize_text(group.get("row_grain") or dimension.get("label") or "")


def _comparable_chart_bundles(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    first = bundles[0]
    for bundle in bundles[1:]:
        if bundle.get("dimension_signature") != first.get("dimension_signature") or bundle.get("row_grain") != first.get("row_grain"):
            return {"success": False, "reason": "多个证据组的业务对象或颗粒度不同，不能在同一张图中混合。"}
    return {"success": True}


def _candidate_from_bundles(bundles: list[dict[str, Any]], *, question: str, source: str) -> dict[str, Any]:
    metric_labels = _unique([label for bundle in bundles for label in bundle.get("metric_labels") or []])
    all_units = {label: str(unit or "") for bundle in bundles for label, unit in (bundle.get("units") or {}).items()}
    units = {label: unit for label, unit in all_units.items() if unit}
    entries = [entry for bundle in bundles for entry in bundle.get("entries") or []]
    unit_check = _compatible_candidate_units(list(units.values()))
    if len(metric_labels) > 2 and (not unit_check.get("success") or len(units) != len(metric_labels)):
        subset = _compatible_metric_subset(metric_labels, all_units)
        if not subset:
            return _chart_candidate_failure("多个指标缺少明确且可比较的单位，不能生成同一张图。")
        metric_labels = subset
        all_units = {label: unit for label, unit in all_units.items() if label in metric_labels}
        units = {label: unit for label, unit in all_units.items() if unit}
        entries = [entry for entry in entries if entry.get("label") in metric_labels]
        unit_check = _compatible_candidate_units(list(units.values()))
    scatter_candidate = len(metric_labels) == 2 and (not unit_check.get("success") or len(units) != len(metric_labels))
    if len(metric_labels) > 2 and (not unit_check.get("success") or len(units) != len(metric_labels)):
        return _chart_candidate_failure("多个指标缺少明确且可比较的单位，不能生成同一张图。")
    if len(metric_labels) <= 1 and not unit_check.get("success"):
        return _chart_candidate_failure(str(unit_check.get("reason") or "指标单位不兼容，不能生成同一张图。"))
    if len(metric_labels) > 1 and not scatter_candidate and not unit_check.get("success"):
        return _chart_candidate_failure(str(unit_check.get("reason") or "指标单位不兼容，不能生成同一张图。"))

    dimension_label = _safe_business_label(bundles[0].get("dimension_label") or "对象")
    row_grain = _safe_business_label(bundles[0].get("row_grain") or dimension_label)
    evidence_refs = _safe_chart_refs([ref for bundle in bundles for ref in bundle.get("evidence_refs") or []])
    time_policy = " ".join(str(bundle.get("time_policy") or "") for bundle in bundles)
    title = _chart_title(question=question, time_policy=time_policy, dimension_label=dimension_label, metric_labels=metric_labels)

    if len(metric_labels) == 1:
        unit = str(unit_check.get("unit") or "")
        metric_label = metric_labels[0]
        rows = [[entry["entity"], entry["value"]] for entry in entries if entry["label"] == metric_label]
        columns = [dimension_label, metric_label]
        chart_type = "ranked_bar"
        x = dimension_label
        y = metric_label
        series = ""
        label = ""
    elif scatter_candidate:
        x, y = metric_labels
        rows = _scatter_rows(entries, x_label=x, y_label=y)
        if not rows:
            return _chart_candidate_failure("两个指标没有同一业务对象下的可比较数值，不能生成图表。")
        columns = [dimension_label, x, y]
        chart_type = "scatter"
        series = ""
        label = dimension_label
        unit = str(all_units.get(y) or "")
    else:
        unit = str(unit_check.get("unit") or "")
        value_axis = _value_axis_label(unit)
        rows = [[entry["entity"], entry["label"], entry["value"]] for entry in entries if entry["label"] in metric_labels]
        columns = [dimension_label, "指标", value_axis]
        chart_type = "grouped_bar"
        x = dimension_label
        y = value_axis
        series = "指标"
        label = ""

    candidate = {
        "success": True,
        "source": source,
        "chart_type": chart_type,
        "title": title,
        "dimension_label": dimension_label,
        "metric_labels": metric_labels,
        "unit": unit,
        "units": units,
        "row_grain": row_grain,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "evidence_refs": evidence_refs,
        "chart_spec": {
            "success": True,
            "source": "grouped_ledger_candidate",
            "chart_type": chart_type,
            "title": title,
            "x": x,
            "y": y,
            "label": label,
            "y_secondary": "",
            "series": series,
            "required_columns": [column for column in (dimension_label, series, y) if column],
            "explanation_basis": ["grouped_question_evidence_ledger"],
            "unit": unit,
            "value_label": True,
            "business_annotation": f"图表仅展示同一{row_grain}下可比较的{_join_labels(metric_labels)}证据。",
            "metric_units": units,
        },
    }
    return _sanitize(candidate)


def _compatible_metric_subset(metric_labels: list[str], units: dict[str, str]) -> list[str]:
    labels_by_family: dict[str, list[str]] = {}
    for label in metric_labels:
        unit = str(units.get(label) or "").strip()
        if not unit:
            continue
        family = _unit_family(unit)
        if not family:
            continue
        labels_by_family.setdefault(family, []).append(label)
    candidates = [labels for labels in labels_by_family.values() if len(labels) >= 2]
    if not candidates:
        return []
    family_priority = {"currency": 0, "count": 1, "percentage": 2}
    return sorted(
        candidates,
        key=lambda labels: (
            family_priority.get(_unit_family(units.get(labels[0], "")), 99),
            -len(labels),
            metric_labels.index(labels[0]),
        ),
    )[0]


def _scatter_rows(entries: list[dict[str, Any]], *, x_label: str, y_label: str) -> list[list[Any]]:
    by_entity: dict[str, dict[str, float]] = {}
    for entry in entries:
        label = str(entry.get("label") or "")
        if label not in {x_label, y_label}:
            continue
        entity = str(entry.get("entity") or "整体")
        by_entity.setdefault(entity, {})[label] = entry.get("value")
    return [
        [entity, values[x_label], values[y_label]]
        for entity, values in by_entity.items()
        if _to_number(values.get(x_label)) is not None and _to_number(values.get(y_label)) is not None
    ]


def _compatible_candidate_units(units: list[str]) -> dict[str, Any]:
    normalized = _unique([_unit_family(unit) for unit in units if str(unit or "").strip()])
    if not normalized:
        return {"success": True, "unit": ""}
    if len(normalized) == 1:
        return {"success": True, "unit": _display_unit(normalized[0])}
    return {"success": False, "reason": "指标单位不兼容，不能生成同一张图。"}


def _unit_family(unit: str) -> str:
    lowered = str(unit or "").strip().lower()
    if lowered in {"currency", "money", "amount", "元", "人民币", "cny", "rmb"}:
        return "currency"
    if lowered in {"percentage", "percent", "pct", "%", "roi", "roas", "rate"}:
        return "percentage"
    if lowered in {"count", "number", "个", "次", "件", "单"}:
        return "count"
    return lowered


def _display_unit(unit: str) -> str:
    family = _unit_family(unit)
    if family == "currency":
        return "元"
    if family == "percentage":
        return "%"
    if family == "count":
        return "个"
    return str(unit or "").strip()


def _value_axis_label(unit: str) -> str:
    family = _unit_family(unit)
    if family == "currency":
        return "金额"
    if family == "percentage":
        return "比例"
    if family == "count":
        return "数量"
    return "指标值"


def _chart_title(*, question: str, time_policy: str, dimension_label: str, metric_labels: list[str]) -> str:
    time_prefix = _time_prefix(question) or _time_prefix(time_policy)
    metric_text = _join_labels(metric_labels) or "指标"
    return f"{time_prefix}{dimension_label}{metric_text}对比"


def _time_prefix(text: str) -> str:
    value = str(text or "")
    match = re.search(r"(最近\s*\d+\s*天|近\s*\d+\s*天|最近\s*\d+\s*个月|近\s*\d+\s*个月|本月|本季度|今年)", value)
    return re.sub(r"\s+", "", match.group(1)) if match else ""


def _join_labels(labels: list[str]) -> str:
    clean = [str(label).strip() for label in labels if str(label).strip()]
    if len(clean) <= 1:
        return clean[0] if clean else ""
    return "与".join(clean)


def _safe_business_label(value: Any) -> str:
    text = str(value or "").strip()
    if not text or _looks_internal_text(text):
        return "对象"
    return text


def _safe_chart_refs(refs: list[str]) -> list[str]:
    safe = [ref for ref in refs if ref and not _looks_internal_text(ref)]
    return safe or ["question_evidence_pack"]



def ledger_supported_fact_texts(ledger: dict[str, Any] | None) -> list[str]:
    if not isinstance(ledger, dict):
        return []
    sanitized = sanitize_question_evidence_ledger(ledger)
    texts: list[str] = []
    grouped_facts = [
        fact
        for group in _ledger_groups(sanitized)
        for fact in group.get("facts") or []
        if isinstance(fact, dict)
    ]
    grouped_derived = [
        metric
        for group in _ledger_groups(sanitized)
        for metric in group.get("derived_metrics") or []
        if isinstance(metric, dict)
    ]
    for fact in grouped_facts or ledger.get("facts") or []:
        if not isinstance(fact, dict):
            continue
        dimension = fact.get("dimension") if isinstance(fact.get("dimension"), dict) else {}
        dim_text = "，".join(f"{key} 为 {value}" for key, value in dimension.items() if str(value).strip())
        label = str(fact.get("label") or "").strip()
        value = fact.get("value")
        if dim_text and label:
            texts.append(f"{dim_text}，{label} 为 {value}。")
        elif label:
            texts.append(f"{label} 为 {value}。")
    for metric in grouped_derived or ledger.get("derived_metrics") or []:
        if not isinstance(metric, dict):
            continue
        label = str(metric.get("label") or metric.get("metric_id") or "").strip()
        if label:
            texts.append(f"{label} 为 {metric.get('value')}。")
    return _unique(texts)


def _chart_entries_from_group(group: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    facts = [item for item in group.get("facts") or [] if isinstance(item, dict)]
    for item in facts:
        value = _to_number(item.get("value"))
        if value is None:
            continue
        label = str(item.get("label") or item.get("metric_id") or "").strip()
        if not label or _looks_internal_text(label):
            continue
        entity = _chart_entity(item.get("dimension") if isinstance(item.get("dimension"), dict) else {})
        entries.append(
            {
                "entity": entity,
                "label": label,
                "value": value,
                "unit": str(item.get("unit") or _metric_unit(group, label) or "").strip(),
            }
        )
    return entries


def _metric_unit(group: dict[str, Any], label: str) -> str:
    for metric in group.get("metrics") or []:
        if isinstance(metric, dict) and str(metric.get("label") or "") == label:
            return str(metric.get("unit") or "")
    return ""


def _chart_entity(dimension: dict[str, Any]) -> str:
    values = [
        str(value).strip()
        for value in dimension.values()
        if str(value).strip() and not _looks_internal_text(str(value))
    ]
    if values:
        return " / ".join(values)
    return "整体"


def _looks_internal_text(value: str) -> bool:
    text = str(value or "")
    lowered = text.lower()
    return (
        any(marker in lowered for marker in ("task_id", "task_purpose", "core_fact", "explanation_support", "trend_or_anomaly"))
        or bool(re.search(r"\b[A-Za-z]+_[A-Za-z0-9_]{8,}\b", text))
        or bool(re.search(r"\b(?:select|with|insert|update|delete|drop|alter|create)\b", text, re.IGNORECASE))
    )


def _answer_business_lens(lens: dict[str, Any]) -> dict[str, Any]:
    return {
        "business_domain": str(lens.get("business_domain") or "").strip(),
        "metrics": [
            {
                "label": str(item.get("label") or "").strip(),
                "metric_role": str(item.get("metric_role") or "").strip(),
            }
            for item in lens.get("metrics") or []
            if isinstance(item, dict) and str(item.get("label") or "").strip()
        ],
        "dimensions": [
            {"label": str(item.get("label") or "").strip()}
            for item in lens.get("dimensions") or []
            if isinstance(item, dict) and str(item.get("label") or "").strip()
        ],
    }


def _answer_evidence_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    answer_groups: list[dict[str, Any]] = []
    for group_index, group in enumerate(groups, start=1):
        if not isinstance(group, dict) or not group.get("supports_answer"):
            continue
        group_dimension = group.get("dimension") if isinstance(group.get("dimension"), dict) else {}
        dimension_label = _safe_business_label(group_dimension.get("label"))
        facts = _answer_facts(group.get("facts") or [], dimension_label=dimension_label)
        derived_metrics = _answer_derived_metrics(group.get("derived_metrics") or [], offset=len(facts))
        evidence_refs = _unique(
            [
                *[str(item.get("evidence_ref") or "") for item in facts if isinstance(item, dict)],
                *[str(item.get("evidence_ref") or "") for item in derived_metrics if isinstance(item, dict)],
            ]
        )
        answer_groups.append(
            {
                "group_id": f"evidence_group_{group_index}",
                "purpose": _sanitize(group.get("purpose")),
                "source": _sanitize(group.get("source") if isinstance(group.get("source"), dict) else {}),
                "dimension": {"label": dimension_label},
                "metrics": _answer_metric_roles(group.get("metrics") if isinstance(group.get("metrics"), list) else []),
                "time_policy": _sanitize(group.get("time_policy")),
                "row_grain": _sanitize(group.get("row_grain")),
                "facts": facts,
                "derived_metrics": derived_metrics,
                "evidence_refs": evidence_refs,
            }
        )
    return answer_groups


def _answer_metric_roles(items: list[Any]) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        label = _safe_business_label(item.get("label"))
        if not label:
            continue
        metrics.append(
            {
                "label": label,
                "role": _sanitize(item.get("role")),
                "unit": _sanitize(item.get("unit")),
            }
        )
    return metrics


def _answer_facts(items: list[Any], *, dimension_label: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        evidence_ref = f"evidence:fact:{index}"
        label = _safe_business_label(item.get("label"))
        dimension = item.get("dimension") if isinstance(item.get("dimension"), dict) else {}
        business_object = _chart_entity(dimension)
        value = _sanitize(item.get("value"))
        unit = _sanitize(item.get("unit"))
        facts.append(
            {
                "label": label,
                "value": value,
                "unit": unit,
                "business_object": business_object,
                "dimension": {"label": dimension_label or "对象", "value": business_object},
                "fact_text": _fact_text(business_object=business_object, label=label, value=value, unit=unit),
                "evidence_ref": evidence_ref,
            }
        )
    return facts


def _answer_derived_metrics(items: list[Any], *, offset: int) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        evidence_ref = f"evidence:derived:{offset + index}"
        label = _safe_business_label(item.get("label") or item.get("metric_id"))
        value = _sanitize(item.get("value"))
        metrics.append(
            {
                "label": label,
                "value": value,
                "fact_text": _fact_text(business_object="", label=label, value=value, unit=""),
                "evidence_ref": evidence_ref,
            }
        )
    return metrics


def _fact_text(*, business_object: str, label: str, value: Any, unit: Any) -> str:
    display_unit = _display_unit(unit)
    prefix = f"{business_object}的" if business_object and business_object != "整体" else ""
    return f"{prefix}{label}为{value}{display_unit}。"


def _display_unit(unit: Any) -> str:
    normalized = str(unit or "").strip().lower()
    if normalized in {"currency", "amount", "money", "yuan", "rmb"}:
        return "元"
    if normalized in {"percentage", "percent", "rate"}:
        return "%"
    return ""


def _answer_data_limits(items: list[Any]) -> list[str]:
    limits: list[str] = []
    for item in items:
        text = _sanitize_text(str(item or ""))
        lowered = text.lower()
        if not text:
            continue
        if any(marker in lowered for marker in ("[redacted_query]", "provider_metadata", "trace_path", "证据任务", "task ")):
            text = "部分辅助证据未能完成；本次回答仅基于已验证的业务事实。"
        limits.append(text)
    return _unique(limits)


def ledger_supports_claim(ledger: dict[str, Any] | None, claim: str) -> bool:
    if not isinstance(ledger, dict) or not claim:
        return False
    claim_numbers = _claim_numbers(claim)
    if not claim_numbers:
        return False
    normalized_claim = _normalize_text(claim)
    grouped_entries = [
        item
        for group in _ledger_groups(sanitize_question_evidence_ledger(ledger))
        for item in [*(group.get("facts") or []), *(group.get("derived_metrics") or [])]
        if isinstance(item, dict)
    ]
    entries = grouped_entries or [*(ledger.get("facts") or []), *(ledger.get("derived_metrics") or [])]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_numbers = _numbers(entry.get("value"))
        if not entry_numbers:
            continue
        if not all(any(_number_close(claim_number, entry_number) for entry_number in entry_numbers) for claim_number in claim_numbers):
            continue
        dimension = entry.get("dimension") if isinstance(entry.get("dimension"), dict) else {}
        dimension_values = [_normalize_text(value) for value in dimension.values() if str(value).strip()]
        if dimension_values and not any(value and value in normalized_claim for value in dimension_values):
            continue
        label = _normalize_text(entry.get("label") or entry.get("metric_id") or "")
        if label and not _label_matches_claim(label, normalized_claim) and not any(value and value in normalized_claim for value in dimension_values):
            continue
        return True
    return False


def _pack(value: QuestionEvidencePack | dict[str, Any] | None) -> QuestionEvidencePack:
    if isinstance(value, QuestionEvidencePack):
        return value
    if isinstance(value, dict) and value:
        return QuestionEvidencePack.from_dict(value)
    return QuestionEvidencePack(task=AnalysisTask(resolved_question=""))


def _facts(
    *,
    pack: QuestionEvidencePack,
    rows: list[dict[str, Any]],
    columns: list[str],
    task_id: str = "",
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    metrics = _metric_labels(pack)
    safe_task_id = _safe_ref(task_id)
    for row_index, row in enumerate(rows):
        dimensions = {column: row.get(column) for column in columns if _is_dimension_value(row.get(column))}
        numeric_columns = [column for column in columns if _to_number(row.get(column)) is not None]
        if not numeric_columns and row:
            numeric_columns = [columns[-1]] if columns else []
        for metric_index, metric_column in enumerate(numeric_columns):
            value = row.get(metric_column)
            evidence_ref = (
                f"evidence:{safe_task_id}:row:{row_index}:{_safe_ref(metric_column)}"
                if task_id
                else f"evidence:row:{row_index}:{_safe_ref(metric_column)}"
            )
            fact = QuestionEvidenceFact(
                fact_id=f"fact_{safe_task_id}_{len(facts) + 1}" if task_id else f"fact_{len(facts) + 1}",
                label=_metric_label_for_column(metric_column, pack=pack, numeric_columns=numeric_columns, metric_hints=metrics),
                value=value,
                task_id=task_id,
                unit=_unit_for(metric_column),
                dimension=dimensions,
                source_columns=[*dimensions.keys(), metric_column],
                source_row_refs=[f"{task_id}:row:{row_index}" if task_id else f"row:{row_index}"],
                evidence_ref=evidence_ref,
            )
            facts.append(fact.to_dict())
    return facts


def _derived_metrics(fact_payload: dict[str, Any], *, facts: list[dict[str, Any]], task_id: str = "") -> list[dict[str, Any]]:
    fact_ids_by_row: dict[int, list[str]] = {}
    for fact in facts:
        refs = fact.get("source_row_refs") or []
        if refs and isinstance(refs[0], str) and refs[0].startswith("row:"):
            try:
                row_index = int(refs[0].split(":", 1)[1])
            except ValueError:
                continue
            fact_ids_by_row.setdefault(row_index, []).append(str(fact.get("fact_id") or ""))
        elif refs and isinstance(refs[0], str) and ":row:" in refs[0]:
            try:
                row_index = int(refs[0].rsplit(":row:", 1)[1])
            except ValueError:
                continue
            fact_ids_by_row.setdefault(row_index, []).append(str(fact.get("fact_id") or ""))

    derived: list[dict[str, Any]] = []
    safe_task_id = _safe_ref(task_id)
    for item in fact_payload.get("derived_metrics") or []:
        if not isinstance(item, dict):
            continue
        values = item.get("values") if isinstance(item.get("values"), list) else [{"value": item.get("value")}]
        for value_item in values:
            if not isinstance(value_item, dict):
                continue
            row_index = value_item.get("row_index")
            source_fact_ids = fact_ids_by_row.get(int(row_index), []) if isinstance(row_index, int) else []
            evidence_ref = (
                f"evidence:{safe_task_id}:derived:{_safe_ref(item.get('metric_id'))}:{row_index if row_index is not None else len(derived)}"
                if task_id
                else f"evidence:derived:{_safe_ref(item.get('metric_id'))}:{row_index if row_index is not None else len(derived)}"
            )
            derived.append(
                QuestionDerivedMetric(
                    metric_id=str(item.get("metric_id") or f"derived_{len(derived) + 1}"),
                    label=str(item.get("label") or item.get("metric_id") or ""),
                    formula=str(item.get("formula") or ""),
                    value=value_item.get("value"),
                    task_id=task_id,
                    source_fact_ids=[fact_id for fact_id in source_fact_ids if fact_id],
                    source_columns=[str(column) for column in item.get("source_columns") or [] if str(column).strip()],
                    evidence_ref=evidence_ref,
                ).to_dict()
            )
    return derived


def _rows_as_dicts(execution: dict[str, Any]) -> list[dict[str, Any]]:
    columns = [str(column) for column in execution.get("columns") or []]
    rows: list[dict[str, Any]] = []
    for row in execution.get("rows") or []:
        if isinstance(row, dict):
            rows.append(dict(row))
        elif isinstance(row, (list, tuple)):
            rows.append({columns[index]: value for index, value in enumerate(row) if index < len(columns)})
    return rows


def _metric_labels(pack: QuestionEvidencePack) -> list[str]:
    lens_metrics = [
        str(metric.get("label") or "").strip()
        for metric in pack.task.business_lens.get("metrics") or []
        if isinstance(metric, dict) and str(metric.get("label") or "").strip()
    ]
    return lens_metrics or [str(metric) for metric in pack.metrics or pack.task.metrics if str(metric).strip()]


def _metric_label_for_column(
    column: str,
    *,
    pack: QuestionEvidencePack,
    numeric_columns: list[str],
    metric_hints: list[str],
) -> str:
    for metric in _lens_metrics(pack):
        label = str(metric.get("label") or metric.get("business_label") or "").strip()
        if label and _column_matches_metric(column, metric):
            return label
    fallback = _label_from_column(column)
    if fallback != str(column):
        return fallback
    if len(numeric_columns) == 1 and metric_hints:
        return metric_hints[0]
    return str(column)


def _column_matches_metric(column: str, metric: dict[str, Any]) -> bool:
    normalized_column = _normalize_identifier(column)
    candidates = [
        metric.get("source_column"),
        metric.get("source_field"),
        metric.get("field"),
        metric.get("name"),
        *list(metric.get("source_fields") or []),
    ]
    for candidate in candidates:
        normalized_candidate = _normalize_identifier(str(candidate or "").split(".")[-1])
        if not normalized_candidate:
            continue
        if normalized_candidate == normalized_column:
            return True
        if normalized_candidate in normalized_column:
            return True
        candidate_tokens = [token for token in normalized_candidate.split("_") if token]
        if candidate_tokens and all(token in normalized_column for token in candidate_tokens):
            return True
    return False


def _label_from_column(column: str) -> str:
    lowered = str(column).lower()
    if "revenue" in lowered:
        return "收入"
    if "sales" in lowered:
        return "销售额"
    if "spend" in lowered or "cost" in lowered:
        return "投放成本"
    if "roi" in lowered or "roas" in lowered:
        return "ROI"
    return str(column)


def _unit_for(column: str) -> str:
    lowered = str(column).lower()
    if any(marker in lowered for marker in ("revenue", "sales", "amount", "spend", "cost", "gmv")):
        return "currency"
    if any(marker in lowered for marker in ("rate", "roi", "roas", "share", "pct")):
        return "percentage"
    if any(marker in lowered for marker in ("count", "quantity", "qty")):
        return "count"
    return ""


def _data_limits(pack: QuestionEvidencePack, validation: dict[str, Any]) -> list[str]:
    return _unique(
        [
            *[str(item) for item in pack.data_limits if str(item).strip()],
            *[str(item) for item in pack.task.business_lens.get("data_limits") or [] if str(item).strip()],
            *[str(item) for item in validation.get("data_limits") or [] if str(item).strip()],
            *[str(item) for item in validation.get("warnings") or [] if str(item).strip()],
        ]
    )


def _chart_refs(chart_artifacts: list[dict[str, Any]]) -> list[str]:
    refs = []
    for chart in chart_artifacts:
        if not isinstance(chart, dict):
            continue
        ref = str(chart.get("artifact_id") or chart.get("chart_id") or chart.get("title") or "").strip()
        if ref:
            refs.append(ref)
    return _unique(refs)


def _task_refs(
    task_id: str,
    facts: list[dict[str, Any]],
    derived_metrics: list[dict[str, Any]],
    data_limits: list[str],
) -> list[str]:
    refs = []
    if task_id and (facts or derived_metrics or data_limits):
        refs.append(task_id)
    for item in [*facts, *derived_metrics]:
        if isinstance(item, dict) and item.get("task_id"):
            refs.append(str(item["task_id"]))
    return _unique(refs)


def _tables_from_pack(*, pack: QuestionEvidencePack, task_id: str = "") -> list[dict[str, Any]]:
    if not pack.rows and not pack.columns:
        return []
    return [
        {
            "table_id": f"table_{_safe_ref(task_id)}_1" if task_id else "table_1",
            "task_id": task_id,
            "columns": list(pack.columns),
            "row_count": len(pack.rows),
            "evidence_ref": f"evidence:{_safe_ref(task_id)}:table:1" if task_id else "evidence:table:1",
        }
    ]


def _evidence_groups(
    *,
    pack: QuestionEvidencePack,
    facts: list[dict[str, Any]],
    derived_metrics: list[dict[str, Any]],
    columns: list[str],
    task_id: str,
) -> list[dict[str, Any]]:
    if not facts and not derived_metrics:
        return []
    group_id = f"group_{_safe_ref(task_id)}" if task_id else "group_1"
    dimension_columns = _dimension_columns_from_facts(facts, columns)
    metric_columns = _metric_columns_from_facts(facts)
    evidence_refs = _unique(
        [
            *[str(fact.get("evidence_ref") or "") for fact in facts],
            *[str(metric.get("evidence_ref") or "") for metric in derived_metrics],
        ]
    )
    group = QuestionEvidenceGroup(
        group_id=group_id,
        purpose=_group_purpose(pack=pack, task_id=task_id),
        source=_group_source(pack=pack, dimension_columns=dimension_columns, metric_columns=metric_columns),
        dimension=_group_dimension(pack=pack, dimension_columns=dimension_columns),
        metrics=_group_metrics(pack=pack, facts=facts, metric_columns=metric_columns),
        time_policy=_time_policy_note(pack.task),
        row_grain=_row_grain(pack=pack, dimension_columns=dimension_columns),
        supports_answer=bool(facts or derived_metrics),
        supports_chart=bool(facts and dimension_columns and metric_columns),
        evidence_refs=evidence_refs,
        facts=[dict(fact) for fact in facts],
        derived_metrics=[dict(metric) for metric in derived_metrics],
    )
    return [group.to_dict()]


def _question_evidence_plan(
    *,
    pack: QuestionEvidencePack,
    groups: list[dict[str, Any]],
    source_pack_id: str,
) -> dict[str, Any]:
    del pack, source_pack_id
    group_ids = [str(group.get("group_id") or "") for group in groups if str(group.get("group_id") or "").strip()]
    return {"plan_id": _plan_id(group_ids), "groups": group_ids}


def _merged_question_evidence_plan(groups: list[dict[str, Any]]) -> dict[str, Any]:
    group_ids = [str(group.get("group_id") or "") for group in groups if str(group.get("group_id") or "").strip()]
    return {"plan_id": _plan_id(group_ids), "groups": group_ids}


def _plan_id(group_ids: list[str]) -> str:
    material = "|".join(group_ids)
    return "qplan_" + hashlib.sha1(material.encode("utf-8")).hexdigest()[:12]


def _dimension_columns_from_facts(facts: list[dict[str, Any]], columns: list[str]) -> list[str]:
    dimension_columns: list[str] = []
    for fact in facts:
        dimension = fact.get("dimension") if isinstance(fact.get("dimension"), dict) else {}
        for column in columns:
            if column in dimension and column not in dimension_columns:
                dimension_columns.append(column)
    return dimension_columns


def _metric_columns_from_facts(facts: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    for fact in facts:
        source_columns = [str(column) for column in fact.get("source_columns") or [] if str(column).strip()]
        if not source_columns:
            continue
        column = source_columns[-1]
        if column not in columns:
            columns.append(column)
    return columns


def _group_source(
    *,
    pack: QuestionEvidencePack,
    dimension_columns: list[str],
    metric_columns: list[str],
) -> dict[str, Any]:
    tables = _unique(
        [
            *[str(item.get("source_table") or "") for item in _lens_dimensions(pack)],
            *[str(item.get("source_table") or "") for item in _lens_metrics(pack)],
        ]
    )
    fields = _unique(
        [
            *[str(item.get("source_field") or item.get("field") or "") for item in _lens_dimensions(pack)],
            *[str(item.get("source_field") or item.get("field") or "") for item in _lens_metrics(pack)],
            *metric_columns,
        ]
    )
    return {"tables": tables, "fields": fields}


def _group_dimension(*, pack: QuestionEvidencePack, dimension_columns: list[str]) -> dict[str, Any]:
    return {
        "role": "dimension",
        "label": _row_grain(pack=pack, dimension_columns=dimension_columns),
        "source_columns": list(dimension_columns),
    }


def _group_metrics(
    *,
    pack: QuestionEvidencePack,
    facts: list[dict[str, Any]],
    metric_columns: list[str],
) -> list[dict[str, Any]]:
    by_column: dict[str, dict[str, Any]] = {}
    for fact in facts:
        source_columns = [str(column) for column in fact.get("source_columns") or [] if str(column).strip()]
        if not source_columns:
            continue
        column = source_columns[-1]
        if column in by_column:
            continue
        label = str(fact.get("label") or _metric_label_for_column(column, pack=pack, numeric_columns=metric_columns, metric_hints=_metric_labels(pack)))
        source_fields = _metric_source_fields_for_column(column, pack)
        by_column[column] = QuestionEvidenceMetricRole(
            role="metric",
            label=label,
            source_column=column,
            source_fields=source_fields,
            unit=str(fact.get("unit") or _unit_for(column)),
        ).to_dict()
    return [by_column[column] for column in metric_columns if column in by_column]


def _metric_source_fields_for_column(column: str, pack: QuestionEvidencePack) -> list[str]:
    fields: list[str] = []
    for metric in _lens_metrics(pack):
        if _column_matches_metric(column, metric):
            for key in ("source_field", "field"):
                value = str(metric.get(key) or "").strip()
                if value:
                    fields.append(value.split(".")[-1])
            for value in metric.get("source_fields") or []:
                text = str(value or "").strip()
                if text:
                    fields.append(text.split(".")[-1])
    return _unique(fields)


def _row_grain(*, pack: QuestionEvidencePack, dimension_columns: list[str]) -> str:
    labels = _dimension_labels_for_columns(pack=pack, dimension_columns=dimension_columns)
    if labels:
        return " / ".join(labels)
    if dimension_columns:
        return " / ".join(dimension_columns)
    return "整体"


def _dimension_labels_for_columns(*, pack: QuestionEvidencePack, dimension_columns: list[str]) -> list[str]:
    labels: list[str] = []
    for column in dimension_columns:
        label = ""
        for dimension in _lens_dimensions(pack):
            candidates = [
                dimension.get("source_column"),
                dimension.get("source_field"),
                dimension.get("field"),
                dimension.get("name"),
            ]
            if any(_normalize_identifier(str(candidate or "").split(".")[-1]) == _normalize_identifier(column) for candidate in candidates):
                label = str(dimension.get("label") or dimension.get("business_label") or "").strip()
                break
        labels.append(label or column)
    return labels


def _group_purpose(*, pack: QuestionEvidencePack, task_id: str) -> str:
    lens = pack.task.business_lens if isinstance(pack.task.business_lens, dict) else {}
    purpose = str(lens.get("evidence_purpose") or lens.get("purpose") or "").strip()
    if purpose:
        return purpose
    domain = str(lens.get("business_domain") or "").lower()
    metric_text = " ".join(
        [
            task_id,
            *[str(metric.get("label") or "") for metric in _lens_metrics(pack)],
            *[str(metric.get("metric_role") or "") for metric in _lens_metrics(pack)],
        ]
    ).lower()
    if "support" in domain or "客服" in metric_text or "工单" in metric_text:
        return "客服压力证据"
    if any(marker in metric_text for marker in ("spend", "cost", "投放", "花费", "成本", "roi", "roas")):
        return "投放效率证据"
    if any(marker in metric_text for marker in ("trend", "趋势", "anomaly", "异常")):
        return "趋势辅助证据"
    return "关键事实"


def _lens_metrics(pack: QuestionEvidencePack) -> list[dict[str, Any]]:
    lens = pack.task.business_lens if isinstance(pack.task.business_lens, dict) else {}
    return [item for item in lens.get("metrics") or [] if isinstance(item, dict)]


def _lens_dimensions(pack: QuestionEvidencePack) -> list[dict[str, Any]]:
    lens = pack.task.business_lens if isinstance(pack.task.business_lens, dict) else {}
    return [item for item in lens.get("dimensions") or [] if isinstance(item, dict)]


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower()).strip("_")


def _ledger_groups(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    groups = [group for group in ledger.get("evidence_groups") or [] if isinstance(group, dict)]
    if groups:
        return groups
    facts = [fact for fact in ledger.get("facts") or [] if isinstance(fact, dict)]
    derived_metrics = [metric for metric in ledger.get("derived_metrics") or [] if isinstance(metric, dict)]
    if not facts and not derived_metrics:
        return []
    grouped: dict[str, dict[str, Any]] = {}
    for fact in facts:
        key = str(fact.get("task_id") or "legacy")
        grouped.setdefault(key, _legacy_group(key))
        grouped[key]["facts"].append(fact)
        ref = str(fact.get("evidence_ref") or "").strip()
        if ref:
            grouped[key]["evidence_refs"].append(ref)
    for metric in derived_metrics:
        key = str(metric.get("task_id") or "legacy")
        grouped.setdefault(key, _legacy_group(key))
        grouped[key]["derived_metrics"].append(metric)
        ref = str(metric.get("evidence_ref") or "").strip()
        if ref:
            grouped[key]["evidence_refs"].append(ref)
    for group in grouped.values():
        group["evidence_refs"] = _unique(group.get("evidence_refs") or [])
        metric_columns = _metric_columns_from_facts(group.get("facts") or [])
        dimension_columns = _dimension_columns_from_facts(group.get("facts") or [], _unique([column for fact in group.get("facts") or [] for column in fact.get("source_columns") or []]))
        group["metrics"] = [
            {
                "role": "metric",
                "label": str(fact.get("label") or "").strip(),
                "source_column": (fact.get("source_columns") or [""])[-1],
                "source_fields": [],
                "unit": str(fact.get("unit") or ""),
            }
            for fact in group.get("facts") or []
            if isinstance(fact, dict) and (fact.get("source_columns") or [])
        ]
        group["dimension"] = {"role": "dimension", "label": " / ".join(dimension_columns) or "对象", "source_columns": dimension_columns}
        group["row_grain"] = " / ".join(dimension_columns) or "对象"
        group["supports_chart"] = bool(metric_columns and dimension_columns)
    return list(grouped.values())


def _legacy_group(key: str) -> dict[str, Any]:
    group_id = f"group_{_safe_ref(key)}"
    return {
        "group_id": group_id,
        "purpose": "业务证据",
        "source": {"tables": [], "fields": []},
        "dimension": {"role": "dimension", "label": "对象", "source_columns": []},
        "metrics": [],
        "time_policy": "",
        "row_grain": "对象",
        "supports_answer": True,
        "supports_chart": False,
        "evidence_refs": [],
        "facts": [],
        "derived_metrics": [],
    }


def _merge_groups(ledgers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ledger in ledgers:
        for group in _ledger_groups(ledger):
            group_id = str(group.get("group_id") or group)
            if group_id in seen:
                continue
            seen.add(group_id)
            merged.append(dict(group))
    return merged


def _merge_items(ledgers: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ledger in ledgers:
        for item in ledger.get(key) or []:
            if not isinstance(item, dict):
                continue
            marker = str(item.get("fact_id") or item.get("metric_id") or item.get("evidence_ref") or item)
            if marker in seen:
                continue
            seen.add(marker)
            merged.append(dict(item))
    return merged


def _merge_tool_calls(ledgers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ledger in ledgers:
        for call in ledger.get("tool_calls") or []:
            if not isinstance(call, dict):
                continue
            marker = "|".join(str(call.get(key) or "") for key in ("tool_name", "purpose", "output_summary", "status"))
            if marker in seen:
                continue
            seen.add(marker)
            merged.append(dict(call))
    return merged


def _merge_tables(ledgers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ledger in ledgers:
        for table in ledger.get("tables") or []:
            if not isinstance(table, dict):
                continue
            marker = str(table.get("table_id") or table.get("evidence_ref") or table)
            if marker in seen:
                continue
            seen.add(marker)
            merged.append(dict(table))
    return merged


def _best_confidence(ledgers: list[dict[str, Any]]) -> str:
    values = [str(ledger.get("confidence") or "low") for ledger in ledgers]
    if values and all(value == "high" for value in values):
        return "high"
    if any(value in {"high", "medium"} for value in values):
        return "medium"
    return "low"


def _merged_ledger_id(*, facts: list[dict[str, Any]], data_limits: list[str]) -> str:
    material = "|".join(
        [
            ",".join(str(fact.get("fact_id") or "") for fact in facts),
            ",".join(data_limits),
        ]
    )
    return "qledger_" + hashlib.sha1(material.encode("utf-8")).hexdigest()[:12]


def _time_policy_note(task: AnalysisTask) -> str:
    lens = task.business_lens if isinstance(task.business_lens, dict) else {}
    note = str(lens.get("time_policy_note") or "").strip()
    if note:
        return note
    raw_text = task.time_range.get("raw_text") if isinstance(task.time_range, dict) else ""
    return str(raw_text or "").strip()


def _safe_tool_call(call: WorkbenchToolCall) -> dict[str, Any]:
    raw = call.to_dict() if isinstance(call, WorkbenchToolCall) else dict(call)
    return {
        "tool_name": _sanitize(raw.get("tool_name")),
        "purpose": _sanitize(raw.get("purpose")),
        "input_summary": _sanitize(raw.get("input_summary")),
        "output_summary": _sanitize(raw.get("output_summary")),
        "status": _sanitize(raw.get("status")),
    }


def _confidence(
    *,
    facts: list[dict[str, Any]],
    derived_metrics: list[dict[str, Any]],
    data_limits: list[str],
    validation: dict[str, Any],
) -> str:
    if not facts and not derived_metrics:
        return "low"
    status = str(validation.get("validation_status") or validation.get("status") or "").lower()
    if status == "validated" and not data_limits:
        return "high"
    return "medium"


def _ledger_id(*, pack: QuestionEvidencePack, facts: list[dict[str, Any]], data_limits: list[str]) -> str:
    material = "|".join(
        [
            pack.task.resolved_question,
            ",".join(pack.columns),
            str(len(pack.rows)),
            str(len(facts)),
            ",".join(data_limits),
        ]
    )
    return "qledger_" + hashlib.sha1(material.encode("utf-8")).hexdigest()[:12]


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if _safe_key(key)}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        return _sanitize_text(value)
    return value


def _sanitize_text(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"(?is)\b(select|with|delete|insert|update|drop|alter)\b.+", "[redacted_query]", text)
    text = re.sub(r"(?i)provider_metadata\s*[=:]?\s*\{?.*?\}?", "[redacted_metadata]", text)
    text = re.sub(r"(?i)\b(api[_-]?key|secret|token|credential)s?\b\s*[:=]?\s*['\"]?[^,，。\s]+", "[redacted_secret]", text)
    text = re.sub(r"(?i)sk-[A-Za-z0-9_-]+", "[redacted_secret]", text)
    text = re.sub(r"(?i)(?:/Users|/private|/tmp|/var|/Volumes)/[^\s,，。;；]+", "[redacted_path]", text)
    text = text.replace("trace.json", "[redacted_trace]")
    return text.strip()


def _safe_key(key: Any) -> bool:
    lowered = str(key or "").lower()
    blocked = ("sql", "trace_path", "provider_metadata", "api_key", "secret", "token", "credential")
    return not any(marker == lowered for marker in blocked)


def _safe_dict(value: Any) -> dict[str, Any]:
    return _sanitize(dict(value)) if isinstance(value, dict) else {}


def _unique(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _safe_ref(value: Any) -> str:
    return re.sub(r"[^\w:.-]+", "_", str(value or "ref")).strip("_") or "ref"


def _is_dimension_value(value: Any) -> bool:
    return value is not None and _to_number(value) is None and str(value).strip() != ""


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _numbers(value: Any) -> list[float]:
    numbers = []
    text = str(value).replace(",", "")
    for match in re.finditer(r"(?<![\d.])(-?\d+(?:\.\d+)?)\s*([万亿]?)(?!\d)", text):
        try:
            number = float(match.group(1))
        except ValueError:
            continue
        unit = match.group(2)
        if unit == "万":
            number *= 10000
        elif unit == "亿":
            number *= 100000000
        numbers.append(number)
    return numbers


def _claim_numbers(value: Any) -> list[float]:
    text = _strip_rank_ordinals(str(value)).replace(",", "")
    numbers: list[float] = []
    for match in re.finditer(r"(?<![\d.])(-?\d+(?:\.\d+)?)\s*([万亿]?)(%)?(?!\s*[天日年月])(?!\d)", text):
        try:
            number = float(match.group(1))
        except ValueError:
            continue
        unit = match.group(2)
        if unit == "万":
            number *= 10000
        elif unit == "亿":
            number *= 100000000
        if match.group(3):
            number /= 100
        numbers.append(number)
    return numbers


def _strip_rank_ordinals(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"(?:排名|排行|名次)\s*第?\s*\d+(?:\.\d+)?\s*(?:名|位)?", " ", value)
    value = re.sub(r"第\s*\d+(?:\.\d+)?\s*(?:名|位)", " ", value)
    value = re.sub(r"\b(?:rank|ranking|ranked|no\.?)\s*#?\s*\d+(?:\.\d+)?\b", " ", value, flags=re.IGNORECASE)
    return value


def _number_close(left: float, right: float) -> bool:
    if abs(left - right) < 0.000001:
        return True
    scale = max(abs(left), abs(right))
    if scale <= 1 and abs(left - right) <= 0.001:
        return True
    return scale >= 1000 and abs(left - right) <= scale * 0.01


def _normalize_text(value: Any) -> str:
    return re.sub(r"[\s,，.。:：;；!！?？()（）_-]+", "", str(value or "").lower())


def _label_matches_claim(label: str, normalized_claim: str) -> bool:
    if label and label in normalized_claim:
        return True
    aliases = [
        {"收入", "销售额", "营收"},
        {"投放成本", "投放花费", "花费", "成本"},
        {"工单数", "问题数", "投诉数"},
    ]
    for group in aliases:
        normalized_group = {_normalize_text(item) for item in group}
        if label in normalized_group and any(alias in normalized_claim for alias in normalized_group):
            return True
    return False


__all__ = [
    "QuestionEvidenceGroup",
    "QuestionDerivedMetric",
    "QuestionEvidenceFact",
    "QuestionEvidenceMetricRole",
    "build_answer_input_ledger",
    "build_chart_safe_table",
    "build_grouped_chart_candidate",
    "build_question_evidence_ledger",
    "empty_question_evidence_ledger",
    "ledger_supported_fact_texts",
    "ledger_supports_claim",
    "merge_question_evidence_ledgers",
    "sanitize_question_evidence_ledger",
]
