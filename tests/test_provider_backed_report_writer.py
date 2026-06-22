from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def _report_state():
    from agents.supervisor import initialize_run

    state = initialize_run(
        "最近 30 天销售额最高的 5 个商品是什么？",
        run_id="run_provider_report_writer",
        session_id="session_provider_report_writer",
    )
    state["selected_metrics"] = ["gmv"]
    state["business_context"] = {"context_summary": "GMV uses paid orders only."}
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
                "claim": "可能需要进一步验证广告流量变化",
                "reason": "Current database lacks traffic data.",
                "needs_more_data": ["ad_impressions", "ctr"],
            }
        ],
        "unsupported_claims_blocked": ["库存不足是导致销量下降的主要原因"],
    }
    state["chart_paths"] = ["reports/charts/run_provider_report_writer_bar_product_name_gmv.png"]
    state["trace_path"] = "logs/traces/run_provider_report_writer.json"
    return state


def test_report_writer_uses_provider_output_and_rejects_unsupported_claims():
    from agents.report_writer import run_report_writer_agent
    from llm_ops.provider import MockLLMProvider

    valid = run_report_writer_agent(
        _report_state(),
        provider=MockLLMProvider(
            {
                "executive_summary": ["Laptop Pro 14 是当前 GMV 最高的商品。"],
                "business_narrative": "Laptop Pro 14 的 GMV 为 511248.56，可作为本次复盘重点。",
                "next_steps": ["继续跟踪广告流量变化。"],
                "used_supported_claims": ["Laptop Pro 14 的 GMV 为 511248.56"],
                "used_hypotheses": ["可能需要进一步验证广告流量变化"],
                "unsupported_claims": [],
            }
        ),
    )

    assert valid["report_writer_result"]["source"] == "provider"
    assert valid["report_writer_result"]["provider_called"] is True
    assert valid["report_writer_result"]["fallback_used"] is False
    assert "Laptop Pro 14" in valid["report_writer_result"]["business_narrative"]
    assert "库存不足" not in valid["report_writer_result"]["business_narrative"]
    assert valid["trace"][-1]["node"] == "report_writer_agent"
    assert valid["trace"][-1]["tool_name"] == "provider_report_writer"

    rejected = run_report_writer_agent(
        _report_state(),
        provider=MockLLMProvider(
            {
                "executive_summary": ["库存不足是导致销量下降的主要原因。"],
                "business_narrative": "库存不足是导致销量下降的主要原因。",
                "next_steps": ["立刻补库存。"],
                "used_supported_claims": [],
                "used_hypotheses": [],
                "unsupported_claims": ["库存不足是导致销量下降的主要原因"],
            }
        ),
    )

    assert rejected["report_writer_result"]["source"] == "deterministic"
    assert rejected["report_writer_result"]["provider_called"] is True
    assert rejected["report_writer_result"]["fallback_used"] is True
    assert rejected["report_writer_result"]["validation_error"]
    assert "库存不足" not in rejected["report_writer_result"]["business_narrative"]


def test_report_agent_writes_provider_polished_sections_after_evidence_validation(tmp_path):
    from agents.report_agent import run_report_agent
    from llm_ops.provider import MockLLMProvider

    state = run_report_agent(
        _report_state(),
        output_dir=tmp_path,
        report_writer_provider=MockLLMProvider(
            {
                "executive_summary": ["Laptop Pro 14 是当前 GMV 最高的商品。"],
                "business_narrative": "Laptop Pro 14 的 GMV 为 511248.56，建议作为商品复盘重点。",
                "next_steps": ["验证广告流量和转化率变化。"],
                "used_supported_claims": ["Laptop Pro 14 的 GMV 为 511248.56"],
                "used_hypotheses": ["可能需要进一步验证广告流量变化"],
                "unsupported_claims": [],
            }
        ),
    )

    report_text = Path(state["report_path"]).read_text(encoding="utf-8")
    assert state["report_writer_result"]["source"] == "provider"
    assert "## LLM 辅助报告表达" in report_text
    assert "Laptop Pro 14 的 GMV 为 511248.56" in report_text
    assert "库存不足是导致销量下降的主要原因" not in report_text


def test_report_supervisor_uses_runtime_report_writer_provider_and_preserves_no_key_baseline(tmp_path, monkeypatch):
    from agents.report_supervisor import plan_business_review_sections, run_report_supervisor_agent
    from agents.supervisor import initialize_run
    from llm_ops.provider import MockLLMProvider

    state = initialize_run(
        "帮我生成本月经营复盘，重点看 GMV 和 Top 商品。",
        run_id="run_supervisor_report_writer",
        session_id="session_supervisor_report_writer",
    )
    state["db_path"] = DB_PATH
    state["trace_dir"] = tmp_path / "traces"
    state["report_sections"] = plan_business_review_sections(state["user_question"])

    result = run_report_supervisor_agent(
        state,
        report_writer_provider=MockLLMProvider(
            {
                "executive_summary": ["本月已完成经营复盘，Top 商品表现突出。"],
                "business_narrative": "报告内容基于已验证 SQL 结果生成，建议关注 Top 商品表现。",
                "next_steps": ["围绕 Top 商品复盘投放与转化。"],
                "used_supported_claims": [],
                "used_hypotheses": [],
                "unsupported_claims": [],
            }
        ),
        report_dir=tmp_path / "markdown",
        chart_dir=tmp_path / "charts",
    )

    assert result["report_writer_result"]["provider_called"] is True
    assert result["report_writer_result"]["source"] == "provider"
    assert result["status"] == "business_review_report_completed"
    assert "LLM 辅助报告表达" in Path(result["weekly_report_path"]).read_text(encoding="utf-8")

    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_REPORT_WRITER", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    fallback_state = initialize_run(
        "帮我生成本月经营复盘。",
        run_id="run_no_key_report_writer",
        session_id="session_no_key_report_writer",
    )
    fallback_state["db_path"] = DB_PATH
    fallback_state["trace_dir"] = tmp_path / "fallback_traces"
    fallback_state["report_sections"] = plan_business_review_sections(fallback_state["user_question"])

    fallback = run_report_supervisor_agent(
        fallback_state,
        report_dir=tmp_path / "fallback_markdown",
        chart_dir=tmp_path / "fallback_charts",
    )

    assert fallback["report_writer_result"]["source"] == "deterministic"
    assert fallback["report_writer_result"]["provider_called"] is False
    assert fallback["status"] == "business_review_report_completed"
