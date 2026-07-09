from __future__ import annotations

import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.models import (
    WorkspaceCreateRequest,
    WorkspaceProfileResponse,
    WorkspaceReportCreateRequest,
    WorkspaceReportCreateResponse,
    WorkspaceReportExportResponse,
    WorkspaceReportPublishResponse,
    WorkspaceReportResponse,
    WorkspaceReportsResponse,
    WorkspaceResponse,
    WorkspaceRunCreateRequest,
    WorkspaceRunFollowUpRequest,
    WorkspaceRunResponse,
    WorkspaceRunsResponse,
    WorkspaceSemanticResponse,
    WorkspaceSettingsResponse,
    WorkspaceSourceImportResponse,
    WorkspaceSourcesResponse,
    WorkspaceSqliteSourceRequest,
)
from llm_ops.runtime_provider import build_report_composer_provider
from workspaces.analysis_runner import (
    execute_workspace_analysis_job,
    run_workspace_analysis_follow_up,
    submit_workspace_analysis_run,
)
from workspaces.importers import import_csv, import_excel, import_sqlite
from workspaces.document_export import export_report_docx
from workspaces.export_package import build_report_export_package
from workspaces.feishu_publisher import CliFeishuPublisher
from workspaces.feishu_sheet_publisher import CliFeishuSheetPublisher
from workspaces.profiler import profile_workspace_database
from workspaces.report_models import ReportArtifactRecord, ReportToolCallRecord
from workspaces.report_runner import run_workspace_report
from workspaces.report_store import ReportNotFoundError, WorkspaceReportStore
from workspaces.run_store import RunNotFoundError, WorkspaceRunStore
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.settings_summary import build_workspace_settings
from workspaces.store import WorkspaceStore


ReportRunner = Callable[..., dict[str, Any]]


def _workspace_not_found(workspace_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")


def _workspace_artifact_url(workspace_id: str, relative_path: str) -> str:
    encoded_path = "/".join(
        quote(part, safe="")
        for part in str(relative_path).split("/")
        if part
    )
    return f"/api/workspaces/{workspace_id}/artifacts/{encoded_path}"


def _friendly_export_warnings(warnings: list[str]) -> list[str]:
    friendly: list[str] = []
    for warning in warnings:
        text = str(warning or "").strip()
        if not text:
            continue
        if "SVG" in text or "静态图" in text or "无法插入" in text:
            friendly.append("部分图表当前以占位说明展示。")
        else:
            friendly.append(text)
    return list(dict.fromkeys(friendly))


def _build_feishu_publisher(*, workspace_root: Path | None = None) -> CliFeishuPublisher:
    return CliFeishuPublisher(
        workspace_root=workspace_root,
        sheet_publisher=CliFeishuSheetPublisher(),
    )


def create_app(
    workspace_store: WorkspaceStore | None = None,
    report_runner: ReportRunner | None = None,
    start_background_analysis: bool = True,
) -> FastAPI:
    store = workspace_store or WorkspaceStore()
    selected_report_runner = report_runner or run_workspace_report
    report_store = WorkspaceReportStore(store)
    run_store = WorkspaceRunStore(store)
    app = FastAPI(title="InsightFlow Agent API", version="0.1.0")
    analysis_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="insightflow-analysis")
    app.state.analysis_executor = analysis_executor
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
            result = submit_workspace_analysis_run(
                store=store,
                workspace_id=workspace_id,
                user_question=request.user_question or "",
                initial_sql=request.initial_sql,
                force_reanalysis=request.force_reanalysis,
            )
            if start_background_analysis and result.get("status") == "running" and result.get("run_id"):
                analysis_executor.submit(
                    execute_workspace_analysis_job,
                    store,
                    workspace_id,
                    str(result["run_id"]),
                    request.user_question or "",
                    request.initial_sql,
                )
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "success": result.get("status") != "failed",
            "workspace_id": workspace_id,
            "run_id": result.get("run_id"),
            "status": result.get("status"),
            "matched_run_id": result.get("matched_run_id"),
            "message": result.get("message"),
            "data_version": result.get("data_version"),
            "normalized_question": result.get("normalized_question"),
            "result": result,
            "product_result": result.get("product_result"),
        }

    @app.post("/api/workspaces/{workspace_id}/runs/{run_id}/follow-ups", response_model=WorkspaceRunResponse)
    def create_workspace_run_follow_up(
        workspace_id: str,
        run_id: str,
        request: WorkspaceRunFollowUpRequest,
    ) -> dict:
        try:
            result = run_workspace_analysis_follow_up(
                store=store,
                workspace_id=workspace_id,
                run_id=run_id,
                message=request.message,
            )
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "success": result.get("status") != "failed",
            "workspace_id": workspace_id,
            "run_id": result.get("run_id"),
            "status": result.get("status"),
            "matched_run_id": result.get("matched_run_id"),
            "message": result.get("message"),
            "data_version": result.get("data_version"),
            "normalized_question": result.get("normalized_question"),
            "result": result,
            "product_result": result.get("product_result"),
        }

    @app.get("/api/workspaces/{workspace_id}/runs", response_model=WorkspaceRunsResponse)
    def list_workspace_runs(workspace_id: str) -> dict:
        try:
            runs = run_store.list_runs(workspace_id)
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)
        return {
            "workspace_id": workspace_id,
            "runs": runs,
        }

    @app.get("/api/workspaces/{workspace_id}/runs/{run_id}", response_model=WorkspaceRunResponse)
    def get_workspace_run(workspace_id: str, run_id: str) -> dict:
        try:
            return run_store.load_run_response(workspace_id, run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)

    @app.get("/api/workspaces/{workspace_id}/artifacts/{relative_path:path}")
    def read_workspace_artifact(workspace_id: str, relative_path: str) -> FileResponse:
        try:
            store.get_workspace(workspace_id)
            artifact_path = store.resolve_workspace_path(workspace_id, relative_path)
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Artifact not found") from exc

        if not artifact_path.exists() or not artifact_path.is_file():
            raise HTTPException(status_code=404, detail="Artifact not found")
        return FileResponse(artifact_path)

    @app.post("/api/workspaces/{workspace_id}/reports", response_model=WorkspaceReportCreateResponse)
    def create_workspace_report(workspace_id: str, request: WorkspaceReportCreateRequest) -> dict:
        try:
            report_composer_provider = build_report_composer_provider()
            providers = (
                {"report_composer": report_composer_provider}
                if report_composer_provider is not None
                else None
            )
            return selected_report_runner(
                store=store,
                workspace_id=workspace_id,
                report_type=request.report_type,
                report_goal=request.report_goal,
                providers=providers,
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

    @app.post(
        "/api/workspaces/{workspace_id}/reports/{report_id}/export",
        response_model=WorkspaceReportExportResponse,
    )
    def export_workspace_report(workspace_id: str, report_id: str) -> dict:
        try:
            workspace = store.get_workspace(workspace_id)
            report = report_store.load_report(workspace_id, report_id)
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)

        workspace_root = Path(workspace["root_path"]).resolve()
        export_package = build_report_export_package(report, workspace_root=workspace_root)
        export_result = export_report_docx(export_package, workspace_root=workspace_root)
        if not export_result.get("success"):
            detail = "; ".join(str(item) for item in export_result.get("warnings", []) if item)
            raise HTTPException(status_code=500, detail=detail or "Report Word export failed")

        document_path = str(export_result.get("document_path") or "")
        try:
            absolute_document_path = store.resolve_workspace_path(workspace_id, document_path)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail="Report Word export path is unsafe") from exc
        if not absolute_document_path.exists() or not absolute_document_path.is_file():
            raise HTTPException(status_code=500, detail="Report Word export file was not created")

        download_url = _workspace_artifact_url(workspace_id, document_path)
        artifact = dict(export_result.get("artifact") or {})
        artifact["relative_path"] = document_path
        artifact["download_url"] = download_url
        artifact["download_name"] = str(export_result.get("download_name") or artifact.get("download_name") or "")
        report.artifacts = [
            artifact_record
            for artifact_record in report.artifacts
            if artifact_record.artifact_id != artifact.get("artifact_id")
        ]
        report.artifacts.append(
            ReportArtifactRecord(
                artifact_id=str(artifact.get("artifact_id") or f"artifact_docx_{report_id}"),
                artifact_type="word_document",
                title=str(artifact.get("title") or report.title or "Word 报告"),
                relative_path=document_path,
                download_url=download_url,
                source="document_export",
                evidence_ids=list(export_package.evidence_refs),
                chart_ids=[
                    str(chart.get("artifact_id") or chart.get("chart_id"))
                    for chart in export_package.chart_artifacts
                    if isinstance(chart, dict) and (chart.get("artifact_id") or chart.get("chart_id"))
                ],
                status="completed",
                created_at=str(artifact.get("created_at") or report.updated_at or report.created_at),
            )
        )
        report.tool_calls.append(
            ReportToolCallRecord(
                tool_call_id=f"tool_call_docx_{report_id}",
                tool_name="document_export",
                input_summary=f"导出 Word 报告：{report.title}",
                referenced_evidence_ids=list(export_package.evidence_refs),
                output_artifact_ids=[str(artifact.get("artifact_id") or f"artifact_docx_{report_id}")],
                status="completed",
            )
        )
        report_store.save_report(report, event_type="report_docx_exported")

        return {
            "success": True,
            "workspace_id": workspace_id,
            "report_id": report_id,
            "document_path": document_path,
            "download_name": str(export_result.get("download_name") or ""),
            "download_url": download_url,
            "warnings": _friendly_export_warnings(list(export_result.get("warnings") or [])),
            "artifact": artifact,
        }

    @app.post(
        "/api/workspaces/{workspace_id}/reports/{report_id}/publish/feishu",
        response_model=WorkspaceReportPublishResponse,
    )
    def publish_workspace_report_to_feishu(workspace_id: str, report_id: str) -> dict:
        try:
            workspace = store.get_workspace(workspace_id)
            report = report_store.load_report(workspace_id, report_id)
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError:
            raise _workspace_not_found(workspace_id)

        try:
            workspace_root = Path(workspace["root_path"]).resolve()
            export_package = build_report_export_package(
                report,
                workspace_root=workspace_root,
                static_asset_target_format="png",
            )
            publish_result = _build_feishu_publisher(workspace_root=workspace_root).publish_report(export_package)
            safe_result = publish_result.to_safe_dict()
            report.external_publish_results = {
                **dict(report.external_publish_results or {}),
                "feishu": safe_result,
            }
            report_store.save_report(report, event_type="report_published_feishu")
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - only unexpected program errors become API 500.
            raise HTTPException(status_code=500, detail="Feishu publish failed unexpectedly") from exc

        return {
            "success": safe_result.get("status") in {"published", "warning"},
            "workspace_id": workspace_id,
            "report_id": report_id,
            "publish_result": safe_result,
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
