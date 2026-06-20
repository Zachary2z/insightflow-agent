from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def test_report_supervisor_decomposes_weekly_report_question():
    from agents.report_supervisor import plan_business_review_sections

    sections = plan_business_review_sections("帮我生成一份本周电商经营分析周报，包括销售额、订单量、Top 商品和运营建议。")

    section_ids = [section["section_id"] for section in sections]
    assert "weekly_gmv" in section_ids
    assert "weekly_order_count" in section_ids
    assert "weekly_aov" in section_ids
    assert "top_products" in section_ids
    assert "top_categories" in section_ids
    assert "declining_categories" in section_ids
    assert "next_week_recommendations" in section_ids

    for section in sections:
        assert section["title"]
        assert section["question"]
        assert section["sql"].strip().lower().startswith("select")
        assert section["expected_chart_type"] in {"bar", "line", "none"}


def test_report_supervisor_runs_multiple_sql_subtasks_and_saves_weekly_report(tmp_path):
    from agents.report_supervisor import run_report_supervisor_agent
    from agents.supervisor import initialize_run

    state = initialize_run(
        "帮我生成一份本周电商经营分析周报，包括销售额、订单量、Top 商品、下降品类和运营建议。",
        run_id="run_weekly_report_test",
        session_id="session_weekly_report_test",
    )
    state["db_path"] = DB_PATH
    state["trace_dir"] = tmp_path / "traces"

    result = run_report_supervisor_agent(
        state,
        report_dir=tmp_path / "markdown",
        chart_dir=tmp_path / "charts",
    )

    assert result["status"] == "business_review_report_completed"
    assert result["report_type"] == "weekly_business_report"
    assert len(result["report_sections"]) >= 7
    assert len(result["report_sub_tasks"]) >= 6
    assert result["weekly_report_result"]["success"] is True

    successful_sql_tasks = [task for task in result["report_sub_tasks"] if task["status"] == "completed"]
    assert len(successful_sql_tasks) >= 5
    for task in result["report_sub_tasks"]:
        assert task["sql"]
        assert "approved" in task["review_result"]
        assert "success" in task["execution_result"]

    report_path = Path(result["weekly_report_path"])
    report_text = report_path.read_text(encoding="utf-8")
    assert report_path.exists()
    assert report_path.name == "run_weekly_report_test_weekly_business_report.md"
    assert "# 本周电商经营分析周报" in report_text
    assert "## 2. 核心指标" in report_text
    assert "## 3. Top 商品" in report_text
    assert "## 5. 销售下降品类" in report_text
    assert "## 7. 数据支持结论" in report_text
    assert "## 8. 需要进一步验证的假设" in report_text
    assert "## 10. Trace 与 SQL 记录" in report_text
    assert "```sql" in report_text
    assert "Execution Evidence" in report_text
    assert "Chart Paths" in report_text
    assert result["trace_path"] in report_text
    assert result["trace_path"].endswith("run_weekly_report_test.json")
    assert Path(result["trace_path"]).exists()

    chart_paths = [path for task in result["report_sub_tasks"] for path in task.get("chart_paths", [])]
    assert chart_paths
    for chart_path in chart_paths:
        assert Path(chart_path).exists()


def test_report_supervisor_records_failed_subtask_without_crashing(tmp_path):
    from agents.report_supervisor import run_report_supervisor_agent
    from agents.supervisor import initialize_run

    state = initialize_run(
        "帮我生成一份本周电商经营分析周报。",
        run_id="run_weekly_report_failure_test",
        session_id="session_weekly_report_failure_test",
    )
    state["db_path"] = DB_PATH
    state["trace_dir"] = tmp_path / "traces"
    state["report_sections"] = [
        {
            "section_id": "weekly_gmv",
            "title": "本周 GMV",
            "question": "本周 GMV 是多少？",
            "sql": """
SELECT ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
WHERE o.status = 'paid'
LIMIT 100
""".strip(),
            "expected_chart_type": "none",
        },
        {
            "section_id": "runtime_failure",
            "title": "失败子任务",
            "question": "执行失败的 SQL 子任务。",
            "sql": "SELECT unknown_runtime_fn(id) AS broken_metric FROM orders LIMIT 5",
            "expected_chart_type": "none",
        },
    ]

    result = run_report_supervisor_agent(
        state,
        report_dir=tmp_path / "markdown",
        chart_dir=tmp_path / "charts",
    )

    failed_task = next(task for task in result["report_sub_tasks"] if task["section_id"] == "runtime_failure")
    assert failed_task["status"] == "failed"
    assert failed_task["review_result"]["approved"] is True
    assert failed_task["execution_result"]["success"] is False
    assert "unknown_runtime_fn" in failed_task["execution_result"]["error"]

    assert result["weekly_report_result"]["success"] is True
    assert Path(result["weekly_report_path"]).exists()
    assert result["status"] == "business_review_report_completed_with_subtask_errors"
    assert "runtime_failure" in Path(result["weekly_report_path"]).read_text(encoding="utf-8")


def test_report_supervisor_decomposes_monthly_review_question_and_saves_monthly_report(tmp_path):
    from agents.report_supervisor import plan_business_review_sections, run_report_supervisor_agent
    from agents.supervisor import initialize_run

    sections = plan_business_review_sections("帮我生成本月电商经营复盘，包含 GMV、订单量、Top 商品和下月建议。")

    assert sections
    assert all(section["report_type"] == "monthly_business_report" for section in sections)
    assert any("本月" in section["title"] or "月" in section["question"] for section in sections)
    assert all("'-29 day'" in section["sql"] or "本月" not in section["question"] for section in sections)

    state = initialize_run(
        "帮我生成本月电商经营复盘，包含 GMV、订单量、Top 商品和下月建议。",
        run_id="run_monthly_report_test",
        session_id="session_monthly_report_test",
    )
    state["db_path"] = DB_PATH
    state["trace_dir"] = tmp_path / "traces"

    result = run_report_supervisor_agent(
        state,
        report_dir=tmp_path / "markdown",
        chart_dir=tmp_path / "charts",
    )

    assert result["status"] == "business_review_report_completed"
    assert result["report_type"] == "monthly_business_report"
    assert result["weekly_report_path"].endswith("run_monthly_report_test_monthly_business_report.md")
    report_text = Path(result["weekly_report_path"]).read_text(encoding="utf-8")
    assert "# 本月电商经营分析月报" in report_text
    assert "下月建议" in report_text
