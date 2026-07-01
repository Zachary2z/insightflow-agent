from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from workspaces.store import WorkspaceStore


def _compact(value: str) -> str:
    return re.sub(r"[\s_\-]+", "", str(value).lower())


def _quote_identifier(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _contains_any(value: str, tokens: tuple[str, ...]) -> bool:
    compact = _compact(value)
    return any(_compact(token) in compact for token in tokens)


def _is_numeric_sql_type(sql_type: str) -> bool:
    lower_type = sql_type.lower()
    return any(token in lower_type for token in ("int", "real", "num", "float", "double", "decimal"))


def _looks_like_date_value(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(
        re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", text)
        or re.match(r"^\d{4}[-/]\d{1,2}$", text)
        or re.match(r"^\d{8}$", text)
    )


_TIME_TOKENS = ("date", "time", "created", "updated", "month", "day", "日期", "时间", "月份", "年月", "创建")
_ID_TOKENS = ("id", "编号", "编码", "主键")
_STATUS_TOKENS = ("status", "state", "stage", "状态", "阶段")
_REVENUE_TOKENS = ("revenue", "sales", "gmv", "income", "turnover", "营业额", "营收", "收入", "销售额", "成交额")
_COST_TOKENS = ("cost", "spend", "expense", "fee", "budget", "成本", "花费", "费用", "支出", "投放")
_AMOUNT_TOKENS = ("amount", "price", "value", "revenue", "sales", "gmv", "金额", "额", "价格", "单价", "营业额")
_COUNT_TOKENS = (
    "count",
    "qty",
    "quantity",
    "number",
    "num",
    "tickets",
    "stock",
    "inventory",
    "数量",
    "次数",
    "件数",
    "单量",
    "库存",
    "客诉",
)
_RATING_TOKENS = ("rating", "score", "stars", "nps", "评分", "满意度", "星级", "得分")
_TEXT_TOKENS = ("note", "comment", "description", "remark", "备注", "描述", "说明", "内容")


def _business_meanings(name: str, *, is_time: bool, is_status: bool) -> list[str]:
    meanings: list[str] = []
    if is_time or _contains_any(name, _TIME_TOKENS):
        meanings.append("date_like")
    if _contains_any(name, _REVENUE_TOKENS):
        meanings.append("revenue_like")
    if _contains_any(name, _COST_TOKENS):
        meanings.append("cost_like")
    if _contains_any(name, _AMOUNT_TOKENS) or any(item in meanings for item in ("revenue_like", "cost_like")):
        meanings.append("amount_like")
    if _contains_any(name, _COUNT_TOKENS):
        meanings.append("count_like")
    if _contains_any(name, _RATING_TOKENS):
        meanings.append("rating_like")
    if is_status or _contains_any(name, _STATUS_TOKENS):
        meanings.append("status")
    return list(dict.fromkeys(meanings))


def _inferred_type(name: str, sql_type: str, examples: list[Any]) -> str:
    if _contains_any(name, _TIME_TOKENS) or any(_looks_like_date_value(value) for value in examples):
        return "time"
    if _is_numeric_sql_type(sql_type):
        return "number"
    return "text"


def _role_candidates(
    name: str,
    sql_type: str,
    distinct_count: int,
    row_count: int,
    examples: list[Any],
) -> dict[str, bool]:
    inferred_type = _inferred_type(name, sql_type, examples)
    is_numeric = inferred_type == "number"
    is_time = inferred_type == "time"
    compact_name = _compact(name)
    is_id = compact_name == "id" or compact_name.endswith("id") or _contains_any(name, _ID_TOKENS)
    is_status = _contains_any(name, _STATUS_TOKENS)
    is_text = (not is_numeric and not is_time) and (
        _contains_any(name, _TEXT_TOKENS) or distinct_count > max(20, row_count // 2)
    )
    is_metric = is_numeric and not is_id
    is_dimension = (
        not is_time
        and not is_metric
        and not is_id
        and not is_text
        and distinct_count <= max(20, row_count // 2)
    )
    if is_status:
        is_dimension = True
        is_text = False
    return {
        "id": is_id,
        "time": is_time,
        "measure": is_metric,
        "metric": is_metric,
        "dimension": is_dimension,
        "status": is_status,
        "text": is_text,
    }


def _field_role(roles: dict[str, bool]) -> str:
    for role in ("time", "metric", "status", "id", "dimension", "text"):
        if roles.get(role):
            return role
    return "dimension"


def _suitable_aggregations(field_role: str, meanings: list[str]) -> list[str]:
    if field_role != "metric":
        return ["count"]
    if "rating_like" in meanings:
        return ["avg", "count", "min", "max"]
    return ["sum", "avg", "count", "min", "max"]


def _table_names(conn: sqlite3.Connection) -> list[str]:
    return [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]


def _column_profile(conn: sqlite3.Connection, table_name: str, column: tuple, row_count: int) -> dict[str, Any]:
    column_name = column[1]
    sql_type = column[2] or ""
    quoted_table = _quote_identifier(table_name)
    quoted = _quote_identifier(column_name)
    null_count = conn.execute(f"SELECT COUNT(*) FROM {quoted_table} WHERE {quoted} IS NULL").fetchone()[0]
    distinct_count = conn.execute(f"SELECT COUNT(DISTINCT {quoted}) FROM {quoted_table}").fetchone()[0]
    examples = [
        row[0]
        for row in conn.execute(
            f"SELECT DISTINCT {quoted} FROM {quoted_table} WHERE {quoted} IS NOT NULL LIMIT 5"
        ).fetchall()
    ]
    inferred_type = _inferred_type(column_name, sql_type, examples)
    role_candidates = _role_candidates(column_name, sql_type, distinct_count, row_count, examples)
    field_role = _field_role(role_candidates)
    business_meanings = _business_meanings(
        column_name,
        is_time=field_role == "time",
        is_status=field_role == "status",
    )
    profile = {
        "name": column_name,
        "original_name": column_name,
        "original_type": sql_type,
        "sql_type": sql_type,
        "inferred_type": inferred_type,
        "field_role": field_role,
        "business_meaning_candidates": business_meanings,
        "suitable_group_by": field_role in {"dimension", "status"},
        "suitable_aggregations": _suitable_aggregations(field_role, business_meanings),
        "null_count": null_count,
        "null_rate": null_count / row_count if row_count else 0.0,
        "distinct_count": distinct_count,
        "examples": examples,
        "role_candidates": role_candidates,
    }
    if inferred_type == "number":
        stats = conn.execute(
            f"SELECT MIN({quoted}), MAX({quoted}), AVG({quoted}) FROM {quoted_table} WHERE {quoted} IS NOT NULL"
        ).fetchone()
        profile["numeric_stats"] = {"min": stats[0], "max": stats[1], "mean": stats[2]}
    if field_role == "time":
        bounds = conn.execute(
            f"SELECT MIN({quoted}), MAX({quoted}) FROM {quoted_table} WHERE {quoted} IS NOT NULL"
        ).fetchone()
        profile["value_range"] = {"min": bounds[0], "max": bounds[1]}
    return profile


def profile_workspace_database(store: WorkspaceStore, workspace_id: str) -> dict[str, Any]:
    workspace = store.get_workspace(workspace_id)
    db_path = workspace["analysis_db_path"]
    tables = []
    with sqlite3.connect(db_path) as conn:
        for table_name in _table_names(conn):
            quoted_table = _quote_identifier(table_name)
            row_count = conn.execute(f"SELECT COUNT(*) FROM {quoted_table}").fetchone()[0]
            columns = [
                _column_profile(conn, table_name, column, row_count)
                for column in conn.execute(f"PRAGMA table_info({_quote_identifier(table_name)})").fetchall()
            ]
            tables.append({"table_name": table_name, "row_count": row_count, "columns": columns})
    profile = {"workspace_id": workspace_id, "database_path": db_path, "tables": tables}
    Path(workspace["profile_path"]).write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return profile
