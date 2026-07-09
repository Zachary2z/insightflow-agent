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
- `docs/product/plans/2026-07-05-p28-analysis-node-consolidation.md`
- `docs/product/plans/2026-07-05-p29-fast-fact-and-risk-routing.md`
- `docs/product/plans/2026-07-06-p30-chart-artifact-and-echarts-enhancement.md`
- `docs/product/plans/2026-07-06-p31-business-lens-and-analysis-thread-memory.md`
- `docs/product/plans/2026-07-06-p32-multi-evidence-task-planning.md`
- `docs/product/plans/2026-07-07-p33-analysis-workbench-ledger-answer-cleanup.md`
- `docs/product/plans/2026-07-07-p34-real-export-tooling.md`
- `docs/product/plans/2026-07-07-p35-analysis-chart-and-ledger-reliability.md`
- `docs/product/plans/2026-07-08-p36-feishu-document-publishing.md`

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
- P27 is complete as the Analysis Workbench multi-agent architecture and latency phase. H1-H6 closed stable Analysis Workbench contracts, Report Center boundary tests, Coordinator/Data Understanding surfaces, an Evidence Agent question-mode surface, an Evidence Auditor surface, a Business Answer Agent surface, fast-path latency cleanup, a `QuestionEvidencePack` cache, conditional visualization, and final cleanup/regression/docs closeout. It primarily refactored Analysis Workbench, not Report Center. Report Center remains on its independent `ReportEvidencePack + EvidenceLedger + ReportDocument` path while Analysis Workbench is now organized around Coordinator, Data Understanding, Evidence, Evidence Auditor, Business Answer, and on-demand Visualization responsibilities.
- P28 is complete as the Analysis Workbench simplification phase. SQL planning plus analysis planning now use one Evidence Planning surface, normal successful complex answers use one Business Answer generation surface plus deterministic local checks/repair, and claim typing comes from Business Answer candidate categories with deterministic Evidence Auditor hard-fact checks. H4 removed obsolete old provider surfaces and verified backend, frontend, live provider behavior, artifact hygiene, and Report Center independence. P28 did not introduce a broad new routing system or a fully model-free fast path, and SQL review, SQL execution, evidence validation, `QuestionEvidencePack`, `AuditResult`, Chinese product output, and Report Center independence remain mandatory.
- P29 is complete as fast-fact and risk-routing stabilization before real external tool-call/export enhancement. Obvious low-risk fact questions now reliably use the fast path, ordinary business analysis wording such as 加预算/最值得/优先复盘 is not rejected as unsafe, and complex judgment/advice/report questions stay on the full evidence-backed path. External Word/PPT/PDF/Feishu/DingTalk/WeCom/Tencent Docs integrations move after this routing foundation is stable.
- P30 is complete as chart artifact and ECharts enhancement before external platform publishing. P30-H1 is complete: the product result and run-history chart artifact contract now preserves legacy PNG/SVG fields and can carry optional ECharts/image/evidence metadata. P30-H2 is complete: deterministic `ChartSpec -> ECharts option` generation now builds JSON-only options from reviewed execution/evidence rows for the initial supported chart types, with clear validation failures and table/static fallback reasons. P30-H3 is complete: Analysis Workbench chart artifacts now prefer interactive ECharts rendering when `echarts_option` is present while preserving PNG/SVG/image fallback, route-based chart generation, and run-history restoration. P30-H4 is complete: Report Center now creates the same unified ChartArtifact payload from report evidence tables, stores it on the report record, renders ECharts in the report web detail view, and keeps Markdown/download on static SVG/image fallback. P30-H5 is complete: `workspaces.export_package` builds safe internal export packages from Report Center records and Analysis Workbench product results for future connector consumption without exposing raw SQL, trace paths, provider metadata, API keys, database paths, or local absolute paths. P30-H6 added focused acceptance and opt-in live DeepSeek verification proving Analysis Workbench charts, Report Center chart artifacts, static fallback, and export packages are stable enough for later connector work.
- P31 is complete as the Business Lens and Analysis Thread Memory phase before external connector work. H1 kept question understanding as the natural-language front door and added Business Lens grounding for semantic-layer-validated business口径, source fields, per-metric time-field bindings, safe default time policy, clarification state, and data limits. H2 made waiting-clarification and completed follow-ups update the same analysis thread/run. H3 added the lightweight Analysis Workbench `question_evidence_ledger` and wired it into Business Answer, Evidence Auditor, product results, chart refs, and thread memory. H4 polished the frontend into one coherent thread view with original question, system understanding, resolved question, turns, time口径, business answer, ledger/evidence summary, chart artifacts, compact history, and same-thread follow-up forms; it also deleted the old active `pending_run_id`/`PendingClarificationStore` continuation path and kept only a negative API boundary test for the superseded request shape. The opt-in live pytest suite stayed gated by flags, while a manual real DeepSeek check with a configured key proved same-thread follow-up works and exposed the next issue: complex multi-metric questions can fail when the provider emits multiple SQL statements in one candidate, which P32 is designed to solve safely.
- P32 is complete as the Analysis Workbench multi-evidence task phase before external connector work. H1 kept the low-latency fast-fact route and added compact Evidence Task contracts plus deterministic planning metadata for standard/deep questions that need more than one result. H2 added the Analysis Workbench evidence task runner for cross-table multi-core evidence plans: each task goes through one SQL candidate, SQL review, optional existing repair/fix paths, approved SQL execution, and evidence validation; successful task evidence merges into the lightweight question evidence ledger with task provenance, while failed tasks become data limits. H3 polished the product surface so multi-task evidence still reads as one business answer, evidence summaries group facts as business-readable evidence blocks, internal task ids/ledger refs/raw chart JSON stay out of the main UI, chart artifacts inherit evidence refs where possible, same-thread/history restoration preserves multi-task ledgers and charts, and Report Center remains independent on `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument`. Post-review live testing confirmed explicit multi-task chart requests now produce ECharts grouped-bar artifacts and no longer leak internal task ids; remaining follow-up work is answer-strategy polish for complex risk/optimization questions, explicit live-provider Report Center prose acceptance, and latency improvement before external connector integration.
- P33 is complete as the Analysis Workbench closeout phase before external connector work. It makes the clean Analysis Evidence Ledger the only input source for user-facing answer generation, requires every final conclusion including fast facts to be model-written from ledger evidence rather than deterministic templates, combines overlapping Question Understanding and Business Lens responsibilities, routes Standard vs Deep by evidence complexity instead of keyword templates, downgrades Product Result Builder into a product-payload assembler, deletes old conflicting answer-rewrite paths, and allows chart generation to run from ledger/sanitized evidence without polluting the main answer.
- P34 is complete as the first real export tooling phase. `workspaces.export_package` exposes the P34 unified safe output contract for Report Center and Analysis Workbench, chart artifacts can be projected to safe static assets for document insertion, Report Center export packages render into real local Word `.docx` files, and the Report Center UI can trigger/download Word export through the backend API. Report content structure follows the generated `ReportDocument`; export tools only provide stable document layout and file generation. P34 does not re-plan, rewrite, or template report content, and does not restore simulated SaaS/action/chart paths.
- P35 is complete as the Analysis Workbench evidence-planning and chart-reliability phase before deeper external-tool work. Analysis Workbench now plans question-level evidence first, keeps evidence grouped by business purpose/dimension/metric/grain/source, lets the model write from an answer-safe grouped ledger, preserves valid model-written answers during audit, selects charts from coherent evidence groups/subsets, and deletes/narrows old broad ledger/chart/row-derived answer paths.
- P36 is complete as the first real external platform publishing phase. H1-H6 proved that existing Report Center `ReportDocument` output can be published to real Feishu Docs through the open-source `lark-cli`, using `p34.export_package.v1` and P30/P34 chart static assets as the handoff. The Feishu body avoids a duplicate top-level report title, keeps evidence tables near their sections without flooding the Feishu outline, and inserts PNG/JPEG/GIF chart images at matching anchors. H7 adds an optional companion Feishu Sheet from the same export package for editable evidence tables and native Feishu sheet charts when a safe bar/line mapping exists. The publisher remains a delivery tool only: it does not call the LLM, rewrite reports, stitch Analysis Workbench answers, introduce fixed report templates, generate chart data, run Sheet-side re-analysis, query databases directly for Sheet export, or restore simulated SaaS/action paths. P36 keeps the interface ready for a later direct Feishu OpenAPI publisher while proving the product can call real business document/spreadsheet tools now.

Current runtime chain:

```text
workspace import
-> profile and semantic layer
-> Question Understanding + Business Lens grounding
-> clarification router
-> route by evidence complexity
-> evidence task planning metadata
-> Evidence Planning
-> guarded SQL candidate
-> SQL review
-> schema repair
-> SQL execution
-> evidence validation
-> Analysis Evidence Ledger
-> Analysis Thread Memory update
-> model-written business answer from ledger only
-> key-fact audit and minimal repair
-> optional visualization / ChartArtifact
-> Product Result Builder assembly
-> save analysis result
-> independent report path when requested
-> optional Report Center external publishing through export package
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
| P27 | Analysis Workbench multi-agent refactor: consolidate duplicated analysis nodes, make tool-calling/evidence boundaries clearer, lower latency, and protect the separate Report Center path | Complete; H1-H6 complete |
| P28 | Analysis Workbench node consolidation: merge repeated planning, answer-generation, and claim-classification provider calls while preserving evidence/tool boundaries and Report Center independence | Complete; H1-H4 complete |
| P29 | Fast fact and risk routing stabilization: make simple facts reliably fast, reduce false business-risk rejection, and preserve full path for judgment/advice/report questions before external tool integrations | Complete; H1-H4 complete |
| P30 | Chart artifact and ECharts enhancement: unify chart artifacts, render interactive ECharts charts, preserve static fallbacks, and prepare report/platform export payloads | Complete; H1-H6 complete |
| P31 | Business Lens and Analysis Thread Memory: ground model intent into current data口径, bind per-metric time fields, add lightweight question evidence ledger, and keep follow-ups in one coherent analysis thread | Complete; H1-H4 complete |
| P32 | Multi Evidence Task Planning: let Analysis Workbench answer complex multi-metric questions with several safe evidence tasks while preserving the fast-fact path and Report Center independence | Complete; H1-H3 complete |
| P33 | Analysis Workbench ledger answer cleanup: finish the answer path so all conclusions are model-written from Evidence Ledger, Standard/Deep routing uses evidence complexity, old template/rewrite paths are deleted, Product Result Builder only assembles, and charts consume ledger/sanitized evidence | Complete; H1-H3 complete |
| P34 | Real export tooling: safe export packages, static chart assets, backend Word export API, frontend download flow, and real local `.docx` export without report rewriting or simulated SaaS connectors | Complete; H1-H4 complete |
| P35 | Analysis Workbench evidence planning and chart reliability: add question-level evidence plans, grouped ledgers, grouped answer generation/audit, coherent chart selection, ECharts polish, and delete conflicting old broad-projection/template paths | Complete; H1-H4 complete |
| P36 | Feishu document publishing: publish existing Report Center reports to real Feishu Docs through `lark-cli`, insert safe chart static assets, persist publish artifacts, polish Feishu document layout/section chart placement, and add an optional companion Feishu Sheet for editable evidence/native charts while keeping old simulated connector/template paths deleted | Complete; H1-H7 complete |

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

P27 is complete in `docs/product/plans/2026-07-04-p27-analysis-workbench-multi-agent-refactor.md`. H1 added `workspaces/analysis_contracts.py` and boundary tests for the separate Report Center path. H2 added `workspaces/data_understanding_agent.py` and `workspaces/analysis_coordinator.py`, adapting existing question understanding, clarification, continuation, safe full-data time defaults, and route policy output into H1 `AnalysisTask` and `CoordinatorDecision` contracts on the Analysis Workbench main path. H3 added `workspaces/evidence_agent.py`, routing the Analysis Workbench evidence acquisition segment through an Evidence Agent question mode that emits `QuestionEvidencePack` and `WorkbenchToolCall` records while preserving SQL review, one-pass schema repair, reviewed execution, and Report Center independence. H4 added `workspaces/evidence_auditor.py` and `workspaces/business_answer_agent.py`: Analysis Workbench now emits H1 `AuditResult` on fast and standard/deep paths, keeps hard facts grounded in `QuestionEvidencePack`/evidence validation, preserves reasonable explanations and recommendations as evidence-bounded inferences, keeps fast_fact lightweight, and keeps complex answers on the insight/reviewer/final-composer quality path. H5 added latency optimization: semantic metric ids such as `sum_sales_amount` no longer disqualify a single-metric fast fact, fast facts still avoid the heavy insight/reviewer/final composer path, `QuestionEvidencePack` cache hits reuse only successfully reviewed and executed evidence for the same workspace/data version/semantic-layer fingerprint/normalized task, explicit `initial_sql` bypasses cache, and visualization is now on-demand rather than unconditional. H6 removed obsolete Analysis Workbench graph node wrappers and route helpers that were made unreachable by the Evidence Agent, cleaned misleading compatibility naming in Data Understanding, removed obsolete action/report/weekly report state fields, and updated cleanup boundary tests to protect the current P27 graph. Report Center remains separate and still uses `ReportEvidencePack + EvidenceLedger + ReportDocument`, not Analysis Workbench answer stitching.

P28 is complete in `docs/product/plans/2026-07-05-p28-analysis-node-consolidation.md`. P28 is a conservative Analysis Workbench node-consolidation phase. It reduced repeated provider calls without replacing the current product with ambiguous routing branches. The current normal complex path is: question understanding, clarification, one Evidence Planning surface, data-context/schema/metric lookup, guarded SQL candidate, SQL review, SQL execution, evidence validation, one Business Answer generation surface, deterministic Evidence Auditor, optional visualization, and save. P28-H1 consolidated SQL planning plus analysis planning into `agents/evidence_planning.py` on the active Analysis Workbench path. P28-H2 consolidated insight drafting, answer review, and final answer composition into the Business Answer Agent normal path while retaining deterministic local answer repair and candidate claims for audit. P28-H3 made Business Answer candidate claim categories the main classification source while Evidence Auditor deterministically checks hard facts and keeps recommendations/inferences as reasonable business judgment. P28-H4 removed obsolete `agents/insight_agent.py`, old answer provider runtime flags/builders, old provider prompt surfaces, and active state compatibility writes. Historical / Superseded by P33-H2: the old statement that `agents/final_answer_composer.py` remained as a deterministic guardrail is no longer current; P33-H2 deleted that module and moved chart annotation leak scrubbing to `workspaces/chart_annotation_safety.py`. Report Center remains independent throughout.

P29 is complete in `docs/product/plans/2026-07-05-p29-fast-fact-and-risk-routing.md`. It addressed the live P28 finding that obvious factual questions such as “最近N天哪个渠道收入最高？” and “本月哪个门店销售额最高？” could still take the full standard path, while safe factual wording such as “只回答数字和口径” or business-analysis wording such as “加预算/最值得/优先复盘” could be over-rejected. P29 added a conservative local fast-fact gate, stabilized the fast fact execution path, split business advice risk from real external action risk, and added deterministic plus opt-in live DeepSeek acceptance with variable time ranges such as 最近30天, 最近90天, 本月, and omitted time ranges that safely default to full available data when the workspace has one safe time field.

P30 is complete in `docs/product/plans/2026-07-06-p30-chart-artifact-and-echarts-enhancement.md`. P30-H1 completed the unified chart artifact contract and compatibility layer: legacy `title`/`path`/`url`/`rendering_status`/`unit`/`value_label`/`business_annotation` fields stay intact, optional `artifact_id`/`renderer`/`chart_type`/`chart_spec`/`echarts_option`/`image_path`/`image_url`/`evidence_refs`/`source`/`data_row_count` fields pass through product results and run-history rebuilds. P30-H2 added `visualization/echarts_option_builder.py`, a deterministic builder that converts reviewed execution/report evidence rows into JSON-only ECharts options for `ranked_bar`, `bar`, `line`, `grouped_bar`, `scatter`, and `dual_axis_line`; `table`, missing columns, empty rows, non-numeric numeric roles, unsupported chart types, and unsafe JavaScript-like/SQL-like/path-like/trace-provider metadata text fail or fall back clearly without exposing SQL/trace/provider/local path metadata. P30-H3 connected those options to the active Analysis Workbench chart chain: Visualization Agent enriches successful local static charts with ECharts metadata, builder failures keep the static image and record the reason in trace metadata, and `ChartArtifactGallery` renders ECharts in a client-only component before falling back to PNG/SVG/image. Route policy remains `fast_fact` only on explicit chart request, `standard_analysis`/`deep_judgment` when evidence is chartable, and no charts for `clarify`/`reject`. P30-H4 connected Report Center to the same chart artifact contract without calling Analysis Workbench: report evidence tables produce deterministic ECharts options plus SVG/image fallback, report records expose `chart_artifacts`, the report web detail view reuses `ChartArtifactGallery`, and Markdown/download output keeps static image links without raw option/spec JSON. P30-H5 added the internal `ExportPackage` contract and builders for report records and analysis product results; packages preserve ECharts metadata plus image fallback assets, evidence refs, and warning-only behavior for missing static fallbacks while excluding SQL/trace/provider/local-path secrets. P30-H6 closed the phase with focused acceptance, full regression, frontend test/build, old-path and artifact-hygiene audits, and real DeepSeek chart/report/export verification.

P31 is complete in `docs/product/plans/2026-07-06-p31-business-lens-and-analysis-thread-memory.md`. P31 paused external connector implementation long enough to fix two real-use Analysis Workbench gaps found in manual testing: ambiguous time-field prompts and fragmented follow-up runs. The current path starts with question understanding LLM/provider/fallback, grounds the result through Business Lens, continues through Evidence Planning, guarded SQL candidate, SQL review, schema repair, SQL execution, evidence validation, lightweight Question Evidence Ledger, Business Answer, deterministic Evidence Auditor, optional ChartArtifact generation, same-thread memory update, and save/history display. Follow-ups from both waiting clarification and completed answers now use `POST /api/workspaces/{workspace_id}/runs/{run_id}/follow-ups`, update the same run/thread, and preserve prior turns. The frontend shows one coherent analysis thread with time口径, ledger/evidence summary, chart artifacts, compact history, and a follow-up form scoped to the current analysis. Report Center remains independent on its `ReportEvidencePack + EvidenceLedger + ReportDocument` path and does not call Analysis Workbench report/answer stitching. Old duplicate-run follow-up behavior, the active `pending_run_id` continuation branch, `PendingClarificationStore`, and stale tests for obsolete behavior are deleted or rewritten; the only remaining `pending_run_id` code hit is a negative API boundary test proving the superseded request shape is rejected.

## P28 Task Status

| Task | Status | Notes |
|---|---|---|
| P28-H1 | `[x]` Complete | Evidence Planning consolidation: replaced separate SQL planning and analysis planning provider calls with one validated planning surface |
| P28-H2 | `[x]` Complete | Business Answer consolidation: normal complex answers use one provider-backed business-answer generation surface plus deterministic checks |
| P28-H3 | `[x]` Complete | Claim typing and Evidence Auditor simplification: Business Answer emits claim categories; Evidence Auditor validates hard facts deterministically by default |
| P28-H4 | `[x]` Complete | Cleanup, regression, live DeepSeek verification, artifact hygiene, old-path audit, and docs closeout |

## P29 Task Status

| Task | Status | Notes |
|---|---|---|
| P29-H1 | `[x]` Complete | Local Fast Fact Gate before provider risk rejection; obvious safe factual totals/rankings/trends can proceed without full-path overclassification, provider alias duplicates are canonicalized, and true external actions are not fast-pathed |
| P29-H2 | `[x]` Complete | Historical fast-fact execution stabilization; P33 supersedes the old provider-skip answer behavior so fast facts now use BusinessAnswerAgent after lightweight evidence prep |
| P29-H3 | `[x]` Complete | Business risk policy split: normal advice/judgment analysis is allowed with evidence boundaries; provider false safety rejects are relaxed for analysis/advice; real external actions, sensitive access, bulk export, and unsafe writes/deletes stop before SQL |
| P29-H4 | `[x]` Complete | Deterministic and opt-in live DeepSeek acceptance using variable time ranges, recorded times, route, provider calls, answer, evidence rows, and chart behavior |

## P30 Task Status

| Task | Status | Notes |
|---|---|---|
| P30-H1 | `[x]` Complete | Defined the unified `ChartArtifact` contract, preserved legacy PNG/SVG image fields, added optional ECharts/image/evidence metadata, and kept run-history/frontend image fallback compatibility |
| P30-H2 | `[x]` Complete | Added deterministic `ChartSpec -> ECharts option` generation and validation from reviewed execution/report evidence rows |
| P30-H3 | `[x]` Complete | Render ECharts interactively in Analysis Workbench and keep image fallback behavior |
| P30-H4 | `[x]` Complete | Report Center creates and stores unified chart artifacts from report evidence tables while preserving static SVG/image fallback |
| P30-H5 | `[x]` Complete | Preserve static export fallback and add an internal export package contract for future platform connectors |
| P30-H6 | `[x]` Complete | Focused P30 acceptance, frontend verification, cleanup, artifact hygiene, and opt-in live DeepSeek chart/report/export verification |

## P32 Task Status

| Task | Status | Notes |
|---|---|---|
| P32-H1 | `[x]` Complete | Added compact `EvidenceTask`, `EvidenceTaskPlan`, and `EvidenceTaskResult` contracts plus deterministic Business Lens based planning metadata; fast facts remain one high-priority one-task route |
| P32-H2 | `[x]` Complete | Added the Analysis Workbench evidence task runner for cross-table multi-core plans, one reviewed SQL per task, safe multi-statement rejection, default/configurable parallelism of 3, partial task-failure data limits, and merged task-aware question evidence ledgers |
| P32-H3 | `[x]` Complete | Product acceptance, frontend/evidence-summary polish, chart/evidence ref binding, same-thread/history restoration hardening, real DeepSeek verification, cleanup audit, and Report Center independence audit |

## P33 Task Status

| Task | Status | Notes |
|---|---|---|
| P33-H1 | `[x]` Complete | Defined the ledger-only answer input contract, made fast facts enter the Business Answer provider seam after evidence prep, removed the old fast_fact composer path, and changed Standard/Deep routing to evidence complexity instead of keyword templates |
| P33-H2 | `[x]` Complete | Removed active template/rewrite answer paths, downgraded Product Result Builder to an assembler, and kept repair limited to unsupported-fact/internal-leak cleanup or clear answer-generation failure |
| P33-H3 | `[x]` Complete | Chart generation consumes ledger/sanitized evidence; P33 repair tightened live acceptance, same-thread follow-up, provider-output tolerance, no-key fallback boundaries, and old-path/no-leak regression |

P34 planning is recorded in `docs/product/plans/2026-07-07-p34-real-export-tooling.md`. P34 is complete as the first real business delivery/export phase after P33: Analysis Workbench and Report Center project safe export packages, chart artifacts have static asset fallbacks for document insertion, Report Center export packages render to real local `.docx`, and the Report Center UI can trigger and download Word export through the backend API. The report content structure follows the existing `ReportDocument` generated by Report Center: title, opening summary, ordered sections, recommendations, data boundaries, charts, and evidence refs. The export tool owns only layout and file generation: typography, heading levels, margins, chart placement, evidence appendix, and download packaging. It does not call the LLM, rewrite conclusions, force fixed business chapters, stitch Analysis Workbench answers into reports, or restore old mock/action/chart paths. External Feishu/DingTalk/WeCom/Tencent Docs/Power BI publishing remains deferred after local export tools.

## P34 Task Status

| Task | Status | Notes |
|---|---|---|
| P34-H1 | `[x]` Complete | Export Package is now `p34.export_package.v1` with `source_type` `report`/`analysis`, `generated_at`, document/business summary, ordered report sections, action recommendations, data boundaries, chart/static assets, evidence summary/refs, and warnings; unsafe SQL/rows/trace/provider/secret/path/task/prompt fields are stripped |
| P34-H2 | `[x]` Complete | `workspaces.chart_static_export` reuses safe PNG/SVG/image assets and generates workspace-relative SVG fallbacks from existing ECharts options when possible; missing data/root returns warnings only |
| P34-H3 | `[x]` Complete | `workspaces.document_export` renders report export packages into local Word `.docx` files using existing ReportDocument content, safe chart assets or placeholders, recommendations, data boundaries, and evidence appendix |
| P34-H4 | `[x]` Complete | Report export API, frontend Word download entry, warning/failure states, acceptance, real DeepSeek report-to-docx verification, and cleanup |

P35 planning is recorded in `docs/product/plans/2026-07-07-p35-analysis-chart-and-ledger-reliability.md`. P35 is complete as the focused Analysis Workbench reliability phase before external-tool work. It responded to manual testing in workspace `p30-echarts-28ece8e6`, where chart artifacts could mix unrelated objects, metric labels could be swapped by ledger projection order, and a mostly valid model-written answer could be reduced to `业务回答缺失` after overly strict review. The fix was to learn Report Center's evidence organization, not its report templates: Analysis Workbench now adds a question-level `QuestionEvidencePlan`, keeps evidence in grouped ledger sections by purpose/source/dimension/metric/grain/time policy, passes only answer-safe grouped evidence to the model, validates hard facts afterward, and generates charts from one coherent evidence group or compatible metric subset. Product Result Builder remains an assembler, final answers remain model-written from evidence, ECharts options remain deterministic from reviewed evidence rows, and Report Center stays independent on `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument`. Old broad chart-safe-table projection, stale row-derived answer behavior, fixed answer templates, and compatibility paths that conflict with this current path were deleted or narrowed instead of preserved.

## P35 Task Status

| Task | Status | Notes |
|---|---|---|
| P35-H1 | `[x]` Complete | Question Evidence Plan and grouped ledger: introduced question-level evidence groups, source-column/semantic-role metric labels, chartability metadata, grouped answer input, and narrowed broad chart-safe projection |
| P35-H2 | `[x]` Complete | Grouped answer generation and non-destructive audit: provider input requires answer-safe grouped ledger evidence, unsupported auxiliary hard facts are removed/softened without erasing supported conclusions, and no-provider mode no longer composes ledger/row-derived prose |
| P35-H3 | `[x]` Complete | Grouped chart selection, ECharts polish, acceptance, and cleanup: charts consume one coherent grouped-ledger candidate, legends/titles/axes are business-readable, and old broad task-row chart fallbacks are removed/narrowed |
| P35-H4 | `[x]` Complete | Live-closeout repair: fast-fact top-N evidence, compatible metric-subset charts, Product Result answer preservation, metric-label/source compatibility fixes, safe-review rewrite, and real DeepSeek acceptance |

P36 planning is recorded in `docs/product/plans/2026-07-08-p36-feishu-document-publishing.md`. P36-H1 through P36-H7 are complete. It publishes existing Report Center reports to real Feishu Docs through `lark-cli`, using the current `ReportDocument` and `p34.export_package.v1` as the source of truth. Publishing remains separate from report generation: no LLM call, no SQL execution, no report rerun, no report rewriting, no fixed report chapters, no Analysis Workbench answer stitching, and no simulated SaaS connector success. Interactive ECharts stays in the InsightFlow UI; Feishu Docs receive complete report Markdown including evidence tables plus safe local PNG/JPEG/GIF chart images when available, and H7 can create a companion Feishu Sheet from export-package evidence tables for editable data plus safe native bar/line charts. If Sheet creation or chart mapping fails, the Doc publish is preserved with warning. Old `action_delivery`, mock SaaS publisher, old chart agent/planner/tool, and template-like publish paths remain deleted or historical/superseded documentation and negative tests only.

## P36 Task Status

| Task | Status | Notes |
|---|---|---|
| P36-H1 | `[x]` Complete | Feishu publisher contract and CLI adapter: `ExternalPublishResult`, `CliFeishuPublisher`, safe command runner, CLI availability/auth failures, JSON parsing, safe serialization, and Report Center package-only guard |
| P36-H2 | `[x]` Complete | Report Center publish API and UI: `POST /reports/{report_id}/publish/feishu`, safe `external_publish_results.feishu` persistence, `发布到飞书` frontend states, and no report rewrite |
| P36-H3 | `[x]` Complete | Chart image insertion: reuse P34 static chart assets, insert local PNG/JPEG/GIF images through Feishu CLI media commands, count inserted/failed charts, and preserve document success with warnings when chart insertion fails |
| P36-H4 | `[x]` Complete | Acceptance, live Feishu verification gate, docs, and cleanup: deterministic Report Center export -> CliFeishuPublisher -> create -> PNG insert path, frontend safe summary display, default-skipped live test, artifact hygiene, and old-path audit |
| P36-H5 | `[x]` Complete | Live-test repair: publish full report Markdown/evidence tables to Feishu Docs, generate/reuse Feishu-safe PNG chart fallbacks from existing ECharts/chart artifacts, show safe warnings, and replace the conflicting simplified publish body path |
| P36-H6 | `[x]` Complete | Feishu document layout polish: removed duplicate body title, rendered evidence tables as section-local body labels instead of noisy outline headings, inserted chart images at matching section anchors, kept safe warnings, and replaced the old append-only active path |
| P36-H7 | `[x]` Complete | Feishu Sheet companion: writes export-package evidence tables to an optional workbook, creates native sheet charts only for safe bar/line mappings, links the Sheet from the Doc, persists safe counts/warnings, and preserves Doc success if Sheet fails |

## Latest P36-H7 Result

P36-H7 completes the hybrid publishing enhancement. The runtime remains `ReportDocument -> p34.export_package.v1 -> CliFeishuPublisher`; Feishu Docs are still the formal report reading page. A companion `CliFeishuSheetPublisher` can create a Feishu Sheet workbook with `lark-cli sheets +workbook-create`, write sanitized `evidence_tables` with `sheets +table-put`, and create native charts with `sheets +chart-create` only when a chart artifact is a simple bar/line chart that maps clearly to an existing category column and numeric value column. Unclear charts are skipped with safe warnings, not model-generated chart data. The document body receives one concise `可编辑数据和图表` link section when the Sheet exists, and does not duplicate all Sheet tables back into the Doc. `external_publish_results.feishu` now persists safe Sheet URL/id/token, written table count, native chart count, and Sheet warnings; frontend Report Center displays the Doc link, optional Sheet link, counts, and filtered warnings. H7 did not call the LLM, execute SQL, rerun Report Runner, rewrite reports, query databases for Sheet export, or restore old mock/fake-success connector paths. Verification passed: `tests/test_feishu_sheet_publisher.py tests/test_feishu_publisher.py tests/test_workspace_report_api.py` (`54 passed`), `tests/test_export_package.py tests/test_chart_static_export.py` (`19 passed`), `frontend/tests/workspace-flow.test.tsx` (`66 passed`), `cd frontend && npm run build`, and `git diff --check`. Live Feishu verification was not run in this pass.

## Latest P36-H6 Result

P36-H6 makes the Feishu output feel like a readable business report rather than an exported artifact bundle. The path is still `ReportDocument -> p34.export_package.v1 -> CliFeishuPublisher`; it does not call the LLM, execute SQL, rerun Report Runner, rewrite reports, stitch Analysis Workbench answers, generate chart data, or introduce fixed templates. The change is layout projection only: Feishu owns the document title, the body begins with business-readable metadata and report content, evidence tables stay beside their report sections without becoming noisy `###` outline entries, and each chart image is inserted at its matching `图表：...` anchor through `lark-cli docs +media-insert --selection-with-ellipsis` when available. A post-H6 real document readback found that report chart artifacts can use wrapped ids such as `artifact_chart_<chart_id>` while sections reference the shorter `chart_id`; the export package now preserves `chart_id`, `chart_ids`, and `source_chapter_id` from `ReportEvidencePack.charts`, and the Feishu publisher matches section `chart_refs` against those aliases before falling back to `图表说明`. If chart placement fails, the report remains published with a safe warning and no raw command output, local path, SQL, trace, provider metadata, prompt, or token leak. Verification passed: `python3 -m pytest tests/test_feishu_publisher.py tests/test_workspace_report_api.py tests/test_chart_static_export.py tests/test_export_package.py -q` (`66 passed`). Live Feishu verification was not run in this repair pass.

## Latest P36-H5 Result

P36-H5 Feishu Tables And PNG Chart Repair completed on 2026-07-08. Live Feishu testing had proved `lark-cli docs +create` works with a real account, but the published document was incomplete: local `report.md` contained evidence tables while `CliFeishuPublisher._package_to_markdown()` published a simplified Markdown body without those tables, and report chart artifacts could be SVG-only while `docs +media-insert` accepts only local PNG/JPEG/GIF images.

- Feishu publishing now renders the existing report/export package into complete Markdown: title, metadata, summary, section bodies, business-readable evidence tables from `ReportEvidencePack.tables`, chart captions, recommendations, and data boundaries.
- Evidence tables come from the already computed evidence package via safe `evidence_tables` in `p34.export_package.v1`; cells escape pipes/newlines, large tables are capped with `仅展示前 10 行`, and raw SQL/rows/provider/trace/debug fields stay out of the document body.
- Chart static export can prepare local PNG assets from existing chart artifacts/ECharts options when the Feishu publish API requests `static_asset_target_format="png"`. The default static export path still preserves SVG/ECharts for web, Markdown, and Word fallback.
- `CliFeishuPublisher` still only inserts workspace-root-safe local PNG/JPEG/GIF files. SVG, URL-only, unsafe, unsupported, or missing assets become clear safe warnings and never fake successes.
- Frontend warning display no longer hides every chart problem if detailed warnings are safety-filtered; it shows `部分图表未插入飞书文档。` when failed chart counts remain.
- P36-H5 did not add Feishu Sheets/Base native chart creation, did not call the LLM, did not execute SQL, did not rerun Report Runner, did not rewrite reports, and did not publish Analysis Workbench answers as reports.
- Verification passed: `tests/test_feishu_publisher.py tests/test_workspace_report_api.py tests/test_chart_static_export.py` (`54 passed`), `tests/test_export_package.py tests/test_document_export.py` (`17 passed`), and `frontend/tests/workspace-flow.test.tsx` (`66 passed`). Live Feishu verification was not run in this repair pass.

## Latest P36-H4 Result

P36-H4 Acceptance, Live Feishu Verification, Docs, And Cleanup completed on 2026-07-08:

- Added deterministic acceptance for the full Report Center publish path: existing report record -> `build_report_export_package()` -> `CliFeishuPublisher` with fake runner -> official `docs +create` -> local PNG `docs +media-insert` -> safe API response persisted under `external_publish_results.feishu`.
- The acceptance test blocks publish-time SQL connections and report composer provider access, then verifies the original `ReportDocument` remains unchanged and no Analysis Workbench `business_answer` is published as a report.
- Safe-result assertions cover stdout/stderr, absolute paths, SQL, raw rows, trace, provider metadata, prompts, tokens, secrets, and local temp paths.
- Frontend coverage now proves `ReportViewer` displays only publish status, Feishu link, inserted/failed chart counts, and safe warnings; malicious warnings/tool-call metadata are filtered from the rendered UI.
- Added `tests/test_feishu_live_publish.py`, default skipped unless `INSIGHTFLOW_FEISHU_LIVE=1` and `LARK_CLI_BIN` are set. The live test creates a minimal Chinese report package with a local PNG chart, calls real `CliFeishuPublisher.publish_report()`, asserts URL/document id/insert attempt, optionally fetches back content with `docs +fetch`, and prints only a safe boolean/count summary.
- Official commands used in P36 are `lark-cli docs +create --doc-format markdown --title <title> --content <markdown>`, `lark-cli docs +media-insert --doc <document_id> --file <file> --type image --align center --caption <caption> --width 800`, and optional `lark-cli docs +fetch --doc <document_id> --doc-format markdown`.
- Artifact hygiene was tightened with explicit ignore rules for generated databases and workspace runs/reports. No real Feishu link, document id, trace, token, generated database, generated report, or generated chart artifact is committed by H4.
- Old-path audit found only historical/superseded documentation, negative boundary tests, or provider rejection tests for chart-agent/planner/tool, action delivery, mock SaaS, and fake-success wording.
- Live Feishu verification was not run during deterministic closeout unless the local machine sets `INSIGHTFLOW_FEISHU_LIVE=1 LARK_CLI_BIN=lark-cli`.

## Latest P36-H3 Result

P36-H3 Chart Image Insertion From ECharts Static Assets completed on 2026-07-08:

- `CliFeishuPublisher` now runs publishing as create-first plus post-create chart insertion. It reads existing `static_assets` from the Report Center export package and does not recalculate chart data.
- Eligible chart assets are local PNG/JPEG/GIF files validated under the workspace root. SVG, URL-only, missing, unsafe, or unsupported assets produce safe warnings and `failed_chart_count`; they are not treated as inserted.
- The official commands used are `lark-cli docs +create --doc-format markdown --title <title> --content <markdown>` and `lark-cli docs +media-insert --doc <document_id> --file <safe local file> --type image --align center --caption <caption> --width 800`.
- If `docs +create` returns a `/wiki/...` URL, chart insertion still uses the returned `document_id` rather than the wiki URL.
- Create failure returns `failed`. Create success plus complete chart insertion returns `published`. Create success plus any chart insertion/asset failure returns `warning`, preserving the document URL and id.
- `ExternalPublishResult.to_safe_dict()` safely serializes `inserted_chart_count`, `failed_chart_count`, `warnings`, and compact `tool_calls` for `create_document` / `insert_chart_image` without raw stdout/stderr, absolute paths, SQL, rows, trace, provider metadata, prompts, tokens, or secrets.
- Report Center displays the inserted/failed chart counts while continuing to hide internal tool call details.
- H3 did not call an LLM, rewrite reports, rerun SQL, regenerate reports, publish Analysis Workbench answers as reports, add live Feishu verification, or restore old simulated connector/action paths.

## Latest P36-H2 Result

P36-H2 Report Center Publish API And UI completed on 2026-07-08:

- Added `POST /api/workspaces/{workspace_id}/reports/{report_id}/publish/feishu`, backed by a small `_build_feishu_publisher()` factory for tests.
- The endpoint loads an existing `ReportRecord`, builds `p34.export_package.v1` with `build_report_export_package()`, calls `CliFeishuPublisher.publish_report()`, persists `ExternalPublishResult.to_safe_dict()` under `external_publish_results.feishu`, and returns that same safe result.
- Publisher business failures return `200` with `status="failed"` and readable warnings; missing report ids return clear `404`; only unexpected program errors become `500`.
- `ReportRecord` now serializes/restores `external_publish_results`, so report detail reloads can show the latest Feishu publish state.
- `frontend/lib/api.ts` adds `ExternalPublishResult`, `WorkspaceReportPublishResponse`, and `publishFeishuReport()`. `ReportViewer` adds `发布到飞书` with idle/publishing/published/warning/failed states and displays only safe status/link/warnings.
- H2 did not modify the official H1 `lark-cli docs +create --doc-format markdown --title <title> --content <markdown>` command, did not add chart insertion, did not do live Feishu verification, did not call the LLM, did not rewrite reports, did not rerun Report Runner, and did not restore old mock/action paths.
- Verification passed:
  - `python3 -m pytest tests/test_feishu_publisher.py tests/test_workspace_report_api.py -q` (`34 passed`)
  - `python3 -m pytest tests/test_export_package.py tests/test_workspace_report_runner.py tests/test_document_export.py -q` (`37 passed`)
  - `cd frontend && npm test` (`81 passed`)
  - `cd frontend && npm run build` passed

## Latest P36-H1 Result

P36-H1 Feishu Publisher Contract And CLI Adapter completed on 2026-07-08:

- Added `workspaces/external_publishing.py` with `ExternalPublishResult`, `FeishuPublisher`, report-package validation helpers, and safe serialization for external publish artifacts.
- Added `workspaces/feishu_publisher.py` with `CliFeishuPublisher`, `CommandRunner`, `SubprocessCommandRunner`, and `CommandExecutionResult`. The CLI binary is controlled by `LARK_CLI_BIN` and defaults to `lark-cli`.
- The adapter consumes existing `p34.export_package.v1` Report Center packages only, renders package content into Markdown, centralizes the official `lark-cli docs +create --doc-format markdown --title <title> --content <markdown>` command, parses official nested `ok/data.document` JSON plus legacy flat document fields, and returns `published`, `warning`, or `failed` without fake success.
- Failure handling covers missing/unexecutable CLI, runner exceptions, non-zero exit codes, invalid/non-JSON stdout, official `ok=false`, official `ok=true` missing `data.document`, and success JSON missing `document_id` or URL. Tool calls are safe summaries only.
- Package validation is strict: inputs must explicitly carry `package_version == p34.export_package.v1` and `source_type == report`; dicts missing `package_version` are rejected.
- Safe serialization strips or rejects local absolute paths, token/secret/API key markers, raw stdout/stderr, raw SQL/rows, trace paths, provider metadata, prompts, and other debug fields.
- H1 did not add Report Center API/UI, chart insertion, direct Feishu OpenAPI, live Feishu tests, other platform connectors, LLM calls, report rewriting, fixed templates, or old mock/action paths.

## Latest P35-H1 Result

P35-H1 Question Evidence Plan And Grouped Ledger completed on 2026-07-07:

- `question_evidence_ledger` now carries a compact `question_evidence_plan` plus `evidence_groups` as the primary contract. Each group records `group_id`, purpose, source tables/fields, dimension role/label/source columns, metric role/label/source column/source fields/unit, time policy, row grain, answer/chart support, evidence refs, facts, and derived metrics.
- Legacy top-level `facts`, `derived_metrics`, and `tables` remain as compatibility projections, but Business Answer prompt input now uses answer-safe grouped evidence only. The answer projection remaps group/evidence refs and strips raw SQL, raw rows, provider metadata, task ids, row refs, ledger ids, source pack ids, and trace/local-path text.
- Metric label integrity now follows actual returned source columns and semantic-layer metric metadata before using metric-list hints. Planner metric order is no longer positional truth, so returned columns such as spend then revenue keep the correct labels even if the planner listed revenue first.
- Multi-task evidence keeps group boundaries. Channel revenue, spend, support pressure, and sales-owner/support issue evidence remain separate groups in the ledger and same-thread follow-up/product summaries preserve grouped context.
- `build_chart_safe_table()` was narrowed to one coherent chartable evidence group and refuses to blindly combine multiple groups. Existing sanitized execution fallback remains available for current visualization compatibility; deeper grouped chart candidate selection moves to P35-H3.
- Product Result Builder only assembles grouped ledger summaries and business-readable group cards. It does not synthesize business answers, and main payload summaries scrub group fact row refs/task ids/tool internals while technical details remain collapsed.
- Report Center was not changed and remains independent on `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument`.

## Latest P35-H2 Result

P35-H2 Grouped Answer Generation And Non-Destructive Audit completed on 2026-07-07:

- Business Answer provider generation is gated by `build_answer_input_ledger()` and an answer-safe grouped `evidence_groups` payload. The provider prompt now explicitly frames the model as a Chinese business analysis assistant, asks for natural direct business prose, forbids fixed chapter/report templates, and limits hard facts to grouped evidence/data limits.
- The prompt/schema context excludes raw execution rows, SQL, task ids/purposes, ledger ids, source pack ids, trace paths, provider metadata, local paths, prompt/debug fields, and other internal execution artifacts. Empty/no-key provider mode returns a clear `业务回答生成失败` response while keeping evidence/table previews outside the main answer; it does not produce a row-derived or ledger-fact natural answer.
- Repair is non-destructive. Typed provider hard-fact claims are checked against the ledger; unsupported auxiliary numbers are removed at sentence/item level while supported main conclusions remain. Internal leaks, empty primary answers after cleanup, provider validation failure, or broadly unsupported primary facts still become explicit generation-failed output.
- Product Result Builder remains an assembler: it preserves usable `business_answer` values and otherwise shows missing/generation-failed answer states without using `execution_result.rows` to compose `direct_answer`.
- Report Center remains independent on `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument`; Report Center tests were rerun unchanged.

## Latest P35-H3 Result

P35-H3 Grouped Chart Selection, ECharts Polish, Acceptance, And Cleanup completed deterministically on 2026-07-07:

- Added `build_grouped_chart_candidate()` as the Analysis Workbench chart input contract. It selects from `question_evidence_ledger.evidence_groups`, records business dimension label, metric labels, display unit, row grain, evidence refs, safe rows/columns, and a deterministic chart spec. One coherent group can chart by default; multiple groups chart only when they share the same dimension signature and row grain and their metric units are compatible.
- Revenue plus spend by the same channel/grain can become a grouped bar candidate with `渠道 / 指标 / 金额`, title such as `最近90天渠道收入与投放花费对比`, legend series `收入` and `投放花费`, and y-axis `金额 (元)`. Currency plus ROI/percentage or channel revenue plus support-owner/support-issue evidence is rejected with a business-readable skip reason.
- `VisualizationAgent` now prefers grouped-ledger candidates and bypasses provider chart-spec/tool choice when a candidate exists. Missing or incoherent grouped evidence skips chart generation instead of falling back to broad `task_id`/`task_purpose` execution rows. The old sparse multi-task row-to-long-table path is removed from the active path; the remaining fallback is limited to legacy single-dimension/single-metric execution results without internal columns.
- `build_echarts_option()` keeps grouped-bar series names from the real metric labels and rejects grouped bars whose `metric_units` mix incompatible unit families. ECharts title, legend, x-axis, y-axis, and unit labels now come from the vetted candidate/spec rather than generic `对象数值对比` / `数值`.
- Chart artifacts can carry a safe `skip_reason`/`failure_reason` so the frontend can explain why no chart was generated without showing SQL, raw rows, task ids, ledger JSON, trace paths, or provider metadata. `ChartArtifactGallery` still prefers ECharts and keeps legacy PNG/SVG/image fallback.
- Report Center was not wired to the Analysis Workbench chart selection node. Its report runner/API regression passed unchanged, and it continues to use `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument` while sharing only the generic ChartArtifact/ECharts builder contract.

## Latest P34-H1 Result

P34-H1 Export Package Unified Output Contract completed on 2026-07-07:

- `workspaces.export_package` now defines `p34.export_package.v1` as the current handoff contract. Packages include `package_id`, `source_type` (`report` or `analysis`), `workspace_id`, `source_id`, `title`, `generated_at`, `language`, `document`, `business_answer`, `business_content_summary`, `sections`, `action_recommendations`, `data_boundaries`, `chart_artifacts`, `static_assets`, `markdown_path`, `document_path`, `evidence_refs`, `evidence_summary`, and `warnings`.
- Report Center packages are projected from `ReportRecord` / `ReportDocument`. The package preserves `ReportDocument.sections` order and titles exactly, keeps action recommendations and data boundaries from the document, carries report chart artifacts/static assets/evidence refs, and does not impose fixed chapters such as 经营概览 / 渠道表现 / 风险问题 / 行动建议.
- Analysis Workbench packages are projected from the current product result only. They export the existing `business_answer`, evidence summary/refs, chart artifacts, static assets, warnings, recommendations/caveats as contract fields, and deliberately keep `sections=[]` so Analysis Workbench answers are not turned into report templates.
- The export package builder remains deterministic and does not call an LLM, run SQL, regenerate chart specs, rewrite report prose, or synthesize missing business answers. Missing static chart fallback records a warning; it does not pretend an image exists.
- Package projection strips or rejects raw SQL, raw execution rows, trace paths, provider metadata, API keys/secrets, database paths, local absolute paths, path traversal, secret-bearing URLs, task ids/purposes, debug ids, prompt text/ids/tokens, and raw `chart_spec` JSON from the user-facing package body.
- Verification passed:
  - `python3 -m pytest tests/test_export_package.py -q` (`8 passed`)
  - `python3 -m pytest tests/test_workspace_report_runner.py tests/test_product_result_builder.py tests/test_p30_acceptance.py -q` (`64 passed`)
  - `python3 -m pytest tests/test_p30_live_chart_acceptance.py -q` (`1 skipped`, live flags absent)
  - `python3 -m pytest tests/test_p33_live_acceptance.py -q` (`1 skipped`, live flags absent)
  - `cd frontend && npm test` (`73 passed`)

## Latest P34-H2 Result

P34-H2 Chart Static Asset Export completed on 2026-07-07:

- Added `workspaces.chart_static_export` with single-chart and batch export functions. The tool first reuses safe `image_path` / `image_url` / `path` / `url` values for legacy PNG/SVG and ECharts image fallbacks.
- When an ECharts artifact has no image fallback but does have usable existing `echarts_option` series data, the tool writes a workspace-relative SVG under `exports/charts/` and returns static asset metadata for document insertion.
- If a chart lacks enough option data or no safe workspace output root is available, the tool returns clear warnings and no fake image path.
- `workspaces.export_package` now uses the static export tool for `static_assets`, while preserving safe `chart_artifacts`, evidence refs, ordered report sections, and H1 leak filtering.
- The static export path is deterministic and does not call an LLM, re-analyze business questions, rewrite conclusions, or restore old chart agent/planner/tool or simulated external publishing/action-delivery paths.

## Latest P34-H3 Result

P34-H3 Word Document Export Tool completed on 2026-07-07:

- Added `workspaces.document_export.export_report_docx()` for deterministic local Word `.docx` generation from `p34.export_package.v1` report packages.
- The document renders only existing package/report content: title, time range/data sources, opening summary/business content summary, ordered `ReportDocument.sections` titles/bodies/chart refs, action recommendations, data boundaries, evidence refs, and compact evidence summary counts.
- Chart refs are matched to safe static assets from the package. PNG/JPEG-compatible assets are inserted into the Word file; missing or SVG-only assets produce a visible placeholder plus warning instead of fake image success.
- Analysis Workbench packages are rejected by default for full Word report export so workbench answers are not stitched into report templates.
- The exporter applies Chinese-friendly Word styles and compact spacing, strips sensitive text from document content, and avoids raw SQL, raw rows, trace/provider metadata, API keys, database paths, local absolute paths, prompt/task/debug fields, and old mock/action/chart paths.

## Latest P34-H4 Result

P34-H4 API, Frontend Download, Acceptance, And Cleanup completed on 2026-07-07:

- Added `POST /api/workspaces/{workspace_id}/reports/{report_id}/export`, which loads an existing Report Center record, builds a safe report export package, calls `export_report_docx()`, verifies the `.docx` exists under the workspace, records a `word_document` artifact, and returns only safe metadata: `success`, `document_path`, `download_name`, `download_url`, `warnings`, and artifact summary.
- The existing workspace artifact endpoint serves the generated `.docx`; API responses use workspace-relative paths and URL-encoded artifact URLs instead of local absolute paths.
- Report Center now shows `导出 Word`, an exporting state, a download link on success, business-friendly chart placeholder warnings such as `部分图表当前以占位说明展示。`, and clear failure reasons without exposing raw SQL, trace, provider metadata, local paths, or export package internals.
- Focused tests cover successful API export/download, missing reports, missing generated files, response no-leak guarantees, SVG-only chart warning behavior, frontend API client typing, ReportViewer success/warning/failure states, and Analysis Workbench package rejection in the document exporter.
- Real DeepSeek acceptance ran on a temporary Chinese channel-operation workspace with goal `生成一份最近90天渠道经营复盘报告，覆盖收入结构、投放效率、客服压力、关键风险和下一步建议。`. The report completed through `ledger_backed_report_center` with `provider_supplied=true`, title `最近90天经营复盘报告`, sections `经营概览`, `收入结构`, `客户分群`, `客服问题`, and `趋势变化`; Word export succeeded in 27.30s, produced a readable `.docx` with title, summary, sections, recommendations, and data boundaries, returned one chart placeholder warning, and leaked none of SQL, trace/provider metadata, API key, database path, prompt/task/debug fields, or local absolute paths.
- Verification passed: P34/P30 focused backend groups, full backend regression (`688 passed, 14 skipped`), full frontend Vitest (`76 passed`), and `cd frontend && npm run build`.

## Latest P33-H3 Result

P33-H3 Parallel Chart And Acceptance Cleanup plus repair completed on 2026-07-07:

- Analysis Workbench chart generation now prefers a chart-safe table projected from `question_evidence_ledger`; fallback chart inputs are sanitized before becoming chart artifacts. Chart artifacts keep the P30 fields (`renderer`, `chart_type`, `echarts_option`, image fallback, evidence refs, source, row count, business annotation) but no longer expose `chart_spec` JSON, raw SQL, raw rows, task ids, trace paths, provider metadata, or local absolute paths in the main product payload.
- `fast_fact` remains chartless by default and only generates charts for explicit chart/visualization requests. `standard_analysis` and `deep_judgment` may generate ECharts when evidence is chartable and policy allows. Visualization exceptions are caught in the visualization node and do not replace or block the already generated Business Answer.
- Product Result Builder still only assembles. It removes main-payload `raw_rows` technical refs and question-evidence `tool_calls`, while keeping raw SQL/rows/provider metadata in collapsed technical details only. BusinessAnswerAgent preserves supported provider answers, scrubs unsupported explanation details/internal leaks, and returns a clear generation-failed boundary when provider output is unsafe; it no longer uses ledger facts as a deterministic repair answer after a provider failure.
- Frontend chart display still prefers ECharts and falls back to static images. The main EvidencePanel filters internal task columns; technical details remain collapsed by default.
- Verification passed:
  - `python3 -m pytest tests/test_answer_consistency.py tests/test_business_answer_quality.py tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py -q` (`126 passed`)
  - `python3 -m pytest tests/test_fast_fact_path.py tests/test_question_evidence_ledger.py tests/test_evidence_tasks.py tests/test_analysis_route_policy.py -q` (`44 passed`)
  - `python3 -m pytest tests/test_visualization_agent_external_tools.py tests/test_p30_acceptance.py -q` (`18 passed`)
  - `python3 -m pytest tests/test_runtime_provider.py tests/test_p20_architecture_cleanup_boundaries.py -q` (`8 passed`)
  - `cd frontend && npm test` (`73 passed`) and `cd frontend && npm run build` passed
  - `git diff --check` passed; old-path audit found only negative boundary tests/config compatibility names; tracked-artifact audit had no hits.
- Real DeepSeek acceptance with `deepseek-v4-flash` passed strict P33 coverage after repair: fast fact, standard one-table, deep multi-evidence, same-thread follow-up, explicit ECharts request, and Report Center smoke. The live test now rejects `业务回答缺失`, `业务回答生成失败`, and `没有可安全展示`; the same-thread follow-up stayed on the same run, produced a natural Chinese model answer, and Report Center stayed on `ledger_backed_report_center`.

## Latest P33-H2 Result

P33-H2 Remove Template/Rewriter Paths completed on 2026-07-07:

- Product Result Builder now assembles existing `business_answer`, evidence, ledger summary, chart artifacts, progress, history display, and technical details. It no longer builds the main business conclusion from `execution_result.rows` or `final_answer` fallback text when `business_answer` is missing or invalid.
- BusinessAnswerAgent no longer calls the old final-answer composer on the active Analysis Workbench path. Provider answers that pass deterministic review are preserved; unsupported facts, internal task ids, raw fields, SQL, trace/provider metadata, and raw-row leaks are removed or downgraded to a clear answer-generation failure instead of being replaced with row-derived template conclusions.
- Cleanup fix: deleted `agents/final_answer_composer.py` and `tests/test_final_answer_composer.py`; deleted `workspaces/answer_consistency.py` and rewrote `tests/test_answer_consistency.py` as boundary coverage for module removal, chart annotation leak scrubbing, provider-answer preservation, and missing-answer behavior. Chart annotation safety now lives in `workspaces/chart_annotation_safety.py` and does not generate or realign business conclusions.
- No-key/dev fallback remains explicit and separated from the real provider path. Fast-fact no-provider fallback may use safe context-pack facts when available, otherwise it returns a clear generation-failure status; Product Result Builder still does not synthesize a replacement conclusion.
- Report Center was not changed.

## Latest P33-H1 Result

P33-H1 Answer Contract And Route Semantics completed on 2026-07-07:

- Analysis Workbench Business Answer prompts now take only an answer-safe projection of the question evidence ledger: business facts, derived metrics, time口径, data limits, chart refs, confidence, and remapped evidence refs. Raw SQL, execution rows, `task_id`, `task_purpose`, task refs, ledger ids, source pack ids, trace paths, provider metadata, local paths, and API-key-like values are excluded from the answer prompt/input.
- Fast facts still run the lightweight SQL/evidence path, but the final `business_answer` is generated through the same Business Answer provider seam from the clean ledger. The old `fast_fact_composer.py` deterministic final-answer path was deleted and replaced by `fast_fact_claims.py`, which only prepares factual claims for validation.
- Standard vs Deep route semantics now use evidence complexity: core evidence task count, source table count, metric count, supporting metric count, and whether a tradeoff/recommendation is needed. Advice/risk/reason/priority wording no longer forces Deep by itself, and plain multi-table/multi-task questions can route Deep even without those words.
- Question Understanding remains the natural-language entry, while Business Lens is the dataset-grounding layer for metrics, dimensions, source fields, and time口径; the combined output now feeds route complexity and evidence task planning as one logical intent/口径 contract.
- Report Center was not changed; it remains on `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument`.

## Latest P32-H3 Result

P32-H3 Product Acceptance, Live Verification, And Cleanup completed on 2026-07-07:

- Analysis Workbench still generates one `business_answer` from the merged ledger; multi-task results are not stitched into mini answers.
- The product evidence summary now groups task evidence with business labels such as `收入证据`, `投放花费证据`, and `效率辅助证据`, and data limits use business wording for missing auxiliary/core evidence instead of showing task ids, SQL, trace paths, or provider metadata.
- The main UI no longer surfaces ledger ids, raw evidence refs, chart refs, chart spec JSON, or ECharts option JSON. Technical details remain collapsed.
- Chart artifacts keep ECharts-first rendering with static image fallback, and Analysis Workbench artifacts inherit ledger evidence refs when the visualization result did not provide them directly.
- Same-thread follow-ups keep evidence refs internally for context but show business-readable evidence continuity; history restoration now rebuilds stale pre-H3 product results when raw P32 `evidence_task_results`, `question_evidence_ledger`, or `chart_artifacts` would otherwise be hidden.
- Report Center was audited and remains independent: `ReportPlan -> ReportEvidencePack -> EvidenceLedger -> one-pass ReportDocument -> validate/render/save`; report code does not call `run_workspace_analysis`.
- Old forbidden active paths were not restored. Remaining `chart_agent`, `visualization_planner`, `chart_tool`, `insight_agent`, `insight_claim_typer`, and `pending_clarification_store` hits are historical docs, negative boundary tests, or current assertions that they are absent.
- Opt-in live DeepSeek verification ran with the configured `.env` key and explicit `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1`. The standard multi-task full-provider case completed via `evidence_task_runner` but took 73.6s; subsequent deep/chart/report checks used deterministic SQL evidence plus real DeepSeek business-answer/visualization/report providers to avoid SQL-provider concurrency stalls. A multi-task explicit chart question produced no chart artifact, while an initial-SQL chart acceptance produced ECharts plus image fallback; this is a follow-up risk for multi-task visualization selection, not a blocker for P32 evidence-task closeout.

## Latest P32-H2 Result

P32-H2 Task Runner And Analysis Ledger Integration completed on 2026-07-06:

- Added `workspaces.evidence_task_runner.run_evidence_task_plan`.
- Each task delegates to the current Evidence Agent safe chain and preserves the sequential boundary: SQL candidate -> SQL review -> optional existing schema repair/execution fix -> approved SQL execution -> evidence validation.
- The graph invokes the runner for standard/deep plans with multiple core tasks across more than one source table. Fast facts, explicit `initial_sql`, helper-only questions, and same-table multi-metric questions stay on the previous one-task/single-SQL path.
- `max_parallel_evidence_tasks` defaults to `3`, is capped by the plan, and can be configured through the runner argument or `INSIGHTFLOW_MAX_PARALLEL_EVIDENCE_TASKS`.
- The lightweight `question_evidence_ledger` now carries `task_id` on facts, derived metrics, table refs, evidence refs, and merged task refs. Task-level data limits merge into the safe ledger without raw SQL, trace paths, provider metadata, API keys/secrets, or local absolute paths.
- Provider multi-statement SQL is rejected before execution. A failed support task contributes data limits while successful core evidence can still answer; if all core tasks fail, the graph returns a business-friendly evidence-insufficient failure.
- Business Answer still runs once from the merged evidence/ledger, and Report Center remains independent on `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument`.
- Verification passed:
  - `python3 -m pytest tests/test_evidence_tasks.py tests/test_evidence_task_runner.py tests/test_question_evidence_ledger.py -q` (`18 passed`)
  - `python3 -m pytest tests/test_fast_fact_path.py tests/test_workspace_analysis_runner.py -q` (`62 passed`)
  - `python3 -m pytest tests/test_product_result_builder.py tests/test_workspace_api.py tests/test_workspace_run_history_api.py -q` (`63 passed`)
  - `python3 -m pytest tests/test_workspace_report_runner.py tests/test_report_planner_evidence.py tests/test_report_composer_validator.py -q` (`73 passed`)
  - `cd frontend && npm test` (`72 passed`)
  - `cd frontend && npm run build` passed

## Latest P31-H4 Result

P31-H4 Frontend Thread UX, Realistic Acceptance, Live Verification, Cleanup Closeout completed on 2026-07-06:

- Analysis Workbench now presents one coherent analysis thread: original question, system understanding, resolved question, clarification/follow-up turns, Business Lens time口径, business answer, safe ledger/evidence summary, chart artifacts, compact history, and collapsed technical details.
- Waiting-clarification and completed-answer follow-ups both continue through `POST /api/workspaces/{workspace_id}/runs/{run_id}/follow-ups` and update the same run/thread. The follow-up form is framed as continuing the current analysis, and completed follow-ups no longer rewrite the main new-question input.
- The old active `pending_run_id` continuation path was removed from runner, graph state/workflow, Product Result, frontend types, and stale tests. `PendingClarificationStore` was deleted. `POST /runs` remains a new-analysis-only entry; one negative API boundary test proves the superseded pending body is rejected.
- Realistic acceptance is covered by focused regression: omitted-time questions safely bind metric time fields and state the full-data口径, cross-table revenue plus spend questions use per-metric time fields, waiting clarification follow-up completes in the same run, completed follow-up appends a same-thread turn, and answer/evidence/chart refs stay connected through the ledger summary.
- Report Center remains independent on `ReportEvidencePack + EvidenceLedger + ReportDocument`; P31 did not merge it into Analysis Workbench or add real Feishu/DingTalk/WeCom/Tencent Docs/Power BI/Word/PPT connectors.
- Live DeepSeek verification was skipped honestly: `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS` was not enabled, `INSIGHTFLOW_PRODUCT_LIVE_MODE` was not enabled, and `DEEPSEEK_API_KEY` was absent in the local environment.
- Verification passed:
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_api.py tests/test_workspace_run_history_api.py -q` (`73 passed`)
  - `python3 -m pytest tests/test_business_lens.py tests/test_question_evidence_ledger.py tests/test_product_result_builder.py -q` (`52 passed`)
  - `python3 -m pytest tests/test_p25_time_range_defaults.py tests/test_p29_acceptance.py -q` (`16 passed`)
  - `python3 -m pytest tests/test_clarification_routing.py tests/test_workflow.py tests/test_workspace_analysis_runner.py tests/test_workspace_api.py tests/test_workspace_run_history_api.py -q` (`81 passed`)
  - `cd frontend && npm test` (`72 passed`)
  - `cd frontend && npm run build` passed
  - `python3 -m pytest -q` (`658 passed, 13 skipped`)

## Latest P31-H2 Result

P31-H2 Analysis Thread Memory and same-thread follow-up continuation completed on 2026-07-06:

- Added `workspaces.analysis_thread_memory` with `thread_id`, `original_question`, `turns`, `current_business_lens`, `evidence_refs`, `answer_summary`, `pending_clarification`, `latest_status`, and `latest_resolved_question`.
- Each turn records `turn_id`, `user_input`, `resolved_question`, `status`, `answer_summary`, `business_lens`, `evidence_refs`, and `created_at`.
- Waiting clarification follow-ups now combine the original question and user supplement, rerun the safe analysis chain with the original `run_id`, append a turn, and update `pending_clarification` if more information is still needed.
- Completed-run follow-ups now combine the original question, previous resolved question, previous answer summary, existing business lens/evidence refs, and the new user message before rerunning the safe chain and appending a new turn to the same thread.
- Added `POST /api/workspaces/{workspace_id}/runs/{run_id}/follow-ups`; the old `pending_run_id` body on `POST /runs` is no longer an active continuation API.
- The frontend uses the same-thread follow-up API for both 用户补充 and 继续追问, and no longer builds `基于上一轮分析继续追问...` as a new `user_question`.
- Run history still lists one card for the thread after follow-up because the original run JSON is updated in place.
- Verification passed:
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_api.py tests/test_workspace_run_history_api.py -q` (`76 passed`)
  - `python3 -m pytest tests/test_business_lens.py tests/test_analysis_coordinator_data_understanding.py -q` (`18 passed`)
  - `python3 -m pytest tests/test_p25_real_usage_acceptance.py tests/test_p29_acceptance.py -q` (`5 passed`)
  - `cd frontend && npm test` (`71 passed`)
  - `cd frontend && npm run build` passed

## Latest P31-H1 Result

P31-H1 Business Lens Contracts And Per-Metric Time Bindings completed on 2026-07-06:

- Added `question_understanding.business_lens` with a structured lens contract: `business_domain`, metric contracts (`label`, `source_table`, `source_field`, `time_field`, `metric_role`), dimension contracts (`label`, `source_table`, `source_field`), `time_range`, `time_policy_note`, `needs_clarification`, `clarification_question`, and `data_limits`.
- Wired Business Lens after question understanding in Data Understanding. The LLM/provider/fallback still owns natural-language intent; Business Lens owns deterministic grounding against workspace semantic metrics, dimensions, time fields, aliases, field meanings, and profile date ranges.
- Added per-metric time binding: revenue-like metrics bind to order/sales/business dates from their source table, spend-like metrics bind to spend/marketing dates, support metrics bind to ticket/support dates, and customer registration counts bind to registration dates when a customer id/date pair exists.
- Replaced the conflicting global date-field clarification for safe cross-table revenue plus spend questions with a lens-level time policy note that explains each metric's own date口径 and full-data default when the user omits a time range.
- H1 repair tightened the safe full-data default boundary: Business Lens only emits `time_range.type="full_data_range"` when every metric-bound time field has non-empty profile `min/max` ranges. If profile ranges are missing or partial, the lens leaves `time_range` empty, records a data limit, asks for a time range, and does not write a default-full-range time policy note.
- `AnalysisTask` and `QuestionEvidencePack.task` now preserve `business_lens` so P31-H2/H3 can build same-thread memory and a lightweight question evidence ledger from the grounded口径.
- Verification passed:
  - `python3 -m pytest tests/test_business_lens.py tests/test_analysis_coordinator_data_understanding.py -q` (`18 passed`)
  - `python3 -m pytest tests/test_question_understanding_router.py tests/test_workspace_analysis_runner.py -q` (`67 passed`)
  - `python3 -m pytest tests/test_p25_real_usage_acceptance.py tests/test_p29_acceptance.py -q` (`5 passed`)

## Latest P30-H6 Result

P30-H6 Acceptance, Cleanup, And Live Verification completed on 2026-07-06:

- Added `tests/test_p30_acceptance.py`, a focused deterministic acceptance test proving an explicit Analysis Workbench chart request produces `renderer="echarts"`, `echarts_option`, static `image_path`/`image_url` fallback, and `evidence_refs`; a no-chart `fast_fact` stays chartless; Report Center creates `source="report_center"` chart artifacts; Markdown stays free of `echarts_option`, `chart_spec`, SQL, trace, and provider metadata; report and analysis export packages include chart artifacts, static assets, and evidence refs; and option-only charts produce `export_warnings` instead of failing.
- Added `tests/test_p30_live_chart_acceptance.py`, an opt-in live DeepSeek acceptance test for the P30 product path. With `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1` and `INSIGHTFLOW_PRODUCT_LIVE_MODE=1`, it ran on model `deepseek-v4-flash`.
- Live Analysis Workbench question: `最近90天按渠道比较收入并生成图表。` It completed on route `standard_analysis` in `38874 ms`, called DeepSeek-backed question understanding, SQL planning, SQL candidate, Business Answer, and Visualization providers once each, produced one `analysis_workbench` ECharts chart artifact with static fallback and `question_evidence_pack`, and built an analysis export package with one chart artifact, one static asset, one evidence ref, and no export warnings.
- Live Report Center goal: `生成一份最近90天经营复盘报告，关注收入结构、客户分群和趋势变化。` It completed on `ledger_backed_report_center` in `18323 ms`, called the DeepSeek-backed report composer once, produced three `report_center` ECharts chart artifacts with static SVG fallback and ledger/evidence refs, and built a report export package with three chart artifacts, three static assets, 79 evidence refs, and no export warnings.
- Cleanup and hygiene were verified: old chart/tool/simulated-connector/action terms remain only in Historical/Superseded docs or negative boundary tests; no `chart_agent`, `visualization_planner`, `chart_tool`, obsolete simulated connector runtime, generated database, report, chart, trace, `.next`, or `node_modules` artifact was added to source tracking.
- P30 still does not publish to Feishu, DingTalk, WeCom, Tencent Docs, Power BI, Word, or PPT. Real external connector/tool-call work is deferred until after P31.
- Verification passed:
  - `python3 -m pytest tests/test_p30_acceptance.py tests/test_p30_live_chart_acceptance.py -q` (`1 passed, 1 skipped`)
  - `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_PRODUCT_LIVE_MODE=1 python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_product_live_mode.py -q` (`5 passed`)
  - `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_PRODUCT_LIVE_MODE=1 python3 -m pytest tests/test_p30_live_chart_acceptance.py -q -s` (`1 passed`)
  - `python3 -m pytest tests/test_export_package.py tests/test_echarts_option_builder.py tests/test_visualization_agent_external_tools.py tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py -q` (`135 passed`)
  - `python3 -m pytest tests/test_report_planner_evidence.py tests/test_report_composer_validator.py tests/test_p29_acceptance.py -q` (`57 passed`)
  - `cd frontend && npm test` (`71 passed`)
  - `cd frontend && npm run build` passed
  - `python3 -m pytest -q` (`638 passed, 13 skipped`)
  - `git diff --check` passed

## Latest P30-H5 Result

P30-H5 Static Export Fallback And Artifact Package completed on 2026-07-06:

- Added `workspaces/export_package.py` with `ExportPackage` (`p30.export_package.v1`) plus `build_report_export_package()` and `build_analysis_export_package()` pure builders. H5 does not save manifests by default, does not call LLMs, does not run SQL, and does not publish to external platforms.
- The package contract includes `workspace_id`, `source_type` (`analysis_run` or `report`), `source_id`, `title`, `created_at`, `language="zh"`, `document`, `business_answer`, `chart_artifacts`, `static_assets`, `markdown_path`, `document_path`, `evidence_refs`, and `export_warnings`.
- Report Center records can be projected into export packages with report document summaries, Markdown/report-document relative paths, unified chart artifacts, static SVG/image fallback assets, and report evidence refs. Report Center remains independent and still does not call Analysis Workbench.
- Analysis Workbench product results can be projected into export packages with the P16 business-answer summary, unified chart artifacts, ECharts option metadata, static PNG/SVG/image fallback assets, and question evidence refs.
- Chart artifacts in export packages are deliberately whitelisted to `artifact_id`, `title`, `renderer`, `chart_type`, `path`/`url`, `image_path`/`image_url`, `rendering_status`, `business_annotation`, `evidence_refs`, `source`, `data_row_count`, and optional `echarts_option`. Internal `chart_spec` stays out of the export package.
- Static export fallback is explicit: Web consumers can use `echarts_option`, while external platform/Markdown/static consumers should use `image_url`/`image_path` or `path`/`url`. Missing static fallback records an `export_warnings` entry instead of failing package creation.
- Export packages exclude raw SQL, trace paths, provider metadata, API keys, database paths, local absolute paths, path-traversal references, and chart asset URLs carrying secret-like query parameters. Workspace-relative paths and clean artifact API URLs are allowed.
- No Feishu/DingTalk/WeCom/Tencent Docs/Power BI/Word/PPT connector, old `chart_agent` / `visualization_planner` / `chart_tool`, generated manifest persistence, generated artifacts, database files, trace files, `.next`, or `node_modules` were added to source tracking.
- Verification passed:
  - `python3 -m pytest tests/test_export_package.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py -q` (`61 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_echarts_option_builder.py tests/test_visualization_agent_external_tools.py tests/test_report_planner_evidence.py tests/test_report_composer_validator.py -q` (`127 passed`)
  - `python3 -m pytest tests/test_workspace_report_runner.py tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py tests/test_echarts_option_builder.py -q` (`115 passed`)
  - `python3 -m pytest tests/test_visualization_agent_external_tools.py tests/test_report_planner_evidence.py tests/test_report_composer_validator.py -q` (`68 passed`)
  - `cd frontend && npm test` (`71 passed`)
  - `cd frontend && npm run build` passed

## Latest P30-H4 Result

P30-H4 Report Center Chart Artifact Reuse completed on 2026-07-06:

- Added `workspaces/report_chart_artifacts.py` so Report Center upgrades report evidence chart intents into unified ChartArtifact payloads using collected `ReportEvidenceTable` rows and deterministic `build_echarts_option`.
- Report records now expose top-level `chart_artifacts` and evidence-pack charts carry the same P30 fields: `artifact_id`, `renderer`, `chart_type`, `chart_spec`, `echarts_option`, `image_path`, `image_url`, `path`/`url`, `rendering_status`, `unit`, `value_label`, `business_annotation`, `evidence_refs`, `source="report_center"`, and `data_row_count`.
- Existing Report Center SVG rendering stays as the static fallback. If ECharts option generation fails, report generation still completes, the artifact falls back to static image/intent state, and the technical reason is recorded in trace events rather than the main report body.
- ReportViewer now reads `report.chart_artifacts` and reuses `ChartArtifactGallery`, so web report details prefer ECharts while legacy evidence-pack chart images still work when unified artifacts are absent.
- Markdown output remains static-only: it links image/SVG fallback and business chart text without embedding `echarts_option`, `chart_spec`, SQL, raw rows, trace, provider metadata, local paths, or internal ids in the main report.
- Report Center remains independent on `ReportEvidencePack + EvidenceLedger + ReportDocument`; it does not call Analysis Workbench nodes, does not stitch Analysis Workbench answers into reports, and does not restore old `chart_agent` / `visualization_planner` / `chart_tool`.
- No Feishu/DingTalk/WeCom/Tencent Docs/Power BI publishing or real connector work was added; external publishing remains deferred until after the P31 Business Lens and analysis-thread work.
- Verification passed:
  - `python3 -m pytest tests/test_workspace_report_runner.py tests/test_report_planner_evidence.py tests/test_report_composer_validator.py tests/test_product_result_builder.py -q` (`107 passed`)
  - `python3 -m pytest tests/test_echarts_option_builder.py tests/test_visualization_agent_external_tools.py tests/test_workspace_analysis_runner.py -q` (`74 passed`)
  - `cd frontend && npm test` (`71 passed`)
  - `cd frontend && npm run build` passed

## Latest P30-H3 Result

P30-H3 Analysis Workbench ECharts Rendering completed on 2026-07-06:

- Updated `agents/visualization_agent.py` so successful local static chart rendering now calls deterministic `build_echarts_option` from the validated `chart_spec` and reviewed `execution_result` rows.
- Successful artifacts now carry `renderer="echarts"`, `chart_type`, `chart_spec`, `echarts_option`, static `image_path`/`image_url` fallback, `evidence_refs=["question_evidence_pack"]`, `source="analysis_workbench"`, `data_row_count`, and the existing title/unit/value-label/business-annotation fields through product results.
- If ECharts option generation fails, the Analysis Workbench run still succeeds with the static PNG/SVG/image fallback; the failure reason is recorded as visualization trace metadata instead of being shown in the main chart UI.
- Updated `frontend/components/ChartArtifactGallery.tsx` to be a client component that initializes ECharts in `useEffect` via the existing `echarts` dependency, renders interactive charts when `echarts_option` is present, and falls back to existing image rendering when no option is available or ECharts initialization fails.
- The main chart UI continues to hide raw SQL, trace paths, provider metadata, evidence refs, and local paths while preserving chart title, unit, and business annotation.
- Route strategy remains unchanged: `fast_fact` does not generate charts unless the user explicitly asks for a chart; `standard_analysis` and `deep_judgment` generate charts only when evidence is chartable and policy allows; `clarify` and `reject` do not generate charts.
- Report Center chart reuse and its separate SVG fallback path were not changed; this remains P30-H4.
- Verification passed:
  - `python3 -m pytest tests/test_echarts_option_builder.py tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py tests/test_visualization_intelligence.py tests/test_visualization_agent_external_tools.py -q` (`114 passed`)
  - `python3 -m pytest tests/test_p29_acceptance.py -q` (`4 passed`)
  - `python3 -m pytest tests/test_fast_fact_path.py -q` (`13 passed`)
  - `cd frontend && npm test` (`70 passed`)
  - `cd frontend && npm run build` passed

## Latest P30-H2 Result

P30-H2 Deterministic ECharts Option Builder completed on 2026-07-06:

- Added `visualization/echarts_option_builder.py` and exported `build_echarts_option` from `visualization.__init__`.
- Supported deterministic ECharts option generation for `ranked_bar`, `bar`, `line`, `grouped_bar`, `scatter`, and `dual_axis_line`. `table` returns a table/static fallback reason and no `echarts_option`.
- The builder uses only reviewed `execution_result` / equivalent evidence table rows plus `chart_spec` and optional unit/business-label metadata. It does not call an LLM, execute SQL, or accept model-written final ECharts options.
- Evidence rows support the existing `columns + list[list]` shape and tolerate `list[dict]`. Required fields must exist, numeric roles must safely convert to finite numbers, empty rows/missing columns/unsupported chart types fail clearly, and large row sets are bounded with `data_limit` / sampled row counts.
- Options are JSON-only: no formatter functions, arbitrary JavaScript functions, raw SQL, trace/provider metadata, or local absolute paths. JavaScript-like, SQL-like, path-like, and trace/provider metadata title text is stripped; the same unsafe text in category/label evidence values fails validation instead of being embedded.
- P30-H1 legacy PNG/SVG compatibility remains intact. No frontend ECharts rendering, ECharts package dependency, Report Center reuse path, Power BI/Feishu/DingTalk/WeCom/Tencent Docs integration, old chart agent/planner/tool restoration, matplotlib removal, or report SVG removal was added.
- Verification passed:
  - `python3 -m pytest tests/test_echarts_option_builder.py -q` (`11 passed`)
  - `python3 -m pytest tests/test_product_result_builder.py tests/test_visualization_intelligence.py tests/test_visualization_agent_external_tools.py -q` (`54 passed`)
  - `python3 -m pytest tests/test_p29_acceptance.py -q` (`4 passed`)

## Latest P29-H4 Result

P29-H4 Acceptance Tests And Live DeepSeek Verification completed on 2026-07-05:

- Added `tests/test_p29_acceptance.py`, a deterministic acceptance matrix for eight real Chinese business questions across fast facts, full judgment/advice, true external-action rejection, and explicit chart requests. The record for each case includes route/routing strategy, provider call count, Business Answer provider use, SQL generation/execution, evidence rows/fact payload summary, answer summary, chart generation, trace nodes, and elapsed milliseconds.
- Deterministic acceptance coverage:
  - `最近30天总销售额是多少？` -> `fast_fact`, no Business Answer provider, SQL reviewed/executed, no chart.
  - `最近90天哪个渠道收入金额最高？` -> `fast_fact`, no Business Answer provider, evidence leader `私域社群`, no chart.
  - `本月哪个门店销售额最高？` -> `fast_fact`, this-month scope, no Business Answer provider, no chart.
  - `收入最高的客户分群是谁？` -> `fast_fact`, safe full-data time range, no Business Answer provider, no chart.
  - `最近90天按渠道比较收入、投放金额和投放效率，哪个渠道表现最好？` -> `deep_judgment`, Business Answer provider called, SQL/evidence/audit present.
  - `最近30天哪个渠道最值得加预算？请给证据和风险边界。` -> `deep_judgment`, Business Answer provider called, SQL/evidence/audit present, not rejected as an unsafe external action.
  - `把预算调整到私域社群并发送通知。` -> rejected before SQL, no provider call, no SQL generation/execution, no chart.
  - `最近90天哪个渠道收入最高？给我画图。` -> `fast_fact`, no Business Answer provider, SQL/evidence present, chart generated only because the question explicitly requested it.
- Fixed one deterministic no-provider gap found by H4: a clearly time-bounded channel budget-advice question could still ask for a metric clarification. The fix narrowly defaults channel budget advice with an explicit time range to existing investment-efficiency evidence metrics (`销售额`, `花费`, `ROAS`), while ambiguous no-time budget questions still clarify.
- Updated live DeepSeek tests so real provider calls occur only when the current process explicitly sets `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1` and `INSIGHTFLOW_PRODUCT_LIVE_MODE=1`, and a DeepSeek key is available. Normal test runs now skip live checks clearly instead of using `.env` flags implicitly.
- Added live P29 acceptance in `tests/test_deepseek_live_smoke.py` covering fast fact, full judgment/advice, and true external-action rejection. The explicit live command ran successfully with real DeepSeek: `5 passed in 64.63s`.
- Verification passed:
  - `python3 -m pytest tests/test_p29_acceptance.py -q` (`4 passed`)
  - `python3 -m pytest tests/test_analysis_route_policy.py tests/test_workspace_analysis_runner.py tests/test_fast_fact_path.py -q` (`73 passed`)
  - `python3 -m pytest tests/test_question_understanding_router.py tests/test_provider_backed_question_understanding.py tests/test_analysis_coordinator_data_understanding.py -q` (`48 passed`)
  - `python3 -m pytest tests/test_business_answer_quality.py tests/test_evidence_auditor_claim_categories.py tests/test_product_result_builder.py -q` (`53 passed`)
  - `python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_product_live_mode.py -q` (`3 passed, 2 skipped`)
  - `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_PRODUCT_LIVE_MODE=1 python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_product_live_mode.py -q` (`5 passed`)

## Latest P29-H3 Result

P29-H3 Business Risk Policy Split completed on 2026-07-05:

- Split normal business advice/judgment from real external action risk in the Analysis Workbench route path. Questions such as `最近30天哪个渠道最值得加预算？请给证据和风险边界。` and `最近90天按渠道比较收入、投放金额和投放效率，哪个渠道表现最好？` now stay on the full evidence-backed analysis path instead of being rejected or fast-pathed.
- Safety rejection now stays focused on real external actions, sensitive data access, bulk export, and unsafe write/delete/update requests. Examples such as `把预算调整到私域社群并发送通知。` and `删除所有客户手机号。` stop before SQL generation/review/execution.
- Provider false `unsafe_operation` flags are cleared for analysis/advice wording when no real external action is requested, including mixed cases such as `unsafe_operation + 数据量不足`; non-safety provider boundary flags such as data-volume caveats no longer preserve a stale `reject` strategy.
- Full-path advice questions keep Evidence Planning, schema/metric lookup, SQL review, SQL execution, evidence validation, `QuestionEvidencePack`, Business Answer Agent generation, deterministic Evidence Auditor, and evidence-bound caveats/recommendations.
- `投放效率` now maps into the existing same-table investment-efficiency metric path, so channel comparisons can include revenue, spend, and ROAS-style evidence without adding table-specific routing rules.
- Verification passed:
  - `python3 -m pytest tests/test_analysis_route_policy.py tests/test_workspace_analysis_runner.py tests/test_fast_fact_path.py -q` (`73 passed`)
  - `python3 -m pytest tests/test_business_answer_quality.py tests/test_evidence_auditor_claim_categories.py tests/test_product_result_builder.py -q` (`53 passed`)
  - `python3 -m pytest tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py -q` (`9 passed`)

## Latest P29-H2 Result

P29-H2 Stable Fast Fact Execution Path completed on 2026-07-05:

- Historical / Superseded by P33-H1 and P35-H2: P29 originally routed fast facts through `fast_fact_composer`. The active path now keeps the same safe SQL/evidence chain but sends final answer generation through BusinessAnswerAgent with an answer-safe grouped ledger; when no provider/model answer is available it returns generation failed instead of composing from rows or ledger facts.
- Fast facts still keep the lightweight SQL/evidence route and skip unnecessary visualization, report generation, and old insight/reviewer/final-composer/provider claim typing paths.
- The fast path does not skip SQL review, SQL execution, evidence validation, fact payload / evidence table preview, technical SQL details, route metadata, audit result, or history persistence.
- Business Answer and Visualization providers are now constructed lazily only when their nodes execute, so no-chart fast facts do not initialize unnecessary heavy providers; explicit chart requests can still route to visualization after evidence execution.
- Added deterministic tests for no-`initial_sql` fast facts (`最近90天哪个渠道收入最高？`), `本月` store ranking, omitted-time full-data defaults with one safe time field, provider request count staying zero, lazy provider construction, and full history restoration of `business_answer`, `analysis_route`, `evidence`, and `technical_details`.
- Verification passed:
  - `python3 -m pytest tests/test_fast_fact_path.py tests/test_analysis_route_policy.py tests/test_workspace_analysis_runner.py -q` (`66 passed`)
  - `python3 -m pytest tests/test_business_answer_quality.py tests/test_evidence_auditor_claim_categories.py tests/test_product_result_builder.py -q` (`53 passed`)

## Latest P29-H1 Result

P29-H1 Local Fast Fact Gate completed on 2026-07-05:

- Added a conservative local fast-fact candidate gate in Data Understanding before Coordinator rejection, so safe factual totals/rankings can override provider false-positive `unsafe_operation` risk flags and proceed as `fast_fact`.
- Kept the gate narrow: one metric, optional one dimension, totals/summaries, rankings, and clear-grain trends only; advice, budget strategy, diagnosis, reports, multi-metric tradeoffs, and true external actions remain out of fast_fact.
- Added a narrow false-positive relaxation for provider `unsafe_operation` on analysis/advice wording, so questions such as `最近30天哪个渠道最值得加预算？请给证据和风险边界。` stay on the full analysis path instead of carrying a stale reject state.
- Added narrow true external-action detection for requests such as adjusting a real budget and sending notifications, which are rejected before SQL.
- Canonicalized provider aliases such as `销售额 + sum_sales_amount` and `渠道 + channel_name`, preventing duplicate labels from forcing simple facts back to `standard_analysis`.
- Verification passed: focused P29 tests (`62 passed`), business-answer/auditor/product regressions (`53 passed`), architecture/project regressions (`9 passed`), and provider/question-understanding regressions (`48 passed`).
- Opt-in live DeepSeek test was skipped because `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS`, `INSIGHTFLOW_PRODUCT_LIVE_MODE`, and `DEEPSEEK_API_KEY` were not set in the shell environment.

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
POST /api/workspaces/{workspace_id}/runs/{run_id}/follow-ups
POST /api/workspaces/{workspace_id}/reports
POST /api/workspaces/{workspace_id}/reports/{report_id}/publish/feishu
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
