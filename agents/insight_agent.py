from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from tools.trace_logger import append_trace


def _format_row(columns: list[str], row: list[Any]) -> str:
    pairs = [f"{column}={value}" for column, value in zip(columns, row, strict=False)]
    return ", ".join(pairs)


def _row_claims(execution_result: dict[str, Any], limit: int = 5) -> list[str]:
    columns = execution_result.get("columns", [])
    rows = execution_result.get("rows", [])
    return [_format_row(columns, row) for row in rows[:limit]]


def _answer_from_result(question: str, execution_result: dict[str, Any]) -> str:
    rows = execution_result.get("rows", [])
    if not rows:
        return "查询已执行成功，但 execution_result 没有返回数据行。"

    lines = [f"基于 execution_result，问题「{question}」的结果如下："]
    for index, claim in enumerate(_row_claims(execution_result), start=1):
        lines.append(f"{index}. {claim}")
    if execution_result.get("truncated"):
        lines.append("结果已按 max_rows 截断。")
    return "\n".join(lines)


def _fallback_output(
    state: dict[str, Any],
    execution_result: dict[str, Any] | None,
    *,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> tuple[dict[str, Any], str]:
    if not execution_result:
        return (
            {
                "success": False,
                "source": "provider_unavailable" if provider_called else "deterministic",
                "provider_called": provider_called,
                "fallback_used": True,
                "final_answer": "缺少 execution_result，无法生成基于数据的回答。",
                "candidate_claims": [],
                "data_used": False,
                "error": "execution_result is required",
                "provider_error": provider_error,
                "validation_error": validation_error,
                "prompt_id": "insight_drafter",
            },
            "error",
        )
    if not execution_result.get("success"):
        return (
            {
                "success": False,
                "source": "provider_unavailable" if provider_called else "deterministic",
                "provider_called": provider_called,
                "fallback_used": True,
                "final_answer": f"SQL 执行失败：{execution_result.get('error', 'unknown error')}",
                "candidate_claims": [],
                "data_used": False,
                "error": execution_result.get("error", "execution_result failed"),
                "provider_error": provider_error,
                "validation_error": validation_error,
                "prompt_id": "insight_drafter",
            },
            "error",
        )
    return (
        {
            "success": True,
            "source": "provider_unavailable" if provider_called else "deterministic",
            "provider_called": provider_called,
            "fallback_used": True,
            "final_answer": _answer_from_result(state.get("user_question", ""), execution_result),
            "candidate_claims": _row_claims(execution_result),
            "data_used": True,
            "error": "",
            "provider_error": provider_error,
            "validation_error": validation_error,
            "prompt_id": "insight_drafter",
        },
        "success",
    )


def _provider_output(state: dict[str, Any], provider: LLMProvider, execution_result: dict[str, Any]) -> tuple[dict[str, Any], str]:
    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "insight_drafter",
        {
            "user_question": state.get("user_question", ""),
            "execution_result": execution_result,
            "business_context": state.get("business_context", {}),
            "metric_context": state.get("metric_context", {}),
        },
    )
    if not rendered.get("success"):
        return _fallback_output(
            state,
            execution_result,
            provider_called=True,
            provider_error=rendered.get("error", ""),
        )

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "insight_agent"},
    )
    response = run_validated_llm_request(provider, request)
    if not response.get("success"):
        if response.get("error_type") == "llm_schema_validation_error":
            return _fallback_output(
                state,
                execution_result,
                provider_called=True,
                validation_error=response.get("error", ""),
            )
        return _fallback_output(
            state,
            execution_result,
            provider_called=True,
            provider_error=response.get("error", ""),
        )

    content = response.get("content", {})
    output = {
        "success": True,
        "source": "provider",
        "provider_called": True,
        "fallback_used": False,
        "final_answer": content.get("draft_summary", ""),
        "candidate_claims": content.get("candidate_claims", []),
        "data_used": True,
        "error": "",
        "provider_error": "",
        "validation_error": "",
        "prompt_id": response.get("prompt_id", "insight_drafter"),
        "prompt_version": response.get("prompt_version", ""),
        "model": response.get("model", ""),
        "usage": response.get("usage", {}),
        "latency_ms": response.get("latency_ms", 0),
    }
    return output, "success"


def run_insight_agent(state: dict[str, Any], provider: LLMProvider | None = None) -> dict[str, Any]:
    execution_result = state.get("execution_result")
    if provider and execution_result and execution_result.get("success"):
        output, status = _provider_output(state, provider, execution_result)
    else:
        output, status = _fallback_output(
            state,
            execution_result,
            provider_called=provider is not None,
            provider_error="" if provider is None else "provider requires successful execution_result",
        )

    updated = {
        **state,
        "insight": output,
        "final_answer": output["final_answer"],
        "claims_to_validate": output.get("candidate_claims", []),
    }
    return append_trace(
        updated,
        {
            "node": "insight_agent",
            "tool_name": "",
            "tool_input_summary": f"row_count={execution_result.get('row_count') if execution_result else 0}",
            "tool_output_summary": output["final_answer"][:200],
            "status": status,
            "latency_ms": 0,
            "error_type": None if output.get("success") else "insight_error",
            "retry_count": state.get("retry_count", 0),
            "provider_called": bool(output.get("provider_called", False)),
            "fallback_used": bool(output.get("fallback_used", False)),
            "prompt_id": output.get("prompt_id", "insight_drafter"),
            "validation_error": output.get("validation_error", ""),
            "provider_error": output.get("provider_error", ""),
        },
    )
