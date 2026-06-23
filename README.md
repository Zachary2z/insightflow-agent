# InsightFlow Agent

InsightFlow Agent is a LangGraph-based, multi-agent data analysis product. The current product direction is P11 General Data Analysis Product: user workspaces, imported business data, FastAPI product APIs, a Next.js frontend, live DeepSeek-backed understanding/planning, validated SQL execution, visualization, and traceable results.

The current product path is:

```text
workspace
-> data source import
-> profile
-> semantic draft
-> natural business question
-> DeepSeek/provider-backed question understanding and SQL planning
-> guarded SQL candidate
-> validate_sql() and SQL Reviewer
-> run_sql() against the workspace analysis database
-> Evidence Validator
-> VisualizationAgent
-> chart/artifact plus trace
```

Streamlit, the original ecommerce demo, the old eval runner, and mock Jira/Power BI demos are historical development context only. They are not the current product entry point.

## Current Status

P11 Product Hardening H1-H5 is complete and final verification has passed.

| Hardening task | Status |
|---|---|
| H1 FastAPI CSV/Excel/SQLite source APIs | Complete |
| H2 Next.js API-backed workspace product flow | Complete |
| H3 Remove tracked Streamlit UI, old RunManager, and old `/api/runs` product entry | Complete |
| H4 Natural live DeepSeek workspace acceptance | Complete |
| H5 Clean current product documentation | Complete |

P12 automated report productization has not started.

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

Open the frontend at `http://localhost:3000`, create a workspace, import CSV/Excel/SQLite data, generate a profile, generate a semantic-layer draft, then ask a natural-language analysis question.

## Current Product APIs

Workspace APIs:

```text
POST /api/workspaces
GET  /api/workspaces
GET  /api/workspaces/{workspace_id}
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

Analysis API:

```text
POST /api/workspaces/{workspace_id}/runs
```

The workspace run API calls `workspaces.analysis_runner.run_workspace_analysis()`, which runs `graph.workflow.run_workflow()` against the workspace `analysis.db`. The old non-workspace `/api/runs` route is intentionally removed.

## Live DeepSeek Acceptance

Live provider tests are explicit opt-in. To verify the P11 product path with a real natural business question:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 \
INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1 \
python3 -m pytest tests/test_p11_live_deepseek_workspace_analysis.py -q
```

The acceptance test imports generated workspace CSV data, profiles it, drafts semantic context, asks a natural Chinese business question, requires provider calls for question understanding, SQL planning, guarded SQL candidate generation, and visualization, then verifies SQL review/execution, real row grounding, workspace-rooted chart artifacts, and workspace-rooted trace output.

## Verification

Backend:

```bash
python3 -m pytest tests/test_p11_cleanup_boundaries.py tests/test_project_initialization.py -q
python3 -m pytest -q
```

Frontend:

```bash
cd frontend
npm test
npm run build
```

Tracked artifact hygiene: run the H5 tracked artifact audit from the task instructions. Expected result: no tracked legacy UI/API/eval files, generated frontend build output, generated reports/charts, generated action DBs, or generated trace JSON.

## Current Architecture

Current product layers:

| Layer | Current owner |
|---|---|
| Frontend | `frontend/app` and `frontend/components` |
| Product API | `api/app.py` |
| Workspace store/import/profile/semantic draft | `workspaces/` |
| Runtime workflow | `graph/workflow.py` |
| Provider and structured output | `llm_ops/` |
| Question understanding and clarification | `question_understanding/`, `agents/question_understanding.py`, `agents/clarification_router.py` |
| SQL planning and guarded candidates | `sql_planning/`, `agents/sql_planning_router.py`, `agents/guarded_llm_enhancer.py` |
| SQL safety and execution | `tools/sql_validator.py`, `tools/sql_executor.py`, `agents/sql_reviewer.py` |
| Evidence safety | `tools/evidence_tool.py`, `agents/evidence_validator.py` |
| Visualization | `agents/visualization_agent.py`, `visualization/`, `visualization_delivery/`, `tools/external_visualization_tool.py` |
| Trace and artifacts | `tools/trace_logger.py`, workspace run directories |

The LLM may understand, plan, draft SQL candidates, draft wording, and choose visualization delivery. Deterministic validators and tools still own SQL approval, SQL execution, evidence checks, chart/tool policy checks, approval gates, audit, and trace persistence.

## Historical / Superseded Context

P0-P10 are retained as historical engineering context and low-level safety coverage. They should not be treated as current product entry points.

- Historical / Superseded: `streamlit run app.py`, `eval/run_eval.py`, mock jira demos, `powerbi_publisher_mock`, fixed template behavior, deterministic action template behavior, and chart keyword inference are old demo/eval or cleanup-history terms, not current P11 product guidance.
- Historical retained low-level fixture: `data/ecommerce.db` remains tracked because low-level schema, SQL validator, SQL executor, workflow, report, MCP, and provider regression tests still use it directly. It is not the default product database, not the API default, and not the current quickstart data source.
- Historical generated-output locations such as eval reports, trace JSON, chart PNG/XLSX files, action DBs, frontend build output, and dependency directories must not be committed.

For the detailed phase tracker, see [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) and [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md).
