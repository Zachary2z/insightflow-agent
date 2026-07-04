import sqlite3

from llm_ops.provider import MockLLMProvider
from workspaces.analysis_contracts import AnalysisTask, QuestionEvidencePack
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
