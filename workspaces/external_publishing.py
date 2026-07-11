from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from workspaces.cli_output import safe_cli_text as _safe_text
from workspaces.cli_output import safe_cli_text_list as _safe_text_list
from workspaces.cli_output import safe_tool_call as _safe_tool_call
from workspaces.export_package import EXPORT_PACKAGE_VERSION, SOURCE_REPORT
from workspaces.models import utc_now_iso
from workspaces.safe_output import safe_int as _safe_int
from workspaces.safe_output import safe_url


PublishStatus = Literal["published", "warning", "failed"]


@dataclass
class ExternalPublishResult:
    platform: str
    status: PublishStatus
    title: str
    url: str | None = None
    document_id: str | None = None
    external_id: str | None = None
    created_at: str | None = None
    inserted_chart_count: int = 0
    failed_chart_count: int = 0
    sheet_url: str | None = None
    sheet_id: str | None = None
    spreadsheet_token: str | None = None
    written_table_count: int = 0
    native_chart_count: int = 0
    sheet_warnings: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_safe_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["platform"] = _safe_text(data.get("platform")) or "external"
        data["status"] = data["status"] if data.get("status") in {"published", "warning", "failed"} else "failed"
        data["title"] = _safe_text(data.get("title"))
        data["url"] = _safe_url(data.get("url"))
        data["document_id"] = _safe_text(data.get("document_id")) or None
        data["external_id"] = _safe_text(data.get("external_id")) or None
        data["created_at"] = _safe_text(data.get("created_at")) or None
        data["inserted_chart_count"] = _safe_int(data.get("inserted_chart_count"))
        data["failed_chart_count"] = _safe_int(data.get("failed_chart_count"))
        data["sheet_url"] = _safe_url(data.get("sheet_url"))
        data["sheet_id"] = _safe_text(data.get("sheet_id")) or None
        data["spreadsheet_token"] = _safe_text(data.get("spreadsheet_token")) or None
        data["written_table_count"] = _safe_int(data.get("written_table_count"))
        data["native_chart_count"] = _safe_int(data.get("native_chart_count"))
        data["sheet_warnings"] = _safe_text_list(data.get("sheet_warnings"))
        data["warnings"] = _safe_text_list(data.get("warnings"))
        data["tool_calls"] = [_safe_tool_call(item) for item in data.get("tool_calls") or [] if isinstance(item, dict)]
        if not any(
            [
                data["sheet_url"],
                data["sheet_id"],
                data["spreadsheet_token"],
                data["written_table_count"],
                data["native_chart_count"],
                data["sheet_warnings"],
            ]
        ):
            for key in [
                "sheet_url",
                "sheet_id",
                "spreadsheet_token",
                "written_table_count",
                "native_chart_count",
                "sheet_warnings",
            ]:
                data.pop(key, None)
        return data


def failed_publish_result(
    *,
    platform: str,
    title: str = "",
    warning: str,
    tool_calls: list[dict[str, Any]] | None = None,
) -> ExternalPublishResult:
    return ExternalPublishResult(
        platform=platform,
        status="failed",
        title=title,
        created_at=utc_now_iso(),
        warnings=[warning],
        tool_calls=tool_calls or [],
    )


def export_package_to_dict(package: Any) -> dict[str, Any]:
    if isinstance(package, dict):
        return dict(package)
    to_dict = getattr(package, "to_dict", None)
    if callable(to_dict):
        data = to_dict()
        return data if isinstance(data, dict) else {}
    return {}


def is_report_export_package(package: Any) -> bool:
    data = export_package_to_dict(package)
    return (
        bool(data)
        and data.get("package_version") == EXPORT_PACKAGE_VERSION
        and data.get("source_type") == SOURCE_REPORT
    )


def safe_warning(value: Any) -> str:
    return _safe_text(value)


def _safe_url(value: Any) -> str | None:
    return safe_url(value, strict_cli=True) or None
