import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def test_example_questions_include_p0_demo_cases():
    from app import EXAMPLE_QUESTIONS

    assert "最近 30 天销售额最高的 5 个商品是什么？" in EXAMPLE_QUESTIONS
    assert "删除所有取消订单的数据。" in EXAMPLE_QUESTIONS
    assert "帮我导出所有用户的手机号和邮箱。" in EXAMPLE_QUESTIONS


def test_run_demo_question_executes_workflow_and_returns_trace(tmp_path):
    from app import run_demo_question

    result = run_demo_question(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_app_success",
        session_id="session_app_success",
    )

    assert result["status"] == "completed"
    assert result["generated_sql"].lower().startswith("select")
    assert result["execution_result"]["success"] is True
    assert result["final_answer"]
    assert Path(result["trace_path"]).is_file()


def test_run_demo_question_can_show_dangerous_sql_block(tmp_path):
    from app import run_demo_question

    result = run_demo_question(
        "删除所有取消订单的数据。",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_app_block",
        session_id="session_app_block",
        initial_sql="DELETE FROM orders WHERE status = 'cancelled'",
    )

    assert result["status"] == "failed"
    assert result["review_result"]["approved"] is False
    assert result["execution_result"] == {}
    assert "SQL 审核未通过" in result["final_answer"]


def test_format_agent_steps_extracts_trace_for_glass_box_view(tmp_path):
    from app import format_agent_steps, run_demo_question

    result = run_demo_question(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_app_steps",
        session_id="session_app_steps",
    )
    steps = format_agent_steps(result)

    assert steps
    assert {"node", "tool_name", "status", "latency_ms"} <= set(steps[0])
    assert "sql_generator_agent" in [step["node"] for step in steps]
    assert "sql_executor_node" in [step["node"] for step in steps]


def test_load_trace_file_reads_saved_trace_json(tmp_path):
    from app import load_trace_file, run_demo_question

    result = run_demo_question(
        "最近 30 天销售额最高的 5 个商品是什么？",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_app_trace",
        session_id="session_app_trace",
    )

    trace_payload = load_trace_file(result["trace_path"])

    assert trace_payload["run_id"] == "run_app_trace"
    assert trace_payload["status"] == "completed"
    assert trace_payload["trace"]


def test_load_trace_file_returns_structured_error_for_missing_file(tmp_path):
    from app import load_trace_file

    result = load_trace_file(tmp_path / "missing.json")

    assert result["success"] is False
    assert "Trace file not found" in result["error"]
