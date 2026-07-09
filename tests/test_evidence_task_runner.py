import sqlite3

from llm_ops.provider import MockLLMProvider
from workspaces.analysis_contracts import AnalysisTask
from workspaces.evidence_tasks import EvidenceTask, EvidenceTaskPlan, plan_evidence_tasks
from workspaces.evidence_task_runner import run_evidence_task_plan
from workspaces.profiler import profile_workspace_database
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


class _SequenceProvider:
    model = "mock-sequence"

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("provider called more times than expected")
        return self.responses.pop(0)


def _workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P32 Evidence Task Runner Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE orders (order_date TEXT, channel TEXT, revenue REAL)")
        conn.execute("CREATE TABLE marketing_spend (spend_date TEXT, channel TEXT, spend REAL)")
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?)",
            [
                ("2026-06-01", "私域社群", 180000.0),
                ("2026-06-02", "搜索广告", 120000.0),
                ("2026-06-03", "直播间", 90000.0),
            ],
        )
        conn.executemany(
            "INSERT INTO marketing_spend VALUES (?, ?, ?)",
            [
                ("2026-06-01", "私域社群", 30000.0),
                ("2026-06-02", "搜索广告", 80000.0),
                ("2026-06-03", "直播间", 70000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return workspace


def _lens():
    return {
        "business_domain": "channel_performance",
        "metrics": [
            {
                "label": "收入",
                "source_table": "orders",
                "source_field": "revenue",
                "time_field": "order_date",
                "metric_role": "revenue_like",
            },
            {
                "label": "投放花费",
                "source_table": "marketing_spend",
                "source_field": "spend",
                "time_field": "spend_date",
                "metric_role": "spend_like",
            },
        ],
        "dimensions": [
            {"label": "渠道", "source_table": "orders", "source_field": "channel"},
            {"label": "渠道", "source_table": "marketing_spend", "source_field": "channel"},
        ],
        "time_policy_note": "收入按下单日期统计，投放花费按投放日期统计。",
        "data_limits": [],
    }


def _analysis_task():
    return AnalysisTask(
        resolved_question="按渠道比较收入和投放花费。",
        metrics=["收入", "投放花费"],
        dimensions=["渠道"],
        route_hint="standard_analysis",
        business_lens=_lens(),
    )


def _state(workspace, plan):
    task = _analysis_task()
    task.evidence_task_plan = plan.to_dict()
    return {
        "run_id": "run_p32_tasks",
        "session_id": "session_p32_tasks",
        "user_question": task.resolved_question,
        "original_question": task.resolved_question,
        "db_path": workspace["analysis_db_path"],
        "workspace_id": workspace["workspace_id"],
        "workspace_root": workspace["root_path"],
        "profile_path": workspace["profile_path"],
        "semantic_layer_path": workspace["semantic_layer_path"],
        "data_version": int(workspace.get("data_version") or 1),
        "analysis_task": task.to_dict(),
        "analysis_task_contract": task.to_dict(),
        "analysis_route": {"route": "standard_analysis"},
        "evidence_task_plan": plan.to_dict(),
        "execution_result": {},
        "review_retry_count": 0,
        "retry_count": 0,
        "schema_repair_attempted": False,
        "schema_repair_succeeded": False,
        "schema_repair_reason": "",
        "schema_repair": {},
        "schema_repair_pending_review": False,
        "trace": [],
    }


def test_one_task_runs_through_sql_review_execution_and_validation(tmp_path):
    workspace = _workspace(tmp_path)
    plan = EvidenceTaskPlan(
        route="standard_analysis",
        tasks=[
            EvidenceTask(
                task_id="revenue_by_channel",
                question="按渠道统计收入",
                purpose="core_fact",
                metrics=["收入"],
                dimensions=["渠道"],
            )
        ],
    )

    result = run_evidence_task_plan(_state(workspace, plan))
    tool_names = {call["tool_name"] for call in result["question_evidence_pack"]["tool_calls"]}
    trace_nodes = [event.get("node") for event in result.get("trace") or []]

    assert result["status"] == "executed"
    assert result["execution_result"]["success"] is True
    assert result["evidence_task_results"][0]["status"] == "executed"
    assert {"schema_lookup", "metric_lookup", "sql_review", "sql_execution"}.issubset(tool_names)
    assert "sql_reviewer_agent" in trace_nodes
    assert "sql_executor_node" in trace_nodes
    assert "evidence_validator_agent" in trace_nodes


def test_multiple_tasks_merge_successful_results_into_one_task_aware_ledger(tmp_path):
    workspace = _workspace(tmp_path)
    task = _analysis_task()
    plan = plan_evidence_tasks(task, route="standard_analysis")

    result = run_evidence_task_plan(_state(workspace, plan))
    ledger = result["question_evidence_ledger"]
    task_ids = {item["task_id"] for item in result["evidence_task_results"] if item["status"] == "executed"}

    assert len(task_ids) >= 2
    assert result["execution_result"]["success"] is True
    assert result["question_evidence_pack"]["rows"]
    assert task_ids.issubset({fact["task_id"] for fact in ledger["facts"]})
    assert all(ref.startswith("evidence:") for ref in ledger["evidence_refs"])
    assert ledger["source_pack_id"] == "merged_question_evidence_pack"


def test_failed_non_core_task_adds_data_limit_without_failing_whole_analysis(tmp_path):
    workspace = _workspace(tmp_path)
    plan = EvidenceTaskPlan(
        route="standard_analysis",
        max_parallel_evidence_tasks=1,
        tasks=[
            EvidenceTask(
                task_id="revenue_by_channel",
                question="按渠道统计收入",
                purpose="core_fact",
                metrics=["收入"],
                dimensions=["渠道"],
            ),
            EvidenceTask(
                task_id="unsafe_support",
                question="读取不安全辅助证据",
                purpose="explanation_support",
                metrics=["辅助证据"],
                dimensions=["渠道"],
                priority=2,
            ),
        ],
    )
    planning_provider = MockLLMProvider(
        {
            "strategy": "llm_candidate",
            "matched_template": "",
            "confidence": 0.9,
            "missing_slots": [],
            "clarification_questions": [],
            "risk_flags": [],
            "reason": "Use provider SQL candidate.",
        }
    )
    candidate_provider = _SequenceProvider(
        [
            {"sql_candidates": [{"sql": "SELECT channel, SUM(revenue) AS 收入 FROM orders GROUP BY channel LIMIT 20"}]},
            {"sql_candidates": [{"sql": "SELECT channel FROM orders; SELECT channel FROM marketing_spend"}]},
        ]
    )

    result = run_evidence_task_plan(
        _state(workspace, plan),
        sql_planning_provider=planning_provider,
        sql_candidate_provider=candidate_provider,
    )
    statuses = {item["task_id"]: item["status"] for item in result["evidence_task_results"]}

    assert result["status"] == "executed"
    assert statuses["revenue_by_channel"] == "executed"
    assert statuses["unsafe_support"] == "failed"
    assert result["question_evidence_ledger"]["data_limits"]
    assert any("unsafe_support" in limit for limit in result["question_evidence_ledger"]["data_limits"])


def test_all_core_tasks_failed_returns_evidence_insufficient_state(tmp_path):
    workspace = _workspace(tmp_path)
    plan = EvidenceTaskPlan(
        route="standard_analysis",
        max_parallel_evidence_tasks=1,
        tasks=[
            EvidenceTask(
                task_id="core_unsafe",
                question="核心证据不安全",
                purpose="core_fact",
                metrics=["收入"],
                dimensions=["渠道"],
            )
        ],
    )

    result = run_evidence_task_plan(
        _state(workspace, plan),
        sql_planning_provider=MockLLMProvider(
            {
                "strategy": "llm_candidate",
                "matched_template": "",
                "confidence": 0.9,
                "missing_slots": [],
                "clarification_questions": [],
                "risk_flags": [],
                "reason": "Use provider SQL candidate.",
            }
        ),
        sql_candidate_provider=MockLLMProvider(
            {"sql_candidates": [{"sql": "SELECT channel FROM orders; SELECT channel FROM marketing_spend"}]}
        ),
    )

    assert result["status"] == "failed"
    assert result["data_used"] is False
    assert "核心证据任务全部失败" in result["error_message"]
    assert result["question_evidence_ledger"]["confidence"] == "low"


def test_multi_statement_sql_is_not_executed_directly(tmp_path):
    workspace = _workspace(tmp_path)
    plan = EvidenceTaskPlan(
        route="standard_analysis",
        tasks=[
            EvidenceTask(
                task_id="multi_statement",
                question="尝试多条 SQL",
                purpose="core_fact",
                metrics=["收入"],
                dimensions=["渠道"],
            )
        ],
    )

    result = run_evidence_task_plan(
        _state(workspace, plan),
        sql_planning_provider=MockLLMProvider(
            {
                "strategy": "llm_candidate",
                "matched_template": "",
                "confidence": 0.9,
                "missing_slots": [],
                "clarification_questions": [],
                "risk_flags": [],
                "reason": "Use provider SQL candidate.",
            }
        ),
        sql_candidate_provider=MockLLMProvider(
            {"sql_candidates": [{"sql": "SELECT channel FROM orders; SELECT channel FROM marketing_spend"}]}
        ),
    )
    task_calls = result["evidence_task_results"][0]["tool_calls"]

    assert result["evidence_task_results"][0]["status"] == "failed"
    assert not any(call["tool_name"] == "sql_execution" for call in task_calls)
    assert any("Multiple SQL statements are not allowed" in limit for limit in result["evidence_task_results"][0]["data_limits"])


def test_max_parallel_evidence_tasks_defaults_to_three_and_is_configurable(tmp_path):
    workspace = _workspace(tmp_path)
    plan = plan_evidence_tasks(_analysis_task(), route="standard_analysis")

    default_result = run_evidence_task_plan(_state(workspace, plan))
    configured = EvidenceTaskPlan.from_dict(plan.to_dict())
    configured.max_parallel_evidence_tasks = 1
    configured_result = run_evidence_task_plan(_state(workspace, configured))

    assert default_result["evidence_task_runner"]["max_parallel_evidence_tasks"] == 3
    assert configured_result["evidence_task_runner"]["max_parallel_evidence_tasks"] == 1
