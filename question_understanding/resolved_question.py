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

    return f"{original}。补充条件：{answer}。请完成分析并给出业务建议。"


def _clean(value: str) -> str:
    return " ".join(str(value or "").split()).strip(" 。")
