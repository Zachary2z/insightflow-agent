from __future__ import annotations

from typing import Any


PRODUCT_RESULT_VERSION = "p16.v1"


def empty_question_thread() -> dict[str, Any]:
    return {
        "original_question": "",
        "system_understanding": "",
        "clarification_question": "",
        "clarification_answer": "",
        "resolved_question": "",
        "pending_run_id": "",
        "status": "",
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
        "trace_path": "",
        "provider_metadata": {},
        "validation_logs": [],
        "debug": {},
    }
