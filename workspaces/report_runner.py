from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from workspaces.models import utc_now_iso
from workspaces.profiler import profile_workspace_database
from workspaces.report_models import (
    EvidenceRequirement,
    ReportChapterPlan,
    ReportDocument,
    ReportDocumentSection,
    ReportEvidenceFact,
    ReportEvidencePack,
    ReportEvidenceTable,
    ReportPlan,
    ReportValidationResult,
)
from workspaces.report_store import WorkspaceReportStore
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


SectionRunner = Callable[..., dict[str, Any]]
SUPPORTED_REPORT_TYPES = {"business_review", "channel_performance", "revenue_trend"}


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
    if report_type not in SUPPORTED_REPORT_TYPES:
        raise ValueError(f"Unsupported report_type: {report_type}")

    workspace = store.get_workspace(workspace_id)
    profile = _ensure_profile(store, workspace)
    semantic_layer = _ensure_semantic_layer(store, workspace, profile)

    plan = _plan_report(
        report_type=report_type,
        report_goal=report_goal.strip(),
        profile=profile,
        semantic_layer=semantic_layer,
    )
    evidence_pack = _collect_evidence(plan=plan, profile=profile, semantic_layer=semantic_layer)
    document = _compose_document(plan=plan, evidence_pack=evidence_pack)
    validation = _validate_document(document=document, evidence_pack=evidence_pack)
    document.technical_appendix = {
        "plan": plan.to_dict(),
        "evidence_pack": evidence_pack.to_dict(),
        "validation": validation.to_dict(),
        "pipeline": ["plan", "evidence", "compose", "validate", "render", "save"],
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
        "pipeline": "ReportPlan -> ReportEvidencePack -> ReportDocument -> validation -> renderer",
        "provider_supplied": bool(providers),
        "section_runner_used": False,
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


def _plan_report(
    *,
    report_type: str,
    report_goal: str,
    profile: dict[str, Any],
    semantic_layer: dict[str, Any],
) -> ReportPlan:
    data_sources = _data_sources(profile)
    metric_hint = _first_semantic_name(semantic_layer.get("metrics")) or "核心业务指标"
    dimension_hint = _first_semantic_name(semantic_layer.get("dimensions")) or "主要业务维度"
    time_range = _infer_time_range(report_goal)
    chapters = [
        ReportChapterPlan(
            chapter_id="overview",
            title="经营概览",
            purpose="说明本报告覆盖的数据范围、核心事实和阅读边界。",
            evidence_requirements=[
                EvidenceRequirement(
                    requirement_id="workspace_scope",
                    chapter_id="overview",
                    description="确认当前工作区可用表、字段和数据规模。",
                    metric_hint=metric_hint,
                    dimension_hint=dimension_hint,
                )
            ],
        ),
        ReportChapterPlan(
            chapter_id="business_structure",
            title=_structure_chapter_title(report_type),
            purpose="基于可用事实描述主要业务结构和后续需要重点分析的方向。",
            evidence_requirements=[
                EvidenceRequirement(
                    requirement_id="business_structure",
                    chapter_id="business_structure",
                    description="整理当前语义层中可用于分组和度量的业务口径。",
                    metric_hint=metric_hint,
                    dimension_hint=dimension_hint,
                    chart_hint="bar",
                )
            ],
        ),
        ReportChapterPlan(
            chapter_id="actions",
            title="行动建议",
            purpose="给出证据边界内的下一步经营动作和补数建议。",
            evidence_requirements=[
                EvidenceRequirement(
                    requirement_id="action_boundary",
                    chapter_id="actions",
                    description="列出当前证据能支持和暂不能支持的经营判断。",
                )
            ],
        ),
    ]
    return ReportPlan(
        title="最近90天经营复盘报告",
        report_style=_report_style(report_type),
        time_range=time_range,
        data_sources=data_sources,
        chapters=chapters,
    )


def _collect_evidence(
    *,
    plan: ReportPlan,
    profile: dict[str, Any],
    semantic_layer: dict[str, Any],
) -> ReportEvidencePack:
    tables = list(profile.get("tables") or [])
    table_count = len(tables)
    row_count = sum(_safe_int(table.get("row_count")) for table in tables if isinstance(table, dict))
    field_count = sum(len(table.get("columns") or []) for table in tables if isinstance(table, dict))
    facts = [
        ReportEvidenceFact(
            fact_id="workspace_table_count",
            label="可用数据表数量",
            value=table_count,
            display_value=str(table_count),
            source_chapter_id="overview",
            evidence_ref="workspace_profile",
        ),
        ReportEvidenceFact(
            fact_id="workspace_row_count",
            label="可用数据行数",
            value=row_count,
            display_value=str(row_count),
            source_chapter_id="overview",
            evidence_ref="workspace_profile",
        ),
        ReportEvidenceFact(
            fact_id="workspace_field_count",
            label="可用字段数量",
            value=field_count,
            display_value=str(field_count),
            source_chapter_id="business_structure",
            evidence_ref="workspace_profile",
        ),
    ]
    metric_names = _semantic_names(semantic_layer.get("metrics"))
    dimension_names = _semantic_names(semantic_layer.get("dimensions"))
    evidence_table = ReportEvidenceTable(
        table_id="workspace_profile",
        title="当前工作区数据概览",
        columns=["数据表", "行数", "字段数"],
        rows=[
            {
                "数据表": str(table.get("table_name") or table.get("name") or "未命名数据表"),
                "行数": _safe_int(table.get("row_count")),
                "字段数": len(table.get("columns") or []),
            }
            for table in tables
            if isinstance(table, dict)
        ],
        source_chapter_id="overview",
        description="H1 使用工作区 profile 作为最小可运行证据包；H2 会接入 SQL/metric/chart 工具采集细粒度证据。",
        evidence_ref="workspace_profile",
    )
    data_limits = [
        "P22-H1 仅完成报告合同和主流程切换，细粒度 SQL 指标证据会在 H2/H3 接入。",
        "本报告不会把查询语句、原始明细、执行轨迹或模型技术元数据放入主正文。",
    ]
    if not metric_names:
        data_limits.append("当前语义层暂未提供可直接用于报告的指标口径。")
    if not dimension_names:
        data_limits.append("当前语义层暂未提供可直接用于报告的分组维度。")
    return ReportEvidencePack(
        facts=facts,
        tables=[evidence_table],
        warnings=[],
        data_limits=data_limits,
        technical_details={
            "profile_table_count": table_count,
            "semantic_metric_count": len(metric_names),
            "semantic_dimension_count": len(dimension_names),
            "planned_chapter_ids": [chapter.chapter_id for chapter in plan.chapters],
        },
    )


def _compose_document(
    *,
    plan: ReportPlan,
    evidence_pack: ReportEvidencePack,
) -> ReportDocument:
    facts = {fact.fact_id: fact for fact in evidence_pack.facts}
    table_count = facts["workspace_table_count"].display_value
    row_count = facts["workspace_row_count"].display_value
    field_count = facts["workspace_field_count"].display_value
    opening_summary = (
        f"本报告基于当前工作区的 {table_count} 张数据表、{row_count} 行记录和 "
        f"{field_count} 个字段生成。H1 已切换为证据驱动报告合同，正文按完整中文报告组织，"
        "不再拼接分析工作台的章节回答。"
    )
    sections = [
        ReportDocumentSection(
            section_id="overview",
            title="经营概览",
            body=(
                f"当前报告覆盖的数据来源包括：{_join_or_default(plan.data_sources, '当前工作区数据')}。"
                f"从数据准备角度看，工作区已经具备 {table_count} 张表和 {row_count} 行记录，"
                "可以作为后续经营复盘的证据基础。"
            ),
            evidence_refs=["workspace_table_count", "workspace_row_count"],
        ),
        ReportDocumentSection(
            section_id="business_structure",
            title=plan.chapters[1].title if len(plan.chapters) > 1 else "业务结构",
            body=(
                "本阶段先根据工作区 profile 和 semantic layer 建立报告证据包。"
                "后续 H2 会把章节证据需求转成 SQL、指标、表格和图表请求，"
                "H3 再由报告撰写器基于这些证据形成更细的业务判断。"
            ),
            evidence_refs=["workspace_field_count"],
        ),
        ReportDocumentSection(
            section_id="actions",
            title="行动建议",
            body=(
                "当前可执行的动作是继续完善语义层指标、时间范围和关键业务维度，"
                "再进入下一轮证据采集和事实校验。涉及预算、利润、客服质量或客户分群的判断，"
                "需要等待对应证据表和图表补齐后再写入主报告结论。"
            ),
            evidence_refs=["action_boundary"],
        ),
    ]
    return ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary=opening_summary,
        sections=sections,
        action_recommendations=[
            "优先完善语义层中的核心指标、主要维度和时间字段。",
            "在 H2 接入证据采集后，再把收入结构、趋势、客户或客服问题写成细分章节。",
            "涉及资源投入或预算加码前，先补齐利润、成本、转化率等支持性证据。",
        ],
        data_boundaries=list(evidence_pack.data_limits),
    )


def _validate_document(
    *,
    document: ReportDocument,
    evidence_pack: ReportEvidencePack,
) -> ReportValidationResult:
    fact_ids = {fact.fact_id for fact in evidence_pack.facts}
    referenced = {
        ref
        for section in document.sections
        for ref in section.evidence_refs
        if ref in fact_ids
    }
    warnings = [
        ref
        for section in document.sections
        for ref in section.evidence_refs
        if ref not in fact_ids and ref != "action_boundary"
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
    return ["H1 暂不生成图表；本报告先基于结构化证据包和 ReportDocument 正文阅读。"]


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


def _data_sources(profile: dict[str, Any]) -> list[str]:
    names = []
    for table in profile.get("tables") or []:
        if not isinstance(table, dict):
            continue
        name = table.get("display_name") or table.get("table_name") or table.get("name")
        if name:
            names.append(str(name))
    return names or ["当前工作区数据"]


def _semantic_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = item.get("label") or item.get("name") or item.get("id")
        if name:
            names.append(str(name))
    return names


def _first_semantic_name(value: Any) -> str:
    names = _semantic_names(value)
    return names[0] if names else ""


def _infer_time_range(report_goal: str) -> str:
    if "90" in report_goal or "九十" in report_goal:
        return "最近90天"
    if "本月" in report_goal:
        return "本月"
    if "本周" in report_goal:
        return "本周"
    return "最近90天"


def _report_style(report_type: str) -> str:
    return {
        "business_review": "经营复盘",
        "channel_performance": "渠道表现复盘",
        "revenue_trend": "收入趋势复盘",
    }.get(report_type, "经营复盘")


def _structure_chapter_title(report_type: str) -> str:
    return {
        "business_review": "业务结构",
        "channel_performance": "渠道表现",
        "revenue_trend": "收入趋势",
    }.get(report_type, "业务结构")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _join_or_default(items: list[str], default: str) -> str:
    visible = [item for item in items if item.strip()]
    return "、".join(visible) if visible else default
