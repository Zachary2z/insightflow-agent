from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def _base_state():
    from agents.supervisor import initialize_run

    return initialize_run(
        "最近 30 天销售额最高的 5 个商品是什么？",
        run_id="run_test",
        session_id="session_test",
    )


def test_supervisor_initializes_structured_run_state():
    from agents.supervisor import initialize_run

    state = initialize_run("最近 30 天销售额最高的 5 个商品是什么？", run_id="run_001", session_id="session_001")

    assert state["success"] is True
    assert state["run_id"] == "run_001"
    assert state["session_id"] == "session_001"
    assert state["task_type"] == "sql_analysis"
    assert state["status"] == "initialized"
    assert state["retry_count"] == 0
    assert state["trace"][0]["node"] == "supervisor_agent"


def test_schema_and_metric_agents_call_tools_and_append_trace():
    from agents.metric_agent import run_metric_agent
    from agents.schema_agent import run_schema_agent

    state = _base_state()
    state = run_schema_agent(state, DB_PATH)
    state = run_metric_agent(state)

    assert state["database_schema"]["success"] is True
    assert "Table orders" in state["schema_text"]
    assert state["metric_context"]["success"] is True
    assert "gmv" in state["metric_context"]["matched_metrics"]
    assert [event["node"] for event in state["trace"]] == [
        "supervisor_agent",
        "schema_agent",
        "metric_agent",
    ]


def test_sql_generator_produces_parseable_structured_select_sql_without_execution():
    from agents.metric_agent import run_metric_agent
    from agents.schema_agent import run_schema_agent
    from agents.sql_generator import run_sql_generator

    state = run_metric_agent(run_schema_agent(_base_state(), DB_PATH))
    state = run_sql_generator(state)

    output = state["sql_generation"]
    assert output["success"] is True
    assert output["sql"].lower().lstrip().startswith("select")
    assert "run_sql" not in output
    assert "orders" in output["tables"]
    assert "order_items" in output["tables"]
    assert "gmv" in output["metrics"]
    assert state["generated_sql"] == output["sql"]
    assert state["trace"][-1]["node"] == "sql_generator_agent"


def test_sql_reviewer_agent_uses_validator_and_rejects_dangerous_sql():
    from agents.schema_agent import run_schema_agent
    from agents.sql_reviewer import run_sql_reviewer

    state = run_schema_agent(_base_state(), DB_PATH)
    state["generated_sql"] = "DELETE FROM orders WHERE status = 'cancelled'"

    state = run_sql_reviewer(state)

    assert state["review_result"]["approved"] is False
    assert state["review_result"]["risk_level"] == "high"
    assert state["trace"][-1]["tool_name"] == "validate_sql"


def test_error_fix_agent_repairs_known_column_error_once_without_running_sql():
    from agents.error_fixer import run_error_fix_agent
    from agents.schema_agent import run_schema_agent

    state = run_schema_agent(_base_state(), DB_PATH)
    state["generated_sql"] = "SELECT oi.price FROM order_items oi LIMIT 5"
    state["execution_result"] = {"success": False, "error": "no such column: oi.price"}
    state["retry_count"] = 0

    state = run_error_fix_agent(state)

    output = state["sql_fix"]
    assert output["success"] is True
    assert output["fixed_sql"] == "SELECT oi.unit_price FROM order_items oi LIMIT 5"
    assert output["retry_count"] == 1
    assert "unit_price" in output["fix_reason"]
    assert "run_sql" not in output
    assert state["fixed_sql"] == output["fixed_sql"]
    assert state["trace"][-1]["node"] == "error_fix_agent"


def test_insight_agent_answers_only_from_execution_result_rows():
    from agents.insight_agent import run_insight_agent

    state = _base_state()
    state["execution_result"] = {
        "success": True,
        "columns": ["product_name", "gmv"],
        "rows": [["Laptop Pro 14", 511248.56], ["Camera A", 456050.99]],
        "row_count": 2,
    }

    state = run_insight_agent(state)

    output = state["insight"]
    assert output["success"] is True
    assert output["data_used"] is True
    assert "Laptop Pro 14" in output["final_answer"]
    assert "511248.56" in output["final_answer"]
    assert state["final_answer"] == output["final_answer"]


def test_insight_agent_returns_error_when_execution_result_is_missing():
    from agents.insight_agent import run_insight_agent

    state = _base_state()

    state = run_insight_agent(state)

    assert state["insight"]["success"] is False
    assert state["insight"]["data_used"] is False
    assert "execution_result" in state["insight"]["error"]
