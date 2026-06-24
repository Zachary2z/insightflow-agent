from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Callable

from workspaces.analysis_runner import run_workspace_analysis
from workspaces.models import utc_now_iso
from workspaces.profiler import profile_workspace_database
from workspaces.report_models import ReportSection
from workspaces.report_store import WorkspaceReportStore
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


SectionRunner = Callable[..., dict[str, Any]]
SECTION_ANALYSIS_MAX_ATTEMPTS = 3


REPORT_TYPE_PRESETS: dict[str, dict[str, Any]] = {
    "business_review": {
        "title": "Business Review",
        "sections": [
            {
                "section_id": "overall_revenue",
                "title": "Overall Revenue",
                "purpose": "Summarize recent revenue scale and channel mix using the current workspace data.",
                "intent_hint": "metric=收入; dimension=渠道; time_range=最近 90 天; operation=summary",
                "question": (
                    "统计最近 90 天订单收入概览：按渠道汇总收入、订单数和平均订单收入，输出渠道分组结果表，"
                    "并用这些结果概述收入表现；不需要总计行。"
                ),
            },
            {
                "section_id": "top_channels_or_products",
                "title": "Channel Revenue Ranking",
                "purpose": "Rank revenue contribution by acquisition channel using the current workspace data.",
                "intent_hint": "metric=收入; dimension=渠道; time_range=最近 90 天; operation=top_n; limit=5",
                "question": (
                    "以渠道收入排行为主，使用工作区 schema 中的 channel、revenue 和 order_date "
                    "或语义层中的等价字段，汇总最近 90 天收入最高的前 5 个渠道，解释主要贡献来源并生成适合对比的图表。"
                ),
            },
            {
                "section_id": "trend_or_recent_change",
                "title": "Trend Or Recent Change",
                "purpose": "Describe recent revenue movement over time using the current workspace date field.",
                "intent_hint": "metric=收入; dimension=时间; time_range=最近 90 天; operation=trend",
                "question": (
                    "使用 order_date 或语义层中的等价时间字段，基于数据集中最大日期推导最近 90 天，"
                    "按月或按周分析收入趋势，指出最近周期变化，并说明对经营复盘的影响。"
                ),
            },
            {
                "section_id": "evidence_backed_recommendations",
                "title": "Evidence Backed Recommendations",
                "purpose": "Produce channel-level evidence that can support concise recommendations.",
                "intent_hint": "metric=收入; dimension=渠道; time_range=最近 90 天; operation=summary",
                "question": (
                    "按渠道汇总最近 90 天收入、订单数和平均订单收入，输出一张渠道分组结果表，"
                    "并用结果指出高收入和低收入渠道，作为后续经营建议的数据证据；"
                    "本节只需要一个数据查询和证据摘要，不需要行动计划、外部投放建议或多步骤分析。"
                ),
            },
        ],
    },
    "channel_performance": {
        "title": "Channel Performance",
        "sections": [
            {
                "section_id": "channel_revenue_ranking",
                "title": "Channel Revenue Ranking",
                "purpose": "Compare revenue contribution across acquisition or sales channels.",
                "question": "按获客渠道比较收入表现，找出贡献最高的渠道并生成图表。",
            },
            {
                "section_id": "channel_trend_or_comparison",
                "title": "Channel Trend Or Comparison",
                "purpose": "Compare channel movement or differences across the available data.",
                "question": "比较不同渠道的变化趋势或表现差异，指出值得关注的渠道。",
            },
            {
                "section_id": "channel_efficiency",
                "title": "Channel Efficiency",
                "purpose": "Assess channel efficiency when spend or cost data is available.",
                "question": "如果当前工作区包含投放、成本或营销花费数据，请分析各渠道效率；如果没有，请基于可用数据说明渠道表现边界。",
            },
        ],
    },
    "revenue_trend": {
        "title": "Revenue Trend",
        "sections": [
            {
                "section_id": "revenue_trend",
                "title": "Revenue Trend",
                "purpose": "Analyze revenue over time using the available time fields.",
                "question": "分析收入随时间的趋势，指出最近周期变化。",
            },
            {
                "section_id": "recent_period_summary",
                "title": "Recent Period Summary",
                "purpose": "Summarize the most recent period relative to the dataset.",
                "question": "基于当前工作区数据，总结最近可用周期的收入表现和主要特征。",
            },
            {
                "section_id": "notable_changes",
                "title": "Notable Changes",
                "purpose": "Identify notable changes, spikes, dips, or shifts in revenue.",
                "question": "找出收入变化中最值得关注的上升、下降或结构性变化，并说明可能的业务含义。",
            },
        ],
    },
}


def run_workspace_report(
    store: WorkspaceStore,
    workspace_id: str,
    report_type: str,
    report_goal: str,
    providers: dict | None = None,
    *,
    section_runner: SectionRunner | None = None,
) -> dict[str, Any]:
    if not report_goal or not report_goal.strip():
        raise ValueError("report_goal is required")
    if report_type not in REPORT_TYPE_PRESETS:
        raise ValueError(f"Unsupported report_type: {report_type}")

    workspace = store.get_workspace(workspace_id)
    profile = _ensure_profile(store, workspace)
    _ensure_semantic_layer(store, workspace, profile)

    preset = REPORT_TYPE_PRESETS[report_type]
    report_store = WorkspaceReportStore(store)
    report = report_store.create_report_record(
        workspace_id=workspace_id,
        report_type=report_type,
        report_goal=report_goal.strip(),
        title=preset["title"],
        status="running",
    )
    runner = section_runner or run_workspace_analysis
    trace_events: list[dict[str, Any]] = []

    for section_plan in preset["sections"]:
        section_question = _section_question(
            report_goal=report.report_goal,
            report_type=report_type,
            section_plan=section_plan,
        )
        try:
            analysis_result = _run_section_analysis_with_retry(
                runner=runner,
                store=store,
                workspace_id=workspace_id,
                user_question=section_question,
                providers=providers,
            )
            section = _section_from_analysis_result(
                section_plan=section_plan,
                question=section_question,
                analysis_result=analysis_result,
                report_dir=Path(report.json_path).parent,
                artifact_dir=Path(report.artifact_dir),
            )
            trace_events.append(
                _section_trace_event(
                    "section_completed" if section.status == "completed" else "section_failed",
                    section,
                    analysis_result=analysis_result,
                )
            )
        except Exception as exc:  # noqa: BLE001 - report generation must keep partial structure.
            section = ReportSection(
                section_id=section_plan["section_id"],
                title=section_plan["title"],
                purpose=section_plan["purpose"],
                status="failed",
                question=section_question,
                error=str(exc),
            )
            trace_events.append(_section_trace_event("section_failed", section))
        report.sections.append(section)

    report.status = _report_status(report.sections)
    report.executive_summary = _executive_summary(report.sections)
    report.provider_metadata = {
        "section_count": len(report.sections),
        "completed_section_count": sum(
            1 for section in report.sections if section.status == "completed"
        ),
        "failed_section_count": sum(
            1 for section in report.sections if section.status == "failed"
        ),
    }
    saved = report_store.save_report(report, event_type=f"report_{report.status}")
    _append_trace_events(Path(saved.trace_path), trace_events)

    return {
        "success": saved.status == "completed",
        "workspace_id": workspace_id,
        "report_id": saved.report_id,
        "report": saved.to_dict(),
    }


def _run_section_analysis_with_retry(
    *,
    runner: SectionRunner,
    store: WorkspaceStore,
    workspace_id: str,
    user_question: str,
    providers: dict | None,
) -> dict[str, Any]:
    last_result: dict[str, Any] = {}
    for attempt in range(SECTION_ANALYSIS_MAX_ATTEMPTS):
        last_result = runner(
            store=store,
            workspace_id=workspace_id,
            user_question=user_question,
            providers=providers,
        )
        if attempt == SECTION_ANALYSIS_MAX_ATTEMPTS - 1:
            return last_result
        if not _retryable_provider_section_failure(last_result):
            return last_result
    return last_result


def _retryable_provider_section_failure(analysis_result: dict[str, Any]) -> bool:
    understanding = analysis_result.get("question_understanding") or {}
    if (
        understanding.get("strategy") == "reject"
        or understanding.get("risk_flags")
        or understanding.get("rejection_reason")
    ):
        return False

    missing_slots = set(understanding.get("missing_slots") or [])
    trace_nodes = {
        str(event.get("node"))
        for event in analysis_result.get("trace") or []
        if event.get("node")
    }
    provider_unavailable = (
        understanding.get("source") == "provider_unavailable"
        or "provider_output" in missing_slots
        or "Provider question understanding is unavailable"
        in str(analysis_result.get("final_answer") or "")
    )
    if (
        understanding.get("provider_called") is True
        and understanding.get("fallback_used") is True
        and provider_unavailable
        and (
            "early_response_node" in trace_nodes
            or analysis_result.get("status") == "waiting_for_clarification"
        )
    ):
        return True

    planning = analysis_result.get("sql_planning") or {}
    if (
        planning.get("provider_called") is True
        and planning.get("fallback_used") is True
        and planning.get("source") == "provider_unavailable"
    ):
        return True

    enhancement = analysis_result.get("llm_sql_enhancement") or {}
    return (
        enhancement.get("provider_called") is True
        and enhancement.get("fallback_used") is True
        and not enhancement.get("accepted")
    )


def _ensure_profile(store: WorkspaceStore, workspace: dict[str, Any]) -> dict[str, Any]:
    profile_path = Path(workspace["profile_path"])
    if profile_path.exists():
        return json.loads(profile_path.read_text(encoding="utf-8"))
    return profile_workspace_database(store, workspace["workspace_id"])


def _ensure_semantic_layer(
    store: WorkspaceStore,
    workspace: dict[str, Any],
    profile: dict[str, Any],
) -> None:
    semantic_layer_path = Path(workspace["semantic_layer_path"])
    if semantic_layer_path.exists():
        return
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)


def _section_question(
    *,
    report_goal: str,
    report_type: str,
    section_plan: dict[str, str],
) -> str:
    return (
        "这是自动报告内部 section，不是用户澄清轮次。"
        "请基于当前 workspace schema、profile 和 semantic layer 选择可用表字段；"
        "不要请求用户补充字段、表名、数据源或时间范围。"
        "隐私边界：只使用订单、渠道、收入、日期等聚合字段；"
        "如涉及客户，只能做非个人级聚合，不访问个人身份字段或客户明细。"
        "如果报告目标包含最近 90 天，请使用数据集中最大可用日期推导最近 90 天。\n"
        f"报告类型：{report_type}。\n"
        f"报告目标：{report_goal}\n"
        f"本节目的：{section_plan['purpose']}\n"
        f"本节意图提示：{section_plan.get('intent_hint', '使用本节问题中的完整分析意图')}\n"
        f"本节问题：{section_plan['question']}"
    )


def _section_from_analysis_result(
    *,
    section_plan: dict[str, str],
    question: str,
    analysis_result: dict[str, Any],
    report_dir: Path,
    artifact_dir: Path,
) -> ReportSection:
    execution_result = dict(analysis_result.get("execution_result") or {})
    status = "completed" if _analysis_succeeded(analysis_result, execution_result) else "failed"
    columns = [str(column) for column in execution_result.get("columns") or []]
    rows_preview = _rows_preview(execution_result)
    artifact_paths = _report_artifact_paths(
        section_id=section_plan["section_id"],
        analysis_result=analysis_result,
        report_dir=report_dir,
        artifact_dir=artifact_dir,
    )
    provider_metadata = _provider_metadata(analysis_result)
    trace_nodes = _trace_nodes(analysis_result.get("trace") or [])
    sql = str(analysis_result.get("generated_sql") or "")
    error = _section_error(analysis_result, execution_result, status)
    summary = _business_summary(analysis_result, sql)
    return ReportSection(
        section_id=section_plan["section_id"],
        title=section_plan["title"],
        purpose=section_plan["purpose"],
        status=status,
        question=question,
        summary=summary,
        sql=sql,
        columns=columns,
        rows_preview=rows_preview,
        artifact_paths=artifact_paths,
        evidence_notes=_evidence_notes(analysis_result.get("evidence_result") or {}),
        business_artifacts=[
            {"type": "chart", "path": path, "title": section_plan["title"]}
            for path in artifact_paths
        ],
        technical_details={
            "internal_question": question,
            "purpose": section_plan["purpose"],
            "sql": sql,
            "columns": columns,
            "rows_preview": rows_preview,
            "provider_metadata": provider_metadata,
            "trace_nodes": trace_nodes,
            "trace_path": str(analysis_result.get("trace_path") or ""),
            "workspace_run_dir": str(analysis_result.get("workspace_run_dir") or ""),
        },
        provider_metadata=provider_metadata,
        trace_nodes=trace_nodes,
        error=error,
    )


def _analysis_succeeded(
    analysis_result: dict[str, Any],
    execution_result: dict[str, Any],
) -> bool:
    return (
        analysis_result.get("status") == "completed"
        and execution_result.get("success") is True
    )


def _business_summary(analysis_result: dict[str, Any], sql: str) -> str:
    summary = str(analysis_result.get("final_answer") or "").strip()
    summary = re.sub(r"```sql\s*.*?```", "", summary, flags=re.IGNORECASE | re.DOTALL).strip()
    if sql:
        summary = summary.replace(sql, "").strip()
    if not summary:
        return "本节分析已完成，业务证据与技术细节见下方章节和附录。"
    return summary


def _rows_preview(execution_result: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    columns = [str(column) for column in execution_result.get("columns") or []]
    rows = list(execution_result.get("rows") or [])[:limit]
    preview = []
    for row in rows:
        if isinstance(row, dict):
            preview.append(row)
        else:
            preview.append(
                {
                    column: row[index] if index < len(row) else None
                    for index, column in enumerate(columns)
                }
            )
    return preview


def _report_artifact_paths(
    *,
    section_id: str,
    analysis_result: dict[str, Any],
    report_dir: Path,
    artifact_dir: Path,
) -> list[str]:
    artifact_paths = _analysis_artifact_paths(analysis_result)
    report_paths = []
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for index, artifact_path in enumerate(artifact_paths, start=1):
        source = Path(artifact_path)
        if not source.exists() or not source.is_file():
            continue
        suffix = source.suffix or ".artifact"
        target = artifact_dir / f"{section_id}_{index}{suffix}"
        shutil.copy2(source, target)
        report_paths.append(str(target.relative_to(report_dir)))
    return report_paths


def _analysis_artifact_paths(analysis_result: dict[str, Any]) -> list[str]:
    paths = []
    visualization_trace = analysis_result.get("visualization_trace") or {}
    for key in ("artifact_path", "chart_path"):
        value = visualization_trace.get(key)
        if value:
            paths.append(str(value))
    for value in analysis_result.get("artifact_paths") or []:
        if value:
            paths.append(str(value))
    return list(dict.fromkeys(paths))


def _evidence_notes(evidence_result: dict[str, Any]) -> list[str]:
    notes = []
    for key in ("data_supported_findings", "hypotheses", "unsupported_claims_blocked"):
        for item in evidence_result.get(key) or []:
            if isinstance(item, dict):
                text = item.get("claim") or item.get("text") or item.get("summary")
            else:
                text = str(item)
            if text:
                notes.append(str(text))
    if evidence_result.get("guarded_summary"):
        notes.append(str(evidence_result["guarded_summary"]))
    return notes


def _provider_metadata(analysis_result: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(analysis_result.get("provider_metadata") or {})
    for key in (
        "question_understanding",
        "sql_planning",
        "llm_sql_enhancement",
        "visualization_trace",
    ):
        value = analysis_result.get(key)
        if isinstance(value, dict):
            metadata[key] = {
                field: value.get(field)
                for field in (
                    "provider_called",
                    "source",
                    "strategy",
                    "model",
                    "prompt_id",
                    "external_tool_called",
                    "fallback_used",
                )
                if field in value
            }
    return metadata


def _trace_nodes(trace: list[dict[str, Any]]) -> list[str]:
    nodes = []
    for event in trace:
        node = event.get("node")
        if node:
            nodes.append(str(node))
    return nodes


def _section_error(
    analysis_result: dict[str, Any],
    execution_result: dict[str, Any],
    status: str,
) -> str | None:
    if status == "completed":
        return None
    return (
        analysis_result.get("final_answer")
        or execution_result.get("error")
        or analysis_result.get("error_message")
        or "Section analysis failed"
    )


def _report_status(sections: list[ReportSection]) -> str:
    completed = sum(1 for section in sections if section.status == "completed")
    failed = sum(1 for section in sections if section.status == "failed")
    if completed and failed:
        return "partial"
    if completed:
        return "completed"
    return "failed"


def _executive_summary(sections: list[ReportSection]) -> list[str]:
    summary = []
    for section in sections:
        if section.status == "completed" and section.summary:
            summary.append(f"{section.title}: {section.summary}")
        elif section.status == "failed":
            summary.append(f"{section.title}: section failed - {section.error}")
    return summary


def _section_trace_event(
    event: str,
    section: ReportSection,
    *,
    analysis_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = analysis_result or {}
    return {
        "event": event,
        "section_id": section.section_id,
        "status": section.status,
        "trace_nodes": section.trace_nodes,
        "workspace_run_dir": result.get("workspace_run_dir", ""),
        "section_trace_path": result.get("trace_path", ""),
        "created_at": utc_now_iso(),
    }


def _append_trace_events(trace_path: Path, events: list[dict[str, Any]]) -> None:
    existing = {}
    if trace_path.exists():
        existing = json.loads(trace_path.read_text(encoding="utf-8"))
    existing_events = list(existing.get("events", []))
    existing_events.extend(events)
    existing["events"] = existing_events
    trace_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
