import sqlite3
import json

from workspaces.context_pack_builder import build_fast_fact_context_pack
from workspaces.fast_fact_composer import compose_fast_fact_answer
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
    assert answer["recommendations"] == []
    assert "最近90天" in text
    assert "总销售额" in text or "销售额" in text
    assert "5.7 万" in text or "56655.44" in text
    assert "SELECT " not in text.upper()
    assert "raw_rows" not in text
    assert "execution_result" not in text
    assert "fact_payload" not in text
    assert "sql_reviewer_agent" in nodes
    assert "sql_executor_node" in nodes
    assert "evidence_validator_agent" in nodes
    assert "fast_fact_composer" in nodes
    assert "question_evidence_pack" in result
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
    assert "visualization_agent" not in nodes
    assert result["product_result"]["chart_artifacts"] == []
    assert result["technical_details"]["sql"].startswith("SELECT SUM")
    assert result["technical_details"]["raw_rows"] == result["execution_result"]["rows"]
    assert "technical_sql" not in result["technical_details"]["fact_payload"]
    assert result["technical_details"]["fact_payload"]["technical_refs"]["sql"] == "technical_details.sql"


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
    assert answer["recommendations"] == []
    assert "上海旗舰店" in text
    assert "2.6 万" in text or "26255.44" in text
    assert "共统计 3" in text
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
    assert answer["recommendations"] == []
    assert "趋势" in text
    assert "上升" in text or "增加" in text
    assert "120" in text
    assert "180" in text
    assert "insight_agent" not in _trace_nodes(result)


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


def test_fast_fact_answer_can_be_composed_from_context_pack_without_full_raw_objects():
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

    answer = compose_fast_fact_answer(
        user_question="最近90天销售额最高的门店是谁？",
        analysis_route={"route": "fast_fact"},
        analysis_task=None,
        execution_result={},
        evidence_result=None,
        fact_payload=None,
        context_pack=pack,
    )
    text = _answer_text(answer)

    assert "上海旗舰店" in text
    assert "2.6 万" in text
    assert "共统计 2" in text
    assert "结论只覆盖当前导入数据" in text
    assert "SELECT" not in text.upper()
    assert "rows" not in text


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
        assert "insight_agent" in _trace_nodes(result)


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
    assert stored["product_result"]["analysis_route"]["route"] == "fast_fact"
    assert stored["product_result"]["business_answer"] == result["product_result"]["business_answer"]
    assert stored["product_result"]["technical_details"]["fact_payload"]["rows"] == result["execution_result"]["rows"]
    assert stored["product_result"]["technical_details"]["fast_fact_context_pack"] == result["fast_fact_context_pack"]
