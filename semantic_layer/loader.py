from __future__ import annotations

from pathlib import Path
from typing import Any

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
