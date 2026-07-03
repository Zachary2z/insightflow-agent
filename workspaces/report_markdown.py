from __future__ import annotations
from typing import Any

from workspaces.report_models import ReportDocument, ReportEvidenceChart, ReportRecord


def render_report_markdown(report: ReportRecord) -> str:
    document = report.document or _empty_document(report)
    lines: list[str] = [
        f"# {document.title or report.title}",
        "",
        f"生成状态：{_status_label(report.status)}",
        f"生成时间：{_date_label(report.updated_at or report.created_at)}",
        f"时间范围：{document.time_range or '当前工作区可用数据'}",
        f"数据来源：{_join_or_default(document.data_sources, '当前工作区数据')}",
        "",
        "## 开篇摘要",
        "",
        document.opening_summary or "本报告正在生成，暂未形成摘要。",
        "",
        "## 报告正文",
        "",
    ]
    body_sections = [
        section for section in document.sections if not _is_action_section(section.section_id, section.title)
    ]
    if body_sections:
        for section in body_sections:
            lines.extend([f"### {section.title}", "", section.body or "本章节暂未形成正文。"])
            for chart in _charts_for_section(report, section.section_id, section.chart_refs):
                lines.extend(["", *_render_chart(chart)])
            for table in _tables_for_section(report, section.section_id):
                lines.extend(["", f"**{table.get('title', '证据表')}**", ""])
                description = str(table.get("description") or "").strip()
                if description:
                    lines.extend([description, ""])
                lines.extend(_render_markdown_table(table))
            lines.append("")
    else:
        lines.extend(["暂无报告正文。", ""])
    lines.extend(["## 行动建议", ""])
    lines.extend(_numbered_list(document.action_recommendations, "暂无行动建议。"))
    lines.extend(["", "## 数据边界", ""])
    lines.extend(_bullet_list(document.data_boundaries, "暂无数据边界说明。"))
    lines.extend(["", "## 技术附录", ""])
    lines.extend(_render_technical_appendix(report, document))
    lines.append("")
    return "\n".join(lines)


def _empty_document(report: ReportRecord) -> ReportDocument:
    return ReportDocument(
        title=report.title,
        time_range="当前工作区可用数据",
        data_sources=[],
        opening_summary="本报告尚未形成可展示正文。",
    )


def _render_technical_appendix(report: ReportRecord, document: ReportDocument) -> list[str]:
    validation = report.validation
    fact_count = len(report.evidence_pack.facts) if report.evidence_pack else 0
    table_count = len(report.evidence_pack.tables) if report.evidence_pack else 0
    chart_count = len(report.evidence_pack.charts) if report.evidence_pack else 0
    warnings = list(validation.warnings) if validation else []
    unsupported_claims = list(validation.unsupported_claims) if validation else []
    lines = [
        "- 校验状态：" + (validation.status if validation else "未校验"),
        f"- 证据概况：已整理 {fact_count} 个关键事实、{table_count} 张证据表、{chart_count} 个图表或图表意图。",
    ]
    coverage_lines = _coverage_summary_lines(document)
    if coverage_lines:
        lines.extend(["", "### 章节覆盖", *coverage_lines])
    lines.extend(f"- 校验提醒：{warning}" for warning in warnings)
    lines.extend(f"- 待复核表述：{claim}" for claim in unsupported_claims)
    return [
        "<details>",
        "<summary>技术附录</summary>",
        "",
        *lines,
        "",
        "</details>",
    ]


def _coverage_summary_lines(document: ReportDocument) -> list[str]:
    ledger = document.technical_appendix.get("evidence_ledger")
    if not isinstance(ledger, dict):
        return []
    coverages = [
        item
        for item in ledger.get("chapter_coverages", [])
        if isinstance(item, dict)
    ]
    lines = []
    for coverage in coverages:
        title = str(coverage.get("title") or coverage.get("chapter_id") or "未命名章节")
        status = str(coverage.get("coverage") or "missing")
        available = _join_or_default([str(item) for item in coverage.get("available_evidence", [])], "暂无")
        missing = _join_or_default([str(item) for item in coverage.get("missing_evidence", [])], "暂无")
        lines.append(f"- {title}：{status}；可用：{available}；缺口：{missing}")
    return lines


def _tables_for_section(report: ReportRecord, section_id: str) -> list[dict[str, Any]]:
    if not report.evidence_pack:
        return []
    return [
        table.to_dict()
        for table in report.evidence_pack.tables
        if table.source_chapter_id == section_id and table.rows
    ]


def _charts_for_section(
    report: ReportRecord,
    section_id: str,
    chart_refs: list[str],
) -> list[ReportEvidenceChart]:
    if not report.evidence_pack:
        return []
    refs = {ref for ref in chart_refs if ref}
    charts = [
        chart
        for chart in report.evidence_pack.charts
        if chart.source_chapter_id == section_id or chart.chart_id in refs
    ]
    unique: dict[str, ReportEvidenceChart] = {}
    for chart in charts:
        unique[chart.chart_id or chart.title] = chart
    return list(unique.values())


def _render_chart(chart: ReportEvidenceChart) -> list[str]:
    artifact = chart.url or chart.path
    if artifact:
        return [
            f"**{chart.title or '报告图表'}**",
            "",
            f"![{chart.title or '报告图表'}]({artifact})",
            "",
            f"[下载图表]({artifact})",
        ]
    description = chart.description or "建议基于本章节证据生成图表后再用于汇报展示。"
    return [f"**待生成图表：{chart.title or '建议图表'}**", "", description]


def _render_markdown_table(table: dict[str, Any]) -> list[str]:
    columns = [str(column) for column in table.get("columns") or [] if str(column).strip()]
    rows = [row for row in table.get("rows") or [] if isinstance(row, dict)]
    if not columns or not rows:
        return []
    visible_rows = rows[:5]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in visible_rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    if len(rows) > len(visible_rows):
        lines.append(f"（仅展示前 {len(visible_rows)} 行）")
    return lines


def _numbered_list(items: list[str], empty_message: str) -> list[str]:
    if not items:
        return [empty_message]
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)]


def _bullet_list(items: list[str], empty_message: str) -> list[str]:
    if not items:
        return [empty_message]
    return [f"- {item}" for item in items]


def _join_or_default(items: list[str], default: str) -> str:
    visible = [item for item in items if item.strip()]
    return "、".join(visible) if visible else default


def _status_label(status: str) -> str:
    return {
        "completed": "已完成",
        "partial": "部分完成",
        "failed": "失败",
        "running": "生成中",
        "draft": "草稿",
    }.get(status, status)


def _date_label(value: str) -> str:
    return value[:10] if value else "未知"


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


def _compact_text(value: Any) -> str:
    return "".join(str(value or "").lower().split()).replace("_", "").replace("-", "")
