from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from tools.trace_logger import append_trace
from visualization.chart_validator import validate_chart_spec


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _normalize(text: str) -> str:
    return str(text).lower().replace(" ", "")


def _columns(execution_result: dict[str, Any]) -> list[str]:
    return [str(column) for column in execution_result.get("columns") or []]


def _rows(execution_result: dict[str, Any]) -> list[list[Any]]:
    return list(execution_result.get("rows") or [])


def _numeric_columns(execution_result: dict[str, Any]) -> list[str]:
    columns = _columns(execution_result)
    rows = _rows(execution_result)
    numeric = []
    for index, column in enumerate(columns):
        if any(len(row) > index and _is_number(row[index]) for row in rows):
            numeric.append(column)
    return numeric


def _categorical_columns(execution_result: dict[str, Any]) -> list[str]:
    numeric = set(_numeric_columns(execution_result))
    return [column for column in _columns(execution_result) if column not in numeric]


def _time_column(columns: list[str]) -> str:
    for column in columns:
        normalized = _normalize(column)
        if any(token in normalized for token in ("date", "day", "month", "time", "dt", "日期", "月份")):
            return column
    return columns[0] if columns else ""


def _infer_chart_type(question: str, execution_result: dict[str, Any]) -> str:
    normalized = _normalize(question)
    columns = _columns(execution_result)
    if any(token in normalized for token in ("riskmatrix", "风险矩阵", "highrisk", "高风险")):
        return "risk_matrix"
    if any(token in normalized for token in ("funnel", "漏斗", "转化")):
        return "funnel"
    if any(token in normalized for token in ("heatmap", "热力", "cohort")):
        return "heatmap"
    if any(token in normalized for token in ("scatter", "散点", " vs ", "vs")):
        return "scatter"
    if any(token in normalized for token in ("dualaxis", "双轴", "refundrate", "退款率")) and len(_numeric_columns(execution_result)) >= 2:
        return "dual_axis_line"
    if any(token in normalized for token in ("groupedbar", "分组", "grouped", "comparison")) and len(_categorical_columns(execution_result)) >= 2:
        return "grouped_bar"
    if any(token in normalized for token in ("line", "趋势", "trend")):
        return "line"
    if any(any(token in _normalize(column) for token in ("date", "day", "month")) for column in columns):
        return "line"
    return "ranked_bar"


def _required_columns(*columns: str) -> list[str]:
    return [column for column in dict.fromkeys(columns) if column]


def _base_spec(
    chart_type: str,
    title: str,
    x: str,
    y: str,
    *,
    y_secondary: str = "",
    series: str = "",
    provider_called: bool = False,
    fallback_used: bool = False,
    validation_error: str = "",
    provider_error: str = "",
) -> dict[str, Any]:
    return {
        "success": True,
        "source": "deterministic",
        "chart_type": chart_type,
        "title": title,
        "x": x,
        "y": y,
        "y_secondary": y_secondary,
        "series": series,
        "required_columns": _required_columns(x, y, y_secondary, series),
        "explanation_basis": ["supported_findings"],
        "provider_called": provider_called,
        "fallback_used": fallback_used,
        "prompt_id": "",
        "validation_error": validation_error,
        "provider_error": provider_error,
    }


def _deterministic_spec(
    question: str,
    execution_result: dict[str, Any],
    *,
    provider_called: bool,
    validation_error: str = "",
    provider_error: str = "",
) -> dict[str, Any]:
    columns = _columns(execution_result)
    numeric = _numeric_columns(execution_result)
    categorical = _categorical_columns(execution_result)
    chart_type = _infer_chart_type(question, execution_result)

    first_numeric = numeric[0] if numeric else (columns[1] if len(columns) > 1 else "")
    second_numeric = numeric[1] if len(numeric) > 1 else ""
    first_category = categorical[0] if categorical else (columns[0] if columns else "")
    second_category = categorical[1] if len(categorical) > 1 else ""

    if chart_type == "line":
        x, y, series = _time_column(columns), first_numeric, ""
    elif chart_type == "grouped_bar":
        x, y, series = first_category, first_numeric, second_category
    elif chart_type == "dual_axis_line":
        x, y, series = _time_column(columns), first_numeric, ""
        second_numeric = second_numeric or first_numeric
    elif chart_type == "funnel":
        x, y, series = first_category, first_numeric, ""
    elif chart_type == "heatmap":
        x, y, series = first_category, first_numeric, second_category
    elif chart_type in {"scatter", "risk_matrix"}:
        x, y, series = first_numeric, second_numeric or first_numeric, first_category
    else:
        x, y, series = first_category, first_numeric, ""

    spec = _base_spec(
        chart_type,
        f"{chart_type.replace('_', ' ').title()}: {y} by {x}",
        x,
        y,
        y_secondary=second_numeric if chart_type == "dual_axis_line" else "",
        series=series,
        provider_called=provider_called,
        fallback_used=provider_called,
        validation_error=validation_error,
        provider_error=provider_error,
    )
    validated = validate_chart_spec(spec, execution_result)
    if validated.get("success"):
        if validation_error:
            validated["validation_error"] = validation_error
        if provider_error:
            validated["provider_error"] = provider_error
        return validated
    if chart_type != "ranked_bar" and categorical and numeric:
        fallback_spec = _base_spec(
            "ranked_bar",
            f"Ranked Bar: {numeric[0]} by {categorical[0]}",
            categorical[0],
            numeric[0],
            provider_called=provider_called,
            fallback_used=True,
            validation_error=validated.get("validation_error", validation_error),
            provider_error=provider_error,
        )
        fallback_validated = validate_chart_spec(fallback_spec, execution_result)
        if fallback_validated.get("success"):
            if validation_error:
                fallback_validated["validation_error"] = validation_error
            if provider_error:
                fallback_validated["provider_error"] = provider_error
            return fallback_validated
    return {
        **spec,
        "success": False,
        "validation_error": validated.get("validation_error", "unable to produce valid chart spec"),
    }


def _provider_spec(content: dict[str, Any], provider_response: dict[str, Any], execution_result: dict[str, Any]) -> dict[str, Any]:
    spec = {
        **content,
        "success": True,
        "source": "provider",
        "provider_called": True,
        "fallback_used": False,
        "prompt_id": provider_response.get("prompt_id", "visualization_planner"),
        "prompt_version": provider_response.get("prompt_version", ""),
        "validation_error": "",
        "provider_error": "",
        "model": provider_response.get("model", ""),
        "usage": provider_response.get("usage", {}),
        "latency_ms": provider_response.get("latency_ms", 0),
    }
    return validate_chart_spec(spec, execution_result)


def plan_visualization(
    question: str,
    *,
    analysis_steps: list[dict[str, Any]] | None,
    execution_result: dict[str, Any],
    evidence_result: dict[str, Any] | None = None,
    provider: LLMProvider | None = None,
    deterministic_fallback: bool = True,
) -> dict[str, Any]:
    if provider is None:
        return _deterministic_spec(question, execution_result, provider_called=False)

    deterministic = _deterministic_spec(question, execution_result, provider_called=False)
    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "visualization_planner",
        {
            "user_question": question,
            "analysis_steps": analysis_steps or [],
            "execution_columns": _columns(execution_result),
            "execution_sample_rows": _rows(execution_result)[:10],
            "evidence_result": evidence_result or {},
            "deterministic_spec": deterministic,
        },
    )
    if not rendered.get("success"):
        if deterministic_fallback:
            return _deterministic_spec(question, execution_result, provider_called=False, provider_error=rendered.get("error", ""))
        return {
            "success": False,
            "source": "provider",
            "provider_called": False,
            "fallback_used": False,
            "provider_error": rendered.get("error", ""),
            "validation_error": "",
            "error": rendered.get("error", ""),
        }

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "visualization_planner_agent"},
    )
    provider_response = run_validated_llm_request(
        provider,
        request,
        schema_context={"execution_columns": _columns(execution_result)},
    )
    if provider_response.get("success"):
        provider_spec = _provider_spec(provider_response.get("content", {}), provider_response, execution_result)
        if provider_spec.get("success"):
            return provider_spec
        if not deterministic_fallback:
            return {
                **provider_spec,
                "source": "provider",
                "provider_called": True,
                "fallback_used": False,
            }
        return _deterministic_spec(
            question,
            execution_result,
            provider_called=True,
            validation_error=provider_spec.get("validation_error", ""),
        )

    error = provider_response.get("error", "")
    error_type = provider_response.get("error_type", "")
    if not deterministic_fallback:
        return {
            "success": False,
            "source": "provider",
            "provider_called": True,
            "fallback_used": False,
            "provider_error": error,
            "validation_error": error if error_type == "llm_schema_validation_error" else "",
            "error": error,
            "error_type": error_type,
        }
    if error_type == "llm_schema_validation_error":
        return _deterministic_spec(question, execution_result, provider_called=True, validation_error=error)
    return _deterministic_spec(question, execution_result, provider_called=True, provider_error=error)


def run_visualization_planner_agent(state: dict[str, Any], provider: LLMProvider | None = None) -> dict[str, Any]:
    execution_result = state.get("execution_result") or {}
    if not execution_result.get("success"):
        return dict(state)
    spec = plan_visualization(
        state.get("user_question", ""),
        analysis_steps=state.get("analysis_steps", []),
        execution_result=execution_result,
        evidence_result=state.get("evidence_result", {}),
        provider=provider,
    )
    updated = {**state, "visualization_plan": spec}
    return append_trace(
        updated,
        {
            "node": "visualization_planner_agent",
            "tool_name": "visualization_planner",
            "tool_input_summary": state.get("user_question", ""),
            "tool_output_summary": (
                f"chart_type={spec.get('chart_type')} provider_called={spec.get('provider_called', False)} "
                f"fallback_used={spec.get('fallback_used', False)}"
            ),
            "status": "success" if spec.get("success") else "error",
            "latency_ms": 0,
            "error_type": None if spec.get("success") else "visualization_planner_error",
            "error": spec.get("validation_error") or spec.get("provider_error") or None,
            "provider_called": bool(spec.get("provider_called", False)),
            "fallback_used": bool(spec.get("fallback_used", False)),
            "prompt_id": spec.get("prompt_id", ""),
        },
    )
