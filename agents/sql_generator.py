from __future__ import annotations

import re
from typing import Any

from semantic_layer.loader import load_workspace_semantic_layer
from tools.metric_tool import build_metric_registry
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


def _city_order_count_sql() -> dict[str, Any]:
    return {
        "sql": """
SELECT u.city, COUNT(*) AS order_count
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.status = 'paid'
GROUP BY u.city
ORDER BY order_count DESC
LIMIT 100
""".strip(),
        "tables": ["orders", "users"],
        "reason": "Aggregate paid order count by user city.",
    }


def _template_sql(template_id: str, variables: dict[str, Any]) -> dict[str, Any] | None:
    limit = int(variables.get("limit") or 5)
    if template_id == "top_products_gmv":
        return _top_product_gmv_sql(limit)
    if template_id == "top_categories_gmv":
        return _category_gmv_sql(limit)
    if template_id == "city_gmv_summary":
        return _city_gmv_sql()
    if template_id == "city_order_count_summary":
        return _city_order_count_sql()
    return None


def run_sql_generator(state: dict[str, Any]) -> dict[str, Any]:
    question = state.get("user_question", "")
    metric_context = state.get("metric_context", {})

    generic_generated = _generic_workspace_sql(state)
    if generic_generated:
        generated = generic_generated
    else:
        generated = _schema_backed_sql(state)

    if generated:
        output = {
            "success": True,
            **generated,
            "metrics": _metric_ids(metric_context) or ["gmv"],
        }
    else:
        output = {
            "success": False,
            "sql": "",
            "tables": [],
            "reason": "当前工作区的语义层或指标字段不足，无法安全生成数据查询；请先补充可分析的指标、维度或时间字段。",
            "metrics": _metric_ids(metric_context),
        }
        updated = {
            **state,
            "sql_generation": output,
            "generated_sql": "",
            "sql_reason": output["reason"],
            "selected_tables": [],
            "selected_metrics": output["metrics"],
            "status": "sql_generation_failed",
            "error_message": output["reason"],
        }
        return append_trace(
            updated,
            {
                "node": "sql_generator_agent",
                "tool_name": "",
                "tool_input_summary": question,
                "tool_output_summary": output["reason"],
                "status": "error",
                "latency_ms": 0,
            },
        )
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


def _schema_backed_sql(state: dict[str, Any]) -> dict[str, Any] | None:
    """Support low-level graph workflows only when the current schema confirms the tables."""

    if not _schema_table_names(state):
        return None

    planning = state.get("sql_planning") if isinstance(state.get("sql_planning"), dict) else {}
    template_id = str(planning.get("matched_template") or "")
    template = _template_sql(template_id, dict(planning.get("template_variables") or {}))
    if template and _schema_supports_tables(state, template["tables"]):
        return template

    question = str(state.get("user_question") or "")
    limit = _limit_from_question(question)
    candidates: list[dict[str, Any]] = []
    if _question_contains(question, "品类", "类别", "category"):
        candidates.append(_category_gmv_sql(limit))
    if _question_contains(question, "城市", "city"):
        if _question_contains(question, "订单数", "订单量", "订单总数", "order_count"):
            candidates.append(_city_order_count_sql())
        candidates.append(_city_gmv_sql())
    if _question_contains(question, "订单数", "订单量", "订单总数", "order_count"):
        candidates.append(_order_count_sql())
    candidates.append(_top_product_gmv_sql(limit))

    for candidate in candidates:
        if _schema_supports_tables(state, candidate["tables"]):
            return candidate
    return None


def _schema_table_names(state: dict[str, Any]) -> set[str]:
    schema = state.get("database_schema") if isinstance(state.get("database_schema"), dict) else {}
    names: set[str] = set()
    for table in schema.get("tables") or []:
        if isinstance(table, dict):
            name = str(table.get("table_name") or "").strip()
            if name:
                names.add(name)
    return names


def _schema_supports_tables(state: dict[str, Any], tables: list[str]) -> bool:
    available = _schema_table_names(state)
    return bool(available) and all(str(table) in available for table in tables)


def _generic_workspace_sql(state: dict[str, Any]) -> dict[str, Any] | None:
    semantic_layer_path = state.get("semantic_layer_path")
    if not semantic_layer_path:
        return None
    loaded = load_workspace_semantic_layer(semantic_layer_path)
    if not loaded.get("success"):
        return None
    semantic_layer = loaded.get("semantic_layer") or {}
    registry = state.get("metric_registry") if isinstance(state.get("metric_registry"), dict) else {}
    if not registry.get("metrics"):
        registry = build_metric_registry(semantic_layer)
    task = state.get("analysis_task") if isinstance(state.get("analysis_task"), dict) else {}
    calculation_type = str(task.get("calculation_type") or "").strip()
    question = str(state.get("user_question") or "")

    selected_metrics = _select_metrics(
        registry=registry,
        semantic_layer=semantic_layer,
        requested=[str(item) for item in task.get("metrics") or []],
        calculation_type=calculation_type,
        question=question,
    )
    dimension_hint = _select_dimension(
        semantic_layer=semantic_layer,
        requested=[str(item) for item in task.get("dimensions") or []],
        table_name="",
        question=question,
    )
    if dimension_hint and selected_metrics:
        dimension_table = _field_table(dimension_hint)
        same_table_metrics = [
            metric
            for metric in selected_metrics
            if not _metric_table(metric) or _metric_table(metric) == dimension_table
        ]
        if same_table_metrics:
            selected_metrics = same_table_metrics
        elif dimension_table:
            fallback_metric = _numeric_entity_metric(
                semantic_layer,
                dimension_table,
                requested=[str(item) for item in task.get("metrics") or []],
                question=question,
            )
            selected_metrics = [fallback_metric] if fallback_metric else []
    if not selected_metrics:
        if dimension_hint:
            fallback_metric = _numeric_entity_metric(
                semantic_layer,
                _field_table(dimension_hint),
                requested=[str(item) for item in task.get("metrics") or []],
                question=question,
            )
            selected_metrics = [fallback_metric] if fallback_metric else []
    if not selected_metrics:
        return None
    primary_metric = selected_metrics[0]
    table_name = _metric_table(primary_metric)
    if not table_name:
        return None
    dimension = dimension_hint if dimension_hint and _field_table(dimension_hint) == table_name else _select_dimension(
        semantic_layer=semantic_layer,
        requested=[str(item) for item in task.get("dimensions") or []],
        table_name=table_name,
        question=question,
    )
    if not dimension:
        return None

    selected_metrics = [
        metric
        for metric in selected_metrics
        if _metric_formula(metric) and (_metric_table(metric) == table_name or not _metric_table(metric))
    ]
    if not selected_metrics:
        return None

    dimension_label = _label(dimension) or _field_column(dimension)
    dimension_sql = _quote(_field_column(dimension))
    select_parts = [f"{dimension_sql} AS {_quote(dimension_label)}"]
    for metric in selected_metrics:
        label = _metric_label(metric)
        select_parts.append(f"{_metric_formula(metric)} AS {_quote(label)}")

    where_sql = _time_where_sql(
        semantic_layer=semantic_layer,
        table_name=table_name,
        time_range=task.get("time_range") if isinstance(task.get("time_range"), dict) else {},
    )
    order_label = _metric_label(_order_metric(selected_metrics, calculation_type=calculation_type, question=question))
    direction = "ASC" if _lower_is_better(order_label, calculation_type=calculation_type, question=question) else "DESC"
    sql = (
        f"SELECT {', '.join(select_parts)} FROM {_quote(table_name)}{where_sql} "
        f"GROUP BY {dimension_sql} ORDER BY {_quote(order_label)} {direction} LIMIT 20"
    )
    return {
        "sql": sql,
        "tables": [table_name],
        "reason": "Use workspace semantic-layer metrics and dimensions to calculate the requested evidence.",
    }


def _select_metrics(
    *,
    registry: dict[str, Any],
    semantic_layer: dict[str, Any],
    requested: list[str],
    calculation_type: str,
    question: str,
) -> list[dict[str, Any]]:
    metrics = [
        {**metric, "name": str(metric.get("name") or metric_id)}
        for metric_id, metric in (registry.get("metrics") or {}).items()
        if isinstance(metric, dict)
    ]
    requested_text = " ".join([*requested, question])
    if calculation_type == "investment_efficiency" or _contains_any(requested_text, ("roas", "roi", "投产比", "净投放回报")):
        ordered = [
            metric
            for label in ("收入", "销售额", "投放", "花费", "成本", "广告投入产出比", "净投放回报率", "ROAS")
            for metric in metrics
            if _matches(metric, (label,))
        ]
        return _dedupe_metrics(ordered)
    if calculation_type == "operational_efficiency":
        ordered = [
            metric
            for label in ("平均响应", "响应时长", "满意度", "工单数", "工单量")
            for metric in metrics
            if _matches(metric, (label,))
        ]
        return _dedupe_metrics(ordered)
    matched = [metric for metric in metrics if any(_matches(metric, (item,)) for item in requested)]
    if matched:
        return _dedupe_metrics(matched)
    semantic_metrics = [item for item in semantic_layer.get("metrics") or [] if isinstance(item, dict)]
    fallback = [
        {**metric, "name": str(metric.get("name") or "")}
        for metric in semantic_metrics
        if _matches(metric, ("收入", "销售额", "成交额", "GMV", "订单数", "工单数"))
    ]
    return _dedupe_metrics(fallback[:1])


def _select_dimension(
    *,
    semantic_layer: dict[str, Any],
    requested: list[str],
    table_name: str,
    question: str,
) -> dict[str, Any] | None:
    dimensions = [
        item
        for item in semantic_layer.get("dimensions") or []
        if isinstance(item, dict) and (not table_name or _field_table(item) == table_name)
    ]
    for label in [*requested, question]:
        match = next((dimension for dimension in dimensions if _matches(dimension, (label,))), None)
        if match:
            return match
    return dimensions[0] if dimensions else None


def _numeric_entity_metric(
    semantic_layer: dict[str, Any],
    table_name: str,
    *,
    requested: list[str],
    question: str,
) -> dict[str, Any] | None:
    candidates = [
        item
        for item in [
            *(semantic_layer.get("metrics") or []),
            *(semantic_layer.get("entities") or []),
        ]
        if isinstance(item, dict) and _field_table(item) == table_name
    ]
    amount_like = next(
        (
            item
            for item in candidates
            if _matches(item, ("amount", "金额", "paid", "销售", "收入", "成交"))
        ),
        None,
    )
    selected = amount_like or next((item for item in candidates if _matches(item, ("count", "数量", "数"))), None)
    if not selected:
        return None
    column = _field_column(selected)
    requested_text = " ".join([*requested, question])
    label = "销售额" if _contains_any(requested_text, ("销售", "收入", "贡献", "占比", "金额", "paid")) else _label(selected)
    return {
        "name": f"sum_{column}",
        "business_label": label or "业务指标",
        "field": f"{table_name}.{column}",
        "formula": f"SUM({_quote(table_name)}.{_quote(column)})",
        "unit": "currency" if _contains_any(label, ("销售", "收入", "金额")) else "number",
        "source_fields": [f"{table_name}.{column}"],
    }


def _order_metric(metrics: list[dict[str, Any]], *, calculation_type: str, question: str) -> dict[str, Any]:
    if calculation_type == "operational_efficiency" or "响应" in question:
        response = next((metric for metric in metrics if _matches(metric, ("响应", "时长"))), None)
        if response:
            return response
    return metrics[0]


def _time_where_sql(*, semantic_layer: dict[str, Any], table_name: str, time_range: dict[str, Any]) -> str:
    range_type = str(time_range.get("type") or "")
    value = time_range.get("value")
    if not range_type:
        return ""
    time_field = next(
        (
            item
            for item in semantic_layer.get("time_fields") or []
            if isinstance(item, dict) and _field_table(item) == table_name
        ),
        None,
    )
    if not time_field:
        return ""
    column = _quote(_field_column(time_field))
    date_value = _date_expression(column)
    table_ref = _quote(table_name)
    max_date = f"(SELECT MAX({date_value}) FROM {table_ref})"
    if range_type == "last_n_days" and value:
        condition = f"{date_value} >= date({max_date}, '-{int(value)} days')"
    elif range_type == "last_n_months" and value:
        condition = f"{date_value} >= date({max_date}, '-{int(value)} months')"
    elif range_type == "this_month":
        condition = f"strftime('%Y-%m', {date_value}) = strftime('%Y-%m', {max_date})"
    elif range_type == "this_week":
        condition = f"{date_value} >= date({max_date}, '-7 days')"
    else:
        return ""
    return f" WHERE {condition}"


def _date_expression(column_sql: str) -> str:
    return (
        f"CASE WHEN length({column_sql}) = 7 "
        f"THEN date({column_sql} || '-01') ELSE date({column_sql}) END"
    )


def _metric_table(metric: dict[str, Any]) -> str:
    source_fields = [str(item) for item in metric.get("source_fields") or [] if str(item).strip()]
    if source_fields:
        return source_fields[0].split(".", 1)[0]
    field = str(metric.get("field") or "")
    if "." in field:
        return field.split(".", 1)[0]
    formula = _metric_formula(metric)
    match = re.search(r'"([^"]+)"\s*\.', formula)
    return match.group(1) if match else str(metric.get("table") or "")


def _field_table(item: dict[str, Any]) -> str:
    field = str(item.get("field") or "")
    if "." in field:
        return field.split(".", 1)[0]
    return str(item.get("table") or "")


def _field_column(item: dict[str, Any]) -> str:
    field = str(item.get("field") or "")
    if "." in field:
        return field.split(".", 1)[1]
    return str(item.get("name") or field)


def _metric_formula(metric: dict[str, Any]) -> str:
    return str(metric.get("formula") or "").strip()


def _metric_label(metric: dict[str, Any]) -> str:
    return str(metric.get("business_label") or metric.get("label") or metric.get("name") or "业务指标")


def _label(item: dict[str, Any]) -> str:
    return str(item.get("business_label") or item.get("label") or item.get("name") or item.get("field") or "")


def _matches(item: dict[str, Any], tokens: tuple[str, ...]) -> bool:
    text = " ".join(
        str(value or "")
        for value in [
            item.get("name"),
            item.get("label"),
            item.get("business_label"),
            item.get("field"),
            item.get("table"),
            *(item.get("aliases") or []),
            *(item.get("meanings") or []),
            *(item.get("business_meaning_candidates") or []),
        ]
    )
    compact = _compact(text)
    expanded = [alias for token in tokens for alias in _token_aliases(str(token))]
    return any(_compact(token) in compact for token in expanded if str(token).strip())


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    compact = _compact(text)
    return any(_compact(token) in compact for token in tokens)


def _token_aliases(token: str) -> list[str]:
    compact = _compact(token)
    aliases = [token]
    if any(item in compact for item in ("品类", "类别", "category")):
        aliases.extend(["category", "category_name", "类别", "品类"])
    if any(item in compact for item in ("商品", "产品", "product")):
        aliases.extend(["product", "product_name", "商品", "产品"])
    if any(item in compact for item in ("门店", "店铺", "store")):
        aliases.extend(["store", "store_name", "门店"])
    if any(item in compact for item in ("团队", "客服组", "team")):
        aliases.extend(["team", "team_name", "团队"])
    if any(item in compact for item in ("渠道", "channel")):
        aliases.extend(["channel", "channel_name", "渠道"])
    if any(item in compact for item in ("销售", "收入", "成交", "金额", "gmv")):
        aliases.extend(["sales", "sales_amount", "revenue", "revenue_amount", "paid_amount", "amount", "销售额"])
    return aliases


def _lower_is_better(label: str, *, calculation_type: str, question: str) -> bool:
    text = _compact(f"{label} {calculation_type} {question}")
    return any(token in text for token in ("响应", "时长", "分钟", "duration", "minutes"))


def _dedupe_metrics(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen = set()
    for metric in metrics:
        key = str(metric.get("name") or metric.get("field") or metric.get("formula") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(metric)
    return deduped


def _compact(value: Any) -> str:
    return re.sub(r"[\s_\-（）()。,.，:：]+", "", str(value or "").lower())


def _quote(identifier: str) -> str:
    return '"' + str(identifier).replace('"', '""') + '"'
