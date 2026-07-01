import sqlite3

from llm_ops.provider import MockLLMProvider
from workspaces.analysis_runner import run_workspace_analysis
from workspaces.profiler import profile_workspace_database
from workspaces.run_store import WorkspaceRunStore
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


def _provider_intent():
    return {
        "strategy": "llm_candidate",
        "intent": {
            "metric": "revenue",
            "dimension": "channel",
            "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近 30 天"},
            "filters": [],
            "operation": "comparison",
            "limit": 20,
        },
        "missing_slots": [],
        "clarification_questions": [],
        "risk_flags": [],
        "reason": "Clear workspace analysis question.",
    }


def _provider_sql_plan():
    return {
        "strategy": "llm_candidate",
        "matched_template": "",
        "confidence": 0.9,
        "missing_slots": [],
        "clarification_questions": [],
        "risk_flags": [],
        "reason": "Use a provider SQL candidate for this workspace schema.",
    }


def _create_ecommerce_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Clarification Analysis Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE orders (id INTEGER, status TEXT)")
        conn.execute("CREATE TABLE order_items (order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price REAL)")
        conn.execute("CREATE TABLE products (id INTEGER, product_name TEXT)")
        conn.executemany("INSERT INTO orders VALUES (?, ?)", [(1, "paid"), (2, "paid")])
        conn.executemany("INSERT INTO products VALUES (?, ?)", [(1, "A"), (2, "B")])
        conn.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?)", [(1, 1, 2, 100.0), (2, 2, 1, 50.0)])
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace


def _create_channel_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Schema Repair Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE orders (order_id TEXT, customer_id TEXT, channel TEXT, order_date TEXT, revenue REAL)"
        )
        conn.execute("CREATE TABLE customers (customer_id TEXT, segment TEXT, city TEXT)")
        conn.execute("CREATE TABLE marketing_spend (spend_id TEXT, channel TEXT, spend_date TEXT, spend REAL)")
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
            [
                ("o_1", "c_1", "email", "2026-06-01", 100.0),
                ("o_2", "c_2", "paid_search", "2026-06-02", 260.0),
                ("o_3", "c_1", "email", "2026-06-03", 140.0),
            ],
        )
        conn.executemany(
            "INSERT INTO customers VALUES (?, ?, ?)",
            [("c_1", "enterprise", "Shanghai"), ("c_2", "consumer", "Beijing")],
        )
        conn.executemany(
            "INSERT INTO marketing_spend VALUES (?, ?, ?, ?)",
            [
                ("s_1", "email", "2026-06-01", 30.0),
                ("s_2", "paid_search", "2026-06-02", 80.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace


def test_workspace_analysis_uses_workspace_database_and_run_artifact_paths(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Analysis Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE orders (channel TEXT, revenue REAL)")
        conn.executemany("INSERT INTO orders VALUES (?, ?)", [("email", 100.0), ("paid_search", 200.0)])
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="按渠道汇总收入",
        initial_sql="SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel LIMIT 20",
        providers={
            "question_understanding": MockLLMProvider(
                {
                    "strategy": "llm_candidate",
                    "intent": {
                        "metric": "revenue",
                        "dimension": "channel",
                        "time_range": None,
                        "filters": [],
                        "operation": "comparison",
                        "limit": 20,
                    },
                    "missing_slots": [],
                    "clarification_questions": [],
                    "risk_flags": [],
                    "reason": "Clear workspace analysis question.",
                }
            )
        },
    )

    assert result["workspace_id"] == workspace["workspace_id"]
    assert result["execution_result"]["success"] is True
    assert result["trace_path"].startswith(str(tmp_path / "workspaces" / workspace["workspace_id"] / "runs"))
    assert result["final_answer"]
    assert result["product_result"]["workspace_id"] == workspace["workspace_id"]
    assert result["product_result"]["business_answer"]["headline"]
    assert result["product_result"]["technical_details"]["sql"] == result["generated_sql"]
    assert result["business_answer"] == result["product_result"]["business_answer"]


def test_workspace_analysis_uses_answer_reviewer_and_composer_providers(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Reviewer Composer Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE results (entity_name TEXT, score_value REAL)")
        conn.executemany("INSERT INTO results VALUES (?, ?)", [("Alpha", 91.0), ("Beta", 83.0)])
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="Which entity should we prioritize?",
        initial_sql="SELECT entity_name, score_value FROM results ORDER BY score_value DESC LIMIT 20",
        providers={
            "insight_drafting": MockLLMProvider(
                {
                    "candidate_claims": ["Alpha score_value is 91.0", "Beta score_value is 83.0"],
                    "business_answer": {
                        "headline": "Gamma wins on margin_rate",
                        "direct_answer": "Prioritize Gamma because margin_rate is strongest.",
                        "why": "Gamma margin_rate is 0.42.",
                        "evidence_bullets": ["Gamma margin_rate is 0.42."],
                        "recommendations": ["Move resources to Gamma using margin_rate."],
                        "caveats": [],
                        "confidence": "high",
                    },
                }
            ),
            "answer_reviewer": MockLLMProvider(
                {
                    "status": "revise",
                    "language": "en",
                    "supported_entities": ["Alpha", "Beta"],
                    "unsupported_entities": ["Gamma"],
                    "supported_metrics": ["score_value"],
                    "unsupported_metrics": ["margin_rate"],
                    "issues": [
                        {
                            "type": "entity_mismatch",
                            "message": "Gamma is absent from evidence.",
                            "affected_fields": ["direct_answer"],
                        }
                    ],
                    "revision_instructions": ["Remove unsupported entity and metric."],
                    "confidence": "high",
                }
            ),
            "final_answer_composer": MockLLMProvider(
                {
                    "headline": "Alpha is the supported priority",
                    "direct_answer": "Prioritize Alpha because the returned evidence ranks it first on score_value.",
                    "why": "The result rows show Alpha at 91.0 versus Beta at 83.0.",
                    "evidence_bullets": ["Alpha score_value is 91.0.", "Beta score_value is 83.0."],
                    "recommendations": ["Use Alpha as the next review focus."],
                    "caveats": ["This only uses the current query result."],
                    "confidence": "medium",
                }
            ),
        },
    )

    assert result["status"] == "completed"
    answer_text = " ".join(
        [
            result["business_answer"]["headline"],
            result["business_answer"]["direct_answer"],
            result["business_answer"]["why"],
            *result["business_answer"]["evidence_bullets"],
            *result["business_answer"]["recommendations"],
            *result["business_answer"]["caveats"],
        ]
    )
    assert result["insight"]["answer_review"]["status"] == "revise"
    assert result["insight"]["answer_composition"]["source"] == "provider"
    assert "Alpha" in answer_text
    assert "Gamma" not in answer_text
    assert "margin_rate" not in answer_text
    assert result["product_result"]["business_answer"] == result["business_answer"]


def test_workspace_analysis_persists_full_product_result_for_history_detail(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Persisted Analysis Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE orders (channel TEXT, revenue REAL)")
        conn.executemany("INSERT INTO orders VALUES (?, ?)", [("email", 100.0), ("paid_search", 200.0)])
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="按渠道汇总收入",
        initial_sql="SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel LIMIT 20",
    )

    stored = WorkspaceRunStore(store).load_run_response(workspace["workspace_id"], result["run_id"])

    assert stored["run_id"] == result["run_id"]
    assert stored["product_result"]["business_answer"] == result["product_result"]["business_answer"]
    assert stored["product_result"]["evidence"]["table_preview"]["rows"] == result["product_result"]["evidence"][
        "table_preview"
    ]["rows"]
    assert stored["product_result"]["technical_details"]["sql"] == result["generated_sql"]
    assert stored["result"]["product_result"]["question_thread"]["original_question"] == "按渠道汇总收入"


def test_workspace_analysis_persists_pending_clarification_run(tmp_path):
    store, workspace = _create_ecommerce_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="帮我看看销售情况",
    )

    assert result["status"] == "waiting_for_clarification"
    assert result["pending_run_id"].startswith("pending_")
    thread = result["product_result"]["question_thread"]
    assert thread["status"] == "waiting_for_clarification"
    assert thread["original_question"] == "帮我看看销售情况"
    assert thread["clarification_question"]
    assert thread["pending_run_id"] == result["pending_run_id"]
    assert "generated_sql" not in result


def test_workspace_analysis_continuation_resolves_question_and_calls_workflow(tmp_path):
    from workspaces.analysis_runner import run_workspace_analysis_continuation

    store, workspace = _create_ecommerce_workspace(tmp_path)
    pending = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="帮我看看销售情况",
    )

    result = run_workspace_analysis_continuation(
        store=store,
        workspace_id=workspace["workspace_id"],
        pending_run_id=pending["pending_run_id"],
        clarification_answer="按商品，最近 90 天，看 Top 5",
    )

    assert result["status"] == "completed"
    assert result["execution_result"]["success"] is True
    assert result["generated_sql"].lower().startswith("select")
    trace_nodes = [event["node"] for event in result["trace"]]
    assert "sql_generator_agent" in trace_nodes
    assert "sql_reviewer_agent" in trace_nodes
    assert "sql_executor_node" in trace_nodes
    thread = result["product_result"]["question_thread"]
    assert thread["status"] == "completed"
    assert thread["original_question"] == "帮我看看销售情况"
    assert thread["clarification_answer"] == "按商品，最近 90 天，看 Top 5"
    assert "最近 90 天" in thread["resolved_question"]
    assert "商品" in thread["resolved_question"]


def test_resolved_question_uses_generic_context_merge_without_channel_budget_template():
    from question_understanding.resolved_question import build_resolved_question

    resolved = build_resolved_question(
        original_question="帮我分析渠道表现，看看哪个渠道该加预算。",
        clarification_answer="最近 90 天。",
        clarification_context={
            "clarification_question": "你希望分析哪个时间范围？",
            "question_understanding": {"intent": {"dimension": "channel"}},
        },
    )

    assert "帮我分析渠道表现" in resolved
    assert "最近 90 天" in resolved
    assert "追问" not in resolved
    assert "你希望分析哪个时间范围" not in resolved
    assert "投放成本" not in resolved
    assert "ROI" not in resolved


def test_workspace_analysis_continuation_marks_pending_failed_when_workflow_errors(tmp_path, monkeypatch):
    from workspaces.analysis_runner import run_workspace_analysis_continuation
    from workspaces.pending_clarification_store import PendingClarificationStore

    store, workspace = _create_ecommerce_workspace(tmp_path)
    pending_store = PendingClarificationStore(store)
    pending = pending_store.create_pending_run(
        workspace_id=workspace["workspace_id"],
        run_id="run_pending",
        original_question="帮我看看销售情况",
        question_understanding={"missing_slots": ["time_range"]},
        clarification_question="你希望分析哪个时间范围？",
        raw_result={"status": "waiting_for_clarification"},
    )

    def fail_workflow(*args, **kwargs):
        raise RuntimeError("workflow exploded")

    monkeypatch.setattr("workspaces.analysis_runner.run_workflow", fail_workflow)

    try:
        run_workspace_analysis_continuation(
            store=store,
            workspace_id=workspace["workspace_id"],
            pending_run_id=pending["pending_run_id"],
            clarification_answer="最近 90 天",
        )
    except RuntimeError:
        pass

    stored = pending_store.load_pending_run(workspace["workspace_id"], pending["pending_run_id"])
    assert stored["status"] == "failed"
    assert stored["clarification_answer"] == "最近 90 天"
    assert stored["resolved_question"]
    assert "workflow exploded" in stored["error"]


def test_workspace_analysis_repairs_schema_mismatch_once(tmp_path):
    store, workspace = _create_channel_workspace(tmp_path)
    bad_sql = (
        "SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS revenue "
        "FROM orders o "
        "JOIN order_items oi ON o.id = oi.order_id "
        "JOIN products p ON oi.product_id = p.id "
        "GROUP BY p.product_name LIMIT 20"
    )
    repaired_sql = (
        "SELECT o.channel, SUM(o.revenue) AS revenue, COALESCE(SUM(ms.spend), 0) AS spend "
        "FROM orders o "
        "LEFT JOIN marketing_spend ms ON o.channel = ms.channel "
        "GROUP BY o.channel "
        "ORDER BY revenue DESC LIMIT 20"
    )
    sql_provider = _SequenceProvider(
        [
            {"sql_candidates": [{"sql": bad_sql, "rationale": "Mistaken adjacent ecommerce schema."}]},
            {"sql_candidates": [{"sql": repaired_sql, "rationale": "Use only workspace tables and channel fields."}]},
        ]
    )

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近 30 天各渠道收入和投放情况怎么样？",
        providers={
            "question_understanding": MockLLMProvider(_provider_intent()),
            "sql_planning": MockLLMProvider(_provider_sql_plan()),
            "sql_candidate": sql_provider,
        },
    )

    assert result["status"] == "completed"
    assert result["execution_result"]["success"] is True
    assert result["execution_result"]["rows"]
    assert result["schema_repair_attempted"] is True
    assert result["schema_repair_succeeded"] is True
    assert "Unknown table" in result["schema_repair_reason"]
    assert "order_items" in result["schema_repair"]["rejected_sql_summary"]
    assert "marketing_spend" in result["schema_repair"]["repaired_sql_summary"]
    assert result["generated_sql"] == result["review_result"]["normalized_sql"]
    assert "order_items" not in result["generated_sql"]
    assert "marketing_spend" in result["generated_sql"]
    assert result["product_result"]["evidence"]["table_preview"]["rows"]
    technical = result["product_result"]["technical_details"]
    assert any(log["name"] == "schema_repair" for log in technical["validation_logs"])
    assert technical["provider_metadata"]["schema_repair"]["attempted"] is True

    review_events = [event for event in result["trace"] if event.get("node") == "sql_reviewer_agent"]
    assert len(review_events) == 2
    assert review_events[0]["status"] == "error"
    assert review_events[1]["status"] == "success"
    repair_prompt = sql_provider.requests[1].prompt
    assert "最近 30 天各渠道收入和投放情况怎么样？" in repair_prompt
    assert bad_sql in repair_prompt
    assert "Unknown table: order_items" in repair_prompt
    assert "Table orders:" in repair_prompt
    assert "Table marketing_spend:" in repair_prompt
    assert "semantic_layer" in repair_prompt or "workspace_semantic_layer" in repair_prompt


def test_workspace_analysis_does_not_retry_schema_repair_more_than_once(tmp_path):
    store, workspace = _create_channel_workspace(tmp_path)
    bad_sql = (
        "SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS revenue "
        "FROM orders o "
        "JOIN order_items oi ON o.id = oi.order_id "
        "JOIN products p ON oi.product_id = p.id "
        "GROUP BY p.product_name LIMIT 20"
    )
    still_bad_sql = "SELECT p.product_name FROM products p LIMIT 20"
    sql_provider = _SequenceProvider(
        [
            {"sql_candidates": [{"sql": bad_sql, "rationale": "Mistaken adjacent ecommerce schema."}]},
            {"sql_candidates": [{"sql": still_bad_sql, "rationale": "Still references a missing table."}]},
        ]
    )

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近 30 天各渠道收入和投放情况怎么样？",
        providers={
            "question_understanding": MockLLMProvider(_provider_intent()),
            "sql_planning": MockLLMProvider(_provider_sql_plan()),
            "sql_candidate": sql_provider,
        },
    )

    assert result["status"] == "failed"
    assert result["execution_result"] == {}
    assert result["schema_repair_attempted"] is True
    assert result["schema_repair_succeeded"] is False
    assert len(sql_provider.requests) == 2
    review_events = [event for event in result["trace"] if event.get("node") == "sql_reviewer_agent"]
    assert len(review_events) == 2
    assert all(event["status"] == "error" for event in review_events)
    assert not any(event.get("node") == "sql_executor_node" for event in result["trace"])
    assert "Unknown table" in result["schema_repair_reason"]
    technical = result["product_result"]["technical_details"]
    assert any(log["name"] == "schema_repair" for log in technical["validation_logs"])
    assert technical["provider_metadata"]["schema_repair"]["succeeded"] is False


def test_workspace_analysis_schema_repair_failure_has_business_friendly_product_answer(tmp_path):
    store, workspace = _create_channel_workspace(tmp_path)
    bad_sql = (
        "SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS revenue "
        "FROM orders o "
        "JOIN order_items oi ON o.id = oi.order_id "
        "JOIN products p ON oi.product_id = p.id "
        "GROUP BY p.product_name LIMIT 20"
    )
    still_bad_sql = "SELECT p.product_name FROM products p LIMIT 20"
    sql_provider = _SequenceProvider(
        [
            {"sql_candidates": [{"sql": bad_sql, "rationale": "Mistaken adjacent ecommerce schema."}]},
            {"sql_candidates": [{"sql": still_bad_sql, "rationale": "Still references a missing table."}]},
        ]
    )

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近 30 天各渠道收入和投放情况怎么样？",
        providers={
            "question_understanding": MockLLMProvider(_provider_intent()),
            "sql_planning": MockLLMProvider(_provider_sql_plan()),
            "sql_candidate": sql_provider,
        },
    )

    assert result["status"] == "failed"
    assert result["execution_result"] == {}
    answer = result["product_result"]["business_answer"]
    assert answer["headline"] == "当前数据无法支持这次查询"
    assert "不存在的表或字段" in answer["direct_answer"]
    assert "Unknown table" not in answer["direct_answer"]
    assert "Unknown column" not in answer["direct_answer"]
    assert "Unknown table" not in answer["headline"]
    technical = result["product_result"]["technical_details"]
    assert {log["name"] for log in technical["validation_logs"]} >= {"review_result", "schema_repair"}
    assert "Unknown table" in str(technical["validation_logs"])
    assert not any(event.get("node") == "sql_executor_node" for event in result["trace"])


def test_schema_repair_still_requires_sql_reviewer_approval(tmp_path):
    store, workspace = _create_channel_workspace(tmp_path)
    bad_sql = (
        "SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS revenue "
        "FROM orders o "
        "JOIN order_items oi ON o.id = oi.order_id "
        "JOIN products p ON oi.product_id = p.id "
        "GROUP BY p.product_name LIMIT 20"
    )
    unsafe_repair = "DELETE FROM orders WHERE revenue < 0"
    sql_provider = _SequenceProvider(
        [
            {"sql_candidates": [{"sql": bad_sql, "rationale": "Mistaken adjacent ecommerce schema."}]},
            {"sql_candidates": [{"sql": unsafe_repair, "rationale": "Unsafe repair must still be reviewed."}]},
        ]
    )

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近 30 天各渠道收入和投放情况怎么样？",
        providers={
            "question_understanding": MockLLMProvider(_provider_intent()),
            "sql_planning": MockLLMProvider(_provider_sql_plan()),
            "sql_candidate": sql_provider,
        },
    )

    assert result["status"] == "failed"
    assert result["execution_result"] == {}
    assert result["schema_repair_attempted"] is True
    assert result["schema_repair_succeeded"] is False
    assert result["review_result"]["approved"] is False
    assert "SQL contains a dangerous keyword" in result["review_result"]["issues"]
    review_events = [event for event in result["trace"] if event.get("node") == "sql_reviewer_agent"]
    assert len(review_events) == 2
    assert review_events[-1]["status"] == "error"
    assert not any(event.get("node") == "sql_executor_node" for event in result["trace"])
