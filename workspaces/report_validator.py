from __future__ import annotations

import re
from typing import Any

from workspaces.report_models import ReportDocument, ReportEvidencePack, ReportPlan, ReportValidationResult


_RANK_TERMS = ("最高", "第一", "第1", "排名首位", "位居首位", "位居第一", "贡献最高", "排名第一")
_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9_.])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*"
    r"(?:万元|分钟|个字段|万|元|%|单|行|张|个)?"
)
_ISO_DATE_RE = re.compile(r"\b(\d{4})[-/](\d{1,2})(?:[-/]\d{1,2})?\b")
_CHINESE_DATE_RE = re.compile(
    r"\d{4}\s*年\s*\d{1,2}\s*月(?:\s*至\s*(?:\d{4}\s*年\s*)?\d{1,2}\s*月)?"
)
_DATE_TOKEN_RE = re.compile(
    r"\d{4}\s*[-/]\s*\d{1,2}(?:\s*[-/]\s*\d{1,2})?|"
    r"\d{4}\s*年\s*\d{1,2}\s*月(?:\s*至\s*(?:\d{4}\s*年\s*)?\d{1,2}\s*月)?"
)


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
    supported_time_forms = _supported_time_forms(evidence_pack)
    for number in _numbers_in_text(_business_text(document), supported_time_forms=supported_time_forms):
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
    chapter_total_values = _chapter_total_values(evidence_pack.facts)
    for fact in evidence_pack.facts:
        for value in (fact.value, fact.display_value):
            values.update(_value_forms(value))
        values.update(_fact_unit_forms(fact.label, fact.value))
        values.update(_fact_unit_forms(fact.label, fact.display_value))
    for table in evidence_pack.tables:
        for row in table.rows:
            for column, value in row.items():
                values.update(_value_forms(value))
                values.update(_fact_unit_forms(str(column), value))
        values.update(_table_share_value_forms(table.rows))
        values.update(
            _chapter_total_share_value_forms(
                table.rows,
                chapter_total_values.get(table.source_chapter_id, []),
            )
        )
    for payload in evidence_pack.evidence_payloads:
        values.update(_payload_value_forms(payload))
    return {value for value in values if value}


def _chapter_total_values(facts: list[Any]) -> dict[str, list[float]]:
    totals: dict[str, list[float]] = {}
    for fact in facts:
        descriptor = f"{getattr(fact, 'fact_id', '')} {getattr(fact, 'label', '')}".lower()
        if "total" not in descriptor and "总" not in descriptor and "合计" not in descriptor:
            continue
        numbers = [
            _to_number(getattr(fact, "display_value", "")),
            _to_number(getattr(fact, "value", None)),
        ]
        supported = [number for number in numbers if number is not None and number > 0]
        if supported:
            totals.setdefault(str(getattr(fact, "source_chapter_id", "")), []).extend(supported)
    return totals


def _chapter_total_share_value_forms(
    rows: list[dict[str, Any]],
    total_values: list[float],
) -> set[str]:
    values: set[str] = set()
    if not rows or not total_values:
        return values
    for row in rows:
        for cell in row.values():
            number = _to_number(cell)
            if number is None or number <= 0:
                continue
            for total in total_values:
                if total <= 0 or number > total:
                    continue
                values.update(_percentage_forms(number / total * 100))
    return values


def _payload_value_forms(payload: Any) -> set[str]:
    values: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in {"display_value", "value"}:
                values.update(_value_forms(value))
            values.update(_payload_value_forms(value))
    elif isinstance(payload, list):
        for item in payload:
            values.update(_payload_value_forms(item))
    return values


def _supported_time_forms(evidence_pack: ReportEvidencePack) -> set[str]:
    values: set[str] = set()
    months_by_year: dict[str, set[int]] = {}
    for value in _raw_evidence_values(evidence_pack):
        text = str(value).strip()
        if not text:
            continue
        for match in _ISO_DATE_RE.finditer(text):
            year, raw_month = match.groups()
            month = int(raw_month)
            months_by_year.setdefault(year, set()).add(month)
            values.update(_month_forms(year, month))
            values.add(match.group(0))
    for year, months in months_by_year.items():
        ordered = sorted(months)
        if len(ordered) < 2:
            continue
        start = ordered[0]
        end = ordered[-1]
        values.update(
            {
                f"{year}年{start}月至{end}月",
                f"{year}年{start}月至{year}年{end}月",
                f"{year}-{start:02d}至{year}-{end:02d}",
                f"{year}/{start:02d}至{year}/{end:02d}",
            }
        )
    return {_compact_time_form(value) for value in values if str(value).strip()}


def _raw_evidence_values(evidence_pack: ReportEvidencePack) -> list[Any]:
    values: list[Any] = []
    for fact in evidence_pack.facts:
        values.extend([fact.value, fact.display_value])
    for table in evidence_pack.tables:
        for row in table.rows:
            values.extend(row.values())
    return values


def _month_forms(year: str, month: int) -> set[str]:
    return {
        f"{year}-{month:02d}",
        f"{year}/{month:02d}",
        f"{year}年{month}月",
        f"{month}月",
    }


def _table_share_value_forms(rows: list[dict[str, Any]]) -> set[str]:
    values: set[str] = set()
    if len(rows) < 2:
        return values
    columns = sorted({str(key) for row in rows for key in row})
    for column in columns:
        numeric_values = [_to_number(row.get(column)) for row in rows]
        if any(value is None for value in numeric_values):
            continue
        total = sum(value or 0 for value in numeric_values)
        if total <= 0:
            continue
        for value in numeric_values:
            if value is None:
                continue
            share = value / total * 100
            values.update(_percentage_forms(share))
    return values


def _percentage_forms(value: float) -> set[str]:
    forms = {
        f"{value:.0f}%",
        f"{value:.1f}%",
        f"{value:.2f}%",
    }
    return {form for form in forms if not form.startswith("-")}


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
        if "万" in text:
            base = str(int(number)) if float(number).is_integer() else str(number)
            forms.update({f"{base} 万", f"{base}万", f"{base}万元"})
        if abs(number) >= 10000:
            forms.add(f"{number / 10000:.1f} 万")
            forms.add(f"{number / 10000:.1f}万")
            forms.add(f"{number / 10000:.1f}万元")
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
    if _looks_like_currency_label(compact_label):
        forms.update(_currency_unit_forms(number, value))
    return forms


def _looks_like_currency_label(label: str) -> bool:
    return any(
        token in label
        for token in ("收入", "营收", "销售额", "销售", "金额", "成本", "花费", "支出", "投放")
    )


def _currency_unit_forms(number: float, raw_value: Any) -> set[str]:
    forms: set[str] = set()
    raw_text = str(raw_value or "")
    base = str(int(number)) if float(number).is_integer() else str(number)
    if "万" in raw_text:
        forms.update({f"{base} 万", f"{base}万", f"{base}万元"})
        return forms
    forms.update({f"{base}元", f"{base} 元"})
    if abs(number) >= 1000:
        rounded_integer = int(round(number))
        forms.update({f"{rounded_integer}元", f"{rounded_integer} 元", f"{rounded_integer:,}元"})
        for precision in (1, 2):
            compact = f"{number / 10000:.{precision}f}"
            forms.update({f"{compact} 万", f"{compact}万", f"{compact}万元"})
    return forms


def _numbers_in_text(text: str, *, supported_time_forms: set[str] | None = None) -> list[str]:
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
        if _supported_date_context(text, match, supported_time_forms or set()):
            continue
        if _near_time_unit(text, match.end()):
            continue
        numbers.append(raw)
    return numbers


def _supported_date_context(text: str, match: re.Match[str], supported_time_forms: set[str]) -> bool:
    if not supported_time_forms:
        return False
    window_start = max(0, match.start() - 8)
    window_end = min(len(text), match.end() + 24)
    window = text[window_start:window_end]
    for token_match in _DATE_TOKEN_RE.finditer(window):
        start = window_start + token_match.start()
        end = window_start + token_match.end()
        if start <= match.start() and end >= match.end():
            token = _compact_time_form(token_match.group(0))
            return token in supported_time_forms
    date_match = _CHINESE_DATE_RE.match(text[match.start() : match.start() + 18])
    if date_match:
        return _compact_time_form(date_match.group(0)) in supported_time_forms
    return False


def _compact_time_form(value: str) -> str:
    return "".join(str(value or "").split()).replace("－", "-").replace("—", "-")


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
