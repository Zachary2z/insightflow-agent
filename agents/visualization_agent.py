from __future__ import annotations

from pathlib import Path
from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from tools.external_visualization_tool import call_external_visualization_tool
from tools.trace_logger import append_trace
from visualization.chart_validator import validate_chart_spec
from visualization_delivery.policy import validate_delivery_tool
from visualization_delivery.tool_catalog import DELIVERY_TOOL_CATALOG


PROMPT_ID = "visualization_agent"


def _columns(execution_result: dict[str, Any]) -> list[str]:
    return [str(column) for column in execution_result.get("columns") or []]


def _rows(execution_result: dict[str, Any]) -> list[list[Any]]:
    return list(execution_result.get("rows") or [])


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _first_numeric_column(execution_result: dict[str, Any]) -> str:
    columns = _columns(execution_result)
    rows = _rows(execution_result)
    for index, column in enumerate(columns):
        if any(len(row) > index and _is_number(row[index]) for row in rows):
            return column
    return columns[1] if len(columns) > 1 else ""


def _fallback_chart_spec(
    execution_result: dict[str, Any],
    *,
    run_id: str,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    columns = _columns(execution_result)
    x = columns[0] if columns else ""
    y = _first_numeric_column(execution_result)
    if y == x and len(columns) > 1:
        y = columns[1]
    spec = {
        "success": True,
        "source": "fallback",
        "chart_type": "ranked_bar",
        "title": f"Ranked Bar: {y} by {x}".strip(),
        "x": x,
        "y": y,
        "y_secondary": "",
        "series": "",
        "required_columns": [column for column in [x, y] if column],
        "explanation_basis": ["supported_findings"],
        "provider_called": provider_called,
        "fallback_used": True,
        "prompt_id": PROMPT_ID if provider_called else "",
        "validation_error": validation_error,
        "provider_error": provider_error,
        "run_id": run_id,
    }
    validated = validate_chart_spec(spec, execution_result)
    if validated.get("success"):
        if validation_error:
            validated["validation_error"] = validation_error
        if provider_error:
            validated["provider_error"] = provider_error
        validated["source"] = "fallback"
        validated["fallback_used"] = True
        validated["provider_called"] = provider_called
        validated["prompt_id"] = PROMPT_ID if provider_called else ""
        return validated
    return {
        **spec,
        "success": False,
        "validation_error": validation_error or validated.get("validation_error", "unable to build fallback chart spec"),
    }


def _tool_catalog_for_prompt() -> list[dict[str, Any]]:
    return [
        {
            "delivery_tool_id": tool.tool_id,
            "tool_type": tool.tool_type,
            "description": tool.description,
            "requires_network": tool.requires_network,
            "requires_api_key": tool.requires_api_key,
            "is_mock": tool.is_mock,
        }
        for tool in DELIVERY_TOOL_CATALOG.values()
    ]


def _decision_from_fallback(
    execution_result: dict[str, Any],
    *,
    run_id: str,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    chart_spec = _fallback_chart_spec(
        execution_result,
        run_id=run_id,
        provider_called=provider_called,
        provider_error=provider_error,
        validation_error=validation_error,
    )
    return {
        "success": bool(chart_spec.get("success")),
        "source": "fallback",
        "chart_spec": chart_spec,
        "delivery_tool_id": "local_renderer",
        "tool_reason": "Structured fallback uses the local renderer with real execution rows.",
        "provider_called": provider_called,
        "fallback_used": True,
        "prompt_id": PROMPT_ID if provider_called else "",
        "validation_error": validation_error or chart_spec.get("validation_error", ""),
        "provider_error": provider_error,
        "fabricated_data": False,
        "data_row_count": len(_rows(execution_result)),
    }


def decide_visualization(
    question: str,
    *,
    analysis_steps: list[dict[str, Any]] | None,
    execution_result: dict[str, Any],
    evidence_result: dict[str, Any] | None = None,
    provider: LLMProvider | None = None,
    run_id: str = "run_unknown",
) -> dict[str, Any]:
    if provider is None:
        return _decision_from_fallback(
            execution_result,
            run_id=run_id,
            provider_called=False,
            provider_error="provider_unavailable",
        )

    rendered = DEFAULT_PROMPT_REGISTRY.render(
        PROMPT_ID,
        {
            "user_question": question,
            "analysis_steps": analysis_steps or [],
            "execution_columns": _columns(execution_result),
            "execution_sample_rows": _rows(execution_result)[:10],
            "evidence_result": evidence_result or {},
            "delivery_tool_catalog": _tool_catalog_for_prompt(),
        },
    )
    if not rendered.get("success"):
        return _decision_from_fallback(
            execution_result,
            run_id=run_id,
            provider_called=False,
            provider_error=rendered.get("error", ""),
        )

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "visualization_agent"},
    )
    provider_response = run_validated_llm_request(
        provider,
        request,
        schema_context={
            "execution_columns": _columns(execution_result),
            "delivery_tool_ids": list(DELIVERY_TOOL_CATALOG),
        },
    )
    if not provider_response.get("success"):
        error = provider_response.get("error", "")
        error_type = provider_response.get("error_type", "")
        return _decision_from_fallback(
            execution_result,
            run_id=run_id,
            provider_called=True,
            provider_error=error if error_type != "llm_schema_validation_error" else "",
            validation_error=error if error_type == "llm_schema_validation_error" else "",
        )

    content = provider_response.get("content") or {}
    chart_spec = {
        **content["chart_spec"],
        "success": True,
        "source": "provider",
        "provider_called": True,
        "fallback_used": False,
        "prompt_id": provider_response.get("prompt_id", PROMPT_ID),
        "prompt_version": provider_response.get("prompt_version", ""),
        "provider_error": "",
        "validation_error": "",
        "run_id": run_id,
        "model": provider_response.get("model", ""),
        "usage": provider_response.get("usage", {}),
        "latency_ms": provider_response.get("latency_ms", 0),
    }
    chart_validation = validate_chart_spec(chart_spec, execution_result)
    if not chart_validation.get("success"):
        return _decision_from_fallback(
            execution_result,
            run_id=run_id,
            provider_called=True,
            validation_error=chart_validation.get("validation_error", ""),
        )

    policy = validate_delivery_tool(content["delivery_tool_id"], execution_result=execution_result)
    if not policy.get("success"):
        return _decision_from_fallback(
            execution_result,
            run_id=run_id,
            provider_called=True,
            validation_error=policy.get("validation_error", ""),
        )

    return {
        "success": True,
        "source": "provider",
        "chart_spec": chart_validation,
        "delivery_tool_id": policy["delivery_tool_id"],
        "tool_reason": content["tool_reason"],
        "provider_called": True,
        "fallback_used": False,
        "prompt_id": provider_response.get("prompt_id", PROMPT_ID),
        "prompt_version": provider_response.get("prompt_version", ""),
        "validation_error": "",
        "provider_error": "",
        "model": provider_response.get("model", ""),
        "usage": provider_response.get("usage", {}),
        "latency_ms": provider_response.get("latency_ms", 0),
        "fabricated_data": False,
        "data_row_count": len(_rows(execution_result)),
    }


def _trace_from(decision: dict[str, Any], delivery_result: dict[str, Any]) -> dict[str, Any]:
    chart_spec = decision.get("chart_spec") if isinstance(decision.get("chart_spec"), dict) else {}
    return {
        "provider_called": bool(decision.get("provider_called", False)),
        "fallback_used": bool(decision.get("fallback_used", False)),
        "prompt_id": decision.get("prompt_id", ""),
        "validation_error": decision.get("validation_error", ""),
        "provider_error": decision.get("provider_error", ""),
        "delivery_tool_id": decision.get("delivery_tool_id", ""),
        "external_tool_called": bool(delivery_result.get("external_tool_called", False)),
        "artifact_path": delivery_result.get("artifact_path") or delivery_result.get("chart_path", ""),
        "artifact_url": delivery_result.get("artifact_url", ""),
        "data_row_count": delivery_result.get("data_row_count", decision.get("data_row_count", 0)),
        "fabricated_data": False,
        "chart_spec": chart_spec,
        "title": chart_spec.get("title", ""),
        "unit": chart_spec.get("unit", ""),
        "value_label": bool(chart_spec.get("value_label", False)),
        "business_annotation": chart_spec.get("business_annotation", ""),
    }


def run_visualization_agent(
    state: dict[str, Any],
    provider: LLMProvider | None = None,
    output_dir: str | Path = Path("reports/charts"),
) -> dict[str, Any]:
    execution_result = state.get("execution_result") or {}
    if not execution_result.get("success"):
        return dict(state)

    run_id = str(state.get("run_id", "run_unknown"))
    decision = decide_visualization(
        state.get("user_question", ""),
        analysis_steps=state.get("analysis_steps", []),
        execution_result=execution_result,
        evidence_result=state.get("evidence_result", {}),
        provider=provider,
        run_id=run_id,
    )
    delivery_result = call_external_visualization_tool(
        delivery_tool_id=decision.get("delivery_tool_id", "local_renderer"),
        chart_spec=decision.get("chart_spec", {}),
        execution_result=execution_result,
        run_id=run_id,
        output_dir=output_dir,
    )
    visualization_trace = _trace_from(decision, delivery_result)
    chart_path = delivery_result.get("artifact_path") or delivery_result.get("chart_path", "")
    chart_paths = list(state.get("chart_paths") or [])
    if chart_path and chart_path not in chart_paths:
        chart_paths.append(chart_path)

    updated = {
        **state,
        "visualization_decision": decision,
        "visualization_plan": decision.get("chart_spec", {}),
        "visualization_delivery_result": delivery_result,
        "visualization_trace": visualization_trace,
        "chart_result": delivery_result,
        "chart_path": chart_path,
        "chart_paths": chart_paths,
    }
    if not delivery_result.get("success"):
        updated["chart_warning"] = delivery_result.get("error", "")

    trace_event = {
        "node": "visualization_agent",
        "tool_name": "external_visualization_tool",
        "tool_input_summary": f"delivery_tool_id={decision.get('delivery_tool_id', '')}",
        "tool_output_summary": (chart_path or delivery_result.get("artifact_url") or "")[:200],
        "status": "success" if delivery_result.get("success") else "error",
        "latency_ms": delivery_result.get("latency_ms", 0),
        "error_type": None if delivery_result.get("success") else "visualization_delivery_error",
        "error": None if delivery_result.get("success") else delivery_result.get("error", ""),
        **visualization_trace,
    }
    return append_trace(updated, trace_event)
