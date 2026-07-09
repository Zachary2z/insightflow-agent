import sqlite3
import time

from workspaces.analysis_runner import run_workspace_analysis
from workspaces.profiler import profile_workspace_database
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


_LIVE_ENV_KEYS = (
    "INSIGHTFLOW_LIVE_DEEPSEEK_TESTS",
    "INSIGHTFLOW_PRODUCT_LIVE_MODE",
    "INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING",
    "INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER",
    "INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING",
    "INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE",
    "INSIGHTFLOW_USE_PROVIDER_BUSINESS_ANSWER",
    "INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT",
    "DEEPSEEK_API_KEY",
)


class _SequenceProvider:
    model = "p29-acceptance-provider"

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("provider should not be called")
        return self.responses.pop(0)


def _workspace(tmp_path, name, setup):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace(name)
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        setup(conn)
    profile = profile_workspace_database(store, workspace["workspace_id"])
    generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace


def _sales_workspace(tmp_path):
    def setup(conn):
        conn.execute("CREATE TABLE store_sales (store_name TEXT, business_date TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?, ?)",
            [
                ("上海旗舰店", "2026-06-10", 26255.44),
                ("北京国贸店", "2026-06-11", 18400.0),
                ("深圳湾店", "2026-07-02", 12000.0),
            ],
        )

    return _workspace(tmp_path, "P29 Sales Acceptance Workspace", setup)


def _channel_revenue_workspace(tmp_path):
    def setup(conn):
        conn.execute("CREATE TABLE channel_sales (sale_date TEXT, channel_name TEXT, revenue REAL)")
        conn.executemany(
            "INSERT INTO channel_sales VALUES (?, ?, ?)",
            [
                ("2026-04-20", "搜索广告", 120000.0),
                ("2026-06-10", "私域社群", 180000.0),
                ("2026-06-12", "直播间", 90000.0),
            ],
        )

    return _workspace(tmp_path, "P29 Channel Revenue Acceptance Workspace", setup)


def _customer_segment_workspace(tmp_path):
    def setup(conn):
        conn.execute("CREATE TABLE customer_revenue (sale_date TEXT, segment_name TEXT, revenue REAL)")
        conn.executemany(
            "INSERT INTO customer_revenue VALUES (?, ?, ?)",
            [
                ("2026-01-05", "高价值会员", 300000.0),
                ("2026-03-10", "新客", 140000.0),
                ("2026-06-18", "沉睡唤醒", 90000.0),
            ],
        )

    return _workspace(tmp_path, "P29 Customer Segment Acceptance Workspace", setup)


def _channel_performance_workspace(tmp_path):
    def setup(conn):
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

    return _workspace(tmp_path, "P29 Channel Performance Acceptance Workspace", setup)


def _business_answer_provider(answer):
    return _SequenceProvider(
        [
            {
                "candidate_claims": answer["claims"],
                "business_answer": {
                    "headline": answer["headline"],
                    "direct_answer": answer["direct"],
                    "why": answer["why"],
                    "evidence_bullets": answer["evidence"],
                    "recommendations": answer["recommendations"],
                    "caveats": answer["caveats"],
                    "confidence": "medium",
                },
            }
        ]
    )


def _run_case(store, workspace, question, providers=None):
    started = time.perf_counter()
    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question=question,
        providers=providers,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    provider_calls = sum(len(getattr(provider, "requests", [])) for provider in (providers or {}).values())
    nodes = [event.get("node") for event in result.get("trace") or []]
    fact_payload = (result.get("product_result", {}).get("evidence") or {}).get("fact_payload") or {}
    summary = {
        "question": question,
        "route": (result.get("analysis_route") or {}).get("route"),
        "routing_strategy": result.get("routing_strategy", ""),
        "provider_call_count": provider_calls,
        "business_answer_provider_called": len(getattr((providers or {}).get("business_answer"), "requests", [])) > 0,
        "sql_generated": bool(result.get("generated_sql") or (result.get("technical_details") or {}).get("sql")),
        "sql_executed": bool((result.get("execution_result") or {}).get("success")),
        "evidence_rows": (result.get("execution_result") or {}).get("rows") or [],
        "fact_payload_summary": {
            "row_count": (fact_payload.get("comparison_scope") or {}).get("row_count"),
            "display_values": (fact_payload.get("display_values") or [])[:2],
        },
        "answer_summary": result.get("final_answer") or (result.get("business_answer") or {}).get("direct_answer", ""),
        "chart_generated": bool((result.get("product_result") or {}).get("chart_artifacts")),
        "elapsed_ms": elapsed_ms,
        "nodes": nodes,
    }
    return result, summary


def _answer_text(result):
    answer = result.get("business_answer") or {}
    return " ".join(
        [
            str(answer.get("headline") or ""),
            str(answer.get("direct_answer") or ""),
            str(answer.get("why") or ""),
            *[str(item) for item in answer.get("evidence_bullets") or []],
            *[str(item) for item in answer.get("recommendations") or []],
            *[str(item) for item in answer.get("caveats") or []],
        ]
    )


def _is_explicit_no_provider_answer(result):
    text = _answer_text(result)
    return "无可用模型" in text or "业务回答生成失败" in text or "业务回答缺失" in text


def _disable_live_env(monkeypatch):
    for key in _LIVE_ENV_KEYS:
        monkeypatch.setenv(key, "")
    monkeypatch.setenv("INSIGHTFLOW_LIVE_DEEPSEEK_TESTS", "0")
    monkeypatch.setenv("INSIGHTFLOW_PRODUCT_LIVE_MODE", "0")


def test_p29_acceptance_fast_fact_questions_record_route_sql_evidence_and_skip_business_provider(
    tmp_path, monkeypatch
):
    _disable_live_env(monkeypatch)
    cases = [
        (
            "最近30天总销售额是多少？",
            _sales_workspace,
            lambda result, summary: (
                summary["route"] == "fast_fact"
                and summary["provider_call_count"] == 0
                and summary["sql_generated"]
                and summary["sql_executed"]
                and summary["evidence_rows"]
                and not summary["chart_generated"]
                and "fast_fact_evidence_preparer" in summary["nodes"]
                and "business_answer_agent" in summary["nodes"]
                and result["analysis_task"]["time_range"]["type"] == "last_n_days"
                and result["analysis_task"]["time_range"]["value"] == 30
                and _is_explicit_no_provider_answer(result)
            ),
        ),
        (
            "最近90天哪个渠道收入金额最高？",
            _channel_revenue_workspace,
            lambda result, summary: (
                summary["route"] == "fast_fact"
                and summary["provider_call_count"] == 0
                and summary["evidence_rows"][0][0] == "私域社群"
                and not summary["chart_generated"]
                and "business_answer_agent" in summary["nodes"]
            ),
        ),
        (
            "本月哪个门店销售额最高？",
            _sales_workspace,
            lambda result, summary: (
                summary["route"] == "fast_fact"
                and result["analysis_task"]["time_range"]["type"] == "this_month"
                and summary["evidence_rows"][0][0] == "深圳湾店"
                and summary["provider_call_count"] == 0
                and not summary["chart_generated"]
            ),
        ),
        (
            "收入最高的客户分群是谁？",
            _customer_segment_workspace,
            lambda result, summary: (
                summary["route"] == "fast_fact"
                and result["analysis_task"]["time_range"]["type"] == "full_data_range"
                and result["analysis_task"]["time_range"]["start"] == "2026-01-05"
                and result["analysis_task"]["time_range"]["end"] == "2026-06-18"
                and summary["evidence_rows"][0][0] == "高价值会员"
                and summary["provider_call_count"] == 0
                and not summary["chart_generated"]
            ),
        ),
    ]

    summaries = []
    for question, workspace_factory, assert_case in cases:
        store, workspace = workspace_factory(tmp_path)
        result, summary = _run_case(
            store,
            workspace,
            question,
            providers={},
        )
        summaries.append(summary)

        assert result["status"] == "completed"
        assert assert_case(result, summary), summary
        assert summary["elapsed_ms"] >= 0
        assert summary["fact_payload_summary"]["row_count"] >= 1
        assert summary["answer_summary"]

    assert [summary["question"] for summary in summaries] == [case[0] for case in cases]


def test_p29_acceptance_full_judgment_questions_record_business_provider_and_boundaries(tmp_path, monkeypatch):
    _disable_live_env(monkeypatch)
    cases = [
        (
            "最近90天按渠道比较收入、投放金额和投放效率，哪个渠道表现最好？",
            {
                "claims": [
                    {"claim": "私域社群 revenue 为 180000.0。", "category": "hard_fact"},
                    {"claim": "私域社群 ad_spend 为 30000.0。", "category": "hard_fact"},
                    {"claim": "私域社群 roas 为 6.0。", "category": "hard_fact"},
                    {"claim": "私域社群综合表现最好。", "category": "business_inference"},
                ],
                "headline": "私域社群综合表现最好。",
                "direct": "私域社群收入最高且投放效率最高，综合表现最好。",
                "why": "证据显示私域社群收入为 180000.0，投放金额为 30000.0，ROAS 为 6.0。",
                "evidence": ["私域社群收入 180000.0、投放金额 30000.0、ROAS 6.0。"],
                "recommendations": ["优先复盘私域社群打法，再评估是否扩大预算。"],
                "caveats": ["当前结论只基于最近90天同表渠道数据。"],
            },
        ),
        (
            "最近30天哪个渠道最值得加预算？请给证据和风险边界。",
            {
                "claims": [
                    {"claim": "私域社群 revenue 为 180000.0。", "category": "hard_fact"},
                    {"claim": "私域社群 roas 为 6.0。", "category": "hard_fact"},
                    {"claim": "私域社群值得优先评估加预算。", "category": "recommendation"},
                ],
                "headline": "私域社群最值得优先评估加预算。",
                "direct": "私域社群收入和投放效率领先，但应先小步测试预算增量。",
                "why": "证据显示私域社群收入为 180000.0，ROAS 为 6.0。",
                "evidence": ["私域社群收入 180000.0、投放金额 30000.0、ROAS 6.0。"],
                "recommendations": ["先做小比例预算增量测试，观察边际 ROAS。"],
                "caveats": ["这是分析建议，不代表系统已执行预算调整。"],
            },
        ),
    ]

    for question, answer in cases:
        store, workspace = _channel_performance_workspace(tmp_path)
        business_answer_provider = _business_answer_provider(answer)
        result, summary = _run_case(
            store,
            workspace,
            question,
            providers={"business_answer": business_answer_provider},
        )

        assert result["status"] == "completed"
        assert summary["route"] in {"standard_analysis", "deep_judgment"}
        assert summary["routing_strategy"] != "reject"
        assert summary["business_answer_provider_called"] is True
        assert summary["provider_call_count"] == 1
        assert summary["sql_generated"] is True
        assert summary["sql_executed"] is True
        assert summary["evidence_rows"]
        assert "business_answer_agent" in summary["nodes"]
        assert "fast_fact_evidence_preparer" not in summary["nodes"]
        assert result["business_answer"]["caveats"]
        assert result["audit_result"]["unsupported_claims"] == []
        assert summary["elapsed_ms"] >= 0


def test_p29_acceptance_external_action_rejects_before_sql_and_provider(tmp_path, monkeypatch):
    _disable_live_env(monkeypatch)
    store, workspace = _channel_performance_workspace(tmp_path)
    business_answer_provider = _SequenceProvider()

    result, summary = _run_case(
        store,
        workspace,
        "把预算调整到私域社群并发送通知。",
        providers={"business_answer": business_answer_provider},
    )

    assert result["status"] == "failed"
    assert summary["routing_strategy"] == "reject"
    assert summary["route"] != "fast_fact"
    assert "external_action" in result["question_understanding"]["risk_flags"]
    assert summary["provider_call_count"] == 0
    assert summary["business_answer_provider_called"] is False
    assert summary["sql_generated"] is False
    assert summary["sql_executed"] is False
    assert summary["evidence_rows"] == []
    assert summary["chart_generated"] is False
    assert "sql_reviewer_agent" not in summary["nodes"]
    assert "sql_executor_node" not in summary["nodes"]
    assert business_answer_provider.requests == []
    assert summary["elapsed_ms"] >= 0


def test_p29_acceptance_fast_fact_chart_request_generates_chart_without_business_provider(tmp_path, monkeypatch):
    _disable_live_env(monkeypatch)
    store, workspace = _channel_revenue_workspace(tmp_path)

    result, summary = _run_case(
        store,
        workspace,
        "最近90天哪个渠道收入最高？给我画图。",
        providers={},
    )

    assert result["status"] == "completed"
    assert summary["route"] == "fast_fact"
    assert summary["provider_call_count"] == 0
    assert summary["business_answer_provider_called"] is False
    assert summary["sql_generated"] is True
    assert summary["sql_executed"] is True
    assert summary["evidence_rows"][0][0] == "私域社群"
    assert summary["chart_generated"] is True
    assert "fast_fact_evidence_preparer" in summary["nodes"]
    assert "visualization_agent" in summary["nodes"]
    assert "business_answer_agent" in summary["nodes"]
    assert _is_explicit_no_provider_answer(result)
    assert summary["elapsed_ms"] >= 0
