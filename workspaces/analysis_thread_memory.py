from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class AnalysisThreadTurn:
    turn_id: str
    user_input: str
    resolved_question: str
    status: str
    answer_summary: str = ""
    business_lens: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["business_lens"] = dict(self.business_lens)
        data["evidence_refs"] = list(self.evidence_refs)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisThreadTurn":
        return cls(
            turn_id=str(data.get("turn_id") or ""),
            user_input=str(data.get("user_input") or ""),
            resolved_question=str(data.get("resolved_question") or ""),
            status=str(data.get("status") or ""),
            answer_summary=str(data.get("answer_summary") or ""),
            business_lens=dict(data.get("business_lens") or {}),
            evidence_refs=[str(item) for item in data.get("evidence_refs") or [] if str(item)],
            created_at=str(data.get("created_at") or ""),
        )


@dataclass
class AnalysisThreadMemory:
    thread_id: str
    original_question: str
    turns: list[AnalysisThreadTurn] = field(default_factory=list)
    current_business_lens: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    answer_summary: str = ""
    pending_clarification: dict[str, Any] | None = None
    latest_status: str = ""
    latest_resolved_question: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "original_question": self.original_question,
            "turns": [turn.to_dict() for turn in self.turns],
            "current_business_lens": dict(self.current_business_lens),
            "evidence_refs": list(self.evidence_refs),
            "answer_summary": self.answer_summary,
            "pending_clarification": dict(self.pending_clarification) if self.pending_clarification else None,
            "latest_status": self.latest_status,
            "latest_resolved_question": self.latest_resolved_question,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisThreadMemory":
        return cls(
            thread_id=str(data.get("thread_id") or ""),
            original_question=str(data.get("original_question") or ""),
            turns=[
                AnalysisThreadTurn.from_dict(item)
                for item in data.get("turns") or []
                if isinstance(item, dict)
            ],
            current_business_lens=dict(data.get("current_business_lens") or {}),
            evidence_refs=[str(item) for item in data.get("evidence_refs") or [] if str(item)],
            answer_summary=str(data.get("answer_summary") or ""),
            pending_clarification=(
                dict(data.get("pending_clarification"))
                if isinstance(data.get("pending_clarification"), dict)
                else None
            ),
            latest_status=str(data.get("latest_status") or ""),
            latest_resolved_question=str(data.get("latest_resolved_question") or ""),
        )


def build_or_update_thread_memory(
    raw: dict[str, Any],
    *,
    thread_id: str,
    user_input: str,
    original_question: str,
    previous_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    memory = (
        AnalysisThreadMemory.from_dict(previous_memory)
        if isinstance(previous_memory, dict) and previous_memory
        else AnalysisThreadMemory(thread_id=thread_id, original_question=original_question)
    )
    memory.thread_id = thread_id
    memory.original_question = memory.original_question or original_question

    status = str(raw.get("status") or "")
    resolved_question = _resolved_question(raw, fallback=user_input or original_question)
    answer_summary = _answer_summary(raw)
    business_lens = _business_lens(raw)
    evidence_refs = _evidence_refs(raw)
    pending_clarification = _pending_clarification(raw)

    memory.current_business_lens = business_lens
    memory.evidence_refs = evidence_refs
    memory.answer_summary = answer_summary
    memory.pending_clarification = pending_clarification if status == "waiting_for_clarification" else None
    memory.latest_status = status
    memory.latest_resolved_question = resolved_question
    memory.turns.append(
        AnalysisThreadTurn(
            turn_id=f"turn_{len(memory.turns) + 1}",
            user_input=user_input,
            resolved_question=resolved_question,
            status=status,
            answer_summary=answer_summary,
            business_lens=business_lens,
            evidence_refs=evidence_refs,
            created_at=_now_iso(),
        )
    )
    return memory.to_dict()


def build_completed_follow_up_question(
    *,
    memory: dict[str, Any],
    message: str,
) -> str:
    original = _clean(memory.get("original_question"))
    latest_resolved = _clean(memory.get("latest_resolved_question"))
    answer_summary = _clean(memory.get("answer_summary"))
    evidence_refs = ", ".join([str(item) for item in memory.get("evidence_refs") or [] if str(item)])
    business_lens = memory.get("current_business_lens") if isinstance(memory.get("current_business_lens"), dict) else {}
    lens_summary = _lens_summary(business_lens)
    parts = [
        "同一分析线程继续分析。",
        f"原问题：{original}。" if original else "",
        f"上一轮整理后问题：{latest_resolved}。" if latest_resolved else "",
        f"上一轮答案摘要：{answer_summary}。" if answer_summary else "",
        f"已有证据引用：{evidence_refs}。" if evidence_refs else "",
        f"已有业务口径：{lens_summary}。" if lens_summary else "",
        f"本轮追问：{_clean(message)}。",
        "请结合上述上下文重新走安全分析流程，给出本轮业务结论和证据边界。",
    ]
    return "".join(part for part in parts if part)


def _resolved_question(raw: dict[str, Any], *, fallback: str) -> str:
    task = raw.get("analysis_task") if isinstance(raw.get("analysis_task"), dict) else {}
    understanding = raw.get("question_understanding") if isinstance(raw.get("question_understanding"), dict) else {}
    return _first_text(
        raw.get("resolved_question"),
        task.get("resolved_question"),
        understanding.get("resolved_question"),
        raw.get("original_question"),
        fallback,
    )


def _answer_summary(raw: dict[str, Any]) -> str:
    answer = raw.get("business_answer") if isinstance(raw.get("business_answer"), dict) else {}
    return _first_text(
        answer.get("direct_answer"),
        answer.get("headline"),
        raw.get("final_answer"),
    )


def _business_lens(raw: dict[str, Any]) -> dict[str, Any]:
    task = raw.get("analysis_task") if isinstance(raw.get("analysis_task"), dict) else {}
    pack = raw.get("question_evidence_pack") if isinstance(raw.get("question_evidence_pack"), dict) else {}
    pack_task = pack.get("task") if isinstance(pack.get("task"), dict) else {}
    understanding = raw.get("question_understanding") if isinstance(raw.get("question_understanding"), dict) else {}
    for value in (
        task.get("business_lens"),
        pack_task.get("business_lens"),
        understanding.get("business_lens"),
    ):
        if isinstance(value, dict) and value:
            return dict(value)
    return {}


def _evidence_refs(raw: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    if isinstance(raw.get("question_evidence_pack"), dict):
        refs.append("question_evidence_pack")
    ledger = raw.get("question_evidence_ledger") if isinstance(raw.get("question_evidence_ledger"), dict) else {}
    if ledger:
        ledger_id = str(ledger.get("ledger_id") or "").strip()
        refs.append(f"question_evidence_ledger:{ledger_id}" if ledger_id else "question_evidence_ledger")
        for ref in ledger.get("evidence_refs") or []:
            text = str(ref or "").strip()
            if text:
                refs.append(text)
    for chart in raw.get("chart_artifacts") or []:
        if not isinstance(chart, dict):
            continue
        for ref in chart.get("evidence_refs") or []:
            text = str(ref or "").strip()
            if text:
                refs.append(text)
    return list(dict.fromkeys(refs))


def _pending_clarification(raw: dict[str, Any]) -> dict[str, Any] | None:
    question = _first_text(
        raw.get("clarification_question"),
        raw.get("clarification_questions"),
        (raw.get("clarification_result") or {}).get("clarification_question")
        if isinstance(raw.get("clarification_result"), dict)
        else "",
        (raw.get("clarification_result") or {}).get("clarification_questions")
        if isinstance(raw.get("clarification_result"), dict)
        else "",
    )
    if not question:
        return None
    clarification = raw.get("clarification_result") if isinstance(raw.get("clarification_result"), dict) else {}
    understanding = raw.get("question_understanding") if isinstance(raw.get("question_understanding"), dict) else {}
    return {
        "clarification_question": question,
        "missing_fields": list(
            clarification.get("missing_slots")
            or clarification.get("missing_fields")
            or understanding.get("missing_slots")
            or []
        ),
    }


def _lens_summary(business_lens: dict[str, Any]) -> str:
    if not business_lens:
        return ""
    metrics = [
        str(metric.get("label") or metric.get("source_field") or "")
        for metric in business_lens.get("metrics") or []
        if isinstance(metric, dict)
    ]
    dimensions = [
        str(dimension.get("label") or dimension.get("source_field") or "")
        for dimension in business_lens.get("dimensions") or []
        if isinstance(dimension, dict)
    ]
    parts = []
    if business_lens.get("business_domain"):
        parts.append(f"业务域={business_lens['business_domain']}")
    if metrics:
        parts.append(f"指标={','.join(metrics)}")
    if dimensions:
        parts.append(f"维度={','.join(dimensions)}")
    if business_lens.get("time_policy_note"):
        parts.append(str(business_lens["time_policy_note"]))
    return "；".join(parts)


def _first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, list):
            for item in value:
                text = _clean(item)
                if text:
                    return text
            continue
        text = _clean(value)
        if text:
            return text
    return ""


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "AnalysisThreadMemory",
    "AnalysisThreadTurn",
    "build_completed_follow_up_question",
    "build_or_update_thread_memory",
]
