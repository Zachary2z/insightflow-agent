# InsightFlow Agent Development Plan

This document tracks the active product plan for InsightFlow Agent. P11 General Data Analysis Product hardening is complete. P12 Report Productization is complete through docs, artifact audit, and final verification. P13 Business Answer And Product UX is complete through H8 real DeepSeek product acceptance, with H9 final documentation, artifact audit, regression, and closeout verification active. Historical P0-P10 notes are retained only as context for why the current safety and tool boundaries exist.

## Current Product Direction

The current product is a workspace-based data analysis application:

```text
FastAPI backend
+ Next.js frontend
+ user workspaces
+ CSV/Excel/SQLite imports
+ workspace database profile
+ semantic-layer draft
+ natural business question for P11 ad hoc analysis
+ structured P12 workspace reports
+ P13 Analysis Workbench, clarification continuation, Data Settings, and chart display
+ live DeepSeek/provider-backed product mode
+ guarded SQL candidate
+ validated SQL execution
+ business answer, visualization/artifact/report/trace output
```

The current product is not the historical Streamlit demo, not the old ecommerce-only demo, not the old eval benchmark, and not mock SaaS integration work.

## Phase Development Status

| Phase | Name | Status | Current meaning |
|---|---|---|---|
| P0 | Agentic SQL Core | Complete | Historical foundation for SQL tools, validator, executor, agents, and trace boundaries |
| P1 | Reliable Analysis & Report Core | Complete | Historical foundation for business context, evidence validation, charts, and reports |
| P2 | Business Review & Action Workflow | Complete | Historical foundation for report supervision and approval-gated action boundaries |
| P3 | MCP & Engineering Core | Complete for scoped baseline | Historical foundation for provider/PromptOps, FastAPI work, MCP contracts, and observability |
| P4 | Realistic Scenario Dataset | Complete | Historical realistic-data and business-rule expansion |
| P5 | Lightweight Semantic Layer | Complete | Retained semantic context layer |
| P6 | Scenario Analysis Planner | Complete | Retained analysis planning support |
| P7 | Visualization Intelligence | Complete | Retained visualization validation/rendering foundation |
| P8.1 | Visualization Agent Dedupe & External Tool Calling | Complete | Current visualization business entry is `VisualizationAgent` |
| P8.2 | Intent & SQL Planning Agent Cleanup | Complete | Provider-backed question understanding and SQL planning are product paths when configured |
| P8.3 | Report & Insight Agent Cleanup | Complete | Provider-backed report/insight planning is evidence-gated |
| P8.4 | Action Agent & Tool Adapter Cleanup | Complete | Provider-backed action drafting remains behind risk/approval/audit boundaries |
| P8.5 | Agent Pipeline UX | Complete | Historical Streamlit visibility work, now superseded by P11 Next.js product UI |
| P9 | Realistic Eval And Demo Polish | Complete | Historical eval/demo polish |
| P10 | MCP Contract & Lightweight Engineering Hardening | Complete | Historical contract and generated-artifact hygiene baseline |
| P11 | General Data Analysis Product | Complete | H1-H5 hardening complete; backend, frontend, artifact, and live DeepSeek verification passed |
| P12 | Report Productization | Complete | H1 report storage and Markdown foundation complete; H2 synchronous workspace report runner complete; H3 FastAPI report APIs complete; H4 Next.js reports UI complete; H5 live DeepSeek report acceptance complete; H6 docs, artifact audit, and final verification complete |
| P13 | Business Answer And Product UX | H9 final verification active | H1-H8 complete: Analysis Workbench, clarification continuation, business-facing answers, reports UI polish, Data Settings UI, chart product quality, and real DeepSeek product acceptance; H9 documentation/audit/regression/closeout is active |

## P11 Product Hardening Plan

P11 is complete. It makes the project read and behave like a general workspace data-analysis product rather than a demo sequence.

| Task | Goal | Status | Acceptance |
|---|---|---|---|
| H1 | Add FastAPI data source endpoints for CSV/Excel upload, SQLite import, and source listing | Complete | `api/app.py` exposes workspace source APIs and tests cover upload/import/list/error paths |
| H2 | Wire Next.js into real product APIs | Complete | Frontend supports workspace list/create, data source import/list, profile, semantic draft, analysis submission, and run-result rendering |
| H3 | Delete replaced Streamlit UI and old ecommerce API entry | Complete | tracked `ui/`, root `app.py`, old `api/run_manager.py`, old `/api/runs`, and legacy async run tests are gone |
| H4 | Strengthen live DeepSeek workspace acceptance | Complete | Natural business question uses workspace profile/semantic context, provider understanding/planning/candidate/visualization, validated SQL, real execution rows, and workspace-rooted artifacts |
| H5 | Clean current product documentation | Complete | README, plan, and status now point to P11 workspace + FastAPI + Next.js + live DeepSeek and mark old demo/eval/mock references as historical only |

## P11 Final Verification Checklist

Latest result: passed on 2026-06-23.

Run these before any future P11 completion claim:

```bash
python3 -m pytest tests/test_p11_cleanup_boundaries.py tests/test_project_initialization.py -q
python3 -m pytest -q
cd frontend && npm test
cd frontend && npm run build
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 \
INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1 \
python3 -m pytest tests/test_p11_live_deepseek_workspace_analysis.py -q
```

Also verify tracked artifact hygiene with the command from the H5 task request. Expected result: no tracked legacy UI/API/eval files and no generated frontend/report/chart/trace artifacts.

## P11 Current Entry Points

Backend:

```bash
uvicorn api.app:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Primary product API:

```text
POST /api/workspaces/{workspace_id}/runs
```

The old non-workspace run API is intentionally absent. Workspace analysis must go through `workspaces.analysis_runner.run_workspace_analysis()` so the run is tied to imported data, workspace profile/semantic context, workspace artifacts, and workspace traces.

## Current Product Boundaries

LLM/provider-backed agents may:

- understand natural business questions;
- ask clarification questions;
- plan SQL strategy;
- draft guarded SQL candidates;
- draft insights/report wording;
- choose visualization specs and delivery tools.

Deterministic code must still own:

- unsafe/sensitive request blocking before execution;
- `validate_sql()` and SQL Reviewer approval;
- `run_sql()` execution;
- Evidence Validator final claim filtering;
- chart spec validation and tool policy validation;
- approval, execution, audit, and trace boundaries.

## Historical / Superseded Context

P0-P10 content is retained as historical context only. It explains how the safety boundaries evolved, but it is not current product guidance.

- Historical / Superseded: `streamlit run app.py`, `eval/run_eval.py`, mock jira demos, `powerbi_publisher_mock`, fixed template behavior, deterministic action template behavior, and chart keyword inference are old demo/eval or cleanup-history terms, not P11 product instructions.
- Historical retained low-level fixture: `data/ecommerce.db` remains tracked because low-level tests still use it for schema, validator, executor, workflow, report, MCP, and provider regressions. It is not the API default, not the quickstart database, and not the current product data source.
- Historical mock adapters demonstrate tool-call boundaries only. They do not mean real SaaS integration, auth/RBAC, deployment, or P12 report productization has started.

## P12 Report Productization Plan

P12 is complete. It turns P11 single-question workspace analysis into a separate structured report product. P11 remains the ad hoc analysis entry point at `/workspaces/{workspace_id}/analysis`; P12 adds report generation under `/workspaces/{workspace_id}/reports`.

Design spec: `docs/superpowers/specs/2026-06-23-p12-workspace-report-productization-design.md`.

### P12 MVP Decisions

- UI output: page display.
- Download output: Markdown file.
- Generation mode: synchronous first.
- Future upgrade: async generation and polling.
- First report types: `business_review`, `channel_performance`, `revenue_trend`.
- P11 analysis remains separate and unchanged.

### P12 MVP Product Flow

```text
workspace
-> reports page
-> select report type
-> enter report goal
-> synchronously generate report
-> run each section through P11-safe analysis boundaries
-> persist report.json, report.md, trace.json, artifacts
-> display report page
-> download Markdown
```

### P12 Backend Target

Add workspace report APIs:

```text
POST /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports/{report_id}
GET  /api/workspaces/{workspace_id}/reports/{report_id}/download
```

Add a report runner:

```text
workspaces/report_runner.py
```

Report storage:

```text
workspaces/{workspace_id}/reports/{report_id}/report.json
workspaces/{workspace_id}/reports/{report_id}/report.md
workspaces/{workspace_id}/reports/{report_id}/trace.json
workspaces/{workspace_id}/reports/{report_id}/artifacts/
```

Report-facing artifacts must be rooted under the report directory. If a section reuses P11 run internals, copy or regenerate any chart/report-facing artifact into `reports/{report_id}/artifacts/` before writing `report.json` and `report.md`.

Existing workspace semantic-layer files must not be silently overwritten. Generate profile/semantic-layer draft context only when missing, or create an explicit report-local context snapshot.

### P12 Frontend Target

Add report routes:

```text
frontend/app/workspaces/[workspaceId]/reports/page.tsx
frontend/app/workspaces/[workspaceId]/reports/[reportId]/page.tsx
```

Likely components:

- `ReportGenerator`
- `ReportList`
- `ReportViewer`
- `ReportSection`
- `ReportDownloadLink`

### P12 Task Queue

| Task | Scope | Status |
|---|---|---|
| P12-H1 | Report domain model, report directory layout, Markdown renderer; no provider calls yet | Complete |
| P12-H2 | Synchronous workspace report runner that creates multi-section reports through P11-safe analysis boundaries; presets create section purposes/questions, not SQL templates or keyword rule trees | Complete |
| P12-H3 | FastAPI report create/list/detail/download APIs | Complete |
| P12-H4 | Next.js reports list/generate/detail UI with Markdown download | Complete |
| P12-H5 | Live DeepSeek workspace report acceptance test | Complete |
| P12-H6 | P12 docs, artifact audit, final verification | Complete |

### P12 Out Of Scope

- PDF/PPT export.
- Async report generation.
- Scheduled reports.
- Email delivery.
- Real Slack/Jira/Power BI/Notion integrations.
- Auth/RBAC.
- Deployment.
- Replacing P11 ad hoc analysis.
- Restoring historical Streamlit/ecommerce/eval product paths.

P13 implementation is active and complete through H8. Use the P13 section below for the final H9 closeout scope.

### P12 Acceptance

- P11 `/analysis` remains available as a single-question product entry.
- P12 `/reports` is separate.
- User can generate a synchronous workspace report from Next.js.
- User can view the report in the UI.
- User can download `report.md`.
- Backend persists `report.json`, `report.md`, `trace.json`, and artifacts under the workspace report directory.
- Backend exposes create/list/detail/download report APIs.
- Report sections preserve P11 SQL validation, SQL execution, evidence validation, visualization, and trace boundaries.
- Report presets do not contain hardcoded SQL, fixed table rules, keyword inference, or deterministic SQL templates.
- Existing semantic-layer files are not silently overwritten.
- P12 opt-in live DeepSeek report acceptance passes.
- Full backend tests, frontend tests, frontend build, tracked artifact audit, and docs audit pass.

### P12 Final Verification Checklist

Latest result: passed on 2026-06-23.

Run these before any future P12 completion claim:

```bash
python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_api.py tests/test_workspace_report_store.py -q
python3 -m pytest tests/test_p12_live_deepseek_workspace_report.py -q
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 \
INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1 \
python3 -m pytest tests/test_p12_live_deepseek_workspace_report.py -q
python3 -m pytest -q
cd frontend && npm test
cd frontend && npm run build
```

Artifact hygiene audit scope:

```text
.env
.venv/
frontend/node_modules/
frontend/.next/
.pytest_cache/
__pycache__/
reports/charts/*
logs/traces/*
workspaces/*/reports/*
eval/report.md
data/action_ops.db
docs/superpowers/plans/*
.superpowers/*
```

Expected result: no generated artifacts from this list are committed. Existing `.gitkeep` files may remain only to preserve empty artifact directories.

## P12 Guardrail

P12 implementation is limited to the scoped report MVP. Do not add PDF/PPT, scheduled reports, async queues, auth/RBAC, deployment, or real SaaS integrations unless explicitly selected later.

## P13 Business Answer And Product UX Plan

P13 turns the current technically working P11/P12 flows into a business-facing product experience. H1-H8 are complete, including real DeepSeek product acceptance for business answer quality and clarification continuation. H9 is the active closeout task for documentation, artifact hygiene, regression, live verification, and final commit.

Design spec: `docs/superpowers/specs/2026-06-24-p13-business-answer-product-ux-design.md`.

Implementation plan: `docs/superpowers/plans/2026-06-24-p13-business-answer-product-ux-implementation-plan.md`.

### P13 Product Direction

Primary product shape:

```text
Analysis Workbench
-> business question
-> integrated question thread
-> optional clarification
-> resolved question
-> guarded SQL/evidence/chart execution
-> business answer
-> evidence and chart
-> report generation
-> collapsed technical details
```

Future-compatible product shape:

```text
Business Q&A Mode
-> chat-style business question
-> same question/evidence/answer/report objects
-> open in workbench for full evidence and technical detail
```

P13 implements the Analysis Workbench, clarification continuation, business-facing answer model, business report reader, Data Settings, and chart image display. Business Q&A Mode is represented in the design and data model for future compatibility, but a full chat product is out of scope for P13.

### P13 Core Requirements

- Add a compact integrated analysis thread that shows original question, model understanding, clarification prompt, user clarification answer, resolved question, and continue/edit controls together.
- Add clarification continuation so users can answer only the missing detail instead of rewriting the full original question.
- Persist and expose the original question, clarification question, clarification answer, and resolved question.
- Make business answers recommendation-first, readable, evidence-backed, and free of raw key-value parameter dumps.
- Collapse SQL, raw execution rows, traces, provider metadata, and validation logs under technical details.
- Redesign report pages so the main report reads like a business report; internal prompts and provider metadata must not appear in the main report body.
- Add Data Settings UI for data sources, profile, semantic layer, product/live model mode, and safety/audit boundaries.
- Fix chart product quality, including Chinese text support, value labels, units, and business annotations.
- Move toward a single product/live mode instead of requiring users to manually enable many provider flags.

### P13 Suggested Task Queue

| Task | Scope | Status |
|---|---|---|
| P13-H1 | Product output model: split question thread, business answer, evidence, charts, report, and technical details instead of one raw result blob | Complete |
| P13-H2 | Clarification continuation: pending run storage, clarification answer API, resolved question generation, and continuation into normal analysis | Complete |
| P13-H3 | Business answer quality: provider insight drafting default in product mode, improved prompt/formatter, no parameter-dump answers | Complete |
| P13-H4 | Analysis Workbench UI: compact integrated analysis thread, business answer first, evidence/chart section, collapsed technical details | Complete |
| P13-H5 | Reports UI polish: business report reader, report progress, Markdown download, technical appendix collapsed | Complete |
| P13-H6 | Data Settings UI: data source, profile, semantic layer, model mode, safety/audit pages | Complete |
| P13-H7 | Chart product quality: Chinese font support, labels, units, annotations, and frontend display polish | Complete |
| P13-H8 | Real DeepSeek product acceptance: answer quality and clarification continuation live tests | Complete |
| P13-H9 | Documentation, artifact audit, frontend/backend regression, final verification | In progress |

### P13-H9 Closeout Checklist

Run and record these before closing P13-H9:

```bash
python3 -m pytest -q
cd frontend && npm test
cd frontend && npm run build
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p13_live_deepseek_product_acceptance.py -q
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p11_live_deepseek_workspace_analysis.py -q
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p12_live_deepseek_workspace_report.py -q
```

H9 artifact hygiene must prove that `.env`, API keys, workspace runs/reports, report chart images, traces, frontend build output, pytest caches, Python caches, and untracked `sample_data/` are not committed. The legacy audit must prove no active Streamlit, old eval, `chart_agent`, `visualization_planner`, or `chart_tool` product path has been restored.

### P13 Out Of Scope

- Full Business Q&A chat product implementation.
- Real SaaS integrations such as Slack, Jira, Power BI, Notion, email, CRM, or ticketing systems.
- Auth/RBAC.
- Deployment.
- PDF/PPT export.
- Scheduled reports.
- Large async job infrastructure beyond lightweight report progress if chosen during implementation.
- Restoring Streamlit, old ecommerce-only demo flows, historical eval product paths, or mock SaaS demos as current product paths.

### P13 Acceptance

- Users can answer a clarification prompt without rewriting the full question.
- The system shows and uses a resolved question before continuing analysis.
- Analysis Workbench shows the compact integrated question thread and keeps the rest of the page readable.
- Business answer appears before SQL/raw rows and contains a recommendation, evidence, next actions, and caveats when relevant.
- Product-facing answers do not pass if they are raw `field=value` or key-value row dumps.
- Reports hide internal section prompts, SQL, trace nodes, provider metadata, and raw rows from the main report body.
- Data Settings clearly exposes data source, profile, semantic layer, model mode, and safety/audit status.
- Charts render Chinese labels correctly and include useful units/value labels.
- Live DeepSeek tests cover question understanding, clarification continuation, SQL planning/candidate, insight drafting, visualization, and readable final answer quality.
- Full backend tests, frontend tests, frontend build, tracked artifact audit, and docs audit pass.
