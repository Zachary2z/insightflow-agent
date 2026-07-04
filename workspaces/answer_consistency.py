from __future__ import annotations

from typing import Any

from workspaces.answer_evidence import (
    business_evidence_sentence,
    business_field_label,
    business_row_sentences,
    metric_tradeoff_summary,
    reason_hypothesis_context,
)
from workspaces.product_models import empty_business_answer


ADVICE_MARKERS = (
    "应该",
    "建议",
    "最值得",
    "更值得",
    "值得",
    "重点",
    "加预算",
    "减少预算",
    "increase",
    "reduce",
    "recommend",
)
COMPARISON_MARKERS = (
    "哪个",
    "最高",
    "最低",
    "对比",
    "排名",
    "best",
    "top",
    "lowest",
)
BUDGET_REDUCTION_MARKERS = (
    "减少预算",
    "减少",
    "降低",
    "削减",
    "转向",
    "reduce",
    "decrease",
    "cut",
)
TRADEOFF_MARKERS = ("取舍", "权衡", "判断口径", "不同指标", "如果目标", "decision basis", "tradeoff")
CHART_DECISION_MARKERS = ADVICE_MARKERS + (
    "最佳",
    "优先",
    "优先投入",
    "should",
    "best",
    "prioritize",
    "priority",
)
IMPROVE_RISK_MARKERS = (
    "优先复盘",
    "优先处理",
    "最需要处理",
    "最需要优先",
    "最值得关注",
    "风险",
    "改善",
    "改进",
    "客服问题",
    "业务问题",
    "问题最需要",
    "问题最多",
    "问题最严重",
    "表现最差",
    "最差",
    "短板",
    "预警",
)
GROWTH_BEST_MARKERS = (
    "表现最好",
    "最值得作为标杆",
    "作为标杆",
    "标杆",
    "加资源",
    "加预算",
    "增长投入",
    "表现最佳",
    "最佳",
    "最好",
    "最高",
    "领先",
    "优秀",
)

CHINESE_FACTUAL_CHART_ANNOTATION = "图表展示本轮查询返回的各对象指标对比，请结合业务结论中的判断口径解读。"
ENGLISH_FACTUAL_CHART_ANNOTATION = (
    "The chart compares returned metrics for this run. Use the business answer as the decision basis."
)


def apply_answer_consistency(
    *,
    user_question: str,
    business_answer: dict[str, Any],
    execution_result: dict[str, Any],
    evidence_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a P16 business_answer that is internally consistent and evidence-bound."""

    answer = _normalize_answer(business_answer)
    rows = _rows_as_dicts(execution_result)
    question = str(user_question or "")

    if _has_single_row_budget_reduction_risk(question, rows):
        return _single_row_budget_answer(question=question, answer=answer, rows=rows)

    direction = _decision_direction(question, answer)
    conflict = _multi_metric_conflict(question, rows)
    primary_metric = _primary_metric_key(question, rows)
    if conflict and primary_metric and not _answer_matches_primary_metric(answer, rows, primary_metric):
        return _primary_metric_answer(
            question=question,
            answer=answer,
            rows=rows,
            primary_metric=primary_metric,
        )
    directional_primary = _directional_primary_entity(rows, direction=direction)
    risk_direction_resolves_conflict = (
        direction == "improve_risk"
        and directional_primary
        and _risk_direction_resolves_conflict(question, rows, directional_primary)
    )
    if conflict and not primary_metric and not _has_tradeoff_language(answer) and not risk_direction_resolves_conflict:
        return _tradeoff_answer(
            answer=answer,
            conflict=conflict,
            chinese=_contains_cjk(question),
            include_recommendations=_should_include_recommendations(question),
            question=question,
        )

    alignment = _answer_evidence_alignment(question=question, answer=answer, rows=rows)
    if alignment:
        return alignment

    return answer


def safe_chart_annotation(
    *,
    annotation: str,
    business_answer: dict[str, Any],
    execution_result: dict[str, Any],
) -> str:
    """Return a chart annotation that does not contradict the final business answer."""

    text = _clean_annotation_text(annotation)
    if not text:
        return ""

    answer = _normalize_answer(business_answer)
    rows = _rows_as_dicts(execution_result)
    answer_text = _answer_text(answer)
    chinese = _contains_cjk(text) or _contains_cjk(answer_text)

    if _looks_like_raw_parameter_dump(text):
        return _factual_chart_annotation(chinese=chinese)
    if not _has_chart_decision_language(text):
        return text

    entities = _entity_values(rows)
    annotation_entities = _mentioned_entities(text, entities)
    answer_entities = _mentioned_entities(answer_text, entities)

    if not annotation_entities:
        return _factual_chart_annotation(chinese=chinese)
    if len(annotation_entities) == 1 and annotation_entities[0] not in answer_entities:
        return _factual_chart_annotation(chinese=chinese)
    if len(annotation_entities) == 1 and _has_tradeoff_language(answer):
        return _factual_chart_annotation(chinese=chinese)

    return text


def _normalize_answer(answer: dict[str, Any]) -> dict[str, Any]:
    normalized = empty_business_answer()
    normalized.update(
        {
            "headline": str(answer.get("headline") or ""),
            "direct_answer": str(answer.get("direct_answer") or ""),
            "why": str(answer.get("why") or ""),
            "evidence_bullets": _list_of_text(answer.get("evidence_bullets")),
            "recommendations": _list_of_text(answer.get("recommendations")),
            "caveats": _list_of_text(answer.get("caveats")),
            "confidence": str(answer.get("confidence") or "medium"),
        }
    )
    if normalized["confidence"] not in {"low", "medium", "high"}:
        normalized["confidence"] = "medium"
    return normalized


def _answer_text(answer: dict[str, Any]) -> str:
    return " ".join(
        [
            answer["headline"],
            answer["direct_answer"],
            answer["why"],
            *answer["evidence_bullets"],
            *answer["recommendations"],
            *answer["caveats"],
        ]
    )


def _rows_as_dicts(execution_result: dict[str, Any]) -> list[dict[str, Any]]:
    columns = [str(column) for column in execution_result.get("columns") or []]
    normalized: list[dict[str, Any]] = []
    for row in execution_result.get("rows") or []:
        if isinstance(row, dict):
            normalized.append({str(key): value for key, value in row.items() if str(key).strip()})
        elif isinstance(row, (list, tuple)):
            normalized.append(
                {
                    column: row[index]
                    for index, column in enumerate(columns)
                    if column.strip() and index < len(row)
                }
            )
    return normalized


def _has_single_row_budget_reduction_risk(question: str, rows: list[dict[str, Any]]) -> bool:
    if len(rows) != 1:
        return False
    lowered = question.lower()
    return (
        any(marker in lowered for marker in ADVICE_MARKERS)
        and any(marker in lowered for marker in BUDGET_REDUCTION_MARKERS)
    )


def _single_row_budget_answer(
    *,
    question: str,
    answer: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    row = rows[0] if rows else {}
    entity_value = _entity_value(row) or "当前对象"
    caveats = answer["caveats"] + ["仅返回 1 行，比较证据不足，不足以判断哪个对象应该减少或调整预算。"]
    if _contains_cjk(question):
        row_summary = _row_summary(row, chinese=True)
        answer.update(
            {
                "headline": f"仅能确认 {entity_value} 的当前结果，不能判断预算减少对象",
                "direct_answer": (
                    f"当前返回结果只显示 {entity_value} 一行，不能据此确定哪个对象应该减少预算。"
                    "需要补充完整对比数据后再判断预算调整对象。"
                ),
                "why": f"证据仅返回 1 行：{row_summary}；缺少其他对象的同口径对比。",
                "recommendations": ["补充完整对比数据后，再判断预算调整对象。"],
                "caveats": _dedupe(caveats),
                "confidence": "low",
            }
        )
        return answer

    row_summary = _row_summary(row, chinese=False)
    answer.update(
        {
            "headline": f"Only {entity_value} is shown, so budget reduction is not supported",
            "direct_answer": (
                f"The returned evidence only shows one row for {entity_value}. "
                "It is not enough to decide which item should reduce budget."
            ),
            "why": f"The evidence contains only one row: {row_summary}; comparable alternatives are missing.",
            "recommendations": ["Add complete comparison evidence before deciding budget changes."],
            "caveats": _dedupe(caveats),
            "confidence": "low",
        }
    )
    return answer


def _multi_metric_conflict(question: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(rows) < 2 or not _is_decision_question(question):
        return None
    entity_key = _entity_key(rows)
    if not entity_key:
        return None
    metrics = _numeric_metric_keys(rows, exclude=entity_key)
    if len(metrics) < 2:
        return None

    leaders: dict[str, tuple[str, float]] = {}
    for metric in metrics:
        leader = _metric_leader(rows, entity_key=entity_key, metric=metric)
        if leader:
            leaders[metric] = leader

    leader_names = {name for name, _value in leaders.values()}
    if len(leader_names) <= 1:
        return None
    return {"entity_key": entity_key, "leaders": leaders}


def _answer_evidence_alignment(
    *,
    question: str,
    answer: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    decision_text = _decision_text(answer)
    direction = _decision_direction(question, answer)
    if not rows or _has_tradeoff_language(answer):
        return None
    if not (_is_decision_question(question) or _has_decision_language(decision_text)):
        return None

    entity_key = _entity_key(rows)
    if not entity_key:
        if _has_decision_language(decision_text):
            return _insufficient_alignment_answer(question=question, answer=answer, rows=rows)
        return None

    entities = _entity_values(rows)
    if not entities:
        return None

    primary_entity = _supported_primary_entity(rows, direction=direction)
    if not primary_entity:
        if (
            _answer_has_entity_conflict(answer=answer, entities=entities)
            or _recommendation_entities(answer, entities)
            or _unknown_decision_entity_candidate(_decision_text(answer))
        ):
            return _insufficient_alignment_answer(question=question, answer=answer, rows=rows)
        return None

    if not _has_decision_language(decision_text):
        return None

    decision_entities = _mentioned_entities(decision_text, entities)
    recommendation_entities = _recommendation_entities(answer, entities)
    support_decision_entities = _support_decision_entities(answer, entities)
    focused_support_entities = _focused_support_entities(answer, entities)
    if not decision_entities and _unknown_decision_entity_candidate(decision_text):
        return _insufficient_alignment_answer(question=question, answer=answer, rows=rows)
    if len(recommendation_entities) == 1 and recommendation_entities[0] != primary_entity:
        return _ranked_evidence_answer(
            question=question,
            answer=answer,
            rows=rows,
            primary_entity=primary_entity,
            direction=direction,
        )
    if direction != "neutral_rank" and not recommendation_entities and len(decision_entities) != 1:
        return _ranked_evidence_answer(
            question=question,
            answer=answer,
            rows=rows,
            primary_entity=primary_entity,
            direction=direction,
        )
    if len(decision_entities) == 1 and decision_entities[0] != primary_entity:
        return _ranked_evidence_answer(
            question=question,
            answer=answer,
            rows=rows,
            primary_entity=primary_entity,
            direction=direction,
        )
    if decision_entities and support_decision_entities and set(decision_entities) != set(support_decision_entities):
        return _ranked_evidence_answer(
            question=question,
            answer=answer,
            rows=rows,
            primary_entity=primary_entity,
            direction=direction,
        )
    if (
        len(decision_entities) == 1
        and len(focused_support_entities) == 1
        and focused_support_entities[0] != decision_entities[0]
    ):
        return _ranked_evidence_answer(
            question=question,
            answer=answer,
            rows=rows,
            primary_entity=primary_entity,
            direction=direction,
        )
    return None


def _decision_text(answer: dict[str, Any]) -> str:
    return " ".join([answer["headline"], answer["direct_answer"], *answer["recommendations"]])


def _support_decision_entities(answer: dict[str, Any], entities: list[str]) -> list[str]:
    mentions: list[str] = []
    for sentence in _support_sentences(answer):
        if not _has_decision_language(sentence):
            continue
        for entity in _mentioned_entities(sentence, entities):
            if entity not in mentions:
                mentions.append(entity)
    return mentions


def _focused_support_entities(answer: dict[str, Any], entities: list[str]) -> list[str]:
    mentions: list[str] = []
    for sentence in _support_sentences(answer):
        for entity in _mentioned_entities(sentence, entities):
            if entity not in mentions:
                mentions.append(entity)
    return mentions if len(mentions) == 1 else []


def _recommendation_entities(answer: dict[str, Any], entities: list[str]) -> list[str]:
    return _mentioned_entities(" ".join(answer["recommendations"]), entities)


def _support_sentences(answer: dict[str, Any]) -> list[str]:
    texts = [answer["why"], *answer["evidence_bullets"]]
    sentences: list[str] = []
    for text in texts:
        parts = str(text or "").replace("；", "。").replace(";", ".").split("。")
        sentences.extend(part.strip() for part in parts if part.strip())
    return sentences


def _answer_has_entity_conflict(*, answer: dict[str, Any], entities: list[str]) -> bool:
    decision_entities = set(_mentioned_entities(_decision_text(answer), entities))
    support_entities = set(_support_decision_entities(answer, entities) or _focused_support_entities(answer, entities))
    return bool(decision_entities and support_entities and decision_entities != support_entities)


def _supported_primary_entity(rows: list[dict[str, Any]], *, direction: str = "neutral_rank") -> str:
    directional = _directional_primary_entity(rows, direction=direction)
    if directional:
        return directional

    entity_key = _entity_key(rows)
    if not entity_key:
        return ""
    metrics = _numeric_metric_keys(rows, exclude=entity_key)
    if not metrics:
        return ""

    leaders = []
    for metric in metrics:
        leader = _metric_leader(rows, entity_key=entity_key, metric=metric)
        if leader:
            leaders.append(leader[0])
    unique_leaders = list(dict.fromkeys(leaders))
    return unique_leaders[0] if len(unique_leaders) == 1 else ""


def _decision_direction(question: str, answer: dict[str, Any]) -> str:
    question_text = _compact_for_direction(question)
    answer_text = _compact_for_direction(_decision_text(answer))
    if any(_compact_for_direction(marker) in question_text for marker in GROWTH_BEST_MARKERS):
        return "growth_best"
    if any(_compact_for_direction(marker) in question_text for marker in IMPROVE_RISK_MARKERS):
        return "improve_risk"
    if any(_compact_for_direction(marker) in answer_text for marker in GROWTH_BEST_MARKERS):
        return "growth_best"
    if any(_compact_for_direction(marker) in answer_text for marker in IMPROVE_RISK_MARKERS):
        return "improve_risk"
    return "neutral_rank"


def _directional_primary_entity(rows: list[dict[str, Any]], *, direction: str) -> str:
    if direction not in {"improve_risk", "growth_best"} or len(rows) < 2:
        return ""
    entity_key = _entity_key(rows)
    if not entity_key:
        return ""

    scores: dict[str, int] = {}
    metric_count = 0
    for metric in _numeric_metric_keys(rows, exclude=entity_key):
        prefer_higher = _prefer_higher_for_decision(metric, direction=direction)
        if prefer_higher is None:
            continue
        candidates: list[tuple[str, float]] = []
        for row in rows:
            entity = str(row.get(entity_key) or "").strip()
            value = _to_number(row.get(metric))
            if entity and value is not None:
                candidates.append((entity, value))
        if len(candidates) < 2:
            continue
        metric_count += 1
        ordered = sorted(candidates, key=lambda item: item[1], reverse=prefer_higher)
        for rank, (entity, _value) in enumerate(ordered):
            scores[entity] = scores.get(entity, 0) + rank

    if not metric_count or not scores:
        return ""
    ranked = sorted(scores.items(), key=lambda item: item[1])
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return ""
    return ranked[0][0]


def _risk_direction_resolves_conflict(question: str, rows: list[dict[str, Any]], primary_entity: str) -> bool:
    entity_key = _entity_key(rows)
    if not entity_key:
        return False
    mentioned_supporting_metrics = 0
    directional_leaders: list[str] = []
    for metric in _numeric_metric_keys(rows, exclude=entity_key):
        prefer_higher = _prefer_higher_for_decision(metric, direction="improve_risk")
        if prefer_higher is None:
            continue
        leader = _directional_metric_leader(rows, entity_key=entity_key, metric=metric, prefer_higher=prefer_higher)
        if leader:
            directional_leaders.append(leader)
        if leader == primary_entity and _metric_mentioned_in_question(metric, question):
            mentioned_supporting_metrics += 1
    if mentioned_supporting_metrics >= 1:
        return True
    unique_leaders = set(directional_leaders)
    return bool(len(directional_leaders) >= 2 and unique_leaders == {primary_entity})


def _directional_metric_leader(
    rows: list[dict[str, Any]],
    *,
    entity_key: str,
    metric: str,
    prefer_higher: bool,
) -> str:
    candidates: list[tuple[str, float]] = []
    for row in rows:
        entity = str(row.get(entity_key) or "").strip()
        value = _to_number(row.get(metric))
        if entity and value is not None:
            candidates.append((entity, value))
    if not candidates:
        return ""
    return sorted(candidates, key=lambda item: item[1], reverse=prefer_higher)[0][0]


def _metric_mentioned_in_question(metric: str, question: str) -> bool:
    question_text = _compact_for_direction(question)
    metric_text = _compact_for_direction(metric)
    token_groups = (
        ("response", "响应", "duration", "时长", "minutes", "分钟"),
        ("satisfaction", "满意", "nps", "评分", "score"),
        ("sales", "revenue", "gmv", "销售", "收入", "营收", "成交"),
        ("grossmargin", "margin", "毛利", "利润率"),
        ("repeat", "repurchase", "复购", "留存"),
        ("quantity", "qty", "销量", "销售量"),
        ("amount", "paid", "成交", "金额"),
        ("complaint", "投诉"),
        ("ticket", "工单"),
        ("cost", "spend", "成本", "花费", "费用"),
        ("roi", "roas", "投产", "回报"),
    )
    for group in token_groups:
        compact_group = [_compact_for_direction(token) for token in group]
        if any(token in metric_text for token in compact_group) and any(token in question_text for token in compact_group):
            return True
    return metric_text and metric_text in question_text


def _primary_metric_key(question: str, rows: list[dict[str, Any]]) -> str:
    entity_key = _entity_key(rows)
    if not entity_key:
        return ""
    mentioned = [
        metric
        for metric in _numeric_metric_keys(rows, exclude=entity_key)
        if _metric_mentioned_in_question(metric, question)
    ]
    return mentioned[0] if len(mentioned) == 1 else ""


def _answer_matches_primary_metric(answer: dict[str, Any], rows: list[dict[str, Any]], primary_metric: str) -> bool:
    entity_key = _entity_key(rows)
    leader = _metric_leader(rows, entity_key=entity_key, metric=primary_metric) if entity_key else None
    if not leader:
        return False
    leader_name, _value = leader
    first_sentence = str(answer.get("direct_answer") or "").split("。", 1)[0].split(".", 1)[0]
    return leader_name in first_sentence and _metric_label(primary_metric, chinese=_contains_cjk(first_sentence)) in first_sentence


def _primary_metric_answer(
    *,
    question: str,
    answer: dict[str, Any],
    rows: list[dict[str, Any]],
    primary_metric: str,
) -> dict[str, Any]:
    chinese = _contains_cjk(question) or _contains_cjk(_answer_text(answer))
    entity_key = _entity_key(rows)
    leader = _metric_leader(rows, entity_key=entity_key, metric=primary_metric) if entity_key else None
    if not leader:
        return answer
    leader_name, value = leader
    label = _metric_label(primary_metric, chinese=chinese)
    formatted = _format_metric_value(value, metric=primary_metric)
    row = _row_for_entity(rows, leader_name) or {}
    context = _row_summary(row, chinese=chinese)
    evidence_bullets = _ranked_row_bullets(rows, chinese=chinese)
    if chinese:
        recommendations = answer["recommendations"]
        if _recommendation_entities(answer, _entity_values(rows)) and leader_name not in " ".join(recommendations):
            recommendations = [f"围绕 {leader_name} 做下一步评估，并用{label}继续跟踪。"]
        answer.update(
            {
                "headline": f"{leader_name}{label}最高",
                "direct_answer": f"{leader_name}{label}最高，为 {formatted}。",
                "why": f"本轮证据按{label}排序，{leader_name}领先；{context}。",
                "evidence_bullets": evidence_bullets,
                "recommendations": recommendations,
                "confidence": "medium" if answer["confidence"] == "high" else answer["confidence"],
            }
        )
        return answer
    recommendations = answer["recommendations"]
    if _recommendation_entities(answer, _entity_values(rows)) and leader_name not in " ".join(recommendations):
        recommendations = [f"Evaluate the next decision around {leader_name} and keep tracking {label}."]
    answer.update(
        {
            "headline": f"{leader_name} has the highest {label}",
            "direct_answer": f"{leader_name} has the highest {label} at {formatted}.",
            "why": f"The returned evidence ranks {leader_name} first by {label}: {context}.",
            "evidence_bullets": evidence_bullets,
            "recommendations": recommendations,
            "confidence": "medium" if answer["confidence"] == "high" else answer["confidence"],
        }
    )
    return answer


def _prefer_higher_for_decision(metric: str, *, direction: str) -> bool | None:
    polarity = _metric_polarity(metric)
    if not polarity:
        return None
    if direction == "improve_risk":
        return polarity in {"risk", "negative"}
    if direction == "growth_best":
        return polarity == "positive"
    return None


def _metric_polarity(metric: str) -> str:
    text = _compact_for_direction(metric)
    if any(marker in text for marker in ("priority", "优先级", "complaint", "投诉", "ticket", "工单")):
        return "risk"
    if any(marker in text for marker in ("response", "响应", "duration", "时长", "minutes", "分钟", "resolution", "解决")):
        return "negative"
    if any(marker in text for marker in ("cost", "spend", "成本", "花费", "费用", "投放金额")):
        return "negative"
    if any(
        marker in text
        for marker in (
            "sales",
            "revenue",
            "gmv",
            "销售",
            "收入",
            "营收",
            "成交",
            "grossmargin",
            "margin",
            "毛利",
            "利润率",
            "满意",
            "satisfaction",
            "nps",
            "score",
            "评分",
            "roi",
            "roas",
            "conversion",
            "转化",
        )
    ):
        return "positive"
    return ""


def _compact_for_direction(text: str) -> str:
    return str(text or "").lower().replace(" ", "").replace("_", "").replace("-", "")


def _has_decision_language(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in CHART_DECISION_MARKERS)


def _ranked_evidence_answer(
    *,
    question: str,
    answer: dict[str, Any],
    rows: list[dict[str, Any]],
    primary_entity: str,
    direction: str = "neutral_rank",
) -> dict[str, Any]:
    chinese = _contains_cjk(question) or _contains_cjk(_answer_text(answer))
    primary_row = _row_for_entity(rows, primary_entity) or (rows[0] if rows else {})
    row_summary = _row_summary(primary_row, chinese=chinese)
    evidence_sentence = business_evidence_sentence(rows, chinese=chinese) or f"{row_summary}。"
    evidence_bullets = _ranked_row_bullets(rows, chinese=chinese)
    decision_noun = _decision_noun(direction=direction, chinese=chinese)
    why_basis = _decision_why_basis(direction=direction, chinese=chinese)
    caveats = _dedupe(
        answer["caveats"]
        + [
            (
                "原回答的推荐对象与排序证据不一致，已按本轮执行结果校正。"
                if chinese
                else "The original recommendation named a different entity than the ranked evidence, so it was corrected from this run."
            )
        ]
    )
    confidence = "medium" if answer["confidence"] == "high" else answer["confidence"]

    if chinese:
        answer.update(
            {
                "headline": f"当前证据最支持优先{decision_noun} {primary_entity}",
                "direct_answer": f"当前数据支持优先{decision_noun} {primary_entity}，{row_summary}。",
                "why": f"当前数据中，{primary_entity}{why_basis}；完整对比见证据说明。",
                "evidence_bullets": evidence_bullets,
                "recommendations": [f"围绕 {primary_entity} 做下一步{decision_noun}，并用相同指标继续跟踪。"],
                "caveats": caveats,
                "confidence": confidence,
            }
        )
        return answer

    answer.update(
        {
            "headline": f"The current evidence most supports prioritizing {primary_entity}",
            "direct_answer": (
                f"The current data most supports prioritizing {primary_entity}; {row_summary}. "
                f"So the recommendation should prioritize {primary_entity}."
            ),
            "why": f"The current data shows {primary_entity} as the evidence-supported priority: {row_summary}.",
            "evidence_bullets": evidence_bullets,
            "recommendations": [f"Evaluate the next resource decision around {primary_entity} using the same metrics."],
            "caveats": caveats,
            "confidence": confidence,
        }
    )
    return answer


def _row_for_entity(rows: list[dict[str, Any]], entity: str) -> dict[str, Any] | None:
    for row in rows:
        if _entity_value(row) == entity:
            return row
    return None


def _decision_noun(*, direction: str, chinese: bool) -> str:
    if not chinese:
        return "review" if direction == "improve_risk" else "evaluate"
    if direction == "improve_risk":
        return "复盘"
    return "评估"


def _decision_why_basis(*, direction: str, chinese: bool) -> str:
    if not chinese:
        return "has the strongest directional support"
    if direction == "improve_risk":
        return "在风险或改善指标上更需要关注"
    if direction == "growth_best":
        return "在主要正向指标上领先"
    return "在主要排序指标上领先"


def _insufficient_alignment_answer(
    *,
    question: str,
    answer: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    chinese = _contains_cjk(question) or _contains_cjk(_answer_text(answer))
    evidence_bullets = _ranked_row_bullets(rows, chinese=chinese)
    evidence_scope = _evidence_scope(rows, chinese=chinese)
    caveat = (
        "当前证据没有包含可验证的推荐对象，因此不能支持原先的确定性结论。"
        if chinese
        else "The current evidence does not include a verifiable recommended entity, so the original conclusion is not supported."
    )

    if chinese:
        answer.update(
            {
                "headline": "当前证据不足以支持该结论",
                "direct_answer": "当前证据不足以支持该结论。执行结果没有返回能够支撑原确定性建议的对象记录，需要补充同口径证据后再判断。",
                "why": f"本轮证据范围为：{evidence_scope}。",
                "evidence_bullets": evidence_bullets,
                "recommendations": ["先补充包含推荐对象的同口径数据，或按当前证据表重新排序后再决定。"],
                "caveats": _dedupe(answer["caveats"] + [caveat]),
                "confidence": "low",
            }
        )
        return answer

    answer.update(
        {
            "headline": "Current evidence is insufficient for that conclusion",
            "direct_answer": (
                "The current evidence is insufficient for that conclusion. The executed result does not return "
                "a verifiable row supporting the original definitive recommendation."
            ),
            "why": f"This run only provides evidence for: {evidence_scope}.",
            "evidence_bullets": evidence_bullets,
            "recommendations": [
                "Add comparable evidence for the recommended entity, or rerank using the current evidence before deciding."
            ],
            "caveats": _dedupe(answer["caveats"] + [caveat]),
            "confidence": "low",
        }
    )
    return answer


def _ranked_row_bullets(rows: list[dict[str, Any]], *, chinese: bool, limit: int = 3) -> list[str]:
    return business_row_sentences(rows, chinese=chinese, limit=limit)


def _evidence_scope(rows: list[dict[str, Any]], *, chinese: bool) -> str:
    entities = _entity_values(rows)
    if entities:
        return "、".join(entities[:5]) if chinese else ", ".join(entities[:5])
    return "没有可识别的维度对象" if chinese else "no identifiable dimension entity"


def _unknown_decision_entity_candidate(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    for marker in ("投入", "加码", "加到", "分配给", "给"):
        candidate = _candidate_after_marker(value, marker)
        if _looks_like_entity_candidate(candidate):
            return candidate
    lowered = value.lower()
    for marker in ("prioritize", "recommend", "increase", "invest in", "allocate to", "for"):
        index = lowered.find(marker)
        if index >= 0:
            candidate = value[index + len(marker):].strip(" :：,，。.")
            candidate = candidate.split(",", 1)[0].split(".", 1)[0].strip()
            if _looks_like_entity_candidate(candidate):
                return candidate
    return ""


def _candidate_after_marker(text: str, marker: str) -> str:
    index = text.find(marker)
    if index < 0:
        return ""
    candidate = text[index + len(marker):].strip(" :：,，。.")
    for stop in ("，", "。", "；", ";", " because ", " 因为", "，因为", "。因为"):
        if stop in candidate:
            candidate = candidate.split(stop, 1)[0]
    return candidate.strip()


def _looks_like_entity_candidate(text: str) -> bool:
    candidate = str(text or "").strip()
    if not candidate or len(candidate) > 24:
        return False
    generic_terms = {
        "预算",
        "资源",
        "加预算",
        "下一轮资源",
        "当前对象",
        "该对象",
        "the budget",
        "budget",
        "resources",
        "the next step",
    }
    if candidate.lower() in generic_terms:
        return False
    return any(char.isalpha() or "\u4e00" <= char <= "\u9fff" for char in candidate)


def _is_decision_question(question: str) -> bool:
    lowered = question.lower()
    return any(marker in lowered for marker in ADVICE_MARKERS + COMPARISON_MARKERS)


def _is_budget_question(question: str) -> bool:
    lowered = question.lower()
    return any(marker in lowered for marker in ("预算", "投放", "budget", "spend"))


def _tradeoff_answer(
    *,
    answer: dict[str, Any],
    conflict: dict[str, Any],
    chinese: bool,
    include_recommendations: bool,
    question: str = "",
) -> dict[str, Any]:
    leaders: dict[str, tuple[str, float]] = conflict["leaders"]
    leader_sentences = _leader_sentences_from_conflict(conflict, chinese=chinese)
    leader_summary = "；".join(sentence.rstrip("。.") for sentence in leader_sentences)
    caveat = "不同数值指标指向不同对象，需要先明确决策口径，不能只用单一最高值下结论。"
    recommendations = ["先明确重点运营口径，再按该口径决定资源倾斜对象。"] if include_recommendations else []

    if chinese:
        hypothesis = reason_hypothesis_context(question, [], chinese=True)
        answer.update(
            {
                "headline": "不同指标领先对象不同，需要按判断口径取舍",
                "direct_answer": leader_summary + "。因此需要先明确决策口径，再判断谁最值得重点投入。",
                "why": (
                    "本次证据显示多个指标的领先对象不一致："
                    + leader_summary
                    + "。当前数据只能确认指标高低，不能直接证明原因。"
                    + f"可能方向包括：{hypothesis}，但需要补充过程数据进一步验证。"
                ),
                "evidence_bullets": leader_sentences,
                "recommendations": recommendations,
                "caveats": _dedupe(answer["caveats"] + [caveat]),
                "confidence": "medium" if answer["confidence"] == "high" else answer["confidence"],
            }
        )
        return answer

    answer.update(
        {
            "headline": "Different metrics point to different leaders",
            "direct_answer": (
                "The answer depends on the decision basis: "
                + " ".join(leader_sentences)
                + ". Choose the priority metric before naming a single winner."
            ),
            "why": "The evidence has a multi-metric tradeoff: " + " ".join(leader_sentences),
            "evidence_bullets": leader_sentences,
            "recommendations": ["Choose the decision basis before shifting resources."] if include_recommendations else [],
            "caveats": _dedupe(answer["caveats"] + ["Different numeric metrics point to different leaders."]),
            "confidence": "medium" if answer["confidence"] == "high" else answer["confidence"],
        }
    )
    return answer


def _should_include_recommendations(question: str) -> bool:
    lowered = str(question or "").lower()
    if any(marker in lowered for marker in ("只回答事实", "不用建议", "不需要建议", "不要建议", "只看事实")):
        return False
    return any(marker in lowered for marker in ADVICE_MARKERS + ("优化", "下一步", "优先处理", "priority", "prioritize"))


def _leader_sentences_from_conflict(conflict: dict[str, Any], *, chinese: bool) -> list[str]:
    leaders: dict[str, tuple[str, float]] = conflict["leaders"]
    if not chinese:
        return [_leader_sentence(metric=metric, name=name, value=value, chinese=False) for metric, (name, value) in leaders.items()]
    rows = []
    entity_key = str(conflict.get("entity_key") or "entity")
    metrics = list(leaders)
    for metric, (name, value) in leaders.items():
        row = {entity_key: name}
        for candidate in metrics:
            if candidate == metric:
                row[candidate] = value
        rows.append(row)
    shared = metric_tradeoff_summary(rows, chinese=chinese, metric_key_values=metrics)
    if len(shared) == len(metrics):
        return shared
    return [_leader_sentence(metric=metric, name=name, value=value, chinese=chinese) for metric, (name, value) in leaders.items()]


def _leader_sentence(*, metric: str, name: str, value: float, chinese: bool) -> str:
    label = _metric_label(metric, chinese=chinese)
    formatted_value = _format_metric_value(value, metric=metric)
    if chinese:
        return f"按{label}看，{name}领先，数值为 {formatted_value}。"
    return f"By {label}, {name} leads with {formatted_value}."


def _metric_label(metric: str, *, chinese: bool) -> str:
    label = business_field_label(metric, chinese=chinese)
    lowered = str(metric or "").lower()
    if not chinese and label == "total revenue":
        return "revenue"
    if not chinese and label == "order count":
        return "orders"
    if not chinese and lowered == "avg_revenue_per_order":
        return "average order revenue"
    return label or ("该指标" if chinese else "the metric")


def _format_metric_value(value: float, *, metric: str = "") -> str:
    if float(value).is_integer():
        return f"{int(value):,}"
    decimals = 3 if "roi" in str(metric or "").lower() or abs(value) < 1 else 2
    return f"{value:,.{decimals}f}".rstrip("0").rstrip(".")


def _entity_key(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        for key, value in row.items():
            if not _is_number(value):
                return key
    return ""


def _entity_value(row: dict[str, Any]) -> str:
    key = _entity_key([row])
    return str(row.get(key) or "").strip() if key else ""


def _entity_values(rows: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for row in rows:
        value = _entity_value(row)
        if value and value not in values:
            values.append(value)
    return values


def _mentioned_entities(text: str, entities: list[str]) -> list[str]:
    return [entity for entity in entities if entity and entity in text]


def _numeric_metric_keys(rows: list[dict[str, Any]], *, exclude: str) -> list[str]:
    keys: list[str] = []
    for row in rows:
        for key, value in row.items():
            if key != exclude and key not in keys and _is_number(value):
                keys.append(key)
    return keys


def _metric_leader(
    rows: list[dict[str, Any]],
    *,
    entity_key: str,
    metric: str,
) -> tuple[str, float] | None:
    candidates: list[tuple[str, float]] = []
    for row in rows:
        entity = str(row.get(entity_key) or "").strip()
        value = _to_number(row.get(metric))
        if entity and value is not None:
            candidates.append((entity, value))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1])


def _row_summary(row: dict[str, Any], *, chinese: bool = True) -> str:
    relation = " 为 " if chinese else " is "
    separator = "，" if chinese else ", "
    pairs = [f"{business_field_label(key, chinese=chinese)}{relation}{value}" for key, value in list(row.items())[:4]]
    if pairs:
        return separator.join(pairs)
    return "当前证据没有可展示字段" if chinese else "the current evidence has no displayable fields"


def _has_tradeoff_language(answer: dict[str, Any]) -> bool:
    text = " ".join(
        [
            answer["headline"],
            answer["direct_answer"],
            answer["why"],
            *answer["evidence_bullets"],
            *answer["recommendations"],
            *answer["caveats"],
        ]
    ).lower()
    return any(marker in text for marker in TRADEOFF_MARKERS)


def _is_number(value: Any) -> bool:
    return _to_number(value) is not None


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
    return None


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(text or ""))


def _has_chart_decision_language(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in CHART_DECISION_MARKERS)


def _clean_annotation_text(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def _factual_chart_annotation(*, chinese: bool) -> str:
    return CHINESE_FACTUAL_CHART_ANNOTATION if chinese else ENGLISH_FACTUAL_CHART_ANNOTATION


def _looks_like_raw_parameter_dump(text: str) -> bool:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return False
    dump_lines = 0
    for line in lines:
        stripped = line.lstrip("-*0123456789.) ")
        assignments = [
            part for part in stripped.replace("，", ",").split(",") if "=" in part and part.split("=", 1)[0].strip()
        ]
        if len(assignments) >= 1:
            dump_lines += 1
    return dump_lines >= max(1, len(lines) // 2)


def _list_of_text(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
