NEW_BUSINESS_ANSWER_KEYS = {
    "headline",
    "direct_answer",
    "why",
    "evidence_bullets",
    "recommendations",
    "caveats",
    "confidence",
}


class _CapturingProvider:
    model = "mock-capturing"

    def __init__(self, response):
        self.response = response
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return self.response


class _SequentialProvider:
    model = "mock-sequential"

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        if self.responses:
            return self.responses.pop(0)
        return {
            "candidate_claims": [],
            "business_answer": {
                "headline": "业务回答缺失",
                "direct_answer": "业务回答缺失",
                "why": "业务回答缺失",
                "evidence_bullets": [],
                "recommendations": [],
                "caveats": ["业务回答缺失"],
                "confidence": "low",
            },
        }


def _grouped_channel_revenue_ledger():
    return {
        "ledger_id": "qledger_internal_should_not_prompt",
        "business_lens": {
            "business_domain": "channel_performance",
            "metrics": [{"label": "收入", "source_table": "orders", "source_field": "revenue"}],
            "dimensions": [{"label": "渠道", "source_table": "orders", "source_field": "channel"}],
        },
        "time_policy_note": "",
        "question_evidence_plan": {"plan_id": "qplan_internal_should_not_prompt", "groups": ["group_revenue"]},
        "evidence_groups": [
            {
                "group_id": "group_revenue",
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
                "time_policy": "",
                "row_grain": "渠道",
                "supports_answer": True,
                "supports_chart": True,
                "evidence_refs": [
                    "evidence:task_revenue_by_channel:row:0:total_revenue",
                    "evidence:task_revenue_by_channel:row:1:total_revenue",
                ],
                "facts": [
                    {
                        "fact_id": "fact_1",
                        "task_id": "task_revenue_by_channel",
                        "label": "收入",
                        "value": 200.0,
                        "dimension": {"channel": "paid_search"},
                        "source_columns": ["channel", "total_revenue"],
                        "source_row_refs": ["task_revenue_by_channel:row:0"],
                        "evidence_ref": "evidence:task_revenue_by_channel:row:0:total_revenue",
                    },
                    {
                        "fact_id": "fact_2",
                        "task_id": "task_revenue_by_channel",
                        "label": "收入",
                        "value": 120.0,
                        "dimension": {"channel": "organic"},
                        "source_columns": ["channel", "total_revenue"],
                        "source_row_refs": ["task_revenue_by_channel:row:1"],
                        "evidence_ref": "evidence:task_revenue_by_channel:row:1:total_revenue",
                    },
                ],
                "derived_metrics": [],
            }
        ],
        "facts": [],
        "derived_metrics": [],
        "data_limits": [
            "task helper failed: SELECT * FROM orders; trace_path=/tmp/ws/trace.json provider_metadata={'token':'sk-test'}"
        ],
        "tool_calls": [
            {
                "tool_name": "sql_execution",
                "purpose": "task_revenue_by_channel",
                "input_summary": "SELECT channel, SUM(revenue) FROM orders",
                "output_summary": "provider_metadata sk-test /tmp/ws/trace.json",
                "status": "completed",
            }
        ],
        "task_refs": ["task_revenue_by_channel"],
        "source_pack_id": "source_pack_internal",
        "confidence": "medium",
    }


def _assert_answer_safe_prompt(provider):
    request = provider.requests[0]
    ledger = request.metadata["schema_context"]["question_evidence_ledger"]
    serialized = request.prompt + " " + str(request.metadata)

    assert "evidence_groups" in ledger
    assert ledger["evidence_groups"][0]["group_id"] == "evidence_group_1"
    assert "facts" not in ledger
    assert "derived_metrics" not in ledger

    forbidden = (
        "ledger_id",
        "source_pack_id",
        "task_id",
        "task_revenue_by_channel",
        "source_row_refs",
        "SELECT",
        "trace_path",
        "provider_metadata",
        "sk-test",
        "/tmp/ws",
        "[[",
        "raw_rows",
    )
    for marker in forbidden:
        assert marker not in serialized


def test_provider_backed_business_answer_agent_generates_business_answer_not_parameter_dump():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_provider_backed_insight",
        "session_id": "session_provider_backed_insight",
        "user_question": "哪个渠道该加预算？",
        "execution_result": {
            "success": True,
            "columns": ["channel", "revenue"],
            "rows": [["paid_search", 200.0], ["organic", 120.0]],
            "row_count": 2,
        },
        "question_evidence_ledger": _grouped_channel_revenue_ledger(),
        "trace": [],
    }
    provider = _CapturingProvider(
        {
            "candidate_claims": [
                {"claim": "paid_search 收入为 200.0。", "category": "hard_fact"},
                {"claim": "organic 收入为 120.0。", "category": "hard_fact"},
            ],
            "business_answer": {
                "headline": "建议优先加码 paid_search",
                "direct_answer": "建议优先加码 paid_search，因为它贡献了最高收入 200.0。",
                "why": "证据显示 paid_search 的收入为 200.0，高于 organic 的 120.0。",
                "evidence_bullets": ["paid_search 收入为 200.0。", "organic 收入为 120.0。"],
                "recommendations": ["优先复盘 paid_search 的投放和转化动作。"],
                "caveats": [],
                "confidence": "high",
            },
        }
    )

    result = run_business_answer_agent(
        state,
        provider=provider,
    )

    assert result["business_answer_generation"]["source"] == "provider"
    assert set(result["business_answer"]) == NEW_BUSINESS_ANSWER_KEYS
    assert result["business_answer"] == {
        "headline": "建议优先加码 paid_search",
        "direct_answer": "建议优先加码 paid_search，因为它贡献了最高收入 200.0。",
        "why": "证据显示 paid_search 的收入为 200.0，高于 organic 的 120.0。",
        "evidence_bullets": ["paid_search 收入为 200.0。", "organic 收入为 120.0。"],
        "recommendations": ["优先复盘 paid_search 的投放和转化动作。"],
        "caveats": [],
        "confidence": "high",
    }
    assert result["final_answer"] == result["business_answer"]["direct_answer"]
    assert "channel=" not in result["final_answer"]
    assert "channel=" not in " ".join(
        [
            result["business_answer"]["headline"],
            result["business_answer"]["direct_answer"],
            result["business_answer"]["why"],
            *result["business_answer"]["evidence_bullets"],
            *result["business_answer"]["recommendations"],
            *result["business_answer"]["caveats"],
        ]
    )
    _assert_answer_safe_prompt(provider)


def test_provider_backed_business_answer_agent_normalizes_minor_schema_drift_without_template_answer():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_provider_schema_drift",
        "session_id": "session_provider_schema_drift",
        "user_question": "最近90天各渠道收入表现怎么样？",
        "execution_result": {
            "success": True,
            "columns": ["channel", "revenue"],
            "rows": [["paid_search", 200.0], ["organic", 120.0]],
            "row_count": 2,
        },
        "question_evidence_ledger": _grouped_channel_revenue_ledger(),
        "trace": [],
    }
    provider = _CapturingProvider(
        {
            "notes": "minor non-contract field from provider",
            "business_answer": {
                "headline": "paid_search 收入领先",
                "direct_answer": "最近90天 paid_search 收入为 200.0，高于 organic 的 120.0。",
                "why": "证据显示 paid_search 和 organic 的收入分别为 200.0 和 120.0。",
                "evidence_bullets": "paid_search 收入为 200.0。",
                "recommendations": "",
                "caveats": "结论仅基于本轮证据。",
                "confidence": "medium",
            },
        }
    )

    result = run_business_answer_agent(state, provider=provider)

    assert result["business_answer_generation"]["source"] == "provider"
    assert result["business_answer_generation"]["success"] is True
    assert result["business_answer"]["direct_answer"].startswith("最近90天 paid_search")
    assert result["business_answer"]["evidence_bullets"] == ["paid_search 收入为 200.0。"]
    assert result["business_answer"]["recommendations"] == []
    assert "业务回答生成失败" not in result["final_answer"]
    assert "根据已验证证据" not in result["final_answer"]


def test_provider_backed_business_answer_agent_retries_model_rewrite_when_review_scrubs_answer_empty():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_provider_retry_after_scrub",
        "session_id": "session_provider_retry_after_scrub",
        "user_question": "最近90天各渠道收入表现怎么样？",
        "execution_result": {
            "success": True,
            "columns": ["channel", "revenue"],
            "rows": [["paid_search", 200.0], ["organic", 120.0]],
            "row_count": 2,
        },
        "question_evidence_ledger": _grouped_channel_revenue_ledger(),
        "trace": [],
    }
    provider = _SequentialProvider(
        [
            {
                "candidate_claims": [{"claim": "paid_search 收入为 200.0。", "category": "hard_fact"}],
                "business_answer": {
                    "headline": "SELECT channel, revenue 内部字段泄漏",
                    "direct_answer": "SELECT channel, revenue 内部字段泄漏",
                    "why": "SELECT channel, revenue 内部字段泄漏",
                    "evidence_bullets": [],
                    "recommendations": [],
                    "caveats": [],
                    "confidence": "medium",
                },
            },
            {
                "candidate_claims": [
                    {"claim": "paid_search 收入为 200.0。", "category": "hard_fact"},
                    {"claim": "organic 收入为 120.0。", "category": "hard_fact"},
                ],
                "business_answer": {
                    "headline": "paid_search 收入领先",
                    "direct_answer": "最近90天 paid_search 收入为 200.0，高于 organic 的 120.0。",
                    "why": "证据显示 paid_search 和 organic 的收入分别为 200.0 和 120.0。",
                    "evidence_bullets": ["paid_search 收入为 200.0。", "organic 收入为 120.0。"],
                    "recommendations": [],
                    "caveats": ["结论仅基于本轮证据。"],
                    "confidence": "medium",
                },
            },
        ]
    )

    result = run_business_answer_agent(state, provider=provider)

    assert len(provider.requests) == 2
    assert "safe-review retry" in provider.requests[1].prompt
    assert result["business_answer_generation"]["source"] == "provider"
    assert result["business_answer_generation"]["retry_used"] is True
    assert result["business_answer_generation"]["success"] is True
    assert result["business_answer"]["direct_answer"].startswith("最近90天 paid_search")
    assert "业务回答生成失败" not in result["final_answer"]
    assert "SELECT" not in result["final_answer"]
    assert "根据已验证证据" not in result["final_answer"]


def test_provider_backed_business_answer_agent_keeps_exact_evidence_anchor():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_provider_backed_insight_anchor",
        "session_id": "session_provider_backed_insight_anchor",
        "user_question": "收入最高的获客渠道是谁？",
        "execution_result": {
            "success": True,
            "columns": ["channel", "total_revenue"],
            "rows": [["email", 44548.53]],
            "row_count": 1,
        },
        "question_evidence_ledger": {
            **_grouped_channel_revenue_ledger(),
            "evidence_groups": [
                {
                    **_grouped_channel_revenue_ledger()["evidence_groups"][0],
                    "facts": [
                        {
                            "label": "收入",
                            "value": 44548.53,
                            "dimension": {"channel": "email"},
                            "source_columns": ["channel", "total_revenue"],
                            "evidence_ref": "evidence:row:0:total_revenue",
                        }
                    ],
                }
            ],
            "data_limits": [],
        },
        "trace": [],
    }
    provider = _CapturingProvider(
        {
            "candidate_claims": [{"claim": "email 渠道收入最高，为 44548.53。", "category": "hard_fact"}],
            "business_answer": {
                "headline": "email 是收入最高渠道",
                "direct_answer": "收入最高的渠道值得优先复盘其投放和转化动作。",
                "why": "当前证据显示 email 渠道收入最高。",
                "evidence_bullets": ["email 渠道收入最高，为 44548.53。"],
                "recommendations": ["复盘 email 的投放和转化动作。"],
                "caveats": [],
                "confidence": "medium",
            },
        }
    )

    result = run_business_answer_agent(
        state,
        provider=provider,
    )

    assert result["final_answer"] == result["business_answer"]["direct_answer"]
    assert "email" in " ".join(result["business_answer"]["evidence_bullets"])
    assert "44548.53" in " ".join(result["business_answer"]["evidence_bullets"])
    assert "channel=" not in result["final_answer"]
    _assert_answer_safe_prompt(provider)


def test_provider_backed_business_answer_agent_without_grouped_ledger_does_not_prompt_from_raw_rows():
    from workspaces.business_answer_agent import run_business_answer_agent

    provider = _CapturingProvider(
        {
            "candidate_claims": [{"claim": "paid_search 收入为 200.0。", "category": "hard_fact"}],
            "business_answer": {
                "headline": "paid_search 收入最高",
                "direct_answer": "paid_search 收入为 200.0。",
                "why": "raw rows show paid_search.",
                "evidence_bullets": ["paid_search 收入为 200.0。"],
                "recommendations": [],
                "caveats": [],
                "confidence": "medium",
            },
        }
    )
    result = run_business_answer_agent(
        {
            "run_id": "run_no_grouped_ledger",
            "session_id": "session_no_grouped_ledger",
            "user_question": "哪个渠道收入最高？",
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["paid_search", 200.0]],
                "row_count": 1,
                "sql": "SELECT channel, revenue FROM orders",
            },
            "trace": [],
        },
        provider=provider,
    )

    answer_text = " ".join(
        [
            result["business_answer"]["headline"],
            result["business_answer"]["direct_answer"],
            result["business_answer"]["why"],
            *result["business_answer"]["evidence_bullets"],
            *result["business_answer"]["recommendations"],
            *result["business_answer"]["caveats"],
        ]
    )
    assert provider.requests == []
    assert result["business_answer_generation"]["source"] == "provider_unavailable"
    assert result["business_answer_generation"]["success"] is False
    assert "paid_search" not in answer_text
    assert "200.0" not in answer_text
    assert "根据已验证证据" not in answer_text
    assert "无可用模型时使用证据账本回答" not in answer_text
