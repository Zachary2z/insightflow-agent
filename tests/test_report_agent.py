from pathlib import Path


def _base_state():
    from agents.supervisor import initialize_run

    state = initialize_run(
        "最近 30 天销售额最高的 5 个商品是什么？",
        run_id="run_report_agent_test",
        session_id="session_report_agent_test",
    )
    state["selected_metrics"] = ["gmv", "product_sales"]
    state["business_context"] = {"context_summary": "Matched paid-order GMV business context."}
    state["generated_sql"] = "SELECT product_name, gmv FROM product_gmv ORDER BY gmv DESC LIMIT 5"
    state["execution_result"] = {
        "success": True,
        "columns": ["product_name", "gmv"],
        "rows": [["Laptop Pro 14", 511248.56], ["Camera A", 456050.99]],
        "row_count": 2,
    }
    state["evidence_result"] = {
        "success": True,
        "data_supported_findings": [
            {
                "claim": "Laptop Pro 14 的 GMV 为 511248.56",
                "evidence": "SQL result row: product_name=Laptop Pro 14, gmv=511248.56",
                "confidence": 0.95,
            }
        ],
        "hypotheses": [
            {
                "claim": "可能与广告流量下降有关",
                "reason": "Current database lacks traffic data.",
                "needs_more_data": ["ad_impressions", "ctr"],
            }
        ],
        "unsupported_claims_blocked": ["库存不足是导致销量下降的主要原因"],
    }
    state["chart_paths"] = ["reports/charts/run_report_agent_test_bar_product_name_gmv.png"]
    state["trace_path"] = "logs/traces/run_report_agent_test.json"
    return state


def test_report_agent_saves_traceable_markdown_report(tmp_path):
    from agents.report_agent import run_report_agent

    state = run_report_agent(_base_state(), output_dir=tmp_path)

    report_path = Path(state["report_path"])
    report_text = report_path.read_text(encoding="utf-8")
    assert state["report_result"]["success"] is True
    assert report_path.exists()
    assert "# InsightFlow Analysis Report" in report_text
    assert "## 用户问题" in report_text
    assert "最近 30 天销售额最高的 5 个商品是什么？" in report_text
    assert "## 使用的业务指标" in report_text
    assert "gmv" in report_text
    assert "## 执行 SQL" in report_text
    assert "SELECT product_name, gmv" in report_text
    assert "## 查询结果摘要" in report_text
    assert "Laptop Pro 14" in report_text
    assert "## 数据支持结论" in report_text
    assert "SQL result row" in report_text
    assert "## 需要进一步验证的假设" in report_text
    assert "ad_impressions" in report_text
    assert "## 图表路径" in report_text
    assert "reports/charts/run_report_agent_test_bar_product_name_gmv.png" in report_text
    assert "## Trace 路径" in report_text
    assert "logs/traces/run_report_agent_test.json" in report_text
    assert "库存不足是导致销量下降的主要原因" not in report_text
    assert state["trace"][-1]["node"] == "report_agent"
    assert state["trace"][-1]["tool_name"] == "save_report"


def test_report_agent_handles_missing_execution_result_without_crashing(tmp_path):
    from agents.report_agent import run_report_agent
    from agents.supervisor import initialize_run

    state = initialize_run("最近 30 天销售额最高的 5 个商品是什么？")

    state = run_report_agent(state, output_dir=tmp_path)

    assert state["report_result"]["success"] is False
    assert "execution_result is required" in state["report_result"]["error"]
    assert state["report_path"] == ""
    assert state["report_warning"] == state["report_result"]["error"]
    assert state["trace"][-1]["node"] == "report_agent"
    assert state["trace"][-1]["status"] == "error"
