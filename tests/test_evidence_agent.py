import sqlite3

from llm_ops.provider import MockLLMProvider
from workspaces.analysis_contracts import AnalysisTask, AuditResult, QuestionEvidencePack
from workspaces.evidence_agent import run_evidence_agent_question_mode


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


def _sales_db(tmp_path):
    db_path = tmp_path / "sales.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE store_sales (store_name TEXT, sales_amount REAL)")
        conn.executemany(
            "INSERT INTO store_sales VALUES (?, ?)",
            [("上海旗舰店", 300000.0), ("北京国贸店", 100000.0)],
        )
    return db_path


def _base_state(db_path, *, initial_sql: str) -> dict:
    return {
        "run_id": "run_evidence_agent",
        "session_id": "session_test",
        "user_question": "哪个门店销售额最高？",
        "original_question": "哪个门店销售额最高？",
        "db_path": db_path,
        "initial_sql": initial_sql,
        "execution_result": {},
        "review_retry_count": 0,
        "retry_count": 0,
        "schema_repair_attempted": False,
        "schema_repair_succeeded": False,
        "schema_repair_reason": "",
        "schema_repair": {},
        "schema_repair_pending_review": False,
        "analysis_task": {
            "task_type": "rank",
            "resolved_question": "哪个门店销售额最高？",
            "metrics": ["销售额"],
            "dimensions": ["门店"],
            "time_range": {},
            "filters": [],
        },
        "analysis_task_contract": AnalysisTask(
            resolved_question="哪个门店销售额最高？",
            metrics=["销售额"],
            dimensions=["门店"],
        ).to_dict(),
        "analysis_route": {"route": "fast_fact"},
        "trace": [],
    }


def _tool_names(pack: QuestionEvidencePack) -> list[str]:
    return [call.tool_name for call in pack.tool_calls]


def test_evidence_agent_builds_question_evidence_pack_from_reviewed_execution(tmp_path):
    db_path = _sales_db(tmp_path)

    result = run_evidence_agent_question_mode(
        _base_state(
            db_path,
            initial_sql=(
                "SELECT store_name, SUM(sales_amount) AS total_sales "
                "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 20"
            ),
        )
    )

    pack = QuestionEvidencePack.from_dict(result["question_evidence_pack"])
    tool_names = _tool_names(pack)

    assert result["execution_result"]["success"] is True
    assert pack.task.metrics == ["销售额"]
    assert pack.columns == ["store_name", "total_sales"]
    assert pack.rows[0] == {"store_name": "上海旗舰店", "total_sales": 300000.0}
    assert pack.metrics == ["销售额"]
    assert isinstance(pack.data_limits, list)
    assert tool_names[:5] == [
        "schema_lookup",
        "metric_lookup",
        "sql_candidate_builder",
        "sql_review",
        "sql_execution",
    ]
    assert "sql" not in pack.to_result_evidence()
    ledger = result["question_evidence_ledger"]
    assert ledger["facts"]
    assert ledger["facts"][0]["source_columns"] == ["store_name", "total_sales"]
    assert ledger["facts"][0]["evidence_ref"]
    assert ledger["tool_calls"]
    assert "SELECT" not in str(ledger).upper()


def test_evidence_agent_validates_reviewed_execution_before_answer_generation(tmp_path):
    db_path = _sales_db(tmp_path)

    result = run_evidence_agent_question_mode(
        _base_state(
            db_path,
            initial_sql=(
                "SELECT store_name, SUM(sales_amount) AS total_sales "
                "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 20"
            ),
        )
    )

    trace_nodes = [event.get("node") for event in result.get("trace") or []]

    assert result["execution_result"]["success"] is True
    assert result["evidence_result"]["success"] is True
    assert result["evidence_result"]["validation_status"] == "validated"
    assert "evidence_validator_agent" in trace_nodes
    assert trace_nodes.index("evidence_validator_agent") > trace_nodes.index("sql_executor_node")


def test_evidence_agent_does_not_execute_sql_when_review_rejects(tmp_path):
    db_path = _sales_db(tmp_path)

    result = run_evidence_agent_question_mode(
        _base_state(db_path, initial_sql="DELETE FROM store_sales WHERE sales_amount < 0")
    )

    pack = QuestionEvidencePack.from_dict(result["question_evidence_pack"])

    assert result["status"] == "failed"
    assert result["review_result"]["approved"] is False
    assert result["execution_result"] == {}
    assert "SQL contains a dangerous keyword" in result["review_result"]["issues"]
    assert "sql_execution" not in _tool_names(pack)
    assert not any(event.get("node") == "sql_executor_node" for event in result["trace"])
    assert result["question_evidence_ledger"]["facts"] == []
    assert result["question_evidence_ledger"]["data_limits"]


def test_evidence_agent_emits_question_evidence_ledger_for_fast_fact_and_standard_paths(tmp_path):
    db_path = _sales_db(tmp_path)

    fast = run_evidence_agent_question_mode(
        _base_state(
            db_path,
            initial_sql=(
                "SELECT store_name, SUM(sales_amount) AS total_sales "
                "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 20"
            ),
        )
    )
    standard_state = _base_state(
        db_path,
        initial_sql=(
            "SELECT store_name, SUM(sales_amount) AS total_sales "
            "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 20"
        ),
    )
    standard_state["analysis_route"] = {"route": "standard_analysis"}
    standard = run_evidence_agent_question_mode(standard_state)

    assert fast["analysis_route"]["route"] == "fast_fact"
    assert fast["question_evidence_ledger"]["facts"]
    assert standard["analysis_route"]["route"] == "standard_analysis"
    assert standard["question_evidence_ledger"]["facts"]


def test_evidence_agent_schema_repair_candidate_must_be_reviewed_before_execution(tmp_path):
    db_path = _sales_db(tmp_path)
    provider = MockLLMProvider(
        {
            "sql_candidates": [
                {
                    "sql": (
                        "SELECT store_name, SUM(sales_amount) AS total_sales "
                        "FROM store_sales GROUP BY store_name ORDER BY total_sales DESC LIMIT 20"
                    ),
                    "rationale": "Use current workspace fields.",
                }
            ]
        }
    )

    result = run_evidence_agent_question_mode(
        _base_state(db_path, initial_sql="SELECT missing_column FROM store_sales LIMIT 20"),
        sql_candidate_provider=provider,
    )

    pack = QuestionEvidencePack.from_dict(result["question_evidence_pack"])
    review_events = [event for event in result["trace"] if event.get("node") == "sql_reviewer_agent"]

    assert result["status"] == "executed"
    assert result["schema_repair_attempted"] is True
    assert result["schema_repair_succeeded"] is True
    assert len(review_events) == 2
    assert review_events[0]["status"] == "error"
    assert review_events[1]["status"] == "success"
    assert _tool_names(pack).count("sql_review") == 2
    assert "schema_repair" in _tool_names(pack)
    assert "sql_execution" in _tool_names(pack)
    assert result["execution_result"]["success"] is True


def test_evidence_agent_does_not_retry_schema_repair_indefinitely(tmp_path):
    db_path = _sales_db(tmp_path)
    provider = _SequenceProvider(
        [
            {
                "sql_candidates": [
                    {
                        "sql": "SELECT still_missing FROM store_sales LIMIT 20",
                        "rationale": "Still invalid.",
                    }
                ]
            }
        ]
    )

    result = run_evidence_agent_question_mode(
        _base_state(db_path, initial_sql="SELECT missing_column FROM store_sales LIMIT 20"),
        sql_candidate_provider=provider,
    )

    pack = QuestionEvidencePack.from_dict(result["question_evidence_pack"])

    assert result["status"] == "failed"
    assert result["execution_result"] == {}
    assert result["schema_repair_attempted"] is True
    assert result["schema_repair_succeeded"] is False
    assert len(provider.requests) == 1
    assert _tool_names(pack).count("schema_repair") == 1
    assert _tool_names(pack).count("sql_review") == 2
    assert "sql_execution" not in _tool_names(pack)


def test_evidence_auditor_builds_audit_result_from_question_evidence_pack():
    from workspaces.evidence_auditor import audit_question_evidence

    task = AnalysisTask(
        resolved_question="哪个门店销售额最高？为什么？",
        metrics=["销售额"],
        dimensions=["门店"],
        decision_goal="判断领先门店并解释边界",
    )
    pack = QuestionEvidencePack(
        task=task,
        rows=[
            {"store_name": "上海旗舰店", "total_sales": 300000.0},
            {"store_name": "北京国贸店", "total_sales": 100000.0},
        ],
        columns=["store_name", "total_sales"],
        metrics=["销售额"],
        data_limits=["当前数据只能确认销售额排名，不能直接证明原因。"],
    )

    audit = audit_question_evidence(
        question="哪个门店销售额最高？为什么？",
        task=task,
        evidence_pack=pack,
        candidate_claims=[
            "上海旗舰店 total_sales 为 300000.0。",
            "利润率为 40%。",
            "基于当前证据，可能与门店客流和活动承接有关，需要进一步验证。",
        ],
    )

    assert isinstance(audit, AuditResult)
    assert any("上海旗舰店" in fact and "300000" in fact for fact in audit.supported_facts)
    assert any("北京国贸店" in fact and "100000" in fact for fact in audit.supported_facts)
    assert "利润率为 40%。" in audit.unsupported_claims
    assert any("可能与门店客流" in item for item in audit.reasonable_inferences)
    assert audit.data_limits == ["当前数据只能确认销售额排名，不能直接证明原因。"]
    assert audit.confidence == "medium"


def test_business_answer_agent_outputs_p16_answer_and_audit_boundary():
    from workspaces.business_answer_agent import run_business_answer_agent

    state = {
        "run_id": "run_business_answer_agent",
        "session_id": "session_business_answer_agent",
        "user_question": "哪个门店最值得优先复盘，为什么？",
        "analysis_task": {
            "resolved_question": "哪个门店最值得优先复盘，为什么？",
            "metrics": ["销售额"],
            "dimensions": ["门店"],
            "decision_goal": "判断复盘对象",
        },
        "execution_result": {
            "success": True,
            "columns": ["store_name", "total_sales"],
            "rows": [["上海旗舰店", 300000.0], ["北京国贸店", 100000.0]],
            "row_count": 2,
        },
        "question_evidence_pack": QuestionEvidencePack(
            task=AnalysisTask(
                resolved_question="哪个门店最值得优先复盘，为什么？",
                metrics=["销售额"],
                dimensions=["门店"],
                decision_goal="判断复盘对象",
            ),
            rows=[
                {"store_name": "上海旗舰店", "total_sales": 300000.0},
                {"store_name": "北京国贸店", "total_sales": 100000.0},
            ],
            columns=["store_name", "total_sales"],
            metrics=["销售额"],
            data_limits=["当前数据不能直接证明原因。"],
        ).to_dict(),
        "trace": [],
    }

    result = run_business_answer_agent(state)
    answer = result["business_answer"]
    answer_text = " ".join(
        [
            answer["headline"],
            answer["direct_answer"],
            answer["why"],
            *answer["evidence_bullets"],
            *answer["recommendations"],
            *answer["caveats"],
        ]
    )

    assert set(answer) == {
        "headline",
        "direct_answer",
        "why",
        "evidence_bullets",
        "recommendations",
        "caveats",
        "confidence",
    }
    assert "业务回答生成失败" in answer_text
    assert "上海旗舰店" not in answer_text
    assert "300000" not in answer_text
    assert result["business_answer_generation"]["fallback_used"] is True
    assert result["business_answer_generation"]["source"] == "provider_unavailable"
    assert "SELECT" not in answer_text.upper()
    assert "raw_rows" not in answer_text
    assert "provider_metadata" not in answer_text
    assert result["audit_result"]["supported_facts"]
    assert result["audit_result"]["data_limits"] == ["当前数据不能直接证明原因。"]
