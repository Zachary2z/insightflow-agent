# InsightFlow Agent Development Plan

This document tracks the active product direction, not the full historical build log. Current implementation guidance lives in `docs/product/plans/`, especially:

- `docs/product/plans/2026-06-30-p16-clean-business-output-model.md`
- `docs/product/plans/2026-06-30-p17-product-codebase-cleanup.md`
- `docs/product/plans/2026-06-30-p18-business-answer-consistency.md`
- `docs/product/plans/2026-07-01-p19-business-output-and-report-quality.md`

## Current Product Direction

InsightFlow is a Chinese business data-analysis product with:

- FastAPI backend in `api/app.py`.
- Next.js frontend in `frontend/`.
- Workspace data import for CSV, Excel, and SQLite.
- Workspace profile and semantic-layer draft.
- P11 ad hoc workspace analysis.
- P12 structured workspace reports.
- P15 analysis history, run restoration, schema repair, and business-friendly failures.
- P16 single `business_answer` contract for analysis and report sections.
- P17 cleanup that removes non-current historical paths while preserving the real multi-agent/tool-calling chain.
- P18 consistency checks across conclusions, evidence, recommendations, chart annotations, and reports.
- P19 planned business-output/report quality work that turns valid model results into decision-ready Chinese business answers and management-ready reports.

Current runtime chain:

```text
workspace import
-> profile and semantic layer
-> question understanding
-> clarification router
-> SQL planning
-> guarded SQL candidate
-> SQL review
-> schema repair
-> SQL execution
-> evidence validation
-> insight/business answer
-> visualization
-> report
-> Next.js product UI
```

LLM/provider-backed components may understand intent, plan, draft guarded candidates, draft business wording, and choose visualization delivery. Deterministic code still owns safety gates, execution, evidence checks, artifact policy, and trace persistence.

## Phase Summary

| Phase | Current meaning | Status |
|---|---|---|
| P0-P10 | Historical foundations for SQL safety, evidence validation, MCP wrappers, semantic context, visualization, provider plumbing, and trace/artifact hygiene | Complete; historical context only |
| P11 | General workspace analysis product: FastAPI workspace APIs, Next.js product frontend, user data import, profile, semantic layer, ad hoc analysis | Complete |
| P12 | Workspace report product: report APIs, synchronous report runner, report storage, Markdown download, Next.js report UI | Complete |
| P13 | Business-facing answer/product UX: clarification continuation, business answer presentation, reports UI polish, Data Settings, chart display | Complete |
| P14 | Unified Chinese product shell and workflow: shared frontend shell, 数据源管理, 分析工作台, 报告中心, 数据设置, 业务问答 preview | Complete |
| P15 | Analysis reliability and history: persisted run history/detail, one-pass schema repair, business-friendly failures, real DeepSeek regression | Complete |
| P16 | Clean business output model: one `business_answer` shape across backend, frontend, reports, Markdown, and run restoration | Complete |
| P17 | Product codebase cleanup: remove historical non-current paths and simplify product docs/status surfaces | Complete |
| P18 | Business answer consistency: align conclusions, evidence, recommendations, chart annotations, and report summaries across general datasets | Complete |
| P19 | Business output and report quality: decision-ready analysis replies, Chinese business vocabulary, synthesized management reports, chart narrative integration, and live acceptance | Planned |

## P16 Business Answer Contract

Current analysis results and report sections use:

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

Report sections reuse this same shape. Main product fields must not contain raw SQL, trace IDs, provider metadata, raw row dumps, internal prompt text, or unsupported claims. Technical details remain available under collapsed UI/appendix sections.

## P17/P18/P19 Roadmap

| Task | Scope | Status |
|---|---|---|
| P17-H1 | Dependency inventory and boundary tests for current product entry points | Complete |
| P17-H2 | Remove legacy action-path code that is not part of current API/UI dependencies | Complete |
| P17-H3 | Remove unsupported external-placeholder visualization runtime entries | Complete |
| P17-H4 | Delete obsolete eval/demo files and mark old design snapshots historical | Complete |
| P17-H5 | Product docs/status simplification | Complete |
| P17-H6 | Final artifact hygiene, legacy audit, backend/frontend regression, and real DeepSeek acceptance | Complete |
| P18-H1 | Add failing tests for multi-metric conflict, insufficient comparison evidence, and chart annotation conflict | Complete |
| P18-H2 | Implement lightweight answer consistency helpers and apply them in product result builder | Complete |
| P18-H3 | Align chart annotations with the final business answer | Complete |
| P18-H4 | Make report sections and executive summaries reuse consistency-checked answers | Complete |
| P18-H5 | Tighten provider prompt/validation only where deterministic consistency is insufficient | Complete |
| P18-H6 | Focused/full regression, real DeepSeek acceptance gating, artifact hygiene, and documentation closeout | Complete |
| P19-H1 | Answer/evidence alignment so recommendations cite the same entity and metric they recommend | Complete |
| P19-H2 | Chinese business vocabulary and unit normalization for user-facing answers and reports | Planned |
| P19-H3 | Decision-ready answer structure with conclusion, basis, actions, tradeoffs, caveats, and next steps | Planned |
| P19-H4 | Report synthesis layer so reports are management documents, not concatenated section outputs | Planned |
| P19-H5 | Chart narrative integration and graceful chart fallback when provider specs reference missing columns | Planned |
| P19-H6 | Report Markdown and frontend reader polish for Chinese-first business reports | Planned |
| P19-H7 | Real DeepSeek acceptance and full regression for improved analysis/report quality | Planned |

P17 must keep current workspace analysis, workspace reports, SQL review, SQL execution, evidence validation, schema repair, visualization, trace logging, MCP database/report wrappers, P16 product output, Next.js product pages, and real DeepSeek live tests.

P17 progress summary: H1-H6 are complete. The current product codebase keeps the FastAPI/Next.js workspace analysis and report product, removes historical demo/action/mock/eval paths from active entry points, and preserves real DeepSeek live acceptance.

P18 is complete. P19 is the next product quality phase. It should improve the business readability, evidence alignment, report synthesis, chart narrative, and live DeepSeek acceptance of the current analysis/report product before adding authenticated external publishing integrations.

## Current Entry Points

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

Primary product APIs:

```text
POST /api/workspaces/{workspace_id}/runs
POST /api/workspaces/{workspace_id}/reports
```

Primary frontend routes:

```text
/workspaces/{workspaceId}/analysis
/workspaces/{workspaceId}/reports
/workspaces/{workspaceId}/settings
/workspaces/{workspaceId}/runs/{runId}
```

## Verification Plan

Use these commands for current product regression:

```bash
python3 -m pytest tests/test_p17_product_cleanup_boundaries.py tests/test_p11_cleanup_boundaries.py -q
python3 -m pytest tests/test_project_initialization.py tests/test_mcp_tool_layer.py -q
python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py -q
cd frontend && npm test
cd frontend && npm run build
```

P19 should begin from `docs/product/plans/2026-07-01-p19-business-output-and-report-quality.md`. It must keep the P16 `business_answer` public shape, avoid table-specific rule trees, keep live DeepSeek tests opt-in, and preserve deterministic unit-test stability.

## Historical / Superseded Context

The following names are retained only for cleanup history, deleted-file assertions, or low-level fixture context. They are not current product entry points or development instructions:

- Historical / Superseded: `streamlit run app.py`, `eval/run_eval.py`, `tests/test_eval_runner.py`, `tests/test_streamlit_app.py`, `chart_agent`, `visualization_planner`, `chart_tool`, `action_delivery`, `action_drafter`, `powerbi_publisher_mock`, `jira_ticket_mock`, mock SaaS, fixed template behavior, deterministic action template behavior, and keyword inference.
- Historical retained fixture: `data/ecommerce.db` remains only because low-level tests use it directly for schema, SQL, workflow, report, MCP, and provider regressions.
- Historical P11/P12/P13 design specs under `docs/superpowers/specs/` are snapshots. Current implementation guidance is `docs/product/plans/`, the P16 `business_answer` contract, and the P17 cleanup plan.
