from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Literal, Protocol

from workspaces.external_publishing import (
    export_package_to_dict,
    is_report_export_package,
    safe_command_name,
    safe_warning,
)
from workspaces.feishu_publisher import (
    DEFAULT_LARK_CLI_BIN,
    DEFAULT_TIMEOUT_SECONDS,
    CommandRunner,
    SubprocessCommandRunner,
)
from workspaces.models import utc_now_iso


SheetPublishStatus = Literal["published", "warning", "failed"]
MAX_SHEET_TABLE_ROWS = 500


@dataclass
class SheetTableWriteResult:
    table_id: str
    title: str
    range: str
    row_count: int
    column_count: int
    success: bool
    warning: str = ""


@dataclass
class SheetChartCreateResult:
    chart_id: str
    title: str
    chart_type: str
    table_id: str
    success: bool
    warning: str = ""


@dataclass
class SheetPublishResult:
    status: SheetPublishStatus
    title: str
    url: str | None = None
    sheet_id: str | None = None
    spreadsheet_token: str | None = None
    created_at: str | None = None
    written_table_count: int = 0
    native_chart_count: int = 0
    warnings: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_safe_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = data["status"] if data.get("status") in {"published", "warning", "failed"} else "failed"
        data["title"] = _safe_text(data.get("title"))
        data["url"] = _safe_url(data.get("url"))
        data["sheet_id"] = _safe_text(data.get("sheet_id")) or None
        data["spreadsheet_token"] = _safe_text(data.get("spreadsheet_token")) or None
        data["created_at"] = _safe_text(data.get("created_at")) or None
        data["written_table_count"] = _safe_int(data.get("written_table_count"))
        data["native_chart_count"] = _safe_int(data.get("native_chart_count"))
        data["warnings"] = _safe_text_list(data.get("warnings"))
        data["tool_calls"] = [_safe_tool_call(item) for item in data.get("tool_calls") or [] if isinstance(item, dict)]
        return data


class FeishuSheetPublisher(Protocol):
    def publish_sheet(self, package: Any) -> SheetPublishResult:
        ...


class CliFeishuSheetPublisher:
    def __init__(
        self,
        *,
        runner: CommandRunner | None = None,
        cli_binary: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        cli_working_dir: str | Path | None = None,
    ) -> None:
        self.cli_binary = cli_binary or os.getenv("LARK_CLI_BIN") or DEFAULT_LARK_CLI_BIN
        self.timeout_seconds = timeout_seconds
        self.cli_working_dir = Path(cli_working_dir).resolve() if cli_working_dir else Path.cwd().resolve()
        self.runner = runner or SubprocessCommandRunner(working_dir=self.cli_working_dir)

    def publish_sheet(self, package: Any) -> SheetPublishResult:
        package_data = export_package_to_dict(package)
        title = f"{_package_title(package_data)} - 可编辑数据"
        if not is_report_export_package(package_data):
            return SheetPublishResult(
                status="failed",
                title=title,
                created_at=utc_now_iso(),
                warnings=["飞书表格附录当前只支持 Report Center 的 report export package。"],
            )
        tables, table_warnings = _project_evidence_tables(package_data.get("evidence_tables"))
        if not tables:
            return SheetPublishResult(
                status="warning",
                title=title,
                created_at=utc_now_iso(),
                warnings=table_warnings or ["当前报告导出包没有可写入飞书表格的证据表。"],
            )

        tool_calls: list[dict[str, Any]] = []
        workbook_command = self._build_workbook_create_command(title)
        try:
            workbook_result = self.runner.run(
                workbook_command,
                input_text=None,
                timeout_seconds=self.timeout_seconds,
            )
        except Exception:  # noqa: BLE001 - external command failures become safe publish results.
            return SheetPublishResult(
                status="failed",
                title=title,
                created_at=utc_now_iso(),
                warnings=["飞书表格创建失败，已保留飞书文档发布。"],
                tool_calls=[
                    _tool_call(
                        operation="create_workbook",
                        command_name=safe_command_name(self.cli_binary),
                        success=False,
                        exit_code=127,
                        elapsed_ms=0,
                    )
                ],
            )

        tool_calls.append(
            _tool_call(
                operation="create_workbook",
                command_name=workbook_result.command_name or self.cli_binary,
                success=workbook_result.exit_code == 0,
                exit_code=workbook_result.exit_code,
                elapsed_ms=workbook_result.elapsed_ms,
            )
        )
        if workbook_result.exit_code != 0:
            return SheetPublishResult(
                status="failed",
                title=title,
                created_at=utc_now_iso(),
                warnings=["飞书表格创建失败，已保留飞书文档发布。"],
                tool_calls=tool_calls,
            )

        parsed = _parse_json_object(workbook_result.stdout)
        workbook = _official_spreadsheet(parsed or {})
        if parsed and parsed.get("ok") is False:
            return SheetPublishResult(
                status="failed",
                title=title,
                created_at=utc_now_iso(),
                warnings=["飞书表格创建失败，已保留飞书文档发布。"],
                tool_calls=tool_calls,
            )
        source = workbook or (parsed if isinstance(parsed, dict) else {})
        spreadsheet_token = _first_text(source, "spreadsheet_token", "spreadsheet_id", "token", "id")
        sheet_url = _first_text(source, "url", "spreadsheet_url", "share_url")
        if not spreadsheet_token:
            return SheetPublishResult(
                status="failed",
                title=title,
                url=sheet_url or None,
                created_at=utc_now_iso(),
                warnings=["飞书表格创建成功但缺少 spreadsheet token，证据表未写入。"],
                tool_calls=tool_calls,
            )

        warnings = list(table_warnings)
        written_tables: dict[str, dict[str, Any]] = {}
        for table in tables:
            command = self._build_table_put_command(spreadsheet_token=spreadsheet_token, table=table)
            try:
                write_result = self.runner.run(
                    command,
                    input_text=None,
                    timeout_seconds=self.timeout_seconds,
                )
            except Exception:  # noqa: BLE001 - table failure should not fail the document publish path.
                write_result = None
            if write_result is not None:
                tool_calls.append(
                    _tool_call(
                        operation="write_table",
                        command_name=write_result.command_name or self.cli_binary,
                        success=write_result.exit_code == 0,
                        exit_code=write_result.exit_code,
                        elapsed_ms=write_result.elapsed_ms,
                    )
                )
            else:
                tool_calls.append(
                    _tool_call(
                        operation="write_table",
                        command_name=safe_command_name(self.cli_binary),
                        success=False,
                        exit_code=127,
                        elapsed_ms=0,
                    )
                )
            if write_result is not None and write_result.exit_code == 0:
                written_tables[table["table_id"]] = table
                continue
            warnings.append(f"飞书表格「{table['title']}」写入失败，已跳过。")

        native_chart_count = 0
        for projection in _project_native_charts(package_data.get("chart_artifacts"), list(written_tables.values())):
            if projection.get("warning"):
                warnings.append(projection["warning"])
                continue
            command = self._build_chart_create_command(
                spreadsheet_token=spreadsheet_token,
                chart=projection,
            )
            try:
                chart_result = self.runner.run(
                    command,
                    input_text=None,
                    timeout_seconds=self.timeout_seconds,
                )
            except Exception:  # noqa: BLE001 - chart failure is warning-only.
                chart_result = None
            if chart_result is not None:
                tool_calls.append(
                    _tool_call(
                        operation="create_native_chart",
                        command_name=chart_result.command_name or self.cli_binary,
                        success=chart_result.exit_code == 0,
                        exit_code=chart_result.exit_code,
                        elapsed_ms=chart_result.elapsed_ms,
                    )
                )
            else:
                tool_calls.append(
                    _tool_call(
                        operation="create_native_chart",
                        command_name=safe_command_name(self.cli_binary),
                        success=False,
                        exit_code=127,
                        elapsed_ms=0,
                    )
                )
            if chart_result is not None and chart_result.exit_code == 0:
                native_chart_count += 1
            else:
                warnings.append(f"图表「{projection['title']}」创建飞书原生图表失败，已跳过。")

        written_count = len(written_tables)
        status: SheetPublishStatus = "published" if written_count and not warnings else "warning"
        safe = SheetPublishResult(
            status=status,
            title=title,
            url=sheet_url or None,
            sheet_id=spreadsheet_token,
            spreadsheet_token=spreadsheet_token,
            created_at=utc_now_iso(),
            written_table_count=written_count,
            native_chart_count=native_chart_count,
            warnings=warnings,
            tool_calls=tool_calls,
        )
        return _from_safe_dict(safe.to_safe_dict())

    def _build_workbook_create_command(self, title: str) -> list[str]:
        return [self.cli_binary, "sheets", "+workbook-create", "--title", title or "InsightFlow 可编辑数据"]

    def _build_table_put_command(self, *, spreadsheet_token: str, table: dict[str, Any]) -> list[str]:
        return [
            self.cli_binary,
            "sheets",
            "+table-put",
            "--spreadsheet",
            spreadsheet_token,
            "--sheet",
            table["title"],
            "--range",
            table["range"],
            "--values",
            json.dumps(table["values"], ensure_ascii=False),
        ]

    def _build_chart_create_command(self, *, spreadsheet_token: str, chart: dict[str, Any]) -> list[str]:
        return [
            self.cli_binary,
            "sheets",
            "+chart-create",
            "--spreadsheet",
            spreadsheet_token,
            "--sheet",
            chart["sheet_title"],
            "--chart-type",
            chart["chart_type"],
            "--range",
            chart["range"],
            "--category-column",
            chart["category_column"],
            "--value-column",
            chart["value_column"],
            "--title",
            chart["title"],
        ]


def _project_evidence_tables(value: Any) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    if not isinstance(value, list):
        return [], []
    tables: list[dict[str, Any]] = []
    used_titles: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        columns = [_safe_text(column) for column in item.get("columns") or [] if _safe_text(column)]
        rows = [row for row in item.get("rows") or [] if isinstance(row, dict)]
        if not columns or not rows:
            continue
        title = _unique_sheet_title(_safe_text(item.get("title")) or f"证据表{index + 1}", used_titles)
        visible_rows = rows[:MAX_SHEET_TABLE_ROWS]
        if len(rows) > len(visible_rows):
            warnings.append(f"证据表「{title}」行数较多，仅写入前 {len(visible_rows)} 行。")
        values = [columns]
        for row in visible_rows:
            values.append([_safe_cell(row.get(column)) for column in columns])
        range_name = f"A1:{_column_letter(len(columns))}{len(values)}"
        tables.append(
            {
                "table_id": _safe_text(item.get("table_id")) or f"evidence_table_{index + 1}",
                "title": title,
                "source_chapter_id": _safe_text(item.get("source_chapter_id")),
                "evidence_ref": _safe_text(item.get("evidence_ref")),
                "evidence_payload_ref": _safe_text(item.get("evidence_payload_ref")),
                "columns": columns,
                "rows": visible_rows,
                "values": values,
                "range": range_name,
            }
        )
    return tables, warnings


def _project_native_charts(value: Any, tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not tables:
        return []
    projections: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = _safe_text(item.get("title")) or "报告图表"
        chart_type = _safe_text(item.get("chart_type")).lower()
        option = item.get("echarts_option") if isinstance(item.get("echarts_option"), dict) else {}
        series = option.get("series")
        series_items = [series] if isinstance(series, dict) else series if isinstance(series, list) else []
        first_series = next((series_item for series_item in series_items if isinstance(series_item, dict)), {})
        option_chart_type = _safe_text(first_series.get("type")).lower()
        safe_chart_type = chart_type if chart_type in {"bar", "line"} else option_chart_type
        if safe_chart_type not in {"bar", "line"}:
            projections.append({"warning": _chart_skip_warning(title)})
            continue
        labels = _axis_labels(option)
        data_values = [_numeric_value(value) for value in first_series.get("data") or []]
        matched = _match_table_for_chart(item, tables, labels=labels, series_name=_safe_text(first_series.get("name")), values=data_values)
        if not matched:
            projections.append({"warning": _chart_skip_warning(title)})
            continue
        projections.append(
            {
                "title": title,
                "chart_type": safe_chart_type,
                "sheet_title": matched["table"]["title"],
                "table_id": matched["table"]["table_id"],
                "range": matched["table"]["range"],
                "category_column": matched["category_column"],
                "value_column": matched["value_column"],
            }
        )
    return projections


def _match_table_for_chart(
    chart: dict[str, Any],
    tables: list[dict[str, Any]],
    *,
    labels: list[str],
    series_name: str,
    values: list[float | None],
) -> dict[str, Any]:
    chart_refs = set(_safe_text_list(chart.get("evidence_refs")))
    chart_source = _safe_text(chart.get("source_chapter_id"))
    candidates = []
    for table in tables:
        table_refs = {
            table.get("table_id", ""),
            table.get("evidence_ref", ""),
            table.get("evidence_payload_ref", ""),
        }
        if chart_refs and chart_refs.intersection(table_refs):
            candidates.append(table)
        elif chart_source and chart_source == table.get("source_chapter_id"):
            candidates.append(table)
    if not candidates:
        candidates = tables

    for table in candidates:
        category_column = _category_column(table, labels)
        value_column = _value_column(table, values=values, series_name=series_name)
        if category_column and value_column:
            return {"table": table, "category_column": category_column, "value_column": value_column}
    return {}


def _category_column(table: dict[str, Any], labels: list[str]) -> str:
    columns = list(table.get("columns") or [])
    rows = list(table.get("rows") or [])
    label_set = [_safe_text(label) for label in labels if _safe_text(label)]
    for column in columns:
        column_values = [_safe_text(row.get(column)) for row in rows]
        if label_set and column_values[: len(label_set)] == label_set:
            return column
    for column in columns:
        if any(_numeric_value(row.get(column)) is None for row in rows):
            return column
    return ""


def _value_column(table: dict[str, Any], *, values: list[float | None], series_name: str) -> str:
    columns = list(table.get("columns") or [])
    rows = list(table.get("rows") or [])
    numeric_columns = [column for column in columns if all(_numeric_value(row.get(column)) is not None for row in rows)]
    if series_name in numeric_columns:
        return series_name
    expected = [value for value in values if value is not None]
    if expected:
        for column in numeric_columns:
            actual = [_numeric_value(row.get(column)) for row in rows[: len(expected)]]
            if _numbers_equal(actual, expected):
                return column
    return numeric_columns[0] if len(numeric_columns) == 1 else ""


def _numbers_equal(left: list[float | None], right: list[float]) -> bool:
    if len(left) != len(right):
        return False
    return all(value is not None and math.isclose(float(value), float(expected), rel_tol=1e-9, abs_tol=1e-9) for value, expected in zip(left, right))


def _axis_labels(option: dict[str, Any]) -> list[str]:
    axis = option.get("xAxis")
    if isinstance(axis, list):
        axis = next((item for item in axis if isinstance(item, dict) and isinstance(item.get("data"), list)), {})
    if isinstance(axis, dict) and isinstance(axis.get("data"), list):
        return [_safe_text(item) for item in axis.get("data") or []]
    return []


def _safe_cell(value: Any) -> str:
    return _safe_text(value)


def _unique_sheet_title(value: str, used_titles: set[str]) -> str:
    base = re.sub(r"[\[\]*?:/\\]", " ", _safe_text(value)).strip() or "证据表"
    base = re.sub(r"\s+", " ", base)[:31].strip() or "证据表"
    title = base
    suffix = 2
    while title in used_titles:
        marker = f" {suffix}"
        title = f"{base[:31 - len(marker)]}{marker}".strip()
        suffix += 1
    used_titles.add(title)
    return title


def _column_letter(count: int) -> str:
    count = max(1, int(count or 1))
    letters = ""
    while count:
        count, remainder = divmod(count - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _package_title(package: dict[str, Any]) -> str:
    document = package.get("document") if isinstance(package.get("document"), dict) else {}
    return _safe_text(package.get("title")) or _safe_text(document.get("title")) or "InsightFlow 报告"


def _parse_json_object(value: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value or "")
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _official_spreadsheet(data: dict[str, Any]) -> dict[str, Any]:
    nested_data = data.get("data") if isinstance(data.get("data"), dict) else {}
    spreadsheet = nested_data.get("spreadsheet") if isinstance(nested_data.get("spreadsheet"), dict) else {}
    return spreadsheet


def _first_text(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        text = _safe_text(data.get(key))
        if text:
            return text
    return ""


def _numeric_value(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, (list, tuple)):
        numeric_values = [_numeric_value(item) for item in value]
        return next((item for item in reversed(numeric_values) if item is not None), None)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_text(value: Any) -> str:
    text = safe_warning(value)
    if "\n" in text:
        text = " ".join(part.strip() for part in text.splitlines() if part.strip())
    return text


def _safe_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for text in (_safe_text(item) for item in value) if text]


def _safe_url(value: Any) -> str | None:
    text = _safe_text(value)
    if not text:
        return None
    if re.search(r"(?i)(api_key=|access_token=|token=|secret=|password=)", text):
        return None
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return None


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _safe_tool_call(value: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key in {"operation", "command_name", "success", "elapsed_ms", "exit_code"}:
        if key not in value:
            continue
        item = value.get(key)
        if key == "success":
            cleaned[key] = bool(item)
        elif key in {"elapsed_ms", "exit_code"}:
            cleaned[key] = _safe_int(item)
        else:
            safe = safe_command_name(item) if key == "command_name" else _safe_text(item)
            if safe:
                cleaned[key] = safe
    return cleaned


def _tool_call(
    *,
    operation: str,
    command_name: str,
    success: bool,
    exit_code: int,
    elapsed_ms: int,
) -> dict[str, Any]:
    return {
        "operation": operation,
        "command_name": safe_command_name(command_name) or DEFAULT_LARK_CLI_BIN,
        "success": success,
        "elapsed_ms": max(0, int(elapsed_ms or 0)),
        "exit_code": int(exit_code or 0),
    }


def _chart_skip_warning(title: str) -> str:
    return f"图表「{_safe_text(title) or '报告图表'}」无法安全映射为飞书原生图表，已跳过。"


def _from_safe_dict(data: dict[str, Any]) -> SheetPublishResult:
    return SheetPublishResult(
        status=data.get("status") if data.get("status") in {"published", "warning", "failed"} else "failed",
        title=data.get("title") or "",
        url=data.get("url"),
        sheet_id=data.get("sheet_id"),
        spreadsheet_token=data.get("spreadsheet_token"),
        created_at=data.get("created_at"),
        written_table_count=_safe_int(data.get("written_table_count")),
        native_chart_count=_safe_int(data.get("native_chart_count")),
        warnings=list(data.get("warnings") or []),
        tool_calls=list(data.get("tool_calls") or []),
    )
