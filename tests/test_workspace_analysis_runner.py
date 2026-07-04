import json
import sqlite3
from pathlib import Path

from llm_ops.provider import MockLLMProvider
from workspaces.analysis_runner import (
    create_workspace_analysis_run_shell,
    execute_workspace_analysis_job,
    submit_workspace_analysis_run,
    run_workspace_analysis,
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
    assert any(event.get("node") == "fast_fact_composer" for event in result["trace"])
    assert fact_payload["comparison_scope"]["row_count"] == 3
    assert fact_payload["comparison_scope"]["sufficient"] is True
    assert fact_payload["rows"] == result["execution_result"]["rows"]
    assert fact_payload["display_values"][0]["门店"] == "上海旗舰店"
    assert fact_payload["display_values"][0]["总收入"] == "2.6 万"
    assert fact_payload["formulas"]
    assert "technical_sql" not in result["product_result"]["technical_details"]["fact_payload"]
    assert result["product_result"]["technical_details"]["sql"].startswith("SELECT store_name")


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
    assert stored["result"]["analysis_route"] == result["analysis_route"]
    assert stored["product_result"]["analysis_route"] == result["product_result"]["analysis_route"]
    assert stored["product_result"]["business_answer"] == result["product_result"]["business_answer"]
    assert stored["product_result"]["evidence"]["table_preview"]["rows"] == result["product_result"]["evidence"][
        "table_preview"
    ]["rows"]
    assert stored["product_result"]["technical_details"]["sql"] == result["generated_sql"]
    assert stored["result"]["product_result"]["question_thread"]["original_question"] == "按渠道汇总收入"


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

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="销售额、满意度综合看哪个门店最好？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales, AVG(satisfaction_score) AS satisfaction_score "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 2"
        ),
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
    assert "退款咨询" in text
    assert "工单数" in text or "ticket_count" not in text
    assert "第 1 行" not in text
    assert "issue_type 为" not in text
    assert "ticket_count 为" not in text
    assert "ticket_count" not in text
    assert "avg_response_minutes" not in text
    evidence_text = " ".join(answer["evidence_bullets"])
    if evidence_text:
        assert "退款咨询" in evidence_text
        assert "工单" in evidence_text
        assert "第 1 行" not in evidence_text
        assert "issue_type 为" not in evidence_text
    assert "不能直接证明原因" in answer["why"]
    assert any(marker in answer["why"] for marker in ("问题发生频次", "处理复杂度", "服务流程"))
    assert "证据表第一行显示" not in text
    assert "本轮排序证据中" not in text
    assert "execution_result" not in text
    assert "channel" not in text.lower()
    assert answer["recommendations"]
    assert answer["direct_answer"] not in answer["recommendations"]


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
    assert "退款咨询" in text
    assert "物流延迟" in text
    assert "工单数" in text or "总工单数" in text
    assert "平均响应时长" in text
    assert "优先级评分" in text or "判断口径" in text
    assert any(marker in text for marker in ("按平均响应时长", "判断口径", "不同指标", "如果目标"))
    assert "不能直接证明原因" in answer["why"]
    assert answer["recommendations"]
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
    assert "退款咨询" in text
    assert "物流延迟" in text
    assert "工单数" in text or "总工单数" in text
    assert "平均响应时长" in text
    assert "优先级评分" in text or "判断口径" in text
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
    assert result["pending_run_id"].startswith("pending_")
    assert stored["result"]["status"] == "waiting_for_clarification"
    assert stored["product_result"]["question_thread"]["pending_run_id"] == result["pending_run_id"]
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

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Continuation Current Product Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE product_sales (sale_date TEXT, product_name TEXT, paid_amount REAL)")
        conn.executemany(
            "INSERT INTO product_sales VALUES (?, ?, ?)",
            [
                ("2026-06-01", "咖啡豆", 3000.0),
                ("2026-06-02", "挂耳咖啡", 1800.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
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


def test_workspace_analysis_partial_continuation_remains_waiting_for_clarification(tmp_path, monkeypatch):
    from workspaces.analysis_runner import run_workspace_analysis_continuation
    from workspaces.pending_clarification_store import PendingClarificationStore

    store, workspace = _create_ecommerce_workspace(tmp_path)
    pending_store = PendingClarificationStore(store)
    pending = pending_store.create_pending_run(
        workspace_id=workspace["workspace_id"],
        run_id="run_pending",
        original_question="帮我分析渠道表现，看看哪个渠道该加预算",
        question_understanding={
            "strategy": "clarify",
            "analysis_task": {
                "task_type": "recommendation",
                "dimensions": ["渠道"],
                "metrics": [],
                "time_range": None,
                "filters": [],
                "decision_goal": "判断哪个渠道该加预算",
                "missing_slots": ["metric", "time_range"],
                "defaults_applied": [],
                "resolved_question": "帮我分析渠道表现，看看哪个渠道该加预算",
                "output_language": "zh",
                "confidence": "medium",
            },
            "missing_slots": ["metric", "time_range"],
        },
        clarification_question="请补充要分析的指标和时间范围，例如：最近90天看销售额。",
        raw_result={"status": "waiting_for_clarification"},
        missing_fields=["metric", "time_range"],
    )

    def wait_for_more_info(*, user_question, **kwargs):
        assert "帮我分析渠道表现" in user_question
        assert "花费" in user_question
        return {
            "status": "waiting_for_clarification",
            "run_id": kwargs["run_id"],
            "workspace_root": workspace["root_path"],
            "trace_path": "",
            "question_understanding": {
                "strategy": "clarify",
                "analysis_task": {
                    "task_type": "recommendation",
                    "dimensions": ["渠道"],
                    "metrics": ["花费"],
                    "time_range": None,
                    "filters": [],
                    "decision_goal": "判断哪个渠道该加预算",
                    "missing_slots": ["time_range"],
                    "defaults_applied": [],
                    "resolved_question": user_question,
                    "output_language": "zh",
                    "confidence": "medium",
                },
                "missing_slots": ["time_range"],
                "clarification_questions": ["请补充时间范围，例如最近90天。"],
            },
            "clarification_result": {
                "requires_clarification": True,
                "missing_slots": ["time_range"],
                "clarification_questions": ["请补充时间范围，例如最近90天。"],
            },
            "clarification_questions": ["请补充时间范围，例如最近90天。"],
            "final_answer": "需要补充信息后才能继续分析：请补充时间范围，例如最近90天。",
            "execution_result": {},
            "trace": [],
        }

    monkeypatch.setattr("workspaces.analysis_runner.run_workflow", wait_for_more_info)

    result = run_workspace_analysis_continuation(
        store=store,
        workspace_id=workspace["workspace_id"],
        pending_run_id=pending["pending_run_id"],
        clarification_answer="花费",
    )

    assert result["status"] == "waiting_for_clarification"
    assert result["pending_run_id"] == pending["pending_run_id"]
    assert result["clarification_question"] == "请补充时间范围，例如最近90天。"
    assert "花费" in result["resolved_question"]
    stored = pending_store.load_pending_run(workspace["workspace_id"], pending["pending_run_id"])
    assert stored["status"] == "pending"
    assert stored["missing_fields"] == ["time_range"]
    assert stored["clarification_answer"] == "花费"
    assert "花费" in stored["resolved_question"]


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
