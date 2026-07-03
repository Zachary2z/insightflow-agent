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


def _create_support_issues_db(tmp_path) -> Path:
    import sqlite3

    db_path = tmp_path / "support_issues.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE support_issues (issue_type TEXT, business_date TEXT, ticket_count INTEGER, avg_response_minutes REAL)"
        )
        conn.executemany(
            "INSERT INTO support_issues VALUES (?, ?, ?, ?)",
            [
                ("退款咨询", "2026-06-01", 320, 48.0),
                ("物流延迟", "2026-06-02", 180, 76.0),
                ("发票问题", "2026-06-03", 90, 22.0),
            ],
        )
    return db_path


def _support_priority_sql(limit: int = 1) -> str:
    return f"""
SELECT issue_type,
       SUM(ticket_count) AS total_tickets,
       AVG(avg_response_minutes) AS avg_response,
       SUM(ticket_count) * AVG(avg_response_minutes) AS priority_score
FROM support_issues
GROUP BY issue_type
ORDER BY priority_score DESC
LIMIT {limit}
""".strip()


def _support_priority_understanding() -> dict:
    return {
        "strategy": "llm_candidate",
        "intent": {
            "metric": "priority_score",
            "dimension": "issue_type",
            "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近90天"},
            "filters": [],
            "operation": "recommendation",
            "limit": 3,
        },
        "missing_slots": [],
        "clarification_questions": [],
        "risk_flags": [],
        "reason": "需要对多个客服问题进行优先级判断。",
    }


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
    assert result["source"] == "provider_unavailable"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["provider_error"]
    assert result["strategy"] == "clarify"


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
    assert result["source"] == "provider_unavailable"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["validation_error"]
    assert result["strategy"] == "clarify"
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
    assert "sql_generator_agent" not in trace_nodes
    assert trace_nodes.index("guarded_sql_candidate_agent") < trace_nodes.index("sql_reviewer_agent")
    assert "run_sql" not in result["llm_sql_enhancement"]


def test_core_workflow_widens_provider_limit_one_for_priority_comparison(tmp_path):
    from graph.workflow import run_workflow
    from llm_ops.provider import MockLLMProvider

    result = run_workflow(
        "最近90天哪个客服问题最需要优先处理，为什么？",
        db_path=_create_support_issues_db(tmp_path),
        trace_dir=tmp_path,
        run_id="run_provider_priority_comparison_scope",
        session_id="session_provider_priority_comparison_scope",
        question_understanding_provider=MockLLMProvider(_support_priority_understanding()),
        sql_planning_provider=MockLLMProvider(_planning_payload()),
        sql_candidate_provider=MockLLMProvider(
            {
                "sql_candidates": [
                    {
                        "sql": _support_priority_sql(limit=1),
                        "rationale": "Provider only returned the top row.",
                    }
                ]
            }
        ),
    )

    assert result["status"] == "completed"
    assert result["llm_sql_enhancement"]["accepted"] is True
    assert result["comparison_scope_adjustment"]["applied"] is True
    assert result["comparison_scope_adjustment"]["reason"] == "insufficient_comparison_scope"
    assert "LIMIT 1" not in result["generated_sql"].upper()
    assert result["execution_result"]["row_count"] >= 2
    rows_text = str(result["execution_result"]["rows"])
    assert "退款咨询" in rows_text
    assert "物流延迟" in rows_text


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

    assert result["status"] == "failed"
    assert result["llm_sql_enhancement"]["provider_called"] is True
    assert result["llm_sql_enhancement"]["accepted"] is False
    assert result["llm_sql_enhancement"]["fallback_used"] is True
    assert result.get("review_result", {}).get("approved") is False
    assert result.get("execution_result", {}) == {}
    assert not result.get("generated_sql", "")


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
