from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI, File, HTTPException, UploadFile

from api.models import (
    RunCreateRequest,
    RunCreateResponse,
    RunEventsResponse,
    RunStatusResponse,
    RunTraceResponse,
    WorkspaceCreateRequest,
    WorkspaceProfileResponse,
    WorkspaceResponse,
    WorkspaceRunCreateRequest,
    WorkspaceRunResponse,
    WorkspaceSemanticResponse,
    WorkspaceSourceImportResponse,
    WorkspaceSourcesResponse,
    WorkspaceSqliteSourceRequest,
)
from api.run_manager import RunManager, RunRecord
from workspaces.analysis_runner import run_workspace_analysis
from workspaces.importers import import_csv, import_excel, import_sqlite
from workspaces.profiler import profile_workspace_database
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


def _not_found(run_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Run not found: {run_id}")


def _workspace_not_found(workspace_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")


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


def create_app(run_manager: RunManager | None = None, workspace_store: WorkspaceStore | None = None) -> FastAPI:
    manager = run_manager or RunManager()
    store = workspace_store or WorkspaceStore()
    app = FastAPI(title="InsightFlow Agent API", version="0.1.0")

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
            result = run_workspace_analysis(
                store=store,
                workspace_id=workspace_id,
                user_question=request.user_question,
                initial_sql=request.initial_sql,
            )
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)
        return {
            "success": result.get("status") != "failed",
            "workspace_id": workspace_id,
            "run_id": result.get("run_id"),
            "result": result,
        }

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
