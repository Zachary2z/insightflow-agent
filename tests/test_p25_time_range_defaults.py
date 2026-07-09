import json
import sqlite3

from workspaces.analysis_runner import run_workspace_analysis
from workspaces.profiler import profile_workspace_database
from workspaces.report_runner import run_workspace_report
from workspaces.report_planner import plan_workspace_report
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


def _prepare_single_time_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P25 Full Range Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            """
            CREATE TABLE business_sales (
                sale_date TEXT,
                customer_segment TEXT,
                product_category TEXT,
                channel TEXT,
                revenue REAL,
                quantity INTEGER
            )
            """
        )
        conn.executemany(
            "INSERT INTO business_sales VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("2025-01-15", "企业客户", "咖啡豆", "私域", 180000.0, 120),
                ("2025-08-20", "成长客户", "挂耳咖啡", "小红书", 90000.0, 300),
                ("2026-06-30", "企业客户", "咖啡豆", "私域", 220000.0, 150),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace, profile, semantic_layer


def _prepare_multi_time_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P25 Ambiguous Time Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            """
            CREATE TABLE business_sales (
                order_date TEXT,
                paid_at TEXT,
                customer_segment TEXT,
                revenue REAL
            )
            """
        )
        conn.executemany(
            "INSERT INTO business_sales VALUES (?, ?, ?, ?)",
            [
                ("2025-01-15", "2025-01-18", "企业客户", 180000.0),
                ("2026-06-28", "2026-06-30", "成长客户", 90000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace, profile, semantic_layer


def _answer_text(result):
    answer = result["product_result"]["business_answer"]
    return " ".join(
        [
            answer["headline"],
            answer["direct_answer"],
            answer["why"],
            *answer["evidence_bullets"],
            *answer["recommendations"],
            *answer["caveats"],
        ]
    )


def test_analysis_defaults_missing_time_range_to_full_data_range_when_single_time_field(tmp_path):
    store, workspace, _profile, _semantic_layer = _prepare_single_time_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="哪个客户分群贡献的收入最高？",
    )

    task = result["question_understanding"]["analysis_task"]
    fact_payload = result["product_result"]["evidence"]["fact_payload"]
    ledger_text = json.dumps(result["product_result"]["question_evidence_ledger"], ensure_ascii=False)

    assert result["status"] == "completed"
    assert task["missing_slots"] == []
    assert task["time_range"]["type"] == "full_data_range"
    assert task["time_range"]["start"] == "2025-01-15"
    assert task["time_range"]["end"] == "2026-06-30"
    assert "用户未指定时间范围" in " ".join(task["defaults_applied"])
    assert "完整可用时间范围" in task["resolved_question"]
    assert fact_payload["time_range"]["raw_text"] == "完整数据时间范围：2025-01-15 至 2026-06-30"
    assert "完整数据时间范围" in ledger_text or "完整数据时间范围" in fact_payload["time_range"]["raw_text"]
    assert "2025-01-15 至 2026-06-30" in fact_payload["time_range"]["raw_text"]


def test_analysis_defaults_missing_time_range_when_business_lens_can_bind_metric_time_field(tmp_path):
    store, workspace, _profile, _semantic_layer = _prepare_multi_time_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="哪个客户分群贡献的收入最高？",
    )

    task = result["analysis_task"]
    understanding = result["question_understanding"]

    assert result["status"] == "completed"
    assert "date_field" not in understanding["missing_slots"]
    assert task["time_range"]["field"] == "business_sales.order_date"
    assert "用户未指定时间范围" in task["time_range"]["reason"]
    assert "完整数据时间范围" in task["time_range"]["raw_text"]
    assert "销售额按order_date统计" in task["business_lens"]["time_policy_note"]
    assert "完整数据时间范围" in result["technical_details"]["fact_payload"]["time_range"]["raw_text"]


def test_analysis_asks_for_trend_grain_even_when_single_full_range_is_available(tmp_path):
    store, workspace, _profile, _semantic_layer = _prepare_single_time_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="收入趋势怎么样？",
    )

    understanding = result["question_understanding"]
    question_text = " ".join(result.get("clarification_questions") or [])

    assert result["status"] == "waiting_for_clarification"
    assert "time_grain" in understanding["missing_slots"]
    assert "按天、周还是月" in question_text
    assert "完整数据范围" in question_text


def test_report_without_time_range_defaults_to_full_data_range_and_not_recent_90_days(tmp_path):
    store, workspace, profile, semantic_layer = _prepare_single_time_workspace(tmp_path)

    plan = plan_workspace_report(
        report_type="channel_performance",
        report_goal="生成渠道表现复盘报告",
        profile=profile,
        semantic_layer=semantic_layer,
    )
    result = run_workspace_report(
        store=store,
        workspace_id=workspace["workspace_id"],
        report_type="channel_performance",
        report_goal="生成渠道表现复盘报告",
    )
    report = result["report"]
    report_text = json.dumps(
        {
            "title": report["title"],
            "plan": report["plan"],
            "document": report["document"],
            "evidence_payloads": report["evidence_pack"]["evidence_payloads"],
        },
        ensure_ascii=False,
    )

    assert "最近90天" not in plan.title
    assert "最近90天" not in report_text
    assert plan.time_range == "完整数据时间范围：2025-01-15 至 2026-06-30"
    assert report["plan"]["time_range"] == "完整数据时间范围：2025-01-15 至 2026-06-30"
    assert report["document"]["time_range"] == "完整数据时间范围：2025-01-15 至 2026-06-30"
    assert "你没有指定时间范围" in report_text
    assert "2025-01-15 至 2026-06-30" in report_text


def test_report_explicit_recent_90_days_is_not_overridden_by_full_data_range(tmp_path):
    _store, _workspace, profile, semantic_layer = _prepare_single_time_workspace(tmp_path)

    plan = plan_workspace_report(
        report_type="channel_performance",
        report_goal="生成最近90天渠道表现复盘报告",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    assert plan.time_range == "最近90天"
    assert plan.title == "最近90天渠道表现复盘报告"


def test_report_explicit_recent_7_days_is_not_overridden_by_full_data_range(tmp_path):
    _store, _workspace, profile, semantic_layer = _prepare_single_time_workspace(tmp_path)

    plan = plan_workspace_report(
        report_type="channel_performance",
        report_goal="生成最近7天渠道表现复盘报告",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    assert plan.time_range == "最近7天"
    assert plan.title == "最近7天渠道表现复盘报告"


def test_report_explicit_recent_180_days_is_not_overridden_by_full_data_range(tmp_path):
    _store, _workspace, profile, semantic_layer = _prepare_single_time_workspace(tmp_path)

    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近180天经营复盘报告",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    assert plan.time_range == "最近180天"
    assert plan.title == "最近180天经营复盘报告"


def test_report_explicit_recent_6_months_is_not_overridden_by_full_data_range(tmp_path):
    _store, _workspace, profile, semantic_layer = _prepare_single_time_workspace(tmp_path)

    plan = plan_workspace_report(
        report_type="revenue_trend",
        report_goal="生成最近6个月收入趋势报告",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    assert plan.time_range == "最近6个月"
    assert plan.title == "最近6个月趋势变化报告"


def test_report_explicit_this_quarter_is_not_overridden_by_full_data_range(tmp_path):
    _store, _workspace, profile, semantic_layer = _prepare_single_time_workspace(tmp_path)

    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成本季度经营复盘报告",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    assert plan.time_range == "本季度"
    assert plan.title == "本季度经营复盘报告"


def test_analysis_explicit_time_range_still_asks_for_missing_trend_grain(tmp_path):
    store, workspace, _profile, _semantic_layer = _prepare_single_time_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天收入趋势怎么样？",
    )

    understanding = result["question_understanding"]
    question_text = " ".join(result.get("clarification_questions") or [])

    assert result["status"] == "waiting_for_clarification"
    assert "time_grain" in understanding["missing_slots"]
    assert "按天、周还是月" in question_text


def test_analysis_explicit_time_range_with_weekly_grain_does_not_ask_for_time_grain(tmp_path):
    store, workspace, _profile, _semantic_layer = _prepare_single_time_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天按周看收入趋势怎么样？",
    )

    understanding = result["question_understanding"]

    assert "time_grain" not in understanding["missing_slots"]
    assert result["status"] != "waiting_for_clarification"


def test_report_missing_time_range_with_multiple_time_fields_requires_clarification(tmp_path):
    store, workspace, profile, semantic_layer = _prepare_multi_time_workspace(tmp_path)

    plan = plan_workspace_report(
        report_type="channel_performance",
        report_goal="生成渠道表现复盘报告",
        profile=profile,
        semantic_layer=semantic_layer,
    )
    result = run_workspace_report(
        store=store,
        workspace_id=workspace["workspace_id"],
        report_type="channel_performance",
        report_goal="生成渠道表现复盘报告",
    )
    report = result["report"]
    report_text = json.dumps(report, ensure_ascii=False)

    assert plan.time_range == ""
    assert "date_field" in plan.missing_slots
    assert result["success"] is False
    assert report["status"] in {"failed", "partial"}
    assert "多个可能的时间字段" in report_text
    assert "order_date" in report_text
    assert "paid_at" in report_text
    assert "完整数据时间范围" not in report_text
    assert "当前工作区全部可用数据" not in report_text
