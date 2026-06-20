# InsightFlow Agent Development Status

Last updated: 2026-06-20

This file is the living development tracker for InsightFlow Agent. Update it after every completed task, test milestone, or scope change.

## Status Legend

- `[x]` Done
- `[~]` In progress
- `[ ]` Not started
- `[!]` Blocked or needs decision

## Current Snapshot

| Field | Status |
|---|---|
| Current phase | P3 - MCP & Engineering Core |
| Current task | Task 20 - LLM Provider and PromptOps Core (complete; Task 20A not started) |
| Last completed task | Task 20 - LLM Provider and PromptOps Core |
| Main demo target | Multi-Agent + Tool Calling + SQL Execution Feedback |
| Active frontend | Streamlit |
| Out of scope for current P3 baseline | React frontend, RBAC, full ActionOps product suite, and unguarded LLM-driven SQL/report generation |

## Phase Overview

| Phase | Goal | Development | Tests | Docs | Overall |
|---|---|---|---|---|---|
| P0 | Agentic SQL Core | `[x]` scaffold, ecommerce DB, metric definitions, schema tool, SQL validator, SQL executor, trace logger, P0 agents, LangGraph workflow, Streamlit demo, eval, and final docs complete | `[x]` 55 tests passing; eval 20/20 passing | `[x]` README includes setup, architecture, demo, limits, and eval result | `[x]` Done |
| P1 | Reliable Analysis & Report Core | `[x]` Task 11 business context retrieval, Task 12 evidence validation, Task 13 chart generation, and Task 14 report generation complete | `[x]` Task 14 tests passing; full suite remains passing after Task 15; eval 20/20 passing | `[x]` Task 14 README and status docs updated | `[x]` Done |
| P2 | Business Review & Action Workflow | `[x]` Task 15 business review report, Task 15A controlled LLM report planning, Task 15B guarded LLM SQL/insight enhancement, and Task 16 action workflow complete | `[x]` Task 16 tests passing; full suite 92/92 passing; eval 20/20 passing | `[x]` Task 16 README and status docs updated | `[x]` Done |
| P3 | MCP & Engineering Core | `[~]` Task 17 MCP-style tool layer, Task 18 FastAPI async run API, Task 19 Trace Dashboard data layer, Task 19A Streamlit unified demo, and Task 20 LLM Provider/PromptOps core complete; CI, question understanding, and SQL routing hardening are not started | `[x]` Task 20 tests passing; full suite 116/116 passing; eval 20/20 passing | `[x]` Task 20 README and status docs updated | `[~]` In progress |

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

## LLM Enhancement Plan

The completed P0 and P1 workflow does not require an LLM or API key. Existing deterministic Agents, tools, validators, reports, and traces remain the baseline behavior.

LLM enhancement is planned as a controlled layer, not as a replacement for tool-calling verification:

- **P2 placement**: use LLMs where natural-language planning and writing help the most, especially report task decomposition, weekly report section outlines, business-language polishing, and clarification questions.
- **P2 guarded SQL placement**: allow LLM-generated SQL candidates only after schema, metric, and business context retrieval, and only if every candidate passes `validate_sql()` before `run_sql()`.
- **P3 placement**: harden model usage through provider abstraction, prompt templates, prompt/version tracking, cost and latency metadata, LLM-specific evals, and trace/observability integration.
- **P3 question understanding placement**: add a structured intent and clarification router that extracts metric, dimension, time range, filters, operation, limit, and risk flags before SQL planning.
- **P3 SQL planning placement**: add a router that chooses deterministic template SQL, guarded LLM SQL candidate generation, clarification, or rejection based on completeness, confidence, and safety.

LLM safety boundaries:

- The LLM must not execute SQL directly.
- The LLM must not bypass `validate_sql()`.
- The LLM must not override `Evidence Validator`.
- The LLM must not create final evidence-backed claims without SQL results, business context, or validated evidence.
- The LLM must not trigger action tools without approval gates and audit logging.

## P2 - Business Review & Action Workflow

| Task | Development | Tests | Docs | Status |
|---|---|---|---|---|
| Task 15 - Business Review Report | `[x]` deterministic Report Supervisor, structured report sections, multi-SQL subtasks, per-task review/execution/evidence/chart records, weekly Markdown save, and trace save | `[x]` `tests/test_report_supervisor.py`; full suite and P0 eval passing | `[x]` weekly report docs in README and status tracker | `[x]` Done |
| Task 15A - Controlled LLM Report Planner | `[x]` optional provider hook, prompt safety contract, allowlisted structured report plan, deterministic fallback, and clarification-question support | `[x]` mocked-provider tests, malformed-response fallback tests, clarification tests, and supervisor integration tests | `[x]` controlled planner interface, no-key fallback, and safety boundaries documented | `[x]` Done |
| Task 15B - Guarded LLM SQL and Insight Enhancement | `[x]` optional guarded SQL candidate agent and guarded insight enhancer behind schema, metric, context, SQL validation, Evidence Validator, and trace | `[x]` valid candidate acceptance, unsafe SQL rejection, deterministic fallback, and unsupported-claim blocking tests | `[x]` guarded SQL/insight usage and safety boundaries documented | `[x]` Done |
| Task 16 - Action Workflow | `[x]` Action Planner, Risk Assessor, Approval Gate, Action Executor, Action Verifier, SQLite action tools, approval records, and audit logs | `[x]` approval blocking, approved execution, task/alert creation, verification, and audit tests | `[x]` action workflow usage and approval boundaries documented | `[x]` Done |

### P2 Acceptance Tracker

- `[x]` Report Supervisor decomposes weekly report questions into structured `report_sections`.
- `[x]` Core modules include weekly GMV, order count, AOV, Top products, Top categories, declining categories, and next-week recommendations.
- `[x]` A weekly report task executes multiple SQL subtasks.
- `[x]` Each SQL subtask stores SQL, `review_result`, and `execution_result`.
- `[x]` Failed subtasks are recorded structurally and do not crash the report workflow.
- `[x]` Weekly Markdown reports save as `{run_id}_weekly_business_report.md`.
- `[x]` Reports include SQL, execution evidence, chart paths, and trace path.
- `[x]` Evidence Validator separates supported findings, hypotheses, and unsupported claims.
- `[x]` Agent and Tool boundaries remain clear: Report Supervisor orchestrates state; existing tools validate SQL, execute SQL, generate charts, save reports, and save traces.
- `[x]` Task 15 has dedicated tests.
- `[x]` Existing P0/P1 tests remain passing after Task 15.
- `[x]` P0 eval remains 20/20 passing after Task 15.
- `[x]` README and DEVELOPMENT_STATUS are updated for Task 15.
- `[x]` Controlled Report Planner accepts mocked provider output only as allowlisted section IDs.
- `[x]` Controlled Report Planner ignores provider-supplied SQL and keeps deterministic section SQL templates.
- `[x]` Missing or malformed provider responses fall back to deterministic Task 15 report sections.
- `[x]` Clarification-question responses stop before SQL execution and set `report_plan_needs_clarification`.
- `[x]` Report Supervisor can optionally use the controlled planner while default behavior remains deterministic.
- `[x]` Task 15A has dedicated tests.
- `[x]` Existing P0/P1/P2 Task 15 tests remain passing after Task 15A.
- `[x]` P0 eval remains 20/20 passing after Task 15A.
- `[x]` README and DEVELOPMENT_STATUS are updated for Task 15A.
- `[x]` Guarded SQL candidate prompt includes schema, metric context, business context, and explicit no-execution contract.
- `[x]` Guarded SQL candidate agent accepts only SQL approved by `validate_sql()`.
- `[x]` Unsafe, sensitive-field, malformed, or missing LLM SQL candidates fall back to deterministic SQL.
- `[x]` Guarded SQL candidate agent does not call `run_sql()`.
- `[x]` Guarded insight enhancer validates provider claims through Evidence Validator.
- `[x]` Unsupported LLM claims are recorded and excluded from guarded summaries.
- `[x]` Task 15B has dedicated tests.
- `[x]` Existing P0/P1/P2 Task 15/15A tests remain passing after Task 15B.
- `[x]` P0 eval remains 20/20 passing after Task 15B.
- `[x]` README and DEVELOPMENT_STATUS are updated for Task 15B.
- `[x]` Action Planner generates structured `action_plan` records from evidence-backed findings.
- `[x]` Risk Assessor marks action tools as requiring approval.
- `[x]` Approval Gate blocks unapproved actions before task, alert, or email draft creation.
- `[x]` Approved `create_task` and `create_metric_alert` actions write SQLite records.
- `[x]` Action Verifier confirms created task and alert records exist.
- `[x]` Audit Logger records approval blocking, action execution, and action verification events.
- `[x]` Task 16 has dedicated tests.
- `[x]` Existing P0/P1/P2 Task 15/15A/15B tests remain passing after Task 16.
- `[x]` P0 eval remains 20/20 passing after Task 16.
- `[x]` README and DEVELOPMENT_STATUS are updated for Task 16.

## P3 - MCP & Engineering Core

| Task | Development | Tests | Docs | Status |
|---|---|---|---|---|
| Task 17 - MCP Tool Layer | `[x]` `mcp_servers/` database, report, and action MCP-style contract wrappers | `[x]` `tests/test_mcp_tool_layer.py`; full suite and P0 eval passing | `[x]` MCP layer docs in README and status tracker | `[x]` Done |
| Task 18 - FastAPI + Async Run API | `[x]` `api/` FastAPI app, in-memory run manager, status model, trace/events/cancel endpoints | `[x]` `tests/test_async_run_api.py`; full suite and P0 eval passing | `[x]` API docs in README and status tracker | `[x]` Done |
| Task 19 - Trace Dashboard | `[x]` `dashboard/` trace dashboard data layer for trace, eval, approval, and audit metrics | `[x]` `tests/test_trace_dashboard.py`; full suite and P0 eval passing | `[x]` dashboard data docs in README and status tracker | `[x]` Done |
| Task 19A - Streamlit Unified Demo | `[x]` multi-tab Streamlit product demo for SQL analysis, report generation, weekly review, action workflow, MCP contracts, async runs, and trace dashboard summaries | `[x]` Streamlit helper/UI tests and workflow smoke tests | `[x]` demo usage docs and UI scope notes | `[x]` Done |
| Task 20 - LLM Provider and PromptOps Core | `[x]` `llm_ops/` provider abstraction, prompt registry, prompt/version metadata, model cost/latency tracking, trace-ready provider metadata, and LLM eval harness | `[x]` `tests/test_llm_provider_promptops.py`; full suite and P0 eval passing | `[x]` provider setup, prompt governance, safety boundaries, and eval docs | `[x]` Done |
| Task 20A - Question Understanding & Clarification Router | `[ ]` intent slot extraction, completeness checks, clarification-question generation, and risk/sensitive-request routing | `[ ]` intent-slot tests, ambiguous-question tests, missing-slot tests, and rejection-routing tests | `[ ]` intent contract, clarification policy, and routing examples | `[ ]` Not started |
| Task 20B - SQL Planning Router | `[ ]` template-vs-LLM-candidate strategy router, confidence/reason payload, fallback policy, and template-mining feedback loop | `[ ]` template routing tests, `llm_candidate` routing tests, clarify/reject routing tests, and P0 eval preservation tests | `[ ]` router contract, strategy matrix, and eval plan | `[ ]` Not started |
| Docker / CI | `[ ]` Dockerfile, compose, CI workflow | `[ ]` CI test command | `[ ]` deployment docs | `[ ]` Not started |

### P3 Task 17 Acceptance Tracker

- `[x]` MCP-style tool contracts are exposed as JSON-compatible dictionaries.
- `[x]` `database-mcp-server` exposes `get_database_schema`, `get_sample_rows`, and `run_sql`.
- `[x]` Database MCP SQL execution internally runs schema lookup, metric context retrieval, SQL review, and only then SQL execution.
- `[x]` `report-mcp-server` exposes `generate_chart` and `save_report`.
- `[x]` Report saving requires successful evidence validation and rejects blocked unsupported claims.
- `[x]` `action-mcp-server` exposes `create_task`, `create_metric_alert`, and `create_email_draft`.
- `[x]` Action MCP wrappers require approved action status before writing task, alert, or email draft records.
- `[x]` Internal SQL review, permission/approval record tools, trace logging, and eval runner are not exposed as MCP tools.
- `[x]` MCP wrappers return `success: false` and structured errors instead of raising workflow-breaking exceptions for expected failures.
- `[x]` Task 17 has dedicated tests.
- `[x]` Existing P0/P1/P2 tests remain passing after Task 17.
- `[x]` P0 eval remains 20/20 passing after Task 17.
- `[x]` README and DEVELOPMENT_STATUS are updated for Task 17.

### P3 Task 18 Acceptance Tracker

- `[x]` `POST /api/runs` creates an async workflow run and returns a `run_id`.
- `[x]` `GET /api/runs/{run_id}` returns run status, summary, timestamps, final answer, trace path, and errors.
- `[x]` `GET /api/runs/{run_id}/trace` returns trace data without requiring the dashboard.
- `[x]` `GET /api/runs/{run_id}/events` returns run lifecycle events.
- `[x]` `POST /api/runs/{run_id}/cancel` marks active runs as `cancelled`.
- `[x]` Supported statuses include `queued`, `running`, `waiting_for_approval`, `completed`, `failed`, and `cancelled`.
- `[x]` API execution calls the existing `graph.workflow.run_workflow()` and preserves deterministic SQL review, execution, repair, insight, and trace behavior.
- `[x]` Workflow failures map to structured API `failed` responses instead of crashing the API.
- `[x]` Unknown run IDs return structured HTTP 404 responses.
- `[x]` Task 18 has dedicated tests.
- `[x]` Existing P0/P1/P2/P3 Task 17 tests remain passing after Task 18.
- `[x]` P0 eval remains 20/20 passing after Task 18.
- `[x]` README and DEVELOPMENT_STATUS are updated for Task 18.
- `[x]` Task 18 does not implement Task 19 Trace Dashboard, SSE, React, RBAC, Docker/CI, persistent queueing, or provider/prompt features.

### P3 Task 19 Acceptance Tracker

- `[x]` Trace Dashboard data layer reads trace JSON artifacts.
- `[x]` Dashboard output includes Agent node latency totals and averages.
- `[x]` Dashboard output includes tool call counts.
- `[x]` Dashboard output includes SQL execution latency totals and averages.
- `[x]` Dashboard output includes SQL repair count.
- `[x]` Dashboard output includes failure type distribution, using eval distribution when supplied.
- `[x]` Dashboard output includes eval totals and pass rate when supplied.
- `[x]` Dashboard output includes Action approval records from the action SQLite DB.
- `[x]` Dashboard output includes Audit Log records from the action SQLite DB.
- `[x]` Bad trace files and unreadable action DBs are reported in `load_errors` instead of crashing.
- `[x]` Task 19 has dedicated tests.
- `[x]` Existing P0/P1/P2/P3 Task 17/18 tests remain passing after Task 19.
- `[x]` P0 eval remains 20/20 passing after Task 19.
- `[x]` README and DEVELOPMENT_STATUS are updated for Task 19.
- `[x]` Task 19 does not implement React, Streamlit UI changes, SSE, RBAC, Docker/CI, provider abstraction, PromptOps, or new LLM behavior.

### P3 Task 19A Acceptance Tracker

- `[x]` Streamlit entry point clearly communicates that P0/P1/P2/P3 backend capabilities exist beyond the original P0 SQL demo.
- `[x]` SQL Analysis view preserves the current glass-box P0 workflow presentation.
- `[x]` Report Generation view exposes P1 evidence validation, chart generation, and Markdown report saving in a clear flow.
- `[x]` Weekly Business Review view exposes P2 report supervisor output, report sections, SQL subtasks, evidence, charts, and saved report path.
- `[x]` Action Workflow view shows action planning, risk assessment, approval gate state, created task/alert/email draft records, verification, and audit log output.
- `[x]` MCP Tool Layer view shows database/report/action tool contracts and safe wrapper outputs without exposing internal validators or audit modules as external tools.
- `[x]` Async Run API view explains local API usage and can show run status, trace, and events in a demo-friendly way.
- `[x]` Trace Dashboard view calls `build_trace_dashboard()` and presents node latency, tool counts, SQL execution latency, repair count, eval pass rate, approvals, and audit logs.
- `[x]` Page copy and layout are clear for demos: no misleading P0-only subtitle, no hidden P1/P2/P3 capabilities, and no raw JSON wall where a table or summary is clearer.
- `[x]` UI does not bypass SQL Validator, Evidence Validator, approval gate, MCP boundaries, or existing deterministic workflow contracts.
- `[x]` Task 19A has dedicated tests for Streamlit helper functions and smoke paths.
- `[x]` Existing P0/P1/P2/P3 tests and P0 eval remain passing after Task 19A.
- `[x]` Task 19A does not implement React, RBAC, Docker/CI, persistent queues, provider abstraction, PromptOps, or new LLM behavior.

### P3 Task 20 Acceptance Tracker

- `[x]` `llm_ops.provider.LLMRequest` defines a clear provider request contract with prompt id, prompt version, model, and metadata.
- `[x]` `run_llm_request()` returns JSON-compatible structured output with `success`, `content`, `usage`, `latency_ms`, `error`, and `trace_event`.
- `[x]` Provider failures return `success: false` and structured `llm_provider_error` trace metadata instead of raising workflow-breaking exceptions.
- `[x]` `llm_ops.prompt_registry.DEFAULT_PROMPT_REGISTRY` stores versioned prompts for report planning, guarded SQL candidates, and guarded insight claims.
- `[x]` Prompt rendering reports missing variables as structured errors.
- `[x]` Guarded SQL candidate prompt metadata includes no-execution and no-`validate_sql()`-bypass safety contracts.
- `[x]` Guarded insight prompt metadata requires Evidence Validator verification before claims can be used.
- `[x]` Provider trace events include model, prompt id, prompt version, token usage, estimated cost, and latency metadata.
- `[x]` `llm_ops.eval_smoke.run_llm_smoke_eval()` runs deterministic mock-provider smoke cases without requiring an API key.
- `[x]` Task 20 does not implement Task 20A Question Understanding, Task 20B SQL Planning Router, real provider integration, React, RBAC, Docker/CI, or full ActionOps.
- `[x]` Existing P0/P1/P2/P3 tests and P0 eval remain passing after Task 20.

### P3 Planned Router Additions

- Question Understanding & Clarification Router extracts `metric`, `dimension`, `time_range`, `filters`, `operation`, `limit`, and `risk_flags` from user questions.
- Ambiguous or incomplete questions return `strategy: clarify` with focused clarification questions instead of forcing SQL generation.
- Sensitive, unsafe, or unsupported requests return `strategy: reject` or route to a safety path before SQL generation.
- SQL Planning Router chooses one of `template`, `llm_candidate`, `clarify`, or `reject` and records confidence, matched template, missing slots, risk flags, and reason.
- Deterministic templates remain the default for stable BI questions; LLM SQL candidates remain optional and must pass `validate_sql()` before any execution.
- Repeated successful `llm_candidate` patterns should feed back into deterministic template expansion, preserving eval stability and reducing future model cost.

## Update Rules

After every task:

1. Update `Last updated`.
2. Move `Current task` and `Last completed task`.
3. Update the relevant phase row in `Phase Overview`.
4. Mark task-level Development, Tests, Docs, and Status fields.
5. Update acceptance trackers when a capability becomes real and verified.
6. Record the exact verification command in the final response for that task.

## Latest Verification

Task 20 verification:

```bash
python3 -m pytest tests/test_llm_provider_promptops.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 20 LLM Provider/PromptOps tests report 5/5 passed; the full test suite reports 116/116 passed with one FastAPI TestClient deprecation warning from Starlette; P0 eval reports 20/20 passed. The `llm_ops` layer now provides versioned prompt templates, a mockable provider contract, structured failure handling, model cost/latency trace metadata, and a deterministic LLM smoke eval harness without changing the default no-key workflow.

Task 19A verification:

```bash
python3 -m pytest tests/test_streamlit_app.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 19A Streamlit unified demo tests report 13/13 passed; the full test suite reports 111/111 passed with one FastAPI TestClient deprecation warning from Starlette; P0 eval reports 20/20 passed. The Streamlit app now exposes SQL Analysis, Report Generation, Weekly Business Review, Action Workflow, MCP Tool Layer, Async Run API, and Trace Dashboard views without changing core backend safety boundaries.

Task 19 verification:

```bash
python3 -m pytest tests/test_trace_dashboard.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 19 trace dashboard tests report 3/3 passed; the full test suite reports 106/106 passed with one FastAPI TestClient deprecation warning from Starlette; P0 eval reports 20/20 passed. The dashboard data layer summarizes trace node latency, tool calls, SQL execution latency, SQL repair count, failure distribution, eval pass rate, action approvals, and audit logs without adding frontend/dashboard UI infrastructure.

Task 18 verification:

```bash
python3 -m pytest tests/test_async_run_api.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 18 async run API tests report 4/4 passed; the full test suite reports 103/103 passed with one FastAPI TestClient deprecation warning from Starlette; P0 eval reports 20/20 passed. The API creates async runs, exposes status, trace, and events, maps workflow failure to `failed`, marks active runs as `cancelled`, and preserves the existing deterministic LangGraph workflow.

Task 17 verification:

```bash
python3 -m pytest tests/test_mcp_tool_layer.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 17 MCP tool layer tests report 5/5 passed; the full test suite reports 99/99 passed; P0 eval reports 20/20 passed. Database MCP wrappers expose schema, sample rows, and reviewed SQL execution without bypassing SQL review; report MCP wrappers generate charts and require evidence validation before saving reports; action MCP wrappers require approved status before creating task, metric alert, or email draft records.

Task 16 verification:

```bash
python3 -m pytest tests/test_action_workflow.py tests/test_report_supervisor.py tests/test_report_planner.py tests/test_guarded_llm_enhancer.py
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 16 action workflow tests plus P2 report/planner/guarded-LLM tests report 15/15 passed; the full test suite reports 92/92 passed; P0 eval reports 20/20 passed. Action Planner generates structured action plans, Risk Assessor triggers approval, Approval Gate blocks unapproved actions, approved task and metric alert actions write SQLite records, Action Verifier confirms records exist, and Audit Logger records approval and execution events.

Task 15B verification:

```bash
python3 -m pytest tests/test_guarded_llm_enhancer.py tests/test_report_planner.py tests/test_report_supervisor.py
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 15B guarded LLM tests plus Task 15A planner and Task 15 supervisor tests report 11/11 passed; the full test suite reports 88/88 passed; P0 eval reports 20/20 passed. Guarded SQL candidates are validated before acceptance, unsafe SQL and sensitive-field candidates fall back to deterministic SQL, no SQL execution happens in the enhancer, and guarded insight output excludes unsupported LLM claims through Evidence Validator.

Task 15A verification:

```bash
python3 -m pytest tests/test_report_planner.py tests/test_report_supervisor.py
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 15A report-planner tests plus Task 15 supervisor tests report 7/7 passed; the full test suite reports 84/84 passed; P0 eval reports 20/20 passed. Controlled Report Planner accepts mocked provider output only as allowlisted section IDs, ignores provider-supplied SQL, falls back on missing or malformed provider responses, supports clarification questions without executing report SQL, and integrates with Report Supervisor as an optional path.

Task 15 verification:

```bash
python3 -m pytest tests/test_report_supervisor.py
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 15 tests report 3/3 passed; the full test suite reports 80/80 passed; P0 eval reports 20/20 passed. Report Supervisor plans weekly business report sections, executes multiple SQL subtasks through SQL review and SQL execution, records per-task evidence and chart paths, preserves failed subtasks without crashing, saves `{run_id}_weekly_business_report.md`, and writes the trace path used by the report.

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
