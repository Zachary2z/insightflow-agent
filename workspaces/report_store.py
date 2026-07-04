from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from workspaces.models import utc_now_iso
from workspaces.report_markdown import render_report_markdown
from workspaces.report_models import ReportRecord
from workspaces.store import WorkspaceStore


class ReportNotFoundError(FileNotFoundError):
    pass


class WorkspaceReportStore:
    def __init__(self, workspace_store: WorkspaceStore):
        self.workspace_store = workspace_store

    def create_report_record(
        self,
        *,
        workspace_id: str,
        report_type: str,
        report_goal: str,
        title: str,
        status: str = "draft",
    ) -> ReportRecord:
        report = ReportRecord(
            report_id=f"report_{uuid4().hex[:8]}",
            workspace_id=workspace_id,
            report_type=report_type,
            report_goal=report_goal,
            title=title,
            status=status,
        )
        return self.save_report(report, event_type="created")

    def save_report(
        self,
        report: ReportRecord,
        *,
        event_type: str = "rendered",
    ) -> ReportRecord:
        report_dir = self._report_dir(report.workspace_id, report.report_id)
        artifact_dir = self._artifact_dir(report, report_dir)
        self._validate_report_paths(report, report_dir, artifact_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        report.json_path = str(report_dir / "report.json")
        report.markdown_path = str(report_dir / "report.md")
        report.trace_path = str(report_dir / "trace.json")
        report.artifact_dir = str(artifact_dir)
        report.updated_at = utc_now_iso()
        self._validate_artifact_paths(report, report_dir)
        (report_dir / "report.json").write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (report_dir / "report.md").write_text(
            render_report_markdown(report),
            encoding="utf-8",
        )
        self._write_trace(report, event_type)
        return report

    def load_report(self, workspace_id: str, report_id: str) -> ReportRecord:
        report_path = self._report_dir(workspace_id, report_id) / "report.json"
        if not report_path.exists():
            raise ReportNotFoundError(f"Report not found: {report_id}")
        return ReportRecord.from_dict(
            json.loads(report_path.read_text(encoding="utf-8"))
        )

    def list_reports(self, workspace_id: str) -> list[ReportRecord]:
        reports_dir = self._reports_dir(workspace_id)
        if not reports_dir.exists():
            return []
        reports = [
            ReportRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
            for path in reports_dir.glob("*/report.json")
        ]
        return sorted(
            reports,
            key=lambda report: (report.created_at, report.report_id),
            reverse=True,
        )

    def _reports_dir(self, workspace_id: str) -> Path:
        workspace = self.workspace_store.get_workspace(workspace_id)
        return Path(workspace["root_path"]) / "reports"

    def _report_dir(self, workspace_id: str, report_id: str) -> Path:
        return self._reports_dir(workspace_id) / report_id

    def _artifact_dir(self, report: ReportRecord, report_dir: Path) -> Path:
        if report.artifact_dir:
            return Path(report.artifact_dir)
        return report_dir / "artifacts"

    def _validate_report_paths(
        self,
        report: ReportRecord,
        report_dir: Path,
        artifact_dir: Path,
    ) -> None:
        resolved_report_dir = report_dir.resolve()
        resolved_artifact_dir = artifact_dir.resolve()
        if (
            resolved_artifact_dir != resolved_report_dir
            and resolved_report_dir not in resolved_artifact_dir.parents
        ):
            raise ValueError(f"Artifact directory is outside report directory: {artifact_dir}")
        for path_value in [report.json_path, report.markdown_path, report.trace_path]:
            if not path_value:
                continue
            path = Path(path_value).resolve()
            if path.parent != resolved_report_dir:
                raise ValueError(f"Report file path is outside report directory: {path_value}")

    def _validate_artifact_paths(self, report: ReportRecord, report_dir: Path) -> None:
        resolved_report_dir = report_dir.resolve()
        if not report.evidence_pack:
            return
        for chart in report.evidence_pack.charts:
            for artifact_path in [chart.path]:
                if not artifact_path:
                    continue
                candidate = Path(artifact_path)
                if not candidate.is_absolute():
                    candidate = self._reports_dir(report.workspace_id).parent / candidate
                resolved_candidate = candidate.resolve()
                if (
                    resolved_candidate != resolved_report_dir
                    and resolved_report_dir not in resolved_candidate.parents
                ):
                    raise ValueError(
                        f"Artifact path is outside report directory: {artifact_path}"
                    )

    def _write_trace(self, report: ReportRecord, event_type: str) -> None:
        trace_path = Path(report.trace_path)
        existing_events = []
        if trace_path.exists():
            existing = json.loads(trace_path.read_text(encoding="utf-8"))
            existing_events = list(existing.get("events", []))
        existing_events.append(
            {
                "event": event_type,
                "report_id": report.report_id,
                "workspace_id": report.workspace_id,
                "created_at": utc_now_iso(),
            }
        )
        trace_path.write_text(
            json.dumps(
                {
                    "report_id": report.report_id,
                    "workspace_id": report.workspace_id,
                    "events": existing_events,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
