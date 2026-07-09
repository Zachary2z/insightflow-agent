from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def _prepared_state():
    from agents.context_retriever import run_context_retriever_agent
    from agents.metric_agent import run_metric_agent
    from agents.schema_agent import run_schema_agent
    from agents.sql_generator import run_sql_generator
    from agents.supervisor import initialize_run

    state = initialize_run(
        "最近 30 天销售额最高的 5 个商品是什么？",
        run_id="run_guarded_llm_test",
        session_id="session_guarded_llm_test",
    )
    state["db_path"] = DB_PATH
    state = run_schema_agent(state, DB_PATH)
    state = run_metric_agent(state)
    state = run_context_retriever_agent(state)
    return run_sql_generator(state)


def test_guarded_sql_candidate_accepts_only_validated_select_without_execution():
    from agents.guarded_llm_enhancer import run_guarded_sql_candidate_agent

    captured = {}

    def mock_sql_provider(prompt):
        captured["prompt"] = prompt
        return {
            "sql_candidates": [
                {
                    "sql": """
SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE o.status = 'paid'
GROUP BY p.product_name
ORDER BY gmv DESC
LIMIT 3
""".strip(),
                    "rationale": "Use paid GMV and a smaller Top 3.",
                }
            ]
        }

    state = _prepared_state()
    result = run_guarded_sql_candidate_agent(state, llm_provider=mock_sql_provider)

    enhancement = result["llm_sql_enhancement"]
    assert enhancement["success"] is True
    assert enhancement["provider_called"] is True
    assert enhancement["accepted"] is True
    assert enhancement["fallback_used"] is False
    assert enhancement["accepted_sql"].endswith("LIMIT 3")
    assert result["generated_sql"] == enhancement["accepted_sql"]
    assert "execution_result" not in enhancement
    assert "run_sql" not in enhancement
    assert enhancement["candidates"][0]["review_result"]["approved"] is True
    assert "schema_text" in captured["prompt"]
    assert "metric_context" in captured["prompt"]
    assert "business_context" in captured["prompt"]
    assert captured["prompt"]["must_validate_sql"] is True
    assert captured["prompt"]["must_not_execute_sql"] is True
    assert result["trace"][-1]["node"] == "guarded_sql_candidate_agent"


def test_guarded_sql_candidate_prompt_includes_workspace_context():
    from agents.guarded_llm_enhancer import run_guarded_sql_candidate_agent

    captured = {}

    def mock_sql_provider(prompt):
        captured["prompt"] = prompt
        return {
            "sql_candidates": [
                {
                    "sql": "SELECT status, COUNT(*) AS order_count FROM orders GROUP BY status LIMIT 5",
                    "rationale": "Use workspace revenue by channel.",
                }
            ]
        }

    state = _prepared_state()
    state["workspace_context"] = {
        "workspace_data_source_selected": True,
        "guidance": ["Use max order_date for dataset-relative recent windows."],
        "tables": [{"table_name": "orders", "columns": [{"name": "order_date", "value_range": {"max": "2025-12-26"}}]}],
    }
    result = run_guarded_sql_candidate_agent(state, llm_provider=mock_sql_provider)

    assert result["llm_sql_enhancement"]["provider_called"] is True
    assert captured["prompt"]["workspace_context"]["workspace_data_source_selected"] is True
    assert captured["prompt"]["workspace_context"]["tables"][0]["columns"][0]["value_range"]["max"] == "2025-12-26"


def test_guarded_sql_candidate_rejects_unsafe_sql_and_keeps_deterministic_sql():
    from agents.guarded_llm_enhancer import run_guarded_sql_candidate_agent

    state = _prepared_state()
    deterministic_sql = state["generated_sql"]

    result = run_guarded_sql_candidate_agent(
        state,
        llm_provider=lambda prompt: {
            "sql_candidates": [
                {"sql": "DELETE FROM orders WHERE status = 'cancelled'", "rationale": "unsafe"},
                {"sql": "SELECT email FROM users LIMIT 5", "rationale": "sensitive"},
            ]
        },
    )

    enhancement = result["llm_sql_enhancement"]
    assert enhancement["success"] is False
    assert enhancement["accepted"] is False
    assert enhancement["fallback_used"] is True
    assert "no approved sql candidates" in enhancement["error"]
    assert result["generated_sql"] == deterministic_sql
    assert len(enhancement["candidates"]) == 2
    assert all(candidate["review_result"]["approved"] is False for candidate in enhancement["candidates"])


def test_guarded_sql_candidate_falls_back_without_provider():
    from agents.guarded_llm_enhancer import run_guarded_sql_candidate_agent

    state = _prepared_state()
    deterministic_sql = state["generated_sql"]

    result = run_guarded_sql_candidate_agent(state)

    assert result["llm_sql_enhancement"]["success"] is True
    assert result["llm_sql_enhancement"]["provider_called"] is False
    assert result["llm_sql_enhancement"]["fallback_used"] is True
    assert result["generated_sql"] == deterministic_sql
