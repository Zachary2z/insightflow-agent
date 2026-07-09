from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from question_understanding.route_policy import classify_analysis_route
from tools.evidence_tool import build_evidence_payload
from workspaces.time_range_defaults import full_range_default_note
from workspaces.answer_evidence import (
    business_field_label,
    business_field_labels,
    localize_business_field_names,
)
from workspaces.chart_annotation_safety import safe_chart_annotation
from workspaces.context_pack_builder import build_fast_fact_context_pack
from workspaces.progress_steps import build_progress_steps
from workspaces.product_models import (
    P30_CHART_ARTIFACT_OPTIONAL_FIELDS,
    PRODUCT_RESULT_VERSION,
    empty_analysis_route,
    empty_business_answer,
    empty_chart_artifact,
    empty_evidence,
    empty_question_thread,
    empty_technical_details,
)
from workspaces.question_evidence_ledger import (
    build_chart_safe_table,
    build_question_evidence_ledger,
    sanitize_question_evidence_ledger,
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
_KNOWN_METRIC_ACRONYMS = {
    "AOV",
    "CAC",
    "CPA",
    "CPC",
    "CPM",
    "CTR",
    "CVR",
    "GMV",
    "ROI",
    "ROAS",
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
    analysis_route = build_analysis_route(raw)
    chart_artifacts = build_chart_artifacts(
        raw,
        workspace_id=str(resolved_workspace_id),
        workspace_root=resolved_workspace_root,
        business_answer=business_answer,
    )
    ledger_summary = build_question_evidence_ledger_summary({**raw, "chart_artifacts": chart_artifacts})
    return {
        "version": PRODUCT_RESULT_VERSION,
        "workspace_id": resolved_workspace_id,
        "run_id": raw.get("run_id") or "",
        "status": raw.get("status", "unknown"),
        "question_thread": build_question_thread(raw),
        "analysis_route": analysis_route,
        "progress_steps": build_progress_steps(
            raw,
            analysis_route=analysis_route,
            chart_artifacts=chart_artifacts,
        ),
        "business_answer": business_answer,
        "evidence": build_evidence({**raw, "question_evidence_ledger": ledger_summary}),
        "question_evidence_ledger": ledger_summary,
        "chart_artifacts": chart_artifacts,
        "report": raw.get("report_result") or None,
        "technical_details": build_technical_details(raw),
    }


def build_question_thread(raw: dict[str, Any]) -> dict[str, Any]:
    thread = empty_question_thread()
    original_question = raw.get("original_question") or raw.get("user_question") or raw.get("question") or ""
    question_understanding = raw.get("pending_question_understanding") or raw.get("question_understanding") or {}
    memory = raw.get("analysis_thread_memory") if isinstance(raw.get("analysis_thread_memory"), dict) else {}
    pending_memory = memory.get("pending_clarification") if isinstance(memory.get("pending_clarification"), dict) else {}
    thread.update(
        {
            "thread_id": str(memory.get("thread_id") or raw.get("run_id") or ""),
            "original_question": str(original_question),
            "system_understanding": str(raw.get("system_understanding") or "")
            or _system_understanding(question_understanding, original_question=str(original_question)),
            "clarification_question": _scrub_internal_ref_text(_first_text(
                raw.get("clarification_question"),
                raw.get("clarification_questions"),
                pending_memory.get("clarification_question"),
                (raw.get("clarification_result") or {}).get("clarification_question"),
                (raw.get("clarification_result") or {}).get("questions"),
            )),
            "clarification_answer": str(raw.get("clarification_answer") or ""),
            "resolved_question": _scrub_internal_ref_text(
                str(raw.get("resolved_question") or memory.get("latest_resolved_question") or "")
            ),
            "status": str(raw.get("question_thread_status") or memory.get("latest_status") or raw.get("status") or ""),
            "turns": _safe_display_turns(memory.get("turns") or []),
            "current_business_lens": dict(memory.get("current_business_lens") or {}),
            "evidence_refs": _safe_display_evidence_refs(memory.get("evidence_refs") or []),
            "answer_summary": _scrub_internal_ref_text(str(memory.get("answer_summary") or "")),
            "pending_clarification": _scrub_internal_ref_keys(memory.get("pending_clarification")) if memory else None,
            "latest_status": str(memory.get("latest_status") or ""),
            "latest_resolved_question": _scrub_internal_ref_text(str(memory.get("latest_resolved_question") or "")),
        }
    )
    return thread


def _safe_display_evidence_refs(value: Any) -> list[str]:
    return _safe_chart_evidence_refs(value)


def _safe_display_turns(value: Any) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    for item in value or []:
        if not isinstance(item, dict):
            continue
        turn = {
            str(key): _scrub_internal_ref_keys(data)
            for key, data in item.items()
            if str(key) not in {"evidence_ref", "evidence_refs"}
        }
        if item.get("evidence_refs"):
            turn["evidence_refs"] = _safe_display_evidence_refs(item.get("evidence_refs") or [])
        for key in ("resolved_question", "answer_summary", "user_input"):
            if key in turn:
                turn[key] = _scrub_internal_ref_text(str(turn.get(key) or ""))
        turns.append(turn)
    return turns


def _scrub_internal_ref_text(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    text = re.sub(r"question_evidence_ledger:qledger_[A-Za-z0-9_:-]+", "question_evidence_pack", text)
    text = re.sub(r"\bqledger_[A-Za-z0-9_:-]+\b", "question_evidence_pack", text)
    text = re.sub(r"\bevidence:[^\s,，。;；]+", "question_evidence_pack", text)
    return text.replace("source_pack_id", "evidence_source")


def build_analysis_route(raw: dict[str, Any]) -> dict[str, Any]:
    existing = _existing_analysis_route(raw)
    if existing:
        route = empty_analysis_route()
        route.update({key: existing.get(key, route[key]) for key in route})
        route["disqualifiers"] = list(existing.get("disqualifiers") or [])
        return route

    question = str(raw.get("original_question") or raw.get("user_question") or raw.get("question") or "")
    understanding = raw.get("question_understanding") if isinstance(raw.get("question_understanding"), dict) else {}
    task = _analysis_task(raw)
    return classify_analysis_route(
        question,
        analysis_task=task,
        missing_slots=list(raw.get("missing_slots") or understanding.get("missing_slots") or task.get("missing_slots") or []),
        risk_flags=list(raw.get("risk_flags") or understanding.get("risk_flags") or []),
    )


def _existing_analysis_route(raw: dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw.get("analysis_route"), dict):
        return raw["analysis_route"]
    understanding = raw.get("question_understanding") if isinstance(raw.get("question_understanding"), dict) else {}
    if isinstance(understanding.get("analysis_route"), dict):
        return understanding["analysis_route"]
    return {}


def build_business_answer(raw: dict[str, Any]) -> dict[str, Any]:
    if _is_sql_review_failure(raw):
        return _business_failure_answer(raw)

    existing_candidates = _business_answer_candidates(raw)
    user_question = str(raw.get("original_question") or raw.get("user_question") or raw.get("question") or "")
    chinese = _uses_chinese_business_answer(user_question)
    execution_result = raw.get("execution_result") if isinstance(raw.get("execution_result"), dict) else {}
    evidence_result = raw.get("evidence_result") if isinstance(raw.get("evidence_result"), dict) else {}

    for existing, from_successful_generation in existing_candidates:
        if business_answer_is_usable(
            existing,
            user_question,
            execution_result,
            evidence_result,
            enforce_evidence_strength=not from_successful_generation,
        ):
            normalized = _normalize_business_answer(existing, chinese=chinese)
            return _with_time_default_caveat(normalized, raw)

    return _missing_business_answer(chinese=chinese)


def _business_answer_candidates(raw: dict[str, Any]) -> list[tuple[dict[str, Any], bool]]:
    candidates: list[tuple[dict[str, Any], bool]] = []
    existing = raw.get("business_answer") if isinstance(raw.get("business_answer"), dict) else {}
    if existing:
        candidates.append((existing, False))
    generation = raw.get("business_answer_generation") if isinstance(raw.get("business_answer_generation"), dict) else {}
    generated = generation.get("business_answer") if isinstance(generation.get("business_answer"), dict) else {}
    if generation.get("success") is True and generated:
        candidates.append((generated, True))
    return candidates


def _missing_business_answer(*, chinese: bool) -> dict[str, Any]:
    if chinese:
        return _business_answer(
            headline="业务回答缺失",
            direct_answer="业务回答缺失：当前没有可安全展示的模型业务回答，系统不会根据原始查询行拼接最终结论。",
            why="结果组装器只负责组装证据、图表和技术明细；最终业务结论需要由 BusinessAnswerAgent 基于证据账本生成。",
            evidence_bullets=[],
            recommendations=[],
            caveats=["可以重新生成回答，或先查看证据区与技术明细确认本轮数据结果。"],
            confidence="low",
        )
    return _business_answer(
        headline="Business answer missing",
        direct_answer="Business answer missing: no safe model-written business answer is available, and raw rows are not used to compose the final conclusion.",
        why="Product Result Builder only assembles evidence, charts, and technical details; BusinessAnswerAgent owns the final business answer.",
        evidence_bullets=[],
        recommendations=[],
        caveats=["Regenerate the answer or inspect the evidence and technical details for this run."],
        confidence="low",
        chinese=False,
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
                "可以先在数据设置中查看当前数据已包含的表、字段、指标和维度，再按这些口径重新提问。",
                "如果要分析当前工作区没有覆盖的业务对象或指标，请先上传对应数据表或补充字段。",
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


def _with_time_default_caveat(answer: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    note = full_range_default_note((_analysis_task(raw) or {}).get("time_range") or {})
    if not note:
        return answer
    updated = dict(answer)
    caveats = _list_of_text(updated.get("caveats"))
    caveats.append(note)
    updated["caveats"] = list(dict.fromkeys(caveats))
    return updated


def business_answer_is_usable(
    existing: dict[str, Any],
    user_question: str,
    execution_result: dict[str, Any] | None = None,
    evidence_result: dict[str, Any] | None = None,
    *,
    enforce_evidence_strength: bool = True,
) -> bool:
    if not existing:
        return False
    if not BUSINESS_ANSWER_KEYS.issubset(set(existing)):
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
    if _looks_like_mechanical_row_evidence(combined) and not _contains_decision_or_recommendation_intent(
        user_question,
        combined,
    ):
        return False
    if _needs_chinese_response(user_question) and not _business_answer_fields_contain_cjk(existing):
        return False
    if enforce_evidence_strength and execution_result is not None:
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


def _has_weak_evidence(execution_result: dict[str, Any], evidence_result: dict[str, Any]) -> bool:
    if not execution_result or execution_result.get("success") is False:
        return True
    if not execution_result.get("rows"):
        return True
    validation_status = str(evidence_result.get("validation_status") or evidence_result.get("status") or "").lower()
    if validation_status in {"failed", "not_validated", "rejected"} and not _evidence_notes(evidence_result):
        return True
    return False


def _clean_business_text(text: Any, *, chinese: bool) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    value = re.sub(r"```sql\s*.*?```", "", value, flags=re.IGNORECASE | re.DOTALL).strip()
    value = re.sub(r"\b(?:SELECT|WITH)\b.+", "", value, flags=re.IGNORECASE | re.DOTALL).strip()
    value = re.sub(r"\b[A-Za-z_][\w. -]*\s*=\s*[^，,。\n]+(?:[,，]\s*)?", "", value).strip()
    value = _remove_template_debug_phrases(value, chinese=chinese)
    value = _localize_common_field_names(value, chinese=chinese)
    return " ".join(value.split())


def _remove_template_debug_phrases(text: str, *, chinese: bool) -> str:
    cleaned = str(text or "")
    if chinese:
        cleaned = cleaned.replace("证据表" + "第一行显示：", "当前数据中，")
        cleaned = cleaned.replace("本轮排序" + "证据中，", "")
        cleaned = re.sub(r"基于\s*" + r"execution_result[。；;,.，]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace("execution_result", "本次返回数据")
    else:
        cleaned = cleaned.replace("The first evidence row shows:", "The current data shows:")
        cleaned = re.sub(r"based on\s*execution_result[.;, ]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace("execution_result", "returned data")
    return cleaned.strip()


def _localize_common_field_names(text: str, *, chinese: bool) -> str:
    localized = localize_business_field_names(text, chinese=chinese)
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


def _contains_decision_or_recommendation_intent(*texts: str) -> bool:
    lowered = " ".join(str(text or "") for text in texts).lower()
    markers = (
        "建议",
        "推荐",
        "应该",
        "值得",
        "优先",
        "加预算",
        "减少预算",
        "优化",
        "下一步",
        "recommend",
        "should",
        "prioritize",
        "budget",
    )
    return any(marker in lowered for marker in markers)


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


def build_evidence(
    raw_or_execution_result: dict[str, Any],
    evidence_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if evidence_result is None and (
        "execution_result" in raw_or_execution_result
        or "question_understanding" in raw_or_execution_result
        or "generated_sql" in raw_or_execution_result
    ):
        raw = raw_or_execution_result
        execution_result = raw.get("execution_result") if isinstance(raw.get("execution_result"), dict) else {}
        evidence_result = raw.get("evidence_result") if isinstance(raw.get("evidence_result"), dict) else {}
    else:
        raw = {}
        execution_result = raw_or_execution_result
        evidence_result = evidence_result or {}
    evidence = empty_evidence()
    evidence["table_preview"] = _safe_table_preview(raw=raw, execution_result=execution_result)
    evidence["evidence_notes"] = _evidence_notes(evidence_result)
    evidence["validation_status"] = str(
        evidence_result.get("validation_status")
        or evidence_result.get("status")
        or ("validated" if evidence_result.get("success") else "not_validated")
    )
    evidence["fact_payload"] = _fact_payload(raw=raw, execution_result=execution_result)
    question_pack = _question_evidence_pack(raw)
    if question_pack:
        evidence["question_evidence"] = {
            "columns": list(question_pack.get("columns") or []),
            "rows": list(question_pack.get("rows") or [])[:20],
            "metrics": list(question_pack.get("metrics") or []),
            "chart_candidates": list(question_pack.get("chart_candidates") or []),
            "data_limits": list(question_pack.get("data_limits") or []),
        }
    ledger = build_question_evidence_ledger_summary(raw)
    if ledger:
        evidence["ledger_summary"] = ledger
    return evidence


def build_question_evidence_ledger_summary(raw: dict[str, Any]) -> dict[str, Any]:
    existing = raw.get("question_evidence_ledger") if isinstance(raw.get("question_evidence_ledger"), dict) else {}
    if existing:
        ledger = sanitize_question_evidence_ledger(existing)
        ledger["chart_refs"] = _unique_text(
            [*list(ledger.get("chart_refs") or []), *_chart_artifact_refs(raw.get("chart_artifacts"))]
        )
        return _business_readable_ledger_summary(ledger, raw)
    pack = _question_evidence_pack(raw)
    if not pack:
        return {}
    execution_result = raw.get("execution_result") if isinstance(raw.get("execution_result"), dict) else {}
    evidence_result = raw.get("evidence_result") if isinstance(raw.get("evidence_result"), dict) else {}
    fact_payload = _fact_payload(raw=raw, execution_result=execution_result)
    ledger = build_question_evidence_ledger(
        question_evidence_pack=pack,
        execution_result=execution_result,
        evidence_validation=evidence_result,
        chart_artifacts=raw.get("chart_artifacts") if isinstance(raw.get("chart_artifacts"), list) else [],
        fact_payload=fact_payload,
    )
    return _business_readable_ledger_summary(ledger, raw)


def _business_readable_ledger_summary(ledger: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    if not ledger:
        return {}
    summary = _scrub_display_ledger_refs(ledger)
    summary["task_groups"] = _ledger_task_groups(ledger, raw)
    summary["business_data_limits"] = _business_data_limits(ledger, raw)
    summary["data_limits"] = list(summary["business_data_limits"])
    return summary


def _scrub_display_ledger_refs(ledger: dict[str, Any]) -> dict[str, Any]:
    summary = dict(ledger)
    summary.pop("ledger_id", None)
    summary.pop("task_refs", None)
    summary.pop("evidence_refs", None)
    summary.pop("source_pack_id", None)
    if isinstance(summary.get("question_evidence_plan"), dict):
        summary["question_evidence_plan"] = _scrub_internal_ref_keys(summary["question_evidence_plan"])
    for key in ("facts", "derived_metrics"):
        cleaned_items: list[dict[str, Any]] = []
        for item in summary.get(key) or []:
            if not isinstance(item, dict):
                continue
            cleaned = dict(item)
            cleaned.pop("task_id", None)
            cleaned.pop("evidence_ref", None)
            cleaned.pop("source_row_refs", None)
            cleaned_items.append(cleaned)
        summary[key] = cleaned_items
    cleaned_groups: list[dict[str, Any]] = []
    for group in summary.get("evidence_groups") or []:
        if not isinstance(group, dict):
            continue
        cleaned_group = dict(group)
        cleaned_group.pop("evidence_refs", None)
        for key in ("facts", "derived_metrics"):
            group_items: list[dict[str, Any]] = []
            for item in cleaned_group.get(key) or []:
                if not isinstance(item, dict):
                    continue
                cleaned = dict(item)
                cleaned.pop("task_id", None)
                cleaned.pop("evidence_ref", None)
                cleaned.pop("source_row_refs", None)
                group_items.append(cleaned)
            cleaned_group[key] = group_items
        cleaned_groups.append(cleaned_group)
    if cleaned_groups:
        summary["evidence_groups"] = cleaned_groups
    for table in summary.get("tables") or []:
        if isinstance(table, dict):
            table.pop("task_id", None)
    return summary


def _scrub_internal_ref_keys(value: Any) -> Any:
    internal_keys = {
        "ledger_id",
        "source_pack_id",
        "task_id",
        "task_purpose",
        "evidence_ref",
        "evidence_refs",
        "source_row_refs",
    }
    if isinstance(value, dict):
        return {
            str(key): _scrub_internal_ref_keys(item)
            for key, item in value.items()
            if str(key) not in internal_keys
        }
    if isinstance(value, list):
        return [_scrub_internal_ref_keys(item) for item in value]
    return value


def _ledger_task_groups(ledger: dict[str, Any], raw: dict[str, Any]) -> list[dict[str, Any]]:
    grouped_sections = _ledger_evidence_group_summaries(ledger)
    if grouped_sections:
        return grouped_sections

    facts = [fact for fact in ledger.get("facts") or [] if isinstance(fact, dict)]
    derived = [metric for metric in ledger.get("derived_metrics") or [] if isinstance(metric, dict)]
    entries = [*facts, *derived]
    if not entries:
        return []

    task_results = {
        str(item.get("task_id") or ""): item
        for item in raw.get("evidence_task_results") or []
        if isinstance(item, dict) and str(item.get("task_id") or "").strip()
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        key = str(entry.get("task_id") or "")
        if not key:
            key = _task_group_title("", [entry])
        grouped.setdefault(key, []).append(entry)

    groups: list[dict[str, Any]] = []
    for task_key, items in grouped.items():
        title = _task_group_title(task_key, items)
        status = "已取得" if task_results.get(task_key, {}).get("status", "executed") == "executed" else "未完整取得"
        groups.append(
            {
                "title": title,
                "status": status,
                "facts": [_business_fact_sentence(item) for item in items[:4] if _business_fact_sentence(item)],
            }
        )
    return groups[:6]


def _ledger_evidence_group_summaries(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for group in ledger.get("evidence_groups") or []:
        if not isinstance(group, dict):
            continue
        title = str(group.get("purpose") or group.get("group_id") or "业务证据").strip()
        facts = [
            _business_fact_sentence(item)
            for item in [*(group.get("facts") or []), *(group.get("derived_metrics") or [])]
            if isinstance(item, dict) and _business_fact_sentence(item)
        ]
        summaries.append(
            {
                "title": title,
                "status": "已取得" if facts else "未完整取得",
                "facts": facts[:4],
            }
        )
    return summaries[:6]


def _task_group_title(task_key: str, items: list[dict[str, Any]]) -> str:
    text = " ".join(
        [
            task_key,
            *[str(item.get("label") or item.get("metric_id") or "") for item in items],
        ]
    ).lower()
    if any(marker in text for marker in ("投放", "花费", "spend", "cost", "成本")):
        return "投放花费证据"
    if any(marker in text for marker in ("效率", "roi", "roas", "转化", "conversion")):
        return "效率辅助证据"
    if any(marker in text for marker in ("收入", "销售", "revenue", "sales", "gmv", "amount")):
        return "收入证据"
    if any(marker in text for marker in ("趋势", "trend", "anomaly", "异常")):
        return "趋势辅助证据"
    return "业务证据"


def _business_fact_sentence(item: dict[str, Any]) -> str:
    label = str(item.get("label") or item.get("metric_id") or "指标").strip()
    value = item.get("value")
    if not label or value is None or isinstance(value, dict | list):
        return ""
    dimension = item.get("dimension") if isinstance(item.get("dimension"), dict) else {}
    dimension_values = [
        str(value).strip()
        for value in dimension.values()
        if str(value).strip() and not _looks_internal_ref(str(value))
    ]
    prefix = "，".join(dimension_values)
    if prefix:
        return f"{prefix}{label}为 {value}。"
    return f"{label}为 {value}。"


def _business_data_limits(ledger: dict[str, Any], raw: dict[str, Any]) -> list[str]:
    limits: list[str] = []
    raw_limits = [str(item).strip() for item in ledger.get("data_limits") or [] if str(item).strip()]
    failed_tasks = [
        item for item in raw.get("evidence_task_results") or []
        if isinstance(item, dict) and str(item.get("status") or "") not in {"", "executed"}
    ]
    if failed_tasks or any("证据任务" in item for item in raw_limits):
        if _has_core_evidence(ledger):
            limits.append("辅助证据未能完成；本次结论仍以已取得的核心证据为准。")
        else:
            limits.append("核心证据未能完整取得，因此当前数据不足以支持确定结论。")
    for limit in raw_limits:
        cleaned = _clean_business_limit(limit)
        if cleaned and cleaned not in limits:
            limits.append(cleaned)
    return limits[:4]


def _has_core_evidence(ledger: dict[str, Any]) -> bool:
    return bool(ledger.get("facts") or ledger.get("derived_metrics"))


def _clean_business_limit(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    if "证据任务" in value:
        return ""
    if _contains_technical_leak(value) or _looks_internal_ref(value):
        return ""
    return _clean_business_text(value, chinese=True)


def _looks_internal_ref(text: str) -> bool:
    value = str(text or "")
    if re.search(r"\b(?:core_fact|trend_or_anomaly_support|explanation_support|task_id|evidence:|qledger_|question_evidence_ledger)\b", value, re.IGNORECASE):
        return True
    return bool(re.search(r"\b[A-Za-z]+_[A-Za-z0-9_]{8,}\b", value))


def _chart_artifact_refs(value: Any) -> list[str]:
    refs: list[str] = []
    for chart in value or []:
        if not isinstance(chart, dict):
            continue
        ref = str(chart.get("artifact_id") or chart.get("chart_id") or chart.get("title") or "").strip()
        if ref:
            refs.append(ref)
    return refs


def build_chart_artifacts(
    raw: dict[str, Any],
    *,
    workspace_id: str = "",
    workspace_root: str | Path | None = None,
    business_answer: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    existing_artifacts = raw.get("chart_artifacts") if isinstance(raw.get("chart_artifacts"), list) else []
    if existing_artifacts:
        normalized_artifacts = [
            _normalize_chart_artifact(
                artifact,
                workspace_id=workspace_id,
                workspace_root=workspace_root,
                business_answer=business_answer or build_business_answer(raw),
                execution_result=raw.get("execution_result") if isinstance(raw.get("execution_result"), dict) else {},
            )
            for artifact in existing_artifacts
            if isinstance(artifact, dict)
        ]
        return [_with_default_chart_evidence_refs(artifact, raw) for artifact in normalized_artifacts]

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
            visualization_trace.get("image_path"),
            delivery.get("artifact_path"),
            delivery.get("chart_path"),
            delivery.get("image_path"),
            raw.get("chart_path"),
            *(raw.get("chart_paths") or []),
        ]
    )
    if not paths and _has_p30_chart_payload(visualization_trace, delivery):
        paths = [""]
    artifacts: list[dict[str, Any]] = []
    for path in paths:
        display_path, url = _artifact_path_and_url(
            path,
            workspace_id=workspace_id,
            workspace_root=workspace_root,
            artifact_url=str(
                visualization_trace.get("artifact_url")
                or visualization_trace.get("image_url")
                or delivery.get("artifact_url")
                or delivery.get("image_url")
                or ""
            ),
        )
        image_path = str(delivery.get("image_path") or visualization_trace.get("image_path") or path or "")
        image_url_hint = str(delivery.get("image_url") or visualization_trace.get("image_url") or "")
        display_image_path, image_url = _artifact_path_and_url(
            image_path,
            workspace_id=workspace_id,
            workspace_root=workspace_root,
            artifact_url=image_url_hint or url,
        )
        artifact = empty_chart_artifact()
        artifact.update(
            {
                "title": title,
                "path": display_path,
                "url": url,
                "rendering_status": str(
                    visualization_trace.get("rendering_status")
                    or delivery.get("rendering_status")
                    or "rendered"
                ),
                "unit": unit,
                "value_label": value_label,
                "business_annotation": safe_annotation,
            }
        )
        artifact.update(
            _p30_chart_artifact_fields(
                visualization_trace,
                delivery,
                chart_spec=chart_spec,
                image_path=display_image_path or display_path,
                image_url=image_url or url,
            )
        )
        artifacts.append(_with_default_chart_evidence_refs(artifact, raw))
    return artifacts


def _with_default_chart_evidence_refs(artifact: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    if artifact.get("evidence_refs"):
        return artifact
    refs = _ledger_evidence_refs(raw)
    if not refs:
        return artifact
    updated = dict(artifact)
    updated["evidence_refs"] = refs
    return updated


def _ledger_evidence_refs(raw: dict[str, Any]) -> list[str]:
    ledger = raw.get("question_evidence_ledger") if isinstance(raw.get("question_evidence_ledger"), dict) else {}
    return _safe_chart_evidence_refs(ledger.get("evidence_refs") or [])


def _normalize_chart_artifact(
    artifact: dict[str, Any],
    *,
    workspace_id: str,
    workspace_root: str | Path | None,
    business_answer: dict[str, Any],
    execution_result: dict[str, Any],
) -> dict[str, Any]:
    normalized = empty_chart_artifact()
    chart_spec = artifact.get("chart_spec") if isinstance(artifact.get("chart_spec"), dict) else {}
    title = str(artifact.get("title") or chart_spec.get("title") or "Chart")
    unit = str(artifact.get("unit") or chart_spec.get("unit") or "")
    value_label = bool(artifact.get("value_label") or chart_spec.get("value_label") or False)
    annotation = str(artifact.get("business_annotation") or chart_spec.get("business_annotation") or "")
    safe_annotation = safe_chart_annotation(
        annotation=annotation,
        business_answer=business_answer,
        execution_result=execution_result,
    )
    path = str(artifact.get("path") or artifact.get("image_path") or "")
    display_path, url = _artifact_path_and_url(
        path,
        workspace_id=workspace_id,
        workspace_root=workspace_root,
        artifact_url=str(artifact.get("url") or artifact.get("image_url") or ""),
    )
    image_path = str(artifact.get("image_path") or artifact.get("path") or "")
    display_image_path, image_url = _artifact_path_and_url(
        image_path,
        workspace_id=workspace_id,
        workspace_root=workspace_root,
        artifact_url=str(artifact.get("image_url") or artifact.get("url") or ""),
    )
    normalized.update(
        {
            "title": title,
            "path": display_path,
            "url": url,
            "rendering_status": str(artifact.get("rendering_status") or "rendered"),
            "unit": unit,
            "value_label": value_label,
            "business_annotation": safe_annotation,
        }
    )
    normalized.update(
        _p30_chart_artifact_fields(
            artifact,
            chart_spec=chart_spec,
            image_path=display_image_path or display_path,
            image_url=image_url or url,
        )
    )
    return normalized


def _has_p30_chart_payload(*sources: dict[str, Any]) -> bool:
    return any(
        bool(
            source.get("artifact_id")
            or source.get("echarts_option")
            or source.get("image_path")
            or source.get("image_url")
            or source.get("skip_reason")
            or source.get("failure_reason")
            or str(source.get("rendering_status") or "") == "skipped"
        )
        for source in sources
    )


def _p30_chart_artifact_fields(
    *sources: dict[str, Any],
    chart_spec: dict[str, Any] | None = None,
    image_path: str = "",
    image_url: str = "",
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    spec = chart_spec if isinstance(chart_spec, dict) else {}
    for key in P30_CHART_ARTIFACT_OPTIONAL_FIELDS:
        value = _first_chart_field(key, *sources)
        if value in (None, ""):
            continue
        if key in {"chart_spec", "echarts_option"}:
            if key == "echarts_option" and isinstance(value, dict):
                fields[key] = _sanitize_chart_option(value)
            continue
        if key == "evidence_refs":
            if isinstance(value, list):
                fields[key] = _safe_chart_evidence_refs(value)
            continue
        if key == "data_row_count":
            try:
                fields[key] = int(value)
            except (TypeError, ValueError):
                continue
            continue
        fields[key] = str(value)
    if spec.get("chart_type") and "chart_type" not in fields:
        fields["chart_type"] = str(spec.get("chart_type"))
    if image_path:
        fields["image_path"] = image_path
    if image_url:
        fields["image_url"] = image_url
    return fields


def _first_chart_field(key: str, *sources: dict[str, Any]) -> Any:
    for source in sources:
        if isinstance(source, dict) and key in source:
            return source.get(key)
    return None


def build_technical_details(raw: dict[str, Any]) -> dict[str, Any]:
    execution_result = raw.get("execution_result") if isinstance(raw.get("execution_result"), dict) else {}
    fact_payload = _fact_payload(raw=raw, execution_result=execution_result)
    details = empty_technical_details()
    details.update(
        {
            "sql": str(raw.get("generated_sql") or ""),
            "raw_rows": list(execution_result.get("rows") or []),
            "fact_payload": fact_payload,
            "question_evidence_pack": _question_evidence_pack(raw),
            "audit_result": _audit_result(raw),
            "data_version": raw.get("data_version"),
            "normalized_question": str(raw.get("normalized_question") or ""),
            "trace_path": str(raw.get("trace_path") or ""),
            "provider_metadata": _provider_metadata(raw),
            "validation_logs": _validation_logs(raw),
            "debug": _debug_fields(raw),
        }
    )
    fast_fact_pack = _fast_fact_context_pack(raw, execution_result=execution_result, fact_payload=fact_payload)
    if fast_fact_pack:
        details["fast_fact_context_pack"] = fast_fact_pack
    return details


def _safe_table_preview(*, raw: dict[str, Any], execution_result: dict[str, Any]) -> dict[str, Any]:
    columns = [str(column) for column in execution_result.get("columns") or []]
    rows = list(execution_result.get("rows") or [])[:20]
    if not _has_internal_table_columns(columns):
        return {"columns": columns, "rows": rows}

    chart_safe_table = build_chart_safe_table(
        raw.get("question_evidence_ledger") if isinstance(raw.get("question_evidence_ledger"), dict) else {}
    )
    if chart_safe_table.get("success"):
        return {
            "columns": list(chart_safe_table.get("columns") or []),
            "rows": list(chart_safe_table.get("rows") or [])[:20],
        }
    keep_indexes = [index for index, column in enumerate(columns) if not _is_internal_table_column(column)]
    return {
        "columns": [columns[index] for index in keep_indexes],
        "rows": [
            [value for index, value in enumerate(row) if index in keep_indexes]
            if isinstance(row, (list, tuple))
            else {key: value for key, value in dict(row).items() if not _is_internal_table_column(str(key))}
            for row in rows
        ],
    }


def _has_internal_table_columns(columns: list[str]) -> bool:
    return any(_is_internal_table_column(column) for column in columns)


def _is_internal_table_column(column: str) -> bool:
    return str(column or "").strip().lower() in {"task_id", "task_purpose"}


def _safe_chart_evidence_refs(value: Any) -> list[str]:
    raw_refs = [str(item).strip() for item in value or [] if str(item).strip()]
    if not raw_refs:
        return []
    safe_refs = [ref for ref in raw_refs if not _looks_internal_ref(ref)]
    if len(safe_refs) != len(raw_refs) or not safe_refs:
        return ["question_evidence_pack"]
    return safe_refs[:20]


def _sanitize_chart_option(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize_chart_option(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_chart_option(item) for item in value]
    if isinstance(value, str) and (_contains_technical_leak(value) or _looks_internal_ref(value)):
        return ""
    return value


def _question_evidence_pack(raw: dict[str, Any]) -> dict[str, Any]:
    value = raw.get("question_evidence_pack")
    return dict(value) if isinstance(value, dict) else {}


def _audit_result(raw: dict[str, Any]) -> dict[str, Any]:
    value = raw.get("audit_result")
    return dict(value) if isinstance(value, dict) else {}


def _fact_payload(*, raw: dict[str, Any], execution_result: dict[str, Any]) -> dict[str, Any]:
    if not execution_result:
        return {}
    task = _analysis_task(raw)
    metric_registry = _metric_registry(raw)
    payload = build_evidence_payload(
        task=task,
        execution_result=execution_result,
        metric_registry=metric_registry,
        sql=str(raw.get("generated_sql") or ""),
        filters=list(task.get("filters") or []),
        business_aliases=_semantic_business_aliases(raw),
    )
    return _main_payload_fact_payload(payload)


def _main_payload_fact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(payload or {})
    technical_refs = cleaned.get("technical_refs")
    if isinstance(technical_refs, dict):
        refs = dict(technical_refs)
        refs.pop("raw_rows", None)
        cleaned["technical_refs"] = refs
    return cleaned


def _fast_fact_context_pack(
    raw: dict[str, Any],
    *,
    execution_result: dict[str, Any],
    fact_payload: dict[str, Any],
) -> dict[str, Any]:
    existing = raw.get("fast_fact_context_pack")
    if isinstance(existing, dict) and existing:
        return existing
    result = raw.get("fast_fact_result") if isinstance(raw.get("fast_fact_result"), dict) else {}
    nested = result.get("context_pack")
    if isinstance(nested, dict) and nested:
        return nested
    route = build_analysis_route(raw)
    if route.get("route") != "fast_fact":
        return {}
    return build_fast_fact_context_pack(
        user_question=str(raw.get("original_question") or raw.get("user_question") or raw.get("question") or ""),
        analysis_route=route,
        analysis_task=_analysis_task(raw),
        fact_payload=fact_payload,
        evidence_result=raw.get("evidence_result") if isinstance(raw.get("evidence_result"), dict) else {},
        execution_result=execution_result,
        metric_registry=_metric_registry(raw),
    )


def _analysis_task(raw: dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw.get("analysis_task"), dict):
        return dict(raw["analysis_task"])
    understanding = raw.get("question_understanding") if isinstance(raw.get("question_understanding"), dict) else {}
    if isinstance(understanding.get("analysis_task"), dict):
        return dict(understanding["analysis_task"])
    pending_understanding = (
        raw.get("pending_question_understanding")
        if isinstance(raw.get("pending_question_understanding"), dict)
        else {}
    )
    if isinstance(pending_understanding.get("analysis_task"), dict):
        return dict(pending_understanding["analysis_task"])
    return {}


def _metric_registry(raw: dict[str, Any]) -> dict[str, Any]:
    for key in ("metric_registry", "metric_context"):
        value = raw.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _semantic_business_aliases(raw: dict[str, Any]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    task = _analysis_task(raw)
    dimensions = [str(item) for item in task.get("dimensions") or [] if str(item).strip()]
    metrics = [str(item) for item in task.get("metrics") or [] if str(item).strip()]
    cjk_dimensions = [item for item in dimensions if _contains_cjk(item)]
    for dimension in dimensions:
        if "." not in dimension and not _contains_cjk(dimension) and cjk_dimensions:
            aliases[dimension] = cjk_dimensions[-1]
    if any(item in {"品类", "类别"} for item in cjk_dimensions):
        aliases.setdefault("category_name", "品类")
        aliases.setdefault("Category Name", "品类")
    if any(item in {"门店", "店铺"} for item in cjk_dimensions):
        aliases.setdefault("store_name", "门店")
        aliases.setdefault("Store Name", "门店")
    if any(item in {"团队", "客服团队"} for item in cjk_dimensions):
        aliases.setdefault("team_name", "团队")
        aliases.setdefault("Team Name", "团队")
    metric_text = " ".join(metrics)
    if any(token in metric_text for token in ("销售", "收入", "成交", "金额", "paid_amount")):
        aliases.setdefault("total_amount", "销售额")
        aliases.setdefault("metric_value", "销售额")
    if "占比" in metric_text:
        aliases.setdefault("percentage", "占比")
        aliases.setdefault("proportion", "占比")
    semantic_context = raw.get("semantic_context") if isinstance(raw.get("semantic_context"), dict) else {}
    for collection_name in ("metrics", "dimensions", "time_fields"):
        items = semantic_context.get(collection_name)
        if isinstance(items, dict):
            iterable = items.values()
        elif isinstance(items, list):
            iterable = items
        else:
            iterable = []
        for item in iterable:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or item.get("business_label") or "").strip()
            field = str(item.get("field") or item.get("name") or "").strip()
            if not label or not field:
                continue
            aliases[field.split(".")[-1]] = label
            aliases[str(item.get("name") or "")] = label
    return {key: value for key, value in aliases.items() if key and value}


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


def _looks_like_raw_parameter_dump(text: str) -> bool:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return False
    dump_lines = 0
    for line in lines:
        stripped = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line)
        assignments = [
            key
            for key in re.findall(r"\b([A-Za-z_][A-Za-z0-9_. -]*)\s*=", stripped)
            if _looks_like_raw_assignment_key(key)
        ]
        if len(assignments) >= 2 or (assignments and "," in stripped):
            dump_lines += 1
    return dump_lines >= max(1, len(lines) // 2)


def _looks_like_raw_assignment_key(key: str) -> bool:
    token = str(key or "").strip().split()[-1] if str(key or "").strip() else ""
    if not token:
        return False
    if token.upper() in _KNOWN_METRIC_ACRONYMS:
        return False
    if token.isupper() and len(token) <= 5:
        return False
    return True


def _looks_like_mechanical_row_evidence(text: str) -> bool:
    value = str(text or "")
    if re.search(r"(?:第\s*\d+\s*行|Row\s+\d+)", value, re.IGNORECASE):
        return True
    raw_field_names = sorted(business_field_labels(chinese=True), key=len, reverse=True)
    raw_field_pattern = "|".join(re.escape(name) for name in raw_field_names)
    if raw_field_pattern and re.search(rf"\b(?:{raw_field_pattern})\b\s*(?:为|is)\s*", value, re.IGNORECASE):
        return True
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    for line in lines:
        stripped = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line)
        if stripped.count(" 为 ") >= 2:
            return True
    return False


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
        "evidence_planning",
        "sql_planning",
        "llm_sql_enhancement",
        "schema_repair",
        "analysis_plan",
        "business_answer_generation",
        "visualization_trace",
    )
    return {key: raw[key] for key in keys if isinstance(raw.get(key), dict)}


def _validation_logs(raw: dict[str, Any]) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    for key in ("review_result", "schema_repair", "evidence_result", "audit_result", "trace_save_result"):
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
