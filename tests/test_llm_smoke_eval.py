class _SequenceProvider:
    model = "mock-sequence"

    def __init__(self, responses):
        self.responses = list(responses)

    def generate(self, request):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


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
                "variables": {
                    "user_question": "最近 30 天销售额最高的 5 个商品是什么？",
                    "workspace_context": {},
                },
                "expected_keys": ["strategy", "intent", "missing_slots", "clarification_questions", "risk_flags"],
                "validate_output": True,
                "expected_success": True,
            },
            {
                "case_id": "malformed_json_is_expected_failure",
                "prompt_id": "question_understanding",
                "variables": {
                    "user_question": "最近 30 天销售额最高的 5 个商品是什么？",
                    "workspace_context": {},
                },
                "expected_keys": ["strategy"],
                "validate_output": True,
                "expected_success": False,
                "expected_error_type": "llm_malformed_json_error",
            },
            {
                "case_id": "schema_mismatch_is_expected_failure",
                "prompt_id": "question_understanding",
                "variables": {
                    "user_question": "最近 30 天销售额最高的 5 个商品是什么？",
                    "workspace_context": {},
                },
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
