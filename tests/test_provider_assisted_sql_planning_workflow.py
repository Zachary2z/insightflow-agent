from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def _planning_payload() -> dict:
    return {
        "strategy": "llm_candidate",
        "matched_template": "",
        "confidence": 0.83,
        "reason": "Complete AOV comparison intent needs a guarded SQL candidate.",
        "risk_flags": [],
    }


def _valid_aov_city_sql() -> str:
    return """
SELECT u.city, ROUND(SUM(oi.quantity * oi.unit_price) / COUNT(DISTINCT o.id), 2) AS aov
FROM orders o
JOIN users u ON o.user_id = u.id
JOIN order_items oi ON o.id = oi.order_id
WHERE o.status = 'paid'
GROUP BY u.city
ORDER BY aov DESC
LIMIT 100
""".strip()


def test_provider_assisted_sql_planning_uses_valid_provider_output_without_sql():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.router import understand_question
    from sql_planning.provider_backed import plan_sql_strategy_with_provider

    understanding = understand_question("本月各城市客单价对比")
    result = plan_sql_strategy_with_provider(
        understanding,
        provider=MockLLMProvider(_planning_payload()),
    )

    assert result["success"] is True
    assert result["source"] == "provider"
    assert result["provider_called"] is True
    assert result["fallback_used"] is False
    assert result["strategy"] == "llm_candidate"
    assert result["confidence"] == 0.83
    assert result["candidate_policy"]["provider_prompt_id"] == "guarded_sql_candidate"
    assert result["validation_policy"]["must_validate_sql_before_execution"] is True
    assert "sql" not in result
    assert "generated_sql" not in result


def test_provider_assisted_sql_planning_falls_back_on_malformed_json():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.router import understand_question
    from sql_planning.provider_backed import plan_sql_strategy_with_provider

    understanding = understand_question("本月各城市客单价对比")
    result = plan_sql_strategy_with_provider(
        understanding,
        provider=MockLLMProvider('{"strategy": "llm_candidate",'),
    )

    assert result["success"] is True
    assert result["source"] == "deterministic"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["provider_error"]
    assert result["strategy"] == "llm_candidate"


def test_provider_assisted_sql_planning_falls_back_on_schema_mismatch_or_sql_leak():
    from llm_ops.provider import MockLLMProvider
    from question_understanding.router import understand_question
    from sql_planning.provider_backed import plan_sql_strategy_with_provider

    understanding = understand_question("本月各城市客单价对比")
    result = plan_sql_strategy_with_provider(
        understanding,
        provider=MockLLMProvider({**_planning_payload(), "sql": "SELECT * FROM orders LIMIT 10"}),
    )

    assert result["success"] is True
    assert result["source"] == "deterministic"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["validation_error"]
    assert result["strategy"] == "llm_candidate"
    assert "sql" not in result
    assert "generated_sql" not in result


def test_provider_assisted_sql_planning_none_keeps_deterministic_baseline():
    from question_understanding.router import understand_question
    from sql_planning.provider_backed import plan_sql_strategy_with_provider

    understanding = understand_question("本月各城市客单价对比")
    result = plan_sql_strategy_with_provider(understanding, provider=None)

    assert result["success"] is True
    assert result["source"] == "deterministic"
    assert result["provider_called"] is False
    assert result["fallback_used"] is False
    assert result["strategy"] == "llm_candidate"


def test_core_workflow_uses_provider_planning_and_validated_sql_candidate(tmp_path):
    from graph.workflow import run_workflow
    from llm_ops.provider import MockLLMProvider

    result = run_workflow(
        "本月各城市客单价对比",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_provider_sql_planning_runtime",
        session_id="session_provider_sql_planning_runtime",
        sql_planning_provider=MockLLMProvider(_planning_payload()),
        sql_candidate_provider=MockLLMProvider(
            {
                "sql_candidates": [
                    {
                        "sql": _valid_aov_city_sql(),
                        "rationale": "Compute paid-order AOV by city and let SQL Reviewer approve before execution.",
                    }
                ]
            }
        ),
    )

    assert result["status"] == "completed"
    assert result["sql_planning"]["source"] == "provider"
    assert result["sql_planning"]["provider_called"] is True
    assert result["sql_planning"]["fallback_used"] is False
    assert result["sql_routing_strategy"] == "llm_candidate"
    assert result["llm_sql_enhancement"]["provider_called"] is True
    assert result["llm_sql_enhancement"]["accepted"] is True
    assert result["generated_sql"] == result["llm_sql_enhancement"]["accepted_sql"]
    assert result["review_result"]["approved"] is True
    assert result["execution_result"]["success"] is True
    trace_nodes = [event["node"] for event in result["trace"]]
    assert trace_nodes.index("sql_planning_router_agent") < trace_nodes.index("sql_generator_agent")
    assert trace_nodes.index("guarded_sql_candidate_agent") < trace_nodes.index("sql_reviewer_agent")
    assert "run_sql" not in result["llm_sql_enhancement"]


def test_core_workflow_rejects_unsafe_provider_sql_candidate_and_keeps_reviewer_boundary(tmp_path):
    from graph.workflow import run_workflow
    from llm_ops.provider import MockLLMProvider

    result = run_workflow(
        "本月各城市客单价对比",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_provider_sql_candidate_rejected",
        session_id="session_provider_sql_candidate_rejected",
        sql_planning_provider=MockLLMProvider(_planning_payload()),
        sql_candidate_provider=MockLLMProvider(
            {
                "sql_candidates": [
                    {"sql": "DELETE FROM orders WHERE status = 'cancelled'", "rationale": "unsafe"}
                ]
            }
        ),
    )

    assert result["status"] == "completed"
    assert result["llm_sql_enhancement"]["provider_called"] is True
    assert result["llm_sql_enhancement"]["accepted"] is False
    assert result["llm_sql_enhancement"]["fallback_used"] is True
    assert result["review_result"]["approved"] is True
    assert result["execution_result"]["success"] is True
    assert result["generated_sql"].lower().startswith("select")


def test_core_workflow_sql_planning_no_key_baseline_preserves_sql_workflow(tmp_path, monkeypatch):
    from graph.workflow import run_workflow

    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING", "1")
    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    result = run_workflow(
        "本月各城市客单价对比",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_no_key_sql_planning_runtime",
        session_id="session_no_key_sql_planning_runtime",
    )

    assert result["status"] == "completed"
    assert result["sql_planning"]["source"] == "deterministic"
    assert result["sql_planning"]["provider_called"] is False
    assert result["llm_sql_enhancement"]["provider_called"] is False
    assert result["review_result"]["approved"] is True
    assert result["execution_result"]["success"] is True
