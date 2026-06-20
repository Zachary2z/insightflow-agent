# InsightFlow Agent

InsightFlow Agent is a LangGraph-based multi-agent tool-calling BI workflow for BI-style SQL analysis.

P0, P1, and P2 are complete. The current system can take a Chinese business question, route it through a LangGraph multi-agent SQL workflow, validate and execute SELECT SQL against a SQLite ecommerce database, repair one execution error, explain results from real query output, save trace artifacts, run a 20-case eval benchmark, retrieve P1 business context, classify evidence-backed versus unsupported claims, generate simple chart artifacts, save traceable Markdown analysis reports, generate weekly business review reports, create approval-gated action plans, expose selected tool capabilities through a P3 MCP-style tool contract layer, submit workflow runs through a FastAPI async run API, and summarize trace/eval/action observability metrics for a dashboard data layer.

## Current Status

P0 - Agentic SQL Core, P1 - Reliable Analysis & Report Core, and P2 - Business Review & Action Workflow are complete. P3 Task 17 - MCP Tool Layer, Task 18 - FastAPI + Async Run API, Task 19 - Trace Dashboard, and Task 19A - Streamlit Unified Demo are complete.

Implemented:

- SQLite ecommerce database
- Schema, metric, SQL validation, SQL execution, and trace tools
- Supervisor, Schema, Metric, SQL Generator, SQL Reviewer, Error Fix, and Insight agents
- LangGraph workflow with review, execution, one-retry repair, failure, insight, and trace-save paths
- Streamlit glass-box demo
- 20-case eval benchmark
- P1 business context retrieval for business rules, table docs, and historical SQL examples
- P1 evidence validation for data-supported findings, hypotheses, and unsupported claims
- P1 chart generation for bar, line, and optional pie charts
- P1 Markdown report generation with SQL, execution evidence, charts, and trace links
- P2 deterministic Report Supervisor for weekly business review reports with multiple SQL subtasks, evidence validation, chart paths, trace paths, and saved Markdown output
- P2 optional controlled LLM Report Planner for structured report section selection, fallback planning, and clarification questions without LLM-generated SQL or final claims
- P2 optional guarded LLM SQL and insight enhancement with SQL validation, deterministic fallback, and Evidence Validator claim blocking
- P2 Action Workflow with structured action plans, risk assessment, approval gate, SQLite task/alert records, action verification, and audit logs
- P3 MCP-style Tool Layer with database, report, and action server contracts over existing deterministic tools
- P3 FastAPI async run API with run submission, status polling, trace retrieval, event retrieval, and cancellation status
- P3 Trace Dashboard data layer with node latency, tool call, SQL execution, SQL repair, eval, approval, and audit metrics
- P3 Streamlit unified demo with SQL analysis, report generation, weekly review, action workflow, MCP, async API, and trace dashboard views

P3 - MCP & Engineering Core has started with Tasks 17, 18, 19, and 19A complete. Task 20+ engineering work is not implemented yet.

Track current phase, task status, test status, and acceptance progress in [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md).

## LLM Enhancement Roadmap

The current P0 and P1 implementation is deterministic and does not call an LLM, so an API key is not required for the completed workflow. `.env.example` keeps `OPENAI_API_KEY` as a reserved configuration point for later controlled LLM enhancement.

LLM usage should be additive, optional, and bounded by tools, validators, and trace:

- **Current baseline**: deterministic Agent state transitions, SQL validation, SQL execution, evidence validation, chart generation, report saving, and trace logging remain the source of truth.
- **P2 controlled enhancement**: introduce an optional LLM adapter for report task planning, report section outlining, business-language polishing, and user clarification questions. LLM outputs must be structured and checked before use.
- **P2 guarded SQL enhancement**: allow an LLM to propose SQL candidates only after schema, metric, and business context retrieval. Every candidate must still pass `validate_sql()` before `run_sql()`.
- **P3 question understanding**: add a structured intent and clarification layer that extracts metric, dimension, time range, filters, operation, and risk flags before SQL planning.
- **P3 SQL planning router**: route clear questions to deterministic templates, complex but complete questions to guarded LLM SQL candidates, ambiguous questions to clarification, and dangerous or sensitive requests to rejection or safety handling.
- **P3 engineering hardening**: add provider abstraction, prompt templates, prompt/version tracking, cost and latency metadata, LLM eval cases, and observability around model-assisted steps.

LLM boundaries:

- The LLM must not execute SQL, bypass `validate_sql()`, override `Evidence Validator`, create final evidence-backed claims without data support, or trigger action tools without approval gates.
- Reports and insights must remain traceable to SQL, execution results, business context, evidence validation, charts, and saved artifacts.

## Planned Question Understanding And SQL Routing

Two P3 tasks are planned to make SQL generation smarter without turning the system into a black-box Text2SQL app.

**Question Understanding & Clarification Router** will decide whether a user question is clear enough for SQL planning. It should extract structured slots such as:

- `metric`: GMV, order count, AOV, repurchase rate, or another known metric
- `dimension`: product, category, city, user, channel, or another grouping
- `time_range`: this week, last 30 days, this month, quarter, or a custom period
- `filters`: paid orders, excluding refunds, new users, high-AOV customers, or other constraints
- `operation`: top N, trend, comparison, decline, summary, or drilldown
- `limit`: Top 5, Top 10, or another row limit

If required slots are missing, it should return `strategy: clarify` with focused clarification questions instead of forcing SQL generation. If a request asks for sensitive fields or unsafe operations, it should return `strategy: reject` or route to a safety flow.

**SQL Planning Router** will decide whether SQL should come from a deterministic template or from the guarded LLM SQL candidate path. Template SQL remains the fast, reliable default for common BI questions. Guarded LLM candidates are used only when the question is clear enough but no existing template covers it. Every LLM candidate must still pass `validate_sql()` before execution.

The intended routing contract is:

```python
{
    "strategy": "template | llm_candidate | clarify | reject",
    "matched_template": "top_products_gmv",
    "confidence": 0.92,
    "missing_slots": [],
    "clarification_questions": [],
    "risk_flags": [],
    "reason": "Question matches a stable Top-N GMV template."
}
```

These tasks belong in P3 because they depend on mature provider, prompt, trace, and eval infrastructure. They should not weaken the current deterministic baseline.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python data/seed_data.py
streamlit run app.py
```

Copy `.env.example` to `.env` and fill in values as needed.

## Run Tests

```bash
python -m pytest
```

Run the P0 eval benchmark:

```bash
python eval/run_eval.py
```

## Seed Database

```bash
python data/seed_data.py
```

This creates `data/ecommerce.db` with the P0 ecommerce schema:

- `users`: 120 rows
- `orders`: 540 rows across `paid`, `cancelled`, and `refunded`
- `order_items`: 1,336 rows
- `products`: 36 rows
- `categories`: 6 rows

## What P0 Can Do

- Accept Chinese business questions in Streamlit.
- Read the real SQLite schema with `get_database_schema()`.
- Retrieve metric definitions such as GMV with `retrieve_metric_definition()`.
- Generate SELECT SQL for P0 ecommerce analysis scenarios.
- Review SQL with `validate_sql()` before execution.
- Block dangerous SQL such as `DELETE`, `DROP`, `UPDATE`, and sensitive-field exports before `run_sql()`.
- Execute approved SQL with `run_sql()` and return structured columns, rows, row count, timing, and errors.
- Repair one supported execution failure and rerun the fixed SQL after validation.
- Generate final answers only from `execution_result`.
- Save run traces to `logs/traces/{run_id}.json`.
- Run 20 eval cases with `eval/run_eval.py`.

## P0 Architecture

```text
User question
-> Supervisor Agent
-> Schema Agent -> get_database_schema()
-> Metric Agent -> retrieve_metric_definition()
-> SQL Generator Agent
-> SQL Reviewer Agent -> validate_sql()
-> SQL Executor Tool -> run_sql()
-> Error Fix Agent, when execution fails once
-> SQL Reviewer Agent -> validate_sql(), for fixed SQL
-> SQL Executor Tool -> run_sql(), for fixed SQL
-> Insight Agent
-> Trace Logger
```

The main entry point is `graph.workflow.run_workflow()`. Streamlit calls the same workflow used by eval, so demo behavior and benchmark behavior stay aligned.

## Metric Definitions

Metric definitions live in `data/metrics.yaml` and can be retrieved with `retrieve_metric_definition()`.

P0 metrics:

- `gmv`: sales amount, using `SUM(order_items.quantity * order_items.unit_price)`
- `order_count`: paid order count
- `aov`: average order value
- `category_gmv`: category-level GMV
- `product_sales`: product-level paid item quantity

Example:

```bash
python -c "from tools.metric_tool import retrieve_metric_definition; print(retrieve_metric_definition('最近 30 天销售额最高的 5 个商品是什么？'))"
```

## Business Context Retrieval

Task 11 adds a lightweight Business Context Retrieval layer for P1. It uses Markdown and JSON sources plus keyword matching; it does not require a vector database.

Context sources:

- `data/business_rules.md`: business rules such as paid-order-only GMV and sensitive-field handling
- `data/table_docs.md`: table and field descriptions for the ecommerce schema
- `data/sql_examples.json`: historical SQL examples for common BI questions

Tool interface:

```python
from tools.context_tool import retrieve_business_context

context = retrieve_business_context("最近 30 天销售额最高的 5 个商品是什么？")
print(context["matched_rules"])
print(context["matched_table_docs"])
print(context["matched_sql_examples"])
print(context["trace_event"])
```

Agent interface:

```python
from agents.context_retriever import run_context_retriever_agent
from agents.supervisor import initialize_run

state = initialize_run("最近 30 天销售额最高的 5 个商品是什么？")
state = run_context_retriever_agent(state)
print(state["business_context"]["context_summary"])
print(state["trace"][-1])
```

The tool returns structured JSON-compatible dictionaries and never raises file loading errors into the workflow. On failure it returns `success: false`, empty match lists, an `error`, and a trace-ready event. The Agent only reads `state["user_question"]`, writes `state["business_context"]`, and appends trace; it does not access the database, execute SQL, or generate reports.

## Evidence Validator

Task 12 adds an Evidence Validator layer for P1. It separates claims into:

- `data_supported_findings`: claims backed by `execution_result` rows or explicit business context
- `hypotheses`: claims framed as possible explanations or requiring more data
- `unsupported_claims_blocked`: deterministic claims without supporting evidence

Tool interface:

```python
from tools.evidence_tool import validate_evidence

result = validate_evidence(
    claims=[
        "Laptop Pro 14 的 GMV 为 511248.56",
        "可能与广告流量下降有关，需要 ad_impressions、ctr 和 conversion_rate 数据进一步验证",
        "库存不足是导致 Camera A 销量下降的主要原因",
    ],
    execution_result={
        "success": True,
        "columns": ["product_name", "gmv"],
        "rows": [["Laptop Pro 14", 511248.56]],
        "row_count": 1,
    },
)
print(result["data_supported_findings"])
print(result["hypotheses"])
print(result["unsupported_claims_blocked"])
```

Agent interface:

```python
from agents.evidence_validator import run_evidence_validator_agent

state["claims_to_validate"] = ["Laptop Pro 14 的 GMV 为 511248.56"]
state = run_evidence_validator_agent(state)
print(state["evidence_result"])
print(state["trace"][-1])
```

The Agent writes `state["evidence_result"]` and appends trace. It does not run SQL, generate charts, or save reports.

## Chart Agent

Task 13 adds chart generation for P1. The Chart Agent infers simple chart specs from the user question and `execution_result`, then calls `generate_chart()` to write PNG files under `reports/charts/` by default.

Rules:

- ranking / top questions -> bar chart
- trend / monthly questions -> line chart
- share / percentage questions -> pie chart, when requested

Tool interface:

```python
from tools.chart_tool import generate_chart

result = generate_chart(
    data={
        "columns": ["product_name", "gmv"],
        "rows": [["Laptop Pro 14", 511248.56], ["Camera A", 456050.99]],
    },
    chart_spec={
        "chart_type": "bar",
        "x": "product_name",
        "y": "gmv",
        "title": "Top Products by GMV",
        "run_id": "run_001",
    },
)
print(result["chart_path"])
print(result["trace_event"])
```

Agent interface:

```python
from agents.chart_agent import run_chart_agent

state = run_chart_agent(state)
print(state["chart_path"])
print(state["chart_paths"])
print(state["trace"][-1])
```

The Agent writes `state["chart_result"]`, `state["chart_path"]`, and `state["chart_paths"]`, and appends trace. It does not run SQL or save reports.

## Report Agent

Task 14 adds Markdown report generation for P1. The Report Agent composes already-available state into a traceable analysis report and calls `save_report()` to write `reports/markdown/{run_id}_report.md`.

Report sections:

- 用户问题
- 使用的业务指标
- 业务上下文
- 执行 SQL
- 查询结果摘要
- 数据支持结论
- 需要进一步验证的假设
- 图表路径
- 下一步建议
- Trace 路径

Tool interface:

```python
from tools.report_tool import save_report

result = save_report(
    run_id="run_001",
    report_content="# InsightFlow Analysis Report\n\nTrace path: logs/traces/run_001.json",
)
print(result["report_path"])
print(result["trace_event"])
```

Agent interface:

```python
from agents.report_agent import run_report_agent

state = run_report_agent(state)
print(state["report_path"])
print(state["trace"][-1])
```

The Agent writes `state["report_result"]` and `state["report_path"]`, and appends trace. It does not run SQL, generate charts, or include blocked unsupported claims as deterministic report findings.

## Business Review Report

Task 15 adds a deterministic P2 Report Supervisor for weekly business review reports. It decomposes a weekly report request into structured sections, then runs each SQL subtask through the existing schema, metric, SQL review, SQL execution, Evidence Validator, Chart Agent, Report Tool, and Trace Logger boundaries.

Core sections:

- 本周 GMV
- 本周订单量
- 本周客单价
- Top 商品
- Top 品类
- 销售下降品类
- 下周建议

Agent interface:

```python
from agents.report_supervisor import run_report_supervisor_agent
from agents.supervisor import initialize_run

state = initialize_run("帮我生成一份本周电商经营分析周报，包括销售额、订单量、Top 商品、下降品类和运营建议。")
state["db_path"] = "data/ecommerce.db"
state["trace_dir"] = "logs/traces"
state = run_report_supervisor_agent(state)

print(state["weekly_report_path"])
print(state["trace_path"])
print(state["report_sub_tasks"][0]["review_result"])
print(state["report_sub_tasks"][0]["execution_result"])
```

The supervisor writes:

- `report_type`: `weekly_business_report`
- `report_sections`: planned weekly report sections
- `report_sub_tasks`: per-section SQL, `review_result`, `execution_result`, evidence result, chart paths, status, and error
- `weekly_report_path`: `reports/markdown/{run_id}_weekly_business_report.md`
- `trace_path`: `logs/traces/{run_id}.json`

Failed subtasks are recorded with `status: failed` and their structured review/execution error, but they do not crash the whole weekly report workflow. Evidence Validator remains responsible for separating data-supported findings, hypotheses, and unsupported claims. Task 15 does not introduce LLM planning, guarded LLM SQL generation, action tools, approval gates, MCP, FastAPI, or dashboard behavior.

## Controlled LLM Report Planner

Task 15A adds an optional controlled planning layer for weekly business reports. The planner can call a supplied `llm_provider` to select report section IDs and ask clarification questions, but it cannot supply SQL, execute SQL, produce final claims, or bypass deterministic report templates.

Safety contract:

- Provider input includes `allowed_section_ids`, `must_not_generate_sql`, `must_not_execute_sql`, and `must_not_generate_final_claims`.
- Provider output is accepted only when section IDs match existing deterministic templates.
- Unknown sections and provider-supplied SQL are ignored.
- Missing, malformed, or unusable provider responses fall back to deterministic Task 15 sections.
- Clarification responses set `status: report_plan_needs_clarification` and return questions without running report SQL.

Agent interface:

```python
from agents.report_planner import run_report_planner_agent
from agents.supervisor import initialize_run

state = initialize_run("帮我生成一份本周电商经营分析周报，优先看 GMV 和 Top 商品。")

state = run_report_planner_agent(
    state,
    llm_provider=lambda prompt: {
        "report_type": "weekly_business_report",
        "sections": [{"section_id": "weekly_gmv"}, {"section_id": "top_products"}],
    },
)

print(state["report_plan"])
print([section["section_id"] for section in state["report_sections"]])
```

Report Supervisor integration:

```python
from agents.report_supervisor import run_report_supervisor_agent
from agents.supervisor import initialize_run

state = initialize_run("帮我生成一份本周电商经营分析周报，优先看 GMV 和 Top 商品。")
state["db_path"] = "data/ecommerce.db"

state = run_report_supervisor_agent(
    state,
    llm_provider=lambda prompt: {
        "report_type": "weekly_business_report",
        "sections": [{"section_id": "weekly_gmv"}, {"section_id": "top_products"}],
    },
)
print(state["weekly_report_path"])
```

No API key is required for the deterministic baseline. Without `llm_provider`, the planner uses the Task 15 deterministic fallback plan.

## Guarded LLM SQL and Insight Enhancement

Task 15B adds optional guarded enhancement agents. These agents accept supplied provider callables for tests or future adapters, but the deterministic baseline still needs no API key and does not call an LLM.

Guarded SQL candidate rules:

- The provider sees `schema_text`, `metric_context`, `business_context`, and current deterministic SQL.
- Provider output can include SQL candidates, but every candidate is checked with `validate_sql()`.
- Only the first approved SELECT candidate can replace `generated_sql`.
- Rejected, unsafe, malformed, or missing candidates leave deterministic SQL unchanged.
- This agent never calls `run_sql()`.

```python
from agents.guarded_llm_enhancer import run_guarded_sql_candidate_agent

state = run_guarded_sql_candidate_agent(
    state,
    llm_provider=lambda prompt: {
        "sql_candidates": [
            {
                "sql": "SELECT COUNT(*) AS order_count FROM orders WHERE status = 'paid' LIMIT 100",
                "rationale": "Safe paid-order count candidate.",
            }
        ]
    },
)
print(state["llm_sql_enhancement"])
print(state["generated_sql"])
```

Guarded insight enhancement rules:

- Provider output is treated as claims, not trusted final prose.
- Claims are checked with `validate_evidence()` against execution results and context.
- `guarded_summary` contains only data-supported findings and hypotheses.
- Unsupported deterministic claims are recorded in `unsupported_claims_blocked` and excluded from the guarded summary.

```python
from agents.guarded_llm_enhancer import run_guarded_insight_enhancer_agent

state = run_guarded_insight_enhancer_agent(
    state,
    llm_provider=lambda prompt: {
        "claims": [
            "Laptop Pro 14 的 GMV 为 511248.56",
            "库存不足是导致销量下降的主要原因",
            "可能需要进一步验证广告流量和转化率数据。",
        ]
    },
)
print(state["llm_insight_enhancement"]["guarded_summary"])
print(state["llm_insight_enhancement"]["unsupported_claims_blocked"])
```

Task 15B does not introduce action tools, approvals, MCP, FastAPI, dashboard behavior, provider abstraction, cost tracking, or prompt registry features.

## Action Workflow

Task 16 adds a local, auditable action workflow that can turn evidence-backed analysis into operational follow-up records. It does not call external task systems, send emails, run background jobs, or bypass approval gates.

Workflow:

```text
Evidence Validator
-> Action Planner
-> Risk Assessor
-> Approval Gate
-> Action Tool
-> Action Verifier
-> Audit Logger
```

Implemented tools:

- `create_task()` writes tasks to SQLite.
- `create_metric_alert()` writes metric alerts to SQLite.
- `create_email_draft()` writes email drafts to SQLite.
- `record_approval()` writes approval records to SQLite.
- `verify_action_execution()` confirms created records exist.
- `log_audit_event()` writes approval, execution, and verification audit events.

Agent interface:

```python
from agents.action_planner import run_action_planner_agent
from agents.action_verifier import run_action_verifier_agent
from agents.risk_assessor import run_action_executor_agent, run_risk_assessor_agent
from tools.approval_tool import record_approval

state = run_action_planner_agent(state)
state = run_risk_assessor_agent(state)

# Approval gate blocks execution until approval_status is approved.
approval = record_approval(
    state["action_db_path"],
    {
        "run_id": state["run_id"],
        "approval_status": "approved",
        "approved_by": "ops_manager",
        "reason": "Approved for operational follow-up.",
    },
)
state["approval_status"] = approval["approval_status"]
state["approval_record"] = approval

state = run_action_executor_agent(state)
state = run_action_verifier_agent(state)
print(state["created_actions"])
print(state["action_verification_result"])
print(state["audit_log_id"])
```

Approval rules:

- `create_task`, `create_metric_alert`, and `create_email_draft` require approval.
- Unapproved actions are blocked and audited.
- Approved actions create local SQLite records, then verifier confirms they exist.
- Audit logs preserve approval blocking, action execution, and action verification events.

Task 16 does not introduce MCP, FastAPI, React, async jobs, RBAC, external SaaS task creation, or real email sending.

## MCP Tool Layer

Task 17 adds a lightweight MCP-style contract layer under `mcp_servers/`. It exposes JSON-compatible tool contracts and wrapper functions for selected external-facing capabilities, while keeping internal safety and audit modules inside the system boundary.

Implemented MCP-style servers:

- `database-mcp-server`: `get_database_schema`, `get_sample_rows`, `run_sql`
- `report-mcp-server`: `generate_chart`, `save_report`
- `action-mcp-server`: `create_task`, `create_metric_alert`, `create_email_draft`

Not exposed as MCP tools:

- SQL review internals
- Permission and approval record tools
- Trace logging
- Eval runner

Safety boundaries:

- `mcp_run_sql()` loads schema, retrieves metric context, runs the existing SQL reviewer internally, and only then calls `run_sql()` with reviewed SQL.
- `mcp_save_report()` requires successful evidence validation and rejects reports with blocked unsupported claims.
- `mcp_create_task()`, `mcp_create_metric_alert()`, and `mcp_create_email_draft()` require `approval_status="approved"` before writing operational records.
- MCP wrappers return structured dictionaries with `success`, `mcp_server`, `tool_name`, and either `result` or `error`.
- The layer does not start a network server and does not add FastAPI, async jobs, dashboards, Docker, CI, or provider/prompt infrastructure.

Example:

```python
from mcp_servers.database_server import get_tool_contract, mcp_run_sql

print(get_tool_contract())

result = mcp_run_sql(
    db_path="data/ecommerce.db",
    sql="SELECT COUNT(*) AS order_count FROM orders",
)
print(result["review_result"]["approved"])
print(result["result"]["rows"])
```

## FastAPI Async Run API

Task 18 adds a minimal FastAPI app under `api/` for submitting LangGraph workflow runs without changing the deterministic baseline.

Run locally:

```bash
uvicorn api.app:app --reload
```

Implemented endpoints:

- `POST /api/runs`: enqueue a workflow run and return `run_id`.
- `GET /api/runs/{run_id}`: read run status and summary.
- `GET /api/runs/{run_id}/trace`: read current or completed trace data.
- `GET /api/runs/{run_id}/events`: read run lifecycle events.
- `POST /api/runs/{run_id}/cancel`: mark an active run as cancelled.

Supported statuses:

- `queued`
- `running`
- `waiting_for_approval`
- `completed`
- `failed`
- `cancelled`

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"user_question":"最近 30 天销售额最高的 5 个商品是什么？"}'
```

The API uses an in-memory `RunManager` and a thread pool to execute existing `graph.workflow.run_workflow()` calls. It is intentionally local and lightweight: Task 18 does not add persistent queues, SSE, dashboard views, React, RBAC, Docker, CI, or new LLM/provider behavior.

## Trace Dashboard Data Layer

Task 19 adds `dashboard.trace_dashboard.build_trace_dashboard()` for dashboard-ready observability summaries. It reads trace JSON artifacts, optional eval summaries, and optional action workflow SQLite records, then returns a JSON-compatible dictionary.

Metrics included:

- Agent node latency totals and averages
- Tool call counts
- SQL execution latency totals and averages
- SQL repair count
- Failure type distribution
- Eval totals and pass rate
- Action approval records
- Audit log records
- Structured load errors for bad trace files or unreadable action DBs

Example:

```python
from dashboard.trace_dashboard import build_trace_dashboard
from eval.run_eval import load_cases, run_eval_cases

eval_summary = run_eval_cases(load_cases())
dashboard = build_trace_dashboard(
    trace_dir="logs/traces",
    eval_summary=eval_summary,
    action_db_path="data/action_ops.db",
)

print(dashboard["agent_node_latency_ms"])
print(dashboard["tool_call_counts"])
print(dashboard["eval_metrics"])
```

Task 19 is a data layer only. It does not add React, Streamlit UI changes, SSE, dashboard frontend routing, RBAC, Docker/CI, provider abstraction, PromptOps, or new LLM behavior.

## Streamlit Unified Demo

Task 19A upgrades the Streamlit app from a P0-only glass-box SQL demo into a clear product demo for the backend capabilities that already exist.

Views:

- SQL Analysis: preserve the current P0 workflow view with Agent steps, SQL, SQL review, execution, repair, final answer, and trace.
- Report Generation: expose P1 evidence validation, chart generation, and Markdown report saving.
- Weekly Business Review: expose P2 report supervisor sections, SQL subtasks, evidence, charts, and saved weekly report path.
- Action Workflow: show action planning, risk assessment, approval gate state, created task/alert/email draft records, verification, and audit logs.
- MCP Tool Layer: show database/report/action MCP-style contracts and safe wrapper outputs.
- Async Run API: explain local FastAPI usage and show run status, trace, and event payloads in a demo-friendly way.
- Trace Dashboard: presents `build_trace_dashboard()` summaries such as node latency, tool counts, SQL execution latency, repair count, eval pass rate, approvals, and audit logs.

Task 19A improves clarity without changing core safety boundaries. The UI does not bypass SQL Validator, Evidence Validator, approval gate, MCP contracts, or deterministic workflow behavior. It does not introduce React, RBAC, Docker/CI, persistent queues, provider abstraction, PromptOps, or new LLM behavior.

## Schema Tool

The schema tool reads SQLite metadata and returns both structured table metadata and prompt-friendly `schema_text`.

```bash
python -c "from tools.schema_tool import get_database_schema; print(get_database_schema('data/ecommerce.db')['schema_text'])"
```

## SQL Validator

The SQL validator checks generated SQL before execution. It only approves safe SELECT statements, blocks dangerous keywords and sensitive fields, validates table/column names against the schema, appends a default `LIMIT 100` when needed, and checks GMV metric rules when metric context is provided.

```python
from tools.metric_tool import retrieve_metric_definition
from tools.schema_tool import get_database_schema
from tools.sql_validator import validate_sql

schema = get_database_schema("data/ecommerce.db")
metric = retrieve_metric_definition("最近 30 天销售额最高的 5 个商品是什么？")
sql = """
SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS sales
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE o.status = 'paid'
GROUP BY p.product_name
ORDER BY sales DESC
LIMIT 5
"""
print(validate_sql(sql, schema, metric))
```

## SQL Executor

The SQL executor runs approved SELECT statements against SQLite and returns structured execution results. It rejects non-SELECT SQL, caps returned rows with `max_rows`, captures database errors, and emits a trace-ready event.

```python
from tools.sql_executor import run_sql

sql = """
SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE o.status = 'paid'
GROUP BY p.product_name
ORDER BY gmv DESC
LIMIT 5
"""
print(run_sql("data/ecommerce.db", sql))
```

## Trace Logger

The trace logger records node and tool-call events for each Agent run. `append_trace()` adds normalized events to state without mutating the original state, and `save_trace()` writes structured JSON artifacts to `logs/traces/{run_id}.json`.

Required trace fields:

- `run_id`
- `session_id`
- `node`
- `tool_name`
- `tool_input_summary`
- `tool_output_summary`
- `status`
- `latency_ms`
- `error_type`
- `retry_count`
- `timestamp`

Example:

```python
from tools.trace_logger import append_trace, save_trace

state = {"run_id": "run_001", "session_id": "session_001", "trace": []}
state = append_trace(state, {
    "node": "sql_executor",
    "tool_name": "run_sql",
    "tool_input_summary": "SELECT 1",
    "tool_output_summary": "1 row returned",
    "status": "success",
    "latency_ms": 12,
})
print(save_trace("run_001", state["trace"], session_id="session_001"))
```

## P0 Agents

P0 agents are lightweight state-transforming modules. They return structured dictionaries and keep the Agent/Tool boundary clear: agents orchestrate state and reasoning, while tools perform schema lookup, metric retrieval, SQL validation, SQL execution, and trace persistence.

Implemented modules:

- `agents.supervisor.initialize_run()` initializes run/session state.
- `agents.schema_agent.run_schema_agent()` calls `get_database_schema()`.
- `agents.metric_agent.run_metric_agent()` calls `retrieve_metric_definition()`.
- `agents.sql_generator.run_sql_generator()` generates structured SELECT SQL output.
- `agents.sql_reviewer.run_sql_reviewer()` calls `validate_sql()`.
- `agents.error_fixer.run_error_fix_agent()` repairs one deterministic P0 SQL error class.
- `agents.insight_agent.run_insight_agent()` answers only from `execution_result`.

Example:

```python
from agents.metric_agent import run_metric_agent
from agents.schema_agent import run_schema_agent
from agents.sql_generator import run_sql_generator
from agents.sql_reviewer import run_sql_reviewer
from agents.supervisor import initialize_run

state = initialize_run("最近 30 天销售额最高的 5 个商品是什么？")
state = run_schema_agent(state, "data/ecommerce.db")
state = run_metric_agent(state)
state = run_sql_generator(state)
state = run_sql_reviewer(state)
print(state["sql_generation"])
print(state["review_result"])
```

## LangGraph Workflow

The P0 workflow composes the Agent and Tool layers with LangGraph:

```text
schema -> metric -> generate -> review
review approved -> execute
review rejected -> fail -> save_trace
execute success -> insight -> save_trace
execute failure and retry_count < 1 -> error_fix -> review
execute failure after retry -> fail -> save_trace
```

Example:

```python
from graph.workflow import run_workflow

result = run_workflow(
    "最近 30 天销售额最高的 5 个商品是什么？",
    db_path="data/ecommerce.db",
)
print(result["generated_sql"])
print(result["final_answer"])
print(result["trace_path"])
```

## Run Demo

```bash
streamlit run app.py
```

Open the Streamlit URL. The unified demo now displays:

- SQL Analysis with Agent steps, generated SQL, SQL review, execution result, repair process, final answer, trace JSON, and eval command entry
- Report Generation for P1 evidence-backed charts and Markdown reports
- Weekly Business Review for P2 report sections and SQL subtasks
- Action Workflow for approval-gated task, alert, email draft, verification, and audit output
- MCP Tool Layer contract summaries
- Async Run API endpoints and local run demo
- Trace Dashboard summary metrics

The SQL Analysis tab preserves the original P0 glass-box workflow, while the other tabs make P1/P2/P3 capabilities visible from the same app.

## Demo Questions

- 最近 30 天销售额最高的 5 个商品是什么？
- 最近 3 个月销售额最高的品类是什么？
- 每个城市的总销售额是多少？
- 删除所有取消订单的数据。
- 帮我导出所有用户的手机号和邮箱。

## Eval

Run the P0 benchmark:

```bash
python eval/run_eval.py
```

Current eval summary:

- Total cases: 20
- Passed cases: 20
- Pass rate: 100.00%
- SQL execution success rate: 92.31%
- SQL first-pass success rate: 91.67%
- SQL repair success rate: 100.00%
- Dangerous SQL block rate: 100.00%
- Metric definition accuracy: 100.00%

The generated report is written to `eval/report.md`.

## P0 Limits

- The SQL Generator is deterministic and covers the P0 ecommerce demo scope; it is not a general text-to-SQL model yet.
- Error Fix Agent supports a narrow one-retry repair path for P0 failure cases.
- React UI, persistent async jobs, RBAC, dashboard frontend views, provider abstraction, PromptOps, Docker/CI, and full ActionOps product features remain outside the current baseline.
- P1 Reliable Analysis & Report Core is complete: Business Context Retrieval, Evidence Validator, Chart Agent, and Report Agent are implemented.
