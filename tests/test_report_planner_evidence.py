import json
import sqlite3
from pathlib import Path

from workspaces.profiler import profile_workspace_database
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
