from __future__ import annotations

from pathlib import Path
from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from tools.external_visualization_tool import call_external_visualization_tool
from tools.trace_logger import append_trace
from visualization.echarts_option_builder import build_echarts_option
from visualization.chart_validator import validate_chart_spec
from visualization_delivery.policy import validate_delivery_tool
from visualization_delivery.tool_catalog import DELIVERY_TOOL_CATALOG
from workspaces.answer_evidence import business_field_label
from workspaces.question_evidence_ledger import build_grouped_chart_candidate


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


def _numeric_columns(execution_result: dict[str, Any]) -> list[str]:
    columns = _columns(execution_result)
    rows = _rows(execution_result)
    numeric: list[str] = []
    for index, column in enumerate(columns):
        if any(len(row) > index and _is_number(row[index]) for row in rows):
            numeric.append(column)
    return numeric


def _chart_ready_execution_result(state: dict[str, Any]) -> tuple[dict[str, Any], str, dict[str, Any]]:
    execution_result = state.get("execution_result") if isinstance(state.get("execution_result"), dict) else {}
    ledger = state.get("question_evidence_ledger") if isinstance(state.get("question_evidence_ledger"), dict) else {}
    if ledger:
        candidate = build_grouped_chart_candidate(ledger, question=str(state.get("user_question") or ""))
        if not candidate.get("success"):
            return {}, "question_evidence_ledger.evidence_groups", candidate
        return (
            {
                "success": True,
                "columns": list(candidate.get("columns") or []),
                "rows": list(candidate.get("rows") or []),
                "row_count": int(candidate.get("row_count") or len(candidate.get("rows") or [])),
                "chart_input_source": "question_evidence_ledger.evidence_groups",
                "evidence_refs": list(candidate.get("evidence_refs") or []),
                "units": dict(candidate.get("units") or {}),
                "chart_candidate": candidate,
            },
            "question_evidence_ledger.evidence_groups",
            candidate,
        )
    if _has_internal_columns(execution_result):
        return {}, "question_evidence_ledger.evidence_groups", {
            "success": False,
            "reason": "缺少可用于图表的分组证据，系统不会从任务明细行拼接混合图表。",
        }
    if _safe_single_metric_execution_result(execution_result):
        return execution_result, "execution_result", {}
    return {}, "execution_result", {
        "success": False,
        "reason": "当前结果不是单一业务维度和单一指标，缺少可安全生成图表的分组证据。",
    }


def _has_internal_columns(execution_result: dict[str, Any]) -> bool:
    return any(column in {"task_id", "task_purpose", "ledger_id"} for column in _columns(execution_result))


def _safe_single_metric_execution_result(execution_result: dict[str, Any]) -> bool:
    if not execution_result.get("success") or not _rows(execution_result):
        return False
    columns = _columns(execution_result)
    if len(columns) < 2 or _has_internal_columns(execution_result):
        return False
    numeric_columns = _numeric_columns(execution_result)
    if len(numeric_columns) != 1:
        return False
    dimension_columns = [column for column in columns if column not in numeric_columns]
    return len(dimension_columns) == 1


def _is_long_metric_chart_table(execution_result: dict[str, Any]) -> bool:
    return _columns(execution_result) == ["对象", "指标", "数值"]


def _chart_type_for_question(question: str, execution_result: dict[str, Any]) -> str:
    if _is_long_metric_chart_table(execution_result):
        return "grouped_bar"
    text = str(question or "").lower()
    if any(marker in text for marker in ("趋势", "走势", "变化", "trend")):
        return "line"
    if (
        any(marker in text for marker in ("比较", "对比", "建议", "推荐", "值得", "关注", "recommend", "compare"))
        and len(_numeric_columns(execution_result)) >= 2
    ):
        return "scatter"
    if any(marker in text for marker in ("最高", "最低", "排名", "top", "rank", "哪个")):
        return "ranked_bar"
    return "ranked_bar"


def _business_label(column: str) -> str:
    return business_field_label(column, chinese=True)


def _fallback_chart_spec(
    question: str,
    execution_result: dict[str, Any],
    *,
    run_id: str,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    columns = _columns(execution_result)
    x = columns[0] if columns else ""
    numeric_columns = _numeric_columns(execution_result)
    y = numeric_columns[0] if numeric_columns else _first_numeric_column(execution_result)
    y_secondary = numeric_columns[1] if len(numeric_columns) >= 2 else ""
    if y == x and len(columns) > 1:
        y = columns[1]
    chart_type = _chart_type_for_question(question, execution_result)
    if chart_type == "grouped_bar" and _is_long_metric_chart_table(execution_result):
        x = "对象"
        y = "数值"
        series = "指标"
        y_secondary = ""
    else:
        series = ""
    if chart_type == "scatter" and len(numeric_columns) >= 2:
        x = numeric_columns[0]
        y = numeric_columns[1]
    spec = {
        "success": True,
        "source": "fallback",
        "chart_type": chart_type,
        "title": _fallback_chart_title(chart_type=chart_type, x=x, y=y, y_secondary=y_secondary),
        "x": x,
        "y": y,
        "y_secondary": y_secondary if chart_type in {"dual_axis_line", "risk_matrix"} else "",
        "series": series,
        "required_columns": [column for column in [x, y] if column],
        "explanation_basis": ["supported_findings"],
        "business_annotation": _fallback_business_annotation(chart_type=chart_type),
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


def _fallback_chart_title(*, chart_type: str, x: str, y: str, y_secondary: str) -> str:
    x_label = _business_label(x)
    y_label = _business_label(y)
    secondary_label = _business_label(y_secondary)
    if chart_type == "line":
        return f"{y_label}趋势"
    if chart_type == "scatter":
        return f"{x_label}与{y_label}对比"
    return f"{x_label}{y_label}对比"


def _fallback_business_annotation(*, chart_type: str) -> str:
    if chart_type == "line":
        return "图表展示本轮查询返回的指标变化趋势，请结合业务结论判断异常或拐点。"
    if chart_type == "scatter":
        return "图表展示本轮查询返回对象在两个指标上的相对位置，请结合业务目标判断优先级。"
    return "图表展示本轮查询返回对象的指标排序，请结合业务结论解读。"


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
    question: str,
    execution_result: dict[str, Any],
    *,
    run_id: str,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    chart_spec = _fallback_chart_spec(
        question,
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


def _decision_from_candidate(candidate: dict[str, Any], execution_result: dict[str, Any], *, run_id: str) -> dict[str, Any]:
    chart_spec = candidate.get("chart_spec") if isinstance(candidate.get("chart_spec"), dict) else {}
    chart_validation = validate_chart_spec(chart_spec, execution_result)
    if not chart_validation.get("success"):
        return _skipped_decision(
            str(chart_validation.get("validation_error") or "分组图表证据未通过校验。"),
            chart_input_source="question_evidence_ledger.evidence_groups",
        )
    return {
        "success": True,
        "source": "grouped_ledger_candidate",
        "chart_spec": chart_validation,
        "delivery_tool_id": "local_renderer",
        "tool_reason": "使用分组证据账本中同一业务对象和同一颗粒度的可比指标生成本地图表。",
        "provider_called": False,
        "fallback_used": False,
        "prompt_id": "",
        "validation_error": "",
        "provider_error": "",
        "fabricated_data": False,
        "data_row_count": len(_rows(execution_result)),
        "chart_input_source": "question_evidence_ledger.evidence_groups",
        "evidence_refs": list(candidate.get("evidence_refs") or []),
        "run_id": run_id,
    }


def _skipped_decision(reason: str, *, chart_input_source: str) -> dict[str, Any]:
    clean_reason = _business_skip_reason(reason)
    return {
        "success": False,
        "source": "grouped_ledger_candidate",
        "chart_spec": {},
        "delivery_tool_id": "",
        "tool_reason": clean_reason,
        "provider_called": False,
        "fallback_used": False,
        "prompt_id": "",
        "validation_error": clean_reason,
        "provider_error": "",
        "fabricated_data": False,
        "data_row_count": 0,
        "chart_input_source": chart_input_source,
        "skip_reason": clean_reason,
    }


def _skipped_delivery(reason: str, *, chart_input_source: str) -> dict[str, Any]:
    return {
        "success": False,
        "rendering_status": "skipped",
        "renderer": "none",
        "source": "analysis_workbench",
        "skip_reason": _business_skip_reason(reason),
        "chart_input_source": chart_input_source,
        "data_row_count": 0,
    }


def _business_skip_reason(reason: str) -> str:
    text = str(reason or "").strip()
    if not text:
        return "当前证据不适合生成一张可靠图表。"
    for marker in ("task_id", "task_purpose", "SELECT", "provider_metadata", "trace_path", "ledger_id"):
        text = text.replace(marker, "")
    return " ".join(text.split())


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
        decision = _decision_from_fallback(
            question,
            execution_result,
            run_id=run_id,
            provider_called=False,
            provider_error="provider_unavailable",
        )
        decision["chart_input_source"] = str(execution_result.get("chart_input_source") or "")
        return decision

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
        decision = _decision_from_fallback(
            question,
            execution_result,
            run_id=run_id,
            provider_called=False,
            provider_error=rendered.get("error", ""),
        )
        decision["chart_input_source"] = str(execution_result.get("chart_input_source") or "")
        return decision

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
        decision = _decision_from_fallback(
            question,
            execution_result,
            run_id=run_id,
            provider_called=True,
            provider_error=error if error_type != "llm_schema_validation_error" else "",
            validation_error=error if error_type == "llm_schema_validation_error" else "",
        )
        decision["chart_input_source"] = str(execution_result.get("chart_input_source") or "")
        return decision

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
        decision = _decision_from_fallback(
            question,
            execution_result,
            run_id=run_id,
            provider_called=True,
            validation_error=chart_validation.get("validation_error", ""),
        )
        decision["chart_input_source"] = str(execution_result.get("chart_input_source") or "")
        return decision

    policy = validate_delivery_tool(content["delivery_tool_id"], execution_result=execution_result)
    if not policy.get("success"):
        decision = _decision_from_fallback(
            question,
            execution_result,
            run_id=run_id,
            provider_called=True,
            validation_error=policy.get("validation_error", ""),
        )
        decision["chart_input_source"] = str(execution_result.get("chart_input_source") or "")
        return decision

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
        "chart_input_source": str(execution_result.get("chart_input_source") or ""),
    }


def _trace_from(decision: dict[str, Any], delivery_result: dict[str, Any]) -> dict[str, Any]:
    chart_spec = decision.get("chart_spec") if isinstance(decision.get("chart_spec"), dict) else {}
    trace = {
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
        "chart_input_source": decision.get("chart_input_source", ""),
        "chart_spec": chart_spec,
        "title": chart_spec.get("title", ""),
        "unit": chart_spec.get("unit", ""),
        "value_label": bool(chart_spec.get("value_label", False)),
        "business_annotation": chart_spec.get("business_annotation", ""),
    }
    if decision.get("skip_reason") or delivery_result.get("skip_reason"):
        trace["skip_reason"] = decision.get("skip_reason") or delivery_result.get("skip_reason")
        trace["rendering_status"] = "skipped"
    for key in (
        "artifact_id",
        "renderer",
        "chart_type",
        "chart_spec",
        "echarts_option",
        "image_path",
        "image_url",
        "evidence_refs",
        "source",
        "data_row_count",
        "rendering_status",
        "echarts_fallback_reason",
        "skip_reason",
        "chart_input_source",
    ):
        value = delivery_result.get(key)
        if value not in (None, ""):
            trace[key] = value
    return trace


def _artifact_id(run_id: str, chart_type: str) -> str:
    safe_run = "".join(character if character.isalnum() or character == "_" else "_" for character in run_id)
    safe_type = "".join(character if character.isalnum() or character == "_" else "_" for character in chart_type)
    return f"chart_{safe_run}_{safe_type or 'artifact'}"


def _with_echarts_payload(
    delivery_result: dict[str, Any],
    *,
    decision: dict[str, Any],
    execution_result: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    updated = dict(delivery_result)
    chart_spec = decision.get("chart_spec") if isinstance(decision.get("chart_spec"), dict) else {}
    artifact_path = str(updated.get("artifact_path") or updated.get("chart_path") or "")
    artifact_url = str(updated.get("artifact_url") or "")
    if artifact_path:
        updated["image_path"] = artifact_path
    if artifact_url:
        updated["image_url"] = artifact_url

    if not updated.get("success") or updated.get("delivery_tool_id") != "local_renderer" or not artifact_path:
        return updated

    try:
        option_result = build_echarts_option(
            chart_spec,
            execution_result,
            unit=str(chart_spec.get("unit") or ""),
            value_label=str(chart_spec.get("y") or ""),
        )
    except Exception as exc:
        updated["renderer"] = "image"
        updated["echarts_fallback_reason"] = str(exc)
        return updated

    if option_result.get("success") and isinstance(option_result.get("echarts_option"), dict):
        chart_type = str(option_result.get("chart_type") or chart_spec.get("chart_type") or updated.get("chart_type") or "")
        updated.update(
            {
                "artifact_id": updated.get("artifact_id") or _artifact_id(run_id, chart_type),
                "renderer": "echarts",
                "chart_type": chart_type,
                "chart_spec": chart_spec,
                "echarts_option": option_result["echarts_option"],
                "evidence_refs": list(execution_result.get("evidence_refs") or []) or ["question_evidence_pack"],
                "source": "analysis_workbench",
                "data_row_count": int(option_result.get("data_row_count") or updated.get("data_row_count") or 0),
                "rendering_status": "rendered",
            }
        )
        return updated

    updated["renderer"] = "image"
    updated["chart_spec"] = chart_spec
    updated["source"] = "analysis_workbench"
    updated["data_row_count"] = int(updated.get("data_row_count") or len(_rows(execution_result)))
    updated["rendering_status"] = "rendered"
    updated["echarts_fallback_reason"] = str(
        option_result.get("validation_error") or option_result.get("fallback_reason") or "echarts option unavailable"
    )
    return updated


def run_visualization_agent(
    state: dict[str, Any],
    provider: LLMProvider | None = None,
    output_dir: str | Path = Path("reports/charts"),
) -> dict[str, Any]:
    execution_result = state.get("execution_result") or {}
    if not execution_result.get("success"):
        return dict(state)
    chart_execution_result, chart_input_source, chart_candidate = _chart_ready_execution_result(state)

    run_id = str(state.get("run_id", "run_unknown"))
    if not chart_execution_result:
        reason = str(chart_candidate.get("reason") or "当前证据不适合生成一张可靠图表。")
        decision = _skipped_decision(reason, chart_input_source=chart_input_source)
        delivery_result = _skipped_delivery(reason, chart_input_source=chart_input_source)
        visualization_trace = _trace_from(decision, delivery_result)
        updated = {
            **state,
            "visualization_decision": decision,
            "visualization_plan": {},
            "visualization_delivery_result": delivery_result,
            "visualization_trace": visualization_trace,
            "chart_result": delivery_result,
            "chart_warning": delivery_result["skip_reason"],
        }
        return append_trace(
            updated,
            {
                "node": "visualization_agent",
                "tool_name": "grouped_chart_candidate",
                "tool_input_summary": chart_input_source,
                "tool_output_summary": delivery_result["skip_reason"],
                "status": "skipped",
                "latency_ms": 0,
                "error_type": None,
                "error": None,
                **visualization_trace,
            },
        )

    if chart_candidate.get("success"):
        decision = _decision_from_candidate(chart_candidate, chart_execution_result, run_id=run_id)
    else:
        decision = decide_visualization(
            state.get("user_question", ""),
            analysis_steps=state.get("analysis_steps", []),
            execution_result=chart_execution_result,
            evidence_result=state.get("evidence_result", {}),
            provider=provider,
            run_id=run_id,
        )
    decision["chart_input_source"] = chart_input_source
    if not decision.get("success"):
        reason = str(decision.get("skip_reason") or decision.get("validation_error") or "当前证据不适合生成一张可靠图表。")
        delivery_result = _skipped_delivery(reason, chart_input_source=chart_input_source)
        visualization_trace = _trace_from(decision, delivery_result)
        updated = {
            **state,
            "visualization_decision": decision,
            "visualization_plan": {},
            "visualization_delivery_result": delivery_result,
            "visualization_trace": visualization_trace,
            "chart_result": delivery_result,
            "chart_warning": delivery_result["skip_reason"],
        }
        return append_trace(
            updated,
            {
                "node": "visualization_agent",
                "tool_name": "grouped_chart_candidate",
                "tool_input_summary": chart_input_source,
                "tool_output_summary": delivery_result["skip_reason"],
                "status": "skipped",
                "latency_ms": 0,
                "error_type": None,
                "error": None,
                **visualization_trace,
            },
        )
    delivery_result = call_external_visualization_tool(
        delivery_tool_id=decision.get("delivery_tool_id", "local_renderer"),
        chart_spec=decision.get("chart_spec", {}),
        execution_result=chart_execution_result,
        run_id=run_id,
        output_dir=output_dir,
    )
    delivery_result = _with_echarts_payload(
        delivery_result,
        decision=decision,
        execution_result=chart_execution_result,
        run_id=run_id,
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
