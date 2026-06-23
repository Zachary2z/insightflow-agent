from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from workspaces.store import WorkspaceStore


def _role_candidates(name: str, sql_type: str, distinct_count: int, row_count: int) -> dict[str, bool]:
    lower_name = name.lower()
    lower_type = sql_type.lower()
    is_numeric = any(token in lower_type for token in ("int", "real", "num", "float", "double", "decimal"))
    is_time = any(token in lower_name for token in ("date", "time", "created", "month", "day"))
    is_id = lower_name.endswith("_id") or lower_name == "id" or "id" in lower_name
    is_measure = is_numeric and any(
        token in lower_name for token in ("amount", "revenue", "sales", "gmv", "price", "cost", "count", "qty", "quantity")
    )
    is_dimension = distinct_count <= max(20, row_count // 2) and not is_measure and not is_time
    return {"id": is_id, "time": is_time, "measure": is_measure, "dimension": is_dimension}


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
    quoted = f'"{column_name}"'
    null_count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE {quoted} IS NULL').fetchone()[0]
    distinct_count = conn.execute(f'SELECT COUNT(DISTINCT {quoted}) FROM "{table_name}"').fetchone()[0]
    examples = [
        row[0]
        for row in conn.execute(
            f'SELECT DISTINCT {quoted} FROM "{table_name}" WHERE {quoted} IS NOT NULL LIMIT 5'
        ).fetchall()
    ]
    role_candidates = _role_candidates(column_name, sql_type, distinct_count, row_count)
    profile = {
        "name": column_name,
        "original_name": column_name,
        "sql_type": sql_type,
        "null_count": null_count,
        "null_rate": null_count / row_count if row_count else 0.0,
        "distinct_count": distinct_count,
        "examples": examples,
        "role_candidates": role_candidates,
    }
    if any(token in sql_type.lower() for token in ("int", "real", "num", "float", "double", "decimal")):
        stats = conn.execute(
            f'SELECT MIN({quoted}), MAX({quoted}), AVG({quoted}) FROM "{table_name}" WHERE {quoted} IS NOT NULL'
        ).fetchone()
        profile["numeric_stats"] = {"min": stats[0], "max": stats[1], "mean": stats[2]}
    if role_candidates.get("time"):
        bounds = conn.execute(
            f'SELECT MIN({quoted}), MAX({quoted}) FROM "{table_name}" WHERE {quoted} IS NOT NULL'
        ).fetchone()
        profile["value_range"] = {"min": bounds[0], "max": bounds[1]}
    return profile


def profile_workspace_database(store: WorkspaceStore, workspace_id: str) -> dict[str, Any]:
    workspace = store.get_workspace(workspace_id)
    db_path = workspace["analysis_db_path"]
    tables = []
    with sqlite3.connect(db_path) as conn:
        for table_name in _table_names(conn):
            row_count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
            columns = [
                _column_profile(conn, table_name, column, row_count)
                for column in conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
            ]
            tables.append({"table_name": table_name, "row_count": row_count, "columns": columns})
    profile = {"workspace_id": workspace_id, "database_path": db_path, "tables": tables}
    Path(workspace["profile_path"]).write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return profile
