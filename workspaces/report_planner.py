from __future__ import annotations

import re
from typing import Any

from workspaces.report_models import EvidenceRequirement, ReportChapterPlan, ReportPlan


def plan_workspace_report(
    *,
    report_type: str,
    report_goal: str,
    profile: dict[str, Any],
    semantic_layer: dict[str, Any],
) -> ReportPlan:
    goal = report_goal.strip()
    capabilities = _semantic_capabilities(profile, semantic_layer)
    requested = _requested_topics(goal)
    if "business_review" in requested or not requested:
        requested.update({"revenue_structure", "trend_changes", "actions"})
        if capabilities["customer_dimensions"]:
            requested.add("customer_segments")
        if capabilities["support_fields"]:
            requested.add("support_issues")

    chapters = [_overview_chapter(capabilities)]
    for topic in (
        "revenue_structure",
        "customer_segments",
        "support_issues",
        "trend_changes",
        "actions",
    ):
        if topic in requested:
            chapters.append(_chapter_for_topic(topic, capabilities))

    if not any(chapter.chapter_id == "actions" for chapter in chapters):
        chapters.append(_chapter_for_topic("actions", capabilities))

    return ReportPlan(
        title=_title_for_goal(goal, report_type),
        report_style=_report_style(report_type, goal),
        time_range=_infer_time_range(goal),
        data_sources=_data_sources(profile),
        chapters=chapters,
    )


def _overview_chapter(capabilities: dict[str, Any]) -> ReportChapterPlan:
    requirements = [
        EvidenceRequirement(
            requirement_id="workspace_overview",
            chapter_id="overview",
            description="梳理当前工作区的数据表、字段规模、可用指标和可用维度。",
            query_hint="profile",
        )
    ]
    if not capabilities["metrics"]:
        requirements.append(
            EvidenceRequirement(
                requirement_id="metrics_missing",
                chapter_id="overview",
                description="当前语义层缺少可直接汇总的指标口径，后续章节只能说明数据边界。",
                query_hint="missing",
            )
        )
    return ReportChapterPlan(
        chapter_id="overview",
        title="经营概览",
        purpose="说明报告使用的数据来源、核心口径和证据边界。",
        evidence_requirements=requirements,
    )


def _chapter_for_topic(topic: str, capabilities: dict[str, Any]) -> ReportChapterPlan:
    builders = {
        "revenue_structure": _revenue_chapter,
        "customer_segments": _customer_chapter,
        "support_issues": _support_chapter,
        "trend_changes": _trend_chapter,
        "actions": _actions_chapter,
    }
    return builders[topic](capabilities)


def _revenue_chapter(capabilities: dict[str, Any]) -> ReportChapterPlan:
    requirements = []
    if capabilities["revenue_metrics"]:
        requirements.append(
            EvidenceRequirement(
                requirement_id="revenue_total",
                chapter_id="revenue_structure",
                description="按收入类指标汇总总收入，并按主要业务维度拆解收入结构。",
                metric_hint=_label(capabilities["revenue_metrics"][0]),
                dimension_hint=_label(_primary_dimension(capabilities) or {}),
                query_hint="revenue_structure",
                chart_hint="bar",
            )
        )
    else:
        requirements.append(
            EvidenceRequirement(
                requirement_id="revenue_missing",
                chapter_id="revenue_structure",
                description="用户要求收入结构，但当前工作区暂未识别到收入或销售额类指标，证据 requirement 缺失。",
                query_hint="missing",
            )
        )
    return ReportChapterPlan(
        chapter_id="revenue_structure",
        title="收入结构",
        purpose="说明收入规模、主要来源和结构集中度。",
        evidence_requirements=requirements,
    )


def _customer_chapter(capabilities: dict[str, Any]) -> ReportChapterPlan:
    if capabilities["customer_dimensions"]:
        requirements = [
            EvidenceRequirement(
                requirement_id="customer_segment_contribution",
                chapter_id="customer_segments",
                description="按客户分群维度统计收入或订单贡献。",
                metric_hint=_label(_primary_metric(capabilities) or {}),
                dimension_hint=_label(capabilities["customer_dimensions"][0]),
                query_hint="customer_segments",
                chart_hint="bar",
            )
        ]
    else:
        requirements = [
            EvidenceRequirement(
                requirement_id="customer_segments_missing",
                chapter_id="customer_segments",
                description="用户要求客户分群，但当前工作区暂未识别到客户、会员、人群或分群维度，证据 requirement 缺失。",
                query_hint="missing",
            )
        ]
    return ReportChapterPlan(
        chapter_id="customer_segments",
        title="客户分群",
        purpose="说明不同客户分群对收入、订单或业务规模的贡献。",
        evidence_requirements=requirements,
    )


def _support_chapter(capabilities: dict[str, Any]) -> ReportChapterPlan:
    if capabilities["support_fields"]:
        requirements = [
            EvidenceRequirement(
                requirement_id="support_issue_summary",
                chapter_id="support_issues",
                description="按客服问题类型统计工单量、满意度或响应时长。",
                dimension_hint="问题类型",
                query_hint="support_issues",
                chart_hint="bar",
            )
        ]
    else:
        requirements = [
            EvidenceRequirement(
                requirement_id="support_issues_missing",
                chapter_id="support_issues",
                description="用户要求客服问题，但当前工作区暂未识别到客服、工单、投诉、满意度或响应时长字段，证据 requirement 缺失。",
                query_hint="missing",
            )
        ]
    return ReportChapterPlan(
        chapter_id="support_issues",
        title="客服问题",
        purpose="说明客服问题分布、服务压力和客户体验风险。",
        evidence_requirements=requirements,
    )


def _trend_chapter(capabilities: dict[str, Any]) -> ReportChapterPlan:
    if capabilities["time_fields"] and capabilities["metrics"]:
        requirements = [
            EvidenceRequirement(
                requirement_id="recent_trend",
                chapter_id="trend_changes",
                description="按时间字段观察最近周期的核心指标变化。",
                metric_hint=_label(_primary_metric(capabilities) or {}),
                dimension_hint=_label(capabilities["time_fields"][0]),
                query_hint="trend_changes",
                chart_hint="line",
            )
        ]
    else:
        requirements = [
            EvidenceRequirement(
                requirement_id="trend_missing",
                chapter_id="trend_changes",
                description="用户要求趋势变化，但当前工作区缺少时间字段或可汇总指标，证据 requirement 缺失。",
                query_hint="missing",
            )
        ]
    return ReportChapterPlan(
        chapter_id="trend_changes",
        title="趋势变化",
        purpose="说明最近周期的业务变化方向。",
        evidence_requirements=requirements,
    )


def _actions_chapter(capabilities: dict[str, Any]) -> ReportChapterPlan:
    missing_parts = []
    if not capabilities["revenue_metrics"]:
        missing_parts.append("收入指标")
    if not capabilities["time_fields"]:
        missing_parts.append("时间字段")
    description = "基于已采集证据形成行动建议，并列出不能直接支持的判断。"
    if missing_parts:
        description += " 当前缺失：" + "、".join(missing_parts) + "。"
    return ReportChapterPlan(
        chapter_id="actions",
        title="行动建议",
        purpose="把证据转化为下一步经营动作和补数建议。",
        evidence_requirements=[
            EvidenceRequirement(
                requirement_id="action_recommendation_inputs",
                chapter_id="actions",
                description=description,
                query_hint="recommendations",
            )
        ],
    )


def _requested_topics(goal: str) -> set[str]:
    compact = _compact(goal)
    topics: set[str] = set()
    if any(token in compact for token in ("经营复盘", "复盘", "businessreview", "review")):
        topics.add("business_review")
    if any(token in compact for token in ("收入结构", "收入", "营收", "销售额", "revenue", "sales")):
        topics.add("revenue_structure")
    if any(token in compact for token in ("客户分群", "客户", "客群", "会员", "人群", "segment")):
        topics.add("customer_segments")
    if any(token in compact for token in ("客服", "工单", "投诉", "满意度", "响应时长", "support", "ticket")):
        topics.add("support_issues")
    if any(token in compact for token in ("趋势", "变化", "环比", "同比", "trend")):
        topics.add("trend_changes")
    if any(token in compact for token in ("行动建议", "建议", "动作", "优化", "recommend")):
        topics.add("actions")
    return topics


def _semantic_capabilities(
    profile: dict[str, Any],
    semantic_layer: dict[str, Any],
) -> dict[str, Any]:
    metrics = [item for item in semantic_layer.get("metrics") or [] if isinstance(item, dict)]
    dimensions = [item for item in semantic_layer.get("dimensions") or [] if isinstance(item, dict)]
    time_fields = [item for item in semantic_layer.get("time_fields") or [] if isinstance(item, dict)]
    return {
        "profile": profile,
        "metrics": metrics,
        "dimensions": dimensions,
        "time_fields": time_fields,
        "revenue_metrics": [metric for metric in metrics if _matches(metric, _REVENUE_TOKENS)],
        "customer_dimensions": [dimension for dimension in dimensions if _matches(dimension, _CUSTOMER_TOKENS)],
        "support_fields": [
            item
            for item in [*metrics, *dimensions, *time_fields, *_profile_fields(profile)]
            if _matches(item, _SUPPORT_TOKENS)
        ],
    }


def _primary_metric(capabilities: dict[str, Any]) -> dict[str, Any] | None:
    return (capabilities["revenue_metrics"] or capabilities["metrics"] or [None])[0]


def _primary_dimension(capabilities: dict[str, Any]) -> dict[str, Any] | None:
    non_customer = [
        dimension
        for dimension in capabilities["dimensions"]
        if dimension not in capabilities["customer_dimensions"]
    ]
    return (non_customer or capabilities["dimensions"] or [None])[0]


def _profile_fields(profile: dict[str, Any]) -> list[dict[str, Any]]:
    fields = []
    for table in profile.get("tables") or []:
        if not isinstance(table, dict):
            continue
        table_name = str(table.get("table_name") or "")
        fields.append({"name": table_name, "label": table_name, "field": table_name})
        for column in table.get("columns") or []:
            if isinstance(column, dict):
                fields.append({**column, "table": table_name, "field": f"{table_name}.{column.get('name', '')}"})
    return fields


def _matches(item: dict[str, Any], tokens: tuple[str, ...]) -> bool:
    text = " ".join(
        str(value or "")
        for value in [
            item.get("name"),
            item.get("label"),
            item.get("field"),
            item.get("table"),
            *(item.get("aliases") or []),
            *(item.get("business_meaning_candidates") or []),
        ]
    )
    compact = _compact(text)
    return any(_compact(token) in compact for token in tokens)


def _label(item: dict[str, Any]) -> str:
    return str(item.get("business_label") or item.get("label") or item.get("name") or item.get("field") or "")


def _data_sources(profile: dict[str, Any]) -> list[str]:
    names = []
    for table in profile.get("tables") or []:
        if isinstance(table, dict):
            name = table.get("display_name") or table.get("table_name") or table.get("name")
            if name:
                names.append(str(name))
    return names or ["当前工作区数据"]


def _title_for_goal(goal: str, report_type: str) -> str:
    if "趋势" in goal and "复盘" not in goal:
        return "最近90天趋势变化报告"
    if "客服" in goal and "经营" not in goal and "复盘" not in goal:
        return "最近90天客服问题报告"
    if report_type == "revenue_trend":
        return "最近90天趋势变化报告"
    return "最近90天经营复盘报告"


def _report_style(report_type: str, goal: str) -> str:
    if "经营" in goal or "复盘" in goal or report_type == "business_review":
        return "经营复盘"
    if "客服" in goal:
        return "问题诊断"
    if "趋势" in goal or report_type == "revenue_trend":
        return "趋势分析"
    if "客户" in goal or "分群" in goal:
        return "客户分析"
    return {
        "business_review": "经营复盘",
        "channel_performance": "渠道表现复盘",
        "revenue_trend": "趋势分析",
    }.get(report_type, "经营复盘")


def _infer_time_range(report_goal: str) -> str:
    if re.search(r"90|九十", report_goal):
        return "最近90天"
    if "最近30天" in report_goal or "近30天" in report_goal:
        return "最近30天"
    if "本月" in report_goal:
        return "本月"
    if "本周" in report_goal:
        return "本周"
    return "最近90天"


def _compact(value: Any) -> str:
    return re.sub(r"[\s_\-]+", "", str(value).lower())


_REVENUE_TOKENS = ("revenue_like", "sales_like", "gmv_like", "revenue", "sales", "收入", "营收", "销售额", "营业额", "成交额")
_CUSTOMER_TOKENS = ("customer", "client", "member", "segment", "客户", "会员", "客群", "人群", "分群")
_SUPPORT_TOKENS = ("support", "ticket", "issue", "complaint", "response", "satisfaction", "客服", "工单", "问题", "投诉", "响应", "满意度")
