# InsightFlow Agent

InsightFlow Agent is a workspace-based business data analysis product. The current product is a FastAPI backend plus a Next.js frontend that lets users import business data, ask natural-language analysis questions, generate workspace reports, and inspect guarded evidence, charts, artifacts, and technical traces.

Current product chain:

```text
workspace data import
-> profile and semantic-layer draft
-> business question or report goal
-> question understanding and clarification
-> SQL planning and guarded SQL candidate
-> SQL review and one-pass schema repair
-> SQL execution
-> evidence validation
-> P16 business_answer
-> visualization artifacts and reports
-> Next.js product UI
```

The product is intentionally guarded: LLM/provider-backed steps may understand, plan, draft SQL candidates, draft business wording, and choose visualization delivery. Deterministic tools still own SQL approval, SQL execution, evidence checks, chart/tool policy checks, artifact writing, and trace persistence.

## Current Status

| Product area | Status | Current entry |
|---|---|---|
| FastAPI product backend | Active | `uvicorn api.app:app --reload` |
| Next.js product frontend | Active | `frontend/`, `npm run dev` |
| Workspace import/profile/semantic layer | Complete | `/api/workspaces`, `/sources`, `/profile`, `/semantic-layer/draft` |
| P11 ad hoc workspace analysis | Complete | `POST /api/workspaces/{workspace_id}/runs` |
| P12 workspace reports | Complete | `POST /api/workspaces/{workspace_id}/reports` |
| P16 clean business output model | Complete | `business_answer` with `headline`, `direct_answer`, `why`, `evidence_bullets`, `recommendations`, `caveats`, `confidence` |
| P17 product codebase cleanup | Complete | `tests/test_p17_product_cleanup_boundaries.py`, `docs/product/plans/2026-06-30-p17-product-codebase-cleanup.md` |
| P18 business answer consistency | Complete | `workspaces/answer_consistency.py`, `docs/product/plans/2026-06-30-p18-business-answer-consistency.md` |
| P19 report and chart synthesis | Complete | Management-style reports with synthesized summary, findings, actions, chart/evidence, limits, technical appendix, and H5 live acceptance |
| P20 general business analysis foundation | In progress | `docs/product/plans/2026-07-01-p20-general-business-analysis-foundation.md` |

P18-H1 through P18-H6 are complete. P19-H1 through P19-H5 are complete. P20-H0 is complete. P20 is the current foundation phase: clean old/conflicting paths, generalize data profiling and semantic context, introduce a reusable analysis task contract, stabilize factual evidence and metric formulas, and make answers/reports use validated evidence without fixed demo templates. Real external business tool calling remains a later product phase after the generalized analysis foundation and responsiveness work are stable.

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

Open `http://localhost:3000`, create a workspace, import CSV/Excel/SQLite data, generate a profile, generate a semantic-layer draft, then use:

- `/workspaces/{workspaceId}/analysis` for ad hoc business analysis.
- `/workspaces/{workspaceId}/reports` for structured workspace reports.
- `/workspaces/{workspaceId}/settings` for data readiness, profile, semantic layer, model mode, and safety/audit status.
- `/workspaces/{workspaceId}/runs/{runId}` to restore a persisted analysis result.

## Current Product APIs

Workspace and data preparation:

```text
POST /api/workspaces
GET  /api/workspaces
GET  /api/workspaces/{workspace_id}
GET  /api/workspaces/{workspace_id}/settings
POST /api/workspaces/{workspace_id}/sources/upload
POST /api/workspaces/{workspace_id}/sources/sqlite
GET  /api/workspaces/{workspace_id}/sources
POST /api/workspaces/{workspace_id}/profile
POST /api/workspaces/{workspace_id}/semantic-layer/draft
```

Analysis and artifacts:

```text
POST /api/workspaces/{workspace_id}/runs
GET  /api/workspaces/{workspace_id}/runs
GET  /api/workspaces/{workspace_id}/runs/{run_id}
GET  /api/workspaces/{workspace_id}/artifacts/{relative_path}
```

`POST /api/workspaces/{workspace_id}/runs` accepts either a new `user_question` or a continuation request with `pending_run_id` and `clarification_answer`.

Reports:

```text
POST /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports/{report_id}
GET  /api/workspaces/{workspace_id}/reports/{report_id}/download
```

Supported report types are `business_review`, `channel_performance`, and `revenue_trend`.

Report records now expose management-facing narrative fields before section details: `executive_summary`, `key_findings`, `action_priorities`, `chart_and_evidence`, `risks_and_limits`, then a collapsed technical appendix for SQL, traces, raw previews, and provider metadata.

## Business Answer Contract

Analysis results and report sections use the P16 contract:

```json
{
  "headline": "",
  "direct_answer": "",
  "why": "",
  "evidence_bullets": [],
  "recommendations": [],
  "caveats": [],
  "confidence": "medium"
}
```

Product-facing fields must stay business-readable, evidence-backed, and free of raw SQL, trace IDs, provider metadata, raw row dumps, or internal prompt text. Technical details remain available in collapsed UI sections and trace artifacts.

## Current Architecture

| Layer | Current owner |
|---|---|
| Product API | `api/app.py` |
| Frontend | `frontend/app`, `frontend/components`, `frontend/lib/api.ts` |
| Workspace store/import/profile/semantic draft | `workspaces/` |
| Analysis runner | `workspaces.analysis_runner`, `graph/workflow.py`, `graph/nodes.py` |
| Report runner/storage/Markdown | `workspaces.report_runner`, `workspaces.report_store`, `workspaces.report_markdown` |
| Provider prompts and structured output | `llm_ops/` |
| Question understanding and clarification | `question_understanding/`, `agents/question_understanding.py`, `agents/clarification_router.py` |
| SQL planning and guarded candidates | `sql_planning/`, `agents/sql_planning_router.py`, `agents/guarded_llm_enhancer.py` |
| SQL safety and execution | `tools/sql_validator.py`, `tools/sql_executor.py`, `agents/sql_reviewer.py`, `agents/schema_repair.py` |
| Evidence safety | `tools/evidence_tool.py`, `agents/evidence_validator.py` |
| Visualization | `agents/visualization_agent.py`, `visualization/`, `visualization_delivery/`, `tools/external_visualization_tool.py` |
| Trace and artifacts | `tools/trace_logger.py`, workspace run directories, workspace report directories |
| MCP wrappers | `mcp_servers/database_server.py`, `mcp_servers/report_server.py` |

P20 should keep this product recognizably multi-agent and tool-calling, but with cleaner boundaries:

- data profiling and semantic-layer tools describe the current workspace instead of relying on a fixed demo schema;
- task-routing agents convert natural-language questions into dimensions, metrics, time ranges, filters, and decision goals;
- SQL/calculation/chart/report tools produce structured evidence and artifacts;
- model-backed insight/report writers explain and recommend within the evidence boundary;
- validators check factual numbers, rankings, fields, and metric formulas without blocking reasonable evidence-backed business judgment.

P20-H0 cleanup note: the old trace-driven SQL template-mining/eval helper path was removed from active code (`sql_planning.feedback`, `tests/test_llm_template_mining_eval_suite.py`, and `template_mining_event` trace payloads). Current provider smoke validation remains in `tests/test_llm_smoke_eval.py`.

## Verification

Focused cleanup boundary:

```bash
python3 -m pytest tests/test_p17_product_cleanup_boundaries.py tests/test_p11_cleanup_boundaries.py -q
```

Current backend regression:

```bash
python3 -m pytest tests/test_project_initialization.py tests/test_mcp_tool_layer.py -q
python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py -q
python3 -m pytest
```

P18 focused regression:

```bash
python3 -m pytest tests/test_answer_consistency.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py tests/test_business_answer_quality.py tests/test_deepseek_provider_structured_output.py -q
```

Frontend regression:

```bash
cd frontend
npm test
npm run build
```

Live provider acceptance is explicit opt-in and requires local environment configuration. Keep real DeepSeek live tests; they cover workspace analysis, workspace reports, product answer quality, clarification continuation, and history reliability.

## Generated Artifacts

Generated runtime outputs must not be committed:

- `.env`
- `.venv/`
- `frontend/node_modules/`
- `frontend/.next/`
- `.pytest_cache/`
- `__pycache__/`
- `sample_data/`
- `data/*.db`
- `eval/report.md`
- `reports/**`
- `reports/charts/*`
- `logs/traces/*`
- `workspaces/*/runs/*`
- `workspaces/*/reports/*`

Tracked `.gitkeep` files may remain only to preserve empty artifact directories.

## Historical / Superseded Context

This section is historical cleanup context only, not current product guidance.

- Historical / Superseded: `streamlit run app.py`, `eval/run_eval.py`, `tests/test_eval_runner.py`, `tests/test_streamlit_app.py`, `chart_agent`, `visualization_planner`, `chart_tool`, `action_delivery`, `action_drafter`, `powerbi_publisher_mock`, `jira_ticket_mock`, mock SaaS, fixed template behavior, deterministic action template behavior, and keyword inference are old demo/eval/action/mock/chart cleanup terms.
- Historical retained low-level fixture: `data/ecommerce.db` remains tracked because low-level schema, SQL validator, SQL executor, workflow, report, MCP, and provider regressions still use it directly. It is not the default product database and is not the quickstart data source.
- Current implementation guidance lives in `docs/product/plans/`, especially the P20 general business analysis foundation plan.

For the concise roadmap, see [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md). For the current task/status surface, see [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md).
