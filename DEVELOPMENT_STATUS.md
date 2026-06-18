# InsightFlow Agent Development Status

Last updated: 2026-06-18

This file is the living development tracker for InsightFlow Agent. Update it after every completed task, test milestone, or scope change.

## Status Legend

- `[x]` Done
- `[~]` In progress
- `[ ]` Not started
- `[!]` Blocked or needs decision

## Current Snapshot

| Field | Status |
|---|---|
| Current phase | P0 - Agentic SQL Core |
| Current task | Task 5 - Implement SQL Executor |
| Last completed task | Task 4 - Implement SQL Validator |
| Main demo target | Multi-Agent + Tool Calling + SQL Execution Feedback |
| Active frontend | Streamlit |
| Out of scope for current phase | MCP, FastAPI, React, async jobs, RBAC, Trace Dashboard, ActionOps |

## Phase Overview

| Phase | Goal | Development | Tests | Docs | Overall |
|---|---|---|---|---|---|
| P0 | Agentic SQL Core | `[~]` scaffold, ecommerce DB, metric definitions, schema tool, and SQL validator done; SQL executor pending | `[~]` scaffold, seed, metric, schema, and validator tests passing | `[~]` README and status doc updated through Task 4 | `[~]` In progress |
| P1 | Reliable Analysis & Report Core | `[ ]` | `[ ]` | `[ ]` | `[ ]` Not started |
| P2 | Business Review & Action Workflow | `[ ]` | `[ ]` | `[ ]` | `[ ]` Not started |
| P3 | MCP & Engineering Core | `[ ]` | `[ ]` | `[ ]` | `[ ]` Not started |

## P0 - Agentic SQL Core

### Task Checklist

| Task | Development | Tests | Docs | Status |
|---|---|---|---|---|
| Task 0 - Project initialization | `[x]` Created scaffold, requirements, env example, Streamlit shell, base directories | `[x]` `tests/test_project_initialization.py`; `pytest` passes | `[x]` README has setup, run, P0 architecture target | `[x]` Done |
| Task 1 - Build ecommerce SQLite database | `[x]` `data/seed_data.py`, `data/ecommerce.db` | `[x]` table counts, schema, status/date coverage, CLI, and GMV query tests | `[x]` seed command and schema summary added to README | `[x]` Done |
| Task 2 - Implement Metric Definition | `[x]` `data/metrics.yaml`, `tools/metric_tool.py` | `[x]` metric matching, unknown metric, missing file, and trace-ready output tests | `[x]` metric definitions documented in README | `[x]` Done |
| Task 3 - Implement Schema Tool | `[x]` `tools/schema_tool.py` | `[x]` normal DB, empty DB, missing DB, schema_text, and trace-ready output tests | `[x]` schema tool usage documented in README | `[x]` Done |
| Task 4 - Implement SQL Validator | `[x]` `tools/sql_validator.py` | `[x]` safety, multi-statement, schema, limit, metric, and sensitive field tests | `[x]` validator rules documented in README | `[x]` Done |
| Task 5 - Implement SQL Executor | `[ ]` `tools/sql_executor.py` | `[ ]` success, max rows, non-SELECT, error capture tests | `[ ]` document executor contract | `[ ]` Not started |
| Task 6 - Implement Trace Logger | `[ ]` `tools/trace_logger.py`, `logs/traces/` | `[ ]` append and save trace tests | `[ ]` document trace fields | `[ ]` Not started |
| Task 7 - Implement P0 Agents | `[ ]` supervisor, schema, metric, generator, reviewer, fixer, insight agents | `[ ]` structured output and boundary tests | `[ ]` document Agent/Tool responsibilities | `[ ]` Not started |
| Task 8 - Implement LangGraph Workflow | `[ ]` `graph/state.py`, `graph/nodes.py`, `graph/workflow.py` | `[ ]` success, blocked SQL, one-retry repair tests | `[ ]` document workflow edges | `[ ]` Not started |
| Task 9 - Implement Streamlit Demo | `[ ]` glass-box app sections | `[ ]` import/smoke test and manual launch check | `[ ]` README demo section | `[ ]` Not started |
| Task 10 - Implement P0 Eval | `[ ]` `eval/test_questions.json`, `eval/run_eval.py`, `eval/report.md` | `[ ]` eval runner and report tests | `[ ]` README eval result summary | `[ ]` Not started |
| P0 final README update | `[ ]` startup, architecture, demo examples, eval result | `[ ]` verify commands documented match reality | `[ ]` final P0 docs complete | `[ ]` Not started |

### P0 Acceptance Tracker

- `[ ]` User can enter a Chinese business question in Streamlit.
- `[x]` System calls `get_database_schema()` against the real SQLite schema.
- `[x]` System calls `retrieve_metric_definition()` for GMV and related metrics.
- `[ ]` SQL Generator produces SELECT SQL.
- `[ ]` SQL Reviewer calls `validate_sql()`.
- `[ ]` Dangerous SQL is rejected before `run_sql()`.
- `[ ]` SQL Executor calls `run_sql()` against SQLite.
- `[ ]` Failed SQL execution enters Error Fix Agent once.
- `[ ]` Fixed SQL is revalidated and rerun.
- `[ ]` Final answer is grounded in `execution_result`.
- `[ ]` Each run creates a complete `trace.json`.
- `[ ]` `eval/run_eval.py` runs 20 test questions.
- `[ ]` README includes startup, architecture, demo examples, and eval results.

## P1 - Reliable Analysis & Report Core

| Task | Development | Tests | Docs | Status |
|---|---|---|---|---|
| Task 11 - Business Context Retrieval | `[ ]` context files, context tool, context agent | `[ ]` retrieval relevance tests | `[ ]` context source docs | `[ ]` Not started |
| Task 12 - Evidence Validator | `[ ]` evidence validator agent/tool | `[ ]` unsupported claim blocking tests | `[ ]` evidence output docs | `[ ]` Not started |
| Task 13 - Chart Agent | `[ ]` chart agent and chart tool | `[ ]` chart generation tests | `[ ]` chart artifact docs | `[ ]` Not started |
| Task 14 - Report Agent | `[ ]` report agent and report tool | `[ ]` report save and traceability tests | `[ ]` report structure docs | `[ ]` Not started |

## P2 - Business Review & Action Workflow

| Task | Development | Tests | Docs | Status |
|---|---|---|---|---|
| Task 15 - Business Review Report | `[ ]` report supervisor and multi-SQL report flow | `[ ]` weekly report completeness tests | `[ ]` weekly report docs | `[ ]` Not started |
| Task 16 - Action Workflow | `[ ]` action planner, risk assessor, approval, verifier, audit tools | `[ ]` approval/action/audit tests | `[ ]` action workflow docs | `[ ]` Not started |

## P3 - MCP & Engineering Core

| Task | Development | Tests | Docs | Status |
|---|---|---|---|---|
| Task 17 - MCP Tool Layer | `[ ]` database, report, and action MCP servers | `[ ]` MCP tool contract tests | `[ ]` MCP server docs | `[ ]` Not started |
| Task 18 - FastAPI + Async Run API | `[ ]` run API and status model | `[ ]` API and run-state tests | `[ ]` API docs | `[ ]` Not started |
| Task 19 - Trace Dashboard | `[ ]` dashboard views and metrics | `[ ]` dashboard data tests | `[ ]` dashboard docs | `[ ]` Not started |
| Docker / CI | `[ ]` Dockerfile, compose, CI workflow | `[ ]` CI test command | `[ ]` deployment docs | `[ ]` Not started |

## Update Rules

After every task:

1. Update `Last updated`.
2. Move `Current task` and `Last completed task`.
3. Update the relevant phase row in `Phase Overview`.
4. Mark task-level Development, Tests, Docs, and Status fields.
5. Update acceptance trackers when a capability becomes real and verified.
6. Record the exact verification command in the final response for that task.

## Latest Verification

Task 4 verification:

```bash
python3 -m pytest tests/test_sql_validator.py
python3 -m pytest
python3 -c 'from tools.schema_tool import get_database_schema; from tools.metric_tool import retrieve_metric_definition; from tools.sql_validator import validate_sql; import json; schema=get_database_schema("data/ecommerce.db"); metric=retrieve_metric_definition("最近 30 天销售额最高的 5 个商品是什么？"); sql="SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS sales FROM orders o JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id WHERE o.status = '\''paid'\'' GROUP BY p.product_name ORDER BY sales DESC LIMIT 5"; print(json.dumps(validate_sql(sql, schema, metric), ensure_ascii=False, indent=2))'
python3 -c 'from tools.schema_tool import get_database_schema; from tools.sql_validator import validate_sql; import json; schema=get_database_schema("data/ecommerce.db"); print(json.dumps(validate_sql("DELETE FROM orders WHERE status = '\''cancelled'\''", schema), ensure_ascii=False, indent=2))'
python3 -c 'from tools.schema_tool import get_database_schema; from tools.sql_validator import validate_sql; import json; schema=get_database_schema("data/ecommerce.db"); print(json.dumps(validate_sql("SELECT id, order_date FROM orders", schema), ensure_ascii=False, indent=2))'
```

Result: safe metric-aware SELECT SQL is approved; DELETE is rejected; multi-statement SQL, unknown tables/columns, sensitive fields, wrong GMV formulas, and missing paid filters are detected; safe SELECT without LIMIT is normalized with `LIMIT 100`; validator output includes trace-ready events.

Task 3 verification:

```bash
python3 -m pytest tests/test_schema_tool.py
python3 -m pytest
python3 -c 'from tools.schema_tool import get_database_schema; import json; result=get_database_schema("data/ecommerce.db"); print(json.dumps({"success": result["success"], "table_count": result["table_count"], "tables": [t["table_name"] for t in result["tables"]], "trace_event": result["trace_event"]}, ensure_ascii=False, indent=2)); print(result["schema_text"].split("\n\n")[2])'
```

Result: schema tool reads 5 SQLite tables, returns columns with types and primary-key/not-null flags, includes foreign keys, emits prompt-friendly `schema_text`, handles empty/missing databases, and includes trace-ready events.

Task 2 verification:

```bash
python3 -m pytest tests/test_metric_tool.py
python3 -m pytest
python3 -c 'from tools.metric_tool import retrieve_metric_definition; import json; print(json.dumps(retrieve_metric_definition("最近 30 天销售额最高的 5 个商品是什么？"), ensure_ascii=False, indent=2))'
python3 -c 'from tools.metric_tool import retrieve_metric_definition; import json; print(json.dumps(retrieve_metric_definition("帮我分析用户喜欢什么颜色"), ensure_ascii=False, indent=2))'
```

Result: metric definitions load from `data/metrics.yaml`; sales questions return `gmv` with formula and paid-order filter; product/category questions return grouped metric context; unknown questions return structured `success: false` errors with trace-ready events.

Task 1 verification:

```bash
python3 -m pytest tests/test_seed_data.py
python3 data/seed_data.py
sqlite3 data/ecommerce.db "SELECT COUNT(*) FROM users;"
sqlite3 data/ecommerce.db "SELECT status, COUNT(*) FROM orders GROUP BY status ORDER BY status;"
sqlite3 data/ecommerce.db "SELECT MIN(order_date), MAX(order_date), ROUND(julianday(MAX(order_date)) - julianday(MIN(order_date)), 0) FROM orders;"
sqlite3 data/ecommerce.db "SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv FROM orders o JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id WHERE o.status = 'paid' GROUP BY p.product_name ORDER BY gmv DESC LIMIT 5;"
```

Result: `data/ecommerce.db` was generated with 120 users, 540 orders, 1,336 order items, 36 products, and 6 categories. Order statuses include `paid`, `cancelled`, and `refunded`; order dates span 330 days; paid GMV JOIN queries return ranked product results.

Task 0 verification:

```bash
python3 -m pytest
/private/tmp/insightflow-task0-venv/bin/python -m pip install -r requirements.txt
/private/tmp/insightflow-task0-venv/bin/python -m pytest
curl -I http://127.0.0.1:8501
```

Result: scaffold tests pass, dependencies install in a temporary venv, and the Streamlit shell returns HTTP 200 locally.
