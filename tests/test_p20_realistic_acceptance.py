import json
import sqlite3
from pathlib import Path

from workspaces.analysis_runner import run_workspace_analysis
from workspaces.importers import import_csv
from workspaces.profiler import profile_workspace_database
from workspaces.report_runner import run_workspace_report
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.write_text("\n".join([header, *rows]), encoding="utf-8")


def _prepare_workspace(tmp_path: Path, workspace_name: str, files: dict[str, tuple[str, list[str]]]):
    dataset_dir = tmp_path / workspace_name
    dataset_dir.mkdir(parents=True, exist_ok=True)
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace(workspace_name)
    for filename, (header, rows) in files.items():
        path = dataset_dir / filename
        _write_csv(path, header, rows)
        import_csv(store, workspace["workspace_id"], path)
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace, profile, semantic_layer


def _answer_text(result: dict) -> str:
    answer = result["product_result"]["business_answer"]
    return "\n".join(
        [
            answer["headline"],
            answer["direct_answer"],
            answer["why"],
            *answer["evidence_bullets"],
            *answer["recommendations"],
            *answer["caveats"],
        ]
    )


def _assert_chinese_business_result(result: dict, *, expect_chart: bool) -> None:
    text = _answer_text(result)
    assert result["status"] == "completed"
    assert result["execution_result"]["success"] is True
    assert result["product_result"]["business_answer"]["headline"]
    assert any("\u4e00" <= char <= "\u9fff" for char in text)
    assert "SELECT " not in text.upper()
    assert "provider_called" not in text
    assert result["product_result"]["evidence"]["table_preview"]["rows"]
    assert result["product_result"]["evidence"]["fact_payload"]["rows"] == result["execution_result"]["rows"]
    if expect_chart:
        assert result["product_result"]["chart_artifacts"]
        assert result["product_result"]["chart_artifacts"][0]["url"].startswith("/api/workspaces/")
    else:
        assert result["product_result"]["chart_artifacts"] == []


def test_p20_store_sales_acceptance_covers_fact_ranking_comparison_trend_recommendation_and_report(tmp_path):
    store, workspace, profile, semantic_layer = _prepare_workspace(
        tmp_path,
        "store_sales_acceptance",
        {
            "store_sales.csv": (
                "store_name,business_date,city,sales_amount,gross_margin,satisfaction_score",
                [
                    "上海旗舰店,2026-04-01,上海,21500,0.37,4.8",
                    "上海旗舰店,2026-05-01,上海,23800,0.39,4.7",
                    "上海旗舰店,2026-06-01,上海,26255.44,0.41,4.8",
                    "北京国贸店,2026-04-01,北京,17600,0.34,4.3",
                    "北京国贸店,2026-05-01,北京,18100,0.35,4.4",
                    "北京国贸店,2026-06-01,北京,18400,0.36,4.4",
                    "深圳湾店,2026-04-01,深圳,11000,0.31,4.1",
                    "深圳湾店,2026-05-01,深圳,11600,0.32,4.2",
                    "深圳湾店,2026-06-01,深圳,12000,0.33,4.1",
                ],
            )
        },
    )

    assert profile["tables"]
    assert "store_sales" in {table["table_name"] for table in profile["tables"]}
    semantic_text = json.dumps(semantic_layer, ensure_ascii=False)
    assert "门店" in semantic_text
    assert "销售额" in semantic_text
    assert "orders" not in semantic_text
    assert "marketing_spend" not in semantic_text

    fact = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近90天哪个门店销售额最高？只回答事实。",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 3"
        ),
    )
    ranking = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近90天按门店做销售额排名。",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 3"
        ),
    )
    comparison = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "比较各门店销售额和满意度，看看哪个更值得关注。",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales, AVG(satisfaction_score) AS satisfaction_score "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 3"
        ),
    )
    trend = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近90天销售额趋势如何？",
        initial_sql=(
            "SELECT substr(business_date, 1, 7) AS month, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY month ORDER BY month"
        ),
    )
    recommendation = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "结合销售额、毛利率和满意度，哪个门店下一步最值得优先复盘？请给建议和风险边界。",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales, AVG(gross_margin) AS margin_rate, "
            "AVG(satisfaction_score) AS satisfaction_score FROM store_sales "
            "GROUP BY store_name ORDER BY total_sales DESC LIMIT 3"
        ),
    )

    for result in (fact, ranking, trend):
        _assert_chinese_business_result(result, expect_chart=False)
        assert result["analysis_route"]["route"] == "fast_fact"
    for result in (comparison, recommendation):
        _assert_chinese_business_result(result, expect_chart=True)
        assert result["analysis_route"]["requires_full_chain"] is True

    assert fact["product_result"]["business_answer"]["recommendations"] == []
    assert ranking["product_result"]["evidence"]["fact_payload"]["comparison_scope"]["sufficient"] is True
    assert comparison["visualization_decision"]["chart_spec"]["chart_type"] == "scatter"
    assert recommendation["product_result"]["business_answer"]["recommendations"]
    assert "上海旗舰店" in _answer_text(recommendation)

    report = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成门店经营复盘报告，关注销售额、毛利率、满意度和下一步优化建议。",
    )
    document = report["report"]["document"]
    assert report["success"] is True
    assert report["report"]["sections"] == []
    assert report["report"]["plan"]["title"] == "最近90天经营复盘报告"
    assert report["report"]["evidence_pack"]["facts"]
    assert document["sections"]
    document_text = json.dumps(
        {
            "opening_summary": document["opening_summary"],
            "sections": document["sections"],
            "action_recommendations": document["action_recommendations"],
            "data_boundaries": document["data_boundaries"],
        },
        ensure_ascii=False,
    )
    assert "ReportDocument" not in document_text
    assert "章节业务答案" not in document_text
    assert "SELECT " not in document_text.upper()


def test_p20_support_ticket_acceptance_covers_service_operations_dataset(tmp_path):
    store, workspace, profile, semantic_layer = _prepare_workspace(
        tmp_path,
        "support_ticket_acceptance",
        {
            "support_tickets.csv": (
                "team_name,ticket_date,issue_type,ticket_count,avg_response_minutes,satisfaction_score",
                [
                    "华东客服组,2026-06-01,退款咨询,86,18,4.7",
                    "华东客服组,2026-06-08,物流咨询,92,16,4.8",
                    "华北客服组,2026-06-01,退款咨询,75,35,4.2",
                    "华北客服组,2026-06-08,物流咨询,80,31,4.3",
                    "华南客服组,2026-06-01,售后维修,68,22,4.5",
                    "华南客服组,2026-06-08,物流咨询,70,21,4.6",
                ],
            )
        },
    )

    semantic_text = json.dumps(semantic_layer, ensure_ascii=False)
    assert profile["tables"]
    assert "客服" in semantic_text or "团队" in semantic_text
    assert "满意度" in semantic_text
    assert "orders" not in semantic_text
    assert "channel" not in semantic_text.lower()

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近30天比较各客服团队工单量、平均响应时长和满意度，哪个团队需要优先关注？",
        initial_sql=(
            "SELECT team_name, SUM(ticket_count) AS ticket_count, "
            "AVG(avg_response_minutes) AS avg_response_minutes, AVG(satisfaction_score) AS satisfaction_score "
            "FROM support_tickets GROUP BY team_name ORDER BY avg_response_minutes DESC LIMIT 3"
        ),
    )

    _assert_chinese_business_result(result, expect_chart=True)
    text = _answer_text(result)
    assert "客服" in text or "团队" in text
    assert "工单" in text
    assert "满意度" in text
    assert "channel" not in text.lower()
    assert "revenue" not in text.lower()


def test_p20_report_output_uses_document_contract_not_fixed_section_prompts(tmp_path):
    store, workspace, _profile, _semantic_layer = _prepare_workspace(
        tmp_path,
        "report_document_acceptance",
        {
            "store_sales.csv": (
                "store_name,business_date,city,sales_amount,gross_margin,satisfaction_score",
                ["上海旗舰店,2026-06-01,上海,26255.44,0.41,4.8"],
            )
        },
    )

    report = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成门店经营复盘报告，关注销售额、毛利率和满意度。",
    )

    assert report["success"] is True
    assert report["report"]["sections"] == []
    assert report["report"]["document"]["sections"]
    removed_metadata_key = "section" + "_" + "runner" + "_" + "used"
    assert removed_metadata_key not in report["report"]["provider_metadata"]
