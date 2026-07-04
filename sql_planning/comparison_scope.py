from __future__ import annotations

import re
from typing import Any


_SINGLE_ROW_LIMIT_RE = re.compile(r"\blimit\s+1\s*(?:offset\s+0\s*)?(?P<semicolon>;)?\s*$", re.IGNORECASE)

_EXPLICIT_SINGLE_RESULT_MARKERS = (
    "只给第一名",
    "只返回第一名",
    "只要第一名",
    "只看第一名",
    "只返回一个",
    "只给一个",
    "只要一个",
    "只返回一行",
    "只给一行",
    "第一名即可",
    "top 1 only",
    "only top 1",
    "only one",
)

_COMPARISON_MARKERS = (
    "哪个",
    "哪一个",
    "谁",
    "最高",
    "最低",
    "最多",
    "最少",
    "最好",
    "最差",
    "排名",
    "对比",
    "比较",
    "best",
    "worst",
    "top",
    "lowest",
)

_WHY_MARKERS = ("为什么", "原因", "why")
_DECISION_MARKERS = (
    "建议",
    "推荐",
    "应该",
    "优先",
    "最需要",
    "值得",
    "关注",
    "复盘",
    "预算",
    "优化",
    "priority",
    "prioritize",
    "recommend",
    "should",
    "budget",
)


def _compact(value: Any) -> str:
    return re.sub(r"[\s_\-（）()。,.，:：]+", "", str(value or "").lower())


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    compact = _compact(text)
    return any(_compact(marker) in compact for marker in markers)


def requires_comparison_scope(
    question: str,
    *,
    analysis_task: dict[str, Any] | None = None,
    question_understanding: dict[str, Any] | None = None,
) -> bool:
    """Return whether the question needs multiple comparable rows before judgment."""

    if not str(question or "").strip():
        return False
    if _contains_any(question, _EXPLICIT_SINGLE_RESULT_MARKERS):
        return False

    analysis_task = analysis_task or {}
    question_understanding = question_understanding or {}
    task_type = str(analysis_task.get("task_type") or "").lower()
    operation = str((question_understanding.get("intent") or {}).get("operation") or "").lower()
    if task_type in {"recommendation", "compare", "anomaly"} or operation in {"recommendation", "compare", "comparison"}:
        return True
    if str(analysis_task.get("decision_goal") or "").strip():
        return True

    has_decision = _contains_any(question, _DECISION_MARKERS)
    has_why = _contains_any(question, _WHY_MARKERS)
    has_comparison = _contains_any(question, _COMPARISON_MARKERS)
    return has_decision or (has_why and has_comparison)


def sql_has_single_row_limit(sql: str) -> bool:
    return bool(_SINGLE_ROW_LIMIT_RE.search(str(sql or "").strip()))


def widen_comparison_limit(sql: str, *, default_limit: int = 3) -> str:
    text = str(sql or "").strip()
    if not sql_has_single_row_limit(text):
        return text
    match = _SINGLE_ROW_LIMIT_RE.search(text)
    semicolon = ";" if match and match.group("semicolon") else ""
    return _SINGLE_ROW_LIMIT_RE.sub(f"LIMIT {int(default_limit)}{semicolon}", text)


def widen_sql_for_comparison_scope(
    sql: str,
    *,
    question: str,
    analysis_task: dict[str, Any] | None = None,
    question_understanding: dict[str, Any] | None = None,
    default_limit: int = 3,
) -> tuple[str, dict[str, Any]]:
    needs_scope = requires_comparison_scope(
        question,
        analysis_task=analysis_task,
        question_understanding=question_understanding,
    )
    single_limit = sql_has_single_row_limit(sql)
    if not needs_scope or not single_limit:
        return str(sql or "").strip(), {
            "applied": False,
            "reason": "",
            "requires_comparison_scope": needs_scope,
            "single_row_limit": single_limit,
            "limit": None,
        }

    widened = widen_comparison_limit(sql, default_limit=default_limit)
    return widened, {
        "applied": True,
        "reason": "insufficient_comparison_scope",
        "requires_comparison_scope": True,
        "single_row_limit": True,
        "original_limit": 1,
        "limit": int(default_limit),
    }
