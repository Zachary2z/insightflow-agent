from __future__ import annotations

from typing import Any


SPEC_FIELDS = (
    "chart_type",
    "title",
    "x",
    "y",
    "y_secondary",
    "series",
    "required_columns",
    "explanation_basis",
    "provider_called",
    "fallback_used",
    "prompt_id",
    "validation_error",
    "provider_error",
)


def normalize_chart_spec(spec: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "success": bool(spec.get("success", True)),
        "source": str(spec.get("source", "deterministic") or "deterministic"),
        "chart_type": str(spec.get("chart_type", "")).strip().lower(),
        "title": str(spec.get("title", "")).strip(),
        "x": str(spec.get("x", "")).strip(),
        "y": str(spec.get("y", "")).strip(),
        "y_secondary": str(spec.get("y_secondary", "") or "").strip(),
        "series": str(spec.get("series", "") or "").strip(),
        "required_columns": [str(column).strip() for column in spec.get("required_columns", []) if str(column).strip()],
        "explanation_basis": [
            str(item).strip()
            for item in spec.get("explanation_basis", ["supported_findings"])
            if str(item).strip()
        ],
        "provider_called": bool(spec.get("provider_called", False)),
        "fallback_used": bool(spec.get("fallback_used", False)),
        "prompt_id": str(spec.get("prompt_id", "") or "").strip(),
        "validation_error": str(spec.get("validation_error", "") or ""),
        "provider_error": str(spec.get("provider_error", "") or ""),
    }
    for field in ("run_id", "prompt_version", "model", "usage", "latency_ms"):
        if field in spec:
            normalized[field] = spec[field]
    return normalized
