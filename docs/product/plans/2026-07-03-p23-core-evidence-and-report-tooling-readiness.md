# P23 Core Evidence And Report Tooling Readiness Implementation Plan

Historical / Superseded note: this phase record describes P23-era answer rewrite/composer work. P33-H2 deleted `agents/final_answer_composer.py`, deleted `workspaces/answer_consistency.py`, and removed the old rewrite tests from active expectations. Keep the references below as historical implementation notes only.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the shared factual evidence layer, Chinese business answer writing, and one-pass report generation path so InsightFlow can move next into stronger general business data understanding before real external chart/document/export tools.

**Architecture:** Analysis Workbench and Report Center remain separate product experiences. They should share factual data profiling, semantic mapping, metric calculation, SQL execution, evidence packing, chart artifact contracts, and fact validation. Tools own facts and artifacts; model-backed agents own explanation, judgment, recommendations, and Chinese business expression inside evidence boundaries.

**Tech Stack:** FastAPI, Python workspace services, LangGraph analysis workflow, SQLite workspace databases, DeepSeek provider path, local chart/report artifacts, Next.js App Router, React, TypeScript, pytest, Vitest, opt-in live DeepSeek acceptance.

---

## Why P23 Exists

P22 replaced stitched report sections with a coherent report document path, but live testing still exposed product-quality gaps:

- Analysis Workbench and Report Center share some low-level tools, but their evidence contracts are not unified enough.
- Report Center can write a full report, but charts may remain intent placeholders instead of real rendered artifacts.
- Model-written reports can introduce derived percentages, dates, rankings, or labels that are reasonable but not traceable enough for validation.
- Some analysis answers still feel template-like instead of natural Chinese business analysis.
- Report Center must not regress into per-section analysis answers stitched together. It should collect section-level evidence, then write the full report once.

P23 is the core evidence/report hardening phase before broader product expansion. Current planning sends the next phase into general business data understanding first, so later chart/document/export integrations do not wrap unstable analysis output in nicer artifacts.

## Product Boundary

Keep these two product modes separate:

```text
Analysis Workbench
-> one business question
-> optional clarification/follow-up
-> one answer with evidence, chart, and technical details

Report Center
-> one report goal
-> report plan
-> multiple evidence packs and chart artifacts
-> one complete Chinese report document
-> download/export-ready artifacts
```

The separation is product-level, not factual-level. Both modes should rely on the same evidence and artifact standards so numbers, rankings, dates, and charts stay consistent.

## Non-Negotiable Cleanup Policy

P23 may delete old paths, compatibility fields, tests, and code that conflict with the current product direction. Do not preserve old behavior only for historical compatibility.

Delete or replace:

- fixed answer templates that make replies sound like system output;
- old stitched report-section generation paths;
- report body rendering that treats section answers as the main report;
- duplicate evidence structures that produce conflicting facts;
- old English-first or bilingual output branches that complicate the Chinese-first product path;
- mock/demo tests that assert template wording instead of real product behavior;
- unused adapters, stale provider flags, dead imports, and unreachable fallback logic.

Keep or strengthen:

- workspace import, profile, and semantic layer;
- question understanding and clarification;
- SQL validation, SQL execution, schema repair, metric calculation, evidence validation, chart/report artifacts, and trace boundaries;
- model-backed explanation, recommendation, and report writing;
- opt-in real DeepSeek acceptance;
- tests that protect current FastAPI/Next.js product behavior and multi-agent/tool-calling boundaries.

## Target Chain After P23

```text
workspace import
-> profile and semantic layer
-> shared metric and evidence tools
-> EvidencePack
-> analysis answer writer OR report evidence collector
-> chart artifact builder
-> fact validator
-> Chinese business expression
-> frontend rendering and download/export-ready artifact records
```

The model may explain why something matters, propose business hypotheses, and recommend next actions. It must not invent hard facts. Hard facts include amounts, dates, rankings, percentages, highest/lowest values, chart values, and report titles/time ranges.

## P23-H1: Shared EvidencePack Contract

Goal: Make Analysis Workbench and Report Center depend on the same factual evidence vocabulary.

Files to inspect first:

- `tools/evidence_tool.py`
- `tools/metric_tool.py`
- `workspaces/product_result_builder.py`
- `workspaces/report_models.py`
- `workspaces/report_evidence.py`
- `workspaces/report_runner.py`
- `agents/final_answer_composer.py`
- `workspaces/fast_fact_composer.py`
- `tests/test_evidence_tool.py`
- `tests/test_metric_tool.py`
- `tests/test_product_result_builder.py`
- `tests/test_report_planner_evidence.py`

Tasks:

- [x] Add failing tests proving the same source data produces consistent top entity, metric value, derived percentage, time scope, and warning fields for analysis answers and report evidence.
- [x] Define or consolidate a shared `EvidencePack` shape that can represent question-level evidence and report-section evidence without leaking SQL/raw rows into the main business answer.
- [x] Ensure derived metrics such as share, average order value, ROI, conversion-like rates, and period changes are calculated by tools when the required fields exist.
- [x] Record formulas and input columns for derived metrics so validators can confirm rounded Chinese display values.
- [x] Keep raw SQL, query ids, raw rows, provider metadata, and trace details in technical details or appendix only.
- [x] Delete duplicate evidence/fact structures once they are no longer called by the active product path.

Acceptance:

- A channel revenue question and a channel report use the same factual top entity and amount.
- A derived percentage in the answer/report is traceable to a formula and source rows.
- If required fields are missing, the evidence pack records a data limit instead of letting the model invent the metric.
- No active logic assumes a specific demo table such as `orders`, `marketing_spend`, or `channel`.

Completion record:

- Completed on 2026-07-03.
- Extended `tools/evidence_tool.build_evidence_payload()` into the shared P23 factual payload (`evidence_pack_version: p23.shared.v1`) while preserving existing `fact_payload` consumers. The shared payload now includes intent, `time_range`, metrics, dimensions, result rows, derived share/rank/trend metrics, formula metadata, chart-ready data, data limits, display values, and technical-detail references.
- Added missing-metric data limits so unsupported requested metrics such as ROI are recorded as unavailable instead of being invented from revenue-only data.
- Added `ReportEvidencePack.evidence_payloads` and `ReportEvidenceTable.evidence_payload_ref` so Report Center can expose the same core evidence payloads collected for chapter evidence, while SQL/raw rows remain in technical details/appendix.
- Added non-channel store-sales coverage and analysis/report parity tests. The active product entries remain separate: Analysis Workbench still returns `product_result.evidence.fact_payload`, and Report Center still writes `ReportDocument` through `plan -> evidence -> compose -> validate -> render -> save`.
- Cleanup audit for stitched/fixed-template/legacy chart and mock terms found no active product-code hits. Remaining hits are historical/superseded docs, negative boundary tests, or the P23 follow-up cleanup task for obsolete section-answer compatibility fields.
- Verification passed:
  - `python3 -m pytest tests/test_evidence_tool.py tests/test_metric_tool.py tests/test_product_result_builder.py tests/test_report_planner_evidence.py -q` (`51 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py -q` (`32 passed`)
  - `python3 -m pytest tests/test_report_composer_validator.py tests/test_workspace_report_api.py tests/test_workspace_report_store.py -q` (`25 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)

Fix record:

- Fixed on 2026-07-03 after H1 review found two contract leaks.
- Removed `technical_sql` and embedded `technical_details.sql` from the shared business evidence payload. Analysis SQL remains available through `product_result.technical_details.sql`; report SQL remains available through `ReportEvidencePack.technical_details["queries"]`.
- Kept `technical_refs` in `build_evidence_payload()` for analysis-side technical expansion, while Report Center strips SQL refs, raw `rows`, trace, query ids, and provider metadata from top-level `ReportEvidencePack.evidence_payloads`.
- Changed derived share/rank/trend metric selection to prefer columns matching `task["metrics"]`, metric registry labels/source fields, and business aliases before falling back to the first numeric column. For example, when `order_count` and `revenue` are both present and the user asks for收入, `revenue_share` and `revenue_rank` are produced instead of `order_count_*`.
- Verification passed:
  - `python3 -m pytest tests/test_evidence_tool.py tests/test_product_result_builder.py tests/test_report_planner_evidence.py -q` (`45 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py -q` (`32 passed`)

## P23-H2: Chinese Business Answer Writer

Goal: Keep the model's explanation and recommendations, but make hard facts evidence-bound and user-facing wording natural.

Files to inspect first:

- `agents/final_answer_composer.py`
- `agents/answer_reviewer.py`
- `workspaces/answer_consistency.py`
- `workspaces/answer_evidence.py`
- `workspaces/product_models.py`
- `frontend/components/BusinessAnswerCard.tsx`
- `frontend/components/RunResult.tsx`
- `tests/test_final_answer_composer.py`
- `tests/test_product_result_builder.py`
- `frontend/tests/workspace-flow.test.tsx`

Tasks:

- [x] Add failing tests for natural Chinese answers that do not contain default phrases such as `证据表第一行显示`, `本轮排序证据中`, internal statuses, SQL, trace ids, or provider metadata.
- [x] Change answer composition so the model returns structured slots for factual conclusion, evidence-backed reasons, business interpretations, recommendations, missing data, caveats, and confidence.
- [x] Allow model-written reasons and recommendations to remain, but label or phrase unsupported causal explanations as hypotheses or conditions.
- [x] Validate only hard facts. Do not block reasonable qualitative advice when it stays inside the evidence boundary.
- [x] Update frontend rendering if needed so factual conclusion, explanation, recommendations, missing data, evidence, and technical details are visually distinct.
- [x] Delete obsolete fixed wording and over-strict downgrade branches that conflict with useful evidence-backed answers.

Acceptance:

- Chinese user questions produce Chinese business replies by default.
- The answer may include model judgment, but hard facts match the evidence pack.
- If cost, ROI, conversion, or repeat-purchase data is missing, the answer can still explain what is known and clearly say what cannot be concluded.
- Technical details remain available but are not the first thing users read.

Completion record:

- Completed on 2026-07-03.
- Added fail-first coverage for the final answer composer, product result builder, workspace analysis runner, and frontend workspace flow so Chinese business answers no longer default to template/debug phrases, internal statuses, SQL, raw rows, trace ids, or provider metadata in the main answer.
- Updated `agents/final_answer_composer.py`, `workspaces/product_result_builder.py`, and `workspaces/answer_consistency.py` so deterministic and provider-normalized answers use natural Chinese business wording, keep factual conclusions grounded in returned evidence, preserve reasonable explanation/recommendation judgment, and phrase unsupported causes as hypotheses or data-bound conditions.
- Missing ROI/cost/conversion/repeat-purchase inputs now produce business boundary caveats and conditional next-step recommendations instead of refusing the whole revenue conclusion or inventing efficiency facts.
- Recommendations are no longer direct-answer duplicates, and caveats now read as business scope/data-boundary notes instead of model/debug cleanup notices.
- Analysis Workbench frontend ordering remains business answer -> evidence -> chart -> collapsed technical details; the main card stays free of SQL/raw rows/provider metadata.
- Cleanup audit found remaining old wording/path hits only in historical/superseded docs, negative tests, cleanup-boundary tests, and the P23 task text itself; no active product-code path needed further migration.
- Verification passed:
  - `python3 -m pytest tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_business_answer_quality.py -q` (`54 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_fast_fact_path.py -q` (`32 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)

Fix record:

- Fixed again on 2026-07-03 after live/provider-style SQL planning showed comparison judgment questions could still return only `LIMIT 1` and lose the peer evidence needed to answer “哪个最需要优先处理/为什么/建议”.
- Added `sql_planning.comparison_scope` as a shared semantic guard for comparison-needed questions. It detects priority, recommendation, budget, optimization, and why-plus-comparison intent from the question and normalized task, while respecting explicit one-result requests.
- The guarded provider SQL candidate agent and final SQL reviewer now widen safe validated `LIMIT 1` SELECT queries to `LIMIT 3` for comparison-needed questions and record `comparison_scope_adjustment.reason = insufficient_comparison_scope` before execution.
- Updated the guarded SQL candidate prompt so provider SQL planning asks for multiple candidate rows, usually `LIMIT 3` or `LIMIT 5`, for why/advice/priority/budget questions; pure factual highest/lowest questions may still use `LIMIT 1`.
- Tightened Chinese task normalization so 优先、最需要、值得、关注、复盘 and provider `recommendation`/`priority` operations route as recommendation-style analysis instead of summary-only analysis.
- Added provider-mock and full workspace-chain regressions for the support-issue priority scenario. A provider SQL candidate with `LIMIT 1` now executes with multi-row comparison evidence and the final business answer keeps Chinese metric labels without leaking SQL aliases, SQL, raw rows, or `execution_result`.
- Verification passed:
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_provider_assisted_sql_planning_workflow.py tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`94 passed`)
  - `python3 -m pytest tests/test_business_answer_quality.py tests/test_fast_fact_path.py -q` (`23 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)

- Fixed again on 2026-07-03 after H2 follow-up found SQL aliases and multi-metric wording could still leak into final Chinese business answers.
- Added dynamic shared business labels in `workspaces.answer_evidence` for SQL aliases such as `total_tickets`, `avg_response`, and `priority_score`, plus generic token rules for totals, averages, response time, revenue/sales, orders, cost/spend, ROI/ROAS, and priority scores.
- Added shared metric leader/tradeoff helpers so evidence bullets and consistency rewrites calculate each metric's leading object from returned rows. Multi-metric answers now express判断口径 differences instead of saying one object is ahead on all returned metrics.
- Updated `agents.final_answer_composer`, `workspaces.answer_consistency`, and `workspaces.product_result_builder` to reuse the shared labeling and leader helpers, including provider-answer cleanup and deterministic fallback paths.
- Recommendation generation remains limited to explicit建议、优化、优先级、预算、下一步 style questions; fact and why-only questions stay focused on facts, cause boundaries, and hypotheses.
- Full-chain support_issues coverage now verifies aliased SQL output (`total_tickets`, `avg_response`, `priority_score`) becomes 总工单数、平均响应时长、优先级评分 or 判断口径 language in the main business answer, without leaking SQL/raw rows/execution_result or row-number wording.
- Verification passed:
  - `python3 -m pytest tests/test_answer_consistency.py tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py -q` (`85 passed`)
  - `python3 -m pytest tests/test_business_answer_quality.py tests/test_fast_fact_path.py -q` (`23 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)

- Fixed on 2026-07-03 after H2 review found evidence bullets and原因解释 were still too row-like and template-like.
- Added fail-first coverage for support-ticket and channel scenarios so Chinese business answers no longer expose `第 1 行`, `Row 1`, `issue_type 为`, `ticket_count 为`, or untranslated raw field names when labels are available.
- Added shared business evidence wording helpers that turn result rows into sentences such as最高对象、指标值、次高对象对比, while leaving SQL/raw rows/provider metadata in technical details only.
- Added lightweight cause-hypothesis context for service issues, channels, and stores. Why answers now state that current data can confirm who is higher/lower but cannot directly prove the reason; hypotheses remain possible directions requiring process data validation.
- Tightened recommendation intent detection: ordinary fact and why questions keep recommendations empty, while explicit建议、优化、优先级、预算、下一步 questions still receive action-oriented recommendations.
- Updated the consistency guardrail so tradeoff rewrites localize service metrics such as工单数 and平均响应时长 instead of leaking raw column ids.
- Verification passed:
  - `python3 -m pytest tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_business_answer_quality.py -q` (`59 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_fast_fact_path.py -q` (`32 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)

## P23-H3: One-Pass Report Center With Shared Evidence

Goal: Preserve P22's one-pass full-report direction while making report evidence, charts, and validation stronger.

Files to inspect first:

- `workspaces/report_planner.py`
- `workspaces/report_evidence.py`
- `workspaces/report_composer.py`
- `workspaces/report_validator.py`
- `workspaces/report_markdown.py`
- `workspaces/report_runner.py`
- `frontend/components/ReportViewer.tsx`
- `frontend/components/ReportGenerator.tsx`
- `tests/test_report_planner_evidence.py`
- `tests/test_report_composer_validator.py`
- `tests/test_workspace_report_runner.py`
- `tests/test_workspace_report_api.py`
- `frontend/tests/workspace-flow.test.tsx`

Tasks:

- [x] Add failing tests proving Report Center does not call Analysis Workbench to generate per-section answers and does not stitch section answers into the final report body.
- [x] Keep section/chapter planning only for evidence collection. The final `ReportWriter` must receive the full plan, all evidence packs, chart refs, warnings, and limits, then write the complete report once.
- [x] Make report titles, report type labels, and time ranges match the user's report goal.
- [x] Generate or attach real chart artifacts when the evidence pack contains chartable data; keep chart-intent placeholders only when artifact generation is unavailable or intentionally deferred.
- [x] Ensure model-written recommendations stay in the report, but unsupported hard facts are downgraded to data limits or conditional suggestions.
- [x] Update Markdown and frontend report rendering so the report reads as one complete Chinese document with charts, evidence summaries, recommendations, data boundaries, and collapsed technical appendix.
- [x] Delete old section-answer rendering, old stitched summary helpers, and obsolete compatibility fields when no longer needed.

Acceptance:

- A business review report reads like one coherent report, not a list of separate Q&A answers.
- A channel performance report has a channel-specific title and evidence focus.
- Charts render inline when artifacts exist and can be downloaded.
- Key report numbers, rankings, dates, and percentages pass validation or are explicitly marked as unavailable.

Completion record:

- Completed on 2026-07-03.
- Strengthened runner/API/composer tests so Report Center cannot call `run_workspace_analysis()` for section bodies, cannot depend on Analysis Workbench `business_answer` output, and must call `report_composer` once with the full `ReportPlan` and shared `ReportEvidencePack`.
- Added `ReportPlan.report_goal`, channel-specific report title/style handling, and evidence data boundaries for requested ROI/投放成本 when the workspace lacks those fields. Supported revenue/order evidence still flows through shared `p23.shared.v1` payloads instead of failing the report.
- Report evidence collection now materializes chartable evidence tables into local SVG chart artifacts in each report's artifact directory. Markdown and `ReportViewer` inline real chart artifacts with download links; missing charts continue to render as business-readable待生成图表/证据不足 placeholders.
- Deleted obsolete report compatibility fields from the active model/API/frontend path: top-level `executive_summary`, `key_findings`, `action_priorities`, `chart_and_evidence`, `risks_and_limits`, and old top-level `sections`. The user-facing report body now comes from `ReportDocument`.
- Main report text and Markdown remain free of SQL, raw rows, execution results, query ids, provider metadata, trace paths, internal contract names, and old section-answer labels. Technical details remain in the collapsed appendix or report technical JSON paths.
- Verification passed:
  - `python3 -m pytest tests/test_report_planner_evidence.py tests/test_report_composer_validator.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`45 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`86 passed`)
  - `python3 -m pytest tests/test_workspace_report_store.py tests/test_p20_realistic_acceptance.py -q` (`8 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`9 passed`)

Fix record:

- Fixed on 2026-07-03 after live DeepSeek report smoke testing exposed two P23-H3 polish issues.
- `report_validator` now accepts percentage/share values only when they are directly derivable from numeric values in the same evidence table, with reasonable rounded forms such as `26.8%`, `18.6%`, and `15.5%`. Unrelated percentages still produce warning validation.
- Provider and deterministic report composition now filter `actions` / `行动建议` sections out of `ReportDocument.sections`; the report keeps recommendations in the dedicated bottom-level `action_recommendations` list.
- Markdown rendering and `ReportViewer` also defensively skip action sections, so older/provider-shaped documents do not show a duplicate “行动建议” block. Frontend progress counts only body sections.
- Verification passed:
  - `python3 -m pytest tests/test_report_composer_validator.py tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`49 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`86 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`9 passed`)
  - `git diff --check` passed

Follow-up fix record:

- Fixed on 2026-07-03 after another live DeepSeek report smoke showed `partial` reports from two validator gaps: provider-written structured `time_range` drift and supported date/year expressions being interpreted as ordinary unsupported numbers.
- `ReportDocument.time_range` is now locked to `ReportPlan.time_range` during provider content conversion. Providers can still explain actual data coverage such as `2026年4月至6月` in the report prose or data boundaries, but cannot overwrite the structured report time range.
- `report_validator` now builds evidence-backed time forms from table/fact date values and trend periods, so supported forms such as `2026-04`, `2026年4月至6月`, and `2026 年 4 月至 6 月` do not create unsupported `2026` claims. Ordinary unsupported business numbers such as `2026 单` still warn.
- Validator support was extended to shared evidence payload `display_value` / `value` fields, table column unit forms such as `100 行`, currency variants such as `4.5万元`, metric-column unit conversions such as `0.77万`, and same-chapter total-derived shares such as `20.4%` and `17.7%`, while unrelated percentages remain rejected.
- Live DeepSeek report smoke passed with provider available: report status `completed`, validation status `passed`, `unsupported_claims` empty, plan/document `time_range` stable, no duplicate `行动建议` section, and no SQL/raw rows/trace/provider metadata leaks in the main body.
- Verification passed:
  - `python3 -m pytest tests/test_report_composer_validator.py tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`56 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`86 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`9 passed`)

## P23-H4: Evidence Ledger And Report Self-Repair

Goal: Stop chasing every possible model-written number with validator patches. Tools should prepare a traceable evidence ledger first; the report writer should use that ledger; validation should check factual claims against ledger ids and repair unsupported facts automatically.

Why this replaces more P23-H3 patching:

- Live DeepSeek reports can correctly derive facts such as totals, shares, period-over-period changes, thresholds, and target recommendations in many different forms.
- A validator that scans the final prose and tries to rediscover every possible calculation will keep growing into brittle rule code.
- The more stable product design is to calculate common business facts and derived metrics before writing, expose them as a compact evidence ledger, and ask the model to cite or select from that ledger for factual statements.
- Model freedom should remain in explanations, hypotheses, and recommendations. It should not be responsible for inventing or recalculating hard facts in prose.

Files to inspect first:

- `workspaces/report_evidence.py`
- `workspaces/report_models.py`
- `workspaces/report_composer.py`
- `workspaces/report_validator.py`
- `workspaces/report_runner.py`
- `workspaces/report_markdown.py`
- `tools/evidence_tool.py`
- `tools/metric_tool.py`
- `frontend/components/ReportViewer.tsx`
- `tests/test_report_composer_validator.py`
- `tests/test_report_planner_evidence.py`
- `tests/test_workspace_report_runner.py`
- `tests/test_workspace_report_api.py`

Target evidence ledger shape:

```json
{
  "ledger_version": "p23.report_ledger.v1",
  "facts": [
    {
      "evidence_id": "revenue_total",
      "label": "总收入",
      "display_value": "97.0 万",
      "value": 970000,
      "unit": "currency",
      "source": "revenue_total",
      "formula": "SUM(revenue)",
      "claim_phrases": ["总收入97.0万元", "收入合计97.0万"]
    }
  ],
  "derived_metrics": [
    {
      "evidence_id": "channel_share_enterprise_wechat",
      "label": "企业微信收入占比",
      "display_value": "39.2%",
      "formula": "380000 / 970000",
      "source_values": ["企业微信收入38.0万", "总收入97.0万"]
    }
  ],
  "recommendation_context": [
    {
      "topic": "交付排期",
      "basis": ["满意度最低", "平均响应时长最高"],
      "allowed_target_metric": "平均响应时长"
    }
  ],
  "data_boundaries": ["缺少利润、成本和转化率字段。"]
}
```

Evidence sufficiency rules:

- The ledger should be generated from structured `EvidenceRequirement` records, not from free-form model prose.
- Each report chapter should define a minimum evidence set. For example, revenue structure needs total value, grouped ranking, share, top/bottom comparison, and missing efficiency/profit fields; trend chapters need time series, period changes, max/min periods, and time coverage limits.
- A `CoverageChecker` should mark every chapter as `strong`, `partial`, or `missing`, with `available_evidence`, `missing_evidence`, `allowed_claims`, and `blocked_claims`.
- If a missing evidence item can be derived from existing evidence, the system should compute it before writing the report. If it requires unavailable source fields, it should become a data boundary.
- The model may help interpret the report goal and choose relevant chapters, but tools own evidence sufficiency, calculations, and data boundaries.

Tasks:

- [x] Add failing tests proving Report Center can generate a ledger with raw facts, table totals, shares, combined shares, period-over-period changes, rankings, and data coverage facts from generic evidence tables.
- [x] Add failing tests for chapter-level coverage: strong evidence when the minimum set exists, partial evidence when optional fields such as cost/profit/ROI are missing, and missing evidence when a requested topic has no usable fields.
- [x] Create a focused report evidence ledger module instead of continuing to expand prose-scanning validator branches. Keep it small and independent enough to read in one pass.
- [x] Add a `CoverageChecker` that turns evidence requirements into available evidence, missing evidence, allowed claims, blocked claims, and data boundaries.
- [x] Add an automatic evidence completion step for derivable facts such as totals, shares, combined shares, period-over-period changes, rankings, and max/min comparisons before the report composer runs.
- [x] Feed the report composer with `EvidenceLedger` plus chart refs and boundaries. Prompt the model to use ledger values for hard facts, while allowing free Chinese business explanation and recommendations.
- [x] Change report validation from broad prose-number guessing to ledger-backed claim validation. Validate factual claims in opening summary, sections, and data boundaries; treat recommendation target numbers as proposed targets when the wording clearly marks them as goals or actions.
- [x] Add a single automatic repair pass: when unsupported factual claims remain, ask the report composer to rewrite only those unsupported facts by deleting them, softening them into hypotheses, or replacing them with available ledger facts.
- [x] Keep the final report user-facing. The ledger and repair trace belong in the collapsed appendix or technical JSON, not in the main report body.
- [x] Delete old validator branches and compatibility code that become unreachable after ledger-backed validation. Do not preserve old behavior only for historical reports.

Acceptance:

- A live DeepSeek report can include common derived metrics such as totals, shares, combined shares, and period-over-period changes without creating `partial` reports when those values are ledger-backed.
- Every report chapter carries coverage metadata, so the model knows which claims are allowed and which claims are blocked by missing data.
- If evidence is insufficient but recoverable through derivation, the system completes the ledger before report writing; if not recoverable, it produces a clear data boundary instead of asking the model to guess.
- Unsupported invented hard facts are repaired or removed before the user sees the final report.
- Recommendation targets such as “目标降至40分钟以内” do not fail validation when they are clearly proposals rather than historical facts.
- The code path is easier to understand than the current validator-rule chase: evidence ledger generation, report writing, validation, and repair are separate modules or clearly separated functions.
- No table-specific business rule tree is introduced for the current Chinese sample data.
- Old report-section stitching, old compatibility fields, unused fallback branches, and obsolete tests may be deleted instead of kept.

Implementation result:

- Added `workspaces/report_ledger.py` with `EvidenceLedger`, ledger facts/derived metrics, `CoverageChecker`, recommendation context, data boundaries, and technical refs. The ledger version is `p23.report_ledger.v1`.
- `ReportRunner` now runs `ReportPlan -> ReportEvidencePack -> EvidenceLedger -> one-pass ReportComposer -> ledger-backed Validator -> optional one-pass Repair -> render/save`.
- `ReportComposer` prompts on `EvidenceLedger`, chart refs, and data boundaries, while preserving model freedom for explanations and recommendations. It also exposes `repair_report_document()` for one repair pass.
- `ReportValidator` now uses ledger-backed supported values and no longer contains the old branches that derived shares/chapter-total shares/payload percentages by scanning final prose. It still validates title/time range/data sources, refs, dates, rankings, unsupported hard numbers, and fake historical facts inside action recommendations.
- Markdown and `ReportTechnicalAppendix` show concise chapter coverage summaries in the collapsed appendix and do not dump raw ledger JSON into the report body.
- Live DeepSeek smoke passed with provider available: status `completed`, validation `passed`, `unsupported_claims` empty, `generation_flow=ledger_backed_report_center`, no duplicate action section, no SQL/raw_rows/trace/provider_metadata/query leaks in the main body, and the ledger contained totals, shares, combined shares, and period changes.
- Verification passed:
  - `python3 -m pytest tests/test_report_composer_validator.py tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`64 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_final_answer_composer.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`86 passed`)
  - `python3 -m pytest tests/test_workspace_report_store.py tests/test_p20_realistic_acceptance.py tests/test_p12_live_deepseek_workspace_report.py -q` (`8 passed, 1 skipped`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`9 passed`)

## P23-H5: Artifact And Tool-Calling Readiness

Goal: Prepare the internal artifact contract so P24 can connect real external tools without rewriting the analysis/report chain or bypassing the P23-H4 evidence ledger.

Files to inspect first:

- `workspaces/report_models.py`
- `workspaces/report_store.py`
- `workspaces/report_markdown.py`
- `workspaces/report_ledger.py` if created in P23-H4
- `tools/external_visualization_tool.py` if still present
- `frontend/lib/api.ts`
- `frontend/components/ReportViewer.tsx`
- current visualization/report artifact tests

Target artifact records:

```json
{
  "artifact_id": "artifact_chart_xxx",
  "artifact_type": "chart",
  "title": "渠道收入排行",
  "relative_path": "reports/report_xxx/artifacts/chart_xxx.svg",
  "download_url": "",
  "source": "local_renderer",
  "evidence_ids": ["ledger_fact_xxx"],
  "ledger_metric_ids": ["ledger_metric_xxx"],
  "chart_ids": ["chart_xxx"],
  "created_at": "2026-07-03T00:00:00Z",
  "status": "completed",
  "error": ""
}
```

Tasks:

- [x] Inventory current chart/report artifact fields used by analysis, reports, API responses, Markdown, and frontend rendering.
- [x] Consolidate artifact records enough that future Word/PDF/PPT/Excel/飞书/腾讯文档 tools can consume the same references without re-querying or re-interpreting facts.
- [x] Ensure chart and report artifacts can reference `EvidenceLedger` entries by `evidence_id` / derived metric id, not only by loose table or chart titles.
- [x] Add or update tool call records so each tool call captures tool name, input summary, referenced evidence ids, output artifact ids, status, and error without exposing secrets or raw data in the main UI.
- [x] Preserve local artifact generation as the current implementation; do not add real external SaaS in P23.
- [x] Keep artifact records compatible with local chart generation today and external document/export tools in P24.
- [x] Delete unused mock external tool placeholders that are not part of the current product path.

Acceptance:

- Analysis and report chart artifacts use a compatible record shape.
- Reports can reference chart artifacts through ledger evidence ids without knowing whether they were generated locally or by a future external tool.
- Future document/export tools can render charts and report sections from artifact ids plus ledger evidence ids, rather than reading raw SQL rows or asking the model to recalculate.
- Tool call records stay technical and auditable, while the main UI remains business-facing.
- P24 can focus on real tool integration instead of fixing artifact plumbing.

Completion record:

- Completed on 2026-07-03.
- Added `ReportArtifactRecord` and `ReportToolCallRecord` to the report contract. Artifact records now carry `artifact_id`, `artifact_type`, title, `relative_path` or `download_url`, `source`, `evidence_ids`, `ledger_metric_ids`, `chart_ids`, timestamps, status, and error. Tool call records carry tool name, safe input summary, referenced ledger evidence ids, output artifact ids, status/error, and start/complete times.
- Extended `ReportEvidenceChart` with `artifact_id`, `evidence_ids`, and `ledger_metric_ids`. `build_evidence_ledger()` now annotates chart artifacts by matching chart `evidence_ref` to ledger facts and derived metrics, so charts no longer depend only on loose table titles.
- `run_workspace_report()` now records local chart artifacts, Markdown report artifacts, report-document artifacts, local chart renderer calls, and Markdown renderer calls. Report and Markdown artifacts reference ledger evidence ids so future export tools can consume trusted facts without raw SQL, raw rows, query ids, trace, provider metadata, or model recalculation.
- Markdown and `ReportViewer` show business-readable artifact summaries and ledger-reference counts only. The main UI does not display raw ledger JSON, SQL, raw rows, query ids, trace/provider metadata, artifact ids, ledger ids, local filesystem paths, or tool names.
- No real PowerPoint/Word/PDF/飞书/钉钉/企业微信 integration was added, no simulated external integration layer was introduced, and old `chart_tool` / `action_delivery` / `powerbi_publisher_mock` / `jira_ticket_mock` paths were not restored.
- Verification passed:
  - `python3 -m pytest tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` (`54 passed`)
  - `python3 -m pytest tests/test_report_composer_validator.py tests/test_workspace_report_store.py -q` (`25 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`67 passed`)
  - `cd frontend && npm test -- --run tests/workspace-flow.test.tsx` (`54 passed`)
  - `cd frontend && npm test -- --run tests/api-client.test.ts` (`9 passed`)

## P23-H6: Cleanup, Regression, And Live Acceptance

Goal: Prove P23 is stable and clean enough to move into real external tool integrations.

Tasks:

- [x] Run targeted backend tests for evidence, metrics, product result builder, answer composer/reviewer, report planner/evidence/composer/validator/runner, and artifact rendering.
- [x] Run frontend tests covering Analysis Workbench answers, evidence display, Report Center generation, report detail rendering, chart downloads, and collapsed technical appendix.
- [x] Run full backend pytest and frontend build.
- [x] Check opt-in real DeepSeek readiness. Real provider acceptance was not run in this environment because `DEEPSEEK_API_KEY`, `INSIGHTFLOW_PRODUCT_LIVE_MODE=1`, and live-test flags were absent.
- [x] Record live manual acceptance status. The required live Chinese analysis/report questions were not executed because the live provider environment was absent; no-key deterministic acceptance remained runnable.
- [x] Confirm Report Center uses the EvidenceLedger path and does not fall back to prose-number validator patching as the primary safety mechanism.
- [x] Confirm ledger-backed totals, shares, combined shares, period changes, and rankings remain covered by regression tests without unsupported hard-fact claims in generated reports.
- [x] Confirm unsupported hard facts are either repaired once, softened into hypotheses, or moved to data boundaries before the user sees the final report.
- [x] Confirm report technical appendix can summarize coverage status without showing ledger debug dumps in the main report body.
- [x] Confirm chart/report artifacts reference ledger evidence ids after P23-H5.
- [x] Audit old-path terms and remove or mark remaining hits as historical/superseded.
- [x] Confirm generated runtime artifacts, traces, workspace DBs, reports, and secrets are not staged.

Suggested live questions:

```text
最近90天哪个获客渠道收入最高？为什么？
最近90天哪个渠道最值得加预算？
最近90天客服问题里哪个问题类型最需要优先处理？
最近90天收入趋势怎么样？有没有异常？
不同客户分群的收入贡献有什么差异？
```

Suggested live reports:

```text
生成最近90天经营复盘报告，包含收入结构、客户分群、客服问题、趋势变化和行动建议。
生成最近90天渠道表现报告，重点比较各获客渠道收入贡献、投放效率和下一步动作建议。
```

Acceptance:

- Analysis answers are natural Chinese business replies.
- Report Center produces full Chinese reports, not stitched analysis answers.
- Hard facts are evidence-bound and validated.
- Evidence-bound report facts flow through the P23-H4 ledger; the final validator no longer needs a growing list of ad hoc prose-number exceptions.
- Model-written explanations and recommendations are preserved with clear evidence strength.
- Real chart artifacts render where chartable evidence exists.
- Artifacts can be traced back to ledger evidence ids and do not require raw data or SQL in the main UI.
- No obsolete active path blocks future external tool calling.

Completion record:

- Completed on 2026-07-03. P23 is ready to close and hand off to P24.
- Focused backend regression passed for report evidence/planner/composer/validator/runner/API, analysis runner, product result builder, answer consistency, architecture cleanup boundaries, product cleanup boundaries, and MCP tool-layer boundaries.
- Full backend regression passed: `python3 -m pytest` (`511 passed, 11 skipped`).
- Frontend regression passed: `cd frontend && npm test` (`68 passed`) and `cd frontend && npm run build`.
- Closeout fixes kept the current product contract sharp: `guarded_sql_candidate` prompt tests now assert v2, provider-backed insight tests assert the canonical data caveat, run-history API tests assert normalized Chinese headline punctuation, and `ReportViewer` preserves section `chart_refs` in its typed report-body helper.
- Report Center remains ledger-backed and one-pass. It still records chart/report artifacts and local tool-call records that cite ledger facts/derived metrics, while the main UI hides SQL, raw rows, query ids, trace/provider metadata, local absolute paths, ledger ids, artifact ids, and tool names.
- Old-path audit found remaining legacy terms only in Historical/Superseded documentation, negative boundary tests, or assertions that old strings such as `章节业务答案` are absent from product output. No active runtime path restored old chart agents, action delivery/drafter, mock SaaS, old stitched reports, fixed templates, keyword inference, Streamlit, or eval runners.
- Tracked artifact audit passed: no `.env`, `frontend/.next`, pytest/cache files, `__pycache__`, workspace run/report output, chart/Markdown report output, trace JSON, or sample data are tracked.
- Live DeepSeek acceptance was not run because `DEEPSEEK_API_KEY`, `INSIGHTFLOW_PRODUCT_LIVE_MODE`, `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS`, and `INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER` were absent. The live-gated tests skipped (`3 skipped`) and no provider call was claimed.
- No-key mode was verified through deterministic report fallback tests (`2 passed`) and the full regression suite.

## P23 Does Not Do

- No real 飞书、企业微信、钉钉、腾讯文档、PowerPoint, Word, PDF, or email integrations.
- No auth/RBAC.
- No vector database or semantic cache.
- No aggressive similar-question cache.
- No frontend redesign beyond what is needed to present the cleaned answer/report contracts.
- No table-specific business rule tree for the Chinese sample dataset.
- No new simulated external SaaS integration layer.

## Handoff To P24

P23 is complete when the core product can honestly claim:

```text
InsightFlow is a Chinese-first business data analysis multi-agent product.
Users can upload business data, ask questions in Analysis Workbench, and generate complete reports in Report Center.
Agents understand, plan, explain, recommend, write, and validate.
Tools query data, calculate metrics, produce evidence, generate charts, persist artifacts, and prepare report outputs.
```

Current planning supersedes the original handoff wording above: before real business tool calling and exports, P24 should strengthen general business data understanding and evidence generation across common Chinese business datasets. External chart/document/export integrations should start after that foundation is proven with deterministic regression and real DeepSeek acceptance.
