from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.models import (
    WorkspaceCreateRequest,
    WorkspaceProfileResponse,
    WorkspaceReportCreateRequest,
    WorkspaceReportCreateResponse,
    WorkspaceReportResponse,
    WorkspaceReportsResponse,
    WorkspaceResponse,
    WorkspaceRunCreateRequest,
    WorkspaceRunResponse,
    WorkspaceSemanticResponse,
    WorkspaceSettingsResponse,
    WorkspaceSourceImportResponse,
    WorkspaceSourcesResponse,
    WorkspaceSqliteSourceRequest,
)
from workspaces.analysis_runner import run_workspace_analysis, run_workspace_analysis_continuation
from workspaces.importers import import_csv, import_excel, import_sqlite
from workspaces.pending_clarification_store import PendingClarificationNotFoundError
from workspaces.profiler import profile_workspace_database
from workspaces.report_runner import run_workspace_report
from workspaces.report_store import ReportNotFoundError, WorkspaceReportStore
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.settings_summary import build_workspace_settings
from workspaces.store import WorkspaceStore


ReportRunner = Callable[..., dict[str, Any]]


def _workspace_not_found(workspace_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")


def create_app(
    workspace_store: WorkspaceStore | None = None,
    report_runner: ReportRunner | None = None,
) -> FastAPI:
    store = workspace_store or WorkspaceStore()
    selected_report_runner = report_runner or run_workspace_report
    report_store = WorkspaceReportStore(store)
    app = FastAPI(title="InsightFlow Agent API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/api/workspaces", response_model=WorkspaceResponse)
    def create_workspace(request: WorkspaceCreateRequest) -> dict:
        return store.create_workspace(request.name)

    @app.get("/api/workspaces")
    def list_workspaces() -> dict:
        return {"workspaces": store.list_workspaces()}

    @app.get("/api/workspaces/{workspace_id}", response_model=WorkspaceResponse)
    def get_workspace(workspace_id: str) -> dict:
        try:
            return store.get_workspace(workspace_id)
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)

    @app.post("/api/workspaces/{workspace_id}/sources/upload", response_model=WorkspaceSourceImportResponse)
    def upload_workspace_source(workspace_id: str, file: UploadFile = File(...)) -> dict:
        try:
            store.get_workspace(workspace_id)
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)

        original_name = Path(file.filename or "").name
        suffix = Path(original_name).suffix.lower()
        if suffix not in {".csv", ".xlsx", ".xls"}:
            raise HTTPException(status_code=400, detail=f"Unsupported source file extension: {suffix or '<none>'}")

        with TemporaryDirectory() as tmp_dir:
            upload_path = Path(tmp_dir) / original_name
            with upload_path.open("wb") as output:
                shutil.copyfileobj(file.file, output)
            if suffix == ".csv":
                return import_csv(store, workspace_id, upload_path)
            return import_excel(store, workspace_id, upload_path)

    @app.post("/api/workspaces/{workspace_id}/sources/sqlite", response_model=WorkspaceSourceImportResponse)
    def create_sqlite_source(workspace_id: str, request: WorkspaceSqliteSourceRequest) -> dict:
        try:
            store.get_workspace(workspace_id)
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)

        sqlite_path = Path(request.sqlite_path)
        if not sqlite_path.exists() or not sqlite_path.is_file():
            raise HTTPException(status_code=400, detail=f"SQLite source is not readable: {request.sqlite_path}")
        try:
            return import_sqlite(store, workspace_id, sqlite_path)
        except (OSError, sqlite3.DatabaseError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"SQLite source is not readable: {exc}") from exc

    @app.get("/api/workspaces/{workspace_id}/sources", response_model=WorkspaceSourcesResponse)
    def list_workspace_sources(workspace_id: str) -> dict:
        try:
            workspace = store.get_workspace(workspace_id)
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)
        return {"sources": workspace.get("sources", [])}

    @app.get("/api/workspaces/{workspace_id}/settings", response_model=WorkspaceSettingsResponse)
    def get_workspace_settings(workspace_id: str) -> dict:
        try:
            workspace = store.get_workspace(workspace_id)
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)
        return build_workspace_settings(store, workspace)

    @app.post("/api/workspaces/{workspace_id}/profile", response_model=WorkspaceProfileResponse)
    def create_profile(workspace_id: str) -> dict:
        try:
            return {"success": True, "profile": profile_workspace_database(store, workspace_id)}
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)

    @app.post("/api/workspaces/{workspace_id}/semantic-layer/draft", response_model=WorkspaceSemanticResponse)
    def create_semantic_draft(workspace_id: str) -> dict:
        try:
            profile = profile_workspace_database(store, workspace_id)
            semantic_layer = generate_semantic_layer_draft(store, workspace_id, profile)
            return {"success": True, "semantic_layer": semantic_layer}
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)

    @app.post("/api/workspaces/{workspace_id}/runs", response_model=WorkspaceRunResponse)
    def create_workspace_run(workspace_id: str, request: WorkspaceRunCreateRequest) -> dict:
        try:
            if request.pending_run_id:
                result = run_workspace_analysis_continuation(
                    store=store,
                    workspace_id=workspace_id,
                    pending_run_id=request.pending_run_id,
                    clarification_answer=request.clarification_answer or "",
                )
            else:
                result = run_workspace_analysis(
                    store=store,
                    workspace_id=workspace_id,
                    user_question=request.user_question or "",
                    initial_sql=request.initial_sql,
                )
        except PendingClarificationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "success": result.get("status") != "failed",
            "workspace_id": workspace_id,
            "run_id": result.get("run_id"),
            "result": result,
            "product_result": result.get("product_result"),
        }

    @app.post("/api/workspaces/{workspace_id}/reports", response_model=WorkspaceReportCreateResponse)
    def create_workspace_report(workspace_id: str, request: WorkspaceReportCreateRequest) -> dict:
        try:
            return selected_report_runner(
                store=store,
                workspace_id=workspace_id,
                report_type=request.report_type,
                report_goal=request.report_goal,
            )
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/workspaces/{workspace_id}/reports", response_model=WorkspaceReportsResponse)
    def list_workspace_reports(workspace_id: str) -> dict:
        try:
            reports = report_store.list_reports(workspace_id)
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)
        return {
            "workspace_id": workspace_id,
            "reports": [report.to_dict() for report in reports],
        }

    @app.get("/api/workspaces/{workspace_id}/reports/{report_id}", response_model=WorkspaceReportResponse)
    def get_workspace_report(workspace_id: str, report_id: str) -> dict:
        try:
            report = report_store.load_report(workspace_id, report_id)
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)
        return {
            "workspace_id": workspace_id,
            "report_id": report_id,
            "report": report.to_dict(),
        }

    @app.get("/api/workspaces/{workspace_id}/reports/{report_id}/download")
    def download_workspace_report(workspace_id: str, report_id: str) -> FileResponse:
        try:
            report = report_store.load_report(workspace_id, report_id)
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)

        markdown_path = Path(report.markdown_path)
        if not markdown_path.exists() or not markdown_path.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"Report Markdown not found: {report_id}",
            )
        return FileResponse(
            markdown_path,
            media_type="text/markdown",
            filename=f"{report_id}.md",
        )

    return app


app = create_app()
