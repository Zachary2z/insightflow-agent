from llm_ops.provider import MockLLMProvider


NEW_BUSINESS_ANSWER_KEYS = {
    "headline",
    "direct_answer",
    "why",
    "evidence_bullets",
    "recommendations",
    "caveats",
    "confidence",
}


def _assert_new_business_answer_shape(answer):
    assert set(answer) == NEW_BUSINESS_ANSWER_KEYS


def _business_answer_text(answer):
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


def _grouped_ledger(rows, columns, *, metric_labels=None, dimension_columns=None, data_limits=None):
    metric_labels = metric_labels or {}
    dimension_columns = dimension_columns or [columns[0]]
    facts = []
    for row_index, row in enumerate(rows):
        row_dict = {column: row[index] for index, column in enumerate(columns)}
        dimension = {column: row_dict[column] for column in dimension_columns if column in row_dict}
        for column in columns:
            value = row_dict.get(column)
            if column in dimension_columns or not isinstance(value, int | float):
                continue
            label = metric_labels.get(column, column)
            facts.append(
                {
                    "label": label,
                    "value": value,
                    "dimension": dimension,
                    "source_columns": [*dimension_columns, column],
                    "evidence_ref": f"evidence:row:{row_index}:{column}",
                }
            )
    return {
        "business_lens": {
            "metrics": [{"label": label} for label in dict.fromkeys(metric_labels.values())],
            "dimensions": [{"label": column} for column in dimension_columns],
        },
        "evidence_groups": [
            {
                "group_id": "group_unit_test",
                "purpose": "关键事实",
                "source": {"tables": ["unit_test"], "fields": list(columns)},
                "dimension": {
                    "role": "dimension",
                    "label": "对象",
                    "source_columns": list(dimension_columns),
                },
                "metrics": [
                    {
                        "role": "metric",
                        "label": metric_labels.get(column, column),
                        "source_column": column,
                        "source_fields": [column],
                        "unit": "",
                    }
                    for column in columns
                    if column not in dimension_columns
                ],
                "time_policy": "",
                "row_grain": "对象",
                "supports_answer": True,
                "supports_chart": True,
                "facts": facts,
                "derived_metrics": [],
            }
        ],
        "facts": facts,
        "derived_metrics": [],
        "data_limits": data_limits or [],
        "confidence": "medium",
    }


class _CapturingProvider:
    model = "mock-capturing"

    def __init__(self, response):
        self.response = response
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return self.response


def test_business_answer_rejects_raw_key_value_dump():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "final_answer": "1. channel=paid_search, revenue=200.0, order_count=10\n"
            "2. channel=email, revenue=100.0, order_count=5",
            "business_answer_generation": {"source": "deterministic", "fallback_used": True},
        }
    )

    _assert_new_business_answer_shape(answer)
    assert answer["headline"] != "channel=paid_search, revenue=200.0, order_count=10"
    assert "channel=" not in _business_answer_text(answer)
    assert "revenue=" not in _business_answer_text(answer)
    assert answer["confidence"] == "low"
    assert answer["caveats"]


def test_business_answer_keeps_raw_rows_out_of_product_fields():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_quality",
            "status": "completed",
            "final_answer": "channel=paid_search, revenue=200.0, order_count=10",
            "generated_sql": "SELECT channel, SUM(revenue) FROM orders GROUP BY channel",
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue", "order_count"],
                "rows": [["paid_search", 200.0, 10]],
            },
            "business_answer_generation": {"source": "deterministic"},
        },
        workspace_id="ws_quality",
    )

    _assert_new_business_answer_shape(product["business_answer"])
    business_text = _business_answer_text(product["business_answer"])
    assert "channel=" not in business_text
    assert "revenue=" not in business_text
    assert "order_count=" not in business_text
    assert "SELECT" not in business_text
    assert "provider_metadata" not in product["business_answer"]
    assert product["technical_details"]["raw_rows"] == [["paid_search", 200.0, 10]]


def test_provider_business_answer_output_becomes_recommendation_first_answer():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_provider_answer",
        "session_id": "session_provider_answer",
        "user_question": "哪个渠道该加预算？",
        "execution_result": {
            "success": True,
            "columns": ["channel", "revenue"],
            "rows": [["paid_search", 200.0], ["organic", 120.0]],
            "row_count": 2,
        },
        "question_evidence_ledger": _grouped_ledger(
            [["paid_search", 200.0], ["organic", 120.0]],
            ["channel", "revenue"],
            metric_labels={"revenue": "收入"},
        ),
        "trace": [],
    }
    provider = _CapturingProvider(
        {
            "candidate_claims": ["paid_search revenue is 200.0", "organic revenue is 120.0"],
            "business_answer": {
                "headline": "建议优先加码 paid_search",
                "direct_answer": "建议优先加码 paid_search，因为它在当前对比中贡献了最高收入 200.0。",
                "why": "证据显示 paid_search 贡献收入 200.0，高于 organic 的 120.0。",
                "evidence_bullets": ["paid_search 收入为 200.0。", "organic 收入为 120.0。"],
                "recommendations": ["优先复盘 paid_search 的投放效率。"],
                "caveats": [],
                "confidence": "high",
            },
        }
    )

    result = run_business_answer_agent(state, provider=provider)

    assert result["business_answer_generation"]["source"] == "provider"
    _assert_new_business_answer_shape(result["business_answer"])
    assert result["business_answer"]["headline"].startswith("建议")
    assert result["business_answer"]["direct_answer"].startswith("建议")
    assert result["business_answer"]["confidence"]
    assert "channel=" not in result["final_answer"]
    assert result["final_answer"] == result["business_answer"]["direct_answer"]
    assert "channel=" not in _business_answer_text(result["business_answer"])


def test_provider_business_answer_is_preserved_when_valid():
    from workspaces.business_answer_agent import run_business_answer_agent

    provider_answer = {
        "headline": "收入领先，但先看效率边界",
        "direct_answer": "最近90天收入最高的是私域社群，收入为 300000.0；但是否加预算仍需要结合投放成本判断。",
        "why": "证据账本显示私域社群收入为 300000.0，当前没有投放成本证据。",
        "evidence_bullets": ["私域社群收入为 300000.0。"],
        "recommendations": ["先补齐投放成本，再判断是否扩大预算。"],
        "caveats": ["当前结论只基于证据账本中的收入事实。"],
        "confidence": "medium",
    }
    provider = _CapturingProvider(
        {
            "candidate_claims": [{"claim": "私域社群收入为 300000.0。", "category": "hard_fact"}],
            "business_answer": provider_answer,
        }
    )

    result = run_business_answer_agent(
        {
            "run_id": "run_preserve_valid_provider_answer",
            "session_id": "session_preserve_valid_provider_answer",
            "user_question": "最近90天哪个渠道最值得加预算？",
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["私域社群", 300000.0], ["搜索广告", 120000.0]],
                "row_count": 2,
            },
            "question_evidence_ledger": _grouped_ledger(
                [["私域社群", 300000.0], ["搜索广告", 120000.0]],
                ["channel", "total_revenue"],
                metric_labels={"total_revenue": "收入"},
            ),
            "evidence_result": {"validation_status": "validated"},
            "trace": [],
        },
        provider=provider,
    )

    assert result["business_answer_generation"]["source"] == "provider"
    assert result["business_answer"] == provider_answer
    assert result["final_answer"] == provider_answer["direct_answer"]
    assert result["business_answer_generation"]["deterministic_check"]["composition_source"] == "provider_preserved"


def test_business_answer_provider_receives_grouped_ledger_not_flat_pool():
    from workspaces.business_answer_agent import run_business_answer_agent

    provider_answer = {
        "headline": "私域社群收入领先",
        "direct_answer": "私域社群收入领先。",
        "why": "模型基于 grouped evidence ledger 表达。",
        "evidence_bullets": ["私域社群收入为 300000.0。"],
        "recommendations": [],
        "caveats": [],
        "confidence": "medium",
    }
    provider = _CapturingProvider(
        {
            "candidate_claims": [{"claim": "私域社群收入为 300000.0。", "category": "hard_fact"}],
            "business_answer": provider_answer,
        }
    )
    ledger = {
        "ledger_id": "qledger_grouped_prompt",
        "business_lens": {"business_domain": "channel_performance"},
        "question_evidence_plan": {"plan_id": "qplan_grouped_prompt", "groups": ["group_revenue_by_channel"]},
        "evidence_groups": [
            {
                "group_id": "group_revenue_by_channel",
                "purpose": "关键事实",
                "source": {"tables": ["orders"], "fields": ["channel", "revenue"]},
                "dimension": {"role": "dimension", "label": "渠道", "source_columns": ["channel"]},
                "metrics": [
                    {
                        "role": "metric",
                        "label": "收入",
                        "source_column": "total_revenue",
                        "source_fields": ["revenue"],
                        "unit": "currency",
                    }
                ],
                "time_policy": "最近90天",
                "row_grain": "渠道",
                "supports_answer": True,
                "supports_chart": True,
                "evidence_refs": ["evidence:row:0:total_revenue"],
                "facts": [
                    {
                        "fact_id": "fact_1",
                        "label": "收入",
                        "value": 300000.0,
                        "dimension": {"channel": "私域社群"},
                        "source_columns": ["channel", "total_revenue"],
                        "source_row_refs": ["row:0"],
                        "evidence_ref": "evidence:row:0:total_revenue",
                    }
                ],
                "derived_metrics": [],
            }
        ],
        "facts": [
            {
                "fact_id": "fact_1",
                "label": "收入",
                "value": 300000.0,
                "dimension": {"channel": "私域社群"},
                "source_columns": ["channel", "total_revenue"],
                "source_row_refs": ["row:0"],
                "evidence_ref": "evidence:row:0:total_revenue",
            }
        ],
        "derived_metrics": [],
        "data_limits": [],
        "evidence_refs": ["evidence:row:0:total_revenue"],
        "confidence": "medium",
    }

    result = run_business_answer_agent(
        {
            "run_id": "run_grouped_prompt",
            "session_id": "session_grouped_prompt",
            "user_question": "最近90天哪个渠道收入最高？",
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["私域社群", 300000.0]],
                "row_count": 1,
            },
            "evidence_result": {"validation_status": "validated"},
            "question_evidence_ledger": ledger,
            "trace": [],
        },
        provider=provider,
    )

    schema_context = provider.requests[0].metadata["schema_context"]["question_evidence_ledger"]
    assert result["business_answer"] == provider_answer
    assert "evidence_groups" in schema_context
    assert "facts" not in schema_context
    assert schema_context["evidence_groups"][0]["group_id"] == "evidence_group_1"
    assert "source_row_refs" not in str(schema_context)


def test_business_answer_scrubs_internal_leaks_without_row_template_rewrite():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_multi_task_internal_ids",
        "session_id": "session_multi_task_internal_ids",
        "user_question": "最近30天按渠道比较收入和投放花费，哪个渠道更值得关注？",
        "execution_result": {
            "success": True,
            "columns": ["task_id", "task_purpose", "channel", "sum_spend", "sum_revenue"],
            "rows": [
                ["corefact_投放成本_渠道", "core_fact", "私域社群", 30000.0, None],
                ["corefact_投放成本_渠道", "core_fact", "搜索广告", 80000.0, None],
                ["corefact_销售额_渠道", "core_fact", "私域社群", None, 180000.0],
                ["corefact_销售额_渠道", "core_fact", "搜索广告", None, 120000.0],
                ["explanationsupport_销售额_投放成本_渠道", "explanation_support", "私域社群", None, None],
                ["explanationsupport_销售额_投放成本_渠道", "explanation_support", "搜索广告", None, None],
            ],
            "row_count": 4,
        },
        "trace": [],
    }
    provider = MockLLMProvider(
        {
            "candidate_claims": [{"claim": "corefact_销售额_渠道 收入最高。", "category": "hard_fact"}],
            "business_answer": {
                "headline": "corefact_销售额_渠道 表现最好",
                "direct_answer": "建议关注 corefact_销售额_渠道，因为它的收入最高。",
                "why": "corefact_销售额_渠道 领先。",
                "evidence_bullets": ["corefact_销售额_渠道 收入为 180000。"],
                "recommendations": ["继续加码 corefact_销售额_渠道。"],
                "caveats": [],
                "confidence": "high",
            },
        }
    )

    result = run_business_answer_agent(state, provider=provider)
    text = _business_answer_text(result["business_answer"])

    assert "corefact" not in text.lower()
    assert "task_id" not in text.lower()
    assert "建议关注" not in text
    assert "排在第一" not in text
    assert "本轮结果显示" not in text
    assert result["business_answer"]["confidence"] == "low"
    assert "回答生成失败" in text or "证据不足" in text


def test_business_answer_does_not_replace_unsupported_provider_draft_with_row_conclusion():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_multi_metric_decision",
        "session_id": "session_multi_metric_decision",
        "user_question": "最近30天按渠道比较收入和投放花费，哪个渠道更值得关注？",
        "execution_result": {
            "success": True,
            "columns": ["task_id", "task_purpose", "channel", "sum_spend", "total_revenue", "total_spend", "roas"],
            "rows": [
                ["corefact_投放成本_渠道", "core_fact", "直播间", 21855.0, None, None, None],
                ["corefact_投放成本_渠道", "core_fact", "私域社群", 11055.0, None, None, None],
                ["explanationsupport_销售额_投放成本_渠道", "explanation_support", "私域社群", None, 62640.0, 11055.0, 5.67],
                ["explanationsupport_销售额_投放成本_渠道", "explanation_support", "直播间", None, 50715.0, 21855.0, 2.32],
            ],
            "row_count": 4,
        },
        "question_evidence_ledger": _grouped_ledger(
            [["直播间", 21855.0], ["私域社群", 11055.0]],
            ["channel", "sum_spend"],
            metric_labels={"sum_spend": "投放成本"},
        ),
        "trace": [],
    }
    provider = MockLLMProvider(
        {
            "candidate_claims": [{"claim": "corefact_投放成本_渠道 花费最高。", "category": "hard_fact"}],
            "business_answer": {
                "headline": "corefact_投放成本_渠道 最值得关注",
                "direct_answer": "建议关注 corefact_投放成本_渠道。",
                "why": "corefact_投放成本_渠道 花费最高。",
                "evidence_bullets": ["corefact_投放成本_渠道 花费最高。"],
                "recommendations": ["继续加码 corefact_投放成本_渠道。"],
                "caveats": [],
                "confidence": "high",
            },
        }
    )

    result = run_business_answer_agent(state, provider=provider)
    text = _business_answer_text(result["business_answer"])

    assert "corefact" not in text.lower()
    assert "按ROAS看" not in text
    assert "按投放成本看" not in text
    assert "私域社群领先" not in text
    assert "直播间领先" not in text
    assert result["business_answer"]["confidence"] == "low"
    assert result["business_answer_generation"]["deterministic_check"]["composition_source"] == "scrubbed_provider_answer"


def test_product_result_consistency_does_not_reintroduce_multi_task_internal_ids():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_product_multi_task_internal_ids",
            "workspace_id": "ws_product_multi_task_internal_ids",
            "status": "completed",
            "original_question": "最近30天按渠道比较收入和投放花费，哪个渠道更值得关注？",
            "business_answer": {
                "headline": "不同指标领先对象不同，需要按判断口径取舍",
                "direct_answer": "本次不能简单用一个赢家概括：按总收入看，私域社群领先，数值为 62,640；按投放成本看，直播间领先，数值为 21,855。",
                "why": "当前数据只能确认各指标高低，不能直接证明原因。",
                "evidence_bullets": [
                    "按总收入看，私域社群领先，数值为 62,640。",
                    "按投放成本看，直播间领先，数值为 21,855。",
                ],
                "recommendations": ["先明确决策口径。"],
                "caveats": ["当前结论只基于本次查询返回的数据。"],
                "confidence": "medium",
            },
            "execution_result": {
                "success": True,
                "columns": [
                    "task_id",
                    "task_purpose",
                    "channel",
                    "sum_spend",
                    "sum_revenue",
                    "total_spend",
                    "total_revenue",
                    "efficiency",
                    "profit",
                ],
                "rows": [
                    ["corefact_投放成本_渠道", "core_fact", "直播间", 21855.0, None, 21855.0, None, None, None],
                    ["corefact_投放成本_渠道", "core_fact", "私域社群", 11055.0, None, 11055.0, None, None, None],
                    ["corefact_销售额_渠道", "core_fact", "私域社群", None, 62640.0, None, 62640.0, 5.67, 51585.0],
                    ["corefact_销售额_渠道", "core_fact", "直播间", None, 50715.0, None, 50715.0, 2.32, 28860.0],
                ],
                "row_count": 4,
            },
            "trace": [],
        },
        workspace_id="ws_product_multi_task_internal_ids",
    )

    text = _business_answer_text(product["business_answer"])
    assert "corefact" not in text.lower()
    assert "task_id" not in text.lower()
    assert "efficiency" not in text.lower()
    assert "profit" not in text.lower()
    assert "私域社群" in text
    assert "直播间" in text
    revenue_bullets = [
        item
        for item in product["business_answer"]["evidence_bullets"]
        if ("总收入" in item or "销售额" in item) and "私域社群" in item and "62,640" in item
    ]
    assert len(revenue_bullets) == 1
    assert product["business_answer"]["evidence_bullets"].count("按投放成本看，直播间领先，数值为 21,855。") == 1


def test_business_answer_agent_receives_ledger_context_and_keeps_evidence_boundary():
    from workspaces.business_answer_agent import run_business_answer_agent

    ledger = {
        "ledger_id": "qledger_test",
        "business_lens": {
            "business_domain": "channel_performance",
            "metrics": [{"label": "收入", "source_table": "orders", "source_field": "revenue"}],
            "dimensions": [{"label": "渠道", "source_table": "orders", "source_field": "channel"}],
        },
        "time_policy_note": "收入按下单日期统计，时间范围为最近90天。",
        "facts": [
            {
                "fact_id": "fact_1",
                "label": "收入",
                "value": 300000.0,
                "unit": "",
                "dimension": {"channel": "私域社群"},
                "source_columns": ["channel", "total_revenue"],
                "source_row_refs": ["row:0"],
                "evidence_ref": "evidence:row:0:total_revenue",
            }
        ],
        "derived_metrics": [],
        "data_limits": ["当前没有投放成本字段，不能证明 ROI 或直接给出加预算结论。"],
        "tool_calls": [],
        "evidence_refs": ["evidence:row:0:total_revenue"],
        "chart_refs": [],
        "source_pack_id": "question_evidence_pack",
        "confidence": "medium",
    }
    provider = _CapturingProvider(
        {
            "candidate_claims": [
                {"claim": "私域社群 收入为 300000.0。", "category": "hard_fact"},
                {
                    "claim": "当前没有投放成本字段，不能证明 ROI 或直接给出加预算结论。",
                    "category": "data_limit",
                },
                {
                    "claim": "可以先复盘私域社群的承接链路，再补投放成本验证效率。",
                    "category": "recommendation",
                },
            ],
            "business_answer": {
                "headline": "私域社群收入最高，但加预算证据不足",
                "direct_answer": "最近90天按下单日期统计，私域社群收入为 300000.0；但当前缺少投放成本字段，不能直接证明 ROI 或给出加预算结论。",
                "why": "本轮硬事实来自证据账本：私域社群在 total_revenue 上为 300000.0。建议部分只能作为基于该事实和数据缺口的业务推断。",
                "evidence_bullets": ["私域社群 收入为 300000.0。"],
                "recommendations": ["先复盘私域社群的承接链路，并补齐投放成本后再判断是否加预算。"],
                "caveats": ["当前没有投放成本字段，不能证明 ROI 或直接给出加预算结论。"],
                "confidence": "medium",
            },
        }
    )

    result = run_business_answer_agent(
        {
            "run_id": "run_ledger_answer",
            "session_id": "session_ledger_answer",
            "user_question": "最近90天哪个渠道最值得加预算？",
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["私域社群", 300000.0]],
                "row_count": 1,
            },
            "question_evidence_ledger": ledger,
            "trace": [],
        },
        provider=provider,
    )

    prompt = provider.requests[0].prompt
    answer_text = _business_answer_text(result["business_answer"])
    assert "Question evidence ledger" in prompt
    assert "收入按下单日期统计" in prompt
    assert "不能证明 ROI" in prompt
    assert "收入按下单日期统计" in answer_text
    assert "不能证明 ROI" in answer_text
    assert result["audit_result"]["unsupported_claims"] == []
    assert any("投放成本" in item for item in result["audit_result"]["reasonable_inferences"])


def test_business_answer_provider_prompt_uses_answer_safe_ledger_not_raw_execution_or_task_metadata():
    from workspaces.business_answer_agent import run_business_answer_agent

    ledger = {
        "ledger_id": "qledger_internal_should_not_prompt",
        "business_lens": {
            "business_domain": "channel_performance",
            "metrics": [{"label": "收入", "source_table": "orders", "source_field": "revenue"}],
            "dimensions": [{"label": "渠道", "source_table": "orders", "source_field": "channel"}],
        },
        "time_policy_note": "收入按下单日期统计，时间范围为最近90天。",
        "facts": [
            {
                "fact_id": "fact_revenue_by_channel_1",
                "task_id": "revenue_by_channel",
                "label": "收入",
                "value": 300000.0,
                "dimension": {"channel": "私域社群"},
                "source_columns": ["channel", "total_revenue"],
                "source_row_refs": ["revenue_by_channel:row:0"],
                "evidence_ref": "evidence:revenue_by_channel:row:0:total_revenue",
            }
        ],
        "derived_metrics": [],
        "data_limits": ["task helper failed: SELECT * FROM orders; trace_path=/tmp/ws/trace.json provider_metadata={'token':'sk-test'}"],
        "tool_calls": [
            {
                "tool_name": "sql_execution",
                "purpose": "revenue_by_channel: 执行证据任务",
                "input_summary": "review approved SQL",
                "output_summary": "rows=1",
                "status": "completed",
            }
        ],
        "evidence_refs": ["evidence:revenue_by_channel:row:0:total_revenue"],
        "task_refs": ["revenue_by_channel"],
        "tables": [{"table_id": "table_revenue_by_channel_1", "task_id": "revenue_by_channel", "columns": ["channel", "total_revenue"]}],
        "source_pack_id": "question_evidence_pack:revenue_by_channel",
        "confidence": "medium",
    }
    provider = _CapturingProvider(
        {
            "candidate_claims": [{"claim": "私域社群收入为 300000.0。", "category": "hard_fact"}],
            "business_answer": {
                "headline": "私域社群收入最高",
                "direct_answer": "最近90天收入最高的是私域社群，收入为 300000.0。",
                "why": "证据账本显示私域社群收入为 300000.0。",
                "evidence_bullets": ["私域社群收入为 300000.0。"],
                "recommendations": [],
                "caveats": ["结论只基于本轮证据账本中的事实。"],
                "confidence": "medium",
            },
        }
    )

    result = run_business_answer_agent(
        {
            "run_id": "run_answer_safe_ledger",
            "session_id": "session_answer_safe_ledger",
            "user_question": "最近90天哪个渠道收入最高？",
            "execution_result": {
                "success": True,
                "columns": ["task_id", "task_purpose", "channel", "total_revenue"],
                "rows": [["revenue_by_channel", "core_fact", "私域社群", 300000.0]],
                "row_count": 1,
                "sql": "SELECT channel, SUM(revenue) FROM orders GROUP BY channel",
                "provider_metadata": {"token": "sk-test"},
            },
            "question_evidence_ledger": ledger,
            "trace": [{"node": "sql_executor_node", "trace_path": "/tmp/ws/trace.json"}],
        },
        provider=provider,
    )

    prompt = provider.requests[0].prompt
    schema_context = provider.requests[0].metadata.get("schema_context", {})
    prompt_and_context = prompt + " " + str(schema_context)
    assert "Question evidence ledger" in prompt
    assert "私域社群" in prompt
    assert "300000.0" in prompt
    assert "Execution result" not in prompt
    assert "SELECT" not in prompt_and_context.upper()
    assert "task_id" not in prompt_and_context
    assert "task_purpose" not in prompt_and_context
    assert "revenue_by_channel" not in prompt_and_context
    assert "source_pack_id" not in prompt_and_context
    assert "provider_metadata" not in prompt_and_context
    assert "sk-test" not in prompt_and_context
    assert "/tmp/ws" not in prompt_and_context
    assert result["business_answer_generation"]["source"] == "provider"


def test_business_answer_no_provider_returns_generation_failed_not_ledger_fact_answer():
    from workspaces.business_answer_agent import run_business_answer_agent

    result = run_business_answer_agent(
        {
            "run_id": "run_no_provider_boundary",
            "session_id": "session_no_provider_boundary",
            "user_question": "最近90天哪个渠道收入最高？",
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["私域社群", 300000.0]],
                "row_count": 1,
            },
            "question_evidence_ledger": {
                "facts": [
                    {
                        "label": "收入",
                        "value": 300000.0,
                        "dimension": {"渠道": "私域社群"},
                    }
                ],
                "derived_metrics": [],
                "data_limits": [],
                "confidence": "medium",
            },
            "trace": [],
        },
        provider=None,
    )

    text = _business_answer_text(result["business_answer"])
    assert result["business_answer_generation"]["success"] is False
    assert result["business_answer_generation"]["source"] == "provider_unavailable"
    assert "业务回答生成失败" in text
    assert "私域社群" not in text
    assert "300000" not in text
    assert "无可用模型时使用证据账本回答" not in text
    assert "根据已验证证据" not in text


def test_business_answer_agent_repairs_provider_draft_before_final_answer():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_reviewed_answer",
        "session_id": "session_reviewed_answer",
        "user_question": "Which entity should we prioritize?",
        "execution_result": {
            "success": True,
            "columns": ["entity_name", "score_value"],
            "rows": [["Alpha", 91.0], ["Beta", 83.0]],
            "row_count": 2,
        },
        "question_evidence_ledger": _grouped_ledger(
            [["Alpha", 91.0], ["Beta", 83.0]],
            ["entity_name", "score_value"],
            metric_labels={"score_value": "score_value"},
        ),
        "evidence_result": {"validation_status": "validated"},
        "trace": [],
    }
    draft_provider = MockLLMProvider(
        {
            "candidate_claims": ["Alpha score_value is 91.0", "Beta score_value is 83.0"],
            "business_answer": {
                "headline": "Gamma wins on margin_rate",
                "direct_answer": "Prioritize Gamma because margin_rate is strongest.",
                "why": "Gamma margin_rate is 0.42.",
                "evidence_bullets": ["Gamma margin_rate is 0.42."],
                "recommendations": ["Move resources to Gamma using margin_rate."],
                "caveats": [],
                "confidence": "high",
            },
        }
    )
    result = run_business_answer_agent(
        state,
        provider=draft_provider,
    )

    _assert_new_business_answer_shape(result["business_answer"])
    business_text = _business_answer_text(result["business_answer"])
    check = result["business_answer_generation"]["deterministic_check"]
    assert check["review_status"] == "revise"
    assert check["composition_source"] == "scrubbed_provider_answer"
    assert "Gamma" not in business_text
    assert "margin_rate" not in business_text
    assert "Alpha" not in business_text
    assert "prioritize" not in business_text.lower()
    assert "evidence is insufficient" in business_text.lower() or "answer generation failed" in business_text.lower()
    assert result["final_answer"] == result["business_answer"]["direct_answer"]


def test_business_answer_agent_preserves_supported_direct_answer_when_only_why_needs_scrub():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_reviewed_answer_partial_scrub",
        "session_id": "session_reviewed_answer_partial_scrub",
        "user_question": "Which entity should we prioritize?",
        "execution_result": {
            "success": True,
            "columns": ["entity_name", "score_value"],
            "rows": [["Alpha", 91.0], ["Beta", 83.0]],
            "row_count": 2,
        },
        "question_evidence_ledger": _grouped_ledger(
            [["Alpha", 91.0], ["Beta", 83.0]],
            ["entity_name", "score_value"],
            metric_labels={"score_value": "score_value"},
        ),
        "evidence_result": {"validation_status": "validated"},
        "trace": [],
    }
    provider = MockLLMProvider(
        {
            "candidate_claims": ["Alpha score_value is 91.0", "Gamma margin_rate is 0.42"],
            "business_answer": {
                "headline": "Alpha is the priority",
                "direct_answer": "Prioritize Alpha based on the current evidence.",
                "why": "Alpha has the strongest score, and Gamma margin_rate is 0.42.",
                "evidence_bullets": ["Alpha score_value is 91.0.", "Gamma margin_rate is 0.42."],
                "recommendations": ["Focus on Alpha first."],
                "caveats": [],
                "confidence": "high",
            },
        }
    )

    result = run_business_answer_agent(state, provider=provider)
    business_text = _business_answer_text(result["business_answer"])

    assert result["business_answer_generation"]["deterministic_check"]["review_status"] == "revise"
    assert result["business_answer"]["direct_answer"].startswith("Prioritize Alpha")
    assert "Gamma" not in business_text
    assert "margin_rate" not in business_text
    assert result["business_answer"]["confidence"] == "medium"


def test_business_answer_agent_preserves_main_conclusion_and_removes_unsupported_auxiliary_number():
    from workspaces.business_answer_agent import run_business_answer_agent

    ledger = {
        "ledger_id": "qledger_non_destructive_repair",
        "business_lens": {
            "business_domain": "channel_performance",
            "metrics": [{"label": "收入", "source_field": "revenue"}],
            "dimensions": [{"label": "渠道", "source_field": "channel"}],
        },
        "evidence_groups": [
            {
                "group_id": "group_revenue_by_channel",
                "purpose": "关键事实",
                "source": {"tables": ["orders"], "fields": ["channel", "revenue", "total_revenue"]},
                "dimension": {"role": "dimension", "label": "渠道", "source_columns": ["channel"]},
                "metrics": [
                    {
                        "role": "metric",
                        "label": "收入",
                        "source_column": "total_revenue",
                        "source_fields": ["revenue"],
                        "unit": "currency",
                    }
                ],
                "time_policy": "最近90天",
                "row_grain": "渠道",
                "supports_answer": True,
                "supports_chart": True,
                "facts": [
                    {
                        "label": "收入",
                        "value": 300000.0,
                        "dimension": {"渠道": "私域社群"},
                        "source_columns": ["channel", "total_revenue"],
                        "evidence_ref": "evidence:row:0:total_revenue",
                    }
                ],
                "derived_metrics": [],
            }
        ],
        "facts": [
            {
                "label": "收入",
                "value": 300000.0,
                "dimension": {"渠道": "私域社群"},
                "source_columns": ["channel", "total_revenue"],
                "evidence_ref": "evidence:row:0:total_revenue",
            }
        ],
        "derived_metrics": [],
        "data_limits": [],
        "confidence": "medium",
    }
    provider = MockLLMProvider(
        {
            "candidate_claims": [
                {"claim": "私域社群收入为 300000.0。", "category": "hard_fact"},
                {"claim": "私域社群转化率为 88.8%。", "category": "hard_fact"},
            ],
            "business_answer": {
                "headline": "私域社群收入领先",
                "direct_answer": "最近90天收入最高的是私域社群，收入为 300000.0；转化率为 88.8%。",
                "why": "证据账本显示私域社群收入为 300000.0。",
                "evidence_bullets": ["私域社群收入为 300000.0。", "私域社群转化率为 88.8%。"],
                "recommendations": ["先围绕私域社群复盘承接链路。"],
                "caveats": [],
                "confidence": "high",
            },
        }
    )

    result = run_business_answer_agent(
        {
            "run_id": "run_non_destructive_repair",
            "session_id": "session_non_destructive_repair",
            "user_question": "最近90天哪个渠道收入最高？",
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["私域社群", 300000.0]],
                "row_count": 1,
            },
            "question_evidence_ledger": ledger,
            "trace": [],
        },
        provider=provider,
    )

    text = _business_answer_text(result["business_answer"])
    assert "私域社群" in text
    assert "300000.0" in text
    assert "88.8" not in text
    assert "业务回答生成失败" not in text
    assert result["business_answer"]["confidence"] == "medium"
    assert result["business_answer_generation"]["deterministic_check"]["composition_source"] == "scrubbed_provider_answer"


def test_business_answer_scrub_does_not_treat_time_window_as_unsupported_amount():
    from workspaces.business_answer_agent import _claim_numbers, _scrub_unsupported_text

    assert _claim_numbers("最近90天，直播间收入最低，为90,000元。") == ["90000"]

    cleaned = _scrub_unsupported_text(
        "最近90天，直播间收入最低，为90,000元。",
        unsupported_values=["90"],
        chinese=True,
    )

    assert "90,000元" in cleaned
    assert "为000元" not in cleaned


def test_business_answer_agent_rejects_unsupported_provider_primary_answer_without_ledger_template():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_ledger_repair_fallback",
        "session_id": "session_ledger_repair_fallback",
        "user_question": "哪个渠道最值得加预算？",
        "execution_result": {
            "success": True,
            "columns": ["channel_name", "revenue"],
            "rows": [["私域社群", 180000.0], ["搜索广告", 120000.0]],
            "row_count": 2,
        },
        "question_evidence_ledger": {
            "facts": [
                {"label": "收入", "value": 180000, "dimension": {"渠道": "私域社群"}},
                {"label": "收入", "value": 120000, "dimension": {"渠道": "搜索广告"}},
            ],
            "data_limits": ["投放成本证据不足，不能直接给出加预算动作。"],
        },
        "trace": [],
    }
    provider = MockLLMProvider(
        {
            "candidate_claims": ["Gamma margin_rate is 0.42"],
            "business_answer": {
                "headline": "Gamma 最值得加预算",
                "direct_answer": "建议给 Gamma 加预算。",
                "why": "Gamma margin_rate is 0.42.",
                "evidence_bullets": ["Gamma margin_rate is 0.42."],
                "recommendations": ["给 Gamma 加预算。"],
                "caveats": [],
                "confidence": "high",
            },
        }
    )

    result = run_business_answer_agent(state, provider=provider)
    text = _business_answer_text(result["business_answer"])

    assert "Gamma" not in text
    assert "margin_rate" not in text
    assert "业务回答生成失败" in text
    assert "根据已验证证据" not in text
    assert "无可用模型" not in text
    assert "私域社群" not in text
    assert "raw_rows" not in text
    assert result["business_answer_generation"]["source"] == "provider_unavailable"
    assert result["business_answer_generation"]["validation_error"]


def test_business_answer_reviewer_allows_supported_metric_acronym_aliases():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_metric_acronym_alias",
        "session_id": "session_metric_acronym_alias",
        "user_question": "结合收入、投放花费和 ROI，哪个渠道最值得加预算？",
        "execution_result": {
            "success": True,
            "columns": ["channel_name", "revenue", "ad_spend", "roas"],
            "rows": [["私域社群", 180000.0, 30000.0, 6.0], ["搜索广告", 120000.0, 80000.0, 1.5]],
            "row_count": 2,
        },
        "question_evidence_ledger": _grouped_ledger(
            [["私域社群", 180000.0, 30000.0, 6.0], ["搜索广告", 120000.0, 80000.0, 1.5]],
            ["channel_name", "revenue", "ad_spend", "roas"],
            metric_labels={"revenue": "收入", "ad_spend": "投放花费", "roas": "ROI"},
        ),
        "evidence_result": {"validation_status": "validated"},
        "trace": [],
    }
    provider = MockLLMProvider(
        {
            "candidate_claims": [
                {"claim": "私域社群 ROI 为 6.0。", "category": "hard_fact"},
                {"claim": "私域社群更值得优先评估加预算。", "category": "recommendation"},
            ],
            "business_answer": {
                "headline": "私域社群 ROI 最好",
                "direct_answer": "私域社群收入和 ROI 领先，更值得优先评估加预算。",
                "why": "证据显示私域社群收入为 180000.0，投放花费为 30000.0，ROI 为 6.0。",
                "evidence_bullets": ["私域社群 ROI 为 6.0。"],
                "recommendations": ["先做小比例预算增量测试。"],
                "caveats": ["结论仅基于本轮返回的渠道收入、投放花费和 ROAS。"],
                "confidence": "medium",
            },
        }
    )

    result = run_business_answer_agent(state, provider=provider)
    text = _business_answer_text(result["business_answer"])

    assert result["business_answer_generation"]["deterministic_check"]["review_status"] in {"accept", "revise"}
    assert "业务回答生成失败" not in text
    assert "ROI" in text
    assert result["final_answer"].startswith("私域社群收入和 ROI")


def test_chinese_question_rejects_english_provider_business_summary():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_provider_language",
        "session_id": "session_provider_language",
        "user_question": "最近90天哪个渠道收入最高？为什么？",
        "execution_result": {
            "success": True,
            "columns": ["channel", "total_revenue"],
            "rows": [["email", 44548.53]],
            "row_count": 1,
        },
        "question_evidence_ledger": _grouped_ledger(
            [["email", 44548.53]],
            ["channel", "total_revenue"],
            metric_labels={"total_revenue": "收入"},
        ),
        "trace": [],
    }
    provider = MockLLMProvider(
        {
            "candidate_claims": ["email total revenue is 44548.53"],
            "business_answer": {
                "headline": "Email is the top revenue channel",
                "direct_answer": (
                    "Based on the data, email is the top revenue channel for the last 90 days, "
                    "bringing in $44,548.53."
                ),
                "why": "The first evidence row shows email at 44548.53 total revenue.",
                "evidence_bullets": ["email total revenue is 44548.53."],
                "recommendations": ["Review the email channel plan."],
                "caveats": [],
                "confidence": "medium",
            },
        }
    )

    result = run_business_answer_agent(state, provider=provider)

    assert result["business_answer_generation"]["fallback_used"] is True
    assert result["business_answer_generation"]["validation_error"]
    assert "输出语言" in result["business_answer_generation"]["validation_error"]
    _assert_new_business_answer_shape(result["business_answer"])
    assert "回答生成失败" in _business_answer_text(result["business_answer"])
    assert "email 总收入最高" not in _business_answer_text(result["business_answer"])
    assert "Based on the data" not in _business_answer_text(result["business_answer"])


def test_chinese_question_localizes_english_system_understanding():
    from workspaces.product_result_builder import build_product_analysis_result

    product = build_product_analysis_result(
        {
            "run_id": "run_language_thread",
            "status": "completed",
            "user_question": "最近90天哪个渠道收入最高？为什么？",
            "question_understanding": {
                "strategy": "llm_candidate",
                "intent": {
                    "metric": "revenue",
                    "dimension": "channel",
                    "time_range": {"type": "last_n_days", "value": 90},
                },
                "reason": (
                    "User explicitly asks for the channel with highest revenue in the last 90 days."
                ),
            },
            "final_answer": "email 渠道收入最高。",
        },
        workspace_id="ws_language",
    )

    understanding = product["question_thread"]["system_understanding"]
    assert understanding.startswith("系统已识别")
    assert "收入" in understanding
    assert "渠道" in understanding
    assert "最近 90 天" in understanding
    assert "User explicitly" not in understanding


def test_business_answer_without_evidence_does_not_extract_plain_guidance_as_recommendation():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "final_answer": (
                "Based on the past 90 days data, email has the highest ROI. "
                "A balanced approach might be to increase email budget while optimizing paid search spend."
            ),
            "business_answer_generation": {"source": "provider"},
        }
    )

    _assert_new_business_answer_shape(answer)
    assert answer["recommendations"] == []
    assert answer["confidence"] == "low"
    assert answer["caveats"]


def test_business_answer_validation_rejects_draft_summary_only_output():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "business_answer",
        {
            "candidate_claims": ["paid_search revenue is 200.0"],
            "draft_summary": "建议优先加码 paid_search，因为它贡献了最高收入 200.0。",
        },
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "business_answer" in result["error"]


def test_business_answer_validation_derives_claims_when_provider_omits_candidate_claims():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "business_answer",
        {
            "candidate_claims": [],
            "business_answer": {
                "headline": "私域社群收入最高",
                "direct_answer": "最近90天私域社群收入最高，为18万元。",
                "why": "证据账本显示私域社群收入高于搜索广告和直播间。",
                "evidence_bullets": ["私域社群收入为18万元。"],
                "recommendations": [],
                "caveats": ["ROI 和利润率需要结合成本继续判断。"],
                "confidence": "medium",
            },
        },
        schema_context={
            "user_question": "最近90天各渠道收入表现怎么样？",
            "question_evidence_ledger": {
                "facts": [{"label": "收入", "value": 180000, "dimension": {"渠道": "私域社群"}}],
            },
        },
    )

    assert result["success"] is True
    assert result["content"]["candidate_claims"][0]["category"] == "business_inference"
    assert any(claim.get("category") == "hard_fact" for claim in result["content"]["candidate_claims"])


def test_business_answer_validation_rejects_extra_old_draft_summary_field():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "business_answer",
        {
            "candidate_claims": ["paid_search revenue is 200.0"],
            "draft_summary": "建议优先加码 paid_search。",
            "business_answer": {
                "headline": "建议优先加码 paid_search",
                "direct_answer": "建议优先加码 paid_search，因为它贡献了最高收入 200.0。",
                "why": "证据显示 paid_search 收入为 200.0。",
                "evidence_bullets": ["paid_search 收入为 200.0。"],
                "recommendations": ["复盘 paid_search 的投放效率。"],
                "caveats": [],
                "confidence": "high",
            },
        },
        schema_context={"user_question": "哪个渠道该加预算？"},
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "draft_summary" in result["error"]


def test_business_answer_validation_rejects_english_business_answer_for_chinese_question():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "business_answer",
        {
            "candidate_claims": ["email total revenue is 44548.53"],
            "business_answer": {
                "headline": "Email is the top revenue channel",
                "direct_answer": "Email is the top revenue channel in the last 90 days.",
                "why": "The evidence row shows email revenue is 44548.53.",
                "evidence_bullets": ["email total revenue is 44548.53."],
                "recommendations": ["Increase email budget."],
                "caveats": [],
                "confidence": "medium",
            },
        },
        schema_context={"user_question": "最近90天哪个渠道收入最高？"},
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "中文问题" in result["error"]


def test_business_answer_validation_rejects_partially_english_business_fields_for_chinese_question():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "business_answer",
        {
            "candidate_claims": ["email total revenue is 44548.53"],
            "business_answer": {
                "headline": "email 渠道收入最高",
                "direct_answer": "Email is the top revenue channel in the last 90 days.",
                "why": "The evidence row shows email revenue is 44548.53.",
                "evidence_bullets": ["email 渠道收入为 44548.53。"],
                "recommendations": ["Increase email budget."],
                "caveats": [],
                "confidence": "medium",
            },
        },
        schema_context={"user_question": "最近90天哪个渠道收入最高？"},
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "business_answer.direct_answer" in result["error"]
    assert "中文" in result["error"]


def test_business_answer_validation_allows_english_business_terms_inside_chinese_sentences():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "business_answer",
        {
            "candidate_claims": ["email ROI 为 0.38"],
            "business_answer": {
                "headline": "email 渠道的 ROI 最高",
                "direct_answer": "建议优先复盘 email 渠道，因为它的 ROI 为 0.38。",
                "why": "证据显示 email 在当前结果中 ROI 领先，且 paid_search 可作为对比渠道。",
                "evidence_bullets": ["email 的 ROI 为 0.38。", "paid_search 的 ROI 低于 email。"],
                "recommendations": ["继续观察 email 的预算效率，并对比 paid_search 的转化质量。"],
                "caveats": ["当前结论只覆盖本次返回数据。"],
                "confidence": "medium",
            },
        },
        schema_context={"user_question": "最近90天哪个渠道 ROI 最高？"},
    )

    assert result["success"] is True
    assert result["content"]["business_answer"]["headline"] == "email 渠道的 ROI 最高"


def test_business_answer_validation_rejects_sql_trace_and_provider_metadata_in_business_fields():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "business_answer",
        {
            "candidate_claims": ["paid_search revenue is 200.0"],
            "business_answer": {
                "headline": "建议优先加码 paid_search",
                "direct_answer": "建议优先加码 paid_search。trace_id=abc123 provider_metadata={model: deepseek}",
                "why": "SELECT channel, SUM(revenue) FROM orders GROUP BY channel",
                "evidence_bullets": ["paid_search 收入为 200.0。"],
                "recommendations": [],
                "caveats": [],
                "confidence": "medium",
            },
        },
        schema_context={"user_question": "哪个渠道该加预算？"},
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "technical" in result["error"] or "技术" in result["error"]


def test_business_answer_validation_rejects_raw_parameter_dump_in_business_answer():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "business_answer",
        {
            "candidate_claims": ["paid_search revenue is 200.0"],
            "business_answer": {
                "headline": "建议优先加码 paid_search",
                "direct_answer": "channel=paid_search, revenue=200.0, order_count=10",
                "why": "证据显示 paid_search 收入最高。",
                "evidence_bullets": ["paid_search 收入为 200.0。"],
                "recommendations": [],
                "caveats": [],
                "confidence": "medium",
            },
        },
        schema_context={"user_question": "哪个渠道该加预算？"},
    )

    assert result["success"] is False
    assert result["error_type"] == "llm_schema_validation_error"
    assert "raw parameter" in result["error"]


def test_business_answer_validation_allows_metric_acronym_display_values():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "business_answer",
        {
            "candidate_claims": [{"claim": "私域社群 ROI=6.0。", "category": "hard_fact"}],
            "business_answer": {
                "headline": "私域社群 ROI 领先",
                "direct_answer": "私域社群 ROI=6.0，收入也排在第一。",
                "why": "该结论来自证据账本中的渠道收入、投放成本和 ROAS。",
                "evidence_bullets": ["私域社群 ROI=6.0。"],
                "recommendations": [],
                "caveats": ["仅基于本轮证据。"],
                "confidence": "medium",
            },
        },
        schema_context={"user_question": "哪个渠道 ROI 最高？"},
    )

    assert result["success"] is True


def test_business_answer_validation_normalizes_string_list_fields():
    from llm_ops.structured_output import validate_prompt_output

    result = validate_prompt_output(
        "business_answer",
        {
            "candidate_claims": [{"claim": "私域社群收入最高。", "category": "hard_fact"}],
            "business_answer": {
                "headline": "私域社群收入最高",
                "direct_answer": "私域社群收入最高。",
                "why": "证据账本显示私域社群收入最高。",
                "evidence_bullets": "私域社群收入最高。",
                "recommendations": "",
                "caveats": "仅基于本轮证据。",
                "confidence": "medium",
            },
        },
        schema_context={"user_question": "哪个渠道收入最高？"},
    )

    assert result["success"] is True
    answer = result["content"]["business_answer"]
    assert answer["evidence_bullets"] == ["私域社群收入最高。"]
    assert answer["recommendations"] == []
    assert answer["caveats"] == ["仅基于本轮证据。"]


def test_product_result_builder_rejects_mixed_language_provider_business_answer_for_chinese_question():
    from workspaces.product_result_builder import build_business_answer

    answer = build_business_answer(
        {
            "user_question": "最近90天哪个渠道收入最高？",
            "business_answer": {
                "headline": "email 渠道收入最高",
                "direct_answer": "Email is the top revenue channel in the last 90 days.",
                "why": "The evidence row shows email revenue is 44548.53.",
                "evidence_bullets": ["email 渠道收入为 44548.53。"],
                "recommendations": ["Increase email budget."],
                "caveats": [],
                "confidence": "medium",
            },
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue"],
                "rows": [["email", 44548.53]],
            },
        }
    )

    _assert_new_business_answer_shape(answer)
    assert "Email is the top revenue channel" not in _business_answer_text(answer)
    assert "The evidence row shows" not in _business_answer_text(answer)
    assert "Increase email budget" not in _business_answer_text(answer)
    assert "当前数据中" not in answer["direct_answer"]
    assert "email 总收入最高" not in answer["direct_answer"]
    assert "业务回答缺失" in _business_answer_text(answer)
