# InsightFlow Agent Development Status

Last updated: 2026-06-29

This file is the living status tracker for InsightFlow Agent.

## Status Legend

- `[x]` Done
- `[~]` In progress
- `[ ]` Not started
- `[!]` Blocked or needs decision

## Current Snapshot

| Field | Status |
|---|---|
| Current phase | P15 Analysis Reliability And History |
| Current task | P15-H2 Analysis Workbench history panel complete |
| Next planned task | P15-H3 Run detail uses backend source of truth |
| Last completed task | P15-H2 Analysis Workbench History Panel |
| Main product target | Coherent Chinese business data-analysis product with persisted analysis history, recoverable run details, schema-aware SQL recovery, 数据源管理, 分析工作台, 报告中心, 数据设置, and future-compatible 业务问答 preview |
| Active backend | FastAPI in `api/app.py` |
| Active frontend | Next.js + React + TypeScript in `frontend/` |
| Active analysis entry | P11: `POST /api/workspaces/{workspace_id}/runs`; P12: `POST /api/workspaces/{workspace_id}/reports` |
| Out of scope for P15 | Full Business Q&A chat backend, real SaaS integrations, auth/RBAC, deployment, vector databases, PDF/PPT export, scheduled reports, fixed SQL templates, keyword-heavy business rules, old demo restoration, and unguarded LLM execution |

## Phase Overview

| Phase | Goal | Overall |
|---|---|---|
| P0 | Agentic SQL Core | `[x]` Historical foundation complete |
| P1 | Reliable Analysis & Report Core | `[x]` Historical foundation complete |
| P2 | Business Review & Action Workflow | `[x]` Historical foundation complete |
| P3 | MCP & Engineering Core | `[x]` Scoped baseline complete |
| P4 | Realistic Scenario Dataset | `[x]` Complete |
| P5 | Lightweight Semantic Layer | `[x]` Complete |
| P6 | Scenario Analysis Planner | `[x]` Complete |
| P7 | Visualization Intelligence | `[x]` Complete |
| P8.1 | Visualization Agent Dedupe & External Tool Calling | `[x]` Complete |
| P8.2 | Intent & SQL Planning Agent Cleanup | `[x]` Complete |
| P8.3 | Report & Insight Agent Cleanup | `[x]` Complete |
| P8.4 | Action Agent & Tool Adapter Cleanup | `[x]` Complete |
| P8.5 | Agent Pipeline UX | `[x]` Complete, now superseded as a UI direction by P11 Next.js |
| P9 | Realistic Eval And Demo Polish | `[x]` Historical eval/demo polish complete |
| P10 | MCP Contract & Lightweight Engineering Hardening | `[x]` Complete |
| P11 | General Data Analysis Product | `[x]` H1-H5 complete; final verification passed |
| P12 | Report Productization | `[x]` Complete; H1 foundation, H2 synchronous runner, H3 FastAPI APIs, H4 Next.js reports UI, H5 live DeepSeek report acceptance, and H6 docs/artifact audit/final verification complete |
| P13 | Business Answer And Product UX | `[x]` Complete; H1-H9 closed with documentation, artifact audit, regression, live verification, and closeout |
| P14 | Product UI Shell And Business Workflow | `[x]` H1-H8 complete; full regression/live acceptance/docs closeout passed |
| P15 | Analysis Reliability And History | `[~]` H1 backend run history APIs complete; H2 Analysis Workbench history panel complete; H3 run detail backend source of truth next |

## P11 Product Hardening

Audit date: 2026-06-23

P11 makes InsightFlow a general workspace data-analysis product:

```text
workspace
-> data source import
-> profile
-> semantic draft
-> natural business question
-> DeepSeek/provider-backed understanding and planning
-> guarded SQL candidate
-> validated SQL execution
-> evidence
-> visualization/artifact
-> trace
```

### Hardening Task Checklist

| Task | Scope | Status | Verification |
|---|---|---|---|
| H1 | Add workspace CSV/Excel upload, SQLite import, and source listing FastAPI endpoints | `[x]` Complete | `tests/test_workspace_api.py`, `tests/test_workspace_importers.py` |
| H2 | Wire Next.js pages into API-backed workspace list/create, data source, profile, semantic draft, analysis, and run-result flows | `[x]` Complete | `cd frontend && npm test && npm run build` |
| H3 | Remove tracked Streamlit UI, old RunManager, old non-workspace run API, and legacy async run tests | `[x]` Complete | `tests/test_p11_cleanup_boundaries.py`, `tests/test_project_initialization.py` |
| H4 | Strengthen P11 live DeepSeek acceptance with a natural business question and workspace-rooted artifact assertions | `[x]` Complete | `tests/test_p11_live_deepseek_workspace_analysis.py` with live flags |
| H5 | Clean current product documentation so historical demo/eval/mock paths are not current guidance | `[x]` Complete | H5 documentation audit plus final verification |

### Remaining P11 Work

No H1-H5 implementation or verification work remains.

## Final Verification Summary

Latest P15-H2 result: passed on 2026-06-29.

P15-H2 verification result summary:

- Focused Analysis Workbench history tests passed: `cd frontend && npm test -- workspace-flow.test.tsx` with `40 passed`.
- Full frontend test suite passed: `cd frontend && npm test` with `50 passed`.
- Frontend production build passed: `cd frontend && npm run build`, including `/workspaces/[workspaceId]/analysis`.
- P15-H1 backend run history API regression passed: `python3 -m pytest tests/test_workspace_run_history_api.py -q` with `7 passed`.
- Analysis Workbench now loads persisted run history from the backend run history API, shows completed, failed, waiting-for-clarification, and running status labels in Chinese, keeps failed runs visible, and restores a selected run through `getWorkspaceRun()`.
- History refreshes after new analysis, clarification continuation, and follow-up analysis. `sessionStorage` remains only as the existing optional run-detail cache, not as the history source.

Latest P14-H8 result: passed on 2026-06-29.

P14-H8 verification result summary:

- Full frontend test suite passed: `cd frontend && npm test` with `46 passed`.
- Frontend production build passed: `cd frontend && npm run build`, including `/workspaces`, `/workspaces/new`, `/workspaces/[workspaceId]/profile`, `/semantic-layer`, `/runs/[runId]`, `/business-qa`, `/analysis`, `/reports`, and `/settings`.
- Full backend suite passed: `python3 -m pytest` with `289 passed, 12 skipped`.
- Real DeepSeek live acceptance passed with `.env`, `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1`, and `INSIGHTFLOW_PRODUCT_LIVE_MODE=1`: `5 passed` across P11 workspace analysis, P12 workspace report, and P13 product acceptance.
- Post-H8 audit fixed remaining route-level product drift: home/workspace entry pages, field profile, semantic-layer draft, and run detail now use Chinese product chrome and tests.
- Post-H8 live/provider hardening fixed real DeepSeek output normalization for multi-metric intent fields, null/object list fields, clarification-router no-clarification decisions, and evidence anchoring for business answers.
- Clarification continuation now merges original question and user clarification answer without injecting the clarification prompt options into the resolved analysis question.
- P14 final product state is 数据源管理, 分析工作台, 报告中心, 数据设置, and 业务问答 preview.
- Business Q&A remains a preview route that reuses the existing workspace analysis API and product result objects; it is not a complete chat product and no backend chat endpoint was added.
- Real SaaS integrations, auth/RBAC, deployment, vector databases, PDF/PPT export, scheduled reports, and full Business Q&A chat remain outside P14 scope.
- Artifact hygiene and legacy path audit were run as H8 closeout checks; generated outputs must remain untracked and old Streamlit/eval/chart-agent product paths must remain absent.

Latest P14-H7 result: passed on 2026-06-29.

P14-H7 verification result summary:

- Focused Business Q&A preview frontend tests passed: `frontend/tests/product-shell.test.tsx` and `frontend/tests/workspace-flow.test.tsx` with `33 passed`.
- Full frontend test suite passed: `41 passed`.
- Frontend production build passed and included `/workspaces/[workspaceId]/business-qa`.
- Backend analysis/clarification regressions plus P14 Business Q&A endpoint boundary test passed: `8 passed`.
- Business Q&A navigation now points to `/workspaces/{workspaceId}/business-qa` and marks `业务问答` active on the preview route.
- Business Q&A preview page is clearly labeled `未来模式预览`, reuses the existing `runAnalysis` / `/api/workspaces/{workspace_id}/runs` concept for one-round preview answers, and does not add a backend chat endpoint.
- The preview answer area reuses existing product result objects through `RunResult`; SQL, raw rows, and provider metadata remain inside collapsed `技术详情`.
- Legacy path audit hits remained historical documentation or existing mock-boundary tests; no Streamlit, old eval UI, old `chart_agent`, `visualization_planner`, or `chart_tool` product path was restored.
- Tracked generated-artifact audit produced no output for `.env`, `frontend/.next`, `frontend/node_modules`, workspace run/report directories, report chart/markdown outputs, trace JSON, or `sample_data/`.

Latest P14-H6 result: passed on 2026-06-29.

P14-H6 verification result summary:

- Focused data-settings frontend tests passed: `frontend/tests/workspace-flow.test.tsx` with `29 passed`.
- Data Settings now uses the shared P14 ProductShell route with active `数据设置` navigation and a Chinese `数据设置` page title.
- Data Settings now presents `数据准备总览`, `数据源`, `字段画像`, `语义层`, `真实模型模式`, and `安全与审计` as business-facing ProductCard sections.
- Empty data sources, missing field profile, missing semantic layer, provider features, SQL review, sensitive-field blocking, Trace, and technical-details policy now render with Chinese product copy.
- Technical audit detail remains collapsed by default; provider metadata, raw config, SQL/raw-row policy detail, and trace-oriented configuration are only rendered after expanding `技术详情`.

Latest P14-H5 result: passed on 2026-06-29.

P14-H5 verification result summary:

- Focused report-center frontend tests passed: `frontend/tests/workspace-flow.test.tsx` with `28 passed`.
- Product shell plus workspace flow frontend regression passed: `29 passed`.
- Full frontend test suite passed: `37 passed`.
- Frontend production build passed and included `/workspaces/[workspaceId]/reports` plus `/workspaces/[workspaceId]/reports/[reportId]`.
- Report backend regressions passed: `28 passed` across `tests/test_workspace_report_api.py`, `tests/test_workspace_report_runner.py`, and `tests/test_workspace_report_store.py`.
- Report UI now uses the shared P14 ProductShell, Chinese report-center copy, Chinese empty/status/type labels, business-facing generation examples, visible Markdown download, and collapsed technical appendix for paths, trace, SQL, provider metadata, and raw JSON details.

Latest P13-H9 result: passed on 2026-06-25.

P13-H9 verification result summary:

- Full backend suite passed: `279 passed, 12 skipped`.
- Frontend tests passed: `33 passed`.
- Frontend production build passed: Next.js compiled successfully and generated all workspace app routes, including analysis, reports, run detail, and settings.
- Live DeepSeek P13 product acceptance passed: `3 passed`, covering readable business answer quality, chart artifact URL output, clarification continuation, resolved question, and deterministic product/live no-key fallback.
- Live DeepSeek P11 workspace analysis regression passed: `1 passed`.
- Live DeepSeek P12 workspace report regression passed: `1 passed`.
- H9 live verification exposed a continuation routing regression where provider-backed clarification or SQL planning could ask for more context after a resolved question; fixed by routing continuation contexts into the guarded SQL path and added `tests/test_clarification_routing.py`.
- Legacy path audit command completed. Hits were historical/audit documentation, mock boundary tests for `powerbi_publisher_mock`, and cleanup-boundary assertions that `chart_tool.py` remains absent; no active Streamlit, old eval, `chart_agent`, `visualization_planner`, or `chart_tool` product path was restored.
- Artifact hygiene audit completed. The required broad tracked-file regex produced only false positives for `.env.example` and frontend route source paths containing `/reports/`; a stricter tracked generated-artifact check produced no output. `.env`, API keys, workspace runs/reports, report chart images, traces, `frontend/.next`, `.pytest_cache`, `__pycache__`, and untracked `sample_data/` are not tracked.

Latest P13-H8 result: passed on 2026-06-24.

P13-H8 verification result summary:

- Real DeepSeek P13 product acceptance passed for a business analysis question with provider-backed understanding, SQL planning, guarded SQL candidate generation, insight drafting, visualization, readable business answer, evidence preview, chart artifact URL, and technical SQL details.
- Real DeepSeek P13 clarification continuation passed: the first run stopped for clarification, persisted a pending run, accepted a short user clarification answer, generated a visible resolved question, and completed the guarded product flow.
- Product/live mode fallback without an API key continued to support the deterministic SQL path.

Latest P13-H7 result: passed on 2026-06-24.

P13-H7 verification result summary:

- Chart/backend focused tests passed: `25 passed`.
- Frontend chart/workspace API tests passed: `33 passed`.
- Frontend production build passed: Next.js compiled successfully and generated all app routes.
- Suggested report/analysis regressions passed: `27 passed`.

Latest P13-H6 result: passed on 2026-06-24.

Required P12-H6 commands:

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

Final verification result summary:

- P13-H6 backend settings API tests passed: `3 passed`.
- P13-H6 frontend settings/client tests passed: `31 passed`.
- P13-H6 frontend production build passed: Next.js compiled successfully and generated the `/workspaces/[workspaceId]/settings` route.
- Suggested report/analysis regressions passed: `27 passed`.
- Targeted P12 backend report tests passed: `28 passed`.
- Non-live P12 DeepSeek acceptance command passed by opt-in skip when `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS` is unset: `1 skipped`.
- Live DeepSeek P12 report acceptance passed with provider flags enabled: `1 passed`, with expected matplotlib CJK glyph warnings.
- Full backend pytest suite passed: `246 passed, 10 skipped`, with matplotlib CJK glyph warnings.
- Frontend unit tests passed: `19 passed`.
- Frontend production build passed: Next.js compiled successfully and generated all app routes.

Required audits completed:

- Documentation audit: every remaining old-term hit must be in an explicit Historical, Superseded, legacy, or retained low-level fixture context.
- Tracked artifact audit: no tracked old UI/API/eval files, generated frontend build output, generated report/chart artifacts, or generated trace JSON.
- Artifact hygiene audit: `.env`, `.venv/`, `frontend/node_modules/`, `frontend/.next/`, `.pytest_cache/`, `__pycache__/`, `reports/charts/*`, `logs/traces/*`, `workspaces/*/reports/*`, `eval/report.md`, `data/action_ops.db`, and `.superpowers/*` are ignored or untracked. Only intentional `.gitkeep` placeholders remain tracked for empty artifact directories.
- Legacy path audit command run: `rg -n "chart_agent|visualization_planner|chart_tool|old|legacy|TODO|deprecated|fixed template|deterministic action template|keyword inference"`. Hits were Historical/Superseded docs, cleanup-boundary tests, or false positives such as `old_price`, `threshold`, `stakeholder`, and `placeholder`; no active legacy chart/Streamlit/eval path was restored.

## Historical / Superseded Notes

The following terms are intentionally retained only in historical notes or fixture notes:

- Historical / Superseded: `streamlit run app.py`, `eval/run_eval.py`, mock jira demos, `powerbi_publisher_mock`, fixed template behavior, deterministic action template behavior, and chart keyword inference are old demo/eval or cleanup-history terms, not current product instructions.
- Historical retained low-level fixture: `data/ecommerce.db` remains tracked because low-level tests directly use it for schema, SQL validation, SQL execution, workflow, report, MCP, and provider regression coverage. It is not the current product database and is not used by the workspace API as a default.

## Update Rules

After future verification:

1. Keep P13 marked complete unless a new scoped P13 follow-up is explicitly opened.
2. Record exact verification results in this file or in the final task response.

## P14 Planning Snapshot

Clickable UI reference: `docs/product/prototypes/p14-clickable-product-ui.html`.

Implementation plan: `docs/product/plans/2026-06-29-p14-product-ui-shell-and-business-workflow.md`.

P14 selected product direction:

```text
workspace
-> 数据源管理
-> 分析工作台
-> 报告中心
-> 数据设置
-> 业务问答 preview
```

Key P14 decisions:

- P14 is a product UI and workflow hardening phase, not a backend-agent rewrite.
- The tracked clickable HTML prototype is the visual reference for Next.js implementation.
- Navigation should be a shared horizontal product shell, not per-page link strips.
- The primary UI should be Chinese and business-facing.
- Data source management should replace the old English `Datasets` page feel.
- Business Q&A is a preview route for future compatibility, not a completed chat product.
- Guarded SQL, evidence validation, report generation, artifact handling, trace boundaries, and live DeepSeek acceptance must remain intact.

Suggested P14 task queue:

| Task | Scope | Status |
|---|---|---|
| P14-H1 | Clickable product UI prototype and full implementation plan | `[x]` Complete |
| P14-H2 | Shared Next.js product shell, design tokens, horizontal nav, and route wrappers | `[x]` Complete |
| P14-H3 | Data source management redesign: `/datasets` becomes 数据源管理 | `[x]` Complete |
| P14-H4 | Analysis Workbench redesign to match prototype while preserving clarification continuation | `[x]` Complete |
| P14-H5 | Report Center redesign with collapsed technical appendix | `[x]` Complete |
| P14-H6 | Data Settings redesign: data source, field profile, semantic layer, model mode, safety/audit | `[x]` Complete |
| P14-H7 | Business Q&A preview route with no new backend chat endpoint | `[x]` Complete |
| P14-H8 | Full regression, real DeepSeek live acceptance, docs closeout, artifact audit | `[x]` Complete |

## P13 Planning Snapshot

Design spec: `docs/superpowers/specs/2026-06-24-p13-business-answer-product-ux-design.md`.

Implementation plan: `docs/superpowers/plans/2026-06-24-p13-business-answer-product-ux-implementation-plan.md`.

P13 selected product direction:

```text
Analysis Workbench
-> compact integrated question thread
-> clarification continuation
-> resolved question
-> guarded SQL/evidence/chart execution
-> business answer
-> report generation
-> collapsed technical details
```

Future-compatible direction:

```text
Business Q&A Mode
-> chat-style surface that reuses the same question/evidence/answer/report/progress objects
```

Key P13 decisions:

- Analysis Workbench is the implementation target.
- Business Q&A Mode is designed for future compatibility but is not a full P13 implementation target.
- Clarification is a normal product state, not an error.
- Users should answer only the missing detail; they should not rewrite the full question.
- The system must combine the original question, system understanding, clarification answer, and workspace context into a visible `resolved_question`.
- Business answers must be recommendation-first, readable, evidence-backed, and not raw parameter dumps.
- SQL, raw rows, trace, provider metadata, and validation logs stay available but collapsed under technical details.
- Reports must read like business reports; internal prompts and provider metadata do not belong in the main report body.
- Data Settings should cover data sources, profile, semantic layer, product/live model mode, and safety/audit boundaries.

Suggested P13 task queue:

| Task | Scope | Status |
|---|---|---|
| P13-H1 | Product output model: question thread, business answer, evidence, charts, report, technical details | `[x]` Complete |
| P13-H2 | Clarification continuation: pending run, clarification answer, resolved question, continue analysis | `[x]` Complete |
| P13-H3 | Business answer quality and product/live provider mode | `[x]` Complete |
| P13-H4 | Analysis Workbench UI with compact integrated question thread | `[x]` Complete |
| P13-H5 | Reports UI polish and collapsed technical appendix | `[x]` Complete |
| P13-H6 | Data Settings UI | `[x]` Complete |
| P13-H7 | Chart product quality and Chinese text support | `[x]` Complete |
| P13-H8 | Real DeepSeek product acceptance for answer quality and clarification continuation | `[x]` Complete |
| P13-H9 | Docs, artifact audit, regression, final verification | `[x]` Complete |

## P12 Planning Snapshot

Design spec: `docs/superpowers/specs/2026-06-23-p12-workspace-report-productization-design.md`.

MVP decisions:

- Page display plus Markdown download.
- Synchronous generation first.
- Async generation is deferred.
- First report types: `business_review`, `channel_performance`, `revenue_trend`.
- P11 single-question analysis remains separate at `/workspaces/{workspace_id}/analysis`.
- P12 reports live at `/workspaces/{workspace_id}/reports`.

Backend report APIs:

```text
POST /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports/{report_id}
GET  /api/workspaces/{workspace_id}/reports/{report_id}/download
```

Completed task queue:

| Task | Scope | Status |
|---|---|---|
| P12-H1 | Report domain model, storage layout, Markdown renderer; no provider calls yet | `[x]` Complete |
| P12-H2 | Synchronous workspace report runner; report presets produce section purposes/questions, not SQL templates or keyword rule trees | `[x]` Complete |
| P12-H3 | FastAPI report APIs | `[x]` Complete |
| P12-H4 | Next.js reports UI and Markdown download | `[x]` Complete |
| P12-H5 | Live DeepSeek workspace report acceptance | `[x]` Complete |
| P12-H6 | Docs, artifact audit, final verification | `[x]` Complete |

P12 MVP excludes PDF/PPT export, async queues, scheduled reports, email delivery, real SaaS integrations, auth/RBAC, deployment, hardcoded SQL templates, keyword-heavy report rule trees, silent semantic-layer overwrites, and any restoration of historical Streamlit/ecommerce/eval product paths.

## P15 Planning Snapshot

Implementation plan: `docs/product/plans/2026-06-29-p15-analysis-reliability-and-history.md`.

P15 selected product direction:

```text
Analysis Workbench
-> ask a business question
-> persist each workspace run
-> show analysis history after navigation or refresh
-> restore previous question thread, answer, evidence, charts, and technical details
-> repair schema-mismatch SQL once when reviewer detects unknown tables or columns
-> show business-friendly failure when repair cannot safely complete
```

Key P15 decisions:

- Workspace run files are the source of truth for analysis history.
- `sessionStorage` must not be the product source of truth for run restoration.
- Backend should expose run list/detail APIs instead of making the frontend infer history from local state.
- Analysis history must include completed, failed, and waiting-for-clarification runs.
- SQL schema repair is allowed exactly once and must still pass SQL Reviewer before execution.
- Do not add fixed SQL templates, keyword-heavy rule trees, or ecommerce-specific fallback logic.
- Main UI must explain failures in Chinese business language; raw reviewer details stay collapsed under technical details.
- Real DeepSeek regression should cover the observed `给我一下最近30天几个渠道的数据` plus `都看` scenario.

Suggested P15 task queue:

| Task | Scope | Status |
|---|---|---|
| P15-H1 | Backend run history APIs: list workspace runs and load run detail from persisted run files | `[x]` Complete |
| P15-H2 | Analysis Workbench history panel: previous questions, statuses, summaries, restore selected run | `[x]` Complete |
| P15-H3 | Run detail source-of-truth cleanup: backend detail API over `sessionStorage` | `[ ]` Not started |
| P15-H4 | One-pass schema-mismatch SQL repair after SQL Reviewer unknown table/column failure | `[ ]` Not started |
| P15-H5 | Business-friendly failure UX for unrepaired SQL review failures | `[ ]` Not started |
| P15-H6 | Real DeepSeek regression for channel data + `都看`, plus history persistence | `[ ]` Not started |

P15 out of scope: full Business Q&A chat backend, real SaaS integrations, auth/RBAC, deployment, PDF/PPT export, scheduled reports, vector databases, fixed SQL templates, keyword-heavy business rules, and any restoration of old Streamlit/eval/chart-agent paths.
