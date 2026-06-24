from __future__ import annotations

import json
from typing import Any

from workspaces.report_models import ReportRecord, ReportSection


def render_report_markdown(report: ReportRecord) -> str:
    lines: list[str] = [
        f"# {report.title}",
        "",
        "## Report Goal",
        "",
        report.report_goal or "_No report goal provided._",
        "",
        "## Status And Progress",
        "",
        f"- Status: `{report.status}`",
        f"- Progress: {_progress_summary(report)}",
        "",
        "## Executive Summary",
        "",
    ]
    lines.extend(_bullet_list(report.executive_summary, "_No executive summary yet._"))
    lines.extend(["", "## Business Sections", ""])
    if report.sections:
        for section in report.sections:
            lines.extend(_render_business_section(section))
            lines.append("")
    else:
        lines.extend(["_No report sections yet._", ""])
    lines.extend(["## Technical Appendix", ""])
    lines.extend(_render_report_appendix(report))
    lines.append("")
    return "\n".join(lines)


def _render_business_section(section: ReportSection) -> list[str]:
    lines = [
        f"### {section.title}",
        "",
        f"- Status: `{section.status}`",
        "",
        section.summary or "_No section summary yet._",
    ]
    lines.extend(["", "#### Evidence Notes", ""])
    lines.extend(_bullet_list(section.evidence_notes, "_No evidence notes recorded._"))
    lines.extend(["", "#### Chart Artifacts", ""])
    lines.extend(
        _bullet_list(
            [f"`{path}`" for path in section.artifact_paths],
            "_No chart artifacts recorded._",
        )
    )
    if section.error:
        lines.extend(["", "#### Error", "", section.error])
    return lines


def _render_report_appendix(report: ReportRecord) -> list[str]:
    lines = [
        "<details>",
        "<summary>Report Metadata</summary>",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Workspace ID: `{report.workspace_id}`",
        f"- Report type: `{report.report_type}`",
        f"- Created at: `{report.created_at}`",
        f"- Updated at: `{report.updated_at}`",
        f"- JSON path: `{report.json_path}`",
        f"- Markdown path: `{report.markdown_path}`",
        f"- Trace path: `{report.trace_path}`",
        f"- Artifact directory: `{report.artifact_dir}`",
    ]
    if report.provider_metadata:
        lines.extend(
            [
                "",
                "```json",
                json.dumps(report.provider_metadata, ensure_ascii=False, indent=2),
                "```",
            ]
        )
    lines.extend(["", "</details>", ""])
    if report.sections:
        for section in report.sections:
            lines.extend(_render_section_appendix(section))
            lines.append("")
    else:
        lines.append("_No technical section details recorded._")
    return lines


def _render_section_appendix(section: ReportSection) -> list[str]:
    details = _section_technical_details(section)
    lines = [
        "<details>",
        f"<summary>{section.title}</summary>",
        "",
        f"- Section ID: `{section.section_id}`",
        f"- Status: `{section.status}`",
        f"- Purpose: {details.get('purpose') or section.purpose or '_Not specified._'}",
        f"- Internal question: {details.get('internal_question') or section.question or '_Not specified._'}",
        "",
        "#### SQL",
        "",
    ]
    sql = details.get("sql") or section.sql
    if sql:
        lines.extend(["```sql", str(sql), "```"])
    else:
        lines.append("_No SQL recorded._")
    lines.extend(["", "#### Result Preview", ""])
    lines.extend(_render_preview_table(section, details))
    lines.extend(["", "#### Provider Metadata", ""])
    provider_metadata = details.get("provider_metadata") or section.provider_metadata
    if provider_metadata:
        lines.extend(["```json", json.dumps(provider_metadata, ensure_ascii=False, indent=2), "```"])
    else:
        lines.append("_No provider metadata recorded._")
    lines.extend(["", "#### Trace Nodes", ""])
    trace_nodes = details.get("trace_nodes") or section.trace_nodes
    lines.extend(_bullet_list([f"`{node}`" for node in trace_nodes], "_No section trace nodes recorded._"))
    if section.error or details.get("error"):
        lines.extend(["", "#### Error", "", str(details.get("error") or section.error)])
    lines.extend(["", "</details>"])
    return lines


def _section_technical_details(section: ReportSection) -> dict[str, Any]:
    details = dict(section.technical_details or {})
    details.setdefault("internal_question", section.question)
    details.setdefault("purpose", section.purpose)
    details.setdefault("sql", section.sql)
    details.setdefault("columns", section.columns)
    details.setdefault("rows_preview", section.rows_preview)
    details.setdefault("provider_metadata", section.provider_metadata)
    details.setdefault("trace_nodes", section.trace_nodes)
    if section.error:
        details.setdefault("error", section.error)
    return details


def _render_preview_table(section: ReportSection, details: dict[str, Any] | None = None) -> list[str]:
    details = details or {}
    rows_preview = list(details.get("rows_preview") or section.rows_preview)
    columns = list(details.get("columns") or section.columns or _columns_from_rows(rows_preview))
    if not columns or not rows_preview:
        return ["_No result preview recorded._"]
    header = "| " + " | ".join(_escape_table_cell(column) for column in columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    rows = [
        "| "
        + " | ".join(_escape_table_cell(row.get(column, "")) for column in columns)
        + " |"
        for row in rows_preview
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


def _progress_summary(report: ReportRecord) -> str:
    total = len(report.sections)
    completed = sum(1 for section in report.sections if section.status == "completed")
    failed = sum(1 for section in report.sections if section.status == "failed")
    running = sum(1 for section in report.sections if section.status == "running")
    if not total:
        return "0/0 sections completed"
    details = [f"{completed}/{total} sections completed"]
    if failed:
        details.append(f"{failed} failed")
    if running or report.status == "running":
        details.append("still running")
    return ", ".join(details)
