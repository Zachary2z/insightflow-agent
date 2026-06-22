from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path
from time import perf_counter
from typing import Any

from visualization.chart_renderer import render_chart
from visualization_delivery.tool_catalog import get_delivery_tool


DEFAULT_VISUALIZATION_DELIVERY_DIR = Path(__file__).resolve().parents[1] / "reports" / "charts"


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return safe.strip("_") or "visualization"


def _row_count(execution_result: dict[str, Any]) -> int:
    return len(execution_result.get("rows") or [])


def _base_result(
    *,
    delivery_tool_id: str,
    run_id: str,
    execution_result: dict[str, Any],
    started_at: float,
) -> dict[str, Any]:
    tool = get_delivery_tool(delivery_tool_id)
    return {
        "success": True,
        "tool_id": delivery_tool_id,
        "delivery_tool_id": delivery_tool_id,
        "tool_type": tool.tool_type if tool else "",
        "run_id": run_id,
        "external_tool_called": True,
        "requires_network": bool(tool.requires_network) if tool else False,
        "requires_api_key": bool(tool.requires_api_key) if tool else False,
        "data_row_count": _row_count(execution_result),
        "fabricated_data": False,
        "latency_ms": int((perf_counter() - started_at) * 1000),
    }


def _trace_event(result: dict[str, Any]) -> dict[str, Any]:
    output = result.get("artifact_path") or result.get("artifact_url") or result.get("fallback_reason", "")
    event = {
        "tool_name": "external_visualization_tool",
        "tool_input_summary": f"delivery_tool_id={result.get('delivery_tool_id', '')}",
        "tool_output_summary": str(output)[:200],
        "status": "success" if result.get("success") else "error",
        "latency_ms": result.get("latency_ms", 0),
        "delivery_tool_id": result.get("delivery_tool_id", ""),
        "external_tool_called": bool(result.get("external_tool_called", False)),
        "tool_type": result.get("tool_type", ""),
        "fabricated_data": bool(result.get("fabricated_data", False)),
    }
    if not result.get("success"):
        event["error_type"] = "external_visualization_tool_error"
        event["error"] = result.get("error", "")
    return event


def _failure(delivery_tool_id: str, error: str, started_at: float) -> dict[str, Any]:
    result = {
        "success": False,
        "tool_id": delivery_tool_id,
        "delivery_tool_id": delivery_tool_id,
        "tool_type": "",
        "external_tool_called": False,
        "artifact_path": "",
        "artifact_url": "",
        "error": error,
        "data_row_count": 0,
        "fabricated_data": False,
        "latency_ms": int((perf_counter() - started_at) * 1000),
    }
    result["trace_event"] = _trace_event(result)
    return result


def _render_local(
    *,
    chart_spec: dict[str, Any],
    execution_result: dict[str, Any],
    run_id: str,
    output_dir: str | Path,
    started_at: float,
) -> dict[str, Any]:
    spec = {**chart_spec, "run_id": chart_spec.get("run_id") or run_id}
    rendered = render_chart(execution_result, spec, output_dir=output_dir)
    result = {
        **_base_result(
            delivery_tool_id="local_renderer",
            run_id=run_id,
            execution_result=execution_result,
            started_at=started_at,
        ),
        **rendered,
        "artifact_path": rendered.get("chart_path", ""),
        "artifact_url": "",
        "external_tool_called": True,
        "fabricated_data": False,
        "data_row_count": _row_count(execution_result),
    }
    result["trace_event"] = _trace_event(result)
    return result


def _xlsx_cell(cell_ref: str, value: Any) -> str:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return f'<c r="{cell_ref}"><v>{value}</v></c>'
    text = html.escape(str(value))
    return f'<c r="{cell_ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _sheet_xml(columns: list[str], rows: list[list[Any]]) -> str:
    all_rows: list[list[Any]] = [columns, *rows]
    row_xml = []
    for row_index, row in enumerate(all_rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cells.append(_xlsx_cell(f"{_column_name(column_index)}{row_index}", value))
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        "</worksheet>"
    )


def _write_xlsx(path: Path, columns: list[str], rows: list[list[Any]]) -> None:
    files = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="execution_result" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>"
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>"
        ),
        "xl/worksheets/sheet1.xml": _sheet_xml(columns, rows),
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as workbook:
        for name, content in files.items():
            workbook.writestr(name, content)


def _export_excel(
    *,
    execution_result: dict[str, Any],
    run_id: str,
    output_dir: str | Path,
    started_at: float,
) -> dict[str, Any]:
    columns = [str(column) for column in execution_result.get("columns") or []]
    rows = list(execution_result.get("rows") or [])
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    artifact_path = output_path / f"{_safe_filename(run_id)}_execution_result.xlsx"
    _write_xlsx(artifact_path, columns, rows)
    result = {
        **_base_result(
            delivery_tool_id="excel_exporter",
            run_id=run_id,
            execution_result=execution_result,
            started_at=started_at,
        ),
        "artifact_path": str(artifact_path),
        "artifact_url": "",
        "exported_columns": columns,
        "exported_rows": rows,
    }
    result["trace_event"] = _trace_event(result)
    return result


def _publish_powerbi_mock(
    *,
    chart_spec: dict[str, Any],
    execution_result: dict[str, Any],
    run_id: str,
    started_at: float,
) -> dict[str, Any]:
    artifact_name = _safe_filename(chart_spec.get("title") or chart_spec.get("chart_type") or "visualization")
    result = {
        **_base_result(
            delivery_tool_id="powerbi_publisher_mock",
            run_id=run_id,
            execution_result=execution_result,
            started_at=started_at,
        ),
        "artifact_path": "",
        "artifact_url": f"mock://powerbi/{run_id}/{artifact_name}",
    }
    result["trace_event"] = _trace_event(result)
    return result


def execute_delivery_tool(
    *,
    delivery_tool_id: str,
    chart_spec: dict[str, Any],
    execution_result: dict[str, Any],
    run_id: str,
    output_dir: str | Path = DEFAULT_VISUALIZATION_DELIVERY_DIR,
) -> dict[str, Any]:
    started_at = perf_counter()
    tool_id = str(delivery_tool_id or "").strip()
    try:
        if tool_id == "local_renderer":
            return _render_local(
                chart_spec=chart_spec,
                execution_result=execution_result,
                run_id=run_id,
                output_dir=output_dir,
                started_at=started_at,
            )
        if tool_id == "excel_exporter":
            return _export_excel(
                execution_result=execution_result,
                run_id=run_id,
                output_dir=output_dir,
                started_at=started_at,
            )
        if tool_id == "powerbi_publisher_mock":
            return _publish_powerbi_mock(
                chart_spec=chart_spec,
                execution_result=execution_result,
                run_id=run_id,
                started_at=started_at,
            )
        return _failure(tool_id, f"Unknown delivery tool: {tool_id}", started_at)
    except Exception as exc:
        return _failure(tool_id, str(exc), started_at)
