from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any


def _signature(intent: dict[str, Any]) -> str:
    metric = str(intent.get("metric", "")).strip()
    dimension = str(intent.get("dimension", "")).strip()
    operation = str(intent.get("operation", "")).strip()
    return f"{metric}:{dimension}:{operation}"


def _template_id_from_signature(signature: str) -> str:
    return signature.replace(":", "_")


def summarize_template_mining_feedback(
    events: list[dict[str, Any]],
    min_success_count: int = 3,
) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    for event in events:
        if event.get("strategy") != "llm_candidate" or not event.get("success"):
            continue
        signature = _signature(event.get("intent", {}))
        if signature.count(":") == 2 and "::" not in signature and not signature.startswith(":"):
            counter[signature] += 1

    candidates = [
        {
            "intent_signature": signature,
            "success_count": count,
            "recommended_template_id": _template_id_from_signature(signature),
            "reason": "Repeated successful llm_candidate pattern can be promoted to a deterministic template.",
        }
        for signature, count in sorted(counter.items())
        if count >= min_success_count
    ]
    return {"success": True, "candidates": candidates}


def extract_template_mining_events_from_trace(trace_payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = []
    for event in trace_payload.get("trace", []):
        if not isinstance(event, dict):
            continue
        if "template_mining_event" not in event:
            continue
        mining_event = event.get("template_mining_event", {})
        if not isinstance(mining_event, dict):
            continue
        candidate = {
            "strategy": mining_event.get("strategy", ""),
            "success": bool(mining_event.get("success", False)),
            "intent": dict(mining_event.get("intent", {})),
            "user_question": mining_event.get("user_question") or trace_payload.get("user_question", ""),
            "accepted": bool(mining_event.get("accepted", False)),
            "provider_called": bool(mining_event.get("provider_called", False)),
        }
        events.append(candidate)
    return events


def mine_template_candidates_from_trace_files(
    trace_paths: list[str | Path],
    min_success_count: int = 3,
) -> dict[str, Any]:
    events = []
    load_errors = []
    for trace_path in trace_paths:
        path = Path(trace_path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            load_errors.append({"trace_path": str(path), "error": str(exc)})
            continue
        events.extend(extract_template_mining_events_from_trace(payload))

    summary = summarize_template_mining_feedback(events, min_success_count=min_success_count)
    questions_by_signature: dict[str, list[str]] = {}
    for event in events:
        if event.get("strategy") != "llm_candidate" or not event.get("success"):
            continue
        signature = _signature(event.get("intent", {}))
        question = str(event.get("user_question", "")).strip()
        if question and question not in questions_by_signature.setdefault(signature, []):
            questions_by_signature[signature].append(question)

    candidates = []
    for candidate in summary["candidates"]:
        signature = candidate["intent_signature"]
        candidates.append(
            {
                **candidate,
                "sample_questions": questions_by_signature.get(signature, [])[:3],
                "auto_apply": False,
            }
        )

    return {
        "success": not load_errors,
        "source": "workflow_trace",
        "events_scanned": len(events),
        "candidates": candidates,
        "load_errors": load_errors,
    }
