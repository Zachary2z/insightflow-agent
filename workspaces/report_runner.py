from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workspaces.models import utc_now_iso
from workspaces.profiler import profile_workspace_database
from workspaces.report_chart_artifacts import build_report_chart_artifacts
from workspaces.report_composer import compose_report_document, repair_report_document
from workspaces.report_evidence import collect_report_evidence
from workspaces.report_ledger import build_evidence_ledger
from workspaces.report_models import (
    EvidenceLedger,
    ReportArtifactRecord,
    ReportDocument,
    ReportEvidencePack,
    ReportRecord,
    ReportToolCallRecord,
    ReportValidationResult,
)
from workspaces.report_planner import plan_workspace_report
from workspaces.report_store import WorkspaceReportStore
from workspaces.report_validator import validate_report_document
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


SUPPORTED_REPORT_TYPES = {"business_review", "channel_performance", "revenue_trend"}


def run_workspace_report(
    store: WorkspaceStore,
    workspace_id: str,
    report_type: str,
    report_goal: str,
    providers: dict | None = None,
) -> dict[str, Any]:
    if not report_goal or not report_goal.strip():
        raise ValueError("report_goal is required")
    if report_type not in SUPPORTED_REPORT_TYPES:
        raise ValueError(f"Unsupported report_type: {report_type}")

    workspace = store.get_workspace(workspace_id)
    profile = _ensure_profile(store, workspace)
    semantic_layer = _ensure_semantic_layer(store, workspace, profile)

    plan = plan_workspace_report(
        report_type=report_type,
        report_goal=report_goal.strip(),
        profile=profile,
        semantic_layer=semantic_layer,
    )
    report_store = WorkspaceReportStore(store)
    report = report_store.create_report_record(
        workspace_id=workspace_id,
        report_type=report_type,
        report_goal=report_goal.strip(),
        title=plan.title,
        status="running",
    )
    if plan.missing_slots:
        saved = _save_report_waiting_for_clarification(
            report_store=report_store,
            report=report,
            plan=plan,
        )
        _append_trace_events(
            Path(saved.trace_path),
            [
                {
                    "event": "report_waiting_for_clarification",
                    "missing_slots": list(plan.missing_slots),
                }
            ],
        )
        return {
            "success": False,
            "workspace_id": workspace_id,
            "report_id": saved.report_id,
            "report": saved.to_dict(),
        }
    artifact_dir = Path(report.artifact_dir)
    artifact_base_path = artifact_dir.relative_to(Path(workspace["root_path"])).as_posix()
    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
        artifact_dir=artifact_dir,
        artifact_base_path=artifact_base_path,
    )
    evidence_ledger = build_evidence_ledger(plan=plan, evidence_pack=evidence_pack)
    chart_artifacts, chart_artifact_trace_events = build_report_chart_artifacts(
        evidence_pack=evidence_pack,
        workspace_id=workspace_id,
    )
    composer_provider = _report_composer_provider(providers)
    document = compose_report_document(
        plan=plan,
        evidence_pack=evidence_pack,
        evidence_ledger=evidence_ledger,
        provider=composer_provider,
    )
    validation = validate_report_document(
        document=document,
        plan=plan,
        evidence_pack=evidence_pack,
        evidence_ledger=evidence_ledger,
    )
    repair_attempted = False
    fallback_to_deterministic_repair = False
    repair_claims: list[str] = []
    if validation.unsupported_claims:
        repair_attempted = True
        repair_claims = list(validation.unsupported_claims)
        document = repair_report_document(
            document=document,
            plan=plan,
            evidence_pack=evidence_pack,
            evidence_ledger=evidence_ledger,
            unsupported_claims=repair_claims,
            provider=composer_provider,
        )
        validation = validate_report_document(
            document=document,
            plan=plan,
            evidence_pack=evidence_pack,
            evidence_ledger=evidence_ledger,
        )
        if composer_provider is not None and validation.unsupported_claims:
            fallback_to_deterministic_repair = True
            repair_claims = list(dict.fromkeys([*repair_claims, *validation.unsupported_claims]))
            document = repair_report_document(
                document=document,
                plan=plan,
                evidence_pack=evidence_pack,
                evidence_ledger=evidence_ledger,
                unsupported_claims=list(validation.unsupported_claims),
                provider=None,
            )
            validation = validate_report_document(
                document=document,
                plan=plan,
                evidence_pack=evidence_pack,
                evidence_ledger=evidence_ledger,
            )
    if composer_provider is not None and validation.status != "passed":
        fallback_to_deterministic_repair = True
        document = compose_report_document(
            plan=plan,
            evidence_pack=evidence_pack,
            evidence_ledger=evidence_ledger,
            provider=None,
        )
        validation = validate_report_document(
            document=document,
            plan=plan,
            evidence_pack=evidence_pack,
            evidence_ledger=evidence_ledger,
        )
    report.title = plan.title
    report.status = "completed" if validation.status == "passed" else "partial"
    report.plan = plan
    report.evidence_pack = evidence_pack
    report.chart_artifacts = chart_artifacts
    report.document = document
    report.validation = validation
    document.technical_appendix = {
        "plan": plan.to_dict(),
        "evidence_ledger": evidence_ledger.to_dict(),
        "ledger_reference_summary": _ledger_reference_summary(evidence_ledger),
        "artifact_summary": _artifact_summary(report),
        "evidence_pack_summary": {
            "fact_count": len(evidence_pack.facts),
            "table_count": len(evidence_pack.tables),
            "chart_count": len(evidence_pack.charts),
        },
        "validation": validation.to_dict(),
        "repair": {
            "attempted": repair_attempted,
            "unsupported_claims": repair_claims,
            "fallback_to_deterministic": fallback_to_deterministic_repair,
        },
        "generation_steps": ["规划报告", "整理证据", "生成证据账本", "撰写正文", "校验证据", "必要时修复一次", "渲染保存"],
    }
    report.artifacts = _build_report_artifacts(
        report=report,
        workspace_root=Path(workspace["root_path"]),
        evidence_ledger=evidence_ledger,
    )
    report.tool_calls = _build_report_tool_calls(
        report=report,
        evidence_ledger=evidence_ledger,
    )
    document.technical_appendix["artifact_summary"] = _artifact_summary(report)
    report.provider_metadata = {
        "generation_flow": "ledger_backed_report_center",
        "provider_supplied": bool(providers),
        "repair_attempted": repair_attempted,
        "fallback_to_deterministic_repair": fallback_to_deterministic_repair,
    }
    saved = report_store.save_report(report, event_type="report_completed")
    _append_trace_events(
        Path(saved.trace_path),
        [
            {"event": "report_planned", "title": plan.title},
            {
                "event": "report_evidence_collected",
                "fact_count": len(evidence_pack.facts),
                "table_count": len(evidence_pack.tables),
                "chart_count": len(evidence_pack.charts),
                "chart_artifact_count": len(chart_artifacts),
            },
            *chart_artifact_trace_events,
            {
                "event": "report_evidence_ledger_built",
                "fact_count": len(evidence_ledger.facts),
                "derived_metric_count": len(evidence_ledger.derived_metrics),
                "coverage_count": len(evidence_ledger.chapter_coverages),
            },
            {"event": "report_document_composed", "section_count": len(document.sections)},
            {"event": "report_repaired", "attempted": repair_attempted},
            {"event": "report_validated", "status": validation.status},
        ],
    )

    return {
        "success": saved.status == "completed",
        "workspace_id": workspace_id,
        "report_id": saved.report_id,
        "report": saved.to_dict(),
    }


def _save_report_waiting_for_clarification(
    *,
    report_store: WorkspaceReportStore,
    report: ReportRecord,
    plan: Any,
) -> ReportRecord:
    message = " ".join(plan.clarification_questions) or "请补充报告所需信息后再生成。"
    report.title = plan.title
    report.status = "failed"
    report.plan = plan
    report.evidence_pack = ReportEvidencePack(
        warnings=[message],
        data_limits=[message],
        technical_details={"missing_slots": list(plan.missing_slots)},
    )
    report.document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=list(plan.data_sources),
        opening_summary=message,
        sections=[],
        action_recommendations=[],
        data_boundaries=[message],
        technical_appendix={
            "plan": plan.to_dict(),
            "generation_steps": ["规划报告", "发现缺少必要信息", "停止生成报告"],
        },
    )
    report.validation = ReportValidationResult(
        status="needs_clarification",
        warnings=[message],
        unsupported_claims=[],
    )
    report.provider_metadata = {
        "generation_flow": "ledger_backed_report_center",
        "provider_supplied": False,
        "requires_clarification": True,
        "missing_slots": list(plan.missing_slots),
    }
    return report_store.save_report(report, event_type="report_needs_clarification")


def _ensure_profile(store: WorkspaceStore, workspace: dict[str, Any]) -> dict[str, Any]:
    profile_path = Path(workspace["profile_path"])
    if profile_path.exists():
        return json.loads(profile_path.read_text(encoding="utf-8"))
    return profile_workspace_database(store, workspace["workspace_id"])


def _ensure_semantic_layer(
    store: WorkspaceStore,
    workspace: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    semantic_layer_path = Path(workspace["semantic_layer_path"])
    if not semantic_layer_path.exists():
        generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    if semantic_layer_path.exists():
        text = semantic_layer_path.read_text(encoding="utf-8")
        try:
            import yaml

            loaded = yaml.safe_load(text)
        except Exception:  # noqa: BLE001 - semantic draft may be JSON in old fixtures.
            loaded = json.loads(text)
        return loaded if isinstance(loaded, dict) else {}
    return {}


def _report_composer_provider(providers: dict | None) -> Any | None:
    if not isinstance(providers, dict):
        return None
    return providers.get("report_composer") or providers.get("composer")


def _build_report_artifacts(
    *,
    report: ReportRecord,
    workspace_root: Path,
    evidence_ledger: EvidenceLedger,
) -> list[ReportArtifactRecord]:
    artifacts: list[ReportArtifactRecord] = []
    if report.evidence_pack:
        for chart in report.evidence_pack.charts:
            if not (chart.path or chart.url):
                continue
            artifact_id = chart.artifact_id or f"artifact_chart_{chart.chart_id}"
            chart.artifact_id = artifact_id
            artifacts.append(
                ReportArtifactRecord(
                    artifact_id=artifact_id,
                    artifact_type="chart",
                    title=chart.title or "报告图表",
                    relative_path=chart.path,
                    download_url=chart.url or chart.image_url,
                    source="local_renderer",
                    evidence_ids=list(chart.evidence_ids),
                    ledger_metric_ids=list(chart.ledger_metric_ids),
                    chart_ids=[chart.chart_id] if chart.chart_id else [],
                    status="completed",
                    created_at=report.updated_at or report.created_at,
                )
            )

    report_evidence_ids = [item.evidence_id for item in evidence_ledger.facts]
    report_metric_ids = [item.evidence_id for item in evidence_ledger.derived_metrics]
    chart_ids = [
        chart.chart_id
        for chart in (report.evidence_pack.charts if report.evidence_pack else [])
        if chart.chart_id
    ]
    artifacts.extend(
        [
            ReportArtifactRecord(
                artifact_id=f"artifact_markdown_{report.report_id}",
                artifact_type="markdown_report",
                title="Markdown 报告",
                relative_path=_relative_to_workspace(report.markdown_path, workspace_root),
                download_url=f"/api/workspaces/{report.workspace_id}/reports/{report.report_id}/download",
                source="report_markdown",
                evidence_ids=report_evidence_ids,
                ledger_metric_ids=report_metric_ids,
                chart_ids=chart_ids,
                status="completed",
                created_at=report.updated_at or report.created_at,
            ),
            ReportArtifactRecord(
                artifact_id=f"artifact_document_{report.report_id}",
                artifact_type="report_document",
                title="报告文档记录",
                relative_path=_relative_to_workspace(report.json_path, workspace_root),
                source="report_markdown",
                evidence_ids=report_evidence_ids,
                ledger_metric_ids=report_metric_ids,
                chart_ids=chart_ids,
                status="completed",
                created_at=report.updated_at or report.created_at,
            ),
        ]
    )
    return artifacts


def _build_report_tool_calls(
    *,
    report: ReportRecord,
    evidence_ledger: EvidenceLedger,
) -> list[ReportToolCallRecord]:
    calls: list[ReportToolCallRecord] = []
    chart_artifacts = {
        artifact.artifact_id: artifact
        for artifact in report.artifacts
        if artifact.artifact_type == "chart"
    }
    for artifact in chart_artifacts.values():
        evidence_ids = [*artifact.evidence_ids, *artifact.ledger_metric_ids]
        calls.append(
            ReportToolCallRecord(
                tool_call_id=f"tool_call_chart_{artifact.chart_ids[0] if artifact.chart_ids else artifact.artifact_id}",
                tool_name="local_chart_renderer",
                input_summary=f"渲染图表：{artifact.title}",
                referenced_evidence_ids=evidence_ids,
                output_artifact_ids=[artifact.artifact_id],
                status=artifact.status,
                error=artifact.error,
                started_at=report.updated_at or report.created_at,
                completed_at=report.updated_at or report.created_at,
            )
        )

    report_artifact_ids = [
        artifact.artifact_id
        for artifact in report.artifacts
        if artifact.artifact_type in {"markdown_report", "report_document"}
    ]
    if report_artifact_ids:
        calls.append(
            ReportToolCallRecord(
                tool_call_id=f"tool_call_markdown_{report.report_id}",
                tool_name="report_markdown_renderer",
                input_summary=f"渲染 Markdown 报告：{report.title}",
                referenced_evidence_ids=[
                    item.evidence_id
                    for item in [*evidence_ledger.facts, *evidence_ledger.derived_metrics]
                ],
                output_artifact_ids=report_artifact_ids,
                status="completed",
                started_at=report.updated_at or report.created_at,
                completed_at=report.updated_at or report.created_at,
            )
        )
    return calls


def _ledger_reference_summary(evidence_ledger: EvidenceLedger) -> dict[str, Any]:
    return {
        "evidence_ids": [item.evidence_id for item in evidence_ledger.facts],
        "ledger_metric_ids": [item.evidence_id for item in evidence_ledger.derived_metrics],
        "fact_count": len(evidence_ledger.facts),
        "derived_metric_count": len(evidence_ledger.derived_metrics),
    }


def _artifact_summary(report: ReportRecord) -> dict[str, Any]:
    artifacts = list(report.artifacts)
    return {
        "artifact_count": len(artifacts),
        "chart_count": sum(1 for artifact in artifacts if artifact.artifact_type == "chart"),
        "report_artifacts": [
            artifact.title
            for artifact in artifacts
            if artifact.artifact_type in {"markdown_report", "report_document"}
        ],
        "tool_call_count": len(report.tool_calls),
    }


def _relative_to_workspace(path_value: str, workspace_root: Path) -> str:
    if not path_value:
        return ""
    path = Path(path_value)
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _append_trace_events(trace_path: Path, events: list[dict[str, Any]]) -> None:
    existing_events = []
    if trace_path.exists():
        existing = json.loads(trace_path.read_text(encoding="utf-8"))
        existing_events = list(existing.get("events", []))
    for event in events:
        event.setdefault("created_at", utc_now_iso())
        existing_events.append(event)
    trace_path.write_text(
        json.dumps(
            {
                "events": existing_events,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
