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
    time_range: Any = field(default_factory=dict)
    metrics: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)
    group_by: list[str] = field(default_factory=list)
    comparison_scope: dict[str, Any] = field(default_factory=dict)
    calculation_type: str = ""
    missing_evidence: list[str] = field(default_factory=list)

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
            time_range=data.get("time_range") if isinstance(data.get("time_range"), dict) else {},
            metrics=[str(item) for item in data.get("metrics", [])],
            dimensions=[str(item) for item in data.get("dimensions", [])],
            filters=[str(item) for item in data.get("filters", [])],
            group_by=[str(item) for item in data.get("group_by", [])],
            comparison_scope=dict(data.get("comparison_scope") or {}),
            calculation_type=str(data.get("calculation_type") or ""),
            missing_evidence=[str(item) for item in data.get("missing_evidence", [])],
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
    report_goal: str = ""
    data_sources: list[str] = field(default_factory=list)
    chapters: list[ReportChapterPlan] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)
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
            report_goal=str(data.get("report_goal") or ""),
            data_sources=[str(source) for source in data.get("data_sources", [])],
            chapters=[
                ReportChapterPlan.from_dict(chapter)
                for chapter in data.get("chapters", [])
                if isinstance(chapter, dict)
            ],
            missing_slots=[str(item) for item in data.get("missing_slots", [])],
            clarification_questions=[
                str(item) for item in data.get("clarification_questions", [])
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
    artifact_id: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    ledger_metric_ids: list[str] = field(default_factory=list)

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
            artifact_id=str(data.get("artifact_id") or ""),
            evidence_ids=[str(item) for item in data.get("evidence_ids", [])],
            ledger_metric_ids=[str(item) for item in data.get("ledger_metric_ids", [])],
        )


@dataclass
class ReportLedgerItem:
    evidence_id: str
    label: str
    display_value: str
    value: Any = None
    unit: str = ""
    chapter_id: str = ""
    source_table: str = ""
    source_evidence: str = ""
    formula: str = ""
    calculation_note: str = ""
    source_values: list[str] = field(default_factory=list)
    claim_phrases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportLedgerItem":
        return cls(
            evidence_id=str(data.get("evidence_id") or ""),
            label=str(data.get("label") or ""),
            display_value=str(data.get("display_value") or ""),
            value=data.get("value"),
            unit=str(data.get("unit") or ""),
            chapter_id=str(data.get("chapter_id") or ""),
            source_table=str(data.get("source_table") or ""),
            source_evidence=str(data.get("source_evidence") or ""),
            formula=str(data.get("formula") or ""),
            calculation_note=str(data.get("calculation_note") or ""),
            source_values=[str(item) for item in data.get("source_values", [])],
            claim_phrases=[str(item) for item in data.get("claim_phrases", [])],
        )


@dataclass
class ReportChapterCoverage:
    chapter_id: str
    coverage: str
    available_evidence: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    allowed_claims: list[str] = field(default_factory=list)
    blocked_claims: list[str] = field(default_factory=list)
    data_boundaries: list[str] = field(default_factory=list)
    title: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportChapterCoverage":
        return cls(
            chapter_id=str(data.get("chapter_id") or ""),
            coverage=str(data.get("coverage") or "missing"),
            available_evidence=[str(item) for item in data.get("available_evidence", [])],
            missing_evidence=[str(item) for item in data.get("missing_evidence", [])],
            allowed_claims=[str(item) for item in data.get("allowed_claims", [])],
            blocked_claims=[str(item) for item in data.get("blocked_claims", [])],
            data_boundaries=[str(item) for item in data.get("data_boundaries", [])],
            title=str(data.get("title") or ""),
        )


@dataclass
class EvidenceLedger:
    ledger_version: str = "p23.report_ledger.v1"
    facts: list[ReportLedgerItem] = field(default_factory=list)
    derived_metrics: list[ReportLedgerItem] = field(default_factory=list)
    chapter_coverages: list[ReportChapterCoverage] = field(default_factory=list)
    recommendation_context: list[dict[str, Any]] = field(default_factory=list)
    data_boundaries: list[str] = field(default_factory=list)
    technical_refs: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["facts"] = [fact.to_dict() for fact in self.facts]
        data["derived_metrics"] = [metric.to_dict() for metric in self.derived_metrics]
        data["chapter_coverages"] = [
            coverage.to_dict() for coverage in self.chapter_coverages
        ]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceLedger":
        return cls(
            ledger_version=str(data.get("ledger_version") or "p23.report_ledger.v1"),
            facts=[
                ReportLedgerItem.from_dict(item)
                for item in data.get("facts", [])
                if isinstance(item, dict)
            ],
            derived_metrics=[
                ReportLedgerItem.from_dict(item)
                for item in data.get("derived_metrics", [])
                if isinstance(item, dict)
            ],
            chapter_coverages=[
                ReportChapterCoverage.from_dict(item)
                for item in data.get("chapter_coverages", [])
                if isinstance(item, dict)
            ],
            recommendation_context=[
                dict(item)
                for item in data.get("recommendation_context", [])
                if isinstance(item, dict)
            ],
            data_boundaries=[str(item) for item in data.get("data_boundaries", [])],
            technical_refs=[
                dict(item)
                for item in data.get("technical_refs", [])
                if isinstance(item, dict)
            ],
        )


@dataclass
class ReportEvidencePack:
    facts: list[ReportEvidenceFact] = field(default_factory=list)
    tables: list[ReportEvidenceTable] = field(default_factory=list)
    charts: list[ReportEvidenceChart] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data_limits: list[str] = field(default_factory=list)
    evidence_payloads: list[dict[str, Any]] = field(default_factory=list)
    ledger: EvidenceLedger | None = None
    technical_details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["facts"] = [fact.to_dict() for fact in self.facts]
        data["tables"] = [table.to_dict() for table in self.tables]
        data["charts"] = [chart.to_dict() for chart in self.charts]
        data["ledger"] = self.ledger.to_dict() if self.ledger else None
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
            ledger=EvidenceLedger.from_dict(data["ledger"])
            if isinstance(data.get("ledger"), dict)
            else None,
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
class ReportArtifactRecord:
    artifact_id: str
    artifact_type: str
    title: str
    relative_path: str = ""
    download_url: str = ""
    source: str = "local_renderer"
    evidence_ids: list[str] = field(default_factory=list)
    ledger_metric_ids: list[str] = field(default_factory=list)
    chart_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    status: str = "completed"
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportArtifactRecord":
        return cls(
            artifact_id=str(data.get("artifact_id") or ""),
            artifact_type=str(data.get("artifact_type") or ""),
            title=str(data.get("title") or ""),
            relative_path=str(data.get("relative_path") or ""),
            download_url=str(data.get("download_url") or ""),
            source=str(data.get("source") or "local_renderer"),
            evidence_ids=[str(item) for item in data.get("evidence_ids", [])],
            ledger_metric_ids=[str(item) for item in data.get("ledger_metric_ids", [])],
            chart_ids=[str(item) for item in data.get("chart_ids", [])],
            created_at=str(data.get("created_at") or utc_now_iso()),
            status=str(data.get("status") or "completed"),
            error=str(data.get("error") or ""),
        )


@dataclass
class ReportToolCallRecord:
    tool_call_id: str
    tool_name: str
    input_summary: str
    referenced_evidence_ids: list[str] = field(default_factory=list)
    output_artifact_ids: list[str] = field(default_factory=list)
    status: str = "completed"
    error: str = ""
    started_at: str = field(default_factory=utc_now_iso)
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data["completed_at"]:
            data["completed_at"] = data["started_at"]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportToolCallRecord":
        return cls(
            tool_call_id=str(data.get("tool_call_id") or ""),
            tool_name=str(data.get("tool_name") or ""),
            input_summary=str(data.get("input_summary") or ""),
            referenced_evidence_ids=[
                str(item) for item in data.get("referenced_evidence_ids", [])
            ],
            output_artifact_ids=[
                str(item) for item in data.get("output_artifact_ids", [])
            ],
            status=str(data.get("status") or "completed"),
            error=str(data.get("error") or ""),
            started_at=str(data.get("started_at") or utc_now_iso()),
            completed_at=str(data.get("completed_at") or ""),
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
    markdown_path: str = ""
    json_path: str = ""
    trace_path: str = ""
    artifact_dir: str = ""
    artifacts: list[ReportArtifactRecord] = field(default_factory=list)
    tool_calls: list[ReportToolCallRecord] = field(default_factory=list)
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
        data["artifacts"] = [artifact.to_dict() for artifact in self.artifacts]
        data["tool_calls"] = [tool_call.to_dict() for tool_call in self.tool_calls]
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
            markdown_path=str(data.get("markdown_path", "")),
            json_path=str(data.get("json_path", "")),
            trace_path=str(data.get("trace_path", "")),
            artifact_dir=str(data.get("artifact_dir", "")),
            artifacts=[
                ReportArtifactRecord.from_dict(item)
                for item in data.get("artifacts", [])
                if isinstance(item, dict)
            ],
            tool_calls=[
                ReportToolCallRecord.from_dict(item)
                for item in data.get("tool_calls", [])
                if isinstance(item, dict)
            ],
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
            provider_metadata=dict(data.get("provider_metadata", {})),
        )
