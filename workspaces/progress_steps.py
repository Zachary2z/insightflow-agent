from __future__ import annotations

from typing import Any, Literal, TypedDict


ProgressStatus = Literal["pending", "running", "completed", "failed", "skipped"]


class ProgressStep(TypedDict):
    key: str
    label: str
    status: ProgressStatus
    summary: str


def build_progress_steps(
    raw: dict[str, Any],
    *,
    analysis_route: dict[str, Any] | None = None,
    chart_artifacts: list[dict[str, Any]] | None = None,
) -> list[ProgressStep]:
    route = str((analysis_route or raw.get("analysis_route") or {}).get("route") or "standard_analysis")
    status = str(raw.get("status") or "").lower()

    if status == "waiting_for_clarification" or route == "clarify":
        return _clarification_steps(raw)
    if route == "report":
        return _report_steps(raw)

    steps = _analysis_steps(route, chart_artifacts=chart_artifacts or [])
    if status == "failed":
        return _mark_failed(steps, _failure_key(raw), _failure_summary(raw))
    if status in {"completed", "trace_save_failed"}:
        return steps
    return _mark_running(steps, _running_key(raw))


def _analysis_steps(route: str, *, chart_artifacts: list[dict[str, Any]]) -> list[ProgressStep]:
    final_label = "业务判断" if route == "deep_judgment" else "整理结论"
    final_summary = "已完成业务判断并整理结论。" if route == "deep_judgment" else "已整理为业务可读结论。"
    route_summary = {
        "fast_fact": "本次问题走快速事实路径。",
        "deep_judgment": "本次问题需要完整业务判断。",
        "standard_analysis": "本次问题走常规分析路径。",
    }.get(route, "已选择合适的分析路径。")
    chart_status: ProgressStatus = "skipped" if route == "fast_fact" else "completed"
    chart_summary = (
        "事实快答不生成图表。"
        if route == "fast_fact"
        else "已完成图表生成或图表可用性检查。"
    )
    if chart_status == "completed" and not chart_artifacts:
        chart_summary = "已检查图表需求，本轮没有可展示图表。"
    return [
        _step("understanding", "理解问题", "completed", "已识别业务问题和分析口径。"),
        _step("routing", "选择分析路径", "completed", route_summary),
        _step("querying", "查询数据", "completed", "已完成数据查询和安全审核。"),
        _step("validating", "验证证据", "completed", "已核对证据可支撑结论。"),
        _step("finalizing", final_label, "completed", final_summary),
        _step("charting", "生成图表", chart_status, chart_summary),
    ]


def _clarification_steps(raw: dict[str, Any]) -> list[ProgressStep]:
    question = _first_text(
        raw.get("clarification_question"),
        raw.get("clarification_questions"),
        (raw.get("clarification_result") or {}).get("clarification_question")
        if isinstance(raw.get("clarification_result"), dict)
        else "",
        (raw.get("clarification_result") or {}).get("questions")
        if isinstance(raw.get("clarification_result"), dict)
        else "",
    )
    summary = "正在等待补充分析条件。"
    if question:
        summary = "正在等待补充分析条件：" + question
    return [
        _step("understanding", "理解问题", "running", summary),
        _step("routing", "选择分析路径", "skipped", "补充信息后再选择分析路径。"),
        _step("querying", "查询数据", "pending", "补充信息后再查询数据。"),
        _step("validating", "验证证据", "pending", "查询完成后再验证证据。"),
        _step("finalizing", "整理结论", "pending", "证据验证后再整理结论。"),
    ]


def _report_steps(raw: dict[str, Any]) -> list[ProgressStep]:
    steps = [
        _step("understanding", "理解问题", "completed", "已识别报告目标。"),
        _step("querying", "查询数据", "completed", "已完成报告所需数据查询。"),
        _step("sectioning", "整理章节", "completed", "已整理报告章节结构。"),
        _step("reporting", "生成报告", "completed", "已生成报告内容。"),
    ]
    if str(raw.get("status") or "").lower() == "failed":
        return _mark_failed(steps, _report_failure_key(raw), "报告生成未能完成。")
    return steps


def _mark_failed(steps: list[ProgressStep], key: str, summary: str) -> list[ProgressStep]:
    failed = []
    seen_failure = False
    for step in steps:
        item = dict(step)
        if item["key"] == key:
            item["status"] = "failed"
            item["summary"] = summary
            seen_failure = True
        elif seen_failure and item["status"] != "skipped":
            item["status"] = "pending"
            item["summary"] = _pending_summary(item["label"])
        failed.append(item)
    return failed


def _mark_running(steps: list[ProgressStep], key: str) -> list[ProgressStep]:
    running = []
    reached = False
    for step in steps:
        item = dict(step)
        if item["key"] == key:
            item["status"] = "running"
            item["summary"] = _running_summary(item["label"])
            reached = True
        elif reached and item["status"] != "skipped":
            item["status"] = "pending"
            item["summary"] = _pending_summary(item["label"])
        running.append(item)
    return running


def _failure_key(raw: dict[str, Any]) -> str:
    evidence = raw.get("evidence_result") if isinstance(raw.get("evidence_result"), dict) else {}
    execution = raw.get("execution_result") if isinstance(raw.get("execution_result"), dict) else {}
    if raw.get("review_result") or raw.get("schema_repair"):
        return "querying"
    if execution and execution.get("success") is False:
        return "querying"
    if str(evidence.get("validation_status") or evidence.get("status") or "").lower() in {"failed", "rejected"}:
        return "validating"
    return "finalizing"


def _failure_summary(raw: dict[str, Any]) -> str:
    if raw.get("review_result") or raw.get("schema_repair"):
        return "数据查询未能通过安全审核。"
    execution = raw.get("execution_result") if isinstance(raw.get("execution_result"), dict) else {}
    if execution and execution.get("success") is False:
        return "数据查询未能完成。"
    evidence = raw.get("evidence_result") if isinstance(raw.get("evidence_result"), dict) else {}
    if str(evidence.get("validation_status") or evidence.get("status") or "").lower() in {"failed", "rejected"}:
        return "证据未能通过校验。"
    return "业务结论未能整理完成。"


def _running_key(raw: dict[str, Any]) -> str:
    if not raw.get("execution_result"):
        return "querying"
    if not raw.get("evidence_result"):
        return "validating"
    return "finalizing"


def _report_failure_key(raw: dict[str, Any]) -> str:
    if not raw.get("execution_result"):
        return "querying"
    report = raw.get("report_result") if isinstance(raw.get("report_result"), dict) else {}
    if not report.get("sections"):
        return "sectioning"
    return "reporting"


def _step(key: str, label: str, status: ProgressStatus, summary: str) -> ProgressStep:
    return {"key": key, "label": label, "status": status, "summary": summary}


def _pending_summary(label: str) -> str:
    return {
        "查询数据": "等待前序步骤完成后再查询数据。",
        "验证证据": "等待数据查询完成后再验证证据。",
        "整理结论": "等待证据验证完成后再整理结论。",
        "业务判断": "等待证据验证完成后再做业务判断。",
        "生成图表": "等待结论完成后再生成图表。",
        "整理章节": "等待数据查询完成后再整理章节。",
        "生成报告": "等待章节整理完成后再生成报告。",
    }.get(label, "等待前序步骤完成。")


def _running_summary(label: str) -> str:
    return {
        "查询数据": "正在查询并校验数据。",
        "验证证据": "正在核对证据是否支撑结论。",
        "整理结论": "正在整理业务结论。",
        "业务判断": "正在做业务判断。",
    }.get(label, "正在处理。")


def _first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    return item.strip()
    return ""
