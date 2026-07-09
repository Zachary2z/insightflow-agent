from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from workspaces.chart_static_export import export_chart_static_asset
from workspaces.models import utc_now_iso


EXPORT_PACKAGE_VERSION = "p34.export_package.v1"
SOURCE_ANALYSIS = "analysis"
SOURCE_REPORT = "report"

_CHART_EXPORT_FIELDS = {
    "artifact_id",
    "chart_id",
    "chart_ids",
    "title",
    "renderer",
    "chart_type",
    "path",
    "url",
    "image_path",
    "image_url",
    "rendering_status",
    "business_annotation",
    "evidence_refs",
    "source_chapter_id",
    "source",
    "data_row_count",
    "echarts_option",
}


@dataclass
class ExportPackage:
    package_id: str
    workspace_id: str
    source_type: str
    source_id: str
    title: str
    generated_at: str
    language: str = "zh"
    document: dict[str, Any] = field(default_factory=dict)
    business_answer: dict[str, Any] = field(default_factory=dict)
    business_content_summary: str = ""
    sections: list[dict[str, Any]] = field(default_factory=list)
    action_recommendations: list[str] = field(default_factory=list)
    data_boundaries: list[str] = field(default_factory=list)
    chart_artifacts: list[dict[str, Any]] = field(default_factory=list)
    static_assets: list[dict[str, Any]] = field(default_factory=list)
    markdown_path: str = ""
    document_path: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    evidence_tables: list[dict[str, Any]] = field(default_factory=list)
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    package_version: str = EXPORT_PACKAGE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_report_export_package(
    report_record: Any,
    *,
    workspace_root: str | Path | None = None,
    static_asset_target_format: str | None = None,
) -> ExportPackage:
    report = _to_dict(report_record)
    workspace_id = _text(report.get("workspace_id"))
    report_id = _text(report.get("report_id"))
    document = _report_document(report.get("document") if isinstance(report.get("document"), dict) else {})
    report_charts = _merge_report_chart_metadata(
        report.get("chart_artifacts") if isinstance(report.get("chart_artifacts"), list) else [],
        report,
    )
    chart_artifacts, static_assets, chart_warnings = _export_chart_artifacts(
        report_charts,
        workspace_root=workspace_root,
        target_format=static_asset_target_format,
    )
    artifact_paths = _report_artifact_paths(report)
    markdown_path = _safe_path(
        artifact_paths.get("markdown_path") or report.get("markdown_path"),
        workspace_root=workspace_root,
    )
    document_path = _safe_path(
        artifact_paths.get("document_path") or report.get("json_path"),
        workspace_root=workspace_root,
    )
    evidence_refs = _unique_texts(
        [
            *_report_evidence_refs(report),
            *_chart_evidence_refs(chart_artifacts),
            *_artifact_evidence_refs(report.get("artifacts") if isinstance(report.get("artifacts"), list) else []),
        ]
    )
    warnings = _unique_texts(
        [
            *chart_warnings,
            *_report_warnings(report),
        ]
    )
    return ExportPackage(
        package_id=f"export_report_{report_id}",
        workspace_id=workspace_id,
        source_type=SOURCE_REPORT,
        source_id=report_id,
        title=_text(report.get("title")) or _text(document.get("title")) or "报告导出包",
        generated_at=_text(report.get("updated_at")) or _text(report.get("created_at")) or utc_now_iso(),
        document=document,
        business_answer={},
        business_content_summary=_text(document.get("opening_summary")),
        sections=list(document.get("sections") or []),
        action_recommendations=_list_of_text(document.get("action_recommendations")),
        data_boundaries=_list_of_text(document.get("data_boundaries")),
        chart_artifacts=chart_artifacts,
        static_assets=static_assets,
        markdown_path=markdown_path,
        document_path=document_path,
        evidence_refs=evidence_refs,
        evidence_tables=_report_evidence_tables(report),
        evidence_summary=_report_evidence_summary(report, evidence_refs=evidence_refs),
        warnings=warnings,
    )


def build_analysis_export_package(
    product_result: dict[str, Any],
    *,
    workspace_root: str | Path | None = None,
) -> ExportPackage:
    result = product_result if isinstance(product_result, dict) else {}
    workspace_id = _text(result.get("workspace_id"))
    run_id = _text(result.get("run_id"))
    business_answer = _business_answer_summary(
        result.get("business_answer") if isinstance(result.get("business_answer"), dict) else {}
    )
    chart_artifacts, static_assets, chart_warnings = _export_chart_artifacts(
        result.get("chart_artifacts") if isinstance(result.get("chart_artifacts"), list) else [],
        workspace_root=workspace_root,
    )
    evidence_refs = _unique_texts(
        [
            *_analysis_evidence_refs(result.get("evidence") if isinstance(result.get("evidence"), dict) else {}),
            *_chart_evidence_refs(chart_artifacts),
        ]
    )
    title = _text(business_answer.get("headline")) or "分析导出包"
    data_boundaries = _list_of_text(business_answer.get("caveats"))
    return ExportPackage(
        package_id=f"export_run_{run_id}",
        workspace_id=workspace_id,
        source_type=SOURCE_ANALYSIS,
        source_id=run_id,
        title=title,
        generated_at=_text(result.get("created_at")) or _text(result.get("updated_at")) or utc_now_iso(),
        document={
            "title": title,
            "summary": _text(business_answer.get("direct_answer")) or _text(business_answer.get("headline")),
            "type": "analysis_answer",
        },
        business_answer=business_answer,
        business_content_summary=_text(business_answer.get("direct_answer")) or _text(business_answer.get("headline")),
        sections=[],
        action_recommendations=_list_of_text(business_answer.get("recommendations")),
        data_boundaries=data_boundaries,
        chart_artifacts=chart_artifacts,
        static_assets=static_assets,
        evidence_refs=evidence_refs,
        evidence_summary=_analysis_evidence_summary(
            result.get("evidence") if isinstance(result.get("evidence"), dict) else {},
            evidence_refs=evidence_refs,
        ),
        warnings=chart_warnings,
    )


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        data = to_dict()
        return data if isinstance(data, dict) else {}
    return {}


def _report_document(document: dict[str, Any]) -> dict[str, Any]:
    sections = []
    for section in document.get("sections") or []:
        if not isinstance(section, dict):
            continue
        sections.append(
            {
                "section_id": _text(section.get("section_id")),
                "title": _text(section.get("title")),
                "body": _text(section.get("body")),
                "chart_refs": _list_of_text(section.get("chart_refs")),
                "evidence_refs": _list_of_text(section.get("evidence_refs")),
            }
        )
    return {
        "title": _text(document.get("title")),
        "time_range": _text(document.get("time_range")),
        "data_sources": _list_of_text(document.get("data_sources")),
        "opening_summary": _text(document.get("opening_summary")),
        "sections": sections,
        "action_recommendations": _list_of_text(document.get("action_recommendations")),
        "data_boundaries": _list_of_text(document.get("data_boundaries")),
    }


def _business_answer_summary(answer: dict[str, Any]) -> dict[str, Any]:
    return {
        "headline": _text(answer.get("headline")),
        "direct_answer": _text(answer.get("direct_answer")),
        "why": _text(answer.get("why")),
        "evidence_bullets": _list_of_text(answer.get("evidence_bullets")),
        "recommendations": _list_of_text(answer.get("recommendations")),
        "caveats": _list_of_text(answer.get("caveats")),
        "confidence": _text(answer.get("confidence")) or "medium",
    }


def _export_chart_artifacts(
    artifacts: list[Any],
    *,
    workspace_root: str | Path | None,
    target_format: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    exported: list[dict[str, Any]] = []
    static_assets: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            continue
        chart = _export_chart_artifact(item, workspace_root=workspace_root, index=index)
        static_result = export_chart_static_asset(
            chart,
            workspace_root=workspace_root,
            target_format=target_format,
        )
        if static_result.get("success") and isinstance(static_result.get("asset"), dict):
            static_asset = _sanitize_static_asset(static_result["asset"])
            if static_asset:
                static_assets.append(static_asset)
            updated_chart = static_result.get("chart_artifact") if isinstance(static_result.get("chart_artifact"), dict) else {}
            if updated_chart:
                chart = _export_chart_artifact(updated_chart, workspace_root=workspace_root, index=index)
        else:
            chart_id = _text(chart.get("artifact_id")) or _text(chart.get("title")) or f"chart_{index + 1}"
            static_warnings = _list_of_text(static_result.get("warnings") if isinstance(static_result, dict) else [])
            warnings.extend(static_warnings or [f"图表 {chart_id} 缺少静态 image fallback；Web 可使用 echarts_option，外部平台/Markdown/静态导出需补充 image_url/path。"])
        exported.append(chart)
    return exported, static_assets, warnings


def _merge_report_chart_metadata(artifacts: list[Any], report: dict[str, Any]) -> list[dict[str, Any]]:
    metadata_by_key = _report_chart_metadata_by_key(report)
    merged: list[dict[str, Any]] = []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        chart = dict(item)
        metadata = _matching_chart_metadata(chart, metadata_by_key)
        if metadata:
            chart_id = _text(metadata.get("chart_id"))
            if chart_id and not _text(chart.get("chart_id")):
                chart["chart_id"] = chart_id
            if chart_id and not _list_of_text(chart.get("chart_ids")):
                chart["chart_ids"] = [chart_id]
            source_chapter_id = _text(metadata.get("source_chapter_id"))
            if source_chapter_id and not _text(chart.get("source_chapter_id")):
                chart["source_chapter_id"] = source_chapter_id
        merged.append(chart)
    return merged


def _report_chart_metadata_by_key(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence_pack = report.get("evidence_pack") if isinstance(report.get("evidence_pack"), dict) else {}
    metadata_by_key: dict[str, dict[str, Any]] = {}
    for chart in evidence_pack.get("charts") or []:
        if not isinstance(chart, dict):
            continue
        for key in [_text(chart.get("artifact_id")), _text(chart.get("chart_id"))]:
            if key:
                metadata_by_key.setdefault(key, chart)
    return metadata_by_key


def _matching_chart_metadata(chart: dict[str, Any], metadata_by_key: dict[str, dict[str, Any]]) -> dict[str, Any]:
    keys = [
        _text(chart.get("artifact_id")),
        _text(chart.get("chart_id")),
        *_list_of_text(chart.get("chart_ids")),
    ]
    for key in keys:
        if key and key in metadata_by_key:
            return metadata_by_key[key]
    return {}


def _export_chart_artifact(
    artifact: dict[str, Any],
    *,
    workspace_root: str | Path | None,
    index: int,
) -> dict[str, Any]:
    exported: dict[str, Any] = {}
    for key in _CHART_EXPORT_FIELDS:
        if key not in artifact:
            continue
        value = artifact.get(key)
        if key in {"path", "image_path"}:
            safe = _safe_path(value, workspace_root=workspace_root)
            if safe:
                exported[key] = safe
            continue
        if key in {"url", "image_url"}:
            safe = _safe_url(value)
            if safe:
                exported[key] = safe
            continue
        if key in {"chart_ids", "evidence_refs"}:
            exported[key] = _list_of_text(value)
            continue
        if key == "data_row_count":
            try:
                exported[key] = int(value)
            except (TypeError, ValueError):
                pass
            continue
        if key == "echarts_option":
            if isinstance(value, dict) and value:
                exported[key] = _sanitize_value(value)
            continue
        text_value = _text(value)
        if text_value:
            exported[key] = text_value

    if not exported.get("artifact_id"):
        exported["artifact_id"] = f"chart_export_{index + 1}"
    if not exported.get("title"):
        exported["title"] = "导出图表"
    if not exported.get("renderer"):
        exported["renderer"] = "image" if _chart_has_static_fallback(exported) else "echarts"
    if not exported.get("chart_type"):
        exported["chart_type"] = _infer_chart_type(exported)
    if not exported.get("image_path") and exported.get("path"):
        exported["image_path"] = exported["path"]
    if not exported.get("image_url") and exported.get("url"):
        exported["image_url"] = exported["url"]
    if not exported.get("rendering_status"):
        exported["rendering_status"] = "rendered" if _chart_has_static_fallback(exported) or exported.get("echarts_option") else "not_rendered"
    if not exported.get("source"):
        exported["source"] = "unknown"
    if "data_row_count" not in exported:
        exported["data_row_count"] = 0
    return exported


def _sanitize_static_asset(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": _text(asset.get("asset_id")),
        "asset_type": _text(asset.get("asset_type")) or "chart_image",
        "title": _text(asset.get("title")),
        "path": _safe_path(asset.get("path"), workspace_root=None),
        "url": _safe_url(asset.get("url")),
        "format": _text(asset.get("format")),
        "source": _text(asset.get("source")),
        "rendering_status": _text(asset.get("rendering_status")),
        "generated": bool(asset.get("generated", False)),
    }


def _chart_has_static_fallback(chart: dict[str, Any]) -> bool:
    return bool(chart.get("image_path") or chart.get("image_url") or chart.get("path") or chart.get("url"))


def _infer_chart_type(chart: dict[str, Any]) -> str:
    path = f"{chart.get('image_path') or ''} {chart.get('path') or ''}".lower()
    if ".svg" in path:
        return "svg"
    if ".png" in path:
        return "png"
    return ""


def _report_artifact_paths(report: dict[str, Any]) -> dict[str, str]:
    paths: dict[str, str] = {}
    for artifact in report.get("artifacts") or []:
        if not isinstance(artifact, dict):
            continue
        artifact_type = _text(artifact.get("artifact_type"))
        if artifact_type == "markdown_report" and not paths.get("markdown_path"):
            paths["markdown_path"] = _text(artifact.get("relative_path"))
        if artifact_type == "report_document" and not paths.get("document_path"):
            paths["document_path"] = _text(artifact.get("relative_path"))
    return paths


def _report_evidence_refs(report: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    document = report.get("document") if isinstance(report.get("document"), dict) else {}
    for section in document.get("sections") or []:
        if isinstance(section, dict):
            refs.extend(_list_of_text(section.get("evidence_refs")))
            refs.extend(_list_of_text(section.get("chart_refs")))

    evidence_pack = report.get("evidence_pack") if isinstance(report.get("evidence_pack"), dict) else {}
    for fact in evidence_pack.get("facts") or []:
        if isinstance(fact, dict):
            refs.extend([_text(fact.get("fact_id")), _text(fact.get("evidence_ref"))])
    for table in evidence_pack.get("tables") or []:
        if isinstance(table, dict):
            refs.extend([_text(table.get("table_id")), _text(table.get("evidence_ref")), _text(table.get("evidence_payload_ref"))])
    for chart in evidence_pack.get("charts") or []:
        if isinstance(chart, dict):
            refs.extend([_text(chart.get("chart_id")), *_list_of_text(chart.get("evidence_refs"))])
    return _unique_texts(refs)


def _report_warnings(report: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    evidence_pack = report.get("evidence_pack") if isinstance(report.get("evidence_pack"), dict) else {}
    warnings.extend(_list_of_text(evidence_pack.get("warnings")))
    validation = report.get("validation") if isinstance(report.get("validation"), dict) else {}
    warnings.extend(_list_of_text(validation.get("warnings")))
    return _unique_texts(warnings)


def _report_evidence_summary(report: dict[str, Any], *, evidence_refs: list[str]) -> dict[str, Any]:
    evidence_pack = report.get("evidence_pack") if isinstance(report.get("evidence_pack"), dict) else {}
    ledger = evidence_pack.get("ledger") if isinstance(evidence_pack.get("ledger"), dict) else {}
    return {
        "fact_count": len(evidence_pack.get("facts") or []),
        "table_count": len(evidence_pack.get("tables") or []),
        "chart_count": len(evidence_pack.get("charts") or []),
        "ledger_fact_count": len(ledger.get("facts") or []),
        "ledger_metric_count": len(ledger.get("derived_metrics") or []),
        "refs": list(evidence_refs),
        "data_boundaries": _list_of_text(evidence_pack.get("data_limits")),
        "warnings": _list_of_text(evidence_pack.get("warnings")),
    }


def _report_evidence_tables(report: dict[str, Any]) -> list[dict[str, Any]]:
    evidence_pack = report.get("evidence_pack") if isinstance(report.get("evidence_pack"), dict) else {}
    tables: list[dict[str, Any]] = []
    for index, table in enumerate(evidence_pack.get("tables") or []):
        if not isinstance(table, dict):
            continue
        columns = _list_of_text(table.get("columns"))
        rows: list[dict[str, str]] = []
        for row in table.get("rows") or []:
            if not isinstance(row, dict):
                continue
            cleaned_row = {
                column: _text(row.get(column))
                for column in columns
                if _text(row.get(column))
            }
            if cleaned_row:
                rows.append(cleaned_row)
        if not columns or not rows:
            continue
        tables.append(
            {
                "table_id": _text(table.get("table_id")) or f"evidence_table_{index + 1}",
                "title": _text(table.get("title")) or "证据表",
                "columns": columns,
                "rows": rows,
                "source_chapter_id": _text(table.get("source_chapter_id")),
                "description": _text(table.get("description")),
                "evidence_ref": _text(table.get("evidence_ref")),
                "evidence_payload_ref": _text(table.get("evidence_payload_ref")),
            }
        )
    return tables


def _artifact_evidence_refs(artifacts: list[Any]) -> list[str]:
    refs: list[str] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        refs.extend(_list_of_text(artifact.get("evidence_ids")))
        refs.extend(_list_of_text(artifact.get("ledger_metric_ids")))
        refs.extend(_list_of_text(artifact.get("chart_ids")))
    return refs


def _analysis_evidence_refs(evidence: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    if isinstance(evidence.get("question_evidence"), dict):
        refs.append("question_evidence_pack")
    ledger = evidence.get("ledger_summary") if isinstance(evidence.get("ledger_summary"), dict) else {}
    refs.extend(_list_of_text(ledger.get("refs")))
    refs.extend(_list_of_text(ledger.get("evidence_refs")))
    fact_payload = evidence.get("fact_payload") if isinstance(evidence.get("fact_payload"), dict) else {}
    for row in fact_payload.get("result_rows") or []:
        if isinstance(row, dict):
            refs.append(_text(row.get("evidence_ref")))
    return _unique_texts(refs)


def _analysis_evidence_summary(evidence: dict[str, Any], *, evidence_refs: list[str]) -> dict[str, Any]:
    ledger = evidence.get("ledger_summary") if isinstance(evidence.get("ledger_summary"), dict) else {}
    return {
        "validation_status": _text(evidence.get("validation_status")),
        "notes": _list_of_text(evidence.get("evidence_notes")),
        "fact_count": len(ledger.get("facts") or []),
        "derived_metric_count": len(ledger.get("derived_metrics") or []),
        "chart_refs": _list_of_text(ledger.get("chart_refs")),
        "data_limits": _list_of_text(ledger.get("data_limits") or ledger.get("business_data_limits")),
        "refs": list(evidence_refs),
    }


def _chart_evidence_refs(chart_artifacts: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for chart in chart_artifacts:
        refs.extend(_list_of_text(chart.get("evidence_refs")))
    return refs


def _safe_path(value: Any, *, workspace_root: str | Path | None) -> str:
    text = _text(value)
    if not text:
        return ""
    if _unsafe_relative_path(text):
        return ""
    path = Path(text)
    if not path.is_absolute():
        return path.as_posix()
    if not workspace_root:
        return ""
    try:
        return path.resolve().relative_to(Path(workspace_root).resolve()).as_posix()
    except (OSError, ValueError):
        return ""


def _safe_url(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if _url_has_secret_marker(text):
        return ""
    if text.startswith("/api/") or text.startswith("http://") or text.startswith("https://"):
        return text
    return ""


def _unsafe_relative_path(value: str) -> bool:
    text = value.strip()
    if text.startswith("~"):
        return True
    path = Path(text)
    return any(part == ".." for part in path.parts)


def _url_has_secret_marker(value: str) -> bool:
    secret_keys = {"api_key", "apikey", "access_key", "access_token", "token", "secret", "password", "key"}
    lower = value.lower()
    if any(marker in lower for marker in ("api_key=", "access_token=", "token=", "secret=", "password=")):
        return True
    try:
        parsed = urlsplit(value)
    except ValueError:
        return True
    return any(key.lower() in secret_keys for key, _ in parse_qsl(parsed.query, keep_blank_values=True))


def _list_of_text(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]


def _unique_texts(values: list[str]) -> list[str]:
    return list(dict.fromkeys([_text(value) for value in values if _text(value)]))


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
        return "" if _contains_sensitive_text(text) else text
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return ""


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            safe_key = str(key)
            if _contains_sensitive_text(safe_key):
                continue
            sanitized = _sanitize_value(item)
            if sanitized in ("", [], {}):
                continue
            cleaned[safe_key] = sanitized
        return cleaned
    if isinstance(value, list):
        return [item for item in (_sanitize_value(item) for item in value) if item not in ("", [], {})]
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, bool | int | float) or value is None:
        return value
    return ""


def _contains_sensitive_text(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    lowered = text.lower()
    if re.search(r"\b(?:select|with|insert|update|delete|drop|alter|create|pragma)\b", text, re.IGNORECASE):
        return True
    if re.search(r"(^|[=/\s])(?:/users/|/tmp/|~[/\\])", lowered):
        return True
    if re.search(r"\b(?:raw_sql|generated_sql|raw_rows|trace_path|trace_id|provider_metadata|api_key|apikey|access_key|access_token|secret|password|database_path|analysis\.db|task_id|task_purpose|debug_id|prompt(?:_id|_text|_version)?|completion_tokens|prompt_tokens)\b", lowered):
        return True
    if re.search(r"\bsk-[A-Za-z0-9_-]+", text):
        return True
    return False
