import json
import sqlite3
from pathlib import Path


def _base_state(tmp_path):
    from agents.supervisor import initialize_run

    state = initialize_run(
        "找出最近销售额下降最多的品类，并为运营团队创建跟进任务和监控告警。",
        run_id="run_action_workflow_test",
        session_id="session_action_workflow_test",
    )
    state["action_db_path"] = tmp_path / "action_ops.db"
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
    return state


def _fixture_action_plan():
    return {
        "success": True,
        "plan_type": "business_action_plan",
        "source": "test_fixture",
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
                "action_id": "action_metric_alert",
                "action_type": "create_metric_alert",
                "metric_name": "category_gmv_change",
                "condition": "below",
                "threshold": "-10%",
                "description": "监控 Cameras GMV 下滑。",
                "delivery_tool_id": "local_sqlite",
                "source_claims": ["Cameras 的 GMV 变化为 -12000.0"],
            },
        ],
    }


def _base_state_with_action_plan(tmp_path):
    state = _base_state(tmp_path)
    state["action_plan"] = _fixture_action_plan()
    return state


def test_action_tools_write_tasks_alerts_approvals_and_audit_logs(tmp_path):
    from tools.action_tool import create_metric_alert, create_task, verify_action_execution
    from tools.approval_tool import record_approval
    from tools.audit_logger import log_audit_event

    db_path = tmp_path / "action_ops.db"

    task_result = create_task(
        db_path,
        {
            "run_id": "run_action_tool_test",
            "title": "Follow up declining category",
            "description": "Review Cameras GMV decline.",
            "owner": "运营团队",
            "priority": "high",
        },
    )
    alert_result = create_metric_alert(
        db_path,
        {
            "run_id": "run_action_tool_test",
            "metric_name": "category_gmv_change",
            "threshold": "-10%",
            "condition": "below",
            "description": "Monitor declining category GMV.",
        },
    )
    approval_result = record_approval(
        db_path,
        {
            "run_id": "run_action_tool_test",
            "approval_status": "approved",
            "approved_by": "ops_manager",
            "reason": "Approved for follow-up.",
        },
    )
    audit_result = log_audit_event(
        db_path,
        {
            "run_id": "run_action_tool_test",
            "event_type": "action_execution",
            "actor": "system",
            "payload": {"task_id": task_result["task_id"], "alert_id": alert_result["alert_id"]},
        },
    )
    verification = verify_action_execution(
        db_path,
        [
            {"action_type": "create_task", "record_id": task_result["task_id"]},
            {"action_type": "create_metric_alert", "record_id": alert_result["alert_id"]},
        ],
    )

    assert task_result["success"] is True
    assert alert_result["success"] is True
    assert approval_result["success"] is True
    assert audit_result["success"] is True
    assert verification["success"] is True
    assert len(verification["verified_actions"]) == 2

    with sqlite3.connect(db_path) as conn:
        task_row = conn.execute("SELECT title, owner, status FROM tasks").fetchone()
        alert_row = conn.execute("SELECT metric_name, condition, status FROM metric_alerts").fetchone()
        approval_row = conn.execute("SELECT approval_status, approved_by FROM approvals").fetchone()
        audit_row = conn.execute("SELECT event_type, payload_json FROM audit_logs").fetchone()

    assert task_row == ("Follow up declining category", "运营团队", "created")
    assert alert_row == ("category_gmv_change", "below", "created")
    assert approval_row == ("approved", "ops_manager")
    assert json.loads(audit_row[1])["task_id"] == task_result["task_id"]


def test_action_planner_and_risk_assessor_require_approval(tmp_path):
    from agents.action_planner import run_action_planner_agent
    from agents.risk_assessor import run_risk_assessor_agent

    state = run_action_planner_agent(_base_state_with_action_plan(tmp_path))
    state = run_risk_assessor_agent(state)

    assert state["action_plan"]["success"] is True
    assert len(state["action_plan"]["actions"]) >= 2
    action_types = {action["action_type"] for action in state["action_plan"]["actions"]}
    assert {"create_task", "create_metric_alert"} <= action_types
    assert state["risk_assessment"]["requires_approval"] is True
    assert state["approval_status"] == "waiting_for_approval"
    assert all(action["requires_approval"] is True for action in state["risk_assessment"]["actions"])
    assert state["trace"][-1]["node"] == "risk_assessor_agent"


def test_approval_gate_blocks_unapproved_actions_and_audits(tmp_path):
    from agents.action_planner import run_action_planner_agent
    from agents.action_executor import run_action_executor_agent
    from agents.risk_assessor import run_risk_assessor_agent

    state = run_risk_assessor_agent(run_action_planner_agent(_base_state_with_action_plan(tmp_path)))
    blocked = run_action_executor_agent(state)

    assert blocked["status"] == "waiting_for_approval"
    assert blocked["created_actions"] == []
    assert blocked["action_execution_result"]["success"] is False
    assert "approval required" in blocked["action_execution_result"]["error"]
    assert blocked["audit_log_result"]["success"] is True

    with sqlite3.connect(state["action_db_path"]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM metric_alerts").fetchone()[0] == 0
        assert conn.execute("SELECT event_type FROM audit_logs").fetchone()[0] == "approval_blocked"


def test_approved_action_workflow_creates_verifies_and_audits_actions(tmp_path):
    from agents.action_planner import run_action_planner_agent
    from agents.action_executor import run_action_executor_agent
    from agents.action_verifier import run_action_verifier_agent
    from agents.risk_assessor import run_risk_assessor_agent
    from tools.approval_tool import record_approval

    state = run_risk_assessor_agent(run_action_planner_agent(_base_state_with_action_plan(tmp_path)))
    approval = record_approval(
        state["action_db_path"],
        {
            "run_id": state["run_id"],
            "approval_status": "approved",
            "approved_by": "ops_manager",
            "reason": "Approved from test.",
        },
    )
    state["approval_status"] = approval["approval_status"]
    state["approval_record"] = approval

    state = run_action_executor_agent(state)
    state = run_action_verifier_agent(state)

    assert state["status"] == "actions_verified"
    assert state["action_execution_result"]["success"] is True
    assert len(state["created_actions"]) >= 2
    assert state["action_verification_result"]["success"] is True
    assert len(state["action_verification_result"]["verified_actions"]) == len(state["created_actions"])
    assert state["audit_log_result"]["success"] is True

    with sqlite3.connect(state["action_db_path"]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] >= 1
        assert conn.execute("SELECT COUNT(*) FROM metric_alerts").fetchone()[0] >= 1
        audit_events = [row[0] for row in conn.execute("SELECT event_type FROM audit_logs").fetchall()]

    assert "action_execution" in audit_events
    assert state["trace"][-1]["node"] == "action_verifier_agent"
