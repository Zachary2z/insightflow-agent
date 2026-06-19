from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp_servers.contracts import build_contract, tool_contract, wrap_failure, wrap_success
from tools.chart_tool import generate_chart
from tools.report_tool import save_report


SERVER_NAME = "report-mcp-server"


def get_tool_contract() -> dict[str, Any]:
    return build_contract(
        SERVER_NAME,
        [
            tool_contract(
                name="generate_chart",
                description="Generate a PNG chart from execution rows and a chart spec.",
                input_schema={"type": "object", "required": ["data", "chart_spec"]},
                output_schema={"type": "object", "required": ["success", "result"]},
                safety={"requires_execution_rows": True},
            ),
            tool_contract(
                name="save_report",
                description="Save a Markdown report only after evidence checking has completed.",
                input_schema={"type": "object", "required": ["run_id", "report_content", "evidence_result"]},
                output_schema={"type": "object", "required": ["success", "result"]},
                safety={"evidence_checked": True, "blocked_claims_not_saved_as_findings": True},
            ),
        ],
    )


def mcp_generate_chart(
    data: dict[str, Any],
    chart_spec: dict[str, Any],
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if output_dir is not None:
        kwargs["output_dir"] = output_dir
    result = generate_chart(data=data, chart_spec=chart_spec, **kwargs)
    if not result.get("success"):
        return wrap_failure(SERVER_NAME, "generate_chart", str(result.get("error", "chart generation failed")), result)
    return wrap_success(SERVER_NAME, "generate_chart", result)


def _evidence_allows_report_save(evidence_result: dict[str, Any]) -> tuple[bool, str]:
    if not evidence_result.get("success"):
        return False, "Evidence validation is required before saving a report"
    blocked_claims = evidence_result.get("unsupported_claims_blocked", [])
    if blocked_claims:
        return False, "Report contains unsupported claims blocked by evidence checking"
    return True, ""


def mcp_save_report(
    run_id: str,
    report_content: str,
    evidence_result: dict[str, Any],
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    allowed, error = _evidence_allows_report_save(evidence_result)
    if not allowed:
        return wrap_failure(SERVER_NAME, "save_report", error, evidence_result=evidence_result)

    kwargs: dict[str, Any] = {}
    if output_dir is not None:
        kwargs["output_dir"] = output_dir
    result = save_report(run_id=run_id, report_content=report_content, **kwargs)
    if not result.get("success"):
        return wrap_failure(SERVER_NAME, "save_report", str(result.get("error", "report save failed")), result)
    return wrap_success(SERVER_NAME, "save_report", result, evidence_result=evidence_result)

