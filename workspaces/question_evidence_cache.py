from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from workspaces.analysis_contracts import AnalysisTask


def with_question_evidence_cache_identity(state: dict[str, Any]) -> dict[str, Any]:
    normalized_task = _normalized_task(state)
    keyed = dict(state)
    keyed["_question_evidence_cache_normalized_task"] = normalized_task
    keyed["_question_evidence_cache_key"] = _cache_key_for(
        workspace_id=str(state.get("workspace_id") or ""),
        data_version=int(state.get("data_version") or 0),
        semantic_layer_fingerprint=_semantic_layer_fingerprint(state),
        normalized_task=normalized_task,
    )
    return keyed


def load_question_evidence_cache(state: dict[str, Any]) -> dict[str, Any] | None:
    cache_path = _cache_path(state)
    if cache_path is None or not cache_path.exists() or state.get("initial_sql"):
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("cache_key") != _cache_key(state):
        return None
    if not _is_successful_cached_evidence(payload):
        return None
    return payload


def save_question_evidence_cache(state: dict[str, Any]) -> None:
    if state.get("initial_sql") or not _is_successful_cached_evidence(state):
        return
    cache_path = _cache_path(state)
    if cache_path is None:
        return
    payload = {
        "cache_key": _cache_key(state),
        "workspace_id": str(state.get("workspace_id") or ""),
        "data_version": int(state.get("data_version") or 0),
        "semantic_layer_fingerprint": _semantic_layer_fingerprint(state),
        "normalized_task": _normalized_task(state),
        "question_evidence_pack": dict(state.get("question_evidence_pack") or {}),
        "execution_result": dict(state.get("execution_result") or {}),
        "generated_sql": str(state.get("generated_sql") or ""),
        "review_result": dict(state.get("review_result") or {}),
        "metric_context": dict(state.get("metric_context") or {}),
        "selected_metrics": list(state.get("selected_metrics") or []),
        "workbench_tool_calls": list(state.get("workbench_tool_calls") or []),
    }
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except OSError:
        return


def _cache_path(state: dict[str, Any]) -> Path | None:
    workspace_root = str(state.get("workspace_root") or "").strip()
    workspace_id = str(state.get("workspace_id") or "").strip()
    data_version = int(state.get("data_version") or 0)
    if not workspace_root or not workspace_id or data_version <= 0:
        return None
    return Path(workspace_root) / ".question_evidence_cache" / f"{_cache_key(state)}.json"


def _cache_key(state: dict[str, Any]) -> str:
    existing = str(state.get("_question_evidence_cache_key") or "").strip()
    if existing:
        return existing
    return _cache_key_for(
        workspace_id=str(state.get("workspace_id") or ""),
        data_version=int(state.get("data_version") or 0),
        semantic_layer_fingerprint=_semantic_layer_fingerprint(state),
        normalized_task=_normalized_task(state),
    )


def _cache_key_for(
    *,
    workspace_id: str,
    data_version: int,
    semantic_layer_fingerprint: str,
    normalized_task: dict[str, Any],
) -> str:
    payload = {
        "workspace_id": workspace_id,
        "data_version": data_version,
        "semantic_layer_fingerprint": semantic_layer_fingerprint,
        "task": normalized_task,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalized_task(state: dict[str, Any]) -> dict[str, Any]:
    existing = state.get("_question_evidence_cache_normalized_task")
    if isinstance(existing, dict):
        return dict(existing)
    task = _task(state)
    question_text = state.get("original_question") or state.get("user_question") or state.get("resolved_question")
    return {
        "resolved_question": _compact(question_text or task.resolved_question),
        "metrics": _normalized_labels(task.metrics),
        "dimensions": sorted(_compact(item) for item in task.dimensions if _compact(item)),
        "time_range": _normalized_time_range(task.time_range, question=question_text),
        "filters": sorted(_compact(item) for item in task.filters if _compact(item)),
    }


def _task(state: dict[str, Any]) -> AnalysisTask:
    for key in ("analysis_task_contract", "analysis_task"):
        value = state.get(key)
        if isinstance(value, AnalysisTask):
            return value
        if isinstance(value, dict):
            return AnalysisTask.from_dict(value)
    return AnalysisTask(resolved_question=str(state.get("resolved_question") or state.get("user_question") or ""))


def _semantic_layer_fingerprint(state: dict[str, Any]) -> str:
    path_text = str(state.get("semantic_layer_path") or "").strip()
    if not path_text:
        return ""
    path = Path(path_text)
    try:
        data = path.read_bytes()
    except OSError:
        return "missing"
    return hashlib.sha256(data).hexdigest()


def _is_successful_cached_evidence(payload: dict[str, Any]) -> bool:
    review = payload.get("review_result") if isinstance(payload.get("review_result"), dict) else {}
    execution = payload.get("execution_result") if isinstance(payload.get("execution_result"), dict) else {}
    pack = payload.get("question_evidence_pack") if isinstance(payload.get("question_evidence_pack"), dict) else {}
    return bool(
        review.get("approved") is True
        and execution.get("success") is True
        and pack
        and payload.get("generated_sql")
    )


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _normalized_time_range(value: Any, *, question: Any = "") -> Any:
    question_days = _relative_days_from_text(question)
    if question_days:
        return {"type": "relative", "unit": "day", "value": question_days}
    if not isinstance(value, dict):
        return _stable(value)
    range_type = str(value.get("type") or "").lower()
    unit = str(value.get("unit") or "").lower()
    amount = value.get("value")
    if amount is None:
        amount = _first_int(value.get("window")) or _first_int(value.get("raw_text"))
    if range_type in {"last", "last_n_days", "relative"} and amount:
        normalized_unit = "day" if unit in {"", "day", "days"} else unit
        return {"type": "relative", "unit": normalized_unit, "value": int(amount)}
    start = value.get("start") or value.get("start_date")
    end = value.get("end") or value.get("end_date")
    if start or end:
        return {"type": "absolute", "start": str(start or ""), "end": str(end or "")}
    raw_text = _compact(value.get("raw_text"))
    if raw_text:
        return {"raw_text": raw_text}
    return _stable(value)


def _first_int(value: Any) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else None


def _relative_days_from_text(value: Any) -> int | None:
    text = str(value or "")
    match = re.search(r"(?:最近|近)\s*(\d+)\s*天", text)
    return int(match.group(1)) if match else None


def _normalized_labels(values: list[str]) -> list[str]:
    labels = [_compact(item) for item in values if _compact(item)]
    cjk_labels = [item for item in labels if _contains_cjk(item)]
    if cjk_labels:
        return sorted(dict.fromkeys(cjk_labels))
    return sorted(dict.fromkeys(labels))


def _contains_cjk(value: Any) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(value or ""))


def _compact(value: Any) -> str:
    return "".join(str(value or "").split())


__all__ = [
    "load_question_evidence_cache",
    "save_question_evidence_cache",
    "with_question_evidence_cache_identity",
]
