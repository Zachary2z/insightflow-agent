from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workspaces.models import utc_now_iso
from workspaces.profiler import profile_workspace_database
from workspaces.report_evidence import collect_report_evidence
from workspaces.report_models import (
    ReportDocument,
    ReportDocumentSection,
    ReportEvidencePack,
    ReportPlan,
    ReportValidationResult,
)
from workspaces.report_planner import plan_workspace_report
from workspaces.report_store import WorkspaceReportStore
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


SUPPORTED_REPORT_TYPES = {"business_review", "channel_performance", "revenue_trend"}


def run_workspace_report(
    store: WorkspaceStore,
    workspace_id: str,
    report_type: str,
    report_goal: str,
    providers: dict | None = None,
) -> dict[str, Any]:
    if not report_goal or not report_goal.strip():
        raise ValueError("report_goal is required")
    if report_type not in SUPPORTED_REPORT_TYPES:
        raise ValueError(f"Unsupported report_type: {report_type}")

    workspace = store.get_workspace(workspace_id)
    profile = _ensure_profile(store, workspace)
    semantic_layer = _ensure_semantic_layer(store, workspace, profile)

    plan = plan_workspace_report(
        report_type=report_type,
        report_goal=report_goal.strip(),
        profile=profile,
        semantic_layer=semantic_layer,
    )
    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )
    document = _compose_document(plan=plan, evidence_pack=evidence_pack)
    validation = _validate_document(document=document, evidence_pack=evidence_pack)
    document.technical_appendix = {
        "plan": plan.to_dict(),
        "evidence_pack": evidence_pack.to_dict(),
        "validation": validation.to_dict(),
        "generation_steps": ["规划报告", "整理证据", "撰写正文", "校验证据", "渲染保存"],
    }

    report_store = WorkspaceReportStore(store)
    report = report_store.create_report_record(
        workspace_id=workspace_id,
        report_type=report_type,
        report_goal=report_goal.strip(),
        title=plan.title,
        status="running",
    )
    report.title = plan.title
    report.status = "completed" if validation.status == "passed" else "partial"
    report.plan = plan
    report.evidence_pack = evidence_pack
    report.document = document
    report.validation = validation
    report.executive_summary = [document.opening_summary]
    report.key_findings = [section.body for section in document.sections[:3]]
    report.action_priorities = list(document.action_recommendations)
    report.chart_and_evidence = _document_evidence_summary(evidence_pack)
    report.risks_and_limits = list(document.data_boundaries)
    report.sections = []
    report.provider_metadata = {
        "generation_flow": "evidence_driven_report_center",
        "provider_supplied": bool(providers),
    }
    saved = report_store.save_report(report, event_type="report_completed")
    _append_trace_events(
        Path(saved.trace_path),
        [
            {"event": "report_planned", "title": plan.title},
            {
                "event": "report_evidence_collected",
                "fact_count": len(evidence_pack.facts),
                "table_count": len(evidence_pack.tables),
                "chart_count": len(evidence_pack.charts),
            },
            {"event": "report_document_composed", "section_count": len(document.sections)},
            {"event": "report_validated", "status": validation.status},
        ],
    )

    return {
        "success": saved.status == "completed",
        "workspace_id": workspace_id,
        "report_id": saved.report_id,
        "report": saved.to_dict(),
    }


def _ensure_profile(store: WorkspaceStore, workspace: dict[str, Any]) -> dict[str, Any]:
    profile_path = Path(workspace["profile_path"])
    if profile_path.exists():
        return json.loads(profile_path.read_text(encoding="utf-8"))
    return profile_workspace_database(store, workspace["workspace_id"])


def _ensure_semantic_layer(
    store: WorkspaceStore,
    workspace: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    semantic_layer_path = Path(workspace["semantic_layer_path"])
    if not semantic_layer_path.exists():
        generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    if semantic_layer_path.exists():
        text = semantic_layer_path.read_text(encoding="utf-8")
        try:
            import yaml

            loaded = yaml.safe_load(text)
        except Exception:  # noqa: BLE001 - semantic draft may be JSON in old fixtures.
            loaded = json.loads(text)
        return loaded if isinstance(loaded, dict) else {}
    return {}


def _compose_document(
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
    base_summary += "正文只使用已采集到的结构化证据，并在数据边界中说明暂不支持的判断。"

    sections = []
    for chapter in plan.chapters:
        chapter_tables = tables_by_chapter.get(chapter.chapter_id, [])
        chapter_facts = [fact for fact in evidence_pack.facts if fact.source_chapter_id == chapter.chapter_id]
        body = _section_body(chapter.chapter_id, plan, chapter_tables, chapter_facts, evidence_pack)
        evidence_refs = [fact.fact_id for fact in chapter_facts] + [table.table_id for table in chapter_tables]
        chart_refs = [chart.chart_id for chart in evidence_pack.charts if chart.source_chapter_id == chapter.chapter_id]
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
                f"{scope.description} 工作区已具备可用于报告阅读的数据画像，并整理了可用指标、维度和时间字段。"
            )
        return "当前报告基于工作区现有数据生成，但数据画像尚不完整，后续结论需要结合补充证据阅读。"

    if chapter_id == "revenue_structure":
        total = next((fact for fact in chapter_facts if fact.fact_id == "revenue_total"), None)
        table = _first_table(chapter_tables)
        if table and table.rows:
            leader = table.rows[0]
            leader_text = _row_summary(leader)
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
    relevant_limits = [limit for limit in [*evidence_pack.warnings, *evidence_pack.data_limits] if topic[:2] in limit or topic in limit]
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


def _data_boundaries(evidence_pack: ReportEvidencePack) -> list[str]:
    limits = [*evidence_pack.warnings, *evidence_pack.data_limits]
    if not limits:
        limits = ["本报告基于当前工作区已识别的数据表、指标和维度生成。"]
    return list(dict.fromkeys(limits))


def _validate_document(
    *,
    document: ReportDocument,
    evidence_pack: ReportEvidencePack,
) -> ReportValidationResult:
    fact_ids = {fact.fact_id for fact in evidence_pack.facts}
    table_ids = {table.table_id for table in evidence_pack.tables}
    chart_ids = {chart.chart_id for chart in evidence_pack.charts}
    supported_refs = fact_ids | table_ids | chart_ids
    referenced = {
        ref
        for section in document.sections
        for ref in [*section.evidence_refs, *section.chart_refs]
        if ref in supported_refs
    }
    warnings = [
        ref
        for section in document.sections
        for ref in [*section.evidence_refs, *section.chart_refs]
        if ref not in supported_refs
    ]
    status = "passed" if document.title and document.sections and not warnings else "warning"
    return ReportValidationResult(
        status=status,
        checked_facts=sorted(referenced),
        warnings=[f"未在证据包中找到引用：{ref}" for ref in warnings],
        unsupported_claims=[],
    )


def _document_evidence_summary(evidence_pack: ReportEvidencePack) -> list[str]:
    if evidence_pack.charts:
        return [chart.title for chart in evidence_pack.charts]
    return ["当前尚未生成图表；本报告先基于工作区数据画像和结构化证据阅读。"]


def _append_trace_events(trace_path: Path, events: list[dict[str, Any]]) -> None:
    existing_events = []
    if trace_path.exists():
        existing = json.loads(trace_path.read_text(encoding="utf-8"))
        existing_events = list(existing.get("events", []))
    for event in events:
        event.setdefault("created_at", utc_now_iso())
        existing_events.append(event)
    trace_path.write_text(
        json.dumps(
            {
                "events": existing_events,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

def _join_or_default(items: list[str], default: str) -> str:
    visible = [item for item in items if item.strip()]
    return "、".join(visible) if visible else default
