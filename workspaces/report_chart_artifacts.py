from __future__ import annotations

import re
from typing import Any

from visualization.echarts_option_builder import SUPPORTED_ECHARTS_TYPES, build_echarts_option
from workspaces.report_models import ReportEvidenceChart, ReportEvidencePack, ReportEvidenceTable


def build_report_chart_artifacts(
    *,
    evidence_pack: ReportEvidencePack,
    workspace_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tables_by_ref = {table.evidence_ref: table for table in evidence_pack.tables if table.rows}
    artifacts: list[dict[str, Any]] = []
    trace_events: list[dict[str, Any]] = []
    for chart in evidence_pack.charts:
        artifact, trace_event = _artifact_from_chart(
            chart=chart,
            table=tables_by_ref.get(chart.evidence_ref),
            workspace_id=workspace_id,
        )
        if artifact:
            artifacts.append(artifact)
        if trace_event:
            trace_events.append(trace_event)
    return artifacts, trace_events


def _artifact_from_chart(
    *,
    chart: ReportEvidenceChart,
    table: ReportEvidenceTable | None,
    workspace_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    artifact_id = chart.artifact_id or f"artifact_chart_{chart.chart_id or _safe_id(chart.title)}"
    chart.artifact_id = artifact_id
    image_path = chart.image_path or chart.path
    image_url = chart.image_url or chart.url or _artifact_url(workspace_id, image_path)
    if image_path and not chart.image_path:
        chart.image_path = image_path
    if image_url and not chart.image_url:
        chart.image_url = image_url
    if image_url and not chart.url:
        chart.url = image_url

    if not table:
        artifact = _base_artifact(
            chart=chart,
            artifact_id=artifact_id,
            renderer="image" if image_path else "intent",
            chart_spec={},
            image_path=image_path,
            image_url=image_url,
            data_row_count=0,
        )
        artifact["rendering_status"] = "rendered" if image_path else "not_rendered"
        _apply_to_chart(chart, artifact)
        return artifact, {}

    chart_spec = _chart_spec(chart=chart, table=table)
    execution_result = _execution_result(table=table, chart_spec=chart_spec)
    option_result = build_echarts_option(
        chart_spec,
        execution_result,
        unit=str(chart_spec.get("unit") or ""),
        value_label=str(chart_spec.get("y") or ""),
    )
    if option_result.get("success") and isinstance(option_result.get("echarts_option"), dict):
        artifact = _base_artifact(
            chart=chart,
            artifact_id=artifact_id,
            renderer="echarts",
            chart_spec=chart_spec,
            image_path=image_path,
            image_url=image_url,
            data_row_count=int(option_result.get("data_row_count") or len(table.rows)),
        )
        artifact["echarts_option"] = option_result["echarts_option"]
        artifact["rendering_status"] = "rendered"
        _apply_to_chart(chart, artifact)
        return artifact, {
            "event": "report_chart_artifact_built",
            "artifact_id": artifact_id,
            "chart_id": chart.chart_id,
            "renderer": "echarts",
            "source": "report_center",
        }

    reason = str(
        option_result.get("validation_error")
        or option_result.get("fallback_reason")
        or "echarts option unavailable"
    )
    artifact = _base_artifact(
        chart=chart,
        artifact_id=artifact_id,
        renderer="image" if image_path else "intent",
        chart_spec=chart_spec,
        image_path=image_path,
        image_url=image_url,
        data_row_count=len(table.rows),
    )
    artifact["rendering_status"] = "rendered" if image_path else "not_rendered"
    _apply_to_chart(chart, artifact)
    return artifact, {
        "event": "report_chart_artifact_echarts_fallback",
        "artifact_id": artifact_id,
        "chart_id": chart.chart_id,
        "renderer": artifact["renderer"],
        "source": "report_center",
        "echarts_fallback_reason": reason,
    }


def _base_artifact(
    *,
    chart: ReportEvidenceChart,
    artifact_id: str,
    renderer: str,
    chart_spec: dict[str, Any],
    image_path: str,
    image_url: str,
    data_row_count: int,
) -> dict[str, Any]:
    evidence_refs = _evidence_refs(chart)
    return {
        "artifact_id": artifact_id,
        "title": chart.title or chart_spec.get("title") or "报告图表",
        "renderer": renderer,
        "chart_type": str(chart_spec.get("chart_type") or chart.chart_type or ""),
        "chart_spec": dict(chart_spec),
        "path": image_path,
        "url": image_url,
        "image_path": image_path,
        "image_url": image_url,
        "rendering_status": "rendered" if image_path else "not_rendered",
        "unit": str(chart_spec.get("unit") or ""),
        "value_label": bool(chart_spec.get("value_label", False)),
        "business_annotation": str(chart_spec.get("business_annotation") or chart.description or ""),
        "evidence_refs": evidence_refs,
        "source": "report_center",
        "data_row_count": data_row_count,
    }


def _apply_to_chart(chart: ReportEvidenceChart, artifact: dict[str, Any]) -> None:
    chart.artifact_id = str(artifact.get("artifact_id") or chart.artifact_id)
    chart.renderer = str(artifact.get("renderer") or "")
    chart.chart_type = str(artifact.get("chart_type") or chart.chart_type)
    chart.chart_spec = dict(artifact.get("chart_spec") or {})
    chart.echarts_option = dict(artifact.get("echarts_option") or {})
    chart.path = str(artifact.get("path") or "")
    chart.url = str(artifact.get("url") or "")
    chart.image_path = str(artifact.get("image_path") or "")
    chart.image_url = str(artifact.get("image_url") or "")
    chart.rendering_status = str(artifact.get("rendering_status") or "")
    chart.unit = str(artifact.get("unit") or "")
    chart.value_label = bool(artifact.get("value_label", False))
    chart.business_annotation = str(artifact.get("business_annotation") or "")
    chart.evidence_refs = [str(item) for item in artifact.get("evidence_refs", [])]
    chart.source = "report_center"
    chart.data_row_count = int(artifact.get("data_row_count") or 0)


def _chart_spec(*, chart: ReportEvidenceChart, table: ReportEvidenceTable) -> dict[str, Any]:
    columns = [str(column) for column in table.columns if str(column).strip()]
    x = columns[0] if columns else ""
    y = _first_numeric_column(table, start=1) or (columns[-1] if len(columns) > 1 else "")
    chart_type = str(chart.chart_type or "").strip().lower()
    if chart_type not in SUPPORTED_ECHARTS_TYPES:
        chart_type = "line" if "趋势" in chart.title or "趋势" in table.title else "bar"
    return {
        "success": True,
        "source": "report_center",
        "chart_type": chart_type,
        "title": chart.title or table.title or "报告图表",
        "x": x,
        "y": y,
        "required_columns": [column for column in [x, y] if column],
        "unit": _unit_for_column(table, y),
        "value_label": True,
        "business_annotation": _business_annotation(chart=chart, table=table),
    }


def _execution_result(*, table: ReportEvidenceTable, chart_spec: dict[str, Any]) -> dict[str, Any]:
    columns = list(table.columns)
    numeric_columns = {
        str(chart_spec.get("y") or ""),
        str(chart_spec.get("y_secondary") or ""),
    }
    rows = []
    for row in table.rows:
        values = []
        for column in columns:
            value = row.get(column)
            values.append(_display_number(value) if column in numeric_columns else value)
        rows.append(values)
    return {"success": True, "columns": columns, "rows": rows}


def _first_numeric_column(table: ReportEvidenceTable, *, start: int = 0) -> str:
    for column in table.columns[start:]:
        if any(_display_number(row.get(column)) is not None for row in table.rows):
            return str(column)
    return ""


def _display_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0))


def _unit_for_column(table: ReportEvidenceTable, column: str) -> str:
    sample = " ".join(str(row.get(column) or "") for row in table.rows[:5])
    if "万" in sample and ("收入" in column or "金额" in column or "成本" in column or "投放" in column):
        return "万元"
    if "%" in sample:
        return "%"
    if "分钟" in sample:
        return "分钟"
    if "收入" in column or "金额" in column or "成本" in column or "投放" in column:
        return "元"
    return ""


def _business_annotation(*, chart: ReportEvidenceChart, table: ReportEvidenceTable) -> str:
    if chart.business_annotation:
        return chart.business_annotation
    rows = table.rows
    first_column = table.columns[0] if table.columns else ""
    first_value = str(rows[0].get(first_column) or "").strip() if rows and first_column else ""
    if first_value:
        return f"{first_value}在{table.title or chart.title}中位居前列，请结合报告正文判断业务动作。"
    return chart.description.replace("图表意图：", "").strip() or f"图表基于{table.title or '报告证据表'}生成。"


def _evidence_refs(chart: ReportEvidenceChart) -> list[str]:
    return list(
        dict.fromkeys(
            [
                item
                for item in [
                    chart.evidence_ref,
                    *chart.evidence_ids,
                    *chart.ledger_metric_ids,
                ]
                if str(item).strip()
            ]
        )
    )


def _artifact_url(workspace_id: str, path: str) -> str:
    if not path:
        return ""
    if path.startswith("/api/") or path.startswith("http://") or path.startswith("https://"):
        return path
    return f"/api/workspaces/{workspace_id}/artifacts/{path.strip('/')}"


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "")).strip("_")
    return safe or "report_chart"
