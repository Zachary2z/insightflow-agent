from __future__ import annotations

import json
from typing import Any

from workspaces.report_models import ReportRecord, ReportSection


def render_report_markdown(report: ReportRecord) -> str:
    lines: list[str] = [
        f"# {report.title}",
        "",
        "## Report Metadata",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Workspace ID: `{report.workspace_id}`",
        f"- Report type: `{report.report_type}`",
        f"- Status: `{report.status}`",
        f"- Created at: `{report.created_at}`",
        f"- Updated at: `{report.updated_at}`",
        f"- JSON path: `{report.json_path}`",
        f"- Markdown path: `{report.markdown_path}`",
        f"- Artifact directory: `{report.artifact_dir}`",
        "",
        "## Report Goal",
        "",
        report.report_goal or "_No report goal provided._",
        "",
        "## Executive Summary",
        "",
    ]
    lines.extend(_bullet_list(report.executive_summary, "_No executive summary yet._"))
    lines.extend(["", "## Sections", ""])
    if report.sections:
        for section in report.sections:
            lines.extend(_render_section(section))
            lines.append("")
    else:
        lines.extend(["_No report sections yet._", ""])
    lines.extend(
        [
            "## Trace",
            "",
            f"- Trace path: `{report.trace_path}`",
            "",
            "## Provider Metadata Summary",
            "",
        ]
    )
    metadata = _provider_metadata_summary(report)
    if metadata:
        lines.extend(["```json", json.dumps(metadata, ensure_ascii=False, indent=2), "```"])
    else:
        lines.append("_No provider metadata recorded._")
    lines.append("")
    return "\n".join(lines)


def _render_section(section: ReportSection) -> list[str]:
    lines = [
        f"### {section.title}",
        "",
        f"- Section ID: `{section.section_id}`",
        f"- Status: `{section.status}`",
        f"- Purpose: {section.purpose or '_Not specified._'}",
        f"- Question: {section.question or '_Not specified._'}",
        "",
        "#### Summary",
        "",
        section.summary or "_No section summary yet._",
        "",
        "#### SQL",
        "",
    ]
    if section.sql:
        lines.extend(["```sql", section.sql, "```"])
    else:
        lines.append("_No SQL recorded._")
    lines.extend(["", "#### Result Preview", ""])
    lines.extend(_render_preview_table(section))
    lines.extend(["", "#### Visualization Artifacts", ""])
    lines.extend(_bullet_list([f"`{path}`" for path in section.artifact_paths], "_No visualization artifacts recorded._"))
    lines.extend(["", "#### Evidence Notes", ""])
    lines.extend(_bullet_list(section.evidence_notes, "_No evidence notes recorded._"))
    lines.extend(["", "#### Trace Nodes", ""])
    lines.extend(_bullet_list([f"`{node}`" for node in section.trace_nodes], "_No section trace nodes recorded._"))
    if section.error:
        lines.extend(["", "#### Error", "", section.error])
    if section.provider_metadata:
        lines.extend(
            [
                "",
                "#### Provider Metadata",
                "",
                "```json",
                json.dumps(section.provider_metadata, ensure_ascii=False, indent=2),
                "```",
            ]
        )
    return lines


def _render_preview_table(section: ReportSection) -> list[str]:
    columns = section.columns or _columns_from_rows(section.rows_preview)
    if not columns or not section.rows_preview:
        return ["_No result preview recorded._"]
    header = "| " + " | ".join(_escape_table_cell(column) for column in columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    rows = [
        "| "
        + " | ".join(_escape_table_cell(row.get(column, "")) for column in columns)
        + " |"
        for row in section.rows_preview
    ]
    return [header, divider, *rows]


def _columns_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    return list(rows[0].keys())


def _escape_table_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _bullet_list(items: list[str], empty_message: str) -> list[str]:
    if not items:
        return [empty_message]
    return [f"- {item}" for item in items]


def _provider_metadata_summary(report: ReportRecord) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if report.provider_metadata:
        summary["report"] = report.provider_metadata
    section_metadata = {
        section.section_id: section.provider_metadata
        for section in report.sections
        if section.provider_metadata
    }
    if section_metadata:
        summary["sections"] = section_metadata
    return summary
