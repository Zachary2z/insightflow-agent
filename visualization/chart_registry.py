from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChartDefinition:
    chart_type: str
    required_roles: tuple[str, ...]
    description: str


CHART_REGISTRY: dict[str, ChartDefinition] = {
    "ranked_bar": ChartDefinition("ranked_bar", ("x", "y"), "Rank entities by a numeric measure."),
    "line": ChartDefinition("line", ("x", "y"), "Show a metric trend over an ordered dimension."),
    "grouped_bar": ChartDefinition("grouped_bar", ("x", "y", "series"), "Compare groups within each category."),
    "dual_axis_line": ChartDefinition("dual_axis_line", ("x", "y", "y_secondary"), "Compare two measures over time."),
    "funnel": ChartDefinition("funnel", ("x", "y"), "Show step-by-step conversion volume."),
    "heatmap": ChartDefinition("heatmap", ("x", "y", "series"), "Show intensity across two dimensions."),
    "scatter": ChartDefinition("scatter", ("x", "y"), "Compare two numeric measures by entity."),
    "risk_matrix": ChartDefinition("risk_matrix", ("x", "y"), "Place entities by value and risk measures."),
}

SUPPORTED_CHART_TYPES = set(CHART_REGISTRY)


def is_supported_chart_type(chart_type: str) -> bool:
    return str(chart_type).strip().lower() in SUPPORTED_CHART_TYPES


def fallback_chart_type(columns: list[str], rows: list[list[object]]) -> str:
    if len(columns) >= 2 and rows:
        return "ranked_bar"
    return "table"
