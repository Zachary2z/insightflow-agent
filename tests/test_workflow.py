import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def test_workflow_completes_success_path_and_saves_trace(tmp_path):
    from graph.workflow import run_workflow

    result = run_workflow(
        "最近 30 天销售额最高的 5 个商品为什么值得复盘？",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_success",
        session_id="session_success",
    )

    assert result["status"] == "completed"
    assert result["review_result"]["approved"] is True
    assert result["execution_result"]["success"] is True
    assert result["final_answer"]
    assert result["trace_path"].endswith("run_success.json")

    saved = json.loads((tmp_path / "run_success.json").read_text(encoding="utf-8"))
    trace_nodes = [event["node"] for event in saved["trace"]]
    assert "schema_agent" in trace_nodes
    assert "metric_agent" in trace_nodes
    assert "sql_generator_agent" in trace_nodes
    assert "sql_reviewer_agent" in trace_nodes
    assert "sql_executor_node" in trace_nodes
    assert "insight_agent" in trace_nodes


def test_workflow_rejects_dangerous_sql_before_execution(tmp_path):
    from graph.workflow import run_workflow

    result = run_workflow(
        "删除所有取消订单的数据。",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_blocked",
        session_id="session_blocked",
        initial_sql="DELETE FROM orders WHERE status = 'cancelled'",
    )

    assert result["status"] == "failed"
    assert result["review_result"]["approved"] is False
    assert result["execution_result"] == {}
    assert "SQL 审核未通过" in result["final_answer"]
    trace_nodes = [event["node"] for event in result["trace"]]
    assert "sql_reviewer_agent" in trace_nodes
    assert "sql_executor_node" not in trace_nodes


def test_workflow_repairs_execution_error_once_and_reruns(tmp_path):
    from graph.workflow import run_workflow

    result = run_workflow(
        "帮我查询订单明细价格。",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_fix",
        session_id="session_fix",
        initial_sql="SELECT missing_price(oi.unit_price) FROM order_items oi LIMIT 5",
    )

    assert result["status"] == "completed"
    assert result["retry_count"] == 1
    assert result["fixed_sql"] == "SELECT oi.unit_price FROM order_items oi LIMIT 5"
    assert result["execution_result"]["success"] is True
    assert result["final_answer"]
    trace_nodes = [event["node"] for event in result["trace"]]
    assert trace_nodes.count("sql_executor_node") == 2
    assert "error_fix_agent" in trace_nodes


def test_workflow_stops_after_one_failed_repair_without_fabricating_answer(tmp_path):
    from graph.workflow import run_workflow

    result = run_workflow(
        "帮我查询一个不存在的字段。",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_fail",
        session_id="session_fail",
        initial_sql="SELECT unknown_runtime_fn(id) FROM orders LIMIT 5",
    )

    assert result["status"] == "failed"
    assert result["retry_count"] == 0
    assert result["execution_result"]["success"] is False
    assert result["final_answer"].startswith("SQL 执行失败")
    assert "unknown_runtime_fn" in result["final_answer"]
    assert not result.get("data_used", False)
    trace_nodes = [event["node"] for event in result["trace"]]
    assert trace_nodes.count("sql_executor_node") == 1
    assert "error_fix_agent" in trace_nodes
