from pathlib import Path


def _base_state(question: str):
    from agents.supervisor import initialize_run

    state = initialize_run(
        question,
        run_id="run_chart_agent_test",
        session_id="session_chart_agent_test",
    )
    state["execution_result"] = {
        "success": True,
        "columns": ["product_name", "gmv"],
        "rows": [["Laptop Pro 14", 511248.56], ["Camera A", 456050.99]],
        "row_count": 2,
    }
    return state


def test_chart_agent_infers_bar_for_ranking_question_and_appends_trace(tmp_path):
    from agents.chart_agent import run_chart_agent

    state = _base_state("最近 30 天销售额最高的 5 个商品是什么？")

    state = run_chart_agent(state, output_dir=tmp_path)

    assert state["chart_result"]["success"] is True
    assert state["chart_result"]["chart_type"] == "bar"
    assert Path(state["chart_path"]).exists()
    assert state["chart_paths"] == [state["chart_path"]]
    assert state["trace"][-1]["node"] == "chart_agent"
    assert state["trace"][-1]["tool_name"] == "generate_chart"


def test_chart_agent_infers_line_for_trend_question(tmp_path):
    from agents.chart_agent import run_chart_agent

    state = _base_state("最近 6 个月每个月的 GMV 趋势是什么？")
    state["execution_result"] = {
        "success": True,
        "columns": ["month", "gmv"],
        "rows": [["2026-01", 1200.0], ["2026-02", 1800.0], ["2026-03", 1500.0]],
        "row_count": 3,
    }

    state = run_chart_agent(state, output_dir=tmp_path)

    assert state["chart_result"]["success"] is True
    assert state["chart_result"]["chart_type"] == "line"
    assert Path(state["chart_path"]).exists()


def test_chart_agent_handles_missing_execution_result_without_crashing(tmp_path):
    from agents.chart_agent import run_chart_agent
    from agents.supervisor import initialize_run

    state = initialize_run("最近 30 天销售额最高的 5 个商品是什么？")

    state = run_chart_agent(state, output_dir=tmp_path)

    assert state["chart_result"]["success"] is False
    assert "execution_result is required" in state["chart_result"]["error"]
    assert state["chart_path"] == ""
    assert state["chart_paths"] == []
    assert state["chart_warning"] == state["chart_result"]["error"]
    assert state["trace"][-1]["node"] == "chart_agent"
    assert state["trace"][-1]["status"] == "error"
