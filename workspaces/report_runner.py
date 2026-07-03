from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workspaces.models import utc_now_iso
from workspaces.profiler import profile_workspace_database
from workspaces.report_composer import compose_report_document
from workspaces.report_evidence import collect_report_evidence
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
    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )
    document = compose_report_document(
        plan=plan,
        evidence_pack=evidence_pack,
        provider=_report_composer_provider(providers),
    )
    validation = validate_report_document(
        document=document,
        plan=plan,
        evidence_pack=evidence_pack,
    )
    document.technical_appendix = {
        "plan": plan.to_dict(),
        "evidence_pack": evidence_pack.to_dict(),
        "validation": validation.to_dict(),
        "generation_steps": ["规划报告", "整理证据", "撰写正文", "校验证据", "渲染保存"],
    }

    report_store = WorkspaceReportStore(store)
    report = report_store.create_report_record(
        workspace_id=workspace_id,
        report_type=report_type,
        report_goal=report_goal.strip(),
        title=plan.title,
        status="running",
    )
    report.title = plan.title
    report.status = "completed" if validation.status == "passed" else "partial"
    report.plan = plan
    report.evidence_pack = evidence_pack
    report.document = document
    report.validation = validation
    report.executive_summary = [document.opening_summary]
    report.key_findings = [section.body for section in document.sections[:3]]
    report.action_priorities = list(document.action_recommendations)
    report.chart_and_evidence = _document_evidence_summary(evidence_pack)
    report.risks_and_limits = list(document.data_boundaries)
    report.sections = []
    report.provider_metadata = {
        "generation_flow": "evidence_driven_report_center",
        "provider_supplied": bool(providers),
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
            },
            {"event": "report_document_composed", "section_count": len(document.sections)},
            {"event": "report_validated", "status": validation.status},
        ],
    )

    return {
        "success": saved.status == "completed",
        "workspace_id": workspace_id,
        "report_id": saved.report_id,
        "report": saved.to_dict(),
    }


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


def _document_evidence_summary(evidence_pack: Any) -> list[str]:
    if evidence_pack.charts:
        return [chart.title for chart in evidence_pack.charts]
    return ["当前尚未生成图表；本报告先基于工作区数据画像和结构化证据阅读。"]


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
