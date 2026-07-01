from __future__ import annotations

from pathlib import Path
from typing import Any

import json
import yaml


SEMANTIC_LAYER_DIR = Path(__file__).resolve().parent
DEFAULT_SEMANTIC_PATHS = {
    "metrics": SEMANTIC_LAYER_DIR / "metrics.yaml",
    "dimensions": SEMANTIC_LAYER_DIR / "dimensions.yaml",
    "entities": SEMANTIC_LAYER_DIR / "entities.yaml",
    "join_paths": SEMANTIC_LAYER_DIR / "join_paths.yaml",
}


def _load_yaml_mapping(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Semantic layer {label} file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Semantic layer {label} file must contain a mapping.")
    return {
        item_id: {"id": item_id, **definition} if isinstance(definition, dict) else definition
        for item_id, definition in data.items()
    }


def load_semantic_layer(paths: dict[str, str | Path] | None = None) -> dict[str, Any]:
    resolved = dict(DEFAULT_SEMANTIC_PATHS)
    if paths:
        for key, value in paths.items():
            resolved[key] = Path(value)

    try:
        metrics = _load_yaml_mapping(resolved["metrics"], "metrics")
        dimensions = _load_yaml_mapping(resolved["dimensions"], "dimensions")
        entities = _load_yaml_mapping(resolved["entities"], "entities")
        join_paths = _load_yaml_mapping(resolved["join_paths"], "join_paths")
    except Exception as exc:
        return {
            "success": False,
            "metrics": {},
            "dimensions": {},
            "entities": {},
            "join_paths": {},
            "error": str(exc),
        }

    return {
        "success": True,
        "metrics": metrics,
        "dimensions": dimensions,
        "entities": entities,
        "join_paths": join_paths,
        "metrics_path": str(resolved["metrics"]),
        "dimensions_path": str(resolved["dimensions"]),
        "entities_path": str(resolved["entities"]),
        "join_paths_path": str(resolved["join_paths"]),
    }


def load_workspace_semantic_layer(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return _workspace_semantic_error("Semantic layer path is empty.")
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return _workspace_semantic_error(f"Semantic layer file not found: {file_path}", path=file_path)

    try:
        data = _read_mapping_file(file_path)
    except Exception as exc:
        return _workspace_semantic_error(f"Failed to load semantic layer file: {exc}", path=file_path)

    return {
        "success": True,
        "semantic_layer": data,
        "semantic_layer_path": str(file_path),
        "metrics": data.get("metrics", []),
        "dimensions": data.get("dimensions", []),
        "entities": data.get("entities", []),
        "time_fields": data.get("time_fields", []),
        "tables": data.get("tables", []),
        "relationships": data.get("relationships", []),
        "metric_map": _index_items(data.get("metrics", [])),
        "dimension_map": _index_items(data.get("dimensions", [])),
        "entity_map": _index_items(data.get("entities", [])),
        "time_field_map": _index_items(data.get("time_fields", [])),
    }


def _read_mapping_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("Semantic layer file must contain a mapping.")
    return data


def _index_items(items: Any) -> dict[str, Any]:
    if not isinstance(items, list):
        return {}
    indexed: dict[str, Any] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("name") or item.get("id") or item.get("field") or "").strip()
        if key:
            indexed[key] = item
    return indexed


def _workspace_semantic_error(error: str, path: str | Path | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "success": False,
        "semantic_layer": {},
        "metrics": [],
        "dimensions": [],
        "entities": [],
        "time_fields": [],
        "tables": [],
        "relationships": [],
        "metric_map": {},
        "dimension_map": {},
        "entity_map": {},
        "time_field_map": {},
        "error": error,
    }
    if path:
        result["semantic_layer_path"] = str(path)
    return result
