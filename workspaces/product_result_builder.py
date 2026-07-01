from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from workspaces.answer_evidence import business_field_label, business_field_labels
from workspaces.answer_consistency import apply_answer_consistency, safe_chart_annotation
from workspaces.product_models import (
    PRODUCT_RESULT_VERSION,
    empty_business_answer,
    empty_chart_artifact,
    empty_evidence,
    empty_question_thread,
    empty_technical_details,
)


BUSINESS_ANSWER_KEYS = {
    "headline",
    "direct_answer",
    "why",
    "evidence_bullets",
    "recommendations",
    "caveats",
    "confidence",
}


def build_product_analysis_result(
    raw: dict[str, Any],
    *,
    workspace_id: str | None = None,
    workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    resolved_workspace_id = workspace_id or raw.get("workspace_id") or ""
    resolved_workspace_root = workspace_root or raw.get("workspace_root") or _workspace_root_from_raw(raw)
    business_answer = build_business_answer(raw)
    return {
        "version": PRODUCT_RESULT_VERSION,
        "workspace_id": resolved_workspace_id,
        "run_id": raw.get("run_id") or "",
        "status": raw.get("status", "unknown"),
        "question_thread": build_question_thread(raw),
        "business_answer": business_answer,
        "evidence": build_evidence(raw.get("execution_result") or {}, raw.get("evidence_result") or {}),
        "chart_artifacts": build_chart_artifacts(
            raw,
            workspace_id=str(resolved_workspace_id),
            workspace_root=resolved_workspace_root,
            business_answer=business_answer,
        ),
        "report": raw.get("report_result") or None,
        "technical_details": build_technical_details(raw),
    }


def build_question_thread(raw: dict[str, Any]) -> dict[str, Any]:
    thread = empty_question_thread()
    original_question = raw.get("original_question") or raw.get("user_question") or raw.get("question") or ""
    question_understanding = raw.get("pending_question_understanding") or raw.get("question_understanding") or {}
    thread.update(
        {
            "original_question": str(original_question),
            "system_understanding": str(raw.get("system_understanding") or "")
            or _system_understanding(question_understanding, original_question=str(original_question)),
            "clarification_question": _first_text(
                raw.get("clarification_question"),
                raw.get("clarification_questions"),
                (raw.get("clarification_result") or {}).get("clarification_question"),
                (raw.get("clarification_result") or {}).get("questions"),
            ),
            "clarification_answer": str(raw.get("clarification_answer") or ""),
            "resolved_question": str(raw.get("resolved_question") or ""),
            "pending_run_id": str(raw.get("pending_run_id") or ""),
            "status": str(raw.get("question_thread_status") or raw.get("status") or ""),
        }
    )
    return thread


def build_business_answer(raw: dict[str, Any]) -> dict[str, Any]:
    if _is_sql_review_failure(raw):
        return _business_failure_answer(raw)

    existing = raw.get("business_answer") if isinstance(raw.get("business_answer"), dict) else {}
    user_question = str(raw.get("original_question") or raw.get("user_question") or raw.get("question") or "")
    chinese = _uses_chinese_business_answer(user_question)
    execution_result = raw.get("execution_result") if isinstance(raw.get("execution_result"), dict) else {}
    evidence_result = raw.get("evidence_result") if isinstance(raw.get("evidence_result"), dict) else {}

    if business_answer_is_usable(existing, user_question, execution_result, evidence_result):
        return apply_answer_consistency(
            user_question=user_question,
            business_answer=_normalize_business_answer(existing, chinese=chinese),
            execution_result=execution_result,
            evidence_result=evidence_result,
        )

    direct_answer, fallback_reason = _safe_direct_answer(raw, user_question, execution_result, chinese=chinese)
    weak_evidence = _has_weak_evidence(execution_result, evidence_result)
    unsafe_fallback = fallback_reason in {"unsafe_text", "language_mismatch"}
    evidence_bullets = _business_evidence_bullets(
        execution_result,
        evidence_result,
        user_question=user_question,
        chinese=chinese,
    )
    caveats = _business_caveats(
        [],
        fallback_reason=fallback_reason,
        weak_evidence=weak_evidence,
        execution_result=execution_result,
        chinese=chinese,
    )

    answer = _business_answer(
        headline=_headline_from(direct_answer),
        direct_answer=direct_answer,
        why=_business_why(direct_answer, evidence_bullets, execution_result, chinese=chinese),
        evidence_bullets=evidence_bullets,
        recommendations=[] if weak_evidence or unsafe_fallback else _business_recommendations(
            direct_answer,
            user_question=user_question,
            execution_result=execution_result,
            chinese=chinese,
        ),
        caveats=caveats,
        confidence="low" if weak_evidence or unsafe_fallback else "medium",
        chinese=chinese,
    )
    return apply_answer_consistency(
        user_question=user_question,
        business_answer=answer,
        execution_result=execution_result,
        evidence_result=evidence_result,
    )


def _business_failure_answer(raw: dict[str, Any]) -> dict[str, Any]:
    schema_mismatch = _is_schema_review_failure(raw)
    if schema_mismatch:
        return _business_answer(
            headline="当前数据无法支持这次查询",
            direct_answer="系统尝试使用当前工作区中不存在的表或字段，因此没有执行查询。",
            why="SQL 审核发现查询引用了当前数据中不存在的表或字段，系统已停止执行以避免给出不可靠结论。",
            evidence_bullets=[],
            recommendations=[
                "可以改问当前数据已包含的渠道、收入、订单、投放花费和 ROI。",
                "如果要分析商品、订单明细或产品维度，请先上传对应数据表。",
            ],
            caveats=["本轮没有执行未通过审核的 SQL。"],
            confidence="low",
        )

    return _business_answer(
        headline="本次查询未能安全执行",
        direct_answer="系统在执行前发现查询不符合当前数据或安全校验要求，因此已停止本轮分析。",
        why="这次分析没有通过 SQL 审核，继续执行可能产生错误或不安全的数据结果。",
        evidence_bullets=[],
        recommendations=["可以换一种更贴近当前数据表和字段的问题重新分析。"],
        caveats=["本轮没有执行未通过审核的 SQL。"],
        confidence="low",
    )


def _business_answer(
    *,
    headline: str,
    direct_answer: str,
    why: str,
    evidence_bullets: list[str],
    recommendations: list[str],
    caveats: list[str],
    confidence: str,
    chinese: bool = True,
) -> dict[str, Any]:
    answer = empty_business_answer()
    answer.update(
        {
            "headline": _clean_business_text(headline, chinese=chinese),
            "direct_answer": _clean_business_text(direct_answer, chinese=chinese),
            "why": _clean_business_text(why, chinese=chinese),
            "evidence_bullets": [
                _clean_business_text(item, chinese=chinese)
                for item in evidence_bullets
                if _clean_business_text(item, chinese=chinese)
            ],
            "recommendations": [
                _clean_business_text(item, chinese=chinese)
                for item in recommendations
                if _clean_business_text(item, chinese=chinese)
            ],
            "caveats": [
                _clean_business_text(item, chinese=chinese)
                for item in caveats
                if _clean_business_text(item, chinese=chinese)
            ],
            "confidence": confidence if confidence in {"low", "medium", "high"} else "medium",
        }
    )
    return answer


def business_answer_is_usable(
    existing: dict[str, Any],
    user_question: str,
    execution_result: dict[str, Any] | None = None,
    evidence_result: dict[str, Any] | None = None,
) -> bool:
    if not existing:
        return False
    if set(existing) != BUSINESS_ANSWER_KEYS:
        return False
    required_strings = ("headline", "direct_answer", "why")
    required_lists = ("evidence_bullets", "recommendations", "caveats")
    if any(not isinstance(existing.get(field), str) or not str(existing.get(field)).strip() for field in required_strings):
        return False
    if any(not isinstance(existing.get(field), list) for field in required_lists):
        return False
    if str(existing.get("confidence") or "") not in {"low", "medium", "high"}:
        return False

    combined = "\n".join(_business_answer_texts(existing))
    if _looks_like_raw_parameter_dump(combined) or _contains_technical_leak(combined):
        return False
    if _needs_chinese_response(user_question) and not _business_answer_fields_contain_cjk(existing):
        return False
    if execution_result is not None:
        weak_evidence = _has_weak_evidence(execution_result, evidence_result or {})
        if weak_evidence and _list_of_text(existing.get("recommendations")):
            return False
        if weak_evidence and not _list_of_text(existing.get("caveats")):
            return False
    return True


def _normalize_business_answer(existing: dict[str, Any], *, chinese: bool) -> dict[str, Any]:
    return _business_answer(
        headline=str(existing.get("headline") or ""),
        direct_answer=str(existing.get("direct_answer") or ""),
        why=str(existing.get("why") or ""),
        evidence_bullets=_list_of_text(existing.get("evidence_bullets")),
        recommendations=_list_of_text(existing.get("recommendations")),
        caveats=_list_of_text(existing.get("caveats")),
        confidence=str(existing.get("confidence") or "medium"),
        chinese=chinese,
    )


def _business_answer_texts(answer: dict[str, Any]) -> list[str]:
    return [
        str(answer.get("headline") or ""),
        str(answer.get("direct_answer") or ""),
        str(answer.get("why") or ""),
        *_list_of_text(answer.get("evidence_bullets")),
        *_list_of_text(answer.get("recommendations")),
        *_list_of_text(answer.get("caveats")),
    ]


def _business_answer_fields_contain_cjk(answer: dict[str, Any]) -> bool:
    for field in ("headline", "direct_answer", "why"):
        if not _contains_cjk(str(answer.get(field) or "")):
            return False
    for field in ("evidence_bullets", "recommendations", "caveats"):
        for item in _list_of_text(answer.get(field)):
            if not _contains_cjk(item):
                return False
    return True


def _safe_direct_answer(
    raw: dict[str, Any],
    user_question: str,
    execution_result: dict[str, Any],
    *,
    chinese: bool,
) -> tuple[str, str]:
    direct_answer = _candidate_direct_answer(raw)
    if not direct_answer and execution_result.get("success"):
        return _answer_from_evidence(user_question, execution_result, chinese=chinese), "missing_direct_answer"
    if _looks_like_raw_parameter_dump(direct_answer) or _contains_technical_leak(direct_answer):
        return _fallback_direct_answer(user_question, execution_result, chinese=chinese), "unsafe_text"
    if _needs_chinese_response(user_question) and direct_answer.strip() and not _contains_cjk(direct_answer):
        return _fallback_direct_answer(user_question, execution_result, chinese=chinese), "language_mismatch"
    return direct_answer, ""


def _fallback_direct_answer(user_question: str, execution_result: dict[str, Any], *, chinese: bool) -> str:
    if execution_result.get("success"):
        return _answer_from_evidence(user_question, execution_result, chinese=chinese)
    if not chinese:
        return "The query completed, but the model returned technical parameter-style content; use the evidence table and charts for this result."
    return "已完成查询，但模型返回了技术参数格式内容；请以证据表和图表为准查看本轮结果。"


def _candidate_direct_answer(raw: dict[str, Any]) -> str:
    for value in (
        raw.get("final_answer"),
        (raw.get("insight") or {}).get("final_answer") if isinstance(raw.get("insight"), dict) else "",
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _business_evidence_bullets(
    execution_result: dict[str, Any],
    evidence_result: dict[str, Any],
    *,
    user_question: str = "",
    chinese: bool = True,
    limit: int = 4,
) -> list[str]:
    notes = _evidence_notes(evidence_result)
    if notes and not _list_language_mismatches_question(notes, user_question):
        return notes[:limit]
    return _evidence_bullets_from_rows(execution_result, chinese=chinese, limit=limit)


def _list_language_mismatches_question(items: list[str], question: str) -> bool:
    return _needs_chinese_response(question) and any(not _contains_cjk(item) for item in items)


def _evidence_bullets_from_rows(execution_result: dict[str, Any], *, chinese: bool, limit: int = 4) -> list[str]:
    rows = list(execution_result.get("rows") or [])[:limit]
    columns = [str(column) for column in execution_result.get("columns") or []]
    bullets: list[str] = []
    for index, row in enumerate(rows, start=1):
        pairs = _row_pairs(row, columns)
        if pairs:
            summary = _business_pairs_text(pairs[:5], chinese=chinese)
            bullets.append(f"第 {index} 行：{summary}。" if chinese else f"Row {index}: {summary}.")
    return bullets


def _business_why(
    direct_answer: str,
    evidence_bullets: list[str],
    execution_result: dict[str, Any],
    *,
    chinese: bool,
) -> str:
    anchor = _evidence_anchor_sentence(execution_result, chinese=chinese)
    if anchor:
        return anchor
    if evidence_bullets:
        return "；".join(evidence_bullets[:2]) if chinese else " ".join(evidence_bullets[:2])
    if direct_answer:
        return "该结论来自本轮已通过校验的数据查询结果。" if chinese else "This conclusion comes from the validated query result."
    return ""


def _business_recommendations(
    direct_answer: str,
    *,
    user_question: str = "",
    execution_result: dict[str, Any] | None = None,
    chinese: bool,
) -> list[str]:
    if _looks_recommendation_like(direct_answer):
        return [direct_answer]
    supported = _supported_budget_recommendation(user_question, execution_result or {}, chinese=chinese)
    if supported:
        return [supported]
    return []


def _supported_budget_recommendation(user_question: str, execution_result: dict[str, Any], *, chinese: bool) -> str:
    if not _asks_for_budget_recommendation(user_question):
        return ""
    rows = execution_result.get("rows") or []
    if not rows:
        return ""
    columns = [str(column) for column in execution_result.get("columns") or []]
    pairs = _row_pairs(rows[0], columns)
    if not pairs:
        return ""
    channel = _first_matching_pair_value(pairs, ("channel", "渠道"))
    if not channel:
        return ""
    evidence = _business_pairs_text(pairs[:5], chinese=chinese)
    if chinese:
        return f"建议优先评估增加 {channel} 的预算，因为证据表第一行显示：{evidence}。"
    return f"Consider increasing budget for {channel}, supported by the first evidence row: {evidence}."


def _asks_for_budget_recommendation(question: str) -> bool:
    lowered = str(question or "").lower()
    markers = (
        "加预算",
        "预算",
        "投放",
        "加码",
        "增加",
        "should increase",
        "increase budget",
        "allocate budget",
        "budget",
    )
    return any(marker in lowered for marker in markers)


def _first_matching_pair_value(pairs: list[tuple[str, Any]], markers: tuple[str, ...]) -> str:
    for key, value in pairs:
        lowered_key = str(key).lower()
        if any(marker in lowered_key for marker in markers):
            text = str(value).strip()
            if text:
                return text
    return ""


def _business_caveats(
    existing_caveats: Any,
    *,
    fallback_reason: str,
    weak_evidence: bool,
    execution_result: dict[str, Any],
    chinese: bool,
) -> list[str]:
    caveats = _list_of_text(existing_caveats)
    if fallback_reason in {"unsafe_text", "language_mismatch"}:
        caveats.append(
            "模型原始回答包含参数格式内容，已从业务结论中移除。"
            if chinese
            else "The original model answer contained technical parameter-style content and was removed from the business answer."
        )
    elif fallback_reason == "missing_direct_answer":
        caveats.append(
            "模型未提供可直接展示的业务回答，已根据证据表重建。"
            if chinese
            else "The model did not provide a displayable business answer, so this was rebuilt from the evidence rows."
        )
    if weak_evidence:
        caveats.append(_weak_evidence_caveat(execution_result, chinese=chinese))
    return list(dict.fromkeys(caveats))


def _has_weak_evidence(execution_result: dict[str, Any], evidence_result: dict[str, Any]) -> bool:
    if not execution_result or execution_result.get("success") is False:
        return True
    if not execution_result.get("rows"):
        return True
    validation_status = str(evidence_result.get("validation_status") or evidence_result.get("status") or "").lower()
    if validation_status in {"failed", "not_validated", "rejected"} and not _evidence_notes(evidence_result):
        return True
    return False


def _weak_evidence_caveat(execution_result: dict[str, Any], *, chinese: bool) -> str:
    if not execution_result.get("rows"):
        return (
            "当前查询没有返回可验证的数据行，不能据此给出确定建议。"
            if chinese
            else "The query returned no verifiable data rows, so it cannot support a firm recommendation."
        )
    return (
        "当前证据未通过充分校验，建议只把本轮结果作为低置信度参考。"
        if chinese
        else "The current evidence was not fully validated, so treat this result as low-confidence context."
    )


def _evidence_anchor_sentence(execution_result: dict[str, Any], *, chinese: bool) -> str:
    rows = execution_result.get("rows") or []
    if not rows:
        return ""
    columns = [str(column) for column in execution_result.get("columns") or []]
    pairs = _row_pairs(rows[0], columns)
    if not pairs:
        return ""
    summary = _business_pairs_text(pairs[:5], chinese=chinese)
    return f"证据表第一行显示：{summary}。" if chinese else f"The first evidence row shows: {summary}."


def _row_pairs(row: Any, columns: list[str]) -> list[tuple[str, Any]]:
    if isinstance(row, dict):
        return [(str(key), value) for key, value in row.items() if str(key).strip()]
    if isinstance(row, (list, tuple)):
        return [
            (str(column), row[index])
            for index, column in enumerate(columns)
            if str(column).strip() and index < len(row)
        ]
    return []


def _business_pairs_text(pairs: list[tuple[str, Any]], *, chinese: bool) -> str:
    separator = "，" if chinese else ", "
    return separator.join(_business_pair_text(key, value, chinese=chinese) for key, value in pairs)


def _business_pair_text(key: Any, value: Any, *, chinese: bool) -> str:
    relation = " 为 " if chinese else " is "
    return f"{business_field_label(key, chinese=chinese)}{relation}{value}"


def _clean_business_text(text: Any, *, chinese: bool) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    value = re.sub(r"```sql\s*.*?```", "", value, flags=re.IGNORECASE | re.DOTALL).strip()
    value = re.sub(r"\b(?:SELECT|WITH)\b.+", "", value, flags=re.IGNORECASE | re.DOTALL).strip()
    value = re.sub(r"\b[A-Za-z_][\w. -]*\s*=\s*[^，,。\n]+(?:[,，]\s*)?", "", value).strip()
    value = _localize_common_field_names(value, chinese=chinese)
    return " ".join(value.split())


def _localize_common_field_names(text: str, *, chinese: bool) -> str:
    localized = text
    labels = business_field_labels(chinese=chinese)
    for raw_key, label in sorted(labels.items(), key=lambda item: len(item[0]), reverse=True):
        localized = re.sub(rf"\b{re.escape(raw_key)}\b", label, localized, flags=re.IGNORECASE)
    if not chinese:
        zh_to_en = {
            zh_label: labels[raw_key]
            for raw_key, zh_label in business_field_labels(chinese=True).items()
            if raw_key in labels
        }
        for zh_label, en_label in sorted(zh_to_en.items(), key=lambda item: len(item[0]), reverse=True):
            localized = localized.replace(zh_label, en_label)
    return localized


def _is_sql_review_failure(raw: dict[str, Any]) -> bool:
    if str(raw.get("status") or "").lower() != "failed":
        return False
    review = raw.get("review_result") if isinstance(raw.get("review_result"), dict) else {}
    if review and review.get("approved") is False:
        return True
    failure_text = "\n".join(
        str(raw.get(key) or "") for key in ("final_answer", "error_message", "failure_reason")
    ).lower()
    return "sql 审核未通过" in failure_text or "sql review" in failure_text


def _is_schema_review_failure(raw: dict[str, Any]) -> bool:
    markers = (
        "unknown table",
        "unknown column",
        "no such table",
        "no such column",
        "missing table",
        "missing column",
        "不存在的表",
        "不存在的字段",
    )
    combined = "\n".join(_review_failure_texts(raw)).lower()
    return any(marker in combined for marker in markers)


def _review_failure_texts(raw: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for key in ("final_answer", "error_message", "schema_repair_reason"):
        value = raw.get(key)
        if value:
            texts.append(str(value))
    for key in ("review_result", "schema_repair"):
        value = raw.get(key)
        if isinstance(value, dict):
            texts.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return texts


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


def build_chart_artifacts(
    raw: dict[str, Any],
    *,
    workspace_id: str = "",
    workspace_root: str | Path | None = None,
    business_answer: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    visualization_trace = raw.get("visualization_trace") if isinstance(raw.get("visualization_trace"), dict) else {}
    delivery = (
        raw.get("visualization_delivery_result")
        if isinstance(raw.get("visualization_delivery_result"), dict)
        else {}
    )
    decision = raw.get("visualization_decision") if isinstance(raw.get("visualization_decision"), dict) else {}
    chart_spec = _chart_spec(raw, visualization_trace, delivery, decision)
    title = str(chart_spec.get("title") or visualization_trace.get("title") or "Chart")
    unit = str(chart_spec.get("unit") or visualization_trace.get("unit") or "")
    value_label = bool(chart_spec.get("value_label") or visualization_trace.get("value_label") or False)
    annotation = str(
        chart_spec.get("business_annotation") or visualization_trace.get("business_annotation") or ""
    )
    safe_annotation = safe_chart_annotation(
        annotation=annotation,
        business_answer=business_answer or build_business_answer(raw),
        execution_result=raw.get("execution_result") if isinstance(raw.get("execution_result"), dict) else {},
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
        display_path, url = _artifact_path_and_url(
            path,
            workspace_id=workspace_id,
            workspace_root=workspace_root,
            artifact_url=str(visualization_trace.get("artifact_url") or delivery.get("artifact_url") or ""),
        )
        artifact = empty_chart_artifact()
        artifact.update(
            {
                "title": title,
                "path": display_path,
                "url": url,
                "rendering_status": str(visualization_trace.get("rendering_status") or "rendered"),
                "unit": unit,
                "value_label": value_label,
                "business_annotation": safe_annotation,
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


def _system_understanding(question_understanding: dict[str, Any], *, original_question: str = "") -> str:
    if not question_understanding:
        return ""
    reason = question_understanding.get("reason")
    if reason and not (_contains_cjk(original_question) and not _contains_cjk(str(reason))):
        return str(reason)
    intent = question_understanding.get("intent")
    if _contains_cjk(original_question) and isinstance(intent, dict) and intent:
        localized = _localized_system_understanding(intent)
        if localized:
            return localized
    if _contains_cjk(original_question) and reason:
        return "系统已识别：当前问题还需要补充更多分析条件。"
    if isinstance(intent, dict) and intent:
        parts = [f"{key}={value}" for key, value in intent.items() if value not in (None, "", [])]
        if parts:
            return ", ".join(parts)
    return json.dumps(question_understanding, ensure_ascii=False, sort_keys=True)


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(text or ""))


def _needs_chinese_response(question: str) -> bool:
    if not _contains_cjk(question):
        return False
    lowered = str(question or "").lower()
    return not any(marker in lowered for marker in ("用英文", "英文回答", "answer in english", "in english"))


def _uses_chinese_business_answer(question: str) -> bool:
    if not str(question or "").strip():
        return True
    return _needs_chinese_response(question)


def _answer_from_evidence(question: str, execution_result: dict[str, Any], *, chinese: bool) -> str:
    rows = execution_result.get("rows") or []
    safe_question = "" if _contains_technical_leak(question) else question
    if not rows:
        if chinese:
            suffix = f"原问题：{safe_question}" if safe_question else ""
            return f"已完成本轮查询，但证据表没有返回数据行。{suffix}"
        suffix = f" Original question: {safe_question}" if safe_question else ""
        return f"The query completed, but the evidence table returned no data rows.{suffix}"
    columns = list(execution_result.get("columns") or [])
    summary = f"已完成本轮查询，共返回 {len(rows)} 行结果。" if chinese else f"The query returned {len(rows)} row{'s' if len(rows) != 1 else ''}."
    first_row = rows[0]
    if isinstance(first_row, dict):
        pairs = list(first_row.items())
    elif isinstance(first_row, (list, tuple)):
        pairs = list(zip(columns, first_row, strict=False))
    else:
        pairs = []
    evidence = [
        _business_pair_text(column, value, chinese=chinese)
        for column, value in pairs[:5]
        if str(column).strip()
    ]
    if evidence:
        if chinese:
            summary += "证据表第一行显示：" + "，".join(evidence) + "。"
        else:
            summary += " The first evidence row shows: " + ", ".join(evidence) + "."
    if safe_question:
        summary += f"原问题：{safe_question}" if chinese else f" Original question: {safe_question}"
    return summary


def _localized_system_understanding(intent: dict[str, Any]) -> str:
    parts = []
    metric = _localized_intent_value(intent.get("metric"))
    dimension = _localized_intent_value(intent.get("dimension"))
    time_range = _localized_time_range(intent.get("time_range"))
    operation = _localized_intent_value(intent.get("operation"))
    if metric:
        parts.append(f"指标为{metric}")
    if dimension:
        parts.append(f"维度为{dimension}")
    if time_range:
        parts.append(f"时间范围为{time_range}")
    if operation:
        parts.append(f"分析目标为{operation}")
    if not parts:
        return ""
    return "系统已识别：" + "，".join(parts) + "。"


def _localized_intent_value(value: Any) -> str:
    text = str(value or "").strip()
    field_label = business_field_label(text, chinese=True)
    if field_label != text:
        return field_label
    mapping = {
        "comparison": "对比分析",
        "top_n": "排序分析",
        "summary": "汇总分析",
    }
    return mapping.get(text.lower(), text)


def _localized_time_range(value: Any) -> str:
    if isinstance(value, dict):
        raw_text = str(value.get("raw_text") or "").strip()
        if raw_text:
            return raw_text
        if value.get("type") == "last_n_days" and value.get("value"):
            return f"最近 {value['value']} 天"
        start = str(value.get("start") or "").strip()
        end = str(value.get("end") or "").strip()
        if start and end:
            return f"{start} 至 {end}"
    return str(value or "").strip()


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
    for index, char in enumerate(normalized):
        if char == "." and _is_decimal_point(normalized, index):
            continue
        if char in "。.!?？":
            return normalized[: index + 1][:120]
    return normalized[:120]


def _is_decimal_point(text: str, index: int) -> bool:
    return 0 < index < len(text) - 1 and text[index - 1].isdigit() and text[index + 1].isdigit()


def _looks_recommendation_like(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    recommendation_markers = (
        "建议",
        "推荐",
        "优先",
        "加大",
        "增加",
        "recommend",
        "prioritize",
        "should",
        "increase",
        "optimize",
        "balanced approach",
        "might be to",
    )
    return normalized.startswith(recommendation_markers) or any(marker in normalized for marker in recommendation_markers)


def _looks_like_raw_parameter_dump(text: str) -> bool:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return False
    dump_lines = 0
    for line in lines:
        stripped = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line)
        assignments = re.findall(r"\b[A-Za-z_][\w. -]*\s*=", stripped)
        if len(assignments) >= 2 or (assignments and "," in stripped):
            dump_lines += 1
    return dump_lines >= max(1, len(lines) // 2)


def _contains_technical_leak(text: str) -> bool:
    value = str(text or "")
    if re.search(r"\b(?:SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|PRAGMA)\b", value, re.IGNORECASE):
        return True
    lowered = value.lower()
    technical_markers = (
        "这是自动报告内部 section",
        "自动报告内部 section",
        "本节意图提示",
        "本节目的",
        "本节问题",
        "internal section",
        "trace_id",
        "trace id",
        "trace_path",
        "provider_metadata",
        "provider_called",
        "prompt_id",
        "prompt_version",
        "latency_ms",
        "completion_tokens",
        "prompt_tokens",
        "raw_rows",
    )
    return any(marker in lowered for marker in technical_markers)


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


def _workspace_root_from_raw(raw: dict[str, Any]) -> str:
    run_dir = raw.get("workspace_run_dir")
    if isinstance(run_dir, str) and run_dir:
        path = Path(run_dir)
        if path.name.startswith("run_") and path.parent.name == "runs":
            return str(path.parent.parent)
    return ""


def _artifact_path_and_url(
    path: str,
    *,
    workspace_id: str,
    workspace_root: str | Path | None,
    artifact_url: str = "",
) -> tuple[str, str]:
    relative_path = _workspace_relative_path(path, workspace_id=workspace_id, workspace_root=workspace_root)
    if relative_path and workspace_id:
        encoded = "/".join(quote(part) for part in relative_path.split("/"))
        return relative_path, f"/api/workspaces/{quote(workspace_id)}/artifacts/{encoded}"
    return path, artifact_url


def _workspace_relative_path(path: str, *, workspace_id: str, workspace_root: str | Path | None) -> str:
    path_text = str(path or "").strip()
    if not path_text:
        return ""
    candidate = Path(path_text)
    if candidate.is_absolute() and workspace_root:
        try:
            workspace_root_path = Path(workspace_root).resolve()
            resolved = candidate.resolve()
            if resolved == workspace_root_path:
                return ""
            if resolved.is_relative_to(workspace_root_path):
                return resolved.relative_to(workspace_root_path).as_posix()
        except (OSError, ValueError):
            return ""
    if not candidate.is_absolute():
        normalized = candidate.as_posix().lstrip("/")
        parts = [part for part in normalized.split("/") if part]
        if ".." in parts:
            return ""
        if workspace_id and len(parts) >= 2 and parts[0] == "workspaces" and parts[1] == workspace_id:
            parts = parts[2:]
        if parts and parts[0] in {"runs", "reports"}:
            return "/".join(parts)
        return ""
    return ""


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
        "schema_repair",
        "analysis_plan",
        "insight",
        "claim_typing_result",
        "visualization_trace",
    )
    return {key: raw[key] for key in keys if isinstance(raw.get(key), dict)}


def _validation_logs(raw: dict[str, Any]) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    for key in ("review_result", "schema_repair", "evidence_result", "trace_save_result"):
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
