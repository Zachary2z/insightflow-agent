# InsightFlow Agent Development Status

Last updated: 2026-07-04

This is the concise current status surface for InsightFlow Agent.

## Current Snapshot

| Field | Status |
|---|---|
| Current phase | P27 Analysis Workbench Multi-Agent Refactor |
| Current task | P27-H3 complete; ready for H4 Evidence Auditor And Business Answer Agent |
| Next planned task | P27-H4 Evidence Auditor And Business Answer Agent |
| Last completed task | P26 Repository Cleanup Before External Tools |
| Active backend | FastAPI in `api/app.py` |
| Active frontend | Next.js + React + TypeScript in `frontend/` |
| Active analysis entry | `POST /api/workspaces/{workspace_id}/runs` |
| Active report entry | `POST /api/workspaces/{workspace_id}/reports` |
| Current answer contract | P16 `business_answer`: `headline`, `direct_answer`, `why`, `evidence_bullets`, `recommendations`, `caveats`, `confidence` |
| Main product target | Chinese-first general business data-analysis multi-agent product with data profiling, semantic layer, task routing, SQL/calculation/chart/report tool calls, evidence validation, Chinese business answers, and coherent Chinese report documents |
| Out of scope for P27 | Report Center rewrite, external SaaS integrations, auth/RBAC, deployment, vector databases, scheduled reports, aggressive semantic search cache, fixed SQL templates, keyword-heavy business rules, table-specific demo logic, and old demo restoration |

## Phase Overview

| Phase | Status | Current meaning |
|---|---|---|
| P0-P10 | `[x]` Complete | Historical foundations for SQL safety, evidence validation, provider plumbing, MCP wrappers, visualization, and trace/artifact hygiene |
| P11 | `[x]` Complete | Workspace data import, profile, semantic-layer draft, and ad hoc analysis through FastAPI + Next.js |
| P12 | `[x]` Complete | Workspace report APIs, runner, storage, Markdown download, and report UI |
| P13 | `[x]` Complete | Business-facing answers, clarification continuation, report reader polish, Data Settings, chart display |
| P14 | `[x]` Complete | Unified Chinese product shell and core workspace pages |
| P15 | `[x]` Complete | Persisted analysis history/detail, schema repair, business-friendly failure UX, real DeepSeek reliability regression |
| P16 | `[x]` Complete | Single clean `business_answer` contract across analysis, reports, Markdown, frontend rendering, and run restoration |
| P17 | `[x]` Complete | Product codebase cleanup; H1-H6 complete |
| P18 | `[x]` Complete | Business answer consistency across conclusions, evidence, recommendations, chart annotations, and reports |
| P19 | `[x]` Complete | Compact quality phase for business-ready replies/reports using reviewer/composer, grounded recommendations, report/chart synthesis, cleanup, and live acceptance |
| P20 | `[x]` Complete | General business analysis foundation: cleanup, generalized profiling/semantic layer, task contract, fact/evidence layer, answer/report generation, realistic acceptance, cleanup audit, and live opt-in verification |
| P21 | `[x]` Complete | Responsive analysis experience: conservative route classification, fast factual path, progress states, exact history reuse, compact task cards, page recovery, and lightweight context packs; H1-H6 complete |
| P22 | `[x]` Complete | Evidence-driven Report Center: H1 replaced the report main contract; H2 added Chinese goal-driven planning and structured evidence collection; H3 added model-backed report composition, API provider wiring, and lightweight fact validation; H4 polished the report reader and Markdown renderer |
| P23 | `[x]` Complete | H1-H6 complete; core evidence/report tooling readiness is clean, regression-tested, no-key verified, and ready to hand off to P24 |
| P24 | `[x]` Complete | H1-H3 complete; real DeepSeek acceptance, cleanup, full verification, frontend build, old-path audit, and artifact hygiene complete |
| P25 | `[x]` Complete | H1-H4 complete; safe missing-time cases now default to full available data range while ambiguous time fields and trend grain gaps still clarify |
| P26 | `[x]` Complete | Cleanup-only phase before external tools; kept history, removed tracked generated artifacts, generated local test DB on demand |
| P27 | `[~]` In progress | H1-H3 complete; Analysis Workbench multi-agent refactor and latency phase; Report Center remains independent and only receives boundary protection |

## P20 Task Status

| Task | Status | Notes |
|---|---|---|
| P20-H0 | `[x]` Complete | Architecture cleanup and main path inventory; removed stale template-mining eval/helper path and clarified current product chain |
| P20-H1 | `[x]` Complete | General profiling/semantic baseline plus safe metric formula quoting and Chinese aliases for English/mixed raw fields |
| P20-H2 | `[x]` Complete | Normalized Chinese `analysis_task` contract, slot-level clarification, partial continuation stays pending, provider output normalized to Chinese |
| P20-H3 | `[x]` Complete | Metric registry, reusable fact/evidence payload, comparison scope, warnings, formulas, and Chinese display values |
| P20-H4 | `[x]` Complete | Evidence-backed Chinese answers, chart intent fallback, and management report synthesis from validated evidence |
| P20-H5 | `[x]` Complete | Realistic acceptance, cleanup audit, documentation closeout, and live DeepSeek verification when enabled |

## P21 Task Status

| Task | Status | Notes |
|---|---|---|
| P21-H1 | `[x]` Complete | Conservative `analysis_route` metadata for `clarify`, `fast_fact`, `standard_analysis`, `deep_judgment`, and `report`; fast path remains metadata-only until H2 |
| P21-H2 | `[x]` Complete | Fast fact path reuses P20 SQL review/execution/evidence validation/fact payloads and skips heavy insight/reviewer/composer/claim typing for simple factual, ranking, summary, and trend questions |
| P21-H3 | `[x]` Complete | Business-friendly `progress_steps` contract and compact frontend progress timeline without exposing raw trace/provider metadata in the main UI |
| P21-H4 | `[x]` Complete | Exact historical reuse with `workspace_id + data_version + normalized_question`; no vector or similar-question cache |
| P21-H5 | `[x]` Complete | Page recovery, lightweight local background work, compact task cards with clamped long questions, and polling-based run detail recovery |
| P21-H6 | `[x]` Complete | Lightweight context packs for `fast_fact`; complex routes keep enough evidence for answer quality |

## P22 Task Status

| Task | Status | Notes |
|---|---|---|
| P22-H1 | `[x]` Complete | Defined new report contracts, cut runner to plan/evidence/document/validation/render/save, deleted fixed English preset and per-section analysis stitching from the report main path, replaced Markdown/frontend report body rendering with `ReportDocument`, and removed old report agent/provider prompt paths |
| P22-H2 | `[x]` Complete | Added Chinese report planner and evidence collector from workspace profile, semantic layer, metric registry, SQL validator/executor, and evidence payload helpers |
| P22-H3 | `[x]` Complete | Added model-backed report composer, API/runtime provider wiring, no-key fallback, and lightweight fact validator |
| P22-H4 | `[x]` Complete | Polished report detail UI and Markdown download into clean Chinese business reports with inline charts, chart-intent placeholders, compact evidence tables, action recommendations, data boundaries, and collapsed non-debug appendices |

P22 planning is recorded in `docs/product/plans/2026-07-02-p22-evidence-driven-report-generation.md`. H1 superseded/deleted the old report main path: fixed English report presets, per-section `run_workspace_analysis()` report generation, stitched report summary helpers, `章节业务答案` main-body rendering, old report supervisor/agent/writer/planner files, old provider report writer/planner flags, and the frontend `ReportSection` business-answer renderer are no longer active report-center code paths. H4 completed the renderer/frontend closeout: Report Center now reads as a business report instead of a debugging page, chart artifacts render inline with download links, chart intents are clearly labeled as待生成图表, Markdown downloads avoid internal dumps, and the appendix stays collapsed with business-readable validation/evidence counts. Remaining search hits for old report terms are historical/superseded notes, negative tests, contract names, or Analysis Workbench tests where `run_workspace_analysis()` remains the correct entry point. P22 does not add external Word/PPT/飞书/腾讯文档 integrations.

P23 planning is recorded in `docs/product/plans/2026-07-03-p23-core-evidence-and-report-tooling-readiness.md`. P23 keeps Analysis Workbench and Report Center separate at the product layer, but makes them share factual evidence, metric, chart artifact, and validation standards. Report Center may collect chapter-level evidence, but it must write the final report once instead of stitching analysis answers together. Model-written explanations and recommendations should be preserved as business judgment; only hard facts such as amounts, dates, rankings, percentages, chart values, and report title/time range are strictly evidence-bound. P23 may delete old templates, stitched report paths, duplicate evidence contracts, stale bilingual branches, mock/demo tests, unused adapters, dead imports, and unreachable compatibility code that conflict with the Chinese-first product path.

P24 planning is recorded in `docs/product/plans/2026-07-03-p24-general-business-data-understanding.md`. P24 is complete. It re-scoped away from immediate external exports and strengthened the Chinese business data analysis foundation across generic field profiling, semantic-layer drafts, evidence requirements, safe evidence calculation, Analysis Workbench grounding, Report Center grounding, real DeepSeek acceptance, and cleanup across different business datasets. P24 has three implementation slices: H1 General Data Understanding, H2 General Evidence Chain, and H3 Real Acceptance And Cleanup; all are complete. Real Word/PPT/PDF/飞书/企业微信/钉钉/腾讯文档 integrations remain deferred until after P24.

P25 planning is recorded in `docs/product/plans/2026-07-04-p25-real-usage-answer-report-polish.md`. P25 is complete: H1 fixes Analysis Workbench directness, evidence-limit contradictions, and stale field fallbacks; H2 simplifies Report Center goal/title inference and removes the main report-type template feel; H3 runs realistic/live acceptance and cleanup; H4 makes missing time ranges use the full available data range when one safe time field exists, while still asking clarification when time fields are ambiguous or analysis trend windows lack grain. Old paths, stale compatibility code, obsolete tests, and unused files can be deleted instead of preserved when they conflict with the current Chinese-first product.

P26 planning is recorded in `docs/product/plans/2026-07-04-p26-repository-cleanup-before-external-tools.md`. P26 is complete: it keeps historical development records, removes tracked generated artifacts, treats `data/ecommerce.db` as a generated local test fixture, and clarifies that the current product path is FastAPI + Next.js + workspace Analysis Workbench + Report Center.

P27 planning is recorded in `docs/product/plans/2026-07-04-p27-analysis-workbench-multi-agent-refactor.md`. P27 primarily refactors Analysis Workbench. The goal is to make the current workflow look and behave more like real multi-agent collaboration instead of a long list of small nodes: Coordinator handles route/state; Data Understanding handles question understanding, clarification, continuation, and `AnalysisTask`; Evidence Agent question mode handles schema/metric/SQL/evidence tool calls; Evidence Auditor handles facts, inferences, unsupported claims, and data limits; Business Answer Agent handles the final Chinese answer; Visualization is on-demand. Report Center remains on its independent report path and must not call Analysis Workbench nodes or stitch Analysis Workbench answers into report sections.

## P27 Task Status

| Task | Status | Notes |
|---|---|---|
| P27-H1 | `[x]` Complete | Added Analysis Workbench contracts and no-key boundary tests proving Report Center stays independent |
| P27-H2 | `[x]` Complete | Coordinator + Data Understanding: consolidated question understanding, clarification, continuation, H1 `AnalysisTask`, and `CoordinatorDecision` route output |
| P27-H3 | `[x]` Complete | Evidence Agent question mode: consolidated analysis evidence planning, schema/metric lookup, SQL candidate/review/repair/execution/fix, and QuestionEvidencePack output |
| P27-H4 | `[ ]` Planned | Evidence Auditor + Business Answer Agent: consolidate evidence validation/claim typing and answer drafting/review/composition |
| P27-H5 | `[ ]` Planned | Analysis Workbench latency optimization: early fast path, conditional model calls, evidence caching, and on-demand visualization |
| P27-H6 | `[ ]` Planned | Cleanup, regression, docs closeout, and optional live DeepSeek acceptance |

## Latest P27-H1 Result

P27-H1 Agent Contracts And Boundary Tests completed on 2026-07-04:

- Added `workspaces/analysis_contracts.py` with stable `AnalysisTask`, `CoordinatorDecision`, `WorkbenchToolCall`, `QuestionEvidencePack`, and `AuditResult` contracts plus lightweight `to_dict/from_dict` serialization.
- Added no-key contract tests proving the new Analysis Workbench contracts can be instantiated and serialized without DeepSeek/provider dependencies.
- Added a runtime Report Center boundary test that makes `run_workspace_analysis()` fail if called, while Report Center still generates a ledger-backed `ReportDocument`.
- Report Center remains on `ReportEvidencePack + EvidenceLedger + ReportDocument`; it does not stitch Analysis Workbench `final_answer` or `business_answer` into report sections.
- Verification passed:
  - `python3 -m pytest tests/test_analysis_contracts.py tests/test_workspace_report_runner.py -q` (`19 passed`)
  - `python3 -m pytest tests/test_workspace_report_runner.py tests/test_report_planner_evidence.py tests/test_report_composer_validator.py -q` (`70 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py -q` (`30 passed`)
  - `python3 -m pytest tests/test_workspace_report_runner.py tests/test_report_planner_evidence.py tests/test_report_composer_validator.py tests/test_workspace_analysis_runner.py tests/test_analysis_contracts.py -q` (`102 passed`)

## Latest P27-H2 Result

P27-H2 Coordinator And Data Understanding completed on 2026-07-04:

- Added `workspaces/data_understanding_agent.py` as the Analysis Workbench Data Understanding surface. It wraps existing deterministic/provider-backed question understanding, clarification question generation, clarification provider fallback, resolved-question continuation, and P25 safe full-data time defaults into the H1 `AnalysisTask` contract.
- Added `workspaces/analysis_coordinator.py` as the Coordinator surface. It converts Data Understanding output plus the existing conservative route policy into H1 `CoordinatorDecision` routes: `clarify`, `fast_fact`, `standard_analysis`, `deep_judgment`, or `reject`, with Chinese route reasons and Chinese required-agent labels.
- Adapted `agents/question_understanding.py` so the Analysis Workbench main path now writes `analysis_task_contract`, `coordinator_decision`, and `data_understanding` state while preserving legacy `analysis_task`, `analysis_route`, and `routing_strategy` fields for the current evidence/SQL/answer chain.
- Made the clarification router reuse Data Understanding's precomputed clarification result, so question understanding and clarification no longer independently rebuild the same missing-slot output on the main path.
- Kept Report Center independent; H2 did not modify report planning, evidence, ledger, composer, validator, Markdown, or report document generation.
- Verification passed:
  - `python3 -m pytest tests/test_analysis_coordinator_data_understanding.py -q` (`7 passed`)
  - `python3 -m pytest tests/test_analysis_contracts.py tests/test_analysis_route_policy.py tests/test_question_understanding_router.py -q` (`31 passed`)
  - `python3 -m pytest tests/test_provider_backed_question_understanding.py tests/test_workspace_analysis_runner.py -q` (`51 passed`)
  - `python3 -m pytest tests/test_workspace_report_runner.py::test_report_center_runtime_does_not_depend_on_analysis_workbench_entrypoint -q` (`1 passed`)

## Latest P27-H3 Result

P27-H3 Evidence Agent Question Mode completed on 2026-07-04:

- Added `workspaces/evidence_agent.py` as the Analysis Workbench Evidence Agent question-mode surface. It wraps the existing evidence planning, schema lookup, metric lookup, SQL candidate building, SQL review, one-pass schema repair, SQL execution, and one-pass execution fix helpers into a single surface.
- The Analysis Workbench graph now routes the evidence acquisition segment through `evidence_agent` while preserving downstream `fast_fact`, standard insight, claim typing, visualization, product result, and trace behavior.
- Evidence Agent emits H1 `QuestionEvidencePack` plus `WorkbenchToolCall` records for schema lookup, metric lookup, SQL planning, SQL candidate building, SQL review, schema repair, SQL execution, and SQL fix where applicable.
- SQL review remains non-bypassable: rejected SQL is not executed; schema repair and execution-fix candidates are re-reviewed before execution; schema repair remains one-pass.
- Product results expose a safe `question_evidence` projection without raw SQL in the main evidence object, while full `question_evidence_pack` stays in technical details.
- Report Center remains independent and does not call Analysis Workbench entrypoints for report sections.

## P25 Task Status

| Task | Status | Notes |
|---|---|---|
| P25-H1 | `[x]` Complete | Analysis answers now directly answer the primary metric, keep calculated evidence and data limits consistent, and stop using stale demo fields |
| P25-H2 | `[x]` Complete | Report Center infers intent/title from the user's goal, keeps broad goals from channel keyword hijack, and makes the main report form goal-first |
| P25-H3 | `[x]` Complete | Realistic Chinese acceptance, opt-in live DeepSeek verification, frontend/backend regression, old-path cleanup, and documentation closeout |
| P25-H4 | `[x]` Complete | Default missing time range to the dataset's full available range when there is one safe time field; still clarify ambiguous time fields or trend grain gaps |

## Latest P25-H4 Result

P25-H4 Default Full Data Time Range For Safe Cases completed on 2026-07-04:

- Added `workspaces/time_range_defaults.py` as the shared Analysis Workbench and Report Center policy. It reads semantic-layer time fields plus profile `value_range` metadata, not table-specific names.
- Analysis Workbench now defaults missing time ranges to `完整数据时间范围：YYYY-MM-DD 至 YYYY-MM-DD` when exactly one safe time field exists, records the default in `analysis_task.defaults_applied`, `resolved_question`, shared evidence payloads, fast-fact context packs, and business-answer caveats, and does not enter `waiting_for_clarification`.
- Analysis Workbench still asks concise clarification when multiple plausible time fields exist (`date_field`) or when trend/同比/环比/变化 questions lack grain (`time_grain`).
- Report Center now uses the same safe full-range policy for missing-time report goals and no longer silently titles those reports as `最近90天`; explicit goals such as `生成最近7天渠道表现复盘报告`, `生成最近180天经营复盘报告`, `生成最近6个月收入趋势报告`, and `生成本季度经营复盘报告` keep the user's time range.
- P25-H4 boundary repair now stops Report Center when a missing-time goal has multiple plausible time fields, returning a clear `date_field` clarification instead of falling back to `当前工作区全部可用数据`.
- Report validation now treats dates from the structured plan time range as supported time context, so full-range date spans are not misread as unsupported prose numbers.
- Live DeepSeek smoke ran with local `.env` and explicit provider flags. Analysis question `哪个客户分群贡献的收入最高？` completed through provider-backed understanding/planning with full range `2025-01-15 至 2026-06-30`; `收入趋势怎么样？` stayed `waiting_for_clarification` with `time_grain`; provider-backed Report Center generated `完整数据渠道表现复盘报告`, validation `passed`, and data boundaries explicitly stated the full data range.
- Verification passed:
  - `python3 -m pytest tests/test_p25_time_range_defaults.py tests/test_clarification_routing.py tests/test_workspace_analysis_runner.py tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_evidence_tool.py -q` (`103 passed`)
  - `python3 -m pytest tests/test_product_result_builder.py tests/test_answer_consistency.py tests/test_workspace_analysis_runner.py -q` (`80 passed`)
  - `python3 -m pytest tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_report_composer_validator.py -q` (`69 passed`)
  - `python3 -m pytest tests/test_p25_real_usage_acceptance.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`51 passed`)
  - `python3 -m pytest tests/test_p20_realistic_acceptance.py tests/test_metric_tool.py tests/test_workspace_profiler.py tests/test_workspace_semantic_draft.py -q` (`31 passed`)
  - `python3 -m pytest tests -q` (`560 passed, 12 skipped`)
  - `cd frontend && npm test` (`69 passed`)
  - `cd frontend && npm run build` passed

## Latest P25-H3 Result

P25-H3 Real Usage Acceptance, Cleanup, And Documentation completed on 2026-07-04:

- Added `tests/test_p25_real_usage_acceptance.py`, a compact generated-data suite that creates Chinese business workspace data in a temp directory and does not depend on saved workspace run/report artifacts.
- Analysis Workbench acceptance covers:
  - `最近90天哪个渠道 ROI 最高？为什么？` -> first sentence names 私域社群 as the ROI leader.
  - `哪个客户分群复购率最高？` -> uses calculated 复购率 evidence for 高价值会员 without reporting 复购率/repeat_rate as missing.
  - `哪个商品品类成交金额最高，哪个销量最高？` -> preserves both 成交金额 and 销量 facts, including different leaders 咖啡豆 and 挂耳咖啡, without data-limit contradictions.
  - `帮我做一下门店经营复盘。` -> uses current 门店/销售额/订单数/毛利率/满意度 evidence and does not fall back to stale demo fields such as `order_date`, `total_revenue`, `marketing_spend`, or `orders_`.
- Report Center acceptance covers:
  - `生成一份最近90天经营复盘报告，包含收入、客户、商品、渠道投放表现和建议。` -> title `最近90天经营复盘报告` with 收入结构、客户分群、商品表现、渠道投放表现 chapters.
  - `生成一份管理层经营简报，重点看渠道效率、商品表现和客户分群。` -> title `最近90天管理层经营简报`.
  - `生成一份最近90天渠道投放表现复盘报告。` -> title `最近90天渠道表现复盘报告`.
  - `生成一份最近90天收入趋势变化报告。` -> title `最近90天趋势变化报告`.
- Report business text is checked for no `章节业务答案`, raw SQL, raw rows, query ids, trace/provider metadata, prompt text, or restored top-level stitched `sections` shape. Report Center still generates one complete `ReportDocument`, not multiple Analysis Workbench answers pasted together.
- Real DeepSeek acceptance ran because local `.env` contains `DEEPSEEK_API_KEY` and opt-in flags were enabled explicitly. Command passed: `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_PRODUCT_LIVE_MODE=1 INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1 INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER=1 python3 -m pytest tests/test_p20_live_deepseek_acceptance.py tests/test_p12_live_deepseek_workspace_report.py tests/test_p11_live_deepseek_workspace_analysis.py -q` (`4 passed in 253.36s`).
- Live record after the P25 fix: analysis question `最近90天按渠道比较收入、投放金额和 ROI，哪个渠道投放效率最高？请给证据、图表和风险边界。`; recognized task `rank` by 渠道 with metrics 销售额、投放成本、收入金额、投放金额、ROI and calculation type `investment_efficiency`; SQL grouped `channel_spend` by 渠道 and calculated 总收入、总投放、ROI、ROAS; evidence rows ranked 私域社群 first by ROI/ROAS, then 小红书, then 抖音; `data_limits` was empty for the calculated ROI evidence.
- Live final analysis reply remained Chinese and evidence-bound: it reported that 抖音 leads by 总收入/总投放 while 私域社群 leads by ROI/ROAS, and kept a tradeoff caveat for multi-metric decision context.
- Live report record: goal `生成经营复盘报告，覆盖门店表现、商品表现、客户分群、客服运营、渠道投放表现、利润和复购率。`; title `最近90天经营复盘报告`; sections `经营概览`, `门店表现`, `收入结构`, `客服问题`, `客服运营`, `渠道投放表现`, `趋势变化`; data boundaries explicitly noted missing 客户分群、利润/毛利/净利, and 复购/留存 evidence where unsupported.
- Live provider calls were recorded on question understanding, SQL planning, guarded SQL candidate, insight drafting, claim typing, and visualization; Report Center recorded `provider_supplied=true`. Report validation status was `passed`, unsupported claims were empty after one provider repair pass, and deterministic fallback repair was not needed.
- Fixed the live-provider H3 edge case where provider metric fragments such as `ROI（收入`, `投放）`, and `销售额（收入）` could make `data_limits` say calculated ROI evidence was missing even when SQL output included `ROI`/`ROAS`/revenue/spend columns. Metric-token normalization now handles bracket/fragment tokens and spend synonyms conservatively.
- Old-path audit found remaining legacy terms only in Historical/Superseded documentation, negative boundary tests, provider/tool rejection tests, or assertions that old strings such as `章节业务答案` and `报告类型` are absent from product output. No active runtime path restored superseded chart, action, mock integration, stitched-report, template, inference, Streamlit, or eval entry points.
- Remaining risk: real provider wording can still choose a multi-metric tradeoff framing when the question includes revenue, spend, and ROI together; deterministic answer consistency and exact ROI questions now keep ROI-first answers, and data limits no longer contradict calculated ROI evidence.
- Verification passed:
  - `python3 -m pytest tests/test_p25_real_usage_acceptance.py tests/test_evidence_tool.py tests/test_report_planner_evidence.py -q` (`48 passed`)
  - `python3 -m pytest tests/test_product_result_builder.py tests/test_answer_consistency.py tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py -q` (`96 passed`)
  - `python3 -m pytest tests/test_p20_realistic_acceptance.py tests/test_metric_tool.py tests/test_workspace_profiler.py tests/test_workspace_semantic_draft.py -q` (`31 passed`)
  - `python3 -m pytest -q` (`548 passed, 12 skipped`)
  - `cd frontend && npm test` (`69 passed`)
  - `cd frontend && npm run build` passed

## Latest P25-H2 Result

P25-H2 Report Goal Inference, Titles, And UI Simplification completed on 2026-07-04:

- Added fail-first coverage for broad经营复盘 goals that mention渠道, management brief goals that mention渠道效率, channel-only goals, and trend-only goals.
- Report planning now infers whole-report intent before local topic keywords. Broad goals keep titles such as `最近90天经营复盘报告`; management brief goals keep `最近90天管理层经营简报`; single-topic channel and trend goals still produce specialized titles.
- Report chapters are still goal/evidence driven: broad goals can include渠道投放表现 without letting that chapter hijack the whole report title or style, and goals mentioning收入、客户、商品、渠道 continue to plan the corresponding chapters.
- Report Center's main form now centers on the report goal. The visible `报告类型` selector was removed from the primary UI, and the frontend sends `business_review` only as an internal default when no explicit type is supplied.
- Report list/detail views no longer foreground `报告类型` as a product-facing template choice. The generated result remains a single `ReportDocument` through the ledger-backed report path, not stitched Analysis Workbench answers.
- Verification passed:
  - `python3 -m pytest tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_report_composer_validator.py tests/test_workspace_report_api.py -q` (`83 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`10 passed`)
  - `python3 -m pytest tests/test_product_result_builder.py tests/test_answer_consistency.py tests/test_workspace_analysis_runner.py -q` (`80 passed`)
  - `python3 -m pytest -q` (`546 passed, 12 skipped`)

## Latest P25-H1 Result

P25-H1 Analysis Answer Decisiveness And Evidence Limits completed on 2026-07-04:

- Analysis Workbench now treats the user's explicit primary metric as the first answer target. ROI questions answer the ROI leader first, then explain revenue scale, spend, and tradeoffs.
- Evidence/data-limit handling now treats SQL-derived aliases and calculated metrics such as `repeat_rate`, 成交金额, and 销量 as supported evidence when they are present in the current run, avoiding contradictory “未计算” caveats.
- Generic semantic-layer SQL generation no longer falls back to old demo fields when no safe current-workspace query can be built. Missing evidence is explained from the current profile/semantic layer instead of trying stale `orders`, `order_date`, `city`, or `total_revenue` assumptions.
- Added focused coverage for ROI leader questions, repeat-rate questions, product category amount/quantity questions, generic store review fallback, and current semantic-layer SQL generation.
- Verification passed:
  - `python3 -m pytest tests/test_product_result_builder.py tests/test_answer_consistency.py tests/test_workspace_analysis_runner.py -q` (`80 passed`)
  - `python3 -m pytest tests/test_evidence_tool.py tests/test_metric_tool.py tests/test_p20_realistic_acceptance.py -q` (`33 passed`)
  - `python3 -m pytest tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py -q` (`9 passed`)
  - `git diff --check` passed

## P24 Task Status

| Task | Status | Notes |
|---|---|---|
| P24-H1 | `[x]` Complete | General data understanding now profiles and drafts semantic layers for 门店销售、商品销售、客服/工单运营 fields beyond the original channel/revenue/spend/order-date sample shape |
| P24-H2 | `[x]` Complete | General evidence chain now turns questions/report goals into explicit evidence requirements and uses semantic-layer SQL/evidence tools for ranking, contribution/share, operational-efficiency, same-table investment-efficiency, and conservative data limits |
| P24-H3 | `[x]` Complete | Real DeepSeek acceptance, realistic multi-dataset regression, cleanup, full backend/frontend verification, old-path audit, and artifact hygiene |

## Latest P24-H3 Result

P24-H3 Real Acceptance And Cleanup completed on 2026-07-04:

- Added P24 realistic acceptance across six Chinese business dataset shapes: 门店销售、商品/品类销售、客户分群、客服/工单运营、渠道投放、区域表现.
- Analysis Workbench now verifies generic semantic-layer SQL/evidence for ranking, contribution/share, operational efficiency, same-table investment efficiency, report-safe chart artifacts, formula traceability, and unsupported复购/趋势 data limits.
- Report Center now verifies one coherent Chinese report over the same realistic workspace, with report evidence payloads, evidence ledger, chart artifacts, data boundaries for missing利润/复购 inputs, and no stitched Analysis Workbench answer blocks.
- Fixed P24 closeout issues found by acceptance: month-grain `YYYY-MM` time fields now work in generic SQL filters, all-zero report chart values no longer crash SVG rendering, metric registry selects compatible same-table revenue/spend pairs for ROAS/net-return even when other revenue metrics exist, and ratio/AOV formulas use floating-point division.
- Fixed the P24-H3 closeout blocker where answer consistency treated “最值得优先复盘/优先处理/风险/改善” as a highest-value ranking. The consistency layer now distinguishes risk/improvement decisions from growth/best/benchmark decisions, keeps `final_answer` and `business_answer` aligned, and does not rewrite a supported low-performance/high-risk object such as 深圳湾店 into the highest-sales object.
- Fixed the final P24-H3 intent edge case where natural question prefixes such as “我有个问题” could trigger risk/improvement direction through the standalone word “问题”. Growth/best/benchmark markers such as “表现最好” and “标杆” now win, so the benchmark question correctly keeps 上海旗舰店 as the supported high-performance object while “客服问题最需要优先处理” remains risk-directed.
- Report Center live stability now has a deterministic ledger-backed fallback when provider report repair still fails validation or leaves the document partial, so real provider calls remain recorded without letting unsupported provider prose close the report as complete.
- Real DeepSeek acceptance ran with local `.env` plus explicit opt-in flags. The new P24 live test records the analysis question, recognized task, semantic fields/metrics, evidence requirements, evidence rows, model answer, report goal, report summary/sections, artifacts, and data limits. The live suite passed: `python3 -m pytest tests/test_p20_live_deepseek_acceptance.py tests/test_p12_live_deepseek_workspace_report.py tests/test_p11_live_deepseek_workspace_analysis.py -q` (`4 passed in 210.23s`).
- Analysis Workbench and Report Center remain separate product experiences. Report Center uses one full ledger-backed report document, not concatenated analysis answers.
- Old-path audit found remaining legacy/mock/demo terms only in Historical/Superseded docs, negative boundary tests, or external-tool rejection tests. Tracked-artifact audit found no committed `.env`, `.next`, caches, workspace run/report output, report chart artifacts, trace JSON, or sample data.
- Verification passed:
  - `python3 -m pytest tests/test_answer_consistency.py tests/test_product_result_builder.py -q` (`47 passed`)
  - `python3 -m pytest tests/test_p20_realistic_acceptance.py tests/test_workspace_analysis_runner.py tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_metric_tool.py tests/test_evidence_tool.py -q` (`108 passed`)
  - `python3 -m pytest tests/test_p20_live_deepseek_acceptance.py tests/test_p12_live_deepseek_workspace_report.py tests/test_p11_live_deepseek_workspace_analysis.py -q` (`4 passed in 210.23s`, real DeepSeek opt-in)
  - `python3 -m pytest` (`539 passed, 12 skipped`)
  - `cd frontend && npm test` (`68 passed`)
  - `cd frontend && npm run build` passed
  - `git diff --check` passed
  - tracked-artifact audit returned no hits
  - old-path audit returned only historical documentation and negative/rejection tests

## Latest P24-H2 Result

P24-H2 General Evidence Chain completed on 2026-07-03:

- Added fail-first coverage for generic 门店销售 ranking, 商品销售 contribution/share, 客服/工单 operational efficiency, report-goal planning, report evidence collection, and unsafe cross-table投放效率 data limits.
- Shared evidence payloads now expose explicit `evidence_requirements`: time range, metrics, dimensions, filters, grouping, comparison scope, calculation type, and missing evidence.
- Analysis Workbench can generate semantic-layer-backed SQL/evidence for common business questions without relying on the original `orders/channel/revenue/spend/order_date` shape.
- Report Center plans and collects evidence for经营复盘、门店表现、商品表现、客服运营、渠道投放表现 from the same requirements/evidence path while preserving one coherent Chinese report composition.
- Cross-table investment-efficiency evidence is conservative: ROAS/净投放回报率 is calculated only when required metrics are safe in the same analyzable table or supported by the metric registry; otherwise the report records a data limit instead of hard-calculating.
- Remaining P24-H3 work: real DeepSeek acceptance, full cleanup, frontend verification, tracked-artifact audit, and final old-path audit.
- Verification passed:
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_report_planner_evidence.py tests/test_report_composer_validator.py tests/test_metric_tool.py tests/test_evidence_tool.py -q` (`107 passed`)
  - `python3 -m pytest tests/test_p20_realistic_acceptance.py tests/test_product_result_builder.py -q` (`32 passed`)
  - `python3 -m pytest tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py -q` (`9 passed`)

## Latest P24-H1 Result

P24-H1 General Data Understanding completed on 2026-07-03:

- Added fail-first coverage for three non-original-sample datasets: 门店销售, 商品销售, and 客服/工单运营.
- Profiling now recognizes common business roles for 时间字段, 金额/收入字段, 成本/投放字段, 数量字段, ID 字段, 维度字段, 订单数字段, 工单数字段, and response-duration style operational metrics.
- Semantic drafts now generate Chinese business aliases and labels for fields such as GMV, 实付金额, 成交金额, 收入金额, 订单数, 件数, 销量, 工单数, 采购成本, and 平均响应分钟.
- Semantic drafts now expose capability flags and data limits for missing time fields, missing cost fields, missing spend/ROI inputs, and missing cross-table relationship fields instead of inventing unavailable metrics.
- Metric registry now preserves semantic-layer capability flags and only generates ROAS/净投放回报率/利润率 when the required metrics are in the same table or can be safely combined through a confirmed relationship/join capability. Unrelated cross-table收入+投放 stays a warning/data limit instead of a formula.
- Evidence payloads can surface missing time/cost/ROI/join capability limits from the real metric registry when requested metrics or task requirements need those inputs.
- Remaining P24-H2 work: convert natural-language questions/report goals into explicit evidence requirements and use the strengthened semantic layer for generic SQL/evidence collection, including safe cross-table evidence when joins are actually available.
- Verification passed:
  - `python3 -m pytest tests/test_workspace_profiler.py tests/test_workspace_semantic_draft.py tests/test_metric_tool.py tests/test_evidence_tool.py -q` (`38 passed`)
  - `python3 -m pytest tests/test_p20_realistic_acceptance.py tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q` (`58 passed`)
  - `python3 -m pytest tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py -q` (`9 passed`)

## P23 Task Status

| Task | Status | Notes |
|---|---|---|
| P23-H1 | `[x]` Complete | Shared EvidencePack foundation: analysis `fact_payload` and report `ReportEvidencePack.evidence_payloads` now share the same factual payload vocabulary with traceable derived metrics, formulas, chart-ready data, warnings/data limits, and technical-detail references |
| P23-H2 | `[x]` Complete | Chinese Business Answer Writer: natural Chinese business answers preserve model explanations/recommendations while binding hard facts and missing-data boundaries to shared evidence |
| P23-H3 | `[x]` Complete | One-Pass Report Center With Shared Evidence |
| P23-H4 | `[x]` Complete | Evidence Ledger And Report Self-Repair: replaced prose-number validator patching with tool-built evidence ledger, ledger-backed report writing, factual-claim validation, one automatic repair pass, evidence-aware coverage, and conservative metric-role-based contribution metric selection |
| P23-H5 | `[x]` Complete | Artifact And Tool-Calling Readiness: chart/report artifacts and local renderer tool calls now cite EvidenceLedger facts/metrics without raw rows or model-recomputed facts |
| P23-H6 | `[x]` Complete | Cleanup, Regression, And Live Acceptance for the ledger-backed report chain, artifact references, old-path deletion, no-key mode, artifact hygiene, and live DeepSeek gating |

## Latest P23-H6 Result

P23-H6 Cleanup, Regression, And Live Acceptance completed on 2026-07-03:

- P23 can close. Analysis Workbench and Report Center remain separate product entries; Report Center remains the one-pass ledger-backed report path and does not restore per-section analysis stitching.
- Fixed closeout regressions found by full build/test: prompt-registry tests now assert the current `guarded_sql_candidate` v2 contract, provider-backed insight tests assert the current canonical data caveat, run-history tests assert normalized Chinese headline punctuation, and `ReportViewer` now preserves `ReportDocumentSection.chart_refs` in its TypeScript helper.
- Report artifacts and tool-call records remain tied to ledger facts/derived metrics. Chart artifacts from `evidence_pack.charts` are preserved into `report.artifacts`, and the main report UI keeps SQL, raw rows, query ids, trace/provider metadata, local absolute paths, ledger ids, artifact ids, and tool names out of the business-facing view.
- Old-path audit found remaining `chart_agent`, `visualization_planner`, `chart_tool`, `action_delivery`, `action_drafter`, `powerbi_publisher_mock`, `jira_ticket_mock`, `streamlit`, `eval/run_eval`, fixed-template, keyword-inference, and `章节业务答案` hits only in Historical/Superseded documentation, negative boundary tests, or assertions that those strings are not product output.
- Tracked artifact audit passed with no committed `.env`, `frontend/.next`, pytest/cache files, `__pycache__`, workspace run/report output, chart/markdown report artifacts, trace JSON, or sample data.
- Live DeepSeek provider acceptance was not run in this environment because `DEEPSEEK_API_KEY`, `INSIGHTFLOW_PRODUCT_LIVE_MODE`, `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS`, and `INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER` were absent. This was recorded explicitly instead of treating skipped tests as provider calls.
- No-key mode remains runnable and verified through deterministic report fallback tests plus the full regression suite.
- Verification passed:
  - `python3 -m pytest tests/test_report_planner_evidence.py tests/test_report_composer_validator.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`75 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`67 passed`)
  - `python3 -m pytest tests/test_p20_architecture_cleanup_boundaries.py tests/test_p17_product_cleanup_boundaries.py tests/test_mcp_tool_layer.py -q` (`21 passed`)
  - `python3 -m pytest` (`511 passed, 11 skipped`)
  - `python3 -m pytest tests/test_p20_live_deepseek_acceptance.py tests/test_p12_live_deepseek_workspace_report.py tests/test_p11_live_deepseek_workspace_analysis.py -q` (`3 skipped`, live env absent)
  - `python3 -m pytest tests/test_report_composer_validator.py::test_report_composer_no_key_fallback_returns_chinese_report_document tests/test_workspace_report_api.py::test_create_report_keeps_no_key_mode_when_report_composer_provider_unavailable -q` (`2 passed`)
  - `cd frontend && npm test` (`68 passed`)
  - `cd frontend && npm run build` passed
  - `git diff --check` passed
  - `git ls-files | rg '(^|/)\\.env$|frontend/\\.next|\\.pytest_cache|__pycache__|workspace_data/.*/runs/|workspace_data/.*/reports/|reports/charts/.*\\.(png|jpg|jpeg|svg)|logs/traces/.*\\.json|sample_data/'` returned no tracked artifact hits

## Latest P23-H5 Result

P23-H5 Artifact And Tool-Calling Readiness completed on 2026-07-03:

- Added `ReportArtifactRecord` and `ReportToolCallRecord` to the report contract. Artifact records cover chart, Markdown report, report document, and future export readiness with title, relative path or download URL, source, evidence ids, ledger metric ids, chart ids, timestamps, status, and error.
- Extended `ReportEvidenceChart` so local chart artifacts carry `artifact_id`, ledger fact ids, and ledger derived metric ids. `build_evidence_ledger()` annotates charts from their `evidence_ref`, so chart artifacts are tied to trusted ledger facts rather than loose table titles.
- Report Center now records local chart renderer and Markdown renderer calls with safe input summaries, referenced ledger evidence ids, output artifact ids, status/error, and start/complete times.
- Markdown/report document artifacts now include ledger reference summaries. Future external export tools can use artifact ids plus ledger evidence ids to retrieve trusted facts instead of re-querying SQL or asking the model to recalculate.
- `ReportViewer` shows only business-readable artifact summaries such as chart, Markdown report, report document, or future export readiness status. The main report UI still hides raw ledger JSON, SQL, raw rows, query ids, trace/provider metadata, local paths, artifact ids, ledger ids, and tool names.
- No real PowerPoint, Word, PDF, 飞书, 钉钉, 企业微信, or other SaaS integration was added, no simulated external integration layer was introduced, and old `chart_tool`, `action_delivery`, `powerbi_publisher_mock`, or `jira_ticket_mock` paths were not restored.
- Verification passed:
  - `python3 -m pytest tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`54 passed`)
  - `python3 -m pytest tests/test_report_composer_validator.py tests/test_workspace_report_store.py -q` (`25 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`67 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`9 passed`)

## Latest P23-H4 Result

P23-H4 non-additive contribution metric repair completed on 2026-07-03:

- Tightened report ledger contribution metric selection so only additive/count metrics can produce SUM-backed totals, shares, combined top-2 shares, and contribution rankings.
- ROI, conversion/rate fields, satisfaction, scores, average values, customer unit price, response durations, and unknown numeric fields remain available as row facts but no longer become default contribution denominators or misleading合计/占比 facts.
- Fixed revenue coverage field existence checks to use only fact ids, fact labels, fact units, and table columns. Table titles and descriptions remain display text but cannot convince coverage that成本、利润、ROI fields exist.
- Added fail-first regressions for ROI-only tables, average/duration-only support tables, and revenue-only tables whose title/description mention ROI or成本.
- Verified that Report Center still uses one-pass composition plus optional one repair and did not restore prose-number validator patching or section-answer stitching.
- Verification passed:
  - `python3 -m pytest tests/test_report_planner_evidence.py tests/test_report_composer_validator.py -q` (`45 passed`)
  - `python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`25 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`86 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`9 passed`)

P23-H4 evidence-aware ledger repair completed on 2026-07-03:

- Fixed chapter coverage so `revenue_structure` checks actual evidence fields/facts before reporting missing成本、利润、ROI. When only part of that evidence is missing, the ledger now names only the missing inputs instead of emitting a fixed boundary.
- Removed fixed optional coverage gaps for `customer_segments` and `support_issues`; those chapters now become partial only when real warnings/data limits or missing minimum evidence justify it.
- Added compact metric role selection for report ledger tables. Additive business metrics such as收入、销售额、金额、订单数、工单量 are preferred for contribution totals, shares, combined shares, and rankings; ROI/rates/averages/satisfaction/duration fields stay available as row facts but are not default contribution-share denominators.
- Added fail-first regression coverage for revenue tables containing收入、成本、ROI, revenue-only tables, and support/customer tables with valid evidence fields.
- Verified that Report Center still uses one-pass composition plus optional one repair and did not restore Analysis Workbench section-answer stitching or prose-number validator patching.
- Verification passed:
  - `python3 -m pytest tests/test_report_planner_evidence.py tests/test_report_composer_validator.py -q` (`42 passed`)
  - `python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`25 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`86 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`9 passed`)

P23-H4 Evidence Ledger And Report Self-Repair completed on 2026-07-03:

- Added `workspaces/report_ledger.py` plus serializable `EvidenceLedger`/coverage models. Report Center now builds `p23.report_ledger.v1` before writing, with ledger facts, derived metrics, chapter coverage, recommendation context, data boundaries, and technical refs.
- The ledger derives common report facts from generic evidence tables and shared payloads: row facts, totals, shares, combined top-2 shares, rankings, period changes, max/min periods, and data coverage ranges. Missing cost/profit/ROI/retention/loss fields become explicit boundaries instead of model guesses.
- ReportComposer now receives `ReportPlan + EvidenceLedger + chart refs + data boundaries`, writes one complete `ReportDocument`, and keeps action recommendations out of body sections. No section-answer stitching or Analysis Workbench chapter generation was restored.
- ReportValidator now validates hard factual claims against the ledger value set. It still checks title/time range/data sources, evidence/chart refs, date forms, ranking conflicts, and unsupported invented amounts/percentages, while clearly worded recommendation targets are not treated as historical facts.
- Runner now follows `plan -> evidence -> ledger -> one-pass compose -> ledger-backed validate -> optional one repair -> render/save`. If unsupported hard facts remain, one repair pass asks the provider to delete, soften, or replace them; no-key mode has deterministic repair fallback.
- Markdown and ReportViewer keep the main report clean and show only concise coverage summaries in the collapsed technical appendix; raw ledger JSON, SQL, raw rows, trace, query ids, and provider metadata stay out of the main body.
- Removed the old validator branches that tried to rediscover table shares, chapter-total shares, and payload percentages directly from final prose.
- Live DeepSeek smoke passed with provider available: report status `completed`, validation `passed`, `unsupported_claims` empty, `generation_flow=ledger_backed_report_center`, `provider_supplied=true`, one repair attempted, no duplicate action section, no SQL/raw_rows/trace/provider_metadata/query leaks in main body, and the ledger contained total/share/combined-share/period-change evidence.
- Verification passed:
  - `python3 -m pytest tests/test_report_composer_validator.py tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`64 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`86 passed`)
  - `python3 -m pytest tests/test_workspace_report_store.py tests/test_p20_realistic_acceptance.py tests/test_p12_live_deepseek_workspace_report.py -q` (`8 passed, 1 skipped`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`9 passed`)

## P23-H4 Direction Update

P23-H4 should not continue the P23-H3 pattern of adding validator rules for every new number DeepSeek can produce. Live report testing showed that models can produce correct but previously unregistered derived values such as totals, combined shares, period-over-period changes, and recommendation target values. Chasing all of these in the final prose validator would make the code increasingly brittle.

The next implementation should instead introduce a compact report evidence ledger before report writing:

- tools calculate raw facts and common derived metrics first, including totals, shares, combined shares, rankings, period changes, and data coverage facts;
- each report fact gets an `evidence_id`, display value, formula/source description, and acceptable claim phrases;
- each report chapter gets coverage metadata: available evidence, missing evidence, allowed claims, blocked claims, and data boundaries;
- derivable missing evidence is completed by tools before writing, while unavailable source fields become explicit data boundaries;
- the report composer receives the ledger, chart refs, and data boundaries, then writes a natural Chinese report using ledger-backed hard facts;
- validation checks factual claims against the ledger and treats clearly worded recommendation targets as proposed actions, not historical facts;
- if unsupported factual claims remain, one automatic repair pass asks the model to delete, soften, or replace only those claims before the user sees the final report.

Cleanup requirement: while implementing P23-H4, delete old validator branches, obsolete compatibility fields, stale tests, fallback code, and old report paths that are made unreachable by ledger-backed validation. Do not keep old code only to preserve historical report behavior. The current product direction is a clean Chinese-first FastAPI/Next.js analysis and report product.

## Latest P23-H3 Result

P23-H3 time-range and date-evidence validator repair completed on 2026-07-03:

- Locked provider-composed `ReportDocument.time_range` to `ReportPlan.time_range`, so providers may describe actual data coverage such as `2026年4月至6月` in report prose but cannot drift the structured report time range away from the plan.
- Extended `report_validator` to treat evidence-backed month/date expressions as time facts instead of unsupported ordinary numbers, including forms such as `2026-04`, `2026年4月至6月`, and spaced Chinese forms such as `2026 年 4 月至 6 月`.
- Kept number validation strict for non-date claims: unsupported business numbers such as `2026 单` still produce warning validation.
- Extended supported hard-fact forms from shared evidence payloads, table column units, currency display variants, metric-column unit conversions, and same-chapter total facts, so model prose such as `4.5万元`, `100 行`, `0.77万`, and evidence-derived shares such as `20.4%` validate only when backed by the current evidence pack.
- Live DeepSeek report smoke passed with provider available: status `completed`, validation `passed`, `unsupported_claims` empty, stable plan/document time range, no duplicate行动建议 section, and no SQL/raw rows/trace/provider metadata leaks in the main body.
- Verification passed:
  - `python3 -m pytest tests/test_report_composer_validator.py tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`56 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`86 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`9 passed`)

P23-H3 derived-share validator and duplicate-action repair completed on 2026-07-03:

- Fixed `report_validator` so percentages such as `26.8%`, `18.6%`, and `15.5%` pass only when they can be directly derived from numeric values in the same `ReportEvidenceTable`; unrelated percentages such as `99.9%` still produce warning validation.
- Updated provider and fallback report composition so an `actions` / `行动建议` section is filtered out of `ReportDocument.sections`; recommendations remain in the bottom-level `action_recommendations` list.
- Added defensive Markdown and `ReportViewer` filtering so older or provider-shaped documents with an actions section do not render duplicate “行动建议” blocks. Progress counts now use only business body sections.
- Verification passed:
  - `python3 -m pytest tests/test_report_composer_validator.py tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`49 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`86 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`9 passed`)
  - `git diff --check` passed

P23-H3 One-Pass Report Center With Shared Evidence completed on 2026-07-03:

- Strengthened Report Center tests so the main path cannot call `run_workspace_analysis()` for report sections, cannot use Analysis Workbench `business_answer` blocks as report body, and must call `report_composer` once with the full plan plus evidence pack.
- Added `ReportPlan.report_goal` and channel-specific title/style handling so goals such as “最近90天渠道表现复盘报告” produce that report identity instead of generic English or management-summary titles.
- Report evidence collection now records requested-but-missing ROI and投放成本 as data boundaries when the workspace lacks those fields, while preserving supported revenue/order evidence instead of failing the whole report.
- Evidence collection can materialize chartable report evidence tables into local SVG chart artifacts under the report artifact directory. `ReportViewer` and Markdown continue to inline real chart artifacts with download links, while missing charts remain business-readable placeholders.
- Removed obsolete top-level report compatibility fields (`executive_summary`, `key_findings`, `action_priorities`, `chart_and_evidence`, `risks_and_limits`, and old `sections`) from `ReportRecord`, API types, frontend fixtures, and report storage. The current report body is only `ReportDocument`.
- Kept technical details in the collapsed appendix and report JSON technical paths; the main report body remains free of SQL, raw rows, query ids, provider metadata, trace paths, internal contract names, and section-answer labels.
- Verification passed:
  - `python3 -m pytest tests/test_report_planner_evidence.py tests/test_report_composer_validator.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`45 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`86 passed`)
  - `python3 -m pytest tests/test_workspace_report_store.py tests/test_p20_realistic_acceptance.py -q` (`8 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`9 passed`)

## Latest P23-H2 Result

P23-H2 provider comparison-scope repair completed on 2026-07-03:

- Added a shared SQL comparison-scope guard in `sql_planning.comparison_scope` so judgment, priority, recommendation, budget, optimization, and why-plus-comparison questions require comparable multi-row evidence unless the user explicitly asks for only one result.
- Updated the guarded provider SQL candidate path and final SQL reviewer to widen safe validated `LIMIT 1` SELECT queries to `LIMIT 3` for comparison-needed questions, recording `comparison_scope_adjustment.reason = insufficient_comparison_scope` before execution.
- Updated the provider SQL candidate prompt so live DeepSeek planning is instructed to return multiple candidate objects, usually `LIMIT 3` or `LIMIT 5`, for why/advice/priority/budget questions while keeping pure factual highest/lowest questions eligible for `LIMIT 1`.
- Tightened task normalization so provider outputs and Chinese questions containing 优先、最需要、值得、关注、复盘 are treated as recommendation/deep-judgment style tasks instead of summary-only tasks.
- Added provider-mock and full workspace-chain regressions proving a support-issue priority question with provider SQL `LIMIT 1` executes with at least two comparison rows and the final business answer mentions multiple候选对象 without exposing aliases, SQL, raw rows, or `execution_result`.
- Verification passed: provider/workspace/composer/product/consistency set (`94 passed`), business quality/fast fact set (`23 passed`), and focused frontend workspace-flow Vitest (`54 passed`).

P23-H2 metric alias and tradeoff repair completed on 2026-07-03:

- Added shared dynamic business field labeling in `workspaces.answer_evidence` so SQL aliases such as `total_tickets`, `avg_response`, and `priority_score` render as 总工单数、平均响应时长、优先级评分 in product-facing Chinese answers.
- Added shared metric-leader/tradeoff helpers and reused them from the final composer and consistency guardrail, so multi-metric answers say which object leads by each metric instead of implying one object leads every metric.
- Tightened deterministic and provider-normalized Chinese wording: ordinary fact questions keep recommendations empty; explicit 优先处理、优化、预算、下一步 questions retain recommendations inside the evidence boundary.
- Fixed the consistency layer so tradeoff rewrites use business metric labels, keep cause explanations as hypotheses, and state that current result metrics cannot directly prove原因.
- Added full-chain support-issue coverage for aliased SQL metrics and verified the manual support_issues example returns business labels without `total_tickets`, `avg_response`, `priority_score`, `第 1 行`, `execution_result`, SQL, or raw rows in the main answer.
- Verification passed: answer consistency/composer/product/workspace set (`85 passed`), business quality/fast fact set (`23 passed`), and focused frontend workspace-flow Vitest (`54 passed`).

P23-H2 evidence wording repair completed on 2026-07-03:

- Replaced row-style Chinese evidence bullets such as `第 1 行` and raw-field `字段 为 值` strings with business evidence sentences built from the returned entity and metric rows.
- Added shared wording helpers for business row evidence and cause-hypothesis context so support-ticket, channel, and store scenarios get domain-appropriate hypothesis language instead of one fixed原因模板.
- Why/cause answers now say when current data only proves the result ranking and cannot directly prove the cause; hypotheses are phrased as possible directions that need process data validation.
- Recommendation generation is now limited to explicit advice, optimization, priority, budget, or next-step questions; ordinary fact and why questions do not auto-fill recommendations.
- The final consistency guard now localizes common service metrics such as工单数 and平均响应时长 in tradeoff rewrites instead of exposing raw field names.
- Verification passed: composer/product/business quality set (`59 passed`), workspace analysis/fast fact set (`32 passed`), and focused frontend workspace-flow Vitest (`54 passed`).

P23-H2 Chinese Business Answer Writer completed on 2026-07-03:

- Added fail-first backend and frontend coverage for natural Chinese business answers without template/debug phrases, internal statuses, SQL, raw rows, trace ids, provider metadata, or direct-answer repetition in recommendations.
- Updated the final answer composer/provider prompt, product result fallback builder, insight fallback text, and final consistency guardrail so Chinese answers read like business analysis: factual conclusion, evidence-based reason, hypothesis-style interpretation when causes are not directly proven, conditional recommendations, and business data-boundary caveats.
- Missing ROI, cost, conversion, or repeat-purchase inputs now preserve supported revenue/ranking conclusions while clearly saying what cannot be concluded and what data should be added before budget or efficiency decisions.
- Product-facing caveats now describe query/data scope instead of model cleanup internals; recommendations no longer simply repeat `direct_answer`.
- Added a non-channel service-issue workspace analysis regression proving the answer writer stays natural and does not depend on channel/orders/revenue-only sample logic.
- Analysis Workbench frontend still renders business answer before evidence/charts and keeps technical details collapsed by default.
- Cleanup audit found remaining old wording/path hits only in historical/superseded docs, negative tests, cleanup-boundary tests, and the P23 task text itself; no active product-code path needed further migration.
- Verification passed: composer/product/business quality set (`54 passed`), workspace analysis/fast fact set (`32 passed`), and focused frontend workspace-flow Vitest (`54 passed`).

## Latest P23-H1 Result

P23-H1 Shared EvidencePack Contract completed on 2026-07-03:

- Extended `tools/evidence_tool.build_evidence_payload()` into the shared P23 factual payload (`p23.shared.v1`) while preserving existing Analysis Workbench `fact_payload` consumers.
- The shared payload now includes intent, `time_range`, metrics, dimensions, structured result rows, derived share/rank/trend metrics, formula metadata with source columns, chart-ready data, warnings/data limits, display values, and references to technical details.
- Unsupported requested metrics such as ROI are recorded as data limits when the current evidence fields/metric registry cannot compute them, instead of allowing model output to invent the metric.
- Report Center now exposes the same payloads through `ReportEvidencePack.evidence_payloads`; evidence tables can point back through `evidence_payload_ref`. SQL/raw rows stay in report technical details/appendix and do not enter the report body.
- Added non-channel store-sales coverage proving the shared contract does not assume `orders`, `marketing_spend`, `channel`, revenue-only demo tables, or ROI-only channel analysis.
- Cleanup audit found stitched/fixed-template/legacy chart/mock terms only in historical/superseded docs, negative boundary tests, and P23 follow-up cleanup wording; no active product-code path needed migration for H1.
- Focused verification passed: evidence/metric/product-result/report-planner set (`51 passed`), workspace analysis/report runner set (`32 passed`), report composer/API/store set (`25 passed`), and frontend workspace-flow Vitest (`54 passed`).

P23-H1 boundary fix completed on 2026-07-03:

- Shared business evidence payloads no longer embed `technical_sql` or `technical_details.sql`. Analysis Workbench reads SQL from `product_result.technical_details.sql`; Report Center reads SQL from `ReportEvidencePack.technical_details["queries"]`.
- Report Center strips SQL refs, raw `rows`, trace/query/provider metadata, and other technical-only fields from top-level `ReportEvidencePack.evidence_payloads`, while keeping the full technical query records in the appendix path.
- Derived share/rank/trend metrics now choose numeric columns by requested metric, metric registry metadata, and business aliases before falling back to the first numeric column, so收入 questions over `order_count` plus `revenue` generate `revenue_share`/`revenue_rank`.
- Fix verification passed: evidence/product-result/report-planner set (`45 passed`) and workspace analysis/report runner set (`32 passed`).

## Latest P22-H4 Result

P22-H4 Report Center UI and Markdown rendering polish completed on 2026-07-02:

- Updated `workspaces/report_markdown.py` so Markdown downloads render a clean Chinese report: title, generated status/time, time range, data sources, opening summary, chapters, inline chart artifacts or待生成图表 prompts, compact evidence tables, action recommendations, data boundaries, and a collapsed technical appendix with only validation/evidence counts.
- Updated `frontend/components/ReportViewer.tsx` so the report detail page no longer presents the report goal as a debug field. It shows report metadata, body chapters, real chart images with “下载图表”, chart-intent placeholders when no artifact exists, evidence tables, action recommendations, and data boundaries in report-reading order.
- Updated `frontend/components/ReportTechnicalAppendix.tsx` so expanding the appendix shows only business-readable evidence and validation summaries instead of JSON dumps, SQL, raw rows, query ids, provider metadata, trace paths, or report contract internals.
- Added/updated backend and frontend tests to cover clean Markdown downloads, chart artifact display, no-artifact chart-intent copy, collapsed appendix behavior, and hiding old report/debug fields from the main reader.
- Focused verification passed: report API/runner/store/composer-validator regression (`33 passed`) and focused frontend Vitest (`63 passed`).

## Latest P22-H3 Result

P22-H3 model-backed report composer and lightweight fact validator completed on 2026-07-02:

- Added `workspaces/report_composer.py` for `ReportPlan + ReportEvidencePack -> ReportDocument`. It asks a provider for structured Chinese JSON when available, keeps the prompt inside the evidence boundary, filters unsupported refs, blocks SQL/raw-row/provider/trace leakage from the main body, and falls back to deterministic Chinese composition when no provider or invalid provider output is available.
- Added `workspaces/report_validator.py` for lightweight key-fact checks: title/time range alignment, evidence refs, key numbers, data sources, and top-ranked entity conflicts within the relevant chapter. Reasonable qualitative recommendations remain allowed when grounded in evidence.
- `workspaces/report_runner.py` now delegates composition and validation to those modules, preserving the clean `plan -> evidence -> compose -> validate -> save/render` path without per-section analysis runs.
- `llm_ops/runtime_provider.py` now supports `INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER`, and `INSIGHTFLOW_PRODUCT_LIVE_MODE=1` also enables the current report composer provider. `api/app.py` passes `providers={"report_composer": provider}` into `run_workspace_report()` when the provider can be built; no-key mode still passes no provider and uses fallback.
- Workspace settings now include the `report_composer` provider feature with the Chinese label `报告撰写`.
- Verification passed: focused report composer/planner/runner/API/store regression (`40 passed`), focused P20/project/P17/P20 boundary regression (`26 passed`), and focused frontend Vitest (`63 passed`).

## Latest P22-H2 Result

P22-H2 Chinese report planner and evidence collector completed on 2026-07-02:

- Added `workspaces/report_planner.py` for Chinese-first report planning from report type, user goal, workspace profile, and semantic layer. Goals such as 经营复盘、收入结构、客户分群、客服问题、趋势变化、行动建议 now produce matching Chinese chapters.
- Added `workspaces/report_evidence.py` for structured evidence collection. It reuses the metric registry, SQL validator, SQL executor, and evidence payload helper; SQL and raw execution details stay in technical details.
- H2 repair aligned report titles, `time_range`, and evidence SQL. 最近90天、最近30天、本月、本周 evidence filters use the relevant table's maximum date as the anchor, not the system date.
- If a requested evidence query cannot apply the report time range because the table has no time field, the evidence pack records a warning or data boundary instead of silently using full-table evidence.
- Evidence packs now include business-readable Chinese facts, display values, evidence tables, chart intents, warnings, data limits, and technical query details.
- `run_workspace_report()` no longer accepts the old removed section compatibility parameter and no longer keeps its provider metadata marker. The report path remains plan -> evidence -> compose -> validate -> render -> save.
- Markdown and the report detail UI now render business-readable evidence table titles, descriptions, and small tables in the main body while keeping internal ids, SQL, raw rows, trace, provider metadata, and query details in the technical appendix.
- Verification passed: report planner/evidence plus runner focused tests (`12 passed`), report API/store regression (`25 passed`), P20 realistic acceptance (`3 passed`), cleanup boundary regression (`23 passed`), report/product-result/analysis regression (`53 passed`), and focused frontend Vitest (`63 passed`).

## Latest P22-H1 Result

P22-H1 report contract and cutover completed on 2026-07-02:

- Added the new report contracts in `workspaces/report_models.py`: `ReportPlan`, `ReportChapterPlan`, `EvidenceRequirement`, `ReportEvidencePack`, `ReportEvidenceFact`, `ReportEvidenceTable`, `ReportEvidenceChart`, `ReportDocument`, `ReportDocumentSection`, and `ReportValidationResult`.
- Replaced the report runner main path with `plan -> evidence -> compose -> validate -> render -> save`. H1 evidence/composition is a minimal skeleton based on workspace profile and semantic-layer context; H2/H3 will add real report planning, SQL/metric/chart evidence collection, model-backed composition, and stronger validation.
- Removed fixed English `REPORT_TYPE_PRESETS`, old report-section question generation, per-section retry/analysis stitching, and stitched narrative helpers from `workspaces/report_runner.py`.
- Replaced Markdown and frontend report detail rendering so the main body comes from `ReportDocument`; technical plan/evidence/validation details stay in the collapsed appendix.
- Deleted the old frontend `ReportSection` business-answer renderer, old report supervisor/agent/writer/planner files, their legacy tests, and the old provider prompt/schema/runtime flags for report writer/planner.
- Cleaned user-visible report copy so the main body uses business-language evidence boundaries rather than H1/H2/H3, pipeline, contract names, or development-stage notes.
- Verification passed: `python3 -m pytest tests/test_workspace_report_runner.py -q` (`6 passed`), `python3 -m pytest tests/test_workspace_report_runner.py tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py -q` (`51 passed`), `python3 -m pytest tests/test_workspace_report_api.py -q` (`12 passed`), cleanup boundary regression (`21 passed`), and focused frontend Vitest (`63 passed`).

## Latest P21-H1 Result

P21-H1 conservative route policy completed on 2026-07-02:

- Added `question_understanding.route_policy.classify_analysis_route()` with the stable `analysis_route` fields: `route`, `reason`, `confidence`, `requires_full_chain`, `fast_path_eligible`, and `disqualifiers`.
- `run_question_understanding_agent()` now writes `analysis_route` into workflow state and question-understanding output.
- Workspace analysis results now persist and restore `analysis_route` at the run top level and in `product_result`.
- `fast_fact` is conservative and metadata-only in H1. It covers complete low-risk factual single-metric totals, ranking, and simple trend questions, but H1 still runs the full P20 SQL/evidence/answer/chart chain.
- Why/cause, diagnosis, recommendation, budget, prioritization, review, report, and multi-metric tradeoff questions are disqualified from `fast_fact` and require the full chain.
- Overall single-metric total questions and trend questions can omit a dimension slot, so “最近90天总销售额是多少？” and “本月订单量趋势怎么样？” can route as low-risk factual requests.
- Verification passed: `python3 -m pytest tests/test_analysis_route_policy.py tests/test_workspace_analysis_runner.py::test_workspace_analysis_fact_payload_keeps_non_channel_comparison_rows tests/test_product_result_builder.py::test_product_result_builder_exposes_fact_payload_only_outside_main_answer -q` (`12 passed`), `python3 -m pytest tests/test_question_understanding_router.py tests/test_provider_backed_question_understanding.py tests/test_analysis_route_policy.py -q` (`50 passed`), `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q` (`31 passed`), cleanup boundary regression (`21 passed`), P20 realistic acceptance (`3 passed`), and full backend regression `python3 -m pytest` (`444 passed, 13 skipped`).
- H1 legacy audit found old cleanup terms only in historical/superseded notes, cleanup/boundary tests, and negative mock-tool tests; no active old product path was restored.

## Latest P21-H2 Result

P21-H2 fast fact path completed on 2026-07-02:

- Added `workspaces.fast_fact_composer` for concise Chinese P16 `business_answer` output for low-risk factual totals, rankings, and simple trends.
- The workflow now routes successful `fast_fact` executions through `fast_fact_composer` after SQL review, SQL execution, and evidence validation, then skips `insight_agent`, Answer Reviewer, Final Answer Composer, and claim typing.
- Fast fact answers keep `recommendations: []`, avoid raw SQL/raw rows/parameter dumps in the main answer, and preserve SQL, raw rows, and `fact_payload` in technical details.
- Ranking answers include the leader, metric value, and comparison scope; trend answers summarize directional movement without generating advice.
- Non-fast questions such as why/复盘, budget advice, reports, and multi-metric综合判断 still use the full P20 chain.
- History detail persists the fast fact `business_answer`, `analysis_route`, evidence, and technical details.
- Verification passed: `python3 -m pytest tests/test_fast_fact_path.py tests/test_workspace_analysis_runner.py::test_workspace_analysis_fact_payload_keeps_non_channel_comparison_rows -q` (`6 passed`), `python3 -m pytest tests/test_analysis_route_policy.py -q` (`10 passed`), `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q` (`31 passed`), `python3 -m pytest tests/test_p20_realistic_acceptance.py -q` (`3 passed`), cleanup/project boundary regression (`21 passed`), and full backend regression `python3 -m pytest` (`449 passed, 13 skipped`).

## Latest P21-H3 Result

P21-H3 business-friendly progress steps completed on 2026-07-02:

- Added centralized `workspaces.progress_steps.build_progress_steps()` and wired `progress_steps` into every analysis `product_result`.
- Route-aware progress now covers `fast_fact`, `standard_analysis`, `deep_judgment`, `report`, `clarify`, and `failed` states using the stable step fields `key`, `label`, `status`, and `summary`.
- `fast_fact` shows the chart step as `skipped` with “事实快答不生成图表”; standard/deep routes keep chart progress; clarify and failed runs stop at the correct waiting/failure point with later steps pending or skipped.
- Workspace run persistence now saves `progress_steps`, and history detail restores them. Older valid P16 history results keep their saved business answer while backfilling progress steps instead of rebuilding the whole product result.
- Added `AnalysisProgressTimeline` to the Analysis Workbench between the analysis thread and business conclusion. The compact Chinese timeline does not render raw SQL, trace IDs, prompt/provider metadata, or raw rows in the main UI.
- Verification passed: `python3 -m pytest tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py tests/test_fast_fact_path.py -q` (`39 passed`), frontend focused Vitest for API/workspace flow (`58 passed`), focused history regression (`51 passed`), and full backend regression `python3 -m pytest` (`452 passed, 13 skipped`).

## Latest P21-H4 Result

P21-H4 exact historical reuse completed on 2026-07-02:

- Workspaces now carry a simple integer `data_version` starting at `1`; CSV, Excel, and SQLite imports increment it when data changes.
- Analysis runs persist `data_version` and a lightweight `normalized_question`; restored history detail keeps those fields, and technical details include them without promoting them into the main business conclusion UI.
- `WorkspaceRunStore` can find reusable completed runs only by exact `workspace_id + data_version + normalized_question`. Failed, waiting, running, and old-data-version runs are ignored.
- Normalization only trims, collapses repeated whitespace, applies Unicode width normalization, and maps common Chinese/English punctuation. It does not call an LLM, rewrite business meaning, perform similar-question matching, or add a keyword-heavy rule tree.
- New analysis requests return `status: "cache_candidate"` with `matched_run_id` before workflow execution when an exact same-version completed run exists. Cache-check errors fall back to normal analysis, and explicit `force_reanalysis: true` bypasses reuse.
- Analysis Workbench renders a compact Chinese reuse prompt with “查看历史结果” and “重新分析”. Viewing loads the matched run detail; rerunning submits a real new analysis with `force_reanalysis`.
- Focused verification passed: `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_run_history_api.py tests/test_workspace_importers.py tests/test_workspace_store.py -q` (`37 passed`) and `cd frontend && npm test -- --run tests/api-client.test.ts tests/workspace-flow.test.tsx` (`60 passed`).

## Latest P21-H5 Result

P21-H5 background work and page recovery completed on 2026-07-02:

- Added a lightweight local run shell/job layer: new analysis requests can persist a `running` run with `run_id`, `workspace_id`, `original_question`, `data_version`, `normalized_question`, and `progress_steps` before the existing analysis workflow finishes.
- FastAPI `POST /api/workspaces/{workspace_id}/runs` now keeps H4 `cache_candidate` behavior first; non-cached new questions return a recoverable `running` run id while a local background executor updates the same run file to `completed`, `failed`, or `waiting_for_clarification`.
- `GET /api/workspaces/{workspace_id}/runs/{run_id}` and history listing can restore running, waiting, completed, and failed runs from persisted workspace files without Redis, Celery, WebSocket, SSE, provider timeout handling, vector cache, or external SaaS.
- Analysis Workbench now stores the active run id in `sessionStorage`, restores it after remount/refresh, polls run detail until terminal status, and clears the active marker after completion/failure/waiting.
- Running/queued runs render a compact task card only: question, Chinese status, and current progress. Long questions are clamped, and SQL, evidence tables, full answers, charts, trace data, and provider metadata are not shown in the task card.
- Completed/waiting/failed runs still open into the full P16 `RunResult`; cache reuse still shows “查看历史结果 / 重新分析” and explicit rerun uses `force_reanalysis`.
- Verification passed: focused backend H5 set `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_run_history_api.py -q` (`35 passed`), full backend regression `python3 -m pytest` (`462 passed, 13 skipped`), focused frontend set `cd frontend && npm test -- --run tests/api-client.test.ts tests/workspace-flow.test.tsx` (`64 passed`), and frontend production build `cd frontend && npm run build`.

## Latest P21-H6 Result

P21-H6 lightweight context packs completed on 2026-07-02:

- Added `workspaces.context_pack_builder.build_fast_fact_context_pack()` as the compact, fixed-shape evidence contract used only by `fast_fact`.
- Fast fact context packs retain the user question, route, task type, metric/dimension ids and Chinese labels, time range, comparison scope, top evidence rows, formulas, units, display values, warnings, data limits, caveats, and evidence validation status.
- The compact pack excludes raw SQL, trace, provider metadata, full workspace profile, full semantic layer, full raw rows, historical runs, prompts, and unrelated report sections. Raw SQL and raw rows remain only in existing technical details/fact payload areas.
- `fast_fact_node` now builds and persists `fast_fact_context_pack`; `fast_fact_composer` prefers it for answer generation and falls back to minimal execution/evidence inputs if the pack is unavailable.
- `technical_details.fast_fact_context_pack` is available for fast fact debugging and tests. `standard_analysis`, `deep_judgment`, and `report` are not forced into this compact context pack and keep the richer evidence path.
- Focused verification passed: `python3 -m pytest tests/test_fast_fact_path.py tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py -q` (`53 passed`).

## P19 Task Status

| Task | Status | Notes |
|---|---|---|
| P19-H1 | `[x]` Complete | Plain why/evidence entity conflicts are now corrected or downgraded by the small deterministic guard |
| P19-H2 | `[x]` Complete | Added Answer Reviewer Agent and Final Answer Composer contracts, deterministic/provider tests, and product/report integration |
| P19-H3 | `[x]` Complete | Polished business answer quality: vocabulary, units, grounded recommendations, tradeoffs, caveats, and report-section reuse |
| P19-H4 | `[x]` Complete | Reports synthesize reviewed answers into management narrative, with language-aware Markdown/frontend labels and business-labeled evidence summaries |
| P19-H5 | `[x]` Complete | Quality closeout: focused/full regression, frontend build, live DeepSeek acceptance, cleanup audit, and artifact hygiene |

## P18 Task Status

| Task | Status | Notes |
|---|---|---|
| P18-H1 | `[x]` Complete | Added RED tests for multi-metric conflict, insufficient comparison evidence, chart annotation conflict, and report inheritance; focused tests intentionally fail until H2-H4 |
| P18-H2 | `[x]` Complete | Added `workspaces/answer_consistency.py` and applied it in `build_business_answer()`; multi-metric tradeoff and single-row budget-reduction RED tests now pass |
| P18-H3 | `[x]` Complete | Align chart annotations with the final business answer |
| P18-H4 | `[x]` Complete | Report sections reuse consistency-checked answers; executive summaries stay concise and do not repeat long section direct answers |
| P18-H5 | `[x]` Complete | Tightened insight drafter prompt and lightweight structured validation for language, raw/internal text, and unsupported single-row budget actions |
| P18-H6 | `[x]` Complete | Focused/full regression, frontend checks, live acceptance gating, artifact hygiene, and docs closeout |

## P17 Task Status

| Task | Status | Notes |
|---|---|---|
| P17-H1 | `[x]` Complete | Added dependency boundary tests proving current product entry points do not require removed historical paths |
| P17-H2 | `[x]` Complete | Removed legacy action-path code and provider/prompt hooks outside the current product |
| P17-H3 | `[x]` Complete | Current visualization delivery runtime is local chart rendering and local workbook export only |
| P17-H4 | `[x]` Complete | Old eval/demo files are deleted or untracked; old design snapshots began being marked historical |
| P17-H5 | `[x]` Complete | Simplified README, DEVELOPMENT_PLAN, DEVELOPMENT_STATUS, and retained P11/P12/P13 specs so current product guidance is obvious |
| P17-H6 | `[x]` Complete | Final artifact hygiene, legacy audit, focused/full regressions, frontend build, and real DeepSeek acceptance |

## Current Product Chain

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

## Latest Verified Baseline

Latest P20-H5 closeout result on 2026-07-02:

- Added realistic acceptance coverage in `tests/test_p20_realistic_acceptance.py` for two non-channel business scenarios: store sales/satisfaction and support ticket operations.
- Store sales acceptance covers factual answer, ranking, multi-metric comparison, trend, recommendation, chart artifacts, fact payload, and management-report synthesis. Fact-only questions do not force recommendations; comparison/recommendation questions can select scatter charts from two numeric metrics; trend questions select line charts.
- Support ticket acceptance covers team-level工单量、平均响应时长、满意度 analysis without requiring channel, orders, marketing spend, or revenue fields.
- Business-review report section prompts now ask agents to use the current workspace schema, profile, and semantic layer. They no longer assume demo tables or fields for the general `business_review` report type.
- Common service-operation fields now map to Chinese business labels: `team_name` -> 团队, `ticket_count` -> 工单数, and `avg_response_minutes` -> 平均响应时长.
- Schema-review failure guidance is now generic to the current workspace: users are pointed to current tables, fields, metrics, and dimensions instead of a demo-specific field set.
- Added `tests/test_p20_live_deepseek_acceptance.py`. It is opt-in and defaults to skip unless `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1`, `INSIGHTFLOW_PRODUCT_LIVE_MODE=1`, provider flags, and `DEEPSEEK_API_KEY` are configured. Forced local live verification with those flags passed against real DeepSeek: `1 passed`.
- Cleanup audit for old action/chart/mock/eval/Streamlit terms found matches only in historical/superseded notes, cleanup/boundary tests, negative mock-tool tests, and the audit command in the P20 plan; no active product import or main path was restored.
- Verification passed: question-understanding/P17/P20/project/P20 acceptance boundary set `45 passed, 1 skipped`; metric/evidence/workspace-analysis/product-result focused set `49 passed`; report/composer/visualization focused set `36 passed`; full backend regression `python3 -m pytest` (`434 passed, 13 skipped`); frontend Vitest `npm test` (`62 passed`); frontend production build passed.

P20 completion definition is now satisfied: InsightFlow is a Chinese-first general business data-analysis multi-agent product foundation that profiles uploaded datasets, builds semantic layers, maps raw Chinese/English/mixed fields into Chinese business semantics, routes natural-language questions into analysis tasks, calls SQL/calculation/chart/report tools, validates factual claims, and writes Chinese business-readable answers and reports. P21 responsiveness and fast-path work is complete; P22 evidence-driven report generation is complete; P23 is core evidence/report tooling readiness. This older note originally expected external tool calling/export next, but current P24 planning supersedes it with general business data understanding and evidence generation first.

Latest P20-H4 answer/report generation result on 2026-07-02:

- Final answer composition no longer accepts stale `downgrade_to_insufficient_evidence` results when validated multi-row evidence contains supported entities and metrics; it rebuilds a useful Chinese business answer from the evidence rows.
- Fact-only questions keep business caveats but do not force unrelated recommendations or action plans.
- Recommendation questions with multiple metrics can explain tradeoffs such as revenue scale versus ROI/efficiency, preserving supported entities and avoiding false "证据不足" downgrades.
- Shared Chinese field labels now cover general store-operation fields such as `store_name`, `sales_amount`, and `satisfaction_score`.
- Visualization fallback chooses chart type from task intent: ranking uses ranked bar, trend uses line, and multi-metric comparison/recommendation uses scatter when enough numeric metrics exist. Fallback chart titles and annotations are Chinese business copy.
- Report synthesis is Chinese-first even for English report goals and continues to reuse section `business_answer`, chart artifacts, evidence rows, and technical appendix separation.
- Legacy audit found historical/action/chart/mock/eval terms only in historical notes, cleanup/boundary tests, and negative mock-tool tests. Active "证据不足" wording remains only as a necessary guardrail for genuinely missing rows, unsupported entities/metrics, or failed final-answer validation.
- Verification passed: `python3 -m pytest tests/test_business_answer_quality.py tests/test_answer_reviewer.py tests/test_final_answer_composer.py -q` (`35 passed`), `python3 -m pytest tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py tests/test_report_insight_cleanup.py tests/test_visualization_intelligence.py -q` (`60 passed`), `python3 -m pytest tests/test_metric_tool.py tests/test_evidence_tool.py tests/test_question_understanding_router.py tests/test_provider_backed_question_understanding.py -q` (`54 passed`), P17/P20/project boundary checks (`21 passed`), and full backend regression `python3 -m pytest` (`430 passed, 12 skipped`).

Latest P20-H3 fact-layer result on 2026-07-02:

- Added a JSON-safe metric registry from workspace semantic metrics. It keeps base metric formulas and derives ROAS, net return, margin rate, and average order value only when the required revenue/spend/cost/order-count sources exist.
- ROAS remains `revenue / spend`; net return remains `(revenue - spend) / spend`; margin rate remains `(revenue - cost) / revenue`. Missing source fields emit warnings instead of inventing derived metrics.
- Added reusable evidence `fact_payload` for product results and technical details. It includes task type, metrics, dimensions, time scope, filters, comparison scope, columns, rows, formulas, warnings, display/formatted values, and technical SQL.
- Comparison/ranking/recommendation payloads require at least two peer rows. If only a winner row is returned, the payload marks comparison scope as insufficient and adds a Chinese warning.
- Chinese business display values now keep raw values alongside readable labels and formats, including `26255.44` -> `2.6 万`, percentages such as `0.367` -> `36.7%`, and raw columns such as `store_name` or `team_name` mapped to Chinese business fields.
- Main `business_answer` fields still do not expose raw SQL or raw rows; raw rows and `technical_sql` live in `technical_details` / `fact_payload`.
- No old demo/mock/action/chart/eval path was restored or deleted as part of H3. Legacy audit found old terms only in historical notes, cleanup/boundary tests, or tests that assert removed mock/tool choices are rejected.
- Verification passed: `python3 -m pytest tests/test_metric_tool.py tests/test_evidence_tool.py tests/test_evidence_validator.py tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q` (`48 passed`), `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`41 passed`), `python3 -m pytest tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py tests/test_mcp_tool_layer.py -q` (`12 passed`), and full backend regression `python3 -m pytest` (`414 passed, 12 skipped`).

P20-H3 task-contract metric normalization repair on 2026-07-02:

- Question understanding now keeps ROAS, ROI, and net return separate before SQL planning and fact payload generation.
- Deterministic router normalization maps `roas` to `ROAS`, `roi` to `ROI`, and `net return` / `net ROI` / `净投放回报率` / `净回报率` to `净投放回报率`.
- Provider-backed question understanding applies the same aliases, so provider output such as `roas`, `net_return`, `net ROI`, or `净投放回报率` cannot collapse into ROI or trigger a missing-metric clarification.
- P20-H3 metric-normalization repair also prevents `net ROI` / `netroi` from being double-counted as both net return and ROI.
- P20-H3 metric-normalization repair now preserves explicit multi-metric questions that ask for net return and plain ROI together.
- Existing Chinese metrics such as 销售额、花费、订单量、客单价、复购率、满意度、销量 remain unchanged.
- This was a P20-H3 semantic/task-contract repair only; no P20-H4 answer/report generation logic was changed and no old demo/mock/action/chart/eval path was restored.
- Verification passed: `python3 -m pytest tests/test_question_understanding_router.py tests/test_provider_backed_question_understanding.py -q` (`32 passed`), `python3 -m pytest tests/test_metric_tool.py tests/test_evidence_tool.py tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q` (`45 passed`), `python3 -m pytest tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py -q` (`8 passed`), and full backend regression `python3 -m pytest` (`419 passed, 12 skipped`).

Latest P20-H2 task-contract result on 2026-07-02:

- Question understanding now emits a normalized `analysis_task` contract with `task_type`, Chinese `dimensions` and `metrics`, `time_range`, `filters`, `decision_goal`, `missing_slots`, `defaults_applied`, `resolved_question`, fixed `output_language: "zh"`, and confidence.
- Complete Chinese analysis questions such as “最近90天按门店比较销售额” proceed without clarification, while incomplete recommendation questions such as “帮我分析渠道表现，看看哪个渠道该加预算” ask concise Chinese follow-ups for missing metric and time range instead of being rejected or sent to SQL.
- English or mixed raw headers in semantic context, such as `Sales Amount` and `Store Name`, normalize to Chinese business slots such as 销售额 and 门店; English user questions still produce `output_language: "zh"`.
- Clarification continuation now merges the original question with the user's short supplement. A partial answer such as “花费” fills only the metric and keeps the pending run waiting for `time_range`; a completed supplement can continue through the normal analysis path.
- Provider-backed question understanding can return optional `analysis_task`, but local normalization applies defaults, forces Chinese output language, maps workspace semantic aliases, and recomputes missing slots so provider output cannot bypass clarification rules.
- Verification passed: `python3 -m pytest tests/test_question_understanding_router.py tests/test_clarification_routing.py tests/test_pending_clarification_store.py -q` (`20 passed`), `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workflow.py -q` (`16 passed`), `python3 -m pytest tests/test_provider_backed_question_understanding.py tests/test_provider_backed_clarification_router.py tests/test_deepseek_provider_structured_output.py -q` (`44 passed`), `python3 -m pytest tests/test_p20_general_semantic_layer.py tests/test_metric_tool.py -q` (`8 passed`), and full backend regression `python3 -m pytest` (`412 passed, 13 skipped`).

Latest P20-H1 generalized semantic-layer result on 2026-07-01:

- CSV/Excel import identifier sanitization now preserves Unicode business headers, so Chinese field names remain available for profiling instead of collapsing to duplicate placeholder names.
- Workspace profiling now emits generalized `original_type`, `inferred_type`, `field_role`, `business_meaning_candidates`, `suitable_group_by`, and `suitable_aggregations` fields while preserving legacy `role_candidates`.
- Semantic-layer drafts are generated from actual workspace fields into `tables`, `metrics`, `dimensions`, `time_fields`, `entities`, `field_roles`, `semantic_aliases`, `relationships`, and `available_analysis_capabilities`; missing `channel` or `revenue` fields are not invented.
- Added `load_workspace_semantic_layer()` as the shared YAML/JSON workspace semantic-layer reader and wired it into settings summary, workspace context summary, metric lookup, and schema repair.
- Schema repair now reads workspace YAML semantic layers without the previous JSON-only “semantic layer could not be read” failure.
- Data Settings recognizes the generalized `metric`, `id`, `status`, and `text` field-role labels.
- Verification passed: `python3 -m pytest tests/test_workspace_profiler.py tests/test_workspace_semantic_draft.py tests/test_semantic_layer.py -q` (`15 passed`), `python3 -m pytest tests/test_schema_tool.py tests/test_metric_tool.py tests/test_workspace_settings_api.py tests/test_p20_general_semantic_layer.py -q` (`17 passed`), `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q` (`27 passed`), combined P20-H1 backend set (`36 passed`), frontend workspace-flow Vitest (`49 passed`), frontend production build passed, and full backend regression passed (`401 passed, 13 skipped`).

P20 language-scope update on 2026-07-02:

- P20 now targets a Chinese-first business product: product-facing UI copy, clarifying questions, answers, chart annotations, reports, Markdown exports, and provider prompts should be Chinese.
- English and mixed raw headers remain supported as imported data reality, but they should be mapped into Chinese business labels and aliases instead of creating bilingual product output branches.
- Historical P19 English-output behavior is no longer a P20 acceptance requirement. Multilingual output is deferred until after the Chinese business analysis chain is stable.
- P20-H1 needs a focused repair before H2 because current semantic metric formulas may not safely quote headers with spaces or punctuation, and English raw fields such as `Sales Amount` need Chinese semantic aliases such as 销售额.

P20-H1 repair completion note on 2026-07-02:

- Semantic metric formulas now quote SQLite identifiers safely, including table and column names with spaces, punctuation, parentheses, Chinese characters, and embedded double quotes.
- Semantic drafts now derive Chinese business aliases and labels from `business_meaning_candidates` and common raw header words, so English/mixed fields such as `Sales Amount`, `Cost Amount`, `Score (NPS)`, and `Store Name` map to 销售额、成本、满意度、门店.
- Workspace metric lookup can answer Chinese semantic questions such as “按门店看销售额”, “按门店看成本”, and “按门店看满意度” against English/mixed raw headers without inventing channel, orders, or ROI fields.
- Verification passed: `python3 -m pytest tests/test_workspace_semantic_draft.py tests/test_metric_tool.py tests/test_p20_general_semantic_layer.py -q` (`14 passed`), `python3 -m pytest tests/test_workspace_profiler.py tests/test_semantic_layer.py tests/test_workspace_settings_api.py -q` (`16 passed`), `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q` (`27 passed`), P17/P20 boundary checks (`18 passed`), and full backend regression `python3 -m pytest` (`403 passed, 13 skipped`).

Latest P20-H0 cleanup result on 2026-07-01:

- Current main path inventory remains: import/profile/semantic layer -> question understanding/clarification -> SQL planning/review/schema repair/execution -> evidence validation -> reviewer/composer/business answer -> visualization/report -> Next.js UI.
- Added `tests/test_p20_architecture_cleanup_boundaries.py` to protect active agent/tool boundaries and prevent old action/chart/mock/eval/template-mining paths from returning to the main product chain.
- Removed the old trace-driven SQL template-mining helper path: `sql_planning.feedback`, `tests/test_llm_template_mining_eval_suite.py`, and `template_mining_event` trace payloads from `agents/guarded_llm_enhancer.py`.
- Preserved provider structured-output smoke coverage in `tests/test_llm_smoke_eval.py`.
- Focused cleanup baseline initially failed because P17 boundary tests still asserted P19/responsiveness-era status text; those assertions now point at P20 General Business Analysis Foundation.
- Verification passed: cleanup/P20 focused boundaries `22 passed`; project initialization/MCP boundaries `9 passed`; workspace analysis/report/product-result/business-answer focused regression `60 passed`; full backend regression `391 passed, 13 skipped`; frontend workspace-flow Vitest `49 passed`; full frontend Vitest `62 passed`; frontend production build passed.
- Legacy audit after cleanup found remaining old action/chart/mock/eval/template terms only in Historical / Superseded documentation or negative boundary/provider tests; no active main product import depends on them.

Latest P18-H6 closeout result on 2026-07-01:

- P18 focused regression passed for answer consistency, report runner, product result builder, business answer quality, and DeepSeek structured output.
- Full backend regression passed after updating stale P17 boundary assertions to the current P18 closeout status: `350 passed, 13 skipped`.
- Frontend Vitest and production build passed.
- Real DeepSeek acceptance was not run because the current environment has a DeepSeek key but does not have the live opt-in flags configured.
- Legacy audit found old chart/action/mock/eval/Streamlit terms only in historical/superseded notes and boundary tests, not active product guidance.
- Generated artifacts, frontend build output, pytest cache, runtime workspace outputs, traces, and sample data remain ignored and must not be committed.

P19 planning note on 2026-07-01:

- Real local DeepSeek product mode was enabled for manual product testing with `INSIGHTFLOW_PRODUCT_LIVE_MODE=1` in the untracked `.env`.
- A real channel budget question produced provider-backed analysis (`provider_called: true` across question understanding, SQL planning/candidate, insight drafting, and claim typing), proving the live path works.
- The output quality review found remaining product gaps: recommendations can cite a different entity than their evidence, raw metric names can leak into business copy, recommendations can be empty or repetitive, and reports read like stitched section output rather than synthesized management reports.
- P19 is therefore focused on business-output/report quality before external publishing integrations.
- Direction update: P19 should not become an expanding deterministic patch list for every possible model mistake. The next design direction is an Answer Reviewer Agent plus Final Answer Composer, with small deterministic checks as the last safety guardrail.
- Planning update: P19 is intentionally compacted into five H tasks so development is easier to steer, but each H task still requires tests, code cleanup, artifact hygiene, and focused/full verification.
- Cleanup policy update: P19 should delete old paths, obsolete tests, fallback/template/demo compatibility code, and unused modules when they conflict with the current FastAPI/Next.js workspace product direction. Historical behavior does not need to be preserved.
- Future notes at the time of P19 planning originally pointed P20 toward responsiveness, but real product testing later re-scoped P20 into the general business analysis foundation. Responsiveness became P21. Later live report testing re-scoped P23 into core evidence/report readiness. Current planning has re-scoped P24 again: P24 is now general business data understanding and evidence generation before external tool calling/export.

P19-H2 completion note on 2026-07-01:

- Added structured `answer_reviewer` and `final_answer_composer` contracts with validation tests.
- Integrated reviewer/composer after insight drafting and before final P16 business answer normalization.
- Report sections reuse the reviewed/composed `business_answer`; deterministic `answer_consistency.py` remains the final small guardrail.
- Focused backend tests, full backend regression, frontend Vitest, and frontend production build passed.

Historical P19-H3 completion note on 2026-07-01:

- Added shared language-aware business labels for common metrics and dimensions. This included bilingual behavior for P19 acceptance, but P20 supersedes it with Chinese-first product output and English/mixed raw-header recognition only.
- Final Answer Composer now produces business-readable revise/downgrade answers, removes reviewer/internal wording from caveats, and states revenue-vs-ROI tradeoffs instead of forcing one winner.
- Product result and report section normalization apply the same field-label cleanup while keeping raw columns, rows, SQL, traces, and provider metadata in technical details.
- Added focused regression coverage for Chinese output, field-label polish, multi-metric tradeoffs, no invented ROI/profit advice, internal metadata leakage, and report section business answers.
- Follow-up fix at that time: English questions kept English fallback wording and English business labels instead of mixing Chinese labels into accepted/composed answers. This remains historical context, not a P20 product requirement.

Historical P19-H4 completion note on 2026-07-01:

- Report records now expose management-facing `executive_summary`, `key_findings`, `action_priorities`, `chart_and_evidence`, and `risks_and_limits` synthesized from reviewed/composed section `business_answer` values.
- Markdown reports used Chinese-first management structure for Chinese goals and English headings/content for English goals in P19. P20 supersedes this with Chinese-first product output while keeping SQL, trace paths, provider metadata, raw rows, and internal prompts in technical appendices.
- Chart artifacts carry title, unit, safe business annotation, and path/URL into report JSON, Markdown image embeds, and the frontend report detail view.
- Missing charts render a business-friendly “暂无可展示图表” explanation instead of visualization errors or trace metadata in the main report body.
- Focused P19-H4 backend regression passed: `python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_store.py tests/test_workspace_report_api.py tests/test_report_insight_cleanup.py tests/test_chart_product_quality.py tests/test_product_result_builder.py -q` with `57 passed`.
- Focused frontend report regression passed: `cd frontend && npm test -- workspace-flow.test.tsx` with `49 passed`.

Historical P19-H4 repair note on 2026-07-01:

- English report goals rendered English business labels in Markdown and the frontend report reader for P19 acceptance. This is superseded in P20; current product output should stay Chinese.
- Report-level chart/evidence summaries reuse the shared business field label helper so fields such as `total_revenue`, `order_count`, `avg_order_value`, and `segment` are shown as business-readable labels instead of raw column names.
- Focused repair regressions covered P19 bilingual Markdown/report detail rendering. P20 should replace or delete those assertions when they conflict with Chinese-first product behavior.

P19-H5 completion note on 2026-07-01:

- Focused backend regression passed for workspace analysis, workspace reports, product result builder, reviewer/composer, business-answer quality, chart/report cleanup, and P17 cleanup boundaries: `100 passed`.
- Full backend pytest passed: `388 passed, 13 skipped`.
- Frontend Vitest passed: `60 passed`.
- Frontend production build passed.
- Real DeepSeek acceptance completed against temporary generated workspace data outside the repo for three Chinese business questions: a single-metric top-revenue question, a revenue-vs-ROI tradeoff question, and a management channel-review report.
- Live acceptance showed real provider participation, SQL review approval, Chinese business answers with evidence, recommendations and limits, chart artifacts with displayable report/API paths, and report-level management summary, key findings, action priorities, chart/evidence, and risks/limits.
- H5 fixed a live acceptance quality gap where a clean provider factual answer could omit recommendations and caveats; the product result builder now fills only minimal evidence-based next-step guidance and query-scope caveats for sufficiently supported answers.
- Artifact hygiene was rechecked: generated databases, reports, report Markdown, chart artifacts, traces, `.env`, frontend build output, `.superpowers`, and real DeepSeek temporary artifacts remain untracked/ignored and were not staged.
- Cleanup audit found old action/chart/mock/template terms only in historical notes, deleted-file assertions, ignored generated artifacts, or necessary test doubles; no current product entry point was restored or duplicated.
- This older closeout note has been superseded by later planning: P20 became the general business analysis foundation, P21 handled responsiveness, P22 rebuilt evidence-driven reports, P23 handled core evidence/report readiness, and current P24 now strengthens general business data understanding before real business tool calling.

P19 closeout fix note on 2026-07-01:

- ProductShell model status now reads `/api/workspaces/{workspace_id}/settings` `model_mode` instead of hardcoding live mode.
- Key-only DeepSeek configuration displays `仅已配置密钥`; only `product_live_mode=true` displays `真实模型已开启`.
- Workspace settings model-mode summary reads the merged local `.env` and process environment, so provider key presence and product live mode remain separate states.
- Frontend coverage now includes loading, key-only, live-mode-on, and fetch-failure model status states without relying on a real backend.
- Local ignored generated artifacts were cleaned from `.superpowers`, chart PNG outputs, run workspaces, pytest/cache directories, `__pycache__`, and frontend build output; retained `.env`, tracked placeholders, and the historical `data/ecommerce.db` fixture were not removed or staged.
- P20 has been re-scoped after real product testing: it is now the general business analysis foundation phase, not responsiveness work. Responsiveness moved to P21; later report testing moved real business tool calling after P23 core evidence/report readiness. Current P24 planning supersedes that handoff and focuses first on general business data understanding and evidence generation.

P20 planning note on 2026-07-01:

- Real P19 workspace testing showed that the system can query useful evidence but still over-downgrade answers to "证据不足" because safety, evidence, consistency, and expression responsibilities are too tightly coupled.
- P20 should split the chain into factual tool output, model judgment, fact validation, and business expression/report writing.
- P20 must support general business datasets by reasoning over dimensions, metrics, time fields, filters, decision goals, evidence rows, chart intents, and report sections instead of hardcoding `orders`, `channel`, `marketing_spend`, `revenue`, or ROI-only channel analysis.
- P20 cleanup policy: delete old paths, obsolete tests, fallback/template/demo compatibility code, and unused modules when they conflict with the current FastAPI/Next.js workspace product direction. Historical behavior does not need to be preserved.
- P20 implementation guidance lives in `docs/product/plans/2026-07-01-p20-general-business-analysis-foundation.md`.

Latest P17-H6 closeout result on 2026-06-30:

- README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS were simplified into current product/status surfaces.
- P11/P12/P13 superpowers specs are marked Historical / Superseded and point current guidance to `docs/product/plans/`, P16 `business_answer`, and P17 cleanup.
- Old eval/demo/action/mock/chart wording is retained only in Historical / Superseded notes, cleanup plans, or test-boundary assertions.
- Final artifact hygiene keeps generated reports, charts, traces, workspace instances, frontend build output, pytest cache, and `__pycache__` out of the working artifact set, with only required `.gitkeep` placeholders retained.
- Legacy audit found superseded cleanup terms only in historical/superseded notes or deletion-boundary tests, not active product entry points.
- Focused cleanup boundary tests are now covered by `tests/test_p17_product_cleanup_boundaries.py`, `tests/test_p20_architecture_cleanup_boundaries.py`, and `tests/test_project_initialization.py`; the old duplicated P11 cleanup-boundary file was removed during P20 cleanup.
- Full backend regression passed: `python3 -m pytest`.
- Frontend tests passed: `cd frontend && npm test`.
- Frontend production build passed: `cd frontend && npm run build`.
- Real DeepSeek live acceptance passed for P15 analysis reliability, P12 workspace reports, and P13 product acceptance with product live/provider flags.

## Historical / Superseded Notes

This section is historical cleanup context only, not current product guidance.

- Historical / Superseded: `streamlit run app.py`, `eval/run_eval.py`, `tests/test_eval_runner.py`, `tests/test_streamlit_app.py`, `chart_agent`, `visualization_planner`, `chart_tool`, `action_delivery`, `action_drafter`, `powerbi_publisher_mock`, `jira_ticket_mock`, mock SaaS, fixed template behavior, deterministic action template behavior, and keyword inference are old cleanup terms.
- Historical low-level fixture: `data/ecommerce.db` used to be tracked for schema, SQL validation, SQL execution, workflow, report, MCP, and provider regressions. It is now generated locally by tests when missing and must not be committed.
- Historical P11/P12/P13 specs under `docs/superpowers/specs/` must be treated as snapshots. Current guidance is `docs/product/plans/`, the P16 `business_answer` contract, and P17 cleanup.
- Real China-oriented external tool calling remains deferred until the core answer/report chain and generic data understanding are stable. Current guidance is P24 for general business data understanding and evidence generation; external tools and exports move after P24.
