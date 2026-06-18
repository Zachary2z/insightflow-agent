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

Task 1 is complete. The project now has a deterministic SQLite ecommerce database for P0 SQL workflow development; tools, agents, workflow, and eval cases will be added in later P0 tasks.

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
