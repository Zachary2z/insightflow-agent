import sqlite3

import pytest


def test_live_deepseek_action_drafter_enters_action_workflow_before_approval(tmp_path):
    from agents.action_planner import run_action_planner_agent
    from agents.risk_assessor import run_action_executor_agent, run_risk_assessor_agent
    from agents.supervisor import initialize_run
    from llm_ops.deepseek_provider import load_deepseek_config
    from llm_ops.runtime_provider import provider_action_drafter_enabled

    config = load_deepseek_config(require_api_key=True)
    if not config.live_tests_enabled or not config.success or not provider_action_drafter_enabled():
        pytest.skip(
            "Set INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 and "
            "INSIGHTFLOW_USE_PROVIDER_ACTION_DRAFTER=1 with DEEPSEEK_API_KEY to run this live workflow test."
        )

    db_path = tmp_path / "action_ops.db"
    state = initialize_run(
        "请基于 Cameras GMV 下滑创建运营跟进任务、监控告警和邮件草稿。",
        run_id="run_live_deepseek_action_drafter",
        session_id="session_live_deepseek_action_drafter",
    )
    state["action_db_path"] = db_path
    state["evidence_result"] = {
        "success": True,
        "data_supported_findings": [
            {
                "claim": "Cameras 的 GMV 变化为 -12000.0",
                "evidence": "SQL result row: category_name=Cameras, gmv_change=-12000.0",
                "confidence": 0.95,
            }
        ],
        "hypotheses": [
            {
                "claim": "可能需要进一步验证广告流量和转化率数据。",
                "reason": "Needs marketing data.",
                "needs_more_data": ["ad_impressions", "conversion_rate"],
            }
        ],
        "unsupported_claims_blocked": ["库存不足是确定原因"],
    }

    planned = run_action_planner_agent(state)
    assessed = run_risk_assessor_agent(planned)
    blocked = run_action_executor_agent(assessed)

    assert planned["action_draft_result"]["provider_called"] is True
    assert planned["action_draft_result"]["source"] == "provider"
    assert planned["action_draft_result"]["fallback_used"] is False
    assert assessed["approval_status"] == "waiting_for_approval"
    assert blocked["created_actions"] == []
    assert any(
        event.get("node") == "action_drafter_agent"
        and event.get("tool_name") == "provider_action_drafter"
        for event in blocked["trace"]
    )
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM metric_alerts").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM email_drafts").fetchone()[0] == 0
