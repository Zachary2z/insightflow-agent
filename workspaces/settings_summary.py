from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_ops.deepseek_provider import load_deepseek_config
from llm_ops.runtime_provider import (
    product_live_mode_enabled,
    provider_claim_typing_enabled,
    provider_clarification_router_enabled,
    provider_insight_drafting_enabled,
    provider_question_understanding_enabled,
    provider_sql_candidate_enabled,
    provider_sql_planning_enabled,
    provider_visualization_agent_enabled,
)
from semantic_layer.loader import load_workspace_semantic_layer
from workspaces.store import WorkspaceStore


def _source_status(sources: list[dict[str, Any]]) -> str:
    return "ready" if sources else "empty"


def _read_json(path: str | Path) -> dict[str, Any] | None:
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_file():
        return None
    return json.loads(candidate.read_text(encoding="utf-8"))


def _profile_status(profile_path: str | Path) -> dict[str, Any]:
    profile = _read_json(profile_path)
    if profile is None:
        return {"status": "missing", "tables": [], "table_count": 0, "column_count": 0, "row_count": 0}

    tables = profile.get("tables", [])
    column_count = sum(len(table.get("columns", [])) for table in tables if isinstance(table, dict))
    row_count = sum(int(table.get("row_count") or 0) for table in tables if isinstance(table, dict))
    return {
        "status": "ready",
        "tables": tables,
        "table_count": len(tables),
        "column_count": column_count,
        "row_count": row_count,
    }


def _semantic_layer_status(semantic_layer_path: str | Path) -> dict[str, Any]:
    loaded = load_workspace_semantic_layer(semantic_layer_path)
    if not loaded.get("success"):
        return {
            "status": "missing",
            "metrics": [],
            "dimensions": [],
            "entities": [],
            "time_fields": [],
        }
    semantic_layer = loaded["semantic_layer"]

    return {
        "status": "ready",
        "metrics": semantic_layer.get("metrics", []),
        "dimensions": semantic_layer.get("dimensions", []),
        "entities": semantic_layer.get("entities", []),
        "time_fields": semantic_layer.get("time_fields", []),
    }


def _model_mode_status() -> dict[str, Any]:
    env_path = Path(".env")
    config = load_deepseek_config(env_path=env_path, require_api_key=False)
    live_mode = product_live_mode_enabled(env_path=env_path)
    provider_features = {
        "question_understanding": provider_question_understanding_enabled(env_path=env_path),
        "clarification": provider_clarification_router_enabled(env_path=env_path),
        "sql_planning": provider_sql_planning_enabled(env_path=env_path),
        "sql_candidate": provider_sql_candidate_enabled(env_path=env_path),
        "insight_drafting": provider_insight_drafting_enabled(env_path=env_path),
        "claim_typing": provider_claim_typing_enabled(env_path=env_path),
        "visualization": provider_visualization_agent_enabled(env_path=env_path),
    }
    enabled_count = sum(1 for enabled in provider_features.values() if enabled)
    if live_mode:
        status_label = "Product/live mode is on"
    elif enabled_count:
        status_label = "Provider-assisted features are partially enabled"
    else:
        status_label = "Product/live mode is off"

    return {
        "product_live_mode": live_mode,
        "status_label": status_label,
        "provider": {
            "name": "DeepSeek",
            "model": config.model,
            "api_key_present": bool(config.api_key),
        },
        "provider_features": provider_features,
        "coverage": {
            "enabled": enabled_count,
            "total": len(provider_features),
        },
    }


def build_workspace_settings(store: WorkspaceStore, workspace: dict[str, Any]) -> dict[str, Any]:
    sources = workspace.get("sources", [])
    return {
        "workspace_id": workspace["workspace_id"],
        "workspace_name": workspace.get("name", ""),
        "data_sources": {
            "status": _source_status(sources),
            "sources": sources,
            "source_count": len(sources),
            "imported_table_count": sum(len(source.get("imported_tables", [])) for source in sources),
        },
        "profile": _profile_status(workspace["profile_path"]),
        "semantic_layer": _semantic_layer_status(workspace["semantic_layer_path"]),
        "model_mode": _model_mode_status(),
        "safety": {
            "sql_review": "enabled",
            "sensitive_field_blocking": "enabled",
            "trace_available": "enabled",
            "technical_details_policy": "collapsed_by_default",
        },
    }
