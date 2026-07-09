import sqlite3
import json

from llm_ops.provider import MockLLMProvider
from workspaces.context_pack_builder import build_fast_fact_context_pack
from workspaces.analysis_runner import run_workspace_analysis
from workspaces.profiler import profile_workspace_database
from workspaces.run_store import WorkspaceRunStore
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


def _answer_text(answer):
    return "\n".join(
        [
            answer["headline"],
            answer["direct_answer"],
            answer["why"],
            *answer["evidence_bullets"],
            *answer["recommendations"],
            *answer["caveats"],
        ]
    )


def _trace_nodes(result):
    return [event.get("node") for event in result.get("trace") or []]


def _assert_no_provider_answer_boundary(answer):
    text = _answer_text(answer)
    assert "业务回答生成失败" in text or "无可用模型" in text or "业务回答缺失" in text
    assert answer["recommendations"] == []


class _CountingProvider:
    model = "counting-provider"

    def __init__(self):
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        raise AssertionError("provider should not be called")


class _FastFactAnswerProvider:
    model = "fast-fact-answer-provider"

    def __init__(self):
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return {
            "candidate_claims": [{"claim": "私域社群收入为 180000.0。", "category": "hard_fact"}],
            "business_answer": {
                "headline": "私域社群收入最高",
                "direct_answer": "最近90天收入最高的是私域社群，收入为 180000.0。",
                "why": "证据账本显示私域社群的收入高于其他渠道。",
                "evidence_bullets": ["私域社群收入为 180000.0。"],
                "recommendations": [],
                "caveats": ["结论只基于本轮证据账本中的事实。"],
                "confidence": "high",
            },
        }


def _prepare_store_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Fast Fact Store Workspace")
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
    return store, workspace


def _prepare_channel_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Fast Fact Channel Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE channel_sales (sale_date TEXT, channel_name TEXT, revenue REAL)")
        conn.executemany(
            "INSERT INTO channel_sales VALUES (?, ?, ?)",
            [
                ("2026-06-09", "搜索广告", 120000.0),
                ("2026-06-10", "私域社群", 180000.0),
                ("2026-06-12", "直播间", 90000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace


def _prepare_customer_segment_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Fast Fact Customer Segment Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE customer_revenue (sale_date TEXT, segment_name TEXT, revenue REAL)")
        conn.executemany(
            "INSERT INTO customer_revenue VALUES (?, ?, ?)",
            [
                ("2026-01-05", "高价值会员", 300000.0),
                ("2026-03-10", "新客", 140000.0),
                ("2026-06-18", "沉睡唤醒", 90000.0),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace


def _prepare_trend_workspace(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Fast Fact Trend Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute("CREATE TABLE orders (order_date TEXT, order_count INTEGER)")
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?)",
            [
                ("2026-07-01", 120),
                ("2026-07-08", 150),
                ("2026-07-15", 180),
            ],
        )
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace


def test_fast_fact_total_uses_short_path_and_keeps_technical_details(tmp_path):
    store, workspace = _prepare_store_workspace(tmp_path)

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近90天总销售额是多少？",
        initial_sql="SELECT SUM(sales_amount) AS total_sales FROM store_sales",
    )

    answer = result["product_result"]["business_answer"]
    text = _answer_text(answer)
    nodes = _trace_nodes(result)

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] == "fast_fact"
    _assert_no_provider_answer_boundary(answer)
    assert "SELECT " not in text.upper()
    assert "raw_rows" not in text
    assert "execution_result" not in text
    assert "fact_payload" not in text
    assert "sql_reviewer_agent" in nodes
    assert "sql_executor_node" in nodes
    assert "evidence_validator_agent" in nodes
    assert "fast_fact_evidence_preparer" in nodes
    assert "business_answer_agent" in nodes
    assert "question_evidence_pack" in result
    assert result["audit_result"]["supported_facts"]
    assert result["product_result"]["technical_details"]["audit_result"] == result["audit_result"]
    assert result["question_evidence_pack"]["columns"] == result["execution_result"]["columns"]
    assert result["question_evidence_pack"]["rows"][0]["total_sales"] == 56655.44
    assert {call["tool_name"] for call in result["question_evidence_pack"]["tool_calls"]} >= {
        "schema_lookup",
        "metric_lookup",
        "sql_review",
        "sql_execution",
    }
    assert result["product_result"]["technical_details"]["question_evidence_pack"]["columns"] == [
        "total_sales"
    ]
    assert "insight_agent" not in nodes
    assert "claim_typing_agent" not in nodes
    assert "final_answer_composer" not in nodes
    assert "visualization_agent" not in nodes
    assert result["product_result"]["chart_artifacts"] == []
    assert result["technical_details"]["sql"].startswith("SELECT SUM")
    assert result["technical_details"]["raw_rows"] == result["execution_result"]["rows"]
    assert "technical_sql" not in result["technical_details"]["fact_payload"]
    assert result["technical_details"]["fact_payload"]["technical_refs"]["sql"] == "technical_details.sql"


def test_fast_fact_channel_ranking_without_initial_sql_uses_answer_provider_from_ledger(tmp_path):
    store, workspace = _prepare_channel_workspace(tmp_path)
    business_answer_provider = _FastFactAnswerProvider()

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近90天哪个渠道收入最高？",
        providers={"business_answer": business_answer_provider},
    )

    nodes = _trace_nodes(result)
    tool_names = {call["tool_name"] for call in result["question_evidence_pack"]["tool_calls"]}

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] == "fast_fact"
    assert result["execution_result"]["success"] is True
    assert result["execution_result"]["rows"][0][0] == "私域社群"
    assert "evidence_planning" in tool_names
    assert {"schema_lookup", "metric_lookup", "sql_review", "sql_execution"}.issubset(tool_names)
    assert "sql_reviewer_agent" in nodes
    assert "sql_executor_node" in nodes
    assert "evidence_validator_agent" in nodes
    assert "fast_fact_evidence_preparer" in nodes
    assert "business_answer_agent" in nodes
    assert "visualization_agent" not in nodes
    assert len(business_answer_provider.requests) == 1
    prompt = business_answer_provider.requests[0].prompt
    assert "Question evidence ledger" in prompt
    assert "Execution result" not in prompt
    assert "SELECT" not in prompt.upper()
    assert "task_id" not in prompt
    assert "task_purpose" not in prompt
    assert "raw_rows" not in prompt
    assert "trace" not in prompt.lower()
    assert "provider_metadata" not in prompt
    assert result["product_result"]["business_answer"] == result["business_answer"]
    assert result["product_result"]["evidence"]["validation_status"] == "validated"
    technical_pack = result["product_result"]["technical_details"]["question_evidence_pack"]
    assert technical_pack["rows"][0] == result["question_evidence_pack"]["rows"][0]
    assert "私域社群" in technical_pack["rows"][0].values()


def test_fast_fact_channel_ranking_with_fact_scope_retains_top_n_candidates(tmp_path):
    store, workspace = _prepare_channel_workspace(tmp_path)
    business_answer_provider = _FastFactAnswerProvider()

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近30天哪个渠道收入最高？只回答事实和口径。",
        providers={"business_answer": business_answer_provider},
    )

    rows = result["execution_result"]["rows"]
    ledger_group = result["question_evidence_ledger"]["evidence_groups"][0]

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] == "fast_fact"
    assert "fast_fact_evidence_preparer" in _trace_nodes(result)
    assert "business_answer_agent" in _trace_nodes(result)
    assert len(business_answer_provider.requests) == 1
    assert len(rows) >= 3
    assert rows[0][0] == "私域社群"
    assert len(result["question_evidence_pack"]["rows"]) >= 3
    assert len(ledger_group["facts"]) >= 3
    assert result["product_result"]["evidence"]["fact_payload"]["comparison_scope"]["row_count"] >= 3


def test_fast_fact_provider_limit_one_ranking_sql_is_widened_to_top_n(tmp_path):
    store, workspace = _prepare_channel_workspace(tmp_path)
    provider_sql = (
        "SELECT channel_name, SUM(revenue) AS total_revenue "
        "FROM channel_sales GROUP BY channel_name ORDER BY total_revenue DESC LIMIT 1"
    )

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近30天哪个渠道收入最高？只回答事实和口径。",
        providers={
            "sql_candidate": MockLLMProvider(
                {"sql_candidates": [{"sql": provider_sql, "rationale": "Provider narrowed ranking to one row."}]}
            )
        },
    )

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] == "fast_fact"
    assert result["comparison_scope_adjustment"]["applied"] is True
    assert "LIMIT 1" not in result["generated_sql"].upper()
    assert len(result["execution_result"]["rows"]) >= 3
    assert result["product_result"]["evidence"]["fact_payload"]["comparison_scope"]["row_count"] >= 3


def test_fast_fact_this_month_store_ranking_without_initial_sql_uses_current_month_scope(tmp_path):
    store, workspace = _prepare_store_workspace(tmp_path)

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "本月哪个门店销售额最高？",
    )

    text = _answer_text(result["business_answer"])

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] == "fast_fact"
    assert result["analysis_task"]["time_range"]["type"] == "this_month"
    assert result["execution_result"]["rows"][0][0] == "上海旗舰店"
    assert "business_answer_agent" in _trace_nodes(result)
    _assert_no_provider_answer_boundary(result["business_answer"])


def test_fast_fact_missing_time_uses_full_data_range_when_workspace_has_one_safe_time_field(tmp_path):
    store, workspace = _prepare_customer_segment_workspace(tmp_path)

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "收入最高的客户分群是谁？",
    )

    text = _answer_text(result["business_answer"])
    time_range = result["analysis_task"]["time_range"]

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] == "fast_fact"
    assert time_range["type"] == "full_data_range"
    assert time_range["start"] == "2026-01-05"
    assert time_range["end"] == "2026-06-18"
    assert result["execution_result"]["rows"][0][0] == "高价值会员"
    ledger_limits = " ".join(result.get("question_evidence_ledger", {}).get("data_limits") or [])
    assert "完整可用时间范围" in text or "完整可用时间范围" in ledger_limits
    assert "business_answer_agent" in _trace_nodes(result)


def test_fast_fact_without_chart_uses_answer_seam_but_does_not_construct_visualization_provider(tmp_path, monkeypatch):
    store, workspace = _prepare_store_workspace(tmp_path)
    constructed = {"visualization": 0}

    def fail_visualization_provider():
        constructed["visualization"] += 1
        raise AssertionError("fast_fact without an explicit chart request must not construct the visualization provider")

    monkeypatch.setattr("graph.workflow.build_visualization_agent_provider", fail_visualization_provider)

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近90天总销售额是多少？",
        initial_sql="SELECT SUM(sales_amount) AS total_sales FROM store_sales",
    )

    nodes = _trace_nodes(result)

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] == "fast_fact"
    assert "fast_fact_evidence_preparer" in nodes
    assert "business_answer_agent" in nodes
    assert "visualization_agent" not in nodes
    assert constructed == {"visualization": 0}


def test_fast_fact_ranking_returns_leader_value_and_comparison_scope_without_dump(tmp_path):
    store, workspace = _prepare_store_workspace(tmp_path)

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近90天销售额最高的门店是谁？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 3"
        ),
    )

    answer = result["product_result"]["business_answer"]
    text = _answer_text(answer)
    fact_payload = result["product_result"]["evidence"]["fact_payload"]

    assert result["analysis_route"]["route"] == "fast_fact"
    _assert_no_provider_answer_boundary(answer)
    assert fact_payload["comparison_scope"]["row_count"] == 3
    assert fact_payload["rows"] == result["execution_result"]["rows"]
    assert "store_name" not in answer["direct_answer"]
    assert "total_sales" not in answer["direct_answer"]
    assert "SELECT " not in text.upper()
    assert "[[" not in text
    assert "execution_result" not in text
    assert "insight_agent" not in _trace_nodes(result)


def test_fast_fact_ranking_context_pack_retains_key_fact_and_excludes_internal_noise(tmp_path):
    store, workspace = _prepare_store_workspace(tmp_path)

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近90天销售额最高的门店是谁？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 3"
        ),
    )

    pack = result["fast_fact_context_pack"]
    packed_text = json.dumps(pack, ensure_ascii=False)

    assert pack["user_question"] == "最近90天销售额最高的门店是谁？"
    assert pack["route"] == "fast_fact"
    assert pack["task_type"] == "rank"
    assert pack["metrics"][0]["label"] == "销售额"
    assert pack["metrics"][0]["unit"] == "currency"
    assert pack["dimensions"][0]["label"] == "门店"
    assert pack["time_range"]["display"] == "最近 90 天"
    assert pack["comparison_scope"]["row_count"] == 3
    assert pack["comparison_scope"]["sufficient"] is True
    assert pack["key_evidence_rows"][0]["dimensions"][0]["display_value"] == "上海旗舰店"
    assert pack["key_evidence_rows"][0]["metrics"][0]["display_value"] == "2.6 万"
    assert pack["formulas"]
    assert "SELECT " not in packed_text.upper()
    assert "technical_sql" not in packed_text
    assert "trace" not in packed_text.lower()
    assert "provider" not in packed_text.lower()
    assert "workspace_profile" not in packed_text
    assert "semantic_layer" not in packed_text
    assert "raw_rows" not in packed_text


def test_fast_fact_trend_returns_fact_summary_without_recommendations(tmp_path):
    store, workspace = _prepare_trend_workspace(tmp_path)

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "本月按周看订单量趋势怎么样？",
        initial_sql="SELECT order_date, SUM(order_count) AS order_count FROM orders GROUP BY order_date ORDER BY order_date",
    )

    answer = result["product_result"]["business_answer"]
    text = _answer_text(answer)

    assert result["analysis_route"]["route"] == "fast_fact"
    _assert_no_provider_answer_boundary(answer)
    assert "insight_agent" not in _trace_nodes(result)


def test_fast_fact_explicit_chart_request_allows_visualization_after_ledger_answer_path(tmp_path):
    store, workspace = _prepare_store_workspace(tmp_path)

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近90天销售额最高的门店是谁？请生成图表。",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 3"
        ),
    )

    nodes = _trace_nodes(result)

    assert result["status"] == "completed"
    assert result["analysis_route"]["route"] == "fast_fact"
    assert "fast_fact_evidence_preparer" in nodes
    assert "business_answer_agent" in nodes
    assert "visualization_agent" in nodes
    assert "insight_agent" not in nodes
    assert "claim_typing_agent" not in nodes
    assert "final_answer_composer" not in nodes
    assert result["product_result"]["chart_artifacts"]
    artifact = result["product_result"]["chart_artifacts"][0]
    assert artifact["renderer"] == "echarts"
    assert artifact["echarts_option"]["series"][0]["type"] == "bar"
    assert artifact["image_path"].endswith(".png")
    assert artifact["image_url"].startswith(f"/api/workspaces/{workspace['workspace_id']}/artifacts/")
    chart_step = next(step for step in result["product_result"]["progress_steps"] if step["key"] == "charting")
    assert chart_step["status"] == "completed"
    assert "事实快答不生成图表" not in chart_step["summary"]


def test_fast_fact_trend_context_pack_keeps_trend_points_and_time_range(tmp_path):
    store, workspace = _prepare_trend_workspace(tmp_path)

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "本月按周看订单量趋势怎么样？",
        initial_sql="SELECT order_date, SUM(order_count) AS order_count FROM orders GROUP BY order_date ORDER BY order_date",
    )

    pack = result["fast_fact_context_pack"]

    assert pack["task_type"] == "trend"
    assert pack["time_range"]["display"] == "本月"
    assert len(pack["key_evidence_rows"]) == 3
    assert [row["dimensions"][0]["display_value"] for row in pack["key_evidence_rows"]] == [
        "2026-07-01",
        "2026-07-08",
        "2026-07-15",
    ]
    assert [row["metrics"][0]["display_value"] for row in pack["key_evidence_rows"]] == ["120", "150", "180"]


def test_fast_fact_context_pack_retains_safe_key_rows_without_full_raw_objects():
    execution_result = {
        "success": True,
        "columns": ["store_name", "total_sales"],
        "rows": [["上海旗舰店", 26255.44], ["北京国贸店", 18400.0]],
    }
    fact_payload = {
        "task_type": "rank",
        "metrics": ["销售额"],
        "dimensions": ["门店"],
        "time_scope": {"raw_text": "最近 90 天"},
        "comparison_scope": {"type": "peer_comparison", "row_count": 2, "sufficient": True},
        "columns": ["store_name", "total_sales"],
        "rows": execution_result["rows"],
        "display_values": [{"门店": "上海旗舰店", "总销售额": "2.6 万"}, {"门店": "北京国贸店", "总销售额": "1.8 万"}],
        "formulas": {"total_sales": "SUM(sales_amount)"},
        "warnings": ["结论只覆盖当前导入数据。"],
    }
    pack = build_fast_fact_context_pack(
        user_question="最近90天销售额最高的门店是谁？",
        analysis_route={"route": "fast_fact"},
        analysis_task={"task_type": "rank", "metrics": ["销售额"], "dimensions": ["门店"]},
        fact_payload=fact_payload,
        evidence_result={"success": True, "validation_status": "validated"},
        execution_result=execution_result,
        metric_registry={"metrics": {"total_sales": {"business_label": "销售额", "unit": "currency"}}},
    )

    packed_text = json.dumps(pack, ensure_ascii=False)

    assert pack["key_evidence_rows"][0]["dimensions"][0]["display_value"] == "上海旗舰店"
    assert pack["key_evidence_rows"][0]["metrics"][0]["display_value"] == "2.6 万"
    assert pack["comparison_scope"]["row_count"] == 2
    assert "结论只覆盖当前导入数据" in packed_text
    assert "SELECT" not in packed_text.upper()
    assert "raw_rows" not in packed_text


def test_non_fast_fact_questions_still_use_full_chain(tmp_path):
    store, workspace = _prepare_store_workspace(tmp_path)

    cases = [
        "哪个门店最值得复盘，为什么？",
        "哪个渠道应该加预算？",
        "生成一份管理层报告",
        "销售额、毛利率、满意度综合看哪个门店最好？",
    ]
    for question in cases:
        result = run_workspace_analysis(
            store,
            workspace["workspace_id"],
            question,
            initial_sql=(
                "SELECT store_name, SUM(sales_amount) AS total_sales "
                "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 3"
            ),
        )

        assert result["analysis_route"]["route"] != "fast_fact"
        assert "business_answer_agent" in _trace_nodes(result)
        assert "insight_agent" not in _trace_nodes(result)


def test_fast_fact_history_detail_persists_answer_and_route(tmp_path):
    store, workspace = _prepare_store_workspace(tmp_path)

    result = run_workspace_analysis(
        store,
        workspace["workspace_id"],
        "最近90天销售额最高的门店是谁？",
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 3"
        ),
    )
    stored = WorkspaceRunStore(store).load_run_response(workspace["workspace_id"], result["run_id"])

    assert stored["result"]["analysis_route"]["route"] == "fast_fact"
    assert stored["result"]["business_answer"] == result["business_answer"]
    assert stored["result"]["evidence"] == result["evidence"]
    assert stored["result"]["technical_details"] == result["technical_details"]
    assert stored["product_result"]["analysis_route"]["route"] == "fast_fact"
    assert stored["product_result"]["business_answer"] == result["product_result"]["business_answer"]
    assert stored["product_result"]["evidence"] == result["product_result"]["evidence"]
    assert stored["product_result"]["technical_details"]["fact_payload"]["rows"] == result["execution_result"]["rows"]
    assert stored["product_result"]["technical_details"]["question_evidence_pack"] == result["question_evidence_pack"]
    assert stored["product_result"]["technical_details"]["fast_fact_context_pack"] == result["fast_fact_context_pack"]
