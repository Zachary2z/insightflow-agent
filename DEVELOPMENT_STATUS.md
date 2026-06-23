# InsightFlow Agent Development Status

Last updated: 2026-06-23

This file is the living status tracker for InsightFlow Agent.

## Status Legend

- `[x]` Done
- `[~]` In progress
- `[ ]` Not started
- `[!]` Blocked or needs decision

## Current Snapshot

| Field | Status |
|---|---|
| Current phase | P12 - Report Productization planning |
| Current task | P12 design/spec documented; implementation not started |
| Next planned task | Review P12 design, then create an implementation plan before code changes |
| Last completed task | H5 current product documentation cleanup |
| Main product target | P11 ad hoc workspace analysis remains available; P12 target is synchronous workspace reports with page display and Markdown download |
| Active backend | FastAPI in `api/app.py` |
| Active frontend | Next.js + React + TypeScript in `frontend/` |
| Active analysis entry | P11: `POST /api/workspaces/{workspace_id}/runs`; P12 planned: `POST /api/workspaces/{workspace_id}/reports` |
| Out of scope for P12 MVP | PDF/PPT export, async queues, scheduled reports, email delivery, real SaaS integrations, auth/RBAC, deployment, old demo restoration, and unguarded LLM execution |

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
| P12 | Report Productization | `[~]` Planned; implementation not started |

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

## Final Verification Plan

Latest result: passed on 2026-06-23.

Required H5/P11 commands:

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

Required audits:

- Documentation audit: every remaining old-term hit must be in an explicit Historical, Superseded, legacy, or retained low-level fixture context.
- Tracked artifact audit: no tracked old UI/API/eval files, generated frontend build output, generated report/chart artifacts, or generated trace JSON.

## Historical / Superseded Notes

The following terms are intentionally retained only in historical notes or fixture notes:

- Historical / Superseded: `streamlit run app.py`, `eval/run_eval.py`, mock jira demos, `powerbi_publisher_mock`, fixed template behavior, deterministic action template behavior, and chart keyword inference are old demo/eval or cleanup-history terms, not current product instructions.
- Historical retained low-level fixture: `data/ecommerce.db` remains tracked because low-level tests directly use it for schema, SQL validation, SQL execution, workflow, report, MCP, and provider regression coverage. It is not the current product database and is not used by the workspace API as a default.

## Update Rules

After future verification:

1. Keep P12 implementation tasks marked `[ ] Not started` until implementation begins.
2. Record exact verification results in this file or in the final task response.

## P12 Planning Snapshot

Design spec: `docs/superpowers/specs/2026-06-23-p12-workspace-report-productization-design.md`.

MVP decisions:

- Page display plus Markdown download.
- Synchronous generation first.
- Async generation is deferred.
- First report types: `business_review`, `channel_performance`, `revenue_trend`.
- P11 single-question analysis remains separate at `/workspaces/{workspace_id}/analysis`.
- P12 reports live at `/workspaces/{workspace_id}/reports`.

Planned backend APIs:

```text
POST /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports/{report_id}
GET  /api/workspaces/{workspace_id}/reports/{report_id}/download
```

Planned task queue:

| Task | Scope | Status |
|---|---|---|
| P12-H1 | Report domain model, storage layout, Markdown renderer; no provider calls yet | `[ ]` Not started |
| P12-H2 | Synchronous workspace report runner; report presets produce section purposes/questions, not SQL templates or keyword rule trees | `[ ]` Not started |
| P12-H3 | FastAPI report APIs | `[ ]` Not started |
| P12-H4 | Next.js reports UI and Markdown download | `[ ]` Not started |
| P12-H5 | Live DeepSeek workspace report acceptance | `[ ]` Not started |
| P12-H6 | Docs, artifact audit, final verification | `[ ]` Not started |

P12 MVP excludes PDF/PPT export, async queues, scheduled reports, email delivery, real SaaS integrations, auth/RBAC, deployment, hardcoded SQL templates, keyword-heavy report rule trees, silent semantic-layer overwrites, and any restoration of historical Streamlit/ecommerce/eval product paths.
