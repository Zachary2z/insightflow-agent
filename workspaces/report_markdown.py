from __future__ import annotations

import json
from typing import Any

from workspaces.report_models import ReportRecord, ReportSection


def render_report_markdown(report: ReportRecord) -> str:
    chinese = _report_is_chinese(report)
    headings = _headings(chinese)
    lines: list[str] = [
        f"# {report.title}",
        "",
        f"## {headings['goal']}",
        "",
        report.report_goal or "_No report goal provided._",
        "",
        f"## {headings['summary']}",
        "",
    ]
    lines.extend(_bullet_list(report.executive_summary, "_No executive summary yet._"))
    lines.extend(["", f"## {headings['findings']}", ""])
    lines.extend(_bullet_list(report.key_findings, "_No key findings yet._"))
    lines.extend(["", f"## {headings['actions']}", ""])
    lines.extend(_bullet_list(report.action_priorities, "_No action priorities yet._"))
    lines.extend(["", f"## {headings['charts']}", ""])
    lines.extend(_render_chart_and_evidence(report, empty_message="_No chart or evidence summary yet._"))
    lines.extend(["", f"## {headings['limits']}", ""])
    lines.extend(_bullet_list(report.risks_and_limits, "_No risks or limits recorded._"))
    lines.extend(["", f"## {headings['sections']}", ""])
    if report.sections:
        for section in report.sections:
            lines.extend(_render_business_section(section))
            lines.append("")
    else:
        lines.extend(["_No report sections yet._", ""])
    lines.extend([f"## {headings['appendix']}", ""])
    lines.extend(_render_report_appendix(report))
    lines.append("")
    return "\n".join(lines)


def _render_business_section(section: ReportSection) -> list[str]:
    answer = section.business_answer or {}
    lines = [
        f"### {section.title}",
        "",
        f"- Status: `{section.status}`",
        "",
        "#### 结论",
        "",
        str(answer.get("headline") or "_No headline recorded._"),
        "",
        "#### 直接回答",
        "",
        str(answer.get("direct_answer") or "_No direct answer recorded._"),
        "",
        "#### 为什么",
        "",
        str(answer.get("why") or "_No reasoning recorded._"),
    ]
    lines.extend(["", "#### 关键证据", ""])
    lines.extend(_bullet_list(_text_list(answer.get("evidence_bullets")), "_No evidence bullets recorded._"))
    lines.extend(["", "#### 建议动作", ""])
    lines.extend(_bullet_list(_text_list(answer.get("recommendations")), "_No recommendations recorded._"))
    lines.extend(["", "#### 限制说明", ""])
    lines.extend(_bullet_list(_text_list(answer.get("caveats")), "_No caveats recorded._"))
    lines.extend(["", "#### 置信度", "", str(answer.get("confidence") or "medium")])
    lines.extend(["", "#### 图表与证据", ""])
    lines.extend(_render_section_artifacts(section))
    if section.error:
        lines.extend(["", "#### Error", "", section.error])
    return lines


def _render_chart_and_evidence(report: ReportRecord, *, empty_message: str) -> list[str]:
    lines: list[str] = []
    rendered_paths: set[str] = set()
    for section in report.sections:
        for artifact in section.business_artifacts or []:
            path_or_url = str(artifact.get("url") or artifact.get("path") or "").strip()
            title = str(artifact.get("title") or section.title or "报告图表").strip()
            if not path_or_url or path_or_url in rendered_paths:
                continue
            rendered_paths.add(path_or_url)
            lines.append(f"![{_escape_image_alt(title)}]({path_or_url})")
            lines.extend(_artifact_caption_lines(artifact, section_title=section.title))
    if report.chart_and_evidence:
        lines.extend(_bullet_list(report.chart_and_evidence, empty_message))
    return lines or [empty_message]


def _render_section_artifacts(section: ReportSection) -> list[str]:
    artifacts = section.business_artifacts or [
        {"type": "chart", "path": path, "title": section.title}
        for path in section.artifact_paths
    ]
    if not artifacts:
        return ["_No chart artifacts recorded._"]
    lines: list[str] = []
    for artifact in artifacts:
        path_or_url = str(artifact.get("url") or artifact.get("path") or "").strip()
        title = str(artifact.get("title") or section.title or "报告图表").strip()
        if path_or_url:
            lines.append(f"![{_escape_image_alt(title)}]({path_or_url})")
        lines.extend(_artifact_caption_lines(artifact, section_title=section.title))
    return lines


def _artifact_caption_lines(artifact: dict[str, Any], *, section_title: str) -> list[str]:
    title = str(artifact.get("title") or section_title or "报告图表").strip()
    unit = str(artifact.get("unit") or "").strip()
    annotation = str(artifact.get("business_annotation") or "").strip()
    lines = [f"- 图表标题：{title}"]
    if unit:
        lines.append(f"- 单位：{unit}")
    if annotation:
        lines.append(f"- 业务注释：{annotation}")
    path_or_url = str(artifact.get("url") or artifact.get("path") or "").strip()
    if path_or_url:
        lines.append(f"- 图表链接：{path_or_url}")
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


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


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


def _report_is_chinese(report: ReportRecord) -> bool:
    text = "\n".join(
        [
            report.report_goal,
            *report.executive_summary,
            *report.key_findings,
            *report.action_priorities,
            *report.risks_and_limits,
        ]
    )
    if "english" in text.lower():
        return False
    return any("\u4e00" <= char <= "\u9fff" for char in text) or not text.strip()


def _headings(chinese: bool) -> dict[str, str]:
    if chinese:
        return {
            "goal": "报告目标",
            "summary": "管理层摘要",
            "findings": "关键发现",
            "actions": "行动优先级",
            "charts": "图表与证据",
            "limits": "风险与边界",
            "sections": "章节业务答案",
            "appendix": "技术附录",
        }
    return {
        "goal": "Report Goal",
        "summary": "Executive Summary",
        "findings": "Key Findings",
        "actions": "Action Priorities",
        "charts": "Chart And Evidence",
        "limits": "Risks And Limits",
        "sections": "Business Sections",
        "appendix": "Technical Appendix",
    }


def _escape_image_alt(value: str) -> str:
    return value.replace("[", "(").replace("]", ")").replace("\n", " ")
