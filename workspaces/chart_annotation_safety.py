from __future__ import annotations

import re
from typing import Any


def safe_chart_annotation(
    *,
    annotation: str,
    business_answer: dict[str, Any],
    execution_result: dict[str, Any],
) -> str:
    """Return displayable chart annotation text without internal runtime leaks."""

    del business_answer, execution_result
    text = _clean_text(annotation)
    if _contains_internal_leak(text):
        return ""
    return text


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return " ".join(text.split())


def _contains_internal_leak(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|PRAGMA)\b",
            str(text or ""),
            flags=re.IGNORECASE,
        )
    ) or any(
        marker in str(text or "").lower()
        for marker in (
            "task_id",
            "task_purpose",
            "trace_id",
            "trace_path",
            "provider_metadata",
            "raw_rows",
            "prompt_id",
            "prompt_version",
            "latency_ms",
            "completion_tokens",
            "prompt_tokens",
            "corefact",
            "explanationsupport",
        )
    )


__all__ = ["safe_chart_annotation"]
