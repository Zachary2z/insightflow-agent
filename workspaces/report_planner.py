from __future__ import annotations

import re
from typing import Any

from workspaces.time_range_defaults import report_time_range_for_goal
from workspaces.report_models import EvidenceRequirement, ReportChapterPlan, ReportPlan


def plan_workspace_report(
    *,
    report_type: str,
    report_goal: str,
    profile: dict[str, Any],
    semantic_layer: dict[str, Any],
) -> ReportPlan:
    goal = report_goal.strip()
    time_policy = report_time_range_for_goal(
        report_goal=goal,
        profile=profile,
        semantic_layer=semantic_layer,
    )
    time_range = str(time_policy.get("time_range") or "")
    capabilities = _semantic_capabilities(profile, semantic_layer)
    inferred_intent = infer_report_intent(goal, report_type=report_type)
    requested = chapter_topics_for_goal(goal, inferred_intent)
    if "business_review" in requested or not requested:
        requested.update({"revenue_structure", "trend_changes", "actions"})
        if capabilities["customer_dimensions"]:
            requested.add("customer_segments")
        if capabilities["support_fields"]:
            requested.add("support_issues")

    chapters = [_overview_chapter(capabilities)]
    for topic in (
        "store_performance",
        "product_performance",
        "revenue_structure",
        "customer_segments",
        "support_issues",
        "support_operations",
        "channel_investment",
        "trend_changes",
        "actions",
    ):
        if topic in requested:
            chapters.append(_chapter_for_topic(topic, capabilities))

    if not any(chapter.chapter_id == "actions" for chapter in chapters):
        chapters.append(_chapter_for_topic("actions", capabilities))

    return ReportPlan(
        title=title_for_report_goal(goal, inferred_intent, time_range),
        report_style=_report_style(inferred_intent),
        time_range=time_range,
        report_goal=goal,
        data_sources=_data_sources(profile),
        chapters=chapters,
        missing_slots=[
            str(item)
            for item in time_policy.get("missing_slots", [])
            if str(item).strip()
        ],
        clarification_questions=[
            str(item)
            for item in time_policy.get("clarification_questions", [])
            if str(item).strip()
        ],
    )


def infer_report_intent(
    goal: str,
    available_evidence: dict[str, Any] | None = None,
    *,
    report_type: str = "business_review",
) -> str:
    del available_evidence
    compact = _compact(goal)
    topics = _requested_topics(goal)
    domain_topics = topics - {"business_review", "actions", "revenue_structure"}

    if "管理层经营简报" in compact or "管理层简报" in compact or (
        "管理层" in compact and "简报" in compact
    ):
        return "management_brief"
    if any(token in compact for token in ("经营复盘", "业务复盘", "经营报告", "经营简报")):
        return "business_review"
    if "简报" in compact and len(domain_topics) >= 2:
        return "management_brief"

    channel_only = "channel_investment" in topics and not (
        domain_topics - {"channel_investment"}
    )
    if channel_only or (report_type == "channel_performance" and not domain_topics):
        return "channel_performance"

    trend_only = "trend_changes" in topics and not (domain_topics - {"trend_changes"})
    if trend_only or (report_type == "revenue_trend" and not domain_topics):
        return "revenue_trend"

    if "product_performance" in topics and not (domain_topics - {"product_performance"}):
        return "product_performance"
    if "customer_segments" in topics and not (domain_topics - {"customer_segments"}):
        return "customer_segments"
    if "support_issues" in topics and not (domain_topics - {"support_issues"}):
        return "support_issues"
    return "business_review"


def title_for_report_goal(goal: str, inferred_intent: str, time_range: str) -> str:
    del goal
    prefix = _title_time_prefix(time_range)
    titles = {
        "management_brief": f"{prefix}管理层经营简报",
        "business_review": f"{prefix}经营复盘报告",
        "channel_performance": f"{prefix}渠道表现复盘报告",
        "revenue_trend": f"{prefix}趋势变化报告",
        "support_issues": f"{prefix}客服问题报告",
        "product_performance": f"{prefix}商品表现专题报告",
        "customer_segments": f"{prefix}客户分群专题报告",
    }
    return titles.get(inferred_intent, f"{prefix}经营复盘报告")


def chapter_topics_for_goal(goal: str, inferred_intent: str) -> set[str]:
    requested = _requested_topics(goal)
    if inferred_intent in {"business_review", "management_brief"}:
        requested.add("business_review")
    elif inferred_intent == "channel_performance":
        requested.add("channel_investment")
    elif inferred_intent == "revenue_trend":
        requested.add("trend_changes")
    elif inferred_intent == "product_performance":
        requested.add("product_performance")
    elif inferred_intent == "customer_segments":
        requested.add("customer_segments")
    elif inferred_intent == "support_issues":
        requested.add("support_issues")
    return requested


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
        "store_performance": _store_chapter,
        "product_performance": _product_chapter,
        "revenue_structure": _revenue_chapter,
        "customer_segments": _customer_chapter,
        "support_issues": _support_chapter,
        "support_operations": _support_operations_chapter,
        "channel_investment": _channel_investment_chapter,
        "trend_changes": _trend_chapter,
        "actions": _actions_chapter,
    }
    return builders[topic](capabilities)


def _requirement(
    *,
    requirement_id: str,
    chapter_id: str,
    description: str,
    metric_hint: str = "",
    dimension_hint: str = "",
    query_hint: str,
    chart_hint: str = "",
    time_range: dict[str, Any] | None = None,
    metrics: list[str] | None = None,
    dimensions: list[str] | None = None,
    calculation_type: str = "",
    missing_evidence: list[str] | None = None,
) -> EvidenceRequirement:
    dimensions = list(dimensions or ([dimension_hint] if dimension_hint else []))
    metrics = list(metrics or ([metric_hint] if metric_hint else []))
    return EvidenceRequirement(
        requirement_id=requirement_id,
        chapter_id=chapter_id,
        description=description,
        metric_hint=metric_hint,
        dimension_hint=dimension_hint,
        query_hint=query_hint,
        chart_hint=chart_hint,
        time_range=time_range or {},
        metrics=metrics,
        dimensions=dimensions,
        group_by=dimensions,
        comparison_scope={"type": "peer_comparison", "required_min_rows": 2},
        calculation_type=calculation_type,
        missing_evidence=list(missing_evidence or []),
    )


def _store_chapter(capabilities: dict[str, Any]) -> ReportChapterPlan:
    metric = _label(_primary_metric(capabilities) or {})
    dimension = _label(_first_matching(capabilities["dimensions"], _STORE_TOKENS) or _primary_dimension(capabilities) or {})
    missing = []
    if not metric:
        missing.append("缺少可汇总的门店表现指标")
    if not dimension:
        missing.append("缺少门店或可分组维度")
    return ReportChapterPlan(
        chapter_id="store_performance",
        title="门店表现",
        purpose="比较门店销售或经营指标表现。",
        evidence_requirements=[
            _requirement(
                requirement_id="store_performance_ranking",
                chapter_id="store_performance",
                description="按门店或主要经营实体计算核心指标排名。",
                metric_hint=metric,
                dimension_hint=dimension,
                query_hint="generic_ranking",
                chart_hint="bar",
                metrics=[metric] if metric else [],
                dimensions=[dimension] if dimension else [],
                calculation_type="ranking",
                missing_evidence=missing,
            )
        ],
    )


def _product_chapter(capabilities: dict[str, Any]) -> ReportChapterPlan:
    metric = _label(_primary_metric(capabilities) or {})
    dimension = _label(_first_matching(capabilities["dimensions"], _PRODUCT_TOKENS) or _primary_dimension(capabilities) or {})
    missing = []
    if not metric:
        missing.append("缺少可汇总的商品表现指标")
    if not dimension:
        missing.append("缺少商品、产品或品类维度")
    return ReportChapterPlan(
        chapter_id="product_performance",
        title="商品表现",
        purpose="说明商品或品类贡献、占比和集中度。",
        evidence_requirements=[
            _requirement(
                requirement_id="product_contribution",
                chapter_id="product_performance",
                description="按商品或品类计算核心指标贡献和占比。",
                metric_hint=metric,
                dimension_hint=dimension,
                query_hint="generic_contribution",
                chart_hint="bar",
                metrics=[metric] if metric else [],
                dimensions=[dimension] if dimension else [],
                calculation_type="contribution",
                missing_evidence=missing,
            )
        ],
    )


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


def _support_operations_chapter(capabilities: dict[str, Any]) -> ReportChapterPlan:
    team_dimension = _label(_first_matching(capabilities["dimensions"], _TEAM_TOKENS) or {})
    metric_labels = [
        _label(item)
        for item in capabilities["metrics"]
        if _matches(item, _SUPPORT_OPERATION_METRIC_TOKENS)
    ]
    missing = []
    if not team_dimension:
        missing.append("缺少客服团队或运营分组维度")
    if not metric_labels:
        missing.append("缺少响应时长、满意度或工单量指标")
    return ReportChapterPlan(
        chapter_id="support_operations",
        title="客服运营",
        purpose="比较客服团队响应效率、工单压力和满意度。",
        evidence_requirements=[
            _requirement(
                requirement_id="support_operational_efficiency",
                chapter_id="support_operations",
                description="按客服团队计算工单量、平均响应时长和满意度。",
                metric_hint=metric_labels[0] if metric_labels else "",
                dimension_hint=team_dimension,
                query_hint="generic_operational_efficiency",
                chart_hint="bar",
                metrics=metric_labels,
                dimensions=[team_dimension] if team_dimension else [],
                calculation_type="operational_efficiency",
                missing_evidence=missing,
            )
        ],
    )


def _channel_investment_chapter(capabilities: dict[str, Any]) -> ReportChapterPlan:
    channel_dimension = _label(_first_matching(capabilities["dimensions"], _CHANNEL_TOKENS) or _primary_dimension(capabilities) or {})
    revenue_metric = _label((capabilities["revenue_metrics"] or [_primary_metric(capabilities) or {}])[0])
    spend_metrics = [_label(metric) for metric in capabilities["metrics"] if _matches(metric, _COST_TOKENS)]
    metrics = [item for item in [revenue_metric, *(spend_metrics[:1]), "ROAS", "净投放回报率"] if item]
    missing = []
    if not channel_dimension:
        missing.append("缺少渠道维度")
    if not revenue_metric:
        missing.append("缺少收入指标")
    if not spend_metrics:
        missing.append("缺少投放成本或花费指标")
    return ReportChapterPlan(
        chapter_id="channel_investment",
        title="渠道投放表现",
        purpose="评估渠道收入、投放成本和投入产出效率。",
        evidence_requirements=[
            _requirement(
                requirement_id="channel_investment_efficiency",
                chapter_id="channel_investment",
                description="按渠道计算收入、投放成本、ROAS 和净投放回报率。",
                metric_hint=revenue_metric,
                dimension_hint=channel_dimension,
                query_hint="generic_investment_efficiency",
                chart_hint="bar",
                metrics=metrics,
                dimensions=[channel_dimension] if channel_dimension else [],
                calculation_type="investment_efficiency",
                missing_evidence=missing,
            )
        ],
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
    if any(token in compact for token in ("经营复盘", "业务复盘", "经营报告", "经营简报", "businessreview", "review")):
        topics.add("business_review")
    if any(token in compact for token in ("门店表现", "门店", "店铺", "store")):
        topics.add("store_performance")
    if any(token in compact for token in ("商品表现", "商品", "产品", "品类", "product", "category")):
        topics.add("product_performance")
    if any(token in compact for token in ("收入结构", "收入", "营收", "销售额", "revenue", "sales")):
        topics.add("revenue_structure")
    if any(token in compact for token in ("客户分群", "客户", "客群", "会员", "人群", "segment")):
        topics.add("customer_segments")
    if any(token in compact for token in ("客服", "工单", "投诉", "满意度", "响应时长", "support", "ticket")):
        topics.add("support_issues")
    if any(token in compact for token in ("客服运营", "响应效率", "客服团队", "supportoperations")):
        topics.add("support_operations")
    if any(token in compact for token in ("渠道投放", "渠道表现", "渠道效率", "投放表现", "投放成本", "roi", "roas", "投产比")):
        topics.add("channel_investment")
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


def _first_matching(items: list[dict[str, Any]], tokens: tuple[str, ...]) -> dict[str, Any] | None:
    return next((item for item in items if _matches(item, tokens)), None)


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


def _report_style(inferred_intent: str) -> str:
    return {
        "management_brief": "管理层经营简报",
        "business_review": "经营复盘",
        "channel_performance": "渠道表现复盘",
        "revenue_trend": "趋势分析",
        "support_issues": "问题诊断",
        "customer_segments": "客户分析",
        "product_performance": "商品专题",
    }.get(inferred_intent, "经营复盘")


def _title_time_prefix(time_range: str) -> str:
    if str(time_range or "").startswith("完整数据时间范围"):
        return "完整数据"
    if str(time_range or "") == "当前工作区全部可用数据":
        return "全部数据"
    return str(time_range or "当前数据")


def _compact(value: Any) -> str:
    return re.sub(r"[\s_\-]+", "", str(value).lower())


_REVENUE_TOKENS = ("revenue_like", "sales_like", "gmv_like", "revenue", "sales", "收入", "营收", "销售额", "营业额", "成交额")
_CUSTOMER_TOKENS = ("customer", "client", "member", "segment", "客户", "会员", "客群", "人群", "分群")
_SUPPORT_TOKENS = ("support", "ticket", "issue", "complaint", "response", "satisfaction", "客服", "工单", "问题", "投诉", "响应", "满意度")
_STORE_TOKENS = ("store", "shop", "门店", "店铺")
_PRODUCT_TOKENS = ("product", "category", "sku", "商品", "产品", "品类", "类别")
_TEAM_TOKENS = ("team", "group", "团队", "客服组", "分组")
_CHANNEL_TOKENS = ("channel", "渠道", "campaign", "广告", "投放")
_COST_TOKENS = ("cost", "spend", "expense", "成本", "花费", "投放", "消耗")
_SUPPORT_OPERATION_METRIC_TOKENS = ("ticket", "response", "satisfaction", "工单", "响应", "满意度", "评分")
