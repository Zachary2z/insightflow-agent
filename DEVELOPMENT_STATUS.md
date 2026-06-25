# InsightFlow Agent Development Status

Last updated: 2026-06-25

This file is the living status tracker for InsightFlow Agent.

## Status Legend

- `[x]` Done
- `[~]` In progress
- `[ ]` Not started
- `[!]` Blocked or needs decision

## Current Snapshot

| Field | Status |
|---|---|
| Current phase | P13 Business Answer And Product UX complete; prepare P14 product direction planning |
| Current task | No unfinished P13 H-task remains |
| Next planned task | Enter P14 product direction planning |
| Last completed task | P13-H9 documentation, artifact audit, regression, live verification, and closeout |
| Main product target | P13 Analysis Workbench with business-facing answers, integrated clarification continuation, reports UI, Data Settings, chart image display, real DeepSeek product acceptance, and future-compatible Business Q&A Mode |
| Active backend | FastAPI in `api/app.py` |
| Active frontend | Next.js + React + TypeScript in `frontend/` |
| Active analysis entry | P11: `POST /api/workspaces/{workspace_id}/runs`; P12: `POST /api/workspaces/{workspace_id}/reports` |
| Out of scope for P13 | Full chat product implementation, real SaaS integrations, auth/RBAC, deployment, PDF/PPT export, scheduled reports, old demo restoration, and unguarded LLM execution |

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
