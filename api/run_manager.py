from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Callable
from uuid import uuid4

from api.models import RunCreateRequest, RunStatus
from graph.workflow import run_workflow


TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _new_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return f"api_run_{timestamp}_{uuid4().hex[:8]}"


@dataclass
class RunRecord:
    run_id: str
    user_question: str
    db_path: str
    trace_dir: str
    session_id: str | None = None
    initial_sql: str | None = None
    status: RunStatus = "queued"
    success: bool = True
    final_answer: str = ""
    trace_path: str = ""
    error: str = ""
    trace: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    workflow_result: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)


class RunManager:
    def __init__(
        self,
        workflow_runner: Callable[..., dict[str, Any]] = run_workflow,
        max_workers: int = 4,
    ) -> None:
        self._workflow_runner = workflow_runner
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._runs: dict[str, RunRecord] = {}
        self._lock = Lock()

    def create_run(self, request: RunCreateRequest) -> RunRecord:
        run_id = request.run_id or _new_run_id()
        record = RunRecord(
            run_id=run_id,
            user_question=request.user_question,
            db_path=request.db_path,
            trace_dir=request.trace_dir,
            session_id=request.session_id,
            initial_sql=request.initial_sql,
        )
        self._append_event(record, "run_queued", {"user_question": request.user_question})
        with self._lock:
            self._runs[run_id] = record
        self._executor.submit(self._execute_run, run_id)
        return self.get_run(run_id) or record

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def cancel_run(self, run_id: str) -> RunRecord | None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return None
            if record.status not in TERMINAL_STATUSES:
                record.status = "cancelled"
                record.success = False
                record.error = "run cancelled"
                record.updated_at = _now()
                self._append_event(record, "run_cancelled", {"reason": "cancel requested"})
            return record

    def _execute_run(self, run_id: str) -> None:
        record = self.get_run(run_id)
        if record is None:
            return

        with self._lock:
            if record.status == "cancelled":
                return
            record.status = "running"
            record.updated_at = _now()
            self._append_event(record, "run_running", {})

        try:
            result = self._workflow_runner(
                user_question=record.user_question,
                db_path=record.db_path,
                trace_dir=record.trace_dir,
                run_id=record.run_id,
                session_id=record.session_id,
                initial_sql=record.initial_sql,
            )
        except Exception as exc:
            with self._lock:
                if record.status == "cancelled":
                    return
                record.status = "failed"
                record.success = False
                record.error = str(exc)
                record.updated_at = _now()
                self._append_event(record, "run_failed", {"error": record.error})
            return

        with self._lock:
            if record.status == "cancelled":
                return
            workflow_status = str(result.get("status", "failed"))
            record.status = self._map_workflow_status(workflow_status)
            record.success = record.status == "completed"
            record.final_answer = str(result.get("final_answer", ""))
            record.trace_path = str(result.get("trace_path", ""))
            record.trace = list(result.get("trace", []))
            record.workflow_result = result
            if record.status == "failed":
                record.error = str(result.get("error_message") or result.get("final_answer") or "workflow failed")
            record.updated_at = _now()
            event_type = {
                "completed": "run_completed",
                "failed": "run_failed",
                "waiting_for_approval": "run_waiting_for_approval",
            }.get(record.status, "run_completed")
            self._append_event(record, event_type, {"workflow_status": workflow_status})

    def _map_workflow_status(self, workflow_status: str) -> RunStatus:
        if workflow_status == "completed":
            return "completed"
        if workflow_status == "waiting_for_approval":
            return "waiting_for_approval"
        return "failed"

    def _append_event(self, record: RunRecord, event_type: str, payload: dict[str, Any]) -> None:
        record.events.append(
            {
                "event_type": event_type,
                "run_id": record.run_id,
                "status": record.status,
                "timestamp": _now(),
                "payload": payload,
            }
        )

