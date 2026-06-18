from __future__ import annotations

from typing import Any

from tools.trace_logger import append_trace


def _format_row(columns: list[str], row: list[Any]) -> str:
    pairs = [f"{column}={value}" for column, value in zip(columns, row, strict=False)]
    return ", ".join(pairs)


def _answer_from_result(question: str, execution_result: dict[str, Any]) -> str:
    columns = execution_result.get("columns", [])
    rows = execution_result.get("rows", [])
    if not rows:
        return "查询已执行成功，但 execution_result 没有返回数据行。"

    lines = [f"基于 execution_result，问题「{question}」的结果如下："]
    for index, row in enumerate(rows[:5], start=1):
        lines.append(f"{index}. {_format_row(columns, row)}")
    if execution_result.get("truncated"):
        lines.append("结果已按 max_rows 截断。")
    return "\n".join(lines)


def run_insight_agent(state: dict[str, Any]) -> dict[str, Any]:
    execution_result = state.get("execution_result")
    if not execution_result:
        output = {
            "success": False,
            "final_answer": "缺少 execution_result，无法生成基于数据的回答。",
            "data_used": False,
            "error": "execution_result is required",
        }
        status = "error"
    elif not execution_result.get("success"):
        output = {
            "success": False,
            "final_answer": f"SQL 执行失败：{execution_result.get('error', 'unknown error')}",
            "data_used": False,
            "error": execution_result.get("error", "execution_result failed"),
        }
        status = "error"
    else:
        output = {
            "success": True,
            "final_answer": _answer_from_result(state.get("user_question", ""), execution_result),
            "data_used": True,
        }
        status = "success"

    updated = {
        **state,
        "insight": output,
        "final_answer": output["final_answer"],
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
        },
    )
