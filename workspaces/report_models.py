from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from workspaces.models import utc_now_iso


@dataclass
class ReportSection:
    section_id: str
    title: str
    purpose: str
    status: str
    question: str = ""
    summary: str = ""
    sql: str = ""
    columns: list[str] = field(default_factory=list)
    rows_preview: list[dict[str, Any]] = field(default_factory=list)
    artifact_paths: list[str] = field(default_factory=list)
    evidence_notes: list[str] = field(default_factory=list)
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    trace_nodes: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportSection":
        return cls(
            section_id=data["section_id"],
            title=data["title"],
            purpose=data.get("purpose", ""),
            status=data.get("status", "draft"),
            question=data.get("question", ""),
            summary=data.get("summary", ""),
            sql=data.get("sql", ""),
            columns=list(data.get("columns", [])),
            rows_preview=list(data.get("rows_preview", [])),
            artifact_paths=list(data.get("artifact_paths", [])),
            evidence_notes=list(data.get("evidence_notes", [])),
            provider_metadata=dict(data.get("provider_metadata", {})),
            trace_nodes=list(data.get("trace_nodes", [])),
            error=data.get("error"),
        )


@dataclass
class ReportRecord:
    report_id: str
    workspace_id: str
    report_type: str
    report_goal: str
    title: str
    status: str = "draft"
    executive_summary: list[str] = field(default_factory=list)
    sections: list[ReportSection] = field(default_factory=list)
    markdown_path: str = ""
    json_path: str = ""
    trace_path: str = ""
    artifact_dir: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    provider_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["sections"] = [section.to_dict() for section in self.sections]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportRecord":
        return cls(
            report_id=data["report_id"],
            workspace_id=data["workspace_id"],
            report_type=data["report_type"],
            report_goal=data.get("report_goal", ""),
            title=data.get("title", data["report_id"]),
            status=data.get("status", "draft"),
            executive_summary=list(data.get("executive_summary", [])),
            sections=[
                ReportSection.from_dict(section)
                for section in data.get("sections", [])
            ],
            markdown_path=data.get("markdown_path", ""),
            json_path=data.get("json_path", ""),
            trace_path=data.get("trace_path", ""),
            artifact_dir=data.get("artifact_dir", ""),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
            provider_metadata=dict(data.get("provider_metadata", {})),
        )
