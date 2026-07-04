import json
import sqlite3
from pathlib import Path

from workspaces.profiler import profile_workspace_database
from workspaces.report_markdown import render_report_markdown
from workspaces.report_models import (
    ReportChapterPlan,
    ReportEvidenceTable,
    ReportEvidencePack,
    ReportPlan,
    ReportDocument,
    ReportDocumentSection,
    ReportRecord,
    ReportValidationResult,
)
from workspaces.report_evidence import collect_report_evidence
from workspaces.report_ledger import CoverageChecker, build_evidence_ledger
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
    assert "date_field" in plan.missing_slots
    assert any("多个可能的时间字段" in question for question in plan.clarification_questions)
    assert "最近90天" not in plan.title
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


def test_report_planner_broad_business_review_is_not_hijacked_by_channel_topic(tmp_path):
    _store, _workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path)

    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成一份最近90天经营复盘报告，包含收入、客户、商品、渠道投放表现和建议。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    titles = {chapter.title for chapter in plan.chapters}

    assert plan.title == "最近90天经营复盘报告"
    assert plan.title != "最近90天渠道表现复盘报告"
    assert plan.report_style == "经营复盘"
    assert {"收入结构", "客户分群", "商品表现", "渠道投放表现"}.issubset(titles)
    assert "行动建议" in titles


def test_report_planner_management_brief_is_not_hijacked_by_channel_efficiency(tmp_path):
    _store, _workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path)

    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成一份管理层经营简报，重点看渠道效率、商品表现和客户分群。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    titles = {chapter.title for chapter in plan.chapters}

    assert "date_field" in plan.missing_slots
    assert any("多个可能的时间字段" in question for question in plan.clarification_questions)
    assert plan.title != "最近90天渠道表现复盘报告"
    assert plan.report_style == "管理层经营简报"
    assert {"经营概览", "商品表现", "客户分群", "渠道投放表现"}.issubset(titles)


def test_report_planner_keeps_specialized_trend_title_for_trend_only_goal(tmp_path):
    _store, _workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path)

    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成一份最近90天收入趋势变化报告。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    assert plan.title == "最近90天趋势变化报告"
    assert plan.report_style == "趋势分析"
    assert any(chapter.title == "趋势变化" for chapter in plan.chapters)
    assert plan.title != "最近90天经营复盘报告"


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


def test_evidence_ledger_derives_totals_shares_rankings_period_changes_and_coverage(tmp_path):
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

    ledger = build_evidence_ledger(plan=plan, evidence_pack=evidence_pack)
    serialized = json.dumps(ledger.to_dict(), ensure_ascii=False)

    assert ledger.ledger_version == "p23.report_ledger.v1"
    assert any(item.evidence_id == "ledger_fact_revenue_total" and item.display_value == "43.0 万" for item in ledger.facts)
    assert "收入占比" in serialized
    assert "合计占比" in serialized
    assert "排名第1" in serialized
    assert "环比" in serialized
    assert "最高周期" in serialized
    assert "数据覆盖" in serialized
    assert any(coverage.chapter_id == "revenue_structure" for coverage in ledger.chapter_coverages)
    assert any("利润" in boundary or "ROI" in boundary for boundary in ledger.data_boundaries)
    assert not any("SELECT" in json.dumps(item.to_dict(), ensure_ascii=False).upper() for item in ledger.facts + ledger.derived_metrics)


def _ledger_fix_plan() -> ReportPlan:
    return ReportPlan(
        title="最近90天经营复盘报告",
        report_style="经营复盘",
        time_range="最近90天",
        data_sources=["订单明细", "客服工单"],
        chapters=[
            ReportChapterPlan(
                chapter_id="revenue_structure",
                title="收入结构",
                purpose="说明收入来源和投入产出。",
                evidence_requirements=[],
            ),
            ReportChapterPlan(
                chapter_id="customer_segments",
                title="客户分群",
                purpose="说明客户分群贡献。",
                evidence_requirements=[],
            ),
            ReportChapterPlan(
                chapter_id="support_issues",
                title="客服问题",
                purpose="说明客服问题规模和体验。",
                evidence_requirements=[],
            ),
        ],
    )


def test_evidence_ledger_coverage_and_derived_metrics_use_revenue_not_roi_when_cost_roi_exist():
    evidence_pack = ReportEvidencePack(
        tables=[
            ReportEvidenceTable(
                table_id="channel_unit_economics",
                title="渠道经营表现",
                columns=["渠道", "收入", "成本", "ROI"],
                rows=[
                    {"渠道": "自然流量", "收入": "30.0 万", "成本": "4.0 万", "ROI": "7.5"},
                    {"渠道": "付费投放", "收入": "20.0 万", "成本": "10.0 万", "ROI": "2.0"},
                    {"渠道": "私域", "收入": "10.0 万", "成本": "2.0 万", "ROI": "5.0"},
                ],
                source_chapter_id="revenue_structure",
                description="按渠道汇总收入、成本和 ROI。",
                evidence_ref="query_channel_unit_economics",
            )
        ]
    )

    ledger = build_evidence_ledger(plan=_ledger_fix_plan(), evidence_pack=evidence_pack)
    coverage = next(item for item in ledger.chapter_coverages if item.chapter_id == "revenue_structure")
    coverage_text = "\n".join(coverage.missing_evidence + coverage.blocked_claims + coverage.data_boundaries)
    derived = json.dumps([item.to_dict() for item in ledger.derived_metrics], ensure_ascii=False)

    assert "缺少成本" not in coverage_text
    assert "ROI" not in coverage_text
    assert "利润" in coverage_text
    assert "收入合计" in derived
    assert "收入占比" in derived
    assert "收入排名" in derived
    assert "ROI合计" not in derived
    assert "ROI占比" not in derived
    assert "top2_ROI_combined_share" not in derived


def test_evidence_ledger_revenue_coverage_reports_only_actually_missing_inputs():
    evidence_pack = ReportEvidencePack(
        tables=[
            ReportEvidenceTable(
                table_id="channel_revenue",
                title="渠道收入结构",
                columns=["渠道", "收入"],
                rows=[
                    {"渠道": "自然流量", "收入": "30.0 万"},
                    {"渠道": "付费投放", "收入": "20.0 万"},
                ],
                source_chapter_id="revenue_structure",
                description="按渠道汇总收入。",
                evidence_ref="query_channel_revenue",
            )
        ]
    )

    ledger = build_evidence_ledger(plan=_ledger_fix_plan(), evidence_pack=evidence_pack)
    coverage = next(item for item in ledger.chapter_coverages if item.chapter_id == "revenue_structure")
    coverage_text = "\n".join(coverage.missing_evidence + coverage.blocked_claims + coverage.data_boundaries)

    assert coverage.coverage == "partial"
    assert "成本" in coverage_text
    assert "利润" in coverage_text
    assert "ROI" in coverage_text


def test_evidence_ledger_support_and_customer_coverage_does_not_emit_fixed_optional_gaps():
    evidence_pack = ReportEvidencePack(
        tables=[
            ReportEvidenceTable(
                table_id="customer_segment_metrics",
                title="客户分群贡献",
                columns=["客户分群", "收入", "订单数"],
                rows=[
                    {"客户分群": "成长型团队", "收入": "19.6 万", "订单数": "18"},
                    {"客户分群": "高价值企业", "收入": "14.8 万", "订单数": "11"},
                ],
                source_chapter_id="customer_segments",
                description="按客户分群汇总收入和订单。",
                evidence_ref="query_customer_segment_metrics",
            ),
            ReportEvidenceTable(
                table_id="support_issue_metrics",
                title="客服问题概览",
                columns=["问题类型", "工单量", "满意度", "平均响应时长"],
                rows=[
                    {"问题类型": "交付延期", "工单量": "42", "满意度": "4.1", "平均响应时长": "38"},
                    {"问题类型": "使用咨询", "工单量": "66", "满意度": "4.7", "平均响应时长": "16"},
                ],
                source_chapter_id="support_issues",
                description="按问题类型汇总工单、满意度和响应时长。",
                evidence_ref="query_support_issue_metrics",
            ),
        ]
    )

    ledger = build_evidence_ledger(plan=_ledger_fix_plan(), evidence_pack=evidence_pack)
    coverages = {item.chapter_id: item for item in ledger.chapter_coverages}
    customer_text = "\n".join(
        coverages["customer_segments"].missing_evidence
        + coverages["customer_segments"].blocked_claims
        + coverages["customer_segments"].data_boundaries
    )
    support_text = "\n".join(
        coverages["support_issues"].missing_evidence
        + coverages["support_issues"].blocked_claims
        + coverages["support_issues"].data_boundaries
    )

    assert coverages["customer_segments"].coverage == "strong"
    assert coverages["support_issues"].coverage == "strong"
    assert "复购" not in customer_text
    assert "留存" not in customer_text
    assert "生命周期价值" not in customer_text
    assert "成本或流失" not in support_text
    assert "经营损失" not in support_text


def test_evidence_ledger_keeps_roi_row_facts_without_contribution_derivatives():
    evidence_pack = ReportEvidencePack(
        tables=[
            ReportEvidenceTable(
                table_id="channel_roi",
                title="渠道ROI表现",
                columns=["渠道", "ROI"],
                rows=[
                    {"渠道": "自然流量", "ROI": "7.5"},
                    {"渠道": "付费投放", "ROI": "2.0"},
                ],
                source_chapter_id="revenue_structure",
                description="按渠道展示 ROI。",
                evidence_ref="query_channel_roi",
            )
        ]
    )

    ledger = build_evidence_ledger(plan=_ledger_fix_plan(), evidence_pack=evidence_pack)
    facts = json.dumps([item.to_dict() for item in ledger.facts], ensure_ascii=False)
    derived = json.dumps([item.to_dict() for item in ledger.derived_metrics], ensure_ascii=False)

    assert "自然流量ROI" in facts
    assert "付费投放ROI" in facts
    assert "ROI合计" not in derived
    assert "ROI占比" not in derived
    assert "top2_ROI_combined_share" not in derived
    assert "SUM(ROI)" not in derived


def test_evidence_ledger_does_not_sum_average_or_duration_only_tables():
    evidence_pack = ReportEvidencePack(
        tables=[
            ReportEvidenceTable(
                table_id="support_experience_metrics",
                title="客服体验指标",
                columns=["问题类型", "满意度", "平均响应时长"],
                rows=[
                    {"问题类型": "交付延期", "满意度": "4.1", "平均响应时长": "38"},
                    {"问题类型": "使用咨询", "满意度": "4.7", "平均响应时长": "16"},
                ],
                source_chapter_id="support_issues",
                description="按问题类型展示满意度和平均响应时长。",
                evidence_ref="query_support_experience_metrics",
            )
        ]
    )

    ledger = build_evidence_ledger(plan=_ledger_fix_plan(), evidence_pack=evidence_pack)
    facts = json.dumps([item.to_dict() for item in ledger.facts], ensure_ascii=False)
    derived = json.dumps([item.to_dict() for item in ledger.derived_metrics], ensure_ascii=False)

    assert "交付延期满意度" in facts
    assert "使用咨询平均响应时长" in facts
    assert "满意度合计" not in derived
    assert "满意度占比" not in derived
    assert "平均响应时长合计" not in derived
    assert "平均响应时长占比" not in derived
    assert "SUM(满意度)" not in derived
    assert "SUM(平均响应时长)" not in derived


def test_evidence_ledger_revenue_coverage_ignores_title_and_description_for_missing_fields():
    evidence_pack = ReportEvidencePack(
        tables=[
            ReportEvidenceTable(
                table_id="channel_revenue_only",
                title="收入与ROI分析",
                columns=["渠道", "收入"],
                rows=[
                    {"渠道": "自然流量", "收入": "30.0 万"},
                    {"渠道": "付费投放", "收入": "20.0 万"},
                ],
                source_chapter_id="revenue_structure",
                description="计划补充成本和ROI后再复盘投入产出。",
                evidence_ref="query_channel_revenue_only",
            )
        ]
    )

    ledger = build_evidence_ledger(plan=_ledger_fix_plan(), evidence_pack=evidence_pack)
    coverage = next(item for item in ledger.chapter_coverages if item.chapter_id == "revenue_structure")
    coverage_text = "\n".join(coverage.missing_evidence + coverage.blocked_claims + coverage.data_boundaries)

    assert coverage.coverage == "partial"
    assert "成本" in coverage_text
    assert "利润" in coverage_text
    assert "ROI" in coverage_text


def test_coverage_checker_marks_strong_partial_and_missing_without_table_name_rules(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path, include_support=False)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成经营复盘报告，关注收入结构、客服问题和行动建议。",
        profile=profile,
        semantic_layer=semantic_layer,
    )
    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )
    ledger = build_evidence_ledger(plan=plan, evidence_pack=evidence_pack)
    coverages = {item.chapter_id: item for item in ledger.chapter_coverages}

    assert coverages["overview"].coverage == "strong"
    assert coverages["revenue_structure"].coverage == "partial"
    assert any("利润" in item or "ROI" in item for item in coverages["revenue_structure"].missing_evidence)
    assert coverages["support_issues"].coverage == "missing"
    assert any("客服" in item or "工单" in item for item in coverages["support_issues"].blocked_claims)
    assert CoverageChecker(plan=plan, evidence_pack=evidence_pack).check()[0].chapter_id == "overview"


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


def test_chart_artifacts_reference_evidence_ledger_items(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告，关注收入结构和趋势变化。",
        profile=profile,
        semantic_layer=semantic_layer,
    )
    artifact_dir = Path(workspace["root_path"]) / "reports" / "report_chart_ledger_test" / "artifacts"
    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
        artifact_dir=artifact_dir,
        artifact_base_path="reports/report_chart_ledger_test/artifacts",
    )

    ledger = build_evidence_ledger(plan=plan, evidence_pack=evidence_pack)
    ledger_ids = {item.evidence_id for item in ledger.facts + ledger.derived_metrics}
    chart = next(chart for chart in evidence_pack.charts if chart.chart_id == "revenue_structure_chart")

    assert chart.artifact_id == "artifact_chart_revenue_structure_chart"
    assert chart.evidence_ids or chart.ledger_metric_ids
    assert set(chart.evidence_ids + chart.ledger_metric_ids).issubset(ledger_ids)
    assert any(item.startswith("ledger_fact_") for item in chart.evidence_ids)
    assert any(item.startswith("ledger_metric_") for item in chart.ledger_metric_ids)
    serialized_chart = json.dumps(chart.to_dict(), ensure_ascii=False)
    assert "query_id" not in serialized_chart
    assert "raw_rows" not in serialized_chart
    assert "SELECT" not in serialized_chart.upper()


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


def test_report_planner_generates_structured_requirements_for_common_business_goals(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Common Business Goals Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (sale_date TEXT, store_name TEXT, sales_amount REAL)")
        conn.execute("CREATE TABLE product_sales (sale_date TEXT, category_name TEXT, paid_amount REAL)")
        conn.execute(
            "CREATE TABLE support_tickets (ticket_date TEXT, team_name TEXT, ticket_count INTEGER, avg_response_minutes REAL, satisfaction_score REAL)"
        )
        conn.execute("CREATE TABLE campaigns (campaign_date TEXT, channel_name TEXT, revenue_amount REAL, spend_amount REAL)")
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成经营复盘报告，包含门店表现、商品表现、客服运营和渠道投放表现。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    requirements = [req.to_dict() for chapter in plan.chapters for req in chapter.evidence_requirements]
    calculations = {req["calculation_type"] for req in requirements}
    requirement_text = json.dumps(requirements, ensure_ascii=False)

    assert "门店表现" in [chapter.title for chapter in plan.chapters]
    assert "商品表现" in [chapter.title for chapter in plan.chapters]
    assert "客服运营" in [chapter.title for chapter in plan.chapters]
    assert "渠道投放表现" in [chapter.title for chapter in plan.chapters]
    assert {"ranking", "contribution", "operational_efficiency", "investment_efficiency"} <= calculations
    assert "time_range" in requirement_text
    assert "metrics" in requirement_text
    assert "dimensions" in requirement_text
    assert "group_by" in requirement_text
    assert "comparison_scope" in requirement_text
    assert "missing_evidence" in requirement_text


def test_report_evidence_collects_generic_store_product_support_and_campaign_evidence(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Generic Report Evidence Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (sale_date TEXT, store_name TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [("2026-06-01", "上海旗舰店", 300000.0), ("2026-06-02", "北京国贸店", 100000.0)],
        )
        conn.execute("CREATE TABLE product_sales (sale_date TEXT, category_name TEXT, paid_amount REAL)")
        conn.executemany(
            "INSERT INTO product_sales VALUES (?, ?, ?)",
            [("2026-06-01", "饮料", 120000.0), ("2026-06-02", "零食", 80000.0)],
        )
        conn.execute(
            "CREATE TABLE support_tickets (ticket_date TEXT, team_name TEXT, ticket_count INTEGER, avg_response_minutes REAL, satisfaction_score REAL)"
        )
        conn.executemany(
            "INSERT INTO support_tickets VALUES (?, ?, ?, ?, ?)",
            [
                ("2026-06-01", "华东客服组", 120, 16.0, 4.8),
                ("2026-06-02", "华北客服组", 95, 35.0, 4.2),
            ],
        )
        conn.execute("CREATE TABLE campaigns (campaign_date TEXT, channel_name TEXT, revenue_amount REAL, spend_amount REAL)")
        conn.executemany(
            "INSERT INTO campaigns VALUES (?, ?, ?, ?)",
            [("2026-06-01", "搜索广告", 180000.0, 60000.0), ("2026-06-02", "内容投放", 90000.0, 45000.0)],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告，包含门店表现、商品表现、客服运营和渠道投放表现。",
        profile=profile,
        semantic_layer=semantic_layer,
    )

    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )

    titles = {table.title for table in evidence_pack.tables}
    serialized_payloads = json.dumps(evidence_pack.evidence_payloads, ensure_ascii=False)

    assert "门店表现" in titles
    assert "商品贡献" in titles
    assert "客服运营效率" in titles
    assert "渠道投放效率" in titles
    assert "上海旗舰店" in serialized_payloads
    assert "60.0%" in serialized_payloads
    assert "华东客服组" in serialized_payloads
    assert "广告投入产出比" in serialized_payloads or "净投放回报率" in serialized_payloads
    assert "SELECT" not in serialized_payloads.upper()


def test_report_evidence_records_data_limit_for_unsafe_cross_table_investment_efficiency(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Unsafe Cross Table Investment Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE sales (sale_date TEXT, channel_name TEXT, revenue_amount REAL)")
        conn.execute("CREATE TABLE ad_spend (spend_date TEXT, campaign_name TEXT, spend_amount REAL)")
        conn.executemany(
            "INSERT INTO sales VALUES (?, ?, ?)",
            [("2026-06-01", "搜索广告", 180000.0), ("2026-06-02", "内容投放", 90000.0)],
        )
        conn.executemany(
            "INSERT INTO ad_spend VALUES (?, ?, ?)",
            [("2026-06-01", "SEM-6月", 60000.0), ("2026-06-02", "内容-6月", 45000.0)],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    plan = plan_workspace_report(
        report_type="channel_performance",
        report_goal="生成最近90天渠道投放表现报告，关注收入、投放成本、ROAS 和净投放回报率。",
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
    investment_tables = [table for table in evidence_pack.tables if table.title == "渠道投放效率"]

    assert not investment_tables
    assert "跨表" in limits or "关联字段" in limits
    assert "ROAS" in limits or "ROI" in limits or "投放" in limits


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


def test_report_markdown_does_not_duplicate_action_recommendation_sections(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告，关注收入结构和行动建议。",
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
        sections=[
            ReportDocumentSection(
                section_id="revenue_structure",
                title="收入结构",
                body="收入结构正文。",
            ),
            ReportDocumentSection(
                section_id="actions",
                title="行动建议",
                body="不要作为正文重复展示。",
            ),
        ],
        action_recommendations=["优先复盘高收入来源。"],
        data_boundaries=evidence_pack.data_limits,
    )
    report = ReportRecord(
        report_id="report_no_duplicate_actions",
        workspace_id=workspace["workspace_id"],
        report_type="business_review",
        report_goal=plan.report_goal,
        title=plan.title,
        status="completed",
        plan=plan,
        evidence_pack=evidence_pack,
        document=document,
        validation=ReportValidationResult(status="passed"),
    )

    markdown = render_report_markdown(report)

    assert "### 行动建议" not in markdown
    assert markdown.count("## 行动建议") == 1
    assert "不要作为正文重复展示" not in markdown
    assert "优先复盘高收入来源。" in markdown


def test_report_markdown_appendix_summarizes_coverage_without_ledger_dump(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path, include_support=False)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告，关注收入结构和客服问题。",
        profile=profile,
        semantic_layer=semantic_layer,
    )
    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
    )
    ledger = build_evidence_ledger(plan=plan, evidence_pack=evidence_pack)
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="本报告基于当前工作区证据生成。",
        sections=[],
        action_recommendations=["先补齐客服数据。"],
        data_boundaries=evidence_pack.data_limits,
        technical_appendix={"evidence_ledger": ledger.to_dict()},
    )
    report = ReportRecord(
        report_id="report_coverage_summary",
        workspace_id=workspace["workspace_id"],
        report_type="business_review",
        report_goal=plan.report_goal,
        title=plan.title,
        status="partial",
        plan=plan,
        evidence_pack=evidence_pack,
        document=document,
        validation=ReportValidationResult(status="warning"),
    )

    markdown = render_report_markdown(report)
    main_body = markdown.split("## 技术附录", 1)[0]
    appendix = markdown.split("## 技术附录", 1)[1]

    assert "ledger_version" not in main_body
    assert "claim_phrases" not in main_body
    assert "coverage" not in main_body
    assert "章节覆盖" in appendix
    assert "收入结构" in appendix
    assert "客服问题" in appendix
    assert "ledger_version" not in appendix
    assert "claim_phrases" not in appendix


def test_report_markdown_appendix_summarizes_artifact_ledger_refs_without_raw_ledger_dump(tmp_path):
    _store, workspace, profile, semantic_layer = _prepare_business_workspace(tmp_path)
    plan = plan_workspace_report(
        report_type="business_review",
        report_goal="生成最近90天经营复盘报告，关注收入结构和趋势变化。",
        profile=profile,
        semantic_layer=semantic_layer,
    )
    artifact_dir = Path(workspace["root_path"]) / "reports" / "report_artifact_summary" / "artifacts"
    evidence_pack = collect_report_evidence(
        plan=plan,
        profile=profile,
        semantic_layer=semantic_layer,
        analysis_db_path=workspace["analysis_db_path"],
        artifact_dir=artifact_dir,
        artifact_base_path="reports/report_artifact_summary/artifacts",
    )
    ledger = build_evidence_ledger(plan=plan, evidence_pack=evidence_pack)
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="本报告基于当前工作区证据生成。",
        sections=[],
        action_recommendations=["继续观察收入变化。"],
        data_boundaries=evidence_pack.data_limits,
        technical_appendix={
            "evidence_ledger": ledger.to_dict(),
            "ledger_reference_summary": {
                "evidence_ids": [item.evidence_id for item in ledger.facts[:2]],
                "ledger_metric_ids": [item.evidence_id for item in ledger.derived_metrics[:2]],
            },
            "artifact_summary": {
                "artifact_count": 3,
                "chart_count": 1,
                "report_artifacts": ["Markdown 报告", "报告文档记录"],
            },
        },
    )
    report = ReportRecord(
        report_id="report_artifact_summary",
        workspace_id=workspace["workspace_id"],
        report_type="business_review",
        report_goal=plan.report_goal,
        title=plan.title,
        status="completed",
        plan=plan,
        evidence_pack=evidence_pack,
        document=document,
        validation=ReportValidationResult(status="passed"),
    )

    markdown = render_report_markdown(report)
    appendix = markdown.split("## 技术附录", 1)[1]

    assert "Artifact" not in appendix
    assert "产物概况" in appendix
    assert "账本引用" in appendix
    assert "Markdown 报告" in appendix
    assert "ledger_version" not in appendix
    assert "claim_phrases" not in appendix
    assert "SELECT" not in appendix.upper()
    assert "raw_rows" not in appendix
