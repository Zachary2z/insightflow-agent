from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from tools.trace_logger import DEFAULT_TRACE_DIR


def _round_average(total: int, count: int) -> float:
    if count == 0:
        return 0.0
    return round(total / count, 2)


def _summary(count: int, total: int) -> dict[str, Any]:
    return {"count": count, "total": total, "average": _round_average(total, count)}


def _load_trace_files(trace_dir: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    path = Path(trace_dir)
    if not path.exists():
        return [], []

    traces: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for trace_path in sorted(path.glob("*.json")):
        try:
            traces.append(json.loads(trace_path.read_text(encoding="utf-8")))
        except Exception as exc:
            errors.append({"trace_path": str(trace_path), "error": str(exc)})
    return traces, errors


def _status_counts(traces: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(trace.get("status", "unknown")) for trace in traces))


def _event_iter(traces: list[dict[str, Any]]):
    for trace in traces:
        for event in trace.get("trace", []):
            yield event


def _node_latency(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    totals: dict[str, int] = defaultdict(int)
    counts: dict[str, int] = defaultdict(int)
    for event in events:
        node = str(event.get("node", "")).strip()
        if not node:
            continue
        totals[node] += int(event.get("latency_ms") or 0)
        counts[node] += 1
    return {node: _summary(counts[node], totals[node]) for node in sorted(counts)}


def _tool_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter()
    for event in events:
        tool_name = str(event.get("tool_name", "")).strip()
        if tool_name:
            counts[tool_name] += 1
    return dict(sorted(counts.items()))


def _sql_execution_latency(events: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [
        int(event.get("latency_ms") or 0)
        for event in events
        if event.get("tool_name") == "run_sql" or event.get("node") == "sql_executor_node"
    ]
    return _summary(len(latencies), sum(latencies))


def _sql_fix_count(events: list[dict[str, Any]]) -> int:
    return sum(1 for event in events if event.get("node") == "error_fix_agent")


def _trace_failure_distribution(traces: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, int]:
    distribution = Counter()
    for trace in traces:
        status = str(trace.get("status", "unknown"))
        if status == "completed":
            distribution["none"] += 1
        elif status == "failed":
            error_type = next((event.get("error_type") for event in events if event.get("error_type")), None)
            distribution[str(error_type or "workflow_failed")] += 1
        else:
            distribution[status] += 1
    return dict(distribution)


def _eval_metrics(eval_summary: dict[str, Any] | None) -> dict[str, Any]:
    if not eval_summary:
        return {
            "total_cases": 0,
            "passed_cases": 0,
            "failed_cases": 0,
            "pass_rate": 0.0,
        }
    return {
        "total_cases": int(eval_summary.get("total_cases") or 0),
        "passed_cases": int(eval_summary.get("passed_cases") or 0),
        "failed_cases": int(eval_summary.get("failed_cases") or 0),
        "pass_rate": float(eval_summary.get("pass_rate") or 0.0),
    }


def build_trace_dashboard(
    trace_dir: str | Path = DEFAULT_TRACE_DIR,
    eval_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    traces, load_errors = _load_trace_files(trace_dir)
    events = list(_event_iter(traces))
    failure_distribution = eval_summary.get("failure_type_distribution") if eval_summary else None

    return {
        "success": True,
        "trace_dir": str(trace_dir),
        "trace_count": len(traces),
        "event_count": len(events),
        "run_status_counts": _status_counts(traces),
        "agent_node_latency_ms": _node_latency(events),
        "tool_call_counts": _tool_counts(events),
        "sql_execution_latency_ms": _sql_execution_latency(events),
        "sql_fix_count": _sql_fix_count(events),
        "failure_type_distribution": dict(failure_distribution or _trace_failure_distribution(traces, events)),
        "eval_metrics": _eval_metrics(eval_summary),
        "load_errors": load_errors,
    }
