# InsightFlow Agent

InsightFlow Agent is a LangGraph-based multi-agent tool-calling BI workflow.

The project is currently in P0, focused on the Agentic SQL Core:

- SQLite ecommerce database
- Schema and metric tools
- SQL validation and execution
- One-step SQL error repair
- Trace logging
- Streamlit glass-box demo
- 20-case eval benchmark

## Current Status

Task 6 is complete. The project now has a deterministic SQLite ecommerce database, metric definitions, schema tool, SQL validator, SQL executor, and trace logger for P0 SQL workflow development; agents, workflow, Streamlit integration, and eval cases will be added in later P0 tasks.

Track current phase, task status, test status, and acceptance progress in [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in values as needed.

## Run Tests

```bash
python -m pytest
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

## Run Demo

```bash
streamlit run app.py
```

## P0 Architecture Target

```text
User question
-> Supervisor Agent
-> Schema Agent -> get_database_schema()
-> Metric Agent -> retrieve_metric_definition()
-> SQL Generator Agent
-> SQL Reviewer Agent -> validate_sql()
-> SQL Executor Tool -> run_sql()
-> Error Fix Agent, when execution fails once
-> Insight Agent
-> Trace Logger
```

## Demo Questions Planned

- 最近 30 天销售额最高的 5 个商品是什么？
- 最近 3 个月销售额最高的品类是什么？
- 每个城市的总销售额是多少？
- 删除所有取消订单的数据。
- 帮我导出所有用户的手机号和邮箱。

## Eval

P0 will add `eval/test_questions.json`, `eval/run_eval.py`, and `eval/report.md` after the core workflow is implemented.
