# InsightFlow Agent

InsightFlow Agent is a LangGraph-based multi-agent tool-calling BI workflow for BI-style SQL analysis.

P0 is complete. The current system can take a Chinese business question, route it through a LangGraph multi-agent SQL workflow, validate and execute SELECT SQL against a SQLite ecommerce database, repair one execution error, explain results from real query output, save trace artifacts, run a 20-case eval benchmark, retrieve P1 business context, classify evidence-backed versus unsupported claims, generate simple chart artifacts, and save traceable Markdown analysis reports.

## Current Status

P0 - Agentic SQL Core and P1 - Reliable Analysis & Report Core are complete.

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

P1 - Reliable Analysis & Report Core is complete. Next phase: P2 - Business Review & Action Workflow.

Track current phase, task status, test status, and acceptance progress in [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md).

## LLM Enhancement Roadmap

The current P0 and P1 implementation is deterministic and does not call an LLM, so an API key is not required for the completed workflow. `.env.example` keeps `OPENAI_API_KEY` as a reserved configuration point for later controlled LLM enhancement.

LLM usage should be additive, optional, and bounded by tools, validators, and trace:

- **Current baseline**: deterministic Agent state transitions, SQL validation, SQL execution, evidence validation, chart generation, report saving, and trace logging remain the source of truth.
- **P2 controlled enhancement**: introduce an optional LLM adapter for report task planning, report section outlining, business-language polishing, and user clarification questions. LLM outputs must be structured and checked before use.
- **P2 guarded SQL enhancement**: allow an LLM to propose SQL candidates only after schema, metric, and business context retrieval. Every candidate must still pass `validate_sql()` before `run_sql()`.
- **P3 engineering hardening**: add provider abstraction, prompt templates, prompt/version tracking, cost and latency metadata, LLM eval cases, and observability around model-assisted steps.

LLM boundaries:

- The LLM must not execute SQL, bypass `validate_sql()`, override `Evidence Validator`, create final evidence-backed claims without data support, or trigger action tools without approval gates.
- Reports and insights must remain traceable to SQL, execution results, business context, evidence validation, charts, and saved artifacts.

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

Open the Streamlit URL, enter a Chinese business question, and run the workflow. The demo displays:

- Agent steps
- Generated SQL
- SQL review result
- SQL execution result
- Error repair process
- Final answer
- Trace JSON
- Eval command entry

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
- FastAPI, React UI, async jobs, MCP, RBAC, trace dashboards, P2 business review reports, and action workflows remain outside P1 scope.
- P1 Reliable Analysis & Report Core is complete: Business Context Retrieval, Evidence Validator, Chart Agent, and Report Agent are implemented.
