from __future__ import annotations

from typing import Any


PRODUCT_RESULT_VERSION = "p16.v1"

LEGACY_CHART_ARTIFACT_FIELDS = (
    "title",
    "path",
    "url",
    "rendering_status",
    "unit",
    "value_label",
    "business_annotation",
)

P30_CHART_ARTIFACT_OPTIONAL_FIELDS = (
    "artifact_id",
    "renderer",
    "chart_type",
    "chart_spec",
    "echarts_option",
    "image_path",
    "image_url",
    "evidence_refs",
    "source",
    "data_row_count",
    "skip_reason",
    "failure_reason",
    "chart_input_source",
)

CHART_ARTIFACT_FIELDS = LEGACY_CHART_ARTIFACT_FIELDS + P30_CHART_ARTIFACT_OPTIONAL_FIELDS


def empty_question_thread() -> dict[str, Any]:
    return {
        "thread_id": "",
        "original_question": "",
        "system_understanding": "",
        "clarification_question": "",
        "clarification_answer": "",
        "resolved_question": "",
        "status": "",
        "turns": [],
        "current_business_lens": {},
        "evidence_refs": [],
        "answer_summary": "",
        "pending_clarification": None,
        "latest_status": "",
        "latest_resolved_question": "",
    }


def empty_business_answer() -> dict[str, Any]:
    return {
        "headline": "",
        "direct_answer": "",
        "why": "",
        "evidence_bullets": [],
        "recommendations": [],
        "caveats": [],
        "confidence": "medium",
    }


def empty_evidence() -> dict[str, Any]:
    return {
        "table_preview": {"columns": [], "rows": []},
        "evidence_notes": [],
        "validation_status": "not_validated",
        "fact_payload": {},
    }


def empty_analysis_route() -> dict[str, Any]:
    return {
        "route": "standard_analysis",
        "reason": "",
        "confidence": "medium",
        "requires_full_chain": True,
        "fast_path_eligible": False,
        "disqualifiers": [],
    }


def empty_chart_artifact() -> dict[str, Any]:
    return {
        "title": "",
        "path": "",
        "url": "",
        "rendering_status": "not_rendered",
        "unit": "",
        "value_label": False,
        "business_annotation": "",
    }


def empty_technical_details() -> dict[str, Any]:
    return {
        "sql": "",
        "raw_rows": [],
        "fact_payload": {},
        "trace_path": "",
        "provider_metadata": {},
        "validation_logs": [],
        "debug": {},
    }
