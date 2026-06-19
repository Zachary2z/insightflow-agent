from __future__ import annotations

from fastapi import FastAPI, HTTPException

from api.models import (
    RunCreateRequest,
    RunCreateResponse,
    RunEventsResponse,
    RunStatusResponse,
    RunTraceResponse,
)
from api.run_manager import RunManager, RunRecord


def _not_found(run_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Run not found: {run_id}")


def _status_response(record: RunRecord) -> RunStatusResponse:
    return RunStatusResponse(
        success=record.success,
        run_id=record.run_id,
        status=record.status,
        user_question=record.user_question,
        final_answer=record.final_answer,
        trace_path=record.trace_path,
        error=record.error,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def create_app(run_manager: RunManager | None = None) -> FastAPI:
    manager = run_manager or RunManager()
    app = FastAPI(title="InsightFlow Agent API", version="0.1.0")

    @app.post("/api/runs", response_model=RunCreateResponse, status_code=202)
    def create_run(request: RunCreateRequest) -> RunCreateResponse:
        record = manager.create_run(request)
        return RunCreateResponse(success=True, run_id=record.run_id, status=record.status)

    @app.get("/api/runs/{run_id}", response_model=RunStatusResponse)
    def get_run(run_id: str) -> RunStatusResponse:
        record = manager.get_run(run_id)
        if record is None:
            raise _not_found(run_id)
        return _status_response(record)

    @app.get("/api/runs/{run_id}/trace", response_model=RunTraceResponse)
    def get_run_trace(run_id: str) -> RunTraceResponse:
        record = manager.get_run(run_id)
        if record is None:
            raise _not_found(run_id)
        return RunTraceResponse(
            success=record.success,
            run_id=record.run_id,
            status=record.status,
            trace_path=record.trace_path,
            trace=record.trace,
        )

    @app.get("/api/runs/{run_id}/events", response_model=RunEventsResponse)
    def get_run_events(run_id: str) -> RunEventsResponse:
        record = manager.get_run(run_id)
        if record is None:
            raise _not_found(run_id)
        return RunEventsResponse(
            success=record.success,
            run_id=record.run_id,
            status=record.status,
            events=record.events,
        )

    @app.post("/api/runs/{run_id}/cancel", response_model=RunStatusResponse)
    def cancel_run(run_id: str) -> RunStatusResponse:
        record = manager.cancel_run(run_id)
        if record is None:
            raise _not_found(run_id)
        return _status_response(record)

    return app


app = create_app()
