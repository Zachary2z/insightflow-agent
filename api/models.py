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


class WorkspaceCreateRequest(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    workspace_id: str
    name: str
    created_at: str
    updated_at: str
    root_path: str
    analysis_db_path: str
    profile_path: str
    semantic_layer_path: str
    sources: list[dict[str, Any]] = Field(default_factory=list)


class WorkspaceSourceImportResponse(BaseModel):
    success: bool
    source: dict[str, Any]
    imported_tables: list[str]


class WorkspaceSourcesResponse(BaseModel):
    sources: list[dict[str, Any]] = Field(default_factory=list)


class WorkspaceSqliteSourceRequest(BaseModel):
    sqlite_path: str = Field(..., min_length=1)


class WorkspaceProfileResponse(BaseModel):
    success: bool
    profile: dict[str, Any]


class WorkspaceSemanticResponse(BaseModel):
    success: bool
    semantic_layer: dict[str, Any]


class WorkspaceRunCreateRequest(BaseModel):
    user_question: str
    initial_sql: str | None = None


class WorkspaceRunResponse(BaseModel):
    success: bool
    workspace_id: str
    run_id: str | None = None
    result: dict[str, Any]
