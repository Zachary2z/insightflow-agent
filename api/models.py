from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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


class WorkspaceReportCreateRequest(BaseModel):
    report_type: str = Field(..., min_length=1)
    report_goal: str = Field(..., min_length=1)


class WorkspaceReportCreateResponse(BaseModel):
    success: bool
    workspace_id: str
    report_id: str
    report: dict[str, Any]


class WorkspaceReportsResponse(BaseModel):
    workspace_id: str
    reports: list[dict[str, Any]] = Field(default_factory=list)


class WorkspaceReportResponse(BaseModel):
    workspace_id: str
    report_id: str
    report: dict[str, Any]
