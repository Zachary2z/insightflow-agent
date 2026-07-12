from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from observability.trace_sink import (
    TraceDocument,
    TracePersistRequest,
    TraceSink,
    TraceSinkResult,
    default_trace_sink,
    local_result,
)
from observability.redaction import classify_error


DEFAULT_TRACE_DIR = Path(__file__).resolve().parents[1] / "logs" / "traces"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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
    sink: TraceSink | None = None,
) -> dict[str, Any]:
    document = TraceDocument(
        run_id=run_id,
        trace=tuple(trace),
        saved_at=_now_iso(),
        session_id=session_id,
        user_question=user_question,
        status=status,
        question_thread=question_thread or {},
    )
    selected_sink = sink or default_trace_sink(trace_dir)
    try:
        result = selected_sink.persist(TracePersistRequest(document=document))
    except Exception as exc:
        result = TraceSinkResult(
            sink_name=getattr(selected_sink, "name", "unknown"),
            success=False,
            latency_ms=0,
            event_count=len(trace),
            error_type=classify_error(exc) or "internal_error",
        )
    compatibility = local_result(result)
    if not compatibility.success:
        error = f"Failed to save trace ({compatibility.error_type or 'internal_error'})."
        return {
            "success": False,
            "run_id": run_id,
            "trace_path": "",
            "event_count": len(trace),
            "error": error,
            "trace_event": _trace_event(run_id, "error", compatibility.latency_ms, error, error),
        }
    return {
        "success": True,
        "run_id": run_id,
        "trace_path": compatibility.trace_path,
        "event_count": len(trace),
        "trace_event": _trace_event(run_id, "success", compatibility.latency_ms, f"{len(trace)} events saved"),
    }
