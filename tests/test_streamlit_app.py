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
    assert "Evidence-backed Report" in labels
    assert "Weekly Business Review" in labels
    assert "Approval-gated Action Workflow" in labels
    assert "MCP Tool Layer" in labels
    assert "FastAPI Async Run API" in labels
    assert "Trace Dashboard" in labels
    assert "LLM Provider & PromptOps" in labels
    assert "Template Mining & Eval" in labels
    assert {"P0", "P1", "P2", "P3"} <= {item["phase"] for item in overview}
    assert all(item["status"] in {"available", "local-api", "provider-optional"} for item in overview)
    assert all(item["entrypoint"] for item in overview)
    assert all(item["safety_boundary"] for item in overview)


def test_source_view_model_extracts_provider_and_prompt_metadata():
    from ui.view_models import build_source_cards

    state = {
        "question_understanding": {
            "source": "provider",
            "provider_called": True,
            "fallback_used": False,
            "prompt_id": "question_understanding",
            "validation_error": "",
            "provider_error": "",
        },
        "sql_planning": {
            "source": "deterministic",
            "provider_called": True,
            "fallback_used": True,
            "prompt_id": "sql_planning_router",
            "validation_error": "strategy must be one of allowed values",
            "provider_error": "",
        },
        "llm_sql_enhancement": {
            "source": "deterministic",
            "provider_called": True,
            "fallback_used": True,
            "prompt_id": "guarded_sql_candidate",
            "validation_error": "",
            "provider_error": "provider timeout",
        },
    }

    cards = build_source_cards(state)

    by_module = {card["module"]: card for card in cards}
    assert by_module["Question Understanding"]["provider_called"] is True
    assert by_module["Question Understanding"]["fallback_used"] is False
    assert by_module["Question Understanding"]["prompt_id"] == "question_understanding"
    assert by_module["SQL Planning Router"]["validation_error"] == "strategy must be one of allowed values"
    assert by_module["Guarded SQL Candidate"]["provider_error"] == "provider timeout"


def test_trace_timeline_view_model_preserves_glass_box_fields():
    from ui.view_models import build_trace_timeline

    state = {
        "trace": [
            {
                "node": "question_understanding_agent",
                "tool_name": "provider_backed_question_understanding",
                "status": "success",
                "latency_ms": 17,
                "retry_count": 1,
                "provider_called": True,
                "fallback_used": False,
                "error_type": "",
            },
            {
                "node": "sql_executor_node",
                "tool_name": "run_sql",
                "status": "error",
                "latency_ms": 9,
                "retry_count": 0,
                "provider_called": False,
                "fallback_used": False,
                "error_type": "sqlite_error",
            },
        ]
    }

    timeline = build_trace_timeline(state)

    assert timeline == [
        {
            "node": "question_understanding_agent",
            "tool_name": "provider_backed_question_understanding",
            "status": "success",
            "latency_ms": 17,
            "retry_count": 1,
            "provider_called": True,
            "fallback_used": False,
            "error_type": "",
            "error": "",
        },
        {
            "node": "sql_executor_node",
            "tool_name": "run_sql",
            "status": "error",
            "latency_ms": 9,
            "retry_count": 0,
            "provider_called": False,
            "fallback_used": False,
            "error_type": "sqlite_error",
            "error": "",
        },
    ]


def test_run_detail_view_model_exposes_cleaned_agent_pipeline_tool_gates_and_artifacts():
    from ui.view_models import build_run_detail_view_model

    state = {
        "status": "completed",
        "user_question": "最近 30 天销售额最高的 5 个商品是什么？",
        "generated_sql": "SELECT product_name, gmv FROM product_sales",
        "review_result": {"approved": True, "reason": "safe select"},
        "execution_result": {
            "success": True,
            "columns": ["product_name", "gmv"],
            "rows": [["Laptop", 1000.0]],
            "row_count": 1,
        },
        "evidence_result": {"success": True, "unsupported_claim_rate": 0.0},
        "visualization_decision": {
            "provider_called": True,
            "fallback_used": False,
            "prompt_id": "visualization_decision",
            "validation_error": "",
            "delivery_tool_id": "powerbi_publisher_mock",
        },
        "visualization_delivery_result": {
            "success": True,
            "delivery_tool_id": "powerbi_publisher_mock",
            "tool_type": "mock_external_bi",
            "external_tool_called": True,
            "artifact_url": "mock://powerbi/run_1/chart",
            "policy_result": {"success": True, "validation_error": ""},
        },
        "action_plan": {"success": True, "source": "provider", "actions": []},
        "risk_assessment": {"requires_approval": True, "actions": []},
        "approval_status": "approved",
        "action_execution_result": {
            "success": True,
            "external_tool_called": True,
            "delivery_results": [
                {
                    "success": True,
                    "delivery_tool_id": "jira_ticket_mock",
                    "tool_type": "mock_external_ticketing",
                    "external_tool_called": True,
                    "artifact_url": "mock://jira/run_1/ticket",
                    "policy_result": {"success": True, "validation_error": ""},
                }
            ],
        },
        "audit_log_id": "audit_1",
        "report_path": "reports/markdown/report.md",
        "trace_path": "logs/traces/run_1.json",
        "trace": [
            {
                "node": "question_understanding_agent",
                "tool_name": "provider_backed_question_understanding",
                "status": "success",
                "provider_called": True,
                "fallback_used": False,
                "prompt_id": "question_understanding",
            },
            {
                "node": "sql_reviewer_agent",
                "tool_name": "validate_sql",
                "status": "success",
            },
            {
                "node": "visualization_agent",
                "tool_name": "external_visualization_tool",
                "status": "success",
                "external_tool_called": True,
            },
            {
                "node": "approval_gate",
                "tool_name": "log_audit_event",
                "status": "success",
            },
        ],
    }

    view = build_run_detail_view_model(state)

    assert view["agent_pipeline"][0]["agent"] == "question_understanding_agent"
    assert view["agent_pipeline"][0]["prompt_id"] == "question_understanding"
    assert any(card["tool_name"] == "validate_sql" for card in view["tool_call_cards"])
    assert any(card["delivery_tool_id"] == "powerbi_publisher_mock" for card in view["tool_call_cards"])
    assert any(card["delivery_tool_id"] == "jira_ticket_mock" for card in view["tool_call_cards"])
    gates = {gate["gate"]: gate for gate in view["validator_gates"]}
    assert gates["SQL Validator"]["status"] == "passed"
    assert gates["Evidence Validator"]["status"] == "passed"
    assert gates["Tool Policy"]["status"] == "passed"
    assert gates["Approval Gate"]["status"] == "approved"
    artifacts = {artifact["artifact_type"]: artifact for artifact in view["artifact_panel"]}
    assert artifacts["report"]["location"] == "reports/markdown/report.md"
    assert artifacts["trace"]["location"] == "logs/traces/run_1.json"
    assert artifacts["mock_external_bi"]["location"] == "mock://powerbi/run_1/chart"
    assert artifacts["audit"]["location"] == "audit_1"


def test_no_key_llm_ops_status_shows_deterministic_not_configured():
    from ui.view_models import build_llm_ops_summary

    summary = build_llm_ops_summary(env={})

    assert summary["provider"]["name"] == "DeepSeek"
    assert summary["provider"]["configured"] is False
    assert summary["provider"]["status"] == "deterministic / not configured"
    assert summary["deterministic_baseline"]["available"] is True


def test_llm_ops_summary_does_not_leak_api_key():
    from ui.view_models import build_llm_ops_summary

    summary = build_llm_ops_summary(env={"DEEPSEEK_API_KEY": "super-secret-token"})
    payload = json.dumps(summary, ensure_ascii=False)

    assert "super-secret-token" not in payload
    assert summary["provider"]["configured"] is True


def test_command_center_analysis_helper_reuses_workflow_helper(monkeypatch):
    import app

    calls = []

    def fake_run_demo_question(question, **kwargs):
        calls.append({"question": question, **kwargs})
        return {"status": "completed", "final_answer": "ok", "trace": []}

    monkeypatch.setattr(app, "run_demo_question", fake_run_demo_question)

    result = app.run_command_center_analysis(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path="demo.db",
        trace_dir="demo-traces",
        initial_sql=None,
    )

    assert result["status"] == "completed"
    assert calls == [
        {
            "question": "最近 30 天销售额最高的 5 个商品是什么？",
            "db_path": "demo.db",
            "trace_dir": "demo-traces",
            "initial_sql": None,
        }
    ]


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
