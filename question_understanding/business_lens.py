from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from question_understanding.task_contract import compact_text


@dataclass
class BusinessLensMetric:
    label: str
    source_table: str = ""
    source_field: str = ""
    time_field: str = ""
    metric_role: str = "metric"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BusinessLensDimension:
    label: str
    source_table: str = ""
    source_field: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BusinessLens:
    business_domain: str = "general_business_analysis"
    metrics: list[BusinessLensMetric] = field(default_factory=list)
    dimensions: list[BusinessLensDimension] = field(default_factory=list)
    time_range: dict[str, Any] = field(default_factory=dict)
    time_policy_note: str = ""
    needs_clarification: bool = False
    clarification_question: str = ""
    data_limits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["metrics"] = [metric.to_dict() for metric in self.metrics]
        data["dimensions"] = [dimension.to_dict() for dimension in self.dimensions]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BusinessLens":
        return cls(
            business_domain=str(data.get("business_domain") or "general_business_analysis"),
            metrics=[
                BusinessLensMetric(
                    label=str(item.get("label") or ""),
                    source_table=str(item.get("source_table") or ""),
                    source_field=str(item.get("source_field") or ""),
                    time_field=str(item.get("time_field") or ""),
                    metric_role=str(item.get("metric_role") or "metric"),
                )
                for item in data.get("metrics", [])
                if isinstance(item, dict)
            ],
            dimensions=[
                BusinessLensDimension(
                    label=str(item.get("label") or ""),
                    source_table=str(item.get("source_table") or ""),
                    source_field=str(item.get("source_field") or ""),
                )
                for item in data.get("dimensions", [])
                if isinstance(item, dict)
            ],
            time_range=dict(data.get("time_range") or {}),
            time_policy_note=str(data.get("time_policy_note") or ""),
            needs_clarification=bool(data.get("needs_clarification")),
            clarification_question=str(data.get("clarification_question") or ""),
            data_limits=[str(item) for item in data.get("data_limits") or [] if str(item).strip()],
        )


ROLE_ALIASES = {
    "revenue_like": ("revenue", "income", "sales", "gmv", "销售额", "收入", "营收", "成交额", "成交金额", "营业额"),
    "spend_like": ("spend", "cost", "ad spend", "marketing spend", "投放花费", "投放金额", "投放成本", "广告费", "花费"),
    "support_like": ("support", "ticket", "satisfaction", "nps", "score", "客服", "工单", "满意度", "评分", "解决时长", "响应时长"),
    "margin_like": ("margin", "gross margin", "margin rate", "毛利", "毛利率", "利润率"),
    "customer_registration_count": ("新增客户", "新客户", "注册客户", "客户新增", "注册", "new customer", "signup"),
}

ROLE_MEANINGS = {
    "revenue_like": {"revenue_like"},
    "spend_like": {"spend_like"},
    "support_like": {"rating_like", "duration_like", "ticket_count_like"},
    "margin_like": {"margin_like", "margin_rate_like", "gross_margin_like", "profit_like"},
}


def build_business_lens(
    question: str,
    *,
    analysis_task: dict[str, Any] | None = None,
    workspace_context: dict[str, Any] | None = None,
) -> BusinessLens:
    task = dict(analysis_task or {})
    context = workspace_context or {}
    metrics_context = [dict(item) for item in context.get("semantic_metrics") or [] if isinstance(item, dict)]
    dimensions_context = [dict(item) for item in context.get("semantic_dimensions") or [] if isinstance(item, dict)]
    time_fields_context = [dict(item) for item in context.get("semantic_time_fields") or [] if isinstance(item, dict)]

    if not any((metrics_context, dimensions_context, time_fields_context)):
        return BusinessLens(
            business_domain=_business_domain([], task.get("dimensions") or []),
            metrics=[BusinessLensMetric(label=str(item)) for item in task.get("metrics") or [] if str(item).strip()],
            dimensions=[
                BusinessLensDimension(label=str(item)) for item in task.get("dimensions") or [] if str(item).strip()
            ],
            time_range=dict(task.get("time_range") or {}),
        )

    requested_roles = _requested_metric_roles(question, task.get("metrics") or [])
    dimension_table_hints = _dimension_table_hints(task.get("dimensions") or [], dimensions_context)
    data_limits: list[str] = []
    metrics = _ground_metrics(
        question,
        requested_roles=requested_roles,
        semantic_metrics=metrics_context,
        semantic_time_fields=time_fields_context,
        workspace_context=context,
        preferred_tables=dimension_table_hints,
        data_limits=data_limits,
    )
    dimensions = _ground_dimensions(
        task.get("dimensions") or [],
        semantic_dimensions=dimensions_context,
        metric_tables=[metric.source_table for metric in metrics],
    )
    time_range = _business_lens_time_range(
        task.get("time_range"),
        metrics,
        time_fields_context,
        context,
        data_limits=data_limits,
    )
    needs_clarification = False
    clarification_question = ""

    if not metrics:
        needs_clarification = True
        clarification_question = "你更关注收入、投放效率、客服体验还是综合表现？请补充要分析的指标口径。"
        data_limits.append("当前问题没有足够明确的业务指标，Business Lens 无法安全落到可计算字段。")
    elif any(not metric.source_field for metric in metrics):
        needs_clarification = True
        clarification_question = "当前数据没有足够证据确认要分析的指标字段，请补充更明确的业务指标。"
    elif any(not metric.time_field for metric in metrics):
        needs_clarification = True
        clarification_question = "当前数据无法为部分指标确认业务时间字段，请补充希望按哪个业务日期统计。"
    elif not task.get("time_range") and not time_range:
        needs_clarification = True
        clarification_question = "当前数据画像没有足够的时间范围信息，不能安全默认完整数据范围。请补充要分析的时间范围。"

    return BusinessLens(
        business_domain=_business_domain([metric.metric_role for metric in metrics], task.get("dimensions") or []),
        metrics=metrics,
        dimensions=dimensions,
        time_range=time_range,
        time_policy_note=_time_policy_note(
            metrics,
            time_fields_context,
            explicit=bool(task.get("time_range")),
            time_range=time_range,
        ),
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
        data_limits=_unique_text(data_limits),
    )


def _requested_metric_roles(question: str, metric_labels: list[Any]) -> list[str]:
    labels = [str(item) for item in metric_labels if str(item).strip()]
    roles: list[str] = [
        role
        for role, aliases in ROLE_ALIASES.items()
        if _contains_any(question, aliases)
    ]
    if roles:
        for label in labels:
            if not _label_is_mentioned(question, label):
                continue
            role = _role_for_label(label)
            if role:
                roles.append(role)
        return _unique_text([role for role in roles if role])

    for role, aliases in ROLE_ALIASES.items():
        if any(_matches_alias(label, aliases) for label in labels):
            roles.append(role)
    if not roles:
        for label in labels:
            roles.append(_role_for_label(label))
    return _unique_text([role for role in roles if role])


def _ground_metrics(
    question: str,
    *,
    requested_roles: list[str],
    semantic_metrics: list[dict[str, Any]],
    semantic_time_fields: list[dict[str, Any]],
    workspace_context: dict[str, Any],
    preferred_tables: list[str],
    data_limits: list[str],
) -> list[BusinessLensMetric]:
    metrics: list[BusinessLensMetric] = []
    for role in requested_roles:
        if role == "customer_registration_count":
            metrics.append(_customer_registration_metric(semantic_time_fields, workspace_context, data_limits))
            continue
        candidate = _best_metric_for_role(question, role, semantic_metrics, preferred_tables=preferred_tables)
        if not candidate:
            label = _default_label_for_role(role)
            if preferred_tables:
                data_limits.append(f"当前语义层没有找到与所选维度同源的{label}字段。")
            else:
                data_limits.append(f"当前语义层没有找到可计算的{label}字段。")
            metrics.append(BusinessLensMetric(label=label, metric_role=role))
            continue
        table, field = _table_field(candidate)
        metrics.append(
            BusinessLensMetric(
                label=str(candidate.get("label") or _default_label_for_role(role)),
                source_table=table,
                source_field=field,
                time_field=_time_field_name(_best_time_field(table, role, semantic_time_fields)),
                metric_role=role,
            )
        )
    return _dedupe_metrics(metrics)


def _best_metric_for_role(
    question: str,
    role: str,
    metrics: list[dict[str, Any]],
    *,
    preferred_tables: list[str],
) -> dict[str, Any] | None:
    scored: list[tuple[int, dict[str, Any]]] = []
    for metric in metrics:
        score = 0
        meanings = {str(item) for item in metric.get("business_meaning_candidates") or []}
        if meanings & ROLE_MEANINGS.get(role, set()):
            score += 5
        if role == "spend_like" and "cost_like" in meanings and _contains_any(question, ROLE_ALIASES["spend_like"]):
            score += 2
        if role == "support_like" and _contains_any(_item_text(metric), ROLE_ALIASES["support_like"]):
            score += 3
        if _contains_any(_item_text(metric), ROLE_ALIASES.get(role, ())):
            score += 4
        if _contains_any(question, _role_specific_item_candidates(metric)):
            score += 3
        if score > 0:
            table, _field = _table_field(metric)
            if preferred_tables and table in preferred_tables:
                score += 8
            scored.append((score, metric))
    if not scored:
        return None
    scored = sorted(scored, key=lambda item: item[0], reverse=True)
    if preferred_tables and not any(_table_field(item[1])[0] in preferred_tables for item in scored):
        return None
    return scored[0][1]


def _label_is_mentioned(question: str, label: str) -> bool:
    compact_question = compact_text(question)
    compact_label = compact_text(label)
    return bool(compact_label and compact_label in compact_question)


def _role_specific_item_candidates(item: dict[str, Any]) -> tuple[str, ...]:
    generic_aliases = {"金额", "数值", "数量", "次数", "单量", "件数", "amount", "value", "count", "number"}
    candidates = []
    for candidate in _item_candidates(item):
        text = str(candidate).strip()
        if not text or compact_text(text) in {compact_text(alias) for alias in generic_aliases}:
            continue
        candidates.append(text)
    return tuple(candidates)


def _customer_registration_metric(
    time_fields: list[dict[str, Any]],
    workspace_context: dict[str, Any],
    data_limits: list[str],
) -> BusinessLensMetric:
    registration_time = _best_customer_registration_time(time_fields)
    table = str(registration_time.get("table") or _split_qualified(str(registration_time.get("field") or ""))[0])
    id_field = _id_field_for_table(table, workspace_context)
    if not registration_time or not table:
        data_limits.append("当前数据没有找到客户注册日期，不能把新增客户口径安全绑定到订单日期。")
    if not id_field:
        data_limits.append("当前数据没有找到客户标识字段，无法计算新增客户数量。")
    return BusinessLensMetric(
        label="新增客户",
        source_table=table,
        source_field=id_field,
        time_field=_time_field_name(registration_time),
        metric_role="customer_registration_count",
    )


def _ground_dimensions(
    labels: list[Any],
    *,
    semantic_dimensions: list[dict[str, Any]],
    metric_tables: list[str],
) -> list[BusinessLensDimension]:
    dimensions: list[BusinessLensDimension] = []
    for label in [str(item) for item in labels if str(item).strip()]:
        candidates = [item for item in semantic_dimensions if _dimension_matches(label, item)]
        if metric_tables:
            same_table = [item for item in candidates if _table_field(item)[0] in metric_tables]
            candidates = same_table or candidates
        for item in candidates[: max(1, len(set(metric_tables)))]:
            table, field = _table_field(item)
            dimensions.append(BusinessLensDimension(label=str(item.get("label") or label), source_table=table, source_field=field))
    return _dedupe_dimensions(dimensions)


def _dimension_table_hints(labels: list[Any], semantic_dimensions: list[dict[str, Any]]) -> list[str]:
    tables: list[str] = []
    for label in [str(item) for item in labels if str(item).strip()]:
        for item in semantic_dimensions:
            if not _dimension_matches(label, item):
                continue
            table, _field = _table_field(item)
            if table and table not in tables:
                tables.append(table)
    return tables


def _business_lens_time_range(
    task_time_range: Any,
    metrics: list[BusinessLensMetric],
    time_fields: list[dict[str, Any]],
    workspace_context: dict[str, Any],
    *,
    data_limits: list[str],
) -> dict[str, Any]:
    if isinstance(task_time_range, dict) and task_time_range:
        return dict(task_time_range)
    metric_fields = [metric for metric in metrics if metric.time_field and metric.source_table]
    if not metric_fields:
        return {}
    ranges = _profile_time_ranges(workspace_context)
    field_ranges = []
    for metric in metric_fields:
        qualified = f"{metric.source_table}.{metric.time_field}"
        value_range = ranges.get(qualified) or ranges.get(metric.time_field) or {}
        start = _normalize_date(value_range.get("min"))
        end = _normalize_date(value_range.get("max"))
        field_ranges.append(
            {
                "metric_label": metric.label,
                "field": qualified,
                "start": start,
                "end": end,
            }
        )
    unsafe_ranges = [item for item in field_ranges if not (item.get("start") and item.get("end"))]
    if unsafe_ranges:
        fields = "、".join(str(item.get("field") or "") for item in unsafe_ranges if item.get("field"))
        data_limits.append(
            f"当前数据画像没有 {fields or '相关时间字段'} 的完整 min/max 时间范围，不能安全默认完整数据范围。"
        )
        return {}
    if len(field_ranges) == 1:
        item = field_ranges[0]
        return {
            "type": "full_data_range",
            "raw_text": f"完整数据时间范围：{item['start']} 至 {item['end']}",
            "start": item["start"],
            "end": item["end"],
            "field": item["field"],
            "reason": "用户未指定时间范围，默认使用该指标业务表的完整可用时间范围。",
        }
    return {
        "type": "full_data_range",
        "raw_text": "各指标完整数据范围",
        "fields": field_ranges,
        "reason": "用户未指定时间范围，默认使用每个指标所在业务表的完整可用时间范围。",
    }


def _time_policy_note(
    metrics: list[BusinessLensMetric],
    time_fields: list[dict[str, Any]],
    *,
    explicit: bool,
    time_range: dict[str, Any],
) -> str:
    if not metrics:
        return ""
    labels_by_field = {_time_field_name(item): str(item.get("label") or item.get("name") or _time_field_name(item)) for item in time_fields}
    parts = []
    for metric in metrics:
        if not metric.time_field:
            continue
        parts.append(f"{metric.label}按{labels_by_field.get(metric.time_field, metric.time_field)}统计")
    if not parts:
        return ""
    if explicit:
        suffix = "时间范围使用用户指定范围。"
    elif time_range:
        suffix = "用户未指定时间范围，默认使用各指标各自完整数据范围。"
    else:
        suffix = "当前数据画像缺少完整起止日期，请补充时间范围。"
    return "，".join(parts) + "；" + suffix


def _business_domain(metric_roles: list[str], dimension_labels: list[Any]) -> str:
    if "support_like" in metric_roles:
        return "support_operations"
    if "customer_registration_count" in metric_roles:
        return "customer_acquisition"
    if "spend_like" in metric_roles and "revenue_like" in metric_roles:
        return "channel_performance"
    if "margin_like" in metric_roles:
        return "store_operations"
    if any(compact_text(item) == "渠道" for item in dimension_labels):
        return "channel_performance"
    if "revenue_like" in metric_roles:
        return "revenue_analysis"
    return "general_business_analysis"


def _best_time_field(table: str, role: str, time_fields: list[dict[str, Any]]) -> dict[str, Any]:
    same_table = [field for field in time_fields if field.get("enabled") is not False and _table_field(field)[0] == table]
    if not same_table:
        return {}
    role_terms = {
        "revenue_like": ("order", "sale", "business", "下单", "订单", "销售", "营业"),
        "spend_like": ("spend", "marketing", "投放", "广告"),
        "support_like": ("ticket", "support", "case", "工单", "客服"),
        "margin_like": ("order", "sale", "business", "下单", "订单", "销售", "营业"),
        "customer_registration_count": ("register", "registration", "signup", "created", "注册", "新增"),
    }.get(role, ())
    scored = []
    for field in same_table:
        score = 1
        if _contains_any(_item_text(field), role_terms):
            score += 5
        scored.append((score, field))
    return sorted(scored, key=lambda item: item[0], reverse=True)[0][1]


def _best_customer_registration_time(time_fields: list[dict[str, Any]]) -> dict[str, Any]:
    scored = []
    for field in time_fields:
        if field.get("enabled") is False:
            continue
        score = 0
        table, _field = _table_field(field)
        if _contains_any(table, ("customer", "client", "user", "客户", "用户")):
            score += 3
        if _contains_any(_item_text(field), ROLE_ALIASES["customer_registration_count"]):
            score += 6
        if score:
            scored.append((score, field))
    return sorted(scored, key=lambda item: item[0], reverse=True)[0][1] if scored else {}


def _id_field_for_table(table: str, workspace_context: dict[str, Any]) -> str:
    for table_item in workspace_context.get("tables") or []:
        if not isinstance(table_item, dict) or str(table_item.get("table_name") or "") != table:
            continue
        for column in table_item.get("columns") or []:
            if not isinstance(column, dict):
                continue
            name = str(column.get("name") or "")
            roles = column.get("roles") if isinstance(column.get("roles"), dict) else {}
            if roles.get("id") or compact_text(name).endswith("id") or "编号" in name:
                return name
    return ""


def _profile_time_ranges(workspace_context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ranges: dict[str, dict[str, Any]] = {}
    for table in workspace_context.get("tables") or []:
        if not isinstance(table, dict):
            continue
        table_name = str(table.get("table_name") or "")
        for column in table.get("columns") or []:
            if not isinstance(column, dict):
                continue
            value_range = column.get("value_range") if isinstance(column.get("value_range"), dict) else {}
            if not value_range:
                continue
            column_name = str(column.get("name") or "")
            ranges[column_name] = value_range
            if table_name and column_name:
                ranges[f"{table_name}.{column_name}"] = value_range
    return ranges


def _role_for_label(label: str) -> str:
    for role, aliases in ROLE_ALIASES.items():
        if _matches_alias(label, aliases):
            return role
    return "metric"


def _dimension_matches(label: str, item: dict[str, Any]) -> bool:
    return _matches_alias(label, _item_candidates(item))


def _table_field(item: dict[str, Any]) -> tuple[str, str]:
    table = str(item.get("table") or "").strip()
    field = str(item.get("field") or "").strip()
    if field and "." in field:
        split_table, split_field = _split_qualified(field)
        table = table or split_table
        field = split_field
    return table, field or str(item.get("name") or "").strip()


def _split_qualified(value: str) -> tuple[str, str]:
    if "." not in value:
        return "", value
    table, field = value.split(".", 1)
    return table, field


def _time_field_name(item: dict[str, Any]) -> str:
    return _table_field(item)[1] if item else ""


def _item_candidates(item: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(candidate)
        for candidate in [
            item.get("name", ""),
            item.get("label", ""),
            item.get("field", ""),
            *list(item.get("aliases") or []),
        ]
        if str(candidate).strip()
    )


def _item_text(item: dict[str, Any]) -> str:
    return " ".join([*_item_candidates(item), *[str(value) for value in item.get("business_meaning_candidates") or []]])


def _contains_any(text: Any, aliases: tuple[str, ...]) -> bool:
    compact = compact_text(text)
    return any(compact_text(alias) and compact_text(alias) in compact for alias in aliases)


def _matches_alias(text: Any, aliases: tuple[str, ...]) -> bool:
    compact = compact_text(text)
    return any(compact and compact_text(alias) and (compact == compact_text(alias) or compact_text(alias) in compact) for alias in aliases)


def _default_label_for_role(role: str) -> str:
    return {
        "revenue_like": "收入",
        "spend_like": "投放花费",
        "support_like": "满意度",
        "margin_like": "毛利率",
        "customer_registration_count": "新增客户",
    }.get(role, role)


def _normalize_date(value: Any) -> str:
    text = str(value or "").strip()
    match = re.match(r"(\d{4})[-/](\d{1,2})(?:[-/](\d{1,2}))?", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}" if day else f"{year}-{int(month):02d}"
    return text


def _dedupe_metrics(metrics: list[BusinessLensMetric]) -> list[BusinessLensMetric]:
    seen: set[tuple[str, str, str]] = set()
    deduped = []
    for metric in metrics:
        key = (metric.metric_role, metric.source_table, metric.source_field)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(metric)
    return deduped


def _dedupe_dimensions(dimensions: list[BusinessLensDimension]) -> list[BusinessLensDimension]:
    seen: set[tuple[str, str, str]] = set()
    deduped = []
    for dimension in dimensions:
        key = (dimension.label, dimension.source_table, dimension.source_field)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(dimension)
    return deduped


def _unique_text(values: list[str]) -> list[str]:
    result = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


__all__ = [
    "BusinessLens",
    "BusinessLensDimension",
    "BusinessLensMetric",
    "build_business_lens",
]
