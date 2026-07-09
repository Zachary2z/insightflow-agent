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


def test_evidence_auditor_exposes_no_claim_typing_provider_parameter():
    import inspect

    from workspaces.evidence_auditor import audit_question_evidence, run_evidence_auditor_agent

    assert "provider" not in inspect.signature(audit_question_evidence).parameters
    assert "provider" not in inspect.signature(run_evidence_auditor_agent).parameters


def test_workflow_uses_deterministic_evidence_auditor_without_provider_claim_typing(tmp_path):
    from graph.workflow import run_workflow

    result = run_workflow(
        "最近 30 天销售额最高的 5 个商品为什么值得复盘？",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_workflow_claim_typing",
        session_id="session_workflow_claim_typing",
    )

    assert result["status"] == "completed"
    assert "claim_typing_result" not in result
    assert result["audit_result"]["supported_facts"]
    assert any(event["node"] == "evidence_auditor_agent" for event in result["trace"])
    assert not any(event["node"] == "insight_claim_typer_agent" for event in result["trace"])


def _auditor_state_without_typed_claims():
    return {
        "user_question": "Which entity should we prioritize?",
        "analysis_task": {
            "resolved_question": "Which entity should we prioritize?",
            "metrics": ["score_value"],
            "dimensions": ["entity_name"],
        },
        "execution_result": {
            "success": True,
            "columns": ["entity_name", "score_value"],
            "rows": [["Alpha", 91.0], ["Beta", 83.0]],
            "row_count": 2,
        },
        "question_evidence_pack": {
            "task": {"resolved_question": "Which entity should we prioritize?"},
            "columns": ["entity_name", "score_value"],
            "rows": [
                {"entity_name": "Alpha", "score_value": 91.0},
                {"entity_name": "Beta", "score_value": 83.0},
            ],
            "metrics": ["score_value"],
            "data_limits": ["Current evidence only covers the returned comparison rows."],
            "tool_calls": [],
        },
        "business_answer": {
            "headline": "Alpha is the supported priority",
            "direct_answer": "Prioritize Alpha because score_value is 91.0.",
            "why": "The result rows show Alpha at 91.0 versus Beta at 83.0.",
            "evidence_bullets": ["Alpha score_value is 91.0.", "Beta score_value is 83.0."],
            "recommendations": ["Use Alpha as the next review focus."],
            "caveats": ["Current evidence only covers the returned comparison rows."],
            "confidence": "medium",
        },
        "trace": [],
    }


def test_evidence_auditor_rebuilds_untyped_claims_without_provider_claim_typing():
    from workspaces.evidence_auditor import run_evidence_auditor_agent

    result = run_evidence_auditor_agent(_auditor_state_without_typed_claims())

    audit = result["audit_result"]
    assert "claim_typing_result" not in result
    assert audit["supported_facts"]
    assert audit["unsupported_claims"] == []
    assert audit["data_limits"]
    assert result["trace"][-1]["node"] == "evidence_auditor_agent"
    assert result["trace"][-1]["tool_name"] == "validate_evidence"
    assert result["trace"][-1]["provider_called"] is False


def test_evidence_auditor_filters_generic_caveats_when_rebuilding_untyped_data_limits():
    from workspaces.evidence_auditor import run_evidence_auditor_agent

    state = _auditor_state_without_typed_claims()
    state["question_evidence_pack"]["data_limits"] = [
        "Current evidence only covers the returned comparison rows."
    ]
    state["business_answer"]["caveats"] = [
        "The answer was rebuilt from the returned data and is limited to this query scope.",
        "Use the current query result as context for the next review.",
        "Missing ROI data limits budget validation.",
    ]

    result = run_evidence_auditor_agent(state)
    data_limits = result["audit_result"]["data_limits"]

    assert "Current evidence only covers the returned comparison rows." in data_limits
    assert "Missing ROI data limits budget validation." in data_limits
    assert "The answer was rebuilt from the returned data and is limited to this query scope." not in data_limits
    assert "Use the current query result as context for the next review." not in data_limits


def test_evidence_auditor_keeps_typed_data_limit_claims_and_pack_limits():
    from workspaces.evidence_auditor import run_evidence_auditor_agent

    state = _auditor_state_without_typed_claims()
    state["business_answer"]["caveats"] = [
        "The answer was rebuilt from the returned data and is limited to this query scope."
    ]
    state["candidate_claims_typed"] = [
        {"claim": "Alpha score_value is 91.0.", "category": "hard_fact"},
        {
            "claim": "Missing ROI data limits budget validation.",
            "category": "data_limit",
        },
        {"claim": "Use Alpha as the next review focus.", "category": "recommendation"},
    ]

    result = run_evidence_auditor_agent(state)
    audit = result["audit_result"]

    assert "Current evidence only covers the returned comparison rows." in audit["data_limits"]
    assert "Missing ROI data limits budget validation." in audit["data_limits"]
    assert "The answer was rebuilt from the returned data and is limited to this query scope." not in audit["data_limits"]
    assert any("next review focus" in claim for claim in audit["reasonable_inferences"])


def test_evidence_auditor_checks_typed_hard_facts_strictly_and_keeps_inferences_reasonable():
    from workspaces.evidence_auditor import run_evidence_auditor_agent

    state = _auditor_state_without_typed_claims()
    state["candidate_claims_typed"] = [
        {"claim": "Alpha score_value is 91.0.", "category": "hard_fact"},
        {"claim": "Gamma score_value is 91.0.", "category": "hard_fact"},
        {
            "claim": "Alpha should be the next review focus because it leads the returned comparison.",
            "category": "recommendation",
        },
        {
            "claim": "Alpha may have stronger operating quality, but that requires follow-up validation.",
            "category": "business_inference",
        },
    ]

    result = run_evidence_auditor_agent(state)
    audit = result["audit_result"]

    assert any("Alpha score_value is 91.0" in claim for claim in audit["supported_facts"])
    assert "Gamma score_value is 91.0." in audit["unsupported_claims"]
    assert all("Gamma" not in claim for claim in audit["supported_facts"])
    assert any("next review focus" in claim for claim in audit["reasonable_inferences"])
    assert any("stronger operating quality" in claim for claim in audit["reasonable_inferences"])
    assert audit["confidence"] in {"medium", "low"}


def test_evidence_auditor_checks_hard_facts_against_question_ledger_first():
    from workspaces.evidence_auditor import run_evidence_auditor_agent

    state = _auditor_state_without_typed_claims()
    state["question_evidence_pack"]["rows"] = [
        {"entity_name": "Alpha", "score_value": 91.0},
        {"entity_name": "Gamma", "score_value": 91.0},
    ]
    state["question_evidence_ledger"] = {
        "ledger_id": "qledger_audit",
        "facts": [
            {
                "fact_id": "fact_1",
                "label": "score_value",
                "value": 91.0,
                "unit": "",
                "dimension": {"entity_name": "Alpha"},
                "source_columns": ["entity_name", "score_value"],
                "source_row_refs": ["row:0"],
                "evidence_ref": "evidence:row:0:score_value",
            }
        ],
        "derived_metrics": [],
        "data_limits": ["Current evidence ledger only certifies Alpha for this turn."],
        "evidence_refs": ["evidence:row:0:score_value"],
        "confidence": "medium",
    }
    state["candidate_claims_typed"] = [
        {"claim": "Alpha score_value is 91.0.", "category": "hard_fact"},
        {"claim": "Gamma score_value is 91.0.", "category": "hard_fact"},
        {"claim": "Alpha should be the next review focus.", "category": "recommendation"},
    ]

    result = run_evidence_auditor_agent(state)
    audit = result["audit_result"]

    assert any("Alpha score_value is 91.0" in fact for fact in audit["supported_facts"])
    assert "Gamma score_value is 91.0." in audit["unsupported_claims"]
    assert any("next review focus" in claim for claim in audit["reasonable_inferences"])
    assert "Current evidence ledger only certifies Alpha for this turn." in audit["data_limits"]
