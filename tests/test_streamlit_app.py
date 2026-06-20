import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def test_example_questions_include_p0_demo_cases():
    from app import APP_SUBTITLE, DEMO_VIEWS, EXAMPLE_QUESTIONS

    assert "最近 30 天销售额最高的 5 个商品是什么？" in EXAMPLE_QUESTIONS
    assert "删除所有取消订单的数据。" in EXAMPLE_QUESTIONS
    assert "帮我导出所有用户的手机号和邮箱。" in EXAMPLE_QUESTIONS
    assert "P0 Agentic SQL Core" not in APP_SUBTITLE
    assert [view["id"] for view in DEMO_VIEWS] == [
        "sql_analysis",
        "report_generation",
        "weekly_business_review",
        "action_workflow",
        "mcp_tool_layer",
        "async_run_api",
        "trace_dashboard",
    ]


def test_build_capability_overview_makes_p1_p2_p3_visible():
    from app import build_capability_overview

    overview = build_capability_overview()

    labels = [item["label"] for item in overview]
    assert "SQL Analysis" in labels
    assert "Report Generation" in labels
    assert "Weekly Business Review" in labels
    assert "Action Workflow" in labels
    assert "MCP Tool Layer" in labels
    assert "Async Run API" in labels
    assert "Trace Dashboard" in labels
    assert all(item["status"] in {"available", "local-api"} for item in overview)


def test_run_report_generation_demo_creates_report_and_chart(tmp_path):
    from app import run_report_generation_demo

    result = run_report_generation_demo(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path=DB_PATH,
        trace_dir=tmp_path / "traces",
        report_dir=tmp_path / "reports",
        chart_dir=tmp_path / "charts",
        run_id="run_unified_report",
        session_id="session_unified_report",
    )

    assert result["status"] == "completed"
    assert result["evidence_result"]["success"] is True
    assert result["chart_result"]["success"] is True
    assert Path(result["chart_path"]).exists()
    assert result["report_result"]["success"] is True
    assert Path(result["report_path"]).exists()


def test_run_weekly_review_demo_exposes_sections_and_report_path(tmp_path):
    from app import run_weekly_review_demo

    result = run_weekly_review_demo(
        "帮我生成一份本周电商经营分析周报，包括销售额、订单量、Top 商品、下降品类和运营建议。",
        db_path=DB_PATH,
        trace_dir=tmp_path / "traces",
        report_dir=tmp_path / "reports",
        chart_dir=tmp_path / "charts",
        run_id="run_unified_weekly",
        session_id="session_unified_weekly",
    )

    assert result["status"] == "completed"
    assert result["report_sections"]
    assert result["report_sub_tasks"]
    assert Path(result["weekly_report_path"]).exists()


def test_run_action_workflow_demo_requires_and_uses_approval(tmp_path):
    from app import run_action_workflow_demo

    blocked = run_action_workflow_demo(action_db_path=tmp_path / "blocked.db", approved=False)
    approved = run_action_workflow_demo(action_db_path=tmp_path / "approved.db", approved=True)

    assert blocked["status"] == "waiting_for_approval"
    assert blocked["created_actions"] == []
    assert blocked["action_execution_result"]["success"] is False

    assert approved["status"] == "actions_verified"
    assert approved["action_execution_result"]["success"] is True
    assert approved["action_verification_result"]["success"] is True


def test_mcp_async_and_dashboard_demo_helpers_return_clear_summaries(tmp_path):
    from app import build_async_run_api_summary, build_mcp_contract_summary, build_trace_dashboard_summary

    mcp_summary = build_mcp_contract_summary()
    api_summary = build_async_run_api_summary()
    dashboard_summary = build_trace_dashboard_summary(trace_dir=tmp_path / "missing")

    assert {item["server_name"] for item in mcp_summary} == {
        "database-mcp-server",
        "report-mcp-server",
        "action-mcp-server",
    }
    assert "POST /api/runs" in api_summary["endpoints"]
    assert "GET /api/runs/{run_id}/trace" in api_summary["endpoints"]
    assert dashboard_summary["success"] is True
    assert dashboard_summary["trace_count"] == 0


def test_sync_selected_question_updates_input_and_clears_stale_result():
    from app import sync_selected_question

    session_state = {
        "selected_question": "最近 30 天销售额最高的 5 个商品是什么？",
        "question_input": "最近 30 天销售额最高的 5 个商品是什么？",
        "last_result": {"generated_sql": "SELECT old_sql"},
    }

    sync_selected_question(session_state, "每个城市的总销售额是多少？")

    assert session_state["selected_question"] == "每个城市的总销售额是多少？"
    assert session_state["question_input"] == "每个城市的总销售额是多少？"
    assert "last_result" not in session_state


def test_sync_selected_question_preserves_manual_input_when_selection_unchanged():
    from app import sync_selected_question

    session_state = {
        "selected_question": "最近 30 天销售额最高的 5 个商品是什么？",
        "question_input": "我手动编辑的问题",
        "last_result": {"generated_sql": "SELECT current_sql"},
    }

    sync_selected_question(session_state, "最近 30 天销售额最高的 5 个商品是什么？")

    assert session_state["question_input"] == "我手动编辑的问题"
    assert session_state["last_result"]["generated_sql"] == "SELECT current_sql"


def test_run_demo_question_executes_workflow_and_returns_trace(tmp_path):
    from app import run_demo_question

    result = run_demo_question(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_app_success",
        session_id="session_app_success",
    )

    assert result["status"] == "completed"
    assert result["generated_sql"].lower().startswith("select")
    assert result["execution_result"]["success"] is True
    assert result["final_answer"]
    assert Path(result["trace_path"]).is_file()


def test_run_demo_question_can_show_dangerous_sql_block(tmp_path):
    from app import run_demo_question

    result = run_demo_question(
        "删除所有取消订单的数据。",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_app_block",
        session_id="session_app_block",
        initial_sql="DELETE FROM orders WHERE status = 'cancelled'",
    )

    assert result["status"] == "failed"
    assert result["review_result"]["approved"] is False
    assert result["execution_result"] == {}
    assert "SQL 审核未通过" in result["final_answer"]


def test_format_agent_steps_extracts_trace_for_glass_box_view(tmp_path):
    from app import format_agent_steps, run_demo_question

    result = run_demo_question(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_app_steps",
        session_id="session_app_steps",
    )
    steps = format_agent_steps(result)

    assert steps
    assert {"node", "tool_name", "status", "latency_ms"} <= set(steps[0])
    assert "sql_generator_agent" in [step["node"] for step in steps]
    assert "sql_executor_node" in [step["node"] for step in steps]


def test_load_trace_file_reads_saved_trace_json(tmp_path):
    from app import load_trace_file, run_demo_question

    result = run_demo_question(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_app_trace",
        session_id="session_app_trace",
    )

    trace_payload = load_trace_file(result["trace_path"])

    assert trace_payload["run_id"] == "run_app_trace"
    assert trace_payload["status"] == "completed"
    assert trace_payload["trace"]


def test_load_trace_file_returns_structured_error_for_missing_file(tmp_path):
    from app import load_trace_file

    result = load_trace_file(tmp_path / "missing.json")

    assert result["success"] is False
    assert "Trace file not found" in result["error"]
