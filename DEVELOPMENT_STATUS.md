# InsightFlow Agent Development Status

Last updated: 2026-06-19

This file is the living development tracker for InsightFlow Agent. Update it after every completed task, test milestone, or scope change.

## Status Legend

- `[x]` Done
- `[~]` In progress
- `[ ]` Not started
- `[!]` Blocked or needs decision

## Current Snapshot

| Field | Status |
|---|---|
| Current phase | P2 - Business Review & Action Workflow |
| Current task | Task 15 - Business Review Report |
| Last completed task | Task 14 - Report Agent |
| Main demo target | Multi-Agent + Tool Calling + SQL Execution Feedback |
| Active frontend | Streamlit |
| Out of scope for current phase | MCP, FastAPI, React, async jobs, RBAC, Trace Dashboard, ActionOps |

## Phase Overview

| Phase | Goal | Development | Tests | Docs | Overall |
|---|---|---|---|---|---|
| P0 | Agentic SQL Core | `[x]` scaffold, ecommerce DB, metric definitions, schema tool, SQL validator, SQL executor, trace logger, P0 agents, LangGraph workflow, Streamlit demo, eval, and final docs complete | `[x]` 55 tests passing; eval 20/20 passing | `[x]` README includes setup, architecture, demo, limits, and eval result | `[x]` Done |
| P1 | Reliable Analysis & Report Core | `[x]` Task 11 business context retrieval, Task 12 evidence validation, Task 13 chart generation, and Task 14 report generation complete | `[x]` Task 14 tests passing; full suite 77/77 passing; eval 20/20 passing | `[x]` Task 14 README and status docs updated | `[x]` Done |
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
| Task 5 - Implement SQL Executor | `[x]` `tools/sql_executor.py` | `[x]` SELECT success, row cap, non-SELECT rejection, database error, missing DB, and multi-statement tests | `[x]` executor contract documented in README | `[x]` Done |
| Task 6 - Implement Trace Logger | `[x]` `tools/trace_logger.py`, `logs/traces/` | `[x]` append, failure/retry, save trace, and write-failure tests | `[x]` trace fields and usage documented in README | `[x]` Done |
| Task 7 - Implement P0 Agents | `[x]` supervisor, schema, metric, generator, reviewer, fixer, insight agents | `[x]` structured output, tool boundary, SQL generation, review, fix, and insight tests | `[x]` Agent/Tool responsibilities documented in README | `[x]` Done |
| Task 8 - Implement LangGraph Workflow | `[x]` `graph/state.py`, `graph/nodes.py`, `graph/workflow.py` | `[x]` success path, blocked SQL, one-retry repair, failed repair, and trace-save tests | `[x]` workflow edges and usage documented in README | `[x]` Done |
| Task 9 - Implement Streamlit Demo | `[x]` glass-box app with input, status, steps, SQL, review, execution, repair, answer, trace, and eval entry | `[x]` app helper tests, workflow-backed smoke tests, and Streamlit launch check | `[x]` README demo section updated | `[x]` Done |
| Task 10 - Implement P0 Eval | `[x]` `eval/test_questions.json`, `eval/run_eval.py`, `eval/report.md` | `[x]` 20-case count, runner summary, report generation, failed expectation, and CLI tests | `[x]` README eval command and result summary updated | `[x]` Done |
| P0 final README update | `[x]` startup, architecture, demo examples, eval result, current capability, and P0 limits documented | `[x]` full test suite and eval command verified | `[x]` final P0 docs complete | `[x]` Done |

### P0 Acceptance Tracker

- `[x]` User can enter a Chinese business question in Streamlit.
- `[x]` System calls `get_database_schema()` against the real SQLite schema.
- `[x]` System calls `retrieve_metric_definition()` for GMV and related metrics.
- `[x]` SQL Generator produces SELECT SQL.
- `[x]` SQL Reviewer calls `validate_sql()`.
- `[x]` Dangerous SQL is rejected before `run_sql()`.
- `[x]` SQL Executor calls `run_sql()` against SQLite.
- `[x]` Failed SQL execution enters Error Fix Agent once.
- `[x]` Fixed SQL is revalidated and rerun.
- `[x]` Final answer is grounded in `execution_result`.
- `[x]` Each run creates a complete `trace.json`.
- `[x]` `eval/run_eval.py` runs 20 test questions.
- `[x]` README includes startup, architecture, demo examples, and eval results.

## P1 - Reliable Analysis & Report Core

| Task | Development | Tests | Docs | Status |
|---|---|---|---|---|
| Task 11 - Business Context Retrieval | `[x]` `data/business_rules.md`, `data/table_docs.md`, `data/sql_examples.json`, `tools/context_tool.py`, `agents/context_retriever.py` | `[x]` context tool and context retriever tests | `[x]` README context source and interface docs | `[x]` Done |
| Task 12 - Evidence Validator | `[x]` `tools/evidence_tool.py`, `agents/evidence_validator.py`, state extension | `[x]` supported finding, hypothesis, unsupported claim blocking, Agent state/trace tests | `[x]` README evidence output and interface docs | `[x]` Done |
| Task 13 - Chart Agent | `[x]` `tools/chart_tool.py`, `agents/chart_agent.py`, state extension, `matplotlib` dependency | `[x]` chart file generation, chart type inference, Agent state/trace tests | `[x]` README chart output and interface docs | `[x]` Done |
| Task 14 - Report Agent | `[x]` `tools/report_tool.py`, `agents/report_agent.py`, state extension | `[x]` report save, traceable content, blocked claim exclusion, Agent state/trace tests | `[x]` README report output and interface docs | `[x]` Done |

### P1 Acceptance Tracker

- `[x]` Business context tool returns relevant business rules.
- `[x]` Business context tool returns relevant table and field documentation.
- `[x]` Business context tool returns relevant historical SQL examples.
- `[x]` Context Retriever Agent writes `business_context` into state.
- `[x]` Business context output is structured dict / JSON-compatible data.
- `[x]` Context load failures return `success: false` with an error instead of crashing.
- `[x]` Context retrieval emits trace-ready events and Agent appends them to trace.
- `[x]` Task 11 has dedicated tests.
- `[x]` Existing P0 tests and eval remain passing.
- `[x]` README and DEVELOPMENT_STATUS are updated for Task 11.
- `[x]` Evidence Validator separates data-supported findings, hypotheses, and unsupported claims.
- `[x]` Evidence Validator blocks deterministic claims without data support.
- `[x]` Evidence Validator computes `unsupported_claim_rate`.
- `[x]` Evidence Validator Agent writes `evidence_result` into state.
- `[x]` Evidence validation emits trace-ready events and Agent appends them to trace.
- `[x]` Task 12 has dedicated tests.
- `[x]` Existing P0 tests and eval remain passing after Task 12.
- `[x]` README and DEVELOPMENT_STATUS are updated for Task 12.
- `[x]` Chart Tool generates real PNG files.
- `[x]` Chart Agent infers bar charts for ranking questions.
- `[x]` Chart Agent infers line charts for trend questions.
- `[x]` Chart Agent writes `chart_path` and `chart_paths` into state.
- `[x]` Chart generation emits trace-ready events and Agent appends them to trace.
- `[x]` Task 13 has dedicated tests.
- `[x]` Existing P0 tests and eval remain passing after Task 13.
- `[x]` README and DEVELOPMENT_STATUS are updated for Task 13.
- `[x]` Report Tool saves real Markdown reports.
- `[x]` Report Agent writes `report_path` into state.
- `[x]` Reports include user question, metrics, SQL, execution result summary, evidence findings, hypotheses, chart paths, and trace path.
- `[x]` Reports exclude blocked unsupported claims as deterministic findings.
- `[x]` Report saving emits trace-ready events and Agent appends them to trace.
- `[x]` Task 14 has dedicated tests.
- `[x]` Existing P0 tests and eval remain passing after Task 14.
- `[x]` README and DEVELOPMENT_STATUS are updated for Task 14.

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

Task 14 verification:

```bash
python3 -m pytest tests/test_report_tool.py tests/test_report_agent.py
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 14 tests report 5/5 passed; the full test suite reports 77/77 passed; P0 eval reports 20/20 passed. Report Tool saves real Markdown files, Report Agent writes `report_path` into state, reports include SQL, execution result evidence, chart paths, and trace path, and blocked unsupported claims are excluded from deterministic findings.

Task 13 verification:

```bash
python3 -m pytest tests/test_chart_tool.py tests/test_chart_agent.py
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 13 tests report 6/6 passed; the full test suite reports 72/72 passed; P0 eval reports 20/20 passed. Chart Tool generates real PNG chart files, Chart Agent infers bar and line charts, writes `chart_path` and `chart_paths` into state, and appends trace without running SQL or generating reports.

Task 12 verification:

```bash
python3 -m pytest tests/test_evidence_tool.py tests/test_evidence_validator.py
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 12 tests report 6/6 passed; the full test suite reports 66/66 passed; P0 eval reports 20/20 passed. Evidence Validator classifies data-supported findings, hypotheses, and unsupported deterministic claims, computes `unsupported_claim_rate`, writes `evidence_result` into state, and appends trace without executing SQL or generating reports.

Task 11 verification:

```bash
python3 -m pytest tests/test_context_tool.py tests/test_context_retriever.py
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 11 tests report 5/5 passed; the full test suite reports 60/60 passed; P0 eval reports 20/20 passed. Business context retrieval returns matched business rules, table docs, historical SQL examples, structured failure payloads, and trace-ready events. Context Retriever Agent writes `business_context` into state and appends trace without accessing the database or executing SQL.

P0 final README update verification:

```bash
python3 eval/run_eval.py
python3 -m pytest
```

Result: P0 eval reports 20/20 passed and the full test suite reports 55/55 passed. README now documents setup, architecture, Streamlit demo, eval results, current capabilities, and P0 limitations.

Task 10 verification:

```bash
python3 -m pytest tests/test_eval_runner.py
python3 eval/run_eval.py
python3 -m pytest
```

Result: `eval/test_questions.json` contains 20 P0 cases; `eval/run_eval.py` runs all cases, writes `eval/report.md`, reports 20/20 passed, 100.00% dangerous SQL block rate, 100.00% SQL repair success rate, and 100.00% metric definition accuracy.

Task 9 verification:

```bash
python3 -m pytest tests/test_streamlit_app.py
python3 -m pytest
python3 -m streamlit run app.py --server.headless true --server.port 8501
curl -I http://localhost:8501
```

Result: Streamlit app exposes a Chinese business question input, runs `run_workflow()`, displays Agent Steps, Generated SQL, SQL Review, Execution Result, Error Repair, Final Answer, Trace JSON, and Eval command entry; the local Streamlit server responds with HTTP 200.

Task 8 verification:

```bash
python3 -m pytest tests/test_workflow.py
python3 -m pytest
python3 -c 'from graph.workflow import run_workflow; import json, tempfile; result=run_workflow("最近 30 天销售额最高的 5 个商品是什么？", db_path="data/ecommerce.db", trace_dir=tempfile.mkdtemp(), run_id="run_manual", session_id="session_manual"); print(json.dumps({"status": result["status"], "approved": result["review_result"]["approved"], "execution_success": result["execution_result"]["success"], "trace_path": result["trace_path"], "trace_nodes": [event["node"] for event in result["trace"]]}, ensure_ascii=False, indent=2))'
```

Result: LangGraph workflow completes the success path, blocks dangerous SQL before execution, retries one execution failure through Error Fix Agent, revalidates and reruns fixed SQL, returns non-fabricated failure responses, and writes `logs/traces/{run_id}.json`.

Task 7 verification:

```bash
python3 -m pytest tests/test_p0_agents.py
python3 -m pytest
python3 -c 'from agents.supervisor import initialize_run; from agents.schema_agent import run_schema_agent; from agents.metric_agent import run_metric_agent; from agents.sql_generator import run_sql_generator; from agents.sql_reviewer import run_sql_reviewer; import json; state=initialize_run("最近 30 天销售额最高的 5 个商品是什么？", run_id="run_manual", session_id="session_manual"); state=run_schema_agent(state, "data/ecommerce.db"); state=run_metric_agent(state); state=run_sql_generator(state); state=run_sql_reviewer(state); print(json.dumps({"generated_sql": state["generated_sql"], "approved": state["review_result"]["approved"], "trace_nodes": [event["node"] for event in state["trace"]]}, ensure_ascii=False, indent=2))'
```

Result: P0 agents initialize run state, call schema/metric/review tools through clear boundaries, generate parseable SELECT SQL, reject dangerous SQL through `validate_sql()`, repair the known `oi.price` column error once without executing SQL, and generate insight text only from `execution_result`.

Task 6 verification:

```bash
python3 -m pytest tests/test_trace_logger.py
python3 -m pytest
python3 -c 'from tools.trace_logger import append_trace, save_trace; import json, tempfile; state={"run_id":"run_manual","session_id":"session_manual","trace":[]}; state=append_trace(state, {"node":"sql_executor","tool_name":"run_sql","tool_input_summary":"SELECT 1","tool_output_summary":"1 row returned","status":"success","latency_ms":1}); result=save_trace("run_manual", state["trace"], trace_dir=tempfile.mkdtemp(), session_id="session_manual", status="success"); print(json.dumps(result, ensure_ascii=False, indent=2))'
```

Result: trace events are appended without mutating the original state, required trace fields are normalized, failure and retry details are preserved, traces save as JSON files, and write failures return structured `success: false` payloads with trace-ready events.

Task 5 verification:

```bash
python3 -m pytest tests/test_sql_executor.py
python3 -m pytest
python3 -c 'from tools.sql_executor import run_sql; import json; sql="SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv FROM orders o JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id WHERE o.status = '\''paid'\'' GROUP BY p.product_name ORDER BY gmv DESC LIMIT 5"; print(json.dumps(run_sql("data/ecommerce.db", sql), ensure_ascii=False, indent=2))'
python3 -c 'from tools.sql_executor import run_sql; import json; print(json.dumps(run_sql("data/ecommerce.db", "SELECT oi.price FROM order_items oi LIMIT 5"), ensure_ascii=False, indent=2))'
```

Result: approved SELECT SQL runs against `data/ecommerce.db` and returns columns/rows/row counts; results are capped by `max_rows`; non-SELECT and multi-statement SQL are rejected; SQLite errors such as `no such column: oi.price` return structured `success: false` payloads with trace-ready events.

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
