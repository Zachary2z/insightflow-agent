from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from workspaces.models import utc_now_iso


@dataclass
class EvidenceRequirement:
    requirement_id: str
    chapter_id: str
    description: str
    metric_hint: str = ""
    dimension_hint: str = ""
    query_hint: str = ""
    chart_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRequirement":
        return cls(
            requirement_id=str(data.get("requirement_id") or ""),
            chapter_id=str(data.get("chapter_id") or ""),
            description=str(data.get("description") or ""),
            metric_hint=str(data.get("metric_hint") or ""),
            dimension_hint=str(data.get("dimension_hint") or ""),
            query_hint=str(data.get("query_hint") or ""),
            chart_hint=str(data.get("chart_hint") or ""),
        )


@dataclass
class ReportChapterPlan:
    chapter_id: str
    title: str
    purpose: str
    evidence_requirements: list[EvidenceRequirement] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_requirements"] = [
            requirement.to_dict() for requirement in self.evidence_requirements
        ]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportChapterPlan":
        return cls(
            chapter_id=str(data.get("chapter_id") or ""),
            title=str(data.get("title") or ""),
            purpose=str(data.get("purpose") or ""),
            evidence_requirements=[
                EvidenceRequirement.from_dict(requirement)
                for requirement in data.get("evidence_requirements", [])
                if isinstance(requirement, dict)
            ],
        )


@dataclass
class ReportPlan:
    title: str
    report_style: str
    time_range: str
    data_sources: list[str] = field(default_factory=list)
    chapters: list[ReportChapterPlan] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["chapters"] = [chapter.to_dict() for chapter in self.chapters]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportPlan":
        return cls(
            title=str(data.get("title") or ""),
            report_style=str(data.get("report_style") or ""),
            time_range=str(data.get("time_range") or ""),
            data_sources=[str(source) for source in data.get("data_sources", [])],
            chapters=[
                ReportChapterPlan.from_dict(chapter)
                for chapter in data.get("chapters", [])
                if isinstance(chapter, dict)
            ],
            created_at=str(data.get("created_at") or utc_now_iso()),
        )


@dataclass
class ReportEvidenceFact:
    fact_id: str
    label: str
    value: Any
    display_value: str
    source_chapter_id: str
    evidence_ref: str
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportEvidenceFact":
        return cls(
            fact_id=str(data.get("fact_id") or ""),
            label=str(data.get("label") or ""),
            value=data.get("value"),
            display_value=str(data.get("display_value") or ""),
            source_chapter_id=str(data.get("source_chapter_id") or ""),
            evidence_ref=str(data.get("evidence_ref") or ""),
            unit=str(data.get("unit") or ""),
        )


@dataclass
class ReportEvidenceTable:
    table_id: str
    title: str
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    source_chapter_id: str = ""
    description: str = ""
    evidence_ref: str = ""
    evidence_payload_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportEvidenceTable":
        return cls(
            table_id=str(data.get("table_id") or ""),
            title=str(data.get("title") or ""),
            columns=[str(column) for column in data.get("columns", [])],
            rows=[
                dict(row)
                for row in data.get("rows", [])
                if isinstance(row, dict)
            ],
            source_chapter_id=str(data.get("source_chapter_id") or ""),
            description=str(data.get("description") or ""),
            evidence_ref=str(data.get("evidence_ref") or ""),
            evidence_payload_ref=str(data.get("evidence_payload_ref") or ""),
        )


@dataclass
class ReportEvidenceChart:
    chart_id: str
    title: str
    source_chapter_id: str
    chart_type: str = ""
    path: str = ""
    url: str = ""
    description: str = ""
    evidence_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportEvidenceChart":
        return cls(
            chart_id=str(data.get("chart_id") or ""),
            title=str(data.get("title") or ""),
            source_chapter_id=str(data.get("source_chapter_id") or ""),
            chart_type=str(data.get("chart_type") or ""),
            path=str(data.get("path") or ""),
            url=str(data.get("url") or ""),
            description=str(data.get("description") or ""),
            evidence_ref=str(data.get("evidence_ref") or ""),
        )


@dataclass
class ReportEvidencePack:
    facts: list[ReportEvidenceFact] = field(default_factory=list)
    tables: list[ReportEvidenceTable] = field(default_factory=list)
    charts: list[ReportEvidenceChart] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data_limits: list[str] = field(default_factory=list)
    evidence_payloads: list[dict[str, Any]] = field(default_factory=list)
    technical_details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["facts"] = [fact.to_dict() for fact in self.facts]
        data["tables"] = [table.to_dict() for table in self.tables]
        data["charts"] = [chart.to_dict() for chart in self.charts]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportEvidencePack":
        return cls(
            facts=[
                ReportEvidenceFact.from_dict(fact)
                for fact in data.get("facts", [])
                if isinstance(fact, dict)
            ],
            tables=[
                ReportEvidenceTable.from_dict(table)
                for table in data.get("tables", [])
                if isinstance(table, dict)
            ],
            charts=[
                ReportEvidenceChart.from_dict(chart)
                for chart in data.get("charts", [])
                if isinstance(chart, dict)
            ],
            warnings=[str(warning) for warning in data.get("warnings", [])],
            data_limits=[str(limit) for limit in data.get("data_limits", [])],
            evidence_payloads=[
                dict(payload)
                for payload in data.get("evidence_payloads", [])
                if isinstance(payload, dict)
            ],
            technical_details=dict(data.get("technical_details", {})),
        )


@dataclass
class ReportValidationResult:
    status: str = "passed"
    checked_facts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportValidationResult":
        return cls(
            status=str(data.get("status") or "passed"),
            checked_facts=[str(fact) for fact in data.get("checked_facts", [])],
            warnings=[str(warning) for warning in data.get("warnings", [])],
            unsupported_claims=[
                str(claim) for claim in data.get("unsupported_claims", [])
            ],
        )


@dataclass
class ReportDocumentSection:
    section_id: str
    title: str
    body: str
    chart_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    technical_details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not self.technical_details:
            data.pop("technical_details", None)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportDocumentSection":
        return cls(
            section_id=str(data.get("section_id") or ""),
            title=str(data.get("title") or ""),
            body=str(data.get("body") or ""),
            chart_refs=[str(ref) for ref in data.get("chart_refs", [])],
            evidence_refs=[str(ref) for ref in data.get("evidence_refs", [])],
            technical_details=dict(data.get("technical_details", {})),
        )


@dataclass
class ReportDocument:
    title: str
    time_range: str
    data_sources: list[str]
    opening_summary: str
    sections: list[ReportDocumentSection] = field(default_factory=list)
    action_recommendations: list[str] = field(default_factory=list)
    data_boundaries: list[str] = field(default_factory=list)
    technical_appendix: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["sections"] = [section.to_dict() for section in self.sections]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportDocument":
        return cls(
            title=str(data.get("title") or ""),
            time_range=str(data.get("time_range") or ""),
            data_sources=[str(source) for source in data.get("data_sources", [])],
            opening_summary=str(data.get("opening_summary") or ""),
            sections=[
                ReportDocumentSection.from_dict(section)
                for section in data.get("sections", [])
                if isinstance(section, dict)
            ],
            action_recommendations=[
                str(item) for item in data.get("action_recommendations", [])
            ],
            data_boundaries=[str(item) for item in data.get("data_boundaries", [])],
            technical_appendix=dict(data.get("technical_appendix", {})),
        )


@dataclass
class ReportRecord:
    report_id: str
    workspace_id: str
    report_type: str
    report_goal: str
    title: str
    status: str = "draft"
    plan: ReportPlan | None = None
    evidence_pack: ReportEvidencePack | None = None
    document: ReportDocument | None = None
    validation: ReportValidationResult | None = None
    executive_summary: list[str] = field(default_factory=list)
    key_findings: list[str] = field(default_factory=list)
    action_priorities: list[str] = field(default_factory=list)
    chart_and_evidence: list[str] = field(default_factory=list)
    risks_and_limits: list[str] = field(default_factory=list)
    sections: list[dict[str, Any]] = field(default_factory=list)
    markdown_path: str = ""
    json_path: str = ""
    trace_path: str = ""
    artifact_dir: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    provider_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["plan"] = self.plan.to_dict() if self.plan else None
        data["evidence_pack"] = (
            self.evidence_pack.to_dict() if self.evidence_pack else None
        )
        data["document"] = self.document.to_dict() if self.document else None
        data["validation"] = self.validation.to_dict() if self.validation else None
        data["sections"] = [dict(section) for section in self.sections]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportRecord":
        plan = data.get("plan") if isinstance(data.get("plan"), dict) else None
        evidence_pack = (
            data.get("evidence_pack")
            if isinstance(data.get("evidence_pack"), dict)
            else None
        )
        document = data.get("document") if isinstance(data.get("document"), dict) else None
        validation = (
            data.get("validation") if isinstance(data.get("validation"), dict) else None
        )
        return cls(
            report_id=str(data["report_id"]),
            workspace_id=str(data["workspace_id"]),
            report_type=str(data["report_type"]),
            report_goal=str(data.get("report_goal", "")),
            title=str(data.get("title", data["report_id"])),
            status=str(data.get("status", "draft")),
            plan=ReportPlan.from_dict(plan) if plan else None,
            evidence_pack=ReportEvidencePack.from_dict(evidence_pack)
            if evidence_pack
            else None,
            document=ReportDocument.from_dict(document) if document else None,
            validation=ReportValidationResult.from_dict(validation)
            if validation
            else None,
            executive_summary=[str(item) for item in data.get("executive_summary", [])],
            key_findings=[str(item) for item in data.get("key_findings", [])],
            action_priorities=[str(item) for item in data.get("action_priorities", [])],
            chart_and_evidence=[str(item) for item in data.get("chart_and_evidence", [])],
            risks_and_limits=[str(item) for item in data.get("risks_and_limits", [])],
            sections=[
                dict(section)
                for section in data.get("sections", [])
                if isinstance(section, dict)
            ],
            markdown_path=str(data.get("markdown_path", "")),
            json_path=str(data.get("json_path", "")),
            trace_path=str(data.get("trace_path", "")),
            artifact_dir=str(data.get("artifact_dir", "")),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
            provider_metadata=dict(data.get("provider_metadata", {})),
        )
