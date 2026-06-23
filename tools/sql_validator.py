from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter
from typing import Any

import sqlglot
from sqlglot import exp
import sqlparse


DANGEROUS_KEYWORDS = {
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
}

SENSITIVE_FIELDS = {"phone", "email", "address", "id_card", "payment_info"}
DEFAULT_LIMIT = 100


def _base_checks() -> dict[str, bool]:
    return {
        "select_only": False,
        "no_dangerous_keywords": True,
        "single_statement": False,
        "tables_exist": True,
        "columns_exist": True,
        "has_limit": False,
        "limit_added": False,
        "sensitive_fields_blocked": True,
        "metric_formula_correct": True,
        "paid_filter_included": True,
        "sqlite_compatible": True,
    }


def _trace_event(sql: str, approved: bool, risk_level: str, latency_ms: int) -> dict[str, Any]:
    return {
        "tool_name": "validate_sql",
        "tool_input_summary": sql[:120],
        "tool_output_summary": f"approved={str(approved).lower()} risk={risk_level}",
        "status": "success" if approved else "error",
        "latency_ms": latency_ms,
    }


def _schema_maps(schema: dict[str, Any]) -> tuple[dict[str, set[str]], set[str]]:
    table_columns: dict[str, set[str]] = {}
    for table in schema.get("tables", []):
        table_name = table.get("table_name", "")
        columns = {column["name"].lower() for column in table.get("columns", [])}
        table_columns[table_name.lower()] = columns
    all_columns = {column for columns in table_columns.values() for column in columns}
    return table_columns, all_columns


def _contains_dangerous_keyword(sql: str) -> bool:
    tokens = {token.upper() for token in re.findall(r"\b[A-Za-z_]+\b", sql)}
    return any(keyword in tokens for keyword in DANGEROUS_KEYWORDS)


def _is_select_expression(expression: exp.Expression | None) -> bool:
    return isinstance(expression, exp.Select)


def _table_aliases(expression: exp.Expression) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for table in expression.find_all(exp.Table):
        table_name = table.name.lower()
        aliases[table_name] = table_name
        if table.alias:
            aliases[table.alias.lower()] = table_name
    return aliases


def _select_aliases(expression: exp.Expression) -> set[str]:
    if not isinstance(expression, exp.Select):
        return set()
    return {projection.alias.lower() for projection in expression.expressions if projection.alias}


def _validate_tables(
    expression: exp.Expression,
    table_columns: dict[str, set[str]],
    issues: list[str],
    checks: dict[str, bool],
) -> None:
    for table in expression.find_all(exp.Table):
        table_name = table.name.lower()
        if table_name not in table_columns:
            checks["tables_exist"] = False
            issues.append(f"Unknown table: {table.name}")


def _validate_columns(
    expression: exp.Expression,
    table_columns: dict[str, set[str]],
    all_columns: set[str],
    issues: list[str],
    checks: dict[str, bool],
) -> None:
    aliases = _table_aliases(expression)
    projection_aliases = _select_aliases(expression)

    for column in expression.find_all(exp.Column):
        column_name = column.name.lower()
        table_ref = column.table.lower() if column.table else ""

        if column_name in SENSITIVE_FIELDS:
            checks["sensitive_fields_blocked"] = False
            issues.append(f"Sensitive field access is not allowed: {column.name}")

        if table_ref:
            table_name = aliases.get(table_ref)
            if not table_name:
                checks["columns_exist"] = False
                issues.append(f"Unknown table alias: {column.table}")
                continue
            if column_name not in table_columns.get(table_name, set()):
                checks["columns_exist"] = False
                issues.append(f"Unknown column: {column.table}.{column.name}")
            continue

        if column_name in projection_aliases:
            continue

        if column_name not in all_columns:
            checks["columns_exist"] = False
            issues.append(f"Unknown column: {column.name}")


def _has_limit(expression: exp.Expression | None) -> bool:
    return bool(expression and expression.args.get("limit"))


def _normalize_sql(sql: str) -> str:
    return sqlparse.format(sql.strip().rstrip(";"), strip_comments=True).strip()


def _metric_context_requires_gmv(metric_context: dict[str, Any] | None) -> bool:
    if not metric_context or not metric_context.get("success"):
        return False
    matched = set(metric_context.get("matched_metrics", []))
    return bool({"gmv", "category_gmv"} & matched)


def _compact(sql: str) -> str:
    return re.sub(r"\s+", "", sql.lower())


def _validate_metric_context(
    sql: str,
    metric_context: dict[str, Any] | None,
    issues: list[str],
    checks: dict[str, bool],
) -> None:
    if not _metric_context_requires_gmv(metric_context):
        return

    compact_sql = _compact(sql)
    formula_patterns = [
        "order_items.quantity*order_items.unit_price",
        "oi.quantity*oi.unit_price",
        "quantity*unit_price",
    ]
    if not any(pattern in compact_sql for pattern in formula_patterns):
        checks["metric_formula_correct"] = False
        issues.append("GMV formula must use order_items.quantity * order_items.unit_price")

    if "status='paid'" not in compact_sql:
        checks["paid_filter_included"] = False
        issues.append("GMV queries must include orders.status = 'paid'")


def _validate_sqlite_compatibility(sql: str, issues: list[str], checks: dict[str, bool]) -> None:
    if re.search(r"\bINTERVAL\s+['\"]?\d+['\"]?\s+\w+", sql, flags=re.IGNORECASE):
        checks["sqlite_compatible"] = False
        issues.append("SQLite does not support INTERVAL date arithmetic; use date() or julianday() syntax")


def validate_sql(
    sql: str,
    schema: dict[str, Any],
    metric_context: dict[str, Any] | None = None,
    default_limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    started_at = perf_counter()
    issues: list[str] = []
    checks = _base_checks()
    normalized_sql = _normalize_sql(sql)

    statements = [statement for statement in sqlparse.split(sql) if statement.strip()]
    checks["single_statement"] = len(statements) == 1
    if not checks["single_statement"]:
        issues.append("Multiple SQL statements are not allowed")

    if _contains_dangerous_keyword(sql):
        checks["no_dangerous_keywords"] = False
        issues.append("SQL contains a dangerous keyword")

    _validate_sqlite_compatibility(sql, issues, checks)

    expression = None
    try:
        expression = sqlglot.parse_one(sql, read="sqlite")
        checks["select_only"] = _is_select_expression(expression)
    except Exception as exc:
        checks["select_only"] = False
        issues.append(f"SQL parse error: {exc}")

    if not checks["select_only"]:
        issues.append("Only SELECT queries are allowed")

    if expression is not None:
        table_columns, all_columns = _schema_maps(schema)
        _validate_tables(expression, table_columns, issues, checks)
        _validate_columns(expression, table_columns, all_columns, issues, checks)
        checks["has_limit"] = _has_limit(expression)
        if checks["select_only"] and not checks["has_limit"]:
            checks["has_limit"] = True
            checks["limit_added"] = True
            normalized_sql = f"{normalized_sql} LIMIT {default_limit}"
            issues.append(f"LIMIT missing; appended LIMIT {default_limit}")

    _validate_metric_context(normalized_sql, metric_context, issues, checks)

    blocking_checks = [
        "select_only",
        "no_dangerous_keywords",
        "single_statement",
        "tables_exist",
        "columns_exist",
        "sensitive_fields_blocked",
        "metric_formula_correct",
        "paid_filter_included",
        "sqlite_compatible",
    ]
    approved = all(checks[check] for check in blocking_checks)
    risk_level = "low" if approved else "high"
    latency_ms = int((perf_counter() - started_at) * 1000)

    return {
        "approved": approved,
        "risk_level": risk_level,
        "issues": issues,
        "checks": checks,
        "normalized_sql": normalized_sql,
        "trace_event": _trace_event(sql, approved, risk_level, latency_ms),
    }
