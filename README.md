# InsightFlow Agent

InsightFlow Agent is a LangGraph-based, multi-agent data analysis product. The current product combines P11 ad hoc workspace analysis, P12 workspace reports, P13 business-facing product UX, and the active P14 product UI shell work:

```text
workspace
-> data source import
-> profile
-> semantic-layer draft
-> P11 natural-language ad hoc analysis
-> P12 structured workspace reports
-> P13 Analysis Workbench, Data Settings, chart display, and product/live acceptance
-> P14 unified Chinese product shell, shared design tokens, and clickable UI reference
-> validated SQL, evidence, visualization, artifacts, and trace output
```

Streamlit, the original ecommerce demo, the old eval runner, and mock Jira/Power BI demos are historical development context only. They are not current product entry points.

## Current Status

P11 General Data Analysis Product is complete. P12 Report Productization is complete through H6 docs, artifact audit, and final verification. P13 Business Answer And Product UX is complete, including P13-H9 documentation, artifact audit, regression, live verification, and final closeout. P14 Product UI Shell And Business Workflow is active; H1 clickable prototype/planning, H2 shared Next.js product shell, H3 data source management redesign, H4 Analysis Workbench redesign, and H5 Report Center redesign are complete, and H6 Data Settings redesign is next.

| Product area | Status | Entry |
|---|---|---|
| P11 ad hoc workspace analysis | Complete | `/workspaces/{workspaceId}/analysis` |
| P12 workspace reports | Complete | `/workspaces/{workspaceId}/reports` |
| P13 Analysis Workbench, Data Settings, and chart display | Complete; H1-H9 closed | `/workspaces/{workspaceId}/analysis`, `/workspaces/{workspaceId}/settings` |
| P14 unified product UI shell | Active; H1-H5 complete, H6 next | `docs/product/prototypes/p14-clickable-product-ui.html` |

## Quickstart

Install backend dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start the FastAPI backend:

```bash
uvicorn api.app:app --reload
```

Start the Next.js frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the frontend at `http://localhost:3000`, create a workspace, import CSV/Excel/SQLite data, generate a profile, generate a semantic-layer draft, then use:

- P11 analysis: `/workspaces/{workspaceId}/analysis`
- P12 reports: `/workspaces/{workspaceId}/reports`
- P13 data settings: `/workspaces/{workspaceId}/settings`

## P13 Product Capabilities

P13 adds business-facing product surfaces on top of the guarded P11/P12 runtime:

- Analysis Workbench with workspace readiness, compact business-question input, integrated analysis thread, business answer, evidence, chart artifacts, and collapsed technical details.
- Clarification continuation: when the workflow asks for missing context, the user can answer only that detail; the system persists the pending run, creates a visible resolved question, and continues through the normal guarded analysis path.
- Business answer quality: product-facing answers are recommendation-first, evidence-backed, and guarded against raw `field=value` or key-value row dumps.
- Business reports: report reader, progress/status summary, Markdown download, and collapsed technical appendix for SQL, provider metadata, trace, and raw rows.
- Data Settings: data sources, profile, semantic layer, product/live model mode, and safety/audit boundaries.
- Chart image display: workspace artifact URLs serve rendered chart images into the frontend, with product metadata such as title, units, value labels, and business annotation.
- Real DeepSeek product acceptance: opt-in live tests cover P13 answer quality, chart artifacts, and clarification continuation, while P11/P12 live tests remain available for regression.

Business Q&A Mode remains future-compatible only. P13 keeps the question/evidence/answer/report/technical-detail objects ready for a future chat surface, but it does not ship a full Business Q&A chat product.

## Current Product APIs

Workspace APIs:

```text
POST /api/workspaces
GET  /api/workspaces
GET  /api/workspaces/{workspace_id}
GET  /api/workspaces/{workspace_id}/settings
```

Data source APIs:

```text
POST /api/workspaces/{workspace_id}/sources/upload
POST /api/workspaces/{workspace_id}/sources/sqlite
GET  /api/workspaces/{workspace_id}/sources
```

Analysis preparation APIs:

```text
POST /api/workspaces/{workspace_id}/profile
POST /api/workspaces/{workspace_id}/semantic-layer/draft
```

P11 ad hoc analysis API:

```text
POST /api/workspaces/{workspace_id}/runs
```

P12 report APIs:

```text
POST /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports/{report_id}
GET  /api/workspaces/{workspace_id}/reports/{report_id}/download
```

P13 artifact display and continuation support:

```text
POST /api/workspaces/{workspace_id}/runs
GET  /api/workspaces/{workspace_id}/artifacts/{relative_path}
```

`POST /api/workspaces/{workspace_id}/runs` accepts either a new `user_question` request or a continuation request with `pending_run_id` and `clarification_answer`.

The workspace run API calls `workspaces.analysis_runner.run_workspace_analysis()`, which runs `graph.workflow.run_workflow()` against the workspace `analysis.db`. The old non-workspace `/api/runs` route is intentionally removed.

## P12 Report Capabilities

Supported report types:

- `business_review`
- `channel_performance`
- `revenue_trend`

The report MVP supports synchronous generation, page display in the Next.js UI, and Markdown download from the report detail page. Report sections reuse the P11-safe analysis path: provider-backed understanding/planning may participate, while SQL validation, SQL review, execution, evidence validation, visualization policy, artifact handling, and trace persistence remain guarded.

Each generated report is stored under the workspace report directory:

```text
workspaces/{workspace_id}/reports/{report_id}/
  report.json
  report.md
  trace.json
  artifacts/
```

`report.json` is the canonical machine-readable record. `report.md` is the downloadable user artifact. `trace.json` records report-level and section-level events. `artifacts/` contains report-facing chart/artifact files copied under the report directory.

## Live DeepSeek Acceptance

Live provider tests are explicit opt-in. To verify the P13 product path with a real DeepSeek-backed provider chain:

```bash
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p13_live_deepseek_product_acceptance.py -q
```

The P13 acceptance test creates a workspace, imports generated business CSV data, profiles it, drafts semantic context, verifies a readable business answer with chart artifacts, then verifies clarification continuation from pending run to resolved question to completed analysis.

To verify the P12 report path:

```bash
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p12_live_deepseek_workspace_report.py -q
```

The acceptance test creates a workspace, imports generated business CSV data, profiles it, drafts semantic context, generates a `business_review` report, requires live provider participation for understanding, SQL planning, guarded SQL candidate generation, and visualization, then verifies reviewed SQL execution, report-local Markdown, report-local chart artifacts, and trace output.

The P11 ad hoc analysis live acceptance remains available:

```bash
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p11_live_deepseek_workspace_analysis.py -q
```

## Verification

Backend:

```bash
python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_api.py tests/test_workspace_report_store.py -q
python3 -m pytest tests/test_p13_live_deepseek_product_acceptance.py -q
python3 -m pytest tests/test_p12_live_deepseek_workspace_report.py -q
python3 -m pytest -q
```

Frontend:

```bash
cd frontend
npm test
npm run build
```

## Generated Artifacts

Generated runtime outputs must not be committed. Keep these paths untracked:

- `.env`
- `.venv/`
- `frontend/node_modules/`
- `frontend/.next/`
- `.pytest_cache/`
- `__pycache__/`
- `reports/charts/*`
- `logs/traces/*`
- `workspaces/*/reports/*`
- `eval/report.md`
- `data/action_ops.db`
- `.superpowers/*`

Tracked `.gitkeep` files may remain only to preserve empty artifact directories.

## Current Architecture

Current product layers:

| Layer | Current owner |
|---|---|
| Frontend | `frontend/app` and `frontend/components` |
| Product API | `api/app.py` |
| Workspace store/import/profile/semantic draft | `workspaces/` |
| P11 runtime workflow | `graph/workflow.py`, `workspaces.analysis_runner` |
| P12 report runner/storage/Markdown | `workspaces.report_runner`, `workspaces.report_store`, `workspaces.report_markdown` |
| Provider and structured output | `llm_ops/` |
| Question understanding and clarification | `question_understanding/`, `agents/question_understanding.py`, `agents/clarification_router.py` |
| SQL planning and guarded candidates | `sql_planning/`, `agents/sql_planning_router.py`, `agents/guarded_llm_enhancer.py` |
| SQL safety and execution | `tools/sql_validator.py`, `tools/sql_executor.py`, `agents/sql_reviewer.py` |
| Evidence safety | `tools/evidence_tool.py`, `agents/evidence_validator.py` |
| Visualization | `agents/visualization_agent.py`, `visualization/`, `visualization_delivery/`, `tools/external_visualization_tool.py` |
| Trace and artifacts | `tools/trace_logger.py`, workspace run directories, workspace report directories |

The LLM may understand, plan, draft SQL candidates, draft wording, and choose visualization delivery. Deterministic validators and tools still own SQL approval, SQL execution, evidence checks, chart/tool policy checks, approval gates, audit, and trace persistence.

## Historical / Superseded Context

P0-P10 are retained as historical engineering context and low-level safety coverage. They should not be treated as current product entry points.

- Historical / Superseded: `streamlit run app.py`, `eval/run_eval.py`, mock jira demos, `powerbi_publisher_mock`, fixed template behavior, deterministic action template behavior, and chart keyword inference are old demo/eval or cleanup-history terms, not current P11/P12/P13 product guidance.
- Historical retained low-level fixture: `data/ecommerce.db` remains tracked because low-level schema, SQL validator, SQL executor, workflow, report, MCP, and provider regression tests still use it directly. It is not the default product database, not the API default, and not the current quickstart data source.
- Historical generated-output locations such as eval reports, trace JSON, chart PNG/XLSX files, action DBs, frontend build output, and dependency directories must not be committed.

For the detailed phase tracker, see [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) and [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md).
