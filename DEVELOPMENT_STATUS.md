# InsightFlow Agent Development Status

Last updated: 2026-07-03

This is the concise current status surface for InsightFlow Agent.

## Current Snapshot

| Field | Status |
|---|---|
| Current phase | P23 Core Evidence And Report Tooling Readiness in progress |
| Current task | P23-H6 Cleanup, Regression, And Live Acceptance next |
| Next planned task | P23-H6 Cleanup, Regression, And Live Acceptance |
| Last completed task | P23-H5 Artifact And Tool-Calling Readiness |
| Active backend | FastAPI in `api/app.py` |
| Active frontend | Next.js + React + TypeScript in `frontend/` |
| Active analysis entry | `POST /api/workspaces/{workspace_id}/runs` |
| Active report entry | `POST /api/workspaces/{workspace_id}/reports` |
| Current answer contract | P16 `business_answer`: `headline`, `direct_answer`, `why`, `evidence_bullets`, `recommendations`, `caveats`, `confidence` |
| Main product target | Chinese-first general business data-analysis multi-agent product with data profiling, semantic layer, task routing, SQL/calculation/chart/report tool calls, evidence validation, Chinese business answers, and coherent Chinese report documents |
| Out of scope for P20 | Real external integrations, auth/RBAC, deployment, vector databases, scheduled reports, fixed SQL templates, keyword-heavy business rules, table-specific demo logic, and old demo restoration |

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
| P23 | `[~]` In progress | H1-H5 complete; core evidence/report tooling readiness continues with cleanup and live acceptance before external tool integrations |
| P24 | `[ ]` Future | Real China-oriented business tool calling and exports after P23 stabilizes the core chain |

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

P23 planning is recorded in `docs/product/plans/2026-07-03-p23-core-evidence-and-report-tooling-readiness.md`. P23 keeps Analysis Workbench and Report Center separate at the product layer, but makes them share factual evidence, metric, chart artifact, and validation standards. Report Center may collect chapter-level evidence, but it must write the final report once instead of stitching analysis answers together. Model-written explanations and recommendations should be preserved as business judgment; only hard facts such as amounts, dates, rankings, percentages, chart values, and report title/time range are strictly evidence-bound. P23 may delete old templates, stitched report paths, duplicate evidence contracts, stale bilingual branches, mock/demo tests, unused adapters, dead imports, and unreachable compatibility code that conflict with the Chinese-first product path. Real Word/PPT/PDF/飞书/企业微信/钉钉/腾讯文档 integrations move to P24 after P23 passes live Chinese analysis/report acceptance.

## P23 Task Status

| Task | Status | Notes |
|---|---|---|
| P23-H1 | `[x]` Complete | Shared EvidencePack foundation: analysis `fact_payload` and report `ReportEvidencePack.evidence_payloads` now share the same factual payload vocabulary with traceable derived metrics, formulas, chart-ready data, warnings/data limits, and technical-detail references |
| P23-H2 | `[x]` Complete | Chinese Business Answer Writer: natural Chinese business answers preserve model explanations/recommendations while binding hard facts and missing-data boundaries to shared evidence |
| P23-H3 | `[x]` Complete | One-Pass Report Center With Shared Evidence |
| P23-H4 | `[x]` Complete | Evidence Ledger And Report Self-Repair: replaced prose-number validator patching with tool-built evidence ledger, ledger-backed report writing, factual-claim validation, one automatic repair pass, evidence-aware coverage, and conservative metric-role-based contribution metric selection |
| P23-H5 | `[x]` Complete | Artifact And Tool-Calling Readiness: chart/report artifacts and local renderer tool calls now cite EvidenceLedger facts/metrics without raw rows or model-recomputed facts |
| P23-H6 | `[ ]` Next | Cleanup, Regression, And Live Acceptance for the ledger-backed report chain, artifact references, old-path deletion, and live DeepSeek analysis/report acceptance |

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

P20 completion definition is now satisfied: InsightFlow is a Chinese-first general business data-analysis multi-agent product foundation that profiles uploaded datasets, builds semantic layers, maps raw Chinese/English/mixed fields into Chinese business semantics, routes natural-language questions into analysis tasks, calls SQL/calculation/chart/report tools, validates factual claims, and writes Chinese business-readable answers and reports. P21 responsiveness and fast-path work is complete; P22 evidence-driven report generation is complete; P23 is core evidence/report tooling readiness; China-oriented external tool calling/export moves to P24.

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
- Future notes at the time of P19 planning originally pointed P20 toward responsiveness, but real product testing later re-scoped P20 into the general business analysis foundation. Responsiveness became P21. Later live report testing re-scoped P23 into core evidence/report readiness, so real business tool calling/export is now P24.

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
- This older closeout note has been superseded by later planning: P20 became the general business analysis foundation, P21 handled responsiveness, P22 rebuilt evidence-driven reports, P23 now handles core evidence/report readiness, and real business tool calling moves to P24.

P19 closeout fix note on 2026-07-01:

- ProductShell model status now reads `/api/workspaces/{workspace_id}/settings` `model_mode` instead of hardcoding live mode.
- Key-only DeepSeek configuration displays `仅已配置密钥`; only `product_live_mode=true` displays `真实模型已开启`.
- Workspace settings model-mode summary reads the merged local `.env` and process environment, so provider key presence and product live mode remain separate states.
- Frontend coverage now includes loading, key-only, live-mode-on, and fetch-failure model status states without relying on a real backend.
- Local ignored generated artifacts were cleaned from `.superpowers`, chart PNG outputs, run workspaces, pytest/cache directories, `__pycache__`, and frontend build output; retained `.env`, tracked placeholders, and the historical `data/ecommerce.db` fixture were not removed or staged.
- P20 has been re-scoped after real product testing: it is now the general business analysis foundation phase, not responsiveness work. Responsiveness moved to P21; later report testing moved real business tool calling to P24 after P23 core evidence/report readiness.

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
- Historical retained fixture: `data/ecommerce.db` remains for low-level tests that directly exercise schema, SQL validation, SQL execution, workflow, report, MCP, and provider regressions. It is not the current product database.
- Historical P11/P12/P13 specs under `docs/superpowers/specs/` must be treated as snapshots. Current guidance is `docs/product/plans/`, the P16 `business_answer` contract, and P17 cleanup.
- Real China-oriented external tool calling remains deferred until the core answer/report chain is stable. Current guidance is P23 for evidence/report readiness, then P24 for real external tools and exports.
