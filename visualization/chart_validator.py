from __future__ import annotations

from typing import Any

from visualization.chart_registry import CHART_REGISTRY, is_supported_chart_type
from visualization.chart_spec import normalize_chart_spec


def _column_names(execution_result: dict[str, Any]) -> list[str]:
    return [str(column) for column in execution_result.get("columns") or []]


def _failure(spec: dict[str, Any], message: str) -> dict[str, Any]:
    normalized = normalize_chart_spec(spec)
    normalized["success"] = False
    normalized["validation_error"] = message
    return normalized


def validate_chart_spec(chart_spec: dict[str, Any], execution_result: dict[str, Any]) -> dict[str, Any]:
    spec = normalize_chart_spec(chart_spec)
    if not execution_result or not execution_result.get("success"):
        return _failure(spec, "execution_result must be successful before chart validation")

    columns = _column_names(execution_result)
    rows = execution_result.get("rows") or []
    if not columns or not rows:
        return _failure(spec, "execution_result requires non-empty columns and rows")

    chart_type = spec["chart_type"]
    if not is_supported_chart_type(chart_type):
        return _failure(spec, f"Unsupported chart_type: {chart_type}")

    required_columns = list(dict.fromkeys([*spec["required_columns"], spec["x"], spec["y"], spec["y_secondary"], spec["series"]]))
    required_columns = [column for column in required_columns if column]
    missing = [column for column in required_columns if column not in columns]
    if missing:
        return _failure(spec, f"Chart spec references missing execution_result columns: {', '.join(missing)}")

    for role in CHART_REGISTRY[chart_type].required_roles:
        if not spec.get(role):
            return _failure(spec, f"chart_type {chart_type} requires role: {role}")

    spec["required_columns"] = required_columns
    spec["success"] = True
    spec["validation_error"] = ""
    return spec
