from __future__ import annotations

import json
import re
from typing import Any

from workspaces.product_models import (
    PRODUCT_RESULT_VERSION,
    empty_business_answer,
    empty_chart_artifact,
    empty_evidence,
    empty_question_thread,
    empty_technical_details,
)


def build_product_analysis_result(raw: dict[str, Any], *, workspace_id: str | None = None) -> dict[str, Any]:
    return {
        "version": PRODUCT_RESULT_VERSION,
        "workspace_id": workspace_id or raw.get("workspace_id") or "",
        "run_id": raw.get("run_id") or "",
        "status": raw.get("status", "unknown"),
        "question_thread": build_question_thread(raw),
        "business_answer": build_business_answer(raw),
        "evidence": build_evidence(raw.get("execution_result") or {}, raw.get("evidence_result") or {}),
        "chart_artifacts": build_chart_artifacts(raw),
        "report": raw.get("report_result") or None,
        "technical_details": build_technical_details(raw),
    }


def build_question_thread(raw: dict[str, Any]) -> dict[str, Any]:
    thread = empty_question_thread()
    original_question = raw.get("original_question") or raw.get("user_question") or raw.get("question") or ""
    thread.update(
        {
            "original_question": str(original_question),
            "system_understanding": _system_understanding(raw.get("question_understanding") or {}),
            "clarification_question": _first_text(
                raw.get("clarification_question"),
                raw.get("clarification_questions"),
                (raw.get("clarification_result") or {}).get("clarification_question"),
                (raw.get("clarification_result") or {}).get("questions"),
            ),
            "clarification_answer": str(raw.get("clarification_answer") or ""),
            "resolved_question": str(raw.get("resolved_question") or ""),
            "pending_run_id": str(raw.get("pending_run_id") or ""),
        }
    )
    return thread


def build_business_answer(raw: dict[str, Any]) -> dict[str, Any]:
    existing = raw.get("business_answer") if isinstance(raw.get("business_answer"), dict) else {}
    insight = raw.get("insight") if isinstance(raw.get("insight"), dict) else {}
    final_answer = str(existing.get("summary") or raw.get("final_answer") or "")
    answer = empty_business_answer()
    answer.update(
        {
            "headline": str(existing.get("headline") or _headline_from(final_answer)),
            "summary": final_answer,
            "recommendations": _list_of_text(existing.get("recommendations")),
            "next_actions": _list_of_text(existing.get("next_actions")),
            "caveats": _list_of_text(existing.get("caveats")),
            "confidence": str(existing.get("confidence") or "medium"),
            "source": str(existing.get("source") or insight.get("source") or ""),
            "quality_flags": _list_of_text(existing.get("quality_flags")),
        }
    )
    return answer


def build_evidence(execution_result: dict[str, Any], evidence_result: dict[str, Any]) -> dict[str, Any]:
    evidence = empty_evidence()
    evidence["table_preview"] = {
        "columns": list(execution_result.get("columns") or []),
        "rows": list(execution_result.get("rows") or [])[:20],
    }
    evidence["evidence_notes"] = _evidence_notes(evidence_result)
    evidence["validation_status"] = str(
        evidence_result.get("validation_status")
        or evidence_result.get("status")
        or ("validated" if evidence_result.get("success") else "not_validated")
    )
    return evidence


def build_chart_artifacts(raw: dict[str, Any]) -> list[dict[str, Any]]:
    visualization_trace = raw.get("visualization_trace") if isinstance(raw.get("visualization_trace"), dict) else {}
    delivery = (
        raw.get("visualization_delivery_result")
        if isinstance(raw.get("visualization_delivery_result"), dict)
        else {}
    )
    chart_spec = _chart_spec(raw, visualization_trace, delivery)
    title = str(chart_spec.get("title") or visualization_trace.get("title") or "Chart")
    unit = str(chart_spec.get("unit") or visualization_trace.get("unit") or "")
    annotation = str(
        chart_spec.get("business_annotation") or visualization_trace.get("business_annotation") or ""
    )

    paths = _unique_text(
        [
            visualization_trace.get("artifact_path"),
            visualization_trace.get("chart_path"),
            delivery.get("artifact_path"),
            delivery.get("chart_path"),
            raw.get("chart_path"),
            *(raw.get("chart_paths") or []),
        ]
    )
    artifacts: list[dict[str, Any]] = []
    for path in paths:
        artifact = empty_chart_artifact()
        artifact.update(
            {
                "title": title,
                "path": path,
                "url": "",
                "rendering_status": str(visualization_trace.get("rendering_status") or "rendered"),
                "unit": unit,
                "business_annotation": annotation,
            }
        )
        artifacts.append(artifact)
    return artifacts


def build_technical_details(raw: dict[str, Any]) -> dict[str, Any]:
    execution_result = raw.get("execution_result") if isinstance(raw.get("execution_result"), dict) else {}
    details = empty_technical_details()
    details.update(
        {
            "sql": str(raw.get("generated_sql") or ""),
            "raw_rows": list(execution_result.get("rows") or []),
            "trace_path": str(raw.get("trace_path") or ""),
            "provider_metadata": _provider_metadata(raw),
            "validation_logs": _validation_logs(raw),
            "debug": _debug_fields(raw),
        }
    )
    return details


def _system_understanding(question_understanding: dict[str, Any]) -> str:
    if not question_understanding:
        return ""
    reason = question_understanding.get("reason")
    if reason:
        return str(reason)
    intent = question_understanding.get("intent")
    if isinstance(intent, dict) and intent:
        parts = [f"{key}={value}" for key, value in intent.items() if value not in (None, "", [])]
        if parts:
            return ", ".join(parts)
    return json.dumps(question_understanding, ensure_ascii=False, sort_keys=True)


def _first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    return item
    return ""


def _headline_from(text: str) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return ""
    match = re.split(r"(?<=[。.!?？])\s*", normalized, maxsplit=1)
    return match[0][:120]


def _list_of_text(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _evidence_notes(evidence_result: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    for key in ("evidence_notes", "notes"):
        notes.extend(_list_of_text(evidence_result.get(key)))
    for finding in evidence_result.get("data_supported_findings") or []:
        if isinstance(finding, dict):
            claim = finding.get("claim") or finding.get("text")
            if claim:
                notes.append(str(claim))
        elif str(finding).strip():
            notes.append(str(finding))
    return list(dict.fromkeys(notes))


def _chart_spec(*values: dict[str, Any]) -> dict[str, Any]:
    for value in values:
        chart_spec = value.get("chart_spec") or value.get("spec")
        if isinstance(chart_spec, dict):
            return chart_spec
    return {}


def _unique_text(values: list[Any]) -> list[str]:
    paths: list[str] = []
    for value in values:
        if isinstance(value, str) and value.strip() and value not in paths:
            paths.append(value)
    return paths


def _provider_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "question_understanding",
        "clarification_result",
        "sql_planning",
        "llm_sql_enhancement",
        "analysis_plan",
        "insight",
        "claim_typing_result",
        "visualization_trace",
    )
    return {key: raw[key] for key in keys if isinstance(raw.get(key), dict)}


def _validation_logs(raw: dict[str, Any]) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    for key in ("review_result", "evidence_result", "trace_save_result"):
        value = raw.get(key)
        if isinstance(value, dict):
            logs.append({"name": key, "value": value})
    return logs


def _debug_fields(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "workspace_run_dir": raw.get("workspace_run_dir") or "",
        "status": raw.get("status") or "",
        "error_message": raw.get("error_message") or "",
    }
