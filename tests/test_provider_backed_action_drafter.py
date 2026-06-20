import sqlite3


class _SequenceProvider:
    model = "mock-sequence"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _base_state(tmp_path):
    from agents.action_planner import run_action_planner_agent
    from agents.supervisor import initialize_run

    state = initialize_run(
        "找出最近销售额下降最多的品类，并为运营团队创建跟进任务、监控告警和邮件草稿。",
        run_id="run_action_drafter_test",
        session_id="session_action_drafter_test",
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
    return run_action_planner_agent(state)


def test_action_drafter_uses_provider_output_before_risk_and_approval(tmp_path):
    from agents.action_drafter import run_action_drafter_agent
    from agents.risk_assessor import run_risk_assessor_agent
    from llm_ops.provider import MockLLMProvider

    state = _base_state(tmp_path)
    drafted = run_action_drafter_agent(
        state,
        provider=MockLLMProvider(
            {
                "actions": [
                    {
                        "action_id": "action_follow_up_task",
                        "action_type": "create_task",
                        "title": "复盘 Cameras GMV 下滑",
                        "description": "请运营团队复查：Cameras 的 GMV 变化为 -12000.0。",
                        "owner": "运营团队",
                        "priority": "high",
                        "source_claims": ["Cameras 的 GMV 变化为 -12000.0"],
                    },
                    {
                        "action_id": "action_metric_alert",
                        "action_type": "create_metric_alert",
                        "metric_name": "category_gmv_change",
                        "condition": "below",
                        "threshold": "-10%",
                        "description": "监控 Cameras GMV 下滑。",
                        "source_claims": ["Cameras 的 GMV 变化为 -12000.0"],
                    },
                    {
                        "action_id": "action_email_draft",
                        "action_type": "create_email_draft",
                        "recipient": "ops@example.com",
                        "subject": "Cameras GMV 下滑复盘",
                        "body": "Cameras 的 GMV 变化为 -12000.0，请复查广告流量和转化率。",
                        "source_claims": [
                            "Cameras 的 GMV 变化为 -12000.0",
                            "可能需要进一步验证广告流量和转化率数据。",
                        ],
                    },
                ],
                "risk_flags": [],
            }
        ),
    )

    assert drafted["action_draft_result"]["source"] == "provider"
    assert drafted["action_draft_result"]["provider_called"] is True
    assert drafted["action_draft_result"]["fallback_used"] is False
    assert "created_actions" not in drafted
    assert drafted.get("approval_status", "") == ""
    action_types = {action["action_type"] for action in drafted["action_plan"]["actions"]}
    assert "create_email_draft" in action_types
    assert "库存不足" not in str(drafted["action_plan"])

    assessed = run_risk_assessor_agent(drafted)
    assert assessed["approval_status"] == "waiting_for_approval"
    assert all(action["requires_approval"] is True for action in assessed["risk_assessment"]["actions"])
    assert assessed["trace"][-2]["node"] == "action_drafter_agent"


def test_action_drafter_rejects_approval_bypass_and_unsupported_claims(tmp_path):
    from agents.action_drafter import run_action_drafter_agent
    from llm_ops.provider import MockLLMProvider

    state = _base_state(tmp_path)
    drafted = run_action_drafter_agent(
        state,
        provider=MockLLMProvider(
            {
                "actions": [
                    {
                        "action_id": "bad_action",
                        "action_type": "create_task",
                        "title": "直接补库存",
                        "description": "库存不足是确定原因，立即补库存。",
                        "owner": "运营团队",
                        "priority": "high",
                        "requires_approval": False,
                        "approval_status": "approved",
                        "source_claims": ["库存不足是确定原因"],
                    }
                ],
                "risk_flags": [],
            }
        ),
    )

    assert drafted["action_draft_result"]["source"] == "deterministic"
    assert drafted["action_draft_result"]["provider_called"] is True
    assert drafted["action_draft_result"]["fallback_used"] is True
    assert drafted["action_draft_result"]["validation_error"]
    assert "bad_action" not in [action["action_id"] for action in drafted["action_plan"]["actions"]]
    assert "库存不足" not in str(drafted["action_plan"])


def test_action_drafter_retries_transient_provider_parse_failure(tmp_path):
    from agents.action_drafter import run_action_drafter_agent

    state = _base_state(tmp_path)
    provider = _SequenceProvider(
        [
            "{not json",
            {
                "actions": [
                    {
                        "action_id": "action_email_draft",
                        "action_type": "create_email_draft",
                        "recipient": "ops@example.com",
                        "subject": "Cameras GMV 下滑复盘",
                        "body": "Cameras 的 GMV 变化为 -12000.0，请复查。",
                        "source_claims": ["Cameras 的 GMV 变化为 -12000.0"],
                    }
                ],
                "risk_flags": [],
            },
        ]
    )

    drafted = run_action_drafter_agent(state, provider=provider)

    assert provider.calls == 2
    assert drafted["action_draft_result"]["source"] == "provider"
    assert drafted["action_draft_result"]["fallback_used"] is False
    assert drafted["action_plan"]["actions"][0]["action_type"] == "create_email_draft"


def test_action_drafter_ignores_top_level_provider_status_metadata(tmp_path):
    from agents.action_drafter import run_action_drafter_agent
    from llm_ops.provider import MockLLMProvider

    state = _base_state(tmp_path)
    drafted = run_action_drafter_agent(
        state,
        provider=MockLLMProvider(
            {
                "status": "drafted",
                "actions": [
                    {
                        "action_id": "action_email_draft",
                        "action_type": "create_email_draft",
                        "recipient": "ops@example.com",
                        "subject": "Cameras GMV 下滑复盘",
                        "body": "Cameras 的 GMV 变化为 -12000.0，请复查。",
                        "source_claims": ["Cameras 的 GMV 变化为 -12000.0"],
                    }
                ],
                "risk_flags": [],
            }
        ),
    )

    assert drafted["action_draft_result"]["source"] == "provider"
    assert drafted["action_draft_result"]["fallback_used"] is False
    assert "status" not in drafted["action_plan"]["actions"][0]


def test_action_planner_runtime_provider_and_no_key_baseline(tmp_path, monkeypatch):
    from agents.action_planner import run_action_planner_agent
    from agents.risk_assessor import run_action_executor_agent, run_risk_assessor_agent
    from agents.supervisor import initialize_run
    from llm_ops.provider import MockLLMProvider

    state = initialize_run("请创建运营跟进任务和邮件草稿。", run_id="run_action_draft_runtime")
    state["action_db_path"] = tmp_path / "action_ops.db"
    state["evidence_result"] = _base_state(tmp_path)["evidence_result"]

    planned = run_action_planner_agent(
        state,
        action_draft_provider=MockLLMProvider(
            {
                "actions": [
                    {
                        "action_id": "action_email_draft",
                        "action_type": "create_email_draft",
                        "recipient": "ops@example.com",
                        "subject": "Cameras GMV 下滑复盘",
                        "body": "Cameras 的 GMV 变化为 -12000.0，请复查。",
                        "source_claims": ["Cameras 的 GMV 变化为 -12000.0"],
                    }
                ],
                "risk_flags": [],
            }
        ),
    )
    assessed = run_risk_assessor_agent(planned)
    blocked = run_action_executor_agent(assessed)

    assert planned["action_draft_result"]["source"] == "provider"
    assert assessed["approval_status"] == "waiting_for_approval"
    assert blocked["created_actions"] == []
    with sqlite3.connect(state["action_db_path"]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM email_drafts").fetchone()[0] == 0

    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_ACTION_DRAFTER", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    fallback_state = initialize_run("请创建运营跟进任务。", run_id="run_action_draft_no_key")
    fallback_state["action_db_path"] = tmp_path / "fallback_action_ops.db"
    fallback_state["evidence_result"] = _base_state(tmp_path)["evidence_result"]
    fallback = run_action_planner_agent(fallback_state)

    assert fallback["action_draft_result"]["source"] == "deterministic"
    assert fallback["action_draft_result"]["provider_called"] is False
    assert fallback["status"] == "action_plan_created"
