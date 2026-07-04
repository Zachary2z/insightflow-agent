from __future__ import annotations

import re
from html import escape
from pathlib import Path
from typing import Any

from tools.evidence_tool import build_evidence_payload
from tools.metric_tool import build_metric_registry
from tools.sql_executor import run_sql
from tools.sql_validator import validate_sql
from workspaces.report_models import (
    ReportEvidenceChart,
    ReportEvidenceFact,
    ReportEvidencePack,
    ReportEvidenceTable,
    ReportPlan,
)


class _TimeFilter:
    def __init__(self, where_sql: str = "") -> None:
        self.where_sql = where_sql


def collect_report_evidence(
    *,
    plan: ReportPlan,
    profile: dict[str, Any],
    semantic_layer: dict[str, Any],
    analysis_db_path: str | Path,
    artifact_dir: str | Path | None = None,
    artifact_base_path: str = "",
) -> ReportEvidencePack:
    context = _EvidenceContext(profile=profile, semantic_layer=semantic_layer)
    technical_queries: list[dict[str, Any]] = []
    facts = _workspace_facts(profile)
    tables = [_workspace_overview_table(profile), _semantic_overview_table(context)]
    charts: list[ReportEvidenceChart] = []
    warnings: list[str] = []
    data_limits: list[str] = []
    default_time_note = _default_time_range_note(plan.time_range)
    if default_time_note:
        warnings.append(default_time_note)

    for chapter in plan.chapters:
        for requirement in chapter.evidence_requirements:
            if requirement.query_hint.startswith("generic_"):
                _collect_generic_requirement(
                    context,
                    analysis_db_path,
                    requirement=requirement,
                    time_range=plan.time_range,
                    tables=tables,
                    charts=charts,
                    warnings=warnings,
                    data_limits=data_limits,
                    technical_queries=technical_queries,
                )
        if chapter.chapter_id == "revenue_structure":
            _collect_revenue_structure(
                context,
                analysis_db_path,
                time_range=plan.time_range,
                facts=facts,
                tables=tables,
                charts=charts,
                warnings=warnings,
                data_limits=data_limits,
                technical_queries=technical_queries,
            )
        elif chapter.chapter_id == "customer_segments":
            _collect_customer_segments(
                context,
                analysis_db_path,
                time_range=plan.time_range,
                tables=tables,
                charts=charts,
                warnings=warnings,
                data_limits=data_limits,
                technical_queries=technical_queries,
            )
        elif chapter.chapter_id == "support_issues":
            _collect_support_issues(
                context,
                analysis_db_path,
                time_range=plan.time_range,
                tables=tables,
                charts=charts,
                warnings=warnings,
                data_limits=data_limits,
                technical_queries=technical_queries,
            )
        elif chapter.chapter_id == "trend_changes":
            _collect_trend_changes(
                context,
                analysis_db_path,
                time_range=plan.time_range,
                tables=tables,
                charts=charts,
                warnings=warnings,
                data_limits=data_limits,
                technical_queries=technical_queries,
            )

    if not context.metrics:
        data_limits.append("当前语义层暂未识别到可直接汇总的指标。")
    if not context.dimensions:
        data_limits.append("当前语义层暂未识别到可用于分组的业务维度。")
    data_limits.extend(_requested_goal_data_limits(plan, context))
    _materialize_chart_artifacts(
        charts=charts,
        tables=tables,
        artifact_dir=Path(artifact_dir) if artifact_dir else None,
        artifact_base_path=artifact_base_path,
        warnings=warnings,
    )
    evidence_payloads = [
        _business_safe_evidence_payload(query["evidence_payload"])
        for query in technical_queries
        if isinstance(query.get("evidence_payload"), dict)
    ]

    return ReportEvidencePack(
        facts=facts,
        tables=[table for table in tables if table.rows],
        charts=charts,
        warnings=list(dict.fromkeys(warnings)),
        data_limits=list(dict.fromkeys(data_limits)),
        evidence_payloads=evidence_payloads,
        technical_details={
            "metric_registry": context.metric_registry,
            "queries": technical_queries,
            "planned_chapter_ids": [chapter.chapter_id for chapter in plan.chapters],
        },
    )


def _requested_goal_data_limits(plan: ReportPlan, context: "_EvidenceContext") -> list[str]:
    goal = str(plan.report_goal or "")
    if not goal:
        return []
    available_items = [*context.metrics, *context.dimensions, *context.time_fields, *_profile_fields(context.profile)]
    limits: list[str] = []
    if _goal_mentions(goal, ("ROI", "roi", "投产比", "投资回报", "回报率")) and not any(
        _matches(item, _ROI_TOKENS) for item in available_items
    ):
        limits.append("用户目标包含 ROI，但当前工作区暂未识别到可计算 ROI 的成本、投放或回报口径。")
    if _goal_mentions(goal, ("投放成本", "成本", "花费", "消耗", "spend", "cost")) and not any(
        _matches(item, _COST_TOKENS) for item in available_items
    ):
        limits.append("用户目标包含投放成本，但当前工作区暂未识别到成本、花费或投放消耗字段。")
    if _goal_mentions(goal, ("利润", "毛利", "净利", "利润率", "profit", "margin")) and not any(
        _matches(item, _PROFIT_TOKENS) for item in available_items
    ):
        limits.append("用户目标包含利润或利润率，但当前工作区暂未识别到利润、毛利、净利或可验证的利润口径字段。")
    if _goal_mentions(goal, ("复购", "留存", "retention", "repeat purchase", "repurchase")) and not any(
        _matches(item, _RETENTION_TOKENS) for item in available_items
    ):
        limits.append("用户目标包含复购或留存，但当前工作区暂未识别到可直接计算复购率/留存率的订单序列或复购标记字段。")
    return limits


def _default_time_range_note(time_range: str) -> str:
    match = re.search(
        r"完整数据时间范围：\s*(\d{4}[-/]\d{1,2}(?:[-/]\d{1,2})?)\s*至\s*(\d{4}[-/]\d{1,2}(?:[-/]\d{1,2})?)",
        str(time_range or ""),
    )
    if not match:
        return ""
    start, end = match.groups()
    return f"你没有指定时间范围，本报告默认使用数据集中完整可用时间范围：{start} 至 {end}。"


def _profile_fields(profile: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for table in profile.get("tables") or []:
        if not isinstance(table, dict):
            continue
        table_name = str(table.get("table_name") or "")
        fields.append({"name": table_name, "label": table_name, "field": table_name})
        for column in table.get("columns") or []:
            if isinstance(column, dict):
                fields.append(
                    {
                        **column,
                        "table": table_name,
                        "field": f"{table_name}.{column.get('name', '')}",
                    }
                )
    return fields


def _goal_mentions(goal: str, tokens: tuple[str, ...]) -> bool:
    compact = _compact(goal)
    return any(_compact(token) in compact for token in tokens)


def _materialize_chart_artifacts(
    *,
    charts: list[ReportEvidenceChart],
    tables: list[ReportEvidenceTable],
    artifact_dir: Path | None,
    artifact_base_path: str,
    warnings: list[str],
) -> None:
    if artifact_dir is None:
        return
    artifact_dir.mkdir(parents=True, exist_ok=True)
    tables_by_ref = {table.evidence_ref: table for table in tables if table.rows}
    for chart in charts:
        if chart.path:
            continue
        table = tables_by_ref.get(chart.evidence_ref)
        if not table:
            chart.description = chart.description or "当前证据不足以生成图表。"
            continue
        chart_id = chart.chart_id.replace("_intent", "_chart") or chart.chart_id
        filename = f"{_safe_artifact_name(chart_id)}.svg"
        target = artifact_dir / filename
        try:
            target.write_text(
                _render_svg_chart(chart=chart, table=table),
                encoding="utf-8",
            )
        except OSError:
            warnings.append(f"{chart.title or '报告图表'}暂未生成，当前证据可先作为表格阅读。")
            chart.description = "当前证据不足以生成图表。"
            continue
        chart.chart_id = chart_id
        chart.path = "/".join(
            part.strip("/")
            for part in [artifact_base_path, filename]
            if str(part).strip("/")
        )
        chart.description = chart.description.replace("图表意图：", "") or f"基于{table.title}生成。"


def _render_svg_chart(*, chart: ReportEvidenceChart, table: ReportEvidenceTable) -> str:
    width = 720
    height = 360
    margin_left = 136
    margin_right = 48
    top = 64
    bar_height = 28
    gap = 20
    rows = table.rows[:8]
    numeric_values = [_display_number(row.get(table.columns[-1] if table.columns else "")) for row in rows]
    max_value = max([value for value in numeric_values if value is not None] or [1.0])
    if max_value <= 0:
        max_value = 1.0
    entity_column = table.columns[0] if table.columns else ""
    metric_column = table.columns[-1] if table.columns else ""
    body_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        f"<title>{escape(chart.title or table.title or '报告图表')}</title>",
        '<rect width="720" height="360" fill="#ffffff"/>',
        f'<text x="32" y="36" font-size="20" font-family="Arial, sans-serif" fill="#111827">{escape(chart.title or table.title or "报告图表")}</text>',
    ]
    palette = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2", "#4b5563", "#db2777"]
    for index, row in enumerate(rows):
        y = top + index * (bar_height + gap)
        label = str(row.get(entity_column, "") or "")
        display_value = str(row.get(metric_column, "") or "")
        numeric_value = numeric_values[index] or 0
        bar_width = max(8, int((width - margin_left - margin_right) * numeric_value / max_value))
        color = palette[index % len(palette)]
        body_lines.extend(
            [
                f'<text x="32" y="{y + 20}" font-size="14" font-family="Arial, sans-serif" fill="#374151">{escape(label[:18])}</text>',
                f'<rect x="{margin_left}" y="{y}" width="{bar_width}" height="{bar_height}" rx="4" fill="{color}"/>',
                f'<text x="{margin_left + bar_width + 8}" y="{y + 20}" font-size="14" font-family="Arial, sans-serif" fill="#111827">{escape(display_value)}</text>',
            ]
        )
    body_lines.append("</svg>")
    return "\n".join(body_lines)


def _display_number(value: Any) -> float | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    multiplier = 10000.0 if "万" in text else 1.0
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0)) * multiplier


def _safe_artifact_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return safe or "report_chart"


class _EvidenceContext:
    def __init__(self, *, profile: dict[str, Any], semantic_layer: dict[str, Any]) -> None:
        self.profile = profile
        self.semantic_layer = semantic_layer
        self.metrics = [item for item in semantic_layer.get("metrics") or [] if isinstance(item, dict)]
        self.dimensions = [item for item in semantic_layer.get("dimensions") or [] if isinstance(item, dict)]
        self.time_fields = [item for item in semantic_layer.get("time_fields") or [] if isinstance(item, dict)]
        self.metric_registry = build_metric_registry(semantic_layer)
        self.registry_metrics = self.metric_registry.get("metrics") or {}

    def revenue_metric(self) -> dict[str, Any] | None:
        return _first_registry_metric(self.registry_metrics, _REVENUE_TOKENS) or _first_semantic_metric(self.metrics, _REVENUE_TOKENS)

    def primary_metric(self) -> dict[str, Any] | None:
        return self.revenue_metric() or _first_registry_metric(self.registry_metrics, tuple()) or (self.metrics[0] if self.metrics else None)

    def structure_dimension(self, table_name: str) -> dict[str, Any] | None:
        preferred = [
            dimension
            for dimension in self.dimensions
            if _field_table(dimension) == table_name and not _matches(dimension, _CUSTOMER_TOKENS)
        ]
        return preferred[0] if preferred else self.dimension_for_table(table_name)

    def customer_dimension(self, table_name: str) -> dict[str, Any] | None:
        return next(
            (
                dimension
                for dimension in self.dimensions
                if _field_table(dimension) == table_name and _matches(dimension, _CUSTOMER_TOKENS)
            ),
            None,
        )

    def dimension_for_table(self, table_name: str) -> dict[str, Any] | None:
        return next((dimension for dimension in self.dimensions if _field_table(dimension) == table_name), None)

    def time_field_for_table(self, table_name: str) -> dict[str, Any] | None:
        return next((field for field in self.time_fields if _field_table(field) == table_name), None)

    def support_table(self) -> str:
        support_names: list[str] = []
        for table in self.profile.get("tables") or []:
            if isinstance(table, dict) and _matches(table, _SUPPORT_TOKENS):
                support_names.append(str(table.get("table_name") or ""))
        for item in [*self.metrics, *self.dimensions, *self.time_fields]:
            if _matches(item, _SUPPORT_TOKENS):
                support_names.append(_field_table(item))
        return next((name for name in support_names if name), "")

    def column(self, table_name: str, tokens: tuple[str, ...]) -> str:
        table = _profile_table(self.profile, table_name)
        for column in table.get("columns") or []:
            if isinstance(column, dict) and _matches(column, tokens):
                return str(column.get("name") or "")
        return ""


def _workspace_facts(profile: dict[str, Any]) -> list[ReportEvidenceFact]:
    tables = [table for table in profile.get("tables") or [] if isinstance(table, dict)]
    row_count = sum(_safe_number(table.get("row_count")) or 0 for table in tables)
    field_count = sum(len(table.get("columns") or []) for table in tables)
    return [
        ReportEvidenceFact(
            fact_id="workspace_table_count",
            label="可用数据表数量",
            value=len(tables),
            display_value=str(len(tables)),
            source_chapter_id="overview",
            evidence_ref="workspace_profile",
        ),
        ReportEvidenceFact(
            fact_id="workspace_row_count",
            label="可用数据行数",
            value=row_count,
            display_value=str(int(row_count)),
            source_chapter_id="overview",
            evidence_ref="workspace_profile",
        ),
        ReportEvidenceFact(
            fact_id="workspace_field_count",
            label="可用字段数量",
            value=field_count,
            display_value=str(field_count),
            source_chapter_id="overview",
            evidence_ref="workspace_profile",
        ),
    ]


def _workspace_overview_table(profile: dict[str, Any]) -> ReportEvidenceTable:
    return ReportEvidenceTable(
        table_id="workspace_overview",
        title="当前工作区数据概览",
        columns=["数据表", "行数", "字段数"],
        rows=[
            {
                "数据表": str(table.get("table_name") or "未命名数据表"),
                "行数": int(_safe_number(table.get("row_count")) or 0),
                "字段数": len(table.get("columns") or []),
            }
            for table in profile.get("tables") or []
            if isinstance(table, dict)
        ],
        source_chapter_id="overview",
        description="证据来自当前工作区数据画像。",
        evidence_ref="workspace_profile",
    )


def _semantic_overview_table(context: _EvidenceContext) -> ReportEvidenceTable:
    return ReportEvidenceTable(
        table_id="semantic_overview",
        title="可用指标和维度",
        columns=["类型", "中文名称", "来源字段"],
        rows=[
            *[
                {"类型": "指标", "中文名称": _metric_label(metric), "来源字段": _source_fields(metric)}
                for metric in context.metrics[:8]
            ],
            *[
                {"类型": "维度", "中文名称": _label(dimension), "来源字段": str(dimension.get("field") or "")}
                for dimension in context.dimensions[:8]
            ],
            *[
                {"类型": "时间字段", "中文名称": _label(field) or str(field.get("name") or ""), "来源字段": str(field.get("field") or "")}
                for field in context.time_fields[:4]
            ],
        ],
        source_chapter_id="overview",
        description="证据来自当前工作区语义层。",
        evidence_ref="semantic_layer",
    )


def _collect_revenue_structure(
    context: _EvidenceContext,
    db_path: str | Path,
    *,
    time_range: str,
    facts: list[ReportEvidenceFact],
    tables: list[ReportEvidenceTable],
    charts: list[ReportEvidenceChart],
    warnings: list[str],
    data_limits: list[str],
    technical_queries: list[dict[str, Any]],
) -> None:
    metric = context.revenue_metric()
    if not metric:
        data_limits.append("当前工作区未识别到收入或销售额类指标，无法生成收入结构证据。")
        return
    table_name = _metric_table(metric)
    dimension = context.structure_dimension(table_name)
    time_filter = _time_filter_clause(
        context,
        table_name,
        time_range=time_range,
        data_limits=data_limits,
        evidence_label="收入结构证据",
    )
    total = _execute_query(
        context,
        db_path,
        sql=f"SELECT {_metric_formula(metric)} AS total_value FROM {_quote(table_name)}{time_filter.where_sql}",
        task={"task_type": "summary", "metrics": [_metric_label(metric)], "dimensions": []},
        time_range=time_range,
        evidence_ref="query_revenue_total",
        technical_queries=technical_queries,
    )
    if total.get("success") and total.get("rows"):
        value = total["rows"][0][0]
        facts.append(
            ReportEvidenceFact(
                fact_id="revenue_total",
                label="总收入",
                value=value,
                display_value=_format_value(value, unit="currency"),
                source_chapter_id="revenue_structure",
                evidence_ref="query_revenue_total",
                unit="currency",
            )
        )
    else:
        warnings.append("收入总额查询未返回可用结果。")

    if not dimension:
        data_limits.append("当前收入表缺少可用于拆解收入结构的业务维度。")
        return
    dim_col = _field_column(dimension)
    detail = _execute_query(
        context,
        db_path,
        sql=(
            f"SELECT {_quote(dim_col)} AS dimension_value, {_metric_formula(metric)} AS metric_value "
            f"FROM {_quote(table_name)}{time_filter.where_sql} "
            f"GROUP BY {_quote(dim_col)} ORDER BY metric_value DESC"
        ),
        task={"task_type": "rank", "metrics": [_metric_label(metric)], "dimensions": [_label(dimension)]},
        time_range=time_range,
        evidence_ref="query_revenue_by_dimension",
        technical_queries=technical_queries,
    )
    if not detail.get("success"):
        warnings.append("收入结构查询未通过校验或执行失败。")
        return
    tables.append(
        _two_column_table(
            table_id="revenue_by_dimension",
            title="收入结构",
            source_chapter_id="revenue_structure",
            description=f"证据来自{_readable_table_name(table_name)}按{_label(dimension)}汇总。",
            dimension_label=_label(dimension) or "业务维度",
            metric_label="收入",
            rows=detail.get("rows") or [],
            metric_unit="currency",
            evidence_ref="query_revenue_by_dimension",
            evidence_payload_ref="query_revenue_by_dimension",
        )
    )
    charts.append(
        ReportEvidenceChart(
            chart_id="revenue_structure_intent",
            title="收入结构图表",
            source_chapter_id="revenue_structure",
            chart_type="bar",
            description="图表意图：按主要业务维度展示收入贡献。",
            evidence_ref="query_revenue_by_dimension",
        )
    )


def _collect_customer_segments(
    context: _EvidenceContext,
    db_path: str | Path,
    *,
    time_range: str,
    tables: list[ReportEvidenceTable],
    charts: list[ReportEvidenceChart],
    warnings: list[str],
    data_limits: list[str],
    technical_queries: list[dict[str, Any]],
) -> None:
    metric = context.primary_metric()
    if not metric:
        data_limits.append("当前工作区缺少可用于客户分群贡献计算的指标。")
        return
    table_name = _metric_table(metric)
    dimension = context.customer_dimension(table_name)
    if not dimension:
        data_limits.append("当前工作区暂未识别到客户分群维度，无法生成客户分群贡献证据。")
        return
    dim_col = _field_column(dimension)
    time_filter = _time_filter_clause(
        context,
        table_name,
        time_range=time_range,
        data_limits=data_limits,
        evidence_label="客户分群证据",
    )
    result = _execute_query(
        context,
        db_path,
        sql=(
            f"SELECT {_quote(dim_col)} AS dimension_value, {_metric_formula(metric)} AS metric_value "
            f"FROM {_quote(table_name)}{time_filter.where_sql} "
            f"GROUP BY {_quote(dim_col)} ORDER BY metric_value DESC"
        ),
        task={"task_type": "rank", "metrics": [_metric_label(metric)], "dimensions": [_label(dimension)]},
        time_range=time_range,
        evidence_ref="query_customer_segment_contribution",
        technical_queries=technical_queries,
    )
    if not result.get("success"):
        warnings.append("客户分群证据查询未通过校验或执行失败。")
        return
    tables.append(
        _two_column_table(
            table_id="customer_segment_contribution",
            title="客户分群贡献",
            source_chapter_id="customer_segments",
            description=f"证据来自{_readable_table_name(table_name)}按{_label(dimension)}汇总。",
            dimension_label="客户分群",
            metric_label="收入" if _matches(metric, _REVENUE_TOKENS) else _metric_label(metric),
            rows=result.get("rows") or [],
            metric_unit=_unit_for_metric(metric),
            evidence_ref="query_customer_segment_contribution",
            evidence_payload_ref="query_customer_segment_contribution",
        )
    )
    charts.append(
        ReportEvidenceChart(
            chart_id="customer_segments_intent",
            title="客户分群贡献图表",
            source_chapter_id="customer_segments",
            chart_type="bar",
            description="图表意图：展示不同客户分群的业务贡献。",
            evidence_ref="query_customer_segment_contribution",
        )
    )


def _collect_support_issues(
    context: _EvidenceContext,
    db_path: str | Path,
    *,
    time_range: str,
    tables: list[ReportEvidenceTable],
    charts: list[ReportEvidenceChart],
    warnings: list[str],
    data_limits: list[str],
    technical_queries: list[dict[str, Any]],
) -> None:
    table_name = context.support_table()
    if not table_name:
        data_limits.append("当前工作区未识别到客服、工单、投诉、满意度或响应时长字段，无法生成客服问题证据。")
        return
    issue_col = context.column(table_name, _ISSUE_TOKENS) or _first_dimension_column(context, table_name)
    if not issue_col:
        data_limits.append("客服相关数据缺少问题类型或可分组字段。")
        return
    ticket_expression = _support_ticket_count_expression(context, table_name)
    satisfaction_col = context.column(table_name, _SATISFACTION_TOKENS)
    response_col = context.column(table_name, _RESPONSE_TOKENS)
    select_parts = [f"{_quote(issue_col)} AS issue_value"]
    select_parts.append(f"{ticket_expression} AS ticket_value")
    if satisfaction_col:
        select_parts.append(f"AVG({_quote(satisfaction_col)}) AS satisfaction_value")
    if response_col:
        select_parts.append(f"AVG({_quote(response_col)}) AS response_value")
    time_filter = _time_filter_clause(
        context,
        table_name,
        time_range=time_range,
        data_limits=data_limits,
        evidence_label="客服问题证据",
    )
    result = _execute_query(
        context,
        db_path,
        sql=(
            f"SELECT {', '.join(select_parts)} FROM {_quote(table_name)}{time_filter.where_sql} "
            f"GROUP BY {_quote(issue_col)} ORDER BY ticket_value DESC"
        ),
        task={"task_type": "rank", "metrics": ["工单量"], "dimensions": ["问题类型"]},
        time_range=time_range,
        evidence_ref="query_support_issue_summary",
        technical_queries=technical_queries,
    )
    if not result.get("success"):
        warnings.append("客服问题证据查询未通过校验或执行失败。")
        return
    columns = ["问题类型", "工单量"]
    if satisfaction_col:
        columns.append("满意度")
    if response_col:
        columns.append("平均响应时长")
    rows = []
    for row in result.get("rows") or []:
        item = {"问题类型": row[0], "工单量": _format_value(row[1])}
        index = 2
        if satisfaction_col:
            item["满意度"] = _format_value(row[index])
            index += 1
        if response_col:
            item["平均响应时长"] = _format_value(row[index], suffix=" 分钟")
        rows.append(item)
    tables.append(
        ReportEvidenceTable(
            table_id="support_issue_summary",
            title="客服问题概览",
            columns=columns,
            rows=rows,
            source_chapter_id="support_issues",
            description=f"证据来自{_readable_table_name(table_name)}按问题类型汇总。",
            evidence_ref="query_support_issue_summary",
            evidence_payload_ref="query_support_issue_summary",
        )
    )
    charts.append(
        ReportEvidenceChart(
            chart_id="support_issues_intent",
            title="客服问题图表",
            source_chapter_id="support_issues",
            chart_type="bar",
            description="图表意图：展示不同问题类型的工单量和体验指标。",
            evidence_ref="query_support_issue_summary",
        )
    )


def _collect_trend_changes(
    context: _EvidenceContext,
    db_path: str | Path,
    *,
    time_range: str,
    tables: list[ReportEvidenceTable],
    charts: list[ReportEvidenceChart],
    warnings: list[str],
    data_limits: list[str],
    technical_queries: list[dict[str, Any]],
) -> None:
    metric = context.primary_metric()
    if not metric:
        data_limits.append("当前工作区缺少可用于趋势分析的指标。")
        return
    table_name = _metric_table(metric)
    time_field = context.time_field_for_table(table_name)
    if not time_field:
        data_limits.append(
            f"趋势变化证据需要按{time_range}读取，但{_readable_table_name(table_name)}缺少时间字段，"
            "未应用时间过滤，无法生成趋势变化证据。"
        )
        return
    time_col = _field_column(time_field)
    time_filter = _time_filter_clause(
        context,
        table_name,
        time_range=time_range,
        data_limits=data_limits,
        evidence_label="趋势变化证据",
    )
    result = _execute_query(
        context,
        db_path,
        sql=(
            f"SELECT substr({_quote(time_col)}, 1, 7) AS period_value, {_metric_formula(metric)} AS metric_value "
            f"FROM {_quote(table_name)}{time_filter.where_sql} GROUP BY period_value ORDER BY period_value"
        ),
        task={"task_type": "trend", "metrics": [_metric_label(metric)], "dimensions": ["周期"]},
        time_range=time_range,
        evidence_ref="query_recent_trend",
        technical_queries=technical_queries,
    )
    if not result.get("success"):
        warnings.append("趋势变化证据查询未通过校验或执行失败。")
        return
    tables.append(
        _two_column_table(
            table_id="recent_trend",
            title="趋势变化",
            source_chapter_id="trend_changes",
            description=f"证据来自{_readable_table_name(table_name)}按月份汇总。",
            dimension_label="周期",
            metric_label="收入" if _matches(metric, _REVENUE_TOKENS) else _metric_label(metric),
            rows=result.get("rows") or [],
            metric_unit=_unit_for_metric(metric),
            evidence_ref="query_recent_trend",
            evidence_payload_ref="query_recent_trend",
        )
    )
    charts.append(
        ReportEvidenceChart(
            chart_id="trend_changes_intent",
            title="趋势变化图表",
            source_chapter_id="trend_changes",
            chart_type="line",
            description="图表意图：展示最近周期核心指标变化。",
            evidence_ref="query_recent_trend",
        )
    )


def _collect_generic_requirement(
    context: _EvidenceContext,
    db_path: str | Path,
    *,
    requirement: Any,
    time_range: str,
    tables: list[ReportEvidenceTable],
    charts: list[ReportEvidenceChart],
    warnings: list[str],
    data_limits: list[str],
    technical_queries: list[dict[str, Any]],
) -> None:
    if requirement.missing_evidence:
        data_limits.extend(requirement.missing_evidence)
    calculation_type = str(requirement.calculation_type or "")
    if calculation_type == "investment_efficiency":
        _collect_generic_investment_efficiency(
            context,
            db_path,
            requirement=requirement,
            time_range=time_range,
            tables=tables,
            charts=charts,
            data_limits=data_limits,
            technical_queries=technical_queries,
        )
        return

    dimension = _requirement_dimension(context, requirement)
    metric = _requirement_metric(
        context,
        requirement,
        table_name=_field_table(dimension) if dimension else "",
    )
    if not dimension or not metric:
        data_limits.append(f"{requirement.description} 当前缺少可匹配的指标或维度，未生成证据。")
        return
    table_name = _metric_table(metric)
    if not table_name or _field_table(dimension) != table_name:
        data_limits.append(f"{requirement.description} 需要指标和维度位于同一可分析表，当前证据不足。")
        return

    selected_metrics = _metrics_for_generic_requirement(context, requirement, table_name)
    if metric not in selected_metrics:
        selected_metrics.insert(0, metric)
    selected_metrics = [item for item in selected_metrics if _metric_table(item) == table_name and _metric_formula(item)]
    if not selected_metrics:
        data_limits.append(f"{requirement.description} 当前缺少可执行的指标公式，未生成证据。")
        return

    time_filter = _time_filter_clause(
        context,
        table_name,
        time_range=time_range,
        data_limits=data_limits,
        evidence_label=requirement.description,
    )
    dim_col = _field_column(dimension)
    select_parts = [f"{_quote(dim_col)} AS dimension_value"]
    for index, item in enumerate(selected_metrics):
        select_parts.append(f"{_metric_formula(item)} AS metric_value_{index}")
    order_index = _generic_order_metric_index(selected_metrics, calculation_type=calculation_type)
    direction = "ASC" if _metric_lower_is_better(selected_metrics[order_index], calculation_type=calculation_type) else "DESC"
    result = _execute_query(
        context,
        db_path,
        sql=(
            f"SELECT {', '.join(select_parts)} FROM {_quote(table_name)}{time_filter.where_sql} "
            f"GROUP BY {_quote(dim_col)} ORDER BY metric_value_{order_index} {direction}"
        ),
        task={
            "task_type": "rank",
            "metrics": [_metric_label(item) for item in selected_metrics],
            "dimensions": [_label(dimension)],
            "calculation_type": calculation_type,
            "group_by": [_label(dimension)],
        },
        time_range=time_range,
        evidence_ref=f"query_{requirement.requirement_id}",
        technical_queries=technical_queries,
    )
    if not result.get("success"):
        warnings.append(f"{requirement.description} 查询未通过校验或执行失败。")
        return

    metric_labels = [_metric_label(item) for item in selected_metrics]
    rows = []
    for row in result.get("rows") or []:
        record = {_label(dimension) or "业务维度": row[0]}
        for index, label in enumerate(metric_labels):
            value = row[index + 1] if len(row) > index + 1 else None
            record[label] = _format_value(value, unit=_unit_for_metric(selected_metrics[index]))
        rows.append(record)
    tables.append(
        ReportEvidenceTable(
            table_id=requirement.requirement_id,
            title=_generic_table_title(requirement),
            columns=[_label(dimension) or "业务维度", *metric_labels],
            rows=rows,
            source_chapter_id=requirement.chapter_id,
            description=f"证据来自{_readable_table_name(table_name)}按{_label(dimension)}汇总。",
            evidence_ref=f"query_{requirement.requirement_id}",
            evidence_payload_ref=f"query_{requirement.requirement_id}",
        )
    )
    charts.append(
        ReportEvidenceChart(
            chart_id=f"{requirement.requirement_id}_intent",
            title=f"{_generic_table_title(requirement)}图表",
            source_chapter_id=requirement.chapter_id,
            chart_type=requirement.chart_hint or "bar",
            description=f"图表意图：展示{_generic_table_title(requirement)}。",
            evidence_ref=f"query_{requirement.requirement_id}",
        )
    )


def _collect_generic_investment_efficiency(
    context: _EvidenceContext,
    db_path: str | Path,
    *,
    requirement: Any,
    time_range: str,
    tables: list[ReportEvidenceTable],
    charts: list[ReportEvidenceChart],
    data_limits: list[str],
    technical_queries: list[dict[str, Any]],
) -> None:
    registry = context.registry_metrics
    revenue = _first_registry_metric(registry, _REVENUE_TOKENS)
    spend = _first_registry_metric(registry, _COST_TOKENS)
    roas = registry.get("roas") if isinstance(registry.get("roas"), dict) else None
    net_return = registry.get("net_return") if isinstance(registry.get("net_return"), dict) else None
    if not revenue or not spend or not roas or not net_return:
        data_limits.append(
            "跨表投放效率需要收入和投放字段位于同一可分析表，或存在可确认关联字段；"
            "当前证据不足，未计算 ROAS/净投放回报率。"
        )
        return
    table_name = _metric_table(roas)
    if not table_name or _metric_table(revenue) != table_name or _metric_table(spend) != table_name:
        data_limits.append(
            "跨表投放效率需要收入和投放字段位于同一可分析表，或存在可确认关联字段；"
            "当前证据不足，未计算 ROAS/净投放回报率。"
        )
        return
    dimension = _requirement_dimension(context, requirement, table_name=table_name)
    if not dimension:
        data_limits.append("渠道投放表现需要渠道或活动维度，当前证据不足。")
        return
    time_filter = _time_filter_clause(
        context,
        table_name,
        time_range=time_range,
        data_limits=data_limits,
        evidence_label=requirement.description,
    )
    dim_col = _field_column(dimension)
    metrics = [revenue, spend, {**roas, "name": "roas"}, {**net_return, "name": "net_return"}]
    result = _execute_query(
        context,
        db_path,
        sql=(
            f"SELECT {_quote(dim_col)} AS dimension_value, "
            f"{_metric_formula(revenue)} AS revenue_value, "
            f"{_metric_formula(spend)} AS spend_value, "
            f"{_metric_formula(roas)} AS roas_value, "
            f"{_metric_formula(net_return)} AS net_return_value "
            f"FROM {_quote(table_name)}{time_filter.where_sql} "
            f"GROUP BY {_quote(dim_col)} ORDER BY roas_value DESC"
        ),
        task={
            "task_type": "rank",
            "metrics": [_metric_label(item) for item in metrics],
            "dimensions": [_label(dimension)],
            "calculation_type": "investment_efficiency",
            "group_by": [_label(dimension)],
        },
        time_range=time_range,
        evidence_ref=f"query_{requirement.requirement_id}",
        technical_queries=technical_queries,
    )
    if not result.get("success"):
        data_limits.append("渠道投放效率查询未通过校验或执行失败。")
        return
    rows = []
    columns = [_label(dimension) or "渠道", "收入", "投放成本", "广告投入产出比", "净投放回报率"]
    for row in result.get("rows") or []:
        rows.append(
            {
                columns[0]: row[0],
                columns[1]: _format_value(row[1], unit="currency"),
                columns[2]: _format_value(row[2], unit="currency"),
                columns[3]: _format_value(row[3]),
                columns[4]: _format_value(row[4], unit="percentage"),
            }
        )
    tables.append(
        ReportEvidenceTable(
            table_id=requirement.requirement_id,
            title="渠道投放效率",
            columns=columns,
            rows=rows,
            source_chapter_id=requirement.chapter_id,
            description=f"证据来自{_readable_table_name(table_name)}按{_label(dimension)}汇总。",
            evidence_ref=f"query_{requirement.requirement_id}",
            evidence_payload_ref=f"query_{requirement.requirement_id}",
        )
    )
    charts.append(
        ReportEvidenceChart(
            chart_id=f"{requirement.requirement_id}_intent",
            title="渠道投放效率图表",
            source_chapter_id=requirement.chapter_id,
            chart_type=requirement.chart_hint or "bar",
            description="图表意图：展示不同渠道的收入、投放成本和回报效率。",
            evidence_ref=f"query_{requirement.requirement_id}",
        )
    )


def _execute_query(
    context: _EvidenceContext,
    db_path: str | Path,
    *,
    sql: str,
    task: dict[str, Any],
    time_range: str = "",
    evidence_ref: str = "",
    technical_queries: list[dict[str, Any]],
) -> dict[str, Any]:
    validation = validate_sql(sql, context.profile, metric_context={"success": True, "matched_metrics": []})
    if not validation.get("approved"):
        technical_queries.append({"sql": sql, "validation": validation, "execution": {}})
        return {"success": False, "error": "; ".join(validation.get("issues") or [])}
    execution = run_sql(db_path, validation["normalized_sql"], max_rows=20)
    task_for_payload = dict(task)
    if time_range and not task_for_payload.get("time_range"):
        task_for_payload["time_range"] = {"raw_text": time_range}
    payload = build_evidence_payload(
        task=task_for_payload,
        execution_result=execution,
        metric_registry=context.metric_registry,
        sql=validation["normalized_sql"],
        business_aliases=_payload_aliases(task_for_payload),
    )
    if evidence_ref:
        payload["evidence_ref"] = evidence_ref
    technical_queries.append(
        {
            "sql": validation["normalized_sql"],
            "validation": validation,
            "execution": execution,
            "evidence_payload": payload,
        }
    )
    return execution


def _payload_aliases(task: dict[str, Any]) -> dict[str, str]:
    metrics = [str(item) for item in task.get("metrics") or [] if str(item).strip()]
    dimensions = [str(item) for item in task.get("dimensions") or [] if str(item).strip()]
    aliases = {}
    if dimensions:
        aliases["dimension_value"] = dimensions[0]
        aliases["period_value"] = dimensions[0]
        aliases["issue_value"] = dimensions[0]
    if metrics:
        aliases["metric_value"] = metrics[0]
        aliases["total_value"] = metrics[0]
        aliases["ticket_value"] = metrics[0]
    return aliases


def _requirement_dimension(context: _EvidenceContext, requirement: Any, table_name: str = "") -> dict[str, Any] | None:
    dimensions = [
        item
        for item in context.dimensions
        if not table_name or _field_table(item) == table_name
    ]
    requested = [str(item) for item in getattr(requirement, "dimensions", []) or []]
    requested.append(str(getattr(requirement, "dimension_hint", "") or ""))
    for label in requested:
        match = next((dimension for dimension in dimensions if _matches(dimension, (label,))), None)
        if match:
            return match
    return dimensions[0] if dimensions else None


def _requirement_metric(context: _EvidenceContext, requirement: Any, table_name: str = "") -> dict[str, Any] | None:
    requested = [str(item) for item in getattr(requirement, "metrics", []) or []]
    requested.append(str(getattr(requirement, "metric_hint", "") or ""))
    for label in requested:
        match = _first_registry_metric(context.registry_metrics, (label,))
        if match and (not table_name or _metric_table(match) == table_name):
            return match
        match = _first_semantic_metric(context.metrics, (label,))
        if match and (not table_name or _metric_table(match) == table_name):
            return match
    if table_name:
        fallback = _profile_numeric_metric(context, table_name, requested=requested)
        if fallback:
            return fallback
    primary = context.primary_metric()
    if primary and (not table_name or _metric_table(primary) == table_name):
        return primary
    return None


def _metrics_for_generic_requirement(
    context: _EvidenceContext,
    requirement: Any,
    table_name: str,
) -> list[dict[str, Any]]:
    calculation_type = str(getattr(requirement, "calculation_type", "") or "")
    if calculation_type == "operational_efficiency":
        tokens = ("工单", "响应", "满意度", "评分", "ticket", "response", "satisfaction", "score")
        return [
            metric
            for metric in [_first_registry_metric(context.registry_metrics, (token,)) for token in tokens]
            if metric and _metric_table(metric) == table_name
        ]
    requested = [str(item) for item in getattr(requirement, "metrics", []) or [] if str(item).strip()]
    metrics: list[dict[str, Any]] = []
    for label in requested:
        metric = _first_registry_metric(context.registry_metrics, (label,))
        if metric and _metric_table(metric) == table_name:
            metrics.append(metric)
    if not metrics:
        fallback = _profile_numeric_metric(context, table_name, requested=requested)
        if fallback:
            metrics.append(fallback)
    return _unique_metrics(metrics)


def _profile_numeric_metric(
    context: _EvidenceContext,
    table_name: str,
    *,
    requested: list[str],
) -> dict[str, Any] | None:
    table = _profile_table(context.profile, table_name)
    columns = [column for column in table.get("columns") or [] if isinstance(column, dict)]
    requested_text = _compact(" ".join(requested))
    numeric_columns = [column for column in columns if _profile_column_is_numeric(column)]
    if not numeric_columns:
        return None
    preferred = next(
        (
            column
            for column in numeric_columns
            if _matches(column, ("amount", "金额", "销售", "收入", "paid"))
            and (
                any(token in requested_text for token in ("销售", "收入", "金额", "paid", "amount"))
                or not requested_text
            )
        ),
        None,
    )
    preferred = preferred or numeric_columns[0]
    column_name = str(preferred.get("name") or "")
    label = _profile_metric_label(preferred, requested=requested)
    aggregation = "AVG" if _matches(preferred, ("avg", "average", "满意度", "评分", "响应", "时长", "minutes")) else "SUM"
    unit = "currency" if _matches(preferred, ("amount", "金额", "销售", "收入", "paid", "cost", "spend")) else "number"
    return {
        "name": f"{aggregation.lower()}_{column_name}",
        "business_label": label,
        "field": f"{table_name}.{column_name}",
        "formula": f'{aggregation}({_quote(table_name)}.{_quote(column_name)})',
        "unit": unit,
        "source_fields": [f"{table_name}.{column_name}"],
    }


def _profile_column_is_numeric(column: dict[str, Any]) -> bool:
    text = _compact(
        " ".join(
            str(value or "")
            for value in [
                column.get("name"),
                column.get("type"),
                column.get("original_type"),
                column.get("inferred_type"),
                column.get("field_role"),
                *(column.get("business_meaning_candidates") or []),
            ]
        )
    )
    return any(token in text for token in ("real", "integer", "float", "number", "numeric", "amount", "count", "金额", "数量"))


def _profile_metric_label(column: dict[str, Any], *, requested: list[str]) -> str:
    cjk_requested = [item for item in requested if any("\u4e00" <= char <= "\u9fff" for char in item)]
    if cjk_requested:
        return cjk_requested[0]
    if _matches(column, ("response", "响应")):
        return "平均响应时长"
    if _matches(column, ("satisfaction", "满意度", "score", "评分")):
        return "满意度"
    if _matches(column, ("ticket", "工单")):
        return "工单数"
    if _matches(column, ("amount", "paid", "销售", "收入", "金额")):
        return "销售额"
    return str(column.get("label") or column.get("name") or "业务指标")


def _generic_order_metric_index(metrics: list[dict[str, Any]], *, calculation_type: str) -> int:
    if calculation_type == "operational_efficiency":
        for index, metric in enumerate(metrics):
            if _metric_lower_is_better(metric, calculation_type=calculation_type):
                return index
    return 0


def _metric_lower_is_better(metric: dict[str, Any], *, calculation_type: str) -> bool:
    text = _compact(f"{_metric_label(metric)} {metric.get('name')} {metric.get('field')} {calculation_type}")
    return "响应" in text or "时长" in text or "duration" in text or "minutes" in text


def _generic_table_title(requirement: Any) -> str:
    return {
        "store_performance": "门店表现",
        "product_performance": "商品贡献",
        "support_operations": "客服运营效率",
        "channel_investment": "渠道投放效率",
    }.get(str(getattr(requirement, "chapter_id", "") or ""), str(getattr(requirement, "description", "") or "业务证据"))


def _unique_metrics(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen = set()
    for metric in metrics:
        key = str(metric.get("name") or metric.get("field") or metric.get("formula") or "")
        if key and key not in seen:
            seen.add(key)
            unique.append(metric)
    return unique


def _business_safe_evidence_payload(payload: dict[str, Any]) -> dict[str, Any]:
    forbidden_keys = {
        "technical_sql",
        "technical_details",
        "rows",
        "raw_rows",
        "query_id",
        "trace",
        "trace_path",
        "provider_metadata",
        "technical_refs",
    }
    return {
        str(key): _strip_forbidden_payload_values(value, forbidden_keys)
        for key, value in payload.items()
        if str(key) not in forbidden_keys
    }


def _strip_forbidden_payload_values(value: Any, forbidden_keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _strip_forbidden_payload_values(item, forbidden_keys)
            for key, item in value.items()
            if str(key) not in forbidden_keys
        }
    if isinstance(value, list):
        return [_strip_forbidden_payload_values(item, forbidden_keys) for item in value]
    return value


def _time_filter_clause(
    context: _EvidenceContext,
    table_name: str,
    *,
    time_range: str,
    data_limits: list[str],
    evidence_label: str,
) -> _TimeFilter:
    normalized_range = str(time_range or "").strip()
    if normalized_range not in {"最近90天", "最近30天", "本月", "本周"}:
        return _TimeFilter()

    time_field = context.time_field_for_table(table_name)
    if not time_field:
        data_limits.append(
            f"{evidence_label}需要按{normalized_range}读取，但{_readable_table_name(table_name)}缺少时间字段，"
            "未应用时间过滤，结果基于该表可用全量数据。"
        )
        return _TimeFilter()

    time_col = _quote(_field_column(time_field))
    table_ref = _quote(table_name)
    max_date = f"(SELECT MAX(date({time_col})) FROM {table_ref})"
    if normalized_range == "最近90天":
        condition = f"date({time_col}) >= date({max_date}, '-90 days')"
    elif normalized_range == "最近30天":
        condition = f"date({time_col}) >= date({max_date}, '-30 days')"
    elif normalized_range == "本月":
        condition = f"strftime('%Y-%m', date({time_col})) = strftime('%Y-%m', {max_date})"
    else:
        condition = f"date({time_col}) >= date({max_date}, '-7 days')"
    return _TimeFilter(where_sql=f" WHERE {condition}")


def _two_column_table(
    *,
    table_id: str,
    title: str,
    source_chapter_id: str,
    description: str,
    dimension_label: str,
    metric_label: str,
    rows: list[list[Any]],
    metric_unit: str,
    evidence_ref: str,
    evidence_payload_ref: str = "",
) -> ReportEvidenceTable:
    return ReportEvidenceTable(
        table_id=table_id,
        title=title,
        columns=[dimension_label, metric_label],
        rows=[
            {
                dimension_label: row[0] if row else "",
                metric_label: _format_value(row[1] if len(row) > 1 else None, unit=metric_unit),
            }
            for row in rows
        ],
        source_chapter_id=source_chapter_id,
        description=description,
        evidence_ref=evidence_ref,
        evidence_payload_ref=evidence_payload_ref,
    )


def _first_registry_metric(metrics: dict[str, Any], tokens: tuple[str, ...]) -> dict[str, Any] | None:
    for name, metric in metrics.items():
        if not isinstance(metric, dict):
            continue
        normalized = {**metric, "name": metric.get("name") or name}
        if not tokens or _matches(normalized, tokens):
            return normalized
    return None


def _first_semantic_metric(metrics: list[dict[str, Any]], tokens: tuple[str, ...]) -> dict[str, Any] | None:
    return next((metric for metric in metrics if _matches(metric, tokens)), None)


def _metric_formula(metric: dict[str, Any]) -> str:
    return str(metric.get("formula") or "").strip()


def _metric_table(metric: dict[str, Any]) -> str:
    source_fields = [str(item) for item in metric.get("source_fields") or [] if str(item).strip()]
    if source_fields:
        return source_fields[0].split(".", 1)[0]
    field = str(metric.get("field") or "")
    if "." in field:
        return field.split(".", 1)[0]
    formula = _metric_formula(metric)
    match = re.search(r'"([^"]+)"\s*\.\s*"([^"]+)"', formula)
    if match:
        return match.group(1)
    return str(metric.get("table") or "")


def _field_table(item: dict[str, Any]) -> str:
    field = str(item.get("field") or "")
    if "." in field:
        return field.split(".", 1)[0]
    return str(item.get("table") or "")


def _field_column(item: dict[str, Any]) -> str:
    field = str(item.get("field") or "")
    if "." in field:
        return field.split(".", 1)[1]
    return str(item.get("name") or field)


def _first_dimension_column(context: _EvidenceContext, table_name: str) -> str:
    dimension = context.dimension_for_table(table_name)
    return _field_column(dimension) if dimension else ""


def _support_ticket_count_expression(context: _EvidenceContext, table_name: str) -> str:
    table = _profile_table(context.profile, table_name)
    columns = [column for column in table.get("columns") or [] if isinstance(column, dict)]
    explicit_count = next(
        (
            str(column.get("name") or "")
            for column in columns
            if _is_explicit_ticket_count_column(column)
        ),
        "",
    )
    if explicit_count:
        return f"SUM({_quote(explicit_count)})"
    ticket_id = next(
        (
            str(column.get("name") or "")
            for column in columns
            if _is_ticket_id_column(column)
        ),
        "",
    )
    if ticket_id:
        return f"COUNT(DISTINCT {_quote(ticket_id)})"
    return "COUNT(*)"


def _profile_table(profile: dict[str, Any], table_name: str) -> dict[str, Any]:
    return next(
        (
            table
            for table in profile.get("tables") or []
            if isinstance(table, dict) and str(table.get("table_name") or "") == table_name
        ),
        {},
    )


def _source_fields(metric: dict[str, Any]) -> str:
    fields = metric.get("source_fields") or [metric.get("field") or ""]
    return "、".join(str(field) for field in fields if str(field).strip())


def _metric_label(metric: dict[str, Any]) -> str:
    return str(metric.get("business_label") or metric.get("label") or metric.get("name") or "业务指标")


def _label(item: dict[str, Any]) -> str:
    return str(item.get("business_label") or item.get("label") or item.get("name") or item.get("field") or "")


def _unit_for_metric(metric: dict[str, Any]) -> str:
    unit = str(metric.get("unit") or "")
    if unit:
        return unit
    if _matches(metric, _REVENUE_TOKENS):
        return "currency"
    return "number"


def _readable_table_name(table_name: str) -> str:
    lower = table_name.lower()
    if "order" in lower or "sales" in lower or "订单" in table_name:
        return "订单表"
    if "support" in lower or "ticket" in lower or "客服" in table_name or "工单" in table_name:
        return "客服工单表"
    return f"{table_name}表"


def _format_value(value: Any, *, unit: str = "number", suffix: str = "") -> str:
    number = _safe_number(value)
    if number is None:
        return "-" if value is None else str(value)
    if unit == "percentage":
        return f"{number * 100:.1f}%"
    if unit == "currency" and abs(number) >= 10000:
        return f"{number / 10000:.1f} 万"
    if float(number).is_integer():
        return f"{int(number)}{suffix}"
    return f"{number:.2f}".rstrip("0").rstrip(".") + suffix


def _safe_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _matches(item: dict[str, Any], tokens: tuple[str, ...]) -> bool:
    text = " ".join(
        str(value or "")
        for value in [
            item.get("table_name"),
            item.get("name"),
            item.get("label"),
            item.get("business_label"),
            item.get("field"),
            item.get("table"),
            *(item.get("aliases") or []),
            *(item.get("meanings") or []),
            *(item.get("business_meaning_candidates") or []),
        ]
    )
    compact = _compact(text)
    return any(_compact(token) in compact for token in tokens)


def _is_explicit_ticket_count_column(column: dict[str, Any]) -> bool:
    compact = _compact(
        " ".join(
            str(value or "")
            for value in [
                column.get("name"),
                column.get("label"),
                column.get("business_label"),
                *(column.get("aliases") or []),
                *(column.get("meanings") or []),
                *(column.get("business_meaning_candidates") or []),
            ]
        )
    )
    if _is_id_like_compact(compact):
        return False
    explicit_tokens = ("ticketcount", "ticketscount", "工单数", "工单量", "数量")
    return compact == "count" or any(token in compact for token in explicit_tokens)


def _is_ticket_id_column(column: dict[str, Any]) -> bool:
    compact = _compact(
        " ".join(
            str(value or "")
            for value in [
                column.get("name"),
                column.get("label"),
                column.get("business_label"),
                *(column.get("aliases") or []),
                *(column.get("meanings") or []),
                *(column.get("business_meaning_candidates") or []),
            ]
        )
    )
    return ("ticket" in compact or "工单" in compact) and _is_id_like_compact(compact)


def _is_id_like_compact(compact: str) -> bool:
    return "id" in compact or "编号" in compact or compact.endswith("号")


def _compact(value: Any) -> str:
    return re.sub(r"[\s_\-]+", "", str(value).lower())


def _quote(identifier: str) -> str:
    return '"' + str(identifier).replace('"', '""') + '"'


_REVENUE_TOKENS = ("revenue_like", "sales_like", "gmv_like", "revenue", "sales", "收入", "营收", "销售额", "营业额", "成交额")
_COST_TOKENS = ("cost", "spend", "expense", "ad_spend", "marketing_spend", "成本", "花费", "消耗", "投放")
_ROI_TOKENS = ("roi", "roas", "return_on_investment", "投产比", "投资回报", "回报率", "roi_like", "roas_like")
_PROFIT_TOKENS = ("profit", "margin", "gross_margin", "net_profit", "利润", "毛利", "净利", "利润率", "毛利率")
_RETENTION_TOKENS = ("retention", "repeat", "repurchase", "repeat_purchase", "复购", "留存", "回购")
_CUSTOMER_TOKENS = ("customer", "client", "member", "segment", "客户", "会员", "客群", "人群", "分群")
_SUPPORT_TOKENS = ("support", "ticket", "issue", "complaint", "response", "satisfaction", "客服", "工单", "问题", "投诉", "响应", "满意度")
_ISSUE_TOKENS = ("issue", "problem", "complaint", "type", "问题", "投诉", "类型")
_TICKET_COUNT_TOKENS = ("ticket_count", "tickets", "工单数", "工单量")
_SATISFACTION_TOKENS = ("satisfaction", "score", "rating", "满意度", "评分")
_RESPONSE_TOKENS = ("response", "响应", "响应时长", "avg_response")
