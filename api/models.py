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
    data_version: int = 1
    sources: list[dict[str, Any]] = Field(default_factory=list)


class WorkspaceSourceImportResponse(BaseModel):
    success: bool
    source: dict[str, Any]
    imported_tables: list[str]
    data_version: int | None = None


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


class WorkspaceSettingsResponse(BaseModel):
    workspace_id: str
    workspace_name: str = ""
    data_sources: dict[str, Any]
    profile: dict[str, Any]
    semantic_layer: dict[str, Any]
    model_mode: dict[str, Any]
    safety: dict[str, Any]


class WorkspaceRunCreateRequest(BaseModel):
    user_question: str | None = None
    initial_sql: str | None = None
    force_reanalysis: bool = False

    @model_validator(mode="after")
    def validate_run_mode(self) -> "WorkspaceRunCreateRequest":
        user_question = (self.user_question or "").strip()
        if not user_question:
            raise ValueError("Provide user_question.")
        self.user_question = user_question
        return self


class WorkspaceRunFollowUpRequest(BaseModel):
    message: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_message(self) -> "WorkspaceRunFollowUpRequest":
        self.message = self.message.strip()
        if not self.message:
            raise ValueError("Provide a follow-up message.")
        return self


class WorkspaceRunResponse(BaseModel):
    success: bool
    workspace_id: str
    run_id: str | None = None
    status: str | None = None
    matched_run_id: str | None = None
    message: str | None = None
    data_version: int | None = None
    normalized_question: str | None = None
    result: dict[str, Any]
    product_result: dict[str, Any] | None = None


class WorkspaceRunSummary(BaseModel):
    run_id: str
    status: str
    question: str = ""
    headline: str = ""
    created_at: str | None = None
    saved_at: str | None = None
    has_chart: bool = False
    requires_clarification: bool = False
    failure_reason: str = ""


class WorkspaceRunsResponse(BaseModel):
    workspace_id: str
    runs: list[WorkspaceRunSummary] = Field(default_factory=list)


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


class WorkspaceReportExportResponse(BaseModel):
    success: bool
    workspace_id: str
    report_id: str
    document_path: str = ""
    download_name: str = ""
    download_url: str = ""
    warnings: list[str] = Field(default_factory=list)
    artifact: dict[str, Any] = Field(default_factory=dict)


class WorkspaceReportPublishResponse(BaseModel):
    success: bool
    workspace_id: str
    report_id: str
    publish_result: dict[str, Any]
