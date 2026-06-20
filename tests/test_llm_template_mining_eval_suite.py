class _SequenceProvider:
    model = "mock-sequence"

    def __init__(self, responses):
        self.responses = list(responses)

    def generate(self, request):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_template_mining_reads_successful_llm_candidate_from_workflow_trace(tmp_path):
    from graph.workflow import run_workflow
    from llm_ops.provider import MockLLMProvider
    from sql_planning.feedback import mine_template_candidates_from_trace_files

    result = run_workflow(
        "最近 30 天按用户分析复购率趋势",
        trace_dir=tmp_path,
        run_id="run_template_mining_trace",
        sql_candidate_provider=MockLLMProvider(
            {
                "sql_candidates": [
                    {
                        "sql": (
                            "SELECT users.id, COUNT(DISTINCT orders.id) AS order_count "
                            "FROM users JOIN orders ON users.id = orders.user_id "
                            "WHERE orders.status = 'paid' "
                            "GROUP BY users.id "
                            "HAVING COUNT(DISTINCT orders.id) > 1 "
                            "LIMIT 100"
                        ),
                        "rationale": "User-level repeat purchase proxy from paid orders.",
                    }
                ]
            }
        ),
    )

    mining = mine_template_candidates_from_trace_files([result["trace_path"]], min_success_count=1)

    assert mining["success"] is True
    assert mining["source"] == "workflow_trace"
    assert mining["candidates"] == [
        {
            "intent_signature": "repurchase_rate:user:trend",
            "success_count": 1,
            "recommended_template_id": "repurchase_rate_user_trend",
            "sample_questions": ["最近 30 天按用户分析复购率趋势"],
            "auto_apply": False,
            "reason": "Repeated successful llm_candidate pattern can be promoted to a deterministic template.",
        }
    ]
    assert "sql" not in mining["candidates"][0]
    assert any(
        event.get("node") == "guarded_sql_candidate_agent"
        and event.get("template_mining_event", {}).get("accepted") is True
        for event in result["trace"]
    )


def test_llm_smoke_eval_validates_schema_and_expected_failures():
    from llm_ops.eval_smoke import run_llm_smoke_eval

    provider = _SequenceProvider(
        [
            {
                "strategy": "template",
                "intent": {
                    "metric": "gmv",
                    "dimension": "product",
                    "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近 30 天"},
                    "filters": ["paid_orders"],
                    "operation": "top_n",
                    "limit": 5,
                    "risk_flags": [],
                },
                "missing_slots": [],
                "clarification_questions": [],
                "risk_flags": [],
                "reason": "Complete BI intent.",
            },
            '{"strategy": "template",',
            {"strategy": "template", "intent": "not an object"},
        ]
    )

    result = run_llm_smoke_eval(
        [
            {
                "case_id": "valid_question_understanding",
                "prompt_id": "question_understanding",
                "variables": {"user_question": "最近 30 天销售额最高的 5 个商品是什么？"},
                "expected_keys": ["strategy", "intent", "missing_slots", "clarification_questions", "risk_flags"],
                "validate_output": True,
                "expected_success": True,
            },
            {
                "case_id": "malformed_json_is_expected_failure",
                "prompt_id": "question_understanding",
                "variables": {"user_question": "最近 30 天销售额最高的 5 个商品是什么？"},
                "expected_keys": ["strategy"],
                "validate_output": True,
                "expected_success": False,
                "expected_error_type": "llm_malformed_json_error",
            },
            {
                "case_id": "schema_mismatch_is_expected_failure",
                "prompt_id": "question_understanding",
                "variables": {"user_question": "最近 30 天销售额最高的 5 个商品是什么？"},
                "expected_keys": ["strategy"],
                "validate_output": True,
                "expected_success": False,
                "expected_error_type": "llm_schema_validation_error",
            },
        ],
        provider=provider,
    )

    assert result["success"] is True
    assert result["total_cases"] == 3
    assert result["passed"] == 3
    assert result["failed"] == 0
    assert result["cases"][0]["validation_enabled"] is True
    assert result["cases"][1]["provider_result"]["error_type"] == "llm_malformed_json_error"
    assert result["cases"][2]["provider_result"]["error_type"] == "llm_schema_validation_error"
