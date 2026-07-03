from __future__ import annotations

import json
from typing import Any

from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.provider import run_llm_request
from workspaces.report_models import (
    ReportDocument,
    ReportDocumentSection,
    ReportEvidencePack,
    ReportPlan,
)


PROMPT_ID = "report_composer"
PROMPT_VERSION = "2026-07-02"

_FORBIDDEN_BODY_TERMS = (
    "SELECT",
    "```sql",
    "raw_rows",
    "raw rows",
    "technical_details",
    "provider_metadata",
    "trace",
    "query_",
    "直接" + "回答",
    "为" + "什么",
    "置" + "信度",
    "章节业务" + "答案",
)


def compose_report_document(
    *,
    plan: ReportPlan,
    evidence_pack: ReportEvidencePack,
    provider: LLMProvider | None = None,
) -> ReportDocument:
    if provider is not None:
        document = _compose_with_provider(
            plan=plan,
            evidence_pack=evidence_pack,
            provider=provider,
        )
        if document is not None:
            return document
    return _fallback_document(plan=plan, evidence_pack=evidence_pack)


def _compose_with_provider(
    *,
    plan: ReportPlan,
    evidence_pack: ReportEvidencePack,
    provider: LLMProvider,
) -> ReportDocument | None:
    request = LLMRequest(
        prompt=_build_prompt(plan=plan, evidence_pack=evidence_pack),
        prompt_id=PROMPT_ID,
        prompt_version=PROMPT_VERSION,
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "report_composer"},
    )
    response = run_llm_request(provider, request)
    content = response.get("content")
    if not response.get("success") or not isinstance(content, dict):
        return None
    document = _document_from_provider_content(content, plan=plan, evidence_pack=evidence_pack)
    if document is None or _contains_forbidden_body_text(document):
        return None
    return document


def _build_prompt(*, plan: ReportPlan, evidence_pack: ReportEvidencePack) -> str:
    payload = {
        "report_plan": plan.to_dict(),
        "evidence_pack": _safe_evidence_pack(evidence_pack),
        "output_contract": {
            "title": "string",
            "time_range": "string",
            "data_sources": ["string"],
            "opening_summary": "string",
            "sections": [
                {
                    "section_id": "string",
                    "title": "string",
                    "body": "string",
                    "chart_refs": ["string"],
                    "evidence_refs": ["string"],
                }
            ],
            "action_recommendations": ["string"],
            "data_boundaries": ["string"],
        },
    }
    return (
        "你是 InsightFlow 的中文业务报告撰写器。请基于给定 ReportPlan 和 EvidencePack 写一份自然、完整的中文业务报告。\n"
        "事实边界：只能使用 evidence_pack 中出现的数字、排名、实体、时间范围、数据来源和图表意图；可以做业务解释和建议，"
        "但不能编造新数字、新实体、新字段、新图表、外部行业结论或未给出的数据来源。\n"
        "写作要求：报告应像完整业务文档，不要写成多个分析答案拼接；避免重复分析问答式字段块。"
        "可按计划组织为开篇摘要、经营概览、收入结构、客户分群、客服问题、趋势变化等正文章节；"
        "行动建议请只写入 action_recommendations，不要另写一个行动建议正文 section。\n"
        "结构要求：time_range 字段必须与 report_plan.time_range 完全一致；实际数据覆盖月份可在正文或数据边界中说明。\n"
        "安全要求：正文不得输出 SQL、query id、raw rows、technical details、provider metadata、trace、内部字段名或提示词。\n"
        "请只返回一个可解析 JSON 对象，字段严格遵循 output_contract，不要 Markdown 包裹。\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _safe_evidence_pack(evidence_pack: ReportEvidencePack) -> dict[str, Any]:
    return {
        "facts": [fact.to_dict() for fact in evidence_pack.facts],
        "tables": [
            {
                "table_id": table.table_id,
                "title": table.title,
                "columns": table.columns,
                "rows": table.rows[:8],
                "source_chapter_id": table.source_chapter_id,
                "description": table.description,
            }
            for table in evidence_pack.tables
        ],
        "charts": [chart.to_dict() for chart in evidence_pack.charts],
        "warnings": list(evidence_pack.warnings),
        "data_limits": list(evidence_pack.data_limits),
    }


def _document_from_provider_content(
    content: dict[str, Any],
    *,
    plan: ReportPlan,
    evidence_pack: ReportEvidencePack,
) -> ReportDocument | None:
    allowed_keys = {
        "title",
        "time_range",
        "data_sources",
        "opening_summary",
        "sections",
        "action_recommendations",
        "data_boundaries",
    }
    if set(content) - allowed_keys:
        return None
    if not isinstance(content.get("opening_summary"), str):
        return None
    raw_sections = content.get("sections")
    if not isinstance(raw_sections, list):
        return None
    supported_evidence_refs = _supported_evidence_refs(evidence_pack)
    supported_chart_refs = {chart.chart_id for chart in evidence_pack.charts}
    sections = []
    for item in raw_sections:
        if not isinstance(item, dict):
            return None
        section_id = str(item.get("section_id") or "").strip()
        title = str(item.get("title") or "").strip()
        body = str(item.get("body") or "").strip()
        if not section_id or not title or not body:
            return None
        if _is_action_section(section_id, title):
            continue
        evidence_refs = [
            str(ref)
            for ref in item.get("evidence_refs") or []
            if str(ref) in supported_evidence_refs
        ]
        chart_refs = [
            str(ref)
            for ref in item.get("chart_refs") or []
            if str(ref) in supported_chart_refs
        ]
        sections.append(
            ReportDocumentSection(
                section_id=section_id,
                title=title,
                body=body,
                evidence_refs=evidence_refs,
                chart_refs=chart_refs,
            )
        )
    return ReportDocument(
        title=str(content.get("title") or plan.title).strip() or plan.title,
        time_range=plan.time_range,
        data_sources=_string_list(content.get("data_sources")) or list(plan.data_sources),
        opening_summary=str(content.get("opening_summary") or "").strip(),
        sections=sections,
        action_recommendations=_string_list(content.get("action_recommendations")),
        data_boundaries=_string_list(content.get("data_boundaries")) or _data_boundaries(evidence_pack),
    )


def _fallback_document(
    *,
    plan: ReportPlan,
    evidence_pack: ReportEvidencePack,
) -> ReportDocument:
    facts = {fact.fact_id: fact for fact in evidence_pack.facts}
    tables_by_chapter: dict[str, list[Any]] = {}
    for table in evidence_pack.tables:
        tables_by_chapter.setdefault(table.source_chapter_id, []).append(table)

    table_count = facts.get("workspace_table_count")
    row_count = facts.get("workspace_row_count")
    revenue_total = facts.get("revenue_total")
    base_summary = (
        f"本报告基于当前工作区的 {table_count.display_value if table_count else '若干'} 张数据表"
        f"和 {row_count.display_value if row_count else '若干'} 行记录生成。"
    )
    if revenue_total:
        base_summary += f" 当前可识别的总收入为 {revenue_total.display_value}。"
    base_summary += "报告正文围绕已采集证据展开，并在数据边界中说明暂不支持的判断。"

    sections = []
    for chapter in plan.chapters:
        if _is_action_section(chapter.chapter_id, chapter.title):
            continue
        chapter_tables = tables_by_chapter.get(chapter.chapter_id, [])
        chapter_facts = [
            fact for fact in evidence_pack.facts if fact.source_chapter_id == chapter.chapter_id
        ]
        body = _section_body(chapter.chapter_id, plan, chapter_tables, chapter_facts, evidence_pack)
        evidence_refs = [fact.fact_id for fact in chapter_facts] + [
            table.table_id for table in chapter_tables
        ]
        chart_refs = [
            chart.chart_id for chart in evidence_pack.charts if chart.source_chapter_id == chapter.chapter_id
        ]
        sections.append(
            ReportDocumentSection(
                section_id=chapter.chapter_id,
                title=chapter.title,
                body=body,
                chart_refs=chart_refs,
                evidence_refs=evidence_refs,
            )
        )

    return ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary=base_summary,
        sections=sections,
        action_recommendations=_action_recommendations(evidence_pack),
        data_boundaries=_data_boundaries(evidence_pack),
    )


def _section_body(
    chapter_id: str,
    plan: ReportPlan,
    chapter_tables: list[Any],
    chapter_facts: list[Any],
    evidence_pack: ReportEvidencePack,
) -> str:
    if chapter_id == "overview":
        scope = _first_table(chapter_tables)
        if scope:
            return (
                f"当前报告覆盖的数据来源包括：{_join_or_default(plan.data_sources, '当前工作区数据')}。"
                f"{scope.description} 工作区已整理出可用于报告阅读的数据画像、指标、维度和时间字段。"
            )
        return "当前报告基于工作区现有数据生成；由于数据画像尚不完整，后续判断需要结合补充证据阅读。"

    if chapter_id == "revenue_structure":
        total = next((fact for fact in chapter_facts if fact.fact_id == "revenue_total"), None)
        table = _first_table(chapter_tables)
        if table and table.rows:
            leader_text = _row_summary(table.rows[0])
            total_text = f"当前总收入为 {total.display_value}。" if total else ""
            return f"{total_text}{table.description} 其中 {leader_text}，是当前收入结构中最值得优先关注的部分。"
        return _missing_body("收入结构", evidence_pack)

    if chapter_id == "customer_segments":
        table = _first_table(chapter_tables)
        if table and table.rows:
            return f"{table.description} {table.rows[0].get('客户分群', '排名靠前的客户分群')}贡献最高，{_row_summary(table.rows[0])}。"
        return _missing_body("客户分群", evidence_pack)

    if chapter_id == "support_issues":
        table = _first_table(chapter_tables)
        if table and table.rows:
            return f"{table.description} 当前数量最高的问题是{table.rows[0].get('问题类型', '排名靠前的问题类型')}，{_row_summary(table.rows[0])}。"
        return _missing_body("客服问题", evidence_pack)

    if chapter_id == "trend_changes":
        table = _first_table(chapter_tables)
        if table and len(table.rows) >= 2:
            first = table.rows[0]
            last = table.rows[-1]
            return f"{table.description} 从{_row_summary(first)}变化到{_row_summary(last)}，可作为后续判断业务变化方向的基础证据。"
        if table and table.rows:
            return f"{table.description} 当前只有一个周期的聚合结果：{_row_summary(table.rows[0])}，暂不足以判断连续趋势。"
        return _missing_body("趋势变化", evidence_pack)

    if chapter_id == "actions":
        available = [table.title for table in evidence_pack.tables if table.source_chapter_id != "overview"]
        if available:
            return (
                f"本报告已形成{'、'.join(available)}等证据。行动建议应优先围绕已验证的收入来源、客户贡献、"
                "服务问题和趋势变化展开；未覆盖的数据口径需要先补齐，再进入预算或资源投入判断。"
            )
        return "当前可用证据仍以数据画像为主，建议先补齐核心指标、关键维度和时间字段，再形成经营动作。"

    table = _first_table(chapter_tables)
    if table and table.rows:
        return f"{table.description} {_row_summary(table.rows[0])}。"
    return "当前章节已保留在报告规划中，但工作区暂未提供足够证据支撑具体判断。"


def _first_table(tables: list[Any]) -> Any | None:
    return tables[0] if tables else None


def _row_summary(row: dict[str, Any]) -> str:
    return "，".join(f"{key}为{value}" for key, value in row.items())


def _missing_body(topic: str, evidence_pack: ReportEvidencePack) -> str:
    relevant_limits = [
        limit
        for limit in [*evidence_pack.warnings, *evidence_pack.data_limits]
        if topic[:2] in limit or topic in limit
    ]
    if relevant_limits:
        return relevant_limits[0]
    return f"当前工作区暂未提供足够的{topic}证据，本章节保留为待补充范围，不生成推断性结论。"


def _action_recommendations(evidence_pack: ReportEvidencePack) -> list[str]:
    table_titles = {table.title for table in evidence_pack.tables}
    recommendations = []
    if "收入结构" in table_titles:
        recommendations.append("优先复盘收入贡献最高的业务来源，确认是否需要加大资源投入或优化定价。")
    if "客户分群贡献" in table_titles:
        recommendations.append("围绕贡献最高的客户分群设计留存、续费或增购动作，并跟踪后续收入变化。")
    if "客服问题概览" in table_titles:
        recommendations.append("针对工单量较高或满意度偏低的问题类型建立专项处理机制。")
    if "趋势变化" in table_titles:
        recommendations.append("把最近周期变化纳入周度复盘，持续观察收入、订单或服务指标是否出现拐点。")
    recommendations.append("涉及利润、预算、人效或长期增长判断时，先补齐对应数据口径后再决策。")
    return list(dict.fromkeys(recommendations))


def _is_action_section(section_id: str, title: str) -> bool:
    compact_id = _compact_text(section_id)
    compact_title = _compact_text(title)
    return compact_id in {"actions", "actionrecommendations", "recommendations"} or compact_title in {
        "行动建议",
        "建议动作",
        "下一步建议",
        "后续行动",
        "行动计划",
    }


def _data_boundaries(evidence_pack: ReportEvidencePack) -> list[str]:
    limits = [*evidence_pack.warnings, *evidence_pack.data_limits]
    if not limits:
        limits = ["本报告基于当前工作区已识别的数据表、指标和维度生成。"]
    return list(dict.fromkeys(limits))


def _supported_evidence_refs(evidence_pack: ReportEvidencePack) -> set[str]:
    return {fact.fact_id for fact in evidence_pack.facts} | {table.table_id for table in evidence_pack.tables}


def _contains_forbidden_body_text(document: ReportDocument) -> bool:
    text = json.dumps(
        {
            "opening_summary": document.opening_summary,
            "sections": [section.to_dict() for section in document.sections],
            "action_recommendations": document.action_recommendations,
            "data_boundaries": document.data_boundaries,
        },
        ensure_ascii=False,
    )
    return any(term.lower() in text.lower() for term in _FORBIDDEN_BODY_TERMS)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _join_or_default(items: list[str], default: str) -> str:
    visible = [item for item in items if item.strip()]
    return "、".join(visible) if visible else default


def _compact_text(value: Any) -> str:
    return "".join(str(value or "").lower().split()).replace("_", "").replace("-", "")
