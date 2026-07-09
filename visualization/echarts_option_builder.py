from __future__ import annotations

import math
import re
from decimal import Decimal
from typing import Any


DEFAULT_MAX_ROWS = 100
_LOCAL_ABSOLUTE_PATH_RE = re.compile(r"^(?:/[A-Za-z0-9_. -]+)+/?$")
_RAW_SQL_RE = re.compile(r"\b(?:select|with|insert|update|delete|drop|alter|create)\b.+\b(?:from|into|table|set)\b", re.IGNORECASE | re.DOTALL)
_TECHNICAL_METADATA_MARKERS = (
    "provider_metadata",
    "trace_path",
    "trace_id",
    "raw_sql",
    "generated_sql",
)
SUPPORTED_ECHARTS_TYPES = {
    "ranked_bar",
    "bar",
    "line",
    "grouped_bar",
    "scatter",
    "dual_axis_line",
}


def build_echarts_option(
    chart_spec: dict[str, Any],
    execution_result: dict[str, Any],
    *,
    unit: str = "",
    value_label: str = "",
    max_rows: int = DEFAULT_MAX_ROWS,
) -> dict[str, Any]:
    """Build an ECharts option from already validated evidence rows."""
    spec = dict(chart_spec or {})
    chart_type = str(spec.get("chart_type") or "").strip().lower()
    unit = str(unit or spec.get("unit") or "").strip()
    value_label = _resolved_value_label(spec, value_label)
    if chart_type == "table":
        return _fallback("table chart uses table/static fallback")
    if chart_type not in SUPPORTED_ECHARTS_TYPES:
        return _failure(f"Unsupported chart_type: {chart_type or '<empty>'}")

    table = _normalize_table(execution_result)
    if not table["success"]:
        return _failure(table["validation_error"])

    columns: list[str] = table["columns"]
    rows: list[dict[str, Any]] = table["rows"]
    if not rows:
        return _failure("execution_result requires non-empty rows")

    unit_check = _validate_metric_units(spec, rows)
    if not unit_check["success"]:
        return _failure(unit_check["validation_error"])

    max_rows = _safe_max_rows(max_rows)
    sampled_rows = rows[:max_rows]
    data_limit = _data_limit(total=len(rows), rendered=len(sampled_rows), max_rows=max_rows)

    required = _required_columns(chart_type, spec)
    missing_roles = [role for role, column in required.items() if not column]
    if missing_roles:
        return _failure(f"chart_type {chart_type} requires role: {', '.join(missing_roles)}")

    missing = [column for column in dict.fromkeys(required.values()) if column not in columns]
    if missing:
        return _failure(f"Chart spec references missing execution_result columns: {', '.join(missing)}")

    label_column = str(spec.get("label") or spec.get("name") or "").strip()
    if label_column and label_column not in columns:
        return _failure(f"Chart spec references missing execution_result columns: {label_column}")

    try:
        if chart_type in {"ranked_bar", "bar"}:
            option = _build_bar_option(spec, sampled_rows, required["x"], required["y"], unit=unit, value_label=value_label)
        elif chart_type == "line":
            option = _build_line_option(spec, sampled_rows, required["x"], required["y"], unit=unit, value_label=value_label)
        elif chart_type == "grouped_bar":
            option = _build_grouped_bar_option(
                spec,
                sampled_rows,
                required["x"],
                required["series"],
                required["y"],
                unit=unit,
                value_label=value_label,
            )
        elif chart_type == "scatter":
            option = _build_scatter_option(
                spec,
                sampled_rows,
                required["x"],
                required["y"],
                label_column=label_column,
                unit=unit,
                value_label=value_label,
            )
        else:
            option = _build_dual_axis_line_option(
                spec,
                sampled_rows,
                required["x"],
                required["y"],
                required["y_secondary"],
                unit=unit,
                value_label=value_label,
            )
    except ValueError as exc:
        return _failure(str(exc), data_limit=data_limit if data_limit["truncated"] else None)

    result = {
        "success": True,
        "echarts_option": option,
        "chart_type": chart_type,
        "data_row_count": len(rows),
        "rendered_row_count": len(sampled_rows),
        "source": "execution_result",
        "validation_error": "",
        "fallback_reason": "",
    }
    if data_limit["truncated"]:
        result["data_limit"] = data_limit
    return result


def _normalize_table(execution_result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(execution_result, dict):
        return {"success": False, "validation_error": "execution_result must be an object"}
    if execution_result.get("success") is False:
        return {"success": False, "validation_error": "execution_result must be successful before option building"}

    table = execution_result.get("table") if isinstance(execution_result.get("table"), dict) else execution_result
    raw_rows = table.get("rows") if isinstance(table, dict) else None
    if not isinstance(raw_rows, list):
        return {"success": False, "validation_error": "execution_result requires rows"}

    raw_columns = table.get("columns") if isinstance(table, dict) else []
    columns = [str(column).strip() for column in raw_columns or [] if str(column).strip()]
    if not columns:
        columns = _columns_from_dict_rows(raw_rows)
    if not columns:
        return {"success": False, "validation_error": "execution_result requires non-empty columns"}

    rows = [_row_to_dict(row, columns) for row in raw_rows]
    return {"success": True, "columns": columns, "rows": rows}


def _columns_from_dict_rows(rows: list[Any]) -> list[str]:
    columns: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in row:
            column = str(key).strip()
            if column and column not in columns:
                columns.append(column)
    return columns


def _row_to_dict(row: Any, columns: list[str]) -> dict[str, Any]:
    if isinstance(row, dict):
        return {column: row.get(column) for column in columns}
    if isinstance(row, (list, tuple)):
        return {column: row[index] if index < len(row) else None for index, column in enumerate(columns)}
    return {column: None for column in columns}


def _safe_max_rows(max_rows: int) -> int:
    try:
        value = int(max_rows)
    except (TypeError, ValueError):
        return DEFAULT_MAX_ROWS
    return max(1, min(value, DEFAULT_MAX_ROWS))


def _data_limit(*, total: int, rendered: int, max_rows: int) -> dict[str, Any]:
    return {
        "truncated": total > rendered,
        "row_count": total,
        "sampled_row_count": rendered,
        "max_rows": max_rows,
        "reason": f"option rows limited to first {rendered} of {total} rows" if total > rendered else "",
    }


def _required_columns(chart_type: str, spec: dict[str, Any]) -> dict[str, str]:
    roles: tuple[str, ...]
    if chart_type in {"ranked_bar", "bar", "line", "scatter"}:
        roles = ("x", "y")
    elif chart_type == "grouped_bar":
        roles = ("x", "series", "y")
    else:
        roles = ("x", "y", "y_secondary")
    return {role: str(spec.get(role) or "").strip() for role in roles}


def _build_bar_option(
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
    x: str,
    y: str,
    *,
    unit: str,
    value_label: str,
) -> dict[str, Any]:
    categories = [_category(row.get(x), column=x) for row in rows]
    values = [_number(row.get(y), column=y) for row in rows]
    return _category_value_option(
        spec,
        x_name=x,
        y_name=y,
        categories=categories,
        series=[{"name": _series_name(y, value_label=value_label), "type": "bar", "data": values}],
        unit=unit,
    )


def _build_line_option(
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
    x: str,
    y: str,
    *,
    unit: str,
    value_label: str,
) -> dict[str, Any]:
    categories = [_category(row.get(x), column=x) for row in rows]
    values = [_number(row.get(y), column=y) for row in rows]
    return _category_value_option(
        spec,
        x_name=x,
        y_name=y,
        categories=categories,
        series=[{"name": _series_name(y, value_label=value_label), "type": "line", "data": values}],
        unit=unit,
    )


def _build_grouped_bar_option(
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
    x: str,
    series_column: str,
    y: str,
    *,
    unit: str,
    value_label: str,
) -> dict[str, Any]:
    categories: list[str] = []
    series_names: list[str] = []
    values_by_series: dict[str, dict[str, float]] = {}
    for row in rows:
        category = _category(row.get(x), column=x)
        series_name = _category(row.get(series_column), column=series_column)
        value = _number(row.get(y), column=y)
        if category not in categories:
            categories.append(category)
        if series_name not in series_names:
            series_names.append(series_name)
        values_by_series.setdefault(series_name, {})
        if category not in values_by_series[series_name]:
            values_by_series[series_name][category] = value

    series = [
        {
            "name": _series_name(series_name, value_label=""),
            "type": "bar",
            "data": [values_by_series.get(series_name, {}).get(category) for category in categories],
        }
        for series_name in series_names
    ]
    return _category_value_option(spec, x_name=x, y_name=y, categories=categories, series=series, unit=unit)


def _validate_metric_units(spec: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    metric_units = spec.get("metric_units") if isinstance(spec.get("metric_units"), dict) else {}
    if not metric_units:
        return {"success": True}
    chart_type = str(spec.get("chart_type") or "").strip().lower()
    if chart_type != "grouped_bar":
        return {"success": True}
    series_column = str(spec.get("series") or "").strip()
    if not series_column:
        return {"success": True}
    used_units = []
    for row in rows:
        series_name = str(row.get(series_column) or "").strip()
        unit = metric_units.get(series_name)
        if unit:
            used_units.append(_unit_family(str(unit)))
    used_units = list(dict.fromkeys(unit for unit in used_units if unit))
    if len(used_units) <= 1:
        return {"success": True}
    return {"success": False, "validation_error": "incompatible metric units for grouped_bar"}


def _unit_family(unit: str) -> str:
    lowered = str(unit or "").strip().lower()
    if lowered in {"currency", "money", "amount", "元", "人民币", "cny", "rmb"}:
        return "currency"
    if lowered in {"percentage", "percent", "pct", "%", "rate", "roi", "roas"}:
        return "percentage"
    if lowered in {"count", "number", "个", "次", "件", "单"}:
        return "count"
    return lowered


def _build_scatter_option(
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
    x: str,
    y: str,
    *,
    label_column: str,
    unit: str,
    value_label: str,
) -> dict[str, Any]:
    data: list[Any] = []
    for row in rows:
        point = [_number(row.get(x), column=x), _number(row.get(y), column=y)]
        if label_column:
            data.append({"value": point, "name": _category(row.get(label_column), column=label_column)})
        else:
            data.append(point)
    option = _base_option(spec)
    option.update(
        {
            "tooltip": {"trigger": "item"},
            "xAxis": {"type": "value", "name": _safe_text(x)},
            "yAxis": {"type": "value", "name": _axis_name(y, unit=unit)},
            "series": [{"name": _series_name(value_label or y, value_label=""), "type": "scatter", "data": data}],
        }
    )
    return option


def _build_dual_axis_line_option(
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
    x: str,
    y: str,
    y_secondary: str,
    *,
    unit: str,
    value_label: str,
) -> dict[str, Any]:
    categories = [_category(row.get(x), column=x) for row in rows]
    primary = [_number(row.get(y), column=y) for row in rows]
    secondary = [_number(row.get(y_secondary), column=y_secondary) for row in rows]
    option = _base_option(spec)
    option.update(
        {
            "tooltip": {"trigger": "axis"},
            "legend": {"data": [_series_name(y, value_label=value_label), _series_name(y_secondary, value_label="")]},
            "grid": {"containLabel": True},
            "xAxis": {"type": "category", "data": categories, "name": _safe_text(x)},
            "yAxis": [
                {"type": "value", "name": _axis_name(y, unit=unit)},
                {"type": "value", "name": _safe_text(y_secondary)},
            ],
            "series": [
                {"name": _series_name(y, value_label=value_label), "type": "line", "yAxisIndex": 0, "data": primary},
                {"name": _series_name(y_secondary, value_label=""), "type": "line", "yAxisIndex": 1, "data": secondary},
            ],
        }
    )
    return option


def _category_value_option(
    spec: dict[str, Any],
    *,
    x_name: str,
    y_name: str,
    categories: list[str],
    series: list[dict[str, Any]],
    unit: str,
) -> dict[str, Any]:
    option = _base_option(spec)
    option.update(
        {
            "tooltip": {"trigger": "axis"},
            "grid": {"containLabel": True},
            "xAxis": {"type": "category", "data": categories, "name": _safe_text(x_name)},
            "yAxis": {"type": "value", "name": _axis_name(y_name, unit=unit)},
            "series": series,
        }
    )
    if len(series) > 1:
        option["legend"] = {"data": [item["name"] for item in series]}
    return option


def _base_option(spec: dict[str, Any]) -> dict[str, Any]:
    title = _safe_text(spec.get("title") or "")
    return {"title": {"text": title}} if title else {}


def _resolved_value_label(spec: dict[str, Any], value_label: str) -> str:
    if value_label:
        return str(value_label)
    for key in ("y_label", "business_label", "value_name"):
        label = str(spec.get(key) or "").strip()
        if label:
            return label
    raw_value_label = spec.get("value_label")
    if isinstance(raw_value_label, str):
        return raw_value_label
    return ""


def _series_name(value: str, *, value_label: str) -> str:
    label = _safe_text(value_label or value)
    return label or _safe_text(value)


def _axis_name(value: str, *, unit: str) -> str:
    safe_value = _safe_text(value)
    safe_unit = _safe_text(unit)
    return f"{safe_value} ({safe_unit})" if safe_value and safe_unit else safe_value


def _number(value: Any, *, column: str) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Column {column} requires numeric values")
    if isinstance(value, Decimal):
        number = float(value)
    elif isinstance(value, int | float):
        number = float(value)
    elif isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            raise ValueError(f"Column {column} requires numeric values")
        try:
            number = float(text)
        except ValueError as exc:
            raise ValueError(f"Column {column} requires numeric values") from exc
    else:
        raise ValueError(f"Column {column} requires numeric values")
    if not math.isfinite(number):
        raise ValueError(f"Column {column} requires finite numeric values")
    return number


def _category(value: Any, *, column: str) -> str:
    if value is None:
        text = ""
    else:
        text = str(value).strip()
    if _is_unsafe_option_text(text):
        raise ValueError(f"Column {column} contains unsafe technical text")
    return text


def _safe_text(value: Any) -> str:
    text = str(value or "").strip()
    if _is_unsafe_option_text(text):
        return ""
    return text


def _is_unsafe_option_text(value: str) -> bool:
    text = str(value or "").strip()
    lowered = text.lower()
    return (
        _looks_like_js_function(text)
        or bool(_RAW_SQL_RE.search(text))
        or bool(_LOCAL_ABSOLUTE_PATH_RE.fullmatch(text))
        or any(marker in lowered for marker in _TECHNICAL_METADATA_MARKERS)
    )


def _looks_like_js_function(value: str) -> bool:
    lowered = str(value or "").lower()
    return "function" in lowered or "=>" in lowered


def _failure(message: str, *, data_limit: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"success": False, "validation_error": message, "fallback_reason": ""}
    if data_limit:
        result["data_limit"] = data_limit
    return result


def _fallback(reason: str) -> dict[str, Any]:
    return {"success": False, "validation_error": "", "fallback_reason": reason}
