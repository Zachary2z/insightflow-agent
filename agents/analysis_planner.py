from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from semantic_layer.loader import load_semantic_layer
from semantic_layer.retriever import retrieve_semantic_context
from tools.trace_logger import append_trace


SCENARIO_TYPES = {
    "quick_metric_lookup",
    "gmv_decline_diagnosis",
    "marketing_roi_review",
    "inventory_risk_analysis",
    "refund_anomaly_analysis",
    "promotion_review",
    "customer_segment_analysis",
    "general_non_template_analysis",
}


_SCENARIO_KEYWORDS = [
    ("marketing_roi_review", ["roi", "roas", "cac", "投放", "营销", "paid search", "广告"]),
    ("inventory_risk_analysis", ["库存", "缺货", "stockout", "inventory"]),
    ("refund_anomaly_analysis", ["退款", "售后", "refund"]),
    ("promotion_review", ["促销", "promotion", "618", "discount", "净 gmv", "净gmv"]),
    ("customer_segment_analysis", ["客户分层", "用户分群", "customer segment", "上海", "城市", "转化"]),
    ("gmv_decline_diagnosis", ["下滑", "下降", "decline", "为什么", "原因"]),
]


_BASE_SCENARIO_STEPS: dict[str, list[dict[str, Any]]] = {
    "quick_metric_lookup": [
        {
            "step_id": "metric_snapshot",
            "question": "Retrieve the requested metric at the most relevant business grain.",
            "required_metrics": ["gmv"],
            "required_dimensions": ["time"],
        }
    ],
    "gmv_decline_diagnosis": [
        {
            "step_id": "gmv_trend",
            "question": "Compare GMV over current and previous periods at the requested category or product grain.",
            "required_metrics": ["gmv"],
            "required_dimensions": ["category", "time"],
        },
        {
            "step_id": "traffic_conversion",
            "question": "Check whether traffic or checkout conversion changed during the GMV decline window.",
            "required_metrics": ["conversion_rate", "checkout_conversion_rate"],
            "required_dimensions": ["category", "channel", "time"],
        },
        {
            "step_id": "inventory_pressure",
            "question": "Check whether stockouts or low available inventory constrained demand.",
            "required_metrics": ["stockout_rate"],
            "required_dimensions": ["product", "category", "time"],
        },
        {
            "step_id": "refund_pressure",
            "question": "Check whether refund pressure increased for the affected category or products.",
            "required_metrics": ["refund_rate"],
            "required_dimensions": ["product", "category", "time"],
        },
    ],
    "marketing_roi_review": [
        {
            "step_id": "spend_return_trend",
            "question": "Compare marketing spend, attributed GMV, ROI, and ROAS over time.",
            "required_metrics": ["roi", "roas", "cac"],
            "required_dimensions": ["campaign", "channel", "time"],
        },
        {
            "step_id": "net_gmv_quality",
            "question": "Check whether net GMV quality changed as campaign spend increased.",
            "required_metrics": ["net_gmv"],
            "required_dimensions": ["campaign", "channel", "time"],
        },
    ],
    "inventory_risk_analysis": [
        {
            "step_id": "stockout_exposure",
            "question": "Identify products or categories with elevated stockout risk.",
            "required_metrics": ["stockout_rate"],
            "required_dimensions": ["product", "category", "time"],
        },
        {
            "step_id": "gmv_at_risk",
            "question": "Estimate which high-GMV products or categories overlap with inventory pressure.",
            "required_metrics": ["gmv"],
            "required_dimensions": ["product", "category", "time"],
        },
    ],
    "refund_anomaly_analysis": [
        {
            "step_id": "refund_rate_trend",
            "question": "Compare refund rate over time for the affected product or category.",
            "required_metrics": ["refund_rate"],
            "required_dimensions": ["product", "category", "time"],
        },
        {
            "step_id": "quality_signal_check",
            "question": "Check whether negative review rate explains the refund anomaly.",
            "required_metrics": ["negative_review_rate"],
            "required_dimensions": ["product", "category", "time"],
        },
    ],
    "promotion_review": [
        {
            "step_id": "promotion_order_lift",
            "question": "Compare promotion-period order count against baseline.",
            "required_metrics": ["order_count"],
            "required_dimensions": ["promotion", "time"],
        },
        {
            "step_id": "aov_and_net_gmv_quality",
            "question": "Check whether promotion lift came with lower AOV or net GMV quality.",
            "required_metrics": ["aov", "net_gmv"],
            "required_dimensions": ["promotion", "category", "time"],
        },
    ],
    "customer_segment_analysis": [
        {
            "step_id": "segment_metric_comparison",
            "question": "Compare core business metrics across customer segment or city groups.",
            "required_metrics": ["gmv", "order_count"],
            "required_dimensions": ["customer_segment", "city", "time"],
        },
        {
            "step_id": "segment_conversion_check",
            "question": "Check whether segment performance is explained by conversion changes.",
            "required_metrics": ["conversion_rate", "checkout_conversion_rate"],
            "required_dimensions": ["city", "channel", "time"],
        },
    ],
    "general_non_template_analysis": [
        {
            "step_id": "semantic_context_scan",
            "question": "Use semantic metrics and dimensions to identify the first analysis grain.",
            "required_metrics": ["gmv"],
            "required_dimensions": ["product", "category", "time"],
        },
        {
            "step_id": "risk_signal_scan",
            "question": "Check available risk signals related to quality, refund, inventory, or fulfillment.",
            "required_metrics": ["refund_rate", "negative_review_rate", "stockout_rate", "on_time_delivery_rate"],
            "required_dimensions": ["product", "category", "time"],
        },
    ],
}


def _normalize(text: str) -> str:
    return str(text).lower().replace(" ", "")


def _ordered_unique(items: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _infer_scenario_type(question: str, semantic_context: dict[str, Any]) -> str:
    normalized = _normalize(question)
    matched_metrics = set(semantic_context.get("matched_metrics", []))
    for scenario_type, keywords in _SCENARIO_KEYWORDS:
        if any(_normalize(keyword) in normalized for keyword in keywords):
            if scenario_type == "gmv_decline_diagnosis" and "gmv" not in matched_metrics and "销售额" not in question:
                continue
            return scenario_type
    if len(matched_metrics) <= 2 and not any(token in normalized for token in ["为什么", "原因", "risk", "风险", "review", "评价"]):
        if matched_metrics & {"gmv", "order_count", "aov", "category_gmv", "product_sales"}:
            return "quick_metric_lookup"
    return "general_non_template_analysis"


def _known_metric_ids() -> set[str]:
    loaded = load_semantic_layer()
    return set(loaded.get("metrics", {})) if loaded.get("success") else set()


def _known_dimension_ids() -> set[str]:
    loaded = load_semantic_layer()
    return set(loaded.get("dimensions", {})) if loaded.get("success") else set()


def _candidate_tables(metric_ids: list[str], dimension_ids: list[str]) -> list[str]:
    loaded = load_semantic_layer()
    if not loaded.get("success"):
        return []

    metrics = loaded["metrics"]
    join_paths = loaded["join_paths"]
    tables: list[str] = []
    metric_set = set(metric_ids)
    dimension_set = set(dimension_ids)
    for path in join_paths.values():
        path_metrics = set(path.get("metrics", []))
        path_dimensions = set(path.get("dimensions", []))
        if not path_metrics & metric_set:
            continue
        if dimension_set and not (path_dimensions & dimension_set):
            continue
        tables.extend(path.get("tables", []))

    for metric_id in metric_ids:
        tables.extend(metrics.get(metric_id, {}).get("required_tables", []))
    return _ordered_unique(tables)


def _semantic_steps(scenario_type: str, semantic_context: dict[str, Any]) -> list[dict[str, Any]]:
    known_metrics = _known_metric_ids()
    known_dimensions = _known_dimension_ids()
    steps = []
    for raw_step in _BASE_SCENARIO_STEPS[scenario_type]:
        metrics = [metric for metric in raw_step["required_metrics"] if metric in known_metrics]
        dimensions = [dimension for dimension in raw_step["required_dimensions"] if dimension in known_dimensions]
        if scenario_type == "quick_metric_lookup":
            matched_metrics = semantic_context.get("matched_metrics", [])
            matched_dimensions = semantic_context.get("matched_dimensions", [])
            metrics = [metric for metric in matched_metrics if metric in known_metrics] or metrics
            dimensions = [dimension for dimension in matched_dimensions if dimension in known_dimensions] or dimensions
        steps.append(
            {
                "step_id": raw_step["step_id"],
                "question": raw_step["question"],
                "required_metrics": metrics,
                "required_dimensions": dimensions,
                "candidate_tables": _candidate_tables(metrics, dimensions),
            }
        )
    return steps


def _deterministic_plan(
    question: str,
    *,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    semantic_context = retrieve_semantic_context(question)
    scenario_type = _infer_scenario_type(question, semantic_context)
    return {
        "success": True,
        "source": "deterministic",
        "scenario_type": scenario_type,
        "analysis_steps": _semantic_steps(scenario_type, semantic_context),
        "provider_called": provider_called,
        "fallback_used": provider_called,
        "prompt_id": "",
        "validation_error": validation_error,
        "provider_error": provider_error,
    }


def _provider_plan(content: dict[str, Any], provider_response: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": True,
        "source": "provider",
        "scenario_type": content["scenario_type"],
        "analysis_steps": content["analysis_steps"],
        "provider_called": True,
        "fallback_used": False,
        "prompt_id": provider_response.get("prompt_id", "analysis_planner"),
        "prompt_version": provider_response.get("prompt_version", ""),
        "validation_error": "",
        "provider_error": "",
        "model": provider_response.get("model", ""),
        "usage": provider_response.get("usage", {}),
        "latency_ms": provider_response.get("latency_ms", 0),
    }


def plan_analysis(
    question: str,
    provider: LLMProvider | None = None,
    deterministic_fallback: bool = True,
) -> dict[str, Any]:
    if provider is None:
        return _deterministic_plan(question, provider_called=False)

    semantic_context = retrieve_semantic_context(question)
    deterministic = _deterministic_plan(question, provider_called=False)
    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "analysis_planner",
        {
            "user_question": question,
            "semantic_context": semantic_context,
            "deterministic_plan": deterministic,
            "supported_scenario_types": sorted(SCENARIO_TYPES),
        },
    )
    if not rendered.get("success"):
        if deterministic_fallback:
            return _deterministic_plan(question, provider_called=False, provider_error=rendered.get("error", ""))
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
        metadata={"node": "analysis_planner_agent"},
    )
    provider_response = run_validated_llm_request(provider, request)
    if provider_response.get("success"):
        return _provider_plan(provider_response.get("content", {}), provider_response)

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
        return _deterministic_plan(question, provider_called=True, validation_error=error)
    return _deterministic_plan(question, provider_called=True, provider_error=error)


def run_analysis_planner_agent(state: dict[str, Any], provider: LLMProvider | None = None) -> dict[str, Any]:
    plan = plan_analysis(state.get("user_question", ""), provider=provider)
    updated = {
        **state,
        "analysis_plan": plan,
        "scenario_type": plan.get("scenario_type", ""),
        "analysis_steps": plan.get("analysis_steps", []),
    }
    return append_trace(
        updated,
        {
            "node": "analysis_planner_agent",
            "tool_name": "scenario_analysis_planner",
            "tool_input_summary": state.get("user_question", ""),
            "tool_output_summary": (
                f"scenario_type={plan.get('scenario_type')} steps={len(plan.get('analysis_steps', []))} "
                f"provider_called={plan.get('provider_called', False)} "
                f"fallback_used={plan.get('fallback_used', False)}"
            ),
            "status": "success" if plan.get("success") else "error",
            "latency_ms": 0,
            "error_type": None if plan.get("success") else "analysis_planner_error",
            "error": plan.get("error") or None,
            "provider_called": bool(plan.get("provider_called", False)),
            "fallback_used": bool(plan.get("fallback_used", False)),
            "prompt_id": plan.get("prompt_id", ""),
        },
    )
