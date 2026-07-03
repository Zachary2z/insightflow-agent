from __future__ import annotations

import re
from typing import Any

from workspaces.report_models import (
    EvidenceLedger,
    ReportChapterCoverage,
    ReportEvidencePack,
    ReportEvidenceTable,
    ReportLedgerItem,
    ReportPlan,
)


def build_evidence_ledger(
    *,
    plan: ReportPlan,
    evidence_pack: ReportEvidencePack,
) -> EvidenceLedger:
    facts = _fact_items(evidence_pack)
    derived = _derived_items(evidence_pack)
    coverages = CoverageChecker(plan=plan, evidence_pack=evidence_pack).check()
    boundaries = _data_boundaries(evidence_pack, coverages)
    ledger = EvidenceLedger(
        facts=facts,
        derived_metrics=derived,
        chapter_coverages=coverages,
        recommendation_context=_recommendation_context(coverages),
        data_boundaries=boundaries,
        technical_refs=_technical_refs(evidence_pack),
    )
    evidence_pack.ledger = ledger
    return ledger


class CoverageChecker:
    def __init__(self, *, plan: ReportPlan, evidence_pack: ReportEvidencePack) -> None:
        self.plan = plan
        self.evidence_pack = evidence_pack

    def check(self) -> list[ReportChapterCoverage]:
        return [self._coverage_for_chapter(chapter.chapter_id, chapter.title) for chapter in self.plan.chapters]

    def _coverage_for_chapter(self, chapter_id: str, title: str) -> ReportChapterCoverage:
        tables = [table for table in self.evidence_pack.tables if table.source_chapter_id == chapter_id and table.rows]
        facts = [fact for fact in self.evidence_pack.facts if fact.source_chapter_id == chapter_id]
        limits = _limits_for_chapter(chapter_id, self.evidence_pack)
        available = [fact.label for fact in facts if fact.label] + [table.title for table in tables if table.title]

        if chapter_id == "overview":
            return ReportChapterCoverage(
                chapter_id=chapter_id,
                title=title,
                coverage="strong" if available else "missing",
                available_evidence=available,
                missing_evidence=[] if available else ["工作区画像和语义层概览"],
                allowed_claims=["可以说明数据表、字段规模、可用指标和维度"] if available else [],
                blocked_claims=[] if available else ["不能说明工作区数据概况"],
                data_boundaries=limits,
            )

        if not available:
            return ReportChapterCoverage(
                chapter_id=chapter_id,
                title=title,
                coverage="missing",
                available_evidence=[],
                missing_evidence=_minimum_evidence(chapter_id),
                allowed_claims=[],
                blocked_claims=_blocked_claims(chapter_id),
                data_boundaries=limits,
            )

        optional_missing = _optional_missing(chapter_id, tables=tables, facts=facts)
        coverage = "partial" if optional_missing or limits else "strong"
        return ReportChapterCoverage(
            chapter_id=chapter_id,
            title=title,
            coverage=coverage,
            available_evidence=list(dict.fromkeys(available + _available_derived_claims(chapter_id, tables))),
            missing_evidence=optional_missing,
            allowed_claims=_allowed_claims(chapter_id),
            blocked_claims=_blocked_claims(chapter_id, missing_evidence=optional_missing, limits=limits) if coverage != "strong" else [],
            data_boundaries=limits + optional_missing,
        )


def _fact_items(evidence_pack: ReportEvidencePack) -> list[ReportLedgerItem]:
    items: list[ReportLedgerItem] = []
    for fact in evidence_pack.facts:
        evidence_id = f"ledger_fact_{fact.fact_id}"
        items.append(
            ReportLedgerItem(
                evidence_id=evidence_id,
                label=fact.label,
                value=fact.value,
                display_value=fact.display_value,
                unit=fact.unit,
                chapter_id=fact.source_chapter_id,
                source_evidence=fact.evidence_ref,
                formula=fact.evidence_ref,
                source_values=[fact.display_value],
                claim_phrases=_claim_phrases(fact.label, fact.display_value),
            )
        )
    for table in evidence_pack.tables:
        items.extend(_row_fact_items(table))
    return _unique_items(items)


def _row_fact_items(table: ReportEvidenceTable) -> list[ReportLedgerItem]:
    items: list[ReportLedgerItem] = []
    if not table.rows:
        return items
    entity_col = _entity_column(table)
    metric_cols = _metric_columns(table)
    if not entity_col or not metric_cols:
        return items
    for metric_col in metric_cols:
        for row in table.rows:
            entity = str(row.get(entity_col) or "").strip()
            value = row.get(metric_col)
            if not entity or _to_number(value) is None:
                continue
            display = str(value)
            label = f"{entity}{metric_col}"
            items.append(
                ReportLedgerItem(
                    evidence_id=f"ledger_fact_{table.table_id}_{_slug(entity)}_{_slug(metric_col)}",
                    label=label,
                    value=_to_number(value),
                    display_value=display,
                    unit=_unit_for_label(metric_col),
                    chapter_id=table.source_chapter_id,
                    source_table=table.table_id,
                    source_evidence=table.evidence_ref,
                    formula=f"{table.title}.{metric_col}",
                    source_values=[f"{entity}{metric_col}{display}"],
                    claim_phrases=_claim_phrases(label, display, entity=entity),
                )
            )
    return items


def _derived_items(evidence_pack: ReportEvidencePack) -> list[ReportLedgerItem]:
    items: list[ReportLedgerItem] = []
    totals_by_chapter = _chapter_totals(evidence_pack)
    for table in evidence_pack.tables:
        items.extend(_table_derived_items(table, totals_by_chapter=totals_by_chapter))
    for payload in evidence_pack.evidence_payloads:
        items.extend(_payload_derived_items(payload))
    return _unique_items(items)


def _table_derived_items(
    table: ReportEvidenceTable,
    *,
    totals_by_chapter: dict[str, tuple[float, str]],
) -> list[ReportLedgerItem]:
    if not table.rows:
        return []
    entity_col = _entity_column(table)
    metric_col = _contribution_metric_column(table)
    if not entity_col or not metric_col:
        return []
    rows = [
        (str(row.get(entity_col) or "").strip(), _to_number(row.get(metric_col)), str(row.get(metric_col) or ""))
        for row in table.rows
    ]
    rows = [(entity, value, display) for entity, value, display in rows if entity and value is not None]
    if not rows:
        return []

    items: list[ReportLedgerItem] = []
    table_total = sum(value for _entity, value, _display in rows)
    total, total_display = totals_by_chapter.get(
        table.source_chapter_id,
        (table_total, _format_metric_value(table_total, metric_col)),
    )
    if total > 0:
        items.append(
            ReportLedgerItem(
                evidence_id=f"ledger_metric_{table.table_id}_{_slug(metric_col)}_total",
                label=f"{table.title}{metric_col}合计",
                value=table_total,
                display_value=_format_metric_value(table_total, metric_col),
                unit=_unit_for_label(metric_col),
                chapter_id=table.source_chapter_id,
                source_table=table.table_id,
                source_evidence=table.evidence_ref,
                formula=f"SUM({metric_col})",
                source_values=[f"{entity}{metric_col}{display}" for entity, _value, display in rows],
                claim_phrases=_claim_phrases(f"{metric_col}合计", _format_metric_value(table_total, metric_col)),
            )
        )
        for index, (entity, value, display) in enumerate(rows, start=1):
            share = value / total * 100
            share_display = _format_percent(share)
            items.append(
                ReportLedgerItem(
                    evidence_id=f"ledger_metric_{table.table_id}_{_slug(entity)}_{_slug(metric_col)}_share",
                    label=f"{entity}{metric_col}占比",
                    value=round(share, 4),
                    display_value=share_display,
                    unit="percentage",
                    chapter_id=table.source_chapter_id,
                    source_table=table.table_id,
                    source_evidence=table.evidence_ref,
                    formula=f"{display} / {total_display}",
                    source_values=[f"{entity}{metric_col}{display}", f"{metric_col}合计{total_display}"],
                    claim_phrases=_claim_phrases(f"{entity}{metric_col}占比", share_display, entity=entity),
                )
            )
            items.append(
                ReportLedgerItem(
                    evidence_id=f"ledger_metric_{table.table_id}_{_slug(entity)}_{_slug(metric_col)}_rank",
                    label=f"{entity}{metric_col}排名",
                    value=index,
                    display_value=f"排名第{index}",
                    unit="rank",
                    chapter_id=table.source_chapter_id,
                    source_table=table.table_id,
                    source_evidence=table.evidence_ref,
                    formula=f"RANK({metric_col} DESC)",
                    source_values=[f"{entity}{metric_col}{display}"],
                    claim_phrases=[f"{entity}排名第{index}", f"{entity}位居第{index}", f"{entity}位居{metric_col}第一" if index == 1 else ""],
                )
            )
        if len(rows) >= 2:
            combined_value = rows[0][1] + rows[1][1]
            combined_share = combined_value / total * 100
            combined_display = _format_percent(combined_share)
            items.append(
                ReportLedgerItem(
                    evidence_id=f"ledger_metric_{table.table_id}_top2_{_slug(metric_col)}_combined_share",
                    label=f"{rows[0][0]}和{rows[1][0]}合计占比",
                    value=round(combined_share, 4),
                    display_value=combined_display,
                    unit="percentage",
                    chapter_id=table.source_chapter_id,
                    source_table=table.table_id,
                    source_evidence=table.evidence_ref,
                    formula=f"({rows[0][2]} + {rows[1][2]}) / {total_display}",
                    source_values=[f"{rows[0][0]}{metric_col}{rows[0][2]}", f"{rows[1][0]}{metric_col}{rows[1][2]}"],
                    claim_phrases=[
                        f"{rows[0][0]}和{rows[1][0]}合计贡献{combined_display}",
                        f"{rows[0][0]}、{rows[1][0]}合计占比{combined_display}",
                    ],
                )
            )
        items.extend(_trend_items(table, rows, entity_col, metric_col))
    return items


def _chapter_totals(evidence_pack: ReportEvidencePack) -> dict[str, tuple[float, str]]:
    totals: dict[str, tuple[float, str]] = {}
    for fact in evidence_pack.facts:
        descriptor = f"{fact.fact_id} {fact.label}"
        if not any(token in descriptor for token in ("total", "总", "合计")):
            continue
        value = _to_number(fact.display_value)
        if value is None or value <= 0:
            value = _to_number(fact.value)
        if value is not None and value > 0:
            totals[fact.source_chapter_id] = (value, fact.display_value or _format_metric_value(value, fact.label))
    return totals


def _trend_items(
    table: ReportEvidenceTable,
    rows: list[tuple[str, float, str]],
    entity_col: str,
    metric_col: str,
) -> list[ReportLedgerItem]:
    if table.source_chapter_id != "trend_changes" or len(rows) < 2:
        return []
    first_entity, first_value, first_display = rows[0]
    last_entity, last_value, last_display = rows[-1]
    items: list[ReportLedgerItem] = [
        ReportLedgerItem(
            evidence_id=f"ledger_metric_{table.table_id}_data_coverage",
            label="数据覆盖范围",
            value=f"{first_entity}至{last_entity}",
            display_value=f"{first_entity}至{last_entity}",
            unit="period",
            chapter_id=table.source_chapter_id,
            source_table=table.table_id,
            source_evidence=table.evidence_ref,
            formula=f"MIN/MAX({entity_col})",
            source_values=[entity for entity, _value, _display in rows],
            claim_phrases=[f"数据覆盖{first_entity}至{last_entity}", f"证据覆盖{first_entity}至{last_entity}"],
        )
    ]
    if first_value:
        change = (last_value - first_value) / abs(first_value) * 100
        display = _format_percent(change)
        items.append(
            ReportLedgerItem(
                evidence_id=f"ledger_metric_{table.table_id}_{_slug(metric_col)}_period_change",
                label=f"{last_entity}较{first_entity}{metric_col}环比变化",
                value=round(change, 4),
                display_value=display,
                unit="percentage",
                chapter_id=table.source_chapter_id,
                source_table=table.table_id,
                source_evidence=table.evidence_ref,
                formula=f"({last_display} - {first_display}) / {first_display}",
                source_values=[f"{first_entity}{metric_col}{first_display}", f"{last_entity}{metric_col}{last_display}"],
                claim_phrases=[f"{last_entity}较{first_entity}环比增长{display}", f"{last_entity}较{first_entity}变化{display}"],
            )
        )
    highest = max(rows, key=lambda item: item[1])
    lowest = min(rows, key=lambda item: item[1])
    for kind, row in (("最高周期", highest), ("最低周期", lowest)):
        items.append(
            ReportLedgerItem(
                evidence_id=f"ledger_metric_{table.table_id}_{_slug(metric_col)}_{_slug(kind)}",
                label=f"{metric_col}{kind}",
                value=row[1],
                display_value=f"{row[0]} {row[2]}",
                unit=_unit_for_label(metric_col),
                chapter_id=table.source_chapter_id,
                source_table=table.table_id,
                source_evidence=table.evidence_ref,
                formula=f"{kind}({metric_col})",
                source_values=[f"{entity}{metric_col}{display}" for entity, _value, display in rows],
                claim_phrases=[f"{row[0]}是{metric_col}{kind}", f"{row[0]}为{kind}"],
            )
        )
    return items


def _payload_derived_items(payload: dict[str, Any]) -> list[ReportLedgerItem]:
    items: list[ReportLedgerItem] = []
    evidence_ref = str(payload.get("evidence_ref") or "")
    for metric in payload.get("derived_metrics") or []:
        if not isinstance(metric, dict):
            continue
        metric_id = str(metric.get("metric_id") or "derived_metric")
        label = str(metric.get("label") or metric_id)
        for index, value in enumerate(metric.get("values") or []):
            if not isinstance(value, dict):
                continue
            display = str(value.get("display_value") or "")
            if not display or display == "-":
                continue
            items.append(
                ReportLedgerItem(
                    evidence_id=f"ledger_metric_payload_{_slug(evidence_ref)}_{_slug(metric_id)}_{index}",
                    label=label,
                    value=value.get("value"),
                    display_value=display,
                    unit=str(metric.get("unit") or ""),
                    source_evidence=evidence_ref,
                    formula=str(metric.get("formula") or ""),
                    source_values=[display],
                    claim_phrases=_claim_phrases(label, display),
                )
            )
    return items


def _entity_column(table: ReportEvidenceTable) -> str:
    for column in table.columns:
        if any(_to_number(row.get(column)) is None and str(row.get(column) or "").strip() for row in table.rows):
            return column
    return table.columns[0] if table.columns else ""


def _contribution_metric_column(table: ReportEvidenceTable) -> str:
    columns = _metric_columns(table)
    if not columns:
        return ""
    return min(columns, key=_contribution_metric_sort_key)


def _contribution_metric_sort_key(column: str) -> tuple[int, int, str]:
    role = _metric_role(column)
    if role == "additive":
        return (0, _metric_priority(column), column)
    if role == "count":
        return (1, _metric_priority(column), column)
    if role == "unknown":
        return (2, _metric_priority(column), column)
    return (3, _metric_priority(column), column)


def _metric_role(label: str) -> str:
    normalized = _normalize_metric_label(label)
    if _contains_any(normalized, ("roi", "roas", "投产比", "回报率", "转化率", "率", "占比", "比例", "ratio", "rate")):
        return "rate"
    if _contains_any(normalized, ("响应时长", "处理时长", "等待时长", "时长", "分钟", "minute", "duration", "latency")):
        return "duration"
    if _contains_any(normalized, ("满意度", "评分", "客单价", "均价", "平均", "avg", "average", "score")):
        return "average"
    if _contains_any(normalized, ("收入", "销售额", "营收", "gmv", "成交额", "流水", "金额", "成本", "利润", "花费", "支出", "revenue", "sales", "amount", "cost", "profit", "spend")):
        return "additive"
    if _contains_any(normalized, ("订单数", "工单数", "工单量", "数量", "次数", "人数", "客户数", "count", "orders", "tickets")):
        return "count"
    return "unknown"


def _metric_priority(label: str) -> int:
    normalized = _normalize_metric_label(label)
    priority_tokens = (
        ("收入", "销售额", "营收", "revenue", "sales", "gmv"),
        ("成交额", "流水", "金额", "amount"),
        ("订单数", "工单数", "工单量", "数量", "count", "orders", "tickets"),
        ("利润", "profit"),
        ("成本", "花费", "支出", "cost", "spend"),
    )
    for index, tokens in enumerate(priority_tokens):
        if _contains_any(normalized, tokens):
            return index
    return len(priority_tokens)


def _normalize_metric_label(label: str) -> str:
    return re.sub(r"\s+", "", str(label or "").lower())


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token.lower() in text for token in tokens)


def _metric_columns(table: ReportEvidenceTable) -> list[str]:
    return [
        column
        for column in table.columns
        if any(_to_number(row.get(column)) is not None for row in table.rows)
    ]


def _claim_phrases(label: str, display: str, *, entity: str = "") -> list[str]:
    phrases = [f"{label}{display}", f"{label}为{display}", f"{label}是{display}"]
    if entity:
        phrases.extend([f"{entity}{display}", f"{entity}为{display}"])
    return [phrase for phrase in dict.fromkeys(phrases) if phrase.strip()]


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    multiplier = 10000.0 if "万" in text else 1.0
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0)) * multiplier


def _format_metric_value(value: float, label: str) -> str:
    if _unit_for_label(label) == "currency" and abs(value) >= 10000:
        return f"{value / 10000:.1f} 万"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _format_percent(value: float) -> str:
    return f"{value:.1f}%"


def _unit_for_label(label: str) -> str:
    if any(token in label for token in ("收入", "销售额", "金额", "成本", "利润", "花费")):
        return "currency"
    if any(token in label for token in ("占比", "率", "环比", "同比")):
        return "percentage"
    return "number"


def _limits_for_chapter(chapter_id: str, evidence_pack: ReportEvidencePack) -> list[str]:
    tokens = {
        "revenue_structure": ("收入", "利润", "成本", "ROI", "投放"),
        "customer_segments": ("客户", "分群", "客群"),
        "support_issues": ("客服", "工单", "满意度", "响应"),
        "trend_changes": ("趋势", "时间", "周期", "最近"),
    }.get(chapter_id, ())
    if not tokens:
        return []
    return [
        item
        for item in [*evidence_pack.warnings, *evidence_pack.data_limits]
        if any(token in item for token in tokens)
    ]


def _minimum_evidence(chapter_id: str) -> list[str]:
    return {
        "revenue_structure": ["总收入", "分组收入", "占比", "top/bottom"],
        "trend_changes": ["时间序列", "环比变化", "最高/最低周期", "数据覆盖范围"],
        "support_issues": ["工单量", "满意度", "响应时长", "问题类型排行"],
        "customer_segments": ["分群收入或订单", "占比", "top/bottom"],
    }.get(chapter_id, ["章节所需结构化证据"])


def _optional_missing(
    chapter_id: str,
    *,
    tables: list[ReportEvidenceTable],
    facts: list[Any],
) -> list[str]:
    if chapter_id == "revenue_structure":
        return _revenue_optional_missing(tables=tables, facts=facts)
    return []


def _revenue_optional_missing(*, tables: list[ReportEvidenceTable], facts: list[Any]) -> list[str]:
    text = _evidence_field_text(tables=tables, facts=facts)
    missing: list[str] = []
    if not _contains_any(text, ("成本", "花费", "支出", "投放", "cost", "spend", "expense")):
        missing.append("成本")
    if not _contains_any(text, ("利润", "毛利", "profit")):
        missing.append("利润")
    if not _contains_any(text, ("roi", "roas", "投产比", "回报率")):
        missing.append("ROI")
    if not missing:
        return []
    return [f"缺少{'、'.join(missing)}字段，不能完整判断投入产出和盈利质量。"]


def _evidence_field_text(*, tables: list[ReportEvidenceTable], facts: list[Any]) -> str:
    parts: list[str] = []
    for fact in facts:
        parts.extend([str(getattr(fact, "fact_id", "")), str(getattr(fact, "label", "")), str(getattr(fact, "unit", ""))])
    for table in tables:
        parts.extend([table.table_id, table.title, table.description])
        parts.extend(table.columns)
    return _normalize_metric_label(" ".join(part for part in parts if part))


def _available_derived_claims(chapter_id: str, tables: list[ReportEvidenceTable]) -> list[str]:
    if not tables:
        return []
    if chapter_id == "trend_changes":
        return ["数据覆盖范围", "环比变化", "最高周期", "最低周期"]
    return ["总计", "占比", "合计占比", "排名", "top/bottom"]


def _allowed_claims(chapter_id: str) -> list[str]:
    return {
        "revenue_structure": ["可以说明总收入、分组收入、占比、合计占比、排名和集中度"],
        "trend_changes": ["可以说明周期覆盖、环比变化、最高周期和最低周期"],
        "support_issues": ["可以说明问题类型排行、工单量、满意度和响应时长"],
        "customer_segments": ["可以说明客户分群贡献、占比和排名"],
        "actions": ["可以基于已验证证据提出行动建议和补数建议"],
    }.get(chapter_id, ["可以说明已采集证据覆盖的事实"])


def _blocked_claims(
    chapter_id: str,
    *,
    missing_evidence: list[str] | None = None,
    limits: list[str] | None = None,
) -> list[str]:
    if missing_evidence:
        if chapter_id == "revenue_structure":
            missing_text = "、".join(_missing_metric_labels(missing_evidence))
            return [f"不能声称{missing_text}相关结论已经验证"] if missing_text else []
        return [f"不能声称缺失证据已经验证：{item}" for item in missing_evidence]
    if limits:
        return [f"不能越过数据边界声称已验证：{item}" for item in limits[:3]]
    return {
        "revenue_structure": ["不能声称利润率、ROI、成本效率或转化率已经验证"],
        "trend_changes": ["不能声称未覆盖周期、同比或预测结果已经验证"],
        "support_issues": ["不能声称未采集的客服问题、损失金额或流失率已经验证"],
        "customer_segments": ["不能声称未采集的复购率、留存率或客户生命周期价值已经验证"],
        "actions": ["不能把建议目标写成已经发生的历史事实"],
    }.get(chapter_id, ["不能声称账本外事实已经验证"])


def _missing_metric_labels(items: list[str]) -> list[str]:
    labels: list[str] = []
    for item in items:
        for label in ("成本", "利润", "ROI", "转化率"):
            if label in item and label not in labels:
                labels.append(label)
    return labels


def _data_boundaries(
    evidence_pack: ReportEvidencePack,
    coverages: list[ReportChapterCoverage],
) -> list[str]:
    boundaries = [*evidence_pack.warnings, *evidence_pack.data_limits]
    for coverage in coverages:
        boundaries.extend(coverage.data_boundaries)
    return list(dict.fromkeys(item for item in boundaries if item))


def _recommendation_context(coverages: list[ReportChapterCoverage]) -> list[dict[str, Any]]:
    return [
        {
            "chapter_id": coverage.chapter_id,
            "coverage": coverage.coverage,
            "basis": coverage.available_evidence[:5],
            "blocked_claims": coverage.blocked_claims,
        }
        for coverage in coverages
        if coverage.chapter_id != "overview"
    ]


def _technical_refs(evidence_pack: ReportEvidencePack) -> list[dict[str, Any]]:
    refs = []
    for table in evidence_pack.tables:
        if table.evidence_ref:
            refs.append(
                {
                    "evidence_ref": table.evidence_ref,
                    "table_id": table.table_id,
                    "chapter_id": table.source_chapter_id,
                }
            )
    return refs


def _unique_items(items: list[ReportLedgerItem]) -> list[ReportLedgerItem]:
    unique: dict[str, ReportLedgerItem] = {}
    for item in items:
        if item.evidence_id and item.evidence_id not in unique:
            item.claim_phrases = [phrase for phrase in dict.fromkeys(item.claim_phrases) if phrase]
            unique[item.evidence_id] = item
    return list(unique.values())


def _slug(value: Any) -> str:
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", str(value or "").strip()).strip("_")
    return text or "item"
