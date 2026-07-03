# InsightFlow Agent

InsightFlow Agent is a Chinese-first workspace-based business data analysis product. The current product is a FastAPI backend plus a Next.js frontend that lets users import business data, ask natural-language analysis questions, generate workspace reports, and inspect guarded evidence, charts, artifacts, and technical traces.

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
| P20 general business analysis foundation | Complete | `docs/product/plans/2026-07-01-p20-general-business-analysis-foundation.md` |
| P21 responsive analysis experience | Complete | `docs/product/plans/2026-07-02-p21-responsive-analysis-experience.md` |
| P22 evidence-driven report generation | Complete | H1-H4 complete; `docs/product/plans/2026-07-02-p22-evidence-driven-report-generation.md` |
| P23 core evidence and report tooling readiness | In progress | H1-H4 complete; `docs/product/plans/2026-07-03-p23-core-evidence-and-report-tooling-readiness.md` |

P18-H1 through P18-H6 are complete. P19-H1 through P19-H5 are complete. P20-H0 through P20-H5 are complete: the product now has a generalized semantic-layer baseline with Chinese business aliases, safe metric formula quoting, a reusable Chinese analysis task contract with slot-level clarification continuation, a stable fact/evidence payload with metric formulas, comparison scope, warnings, and Chinese business display values, plus evidence-backed Chinese business answers, chart descriptions, and report synthesis. P21-H1 through P21-H6 are complete: each analysis run carries conservative `analysis_route` metadata, low-risk `fast_fact` questions use a shorter SQL/evidence-backed answer path, product results include business-friendly `progress_steps`, same-workspace/same-data-version/same-normalized-question completed runs can be offered as historical reuse candidates without calling the model, newly submitted runs create recoverable background run shells with compact task cards plus polling/page recovery, and `fast_fact` answers use lightweight context packs that retain key evidence while excluding raw SQL, trace, provider metadata, full workspace profile, and full raw rows from the compact pack. P22-H1 through P22-H4 are complete: Report Center now persists the new report document contract, deletes the old fixed-preset/per-section analysis stitching path, plans Chinese chapters from the user's report goal, collects structured evidence from workspace profile, semantic layer, metric registry, guarded SQL execution, and evidence payload helpers, composes one coherent Chinese report through the current `report_composer`, validates key facts, and renders a clean business report page plus clean Markdown download. P23-H1 through P23-H4 are complete: Analysis Workbench and Report Center now share factual evidence vocabulary, Analysis Workbench answers stay natural and evidence-bound, Report Center writes one full report from shared evidence, and P23-H4 adds a report EvidenceLedger plus one repair pass for unsupported hard facts. Real chart artifacts are shown inline with download links; chart intents are labeled as待生成图表 instead of pretending an artifact exists. Product-facing copy, answers, charts, reports, and prompts should be Chinese; English or mixed raw headers remain supported through semantic recognition and Chinese aliases.

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

`POST /api/workspaces/{workspace_id}/runs` accepts either a new `user_question` or a continuation request with `pending_run_id` and `clarification_answer`. New analysis requests create a recoverable run id and can return `status: "running"` while local background work continues; clients should poll `GET /api/workspaces/{workspace_id}/runs/{run_id}` for `running`, `waiting_for_clarification`, `completed`, or `failed`. For repeated completed questions in the same workspace `data_version`, it can return `status: "cache_candidate"` with `matched_run_id`; send `force_reanalysis: true` to explicitly rerun.

Reports:

```text
POST /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports
GET  /api/workspaces/{workspace_id}/reports/{report_id}
GET  /api/workspaces/{workspace_id}/reports/{report_id}/download
```

Supported report types are `business_review`, `channel_performance`, and `revenue_trend`.

Current report records expose the P22 document contract: `plan`, `evidence_pack`, `document`, and `validation`. Markdown and the report detail UI render `ReportDocument` as a Chinese report with title metadata, opening summary, body chapters, inline charts or chart-intent prompts, compact evidence tables, action recommendations, data boundaries, and a collapsed business-readable technical appendix. Markdown downloads do not dump SQL, raw rows, query ids, provider metadata, trace details, or internal report contracts. When enabled, the FastAPI report API passes a DeepSeek-backed `report_composer` provider into the runner; if no key or flag is available, the same contract is produced by the deterministic fallback. The old stitched section-answer report shape is superseded/deleted from the main path; legacy top-level summary arrays remain only as derived list/detail metadata during the cutover.

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

P20-H1 semantic foundation note: workspace profiling now emits generalized field roles, inferred types, business-meaning candidates, group-by suitability, and aggregation suitability for imported business data. Workspace semantic drafts are generated from actual tables/columns into metrics, dimensions, time fields, entities, field roles, aliases, relationship candidates, and available analysis capabilities without inventing missing `channel` or `revenue` fields. Generated metric formulas quote SQLite identifiers safely, and English/mixed raw headers such as `Sales Amount` or `Score (NPS)` map into Chinese business aliases such as 销售额 or 满意度. Workspace semantic-layer YAML/JSON loading is unified for settings, context summaries, metric lookup, and schema repair.

P20-H2 task contract note: question understanding now emits a normalized `analysis_task` contract with `task_type`, Chinese `dimensions` and `metrics`, `time_range`, `filters`, `decision_goal`, `missing_slots`, `defaults_applied`, `resolved_question`, fixed `output_language: "zh"`, and confidence. Complete Chinese questions such as “最近90天按门店比较销售额” continue into analysis; incomplete recommendation questions ask concise Chinese follow-ups for missing slots; partial continuation answers such as “花费” keep the run waiting for the remaining time range; and provider-backed outputs are normalized so they cannot bypass missing-slot rules or switch product output away from Chinese.

P20-H3 fact layer note: metric lookup now exposes a JSON-safe metric registry with base formulas and supported derived metrics only when source fields exist. ROAS, net return, margin rate, and average order value keep separate formulas and source fields; missing sources produce warnings instead of invented metrics. Product results now carry a reusable `fact_payload` under evidence and technical details with `columns`, `rows`, `formulas`, `time_scope`, `filters`, `comparison_scope`, `warnings`, `display_values`, and `technical_sql`. Main `business_answer` fields remain free of raw SQL and raw rows.

P20-H4 answer/report note: answer composition now rebuilds useful Chinese recommendations from validated multi-row evidence instead of accepting stale "证据不足" downgrades. Fact-only questions keep caveats without forcing action plans; recommendation questions can explain metric tradeoffs such as revenue scale versus ROI; fallback charts choose chart types from task intent with Chinese titles and annotations; and management reports stay Chinese-first while reusing section business answers and evidence.

P20-H5 closeout note: realistic acceptance now covers store sales/satisfaction and support ticket operations datasets, with factual questions, ranking, comparison, trend, recommendation, chart artifacts, evidence payloads, and management-report synthesis all running through the current workspace product path. Report section prompts now ask agents to use the current workspace schema/profile/semantic layer rather than assuming a demo schema. Common service-operation fields such as `team_name`, `ticket_count`, and `avg_response_minutes` display as Chinese business labels. Schema-review failure guidance is generic to the current workspace and no longer points users toward a demo-specific field set.

## Product Capabilities After P20

InsightFlow can now be described as a Chinese-first general business data-analysis multi-agent product foundation:

- Import different business datasets through workspace CSV/Excel/SQLite flows.
- Profile tables and fields, then draft a semantic layer with metrics, dimensions, time fields, entities, aliases, formulas, and relationship candidates.
- Map Chinese, English, and mixed raw headers into Chinese business semantics.
- Understand Chinese business questions, ask concise follow-up questions for missing slots, and continue after clarification.
- Use SQL, metric, evidence, chart, and report tools to produce validated facts and artifacts.
- Keep factual evidence, model judgment, validation, and final expression separated.
- Produce Chinese business conclusions, caveats, recommendations when requested, chart annotations, Markdown reports, and report summaries.

Current report work:

- P22: evidence-driven Report Center rewrite so reports become coherent Chinese business documents instead of stitched analysis answers. H1 closeout removed the old report supervisor/agent/writer/planner path and its provider prompt/schema flags; H3 added the current `report_composer` provider path and lightweight fact validator without restoring old report stitching; H4 polished the frontend reader and Markdown download so charts, evidence tables, recommendations, data boundaries, and collapsed appendices read like a business report.
- P23: core evidence and report tooling readiness before external business tool calling and exports. H1-H4 are complete: Analysis Workbench `fact_payload` and Report Center `ReportEvidencePack.evidence_payloads` now share the same factual payload vocabulary with traceable derived metrics, formulas, chart-ready data, warnings/data limits, and technical-detail references; Analysis Workbench Chinese business answers read naturally while preserving evidence-bound hard facts; Report Center writes one complete document from shared evidence; and P23-H4 adds `p23.report_ledger.v1`, chapter coverage metadata, ledger-backed validation, and one automatic repair pass for unsupported hard facts. Real China-oriented external business tool calling and exports remain P24.

## Verification

Focused cleanup boundary:

```bash
python3 -m pytest tests/test_p17_product_cleanup_boundaries.py tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py -q
```

Current backend regression:

```bash
python3 -m pytest tests/test_metric_tool.py tests/test_evidence_tool.py tests/test_evidence_validator.py tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q
python3 -m pytest tests/test_project_initialization.py tests/test_mcp_tool_layer.py -q
python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py -q
python3 -m pytest tests/test_p20_realistic_acceptance.py tests/test_p20_live_deepseek_acceptance.py -q
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

Live provider acceptance is explicit opt-in and requires local environment configuration. Keep real DeepSeek live tests; they cover workspace analysis, workspace reports, product answer quality, clarification continuation, history reliability, and P20 non-channel store analysis.

To enable live DeepSeek acceptance locally:

```bash
export INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1
export INSIGHTFLOW_PRODUCT_LIVE_MODE=1
export DEEPSEEK_API_KEY=...
python3 -m pytest tests/test_p20_live_deepseek_acceptance.py -q
```

Without those flags and a key, live tests skip by default and must not fail normal regression.

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
