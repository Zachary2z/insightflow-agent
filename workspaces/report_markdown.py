from __future__ import annotations

import json
from typing import Any

from workspaces.report_models import ReportDocument, ReportRecord


def render_report_markdown(report: ReportRecord) -> str:
    document = report.document or _empty_document(report)
    lines: list[str] = [
        f"# {document.title or report.title}",
        "",
        f"生成状态：{report.status}",
        f"报告目标：{report.report_goal}",
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
    if document.sections:
        for section in document.sections:
            lines.extend([f"### {section.title}", "", section.body or "本章节暂未形成正文。"])
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
    appendix: dict[str, Any] = {
        "report_id": report.report_id,
        "workspace_id": report.workspace_id,
        "report_type": report.report_type,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
        "validation": report.validation.to_dict() if report.validation else {},
    }
    if document.technical_appendix:
        appendix.update(document.technical_appendix)
    return [
        "<details>",
        "<summary>技术细节</summary>",
        "",
        "```json",
        json.dumps(appendix, ensure_ascii=False, indent=2),
        "```",
        "",
        "</details>",
    ]


def _tables_for_section(report: ReportRecord, section_id: str) -> list[dict[str, Any]]:
    if not report.evidence_pack:
        return []
    return [
        table.to_dict()
        for table in report.evidence_pack.tables
        if table.source_chapter_id == section_id and table.rows
    ]


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
