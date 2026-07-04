import json
from pathlib import Path

from workspaces.analysis_runner import run_workspace_analysis
from workspaces.importers import import_csv
from workspaces.profiler import profile_workspace_database
from workspaces.report_runner import run_workspace_report
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


PROVIDER_FLAGS = [
    "INSIGHTFLOW_PRODUCT_LIVE_MODE",
    "INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING",
    "INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING",
    "INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE",
    "INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT",
    "INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER",
    "INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING",
    "INSIGHTFLOW_USE_PROVIDER_ANSWER_REVIEWER",
    "INSIGHTFLOW_USE_PROVIDER_FINAL_ANSWER_COMPOSER",
    "INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING",
]

FORBIDDEN_REPORT_TERMS = [
    "章节业务答案",
    "SELECT ",
    "raw_rows",
    "raw rows",
    "query id",
    "query_",
    "trace",
    "provider_metadata",
    "prompt",
    "PROMPT",
]


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.write_text("\n".join([header, *rows]), encoding="utf-8")


def _prepare_p25_workspace(tmp_path: Path):
    dataset_dir = tmp_path / "p25_real_usage_data"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P25 Real Usage Acceptance")
    files = {
        "channel_spend.csv": (
            "渠道,日期,收入金额,投放金额",
            [
                "抖音,2026-04-12,240000,90000",
                "抖音,2026-05-18,250000,95000",
                "小红书,2026-04-20,180000,52000",
                "小红书,2026-06-08,170000,50000",
                "私域社群,2026-05-02,180000,24000",
                "私域社群,2026-06-15,196000,26000",
            ],
        ),
        "customer_orders.csv": (
            "客户ID,客户分群,订单日期,订单ID,订单金额",
            [
                "C001,高价值会员,2026-04-10,O001,1200",
                "C001,高价值会员,2026-05-10,O002,900",
                "C002,高价值会员,2026-04-15,O003,1500",
                "C002,高价值会员,2026-06-02,O004,1100",
                "C003,高价值会员,2026-05-18,O005,700",
                "C004,成长会员,2026-04-11,O006,650",
                "C004,成长会员,2026-05-12,O007,680",
                "C005,成长会员,2026-06-16,O008,720",
                "C006,成长会员,2026-05-20,O009,540",
                "C007,新客试用,2026-04-21,O010,300",
                "C008,新客试用,2026-05-22,O011,320",
                "C009,新客试用,2026-06-23,O012,280",
            ],
        ),
        "customer_segments.csv": (
            "客户分群,月份,客户数,复购客户数,复购率",
            [
                "高价值会员,2026-06,120,96,0.8000",
                "成长会员,2026-06,180,90,0.5000",
                "新客试用,2026-06,260,52,0.2000",
            ],
        ),
        "product_sales.csv": (
            "品类,日期,成交金额,销量",
            [
                "咖啡豆,2026-04-01,88000,340",
                "咖啡豆,2026-05-01,96000,360",
                "咖啡豆,2026-06-01,105000,390",
                "挂耳咖啡,2026-04-01,52000,1150",
                "挂耳咖啡,2026-05-01,56000,1250",
                "挂耳咖啡,2026-06-01,61000,1320",
                "杯具周边,2026-04-01,42000,260",
                "杯具周边,2026-05-01,39000,240",
                "杯具周边,2026-06-01,45000,280",
            ],
        ),
        "store_sales.csv": (
            "门店,营业日期,城市,销售额,订单数,毛利率,满意度",
            [
                "上海旗舰店,2026-04-01,上海,92000,310,0.42,4.8",
                "上海旗舰店,2026-05-01,上海,98000,328,0.43,4.8",
                "上海旗舰店,2026-06-01,上海,108000,352,0.44,4.9",
                "北京国贸店,2026-04-01,北京,76000,280,0.38,4.5",
                "北京国贸店,2026-05-01,北京,79000,292,0.39,4.5",
                "北京国贸店,2026-06-01,北京,81000,301,0.39,4.6",
                "深圳湾店,2026-04-01,深圳,65000,240,0.35,4.2",
                "深圳湾店,2026-05-01,深圳,68000,248,0.35,4.3",
                "深圳湾店,2026-06-01,深圳,69000,251,0.36,4.3",
            ],
        ),
    }
    for filename, (header, rows) in files.items():
        path = dataset_dir / filename
        _write_csv(path, header, rows)
        import_csv(store, workspace["workspace_id"], path)
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace, profile, semantic_layer


def _business_text(result: dict) -> str:
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


def _data_limits_text(result: dict) -> str:
    payload = result["product_result"]["evidence"]["fact_payload"]
    return "\n".join(
        [
            *payload.get("data_limits", []),
            *payload.get("warnings", []),
            *result["product_result"]["business_answer"]["caveats"],
        ]
    )


def _assert_clean_chinese_analysis(result: dict) -> None:
    text = _business_text(result)
    assert result["status"] == "completed"
    assert result["execution_result"]["success"] is True
    assert any("\u4e00" <= char <= "\u9fff" for char in text)
    assert "SELECT " not in text.upper()
    assert "raw_rows" not in text
    assert "provider_metadata" not in text
    assert result["product_result"]["evidence"]["fact_payload"]["evidence_requirements"]


def _report_business_text(report: dict) -> str:
    document = report["report"]["document"]
    return json.dumps(
        {
            "title": document["title"],
            "opening_summary": document["opening_summary"],
            "sections": document["sections"],
            "action_recommendations": document["action_recommendations"],
            "data_boundaries": document["data_boundaries"],
        },
        ensure_ascii=False,
    )


def test_p25_compact_realistic_acceptance_covers_analysis_and_report_goals(tmp_path, monkeypatch):
    for name in PROVIDER_FLAGS:
        monkeypatch.setenv(name, "0")

    store, workspace, _profile, semantic_layer = _prepare_p25_workspace(tmp_path)
    semantic_text = json.dumps(semantic_layer, ensure_ascii=False)
    for keyword in ["渠道", "客户", "品类", "门店", "销售额", "成交金额", "销量", "投放"]:
        assert keyword in semantic_text

    roi = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近90天哪个渠道 ROI 最高？为什么？",
        initial_sql=(
            'SELECT "渠道", SUM("收入金额") AS "收入", SUM("投放金额") AS "投放金额", '
            'ROUND(1.0 * SUM("收入金额") / NULLIF(SUM("投放金额"), 0), 2) AS "ROI" '
            'FROM "channel_spend" GROUP BY "渠道" ORDER BY "ROI" DESC'
        ),
    )
    _assert_clean_chinese_analysis(roi)
    roi_answer = roi["product_result"]["business_answer"]
    first_sentence = roi_answer["direct_answer"].split("。", 1)[0]
    assert "私域社群" in first_sentence
    assert "ROI" in first_sentence

    repeat_rate = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "哪个客户分群复购率最高？",
        initial_sql=(
            'SELECT "客户分群", SUM("客户数") AS "客户数", SUM("复购客户数") AS "复购客户数", '
            'ROUND(AVG("复购率"), 4) AS "复购率" '
            'FROM "customer_segments" GROUP BY "客户分群" ORDER BY "复购率" DESC'
        ),
    )
    _assert_clean_chinese_analysis(repeat_rate)
    assert "高价值会员" in _business_text(repeat_rate)
    repeat_limits = _data_limits_text(repeat_rate)
    assert "复购率" not in repeat_limits
    assert "repeat_rate" not in repeat_limits.lower()

    category = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "哪个商品品类成交金额最高，哪个销量最高？",
        initial_sql=(
            'SELECT "品类", SUM("成交金额") AS "成交金额", SUM("销量") AS "销量" '
            'FROM "product_sales" GROUP BY "品类" ORDER BY "成交金额" DESC'
        ),
    )
    _assert_clean_chinese_analysis(category)
    category_text = _business_text(category)
    category_limits = _data_limits_text(category)
    assert "咖啡豆" in category_text
    assert "挂耳咖啡" in category_text
    assert "成交金额" in category_text
    assert "销量" in category_text
    assert "成交金额" not in category_limits
    assert "销量" not in category_limits

    store_review = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "帮我做一下门店经营复盘。",
        initial_sql=(
            'SELECT "门店", SUM("销售额") AS "销售额", SUM("订单数") AS "订单数", '
            'ROUND(AVG("毛利率"), 4) AS "毛利率", ROUND(AVG("满意度"), 2) AS "满意度" '
            'FROM "store_sales" GROUP BY "门店" ORDER BY "销售额" DESC'
        ),
    )
    _assert_clean_chinese_analysis(store_review)
    store_text = _business_text(store_review) + "\n" + _data_limits_text(store_review)
    assert "上海旗舰店" in store_text
    for stale_field in ["order_date", "total_revenue", "marketing_spend", "orders_"]:
        assert stale_field not in store_text

    report_cases = [
        ("生成一份最近90天经营复盘报告，包含收入、客户、商品、渠道投放表现和建议。", "最近90天经营复盘报告"),
        ("生成一份最近90天渠道投放表现复盘报告。", "最近90天渠道表现复盘报告"),
        ("生成一份最近90天收入趋势变化报告。", "最近90天趋势变化报告"),
    ]
    for goal, expected_title in report_cases:
        report = run_workspace_report(store, workspace["workspace_id"], "business_review", goal)
        assert report["success"] is True
        assert report["report"]["title"] == expected_title
        assert report["report"]["document"]["title"] == expected_title
        assert report["report"]["document"]["sections"]
        report_text = _report_business_text(report)
        assert any("\u4e00" <= char <= "\u9fff" for char in report_text)
        for forbidden in FORBIDDEN_REPORT_TERMS:
            assert forbidden.lower() not in report_text.lower()
        assert "sections" not in report["report"]

    ambiguous_report = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成一份管理层经营简报，重点看渠道效率、商品表现和客户分群。",
    )
    ambiguous_text = json.dumps(ambiguous_report["report"], ensure_ascii=False)
    assert ambiguous_report["success"] is False
    assert "date_field" in ambiguous_report["report"]["plan"]["missing_slots"]
    assert "多个可能的时间字段" in ambiguous_text

    broad_report = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成一份最近90天经营复盘报告，包含收入、客户、商品、渠道投放表现和建议。",
    )
    broad_sections = {section["title"] for section in broad_report["report"]["document"]["sections"]}
    assert {"收入结构", "客户分群", "商品表现", "渠道投放表现"}.issubset(broad_sections)
