from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from graph.workflow import run_workflow


APP_TITLE = "InsightFlow Agent"
APP_SUBTITLE = "P0 Agentic SQL Core"
DEFAULT_DB_PATH = Path("data/ecommerce.db")
DEFAULT_TRACE_DIR = Path("logs/traces")
EXAMPLE_QUESTIONS = [
    "最近 30 天销售额最高的 5 个商品是什么？",
    "最近 3 个月销售额最高的品类是什么？",
    "每个城市的总销售额是多少？",
    "删除所有取消订单的数据。",
    "帮我导出所有用户的手机号和邮箱。",
]


def run_demo_question(
    question: str,
    db_path: str | Path = DEFAULT_DB_PATH,
    trace_dir: str | Path = DEFAULT_TRACE_DIR,
    run_id: str | None = None,
    session_id: str | None = None,
    initial_sql: str | None = None,
) -> dict[str, Any]:
    return run_workflow(
        question,
        db_path=db_path,
        trace_dir=trace_dir,
        run_id=run_id,
        session_id=session_id,
        initial_sql=initial_sql,
    )


def format_agent_steps(result: dict[str, Any]) -> list[dict[str, Any]]:
    steps = []
    for event in result.get("trace", []):
        steps.append(
            {
                "node": event.get("node", ""),
                "tool_name": event.get("tool_name", ""),
                "status": event.get("status", ""),
                "latency_ms": event.get("latency_ms", 0),
                "retry_count": event.get("retry_count", 0),
                "summary": event.get("tool_output_summary", ""),
            }
        )
    return steps


def load_trace_file(trace_path: str | Path) -> dict[str, Any]:
    path = Path(trace_path)
    if not path.exists():
        return {
            "success": False,
            "error": f"Trace file not found: {path}",
        }

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to load trace file: {exc}",
        }


def _rows_as_records(execution_result: dict[str, Any]) -> list[dict[str, Any]]:
    columns = execution_result.get("columns", [])
    rows = execution_result.get("rows", [])
    return [dict(zip(columns, row, strict=False)) for row in rows]


def _render_sidebar(st: Any) -> dict[str, Any]:
    st.sidebar.header("Run")
    selected = st.sidebar.selectbox("Demo question", EXAMPLE_QUESTIONS, index=0)
    db_path = st.sidebar.text_input("SQLite database", value=str(DEFAULT_DB_PATH))
    trace_dir = st.sidebar.text_input("Trace directory", value=str(DEFAULT_TRACE_DIR))
    use_initial_sql = st.sidebar.checkbox("Use SQL override", value=False)
    initial_sql = ""
    if use_initial_sql:
        initial_sql = st.sidebar.text_area(
            "SQL override",
            value="DELETE FROM orders WHERE status = 'cancelled'",
            height=120,
        )
    return {
        "selected_question": selected,
        "db_path": db_path,
        "trace_dir": trace_dir,
        "initial_sql": initial_sql.strip() if use_initial_sql else None,
    }


def _render_agent_steps(st: Any, result: dict[str, Any]) -> None:
    steps = format_agent_steps(result)
    st.subheader("Agent Steps")
    if steps:
        st.dataframe(steps, use_container_width=True, hide_index=True)
    else:
        st.write("No trace events yet.")


def _render_sql(st: Any, result: dict[str, Any]) -> None:
    st.subheader("Generated SQL")
    st.code(result.get("generated_sql", ""), language="sql")
    if result.get("sql_reason"):
        st.caption(result["sql_reason"])


def _render_review(st: Any, result: dict[str, Any]) -> None:
    st.subheader("SQL Review Result")
    st.json(result.get("review_result", {}), expanded=True)


def _render_execution(st: Any, result: dict[str, Any]) -> None:
    st.subheader("SQL Execution Result")
    execution_result = result.get("execution_result", {})
    st.json(execution_result, expanded=False)
    records = _rows_as_records(execution_result)
    if records:
        st.dataframe(records, use_container_width=True, hide_index=True)


def _render_repair(st: Any, result: dict[str, Any]) -> None:
    st.subheader("Error Repair Process")
    sql_fix = result.get("sql_fix", {})
    if sql_fix:
        st.json(sql_fix, expanded=True)
        if sql_fix.get("fixed_sql"):
            st.code(sql_fix["fixed_sql"], language="sql")
    else:
        st.write("No repair attempted.")


def _render_final_answer(st: Any, result: dict[str, Any]) -> None:
    st.subheader("Final Answer")
    if result.get("status") == "completed":
        st.success(result.get("final_answer", ""))
    else:
        st.error(result.get("final_answer", "Workflow failed."))


def _render_trace(st: Any, result: dict[str, Any]) -> None:
    st.subheader("Trace Viewer")
    trace_path = result.get("trace_path", "")
    if trace_path:
        st.code(trace_path)
        st.json(load_trace_file(trace_path), expanded=False)
    else:
        st.write("No trace file saved.")


def _render_eval_entry(st: Any) -> None:
    st.subheader("Eval Entry")
    st.code("python eval/run_eval.py", language="bash")


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title=APP_TITLE, page_icon="IF", layout="wide")
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    config = _render_sidebar(st)
    question = st.text_area(
        "业务问题",
        value=config["selected_question"],
        height=90,
        placeholder="最近 30 天销售额最高的 5 个商品是什么？",
    )

    run_clicked = st.button("运行 Workflow", type="primary")
    if run_clicked:
        with st.spinner("Running InsightFlow workflow..."):
            st.session_state["last_result"] = run_demo_question(
                question,
                db_path=config["db_path"],
                trace_dir=config["trace_dir"],
                initial_sql=config["initial_sql"],
            )

    result = st.session_state.get("last_result")
    if not result:
        st.info("输入业务问题后运行 Workflow。")
        return

    status = result.get("status", "unknown")
    st.metric("Status", status)

    tabs = st.tabs(
        [
            "Agent Steps",
            "Generated SQL",
            "SQL Review",
            "Execution Result",
            "Error Repair",
            "Final Answer",
            "Trace",
            "Eval",
        ]
    )
    with tabs[0]:
        _render_agent_steps(st, result)
    with tabs[1]:
        _render_sql(st, result)
    with tabs[2]:
        _render_review(st, result)
    with tabs[3]:
        _render_execution(st, result)
    with tabs[4]:
        _render_repair(st, result)
    with tabs[5]:
        _render_final_answer(st, result)
    with tabs[6]:
        _render_trace(st, result)
    with tabs[7]:
        _render_eval_entry(st)


if __name__ == "__main__":
    main()
