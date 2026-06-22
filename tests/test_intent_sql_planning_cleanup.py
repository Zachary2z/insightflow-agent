from __future__ import annotations

from pathlib import Path

from llm_ops.provider import MockLLMProvider


def _provider_intent() -> dict:
    return {
        "strategy": "llm_candidate",
        "intent": {
            "metric": "gmv",
            "dimension": "category",
            "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近 30 天"},
            "filters": ["paid_orders"],
            "operation": "comparison",
            "limit": 5,
            "risk_flags": [],
        },
        "missing_slots": [],
        "clarification_questions": [],
        "risk_flags": [],
        "reason": "Provider chose a non-template category comparison analysis.",
    }


def _provider_sql_plan() -> dict:
    return {
        "strategy": "llm_candidate",
        "matched_template": "",
        "confidence": 0.83,
        "missing_slots": [],
        "clarification_questions": [],
        "risk_flags": [],
        "reason": "Use a guarded SQL candidate because this comparison is not a stable template.",
    }


def test_provider_malformed_question_understanding_does_not_revive_keyword_router():
    from question_understanding.provider_backed import understand_question_with_provider

    result = understand_question_with_provider(
        "最近 30 天销售额最高的 5 个商品是什么？",
        provider=MockLLMProvider('{"strategy": "template",'),
    )

    assert result["success"] is True
    assert result["source"] == "provider_unavailable"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["strategy"] == "clarify"
    assert result["intent"]["metric"] == ""
    assert result["intent"]["dimension"] == ""
    assert result["provider_error"]


def test_sensitive_question_is_rejected_before_provider_can_override_safety():
    from question_understanding.provider_backed import understand_question_with_provider

    result = understand_question_with_provider(
        "导出所有用户的手机号和邮箱。",
        provider=MockLLMProvider(_provider_intent()),
    )

    assert result["success"] is True
    assert result["source"] == "safety_guard"
    assert result["strategy"] == "reject"
    assert result["provider_called"] is False
    assert "sensitive_field" in result["risk_flags"]
    assert "bulk_export" in result["risk_flags"]


def test_provider_sql_planning_sql_leak_does_not_fall_back_to_template_router():
    from sql_planning.provider_backed import plan_sql_strategy_with_provider

    understanding = {
        "success": True,
        "strategy": "template",
        "intent": {
            "metric": "gmv",
            "dimension": "product",
            "time_range": {"type": "last_n_days", "value": 30},
            "filters": ["paid_orders"],
            "operation": "top_n",
            "limit": 5,
            "risk_flags": [],
        },
        "missing_slots": [],
        "clarification_questions": [],
        "risk_flags": [],
        "question": "最近 30 天销售额最高的 5 个商品是什么？",
    }

    result = plan_sql_strategy_with_provider(
        understanding,
        provider=MockLLMProvider({**_provider_sql_plan(), "sql": "SELECT * FROM orders"}),
    )

    assert result["success"] is True
    assert result["source"] == "provider_unavailable"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["strategy"] == "clarify"
    assert result["matched_template"] == ""
    assert result["validation_error"]


def test_provider_llm_candidate_workflow_skips_sql_generator_but_keeps_sql_reviewer(tmp_path):
    from graph.workflow import run_workflow

    result = run_workflow(
        "比较最近 30 天各品类 GMV。",
        db_path=Path(__file__).resolve().parents[1] / "data" / "ecommerce.db",
        trace_dir=tmp_path,
        run_id="run_p82_provider_sql_candidate",
        session_id="session_p82_provider_sql_candidate",
        question_understanding_provider=MockLLMProvider(_provider_intent()),
        sql_planning_provider=MockLLMProvider(_provider_sql_plan()),
        sql_candidate_provider=MockLLMProvider(
            {
                "sql_candidates": [
                    {
                        "sql": (
                            "SELECT c.category_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv "
                            "FROM orders o "
                            "JOIN order_items oi ON o.id = oi.order_id "
                            "JOIN products p ON oi.product_id = p.id "
                            "JOIN categories c ON p.category_id = c.id "
                            "WHERE o.status = 'paid' "
                            "GROUP BY c.category_name ORDER BY gmv DESC LIMIT 5"
                        ),
                        "rationale": "Aggregate paid GMV by category from real tables.",
                    }
                ]
            }
        ),
    )

    trace_nodes = [event.get("node") for event in result["trace"]]
    assert result["status"] == "completed"
    assert "sql_generator_agent" not in trace_nodes
    assert "guarded_sql_candidate_agent" in trace_nodes
    assert "sql_reviewer_agent" in trace_nodes
    assert trace_nodes.index("guarded_sql_candidate_agent") < trace_nodes.index("sql_reviewer_agent")
    assert result["review_result"]["approved"] is True
    assert result["execution_result"]["success"] is True
    assert result["sql_planning"]["source"] == "provider"
    assert result["sql_planning"]["strategy"] == "llm_candidate"


def test_provider_template_workflow_uses_matched_template_not_question_keywords(tmp_path):
    from graph.workflow import run_workflow

    provider_intent = _provider_intent()
    provider_intent["strategy"] = "template"
    provider_intent["intent"] = {
        **provider_intent["intent"],
        "dimension": "category",
        "operation": "top_n",
    }
    result = run_workflow(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path=Path(__file__).resolve().parents[1] / "data" / "ecommerce.db",
        trace_dir=tmp_path,
        run_id="run_p82_provider_template",
        session_id="session_p82_provider_template",
        question_understanding_provider=MockLLMProvider(provider_intent),
        sql_planning_provider=MockLLMProvider(
            {
                "strategy": "template",
                "matched_template": "top_categories_gmv",
                "confidence": 0.91,
                "missing_slots": [],
                "clarification_questions": [],
                "risk_flags": [],
                "reason": "Provider selected category GMV even though the wording contains product.",
            }
        ),
    )

    assert result["status"] == "completed"
    assert result["sql_planning"]["source"] == "provider"
    assert result["sql_planning"]["matched_template"] == "top_categories_gmv"
    assert "c.category_name" in result["generated_sql"]
    assert "p.product_name" not in result["generated_sql"]
    assert result["review_result"]["approved"] is True
    assert result["execution_result"]["success"] is True
