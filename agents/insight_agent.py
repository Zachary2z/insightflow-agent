from __future__ import annotations

from typing import Any

from agents.answer_reviewer import review_answer
from agents.final_answer_composer import compose_final_answer_result
from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from tools.trace_logger import append_trace
from workspaces.product_result_builder import build_business_answer


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

    columns = execution_result.get("columns", [])
    lines = [f"已完成问题「{question}」的查询，共返回 {len(rows)} 行结果。"]
    for index, row in enumerate(rows[:5], start=1):
        parts = [f"{column} 为 {value}" for column, value in zip(columns, row, strict=False)]
        lines.append(f"{index}. " + "，".join(parts) + "。")
    if execution_result.get("truncated"):
        lines.append("结果已按 max_rows 截断。")
    return "\n".join(lines)


def _flatten_execution_values(execution_result: dict[str, Any], limit: int = 5) -> list[Any]:
    values = []
    for row in execution_result.get("rows", [])[:limit]:
        if isinstance(row, dict):
            values.extend(row.values())
        elif isinstance(row, (list, tuple)):
            values.extend(row)
    return [value for value in values if value is not None and str(value).strip()]


def _answer_mentions_exact_value(answer: str, execution_result: dict[str, Any]) -> bool:
    return any(str(value) in answer for value in _flatten_execution_values(execution_result))


def _evidence_anchor(execution_result: dict[str, Any]) -> str:
    rows = execution_result.get("rows", [])
    if not rows:
        return ""
    columns = execution_result.get("columns", [])
    first_row = rows[0]
    if isinstance(first_row, dict):
        pairs = [(str(key), value) for key, value in first_row.items()]
    elif isinstance(first_row, (list, tuple)):
        pairs = [(str(column), value) for column, value in zip(columns, first_row, strict=False)]
    else:
        return ""
    parts = [f"{column} 为 {value}" for column, value in pairs[:3] if value is not None and str(value).strip()]
    if not parts:
        return ""
    return "证据表第一行显示：" + "，".join(parts) + "。"


def _ensure_evidence_anchor(answer: str, execution_result: dict[str, Any]) -> str:
    if _answer_mentions_exact_value(answer, execution_result):
        return answer
    anchor = _evidence_anchor(execution_result)
    if not anchor:
        return answer
    return f"{answer}\n{anchor}" if answer else anchor


def _fallback_output(
    state: dict[str, Any],
    execution_result: dict[str, Any] | None,
    *,
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> tuple[dict[str, Any], str]:
    if not execution_result:
        business_answer = build_business_answer(
            {
                "user_question": state.get("user_question", ""),
                "final_answer": "缺少 execution_result，无法生成基于数据的回答。",
                "execution_result": {},
                "evidence_result": state.get("evidence_result") or {},
            }
        )
        return (
            {
                "success": False,
                "source": "provider_unavailable" if provider_called else "deterministic",
                "provider_called": provider_called,
                "fallback_used": True,
                "final_answer": business_answer["direct_answer"],
                "business_answer": business_answer,
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
        business_answer = build_business_answer(
            {
                "user_question": state.get("user_question", ""),
                "final_answer": f"SQL 执行失败：{execution_result.get('error', 'unknown error')}",
                "execution_result": execution_result,
                "evidence_result": state.get("evidence_result") or {},
            }
        )
        return (
            {
                "success": False,
                "source": "provider_unavailable" if provider_called else "deterministic",
                "provider_called": provider_called,
                "fallback_used": True,
                "final_answer": business_answer["direct_answer"],
                "business_answer": business_answer,
                "candidate_claims": [],
                "data_used": False,
                "error": execution_result.get("error", "execution_result failed"),
                "provider_error": provider_error,
                "validation_error": validation_error,
                "prompt_id": "insight_drafter",
            },
            "error",
        )
    fallback_answer = _answer_from_result(state.get("user_question", ""), execution_result)
    business_answer = build_business_answer(
        {
            "user_question": state.get("user_question", ""),
            "final_answer": fallback_answer,
            "execution_result": execution_result,
            "evidence_result": state.get("evidence_result") or {},
        }
    )
    return (
        {
            "success": True,
            "source": "provider_unavailable" if provider_called else "deterministic",
            "provider_called": provider_called,
            "fallback_used": True,
            "final_answer": business_answer["direct_answer"],
            "business_answer": business_answer,
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
    response = run_validated_llm_request(
        provider,
        request,
        schema_context={
            "user_question": state.get("user_question", ""),
            "execution_result": execution_result,
            "evidence_result": state.get("evidence_result") or {},
        },
    )
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
    provider_business_answer = content.get("business_answer") if isinstance(content.get("business_answer"), dict) else {}
    final_answer = str(provider_business_answer.get("direct_answer") or "")
    output = {
        "success": True,
        "source": "provider",
        "provider_called": True,
        "fallback_used": False,
        "final_answer": final_answer,
        "business_answer": provider_business_answer,
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


def run_insight_agent(
    state: dict[str, Any],
    provider: LLMProvider | None = None,
    answer_reviewer_provider: LLMProvider | None = None,
    final_answer_composer_provider: LLMProvider | None = None,
) -> dict[str, Any]:
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

    draft_business_answer = output.get("business_answer") if isinstance(output.get("business_answer"), dict) else {}
    answer_review = review_answer(
        user_question=state.get("user_question", ""),
        execution_result=execution_result or {},
        evidence_result=state.get("evidence_result") or {},
        draft_business_answer=draft_business_answer,
        profile_context={
            "business_context": state.get("business_context") or {},
            "metric_context": state.get("metric_context") or {},
            "workspace_context": state.get("workspace_context") or {},
        },
        provider=answer_reviewer_provider,
    )
    composition = compose_final_answer_result(
        user_question=state.get("user_question", ""),
        execution_result=execution_result or {},
        evidence_result=state.get("evidence_result") or {},
        draft_business_answer=draft_business_answer,
        reviewer_result=answer_review,
        provider=final_answer_composer_provider,
    )

    business_answer = build_business_answer(
        {
            "user_question": state.get("user_question", ""),
            "final_answer": composition["business_answer"].get("direct_answer") or output["final_answer"],
            "business_answer": composition["business_answer"],
            "execution_result": execution_result or {},
            "evidence_result": state.get("evidence_result") or {},
            "insight": output,
        }
    )
    canonical_final_answer = business_answer.get("direct_answer") or business_answer.get("headline") or output["final_answer"]
    output = {
        **output,
        "final_answer": canonical_final_answer,
        "business_answer": business_answer,
        "answer_review": answer_review,
        "answer_composition": {
            "source": composition.get("source", "deterministic"),
            "provider_called": bool(composition.get("provider_called", False)),
            "error": composition.get("error", ""),
        },
    }
    updated = {
        **state,
        "insight": output,
        "business_answer": business_answer,
        "final_answer": canonical_final_answer,
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
