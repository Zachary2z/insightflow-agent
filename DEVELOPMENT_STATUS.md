# InsightFlow Agent Development Status

Last updated: 2026-06-23

This file is the living development tracker for InsightFlow Agent. Update it after every completed task, test milestone, or scope change.

## Status Legend

- `[x]` Done
- `[~]` In progress
- `[ ]` Not started
- `[!]` Blocked or needs decision

## Current Snapshot

| Field | Status |
|---|---|
| Current phase | P11 - General Data Analysis Product hardening |
| Current task | P11 Product Hardening H5 - current product documentation cleanup |
| Next planned task | H5 current product documentation cleanup |
| Last completed task | H4 natural live DeepSeek workspace acceptance |
| Main demo target | User workspace analysis over CSV, Excel, or SQLite data with real upload/API flow, profiling, semantic draft, validated SQL, evidence, charts, traces, Next.js UI, and live DeepSeek acceptance |
| Active frontend | Next.js + React + TypeScript |
| Out of scope for current P11 | P12 automated report productization, P13 real Jira/Slack/Email/Power BI SaaS integrations, auth/RBAC, deployment, and unguarded LLM-driven execution |

## Phase Overview

| Phase | Goal | Development | Tests | Docs | Overall |
|---|---|---|---|---|---|
| P0 | Agentic SQL Core | `[x]` scaffold, ecommerce DB, metric definitions, schema tool, SQL validator, SQL executor, trace logger, P0 agents, LangGraph workflow, Streamlit demo, eval, and final docs complete | `[x]` 55 tests passing; eval 20/20 passing | `[x]` README includes setup, architecture, demo, limits, and eval result | `[x]` Done |
| P1 | Reliable Analysis & Report Core | `[x]` Task 11 business context retrieval, Task 12 evidence validation, Task 13 chart generation, and Task 14 report generation complete | `[x]` Task 14 tests passing; full suite remains passing after Task 15; eval 20/20 passing | `[x]` Task 14 README and status docs updated | `[x]` Done |
| P2 | Business Review & Action Workflow | `[x]` Task 15 business review report, Task 15A controlled LLM report planning, Task 15B guarded LLM SQL/insight enhancement, and Task 16 action workflow complete | `[x]` Task 16 tests passing; full suite 92/92 passing; eval 20/20 passing | `[x]` Task 16 README and status docs updated | `[x]` Done |
| P3 | MCP & Engineering Core | `[x]` Task 17 MCP-style tool layer, Task 18 FastAPI async run API, Task 19 Trace Dashboard data layer, Task 19A Streamlit unified demo, Streamlit Command Center UI hardening, Task 20 LLM Provider/PromptOps core, Task 20C production DeepSeek provider hardening, Task 20A question understanding, Task 20B SQL planning router, Task 21 provider-backed question understanding, Task 21A runtime workflow wiring, Task 22 provider-backed clarification router, Task 23 provider-assisted SQL planning/guarded candidate integration, Task 24 LLM business review decomposition, Task 25 evidence-backed report writing, Task 26 guarded insight claim typing, Task 27 action/email drafting, and Task 28 template mining/eval suite complete; Docker/CI deferred unless explicitly selected | `[x]` Task 28 full suite 185+ passed / live tests skipped by default; P0 eval 20/20 passing | `[x]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS updated through Task 28 | `[x]` Done for scoped baseline |
| P4 | Realistic Scenario Dataset | `[x]` realistic scenario tables, deterministic anomaly profiles, business rules, table docs, metrics, and seed integration complete | `[x]` `tests/test_realistic_seed_data.py` passing; P0 eval preserved | `[x]` realistic scenario docs added to data docs and planning notes | `[x]` Done |
| P5 | Lightweight Semantic Layer | `[x]` `semantic_layer/` metrics, dimensions, entities, join paths, loader, retriever, metric tool compatibility, and context semantic attachment complete | `[x]` semantic layer tests 6/6 passing; related regression 23/23 passing; full suite 203 passed / 9 skipped; P0 eval 20/20 passing | `[x]` DEVELOPMENT_PLAN and DEVELOPMENT_STATUS now expose phase status at the top | `[x]` Done |
| P6 | Scenario Analysis Planner | `[x]` deterministic planner, provider-backed planner validation, runtime provider switch, workflow state, and trace metadata complete | `[x]` planner tests 9/9 passing; related regression 22/22 passing; full suite 212 passed / 9 skipped; P0 eval 20/20 passing | `[x]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS updated | `[x]` Done |
| P7 | Visualization Intelligence | `[x]` `visualization/` registry/spec/validator/renderer and workflow trace metadata complete; P8.1 later replaced the old planner/agent product path | `[x]` visualization tests preserved | `[x]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS updated | `[x]` Done |
| P8.1 | Visualization Agent Dedupe & External Tool Calling | `[x]` `agents/visualization_agent.py`, `visualization_delivery/`, and `tools/external_visualization_tool.py` complete; old `agents/chart_agent.py`, `agents/visualization_planner.py`, and `tools/chart_tool.py` deleted; MCP chart generation now delegates to the external visualization tool with `local_renderer` | `[x]` P8.1 tests 14/14 passing; focused visualization tests 17/17 passing; related regression 36/36 passing; full suite 223 passed / 9 skipped; eval 20/20 passing | `[x]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS updated | `[x]` Done |
| P8.2 | Intent & SQL Planning Agent Cleanup | `[x]` provider-backed question understanding and SQL planning are the configured product paths; safety guard rejects unsafe/sensitive questions before provider calls; provider failures return `provider_unavailable`; provider `llm_candidate` paths skip `sql_generator.py`; provider template paths render by matched template id | `[x]` P8.2 focused tests 5/5 passing; related intent/SQL planning regression 47/47 passing; full suite 228 passed / 9 skipped; eval 20/20 passing | `[x]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS updated | `[x]` Done |
| P8.3 | Report & Insight Agent Cleanup | `[x]` provider-backed report planning no longer falls back to fixed section selection; Report Supervisor stops on `provider_unavailable` unless sections are explicitly supplied; `insight_drafter` prompt/schema/runtime wiring drafts candidate claims before claim typing/Evidence Validator | `[x]` P8.3 focused tests 6/6 passing; related report/insight/runtime regression 71/71 passing; full suite 234 passed / 9 skipped; eval 20/20 passing | `[x]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS updated | `[x]` Done |
| P8.4 | Action Agent & Tool Adapter Cleanup | `[x]` fixed action templates removed from the product path; provider-backed action planning returns contextual action payloads plus delivery-tool ids; missing providers return structured `provider_unavailable`; `agents/action_executor.py` owns approved execution through `action_delivery/` adapters | `[x]` P8.4 focused tests 5/5 passing; action/provider regression 30/30 passing; related regression 40/40 passing; full suite 239 passed / 9 skipped; eval 20/20 passing | `[x]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS updated | `[x]` Done |
| P8.5 | Agent Pipeline UX | `[x]` Streamlit run summaries now expose agent pipeline, tool-call cards, validator gates, artifact panel, source metadata, provider prompt ids, fallback flags, policy status, and mock external artifact URLs from existing state/trace data | `[x]` P8.5 focused test red/green verified; Streamlit tests 19/19 passing; related regression 42/42 passing; full suite 240 passed / 9 skipped; eval 20/20 passing | `[x]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS updated | `[x]` Done |
| P9 | Realistic Eval And Demo Polish | `[x]` 32-case realistic eval, P9 metrics, no-key mock provider/action coverage, unsafe rejection, and demo questions complete | `[x]` focused P9 eval and Streamlit tests passing; full verification recorded below | `[x]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS updated | `[x]` Done |
| P10 | Lightweight Engineering Hardening | `[x]` external-safe MCP contract metadata, internal-tool exposure checks, eval artifact hygiene note, and generated-artifact ignore coverage complete | `[x]` focused tests, related regressions, full suite, eval, and legacy audit passing | `[x]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS updated | `[x]` Done |
| P11 | General Data Analysis Product | `[~]` workspace store/import/profile/semantic draft, synthetic workspace data, workspace-aware analysis, FastAPI workspace APIs, H1 source upload/import APIs, H2 Next.js API-backed product flow, H3 old UI/API cleanup, natural live DeepSeek acceptance, and old demo/mock cleanup are present; H5 hardening remains | `[x]` audit verification: backend suite 208 passed / 9 skipped; frontend H2 tests and production build passing; opt-in live DeepSeek workspace acceptance passing with a natural business question; H1 focused API/importer tests passing | `[~]` docs now track P11 hardening plan | `[~]` In progress |

## P11 Product Hardening

Audit date: 2026-06-23

The P11 implementation is functional but not product-complete. The audit found five required hardening tasks before P12 can begin.

### Audit Findings

- `[x]` FastAPI now exposes CSV/Excel upload, SQLite source import, and source listing endpoints backed by workspace importers.
- `[x]` Next.js workspace pages now drive the API-backed product flow for workspace create/list, data sources, profile, semantic draft, analysis submission, and run-result rendering.
- `[x]` `app.py`, old Streamlit tests, tracked `ui/` modules, and old ecommerce-style `/api/runs` product routes/defaults are gone.
- `[x]` P11 live DeepSeek acceptance now passes with a natural business question, real workspace profile/semantic context, guarded SQL candidate validation, workspace `analysis.db` execution, and workspace-rooted visualization artifacts.
- `[!]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS still contain many historical Streamlit/ecommerce/eval references; current-product sections must be cleaned so future agents do not revert to the old demo path.

### Hardening Task Checklist

| Task | Scope | Status | Required verification |
|---|---|---|---|
| H1 | Add `POST /api/workspaces/{workspace_id}/sources/upload`, `POST /sources/sqlite`, and `GET /sources`; wire to `import_csv`, `import_excel`, and `import_sqlite` | `[x]` Complete; `requirements.txt` includes `python-multipart` for file upload support | `python3 -m pytest tests/test_workspace_api.py tests/test_workspace_importers.py -q` |
| H2 | Replace Next.js placeholder pages with real API-backed workspace list, create, data source, profile, semantic-layer, analysis, and run-result flows | `[x]` Complete; API client, interactive components, route pages, and frontend tests now cover the product flow | `cd frontend && npm test && npm run build` |
| H3 | Delete tracked `ui/`; remove old `/api/runs` ecommerce product entry; update cleanup/project-initialization tests | `[x]` Complete | `python3 -m pytest tests/test_p11_cleanup_boundaries.py tests/test_project_initialization.py tests/test_workspace_api.py tests/test_workspace_analysis_runner.py -q` |
| H4 | Strengthen P11 live DeepSeek test with a natural business question and workspace-rooted artifact assertions | `[x]` Complete | `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1 python3 -m pytest tests/test_p11_live_deepseek_workspace_analysis.py -q` |
| H5 | Clean current docs so Streamlit/ecommerce/eval/mock references are historical only, not current product guidance | `[~]` Started | `rg -n "streamlit run app.py|eval/run_eval.py|data/ecommerce.db|mock jira|powerbi_publisher_mock|fixed template|deterministic action template|keyword inference" README.md DEVELOPMENT_PLAN.md DEVELOPMENT_STATUS.md` |

### Hardening Final Acceptance

P11 can be marked complete only after:

- `[ ]` H1-H5 are complete.
- `[ ]` `python3 -m pytest` passes.
- `[ ]` `cd frontend && npm test && npm run build` passes.
- `[x]` P11 opt-in live DeepSeek acceptance passes with a natural business question.
- `[ ]` `git ls-files` shows no tracked Streamlit app, `ui/`, old eval runner/questions, mock-action acceptance tests, generated DB/report/trace/chart artifacts, `frontend/node_modules`, or `frontend/.next`.
- `[ ]` Docs make P11 workspace + FastAPI + Next.js the current product path and clearly mark historical P0-P10 references as superseded.

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
| Task 13 - Chart Agent | `[x]` Historical P1 chart path was implemented, then superseded and deleted by P8.1; retained rendering now lives under `visualization/` plus `tools/external_visualization_tool.py` | `[x]` chart file generation and trace behavior covered by current visualization/MCP tests | `[x]` README visualization output and interface docs | `[x]` Superseded |
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
- `[x]` Historical Chart Tool generated real PNG files before P8.1 superseded and deleted that product path.
- `[x]` Historical Chart Agent bar/line decision behavior is superseded by the current `VisualizationAgent`.
- `[x]` Current visualization output writes `chart_path` and `chart_paths` through `tools/external_visualization_tool.py` and `visualization_delivery/`.
- `[x]` Current visualization delivery emits trace-ready events and appends them to trace.
- `[x]` Historical Task 13 tests were replaced by current visualization/MCP tests after P8.1 cleanup.
- `[x]` Existing P0 tests and eval remained passing after Task 13.
- `[x]` README and DEVELOPMENT_STATUS were updated for Task 13 and later superseded by P8.1/P9 docs.
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

Final LLM participation map added to the tracked [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md):

| Area | Intended LLM role | Boundary |
|---|---|---|
| Provider / PromptOps | DeepSeek adapter, prompt registry, prompt versions, structured output validation, usage/cost/latency trace metadata | Preserve deterministic safety boundaries and structured provider-unavailable handling |
| Question understanding and clarification | Extract intent slots and ask missing-context questions | No SQL generation or execution |
| SQL planning and guarded SQL candidates | Route to deterministic templates or propose validated candidates for clear non-template questions | `validate_sql()` remains mandatory before `run_sql()` |
| Report planning and business review decomposition | Select allowlisted report sections and organize subtasks | No provider-supplied SQL or final factual claims |
| Insight/report polishing | Suggest or polish claims from execution results and context | Evidence Validator decides what can be used |
| Action drafting | Draft task, alert, and email wording from evidence-backed findings | Approval Gate, Action Executor, and Audit Logger remain mandatory |
| Template mining and LLM eval | Summarize repeated candidate patterns and validate provider/prompt health | No automatic production template changes; live tests remain opt-in |

Non-negotiable deterministic ownership remains with `validate_sql()`, `run_sql()`, `Evidence Validator`, `Approval Gate`, `Audit Logger`, `Trace Logger`, MCP safety wrappers, and the P0 eval baseline.

### LLM Enhancement Task Backlog

These completed tasks are historical LLM enhancement records. Future P8.1-P8.5 cleanup follows the newer rule in `DEVELOPMENT_PLAN.md`: conflicting legacy product paths may be deleted, obsolete tests may be removed or rewritten, focused tests are enough during a migration slice, and full pytest/P0 eval run at phase completion or before commit/push.

| Task | Development | Tests | Docs | Status |
|---|---|---|---|---|
| Task 21 - Provider-backed Question Understanding | `[x]` Added optional DeepSeek-compatible intent extraction behind the existing deterministic `question_understanding` router; normalized output into the existing intent schema; kept deterministic fallback on provider/schema failure | `[x]` mocked provider success, malformed output fallback, schema mismatch fallback, no-key baseline, risk flag preservation, Agent trace, and no-SQL/no-execution boundary tests | `[x]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS usage and boundary docs | `[x]` Done |
| Task 21A - Runtime Provider-backed Question Understanding Wiring | `[x]` Wired question understanding into `graph.workflow.run_workflow()` before schema retrieval; added runtime DeepSeek provider factory behind `INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING`; Streamlit and FastAPI inherit the core workflow path | `[x]` mock-provider workflow tests, runtime provider factory tests, no-key env fallback, provider alias normalization, full suite, P0 eval, and real DeepSeek-backed workflow smoke | `[x]` Runtime switch and live workflow smoke command documented | `[x]` Done |
| Task 22 - Provider-backed Clarification Router | `[x]` Added structured clarification prompt/schema for missing metric, dimension, time range, filters, operation, or limit; wired clarification output into workflow state before SQL generation | `[x]` focused-question generation, ambiguous-question fallback, unsafe-request rejection preservation, malformed output fallback, runtime workflow trace, no-key baseline, and live DeepSeek clarification smoke tests | `[x]` Clarification examples, runtime switch behavior, and safety boundaries documented | `[x]` Done |
| Task 23 - Provider-assisted SQL Planning and Guarded Candidate Integration | `[x]` Added optional provider-assisted SQL planning, structured `sql_planning_router` validation, runtime provider factories, workflow SQL planning node, and guarded SQL candidate workflow integration | `[x]` provider routing success, malformed/schema mismatch fallback, no-key baseline, candidate validation, rejected unsafe SQL, no direct provider SQL execution, runtime workflow trace, and live DeepSeek SQL planning smoke tests | `[x]` SQL planning/candidate flow, runtime switches, live smoke command, and validation policy documented | `[x]` Done |
| Task 24 - LLM Business Review Decomposition | `[x]` Expanded controlled report planner with PromptOps provider support, weekly/monthly allowlisted section selection, provider SQL/claim rejection, and report supervisor runtime wiring | `[x]` provider section selection, SQL leak rejection, schema mismatch fallback, no-key baseline, monthly review runtime, trace metadata, full suite, P0 eval, and live DeepSeek review-planning smoke tests | `[x]` Review planning runtime switch, live smoke command, monthly report support, and allowlist rules documented | `[x]` Done |
| Task 25 - Evidence-backed Report Writing and Polishing | `[x]` Added provider-backed `report_writer` prompt/schema, report writer agent, env-gated runtime provider factory, and report-agent/report-supervisor wiring after Evidence Validator | `[x]` supported-claim inclusion, unsupported-claim rejection, Evidence Validator gate, no-key fallback, report save integration, full suite, P0 eval, and live DeepSeek report-writing smoke tests | `[x]` Report polishing contract, runtime switches, live smoke command, and evidence boundaries documented | `[x]` Done |
| Task 26 - Guarded Insight Claim Typing | `[x]` Added provider-backed `insight_claim_typer` prompt/schema, claim typing agent, env-gated runtime provider factory, and core workflow/report supervisor wiring before Evidence Validator filtering | `[x]` claim-type normalization, Evidence Validator final classification, unsupported blocking, fallback, runtime trace metadata, full suite, P0 eval, and live DeepSeek claim-typing smoke tests | `[x]` Claim type schema, runtime integration, live smoke command, and Evidence Validator interaction documented | `[x]` Done |
| Task 27 - LLM Action and Email Drafting | `[x]` Added optional provider-backed task/alert/email draft wording from evidence-backed findings after Action Planner and before Risk Assessor, Approval Gate, Action Executor, and Audit Logger | `[x]` draft schema validation, approval gate preservation, no direct action creation, audit requirement, malformed output fallback/retry, runtime action workflow trace, full suite, P0 eval, and live DeepSeek drafting smoke tests | `[x]` Action drafting flow, runtime integration, approval boundary, and email draft rules documented | `[x]` Done |
| Task 28 - LLM Template Mining and Eval Suite | `[x]` Expanded template-mining feedback to read safe metadata from saved workflow traces and expanded LLM eval smoke cases for provider output shape, malformed JSON, schema mismatch, and expected failures | `[x]` trace-mining recommendation tests, no auto-template-write checks, schema-aware eval tests, no-key baseline, full suite, P0 eval, and live DeepSeek eval suite tests | `[x]` LLM eval command, runtime trace-mining policy, and opt-in live test docs | `[x]` Done |

### LLM Enhancement Backlog Acceptance Rules

- `[ ]` Each task must have dedicated tests before implementation.
- `[ ]` Each LLM task must wire the feature into at least one real project runtime path: `graph.workflow`, FastAPI run API, Streamlit helper/demo, report supervisor, or action workflow.
- `[ ]` Each LLM task must expose trace/state evidence showing whether the provider was called and how provider-unavailable or validation failures were handled.
- `[ ]` Live DeepSeek smoke tests are required for major provider-backed phase completion, not every small cleanup edit.
- `[ ]` Each task must return structured dict / JSON-compatible outputs.
- `[ ]` Provider failures must return `success: false` or explicit provider-unavailable states instead of crashing workflows.
- `[ ]` No task may bypass `validate_sql()`, `run_sql()`, Evidence Validator, Approval Gate, Audit Logger, Trace Logger, or MCP safety wrappers.
- `[ ]` Missing-provider behavior must be structured and must not revive removed rule trees.
- `[ ]` Focused tests should pass during each migration slice.
- `[ ]` Full pytest and `python3 eval/run_eval.py` must pass at phase completion or before commit/push.
- `[ ]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS must be updated after every task.

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
| Streamlit Command Center UI hardening | `[x]` Command Center navigation, Ask & Analyze run summary, source/safety cards, run detail timeline, LLM Ops, Observability/Audit, Integrations, and Capability Catalog | `[x]` Streamlit view-model/helper tests for capability coverage, provider metadata, no-key baseline, trace timeline, workflow helper reuse, approval gate semantics, and secret redaction | `[x]` README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS command-center notes | `[x]` Done |
| Task 20 - LLM Provider and PromptOps Core | `[x]` `llm_ops/` provider abstraction, prompt registry, prompt/version metadata, model cost/latency tracking, trace-ready provider metadata, and LLM eval harness | `[x]` `tests/test_llm_provider_promptops.py`; full suite and P0 eval passing | `[x]` provider setup, prompt governance, safety boundaries, and eval docs | `[x]` Done |
| Task 20C - Production DeepSeek Provider & Structured Output Validation | `[x]` `DeepSeekProvider`, `.env`-driven model/base URL config, strict JSON schema/structure validation, provider response normalization, and production smoke-test controls | `[x]` provider adapter contract tests, schema validation failure tests, malformed JSON fallback tests, optional live DeepSeek smoke test, and no-key baseline tests | `[x]` DeepSeek setup, structured output rules, live-test opt-in, and safety boundary docs | `[x]` Done |
| Task 20A - Question Understanding & Clarification Router | `[x]` deterministic intent slot extraction, completeness checks, clarification-question generation, and risk/sensitive-request routing | `[x]` intent-slot tests, ambiguous-question tests, missing-slot tests, rejection-routing tests, and no-SQL/no-20B-boundary tests | `[x]` intent contract, clarification policy, and routing examples | `[x]` Done |
| Task 20B - SQL Planning Router | `[x]` template-vs-LLM-candidate strategy router, confidence/reason payload, fallback policy, and template-mining feedback loop | `[x]` template routing tests, `llm_candidate` routing tests, clarify/reject routing tests, no-provider/no-SQL boundary tests, and P0 eval preservation tests | `[x]` router contract, strategy matrix, and eval plan | `[x]` Done |
| Task 21 - Provider-backed Question Understanding | `[x]` optional provider-backed intent extraction, `question_understanding` prompt, structured-output validation, deterministic fallback, provider/fallback trace metadata | `[x]` `tests/test_provider_backed_question_understanding.py`; full suite and P0 eval passing | `[x]` provider-backed contract and safety boundaries documented | `[x]` Done |
| Task 21A - Runtime Provider-backed Question Understanding Wiring | `[x]` `run_workflow()` question-understanding node, env-gated DeepSeek provider factory, state schema fields, provider alias normalization, live workflow smoke test | `[x]` focused runtime tests, runtime provider factory tests, full suite, P0 eval, and live DeepSeek-backed workflow smoke pass | `[x]` runtime wiring and env switch documented | `[x]` Done |
| Task 22 - Provider-backed Clarification Router | `[x]` `clarification_router` prompt, structured-output validation, optional provider-backed clarification helper, agent wrapper, workflow node, env-gated runtime provider factory | `[x]` provider success/fallback tests, malformed/schema-mismatch tests, no-key baseline tests, workflow trace/no-SQL tests, full suite, P0 eval, and live DeepSeek-backed clarification workflow smoke pass | `[x]` runtime switch, clarification contract, live smoke command, and safety boundaries documented | `[x]` Done |
| Task 23 - Provider-assisted SQL Planning and Guarded Candidate Integration | `[x]` `sql_planning_router` prompt/schema, provider-backed planning helper, provider-aware planning agent, runtime provider factories, workflow planning node, guarded candidate node before SQL Reviewer | `[x]` provider/fallback tests, SQL leak validation test, no-key baseline test, candidate accepted/rejected workflow tests, full suite, P0 eval, and live DeepSeek-backed SQL planning workflow smoke pass | `[x]` runtime switches, guarded candidate flow, live smoke command, and SQL validation boundary documented | `[x]` Done |
| Task 24 - LLM Business Review Decomposition | `[x]` PromptOps-backed `report_planner` path, weekly/monthly report section templates, env-gated DeepSeek provider factory, and report supervisor runtime integration | `[x]` provider success/fallback tests, provider SQL/claim rejection tests, no-key baseline tests, monthly supervisor tests, full suite, P0 eval, and live DeepSeek-backed business review workflow smoke pass | `[x]` runtime switch, monthly review behavior, live smoke command, and allowlist/SQL boundaries documented | `[x]` Done |
| Task 25 - Evidence-backed Report Writing and Polishing | `[x]` PromptOps-backed `report_writer` path, structured evidence-bound prose schema, env-gated DeepSeek provider factory, and report agent/supervisor runtime integration | `[x]` provider success/fallback tests, blocked unsupported-claim rejection tests, no-key baseline tests, report save integration tests, full suite, P0 eval, and live DeepSeek-backed report writer workflow smoke pass | `[x]` runtime switch, report writer contract, live smoke command, and Evidence Validator boundary documented | `[x]` Done |
| Task 26 - Guarded Insight Claim Typing | `[x]` PromptOps-backed `insight_claim_typer` path, structured claim type schema, env-gated DeepSeek provider factory, core workflow claim typing node, and report supervisor section integration | `[x]` provider success/fallback tests, schema mismatch fallback, Evidence Validator final-decision tests, report supervisor tests, full suite, P0 eval, and live DeepSeek-backed claim typing workflow smoke pass | `[x]` runtime switch, claim typing contract, live smoke command, and Evidence Validator ownership documented | `[x]` Done |
| Task 27 - LLM Action and Email Drafting | `[x]` PromptOps-backed `action_drafter` path, structured action/email draft schema, env-gated DeepSeek provider factory, action planner runtime integration, and provider retry/fallback metadata | `[x]` provider success/fallback tests, approval bypass rejection, unsupported claim blocking, no-key baseline, runtime action workflow tests, full suite, P0 eval, and live DeepSeek-backed action drafting workflow smoke pass | `[x]` runtime switch, action drafter contract, live smoke command, and approval/audit boundaries documented | `[x]` Done |
| Task 28 - LLM Template Mining and Eval Suite | `[x]` Workflow trace mining for accepted guarded SQL candidates, safe template-mining trace metadata, schema-aware LLM smoke eval, expected failure cases, and package exports | `[x]` trace-file mining tests, schema validation eval tests, malformed/schema mismatch expected-failure tests, related SQL planning/PromptOps regressions, full suite, P0 eval, and live DeepSeek eval suite pass | `[x]` trace mining usage, no-auto-template-write policy, schema-aware eval usage, and live DeepSeek eval command documented | `[x]` Done |
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

### P3 Streamlit Command Center UI Hardening Acceptance Tracker

- `[x]` Main Streamlit entry uses Command Center navigation instead of the original horizontal tab demo as the first-level structure.
- `[x]` Ask & Analyze shows question, status, answer, SQL/review/execution, evidence, report/action artifacts, source/safety cards, and trace timeline for one run.
- `[x]` Source cards expose `provider_called`, `fallback_used`, `prompt_id`, `validation_error`, and `provider_error` from existing workflow state.
- `[x]` LLM Ops shows provider configured/not configured status, runtime switches, prompt registry, and deterministic baseline without exposing API keys.
- `[x]` Observability/Audit shows trace count, event count, SQL fix count, eval pass rate, approval records, audit logs, latency, tool counts, failures, and raw details.
- `[x]` Capability Catalog covers P0/P1/P2/P3 including LLM Provider & PromptOps and Template Mining & Eval.
- `[x]` Integrations keep MCP Tool Layer and FastAPI Async Run API visible.
- `[x]` UI helper tests prove Command Center analysis still calls the existing workflow helper and does not bypass `run_workflow()`.
- `[x]` Action workflow approval gate semantics remain covered by Streamlit tests.
- `[x]` `python3 -m pytest` reports 190 passed and 9 opt-in live DeepSeek tests skipped by default.
- `[x]` `python3 eval/run_eval.py` reports 20/20 passed.
- `[x]` This hardening does not implement React, Docker/CI, RBAC, full ActionOps, or new backend LLM behavior.

### P3 Task 20 Acceptance Tracker

- `[x]` `llm_ops.provider.LLMRequest` defines a clear provider request contract with prompt id, prompt version, model, and metadata.
- `[x]` `run_llm_request()` returns JSON-compatible structured output with `success`, `content`, `usage`, `latency_ms`, `error`, and `trace_event`.
- `[x]` Provider failures return `success: false` and structured `llm_provider_error` trace metadata instead of raising workflow-breaking exceptions.
- `[x]` `llm_ops.prompt_registry.DEFAULT_PROMPT_REGISTRY` stores versioned prompts for report planning, guarded SQL candidates, insight drafting, and guarded insight claims.
- `[x]` Prompt rendering reports missing variables as structured errors.
- `[x]` Guarded SQL candidate prompt metadata includes no-execution and no-`validate_sql()`-bypass safety contracts.
- `[x]` Guarded insight prompt metadata requires Evidence Validator verification before claims can be used.
- `[x]` Provider trace events include model, prompt id, prompt version, token usage, estimated cost, and latency metadata.
- `[x]` `llm_ops.eval_smoke.run_llm_smoke_eval()` runs deterministic mock-provider smoke cases without requiring an API key.
- `[x]` Task 20 does not implement Task 20A Question Understanding, Task 20B SQL Planning Router, real provider integration, React, RBAC, Docker/CI, or full ActionOps.
- `[x]` Existing P0/P1/P2/P3 tests and P0 eval remain passing after Task 20.

### P3 Task 20C Acceptance Tracker

- `[x]` Add a production `DeepSeekProvider` adapter that implements the existing `llm_ops` provider contract.
- `[x]` Read `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL` from environment or `.env` without logging secrets.
- `[x]` Keep live API tests opt-in so the deterministic no-key baseline remains the default.
- `[x]` Validate model output against strict per-prompt schemas before returning accepted content to agents.
- `[x]` Normalize allowed structures, such as converting planner section objects only when they match the schema, and reject loose string-list responses.
- `[x]` Return `success: false` with structured errors for malformed JSON, schema mismatch, provider timeout, auth failure, or rate-limit failure.
- `[x]` Record provider, model, prompt id, prompt version, latency, token usage, and cost metadata in trace-ready events.
- `[x]` Ensure real provider output cannot bypass `validate_sql()`, Evidence Validator, approval gate, or deterministic fallback behavior.
- `[x]` Document DeepSeek setup, live smoke test usage, and structured output governance.

### P3 Task 20A Acceptance Tracker

- `[x]` `question_understanding.router.understand_question()` returns JSON-compatible intent and routing output.
- `[x]` Intent slots include `metric`, `dimension`, `time_range`, `filters`, `operation`, `limit`, and `risk_flags`.
- `[x]` Clear stable BI questions return complete slots and `strategy: template` without generating SQL.
- `[x]` Complete but non-template questions return `strategy: llm_candidate` for later planning.
- `[x]` Ambiguous or incomplete questions return `strategy: clarify`, `missing_slots`, and focused clarification questions.
- `[x]` Sensitive-field and unsafe-write requests return `strategy: reject` before SQL planning.
- `[x]` `agents.question_understanding.run_question_understanding_agent()` writes `question_understanding`, `intent_slots`, and `routing_strategy` into state and appends trace.
- `[x]` Task 20A does not emit SQL, execute SQL, choose a concrete `matched_template`, or add Task 20B confidence fields.
- `[x]` Existing P0/P1/P2/P3 tests and P0 eval remain passing after Task 20A.

### P3 Task 20B Acceptance Tracker

- `[x]` `sql_planning.router.plan_sql_strategy()` chooses one of `template`, `llm_candidate`, `clarify`, or `reject`.
- `[x]` Stable Top product/category/city BI intents route to deterministic template IDs with confidence and template variables.
- `[x]` Clarify and reject routes preserve missing slots, clarification questions, risk flags, and rejection reasons from Task 20A.
- `[x]` Complete non-template intents route to `llm_candidate` with a guarded candidate policy.
- `[x]` `llm_candidate` routing does not call a provider and does not return SQL.
- `[x]` All planned SQL paths carry `must_validate_sql_before_execution`.
- `[x]` `sql_planning.feedback.summarize_template_mining_feedback()` flags repeated successful `llm_candidate` intent patterns for future deterministic template mining.
- `[x]` `agents.sql_planning_router.run_sql_planning_router_agent()` writes planning state and appends trace without generating SQL.
- `[x]` Existing P0/P1/P2/P3 tests and P0 eval remain passing after Task 20B.

### P3 Task 21 Acceptance Tracker

- `[x]` `question_understanding.provider_backed.understand_question_with_provider()` adds an optional provider-backed path behind deterministic question understanding.
- `[x]` Provider output is rendered through prompt id `question_understanding`.
- `[x]` Provider output must pass prompt-specific structured validation before use.
- `[x]` Accepted provider output is normalized into existing intent slots: `metric`, `dimension`, `time_range`, `filters`, `operation`, `limit`, and `risk_flags`.
- `[x]` `provider=None` preserves the no-key deterministic baseline.
- `[x]` Provider errors, malformed JSON, and schema mismatch fall back to deterministic `understand_question()`.
- `[x]` Fallback results record `provider_called`, `fallback_used`, and `provider_error` or `validation_error`.
- `[x]` Sensitive or unsafe provider risk flags are preserved and force `strategy: reject`.
- `[x]` Task 21 does not generate SQL, execute SQL, emit `matched_template`, or perform SQL planning.
- `[x]` `agents.question_understanding.run_question_understanding_agent()` accepts an optional provider, writes state, and appends trace with `provider_called` and `fallback_used`.
- `[x]` Existing P0/P1/P2/P3 tests and P0 eval remain passing after Task 21.

### P3 Task 21A Acceptance Tracker

- `[x]` `graph.workflow.run_workflow()` runs Question Understanding Agent before schema retrieval.
- `[x]` Workflow state includes `question_understanding`, `intent_slots`, and `routing_strategy`.
- `[x]` `run_workflow(..., question_understanding_provider=provider)` uses provider-backed question understanding in the real core workflow.
- `[x]` `INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1` enables runtime provider creation.
- `[x]` Missing API key keeps deterministic baseline instead of crashing workflow.
- `[x]` Streamlit demo helpers and FastAPI async runs inherit provider-backed behavior through the core workflow.
- `[x]` Provider slot aliases such as `销售额`, `商品`, and `最高` normalize to `gmv`, `product`, and `top_n`.
- `[x]` Task 21A still does not generate SQL, execute SQL, emit `matched_template`, or bypass SQL validation.
- `[x]` Live DeepSeek workflow smoke test passes with `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1` and `INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1`.

### P3 Task 22 Acceptance Tracker

- `[x]` `question_understanding.clarification.clarify_with_provider()` adds an optional provider-backed clarification path behind deterministic question understanding.
- `[x]` Provider clarification output is rendered through prompt id `clarification_router`.
- `[x]` Provider clarification output must pass prompt-specific structured validation before use.
- `[x]` Provider success returns focused clarification questions with `provider_called: true`, `fallback_used: false`, and `source: provider`.
- `[x]` `provider=None`, provider errors, malformed JSON, and schema mismatch fall back to deterministic clarification questions.
- `[x]` Fallback results record `provider_called`, `fallback_used`, and `provider_error` or `validation_error`.
- `[x]` Unsafe or sensitive question-understanding rejection is preserved before SQL generation.
- `[x]` `agents.clarification_router.run_clarification_router_agent()` writes state and appends trace with `provider_called` and `fallback_used`.
- `[x]` `graph.workflow.run_workflow()` runs clarification after question understanding and before schema retrieval.
- `[x]` Provider-backed clarification stops ambiguous requests before schema retrieval, SQL generation, SQL execution, and SQL planning.
- `[x]` The no-key deterministic baseline continues through the existing P0 SQL workflow.
- `[x]` Live DeepSeek clarification workflow smoke test passes with `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1` and `INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER=1`.

### P3 Task 23 Acceptance Tracker

- `[x]` `sql_planning.provider_backed.plan_sql_strategy_with_provider()` adds an optional provider-assisted planning path behind deterministic SQL planning.
- `[x]` Provider planning output is rendered through prompt id `sql_planning_router`.
- `[x]` Provider planning output must pass prompt-specific structured validation before use.
- `[x]` Provider planning output cannot include SQL, generated SQL, SQL candidates, or selected table fields.
- `[x]` Provider success records `provider_called: true`, `fallback_used: false`, and `source: provider`.
- `[x]` `provider=None`, provider errors, malformed JSON, schema mismatch, and SQL leakage fall back to deterministic `plan_sql_strategy()`.
- `[x]` `graph.workflow.run_workflow()` runs SQL planning after clarification and before schema retrieval.
- `[x]` `llm_candidate` workflow routes can call `guarded_sql_candidate` after deterministic SQL generation.
- `[x]` Candidate SQL is validated by `validate_sql()` inside the guarded candidate agent before it can replace deterministic SQL.
- `[x]` Accepted candidate SQL still passes through the existing SQL Reviewer before `run_sql()`.
- `[x]` Rejected unsafe provider SQL candidates fall back to deterministic SQL without crashing workflow.
- `[x]` The no-key deterministic baseline continues through the existing SQL workflow.
- `[x]` Live DeepSeek SQL planning workflow smoke test passes with `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1`, `INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1`, and `INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1`.

### P3 Task 24 Acceptance Tracker

- `[x]` Report planning output is rendered through prompt id `report_planner` for PromptOps-compatible providers.
- `[x]` Provider report plans must pass prompt-specific structured validation before use.
- `[x]` Provider success records `provider_called: true`, `fallback_used: false`, `source: provider`, prompt id/version, model, usage, and latency metadata.
- `[x]` Provider output can select only allowlisted weekly/monthly report section IDs.
- `[x]` Provider-supplied SQL, generated SQL, SQL candidates, factual claims, or final claims trigger deterministic fallback.
- `[x]` `provider=None`, missing API key, provider errors, malformed JSON, schema mismatch, and SQL/claim leakage fall back to deterministic report planning.
- `[x]` `run_report_supervisor_agent()` can call the runtime DeepSeek provider factory when `INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER=1`.
- `[x]` The no-key deterministic baseline continues through the report supervisor without requiring a provider.
- `[x]` Monthly review questions produce `monthly_business_report` sections and save monthly report artifacts while preserving existing SQL review/execution/evidence/chart/report boundaries.
- `[x]` Provider-backed business review decomposition does not generate SQL, execute SQL, bypass `validate_sql()`, bypass Evidence Validator, or create final unsupported claims.
- `[x]` Live DeepSeek business review decomposition smoke test passes with `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1` and `INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER=1`.

### P3 Task 25 Acceptance Tracker

- `[x]` Report writing output is rendered through prompt id `report_writer` for PromptOps-compatible providers.
- `[x]` Provider report prose must pass prompt-specific structured validation before use.
- `[x]` Provider success records `provider_called: true`, `fallback_used: false`, `source: provider`, prompt id/version, model, usage, and latency metadata.
- `[x]` Provider input includes only user question, verified findings, verified hypotheses, blocked unsupported claims, SQL records, chart paths, and trace path.
- `[x]` Provider output can include executive summary, business narrative, next steps, and references to verified findings/hypotheses.
- `[x]` Provider output is rejected if it returns SQL fields, unverified claim references, non-empty `unsupported_claims`, or text containing a blocked unsupported claim.
- `[x]` `provider=None`, missing API key, provider errors, malformed JSON, schema mismatch, and unsupported-claim leakage fall back to deterministic report wording.
- `[x]` `run_report_agent()` can write provider-polished prose after Evidence Validator without changing SQL execution or evidence validation.
- `[x]` `run_report_supervisor_agent()` can write provider-polished prose after report subtasks finish Evidence Validator checks.
- `[x]` The no-key deterministic baseline continues through report generation without requiring a provider.
- `[x]` Provider-backed report writing does not generate SQL, execute SQL, bypass `validate_sql()`, bypass Evidence Validator, or create approval-gated actions.
- `[x]` Live DeepSeek report writer workflow smoke test passes with `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1` and `INSIGHTFLOW_USE_PROVIDER_REPORT_WRITER=1`.

### P3 Task 26 Acceptance Tracker

- `[x]` Claim typing output is rendered through prompt id `insight_claim_typer` for PromptOps-compatible providers.
- `[x]` Provider claim typing output must pass prompt-specific structured validation before use.
- `[x]` Provider success records `provider_called: true`, `fallback_used: false`, `source: provider`, prompt id/version, model, usage, and latency metadata.
- `[x]` Provider output can classify candidate claims as `data_supported_finding`, `hypothesis`, or `unsupported`.
- `[x]` Provider classification is advisory; Evidence Validator still produces the final supported/hypothesis/blocked split.
- `[x]` Provider output is rejected if it returns SQL fields, malformed `typed_claims`, unknown claim types, or invalid risk flags.
- `[x]` `provider=None`, missing API key, provider errors, malformed JSON, and schema mismatch fall back to deterministic claim validation.
- `[x]` `run_workflow()` runs claim typing after deterministic Insight Agent output and before trace save.
- `[x]` `run_report_supervisor_agent()` can run claim typing on report-section claims before Evidence Validator filtering.
- `[x]` The no-key deterministic baseline continues through insight and report workflows without requiring a provider.
- `[x]` Provider-backed claim typing does not generate SQL, execute SQL, bypass `validate_sql()`, bypass Evidence Validator, or create approval-gated actions.
- `[x]` Live DeepSeek claim typing workflow smoke test passes with `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1` and `INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING=1`.

### P3 Task 27 Acceptance Tracker

- `[x]` Action drafting output is rendered through prompt id `action_drafter` for PromptOps-compatible providers.
- `[x]` Provider action drafting output must pass prompt-specific structured validation before use.
- `[x]` Provider success records `provider_called: true`, `fallback_used: false`, `source: provider`, prompt id/version, model, usage, and latency metadata.
- `[x]` Provider output can draft only `create_task`, `create_metric_alert`, and `create_email_draft` pending action payloads.
- `[x]` Provider input is limited to user question, existing deterministic actions, verified findings, verified hypotheses, and blocked unsupported claims.
- `[x]` Provider output is rejected if it returns approval-bypass fields, action record IDs, audit IDs, send-email flags, unsupported claim references, malformed action fields, or blocked unsupported claim text.
- `[x]` Top-level provider metadata such as `status` is ignored instead of being copied into action payloads.
- `[x]` Provider malformed JSON or transient validation/provider failures retry once, then fall back deterministically if the second attempt still fails.
- `[x]` `provider=None`, missing API key, provider errors, malformed JSON, and schema mismatch fall back to deterministic action plans.
- `[x]` `run_action_planner_agent()` calls the action drafter before Risk Assessor and Approval Gate when `INSIGHTFLOW_USE_PROVIDER_ACTION_DRAFTER=1` or an explicit provider is supplied.
- `[x]` The no-key deterministic baseline continues through action planning without requiring a provider.
- `[x]` Provider-backed action drafting does not generate SQL, execute SQL, bypass `validate_sql()`, bypass Evidence Validator, set approval status, create actions, send email, or bypass Risk Assessor, Approval Gate, Action Executor, or Audit Logger.
- `[x]` Live DeepSeek action drafting workflow smoke test passes with `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1` and `INSIGHTFLOW_USE_PROVIDER_ACTION_DRAFTER=1`.

### P3 Task 28 Acceptance Tracker

- `[x]` Accepted guarded SQL candidate trace events include safe `template_mining_event` metadata.
- `[x]` Template mining metadata records strategy, accepted status, provider flag, candidate count, user question, and structured intent.
- `[x]` Template mining metadata does not expose provider SQL as a production template.
- `[x]` `mine_template_candidates_from_trace_files()` reads saved workflow trace JSON files and extracts successful `llm_candidate` patterns.
- `[x]` Template mining recommendations include `intent_signature`, `success_count`, `recommended_template_id`, `sample_questions`, and `auto_apply: false`.
- `[x]` Template mining recommendations do not automatically modify deterministic template code or production SQL.
- `[x]` Trace load failures return structured `load_errors` instead of crashing.
- `[x]` `run_llm_smoke_eval()` supports `validate_output: true` and validates provider output through prompt-specific structured schemas.
- `[x]` LLM smoke eval supports `expected_success: false` and `expected_error_type` for malformed JSON and schema mismatch cases.
- `[x]` Default no-key pytest skips live DeepSeek eval by default.
- `[x]` Live DeepSeek eval suite passes with `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1`.
- `[x]` Task 28 does not bypass `validate_sql()`, `run_sql()`, Evidence Validator, Approval Gate, Audit Logger, Trace Logger, or MCP safety wrappers.

### P6 Scenario Analysis Planner Acceptance Tracker

- `[x]` `agents/analysis_planner.py` implements deterministic scenario-aware planning.
- `[x]` Planner supports `quick_metric_lookup`, `gmv_decline_diagnosis`, `marketing_roi_review`, `inventory_risk_analysis`, `refund_anomaly_analysis`, `promotion_review`, `customer_segment_analysis`, and `general_non_template_analysis`.
- `[x]` Planner output includes `success`, `scenario_type`, `analysis_steps`, `provider_called`, `fallback_used`, `prompt_id`, `validation_error`, and `provider_error`.
- `[x]` Each analysis step includes `step_id`, `question`, `required_metrics`, `required_dimensions`, and `candidate_tables`.
- `[x]` Planner reuses P5 semantic metrics, dimensions, entities, and join paths to populate required metrics, dimensions, and candidate tables.
- `[x]` No-key deterministic baseline works without an API key or provider.
- `[x]` Optional provider-backed planner uses `llm_ops/runtime_provider.py`, `prompt_registry.py`, and `structured_output.py`.
- `[x]` Provider output is rejected if it contains SQL, final claims, action payloads, approval fields, or malformed step shapes.
- `[x]` Malformed provider JSON and provider/schema errors fall back to deterministic planning without crashing.
- `[x]` Workflow adds planner state and trace evidence without bypassing Schema Agent, Metric Agent, SQL Reviewer, `validate_sql()`, `run_sql()`, or Evidence Validator.
- `[x]` P0 workflow and P0 eval remain compatible and provider-independent by default.

### P7 Visualization Intelligence Acceptance Tracker

- `[x]` `visualization/chart_registry.py` registers `ranked_bar`, `line`, `grouped_bar`, `dual_axis_line`, `funnel`, `heatmap`, `scatter`, and `risk_matrix`.
- `[x]` `visualization/chart_spec.py` normalizes chart specs with `chart_type`, `title`, `x`, `y`, `y_secondary`, `series`, `required_columns`, `explanation_basis`, `provider_called`, `fallback_used`, `prompt_id`, `validation_error`, and `provider_error`.
- `[x]` `visualization/chart_validator.py` rejects chart specs that reference columns missing from `execution_result`.
- `[x]` `visualization/chart_renderer.py` renders from real `execution_result.rows`, reports `data_row_count`, preserves rendered rows for traceability, and marks `fabricated_data: false`.
- `[x]` Unsupported chart types fall back to a safe table or basic ranked bar chart instead of crashing.
- `[x]` Historical P7 `agents/visualization_planner.py` generated deterministic chart specs before P8.1 superseded and deleted it.
- `[x]` Provider-backed visualization planning uses `llm_ops/runtime_provider.py`, `prompt_registry.py`, and `structured_output.py`.
- `[x]` Provider output is rejected if it contains SQL, final claims, action payloads, approval fields, unsupported chart types, malformed fields, or columns absent from `execution_result`.
- `[x]` Malformed provider output and provider/schema errors fall back to deterministic chart specs without crashing.
- `[x]` Historical P7 `agents/chart_agent.py` preserved the old simple bar/line/pie path before P8.1 superseded and deleted it.
- `[x]` Workflow adds visualization plan state and trace metadata after SQL execution and insight/claim typing without bypassing Schema Agent, Metric Agent, SQL Reviewer, `validate_sql()`, `run_sql()`, or Evidence Validator.
- `[x]` Historical P7 baseline: default no-key deterministic visualization planning worked without an API key or provider before the P8 cleanup.
- `[x]` Historical P7 baseline: P0 workflow and P0 eval remained compatible and provider-independent before the P8 cleanup.

### P8.1 Visualization Agent Dedupe & External Tool Calling Status

- `[x]` `agents/visualization_agent.py` is the main visualization decision entry point.
- `[x]` P7 `visualization/` chart spec, validator, and renderer are reused as safety/tool foundations.
- `[x]` `visualization_delivery/tool_catalog.py` registers `local_renderer`, `excel_exporter`, and `powerbi_publisher_mock`.
- `[x]` The `visualization_agent` prompt/schema lets the provider select both chart spec and delivery tool.
- `[x]` `tools/external_visualization_tool.py` and delivery adapters validate tool policy before execution.
- `[x]` Deterministic code owns column validation, tool existence, artifact policy, trace metadata, and adapter execution.
- `[x]` Old chart-decision behavior and obsolete tests were deleted instead of preserved as parallel compatibility paths.
- `[x]` Provider output containing SQL, final claims, action payloads, approval fields, credentials, unknown tool ids, unsupported chart types, missing columns, malformed JSON, or fabricated rows is rejected or safely falls back.
- `[x]` Excel export writes a real local workbook from `execution_result.rows`.
- `[x]` Power BI delivery is an explicit mock external adapter returning `external_tool_called: true` and `mock://powerbi/...`; no real SaaS auth/API is used.
- `[x]` Workflow state/trace runs after SQL execution and Evidence Validator boundaries without bypassing Schema Agent, Metric Agent, SQL Reviewer, `validate_sql()`, `run_sql()`, or Evidence Validator.
- `[x]` Focused tests cover provider success, provider malformed output, unsafe provider output, missing columns, unknown tool ids, real-row export/rendering, mock external publish trace, and retained workflow safety boundaries.

### P9 Realistic Eval And Demo Polish Status

- `[x]` `eval/test_questions.json` now includes 32 cases: the original P0 guardrail cases plus P9 GMV decline, category anomaly, city/regional performance, Top/Bottom products, refund risk, weekly review, visualization delivery, action suggestion, unsafe/sensitive rejection, provider-unavailable fallback, and provider validation-error scenarios.
- `[x]` `eval/run_eval.py` reports provider-called cases, fallback-used cases, visualization delivery tool id, external visualization tool calls, artifact type/path/url, action delivery tool ids, approval requirements, evidence success, unsupported claim rate, trace event count, tool call count, validation errors, and provider errors.
- `[x]` No-key eval uses deterministic runtime plus explicit mock provider payloads in eval cases; it does not require a real DeepSeek API key.
- `[x]` Excel exporter, Power BI mock, Jira mock, approval gate, validation-error fallback, provider-unavailable fallback, and unsafe sensitive-field rejection are visible in eval results.
- `[x]` Streamlit demo questions now include realistic P9 business paths while remaining a transition demo, not the final product UI.

### P8.2-P8.5 Cleanup Program Status

- `[x]` P8.2 Intent & SQL Planning Agent Cleanup is complete: provider-backed intent and SQL planning are the configured product paths, unsafe/sensitive guards run before provider calls, provider failures return `provider_unavailable`, and provider candidate SQL still requires validation/review.
- `[x]` P8.3 Report & Insight Agent Cleanup is complete: provider-backed report planning is the product path for section selection, provider-unavailable plans do not auto-select fixed sections, Report Supervisor remains an orchestrator, and `insight_drafter` feeds candidate claims into claim typing/Evidence Validator.
- `[x]` P8.4 Action Agent & Tool Adapter Cleanup is complete: `agents/action_planner.py` no longer emits fixed action templates in the product path, provider output drafts contextual actions plus `delivery_tool_id`, provider-unavailable mode is structured, `agents/action_executor.py` is split from Risk Assessor, and `action_delivery/` executes local SQLite plus mock Jira-style adapters only after approval.
- `[x]` P8.5 Agent Pipeline UX is complete: Streamlit Command Center exposes the cleaned agent pipeline, tool-call cards, validator gates, artifact panel, and source metadata without changing workflow execution or safety boundaries.
- `[x]` P9 Realistic Eval And Demo Polish is complete.
- `[x]` P10 Lightweight Engineering Hardening is complete at implementation/doc level: MCP contracts advertise an external-safe scope, public MCP contracts do not expose internal validator/audit/trace tools, eval reports include artifact hygiene notes, and generated DB/report/trace/chart/workbook/mock output paths are covered by `.gitignore`.

## Update Rules

After every task:

1. Update `Last updated`.
2. Move `Current task` and `Last completed task`.
3. Update the relevant phase row in `Phase Overview`.
4. Mark task-level Development, Tests, Docs, and Status fields.
5. Update acceptance trackers when a capability becomes real and verified.
6. Record the exact verification command in the final response for that task.

## Latest Verification

P10 verification:

```bash
python3 -m pytest tests/test_mcp_tool_layer.py tests/test_eval_runner.py -q
python3 -m pytest tests/test_mcp_tool_layer.py tests/test_eval_runner.py tests/test_streamlit_app.py -q
python3 -m pytest tests/test_visualization_agent_external_tools.py tests/test_action_agent_tool_adapter_cleanup.py tests/test_workflow.py -q
python3 -m pytest
python3 eval/run_eval.py
rg -n "chart_agent|visualization_planner|chart_tool|old|legacy|TODO|deprecated|fixed template|deterministic action template|keyword inference"
```

Result: P10 red/green focused tests first failed on missing MCP `contract_scope`, missing eval `artifact_hygiene_note`, and missing generated-artifact `.gitignore` entries; after implementation, the focused MCP/eval tests report 13/13 passed. The suggested MCP/eval/Streamlit regression reports 34/34 passed, the visualization/action/workflow regression reports 23/23 passed, the default full suite reports 246 passed and 9 opt-in live DeepSeek tests skipped by default, and `python3 eval/run_eval.py` reports 32/32 passed with SQL execution success rate 95.83%, SQL repair success rate 100.00%, dangerous SQL block rate 100.00%, metric definition accuracy 100.00%, provider-called cases 4, fallback-used cases 23, visualization external-tool-called cases 23, Excel exporter 1, Power BI mock 1, Jira mock 1, evidence success rate 100.00%, validation-error cases 1, provider-error cases 20, and an artifact hygiene note in the eval summary/report. The legacy audit only found superseded historical documentation/test assertions, schema field names such as `old_price`, and action alert `threshold` fields; it did not find active old chart agent/planner/tool product paths.

P9 verification:

```bash
python3 -m pytest tests/test_eval_runner.py tests/test_streamlit_app.py tests/test_visualization_agent_external_tools.py tests/test_action_agent_tool_adapter_cleanup.py -q
python3 -m pytest tests/test_workflow.py tests/test_mcp_tool_layer.py tests/test_sql_validator.py tests/test_evidence_validator.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: P9 focused eval/Streamlit/visualization/action tests report 47/47 passed; workflow/MCP/SQL/Evidence regression reports 19/19 passed; the default full suite reports 245 passed and 9 opt-in live DeepSeek tests skipped by default; P9 eval reports 32/32 passed with SQL execution success rate 95.83%, SQL repair success rate 100.00%, dangerous SQL block rate 100.00%, metric definition accuracy 100.00%, provider-called cases 4, fallback-used cases 23, visualization external-tool-called cases 23, Excel exporter 1, Power BI mock 1, Jira mock 1, evidence success rate 100.00%, validation-error cases 1, and provider-error cases 20. P9 proves realistic scenario eval coverage, external visualization/action tool traceability, no-key mock provider coverage, provider-unavailable fallback, provider validation-error fallback, and unsafe/sensitive request blocking without restoring old chart/planner/tool product paths.

P8.5 verification:

```bash
python3 -m pytest tests/test_streamlit_app.py::test_run_detail_view_model_exposes_cleaned_agent_pipeline_tool_gates_and_artifacts -q
python3 -m pytest tests/test_streamlit_app.py -q
python3 -m pytest tests/test_streamlit_app.py tests/test_workflow.py tests/test_visualization_agent_external_tools.py tests/test_action_agent_tool_adapter_cleanup.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: P8.5 red/green focused test first failed on missing `agent_pipeline` and then passed after implementation; Streamlit tests report 19/19 passed; related Streamlit/workflow/visualization/action regression reports 42/42 passed; the default full suite reports 240 passed and 9 opt-in live DeepSeek tests skipped by default; P0 eval reports 20/20 passed. P8.5 exposes agent pipeline, tool calls, validator gates, artifacts, provider prompts, fallback flags, policy status, and mock external URLs in Streamlit without changing backend safety boundaries.

P8.4 verification:

```bash
python3 -m pytest tests/test_action_agent_tool_adapter_cleanup.py tests/test_action_workflow.py tests/test_provider_backed_action_drafter.py tests/test_llm_provider_promptops.py tests/test_deepseek_provider_structured_output.py -q
python3 -m pytest tests/test_mcp_tool_layer.py tests/test_workflow.py tests/test_sql_validator.py tests/test_evidence_validator.py tests/test_streamlit_app.py tests/test_runtime_provider.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: P8.4 focused/action/provider tests report 30/30 passed; related MCP/workflow/SQL/Evidence/Streamlit/runtime regression reports 40/40 passed; the default full suite reports 239 passed and 9 opt-in live DeepSeek tests skipped by default; P0 eval reports 20/20 passed. P8.4 removes fixed action templates from the product path, keeps provider-unavailable action planning structured, splits execution into `agents/action_executor.py`, and routes approved action delivery through local SQLite plus mock Jira-style adapters behind audit and approval.

P7 verification:

```bash
python3 -m pytest tests/test_visualization_intelligence.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: Historical P7 verification passed before P8 cleanup. The retained P7 boundary is chart spec validation and no-fabricated-data rendering; obsolete chart-tool/chart-agent product-path tests are deleted during P8.1 cleanup. The historical default full suite reported 220 passed and 9 opt-in live DeepSeek tests skipped by default; P0 eval reported 20/20 passed.

P6 verification:

```bash
python3 -m pytest tests/test_analysis_planner.py tests/test_provider_backed_analysis_planner.py -q
python3 -m pytest tests/test_semantic_layer.py tests/test_metric_tool.py tests/test_workflow.py tests/test_sql_validator.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: P6 planner tests report 9/9 passed; semantic layer, metric tool, workflow, and SQL validator regressions report 22/22 passed; the default full suite reports 212 passed and 9 opt-in live DeepSeek tests skipped by default; P0 eval reports 20/20 passed. P6 adds deterministic and provider-backed scenario analysis planning, semantic metrics/dimensions/table retrieval, workflow trace metadata, provider fallback on malformed or unsafe output, and preserves SQL validation, SQL execution, Evidence Validator, action approval, audit, and no-key baseline boundaries.

Task 28 verification:

```bash
python3 -m pytest tests/test_llm_template_mining_eval_suite.py tests/test_deepseek_llm_eval_suite_live.py -q
python3 -m pytest tests/test_llm_template_mining_eval_suite.py tests/test_sql_planning_router.py tests/test_provider_assisted_sql_planning_workflow.py tests/test_llm_provider_promptops.py -q
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 python3 -m pytest tests/test_deepseek_llm_eval_suite_live.py -q
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER=1 INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER=1 INSIGHTFLOW_USE_PROVIDER_REPORT_WRITER=1 INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING=1 INSIGHTFLOW_USE_PROVIDER_ACTION_DRAFTER=1 python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_deepseek_question_understanding_workflow_live.py tests/test_deepseek_clarification_workflow_live.py tests/test_deepseek_sql_planning_workflow_live.py tests/test_deepseek_business_review_planner_live.py tests/test_deepseek_report_writer_live.py tests/test_deepseek_claim_typing_workflow_live.py tests/test_deepseek_action_drafter_live.py tests/test_deepseek_llm_eval_suite_live.py -q
python3 -m pytest -q -rs
python3 eval/run_eval.py
```

Result: Task 28 local trace-mining/eval tests report 2 passed and 1 live test skipped by default; SQL planning/PromptOps regressions report 24/24 passed; the real DeepSeek-backed LLM eval suite reports 1/1 passed when explicitly enabled; the full live DeepSeek workflow/eval suite reports 9/9 passed when all provider switches are explicitly enabled; the default full suite reports 185 passed and 9 opt-in live DeepSeek tests skipped by default; P0 eval reports 20/20 passed. Task 28 proves the project can mine accepted guarded SQL candidate traces into non-auto-applied deterministic-template recommendations and can run schema-aware LLM evals for valid output, malformed JSON, and schema mismatch handling.

Task 27 verification:

```bash
python3 -m pytest tests/test_provider_backed_action_drafter.py tests/test_deepseek_action_drafter_live.py tests/test_llm_provider_promptops.py tests/test_runtime_provider.py -q
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_ACTION_DRAFTER=1 python3 -m pytest tests/test_deepseek_action_drafter_live.py -q
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER=1 INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER=1 INSIGHTFLOW_USE_PROVIDER_REPORT_WRITER=1 INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING=1 INSIGHTFLOW_USE_PROVIDER_ACTION_DRAFTER=1 python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_deepseek_question_understanding_workflow_live.py tests/test_deepseek_clarification_workflow_live.py tests/test_deepseek_sql_planning_workflow_live.py tests/test_deepseek_business_review_planner_live.py tests/test_deepseek_report_writer_live.py tests/test_deepseek_claim_typing_workflow_live.py tests/test_deepseek_action_drafter_live.py -q
python3 -m pytest -q -rs
python3 eval/run_eval.py
```

Result: Task 27 action drafter/PromptOps/runtime provider tests report 16 passed and 1 live test skipped by default; the real DeepSeek-backed action drafting workflow smoke reports 1/1 passed when explicitly enabled; the full live DeepSeek workflow suite reports 8/8 passed when all provider switches are explicitly enabled; the default full suite reports 183 passed and 8 opt-in live DeepSeek tests skipped by default; P0 eval reports 20/20 passed. Task 27 proves DeepSeek can participate in the real action workflow by drafting pending task, metric-alert, and email-draft payloads before Risk Assessor and Approval Gate, while deterministic fallback, approval blocking, action execution, and audit boundaries remain intact.

Task 26 verification:

```bash
python3 -m pytest tests/test_guarded_insight_claim_typing.py tests/test_deepseek_claim_typing_workflow_live.py tests/test_llm_provider_promptops.py tests/test_runtime_provider.py -q
python3 -m pytest tests/test_workflow.py tests/test_guarded_insight_claim_typing.py tests/test_deepseek_claim_typing_workflow_live.py -q
python3 -m pytest tests/test_report_supervisor.py tests/test_provider_backed_report_writer.py tests/test_report_planner.py -q
python3 -m pytest tests/test_guarded_llm_enhancer.py tests/test_llm_provider_promptops.py tests/test_deepseek_provider_structured_output.py tests/test_runtime_provider.py -q
python3 -m pytest tests/test_streamlit_app.py tests/test_async_run_api.py -q
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING=1 python3 -m pytest tests/test_deepseek_claim_typing_workflow_live.py -q
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER=1 INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER=1 INSIGHTFLOW_USE_PROVIDER_REPORT_WRITER=1 INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING=1 python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_deepseek_question_understanding_workflow_live.py tests/test_deepseek_clarification_workflow_live.py tests/test_deepseek_sql_planning_workflow_live.py tests/test_deepseek_business_review_planner_live.py tests/test_deepseek_report_writer_live.py tests/test_deepseek_claim_typing_workflow_live.py -q
python3 -m pytest -q -rs
python3 eval/run_eval.py
```

Result: Task 26 claim typing tests report 14 passed and 1 live test skipped by default; workflow claim-typing tests report 8 passed and 1 live test skipped by default; report-supervisor/report-writer/report-planner tests report 13/13 passed; guarded enhancer/PromptOps/DeepSeek/runtime provider tests report 22/22 passed; Streamlit/API tests report 17/17 passed; the real DeepSeek-backed claim typing workflow smoke reports 1/1 passed when explicitly enabled; the full live DeepSeek workflow suite reports 7/7 passed when all provider switches are explicitly enabled; the default full suite reports 177 passed and 7 opt-in live DeepSeek tests skipped by default; P0 eval reports 20/20 passed. Task 26 proves DeepSeek can participate in core insight claim typing and report-section claim typing while Evidence Validator remains the final authority.

Task 25 verification:

```bash
python3 -m pytest tests/test_provider_backed_report_writer.py tests/test_deepseek_report_writer_live.py tests/test_llm_provider_promptops.py tests/test_runtime_provider.py -q
python3 -m pytest tests/test_report_agent.py tests/test_report_supervisor.py tests/test_report_planner.py tests/test_provider_backed_report_writer.py tests/test_deepseek_report_writer_live.py -q
python3 -m pytest tests/test_deepseek_provider_structured_output.py tests/test_llm_provider_promptops.py tests/test_runtime_provider.py -q
python3 -m pytest tests/test_streamlit_app.py -q
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_REPORT_WRITER=1 python3 -m pytest tests/test_deepseek_report_writer_live.py -q
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER=1 INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER=1 INSIGHTFLOW_USE_PROVIDER_REPORT_WRITER=1 python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_deepseek_question_understanding_workflow_live.py tests/test_deepseek_clarification_workflow_live.py tests/test_deepseek_sql_planning_workflow_live.py tests/test_deepseek_business_review_planner_live.py tests/test_deepseek_report_writer_live.py -q
python3 -m pytest -q -rs
python3 eval/run_eval.py
```

Result: Task 25 provider-backed report writer tests report 12 passed and 1 live test skipped by default; report/report-supervisor regression tests report 15 passed and 1 live test skipped by default; DeepSeek structured-output/PromptOps/runtime provider tests report 17/17 passed; Streamlit tests report 13/13 passed; the real DeepSeek-backed report writer workflow smoke reports 1/1 passed when explicitly enabled; the full live DeepSeek workflow suite reports 6/6 passed when all provider switches are explicitly enabled; the default full suite reports 172 passed and 6 opt-in live DeepSeek tests skipped by default; P0 eval reports 20/20 passed. Task 25 proves DeepSeek can participate in real report writing after Evidence Validator while unsupported claims are rejected and deterministic fallback remains available without an API key.

Task 24 verification:

```bash
python3 -m pytest tests/test_runtime_provider.py -q
python3 -m pytest tests/test_report_planner.py tests/test_report_supervisor.py tests/test_deepseek_business_review_planner_live.py -q
python3 -m pytest tests/test_streamlit_app.py tests/test_llm_provider_promptops.py tests/test_deepseek_provider_structured_output.py -q
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER=1 python3 -m pytest tests/test_deepseek_business_review_planner_live.py -q
python3 -m pytest -q -rs
python3 eval/run_eval.py
```

Result: runtime provider tests report 3/3 passed; Task 24 report planner/supervisor tests report 10 passed and 1 live DeepSeek test skipped by default; Streamlit/PromptOps/DeepSeek structured-output tests report 26/26 passed; the real DeepSeek-backed business review decomposition workflow smoke reports 1/1 passed when explicitly enabled; the default full suite reports 168 passed and 5 opt-in live DeepSeek tests skipped by default; P0 eval reports 20/20 passed. No full-suite warning was reported. Task 24 proves DeepSeek can participate in the real report supervisor workflow by selecting validated weekly/monthly review sections while provider-supplied SQL or claims are rejected and deterministic fallback remains available without an API key.

Task 23 verification:

```bash
python3 -m pytest tests/test_provider_assisted_sql_planning_workflow.py tests/test_deepseek_sql_planning_workflow_live.py -q
python3 -m pytest tests/test_provider_assisted_sql_planning_workflow.py tests/test_deepseek_sql_planning_workflow_live.py tests/test_sql_planning_router.py tests/test_guarded_llm_enhancer.py -q
python3 -m pytest tests/test_workflow.py tests/test_async_run_api.py tests/test_streamlit_app.py -q
python3 -m pytest tests/test_llm_provider_promptops.py tests/test_deepseek_provider_structured_output.py tests/test_runtime_provider.py -q
python3 -m pytest
python3 eval/run_eval.py
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 python3 -m pytest tests/test_deepseek_sql_planning_workflow_live.py -q
```

Result: Task 23 provider-assisted SQL planning workflow tests report 7/7 passed; related SQL planning/guarded-candidate/live-skip tests report 18 passed and 1 skipped by default; workflow/API/Streamlit tests report 21/21 passed; PromptOps/DeepSeek/runtime provider tests report 16/16 passed; the default full test suite reports 165 passed, 4 skipped live tests, and one FastAPI TestClient deprecation warning from Starlette; P0 eval reports 20/20 passed. A real DeepSeek-backed SQL planning workflow run with `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1` reports 1/1 passed, proving DeepSeek participates in runtime SQL planning and guarded candidate generation while SQL still passes through `validate_sql()` and the SQL Reviewer before execution.

Task 22 verification:

```bash
python3 -m pytest tests/test_provider_backed_clarification_router.py
python3 -m pytest tests/test_provider_backed_clarification_router.py tests/test_runtime_provider.py tests/test_deepseek_clarification_workflow_live.py -q
python3 -m pytest tests/test_workflow.py tests/test_async_run_api.py tests/test_streamlit_app.py -q
python3 -m pytest tests/test_question_understanding_router.py tests/test_provider_backed_question_understanding.py tests/test_sql_planning_router.py -q
python3 -m pytest tests/test_provider_backed_clarification_router.py tests/test_workflow.py tests/test_eval_runner.py -q
python3 -m pytest
python3 eval/run_eval.py
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER=1 python3 -m pytest tests/test_deepseek_clarification_workflow_live.py -q
```

Result: Task 22 provider-backed clarification tests report 7/7 passed; runtime provider/provider-backed/live-skip tests report 10 passed and 1 skipped by default; workflow/API/Streamlit tests report 21/21 passed; question-understanding/provider-backed/SQL-planning tests report 24/24 passed; the default full test suite reports 158 passed, 3 skipped live tests, and one FastAPI TestClient deprecation warning from Starlette; P0 eval reports 20/20 passed. A real DeepSeek-backed clarification workflow run with `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER=1` reports 1/1 passed, proving DeepSeek participates in the runtime clarification node while ambiguous requests stop before schema retrieval, SQL generation, and SQL execution.

Task 21A verification:

```bash
python3 -m pytest tests/test_provider_backed_question_understanding.py::test_core_workflow_uses_provider_backed_question_understanding_when_provider_is_supplied tests/test_provider_backed_question_understanding.py::test_core_workflow_env_opt_in_without_api_key_keeps_deterministic_baseline
python3 -m pytest tests/test_runtime_provider.py tests/test_provider_backed_question_understanding.py tests/test_deepseek_question_understanding_workflow_live.py -q
python3 -m pytest tests/test_provider_backed_question_understanding.py tests/test_workflow.py tests/test_async_run_api.py tests/test_streamlit_app.py
python3 -m pytest tests/test_question_understanding_router.py tests/test_sql_planning_router.py
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 python3 -m pytest tests/test_deepseek_question_understanding_workflow_live.py -q
```

Result: focused runtime workflow tests report 2/2 passed; runtime provider/provider-backed/live-skip tests report 13 passed and 1 skipped by default; provider-backed/workflow/API/Streamlit tests report 31/31 passed; question-understanding and SQL-planning tests report 14/14 passed; the default full test suite reports 151 passed, 2 skipped live tests, and one FastAPI TestClient deprecation warning from Starlette; P0 eval reports 20/20 passed with average tool calls 7.85 after adding the question-understanding workflow node. A real DeepSeek-backed workflow run with `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1` reports 1/1 passed, proving DeepSeek participates in the core workflow question-understanding node. Live workflow attempts exposed real normalization issues (`销售额` and `sales` needed to normalize to `gmv`); Task 21A now includes alias normalization and regression tests for those paths.

Task 21 verification:

```bash
python3 -m pytest tests/test_provider_backed_question_understanding.py
python3 -m pytest tests/test_question_understanding_router.py tests/test_deepseek_provider_structured_output.py tests/test_llm_provider_promptops.py tests/test_provider_backed_question_understanding.py
python3 -m pytest
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 python3 -m pytest tests/test_deepseek_live_smoke.py -q
python3 eval/run_eval.py
```

Result: Task 21 provider-backed question-understanding tests report 7/7 passed; related Task 20A/20C/PromptOps tests report 27/27 passed; the default full test suite reports 145 passed, 1 skipped opt-in live DeepSeek smoke test, and one FastAPI TestClient deprecation warning from Starlette; the real live DeepSeek smoke test reports 1/1 passed when explicitly enabled with network access; P0 eval reports 20/20 passed. The provider-backed path validates `question_understanding` output, normalizes intent slots, falls back deterministically on provider failure, malformed JSON, or schema mismatch, records provider/fallback metadata, preserves sensitive risk flags, and does not generate SQL, execute SQL, or perform SQL planning.

Task 20B verification:

```bash
python3 -m pytest tests/test_sql_planning_router.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 20B SQL planning router tests report 7/7 passed; the full test suite reports 138/138 passed with 1 skipped opt-in live DeepSeek smoke test and one FastAPI TestClient deprecation warning from Starlette; P0 eval reports 20/20 passed. The router maps stable intents to deterministic template IDs, preserves clarify/reject routes, sends complete non-template intents to guarded `llm_candidate` policy, records validation requirements, summarizes repeated candidate patterns for template mining, and does not call a provider, generate SQL, or execute SQL.

Task 20A verification:

```bash
python3 -m pytest tests/test_question_understanding_router.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 20A question-understanding tests report 7/7 passed; the full test suite reports 131/131 passed with 1 skipped opt-in live DeepSeek smoke test and one FastAPI TestClient deprecation warning from Starlette; P0 eval reports 20/20 passed. The router extracts deterministic intent slots, returns clarification questions for missing slots, rejects sensitive or unsafe requests before SQL planning, writes state and trace through the Agent wrapper, and does not generate SQL or Task 20B `matched_template` / confidence fields.

Task 20C verification:

```bash
python3 -m pytest tests/test_llm_provider_promptops.py tests/test_deepseek_provider_structured_output.py tests/test_deepseek_live_smoke.py -q
python3 -m pytest
python3 eval/run_eval.py
```

Result: Task 20/20C provider and structured-output tests report 13/13 passed with 1 opt-in live DeepSeek smoke test skipped by default; the full test suite reports 124/124 passed with 1 skipped live test and one FastAPI TestClient deprecation warning from Starlette; P0 eval reports 20/20 passed. Task 20C adds `DeepSeekProvider`, `.env` config loading, strict per-prompt schema validation, malformed JSON errors, schema mismatch errors, and an explicit live-test opt-in while preserving the no-key deterministic baseline.

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
python3 -m pytest
python3 eval/run_eval.py
```

Result: Historical Task 13 verification passed before P8 cleanup. The old Chart Tool / Chart Agent business path is no longer retained as the planned product path; P8.1 replaces it with one LLM-first Visualization Agent plus approved external visualization tool adapters.

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
