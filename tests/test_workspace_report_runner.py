import json
import sqlite3
from pathlib import Path

import pytest
import yaml

from workspaces.report_runner import REPORT_TYPE_PRESETS, _section_question, run_workspace_report
from workspaces.store import WorkspaceStore


def _create_workspace_with_orders(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Report Runner Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE orders (order_date TEXT, channel TEXT, revenue REAL)"
        )
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?)",
            [
                ("2026-01-01", "email", 100.0),
                ("2026-01-02", "paid_search", 200.0),
                ("2026-01-03", "organic", 150.0),
            ],
        )
    return store, workspace


def _fake_section_runner(calls):
    def runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        workspace = store.get_workspace(workspace_id)
        call_index = len(calls) + 1
        run_dir = Path(workspace["root_path"]) / "runs" / f"fake_run_{call_index}"
        run_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = run_dir / f"chart_{call_index}.png"
        artifact_path.write_bytes(b"fake-png")
        calls.append(
            {
                "workspace_id": workspace_id,
                "user_question": user_question,
                "initial_sql": initial_sql,
                "providers": providers,
                "artifact_path": str(artifact_path),
            }
        )
        return {
            "status": "completed",
            "final_answer": f"Section answer {call_index} with business recommendation.",
            "generated_sql": (
                "SELECT channel, SUM(revenue) AS revenue "
                "FROM orders GROUP BY channel LIMIT 20"
            ),
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["paid_search", 200.0], ["organic", 150.0]],
                "row_count": 2,
            },
            "evidence_result": {
                "data_supported_findings": [
                    {"claim": "paid_search has the highest revenue."}
                ],
                "hypotheses": [{"claim": "organic may be worth deeper review."}],
            },
            "visualization_trace": {
                "artifact_path": str(artifact_path),
                "provider_called": False,
            },
            "provider_metadata": {"fake": {"call_index": call_index}},
            "trace": [
                {"node": "question_understanding_agent"},
                {"node": "sql_reviewer_agent"},
                {"node": "sql_executor_node"},
                {"node": "visualization_agent"},
            ],
            "trace_path": str(run_dir / "trace.json"),
            "workspace_run_dir": str(run_dir),
        }

    return runner


def test_business_review_generates_multiple_sections_and_persists_report_artifacts(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = []

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成一份经营复盘报告，关注收入、渠道、趋势和建议。",
        providers={"question_understanding": object()},
        section_runner=_fake_section_runner(calls),
    )

    report = result["report"]
    report_dir = Path(workspace["root_path"]) / "reports" / report["report_id"]
    artifact_dir = report_dir / "artifacts"

    assert result["success"] is True
    assert report["status"] == "completed"
    assert len(report["sections"]) >= 3
    assert len(calls) == len(report["sections"])
    assert all(call["providers"] for call in calls)
    assert all("SELECT" not in call["user_question"].upper() for call in calls)
    assert (report_dir / "report.json").is_file()
    assert (report_dir / "report.md").is_file()
    assert (report_dir / "trace.json").is_file()
    assert artifact_dir.is_dir()

    saved = json.loads((report_dir / "report.json").read_text(encoding="utf-8"))
    markdown = (report_dir / "report.md").read_text(encoding="utf-8")
    assert saved["sections"][0]["summary"] == "Section answer 1 with business recommendation."
    assert "SELECT channel" not in saved["sections"][0]["summary"]
    assert "provider_called" not in saved["sections"][0]["summary"]
    assert "question_understanding_agent" not in saved["sections"][0]["summary"]
    assert saved["sections"][0]["columns"] == ["channel", "revenue"]
    assert saved["sections"][0]["rows_preview"][0] == {
        "channel": "paid_search",
        "revenue": 200.0,
    }
    assert saved["sections"][0]["trace_nodes"] == [
        "question_understanding_agent",
        "sql_reviewer_agent",
        "sql_executor_node",
        "visualization_agent",
    ]
    technical_details = saved["sections"][0]["technical_details"]
    assert technical_details["internal_question"].startswith("这是自动报告内部 section")
    assert technical_details["purpose"] == "Summarize recent revenue scale and channel mix using the current workspace data."
    assert technical_details["sql"].startswith("SELECT channel")
    assert technical_details["rows_preview"][0] == {
        "channel": "paid_search",
        "revenue": 200.0,
    }
    assert technical_details["provider_metadata"]["fake"]["call_index"] == 1
    assert technical_details["trace_nodes"] == [
        "question_understanding_agent",
        "sql_reviewer_agent",
        "sql_executor_node",
        "visualization_agent",
    ]
    for section in saved["sections"]:
        assert section["artifact_paths"]
        for artifact_path in section["artifact_paths"]:
            assert artifact_path.startswith("artifacts/")
            assert (report_dir / artifact_path).is_file()
            assert Path(artifact_path).is_relative_to("artifacts")
            assert "runs/fake_run" not in artifact_path
            assert artifact_path in markdown

    trace = json.loads((report_dir / "trace.json").read_text(encoding="utf-8"))
    assert trace["report_id"] == report["report_id"]
    assert any(event["event"] == "section_completed" for event in trace["events"])


def test_business_review_section_questions_are_specific_internal_analysis_prompts():
    report_goal = "基于最近 90 天的订单、客户和营销数据，生成面向管理层的收入复盘报告。"
    sections = {
        section["section_id"]: section
        for section in REPORT_TYPE_PRESETS["business_review"]["sections"]
    }

    channel_question = _section_question(
        report_goal=report_goal,
        report_type="business_review",
        section_plan=sections["top_channels_or_products"],
    )
    overall_question = _section_question(
        report_goal=report_goal,
        report_type="business_review",
        section_plan=sections["overall_revenue"],
    )
    trend_question = _section_question(
        report_goal=report_goal,
        report_type="business_review",
        section_plan=sections["trend_or_recent_change"],
    )

    assert "报告内部 section" in channel_question
    assert "不要请求用户补充" in channel_question
    assert "渠道" in channel_question
    assert "channel" in channel_question
    assert "收入" in channel_question
    assert "产品或其他" not in channel_question
    assert "只使用订单、渠道、收入、日期等聚合字段" in overall_question
    assert "非个人级聚合" in overall_question
    assert "不访问个人身份字段" in overall_question
    assert "customer_id" not in overall_question
    assert "客户数" not in overall_question
    assert "order_date" in trend_question
    assert "最近 90 天" in trend_question
    assert "按月" in trend_question or "按周" in trend_question
    assert "不要请求用户补充" in trend_question


def test_existing_semantic_layer_is_not_overwritten(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    existing_semantic = {
        "workspace_id": workspace["workspace_id"],
        "metrics": [{"name": "reviewed_revenue", "formula": "SUM(orders.revenue)"}],
        "dimensions": [],
        "time_fields": [],
        "entities": [],
        "join_paths": [],
    }
    Path(workspace["semantic_layer_path"]).write_text(
        yaml.safe_dump(existing_semantic, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "分析收入趋势。",
        section_runner=_fake_section_runner([]),
    )

    loaded = yaml.safe_load(
        Path(workspace["semantic_layer_path"]).read_text(encoding="utf-8")
    )
    assert loaded["metrics"][0]["name"] == "reviewed_revenue"


def test_provider_unavailable_section_is_retried_before_marking_failed(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = []

    def retryable_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        calls.append(user_question)
        if len(calls) == 1:
            return {
                "status": "waiting_for_clarification",
                "final_answer": (
                    "需要补充信息后才能继续分析：Provider question understanding is unavailable; "
                    "please retry with a configured provider."
                ),
                "execution_result": {},
                "question_understanding": {
                    "provider_called": True,
                    "source": "provider_unavailable",
                    "strategy": "clarify",
                    "missing_slots": ["provider_output"],
                    "fallback_used": True,
                },
                "trace": [
                    {"node": "question_understanding_agent"},
                    {"node": "clarification_router_agent"},
                    {"node": "early_response_node"},
                ],
            }
        return _fake_section_runner([])(
            store, workspace_id, user_question, initial_sql, providers
        )

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "分析最近 90 天收入趋势。",
        section_runner=retryable_runner,
    )

    assert result["success"] is True
    assert result["report"]["status"] == "completed"
    assert len(calls) == len(result["report"]["sections"]) + 1
    assert result["report"]["sections"][0]["status"] == "completed"
    assert "early_response_node" not in result["report"]["sections"][0]["trace_nodes"]


def test_provider_unavailable_section_can_retry_twice_before_success(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = []

    def retryable_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        calls.append(user_question)
        if len(calls) <= 2:
            return {
                "status": "waiting_for_clarification",
                "final_answer": (
                    "需要补充信息后才能继续分析：Provider question understanding is unavailable; "
                    "please retry with a configured provider."
                ),
                "execution_result": {},
                "question_understanding": {
                    "provider_called": True,
                    "source": "provider_unavailable",
                    "strategy": "clarify",
                    "missing_slots": ["provider_output"],
                    "fallback_used": True,
                    "validation_error": "question_understanding schema validation failed",
                },
                "trace": [
                    {"node": "question_understanding_agent"},
                    {"node": "clarification_router_agent"},
                    {"node": "early_response_node"},
                ],
            }
        return _fake_section_runner([])(
            store, workspace_id, user_question, initial_sql, providers
        )

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "分析最近 90 天收入趋势。",
        section_runner=retryable_runner,
    )

    assert result["success"] is True
    assert result["report"]["status"] == "completed"
    assert len(calls) == len(result["report"]["sections"]) + 2
    assert result["report"]["sections"][0]["status"] == "completed"


def test_safety_reject_section_is_not_retried_into_completed(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = []

    def rejecting_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        calls.append(user_question)
        return {
            "status": "failed",
            "final_answer": "请求包含敏感字段或不安全操作，已在 SQL 生成前拒绝。",
            "execution_result": {},
            "question_understanding": {
                "provider_called": True,
                "source": "provider",
                "strategy": "reject",
                "risk_flags": ["sensitive_field"],
                "rejection_reason": "Request asks for sensitive fields or unsafe data access.",
                "fallback_used": False,
            },
            "trace": [
                {"node": "question_understanding_agent"},
                {"node": "early_response_node"},
            ],
        }

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "分析最近 90 天收入趋势。",
        section_runner=rejecting_runner,
    )

    assert result["success"] is False
    assert result["report"]["status"] == "failed"
    assert len(calls) == len(result["report"]["sections"])
    assert all(section["status"] == "failed" for section in result["report"]["sections"])


def test_one_section_failure_marks_report_partial(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = []

    def flaky_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        if len(calls) == 1:
            calls.append(user_question)
            raise RuntimeError("section analysis failed")
        calls.append(user_question)
        return _fake_section_runner([])(
            store, workspace_id, user_question, initial_sql, providers
        )

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "channel_performance",
        "比较渠道表现。",
        section_runner=flaky_runner,
    )

    statuses = [section["status"] for section in result["report"]["sections"]]
    assert result["report"]["status"] == "partial"
    assert "completed" in statuses
    assert "failed" in statuses
    assert Path(result["report"]["json_path"]).is_file()
    assert Path(result["report"]["markdown_path"]).is_file()


def test_all_section_failures_mark_report_failed(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    def failing_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        raise RuntimeError("provider unavailable")

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "分析收入趋势。",
        section_runner=failing_runner,
    )

    assert result["success"] is False
    assert result["report"]["status"] == "failed"
    assert all(section["status"] == "failed" for section in result["report"]["sections"])
    assert all(section["error"] == "provider unavailable" for section in result["report"]["sections"])
    assert Path(result["report"]["json_path"]).is_file()
    assert Path(result["report"]["markdown_path"]).is_file()


def test_unsupported_report_type_raises_clear_error(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    with pytest.raises(ValueError, match="Unsupported report_type: unknown_report"):
        run_workspace_report(
            store,
            workspace["workspace_id"],
            "unknown_report",
            "生成报告。",
            section_runner=_fake_section_runner([]),
        )


def test_missing_report_goal_raises_clear_error(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    with pytest.raises(ValueError, match="report_goal is required"):
        run_workspace_report(
            store,
            workspace["workspace_id"],
            "business_review",
            "   ",
            section_runner=_fake_section_runner([]),
        )
