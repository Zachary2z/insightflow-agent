from __future__ import annotations

import re
from typing import Any

from workspaces.report_models import ReportDocument, ReportEvidencePack, ReportPlan, ReportValidationResult


_RANK_TERMS = ("最高", "第一", "第1", "排名首位", "位居首位", "位居第一", "贡献最高", "排名第一")
_NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s*(?:万元|分钟|个字段|万|元|%|单|行|张|个)?")


def validate_report_document(
    *,
    document: ReportDocument,
    plan: ReportPlan,
    evidence_pack: ReportEvidencePack,
) -> ReportValidationResult:
    warnings: list[str] = []
    unsupported_claims: list[str] = []
    checked_facts: set[str] = set()

    if document.title != plan.title:
        warnings.append(f"报告标题与计划不一致：计划为{plan.title}，正文为{document.title}。")
    if document.time_range != plan.time_range:
        warnings.append(f"报告时间范围与计划不一致：计划为{plan.time_range}，正文为{document.time_range}。")

    supported_refs = _supported_refs(evidence_pack)
    for section in document.sections:
        for ref in [*section.evidence_refs, *section.chart_refs]:
            if ref in supported_refs:
                checked_facts.add(ref)
            else:
                warnings.append(f"未在证据包中找到引用：{ref}")

    allowed_sources = {source for source in plan.data_sources if source.strip()}
    for source in document.data_sources:
        if source.strip() and source not in allowed_sources:
            unsupported_claims.append(f"正文使用了计划和证据外的数据来源：{source}")

    supported_values = _supported_values(evidence_pack)
    for number in _numbers_in_text(_business_text(document)):
        if number not in supported_values:
            unsupported_claims.append(f"正文数字缺少证据支持：{number}")

    unsupported_claims.extend(_rank_conflicts(document, evidence_pack))

    status = "passed" if not warnings and not unsupported_claims else "warning"
    return ReportValidationResult(
        status=status,
        checked_facts=sorted(checked_facts),
        warnings=list(dict.fromkeys(warnings)),
        unsupported_claims=list(dict.fromkeys(unsupported_claims)),
    )


def _business_text(document: ReportDocument) -> str:
    parts = [
        document.title,
        document.time_range,
        *document.data_sources,
        document.opening_summary,
        *[section.title for section in document.sections],
        *[section.body for section in document.sections],
        *document.action_recommendations,
        *document.data_boundaries,
    ]
    return "\n".join(str(part) for part in parts if str(part).strip())


def _supported_refs(evidence_pack: ReportEvidencePack) -> set[str]:
    return (
        {fact.fact_id for fact in evidence_pack.facts}
        | {table.table_id for table in evidence_pack.tables}
        | {chart.chart_id for chart in evidence_pack.charts}
    )


def _supported_values(evidence_pack: ReportEvidencePack) -> set[str]:
    values: set[str] = set()
    for fact in evidence_pack.facts:
        for value in (fact.value, fact.display_value):
            values.update(_value_forms(value))
        values.update(_fact_unit_forms(fact.label, fact.value))
        values.update(_fact_unit_forms(fact.label, fact.display_value))
    for table in evidence_pack.tables:
        for row in table.rows:
            for value in row.values():
                values.update(_value_forms(value))
    return {value for value in values if value}


def _value_forms(value: Any) -> set[str]:
    text = str(value).strip()
    if not text:
        return set()
    forms = {text, text.replace(" ", "")}
    number = _to_number(value)
    if number is not None:
        if float(number).is_integer():
            forms.add(str(int(number)))
        forms.add(str(number))
        if abs(number) >= 10000:
            forms.add(f"{number / 10000:.1f} 万")
            forms.add(f"{number / 10000:.1f}万")
    return forms


def _fact_unit_forms(label: str, value: Any) -> set[str]:
    number = _to_number(value)
    if number is None:
        return set()
    base = str(int(number)) if float(number).is_integer() else str(number)
    compact_label = str(label or "")
    units: list[str] = []
    if "行" in compact_label:
        units.extend(["行", "行记录"])
    if "表" in compact_label:
        units.append("张")
    if "字段" in compact_label:
        units.extend(["个", "个字段"])
    if "工单" in compact_label or "订单" in compact_label:
        units.append("单")
    forms = set()
    for unit in units:
        forms.add(f"{base}{unit}")
        forms.add(f"{base} {unit}")
    return forms


def _numbers_in_text(text: str) -> list[str]:
    numbers = []
    for match in _NUMBER_RE.finditer(text):
        raw = match.group(0).strip()
        compact = raw.replace(" ", "")
        suffix = compact[-1] if compact else ""
        number = _to_number(re.sub(r"[^\d.]", "", compact))
        if number is None:
            continue
        if suffix not in {"万", "元", "%"} and number <= 31:
            continue
        if _near_time_unit(text, match.end()):
            continue
        numbers.append(raw)
    return numbers


def _near_time_unit(text: str, end_index: int) -> bool:
    return text[end_index : end_index + 1] in {"天", "月", "周", "日"}


def _rank_conflicts(document: ReportDocument, evidence_pack: ReportEvidencePack) -> list[str]:
    claims = []
    for table in evidence_pack.tables:
        if not table.rows:
            continue
        sentences = _sentences(_text_for_table_chapter(document, table.source_chapter_id))
        entity_column = _entity_column(table.rows[0])
        if not entity_column:
            continue
        expected = str(table.rows[0].get(entity_column) or "").strip()
        if not expected:
            continue
        competitors = [
            str(row.get(entity_column) or "").strip()
            for row in table.rows[1:]
            if str(row.get(entity_column) or "").strip()
        ]
        for sentence in sentences:
            if not any(term in sentence for term in _RANK_TERMS):
                continue
            for competitor in competitors:
                if competitor in sentence and expected not in sentence:
                    claims.append(
                        f"{table.title}第一名与证据冲突：证据第一名是{expected}，正文写成{competitor}。"
                    )
    return claims


def _text_for_table_chapter(document: ReportDocument, chapter_id: str) -> str:
    parts = []
    for section in document.sections:
        if section.section_id == chapter_id:
            parts.extend([section.title, section.body])
    return "\n".join(parts)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[。！？!?\n]", text) if part.strip()]


def _entity_column(row: dict[str, Any]) -> str:
    for key, value in row.items():
        if _to_number(value) is None and str(value).strip():
            return str(key)
    return ""


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    if text.endswith("%"):
        text = text[:-1]
    if text.endswith("万"):
        text = text[:-1]
    try:
        return float(text)
    except ValueError:
        return None
