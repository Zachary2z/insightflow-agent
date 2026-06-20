from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.action_planner import run_action_planner_agent
from agents.action_verifier import run_action_verifier_agent
from agents.chart_agent import run_chart_agent
from agents.context_retriever import run_context_retriever_agent
from agents.evidence_validator import run_evidence_validator_agent
from agents.report_agent import run_report_agent
from agents.report_supervisor import run_report_supervisor_agent
from agents.risk_assessor import run_action_executor_agent, run_risk_assessor_agent
from agents.supervisor import initialize_run
from api.models import RunCreateRequest
from api.run_manager import RunManager
from dashboard.trace_dashboard import build_trace_dashboard
from graph.workflow import run_workflow
from mcp_servers.action_server import get_tool_contract as get_action_mcp_contract
from mcp_servers.database_server import get_tool_contract as get_database_mcp_contract
from mcp_servers.report_server import get_tool_contract as get_report_mcp_contract
from tools.approval_tool import record_approval
from tools.action_tool import DEFAULT_ACTION_DB_PATH


APP_TITLE = "InsightFlow Agent"
APP_SUBTITLE = "Unified Multi-Agent BI Workflow Demo"
DEFAULT_DB_PATH = Path("data/ecommerce.db")
DEFAULT_TRACE_DIR = Path("logs/traces")
DEFAULT_ACTION_DB_PATH_FOR_DEMO = DEFAULT_ACTION_DB_PATH
EXAMPLE_QUESTIONS = [
    "最近 30 天销售额最高的 5 个商品是什么？",
    "最近 3 个月销售额最高的品类是什么？",
    "每个城市的总销售额是多少？",
    "删除所有取消订单的数据。",
    "帮我导出所有用户的手机号和邮箱。",
]
WEEKLY_REVIEW_QUESTION = "帮我生成一份本周电商经营分析周报，包括销售额、订单量、Top 商品、下降品类和运营建议。"
DEMO_VIEWS = [
    {"id": "sql_analysis", "label": "SQL Analysis", "phase": "P0"},
    {"id": "report_generation", "label": "Report Generation", "phase": "P1"},
    {"id": "weekly_business_review", "label": "Weekly Business Review", "phase": "P2"},
    {"id": "action_workflow", "label": "Action Workflow", "phase": "P2"},
    {"id": "mcp_tool_layer", "label": "MCP Tool Layer", "phase": "P3"},
    {"id": "async_run_api", "label": "Async Run API", "phase": "P3"},
    {"id": "trace_dashboard", "label": "Trace Dashboard", "phase": "P3"},
]


def build_capability_overview() -> list[dict[str, str]]:
    return [
        {
            "label": view["label"],
            "phase": view["phase"],
            "status": "local-api" if view["id"] == "async_run_api" else "available",
        }
        for view in DEMO_VIEWS
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


def run_report_generation_demo(
    question: str,
    db_path: str | Path = DEFAULT_DB_PATH,
    trace_dir: str | Path = DEFAULT_TRACE_DIR,
    report_dir: str | Path = "reports/markdown",
    chart_dir: str | Path = "reports/charts",
    run_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    state = run_demo_question(
        question,
        db_path=db_path,
        trace_dir=trace_dir,
        run_id=run_id,
        session_id=session_id,
    )
    if state.get("status") != "completed":
        return state
    state = run_context_retriever_agent(state)
    state = run_evidence_validator_agent(state)
    state = run_chart_agent(state, output_dir=chart_dir)
    state = run_report_agent(state, output_dir=report_dir)
    return state


def run_weekly_review_demo(
    question: str = WEEKLY_REVIEW_QUESTION,
    db_path: str | Path = DEFAULT_DB_PATH,
    trace_dir: str | Path = DEFAULT_TRACE_DIR,
    report_dir: str | Path = "reports/markdown",
    chart_dir: str | Path = "reports/charts",
    run_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    state = initialize_run(question, run_id=run_id, session_id=session_id)
    state["db_path"] = db_path
    state["trace_dir"] = trace_dir
    result = run_report_supervisor_agent(state, report_dir=report_dir, chart_dir=chart_dir)
    workflow_status = result.get("status", "")
    if workflow_status == "business_review_report_completed":
        result = {**result, "workflow_status": workflow_status, "status": "completed"}
    return result


def _demo_action_state(action_db_path: str | Path) -> dict[str, Any]:
    state = initialize_run(
        "找出最近销售额下降最多的品类，并为运营团队创建跟进任务和监控告警。",
        run_id="run_streamlit_action_demo",
        session_id="session_streamlit_action_demo",
    )
    state["action_db_path"] = action_db_path
    state["evidence_result"] = {
        "success": True,
        "data_supported_findings": [
            {
                "claim": "Cameras 的 GMV 变化为 -12000.0",
                "evidence": "SQL result row: category_name=Cameras, gmv_change=-12000.0",
                "confidence": 0.95,
            }
        ],
        "hypotheses": [
            {
                "claim": "可能需要进一步验证广告流量和转化率数据。",
                "reason": "Needs marketing data.",
                "needs_more_data": ["ad_impressions", "conversion_rate"],
            }
        ],
        "unsupported_claims_blocked": ["库存不足是确定原因"],
    }
    return state


def run_action_workflow_demo(
    action_db_path: str | Path = DEFAULT_ACTION_DB_PATH_FOR_DEMO,
    approved: bool = False,
) -> dict[str, Any]:
    state = run_risk_assessor_agent(run_action_planner_agent(_demo_action_state(action_db_path)))
    if approved:
        approval = record_approval(
            action_db_path,
            {
                "run_id": state["run_id"],
                "approval_status": "approved",
                "approved_by": "streamlit_demo",
                "reason": "Approved from Streamlit unified demo.",
            },
        )
        state["approval_status"] = approval["approval_status"]
        state["approval_record"] = approval
    state = run_action_executor_agent(state)
    if state.get("created_actions"):
        state = run_action_verifier_agent(state)
    return state


def build_mcp_contract_summary() -> list[dict[str, Any]]:
    contracts = [get_database_mcp_contract(), get_report_mcp_contract(), get_action_mcp_contract()]
    return [
        {
            "server_name": contract["server_name"],
            "tool_count": len(contract.get("tools", [])),
            "tools": [tool["name"] for tool in contract.get("tools", [])],
        }
        for contract in contracts
    ]


def build_async_run_api_summary() -> dict[str, Any]:
    return {
        "base_command": "uvicorn api.app:app --reload",
        "statuses": ["queued", "running", "waiting_for_approval", "completed", "failed", "cancelled"],
        "endpoints": [
            "POST /api/runs",
            "GET /api/runs/{run_id}",
            "GET /api/runs/{run_id}/trace",
            "GET /api/runs/{run_id}/events",
            "POST /api/runs/{run_id}/cancel",
        ],
    }


def run_async_run_api_demo(question: str, db_path: str | Path = DEFAULT_DB_PATH, trace_dir: str | Path = DEFAULT_TRACE_DIR) -> dict[str, Any]:
    manager = RunManager()
    record = manager.create_run(
        RunCreateRequest(
            user_question=question,
            db_path=str(db_path),
            trace_dir=str(trace_dir),
        )
    )
    return {
        "run_id": record.run_id,
        "status": record.status,
        "events": record.events,
    }


def build_trace_dashboard_summary(
    trace_dir: str | Path = DEFAULT_TRACE_DIR,
    action_db_path: str | Path = DEFAULT_ACTION_DB_PATH_FOR_DEMO,
) -> dict[str, Any]:
    return build_trace_dashboard(trace_dir=trace_dir, action_db_path=action_db_path)


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


def sync_selected_question(session_state: Any, selected_question: str) -> None:
    if session_state.get("selected_question") == selected_question:
        return
    session_state["selected_question"] = selected_question
    session_state["question_input"] = selected_question
    session_state.pop("last_result", None)


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


def _render_capability_overview(st: Any) -> None:
    st.subheader("Capability Overview")
    st.dataframe(build_capability_overview(), use_container_width=True, hide_index=True)


def _render_sql_analysis_view(st: Any, config: dict[str, Any]) -> None:
    sync_selected_question(st.session_state, config["selected_question"])
    question = st.text_area(
        "业务问题",
        key="question_input",
        height=90,
        placeholder="最近 30 天销售额最高的 5 个商品是什么？",
    )

    run_clicked = st.button("运行 SQL Analysis Workflow", type="primary")
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
        st.info("输入业务问题后运行 SQL Analysis。")
        return

    status = result.get("status", "unknown")
    st.metric("Status", status)
    tabs = st.tabs(["Agent Steps", "Generated SQL", "SQL Review", "Execution", "Repair", "Answer", "Trace", "Eval"])
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


def _render_report_generation_view(st: Any, config: dict[str, Any]) -> None:
    st.subheader("Report Generation")
    question = st.text_area(
        "报告分析问题",
        value=config["selected_question"],
        key="report_question_input",
        height=90,
    )
    if st.button("生成 P1 Analysis Report"):
        with st.spinner("Generating evidence-backed report..."):
            st.session_state["report_demo_result"] = run_report_generation_demo(
                question,
                db_path=config["db_path"],
                trace_dir=config["trace_dir"],
            )

    result = st.session_state.get("report_demo_result")
    if not result:
        st.info("运行后将展示 Evidence Validator、Chart Agent 和 Markdown Report 输出。")
        return
    st.metric("Workflow Status", result.get("status", "unknown"))
    st.metric("Evidence Unsupported Claim Rate", result.get("evidence_result", {}).get("unsupported_claim_rate", 0))
    summary = {
        "chart_path": result.get("chart_path", ""),
        "report_path": result.get("report_path", ""),
        "trace_path": result.get("trace_path", ""),
    }
    st.json(summary, expanded=True)
    with st.expander("Evidence Result"):
        st.json(result.get("evidence_result", {}), expanded=False)


def _render_weekly_review_view(st: Any, config: dict[str, Any]) -> None:
    st.subheader("Weekly Business Review")
    question = st.text_area("周报需求", value=WEEKLY_REVIEW_QUESTION, key="weekly_review_question", height=90)
    if st.button("生成 Weekly Business Review"):
        with st.spinner("Running report supervisor..."):
            st.session_state["weekly_review_result"] = run_weekly_review_demo(
                question,
                db_path=config["db_path"],
                trace_dir=config["trace_dir"],
            )

    result = st.session_state.get("weekly_review_result")
    if not result:
        st.info("运行后将展示 report sections、SQL subtasks、evidence、charts 和 weekly report path。")
        return
    st.metric("Report Status", result.get("status", "unknown"))
    st.code(result.get("weekly_report_path", ""))
    sections = [
        {"section_id": section.get("section_id"), "title": section.get("title")}
        for section in result.get("report_sections", [])
    ]
    st.dataframe(sections, use_container_width=True, hide_index=True)
    sub_tasks = [
        {
            "section_id": task.get("section_id"),
            "status": task.get("status"),
            "row_count": task.get("execution_result", {}).get("row_count", 0),
            "chart_count": len(task.get("chart_paths", [])),
        }
        for task in result.get("report_sub_tasks", [])
    ]
    st.dataframe(sub_tasks, use_container_width=True, hide_index=True)


def _render_action_workflow_view(st: Any) -> None:
    st.subheader("Action Workflow")
    approved = st.checkbox("Approve action execution", value=False)
    action_db_path = st.text_input("Action database", value=str(DEFAULT_ACTION_DB_PATH_FOR_DEMO))
    if st.button("运行 Action Workflow Demo"):
        with st.spinner("Running approval-gated action workflow..."):
            st.session_state["action_workflow_result"] = run_action_workflow_demo(
                action_db_path=action_db_path,
                approved=approved,
            )

    result = st.session_state.get("action_workflow_result")
    if not result:
        st.info("未勾选 approval 时会停在 approval gate；勾选后会创建并验证 task / alert / email draft。")
        return
    st.metric("Action Status", result.get("status", "unknown"))
    st.json(
        {
            "approval_status": result.get("approval_status"),
            "created_actions": result.get("created_actions", []),
            "audit_log_id": result.get("audit_log_id", ""),
        },
        expanded=True,
    )
    with st.expander("Risk Assessment"):
        st.json(result.get("risk_assessment", {}), expanded=False)


def _render_mcp_view(st: Any) -> None:
    st.subheader("MCP Tool Layer")
    summary = build_mcp_contract_summary()
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.caption("Internal SQL review, approval records, trace logging, and eval runner are not exposed as MCP tools.")


def _render_async_api_view(st: Any, config: dict[str, Any]) -> None:
    st.subheader("Async Run API")
    summary = build_async_run_api_summary()
    st.code(summary["base_command"], language="bash")
    st.dataframe([{"endpoint": endpoint} for endpoint in summary["endpoints"]], use_container_width=True, hide_index=True)
    if st.button("创建本地 in-memory API Run Demo"):
        st.session_state["async_api_demo_result"] = run_async_run_api_demo(
            config["selected_question"],
            db_path=config["db_path"],
            trace_dir=config["trace_dir"],
        )
    result = st.session_state.get("async_api_demo_result")
    if result:
        st.json(result, expanded=True)


def _render_trace_dashboard_view(st: Any, config: dict[str, Any]) -> None:
    st.subheader("Trace Dashboard")
    action_db_path = st.text_input("Dashboard action database", value=str(DEFAULT_ACTION_DB_PATH_FOR_DEMO))
    if st.button("刷新 Trace Dashboard Summary"):
        st.session_state["trace_dashboard_summary"] = build_trace_dashboard_summary(
            trace_dir=config["trace_dir"],
            action_db_path=action_db_path,
        )
    summary = st.session_state.get("trace_dashboard_summary") or build_trace_dashboard_summary(
        trace_dir=config["trace_dir"],
        action_db_path=action_db_path,
    )
    metric_cols = st.columns(4)
    metric_cols[0].metric("Trace Count", summary.get("trace_count", 0))
    metric_cols[1].metric("Event Count", summary.get("event_count", 0))
    metric_cols[2].metric("SQL Fix Count", summary.get("sql_fix_count", 0))
    metric_cols[3].metric("Eval Pass Rate", summary.get("eval_metrics", {}).get("pass_rate", 0.0))
    st.dataframe(
        [{"tool_name": key, "count": value} for key, value in summary.get("tool_call_counts", {}).items()],
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Dashboard JSON"):
        st.json(summary, expanded=False)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title=APP_TITLE, page_icon="IF", layout="wide")
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    config = _render_sidebar(st)
    _render_capability_overview(st)
    tabs = st.tabs([view["label"] for view in DEMO_VIEWS])
    with tabs[0]:
        _render_sql_analysis_view(st, config)
    with tabs[1]:
        _render_report_generation_view(st, config)
    with tabs[2]:
        _render_weekly_review_view(st, config)
    with tabs[3]:
        _render_action_workflow_view(st)
    with tabs[4]:
        _render_mcp_view(st)
    with tabs[5]:
        _render_async_api_view(st, config)
    with tabs[6]:
        _render_trace_dashboard_view(st, config)


if __name__ == "__main__":
    main()
