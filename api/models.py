from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


RunStatus = Literal["queued", "running", "waiting_for_approval", "completed", "failed", "cancelled"]


class RunCreateRequest(BaseModel):
    user_question: str = Field(..., min_length=1)
    db_path: str = "data/ecommerce.db"
    trace_dir: str = "logs/traces"
    run_id: str | None = None
    session_id: str | None = None
    initial_sql: str | None = None


class RunCreateResponse(BaseModel):
    success: bool
    run_id: str
    status: RunStatus


class RunStatusResponse(BaseModel):
    success: bool
    run_id: str
    status: RunStatus
    user_question: str
    final_answer: str = ""
    trace_path: str = ""
    error: str = ""
    created_at: str
    updated_at: str


class RunTraceResponse(BaseModel):
    success: bool
    run_id: str
    status: RunStatus
    trace_path: str = ""
    trace: list[dict[str, Any]]


class RunEventsResponse(BaseModel):
    success: bool
    run_id: str
    status: RunStatus
    events: list[dict[str, Any]]

