from __future__ import annotations

import re
from typing import Any


TREND_TERMS = ("趋势", "走势", "同比", "环比", "变化", "trend")
GRAIN_TERMS = (
    "按天",
    "按日",
    "按周",
    "按月",
    "按季度",
    "按季",
    "按年",
    "每天",
    "每日",
    "每周",
    "每月",
    "每季度",
    "每季",
    "每年",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "yearly",
)


def explicit_time_range_text(text: str) -> str:
    value = str(text or "")
    match = re.search(r"(?:最近|近)\s*([0-9]+|[一二两三四五六七八九十百零〇]+)\s*天", value)
    if match:
        days = _parse_number(match.group(1))
        return f"最近{days}天" if days else f"最近{match.group(1)}天"
    match = re.search(r"(?:最近|近)\s*([0-9]+|[一二两三四五六七八九十百零〇]+)\s*个?月", value)
    if match:
        months = _parse_number(match.group(1))
        return f"最近{months}个月" if months else f"最近{match.group(1)}个月"
    if "本季度" in value:
        return "本季度"
    if "本月" in value:
        return "本月"
    if "本周" in value:
        return "本周"
    return ""


def resolve_time_default(
    *,
    text: str,
    workspace_context: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
    semantic_layer: dict[str, Any] | None = None,
    task_type: str = "",
) -> dict[str, Any]:
    if _needs_trend_grain(text, task_type=task_type):
        return {
            "action": "clarify",
            "missing_slot": "time_grain",
            "reason": "趋势、同比、环比或变化类问题需要先确认分析粒度。",
        }

    if explicit_time_range_text(text):
        return {"action": "explicit"}

    candidates = _time_field_candidates(
        workspace_context=workspace_context,
        profile=profile,
        semantic_layer=semantic_layer,
    )
    if len(candidates) > 1:
        return {
            "action": "clarify",
            "missing_slot": "date_field",
            "candidates": candidates,
            "reason": "当前数据存在多个可能的时间字段，直接默认会改变业务含义。",
        }
    if len(candidates) == 1:
        candidate = candidates[0]
        start = str(candidate.get("start") or "").strip()
        end = str(candidate.get("end") or "").strip()
        if start and end:
            raw_text = f"完整数据时间范围：{start} 至 {end}"
            return {
                "action": "apply",
                "time_range": {
                    "type": "full_data_range",
                    "raw_text": raw_text,
                    "start": start,
                    "end": end,
                    "field": str(candidate.get("field") or ""),
                    "reason": "用户未指定时间范围，默认使用数据集中完整可用时间范围。",
                },
                "default_note": f"用户未指定时间范围，默认使用数据集中完整可用时间范围：{start} 至 {end}。",
            }
    return {"action": "none"}


def report_time_range_for_goal(
    *,
    report_goal: str,
    profile: dict[str, Any],
    semantic_layer: dict[str, Any],
) -> dict[str, Any]:
    explicit = explicit_time_range_text(report_goal)
    if explicit:
        return {"time_range": explicit, "default_note": "", "defaulted": False}
    decision = resolve_time_default(
        text="",
        profile=profile,
        semantic_layer=semantic_layer,
        task_type="report",
    )
    if decision.get("action") == "apply":
        return {
            "time_range": str((decision.get("time_range") or {}).get("raw_text") or ""),
            "default_note": str(decision.get("default_note") or ""),
            "defaulted": True,
        }
    if decision.get("action") == "clarify":
        return {
            "action": "clarify",
            "time_range": "",
            "default_note": "",
            "defaulted": False,
            "missing_slots": [str(decision.get("missing_slot") or "")],
            "clarification_questions": [_clarification_question_for_decision(decision)],
            "candidates": list(decision.get("candidates") or []),
            "reason": str(decision.get("reason") or ""),
        }
    return {"time_range": "当前工作区全部可用数据", "default_note": "用户未指定时间范围，本报告基于当前工作区全部可用记录。", "defaulted": True}


def full_range_default_note(time_range: Any) -> str:
    if not isinstance(time_range, dict):
        return ""
    if time_range.get("type") != "full_data_range":
        return ""
    start = str(time_range.get("start") or "").strip()
    end = str(time_range.get("end") or "").strip()
    if not (start and end):
        return ""
    return f"你没有指定时间范围，本次默认使用数据集中完整可用时间范围：{start} 至 {end}。"


def _needs_trend_grain(text: str, *, task_type: str = "") -> bool:
    compact = _compact(text)
    if task_type != "trend" and not any(_compact(term) in compact for term in TREND_TERMS):
        return False
    return not any(_compact(term) in compact for term in GRAIN_TERMS)


def _clarification_question_for_decision(decision: dict[str, Any]) -> str:
    if decision.get("missing_slot") == "date_field":
        names = [
            str(item.get("name") or item.get("field") or "").strip()
            for item in decision.get("candidates") or []
            if isinstance(item, dict) and str(item.get("name") or item.get("field") or "").strip()
        ]
        if names:
            return f"当前数据存在多个可能的时间字段，请指定使用哪个时间字段，例如 { ' 或 '.join(names[:3]) }。"
        return "当前数据存在多个可能的时间字段，请指定使用哪个时间字段。"
    if decision.get("missing_slot") == "time_grain":
        return "你希望按天、周还是月查看趋势？"
    return str(decision.get("reason") or "请补充必要信息后再生成。")


def _time_field_candidates(
    *,
    workspace_context: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
    semantic_layer: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    semantic_fields = []
    if workspace_context:
        semantic_fields.extend(
            item for item in workspace_context.get("semantic_time_fields") or [] if isinstance(item, dict)
        )
    if semantic_layer:
        semantic_fields.extend(item for item in semantic_layer.get("time_fields") or [] if isinstance(item, dict))

    ranges = _profile_time_ranges(workspace_context=workspace_context, profile=profile)
    candidates: list[dict[str, str]] = []
    for field in semantic_fields:
        if field.get("enabled") is False:
            continue
        qualified = _qualified_field(field)
        if not qualified:
            continue
        value_range = ranges.get(qualified) or ranges.get(qualified.split(".")[-1], {})
        start = _normalize_date(value_range.get("min"))
        end = _normalize_date(value_range.get("max"))
        candidates.append(
            {
                "field": qualified,
                "name": str(field.get("name") or qualified.split(".")[-1]),
                "label": str(field.get("label") or field.get("business_label") or field.get("name") or qualified),
                "start": start,
                "end": end,
            }
        )
    return _dedupe_candidates(candidates)


def _profile_time_ranges(
    *,
    workspace_context: dict[str, Any] | None,
    profile: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    ranges: dict[str, dict[str, Any]] = {}
    for source in (workspace_context or {}, profile or {}):
        for table in source.get("tables") or []:
            if not isinstance(table, dict):
                continue
            table_name = str(table.get("table_name") or "")
            for column in table.get("columns") or []:
                if not isinstance(column, dict):
                    continue
                value_range = column.get("value_range") if isinstance(column.get("value_range"), dict) else {}
                if not value_range:
                    continue
                column_name = str(column.get("name") or "")
                if not column_name:
                    continue
                ranges[column_name] = value_range
                if table_name:
                    ranges[f"{table_name}.{column_name}"] = value_range
    return ranges


def _qualified_field(field: dict[str, Any]) -> str:
    qualified = str(field.get("field") or "").strip()
    if qualified:
        return qualified
    table = str(field.get("table") or "").strip()
    name = str(field.get("name") or "").strip()
    return f"{table}.{name}" if table and name else name


def _normalize_date(value: Any) -> str:
    text = str(value or "").strip()
    match = re.match(r"(\d{4})[-/](\d{1,2})(?:[-/](\d{1,2}))?", text)
    if match:
        year, month, day = match.groups()
        if day:
            return f"{year}-{int(month):02d}-{int(day):02d}"
        return f"{year}-{int(month):02d}"
    match = re.match(r"(\d{4})(\d{2})(\d{2})$", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    return text


def _parse_number(value: str) -> int | None:
    text = str(value or "").strip()
    if text.isdigit():
        return int(text)
    if not text:
        return None
    numerals = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    if text == "十":
        return 10
    if "百" in text:
        left, _, right = text.partition("百")
        hundreds = numerals.get(left, 1 if not left else 0)
        tail = _parse_number(right) if right else 0
        return hundreds * 100 + (tail or 0)
    if "十" in text:
        left, _, right = text.partition("十")
        tens = numerals.get(left, 1 if not left else 0)
        ones = numerals.get(right, 0) if right else 0
        return tens * 10 + ones
    if all(char in numerals for char in text):
        number = 0
        for char in text:
            number = number * 10 + numerals[char]
        return number
    return None


def _dedupe_candidates(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen = set()
    for candidate in candidates:
        key = str(candidate.get("field") or candidate.get("name") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def _compact(value: Any) -> str:
    return re.sub(r"[\s_\-（）()。,.，:：]+", "", str(value or "").lower())
