from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any


DEFAULT_TRACE_DIR = Path(__file__).resolve().parents[1] / "logs" / "traces"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe_run_id(run_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in run_id.strip())
    return safe or "run_unknown"


def _summary(value: Any) -> str:
    if value is None:
        return ""
    return str(value)[:200]


def _normalized_event(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "run_id": event.get("run_id") or state.get("run_id") or "run_unknown",
        "session_id": event.get("session_id") or state.get("session_id") or "session_unknown",
        "node": event.get("node") or state.get("current_node") or "",
        "tool_name": event.get("tool_name") or "",
        "tool_input_summary": _summary(event.get("tool_input_summary")),
        "tool_output_summary": _summary(event.get("tool_output_summary")),
        "status": event.get("status") or "unknown",
        "latency_ms": int(event.get("latency_ms") or 0),
        "error_type": event.get("error_type"),
        "retry_count": int(event.get("retry_count") or state.get("retry_count") or 0),
        "timestamp": event.get("timestamp") or _now_iso(),
    }

    for key, value in event.items():
        if key not in normalized:
            normalized[key] = value

    return normalized


def append_trace(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(state)
    trace = list(updated.get("trace") or [])
    trace.append(_normalized_event(updated, event))
    updated["trace"] = trace
    return updated


def _trace_event(run_id: str, status: str, latency_ms: int, summary: str, error: str | None = None) -> dict[str, Any]:
    event = {
        "tool_name": "save_trace",
        "tool_input_summary": f"run_id={run_id}",
        "tool_output_summary": summary,
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "trace_save_error"
        event["error"] = error
    return event


def save_trace(
    run_id: str,
    trace: list[dict[str, Any]],
    trace_dir: str | Path = DEFAULT_TRACE_DIR,
    session_id: str | None = None,
    user_question: str | None = None,
    status: str = "success",
    question_thread: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started_at = perf_counter()
    safe_run_id = _safe_run_id(run_id)
    path = Path(trace_dir) / f"{safe_run_id}.json"
    payload = {
        "run_id": run_id,
        "session_id": session_id,
        "user_question": user_question,
        "status": status,
        "question_thread": question_thread or {},
        "event_count": len(trace),
        "trace": trace,
        "saved_at": _now_iso(),
    }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        latency_ms = int((perf_counter() - started_at) * 1000)
        error = f"Failed to save trace: {exc}"
        return {
            "success": False,
            "run_id": run_id,
            "trace_path": "",
            "event_count": len(trace),
            "error": error,
            "trace_event": _trace_event(run_id, "error", latency_ms, error, error),
        }

    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": True,
        "run_id": run_id,
        "trace_path": str(path),
        "event_count": len(trace),
        "trace_event": _trace_event(run_id, "success", latency_ms, f"{len(trace)} events saved"),
    }
