from __future__ import annotations

from collections import Counter
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
