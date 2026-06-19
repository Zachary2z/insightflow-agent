from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter
from typing import Any


DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "markdown"


def _safe_run_id(run_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", run_id.strip())
    normalized = normalized.strip("._-/")
    return normalized or "run_unknown"


def _trace_event(
    run_id: str,
    report_path: str,
    status: str,
    latency_ms: int,
    error: str | None = None,
) -> dict[str, Any]:
    summary = report_path if report_path else error or "report not saved"
    event = {
        "tool_name": "save_report",
        "tool_input_summary": f"run_id={run_id}",
        "tool_output_summary": summary[:200],
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "report_save_error"
        event["error"] = error
    return event


def _failure(started_at: float, run_id: str, error: str) -> dict[str, Any]:
    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": False,
        "run_id": run_id,
        "report_path": "",
        "error": error,
        "trace_event": _trace_event(run_id, "", "error", latency_ms, error),
    }


def save_report(
    run_id: str,
    report_content: str,
    output_dir: str | Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    started_at = perf_counter()
    if not str(report_content).strip():
        return _failure(started_at, run_id, "report_content is required")

    safe_run_id = _safe_run_id(run_id)
    report_path = Path(output_dir) / f"{safe_run_id}_report.md"

    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_content, encoding="utf-8")
    except Exception as exc:
        return _failure(started_at, run_id, str(exc))

    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": True,
        "run_id": run_id,
        "report_path": str(report_path),
        "trace_event": _trace_event(run_id, str(report_path), "success", latency_ms),
    }
