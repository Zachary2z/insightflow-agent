from __future__ import annotations

from typing import Any


def build_resolved_question(
    *,
    original_question: str,
    clarification_answer: str,
    clarification_context: dict[str, Any] | None = None,
) -> str:
    original = _clean(original_question)
    answer = _clean(clarification_answer)
    context = clarification_context or {}

    if not original:
        return answer
    if not answer:
        return original

    if _contains(original, "渠道", "channel") and _contains(original, "预算", "加预算", "投放", "表现"):
        time_text = _extract_time_text(answer)
        prefix = f"{time_text} " if time_text else ""
        return f"分析{prefix}各渠道的收入、订单数、投放成本和 ROI，并给出预算调整建议。"

    clarification_question = _clean(str(context.get("clarification_question") or ""))
    if clarification_question:
        return f"{original}。补充回答：{answer}。请基于补充回答完成分析并给出业务建议。"
    return f"{original}。补充条件：{answer}。请完成分析并给出业务建议。"


def _clean(value: str) -> str:
    return " ".join(str(value or "").split()).strip(" 。")


def _contains(text: str, *keywords: str) -> bool:
    compact = text.lower().replace(" ", "")
    return any(keyword.lower().replace(" ", "") in compact for keyword in keywords)


def _extract_time_text(text: str) -> str:
    compact = _clean(text)
    for marker in ("最近 90 天", "最近90天", "最近 30 天", "最近30天", "本月", "本周", "本季度"):
        if marker.replace(" ", "") in compact.replace(" ", ""):
            return marker if " " in marker else marker.replace("最近", "最近 ")
    return compact
