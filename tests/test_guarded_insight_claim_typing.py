from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def _executed_state():
    from agents.supervisor import initialize_run
    from tools.sql_executor import run_sql

    sql = """
SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE o.status = 'paid'
GROUP BY p.product_name
ORDER BY gmv DESC
LIMIT 1
""".strip()
    state = initialize_run(
        "最近 30 天销售额最高的商品是什么？",
        run_id="run_claim_typing_test",
        session_id="session_claim_typing_test",
    )
    state["db_path"] = DB_PATH
    state["generated_sql"] = sql
    state["execution_result"] = run_sql(DB_PATH, sql)
    product, gmv = state["execution_result"]["rows"][0]
    state["final_answer"] = f"{product} 的 GMV 为 {gmv}"
    state["business_context"] = {"matched_rules": [{"title": "GMV", "content": "GMV uses paid orders."}]}
    state["metric_context"] = {"metric_name": "gmv"}
    return state, product, gmv


def test_claim_typer_uses_provider_types_but_evidence_validator_decides():
    from agents.insight_claim_typer import run_insight_claim_typer_agent
    from llm_ops.provider import MockLLMProvider

    state, product, gmv = _executed_state()
    result = run_insight_claim_typer_agent(
        state,
        provider=MockLLMProvider(
            {
                "typed_claims": [
                    {
                        "claim": f"{product} 的 GMV 为 {gmv}",
                        "claim_type": "data_supported_finding",
                        "rationale": "Matches the SQL result.",
                    },
                    {
                        "claim": "可能需要进一步验证广告流量变化。",
                        "claim_type": "hypothesis",
                        "rationale": "Traffic data is unavailable.",
                    },
                    {
                        "claim": "库存不足是导致销量下降的主要原因",
                        "claim_type": "unsupported",
                        "rationale": "No inventory evidence.",
                    },
                ],
                "risk_flags": [],
            }
        ),
    )

    typing = result["claim_typing_result"]
    assert typing["source"] == "provider"
    assert typing["provider_called"] is True
    assert typing["fallback_used"] is False
    assert typing["typed_claims"][0]["claim_type"] == "data_supported_finding"
    assert any(product in item["claim"] for item in typing["evidence_result"]["data_supported_findings"])
    assert typing["evidence_result"]["unsupported_claims_blocked"] == ["库存不足是导致销量下降的主要原因"]
    assert "库存不足" not in typing["guarded_summary"]
    assert result["trace"][-1]["node"] == "insight_claim_typer_agent"
    assert result["trace"][-1]["tool_name"] == "provider_insight_claim_typer"


def test_claim_typer_falls_back_on_schema_mismatch_without_crashing():
    from agents.insight_claim_typer import run_insight_claim_typer_agent
    from llm_ops.provider import MockLLMProvider

    state, product, gmv = _executed_state()
    state["claims_to_validate"] = [f"{product} 的 GMV 为 {gmv}"]

    result = run_insight_claim_typer_agent(
        state,
        provider=MockLLMProvider({"typed_claims": [{"claim": f"{product} 的 GMV 为 {gmv}", "claim_type": "certain"}]}),
    )

    typing = result["claim_typing_result"]
    assert typing["source"] == "deterministic"
    assert typing["provider_called"] is True
    assert typing["fallback_used"] is True
    assert typing["validation_error"]
    assert any(product in item["claim"] for item in typing["evidence_result"]["data_supported_findings"])


def test_workflow_runs_provider_claim_typing_after_insight(tmp_path):
    from graph.workflow import run_workflow
    from llm_ops.provider import MockLLMProvider

    result = run_workflow(
        "最近 30 天销售额最高的 5 个商品为什么值得复盘？",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_workflow_claim_typing",
        session_id="session_workflow_claim_typing",
        claim_typing_provider=MockLLMProvider(
            {
                "typed_claims": [
                    {
                        "claim": "可能需要进一步验证广告流量变化。",
                        "claim_type": "hypothesis",
                        "rationale": "Traffic data is unavailable.",
                    }
                ],
                "risk_flags": [],
            }
        ),
    )

    assert result["status"] == "completed"
    assert result["claim_typing_result"]["provider_called"] is True
    assert result["claim_typing_result"]["source"] == "provider"
    assert any(event["node"] == "insight_claim_typer_agent" for event in result["trace"])
    assert "claim_typing_result" in result
