def _base_state():
    from agents.supervisor import initialize_run

    state = initialize_run(
        "最近 30 天销售额最高的 5 个商品是什么？",
        run_id="run_evidence_test",
        session_id="session_evidence_test",
    )
    state["execution_result"] = {
        "success": True,
        "columns": ["product_name", "gmv"],
        "rows": [["Laptop Pro 14", 511248.56], ["Camera A", 456050.99]],
        "row_count": 2,
    }
    state["business_context"] = {
        "matched_rules": [
            {
                "title": "paid_orders_define_sales",
                "content": "Sales analysis must use paid orders only. Required SQL filter: orders.status = 'paid'",
            }
        ]
    }
    return state


def test_evidence_validator_agent_writes_result_and_trace():
    from agents.evidence_validator import run_evidence_validator_agent

    state = _base_state()
    state["claims_to_validate"] = [
        "Laptop Pro 14 的 GMV 为 511248.56",
        "库存不足是导致 Camera A 销量下降的主要原因",
    ]

    state = run_evidence_validator_agent(state)

    assert state["evidence_result"]["success"] is True
    assert len(state["evidence_result"]["data_supported_findings"]) == 1
    assert state["evidence_result"]["unsupported_claims_blocked"] == ["库存不足是导致 Camera A 销量下降的主要原因"]
    assert state["trace"][-1]["node"] == "evidence_validator_agent"
    assert state["trace"][-1]["tool_name"] == "validate_evidence"
    assert state["trace"][-1]["status"] == "success"


def test_evidence_validator_agent_can_validate_final_answer_lines():
    from agents.evidence_validator import run_evidence_validator_agent

    state = _base_state()
    state["final_answer"] = """
基于 execution_result，问题结果如下：
1. product_name=Laptop Pro 14, gmv=511248.56
2. 库存不足是导致 Camera A 销量下降的主要原因
"""

    state = run_evidence_validator_agent(state)

    assert state["evidence_result"]["success"] is True
    assert any("Laptop Pro 14" in item["claim"] for item in state["evidence_result"]["data_supported_findings"])
    assert state["evidence_result"]["unsupported_claims_blocked"] == ["库存不足是导致 Camera A 销量下降的主要原因"]


def test_evidence_validator_agent_handles_failure_without_crashing():
    from agents.evidence_validator import run_evidence_validator_agent

    state = _base_state()
    state["claims_to_validate"] = []
    state["final_answer"] = ""

    state = run_evidence_validator_agent(state)

    assert state["evidence_result"]["success"] is False
    assert "claims are required" in state["evidence_result"]["error"]
    assert state["evidence_warning"] == state["evidence_result"]["error"]
    assert state["trace"][-1]["node"] == "evidence_validator_agent"
    assert state["trace"][-1]["status"] == "error"
