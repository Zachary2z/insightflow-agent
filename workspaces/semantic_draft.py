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
    for table in profile.get("tables", []):
        table_name = table["table_name"]
        for column in table.get("columns", []):
            name = column["name"]
            roles = column.get("role_candidates", {})
            qualified = f"{table_name}.{name}"
            if roles.get("measure"):
                metrics.append(
                    {
                        "name": f"sum_{name}",
                        "label": f"Sum {name}",
                        "table": table_name,
                        "field": qualified,
                        "formula": f"SUM({qualified})",
                        "enabled": True,
                        "description": f"Auto-detected numeric measure from {qualified}.",
                    }
                )
            if roles.get("dimension"):
                dimensions.append(
                    {
                        "name": name,
                        "label": name.replace("_", " ").title(),
                        "table": table_name,
                        "field": qualified,
                        "enabled": True,
                        "description": f"Auto-detected categorical dimension from {qualified}.",
                    }
                )
            if roles.get("time"):
                time_fields.append(
                    {
                        "name": name,
                        "table": table_name,
                        "field": qualified,
                        "enabled": True,
                        "description": f"Auto-detected time field from {qualified}.",
                    }
                )
            if roles.get("id"):
                entities.append(
                    {
                        "name": name,
                        "table": table_name,
                        "field": qualified,
                        "enabled": True,
                        "description": f"Auto-detected identifier from {qualified}.",
                    }
                )
    semantic_layer = {
        "workspace_id": workspace_id,
        "metrics": metrics,
        "dimensions": dimensions,
        "time_fields": time_fields,
        "entities": entities,
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
