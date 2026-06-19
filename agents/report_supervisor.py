from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.chart_agent import run_chart_agent
from agents.context_retriever import run_context_retriever_agent
from agents.evidence_validator import run_evidence_validator_agent
from agents.metric_agent import run_metric_agent
from agents.report_planner import LLMProvider, run_report_planner_agent
from agents.schema_agent import run_schema_agent
from agents.sql_reviewer import run_sql_reviewer
from tools.report_tool import DEFAULT_REPORT_DIR, save_report
from tools.sql_executor import run_sql
from tools.trace_logger import append_trace, save_trace


WEEK_FILTER = """
o.order_date >= date((SELECT MAX(order_date) FROM orders), '-6 day')
AND o.order_date <= (SELECT MAX(order_date) FROM orders)
""".strip()

PREVIOUS_WEEK_FILTER = """
o.order_date >= date((SELECT MAX(order_date) FROM orders), '-13 day')
AND o.order_date < date((SELECT MAX(order_date) FROM orders), '-6 day')
""".strip()


def plan_business_review_sections(user_question: str) -> list[dict[str, Any]]:
    del user_question
    return [
        {
            "section_id": "weekly_gmv",
            "title": "本周 GMV",
            "question": "本周 GMV 是多少？",
            "sql": f"""
SELECT 'GMV' AS metric, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS value
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
WHERE o.status = 'paid'
  AND {WEEK_FILTER}
LIMIT 100
""".strip(),
            "expected_chart_type": "none",
        },
        {
            "section_id": "weekly_order_count",
            "title": "本周订单量",
            "question": "本周订单量是多少？",
            "sql": f"""
SELECT '订单量' AS metric, COUNT(*) AS value
FROM orders o
WHERE o.status = 'paid'
  AND {WEEK_FILTER}
LIMIT 100
""".strip(),
            "expected_chart_type": "none",
        },
        {
            "section_id": "weekly_aov",
            "title": "本周客单价",
            "question": "本周客单价是多少？",
            "sql": f"""
SELECT '客单价' AS metric,
       ROUND(SUM(oi.quantity * oi.unit_price) / COUNT(DISTINCT o.id), 2) AS value
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
WHERE o.status = 'paid'
  AND {WEEK_FILTER}
LIMIT 100
""".strip(),
            "expected_chart_type": "none",
        },
        {
            "section_id": "top_products",
            "title": "Top 商品",
            "question": "本周 GMV 最高的 Top 5 商品是什么？",
            "sql": f"""
SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE o.status = 'paid'
  AND {WEEK_FILTER}
GROUP BY p.product_name
ORDER BY gmv DESC
LIMIT 5
""".strip(),
            "expected_chart_type": "bar",
        },
        {
            "section_id": "top_categories",
            "title": "Top 品类",
            "question": "本周 GMV 最高的 Top 5 品类是什么？",
            "sql": f"""
SELECT c.category_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
JOIN categories c ON p.category_id = c.id
WHERE o.status = 'paid'
  AND {WEEK_FILTER}
GROUP BY c.category_name
ORDER BY gmv DESC
LIMIT 5
""".strip(),
            "expected_chart_type": "bar",
        },
        {
            "section_id": "declining_categories",
            "title": "销售下降品类",
            "question": "本周较上周 GMV 下降最多的品类是什么？",
            "sql": f"""
SELECT c.category_name,
       ROUND(SUM(CASE WHEN {WEEK_FILTER} THEN oi.quantity * oi.unit_price ELSE 0 END), 2) AS this_week_gmv,
       ROUND(SUM(CASE WHEN {PREVIOUS_WEEK_FILTER} THEN oi.quantity * oi.unit_price ELSE 0 END), 2) AS previous_week_gmv,
       ROUND(
           SUM(CASE WHEN {WEEK_FILTER} THEN oi.quantity * oi.unit_price ELSE 0 END)
           - SUM(CASE WHEN {PREVIOUS_WEEK_FILTER} THEN oi.quantity * oi.unit_price ELSE 0 END),
           2
       ) AS gmv_change
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
JOIN categories c ON p.category_id = c.id
WHERE o.status = 'paid'
  AND o.order_date >= date((SELECT MAX(order_date) FROM orders), '-13 day')
  AND o.order_date <= (SELECT MAX(order_date) FROM orders)
GROUP BY c.category_name
ORDER BY gmv_change ASC
LIMIT 5
""".strip(),
            "expected_chart_type": "bar",
        },
        {
            "section_id": "next_week_recommendations",
            "title": "下周建议",
            "question": "基于本周经营数据生成下周建议。",
            "sql": f"""
SELECT '下周建议依据' AS metric, COUNT(*) AS paid_orders
FROM orders o
WHERE o.status = 'paid'
  AND {WEEK_FILTER}
LIMIT 100
""".strip(),
            "expected_chart_type": "none",
        },
    ]


def _execution_skipped(reason: str) -> dict[str, Any]:
    return {
        "success": False,
        "columns": [],
        "rows": [],
        "row_count": 0,
        "truncated": False,
        "error": reason,
        "execution_time_ms": 0,
    }


def _first_rows(execution_result: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    columns = execution_result.get("columns", [])
    rows = execution_result.get("rows", [])
    return [dict(zip(columns, row, strict=False)) for row in rows[:limit]]


def _claims_for_section(section: dict[str, Any], execution_result: dict[str, Any]) -> list[str]:
    if not execution_result.get("success"):
        return [f"{section['title']} 子任务执行失败，需要修复 SQL 或补充数据后进一步验证。"]

    rows = _first_rows(execution_result)
    if not rows:
        return [f"{section['title']} 暂无返回数据，需要进一步验证。"]

    section_id = section["section_id"]
    first = rows[0]
    if section_id in {"weekly_gmv", "weekly_order_count", "weekly_aov"}:
        return [f"{first.get('metric')} 为 {first.get('value')}"]
    if section_id == "top_products":
        return [f"{first.get('product_name')} 的 GMV 为 {first.get('gmv')}"]
    if section_id == "top_categories":
        return [f"{first.get('category_name')} 的 GMV 为 {first.get('gmv')}"]
    if section_id == "declining_categories":
        return [f"{first.get('category_name')} 的 GMV 变化为 {first.get('gmv_change')}"]
    if section_id == "next_week_recommendations":
        return [
            f"{first.get('metric')} paid_orders 为 {first.get('paid_orders')}",
            "可能需要下周继续复查 GMV、订单量和下降品类。",
        ]
    return [f"{section['title']} 返回 {execution_result.get('row_count', 0)} 行数据"]


def _chart_spec(section: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
    if section.get("expected_chart_type") == "none":
        return None
    execution_result = state.get("execution_result", {})
    columns = execution_result.get("columns") or []
    if len(columns) < 2 or not execution_result.get("rows"):
        return None
    return {
        "chart_type": section.get("expected_chart_type", "bar"),
        "x": columns[0],
        "y": columns[-1],
        "title": section["section_id"],
        "run_id": f"{state.get('run_id', 'run_unknown')}_{section['section_id']}",
    }


def _run_section(
    state: dict[str, Any],
    section: dict[str, Any],
    chart_dir: str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    task_state = {
        **state,
        "user_question": section["question"],
        "generated_sql": section["sql"],
        "chart_paths": [],
    }

    task_state = run_metric_agent(task_state)
    task_state = run_sql_reviewer(task_state)
    review_result = task_state.get("review_result", {})
    sql = task_state.get("generated_sql", section["sql"])

    if review_result.get("approved"):
        execution_result = run_sql(state["db_path"], sql)
        task_state = {
            **task_state,
            "execution_result": execution_result,
            "error_message": execution_result.get("error", ""),
        }
        trace_event = dict(execution_result.get("trace_event", {}))
        trace_event["node"] = "sql_executor_node"
        task_state = append_trace(task_state, trace_event)
    else:
        execution_result = _execution_skipped("SQL review rejected; execution skipped")
        task_state = {**task_state, "execution_result": execution_result}

    task_state["claims_to_validate"] = _claims_for_section(section, execution_result)
    task_state = run_evidence_validator_agent(task_state)

    chart_paths: list[str] = []
    chart_spec = _chart_spec(section, task_state)
    if chart_spec:
        task_state["chart_spec"] = chart_spec
        task_state = run_chart_agent(task_state, output_dir=chart_dir)
        chart_paths = task_state.get("chart_paths", [])

    status = "completed" if review_result.get("approved") and execution_result.get("success") else "failed"
    task = {
        "section_id": section["section_id"],
        "title": section["title"],
        "question": section["question"],
        "sql": sql,
        "review_result": review_result,
        "execution_result": execution_result,
        "claims_to_validate": task_state.get("claims_to_validate", []),
        "evidence_result": task_state.get("evidence_result", {}),
        "chart_paths": chart_paths,
        "status": status,
        "error": "" if status == "completed" else execution_result.get("error", "subtask failed"),
    }
    return task_state, task


def _format_table(execution_result: dict[str, Any]) -> str:
    columns = execution_result.get("columns") or []
    rows = execution_result.get("rows") or []
    if not rows:
        return "No rows returned."
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows[:5]:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def _format_findings(tasks: list[dict[str, Any]], field: str) -> str:
    lines = []
    for task in tasks:
        for item in task.get("evidence_result", {}).get(field, []):
            if isinstance(item, dict):
                lines.append(f"- [{task['title']}] {item.get('claim', '')}")
            else:
                lines.append(f"- [{task['title']}] {item}")
    return "\n".join(lines) if lines else "- None"


def _build_weekly_report_content(state: dict[str, Any]) -> str:
    tasks = state.get("report_sub_tasks", [])
    failed_tasks = [task for task in tasks if task.get("status") != "completed"]
    chart_paths = [path for task in tasks for path in task.get("chart_paths", [])]

    lines = [
        "# 本周电商经营分析周报",
        "",
        "## 1. 核心结论",
        f"- 已完成 {len(tasks) - len(failed_tasks)} 个数据子任务，失败 {len(failed_tasks)} 个。",
        "- 本报告仅将 Evidence Validator 判定为数据支持的内容写入确定性结论。",
        "",
        "## 2. 核心指标",
    ]
    for task in tasks:
        if task["section_id"] in {"weekly_gmv", "weekly_order_count", "weekly_aov"}:
            lines.extend([f"### {task['title']}", _format_table(task["execution_result"]), ""])

    section_headers = {
        "top_products": "## 3. Top 商品",
        "top_categories": "## 4. Top 品类",
        "declining_categories": "## 5. 销售下降品类",
        "next_week_recommendations": "## 9. 下周建议",
    }
    for section_id, header in section_headers.items():
        task = next((item for item in tasks if item["section_id"] == section_id), None)
        if not task:
            continue
        lines.extend([header, _format_table(task["execution_result"]), ""])

    lines.extend(
        [
            "## 6. 渠道表现",
            "- 当前 P0/P1 ecommerce baseline 没有渠道字段，本模块保留为后续数据扩展项。",
            "",
            "## 7. 数据支持结论",
            _format_findings(tasks, "data_supported_findings"),
            "",
            "## 8. 需要进一步验证的假设",
            _format_findings(tasks, "hypotheses"),
            "",
            "## 10. Trace 与 SQL 记录",
            f"- Trace Path: {state.get('trace_path', '')}",
            "",
            "### Chart Paths",
        ]
    )
    lines.extend([f"- {path}" for path in chart_paths] or ["- None"])
    lines.append("")

    for task in tasks:
        lines.extend(
            [
                f"### {task['section_id']} - {task['title']}",
                f"- Status: {task['status']}",
                f"- Execution Evidence: success={task['execution_result'].get('success')} row_count={task['execution_result'].get('row_count', 0)}",
                f"- Chart Paths: {', '.join(task.get('chart_paths', [])) if task.get('chart_paths') else 'None'}",
                "",
                "```sql",
                task["sql"],
                "```",
                "",
            ]
        )
        if task.get("error"):
            lines.extend([f"- Error: {task['error']}", ""])

    return "\n".join(lines)


def run_report_supervisor_agent(
    state: dict[str, Any],
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    chart_dir: str | Path | None = None,
    llm_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    chart_output_dir = chart_dir or Path(__file__).resolve().parents[1] / "reports" / "charts"
    planned_state = run_report_planner_agent(state, llm_provider) if llm_provider else state
    if planned_state.get("status") == "report_plan_needs_clarification":
        return planned_state
    sections = planned_state.get("report_sections") or plan_business_review_sections(state.get("user_question", ""))

    current = {
        **planned_state,
        "task_type": "business_review_report",
        "report_type": "weekly_business_report",
        "report_sections": sections,
        "report_sub_tasks": [],
    }
    current = append_trace(
        current,
        {
            "node": "report_supervisor_agent",
            "tool_name": "",
            "tool_input_summary": current.get("user_question", ""),
            "tool_output_summary": f"planned {len(sections)} report sections",
            "status": "success",
            "latency_ms": 0,
        },
    )

    current = run_schema_agent(current, current["db_path"])
    current = run_context_retriever_agent(current)

    tasks = []
    for section in sections:
        task_state, task = _run_section(current, section, chart_output_dir)
        current["trace"] = task_state.get("trace", current.get("trace", []))
        tasks.append(task)

    failed_count = sum(1 for task in tasks if task["status"] != "completed")
    current = {
        **current,
        "report_sub_tasks": tasks,
        "status": (
            "business_review_report_completed_with_subtask_errors"
            if failed_count
            else "business_review_report_completed"
        ),
    }

    expected_trace_path = Path(current.get("trace_dir", "logs/traces")) / f"{current['run_id']}.json"
    current["trace_path"] = str(expected_trace_path)
    report_content = _build_weekly_report_content(current)
    report_result = save_report(f"{current['run_id']}_weekly_business", report_content, output_dir=report_dir)
    current = {
        **current,
        "weekly_report_result": report_result,
        "weekly_report_path": report_result.get("report_path", "") if report_result.get("success") else "",
    }
    trace_event = dict(report_result.get("trace_event", {}))
    trace_event["node"] = "report_agent"
    current = append_trace(current, trace_event)

    trace_result = save_trace(
        current["run_id"],
        current.get("trace", []),
        trace_dir=current.get("trace_dir", "logs/traces"),
        session_id=current.get("session_id"),
        user_question=current.get("user_question"),
        status=current.get("status", "unknown"),
    )
    current = {
        **current,
        "trace_save_result": trace_result,
        "trace_path": trace_result.get("trace_path", str(expected_trace_path)),
    }
    return current
