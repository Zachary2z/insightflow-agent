from __future__ import annotations

import re
from time import perf_counter
from typing import Any

from semantic_layer.loader import load_semantic_layer


def _normalize(text: str) -> str:
    return re.sub(r"[\s_\-]+", "", str(text).lower())


def _candidates(item_id: str, definition: dict[str, Any]) -> list[str]:
    aliases = definition.get("aliases", [])
    name = definition.get("name", "")
    return [item_id, name, *aliases]


def _matches(question: str, item_id: str, definition: dict[str, Any]) -> bool:
    normalized_question = _normalize(question)
    return any(_normalize(candidate) in normalized_question for candidate in _candidates(item_id, definition) if candidate)


def _matched_ids(question: str, definitions: dict[str, Any]) -> list[str]:
    return [
        item_id
        for item_id, definition in definitions.items()
        if isinstance(definition, dict) and _matches(question, item_id, definition)
    ]


def _ordered_unique(items: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _infer_entities(
    matched_metrics: list[str],
    matched_dimensions: list[str],
    explicit_entities: list[str],
    metrics: dict[str, Any],
    dimensions: dict[str, Any],
) -> list[str]:
    inferred: list[str] = list(explicit_entities)
    for metric_id in matched_metrics:
        inferred.extend(metrics.get(metric_id, {}).get("entities", []))
    for dimension_id in matched_dimensions:
        inferred.extend(dimensions.get(dimension_id, {}).get("entities", []))
    return _ordered_unique(inferred)


def _path_matches(
    path: dict[str, Any],
    matched_metrics: list[str],
    matched_dimensions: list[str],
    matched_entities: list[str],
) -> bool:
    path_metrics = set(path.get("metrics", []))
    path_dimensions = set(path.get("dimensions", []))
    path_entities = set(path.get("entities", []))
    metric_match = bool(path_metrics & set(matched_metrics)) if matched_metrics else False
    dimension_match = bool(path_dimensions & set(matched_dimensions)) if matched_dimensions else False
    entity_match = bool(path_entities & set(matched_entities)) if matched_entities else False
    return metric_match and (dimension_match or entity_match)


def _matched_join_paths(
    question: str,
    join_paths: dict[str, Any],
    matched_metrics: list[str],
    matched_dimensions: list[str],
    matched_entities: list[str],
) -> list[str]:
    explicit = _matched_ids(question, join_paths)
    inferred = [
        path_id
        for path_id, path in join_paths.items()
        if isinstance(path, dict) and _path_matches(path, matched_metrics, matched_dimensions, matched_entities)
    ]
    return _ordered_unique([*explicit, *inferred])


def retrieve_semantic_context(question: str) -> dict[str, Any]:
    started_at = perf_counter()
    loaded = load_semantic_layer()
    latency_ms = int((perf_counter() - started_at) * 1000)
    if not loaded["success"]:
        return {
            "success": False,
            "question": question,
            "matched_metrics": [],
            "matched_dimensions": [],
            "matched_entities": [],
            "matched_join_paths": [],
            "metrics": {},
            "dimensions": {},
            "entities": {},
            "join_paths": {},
            "error": loaded.get("error", "Failed to load semantic layer."),
            "latency_ms": latency_ms,
        }

    metrics = loaded["metrics"]
    dimensions = loaded["dimensions"]
    entities = loaded["entities"]
    join_paths = loaded["join_paths"]
    matched_metrics = _matched_ids(question, metrics)
    matched_dimensions = _matched_ids(question, dimensions)
    explicit_entities = _matched_ids(question, entities)
    matched_entities = _infer_entities(matched_metrics, matched_dimensions, explicit_entities, metrics, dimensions)
    matched_join_paths = _matched_join_paths(question, join_paths, matched_metrics, matched_dimensions, matched_entities)

    return {
        "success": True,
        "question": question,
        "matched_metrics": matched_metrics,
        "matched_dimensions": matched_dimensions,
        "matched_entities": matched_entities,
        "matched_join_paths": matched_join_paths,
        "metrics": {metric_id: metrics[metric_id] for metric_id in matched_metrics},
        "dimensions": {dimension_id: dimensions[dimension_id] for dimension_id in matched_dimensions},
        "entities": {entity_id: entities[entity_id] for entity_id in matched_entities if entity_id in entities},
        "join_paths": {path_id: join_paths[path_id] for path_id in matched_join_paths},
        "latency_ms": latency_ms,
    }
