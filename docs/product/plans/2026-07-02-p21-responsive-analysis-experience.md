# P21 Responsive Analysis Experience Implementation Plan

**Date:** 2026-07-02

**Status:** Complete; P21-H1 through P21-H6 complete

**Product Direction:** P21 makes the P20 Chinese-first general analysis foundation feel faster, clearer, and more recoverable in real use. The goal is not to weaken the evidence chain or replace the multi-agent/tool-calling architecture. The goal is to avoid sending every question through the full heavy path, return simple factual answers sooner, and show users what the system is doing.

**Architecture Principle:** Route conservatively. Fast paths are allowed only for low-risk factual questions. Advice, budget, diagnosis, causal explanation, multi-metric tradeoff, and report-generation questions continue to use the full P20 evidence-backed analysis path.

## Why P21 Exists

P20 made InsightFlow capable of general Chinese business analysis across different uploaded datasets. Real product usage still needs a better response experience:

- simple factual questions should not wait for the entire deep-answer/report-style chain;
- users should see progress instead of an opaque loading state;
- switching pages or refreshing should not hide active or completed work;
- repeated questions in the same data version should be reusable;
- model context should be focused without removing evidence needed for quality.

P21 should improve perceived and actual responsiveness while preserving P20's clean separation of factual tools, model judgment, validation, and final Chinese expression.

## P21 Non-Goals

P21 does not include:

- provider timeout or automatic provider fallback work;
- Redis, Celery, distributed queues, WebSocket, or SSE;
- vector similarity search or semantic cache retrieval;
- aggressive fast-path routing;
- real external SaaS integrations;
- auth/RBAC, deployment, or scheduled reports;
- restoring old Streamlit, eval, fixed-template, chart-agent, action-workflow, mock SaaS, or demo-specific paths.

Old code, tests, docs, or routes that conflict with the current FastAPI/Next.js workspace product direction should be deleted instead of preserved. P21 should keep only useful current-product behavior. Do not keep dead modules, unused adapters, stale tests, duplicate routes, historical compatibility branches, or "just in case" fallback code when they make the project harder to understand.

## Product Target After P21

After P21, InsightFlow should:

- classify each analysis request into a conservative route;
- answer simple factual questions through a shorter path;
- keep complex questions on the full P20 evidence-backed path;
- show clear business-friendly run progress;
- keep compact task cards for active/history runs;
- allow users to reuse exact historical results from the same data version;
- restore run state after page switches or refreshes;
- use lightweight context packs for fast factual answers without starving complex answers of evidence.

## Route Types

P21 introduces a run route object:

```json
{
  "route": "fast_fact",
  "reason": "单指标、明确时间范围、事实型排名问题",
  "confidence": "high",
  "requires_full_chain": false,
  "fast_path_eligible": true,
  "disqualifiers": []
}
```

Allowed routes:

- `clarify`: missing required metric, dimension, time range, or other task slot.
- `fast_fact`: low-risk factual lookup, ranking, summary, or simple trend.
- `standard_analysis`: normal analysis, comparison, explanation, and chart-supported findings.
- `deep_judgment`: recommendation, budget, prioritization, diagnosis, cause analysis, or multi-metric tradeoff.
- `report`: management report or multi-section report generation.

Fast path eligibility must be conservative. A question can use `fast_fact` only when all of these are true:

- task slots are complete;
- the task is factual, ranking, summary, or simple trend;
- the metric/dimension/time range are clear;
- the question does not ask for advice, strategy, budget, root cause, diagnosis,复盘优先级, or report generation;
- the question does not require multi-metric tradeoff judgment;
- evidence can be produced by the existing guarded SQL/tool path.

Disqualifiers for `fast_fact` include:

- 为什么 / 原因 / 诊断;
- 应该 / 建议 / 推荐 / 优先级 / 复盘;
- 加预算 / 减预算 / 投放策略;
- 生成报告 / 管理层汇报 / 复盘报告;
- multi-metric "综合看";
- insufficient slots or unsafe requests.

## P21-H1: Conservative Route Policy

Goal: Add a clear routing decision layer without rewriting the P20 analysis chain.

Implementation shape:

- Add a small route-policy module that consumes P20 `analysis_task`, missing slots, risk flags, and user question.
- Produce `analysis_route` for each run.
- Store the route object in run state and run detail.
- Do not execute a new fast path yet.
- Do not introduce keyword-heavy business rule trees. Use generic signals from `analysis_task`: task type, metric count, dimension count, missing slots, report intent, advice/judgment intent, and confidence.

Acceptance:

- "最近90天销售额最高的门店是谁？" routes to `fast_fact`.
- "最近30天各渠道收入排名" routes to `fast_fact`.
- "本月订单量趋势怎么样？" routes to `fast_fact`.
- "哪个门店最值得复盘，为什么？" routes to `deep_judgment`.
- "哪个渠道应该加预算？" routes to `deep_judgment`.
- "生成一份管理层报告" routes to `report`.
- "销售额、毛利率、满意度综合看哪个门店最好？" does not route to `fast_fact`.
- route metadata is visible in run detail, but internal prompt/provider metadata is not shown in the main business UI.

P21-H1 completion note on 2026-07-02:

- Added `question_understanding.route_policy.classify_analysis_route()` as a small conservative routing policy over the existing P20 `analysis_task`, missing slots, risk flags, decision goal, confidence, and generic question intent signals.
- Route output now uses the stable `analysis_route` shape: `route`, `reason`, `confidence`, `requires_full_chain`, `fast_path_eligible`, and `disqualifiers`.
- Every analysis run now carries `analysis_route` in workflow state, persisted run result, restored run detail, and `product_result`.
- `fast_fact` is currently metadata only. It does not short-circuit SQL planning, evidence validation, answer composition, visualization, or the rest of the P20 chain; H2 will implement the actual shorter path.
- Fast fact routing is conservative: complete low-risk factual single-metric totals, ranking, and simple trend questions can be marked `fast_fact`; report, why/cause, diagnosis, recommendation, budget, review, prioritization, and multi-metric tradeoff questions are disqualified from `fast_fact`.
- Overall single-metric total questions and trend questions no longer require a dimension slot, so questions such as “最近90天总销售额是多少？” and “本月订单量趋势怎么样？” can be routed as low-risk factual requests.
- Added route policy unit coverage and workspace/product result integration coverage proving route metadata is persisted and restored without changing the P20 business answer, evidence, chart, and technical-details structure.
- Verification passed: route/workspace/product focused tests, question-understanding/provider focused tests, cleanup boundary regression, P20 realistic acceptance, and full backend regression `python3 -m pytest` (`444 passed, 13 skipped`). Legacy audit found matches only in historical notes, cleanup/boundary tests, and negative mock-tool tests.

## P21-H2: Fast Fact Path

Goal: Let simple factual questions return faster by skipping heavy judgment/report steps.

Fast fact chain:

```text
question understanding
-> route policy
-> SQL planning / guarded SQL candidate
-> SQL validation
-> SQL execution
-> evidence payload
-> fast fact composer
```

The path should reuse P20 SQL planning, guarded SQL generation, validation, execution, metric registry, and evidence payload. It must not create a second SQL system.

Skip or defer for `fast_fact`:

- deep insight drafting;
- answer reviewer;
- final answer composer;
- report writer;
- non-essential chart generation;
- recommendations and action plans.

Fast fact output should be concise Chinese business text:

```text
最近90天销售额最高的是「上海静安店」，销售额为 128.6 万元。
对比范围：共统计 12 家门店。
数据限制：结论基于当前已导入数据。
```

Acceptance:

- fact answers are short, readable, and not parameter dumps;
- evidence rows, metric labels, dimension labels, time scope, formulas, caveats, and technical SQL remain available in technical details;
- fact-only answers do not invent recommendations;
- fast path still uses SQL safety and evidence validation.

P21-H2 completion note on 2026-07-02:

- Added `workspaces.fast_fact_composer` to produce concise Chinese P16 `business_answer` objects for fast factual totals, rankings, and simple trends.
- Added a `fast_fact` workflow node after SQL execution. It builds evidence claims, runs the existing evidence validator, composes the fast fact answer, and then skips the heavy insight/reviewer/final composer/claim typing path.
- The path still uses the current question understanding, conservative `analysis_route`, SQL planning/generation path, SQL reviewer, SQL execution, evidence validation, fact payload generation, chart artifact generation, trace saving, and workspace run persistence.
- Fast fact answers keep `recommendations` empty, avoid raw SQL/raw rows/`execution_result`/`fact_payload` dumps in main copy, and preserve SQL, raw rows, and `fact_payload` under `technical_details`.
- Ranking answers include the first-ranked entity, metric value, and comparison scope; trend answers summarize factual movement and generate no advice.
- Complex questions with why/原因/复盘, budget/advice intent, report intent, or multi-metric综合判断 continue through the full P20 chain.
- Focused H2 tests and full backend regression passed: `python3 -m pytest` (`449 passed, 13 skipped`).

## P21-H3: Business-Friendly Progress Steps

Goal: Replace opaque loading with a clear progress timeline.

Run progress shape:

```json
[
  {
    "key": "understanding",
    "label": "理解问题",
    "status": "completed",
    "summary": "已识别指标、维度和时间范围"
  },
  {
    "key": "routing",
    "label": "选择分析路径",
    "status": "completed",
    "summary": "本次问题走快速事实路径"
  },
  {
    "key": "querying",
    "label": "查询数据",
    "status": "running",
    "summary": "正在查询并安全审核数据"
  }
]
```

Allowed statuses:

- `pending`
- `running`
- `completed`
- `failed`
- `skipped`

Progress labels should be business-friendly:

- 理解问题
- 选择分析路径
- 查询数据
- 验证证据
- 整理结论
- 生成图表
- 生成报告

Do not show raw trace IDs, prompt IDs, provider metadata, raw SQL, or raw execution rows in the main progress UI. Technical details can remain collapsed.

Acceptance:

- run result includes `progress_steps`;
- `fast_fact`, `standard_analysis`, `deep_judgment`, and `report` can show different step sets;
- frontend Analysis Workbench displays a compact progress timeline;
- restored history runs keep their progress steps.

P21-H3 completion note on 2026-07-02:

- Added centralized `workspaces.progress_steps.build_progress_steps()` and exposed `progress_steps` from analysis `product_result`.
- Progress steps use the stable fields `key`, `label`, `status`, and `summary`, with statuses limited to `pending`, `running`, `completed`, `failed`, and `skipped`.
- `fast_fact` uses 理解问题 / 选择分析路径 / 查询数据 / 验证证据 / 整理结论 / 生成图表, with chart generation skipped and explained as “事实快答不生成图表”.
- `standard_analysis` and `deep_judgment` keep the full analysis progress set, with deep judgment showing 业务判断 before chart progress; `report` uses 理解问题 / 查询数据 / 整理章节 / 生成报告.
- `clarify` and failed runs stop at the correct waiting or failure point; later steps remain pending or skipped instead of pretending to be complete.
- History detail persists and restores progress steps. Older valid P16 history product results keep their stored business answer and only backfill progress steps when missing.
- Added a compact Chinese `AnalysisProgressTimeline` in the Analysis Workbench near the analysis thread and business conclusion. The main UI does not display raw SQL, trace IDs, prompt/provider metadata, or raw rows through progress.
- Verification passed: focused backend progress/fast-fact/workspace tests, frontend API/workspace-flow Vitest, focused history regression, and full backend regression `python3 -m pytest` (`452 passed, 13 skipped`).

## P21-H4: Exact Historical Reuse And Data Version

Goal: Avoid rerunning the same completed question against the same workspace data version.

First version should be exact-match only:

```text
workspace_id + data_version + normalized_question
```

Do not use vector search or similar-question matching in P21.

Data version:

- each workspace has a `data_version`;
- importing or changing data increments the version;
- runs store the data version they were created against;
- cached/reused results are valid only when the current workspace data version matches the run data version.

Question normalization:

- trim whitespace;
- normalize simple punctuation;
- normalize repeated spaces;
- do not rewrite business meaning with a heavy rule tree or LLM.

Product behavior:

If a matching completed run exists, the API can return:

```json
{
  "status": "cache_candidate",
  "matched_run_id": "run_123",
  "message": "已找到同一数据版本下的历史分析"
}
```

The frontend should let users choose:

- 查看历史结果
- 重新分析

Cache checks must not call DeepSeek. Cache failure or timeout should not block analysis.

Acceptance:

- identical questions in the same data version can show a reuse prompt;
- changed data versions do not reuse old runs;
- users can explicitly rerun;
- generated artifacts are reused only as part of the matched run;
- no vector database or semantic cache is introduced.

P21-H4 completion note on 2026-07-02:

- Added simple integer workspace `data_version`, initialized at `1` and incremented by CSV, Excel, and SQLite imports.
- Analysis runs persist `data_version` and lightweight `normalized_question`; product technical details include those fields while the main business answer UI stays focused on conclusions, evidence, and charts.
- Exact reuse checks use only `workspace_id + data_version + normalized_question` and only return completed runs. Failed, waiting, running, and old-data-version runs are ignored.
- Question normalization is deliberately small: trim, repeated-whitespace collapse, Unicode width normalization, and common Chinese/English punctuation normalization. It does not call an LLM, use similarity matching, vector search, semantic cache retrieval, or a keyword-heavy rule tree.
- `POST /api/workspaces/{workspace_id}/runs` can return `status: "cache_candidate"` with `matched_run_id` and the Chinese message “已找到同一数据版本下的历史分析” before the workflow starts; cache-check failures fall back to normal analysis.
- `force_reanalysis: true` bypasses reuse and creates a real new run.
- Analysis Workbench shows “查看历史结果” and “重新分析”. Viewing loads the matched run detail; rerunning submits a new request with `force_reanalysis`.
- Focused verification passed: backend P21-H4/workspace store/import/history set (`37 passed`) and frontend API/workspace-flow Vitest (`60 passed`).

## P21-H5: Background Work And Page Recovery

Goal: Make analysis recoverable when users switch pages, refresh, or wait for slower artifacts.

First version should use lightweight local backend behavior, not Redis/Celery:

```text
POST /runs
-> create run_id with queued/running status
-> execute analysis
-> frontend polls GET /runs/{run_id}
-> completed/failed/waiting state is restored from backend history
```

Allowed run statuses:

- `queued`
- `running`
- `waiting_for_clarification`
- `completed`
- `failed`

Task cards must stay compact. They are status entry points, not full result panels.

Card content examples:

```text
问题：最近90天销售额最高的门店是谁？
状态：正在分析
进度：正在查询数据
```

```text
问题：最近90天销售额最高的门店是谁？
状态：已完成
摘要：上海静安店销售额最高，为 128.6 万元
```

Frontend card rules:

- fixed/controlled height;
- long questions clamp to one or two lines with ellipsis;
- do not show complete answers, SQL, evidence tables, charts, or raw details inside cards;
- clicking a card opens or restores full run detail;
- waiting, running, failed, and completed states have short Chinese labels.

Acceptance:

- submitting a run quickly returns a run id or visible task card;
- switching away and back restores active/completed/failed/waiting runs;
- task cards remain compact and readable;
- background chart/report failures do not hide an already available core answer.

P21-H5 completion note on 2026-07-02:

- Added a lightweight local run shell/job layer around the existing workspace analysis runner. New non-cached requests persist a `running` shell with `run_id`, `workspace_id`, `original_question`, `data_version`, `normalized_question`, and compact `progress_steps`, then the existing analysis workflow updates the same run id to `completed`, `failed`, or `waiting_for_clarification`.
- FastAPI keeps H4 exact historical reuse first: same-version same-normalized-question completed runs still return `status: "cache_candidate"` and do not create a background run unless the user explicitly sends `force_reanalysis`.
- `GET /api/workspaces/{workspace_id}/runs/{run_id}` and the run history list restore running, waiting, completed, and failed run files. The implementation is local and intentionally avoids Redis, Celery, WebSocket, SSE, provider timeout handling, vector databases, and external SaaS.
- Analysis Workbench stores the active run id in `sessionStorage`, restores it after remount/refresh, polls run detail until the status becomes waiting/completed/failed, and clears the active marker after terminal states.
- Running/queued analysis shows a compact task card with only the question, Chinese status, and current progress. Long questions clamp to two lines, and the card does not render full answers, raw SQL, evidence tables, charts, traces, provider metadata, or other technical details.
- Completed, waiting, and failed runs still render the full P16 `RunResult` when opened. The H4 reuse prompt keeps “查看历史结果 / 重新分析”, and explicit rerun submits `force_reanalysis`.
- Verification passed: `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_run_history_api.py -q` (`35 passed`), full backend `python3 -m pytest` (`462 passed, 13 skipped`), focused frontend `cd frontend && npm test -- --run tests/api-client.test.ts tests/workspace-flow.test.tsx` (`64 passed`), and frontend production build `cd frontend && npm run build`.

## P21-H6: Lightweight Context Packs

Goal: Reduce unnecessary model context without hurting answer quality.

Use a `context_pack_builder` concept:

```text
route + analysis_task + evidence_payload -> context pack
```

The structure is fixed, but business content is dynamic.

Fast fact context pack should include:

- user question;
- route;
- task type;
- metric labels;
- dimension labels;
- time range;
- key evidence rows;
- formulas/units;
- caveats/data limits.

Fast fact context pack should not include:

- full workspace profile;
- all table fields;
- full trace;
- provider metadata;
- historical runs;
- unrelated raw rows;
- report chapters.

For P21, strict context reduction applies only to `fast_fact`. `standard_analysis`, `deep_judgment`, and `report` should stay conservative and keep enough evidence for quality.

Acceptance:

- fast fact answer generation uses a compact context pack;
- complex routes do not lose required evidence;
- tests prove key numbers, rankings, labels, and units are still present after context packing;
- no business-specific hardcoded templates are introduced.

P21-H6 completion note on 2026-07-02:

- Added `workspaces.context_pack_builder.build_fast_fact_context_pack()` as a fixed-shape, dynamic-content context pack for the fast fact path only.
- The pack keeps `user_question`, route, task type, metric ids/labels/units/formulas, dimension ids/labels, time range, comparison scope, top evidence rows, display values, caveats, warnings, data limits, and evidence validation status.
- The pack deliberately excludes raw SQL, trace, provider metadata, full workspace profile, full semantic layer, prompt text, historical runs, unrelated report sections, and full raw rows. Existing `technical_details.sql`, `technical_details.raw_rows`, and `fact_payload.technical_sql` remain available outside the compact pack for debugging.
- `fast_fact_node` builds and persists `fast_fact_context_pack`; `fast_fact_composer` now prefers the pack and falls back to minimal execution/evidence inputs when the pack is missing or empty.
- `technical_details.fast_fact_context_pack` exposes the pack for fast fact debugging and tests. `standard_analysis`, `deep_judgment`, and `report` are not forced into the fast fact pack and keep enough context for answer quality.
- Added/updated tests covering ranking pack evidence retention, trend points/time range retention, noise exclusion, Chinese answer generation from the pack, technical-details exposure, persistence, and non-fast-route protection. Focused backend verification passed with `53 passed`.

## Suggested Implementation Order

1. H1: route object and conservative route policy.
2. H2: fast fact execution and composer.
3. H3: progress steps and frontend timeline.
4. H4: exact historical reuse with data version.
5. H5: page recovery and compact task cards.
6. H6: fast fact context pack cleanup and verification.

This order keeps the work incremental. H1 defines the contract. H2 uses it. H3 makes the product explain itself. H4 and H5 reduce repeated work and broken waiting experiences. H6 trims model context only after the routes and outputs are stable.

## Testing Requirements

Use TDD for each H task.

Required coverage:

- route policy unit tests for all route types and disqualifiers;
- fast fact backend tests for factual, ranking, and trend questions;
- no-fast-path tests for why/advice/budget/report/multi-metric judgment questions;
- evidence and SQL safety regression for fast fact;
- frontend tests for progress timeline and compact task cards;
- history reuse tests with same data version and changed data version;
- page recovery tests for running/completed/failed/waiting states;
- context pack tests proving essential evidence is retained.

Live DeepSeek tests remain opt-in and should not run by default. If local flags and `DEEPSEEK_API_KEY` are configured, run a focused live acceptance for at least one fast factual question and one deep judgment question to prove routing chooses different paths.

## Cleanup And Artifact Hygiene

P21 must keep the project clean:

- delete obsolete code or tests that conflict with the current product direction;
- do not keep old compatibility branches only for historical behavior;
- do not preserve code only because an old test expects it; update or delete the obsolete test instead;
- remove unused helpers, duplicate routes, inactive adapters, stale prompts, dead imports, and unreachable fallback branches when discovered during P21 work;
- prefer one clear current product path over parallel old/new implementations;
- do not restore old Streamlit, eval, chart-agent, action-workflow, mock SaaS, fixed-template, or keyword-heavy rule paths;
- do not commit generated workspaces, databases, reports, charts, traces, `.env`, `.next`, caches, or local sample outputs.

Before P21 closeout, run the standard cleanup audit:

```bash
rg -n "chart_agent|visualization_planner|chart_tool|action_delivery|action_drafter|powerbi_publisher_mock|jira_ticket_mock|fixed template|deterministic action template|keyword inference|streamlit|eval/run_eval"
```

Matches are acceptable only in historical/superseded notes, cleanup plans, or tests that assert old paths are deleted/rejected.

## Completion Definition

P21 is complete when InsightFlow can truthfully be described as:

> A Chinese-first general business data-analysis product that routes each question conservatively, answers simple factual questions through a shorter evidence-backed path, keeps complex questions on the full multi-agent analysis path, shows clear progress, restores active/history runs after page changes, and reuses exact same-version analysis safely without sacrificing evidence quality.
