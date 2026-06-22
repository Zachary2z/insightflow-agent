from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryTool:
    tool_id: str
    tool_type: str
    description: str
    requires_network: bool = False
    requires_api_key: bool = False
    is_mock: bool = False


DELIVERY_TOOL_CATALOG: dict[str, DeliveryTool] = {
    "local_renderer": DeliveryTool(
        tool_id="local_renderer",
        tool_type="local_artifact",
        description="Render a local PNG chart or structured table fallback from execution rows.",
    ),
    "excel_exporter": DeliveryTool(
        tool_id="excel_exporter",
        tool_type="local_file_export",
        description="Export execution columns and rows to a local XLSX workbook.",
    ),
    "powerbi_publisher_mock": DeliveryTool(
        tool_id="powerbi_publisher_mock",
        tool_type="mock_external_bi",
        description="Mock a Power BI publish call without network, OAuth, or API keys.",
        is_mock=True,
    ),
}


def get_delivery_tool(tool_id: str) -> DeliveryTool | None:
    return DELIVERY_TOOL_CATALOG.get(str(tool_id).strip())
