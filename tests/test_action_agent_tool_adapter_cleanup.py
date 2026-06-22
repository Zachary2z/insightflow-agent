import sqlite3


def _state(tmp_path):
    from agents.supervisor import initialize_run

    state = initialize_run(
        "基于 Cameras GMV 下滑，创建运营跟进任务、监控告警和邮件草稿。",
        run_id="run_p84_action_cleanup",
        session_id="session_p84_action_cleanup",
    )
    state["action_db_path"] = tmp_path / "action_ops.db"
    state["evidence_result"] = {
        "success": True,
        "data_supported_findings": [
            {"claim": "Cameras 的 GMV 变化为 -12000.0", "confidence": 0.95}
        ],
        "hypotheses": [
            {
                "claim": "可能需要进一步验证广告流量和转化率数据。",
                "needs_more_data": ["ad_impressions", "conversion_rate"],
            }
        ],
        "unsupported_claims_blocked": ["库存不足是确定原因"],
    }
    return state


def _provider_actions():
    return {
        "actions": [
            {
                "action_id": "action_follow_up_task",
                "action_type": "create_task",
                "title": "复盘 Cameras GMV 下滑",
                "description": "请运营团队复查：Cameras 的 GMV 变化为 -12000.0。",
                "owner": "运营团队",
                "priority": "high",
                "delivery_tool_id": "local_sqlite",
                "source_claims": ["Cameras 的 GMV 变化为 -12000.0"],
            },
            {
                "action_id": "action_jira_ticket",
                "action_type": "create_task",
                "title": "Jira: Cameras GMV 下滑复盘",
                "description": "Cameras 的 GMV 变化为 -12000.0，需要跨团队复盘。",
                "owner": "运营团队",
                "priority": "high",
                "delivery_tool_id": "jira_ticket_mock",
                "source_claims": ["Cameras 的 GMV 变化为 -12000.0"],
            },
            {
                "action_id": "action_email_draft",
                "action_type": "create_email_draft",
                "recipient": "ops@example.com",
                "subject": "Cameras GMV 下滑复盘",
                "body": "Cameras 的 GMV 变化为 -12000.0，请复查广告流量和转化率。",
                "delivery_tool_id": "local_sqlite",
                "source_claims": [
                    "Cameras 的 GMV 变化为 -12000.0",
                    "可能需要进一步验证广告流量和转化率数据。",
                ],
            },
        ],
        "risk_flags": [],
    }


def test_action_planner_provider_unavailable_does_not_emit_fixed_templates(tmp_path):
    from agents.action_planner import run_action_planner_agent

    result = run_action_planner_agent(_state(tmp_path))

    assert result["action_plan"]["success"] is False
    assert result["action_plan"]["source"] == "provider_unavailable"
    assert result["action_plan"]["actions"] == []
    assert result["action_draft_result"]["source"] == "provider_unavailable"
    assert result["status"] == "action_plan_provider_unavailable"


def test_action_planner_uses_provider_contextual_actions_without_approval_or_records(tmp_path):
    from agents.action_planner import run_action_planner_agent
    from llm_ops.provider import MockLLMProvider

    result = run_action_planner_agent(_state(tmp_path), action_draft_provider=MockLLMProvider(_provider_actions()))

    assert result["action_plan"]["success"] is True
    assert result["action_plan"]["source"] == "provider"
    assert result["action_draft_result"]["fallback_used"] is False
    assert {action["delivery_tool_id"] for action in result["action_plan"]["actions"]} == {
        "local_sqlite",
        "jira_ticket_mock",
    }
    assert "approval_status" not in result
    assert "created_actions" not in result
    assert not result["action_db_path"].exists()


def test_action_executor_is_split_from_risk_assessor_and_blocks_before_approval(tmp_path):
    import agents.risk_assessor as risk_assessor
    from agents.action_executor import run_action_executor_agent
    from agents.action_planner import run_action_planner_agent
    from agents.risk_assessor import run_risk_assessor_agent
    from llm_ops.provider import MockLLMProvider

    assert not hasattr(risk_assessor, "run_action_executor_agent")

    state = run_action_planner_agent(_state(tmp_path), action_draft_provider=MockLLMProvider(_provider_actions()))
    state = run_risk_assessor_agent(state)
    blocked = run_action_executor_agent(state)

    assert state["trace"][-1]["node"] == "risk_assessor_agent"
    assert blocked["status"] == "waiting_for_approval"
    assert blocked["created_actions"] == []
    assert blocked["action_execution_result"]["success"] is False
    assert "approval required" in blocked["action_execution_result"]["error"]
    assert blocked["audit_log_result"]["success"] is True

    with sqlite3.connect(state["action_db_path"]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
        assert conn.execute("SELECT event_type FROM audit_logs").fetchone()[0] == "approval_blocked"


def test_approved_action_executor_calls_local_and_mock_delivery_adapters(tmp_path):
    from agents.action_executor import run_action_executor_agent
    from agents.action_planner import run_action_planner_agent
    from agents.risk_assessor import run_risk_assessor_agent
    from llm_ops.provider import MockLLMProvider
    from tools.approval_tool import record_approval

    state = run_action_planner_agent(_state(tmp_path), action_draft_provider=MockLLMProvider(_provider_actions()))
    state = run_risk_assessor_agent(state)
    approval = record_approval(
        state["action_db_path"],
        {
            "run_id": state["run_id"],
            "approval_status": "approved",
            "approved_by": "ops_manager",
            "reason": "Approved P8.4 adapter execution.",
        },
    )
    state["approval_status"] = approval["approval_status"]
    state["approval_record"] = approval

    result = run_action_executor_agent(state)

    assert result["status"] == "actions_executed"
    assert result["action_execution_result"]["success"] is True
    assert result["action_execution_result"]["external_tool_called"] is True
    assert any(action["artifact_url"].startswith("mock://jira/") for action in result["created_actions"])
    assert any(action["delivery_tool_id"] == "local_sqlite" for action in result["created_actions"])

    with sqlite3.connect(state["action_db_path"]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM email_drafts").fetchone()[0] == 1
        audit_events = [row[0] for row in conn.execute("SELECT event_type FROM audit_logs").fetchall()]
    assert "action_execution" in audit_events


def test_unknown_action_delivery_tool_is_rejected_without_execution(tmp_path):
    from agents.action_executor import run_action_executor_agent
    from agents.risk_assessor import run_risk_assessor_agent
    from tools.approval_tool import record_approval

    state = _state(tmp_path)
    state["action_plan"] = {
        "success": True,
        "source": "provider",
        "actions": [
            {
                "action_id": "bad_delivery",
                "action_type": "create_task",
                "title": "Bad delivery",
                "description": "Should not execute.",
                "owner": "运营团队",
                "priority": "high",
                "delivery_tool_id": "unknown_tool",
                "source_claims": ["Cameras 的 GMV 变化为 -12000.0"],
            }
        ],
    }
    state = run_risk_assessor_agent(state)
    approval = record_approval(
        state["action_db_path"],
        {
            "run_id": state["run_id"],
            "approval_status": "approved",
            "approved_by": "ops_manager",
            "reason": "Approved for rejection test.",
        },
    )
    state["approval_status"] = approval["approval_status"]

    result = run_action_executor_agent(state)

    assert result["status"] == "action_execution_failed"
    assert result["created_actions"] == []
    assert "Unknown action delivery tool" in result["action_execution_result"]["failed_actions"][0]["error"]
    with sqlite3.connect(state["action_db_path"]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
