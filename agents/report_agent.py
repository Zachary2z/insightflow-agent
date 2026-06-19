from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.report_tool import DEFAULT_REPORT_DIR, save_report
from tools.trace_logger import append_trace


def _bullet_list(items: list[Any]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def _format_result_summary(execution_result: dict[str, Any]) -> str:
    columns = execution_result.get("columns", [])
    rows = execution_result.get("rows", [])
    if not rows:
        return "查询执行成功，但没有返回数据行。"

    lines = [f"row_count: {execution_result.get('row_count', len(rows))}", "", "| " + " | ".join(columns) + " |"]
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for row in rows[:5]:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    if execution_result.get("truncated"):
        lines.append("")
        lines.append("结果已按 max_rows 截断。")
    return "\n".join(lines)


def _format_findings(evidence_result: dict[str, Any]) -> str:
    findings = evidence_result.get("data_supported_findings", [])
    if not findings:
        return "- None"
    lines = []
    for finding in findings:
        lines.append(f"- {finding.get('claim', '')}")
        lines.append(f"  - Evidence: {finding.get('evidence', '')}")
        lines.append(f"  - Confidence: {finding.get('confidence', '')}")
    return "\n".join(lines)


def _format_hypotheses(evidence_result: dict[str, Any]) -> str:
    hypotheses = evidence_result.get("hypotheses", [])
    if not hypotheses:
        return "- None"
    lines = []
    for hypothesis in hypotheses:
        lines.append(f"- {hypothesis.get('claim', '')}")
        lines.append(f"  - Reason: {hypothesis.get('reason', '')}")
        needs_more_data = hypothesis.get("needs_more_data", [])
        lines.append(f"  - Needs more data: {', '.join(needs_more_data) if needs_more_data else 'None'}")
    return "\n".join(lines)


def _format_next_steps(evidence_result: dict[str, Any]) -> str:
    hypotheses = evidence_result.get("hypotheses", [])
    if hypotheses:
        needed = []
        for hypothesis in hypotheses:
            for item in hypothesis.get("needs_more_data", []):
                if item not in needed:
                    needed.append(item)
        if needed:
            return "- Collect or connect additional data: " + ", ".join(needed)
    return "- Review supported findings with business stakeholders."


def build_report_content(state: dict[str, Any]) -> str:
    execution_result = state.get("execution_result") or {}
    evidence_result = state.get("evidence_result") or {}
    chart_paths = state.get("chart_paths") or ([state["chart_path"]] if state.get("chart_path") else [])
    selected_metrics = state.get("selected_metrics") or state.get("metric_context", {}).get("matched_metrics", [])
    business_context_summary = state.get("business_context", {}).get("context_summary", "")

    return "\n".join(
        [
            "# InsightFlow Analysis Report",
            "",
            "## 用户问题",
            state.get("user_question", ""),
            "",
            "## 使用的业务指标",
            _bullet_list(selected_metrics),
            "",
            "## 业务上下文",
            business_context_summary or "No business context summary available.",
            "",
            "## 执行 SQL",
            "```sql",
            state.get("generated_sql", ""),
            "```",
            "",
            "## 查询结果摘要",
            _format_result_summary(execution_result),
            "",
            "## 数据支持结论",
            _format_findings(evidence_result),
            "",
            "## 需要进一步验证的假设",
            _format_hypotheses(evidence_result),
            "",
            "## 图表路径",
            _bullet_list(chart_paths),
            "",
            "## 下一步建议",
            _format_next_steps(evidence_result),
            "",
            "## Trace 路径",
            state.get("trace_path", ""),
            "",
        ]
    )


def _report_failure(error: str) -> dict[str, Any]:
    return {
        "success": False,
        "run_id": "",
        "report_path": "",
        "error": error,
        "trace_event": {
            "tool_name": "save_report",
            "tool_input_summary": "run_id=",
            "tool_output_summary": error,
            "status": "error",
            "latency_ms": 0,
            "error_type": "report_save_error",
            "error": error,
        },
    }


def run_report_agent(
    state: dict[str, Any],
    output_dir: str | Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    execution_result = state.get("execution_result")
    if not execution_result or not execution_result.get("success"):
        result = _report_failure("execution_result is required for report generation")
    else:
        report_content = build_report_content(state)
        result = save_report(state.get("run_id", "run_unknown"), report_content, output_dir=output_dir)

    updated = {
        **state,
        "report_result": result,
        "report_path": result.get("report_path", "") if result.get("success") else "",
    }
    if not result.get("success"):
        updated["report_warning"] = result.get("error", "")

    trace_event = dict(result.get("trace_event", {}))
    trace_event["node"] = "report_agent"
    return append_trace(updated, trace_event)
