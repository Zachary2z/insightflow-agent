from __future__ import annotations

from pathlib import Path
from typing import Any

from visualization_delivery.adapters import DEFAULT_VISUALIZATION_DELIVERY_DIR, execute_delivery_tool
from visualization_delivery.policy import validate_delivery_tool


def call_external_visualization_tool(
    *,
    delivery_tool_id: str,
    chart_spec: dict[str, Any],
    execution_result: dict[str, Any],
    run_id: str,
    output_dir: str | Path = DEFAULT_VISUALIZATION_DELIVERY_DIR,
) -> dict[str, Any]:
    policy = validate_delivery_tool(delivery_tool_id, execution_result=execution_result)
    if not policy.get("success"):
        return {
            "success": False,
            "tool_id": delivery_tool_id,
            "delivery_tool_id": delivery_tool_id,
            "external_tool_called": False,
            "artifact_path": "",
            "artifact_url": "",
            "error": policy.get("validation_error", "delivery tool policy rejected request"),
            "policy_result": policy,
            "data_row_count": len(execution_result.get("rows") or []),
            "fabricated_data": False,
        }

    result = execute_delivery_tool(
        delivery_tool_id=policy["delivery_tool_id"],
        chart_spec=chart_spec,
        execution_result=execution_result,
        run_id=run_id,
        output_dir=output_dir,
    )
    return {**result, "policy_result": policy}
