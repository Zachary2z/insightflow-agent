from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol, Sequence, runtime_checkable

from observability.events import build_observability_event
from observability.logging import EventEmitter, emit_observability_event
from observability.redaction import classify_error
from observability.trace_paths import has_symlink_component, safe_trace_run_id


@dataclass(frozen=True, slots=True)
class TraceDocument:
    run_id: str
    trace: tuple[dict[str, Any], ...]
    saved_at: str
    session_id: str | None = None
    user_question: str | None = None
    status: str = "success"
    question_thread: dict[str, Any] = field(default_factory=dict)

    @property
    def event_count(self) -> int:
        return len(self.trace)

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "user_question": self.user_question,
            "status": self.status,
            "question_thread": self.question_thread,
            "event_count": self.event_count,
            "trace": list(self.trace),
            "saved_at": self.saved_at,
        }


@dataclass(frozen=True, slots=True)
class TracePersistRequest:
    document: TraceDocument
    prior_results: tuple["TraceSinkResult", ...] = ()


@dataclass(frozen=True, slots=True)
class TraceSinkResult:
    sink_name: str
    success: bool
    latency_ms: int
    event_count: int
    trace_path: str = ""
    error_type: str | None = None
    results: tuple["TraceSinkResult", ...] = ()


@runtime_checkable
class TraceSink(Protocol):
    name: str

    def persist(self, request: TracePersistRequest) -> TraceSinkResult: ...


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((perf_counter() - started_at) * 1000))


class LocalJsonTraceSink:
    name = "local_json"

    def __init__(self, trace_root: str | Path):
        self._trace_root = Path(trace_root)

    def persist(self, request: TracePersistRequest) -> TraceSinkResult:
        started_at = perf_counter()
        event_count = request.document.event_count
        temporary_path: Path | None = None
        try:
            root = self._validated_root()
            final_path = root / f"{safe_trace_run_id(request.document.run_id)}.json"
            if final_path.is_symlink() or final_path.parent.resolve() != root:
                raise ValueError("unsafe trace destination")
            handle, temporary_name = tempfile.mkstemp(
                prefix=f".{safe_trace_run_id(request.document.run_id)}.",
                suffix=".tmp",
                dir=root,
            )
            temporary_path = Path(temporary_name)
            try:
                with os.fdopen(handle, "w", encoding="utf-8") as stream:
                    json.dump(request.document.to_legacy_dict(), stream, ensure_ascii=False, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary_path, final_path)
                temporary_path = None
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)
            return TraceSinkResult(
                sink_name=self.name,
                success=True,
                latency_ms=_elapsed_ms(started_at),
                event_count=event_count,
                trace_path=str(final_path),
            )
        except Exception as exc:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except Exception:
                    pass
            return TraceSinkResult(
                sink_name=self.name,
                success=False,
                latency_ms=_elapsed_ms(started_at),
                event_count=event_count,
                error_type=classify_error(exc) or "internal_error",
            )

    def _validated_root(self) -> Path:
        if has_symlink_component(self._trace_root):
            raise ValueError("unsafe trace root")
        self._trace_root.mkdir(parents=True, exist_ok=True)
        if has_symlink_component(self._trace_root) or not self._trace_root.is_dir():
            raise ValueError("unsafe trace root")
        return self._trace_root.resolve(strict=True)


class StructuredLogTraceSink:
    name = "structured_log"

    def __init__(self, emitter: EventEmitter = emit_observability_event):
        self._emitter = emitter

    def persist(self, request: TracePersistRequest) -> TraceSinkResult:
        started_at = perf_counter()
        document = request.document
        try:
            primary = next(
                (result for result in request.prior_results if result.sink_name == LocalJsonTraceSink.name),
                None,
            )
            latency_ms = primary.latency_ms if primary is not None else _elapsed_ms(started_at)
            status = "success" if primary is None or primary.success else "error"
            error_type = None if primary is None or primary.success else primary.error_type
            payload = build_observability_event(
                "trace_persist_completed",
                run_id=document.run_id,
                session_id=document.session_id,
                operation="trace_persist",
                status=status,
                error_type=error_type,
                latency_ms=latency_ms,
                event_count=document.event_count,
            )
            fields = {key: value for key, value in payload.items() if key not in {"timestamp", "level", "event"}}
            fields.setdefault("error_type", None)
            self._emitter("trace_persist_completed", **fields)
            return TraceSinkResult(self.name, True, latency_ms, document.event_count)
        except Exception as exc:
            return TraceSinkResult(
                self.name,
                False,
                _elapsed_ms(started_at),
                document.event_count,
                error_type=classify_error(exc) or "internal_error",
            )


class CompositeTraceSink:
    name = "composite"

    def __init__(self, sinks: Sequence[TraceSink]):
        self._sinks = tuple(sinks)

    def persist(self, request: TracePersistRequest) -> TraceSinkResult:
        started_at = perf_counter()
        results: list[TraceSinkResult] = []
        for sink in self._sinks:
            try:
                prior_results = request.prior_results + tuple(results)
                results.append(sink.persist(replace(request, prior_results=prior_results)))
            except Exception as exc:
                results.append(
                    TraceSinkResult(
                        sink_name=getattr(sink, "name", "unknown"),
                        success=False,
                        latency_ms=0,
                        event_count=request.document.event_count,
                        error_type=classify_error(exc) or "internal_error",
                    )
                )
        return TraceSinkResult(
            sink_name=self.name,
            success=all(result.success for result in results),
            latency_ms=_elapsed_ms(started_at),
            event_count=request.document.event_count,
            results=tuple(results),
        )


def default_trace_sink(trace_root: str | Path, configured: str | None = None) -> TraceSink:
    raw = configured if configured is not None else os.getenv("INSIGHTFLOW_TRACE_SINKS", "local")
    selected = tuple(part.strip().lower() for part in raw.split(",")) if type(raw) is str else ("local",)
    if not selected or selected[0] != "local" or any(part not in {"local", "structured"} for part in selected):
        selected = ("local",)
    sinks: list[TraceSink] = [LocalJsonTraceSink(trace_root)]
    if "structured" in selected:
        sinks.append(StructuredLogTraceSink())
    return sinks[0] if len(sinks) == 1 else CompositeTraceSink(sinks)


def local_result(result: TraceSinkResult) -> TraceSinkResult:
    if result.sink_name == LocalJsonTraceSink.name:
        return result
    for child in result.results:
        found = local_result(child)
        if found.sink_name == LocalJsonTraceSink.name:
            return found
    return result
