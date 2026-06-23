from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def _read_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return json.loads(file_path.read_text(encoding="utf-8"))


def _read_yaml(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}


def _compact_column(column: dict[str, Any]) -> dict[str, Any]:
    compact = {
        "name": column.get("name", ""),
        "sql_type": column.get("sql_type", ""),
        "roles": {
            key: value
            for key, value in dict(column.get("role_candidates", {})).items()
            if value
        },
        "examples": list(column.get("examples", []))[:5],
    }
    if column.get("value_range"):
        compact["value_range"] = column["value_range"]
    if column.get("numeric_stats"):
        compact["numeric_stats"] = column["numeric_stats"]
    return compact


def build_workspace_context_summary(
    *,
    profile_path: str | Path | None,
    semantic_layer_path: str | Path | None,
) -> dict[str, Any]:
    profile = _read_json(profile_path)
    semantic_layer = _read_yaml(semantic_layer_path)
    tables = [
        {
            "table_name": table.get("table_name", ""),
            "row_count": table.get("row_count", 0),
            "columns": [_compact_column(column) for column in table.get("columns", [])],
        }
        for table in profile.get("tables", [])
    ]
    return {
        "workspace_data_source_selected": bool(tables),
        "guidance": [
            "Use the current workspace analysis database; do not ask the user to name a data source, table, or fields when this context is present.",
            "For dataset-relative recent windows such as 数据的最近 90 天, use the maximum available time value in the workspace data rather than DATE('now').",
        ],
        "tables": tables,
        "semantic_metrics": list(semantic_layer.get("metrics", []))[:20],
        "semantic_dimensions": list(semantic_layer.get("dimensions", []))[:30],
        "semantic_time_fields": list(semantic_layer.get("time_fields", []))[:20],
    }
