# P24 General Business Data Understanding And Evidence Generation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make InsightFlow stronger as a Chinese-first business data analysis product by improving generic data understanding, evidence generation, and real DeepSeek acceptance across different business datasets.

**Architecture:** Keep Analysis Workbench and Report Center as separate product experiences. Both may share data profiling, semantic-layer drafting, evidence requirements, metric calculation, SQL execution, evidence ledgers, chart artifacts, and validation. Tools own hard facts. Model-backed agents explain, infer business meaning, and recommend inside evidence boundaries.

**Tech Stack:** FastAPI, Python workspace services, LangGraph analysis workflow, SQLite workspace databases, semantic-layer JSON/YAML, DeepSeek provider path, local chart/report artifacts, Next.js App Router, React, TypeScript, pytest, Vitest, opt-in live DeepSeek acceptance.

---

## Why P24 Exists

P20-P23 moved InsightFlow away from demo-specific analysis and toward a Chinese business data analysis product. Real usage still exposed one important gap: many tests and examples naturally concentrate on the current sample fields such as渠道、收入、投放、ROI. That is not enough for a credible product.

P24 focuses on the business-data foundation before external document or collaboration integrations. The product should handle common business datasets such as store sales, product sales, customer repeat purchase, support operations, marketing spend, and regional performance. It should not assume that every workspace has `orders`, `channel`, `revenue`, `spend`, or `order_date`.

## Product Boundary

P24 is not a universal BI platform and not the external export phase. It is a focused hardening phase for common business data analysis:

- understand uploaded business tables and fields;
- infer available metrics, dimensions, time fields, entities, and relationship candidates;
- convert Chinese business questions and report goals into evidence requirements;
- use tools to calculate facts and evidence before model writing;
- clearly state data limits when fields or joins are unavailable;
- verify the current product path with real DeepSeek calls.

Do not add:

- Word/PPT/PDF/飞书/企业微信/钉钉/Tencent Docs integrations;
- RBAC, deployment, scheduling, vector databases, or external SaaS sync;
- keyword-heavy business rule trees;
- table-specific demo branches;
- old stitched report paths, fixed answer templates, or legacy mock adapters.

## Non-Negotiable Cleanup Policy

P24 may delete old paths, compatibility code, stale tests, fixtures, and docs that conflict with the current product direction. Do not keep code only because it used to support a previous phase.

Delete or replace:

- sample-data-specific branches that only work for current channel/revenue/spend fields;
- tests that only protect old template wording or old report stitching;
- duplicate field-role, metric, evidence, report, or chart contracts made obsolete by the P24 path;
- stale bilingual output branches that complicate Chinese-first product behavior;
- unused adapters, dead imports, unreachable fallbacks, and historical compatibility wrappers.

Keep or strengthen:

- workspace CSV/Excel/SQLite import;
- data profile and semantic-layer draft;
- question understanding and clarification;
- SQL review, SQL execution, schema repair, metric calculation, evidence validation, report evidence ledger, chart/report artifacts, and trace boundaries;
- model-backed Chinese explanation, business judgment, and recommendations;
- opt-in real DeepSeek acceptance.

## Target Chain After P24

```text
workspace import
-> generic field profile
-> semantic-layer draft with metrics, dimensions, time fields, entities, and relationships
-> question/report goal
-> evidence requirements
-> SQL/metric/evidence tools
-> analysis answer OR full report
-> validation and artifact rendering
-> real DeepSeek acceptance evidence
```

The model may explain why a result matters, compare tradeoffs, and propose next actions. It must not invent hard facts. Missing source fields, weak joins, unsupported metrics, and unavailable time filters must become data limits.

## P24-H1: General Data Understanding

Goal: Let InsightFlow understand common business datasets without relying on fixed sample field names.

Files to inspect first:

- `workspaces/profiler.py`
- `workspaces/semantic_draft.py`
- `workspaces/context_summary.py`
- `tools/metric_tool.py`
- `tools/evidence_tool.py`
- `question_understanding/`
- `tests/test_workspace_profiler.py`
- `tests/test_metric_tool.py`
- `tests/test_evidence_tool.py`
- `tests/test_p20_realistic_acceptance.py`

Tasks:

- [x] Add fail-first tests with non-channel datasets such as store sales, product sales, customer repeat purchase, support operations, and regional performance.
- [x] Strengthen generic field-role detection for time, amount, cost, quantity, id, category/dimension, customer, product, store, region, channel, and operational metrics.
- [x] Improve semantic-layer drafts so different raw names such as销售额、成交金额、GMV、收入、Sales Amount map to Chinese business metric aliases without inventing unavailable fields.
- [x] Record unavailable metrics as capabilities/data limits. For example, missing cost means ROI/profit cannot be fully calculated; missing date means recent-period trends cannot be guaranteed.
- [x] Keep detection conservative when fields are ambiguous. Prefer asking for clarification or recording a data limit over silently choosing the wrong field.
- [x] Delete old field-mapping branches or tests that only protect the current sample schema.

Acceptance:

- The same product path can profile and draft semantics for at least three different Chinese business datasets that do not share the original channel/revenue/spend/order-date shape.
- Common business aliases map into Chinese metric/dimension labels.
- Missing fields produce explicit data limits, not invented metrics.
- No active code assumes `orders`, `marketing_spend`, `channel`, `revenue`, `spend`, or `order_date` as required product fields.

Status: Completed on 2026-07-03.

Result:

- Added P24-H1 fail-first coverage for 门店销售、商品销售、客服/工单运营 plus a missing-limit 区域销售 case.
- `workspaces.profiler` now recognizes broader common business roles including 下单时间/创建时间/月, GMV/实付金额/成交金额/收入金额, 成本/采购成本/投放金额, 销量/订单数/件数/工单数, 编号字段, 门店/城市/商品/品类/团队 dimensions, and 平均响应分钟 style operational metrics.
- `workspaces.semantic_draft` now emits Chinese aliases/labels, field roles, entities, time fields, relationship candidates, capability flags, and data limits without requiring channel/revenue/spend/order_date sample fields.
- `tools.metric_tool` now preserves semantic-layer capability flags and blocks ROAS/净投放回报率/利润率 formulas when required fields are split across unrelated tables.
- `tools.evidence_tool` now carries missing time/cost/ROI/join limits from the real metric registry into shared evidence payloads when the task or requested metrics require those inputs.
- Verification: focused H1 tests `38 passed`; related analysis/product regression `58 passed`; cleanup/init boundary regression `9 passed`.

## P24-H2: General Evidence Chain

Goal: Convert questions and report goals into evidence requirements, then let tools calculate evidence for both Analysis Workbench and Report Center.

Files to inspect first:

- `workspaces/analysis_runner.py`
- `graph/workflow.py`
- `graph/nodes.py`
- `question_understanding/route_policy.py`
- `sql_planning/`
- `tools/metric_tool.py`
- `tools/evidence_tool.py`
- `workspaces/report_planner.py`
- `workspaces/report_evidence.py`
- `workspaces/report_ledger.py`
- `workspaces/report_composer.py`
- `workspaces/report_validator.py`
- `tests/test_workspace_analysis_runner.py`
- `tests/test_report_planner_evidence.py`
- `tests/test_report_composer_validator.py`

Tasks:

- [x] Add fail-first tests for ranking, trend, contribution/share, comparison, operational performance, and investment-efficiency questions across different dataset shapes.
- [x] Represent evidence requirements explicitly: time range, metrics, dimensions, filters, grouping, comparison scope, desired calculation, and missing evidence.
- [x] Use semantic-layer fields to calculate facts instead of table-specific branches.
- [x] Add generic cross-table evidence where safe: for example revenue plus cost by a shared dimension and compatible time fields. If no safe join exists, record a data limit.
- [x] Keep Analysis Workbench and Report Center product outputs separate. They may share evidence and ledger helpers, but Report Center must still write one full report rather than stitched analysis answers.
- [x] Ensure report evidence can cover common report goals such as经营复盘、门店表现、商品表现、客户复购、客服运营、渠道投放表现, when the uploaded data supports them.
- [x] Delete obsolete evidence/report paths made unreachable by the generic evidence chain.

Acceptance:

- Analysis answers and reports use tool-produced evidence for hard facts.
- Recommendation-style answers can include model judgment, but rankings, amounts, percentages, dates, and metric formulas come from evidence.
- If a question asks for ROI/profit/trend/repeat purchase and the data lacks required fields or joins, the product says exactly what is missing.
- Report Center produces a coherent Chinese report, not multiple Analysis Workbench answers pasted together.

Status: Completed on 2026-07-03.

Result:

- Added P24-H2 fail-first coverage for generic 门店销售 ranking, 商品销售 contribution/share, 客服/工单 operational-efficiency analysis, common report-goal evidence planning, report evidence collection, and unsafe cross-table投放效率 limits.
- `tools.evidence_tool.build_evidence_payload()` now exposes explicit `evidence_requirements` with time range, metrics, dimensions, filters, grouping, comparison scope, calculation type, and missing evidence.
- `question_understanding.task_contract` and the SQL generation path now carry generic calculation intent such as ranking, contribution, operational efficiency, trend/comparison hints, and safe investment-efficiency needs without depending on the original sample table names.
- Analysis Workbench can use workspace semantic-layer metrics/dimensions/time fields to calculate supported ranking, contribution/share, operational, and same-table investment-efficiency facts for datasets such as 门店销售、商品销售、客服运营、渠道投放.
- Report Center plans and collects generic evidence for经营复盘、门店表现、商品表现、客服运营、渠道投放表现 while preserving the one-pass coherent Chinese report path.
- Unsafe cross-table ROI/ROAS/净投放回报率 requests now record a data limit when收入 and投放 fields are not in the same analyzable table or otherwise safely related.
- Verification: focused H2 tests `107 passed`; related realistic/product regression `32 passed`; cleanup/init boundary regression `9 passed`.

## P24-H3: Real Acceptance And Cleanup

Goal: Prove the P24 chain with realistic Chinese business data, real DeepSeek calls, regression tests, and cleanup.

Files to inspect first:

- `tests/test_p20_realistic_acceptance.py`
- `tests/test_p20_live_deepseek_acceptance.py`
- `tests/test_p12_live_deepseek_workspace_report.py`
- `tests/test_p11_live_deepseek_workspace_analysis.py`
- `README.md`
- `DEVELOPMENT_PLAN.md`
- `DEVELOPMENT_STATUS.md`

Tasks:

- [x] Prepare or reuse realistic Chinese business datasets for store sales, product sales, customer repeat purchase/customer segmentation, support operations, marketing spend, and regional performance.
- [x] Run deterministic regression for data understanding, semantic-layer drafts, evidence generation, analysis answers, reports, charts, and frontend rendering.
- [x] Run real DeepSeek acceptance with local opt-in flags and a real key. This covers Analysis Workbench and Report Center.
- [x] Record live-test evidence: questions asked, fields/metrics recognized, evidence generated, model conclusions, report output, data limits, hallucination/conflict checks, and remaining limitations.
- [x] Fix live-test failures in the smallest appropriate layer: field understanding, evidence requirement, metric/evidence tool, prompt, validator, or frontend rendering. Do not weaken tests just to pass.
- [x] Delete obsolete code, stale tests, generated artifacts, old paths, and compatibility wrappers that are no longer part of the product.
- [x] Update README, DEVELOPMENT_PLAN, DEVELOPMENT_STATUS, and this plan with completion notes.

Acceptance:

- Full deterministic backend regression passes.
- Frontend tests and build pass.
- Real DeepSeek analysis and report acceptance run successfully when the local environment has the key and flags.
- Product-facing output is Chinese and business-readable.
- Generated reports and answers are grounded in evidence and name data limits clearly.
- Tracked-artifact audit is clean.
- Old-path audit finds only Historical/Superseded documentation, negative tests, or intentionally retained low-level fixtures.

Status: Completed on 2026-07-04.

Result:

- Added P24-H3 acceptance coverage for a realistic Chinese workspace with 门店销售、商品/品类销售、客户分群、客服/工单运营、渠道投放、区域表现 datasets.
- Analysis Workbench deterministic acceptance verifies ranking, contribution/share, operational efficiency, same-table investment-efficiency, formula traceability, report-safe chart artifacts, Chinese business output, and explicit data limits for unsupported复购/趋势 needs.
- Report Center deterministic acceptance verifies one coherent Chinese report, evidence payloads, evidence ledger, chart artifacts, data boundaries for missing利润/复购 inputs, and no stitched analysis-answer body.
- Fixed closeout issues found by acceptance:
  - generic SQL time filters now support month-grain `YYYY-MM` fields by treating them as the first day of the month;
  - report SVG chart rendering handles all-zero numeric series safely;
  - metric registry selects compatible same-table revenue/spend pairs for ROAS and净投放回报率 even when other revenue metrics exist;
  - ratio and AOV formulas use floating-point division in SQLite.
- Fixed the P24-H3 live blocker where answer consistency could rewrite a supported “最值得优先复盘/风险/改善/优先处理” conclusion to the highest-sales or highest-ranked entity. The ranked correction now uses decision direction: risk/improvement questions prefer low positive metrics such as销售额、毛利率、满意度 or high risk metrics such as响应时长/投诉/工单 pressure; growth/best/benchmark questions still prefer high positive metrics or low duration/cost metrics when evidence supports that direction.
- Fixed the final P24-H3 intent edge case where natural prefixes such as “我有个问题” could be mistaken for risk/improvement intent. The standalone word “问题” no longer acts as a strong risk marker, explicit growth/best/benchmark markers are evaluated first, and “我有个问题，最近90天哪个门店表现最好，最值得作为标杆？” now stays aligned to 上海旗舰店 while “客服问题最需要优先处理” remains risk-directed.
- Report Center live acceptance is more stable: when a real provider report or provider repair remains partial or unsupported after validation, the runner falls back to the deterministic evidence-ledger report composer instead of closing a partial report as successful.
- Real DeepSeek acceptance ran with local `.env` plus explicit opt-in flags. The new live P24 test records the analysis question, recognized task, semantic fields/metrics, evidence requirements, evidence rows, model answer, report goal, report opening summary/sections, chart/report artifacts, and data limits. The live suite passed: `python3 -m pytest tests/test_p20_live_deepseek_acceptance.py tests/test_p12_live_deepseek_workspace_report.py tests/test_p11_live_deepseek_workspace_analysis.py -q` (`4 passed in 210.23s`).
- Frontend acceptance remains clean: Analysis Workbench displays business conclusions, progress, evidence, charts, data limits/history, and keeps SQL/raw rows/trace/provider/prompt details out of the main UI; Report Center displays complete reports, chart artifacts, evidence summaries, data boundaries, and Markdown download without exposing internal ids or local paths.
- Cleanup and hygiene passed: old-path scan only found Historical/Superseded docs and negative/rejection tests; tracked-artifact scan found no committed `.env`, `.next`, caches, workspace runs/reports, chart/report output, trace JSON, or sample data.
- Verification:
  - `python3 -m pytest tests/test_answer_consistency.py tests/test_product_result_builder.py -q` (`47 passed`)
  - `python3 -m pytest tests/test_p20_realistic_acceptance.py tests/test_workspace_analysis_runner.py tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_metric_tool.py tests/test_evidence_tool.py -q` (`108 passed`)
  - `python3 -m pytest tests/test_p20_live_deepseek_acceptance.py tests/test_p12_live_deepseek_workspace_report.py tests/test_p11_live_deepseek_workspace_analysis.py -q` (`4 passed in 210.23s`, real DeepSeek opt-in)
  - `python3 -m pytest` (`539 passed, 12 skipped`)
  - `cd frontend && npm test` (`68 passed`)
  - `cd frontend && npm run build` passed
  - `git diff --check` passed

## Live DeepSeek Requirement

P24 cannot close on no-key mode alone. Before closeout, run real provider acceptance with a local environment similar to:

```bash
set -a
source .env
set +a
export INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1
export INSIGHTFLOW_PRODUCT_LIVE_MODE=1
export INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1
export INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1
export INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1
export INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1
export INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER=1
python3 -m pytest tests/test_p20_live_deepseek_acceptance.py tests/test_p12_live_deepseek_workspace_report.py tests/test_p11_live_deepseek_workspace_analysis.py -q
```

Do not print API keys. If the environment does not contain a live key, record that explicitly and do not claim live-provider behavior was tested.

## Verification Ladder

Use focused tests first, then regression:

```bash
python3 -m pytest tests/test_metric_tool.py tests/test_evidence_tool.py tests/test_workspace_analysis_runner.py tests/test_report_planner_evidence.py tests/test_report_composer_validator.py -q
python3 -m pytest tests/test_p20_realistic_acceptance.py -q
python3 -m pytest
cd frontend && npm test
cd frontend && npm run build
```

Then run live DeepSeek acceptance with the explicit opt-in flags above.

## Handoff After P24

If P24 closes cleanly, the next phase can return to real business tool calling and exports. At that point, external chart/document/report export tools should consume trusted evidence ledgers and artifact records instead of re-querying data or asking the model to recalculate facts.
