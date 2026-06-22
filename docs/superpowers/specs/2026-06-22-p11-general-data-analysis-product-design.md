# P11 General Data Analysis Product Design

Date: 2026-06-22

## Decision

P11 turns InsightFlow from an ecommerce demo-oriented BI workflow into a general data analysis product.

The product direction is:

```text
User data
-> workspace import
-> data profiling
-> semantic layer draft and review
-> DeepSeek-backed analysis
-> validated SQL execution
-> real charts, results, explanations, and traces
```

P11 prioritizes CSV, Excel, and SQLite data sources. P12 can productize recurring BI reports. P13 can productize real action delivery to Jira, Slack, email, or similar systems.

## Product Goal

Users should be able to bring their own tabular business data and ask natural-language analysis questions without being locked into the built-in ecommerce database.

The first product experience should be:

1. Create or select a workspace.
2. Upload CSV or Excel files, or connect an existing SQLite file.
3. Import the data into a workspace SQLite analysis database.
4. Inspect automatically generated table and column profiles.
5. Review and edit a semantic layer draft.
6. Ask a natural-language question.
7. See the agent plan, generated SQL, validation result, real query output, chart, explanation, and trace.

This is the main P11 product path. The current ecommerce demo should no longer be the main experience.

## Non-Goals

P11 will not build:

- Real Jira, Slack, email, Power BI, or SaaS integrations.
- Recurring weekly or monthly business review automation.
- RBAC, multi-user permissions, or enterprise auth.
- Docker, CI, or cloud deployment unless separately selected.
- Vector database or document RAG.
- A complex ETL or data-cleaning platform.
- Automatic mutation of user source data.
- A final report automation product.
- A final action execution product.

## Hard Cleanup Rule

P11 must delete product-path code and tests that conflict with the general data analysis product.

Do not preserve old behavior for historical compatibility when it is no longer part of the product.

Delete or replace:

- Fixed ecommerce demo routes as the primary product path.
- Fixed ecommerce question/template acceptance tests that only prove old demo behavior.
- Business keyword trees that compete with provider-backed analysis decisions.
- Old mock-driven product acceptance tests.
- Mock Power BI, mock Jira, and local action delivery tests when they are only proving the old main demo path.
- Streamlit product-entry tests if Streamlit is no longer the primary frontend.
- Compatibility wrappers for deleted agent paths.

Keep only what is still useful as a real product boundary:

- SQL validation.
- SQL execution.
- Evidence validation.
- Chart validation.
- Prompt/version tracking.
- Provider structured-output validation.
- Trace and artifact hygiene.
- Workspace import, profiling, semantic layer, and analysis tests.

Mock tests are allowed only for small deterministic units where a real provider call would add no confidence. Mock tests must not be used as product acceptance for P11.

## Frontend Direction

P11 uses Next.js with React and TypeScript as the primary product frontend.

Streamlit becomes a temporary developer/debug surface and may be removed later.

Recommended frontend stack:

- Next.js App Router.
- React + TypeScript.
- ECharts for charts.
- TanStack Table for data previews and result tables.
- FastAPI polling for long-running run status in P11.
- SSE or WebSocket can be added later if needed.

Primary frontend routes:

```text
/workspaces
/workspaces/new
/workspaces/[workspaceId]/datasets
/workspaces/[workspaceId]/profile
/workspaces/[workspaceId]/semantic-layer
/workspaces/[workspaceId]/analysis
/workspaces/[workspaceId]/runs/[runId]
```

## Backend Direction

The existing Python backend remains the agent and tool execution layer.

FastAPI should become the product API layer for:

- Workspace CRUD.
- File upload.
- SQLite source registration.
- Import status.
- Data profiling.
- Semantic layer draft generation.
- Semantic layer review and save.
- Analysis run submission.
- Run status polling.
- Run result retrieval.
- Trace and artifact retrieval.

The LangGraph workflow should become workspace-aware instead of being tied to `data/ecommerce.db`.

## Workspace Model

Each workspace owns its imported data, metadata, semantic layer, runs, and artifacts.

Directory shape:

```text
workspaces/
  {workspace_id}/
    workspace.json
    raw/
      uploaded_files/
    analysis.db
    profile.json
    semantic_layer.yaml
    runs/
      {run_id}/
        trace.json
        result.json
        charts/
        reports/
```

`workspace.json` contains:

- Workspace id.
- Name.
- Created timestamp.
- Data source list.
- Active database path.
- Active profile path.
- Active semantic layer path.

Generated workspace artifacts must be ignored by git.

## Data Sources

P11 supports:

1. CSV upload.
2. Excel upload with one or more sheets.
3. SQLite database connection or import.

All sources are normalized into the workspace `analysis.db`.

CSV and Excel import rules:

- Infer table names from file and sheet names.
- Sanitize table and column names.
- Preserve original names in metadata.
- Infer basic column types.
- Store raw uploaded files under `raw/uploaded_files`.
- Never mutate raw source files.

SQLite import rules:

- Either copy the SQLite file into the workspace or register a read-only connection path.
- Extract table schemas and row counts.
- Use the same profiling and semantic layer pipeline as imported CSV and Excel data.

## Data Profiling

The profiler creates `profile.json`.

It should include:

- Tables.
- Row counts.
- Column names.
- Original column names.
- Inferred SQL types.
- Null counts and null rates.
- Distinct counts.
- Example values.
- Numeric min, max, mean where applicable.
- Date/time min and max where applicable.
- Candidate id columns.
- Candidate time columns.
- Candidate measure columns.
- Candidate categorical dimensions.
- Candidate foreign-key relationships.

The profile is product context for the LLM. It is not a final business truth.

## Semantic Layer Draft

P11 introduces a workspace semantic layer draft generated from profile data.

The draft should include:

- Metrics.
- Dimensions.
- Entities.
- Time fields.
- Candidate join paths.
- Business descriptions.
- Disabled or uncertain items.

Users can review and edit:

- Metric names.
- Metric formulas.
- Primary time fields.
- Dimension labels.
- Table and field descriptions.
- Which suggested items are enabled.

The semantic layer becomes the main analysis context for the agent.

## Analysis Runtime

The analysis workflow receives:

```text
workspace_id
database_path
profile_path
semantic_layer_path
user_question
provider configuration
```

The runtime flow:

```text
Question Understanding
-> Analysis Planning
-> Schema and Semantic Context
-> SQL Planning
-> Guarded SQL Candidate
-> SQL Validation
-> SQL Execution
-> Evidence Validation
-> Visualization Agent
-> Result Explanation
-> Trace Save
```

DeepSeek should be the real product analysis path when configured.

Deterministic tools remain responsible for:

- SQL safety approval.
- SQL execution.
- Evidence validation.
- Chart column validation.
- Artifact writing.
- Trace writing.

The model must not execute SQL, bypass validators, fabricate rows, or create unsupported claims.

## Product Tests

P11 tests should represent the future product, not old demos.

Required tests:

- CSV import creates a workspace `analysis.db`.
- Excel multi-sheet import creates multiple tables.
- SQLite import or connection is profiled.
- Profiling identifies likely time, measure, id, and dimension fields.
- Semantic layer draft is generated from profile data.
- User semantic edits are saved and used by analysis.
- Workflow runs against a workspace database instead of `data/ecommerce.db`.
- Generated SQL validates against the workspace schema.
- Query execution returns real rows from workspace data.
- Visualization uses real execution columns.
- Artifact paths stay inside the workspace run directory.
- Next.js upload/profile/semantic/analysis pages can call FastAPI endpoints.
- Live DeepSeek acceptance runs at least one end-to-end workspace analysis.

Tests to delete when replaced:

- Fixed ecommerce demo acceptance tests.
- Template-only tests that prove hardcoded ecommerce behavior.
- Mock external delivery tests that are not part of P11 product acceptance.
- Streamlit product-entry tests once Next.js owns the product UI.
- Tests for paths that P11 deletes.

## Live LLM Acceptance

P11 must include real DeepSeek acceptance tests.

Minimum live acceptance:

1. Import a realistic generated CSV/Excel dataset into a workspace.
2. Generate profile and semantic layer draft.
3. Save reviewed semantic layer.
4. Ask a business analysis question.
5. DeepSeek performs question understanding and SQL planning.
6. SQL candidate passes validation.
7. Query executes against the workspace database.
8. Visualization is generated from real result columns.
9. Explanation references evidence-backed result rows.
10. Trace records provider, prompt id, prompt version, validation, fallback, SQL, chart, and artifact paths.

Mock-provider tests may support development, but P11 is not accepted without live DeepSeek evidence.

## Realistic Data Without User Data

The user does not currently have real business data.

P11 should include a realistic synthetic dataset generator that can create nontrivial business workspaces.

The generator should produce datasets that feel like real operational exports:

- Multiple CSV files and one Excel workbook option.
- Multiple related tables.
- Dirty but manageable data: missing values, inconsistent labels, delayed events, refunds, duplicate-looking names.
- At least 12 months of time-series data.
- Known embedded scenarios for validation.

This synthetic data is used for product demos and live acceptance, but the product path must also support user-uploaded files.

## API Shape

Initial FastAPI endpoints:

```text
POST /api/workspaces
GET  /api/workspaces
GET  /api/workspaces/{workspace_id}

POST /api/workspaces/{workspace_id}/sources/upload
POST /api/workspaces/{workspace_id}/sources/sqlite
GET  /api/workspaces/{workspace_id}/sources

POST /api/workspaces/{workspace_id}/profile
GET  /api/workspaces/{workspace_id}/profile

POST /api/workspaces/{workspace_id}/semantic-layer/draft
GET  /api/workspaces/{workspace_id}/semantic-layer
PUT  /api/workspaces/{workspace_id}/semantic-layer

POST /api/workspaces/{workspace_id}/runs
GET  /api/workspaces/{workspace_id}/runs/{run_id}
GET  /api/workspaces/{workspace_id}/runs/{run_id}/trace
```

## Migration From Current System

P11 should migrate useful existing modules instead of rewriting everything.

Keep and adapt:

- `graph/` workflow, made workspace-aware.
- `llm_ops/` provider, prompts, and structured output.
- SQL validator and executor.
- Evidence validator.
- Visualization agent and local chart rendering if still useful for workspace results.
- Trace and artifact hygiene.
- FastAPI async run ideas, adapted to workspace runs.

Delete or demote:

- Ecommerce as the main product database.
- Fixed demo question flows.
- Mock external delivery as main product proof.
- Streamlit as main user-facing frontend.
- Tests that exist only to preserve old demo behavior.

## Acceptance Criteria

P11 is complete when:

1. A user can create a workspace.
2. A user can upload CSV and Excel files.
3. A user can register or import a SQLite source.
4. The system creates a workspace `analysis.db`.
5. The system generates a profile for imported data.
6. The system generates and saves an editable semantic layer.
7. The product frontend is Next.js, not Streamlit.
8. The user can ask a natural-language question against the workspace.
9. DeepSeek live mode can drive the product analysis path.
10. SQL validates against the workspace schema.
11. SQL executes against workspace data.
12. Charts and explanations are generated from real query output.
13. Trace and artifact files are stored under the workspace run directory.
14. Old conflicting ecommerce/template/mock product paths and tests are deleted.
15. P11 acceptance includes real DeepSeek evidence, not only mock tests.

## Open Implementation Choices For The Plan

The implementation plan should decide:

- Whether SQLite sources are copied into the workspace or referenced read-only.
- Whether imports run synchronously in P11 or through a background job abstraction.
- Whether semantic layer review is a form-first UI or a YAML editor with guided controls.
- Whether Next.js and FastAPI run as separate dev servers or through one proxy command.
- Which old tests are deleted in the first cleanup slice versus after replacement coverage exists.

The implementation plan should keep each slice shippable and should delete old tests as soon as their replacement product coverage exists.
