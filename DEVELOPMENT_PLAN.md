# InsightFlow Agent Development Plan

This document tracks the active product direction, not the full historical build log. Current implementation guidance lives in `docs/product/plans/`, especially:

- `docs/product/plans/2026-06-30-p16-clean-business-output-model.md`
- `docs/product/plans/2026-06-30-p17-product-codebase-cleanup.md`
- `docs/product/plans/2026-06-30-p18-business-answer-consistency.md`
- `docs/product/plans/2026-07-01-p19-business-output-and-report-quality.md`
- `docs/product/plans/2026-07-01-p20-general-business-analysis-foundation.md`
- `docs/product/plans/2026-07-02-p21-responsive-analysis-experience.md`
- `docs/product/plans/2026-07-02-p22-evidence-driven-report-generation.md`
- `docs/product/plans/2026-07-03-p23-core-evidence-and-report-tooling-readiness.md`
- `docs/product/plans/2026-07-03-p24-general-business-data-understanding.md`
- `docs/product/plans/2026-07-04-p25-real-usage-answer-report-polish.md`
- `docs/product/plans/2026-07-04-p26-repository-cleanup-before-external-tools.md`
- `docs/product/plans/2026-07-04-p27-analysis-workbench-multi-agent-refactor.md`

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
- P19 business-output/report quality work that moves from one-off consistency patches toward an Answer Reviewer Agent, Final Answer Composer, and small deterministic safety guardrail.
- P20 general business analysis foundation work that cleans old paths and separates factual tools, model judgment, fact validation, and expression/report writing so the product can handle different uploaded business datasets.
- P20 Chinese-first product scope: product-facing UI copy, clarifications, answers, charts, reports, and prompts should be Chinese; English or mixed raw headers are supported through semantic recognition and Chinese aliases, not bilingual output branches.
- P21 responsive analysis experience work added conservative route classification, fast factual paths, progress states, exact historical reuse, page recovery, compact task cards, and lightweight context packs without weakening the P20 evidence chain.
- P22 evidence-driven report generation work replaced stitched Analysis Workbench report sections with a clean report document contract, Chinese goal-driven report planning, structured report evidence collection, model-backed report composition, lightweight fact validation, and clean report reader/Markdown rendering.
- P23 core evidence and report tooling readiness is complete. It keeps Analysis Workbench and Report Center as separate product experiences, unifies their factual `EvidencePack`/artifact standards, preserves model-written explanations and recommendations inside evidence boundaries, hardens one-pass full-report generation, and removes old paths before the next product-hardening phase. P23-H4 replaced brittle prose-number validator patching with a tool-built report evidence ledger plus one automatic report repair pass; its coverage and metric-role selection are evidence-aware, so actual fact fields/table columns control missing-evidence boundaries and only additive/count business metrics are chosen for totals/shares. Rate, average, duration, satisfaction, and unknown numeric fields stay as row facts instead of contribution denominators. P23-H5 adds ledger-referenced artifact records and minimal local tool-call records so charts, Markdown reports, report documents, and future exports can consume trusted facts without raw SQL rows or model recalculation. P23-H6 completed cleanup, focused/full regression, frontend tests/build, tracked-artifact audit, old-path audit, no-key acceptance, and live-provider gating documentation.
- P24 is complete as the general business data understanding and evidence generation phase before external integrations. H1-H3 are complete: generic field profiling, semantic-layer drafting, explicit evidence requirements, semantic-layer-backed Analysis Workbench facts, Report Center evidence planning/collection, conservative investment-efficiency/data-limit handling, real DeepSeek acceptance, full cleanup, frontend verification, and artifact hygiene now work across common Chinese business datasets.
- P25 is complete as a compact real-usage polish phase for Analysis Workbench and Report Center. H1-H4 addressed direct-answer decisiveness, contradictory evidence limits, stale field fallbacks, report goal/title inference, the visible report-type template feel, realistic/live acceptance, cleanup, documentation closeout, and safe full-data time defaults for missing-time questions/reports.
- P26 is a cleanup-only phase before external business tool integrations. It keeps historical docs, removes tracked generated artifacts, makes the local SQLite test fixture generated on demand, and clarifies the current FastAPI/Next.js product path.
- P27 is the active Analysis Workbench multi-agent architecture and latency phase. H1 is complete with stable Analysis Workbench contracts and Report Center boundary tests. It primarily refactors Analysis Workbench, not Report Center. It keeps Report Center on its independent `ReportEvidencePack + EvidenceLedger + ReportDocument` path while consolidating duplicated Analysis Workbench nodes into clearer Coordinator, Data Understanding, Evidence, Evidence Auditor, Business Answer, and on-demand Visualization responsibilities.

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
| P19 | Business output and report quality: Answer Reviewer Agent, Final Answer Composer, decision-ready replies, synthesized reports, chart narrative, cleanup, and live acceptance | Complete |
| P20 | Chinese-first general business analysis foundation: project cleanup, generalized data profiling/semantic layer, task contract, fact/evidence layer, business answer/report generation, realistic acceptance, cleanup audit, and live DeepSeek opt-in verification | Complete |
| P21 | Responsive analysis experience: conservative route classification, fast factual path, progress states, exact history reuse, compact task cards, page recovery, and lightweight context packs | Complete |
| P22 | Evidence-driven report generation: replace stitched report sections with a coherent Chinese report document path and delete old report paths | Complete; H1-H4 complete |
| P23 | Core evidence and report tooling readiness: shared factual evidence/artifact contracts for Analysis Workbench and Report Center, natural Chinese business answers, one-pass report hardening, evidence-ledger report self-repair, artifact/tool-call readiness, cleanup, and live acceptance gating before external tool integrations | Complete; H1-H6 complete |
| P24 | General business data understanding and evidence generation: common business dataset profiling, semantic-layer strengthening, generic evidence requirements, Analysis Workbench and Report Center grounding, real DeepSeek acceptance, and cleanup | Complete; H1-H3 complete |
| P25 | Real usage answer/report polish: direct primary-metric answers, clean evidence limits, stale-field removal, report goal/title inference, simplified report UI, realistic/live acceptance, cleanup, and safe full-data time defaults | Complete; H1-H4 complete |
| P26 | Repository cleanup before external tools: generated artifact hygiene, local fixture generation, current-path docs, historical-record retention | Complete |
| P27 | Analysis Workbench multi-agent refactor: consolidate duplicated analysis nodes, make tool-calling/evidence boundaries clearer, lower latency, and protect the separate Report Center path | In progress; H1 complete |

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

## P17/P18/P19/P20 Roadmap

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
| P19-H1 | Close the current deterministic answer/evidence alignment hole without expanding keyword-heavy rules | Complete |
| P19-H2 | Add reviewer/composer foundation with structured contracts and deterministic tests | Complete |
| P19-H3 | Polish business answer quality: vocabulary, units, grounded recommendations, tradeoffs, and concise one-screen answers | Complete |
| P19-H4 | Synthesize reports and chart narrative from reviewed business answers, with language-aware report labels and business-readable evidence summaries | Complete |
| P19-H5 | Quality closeout: focused/full regression, frontend build, live DeepSeek acceptance, cleanup, and artifact hygiene | Complete |
| P20-H0 | Architecture cleanup and main path inventory; remove old paths and conflicting compatibility code | Complete |
| P20-H1 | General data profiling and semantic layer for arbitrary uploaded business datasets | Complete |
| P20-H2 | General Chinese analysis task contract and clarification continuation | Complete |
| P20-H3 | Fact layer, metric registry, and evidence payload with stable formulas and comparison scope | Complete |
| P20-H4 | Business insight, answer, chart, and report generation from validated evidence | Complete |
| P20-H5 | Realistic acceptance, cleanup audit, documentation closeout, and live DeepSeek verification when enabled | Complete |
| P21-H1 | Conservative route policy for clarify, fast_fact, standard_analysis, deep_judgment, and report routes | Complete |
| P21-H2 | Fast fact path for low-risk factual, ranking, summary, and simple trend questions | Complete |
| P21-H3 | Business-friendly progress steps and frontend progress timeline | Complete |
| P21-H4 | Exact historical reuse using workspace data_version and normalized_question | Complete |
| P21-H5 | Page recovery, lightweight background work, and compact task cards | Complete |
| P21-H6 | Lightweight context packs for fast_fact without starving complex routes of evidence | Complete |

P17 must keep current workspace analysis, workspace reports, SQL review, SQL execution, evidence validation, schema repair, visualization, trace logging, MCP database/report wrappers, P16 product output, Next.js product pages, and real DeepSeek live tests.

P17 progress summary: H1-H6 are complete. The current product codebase keeps the FastAPI/Next.js workspace analysis and report product, removes historical demo/action/mock/eval paths from active entry points, and preserves real DeepSeek live acceptance.

P18 and P19 are complete. P19-H1 closed the immediate deterministic alignment hole, P19-H2 added the reviewer/composer foundation, P19-H3 polished language-aware business answer vocabulary, tradeoffs, grounded recommendations, caveats, and report-section reuse, P19-H4 made reports synthesize reviewed answers into management summaries, key findings, action priorities, chart/evidence narrative, risks/limits, and a technical appendix, and P19-H5 completed focused/full regression, frontend build, live DeepSeek acceptance, artifact hygiene, and cleanup audit. Historical P19 bilingual output support is no longer a P20 product requirement; P20 now targets a Chinese-first business product, while English or mixed raw data headers remain supported through semantic recognition and Chinese labels.

P20 is complete as the Chinese-first general business analysis foundation described in `docs/product/plans/2026-07-01-p20-general-business-analysis-foundation.md`. It avoids table-specific rule trees, fixed answer templates, bilingual output branching, and old compatibility paths. P20-H0 inventoried and cleaned the active FastAPI/Next.js workspace chain. P20-H1 added generalized profiling, semantic-layer drafts, safe formula quoting, and Chinese aliases for English/mixed raw fields. P20-H2 added the normalized Chinese `analysis_task` contract and slot-level clarification continuation. P20-H3 added the metric registry and reusable fact payload with comparison scope, warnings, formulas, display values, and technical SQL kept outside the main answer. P20-H4 made final answers, chart fallback, and management reports use validated evidence for Chinese business conclusions, recommendations when requested, tradeoff explanations, chart annotations, and report synthesis. P20-H5 proved the foundation against store sales/satisfaction and support ticket operations datasets, generalized management-report section prompts away from demo fields, added opt-in P20 live DeepSeek acceptance, and completed cleanup/documentation closeout. Old code, tests, docs, and routes that conflict with the current FastAPI/Next.js workspace product may be deleted instead of preserved.

After P20, InsightFlow can import different business datasets, auto-profile them, draft a semantic layer, map raw Chinese/English/mixed fields into Chinese business semantics, understand and clarify Chinese business questions, call SQL/metric/evidence/chart/report tools, separate factual evidence from model judgment and final expression, and produce Chinese business answers plus reports. P21 responsiveness work is complete. P22 rebuilt Report Center into an evidence-driven Chinese report document pipeline. P23 completed shared evidence/artifact readiness, natural Chinese analysis answers, one-pass report hardening, cleanup, and live acceptance gating. P24 now strengthens generic business data understanding and evidence generation before real external business document/export integrations.

P21 is complete in `docs/product/plans/2026-07-02-p21-responsive-analysis-experience.md`. P21-H1 through P21-H6 are complete: analysis runs now produce conservative `analysis_route` metadata for `clarify`, `fast_fact`, `standard_analysis`, `deep_judgment`, and `report`; low-risk factual totals, rankings, and simple trends can use a shorter SQL/evidence-backed fast fact path; every product result now carries business-friendly `progress_steps`; exact same-workspace/same-data-version/same-normalized-question completed runs can be offered as historical reuse candidates; new non-cached analysis requests create recoverable local background run shells that the frontend restores with compact task cards and polling; and fast fact answers use lightweight context packs that retain key facts without carrying full workspace/profile/semantic/trace/provider/raw-row context. The H2 path still runs SQL review, execution, evidence validation, fact payload generation, technical detail preservation, and history persistence, but skips the heavy insight/reviewer/final composer/claim typing chain for `fast_fact`; H3 keeps progress copy free of raw SQL, trace IDs, prompt/provider metadata, and raw rows; H4 avoids LLM cache checks, vector search, similar-question matching, and keyword-heavy normalization; H5 avoids Redis, Celery, WebSocket, SSE, timeout handling, and external SaaS while preserving same-run-id recovery for `running`, `waiting_for_clarification`, `completed`, and `failed`; H6 applies strict context compression only to `fast_fact`, while `standard_analysis`, `deep_judgment`, and `report` keep richer context for answer quality. P21 makes the P20 foundation feel faster and more recoverable by routing requests conservatively, giving low-risk factual questions a shorter evidence-backed path, showing clear progress, reusing exact same-version historical runs, restoring active/history runs after page changes, keeping task cards compact, and using focused fast fact context packs. P21 did not add provider timeout work, vector cache, Redis/Celery, WebSocket/SSE, aggressive fast paths, or old compatibility paths. During P21, obsolete code, stale tests, dead imports, duplicate routes, unused adapters, historical compatibility branches, and unreachable fallback code could be deleted instead of preserved; keep one clean current product path.

P22 is complete in `docs/product/plans/2026-07-02-p22-evidence-driven-report-generation.md`. H1 rebuilt Report Center around a clean evidence-first report document contract; Markdown and the frontend render the document body instead of analysis workbench answer blocks. H2 replaced the profile-only skeleton with Chinese goal-driven planning and structured evidence collection for workspace overview, available metrics/dimensions, revenue structure, customer segments, support issues, and trend changes when the semantic layer and data support them. H3 added `workspaces/report_composer.py` and `workspaces/report_validator.py`, wires `INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER` and product live mode into the FastAPI report API, and keeps deterministic fallback for no-key mode. H4 polished Markdown and the report reader into a clean Chinese business report: title metadata, opening summary, body chapters, inline chart artifacts with download links, chart-intent placeholders when no artifact exists, compact evidence tables, action recommendations, data boundaries, and a collapsed appendix that summarizes validation/evidence without dumping SQL, raw rows, query ids, provider metadata, trace details, or internal contracts. Missing requested evidence is preserved as warnings or data limits rather than invented. The old stitched-section behavior, where preset report sections call the analysis runner and Markdown renders each section's `business_answer`, is superseded/deleted from the active report main path. Old report presets, stitched summary functions, `章节业务答案` main-body rendering, English default report titles, obsolete report agents/writers/supervisors, and tests that only protect old stitched output may be deleted instead of preserved.

P23 is complete in `docs/product/plans/2026-07-03-p23-core-evidence-and-report-tooling-readiness.md`. It is not the external-integration phase. P23 finished the core intelligence chain: Analysis Workbench and Report Center stay product-separated, but share factual evidence, metric, chart artifact, and validation standards; Report Center collects chapter-level evidence but writes the full report once; model-written reasons and recommendations are preserved as business judgment while hard facts remain evidence-bound; old template, stitched-report, duplicate evidence, stale bilingual, mock/demo, and compatibility paths that conflict with the current Chinese-first product may be deleted instead of preserved. P23-H4 is complete: tools calculate report facts and derived metrics into a compact ledger before the model writes, validation checks factual claims against that ledger instead of chasing every prose number, and one repair pass rewrites unsupported hard facts. The H4 ledger now derives coverage from actual fact fields/table columns, not titles or descriptions, and uses compact metric roles to choose contribution metrics, preventing ROI/rates/averages/satisfaction/durations or unknown numeric fields from becoming default total/share denominators. P23-H5 is complete: chart/report artifacts now carry `artifact_id`, local/report source, paths or download URLs, chart ids, and ledger fact/metric ids; local chart and Markdown renderer calls are recorded with safe summaries and output artifact ids; the main UI shows business-readable artifact status without raw ledger JSON, SQL, raw rows, query ids, trace, provider metadata, local paths, or tool names. P23-H6 is complete: focused and full regressions, frontend tests/build, old-path audit, tracked-artifact audit, no-key mode, and live-provider gating were verified.

P24 is complete in `docs/product/plans/2026-07-03-p24-general-business-data-understanding.md`. P24 made the product stronger for common Chinese business datasets, not just the current sample fields. P24-H1 added generic profiling and semantic-layer drafts for 门店销售、商品销售、客服/工单运营 style fields, including common time, amount/revenue, cost/spend, quantity, ID, dimension, order-count, ticket-count, and response-duration roles. P24-H2 made questions and report goals explicit evidence requirements; generic semantic-layer SQL/evidence covers rankings, contribution/share, operational efficiency, and safe same-table investment efficiency; unsupported ROI/net-return/trend/repeat-purchase/cross-table combinations become data limits instead of invented hard facts. P24-H3 proved the chain against realistic Chinese 门店、商品/品类、客户分群、客服、渠道投放、区域 datasets, fixed month-grain date filtering and same-table ROAS formula selection, fixed risk/improvement decision consistency so “优先复盘/优先处理/风险/改善” questions are not rewritten to the highest-sales entity, added deterministic report fallback when provider report validation remains partial, ran real DeepSeek analysis/report acceptance, and completed cleanup, frontend verification, old-path audit, and tracked-artifact hygiene. Report Center still writes one coherent Chinese report rather than stitched analysis answers. P24 did not add Word/PPT/PDF/飞书/企业微信/钉钉/Tencent Docs integrations; those move after the now-stable evidence ledger/artifact path.

P25 is complete in `docs/product/plans/2026-07-04-p25-real-usage-answer-report-polish.md`. It used the real manual testing issues from workspace `p24-32cc63f6` as product feedback: answer the primary metric directly, remove contradictory data limits, stop stale demo-field fallbacks, infer report titles and report shape from the user's goal, simplify the Report Center form, verify the result with realistic Chinese datasets plus opt-in live DeepSeek tests, and make missing time ranges natural in safe cases. H3 added a compact generated-data acceptance suite for the four real analysis questions and four report goals, fixed live-provider metric-fragment normalization so calculated ROI evidence is not reported as missing, reran real DeepSeek acceptance, and closed cleanup/documentation. H4 added a shared semantic/profile-backed time default policy: when users omit a time range, Analysis Workbench and Report Center default to the dataset's full available time range only when there is one safe time field, state the full date span in evidence and output, and still clarify ambiguous time fields or analysis trend grain gaps. Old paths, stale tests, unreachable compatibility branches, and template-like report-type behavior may be deleted instead of preserved.

P25-H1 is complete. Analysis Workbench now prioritizes the primary metric in the user's question, avoids contradictory data-limit wording for calculated evidence, and stops falling back to old demo schema fields when the current workspace cannot safely support a query. P25-H2 is complete. Report Center now infers report intent from the user's goal before local topic keywords, keeps broad经营复盘 and管理层经营简报 titles from being hijacked by渠道局部词, preserves specialized channel/trend titles for single-topic goals, and makes the main report form goal-first with `report_type` reduced to an internal default. P25-H3 is complete. Realistic acceptance, live DeepSeek acceptance, backend/frontend regression, old-path audit, tracked-artifact audit, and documentation closeout are done. P25-H4 is complete. A shared time default helper applies safe full-data time ranges across question understanding, evidence requirements, answers, and report metadata without introducing table-specific business rules; it now recognizes generic explicit ranges such as 最近 N 天, 近 N 个月, and 本季度, keeps trend analysis clarifications when grain is missing, and stops Report Center on ambiguous time fields instead of silently defaulting.

P26 is complete in `docs/product/plans/2026-07-04-p26-repository-cleanup-before-external-tools.md`. P26 retained historical development docs while removing generated artifact tracking and stale fixture assumptions. `data/ecommerce.db` is now treated as a generated local fixture, recreated by tests when absent, not as source.

P27 is in progress in `docs/product/plans/2026-07-04-p27-analysis-workbench-multi-agent-refactor.md`. H1 added `workspaces/analysis_contracts.py` and boundary tests for the separate Report Center path. P27 must focus on Analysis Workbench. It should consolidate duplicated analysis nodes rather than add more small agents: `question_understanding + clarification` become Data Understanding; `sql_planning + analysis_planner`, SQL candidate generation, SQL review/repair/execution/fix, and evidence payload construction become the Evidence Agent question mode; `evidence_validator + claim_typing` become the Evidence Auditor; `insight + answer_reviewer + final_answer_composer` become the Business Answer Agent; visualization becomes on-demand. Report Center must remain separate and should only receive guardrail tests proving it still uses `ReportEvidencePack + EvidenceLedger + ReportDocument`, not Analysis Workbench answer stitching.

P23-H1 through P23-H6 are complete. The shared factual payload foundation now lives in `tools/evidence_tool.build_evidence_payload()` as `p23.shared.v1`, and both Analysis Workbench `fact_payload` and Report Center `ReportEvidencePack.evidence_payloads` use it for intent, time range, metrics, dimensions, result rows, derived metrics, formula metadata, chart-ready data, warnings/data limits, and technical-detail references. Unsupported requested metrics are recorded as data limits instead of being invented. H2 polished Analysis Workbench Chinese business answers so supported facts remain evidence-bound while model explanations, hypotheses, conditional recommendations, and missing-data caveats read like natural business analysis. H3 hardened the one-pass Report Center path with shared evidence. H4 added the `p23.report_ledger.v1` EvidenceLedger, chapter coverage metadata, ledger-backed report composition/validation, and one automatic repair pass for unsupported hard facts while keeping Report Center one-pass and free of old section-answer stitching. H4's post-acceptance repair made coverage evidence-aware and added metric role selection so tables with收入、成本、ROI use收入 for contribution totals/shares/rankings, ROI-only or average/duration-only tables keep row facts without misleading SUM/share derivatives, and coverage reports only truly missing cost/profit/ROI inputs. H5 added report artifact and tool-call readiness without external SaaS: chart artifacts reference ledger facts/derived metrics, Markdown/report-document artifacts summarize ledger references, and future export tools can use artifact ids plus ledger evidence ids instead of re-querying SQL or asking the model to recalculate. H6 closed the phase with cleanup, regression, no-key verification, tracked-artifact audit, and explicit live-provider gating.

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
python3 -m pytest tests/test_p17_product_cleanup_boundaries.py tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py -q
python3 -m pytest tests/test_p26_repository_hygiene.py -q
python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py tests/test_fast_fact_path.py tests/test_analysis_route_policy.py -q
python3 -m pytest tests/test_workspace_report_runner.py tests/test_report_planner_evidence.py tests/test_report_composer_validator.py -q
python3 -m pytest tests/test_metric_tool.py tests/test_evidence_tool.py tests/test_evidence_validator.py tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q
python3 -m pytest tests/test_project_initialization.py tests/test_mcp_tool_layer.py -q
python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py -q
python3 -m pytest tests/test_p20_realistic_acceptance.py tests/test_p20_live_deepseek_acceptance.py -q
cd frontend && npm test
cd frontend && npm run build
```

Live DeepSeek tests remain opt-in. To run live acceptance locally, set `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1`, `INSIGHTFLOW_PRODUCT_LIVE_MODE=1`, `DEEPSEEK_API_KEY`, and the provider feature flags, then run the current live analysis/report acceptance tests. Without those flags and a key, live tests skip and normal regression remains deterministic. P25-H3 reran real DeepSeek acceptance with local `.env` plus explicit opt-in flags: P24/P25-style analysis/report evidence acceptance, P20 live store analysis, P12 report acceptance, and P11 workspace analysis all passed (`4 passed in 254.67s`).

## Historical / Superseded Context

The following names are retained only for cleanup history, deleted-file assertions, or low-level fixture context. They are not current product entry points or development instructions:

- Historical / Superseded: `streamlit run app.py`, `eval/run_eval.py`, `tests/test_eval_runner.py`, `tests/test_streamlit_app.py`, `chart_agent`, `visualization_planner`, `chart_tool`, `action_delivery`, `action_drafter`, `powerbi_publisher_mock`, `jira_ticket_mock`, mock SaaS, fixed template behavior, deterministic action template behavior, and keyword inference.
- Historical low-level fixture: `data/ecommerce.db` used to be tracked for schema, SQL, workflow, report, MCP, and provider regressions. It is now generated locally by tests and must not be committed.
- Historical P11/P12/P13 design specs under `docs/superpowers/specs/` are snapshots. Current implementation guidance is `docs/product/plans/`, the P16 `business_answer` contract, and the P17 cleanup plan.
