from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


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
    user_question: str | None = None
    initial_sql: str | None = None
    pending_run_id: str | None = None
    clarification_answer: str | None = None

    @model_validator(mode="after")
    def validate_run_mode(self) -> "WorkspaceRunCreateRequest":
        user_question = (self.user_question or "").strip()
        pending_run_id = (self.pending_run_id or "").strip()
        clarification_answer = (self.clarification_answer or "").strip()
        has_question = bool(user_question)
        has_continuation = bool(pending_run_id or clarification_answer)

        if has_question and has_continuation:
            raise ValueError("Provide either user_question or pending_run_id with clarification_answer, not both.")
        if has_question:
            self.user_question = user_question
            return self
        if pending_run_id and clarification_answer:
            self.pending_run_id = pending_run_id
            self.clarification_answer = clarification_answer
            return self
        raise ValueError("Provide user_question or pending_run_id with clarification_answer.")


class WorkspaceRunResponse(BaseModel):
    success: bool
    workspace_id: str
    run_id: str | None = None
    result: dict[str, Any]
    product_result: dict[str, Any] | None = None


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
