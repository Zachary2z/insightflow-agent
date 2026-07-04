# Historical / Superseded: P12 Workspace Report Productization Design

Date: 2026-06-23

This document is retained only as a historical P12 design snapshot. Current implementation guidance lives in docs/product/plans/, especially the P17 cleanup plan and the completed P16 clean business output model plan. The current report implementation uses the P16 business_answer contract for report sections and must not treat older section summary, old eval, Streamlit, mock SaaS, or action-workflow wording in this snapshot as current product guidance.

## Summary

P12 turns P11's single-question workspace analysis into a report product. P11 remains the ad hoc analysis entry point. P12 adds a separate report entry point where a user chooses a workspace, selects a report type, enters a report goal, generates a structured report synchronously, views it in the Next.js UI, and downloads the generated Markdown file.

P12 MVP is intentionally small:

- Page display plus Markdown download.
- Synchronous generation first.
- Async report generation is deferred.
- No PDF/PPT export.
- No scheduled reports.
- No auth/RBAC.
- No real SaaS integrations.
- No restoration of Streamlit, old eval, or old non-workspace APIs.

## Product Shape

P11 remains:

```text
/workspaces/{workspace_id}/analysis
```

Use this for one-off natural-language analysis.

P12 adds:

```text
/workspaces/{workspace_id}/reports
/workspaces/{workspace_id}/reports/{report_id}
```

Use this for structured, multi-section report generation.

## User Flow

1. User opens a workspace.
2. User opens Reports.
3. User selects one report type:
   - `business_review`
   - `channel_performance`
   - `revenue_trend`
4. User enters a natural-language report goal.
5. User clicks Generate report.
6. Backend synchronously generates the report.
7. UI displays:
   - report title
   - status
   - executive summary
   - report sections
   - section SQL
   - section result summary
   - section chart/artifact links
   - evidence notes
   - provider and trace metadata
8. User downloads `report.md`.

## Report Types

### business_review

Initial section targets:

- Overall revenue
- Top channels or products
- Trend or recent change
- Evidence-backed recommendations

### channel_performance

Initial section targets:

- Channel revenue ranking
- Channel trend or comparison
- Marketing efficiency when marketing-spend data exists

### revenue_trend

Initial section targets:

- Revenue trend
- Recent-period summary
- Notable changes

These are report-type presets, not old fixed SQL templates. They constrain the product experience and give the provider/report planner a safe set of section purposes. Presets may define section purposes and natural-language section questions, but they must not include hardcoded SQL, table-specific rule trees, keyword inference, or deterministic SQL templates. Each section still uses the P11 safety path for SQL planning, SQL validation, SQL execution, evidence, visualization, artifacts, and trace.

## Backend API

Add synchronous workspace report APIs:

```text
POST /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports/{report_id}
GET  /api/workspaces/{workspace_id}/reports/{report_id}/download
```

`POST /reports` request:

```json
{
  "report_type": "business_review",
  "report_goal": "Generate a monthly business review focused on revenue, channels, changes, and recommendations."
}
```

`POST /reports` response:

```json
{
  "success": true,
  "workspace_id": "workspace_123",
  "report_id": "report_abcd1234",
  "report": {
    "report_id": "report_abcd1234",
    "report_type": "business_review",
    "title": "Business Review",
    "status": "completed",
    "executive_summary": [],
    "sections": [],
    "markdown_path": ".../report.md",
    "json_path": ".../report.json",
    "trace_path": ".../trace.json"
  }
}
```

## Storage Layout

Each report is stored under the workspace root:

```text
workspaces/{workspace_id}/reports/{report_id}/
  report.json
  report.md
  trace.json
  artifacts/
```

`report.json` is the canonical machine-readable report. `report.md` is the first downloadable user artifact. `trace.json` records report-level and section-level events. `artifacts/` stores section chart files or copied/generated section artifacts.

All report-facing artifacts must be rooted under the report directory. If a reused P11 section run creates charts or traces in a workspace run directory, the report runner must copy or regenerate the report-facing artifact into `reports/{report_id}/artifacts/` and reference that report-local path from `report.json` and `report.md`. The final downloadable Markdown must not depend on transient section run directories.

Generated Markdown and chart files are runtime outputs and must not be committed.

## Report Runner

Add a workspace report runner under `workspaces/report_runner.py`.

Responsibilities:

- load workspace metadata;
- ensure profile and semantic-layer context exist or generate missing draft context;
- create a report directory;
- build a section plan from `report_type` plus `report_goal`;
- run each section through P11 workspace analysis capabilities;
- collect SQL, execution rows, evidence, visualization, and trace metadata;
- compose `report.json`;
- render `report.md`;
- return a structured response to FastAPI.

The runner should keep P11 ad hoc analysis untouched. P12 is a separate orchestrator that can reuse P11 internals.

Profile and semantic-layer rules:

- If a workspace profile is missing, the runner may generate it and persist it to the existing workspace profile path.
- If a semantic-layer file is missing, the runner may generate a draft and persist it to the existing workspace semantic-layer path.
- If a semantic-layer file already exists, the runner must not silently overwrite it. It may read it, include it in context, or create an explicit report-local derived context snapshot.
- P12-H1 should implement the report model, directory layout, and Markdown renderer without provider calls. Provider-backed section generation starts in P12-H2.

## Section Execution

Each section becomes a focused natural-language analysis question derived from:

- workspace context;
- report type;
- report goal;
- section purpose.

Each section must preserve these boundaries:

- provider question understanding can participate;
- provider SQL planning can participate;
- guarded SQL candidates can participate;
- every candidate must pass `validate_sql()`;
- SQL Reviewer must approve before execution;
- `run_sql()` executes only against the workspace `analysis.db`;
- Evidence Validator remains the final factual boundary;
- VisualizationAgent chooses chart/artifact output;
- section-local execution may reuse P11 workspace run directories internally;
- report-facing artifacts, report-level trace, `report.json`, and `report.md` must live under the report directory.

## Frontend

Add a Reports entry to workspace navigation.

Reports list page:

```text
frontend/app/workspaces/[workspaceId]/reports/page.tsx
```

Report detail page:

```text
frontend/app/workspaces/[workspaceId]/reports/[reportId]/page.tsx
```

Suggested components:

- `ReportGenerator`
- `ReportList`
- `ReportViewer`
- `ReportSection`
- `ReportDownloadLink`

The UI should be functional, not decorative. It should show the report result clearly and expose SQL/evidence/trace details in compact sections.

## Markdown Output

The Markdown report should include:

- title;
- report metadata;
- report goal;
- executive summary;
- section summaries;
- SQL per section;
- table/result preview per section;
- visualization artifact paths;
- evidence notes;
- trace path;
- provider metadata summary.

Download behavior:

- The API should return `text/markdown`.
- Filename should be stable, for example `report_abcd1234.md`.

## Error Handling

Report generation can return partial results.

Rules:

- If one section fails, mark that section `failed` and keep the report generation result structured.
- If no section succeeds, report status is `failed`.
- If at least one section succeeds and at least one fails, report status is `partial`.
- If all sections succeed, report status is `completed`.
- API errors should be explicit for missing workspace, unsupported report type, missing report goal, missing report id, and missing Markdown file.

## Live DeepSeek Acceptance

P12 needs an opt-in live acceptance test separate from P11:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 \
INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1 \
python3 -m pytest tests/test_p12_live_deepseek_workspace_report.py -q
```

The live test should:

- create a workspace;
- import synthetic workspace data;
- generate profile and semantic draft;
- submit a natural report goal;
- assert multiple report sections;
- assert at least one section uses live provider question understanding, SQL planning, guarded SQL candidate, and visualization;
- assert every executed SQL passed validation/review;
- assert Markdown exists;
- assert downloadable Markdown contains report title, section headings, SQL, chart/artifact references, and trace reference.

## Out Of Scope For P12 MVP

- PDF/PPT export.
- Async report generation.
- Email delivery.
- Scheduled recurring reports.
- Real Slack/Jira/Power BI/Notion integrations.
- Auth/RBAC.
- Deployment.
- Replacing P11 ad hoc analysis.
- Restoring historical Streamlit/ecommerce/eval product paths.

## Acceptance Criteria

- P11 `/analysis` remains available and unchanged as a single-question entry.
- P12 `/reports` is a separate product entry.
- User can generate a synchronous workspace report from the Next.js UI.
- User can view the report in the UI.
- User can download `report.md`.
- Backend persists `report.json`, `report.md`, `trace.json`, and artifacts under the workspace report directory.
- Backend exposes create/list/detail/download report APIs.
- Report sections preserve P11 SQL, evidence, visualization, and trace boundaries.
- P12 live DeepSeek report acceptance passes.
- Full backend tests, frontend tests, frontend build, tracked artifact audit, and docs audit pass.
