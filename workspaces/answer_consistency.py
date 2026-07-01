from __future__ import annotations

from typing import Any

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
TRADEOFF_MARKERS = ("取舍", "权衡", "口径", "如果目标", "decision basis", "tradeoff")
CHART_DECISION_MARKERS = ADVICE_MARKERS + (
    "最佳",
    "优先",
    "优先投入",
    "should",
    "best",
    "prioritize",
    "priority",
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

    conflict = _multi_metric_conflict(question, rows)
    if conflict and not _has_tradeoff_language(answer):
        return _tradeoff_answer(answer=answer, conflict=conflict, chinese=_contains_cjk(question))

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
    row_summary = _row_summary(row)
    caveats = answer["caveats"] + ["仅返回 1 行，比较证据不足，不足以判断哪个对象应该减少或调整预算。"]
    if _contains_cjk(question):
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
    if _is_budget_question(question):
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
    if not rows or not _is_decision_question(question) or _has_tradeoff_language(answer):
        return None

    entity_key = _entity_key(rows)
    if not entity_key:
        if _has_decision_language(_decision_text(answer)):
            return _insufficient_alignment_answer(question=question, answer=answer, rows=rows)
        return None

    entities = _entity_values(rows)
    if not entities:
        return None

    primary_entity = _supported_primary_entity(rows)
    if not primary_entity:
        if (
            _answer_has_entity_conflict(answer=answer, entities=entities)
            or _recommendation_entities(answer, entities)
            or _unknown_decision_entity_candidate(_decision_text(answer))
        ):
            return _insufficient_alignment_answer(question=question, answer=answer, rows=rows)
        return None

    decision_text = _decision_text(answer)
    if not _has_decision_language(decision_text):
        return None

    decision_entities = _mentioned_entities(decision_text, entities)
    support_entities = _support_decision_entities(answer, entities)
    if len(decision_entities) == 1 and decision_entities[0] != primary_entity:
        return _ranked_evidence_answer(
            question=question,
            answer=answer,
            rows=rows,
            primary_entity=primary_entity,
        )
    if decision_entities and support_entities and set(decision_entities) != set(support_entities):
        return _ranked_evidence_answer(
            question=question,
            answer=answer,
            rows=rows,
            primary_entity=primary_entity,
        )
    if not decision_entities and _unknown_decision_entity_candidate(decision_text):
        return _insufficient_alignment_answer(question=question, answer=answer, rows=rows)
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
    support_entities = set(_support_decision_entities(answer, entities))
    return bool(decision_entities and support_entities and decision_entities != support_entities)


def _supported_primary_entity(rows: list[dict[str, Any]]) -> str:
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


def _has_decision_language(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in CHART_DECISION_MARKERS)


def _ranked_evidence_answer(
    *,
    question: str,
    answer: dict[str, Any],
    rows: list[dict[str, Any]],
    primary_entity: str,
) -> dict[str, Any]:
    chinese = _contains_cjk(question) or _contains_cjk(_answer_text(answer))
    row_summary = _row_summary(rows[0])
    evidence_bullets = _ranked_row_bullets(rows, chinese=chinese)
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
                "headline": f"当前证据最支持优先评估 {primary_entity}",
                "direct_answer": f"本轮排序证据中，{primary_entity} 位于第一；{row_summary}。因此本次建议优先评估 {primary_entity}。",
                "why": f"证据表第一行显示：{row_summary}。",
                "evidence_bullets": evidence_bullets,
                "recommendations": [f"围绕 {primary_entity} 做下一步资源评估，并用相同指标继续跟踪。"],
                "caveats": caveats,
                "confidence": confidence,
            }
        )
        return answer

    answer.update(
        {
            "headline": f"The current evidence most supports prioritizing {primary_entity}",
            "direct_answer": (
                f"In the ranked evidence for this run, {primary_entity} is first; {row_summary}. "
                f"So the recommendation should prioritize {primary_entity}."
            ),
            "why": f"The first evidence row shows: {row_summary}.",
            "evidence_bullets": evidence_bullets,
            "recommendations": [f"Evaluate the next resource decision around {primary_entity} using the same metrics."],
            "caveats": caveats,
            "confidence": confidence,
        }
    )
    return answer


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
    bullets: list[str] = []
    for index, row in enumerate(rows[:limit], start=1):
        summary = _row_summary(row)
        if chinese:
            bullets.append(f"第 {index} 行：{summary}。")
        else:
            bullets.append(f"Row {index}: {summary}.")
    return bullets


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
) -> dict[str, Any]:
    leaders: dict[str, tuple[str, float]] = conflict["leaders"]
    leader_sentences = [
        _leader_sentence(metric=metric, name=name, value=value, chinese=chinese)
        for metric, (name, value) in leaders.items()
    ]
    leader_summary = "；".join(sentence.rstrip("。.") for sentence in leader_sentences)
    caveat = "不同数值指标指向不同对象，不能只用单一最高值下结论。"

    if chinese:
        answer.update(
            {
                "headline": "不同指标领先对象不同，需要按判断口径取舍",
                "direct_answer": leader_summary + "。因此需要先明确决策口径，再判断谁最值得重点投入。",
                "why": "本次证据显示多个指标的领先对象不一致：" + leader_summary + "。",
                "evidence_bullets": leader_sentences,
                "recommendations": ["先明确重点运营口径，再按该口径决定资源倾斜对象。"],
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
            "recommendations": ["Choose the decision basis before shifting resources."],
            "caveats": _dedupe(answer["caveats"] + ["Different numeric metrics point to different leaders."]),
            "confidence": "medium" if answer["confidence"] == "high" else answer["confidence"],
        }
    )
    return answer


def _leader_sentence(*, metric: str, name: str, value: float, chinese: bool) -> str:
    label = _metric_label(metric, chinese=chinese)
    formatted_value = _format_metric_value(value, metric=metric)
    if chinese:
        return f"按{label}看，{name}领先，数值为 {formatted_value}。"
    return f"By {label}, {name} leads with {formatted_value}."


def _metric_label(metric: str, *, chinese: bool) -> str:
    lowered = str(metric or "").lower()
    if "roi" in lowered:
        return "ROI"
    if "avg" in lowered and "revenue" in lowered and ("order" in lowered or "per_order" in lowered):
        return "客单价" if chinese else "average order revenue"
    if lowered in {"order_count", "orders"} or ("order" in lowered and "count" in lowered):
        return "订单数" if chinese else "orders"
    if "spend" in lowered:
        return "投放成本" if chinese else "spend"
    if "revenue" in lowered:
        return "收入" if chinese else "revenue"
    return str(metric or "").strip() or "该指标"


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


def _row_summary(row: dict[str, Any]) -> str:
    pairs = [f"{key} 为 {value}" for key, value in list(row.items())[:4]]
    return "，".join(pairs) if pairs else "当前证据没有可展示字段"


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
