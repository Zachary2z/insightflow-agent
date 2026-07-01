from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from workspaces.store import WorkspaceStore


def generate_semantic_layer_draft(
    store: WorkspaceStore,
    workspace_id: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    metrics = []
    dimensions = []
    time_fields = []
    entities = []
    field_roles: dict[str, str] = {}
    semantic_aliases: dict[str, list[str]] = {}
    tables = []
    for table in profile.get("tables", []):
        table_name = table["table_name"]
        tables.append(
            {
                "table_name": table_name,
                "row_count": table.get("row_count", 0),
                "columns": [column.get("name", "") for column in table.get("columns", [])],
            }
        )
        for column in table.get("columns", []):
            name = column["name"]
            roles = column.get("role_candidates", {})
            qualified = f"{table_name}.{name}"
            field_role = column.get("field_role") or _field_role_from_candidates(roles)
            field_roles[qualified] = field_role
            semantic_aliases[qualified] = _aliases_for_field(name)
            if field_role == "metric":
                metrics.extend(_metric_definitions(table_name, name, qualified, column))
            if field_role in {"dimension", "status"}:
                dimensions.append(
                    {
                        "name": name,
                        "label": _label_for_field(name),
                        "table": table_name,
                        "field": qualified,
                        "enabled": True,
                        "role": field_role,
                        "aliases": semantic_aliases[qualified],
                        "description": f"Auto-detected groupable {field_role} from {qualified}.",
                    }
                )
            if field_role == "time":
                time_fields.append(
                    {
                        "name": name,
                        "table": table_name,
                        "field": qualified,
                        "enabled": True,
                        "aliases": semantic_aliases[qualified],
                        "description": f"Auto-detected time field from {qualified}.",
                    }
                )
            if field_role == "id":
                entities.append(
                    {
                        "name": name,
                        "table": table_name,
                        "field": qualified,
                        "enabled": True,
                        "aliases": semantic_aliases[qualified],
                        "description": f"Auto-detected identifier from {qualified}.",
                    }
                )
    relationships = _relationship_candidates(profile)
    semantic_layer = {
        "workspace_id": workspace_id,
        "tables": tables,
        "metrics": metrics,
        "dimensions": dimensions,
        "time_fields": time_fields,
        "entities": entities,
        "field_roles": field_roles,
        "semantic_aliases": semantic_aliases,
        "relationships": relationships,
        "available_analysis_capabilities": {
            "metrics": [metric["field"] for metric in metrics],
            "groupable_dimensions": [dimension["field"] for dimension in dimensions],
            "time_fields": [field["field"] for field in time_fields],
            "relationships": [relationship["name"] for relationship in relationships],
        },
        "join_paths": [],
    }
    save_semantic_layer(store, workspace_id, semantic_layer)
    return semantic_layer


def save_semantic_layer(store: WorkspaceStore, workspace_id: str, semantic_layer: dict[str, Any]) -> dict[str, Any]:
    workspace = store.get_workspace(workspace_id)
    semantic_layer["workspace_id"] = workspace_id
    Path(workspace["semantic_layer_path"]).write_text(
        yaml.safe_dump(semantic_layer, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return {"success": True, "semantic_layer_path": workspace["semantic_layer_path"]}


def _field_role_from_candidates(roles: dict[str, Any]) -> str:
    for role in ("time", "metric", "measure", "status", "id", "dimension", "text"):
        if roles.get(role):
            return "metric" if role == "measure" else role
    return "dimension"


def _label_for_field(name: str) -> str:
    return str(name).replace("_", " ").strip().title() if str(name).isascii() else str(name)


def _aliases_for_field(name: str) -> list[str]:
    text = str(name)
    aliases = [text]
    spaced = text.replace("_", " ").strip()
    if spaced and spaced != text:
        aliases.append(spaced)
    compact = text.replace("_", "").strip()
    if compact and compact not in aliases:
        aliases.append(compact)
    return list(dict.fromkeys(alias for alias in aliases if alias))


def _metric_definitions(table_name: str, name: str, qualified: str, column: dict[str, Any]) -> list[dict[str, Any]]:
    meanings = set(column.get("business_meaning_candidates", []))
    aggregations = set(column.get("suitable_aggregations", [])) or {"sum", "avg", "count"}
    if "rating_like" in meanings:
        selected_aggregations = ["avg"]
    elif "sum" in aggregations:
        selected_aggregations = ["sum"]
    elif "avg" in aggregations:
        selected_aggregations = ["avg"]
    else:
        selected_aggregations = ["count"]

    definitions = []
    for aggregation in selected_aggregations:
        metric_name = f"{aggregation}_{name}"
        definitions.append(
            {
                "name": metric_name,
                "label": f"{aggregation.upper()} {_label_for_field(name)}",
                "table": table_name,
                "field": qualified,
                "formula": f"{aggregation.upper()}({qualified})",
                "aggregation": aggregation,
                "enabled": True,
                "business_meaning_candidates": list(meanings),
                "aliases": _aliases_for_field(name) + _aliases_for_field(metric_name),
                "description": f"Auto-detected {aggregation} metric from {qualified}.",
            }
        )
    return definitions


def _normalized_join_key(name: str) -> str:
    text = str(name).lower().replace("_", "").replace("-", "").replace(" ", "")
    for suffix in ("id", "编号", "编码"):
        if text.endswith(suffix):
            return text[: -len(suffix)] or text
    return text


def _relationship_candidates(profile: dict[str, Any]) -> list[dict[str, Any]]:
    id_fields: list[dict[str, str]] = []
    for table in profile.get("tables", []):
        table_name = table.get("table_name", "")
        for column in table.get("columns", []):
            roles = column.get("role_candidates", {})
            if column.get("field_role") == "id" or roles.get("id"):
                name = column.get("name", "")
                id_fields.append(
                    {
                        "table": table_name,
                        "column": name,
                        "field": f"{table_name}.{name}",
                        "join_key": _normalized_join_key(name),
                    }
                )

    relationships = []
    seen: set[tuple[str, str]] = set()
    for left_index, left in enumerate(id_fields):
        for right in id_fields[left_index + 1 :]:
            if left["table"] == right["table"] or left["join_key"] != right["join_key"]:
                continue
            key = tuple(sorted((left["field"], right["field"])))
            if key in seen:
                continue
            seen.add(key)
            relationships.append(
                {
                    "name": f"{left['table']}_{right['table']}_{left['join_key']}",
                    "left_table": left["table"],
                    "left_column": left["column"],
                    "left_field": left["field"],
                    "right_table": right["table"],
                    "right_column": right["column"],
                    "right_field": right["field"],
                    "confidence": "candidate",
                    "reason": "Columns share an identifier-like name across tables.",
                }
            )
    return relationships
