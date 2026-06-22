from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionDeliveryTool:
    tool_id: str
    tool_type: str
    description: str
    is_mock: bool
    requires_network: bool
    requires_api_key: bool


ACTION_DELIVERY_TOOLS: dict[str, ActionDeliveryTool] = {
    "local_sqlite": ActionDeliveryTool(
        tool_id="local_sqlite",
        tool_type="local_action_store",
        description="Create local SQLite task, alert, and email draft records.",
        is_mock=False,
        requires_network=False,
        requires_api_key=False,
    ),
    "jira_ticket_mock": ActionDeliveryTool(
        tool_id="jira_ticket_mock",
        tool_type="mock_external_ticketing",
        description="Simulate creating an external Jira ticket without network or credentials.",
        is_mock=True,
        requires_network=False,
        requires_api_key=False,
    ),
}


def get_action_delivery_tool(tool_id: str) -> ActionDeliveryTool | None:
    return ACTION_DELIVERY_TOOLS.get(str(tool_id or "").strip())
