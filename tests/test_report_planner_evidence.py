import json
import sqlite3
from pathlib import Path

from workspaces.profiler import profile_workspace_database
from workspaces.report_markdown import render_report_markdown
from workspaces.report_models import ReportDocument, ReportRecord, ReportValidationResult
from workspaces.report_evidence import collect_report_evidence
from workspaces.report_planner import plan_workspace_report
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


def _prepare_business_workspace(tmp_path: Path, *, include_support: bool = True):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Report Evidence Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            """
            CREATE TABLE orders (
                order_date TEXT,
                product_category TEXT,
                customer_segment TEXT,
                revenue REAL,
                order_count INTEGER
            )
            """
        )
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
            [
                ("2026-04-01", "企业SaaS订阅", "成长型团队", 120000.0, 12),
                ("2026-05-01", "数据分析服务", "高价值企业", 86000.0, 8),
                ("2026-06-01", "企业SaaS订阅", "高价值企业", 148000.0, 11),
                ("2026-06-15", "运营代投服务", "成长型团队", 76000.0, 6),
            ],
        )
        if include_support:
            conn.execute(
                """
                CREATE TABLE support_tickets (
                    ticket_date TEXT,
                    issue_type TEXT,
                    ticket_count INTEGER,
                    satisfaction_score REAL,
                    avg_response_minutes REAL
                )
                """
            )
            conn.executemany(
                "INSERT INTO support_tickets VALUES (?, ?, ?, ?, ?)",
                [
                    ("2026-06-01", "交付延期", 42, 4.1, 38.0),
                    ("2026-06-08", "退款投诉", 28, 3.8, 52.0),
                    ("2026-06-15", "使用咨询", 66, 4.7, 16.0),
                ],
            )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace, profile, semantic_layer


def _prepare_workspace_with_old_revenue(tmp_path: Path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Report Time Scope Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            """
            CREATE TABLE orders (
                order_date TEXT,
                product_category TEXT,
                customer_segment TEXT,
                revenue REAL,
                order_count INTEGER
            )
            """
        )
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
            [
                ("2025-12-01", "旧品类", "旧客群", 999000.0, 99),
                ("2026-03-10", "临界外品类", "旧客群", 300000.0, 30),
                ("2026-05-20", "企业SaaS订阅", "成长型团队", 120000.0, 12),
                ("2026-06-15", "数据分析服务", "高价值企业", 80000.0, 8),
                ("2026-06-30", "企业SaaS订阅", "成长型团队", 50000.0, 5),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace, profile, semantic_layer


def _prepare_workspace_without_time_field(tmp_path: Path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Report No Time Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            """
            CREATE TABLE orders (
                product_category TEXT,
                customer_segment TEXT,
                revenue REAL,
                order_count INTEGER
            )
            """
        )
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            [
                ("企业SaaS订阅", "成长型团队", 120000.0, 12),
                ("旧品类", "旧客群", 999000.0, 99),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace, profile, semantic_layer


def test_chinese_report_planner_generates_goal_driven_chapters(tmp_path):
    _store, _workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path)

    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="帮我生成一份经营复盘报告，包含收入结构、客户分群、客服问题和行动建议。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    titles = [chapter.title for chapter in plan.chapters]
    assert plan.title == "最近90天经营复盘报告"
    assert plan.report_style == "经营复盘"
    assert "经营概览" in titles
    assert "收入结构" in titles
    assert "客户分群" in titles
    assert "客服问题" in titles
    assert "行动建议" in titles
    assert all(any("\u4e00" <= char <= "\u9fff" for char in title) for title in titles)
    assert any(req.description.startswith("按收入") for chapter in plan.chapters for req in chapter.evidence_requirements)


def test_report_planner_title_matches_channel_performance_goal(tmp_path):
    _store, _workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path)

    plan = plan_workspace_report(
        report_type="channel_performance",
        report_goal="生成一份最近90天渠道表现复盘报告，包含收入、订单、投放成本、ROI 和建议。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    assert plan.title == "最近90天渠道表现复盘报告"
    assert plan.report_goal == "生成一份最近90天渠道表现复盘报告，包含收入、订单、投放成本、ROI 和建议。"
    assert plan.report_style == "渠道表现复盘"
    assert plan.time_range == "最近90天"
    assert "Business Review" not in plan.title
    assert "管理层摘要" not in plan.title
    assert "Revenue Overview" not in plan.title


def test_report_evidence_records_requested_cost_and_roi_data_limits(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path)
    plan = plan_workspace_report(
        report_type="channel_performance",
        report_goal="生成一份最近90天渠道表现复盘报告，包含收入、订单、投放成本、ROI 和建议。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )

    limits = "\n".join(evidence_pack.data_limits)
    assert "投放成本" in limits
    assert "ROI" in limits
    assert "当前工作区" in limits


def test_report_planner_keeps_requested_unsupported_chapter_with_missing_requirement(tmp_path):
    _store, _workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path, include_support=False)

    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成经营复盘报告，重点看客服问题和行动建议。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    support = next(chapter for chapter in plan.chapters if chapter.chapter_id == "support_issues")
    descriptions = " ".join(req.description for req in support.evidence_requirements)
    assert support.title == "客服问题"
    assert "当前工作区暂未识别到客服" in descriptions
    assert "缺失" in descriptions


def test_evidence_collector_builds_business_readable_pack_from_orders_and_support(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成经营复盘报告，关注收入结构、客户分群、客服问题、趋势变化和行动建议。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )

    fact_text = json.dumps([fact.to_dict() for fact in evidence_pack.facts], ensure_ascii=False)
    table_titles = [table.title for table in evidence_pack.tables]
    assert "总收入" in fact_text
    assert "43.0 万" in fact_text
    assert "收入结构" in table_titles
    assert "客户分群贡献" in table_titles
    assert "客服问题概览" in table_titles
    assert "趋势变化" in table_titles
    assert all(any("\u4e00" <= char <= "\u9fff" for char in fact.label) for fact in evidence_pack.facts)
    assert all(any("\u4e00" <= char <= "\u9fff" for char in column) for table in evidence_pack.tables for column in table.columns)
    assert evidence_pack.technical_details["queries"]
    assert "SELECT" in json.dumps(evidence_pack.technical_details, ensure_ascii=False).upper()


def test_evidence_collector_generates_chart_artifacts_for_chartable_tables(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告，关注收入结构、客户分群和趋势变化。",
        profile=profile,
        semantic_layer=semantic_layer,
    )
    artifact_dir = Path(workspace["root_path"]) / "reports" / "report_chart_test" / "artifacts"

    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
        artifact_dir=artifact_dir,
        artifact_base_path="reports/report_chart_test/artifacts",
    )

    artifact_charts = [chart for chart in evidence_pack.charts if chart.path]
    assert artifact_charts
    assert all(chart.path.startswith("reports/report_chart_test/artifacts/") for chart in artifact_charts)
    assert all((Path(workspace["root_path"]) / chart.path).is_file() for chart in artifact_charts)
    assert any(chart.chart_id == "revenue_structure_chart" for chart in artifact_charts)
    assert "待生成图表" not in json.dumps([chart.to_dict() for chart in artifact_charts], ensure_ascii=False)


def test_report_evidence_pack_exposes_shared_payloads_for_non_channel_sales(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Store Sales Shared Evidence Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            """
            CREATE TABLE store_sales (
                sale_date TEXT,
                store_name TEXT,
                sales_amount REAL
            )
            """
        )
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [
                ("2026-06-01", "上海旗舰店", 300000.0),
                ("2026-06-02", "北京国贸店", 100000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告，关注销售额和门店贡献。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )

    shared_payloads = evidence_pack.evidence_payloads
    revenue_table = next(table for table in evidence_pack.tables if table.table_id == "revenue_by_dimension")
    payload = next(item for item in shared_payloads if item["evidence_ref"] == revenue_table.evidence_payload_ref)

    assert payload["evidence_pack_version"] == "p23.shared.v1"
    assert payload["dimensions"] == ["门店"]
    assert payload["metrics"] == ["销售额"]
    assert payload["time_range"] == {"raw_text": "最近90天"}
    assert payload["result_rows"][0]["dimensions"][0]["display_value"] == "上海旗舰店"
    assert payload["result_rows"][0]["metrics"][0]["display_value"] == "30.0 万"
    share = next(item for item in payload["derived_metrics"] if item["metric_id"].endswith("_share"))
    assert share["values"][0]["display_value"] == "75.0%"
    assert revenue_table.rows[0]["门店"] == "上海旗舰店"
    assert revenue_table.rows[0]["收入"] == "30.0 万"
    assert revenue_table.evidence_payload_ref


def test_report_evidence_payloads_do_not_embed_sql_or_raw_rows(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告，关注收入结构。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )

    payloads = evidence_pack.to_dict()["evidence_payloads"]
    serialized_payloads = json.dumps(payloads, ensure_ascii=False)

    assert payloads
    assert "SELECT" not in serialized_payloads.upper()
    assert "technical_sql" not in serialized_payloads
    assert "technical_details" not in serialized_payloads
    assert "raw_rows" not in serialized_payloads
    assert all("rows" not in payload for payload in payloads)
    assert all("rows" not in payload.get("chart_data", {}) for payload in payloads)
    assert "SELECT" in json.dumps(evidence_pack.technical_details["queries"], ensure_ascii=False).upper()


def test_evidence_collector_records_data_limit_when_support_data_missing(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path, include_support=False)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成经营复盘报告，包含客服问题。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )

    limits = "\n".join([*evidence_pack.warnings, *evidence_pack.data_limits])
    assert "客服" in limits
    assert "未识别" in limits or "缺少" in limits
    assert not any(table.source_chapter_id == "support_issues" for table in evidence_pack.tables)


def test_support_issue_evidence_counts_tickets_instead_of_summing_ticket_ids(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Chinese Support ID Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            """
            CREATE TABLE customer_support (
                ticket_id_工单编号 INTEGER,
                issue_type_问题类型 TEXT,
                satisfaction_score_满意度 REAL
            )
            """
        )
        conn.executemany(
            "INSERT INTO customer_support VALUES (?, ?, ?)",
            [
                (1001, "交付延期", 4.1),
                (1002, "交付延期", 3.9),
                (1003, "退款投诉", 3.2),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告，重点关注客服问题。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )

    support_table = next(table for table in evidence_pack.tables if table.table_id == "support_issue_summary")
    technical_sql = "\n".join(
        str(query.get("sql") or "")
        for query in evidence_pack.technical_details["queries"]
        if "support" in str(query.get("sql") or "").lower()
    )

    assert support_table.rows[0]["问题类型"] == "交付延期"
    assert support_table.rows[0]["工单量"] == "2"
    assert max(int(row["工单量"]) for row in support_table.rows) <= 3
    assert "COUNT(" in technical_sql.upper()
    assert "SUM(\"ticket_id_工单编号\")" not in technical_sql


def test_evidence_collector_filters_recent_90_days_from_table_max_date(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_workspace_with_old_revenue(tmp_path)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告，关注收入结构和客户分群。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )

    revenue_total = next(fact for fact in evidence_pack.facts if fact.fact_id == "revenue_total")
    revenue_table = next(table for table in evidence_pack.tables if table.title == "收入结构")
    customer_table = next(table for table in evidence_pack.tables if table.title == "客户分群贡献")
    technical_text = json.dumps(evidence_pack.technical_details, ensure_ascii=False)

    assert revenue_total.value == 250000.0
    assert revenue_total.display_value == "25.0 万"
    assert revenue_table.rows[0]["收入"] == "17.0 万"
    assert revenue_table.rows[0]["产品"] == "企业SaaS订阅"
    assert all("旧" not in json.dumps(row, ensure_ascii=False) for row in revenue_table.rows)
    assert all("旧" not in json.dumps(row, ensure_ascii=False) for row in customer_table.rows)
    assert "MAX(date" in technical_text
    assert "-90 days" in technical_text


def test_report_planner_title_matches_recent_30_days_and_current_month():
    profile = {"tables": []}
    semantic_layer = {}

    recent_30 = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近30天经营复盘报告。",
        profile=profile,
        semantic_layer=semantic_layer,
    )
    current_month = plan_workspace_report(
        report_type="revenue_trend",
        report_goal="生成本月趋势变化报告。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    assert recent_30.time_range == "最近30天"
    assert recent_30.title == "最近30天经营复盘报告"
    assert current_month.time_range == "本月"
    assert current_month.title == "本月趋势变化报告"


def test_evidence_collector_applies_supported_relative_time_ranges(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_workspace_with_old_revenue(tmp_path)
    cases = [
        ("生成最近30天经营复盘报告，关注收入结构。", "最近30天", 130000.0, "-30 days"),
        ("生成本月经营复盘报告，关注收入结构。", "本月", 130000.0, "strftime('%Y-%m'"),
        ("生成本周经营复盘报告，关注收入结构。", "本周", 50000.0, "-7 days"),
    ]

    for goal, expected_range, expected_total, sql_marker in cases:
        plan = plan_workspace_report(
            report_type="business_review",
            report_goal=goal,
            profile=profile,
            semantic_layer=semantic_layer,
        )
        evidence_pack = collect_report_evidence(
            plan=plan,
            profile=profile,
            semantic_layer=semantic_layer,
            analysis_db_path=workspace["analysis_db_path"],
        )
        revenue_total = next(fact for fact in evidence_pack.facts if fact.fact_id == "revenue_total")
        technical_text = json.dumps(evidence_pack.technical_details, ensure_ascii=False)

        assert plan.time_range == expected_range
        assert revenue_total.value == expected_total
        assert sql_marker in technical_text


def test_evidence_collector_records_data_limit_when_time_filter_cannot_apply(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_workspace_without_time_field(tmp_path)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近30天经营复盘报告，关注收入结构和客户分群。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )

    limits = "\n".join([*evidence_pack.warnings, *evidence_pack.data_limits])
    assert "最近30天" in limits
    assert "时间字段" in limits
    assert "未应用时间过滤" in limits


def test_report_markdown_main_body_hides_sql_query_ids_and_technical_details(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_workspace_with_old_revenue(tmp_path)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告，关注收入结构。",
        profile=profile,
        semantic_layer=semantic_layer,
    )
    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="本报告基于当前工作区证据生成。",
        sections=[],
        data_boundaries=evidence_pack.data_limits,
        technical_appendix={"evidence_pack": evidence_pack.to_dict()},
    )
    report = ReportRecord(
        report_id="report_time_scope",
        workspace_id=workspace["workspace_id"],
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告，关注收入结构。",
        title=plan.title,
        status="completed",
        plan=plan,
        evidence_pack=evidence_pack,
        document=document,
        validation=ReportValidationResult(status="passed"),
    )

    markdown = render_report_markdown(report)
    main_body = markdown.split("## 技术附录", 1)[0]

    assert "SELECT" not in main_body.upper()
    assert "query_revenue" not in main_body
    assert "technical_details" not in main_body
    assert "raw_rows" not in main_body
