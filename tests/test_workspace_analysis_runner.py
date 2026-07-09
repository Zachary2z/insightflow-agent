import json
import sqlite3
from pathlib import Path

from llm_ops.provider import MockLLMProvider
from workspaces.analysis_runner import (
    create_workspace_analysis_run_shell,
    execute_workspace_analysis_job,
    submit_workspace_analysis_run,
    run_workspace_analysis,
    run_workspace_analysis_follow_up,
)
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


def _business_answer_text(answer):
    return " ".join(
        [
            answer["headline"],
            answer["direct_answer"],
            answer["why"],
            *answer["evidence_bullets"],
            *answer["recommendations"],
            *answer["caveats"],
        ]
    )


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


def _create_p29_fast_fact_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P29 Fast Fact Gate Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE channel_sales (sale_date TEXT, channel_name TEXT, sales_amount REAL)"
        )
        conn.executemany(
            "INSERT INTO channel_sales VALUES (?, ?, ?)",
            [
                ("2026-06-10", "搜索广告", 120000.0),
                ("2026-06-11", "私域社群", 180000.0),
                ("2026-06-12", "直播间", 90000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace


def _create_p29_channel_investment_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P29 Channel Investment Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE channel_performance ("
            "business_date TEXT, channel_name TEXT, revenue REAL, ad_spend REAL, roas REAL)"
        )
        conn.executemany(
            "INSERT INTO channel_performance VALUES (?, ?, ?, ?, ?)",
            [
                ("2026-06-10", "搜索广告", 120000.0, 80000.0, 1.5),
                ("2026-06-11", "私域社群", 180000.0, 30000.0, 6.0),
                ("2026-06-12", "直播间", 90000.0, 70000.0, 1.29),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace


def _mock_chinese_business_answer_provider():
    return _SequenceProvider(
        [
            {
            "candidate_claims": ["上海旗舰店 total_sales 为 26255.44。", "北京国贸店 satisfaction_score 为 4.2。"],
            "business_answer": {
                "headline": "上海旗舰店综合表现更靠前。",
                "direct_answer": "上海旗舰店在销售额和满意度上都更靠前，可作为优先复盘对象。",
                "why": "返回数据中上海旗舰店销售额为 26255.44，满意度为 4.8。",
                "evidence_bullets": ["上海旗舰店销售额为 26255.44，满意度为 4.8。"],
                "recommendations": ["优先复盘上海旗舰店的经营动作。"],
                "caveats": ["当前结论只基于本次查询返回的数据。"],
                "confidence": "medium",
            },
            }
        ]
    )


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
    assert result["analysis_task"]["business_lens"]["metrics"]
    assert result["analysis_task"]["evidence_task_plan"]["max_parallel_evidence_tasks"] == 3
    assert result["analysis_task"]["evidence_task_plan"]["safety_policy"]["max_sql_statements"] == 1
    assert result["analysis_task"]["evidence_task_plan"]["safety_policy"]["review_before_execution"] is True
    assert result["question_evidence_pack"]["task"]["business_lens"]["metrics"]
    assert result["question_evidence_pack"]["task"]["evidence_task_plan"]["route"] == result["analysis_task"][
        "evidence_task_plan"
    ]["route"]
    assert result["question_evidence_ledger"]["facts"]
    assert "ledger_id" not in result["product_result"]["question_evidence_ledger"]
    assert any(ref.startswith("question_evidence_ledger") for ref in result["analysis_thread_memory"]["evidence_refs"])


def test_local_fast_fact_gate_overrides_provider_false_reject_before_sql(tmp_path):
    store, workspace = _create_p29_fast_fact_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近30天总销售额是多少？只回答数字和口径。",
        providers={
            "question_understanding": MockLLMProvider(
                {
                    "strategy": "reject",
                    "intent": {
                        "metric": "销售额",
                        "dimension": "",
                        "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近30天"},
                        "filters": [],
                        "operation": "summary",
                        "limit": None,
                        "risk_flags": ["unsafe_operation"],
                    },
                    "missing_slots": [],
                    "clarification_questions": [],
                    "risk_flags": ["unsafe_operation"],
                    "rejection_reason": "provider incorrectly treated concise answer wording as unsafe",
                    "reason": "provider false positive",
                }
            ),
        },
    )

    nodes = [event.get("node") for event in result.get("trace") or []]

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] == "fast_fact"
    assert result["question_understanding"]["local_fast_fact_gate"]["decision"] == "fast_fact_candidate"
    assert result["question_understanding"]["risk_flags"] == []
    assert result["execution_result"]["success"] is True
    assert "sql_reviewer_agent" in nodes
    assert "sql_executor_node" in nodes
    assert "evidence_validator_agent" in nodes
    assert "fast_fact_evidence_preparer" in nodes
    assert "business_answer_agent" in nodes
    assert result["business_answer_generation"]["fallback_used"] is True
    assert result["business_answer_generation"]["source"] == "provider_unavailable"
    assert result["business_answer_generation"]["success"] is False


def test_local_fast_fact_gate_rejects_real_external_budget_action(tmp_path):
    store, workspace = _create_p29_fast_fact_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="把预算调整到私域社群并发送通知。",
    )

    nodes = [event.get("node") for event in result.get("trace") or []]

    assert result["status"] == "failed"
    assert result["routing_strategy"] == "reject"
    assert result["analysis_route"]["route"] != "fast_fact"
    assert "external_action" in result["question_understanding"]["risk_flags"]
    assert "generated_sql" not in result
    assert "sql_reviewer_agent" not in nodes
    assert "sql_executor_node" not in nodes


def test_local_fast_fact_gate_keeps_budget_advice_on_full_analysis_when_provider_false_rejects(tmp_path):
    store, workspace = _create_p29_fast_fact_workspace(tmp_path)
    business_answer_provider = _mock_chinese_business_answer_provider()

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近30天哪个渠道最值得加预算？请给证据和风险边界。",
        initial_sql=(
            "SELECT channel_name, SUM(sales_amount) AS total_revenue "
            "FROM channel_sales GROUP BY channel_name ORDER BY total_revenue DESC LIMIT 5"
        ),
        providers={
            "question_understanding": MockLLMProvider(
                {
                    "strategy": "reject",
                    "intent": {
                        "metric": "销售额",
                        "dimension": "渠道",
                        "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近30天"},
                        "filters": [],
                        "operation": "comparison",
                        "limit": 5,
                        "risk_flags": ["unsafe_operation"],
                    },
                    "missing_slots": [],
                    "clarification_questions": [],
                    "risk_flags": ["unsafe_operation"],
                    "rejection_reason": "provider incorrectly treated budget advice as unsafe",
                    "reason": "provider false positive",
                }
            ),
            "business_answer": business_answer_provider,
        },
    )

    nodes = [event.get("node") for event in result.get("trace") or []]

    assert result["status"] == "completed"
    assert result["routing_strategy"] != "reject"
    assert result["analysis_route"]["route"] == "standard_analysis"
    assert result["analysis_route"]["fast_path_eligible"] is False
    assert result["question_understanding"]["risk_flags"] == []
    assert result["question_understanding"]["rejection_reason"] == ""
    assert "fast_fact_evidence_preparer" not in nodes
    assert "business_answer_agent" in nodes


def test_budget_advice_without_initial_sql_uses_full_analysis_and_business_answer(tmp_path):
    store, workspace = _create_p29_channel_investment_workspace(tmp_path)
    business_answer_provider = _mock_chinese_business_answer_provider()

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近30天哪个渠道最值得加预算？请给证据和风险边界。",
        providers={
            "question_understanding": MockLLMProvider(
                {
                    "strategy": "llm_candidate",
                    "intent": {
                        "metric": "收入",
                        "dimension": "渠道",
                        "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近30天"},
                        "filters": [],
                        "operation": "comparison",
                        "limit": 5,
                        "risk_flags": [],
                    },
                    "missing_slots": [],
                    "clarification_questions": [],
                    "risk_flags": [],
                    "rejection_reason": "",
                    "reason": "safe business advice question",
                }
            ),
            "business_answer": business_answer_provider,
        },
    )

    nodes = [event.get("node") for event in result.get("trace") or []]
    tool_names = {call["tool_name"] for call in result["question_evidence_pack"]["tool_calls"]}

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] != "fast_fact"
    assert result["routing_strategy"] != "reject"
    assert result["question_understanding"]["risk_flags"] == []
    assert result["question_understanding"]["rejection_reason"] == ""
    assert {"evidence_planning", "schema_lookup", "metric_lookup", "sql_review", "sql_execution"}.issubset(tool_names)
    assert result["execution_result"]["success"] is True
    assert "evidence_validator_agent" in nodes
    assert "business_answer_agent" in nodes
    assert "fast_fact_evidence_preparer" not in nodes
    assert len(business_answer_provider.requests) == 1
    assert result["product_result"]["evidence"]["fact_payload"]["comparison_scope"]["sufficient"] is True


def test_provider_business_caveat_risk_flag_does_not_keep_reject_state(tmp_path):
    store, workspace = _create_p29_channel_investment_workspace(tmp_path)
    business_answer_provider = _mock_chinese_business_answer_provider()

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近30天哪个渠道最值得加预算？请给证据和风险边界。",
        providers={
            "question_understanding": MockLLMProvider(
                {
                    "strategy": "reject",
                    "intent": {
                        "metric": "收入",
                        "dimension": "渠道",
                        "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近30天"},
                        "filters": [],
                        "operation": "comparison",
                        "limit": 5,
                        "risk_flags": ["数据量不足"],
                    },
                    "missing_slots": [],
                    "clarification_questions": [],
                    "risk_flags": ["数据量不足"],
                    "rejection_reason": "",
                    "reason": "provider expressed a data boundary as a risk flag",
                }
            ),
            "business_answer": business_answer_provider,
        },
    )

    assert result["status"] == "completed"
    assert result["routing_strategy"] != "reject"
    assert result["analysis_route"]["route"] != "fast_fact"
    assert result["question_understanding"]["rejection_reason"] == ""
    assert result["execution_result"]["success"] is True
    assert len(business_answer_provider.requests) == 1


def test_provider_false_unsafe_budget_advice_without_initial_sql_clears_reject_state(tmp_path):
    store, workspace = _create_p29_channel_investment_workspace(tmp_path)
    business_answer_provider = _mock_chinese_business_answer_provider()

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近30天哪个渠道最值得加预算？请给证据和风险边界。",
        providers={
            "question_understanding": MockLLMProvider(
                {
                    "strategy": "reject",
                    "intent": {
                        "metric": "收入",
                        "dimension": "渠道",
                        "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近30天"},
                        "filters": [],
                        "operation": "comparison",
                        "limit": 5,
                        "risk_flags": ["unsafe_operation"],
                    },
                    "missing_slots": [],
                    "clarification_questions": [],
                    "risk_flags": ["unsafe_operation"],
                    "rejection_reason": "provider incorrectly treated budget advice as unsafe",
                    "reason": "provider false positive",
                }
            ),
            "business_answer": business_answer_provider,
        },
    )

    assert result["status"] == "completed"
    assert result["routing_strategy"] != "reject"
    assert result["analysis_route"]["route"] != "fast_fact"
    assert result["question_understanding"]["risk_flags"] == []
    assert result["question_understanding"]["rejection_reason"] == ""
    assert result["execution_result"]["success"] is True
    assert len(business_answer_provider.requests) == 1


def test_provider_false_unsafe_budget_advice_with_business_boundary_flag_stays_full_analysis(tmp_path):
    store, workspace = _create_p29_channel_investment_workspace(tmp_path)
    business_answer_provider = _mock_chinese_business_answer_provider()

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近30天哪个渠道最值得加预算？请给证据和风险边界。",
        providers={
            "question_understanding": MockLLMProvider(
                {
                    "strategy": "reject",
                    "intent": {
                        "metric": "收入",
                        "dimension": "渠道",
                        "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近30天"},
                        "filters": [],
                        "operation": "comparison",
                        "limit": 5,
                        "risk_flags": ["unsafe_operation", "数据量不足"],
                    },
                    "missing_slots": [],
                    "clarification_questions": [],
                    "risk_flags": ["unsafe_operation", "数据量不足"],
                    "rejection_reason": "provider incorrectly treated budget advice as unsafe",
                    "reason": "provider false positive plus data boundary",
                }
            ),
            "business_answer": business_answer_provider,
        },
    )

    assert result["status"] == "completed"
    assert result["routing_strategy"] != "reject"
    assert result["analysis_route"]["route"] != "fast_fact"
    assert result["question_understanding"]["risk_flags"] == ["数据量不足"]
    assert result["question_understanding"]["rejection_reason"] == ""
    assert result["execution_result"]["success"] is True
    assert len(business_answer_provider.requests) == 1


def test_real_sensitive_delete_request_rejects_before_sql(tmp_path):
    store, workspace = _create_p29_channel_investment_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="删除所有客户手机号。",
    )

    nodes = [event.get("node") for event in result.get("trace") or []]

    assert result["status"] == "failed"
    assert result["routing_strategy"] == "reject"
    assert set(result["question_understanding"]["risk_flags"]) >= {"unsafe_operation", "sensitive_field"}
    assert "generated_sql" not in result
    assert "sql_reviewer_agent" not in nodes
    assert "sql_executor_node" not in nodes


def test_multi_metric_channel_investment_efficiency_question_uses_full_path(tmp_path):
    store, workspace = _create_p29_channel_investment_workspace(tmp_path)
    business_answer_provider = _SequenceProvider(
        [
            {
                "candidate_claims": [
                    {"claim": "私域社群 revenue 为 180000.0。", "category": "hard_fact"},
                    {"claim": "私域社群 ad_spend 为 30000.0。", "category": "hard_fact"},
                    {"claim": "私域社群 roas 为 6.0。", "category": "hard_fact"},
                    {"claim": "私域社群综合表现最好。", "category": "business_inference"},
                ],
                "business_answer": {
                    "headline": "私域社群综合表现最好。",
                    "direct_answer": "私域社群收入最高且投放效率最高，综合表现最好。",
                    "why": "证据显示私域社群收入为 180000.0，投放金额为 30000.0，ROAS 为 6.0。",
                    "evidence_bullets": ["私域社群收入 180000.0、投放金额 30000.0、ROAS 6.0。"],
                    "recommendations": ["优先复盘私域社群打法，再评估是否扩大预算。"],
                    "caveats": ["当前结论只基于最近30天同表渠道数据。"],
                    "confidence": "medium",
                },
            }
        ]
    )

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天按渠道比较收入、投放金额和投放效率，哪个渠道表现最好？",
        providers={"business_answer": business_answer_provider},
    )

    nodes = [event.get("node") for event in result.get("trace") or []]
    columns = result["execution_result"]["columns"]
    answer_text = _business_answer_text(result["business_answer"])

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] != "fast_fact"
    assert result["routing_strategy"] != "reject"
    assert result["question_understanding"]["risk_flags"] == []
    assert result["execution_result"]["success"] is True
    assert "business_answer_agent" in nodes
    assert "fast_fact_evidence_preparer" not in nodes
    assert len(business_answer_provider.requests) == 1
    assert any("收入" in column or "销售额" in column or "revenue" in column for column in columns)
    assert any("投放" in column or "spend" in column for column in columns)
    assert any("ROAS" in column.upper() or "效率" in column for column in columns)
    assert "私域社群" in answer_text
    assert result["product_result"]["evidence"]["fact_payload"]["comparison_scope"]["sufficient"] is True
    assert result["business_answer"]["caveats"]


def test_cross_table_revenue_and_spend_question_uses_multi_task_evidence(tmp_path):
    store, workspace = _create_channel_workspace(tmp_path)
    business_answer_provider = _SequenceProvider(
        [
            {
                "candidate_claims": [
                    {"claim": "私域社群收入和投放花费均有证据。", "category": "business_inference"}
                ],
                "business_answer": {
                    "headline": "已合并收入和投放证据。",
                    "direct_answer": "已基于收入和投放花费的多任务证据生成一个业务回答。",
                    "why": "收入和投放花费来自不同数据表，因此分别执行安全证据任务后合并判断。",
                    "evidence_bullets": ["收入任务和投放任务均返回了按渠道汇总结果。"],
                    "recommendations": ["优先关注收入和投放差异较大的渠道。"],
                    "caveats": ["当前结论基于本次已审核查询返回的数据。"],
                    "confidence": "medium",
                },
            }
        ]
    )

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近30天按渠道比较收入和投放花费，哪个渠道更值得关注？",
        providers={"business_answer": business_answer_provider},
    )

    task_results = result["evidence_task_results"]
    ledger = result["question_evidence_ledger"]

    assert result["status"] == "completed"
    assert result["evidence_task_runner"]["max_parallel_evidence_tasks"] == 3
    assert len(task_results) >= 2
    assert {item["status"] for item in task_results} == {"executed"}
    assert result["execution_result"]["success"] is True
    assert result["execution_result"]["row_count"] >= 2
    assert ledger["source_pack_id"] == "merged_question_evidence_pack"
    assert ledger["question_evidence_plan"]["groups"]
    assert len(ledger["evidence_groups"]) >= 2
    assert all(group["facts"] for group in ledger["evidence_groups"])
    assert all(group["source"]["tables"] for group in ledger["evidence_groups"])
    assert all(group["metrics"] for group in ledger["evidence_groups"])
    assert len({group["group_id"] for group in ledger["evidence_groups"]}) == len(ledger["evidence_groups"])
    assert {item["task_id"] for item in task_results}.issubset({fact["task_id"] for fact in ledger["facts"]})
    assert len(business_answer_provider.requests) == 1


def test_workspace_analysis_fact_payload_keeps_non_channel_comparison_rows(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Store Fact Payload Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (store_name TEXT, order_date TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [
                ("上海旗舰店", "2026-06-01", 26255.44),
                ("北京国贸店", "2026-06-02", 18400.0),
                ("深圳湾店", "2026-06-03", 12000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个门店销售额最高？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_revenue "
            "FROM store_sales GROUP BY store_name ORDER BY total_revenue DESC LIMIT 3"
        ),
    )

    fact_payload = result["product_result"]["evidence"]["fact_payload"]
    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] == "fast_fact"
    assert result["analysis_route"]["fast_path_eligible"] is True
    assert result["product_result"]["analysis_route"] == result["analysis_route"]
    assert not any(event.get("node") == "insight_agent" for event in result["trace"])
    assert any(event.get("node") == "fast_fact_evidence_preparer" for event in result["trace"])
    assert any(event.get("node") == "business_answer_agent" for event in result["trace"])
    assert fact_payload["comparison_scope"]["row_count"] == 3
    assert fact_payload["comparison_scope"]["sufficient"] is True
    assert fact_payload["rows"] == result["execution_result"]["rows"]
    assert fact_payload["display_values"][0]["门店"] == "上海旗舰店"
    assert fact_payload["display_values"][0]["总收入"] == "2.6 万"
    assert fact_payload["formulas"]
    assert "technical_sql" not in result["product_result"]["technical_details"]["fact_payload"]
    assert result["product_result"]["technical_details"]["sql"].startswith("SELECT store_name")


def test_workspace_analysis_uses_single_business_answer_provider_surface(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Reviewer Composer Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE results (entity_name TEXT, score_value REAL)")
        conn.executemany("INSERT INTO results VALUES (?, ?)", [("Alpha", 91.0), ("Beta", 83.0)])
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    business_answer_provider = _SequenceProvider(
        [
            {
                "candidate_claims": [
                    {"claim": "Alpha score_value is 91.0", "category": "hard_fact"},
                    {"claim": "Beta score_value is 83.0", "category": "hard_fact"},
                    {"claim": "Prioritize Alpha as the next review focus.", "category": "recommendation"},
                ],
                "business_answer": {
                    "headline": "Alpha is the supported priority",
                    "direct_answer": "Prioritize Alpha because the returned evidence ranks it first on score_value.",
                    "why": "The result rows show Alpha at 91.0 versus Beta at 83.0.",
                    "evidence_bullets": ["Alpha score_value is 91.0.", "Beta score_value is 83.0."],
                    "recommendations": ["Use Alpha as the next review focus."],
                    "caveats": ["This only uses the current query result."],
                    "confidence": "medium",
                },
            }
        ]
    )

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="Which entity should we prioritize?",
        initial_sql="SELECT entity_name, score_value FROM results ORDER BY score_value DESC LIMIT 20",
        providers={
            "business_answer": business_answer_provider,
        },
    )

    nodes = [event.get("node") for event in result.get("trace") or []]
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
    assert "business_answer_agent" in nodes
    assert "insight_agent" not in nodes
    assert len(business_answer_provider.requests) == 1
    assert result["business_answer_generation"]["provider_called"] is True
    assert result["audit_result"]["supported_facts"]
    assert result["audit_result"]["unsupported_claims"] == []
    assert result["product_result"]["technical_details"]["audit_result"] == result["audit_result"]
    assert set(result["business_answer"]) == {
        "headline",
        "direct_answer",
        "why",
        "evidence_bullets",
        "recommendations",
        "caveats",
        "confidence",
    }
    assert result["candidate_claims"]
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
    assert stored["result"]["analysis_route"] == result["analysis_route"]
    assert stored["product_result"]["analysis_route"] == result["product_result"]["analysis_route"]
    assert stored["product_result"]["business_answer"] == result["product_result"]["business_answer"]
    assert stored["product_result"]["evidence"]["table_preview"]["rows"] == result["product_result"]["evidence"][
        "table_preview"
    ]["rows"]
    assert stored["product_result"]["technical_details"]["sql"] == result["generated_sql"]
    assert stored["result"]["product_result"]["question_thread"]["original_question"] == "按渠道汇总收入"


def test_workspace_analysis_history_restores_p30_chart_artifact_fields(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P30 Chart History Workspace")
    run_id = "run_p30_chart_history"
    run_dir = Path(workspace["root_path"]) / "runs" / run_id
    run_dir.mkdir(parents=True)
    run_path = run_dir / f"{run_id}.json"
    run_payload = {
        "run_id": run_id,
        "result": {
            "run_id": run_id,
            "workspace_id": workspace["workspace_id"],
            "workspace_root": workspace["root_path"],
            "status": "completed",
            "user_question": "按渠道比较收入并画图",
            "business_answer": {
                "headline": "付费搜索收入最高。",
                "direct_answer": "付费搜索收入最高，为 200.0。",
                "why": "证据显示付费搜索高于邮件渠道。",
                "evidence_bullets": ["付费搜索收入为 200.0。", "邮件收入为 100.0。"],
                "recommendations": [],
                "caveats": ["当前结论只基于本次查询返回的数据。"],
                "confidence": "medium",
            },
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["email", 100.0], ["paid_search", 200.0]],
            },
            "visualization_delivery_result": {
                "artifact_id": "chart_channel_revenue_001",
                "renderer": "echarts",
                "chart_type": "ranked_bar",
                "chart_spec": {"chart_type": "ranked_bar", "x": "channel", "y": "revenue"},
                "echarts_option": {"series": [{"type": "bar", "data": [100.0, 200.0]}]},
                "artifact_path": str(run_dir / "charts" / "channel.png"),
                "image_path": str(run_dir / "charts" / "channel.png"),
                "evidence_refs": ["question_evidence_pack"],
                "source": "analysis_workbench",
                "data_row_count": 2,
            },
        },
    }
    run_path.write_text(json.dumps(run_payload, ensure_ascii=False), encoding="utf-8")

    stored = WorkspaceRunStore(store).load_run_response(workspace["workspace_id"], run_id)
    artifact = stored["product_result"]["chart_artifacts"][0]

    assert artifact["artifact_id"] == "chart_channel_revenue_001"
    assert artifact["renderer"] == "echarts"
    assert artifact["chart_type"] == "ranked_bar"
    assert "chart_spec" not in artifact
    assert artifact["echarts_option"]["series"][0]["data"] == [100.0, 200.0]
    assert artifact["image_path"] == f"runs/{run_id}/charts/channel.png"
    assert artifact["image_url"] == f"/api/workspaces/{workspace['workspace_id']}/artifacts/runs/{run_id}/charts/channel.png"
    assert artifact["evidence_refs"] == ["question_evidence_pack"]
    assert artifact["source"] == "analysis_workbench"
    assert artifact["data_row_count"] == 2


def test_workspace_analysis_returns_cache_candidate_for_same_data_version_and_normalized_question(
    tmp_path,
):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("History Reuse Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (store_name TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?)",
            [("上海旗舰店", 26255.44), ("北京国贸店", 18400.0)],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    first = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天销售额最高的门店是谁？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 2"
        ),
    )
    exploding_provider = _SequenceProvider([])

    second = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="  最近90天销售额最高的门店是谁?   ",
        providers={"question_understanding": exploding_provider},
    )

    assert first["status"] == "completed"
    assert first["data_version"] == 1
    assert first["normalized_question"] == "最近90天销售额最高的门店是谁?"
    assert first["product_result"]["technical_details"]["data_version"] == 1
    assert second == {
        "status": "cache_candidate",
        "matched_run_id": first["run_id"],
        "message": "已找到同一数据版本下的历史分析",
        "workspace_id": workspace["workspace_id"],
        "data_version": 1,
        "normalized_question": "最近90天销售额最高的门店是谁?",
    }
    assert exploding_provider.requests == []


def test_workspace_analysis_does_not_reuse_after_data_version_changes(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Version Changed Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (store_name TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?)",
            [("上海旗舰店", 26255.44), ("北京国贸店", 18400.0)],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    first = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天销售额最高的门店是谁？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 2"
        ),
    )
    store.increment_data_version(workspace["workspace_id"])
    second = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天销售额最高的门店是谁？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 2"
        ),
    )

    assert first["data_version"] == 1
    assert second["status"] == "completed"
    assert second["run_id"] != first["run_id"]
    assert second["data_version"] == 2


def test_workspace_analysis_persists_progress_steps_for_history_detail(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Progress History Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (store_name TEXT, business_date TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [
                ("上海旗舰店", "2026-06-01", 26255.44),
                ("北京国贸店", "2026-06-02", 18400.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天销售额最高的门店是谁？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 2"
        ),
    )
    stored = WorkspaceRunStore(store).load_run_response(workspace["workspace_id"], result["run_id"])

    assert result["progress_steps"] == result["product_result"]["progress_steps"]
    assert stored["product_result"]["progress_steps"] == result["product_result"]["progress_steps"]
    assert [step["status"] for step in stored["product_result"]["progress_steps"]] == [
        "completed",
        "completed",
        "completed",
        "completed",
        "completed",
        "skipped",
    ]
    assert "SELECT" not in " ".join(step["summary"] for step in stored["product_result"]["progress_steps"])


def test_workspace_analysis_persists_fast_fact_context_pack_for_history_detail(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Fast Fact Context Pack History Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (store_name TEXT, business_date TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [
                ("上海旗舰店", "2026-06-01", 26255.44),
                ("北京国贸店", "2026-06-02", 18400.0),
                ("深圳湾店", "2026-06-03", 12000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天销售额最高的门店是谁？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 3"
        ),
    )
    stored = WorkspaceRunStore(store).load_run_response(workspace["workspace_id"], result["run_id"])

    pack = result["fast_fact_context_pack"]
    assert result["analysis_route"]["route"] == "fast_fact"
    assert pack["key_evidence_rows"][0]["dimensions"][0]["display_value"] == "上海旗舰店"
    assert result["technical_details"]["fast_fact_context_pack"] == pack
    assert result["product_result"]["technical_details"]["fast_fact_context_pack"] == pack
    assert stored["result"]["fast_fact_context_pack"] == pack
    assert stored["product_result"]["technical_details"]["fast_fact_context_pack"] == pack


def test_workspace_analysis_standard_route_is_not_forced_into_fast_fact_context_pack(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Standard Route No Fast Pack Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (store_name TEXT, sales_amount REAL, satisfaction_score REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [("上海旗舰店", 26255.44, 4.8), ("北京国贸店", 18400.0, 4.2)],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    business_answer_provider = _mock_chinese_business_answer_provider()

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="销售额、满意度综合看哪个门店最好？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales, AVG(satisfaction_score) AS satisfaction_score "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 2"
        ),
        providers={"business_answer": business_answer_provider},
    )

    assert result["analysis_route"]["route"] != "fast_fact"
    assert "fast_fact_context_pack" not in result
    assert "fast_fact_context_pack" not in result["technical_details"]
    assert "fast_fact_context_pack" not in result["product_result"]["technical_details"]
    assert result["product_result"]["technical_details"]["fact_payload"]["rows"] == result["execution_result"]["rows"]


def test_workspace_analysis_non_channel_judgment_answer_reads_like_business_chinese(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Service Issue Judgment Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE support_issues (issue_type TEXT, business_date TEXT, ticket_count INTEGER, avg_response_minutes REAL)"
        )
        conn.executemany(
            "INSERT INTO support_issues VALUES (?, ?, ?, ?)",
            [
                ("退款咨询", "2026-06-01", 320, 48.0),
                ("物流延迟", "2026-06-02", 180, 76.0),
                ("发票问题", "2026-06-03", 90, 22.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个客服问题最需要优先处理，为什么？",
        initial_sql=(
            "SELECT issue_type, SUM(ticket_count) AS ticket_count, AVG(avg_response_minutes) AS avg_response_minutes "
            "FROM support_issues GROUP BY issue_type ORDER BY ticket_count DESC LIMIT 3"
        ),
    )

    answer = result["product_result"]["business_answer"]
    text = _business_answer_text(answer)

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] != "fast_fact"
    assert "业务回答生成失败" in text
    assert "退款咨询" not in text
    assert "第 1 行" not in text
    assert "issue_type 为" not in text
    assert "ticket_count 为" not in text
    assert "ticket_count" not in text
    assert "avg_response_minutes" not in text
    assert answer["evidence_bullets"] == []
    assert "不能直接证明原因" not in answer["why"]
    assert "证据表第一行显示" not in text
    assert result["business_answer_generation"]["source"] == "provider_unavailable"
    assert "本轮排序证据中" not in text
    assert "execution_result" not in text
    assert "channel" not in text.lower()
    assert answer["recommendations"] == []
    assert result["product_result"]["evidence"]["table_preview"]["rows"]
    assert answer["direct_answer"] not in answer["recommendations"]


def test_standard_analysis_without_chart_request_keeps_full_answer_path_but_skips_visualization(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("No Chart Standard Analysis Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (store_name TEXT, sales_amount REAL, satisfaction_score REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [("上海旗舰店", 26255.44, 4.8), ("北京国贸店", 18400.0, 4.2)],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    business_answer_provider = _mock_chinese_business_answer_provider()

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="销售额、满意度综合看哪个门店最好？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales, AVG(satisfaction_score) AS satisfaction_score "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 2"
        ),
        providers={
            "business_answer": business_answer_provider,
        },
    )

    nodes = [event.get("node") for event in result.get("trace") or []]

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] != "fast_fact"
    assert "business_answer_agent" in nodes
    assert "insight_agent" not in nodes
    assert len(business_answer_provider.requests) == 1
    assert "visualization_agent" not in nodes
    assert result["product_result"]["chart_artifacts"] == []


def test_chartable_deep_analysis_generates_echarts_artifact_and_history_keeps_option(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P30 H3 Deep Chart Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (store_name TEXT, sales_amount REAL, satisfaction_score REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [("上海旗舰店", 26255.44, 4.8), ("北京国贸店", 18400.0, 4.2), ("深圳湾店", 9800.0, 3.9)],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="请对比各门店销售额和满意度，哪个门店最值得优先复盘？请给证据和风险边界。",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales, AVG(satisfaction_score) AS satisfaction_score "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 3"
        ),
        providers={"business_answer": _mock_chinese_business_answer_provider()},
    )

    nodes = [event.get("node") for event in result.get("trace") or []]
    artifact = result["product_result"]["chart_artifacts"][0]
    stored = WorkspaceRunStore(store).load_run_response(workspace["workspace_id"], result["run_id"])
    restored_artifact = stored["product_result"]["chart_artifacts"][0]

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] == "deep_judgment"
    assert "visualization_agent" in nodes
    assert artifact["renderer"] == "echarts"
    assert artifact["echarts_option"]["series"][0]["type"] in {"bar", "scatter"}
    assert artifact["image_path"].endswith(".png")
    assert artifact["image_url"].startswith(f"/api/workspaces/{workspace['workspace_id']}/artifacts/")
    assert artifact["evidence_refs"] == ["question_evidence_pack"]
    assert restored_artifact["echarts_option"] == artifact["echarts_option"]
    assert restored_artifact["image_url"] == artifact["image_url"]


def test_chart_generation_failure_does_not_block_business_answer(tmp_path, monkeypatch):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Chart Failure Isolation Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (store_name TEXT, sales_amount REAL, satisfaction_score REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [("上海旗舰店", 26255.44, 4.8), ("北京国贸店", 18400.0, 4.2)],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    def explode_visualization(*args, **kwargs):
        raise RuntimeError("chart renderer exploded after answer")

    monkeypatch.setattr("graph.nodes.run_visualization_agent", explode_visualization)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="请对比各门店销售额和满意度，用图表展示哪个门店最值得优先复盘？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales, AVG(satisfaction_score) AS satisfaction_score "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 2"
        ),
        providers={"business_answer": _mock_chinese_business_answer_provider()},
    )

    nodes = [event.get("node") for event in result.get("trace") or []]

    assert result["status"] == "completed"
    assert result["business_answer"]["headline"]
    assert result["product_result"]["business_answer"] == result["business_answer"]
    assert result["product_result"]["chart_artifacts"] == []
    assert result["chart_warning"] == "chart renderer exploded after answer"
    assert "business_answer_agent" in nodes
    assert "visualization_agent" in nodes


def test_workspace_analysis_support_issue_priority_aliases_are_business_labeled(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Service Issue Alias Priority Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE support_issues (issue_type TEXT, business_date TEXT, ticket_count INTEGER, avg_response_minutes REAL)"
        )
        conn.executemany(
            "INSERT INTO support_issues VALUES (?, ?, ?, ?)",
            [
                ("退款咨询", "2026-06-01", 320, 48.0),
                ("物流延迟", "2026-06-02", 180, 76.0),
                ("发票问题", "2026-06-03", 90, 22.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个客服问题最需要优先处理，为什么？",
        initial_sql=(
            "SELECT issue_type, "
            "SUM(ticket_count) AS total_tickets, "
            "AVG(avg_response_minutes) AS avg_response, "
            "SUM(ticket_count) * AVG(avg_response_minutes) AS priority_score "
            "FROM support_issues "
            "GROUP BY issue_type "
            "ORDER BY priority_score DESC "
            "LIMIT 3"
        ),
    )

    assert result["status"] == "completed"
    answer = result["product_result"]["business_answer"]
    text = _business_answer_text(answer)
    assert "业务回答生成失败" in text
    assert "退款咨询" not in text
    assert "不能直接证明原因" not in answer["why"]
    assert answer["recommendations"] == []
    assert answer["evidence_bullets"] == []
    assert result["product_result"]["evidence"]["table_preview"]["rows"]
    for forbidden in (
        "total_tickets",
        "avg_response",
        "priority_score",
        "第 1 行",
        "execution_result",
        "SQL",
        "raw rows",
    ):
        assert forbidden not in text


def test_workspace_analysis_provider_priority_question_preserves_comparison_scope(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Provider Priority Scope Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE support_issues (issue_type TEXT, business_date TEXT, ticket_count INTEGER, avg_response_minutes REAL)"
        )
        conn.executemany(
            "INSERT INTO support_issues VALUES (?, ?, ?, ?)",
            [
                ("退款咨询", "2026-06-01", 320, 48.0),
                ("物流延迟", "2026-06-02", 180, 76.0),
                ("发票问题", "2026-06-03", 90, 22.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    provider_sql = (
        "SELECT issue_type, "
        "SUM(ticket_count) AS total_tickets, "
        "AVG(avg_response_minutes) AS avg_response, "
        "SUM(ticket_count) * AVG(avg_response_minutes) AS priority_score "
        "FROM support_issues "
        "GROUP BY issue_type "
        "ORDER BY priority_score DESC "
        "LIMIT 1"
    )
    support_intent = {
        "strategy": "llm_candidate",
        "intent": {
            "metric": "priority_score",
            "dimension": "issue_type",
            "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近90天"},
            "filters": [],
            "operation": "recommendation",
            "limit": 3,
        },
        "missing_slots": [],
        "clarification_questions": [],
        "risk_flags": [],
        "reason": "需要对多个客服问题进行优先级判断。",
    }

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个客服问题最需要优先处理，为什么？",
        providers={
            "question_understanding": MockLLMProvider(support_intent),
            "sql_planning": MockLLMProvider(_provider_sql_plan()),
            "sql_candidate": MockLLMProvider(
                {"sql_candidates": [{"sql": provider_sql, "rationale": "Provider only returned one row."}]}
            ),
        },
    )

    assert result["status"] == "completed"
    assert result["comparison_scope_adjustment"]["applied"] is True
    assert result["execution_result"]["row_count"] >= 2
    assert "LIMIT 1" not in result["generated_sql"].upper()
    answer = result["product_result"]["business_answer"]
    text = _business_answer_text(answer)
    assert "业务回答生成失败" in text
    assert "退款咨询" not in text
    assert result["product_result"]["evidence"]["table_preview"]["rows"]
    for forbidden in (
        "total_tickets",
        "avg_response",
        "priority_score",
        "第 1 行",
        "execution_result",
        "SQL",
        "raw rows",
    ):
        assert forbidden not in text


def test_workspace_analysis_generates_generic_store_ranking_evidence_without_initial_sql(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Generic Store Evidence Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (sale_date TEXT, store_name TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [
                ("2026-06-01", "上海旗舰店", 300000.0),
                ("2026-06-02", "北京国贸店", 100000.0),
                ("2026-06-03", "深圳湾店", 80000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个门店销售额最高，为什么？",
    )

    fact_payload = result["product_result"]["evidence"]["fact_payload"]
    requirement = fact_payload["evidence_requirements"][0]

    assert result["status"] == "completed"
    assert "store_sales" in result["generated_sql"]
    assert "orders" not in result["generated_sql"]
    assert result["execution_result"]["rows"][0][0] == "上海旗舰店"
    assert fact_payload["display_values"][0]["门店"] == "上海旗舰店"
    assert fact_payload["display_values"][0]["销售额"] == "30.0 万"
    assert requirement["metrics"] == ["销售额"]
    assert requirement["dimensions"] == ["门店"]
    assert requirement["time_range"]["raw_text"] == "最近 90 天"
    assert requirement["calculation_type"] == "ranking"
    assert requirement["missing_evidence"] == []


def test_workspace_analysis_exposes_single_evidence_planning_surface(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Single Evidence Planning Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (sale_date TEXT, store_name TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [
                ("2026-06-01", "上海旗舰店", 300000.0),
                ("2026-06-02", "北京国贸店", 100000.0),
                ("2026-06-03", "深圳湾店", 80000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个门店销售额最高，为什么？",
    )

    trace_nodes = [event.get("node") for event in result.get("trace") or []]
    tool_names = [call["tool_name"] for call in result["question_evidence_pack"]["tool_calls"]]

    assert result["status"] == "completed"
    assert tool_names.count("evidence_planning") == 1
    assert "sql_planning" not in tool_names
    assert "evidence_planning_agent" in trace_nodes
    assert "sql_planning_router_agent" not in trace_nodes
    assert "analysis_planner_agent" not in trace_nodes
    assert trace_nodes.index("evidence_planning_agent") < trace_nodes.index("schema_agent")
    assert "sql_reviewer_agent" in trace_nodes
    assert "sql_executor_node" in trace_nodes
    assert result["execution_result"]["success"] is True


def test_provider_backed_evidence_planning_uses_one_planning_provider_surface(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Provider Evidence Planning Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE support_issues (issue_type TEXT, business_date TEXT, ticket_count INTEGER)")
        conn.executemany(
            "INSERT INTO support_issues VALUES (?, ?, ?)",
            [
                ("退款咨询", "2026-06-01", 320),
                ("物流延迟", "2026-06-02", 180),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    planning_provider = _SequenceProvider(
        [
            {
                "strategy": "template",
                "matched_template": "",
                "confidence": 0.9,
                "missing_slots": [],
                "clarification_questions": [],
                "risk_flags": [],
                "reason": "当前语义层可生成确定性证据 SQL。",
            }
        ]
    )

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个客服问题最需要优先处理，为什么？",
        providers={
            "question_understanding": MockLLMProvider(
                {
                    "strategy": "llm_candidate",
                    "intent": {
                        "metric": "工单数",
                        "dimension": "客服问题",
                        "time_range": {"type": "last_n_days", "value": 90, "raw_text": "最近90天"},
                        "filters": [],
                        "operation": "recommendation",
                        "limit": 20,
                    },
                    "missing_slots": [],
                    "clarification_questions": [],
                    "risk_flags": [],
                    "reason": "问题槽位完整，可以生成证据规划。",
                }
            ),
            "sql_planning": planning_provider,
        },
    )

    planning_trace = [
        event
        for event in result.get("trace") or []
        if event.get("node")
        in {"evidence_planning_agent", "sql_planning_router_agent", "analysis_planner_agent"}
    ]
    tool_names = [call["tool_name"] for call in result["question_evidence_pack"]["tool_calls"]]

    assert result["status"] == "completed"
    assert len(planning_provider.requests) == 1
    assert [event.get("node") for event in planning_trace] == ["evidence_planning_agent"]
    assert planning_trace[0]["provider_called"] is True
    assert result["evidence_planning"]["provider_called"] is True
    assert result["sql_planning"]["provider_called"] is True
    assert tool_names.count("evidence_planning") == 1
    assert "sql_review" in tool_names
    assert "sql_execution" in tool_names


def test_workspace_analysis_reuses_question_evidence_pack_cache_for_same_task(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Question Evidence Cache Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (sale_date TEXT, store_name TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [
                ("2026-06-01", "上海旗舰店", 300000.0),
                ("2026-06-02", "北京国贸店", 100000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    first = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个门店销售额最高？",
        force_reanalysis=True,
    )
    second = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个门店销售额最高？",
        force_reanalysis=True,
    )

    second_nodes = [event.get("node") for event in second.get("trace") or []]
    second_tool_names = [
        call["tool_name"]
        for call in second["question_evidence_pack"]["tool_calls"]
    ]

    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert second["question_evidence_cache"]["hit"] is True
    assert second["generated_sql"] == first["generated_sql"]
    assert second["execution_result"]["rows"] == first["execution_result"]["rows"]
    assert "question_evidence_cache" in second_nodes
    assert "sql_executor_node" not in second_nodes
    assert "question_evidence_cache" in second_tool_names
    assert {"sql_review", "sql_execution"}.issubset(second_tool_names)
    assert second["audit_result"]["supported_facts"]


def test_workspace_analysis_question_evidence_cache_invalidates_on_data_version_change(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Question Evidence Data Version Cache Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (sale_date TEXT, store_name TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [
                ("2026-06-01", "上海旗舰店", 300000.0),
                ("2026-06-02", "北京国贸店", 100000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    first = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个门店销售额最高？",
        force_reanalysis=True,
    )
    store.increment_data_version(workspace["workspace_id"])
    second = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个门店销售额最高？",
        force_reanalysis=True,
    )

    second_nodes = [event.get("node") for event in second.get("trace") or []]

    assert first["data_version"] == 1
    assert second["data_version"] == 2
    assert second["status"] == "completed"
    assert second.get("question_evidence_cache", {}).get("hit") is not True
    assert "question_evidence_cache" not in second_nodes
    assert "sql_executor_node" in second_nodes


def test_workspace_analysis_question_evidence_cache_invalidates_on_semantic_layer_change(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Question Evidence Semantic Cache Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (sale_date TEXT, store_name TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [
                ("2026-06-01", "上海旗舰店", 300000.0),
                ("2026-06-02", "北京国贸店", 100000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    first = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个门店销售额最高？",
        force_reanalysis=True,
    )
    semantic_path = Path(workspace["semantic_layer_path"])
    semantic_path.write_text(semantic_path.read_text(encoding="utf-8") + "\n# cache bust\n", encoding="utf-8")
    second = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个门店销售额最高？",
        force_reanalysis=True,
    )

    second_nodes = [event.get("node") for event in second.get("trace") or []]

    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert second.get("question_evidence_cache", {}).get("hit") is not True
    assert "question_evidence_cache" not in second_nodes
    assert "sql_executor_node" in second_nodes


def test_workspace_analysis_initial_sql_bypasses_question_evidence_cache(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Question Evidence Initial SQL Cache Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (sale_date TEXT, store_name TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [
                ("2026-06-01", "上海旗舰店", 300000.0),
                ("2026-06-02", "北京国贸店", 100000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    first = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个门店销售额最高？",
        force_reanalysis=True,
    )
    second = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪个门店销售额最高？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales ASC LIMIT 2"
        ),
        force_reanalysis=True,
    )

    second_nodes = [event.get("node") for event in second.get("trace") or []]

    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert second.get("question_evidence_cache", {}).get("hit") is not True
    assert "question_evidence_cache" not in second_nodes
    assert "sql_executor_node" in second_nodes
    assert second["execution_result"]["rows"][0][0] == "北京国贸店"


def test_workspace_analysis_generates_generic_product_contribution_share_without_initial_sql(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Generic Product Contribution Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE product_sales (sale_date TEXT, category_name TEXT, paid_amount REAL)")
        conn.executemany(
            "INSERT INTO product_sales VALUES (?, ?, ?)",
            [
                ("2026-06-01", "饮料", 120000.0),
                ("2026-06-02", "零食", 80000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天哪些品类贡献最大，占比多少？",
    )

    payload = result["product_result"]["evidence"]["fact_payload"]

    assert result["status"] == "completed"
    assert "product_sales" in result["generated_sql"]
    assert result["execution_result"]["rows"][0][0] == "饮料"
    share = next(item for item in payload["derived_metrics"] if item["metric_id"].endswith("_share"))

    assert payload["display_values"][0]["品类"] == "饮料"
    assert share["values"][0]["display_value"] == "60.0%"
    assert payload["evidence_requirements"][0]["calculation_type"] == "contribution"


def test_workspace_analysis_generates_generic_support_operational_evidence_without_initial_sql(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Generic Support Operations Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE support_tickets (ticket_date TEXT, team_name TEXT, ticket_count INTEGER, avg_response_minutes REAL, satisfaction_score REAL)"
        )
        conn.executemany(
            "INSERT INTO support_tickets VALUES (?, ?, ?, ?, ?)",
            [
                ("2026-06-01", "华东客服组", 120, 16.0, 4.8),
                ("2026-06-02", "华北客服组", 95, 35.0, 4.2),
                ("2026-06-03", "华南客服组", 80, 22.0, 4.5),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近30天哪个客服团队响应效率最好，是否影响满意度？",
    )

    payload = result["product_result"]["evidence"]["fact_payload"]
    requirement = payload["evidence_requirements"][0]

    assert result["status"] == "completed"
    assert "support_tickets" in result["generated_sql"]
    assert result["execution_result"]["rows"][0][0] == "华东客服组"
    assert payload["display_values"][0]["团队"] == "华东客服组"
    assert "平均响应时长" in payload["display_values"][0]
    assert "满意度" in payload["display_values"][0]
    assert requirement["calculation_type"] == "operational_efficiency"
    assert requirement["metrics"] == ["平均响应时长", "满意度"]


def test_sql_generator_does_not_fallback_to_old_demo_schema_for_store_review():
    from agents.sql_generator import run_sql_generator

    result = run_sql_generator(
        {
            "user_question": "帮我做一下门店经营复盘。",
            "analysis_task": {
                "task_type": "summary",
                "dimensions": ["门店"],
                "metrics": [],
                "time_range": {},
                "filters": [],
            },
            "metric_context": {"success": False, "matched_metrics": []},
            "sql_planning": {},
        }
    )

    sql = result.get("generated_sql") or ""
    reason = result["sql_generation"]["reason"]

    assert result["sql_generation"]["success"] is False
    assert sql == ""
    assert "当前工作区" in reason
    for stale_name in ("orders", "order_items", "products", "users", "city", "total_revenue", "order_date"):
        assert stale_name not in sql
        assert stale_name not in reason


def test_workspace_analysis_shell_can_be_restored_before_job_finishes(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Recoverable Run Workspace")

    shell = create_workspace_analysis_run_shell(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天销售额最高的门店是谁？",
    )
    stored = WorkspaceRunStore(store).load_run_response(workspace["workspace_id"], shell["run_id"])
    history = WorkspaceRunStore(store).list_runs(workspace["workspace_id"])

    assert shell["status"] == "running"
    assert shell["data_version"] == 1
    assert shell["normalized_question"] == "最近90天销售额最高的门店是谁?"
    assert stored["run_id"] == shell["run_id"]
    assert stored["result"]["status"] == "running"
    assert stored["result"]["original_question"] == "最近90天销售额最高的门店是谁？"
    assert stored["product_result"]["progress_steps"][2]["key"] == "querying"
    assert stored["product_result"]["progress_steps"][2]["status"] == "running"
    assert history[0]["run_id"] == shell["run_id"]
    assert history[0]["status"] == "running"
    assert history[0]["question"] == "最近90天销售额最高的门店是谁？"


def test_workspace_analysis_job_updates_same_run_id_when_completed(tmp_path, monkeypatch):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Recoverable Completion Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE store_sales (store_name TEXT, sales_amount REAL)")
        conn.execute("INSERT INTO store_sales VALUES ('上海旗舰店', 26255.44)")

    shell = create_workspace_analysis_run_shell(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天销售额最高的门店是谁？",
    )

    def complete_workflow(*, run_id, workspace_root, trace_dir, user_question, **kwargs):
        return {
            "status": "completed",
            "run_id": run_id,
            "workspace_root": workspace_root,
            "trace_path": str(trace_dir / f"{run_id}.json"),
            "original_question": user_question,
            "final_answer": "上海旗舰店销售额最高。",
            "execution_result": {
                "success": True,
                "columns": ["store_name", "total_sales"],
                "rows": [["上海旗舰店", 26255.44]],
            },
            "evidence_result": {"validation_status": "passed"},
            "trace": [],
        }

    monkeypatch.setattr("workspaces.analysis_runner.run_workflow", complete_workflow)

    result = execute_workspace_analysis_job(
        store=store,
        workspace_id=workspace["workspace_id"],
        run_id=shell["run_id"],
        user_question="最近90天销售额最高的门店是谁？",
    )
    stored = WorkspaceRunStore(store).load_run_response(workspace["workspace_id"], shell["run_id"])

    assert result["run_id"] == shell["run_id"]
    assert result["status"] == "completed"
    assert stored["run_id"] == shell["run_id"]
    assert stored["result"]["status"] == "completed"
    assert stored["product_result"]["status"] == "completed"
    assert stored["product_result"]["business_answer"]["headline"]
    assert stored["result"]["data_version"] == shell["data_version"]
    assert stored["result"]["normalized_question"] == shell["normalized_question"]


def test_workspace_analysis_job_persists_failed_state_for_recovery(tmp_path, monkeypatch):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Recoverable Failure Workspace")
    shell = create_workspace_analysis_run_shell(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="分析不存在字段",
    )

    def fail_workflow(*args, **kwargs):
        raise RuntimeError("workflow exploded")

    monkeypatch.setattr("workspaces.analysis_runner.run_workflow", fail_workflow)

    result = execute_workspace_analysis_job(
        store=store,
        workspace_id=workspace["workspace_id"],
        run_id=shell["run_id"],
        user_question="分析不存在字段",
    )
    stored = WorkspaceRunStore(store).load_run_response(workspace["workspace_id"], shell["run_id"])

    assert result["status"] == "failed"
    assert "workflow exploded" in result["error_message"]
    assert stored["result"]["status"] == "failed"
    assert stored["result"]["error_message"] == "workflow exploded"
    assert stored["product_result"]["status"] == "failed"
    assert stored["product_result"]["progress_steps"][-2]["status"] == "failed"


def test_workspace_analysis_job_persists_waiting_for_clarification_for_recovery(tmp_path, monkeypatch):
    store, workspace = _create_ecommerce_workspace(tmp_path)
    shell = create_workspace_analysis_run_shell(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="帮我看看销售情况",
    )

    def wait_for_clarification(*, run_id, workspace_root, trace_dir, user_question, **kwargs):
        return {
            "status": "waiting_for_clarification",
            "run_id": run_id,
            "workspace_root": workspace_root,
            "trace_path": str(trace_dir / f"{run_id}.json"),
            "original_question": user_question,
            "question_understanding": {"missing_slots": ["time_range"]},
            "clarification_result": {
                "requires_clarification": True,
                "missing_slots": ["time_range"],
                "clarification_questions": ["请补充时间范围，例如最近90天。"],
            },
            "clarification_questions": ["请补充时间范围，例如最近90天。"],
            "final_answer": "需要补充信息后才能继续分析。",
            "execution_result": {},
            "trace": [],
        }

    monkeypatch.setattr("workspaces.analysis_runner.run_workflow", wait_for_clarification)

    result = execute_workspace_analysis_job(
        store=store,
        workspace_id=workspace["workspace_id"],
        run_id=shell["run_id"],
        user_question="帮我看看销售情况",
    )
    stored = WorkspaceRunStore(store).load_run_response(workspace["workspace_id"], shell["run_id"])

    assert result["status"] == "waiting_for_clarification"
    assert result["run_id"] == shell["run_id"]
    assert stored["result"]["status"] == "waiting_for_clarification"
    assert stored["product_result"]["question_thread"]["thread_id"] == shell["run_id"]
    assert stored["product_result"]["question_thread"]["clarification_question"] == "请补充时间范围，例如最近90天。"


def test_submit_workspace_analysis_run_cache_candidate_does_not_create_background_shell(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Recoverable Cache Workspace")
    run_id = "run_completed"
    run_dir = Path(workspace["root_path"]) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / f"{run_id}.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "completed",
                "workspace_id": workspace["workspace_id"],
                "data_version": 1,
                "normalized_question": "最近90天销售额最高的门店是谁?",
                "original_question": "最近90天销售额最高的门店是谁？",
                "saved_at": "2026-07-02T10:00:00Z",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = submit_workspace_analysis_run(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="最近90天销售额最高的门店是谁？",
    )

    assert result["status"] == "cache_candidate"
    assert result["matched_run_id"] == run_id
    assert len(WorkspaceRunStore(store).list_runs(workspace["workspace_id"])) == 1


def test_workspace_analysis_persists_waiting_clarification_thread(tmp_path):
    store, workspace = _create_ecommerce_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="帮我看看销售情况",
    )

    assert result["status"] == "waiting_for_clarification"
    thread = result["product_result"]["question_thread"]
    assert thread["status"] == "waiting_for_clarification"
    assert thread["thread_id"] == result["run_id"]
    assert thread["original_question"] == "帮我看看销售情况"
    assert thread["clarification_question"]
    assert "generated_sql" not in result


def test_waiting_for_clarification_follow_up_updates_same_run_id(tmp_path, monkeypatch):
    store, workspace = _create_ecommerce_workspace(tmp_path)
    calls = []

    def workflow_sequence(*, run_id, user_question, trace_dir, workspace_root, **kwargs):
        calls.append({"run_id": run_id, "user_question": user_question, "trace_dir": trace_dir})
        if len(calls) == 1:
            return {
                "status": "waiting_for_clarification",
                "run_id": run_id,
                "workspace_root": workspace_root,
                "trace_path": str(trace_dir / f"{run_id}.json"),
                "original_question": user_question,
                "question_understanding": {"missing_slots": ["time_range"]},
                "analysis_task": {
                    "resolved_question": user_question,
                    "missing_slots": ["time_range"],
                    "business_lens": {"business_domain": "sales", "metrics": [{"label": "销售额"}]},
                },
                "clarification_result": {
                    "requires_clarification": True,
                    "missing_slots": ["time_range"],
                    "clarification_questions": ["请补充时间范围，例如最近90天。"],
                },
                "clarification_questions": ["请补充时间范围，例如最近90天。"],
                "final_answer": "需要补充信息后才能继续分析。",
                "execution_result": {},
                "trace": [],
            }
        assert run_id == calls[0]["run_id"]
        assert "帮我看看销售情况" in user_question
        assert "最近 90 天" in user_question
        return {
            "status": "completed",
            "run_id": run_id,
            "workspace_root": workspace_root,
            "trace_path": str(trace_dir / f"{run_id}.json"),
            "analysis_task": {
                "resolved_question": user_question,
                "business_lens": {"business_domain": "sales", "metrics": [{"label": "销售额"}]},
            },
            "business_answer": {
                "headline": "最近 90 天销售额已完成分析",
                "direct_answer": "最近 90 天销售额为 250。",
                "why": "证据表汇总了 paid 订单。",
                "evidence_bullets": ["销售额合计为 250。"],
                "recommendations": [],
                "caveats": [],
                "confidence": "medium",
            },
            "execution_result": {"success": True, "columns": ["revenue"], "rows": [[250.0]]},
            "trace": [],
        }

    monkeypatch.setattr("workspaces.analysis_runner.run_workflow", workflow_sequence)

    pending = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="帮我看看销售情况",
    )
    result = run_workspace_analysis_follow_up(
        store=store,
        workspace_id=workspace["workspace_id"],
        run_id=pending["run_id"],
        message="最近 90 天",
    )
    history = WorkspaceRunStore(store).list_runs(workspace["workspace_id"])

    assert result["status"] == "completed"
    assert result["run_id"] == pending["run_id"]
    assert len(history) == 1
    assert history[0]["run_id"] == pending["run_id"]
    memory = result["analysis_thread_memory"]
    assert memory["thread_id"] == pending["run_id"]
    assert memory["original_question"] == "帮我看看销售情况"
    assert memory["latest_status"] == "completed"
    assert memory["pending_clarification"] is None
    assert len(memory["turns"]) == 2
    assert memory["turns"][1]["user_input"] == "最近 90 天"
    assert result["product_result"]["question_thread"]["thread_id"] == pending["run_id"]


def test_completed_run_follow_up_appends_new_turn_to_same_thread(tmp_path, monkeypatch):
    store, workspace = _create_channel_workspace(tmp_path)
    calls = []

    def workflow_sequence(*, run_id, user_question, trace_dir, workspace_root, **kwargs):
        calls.append(user_question)
        if len(calls) == 1:
            return {
                "status": "completed",
                "run_id": run_id,
                "workspace_root": workspace_root,
                "trace_path": str(trace_dir / f"{run_id}.json"),
                "analysis_task": {
                    "resolved_question": user_question,
                    "business_lens": {
                        "business_domain": "channel_performance",
                        "metrics": [{"label": "收入", "source_table": "orders", "source_field": "revenue"}],
                        "dimensions": [{"label": "渠道", "source_table": "orders", "source_field": "channel"}],
                    },
                },
                "business_answer": {
                    "headline": "email 渠道收入最高",
                    "direct_answer": "email 渠道收入最高。",
                    "why": "证据表显示 email 收入最高。",
                    "evidence_bullets": ["email 收入为 240。"],
                    "recommendations": [],
                    "caveats": [],
                    "confidence": "medium",
                },
                "question_evidence_pack": {
                    "task": {
                        "business_lens": {
                            "business_domain": "channel_performance",
                            "metrics": [{"label": "收入"}],
                        }
                    },
                    "rows": [{"channel": "email", "revenue": 240.0}],
                    "columns": ["channel", "revenue"],
                },
                "question_evidence_ledger": {
                    "ledger_id": "qledger_first",
                    "business_lens": {"business_domain": "channel_performance"},
                    "question_evidence_plan": {"plan_id": "qplan_first", "groups": ["group_first"]},
                    "evidence_groups": [
                        {
                            "group_id": "group_first",
                            "purpose": "关键事实",
                            "source": {"tables": ["orders"], "fields": ["channel", "revenue"]},
                            "dimension": {"role": "dimension", "label": "渠道", "source_columns": ["channel"]},
                            "metrics": [
                                {
                                    "role": "metric",
                                    "label": "收入",
                                    "source_column": "revenue",
                                    "source_fields": ["revenue"],
                                    "unit": "currency",
                                }
                            ],
                            "time_policy": "最近90天",
                            "row_grain": "渠道",
                            "supports_answer": True,
                            "supports_chart": True,
                            "evidence_refs": ["evidence:row:0:revenue"],
                            "facts": [
                                {
                                    "fact_id": "fact_1",
                                    "label": "收入",
                                    "value": 240.0,
                                    "dimension": {"channel": "email"},
                                    "source_columns": ["channel", "revenue"],
                                    "evidence_ref": "evidence:row:0:revenue",
                                }
                            ],
                            "derived_metrics": [],
                        }
                    ],
                    "facts": [
                        {
                            "fact_id": "fact_1",
                            "label": "收入",
                            "value": 240.0,
                            "unit": "",
                            "dimension": {"channel": "email"},
                            "source_columns": ["channel", "revenue"],
                            "source_row_refs": ["row:0"],
                            "evidence_ref": "evidence:row:0:revenue",
                        }
                    ],
                    "derived_metrics": [],
                    "data_limits": [],
                    "tool_calls": [],
                    "evidence_refs": ["evidence:row:0:revenue"],
                    "chart_refs": [],
                    "source_pack_id": "question_evidence_pack",
                    "confidence": "medium",
                },
                "execution_result": {"success": True, "columns": ["channel", "revenue"], "rows": [["email", 240.0]]},
                "trace": [],
            }
        assert "帮我分析最近90天哪些渠道收益比较好" in user_question
        assert "email 渠道收入最高" in user_question
        assert "为什么 email 渠道收益最好" in user_question
        return {
            "status": "completed",
            "run_id": run_id,
            "workspace_root": workspace_root,
            "trace_path": str(trace_dir / f"{run_id}.json"),
            "analysis_task": {
                "resolved_question": user_question,
                "business_lens": {"business_domain": "channel_performance", "metrics": [{"label": "客单价"}]},
            },
            "business_answer": {
                "headline": "email 的客单价更高",
                "direct_answer": "email 渠道收益高主要来自客单价。",
                "why": "本轮证据补充比较了客单价。",
                "evidence_bullets": ["email 客单价更高。"],
                "recommendations": [],
                "caveats": [],
                "confidence": "medium",
            },
            "question_evidence_ledger": {
                "ledger_id": "qledger_follow_up",
                "business_lens": {"business_domain": "channel_performance"},
                "question_evidence_plan": {"plan_id": "qplan_follow_up", "groups": ["group_follow_up"]},
                "evidence_groups": [
                    {
                        "group_id": "group_follow_up",
                        "purpose": "关键事实",
                        "source": {"tables": ["orders"], "fields": ["channel", "avg_order_value"]},
                        "dimension": {"role": "dimension", "label": "渠道", "source_columns": ["channel"]},
                        "metrics": [
                            {
                                "role": "metric",
                                "label": "客单价",
                                "source_column": "avg_order_value",
                                "source_fields": ["avg_order_value"],
                                "unit": "currency",
                            }
                        ],
                        "time_policy": "最近90天",
                        "row_grain": "渠道",
                        "supports_answer": True,
                        "supports_chart": True,
                        "evidence_refs": ["evidence:row:0:avg_order_value"],
                        "facts": [
                            {
                                "fact_id": "fact_1",
                                "label": "客单价",
                                "value": 120.0,
                                "dimension": {"channel": "email"},
                                "source_columns": ["channel", "avg_order_value"],
                                "evidence_ref": "evidence:row:0:avg_order_value",
                            }
                        ],
                        "derived_metrics": [],
                    }
                ],
                "facts": [
                    {
                        "fact_id": "fact_1",
                        "label": "客单价",
                        "value": 120.0,
                        "unit": "",
                        "dimension": {"channel": "email"},
                        "source_columns": ["channel", "avg_order_value"],
                        "source_row_refs": ["row:0"],
                        "evidence_ref": "evidence:row:0:avg_order_value",
                    }
                ],
                "derived_metrics": [],
                "data_limits": [],
                "tool_calls": [],
                "evidence_refs": ["evidence:row:0:avg_order_value"],
                "chart_refs": [],
                "source_pack_id": "question_evidence_pack",
                "confidence": "medium",
            },
            "execution_result": {"success": True, "columns": ["channel", "avg_order_value"], "rows": [["email", 120.0]]},
            "trace": [],
        }

    monkeypatch.setattr("workspaces.analysis_runner.run_workflow", workflow_sequence)

    first = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="帮我分析最近90天哪些渠道收益比较好",
    )
    follow_up = run_workspace_analysis_follow_up(
        store=store,
        workspace_id=workspace["workspace_id"],
        run_id=first["run_id"],
        message="为什么 email 渠道收益最好？",
    )

    assert follow_up["run_id"] == first["run_id"]
    memory = follow_up["analysis_thread_memory"]
    assert memory["thread_id"] == first["run_id"]
    assert memory["answer_summary"] == "email 渠道收益高主要来自客单价。"
    assert memory["latest_status"] == "completed"
    assert memory["latest_resolved_question"] == calls[1]
    assert len(memory["turns"]) == 2
    assert memory["turns"][0]["answer_summary"] == "email 渠道收入最高。"
    assert memory["turns"][1]["user_input"] == "为什么 email 渠道收益最好？"
    assert "question_evidence_ledger:qledger_follow_up" in memory["evidence_refs"]
    product_text = json.dumps(follow_up["product_result"], ensure_ascii=False)
    assert "qledger_follow_up" not in product_text
    assert follow_up["product_result"]["question_thread"]["evidence_refs"] == ["question_evidence_pack"]
    assert follow_up["product_result"]["question_evidence_ledger"]["question_evidence_plan"]["groups"] == [
        "group_follow_up"
    ]
    assert follow_up["product_result"]["question_evidence_ledger"]["evidence_groups"][0]["group_id"] == "group_follow_up"
    assert WorkspaceRunStore(store).list_runs(workspace["workspace_id"])[0]["run_id"] == first["run_id"]


def test_partial_clarification_follow_up_remains_waiting_in_same_thread(tmp_path, monkeypatch):
    store, workspace = _create_ecommerce_workspace(tmp_path)
    calls = []

    def workflow_sequence(*, run_id, user_question, trace_dir, workspace_root, **kwargs):
        calls.append(user_question)
        question = "请补充时间范围，例如最近90天。" if len(calls) == 2 else "请补充要分析的指标和时间范围。"
        missing = ["time_range"] if len(calls) == 2 else ["metric", "time_range"]
        return {
            "status": "waiting_for_clarification",
            "run_id": run_id,
            "workspace_root": workspace_root,
            "trace_path": str(trace_dir / f"{run_id}.json"),
            "analysis_task": {
                "resolved_question": user_question,
                "metrics": ["花费"] if len(calls) == 2 else [],
                "missing_slots": missing,
                "business_lens": {"business_domain": "channel_performance", "metrics": []},
            },
            "question_understanding": {"missing_slots": missing},
            "clarification_result": {
                "requires_clarification": True,
                "missing_slots": missing,
                "clarification_questions": [question],
            },
            "clarification_questions": [question],
            "final_answer": "需要补充信息后才能继续分析。",
            "execution_result": {},
            "trace": [],
        }

    monkeypatch.setattr("workspaces.analysis_runner.run_workflow", workflow_sequence)

    pending = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="帮我分析渠道表现，看看哪个渠道该加预算",
    )
    result = run_workspace_analysis_follow_up(
        store=store,
        workspace_id=workspace["workspace_id"],
        run_id=pending["run_id"],
        message="花费",
    )

    assert result["status"] == "waiting_for_clarification"
    assert result["run_id"] == pending["run_id"]
    assert len(WorkspaceRunStore(store).list_runs(workspace["workspace_id"])) == 1
    memory = result["analysis_thread_memory"]
    assert memory["latest_status"] == "waiting_for_clarification"
    assert memory["pending_clarification"]["clarification_question"] == "请补充时间范围，例如最近90天。"
    assert memory["turns"][1]["user_input"] == "花费"


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
