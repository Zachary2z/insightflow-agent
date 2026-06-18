from __future__ import annotations

from typing import Any

from tools.trace_logger import append_trace


def _question_contains(question: str, *keywords: str) -> bool:
    normalized = question.lower().replace(" ", "")
    return any(keyword.lower().replace(" ", "") in normalized for keyword in keywords)


def _limit_from_question(question: str, default: int = 5) -> int:
    for candidate in (20, 10, 5, 3, 1):
        if str(candidate) in question:
            return candidate
    return default


def _metric_ids(metric_context: dict[str, Any]) -> list[str]:
    if not metric_context.get("success"):
        return []
    return list(metric_context.get("matched_metrics", []))


def _top_product_gmv_sql(limit: int) -> dict[str, Any]:
    return {
        "sql": f"""
SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE o.status = 'paid'
GROUP BY p.product_name
ORDER BY gmv DESC
LIMIT {limit}
""".strip(),
        "tables": ["orders", "order_items", "products"],
        "reason": "Use paid orders and order_items.quantity * order_items.unit_price to calculate product GMV.",
    }


def _category_gmv_sql(limit: int) -> dict[str, Any]:
    return {
        "sql": f"""
SELECT c.category_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
JOIN categories c ON p.category_id = c.id
WHERE o.status = 'paid'
GROUP BY c.category_name
ORDER BY gmv DESC
LIMIT {limit}
""".strip(),
        "tables": ["orders", "order_items", "products", "categories"],
        "reason": "Aggregate paid GMV by category through products.category_id.",
    }


def _city_gmv_sql() -> dict[str, Any]:
    return {
        "sql": """
SELECT u.city, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv
FROM orders o
JOIN users u ON o.user_id = u.id
JOIN order_items oi ON o.id = oi.order_id
WHERE o.status = 'paid'
GROUP BY u.city
ORDER BY gmv DESC
LIMIT 100
""".strip(),
        "tables": ["orders", "users", "order_items"],
        "reason": "Aggregate paid GMV by user city.",
    }


def _order_count_sql() -> dict[str, Any]:
    return {
        "sql": """
SELECT COUNT(*) AS order_count
FROM orders
WHERE status = 'paid'
LIMIT 100
""".strip(),
        "tables": ["orders"],
        "reason": "Count paid orders only.",
    }


def run_sql_generator(state: dict[str, Any]) -> dict[str, Any]:
    question = state.get("user_question", "")
    metric_context = state.get("metric_context", {})
    limit = _limit_from_question(question)

    if _question_contains(question, "品类", "类别", "category"):
        generated = _category_gmv_sql(limit)
    elif _question_contains(question, "城市", "city"):
        generated = _city_gmv_sql()
    elif _question_contains(question, "订单数", "订单量", "order_count"):
        generated = _order_count_sql()
    else:
        generated = _top_product_gmv_sql(limit)

    output = {
        "success": True,
        **generated,
        "metrics": _metric_ids(metric_context) or ["gmv"],
    }
    updated = {
        **state,
        "sql_generation": output,
        "generated_sql": output["sql"],
        "sql_reason": output["reason"],
        "selected_tables": output["tables"],
        "selected_metrics": output["metrics"],
    }
    return append_trace(
        updated,
        {
            "node": "sql_generator_agent",
            "tool_name": "",
            "tool_input_summary": question,
            "tool_output_summary": output["sql"][:200],
            "status": "success",
            "latency_ms": 0,
        },
    )
