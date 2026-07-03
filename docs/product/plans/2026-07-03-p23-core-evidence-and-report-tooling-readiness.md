# P23 Core Evidence And Report Tooling Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the shared factual evidence layer, Chinese business answer writing, and one-pass report generation path so InsightFlow can move next into real external chart/document/export tools.

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

P23 is the final core-chain hardening phase before external tool calling. After P23, work should be able to move into real chart/document/export integrations without wrapping unstable analysis output in nicer artifacts.

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

- [ ] Add failing tests proving Report Center does not call Analysis Workbench to generate per-section answers and does not stitch section answers into the final report body.
- [ ] Keep section/chapter planning only for evidence collection. The final `ReportWriter` must receive the full plan, all evidence packs, chart refs, warnings, and limits, then write the complete report once.
- [ ] Make report titles, report type labels, and time ranges match the user's report goal.
- [ ] Generate or attach real chart artifacts when the evidence pack contains chartable data; keep chart-intent placeholders only when artifact generation is unavailable or intentionally deferred.
- [ ] Ensure model-written recommendations stay in the report, but unsupported hard facts are downgraded to data limits or conditional suggestions.
- [ ] Update Markdown and frontend report rendering so the report reads as one complete Chinese document with charts, evidence summaries, recommendations, data boundaries, and collapsed technical appendix.
- [ ] Delete old section-answer rendering, old stitched summary helpers, and obsolete compatibility fields when no longer needed.

Acceptance:

- A business review report reads like one coherent report, not a list of separate Q&A answers.
- A channel performance report has a channel-specific title and evidence focus.
- Charts render inline when artifacts exist and can be downloaded.
- Key report numbers, rankings, dates, and percentages pass validation or are explicitly marked as unavailable.

## P23-H4: Artifact And Tool-Calling Readiness

Goal: Prepare the internal artifact contract so P24 can connect real external tools without rewriting the analysis/report chain.

Files to inspect first:

- `workspaces/report_models.py`
- `workspaces/report_store.py`
- `workspaces/report_markdown.py`
- `tools/external_visualization_tool.py` if still present
- `frontend/lib/api.ts`
- `frontend/components/ReportViewer.tsx`
- current visualization/report artifact tests

Target artifact records:

```json
{
  "artifact_id": "chart_xxx",
  "artifact_type": "chart",
  "title": "渠道收入排行",
  "format": "png",
  "file_path": "...",
  "evidence_pack_id": "evidence_xxx",
  "created_by_tool": "local_chart_renderer",
  "status": "completed"
}
```

Tasks:

- [ ] Inventory current chart/report artifact fields used by analysis, reports, API responses, Markdown, and frontend rendering.
- [ ] Consolidate artifact records enough that future Word/PDF/PPT/Excel/飞书/腾讯文档 tools can consume the same references.
- [ ] Preserve local artifact generation as the current implementation; do not add real external SaaS in P23.
- [ ] Ensure tool call records capture tool name, input summary, output artifact, status, and error without exposing secrets or full raw data in the main UI.
- [ ] Delete unused mock external tool placeholders that are not part of the current product path.

Acceptance:

- Analysis and report chart artifacts use a compatible record shape.
- Reports can reference chart artifacts without knowing whether they were generated locally or by a future external tool.
- P24 can focus on real tool integration instead of fixing artifact plumbing.

## P23-H5: Cleanup, Regression, And Live Acceptance

Goal: Prove P23 is stable and clean enough to move into real external tool integrations.

Tasks:

- [ ] Run targeted backend tests for evidence, metrics, product result builder, answer composer/reviewer, report planner/evidence/composer/validator/runner, and artifact rendering.
- [ ] Run frontend tests covering Analysis Workbench answers, evidence display, Report Center generation, report detail rendering, chart downloads, and collapsed technical appendix.
- [ ] Run full backend pytest and frontend build.
- [ ] Run opt-in real DeepSeek tests when `DEEPSEEK_API_KEY`, `INSIGHTFLOW_PRODUCT_LIVE_MODE=1`, and live-test flags are available.
- [ ] Manually test at least five Chinese analysis questions and two Chinese reports on a realistic Chinese business dataset.
- [ ] Audit old-path terms and remove or mark remaining hits as historical/superseded.
- [ ] Confirm generated runtime artifacts, traces, workspace DBs, reports, and secrets are not staged.

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
- Model-written explanations and recommendations are preserved with clear evidence strength.
- Real chart artifacts render where chartable evidence exists.
- No obsolete active path blocks future external tool calling.

## P23 Does Not Do

- No real 飞书、企业微信、钉钉、腾讯文档、PowerPoint, Word, PDF, or email integrations.
- No auth/RBAC.
- No vector database or semantic cache.
- No aggressive similar-question cache.
- No frontend redesign beyond what is needed to present the cleaned answer/report contracts.
- No table-specific business rule tree for the Chinese sample dataset.
- No new mock SaaS integration layer.

## Handoff To P24

P23 is complete when the core product can honestly claim:

```text
InsightFlow is a Chinese-first business data analysis multi-agent product.
Users can upload business data, ask questions in Analysis Workbench, and generate complete reports in Report Center.
Agents understand, plan, explain, recommend, write, and validate.
Tools query data, calculate metrics, produce evidence, generate charts, persist artifacts, and prepare report outputs.
```

After that, P24 should start real business tool calling and exports: stronger chart rendering, Word/PDF/PPT/Excel outputs, and China-oriented document/collaboration tools where useful.
