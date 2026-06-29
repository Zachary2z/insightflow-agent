from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workspaces.product_result_builder import build_product_analysis_result
from workspaces.store import WorkspaceStore


class RunNotFoundError(FileNotFoundError):
    pass


_SAFE_RUN_ID = re.compile(r"^run_[A-Za-z0-9_-]+$")
_SCHEMA_MISMATCH_MARKERS = (
    "unknown table",
    "unknown column",
    "no such table",
    "no such column",
    "missing table",
    "missing column",
    "不存在的表",
    "不存在的字段",
)
_SCHEMA_MISMATCH_FAILURE = "系统尝试使用当前工作区中不存在的表或字段，因此没有执行查询。"


class WorkspaceRunStore:
    def __init__(self, workspace_store: WorkspaceStore):
        self.workspace_store = workspace_store

    def list_runs(self, workspace_id: str) -> list[dict[str, Any]]:
        workspace_root = self._workspace_root(workspace_id)
        runs_dir = self._runs_dir(workspace_id)
        if not runs_dir.exists():
            return []

        summaries = []
        for path in sorted(runs_dir.glob("run_*/run_*.json")):
            if not self._is_safe_run_file(path, workspace_root):
                continue
            try:
                raw = self._read_run_payload(path)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            summaries.append(self._build_summary(raw, path, workspace_id, workspace_root))
        return sorted(
            summaries,
            key=lambda summary: (summary.get("_sort_time") or "", summary.get("run_id") or ""),
            reverse=True,
        )

    def load_run_response(self, workspace_id: str, run_id: str) -> dict[str, Any]:
        self._validate_run_id(run_id)
        workspace_root = self._workspace_root(workspace_id)
        path = self._run_path(workspace_id, run_id)
        if not self._is_safe_run_file(path, workspace_root) or not path.exists():
            raise RunNotFoundError(f"Run not found: {run_id}")

        try:
            raw = self._read_run_payload(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise RunNotFoundError(f"Run not found: {run_id}") from exc

        result = dict(raw.get("result")) if isinstance(raw.get("result"), dict) else dict(raw)
        product_result = self._product_result(raw, result, workspace_id, workspace_root)
        result["product_result"] = product_result
        resolved_run_id = str(result.get("run_id") or raw.get("run_id") or run_id)
        status = str(result.get("status") or product_result.get("status") or raw.get("status") or "unknown")
        return {
            "success": status != "failed",
            "workspace_id": workspace_id,
            "run_id": resolved_run_id,
            "result": result,
            "product_result": product_result,
        }

    def _build_summary(
        self,
        raw: dict[str, Any],
        path: Path,
        workspace_id: str,
        workspace_root: Path,
    ) -> dict[str, Any]:
        result = raw.get("result") if isinstance(raw.get("result"), dict) else raw
        product_result = self._product_result(raw, result, workspace_id, workspace_root)
        status = str(result.get("status") or product_result.get("status") or raw.get("status") or "unknown")
        created_at = _text(result.get("created_at") or raw.get("created_at")) or None
        saved_at = _text(result.get("saved_at") or raw.get("saved_at")) or _mtime_iso(path)
        failure_reason = _failure_reason(result, product_result)
        headline = _headline(result, product_result, status, failure_reason)
        return {
            "run_id": str(result.get("run_id") or raw.get("run_id") or path.parent.name),
            "status": status,
            "question": _question(result, product_result),
            "headline": headline,
            "created_at": created_at,
            "saved_at": saved_at,
            "has_chart": _has_chart(result, product_result),
            "requires_clarification": _requires_clarification(result, product_result),
            "failure_reason": failure_reason,
            "_sort_time": saved_at or created_at or "",
        }

    def _product_result(
        self,
        raw: dict[str, Any],
        result: dict[str, Any],
        workspace_id: str,
        workspace_root: Path,
    ) -> dict[str, Any]:
        if isinstance(raw.get("product_result"), dict):
            return raw["product_result"]
        if isinstance(result.get("product_result"), dict):
            return result["product_result"]
        return build_product_analysis_result(result, workspace_id=workspace_id, workspace_root=workspace_root)

    def _run_path(self, workspace_id: str, run_id: str) -> Path:
        return self.workspace_store.resolve_workspace_path(workspace_id, Path("runs") / run_id / f"{run_id}.json")

    def _runs_dir(self, workspace_id: str) -> Path:
        return self.workspace_store.resolve_workspace_path(workspace_id, "runs")

    def _workspace_root(self, workspace_id: str) -> Path:
        self.workspace_store.get_workspace(workspace_id)
        return self.workspace_store.resolve_workspace_path(workspace_id, ".").resolve()

    def _read_run_payload(self, path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Run payload must be an object")
        return payload

    def _is_safe_run_file(self, path: Path, workspace_root: Path) -> bool:
        if not path.name.startswith("run_") or path.suffix != ".json":
            return False
        if not _SAFE_RUN_ID.fullmatch(path.stem) or not _SAFE_RUN_ID.fullmatch(path.parent.name):
            return False
        if path.stem != path.parent.name:
            return False
        try:
            resolved = path.resolve()
            return resolved == workspace_root or resolved.is_relative_to(workspace_root)
        except (OSError, ValueError):
            return False

    def _validate_run_id(self, run_id: str) -> None:
        if not _SAFE_RUN_ID.fullmatch(run_id):
            raise RunNotFoundError(f"Run not found: {run_id}")


def _question(result: dict[str, Any], product_result: dict[str, Any]) -> str:
    product_thread = product_result.get("question_thread") if isinstance(product_result.get("question_thread"), dict) else {}
    raw_thread = result.get("question_thread") if isinstance(result.get("question_thread"), dict) else {}
    return _first_text(
        product_thread.get("original_question"),
        raw_thread.get("original_question"),
        result.get("original_question"),
        result.get("user_question"),
    )


def _headline(
    result: dict[str, Any],
    product_result: dict[str, Any],
    status: str,
    failure_reason: str,
) -> str:
    product_answer = product_result.get("business_answer") if isinstance(product_result.get("business_answer"), dict) else {}
    raw_answer = result.get("business_answer") if isinstance(result.get("business_answer"), dict) else {}
    return _first_text(
        product_answer.get("headline"),
        raw_answer.get("headline"),
        failure_reason,
        status,
    )


def _failure_reason(result: dict[str, Any], product_result: dict[str, Any]) -> str:
    status = str(result.get("status") or product_result.get("status") or "")
    if status != "failed":
        return ""
    failure_texts = _failure_texts(result, product_result)
    if _has_schema_mismatch(failure_texts):
        return _SCHEMA_MISMATCH_FAILURE
    return _first_text(*failure_texts)


def _failure_texts(result: dict[str, Any], product_result: dict[str, Any]) -> list[str]:
    texts = []
    product_answer = product_result.get("business_answer") if isinstance(product_result.get("business_answer"), dict) else {}
    raw_answer = result.get("business_answer") if isinstance(result.get("business_answer"), dict) else {}
    texts.extend(
        [
            product_answer.get("summary"),
            product_answer.get("headline"),
            raw_answer.get("summary"),
            raw_answer.get("headline"),
        ]
    )
    texts.extend(
        [
            result.get("error_message"),
            result.get("final_answer"),
            result.get("failure_reason"),
        ]
    )
    review = result.get("review_result") if isinstance(result.get("review_result"), dict) else {}
    for key in ("reasons", "errors", "validation_errors"):
        value = review.get(key)
        if isinstance(value, list):
            texts.extend(value)
        else:
            texts.append(value)
    for event in result.get("trace") or []:
        if isinstance(event, dict) and event.get("node") == "fail_response_node":
            texts.append(event.get("tool_output_summary"))
            texts.append(event.get("error"))
    return [_text(value) for value in texts if _text(value)]


def _has_schema_mismatch(texts: list[str]) -> bool:
    combined = "\n".join(texts).lower()
    return any(marker in combined for marker in _SCHEMA_MISMATCH_MARKERS)


def _has_chart(result: dict[str, Any], product_result: dict[str, Any]) -> bool:
    charts = product_result.get("chart_artifacts")
    if isinstance(charts, list) and any(isinstance(chart, dict) and (chart.get("path") or chart.get("url")) for chart in charts):
        return True
    if result.get("chart_path") or result.get("chart_paths"):
        return True
    visualization = result.get("visualization_trace") if isinstance(result.get("visualization_trace"), dict) else {}
    delivery = (
        result.get("visualization_delivery_result")
        if isinstance(result.get("visualization_delivery_result"), dict)
        else {}
    )
    return bool(
        visualization.get("artifact_path")
        or visualization.get("chart_path")
        or delivery.get("artifact_path")
        or delivery.get("chart_path")
    )


def _requires_clarification(result: dict[str, Any], product_result: dict[str, Any]) -> bool:
    product_thread = product_result.get("question_thread") if isinstance(product_result.get("question_thread"), dict) else {}
    raw_thread = result.get("question_thread") if isinstance(result.get("question_thread"), dict) else {}
    status = _first_text(
        product_result.get("status"),
        result.get("status"),
        product_thread.get("status"),
        raw_thread.get("status"),
    ).lower()
    if status == "waiting_for_clarification":
        return True
    if status in {"completed", "failed"}:
        return False
    clarification = result.get("clarification_result") if isinstance(result.get("clarification_result"), dict) else {}
    return clarification.get("requires_clarification") is True


def _first_text(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return " ".join(text.split())


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat().replace("+00:00", "Z")
