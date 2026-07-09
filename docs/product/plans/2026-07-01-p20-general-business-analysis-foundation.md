# P20 General Business Analysis Foundation Implementation Plan

Historical / Superseded note: this phase record predates P33-H2. Any references to `agents/final_answer_composer.py` are historical; P33-H2 deleted that module from the active Analysis Workbench path.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor InsightFlow from a channel-marketing demo-shaped product into a clean, general business data analysis multi-agent foundation that can work with different uploaded business datasets.

**Architecture:** P20 separates the analysis/report path into four explicit layers: factual tool output, model judgment, fact validation, and user-facing expression. Agents may understand, plan, interpret, and write; tools own profiling, metric calculation, SQL execution, evidence tables, chart artifacts, report artifacts, and persistence. Old paths, compatibility code, fixed templates, table-specific business rules, and mock/demo leftovers that conflict with this direction should be deleted instead of preserved.

**Tech Stack:** FastAPI, Python workspace services, LangGraph product workflow, DeepSeek provider path, SQLite-backed workspace analysis, Next.js App Router, React, TypeScript, pytest, Vitest, opt-in live DeepSeek acceptance.

---

## Why P20 Exists

Real P19 product testing exposed a structural issue: the system can often query correct data, but over-rigid safety, consistency, and evidence checks can still turn useful evidence into "insufficient evidence" answers. P20 should not add more narrow patches for individual questions. It should reorganize the answer/report chain so evidence, judgment, validation, and expression each have a clear responsibility.

P20 must remain a general business analysis product direction. The current Chinese marketing-channel dataset is only an acceptance fixture, not a schema to hardcode.

## P20 Language Scope: Chinese Business Product

P20 is now scoped as a Chinese-first business product. Product-facing UI copy, clarifying questions, analysis answers, chart annotations, report sections, Markdown exports, and provider prompts should default to Chinese business language.

English is still supported as raw data reality, not as a product output mode. Many real Chinese business files use English or mixed headers such as `sales_amount`, `store_name`, `customer_id`, `Sales Amount`, or `Score (NPS)`. The semantic layer must recognize these raw fields and map them into Chinese business labels and aliases such as 销售额、门店、客户、满意度. Do not require uploaded datasets to use Chinese column names only.

Do not preserve bilingual output branches as a P20 product requirement. Historical P19 English-answer/report behavior is superseded for the current product direction and can be deleted when it complicates the main path. Multilingual output can be reconsidered in a later phase after the Chinese business analysis chain is stable.

## Product Target After P20

Users should be able to import different business datasets and ask questions such as:

- "最近 90 天哪个渠道最值得加预算？"
- "本季度哪些产品利润率最低？"
- "哪个客户群复购表现最好？"
- "最近 30 天销售趋势有没有异常？"
- "帮我生成一份管理层经营分析报告。"

The product should:

1. Profile the current workspace data.
2. Build a business-readable semantic layer from the actual uploaded fields.
3. Convert user questions into a general analysis task contract.
4. Ask concise follow-up questions when required slots are missing.
5. Use tools to query and calculate facts.
6. Let the model explain and recommend within the evidence boundary.
7. Validate factual claims without blocking reasonable evidence-backed business judgment.
8. Generate natural Chinese business answers and management-style Chinese reports.

## Non-Negotiable Cleanup Policy

P20 is allowed to remove code, tests, docs, and paths that no longer serve the target product. Do not keep old code only for historical compatibility.

Delete or replace:

- old fixed answer templates that force "insufficient evidence" when evidence exists;
- table-specific rules tied to `orders`, `channel`, `marketing_spend`, or ROI-only channel analysis;
- keyword-heavy business decision trees;
- old mock/demo/eval/action/chart-agent compatibility paths;
- obsolete tests that only assert old template wording;
- duplicate report/answer paths that generate separate unsupported conclusions;
- generated artifacts, workspace runs, report outputs, traces, build output, `.env`, and sample runtime files.

Keep or strengthen:

- current FastAPI workspace APIs;
- Next.js product pages;
- workspace import/profile/semantic-layer flow;
- SQL validation, SQL execution, schema repair, evidence, visualization, report, and trace tool boundaries;
- opt-in real DeepSeek acceptance;
- tests that protect the current product and multi-agent/tool-calling boundaries.

## Generalization Rules

P20 must not hardcode the current dataset.

Do not write active logic that assumes:

- `orders` must exist;
- `marketing_spend` must exist;
- `channel` must exist;
- `revenue` must exist;
- ROI is always available;
- "budget recommendation" is the only recommendation scenario;
- Chinese marketing-channel sample data is the product schema.

Instead, active logic should reason in terms of:

- tables;
- dimensions;
- metrics;
- time fields;
- filters;
- comparison objects;
- metric formulas;
- decision goals;
- missing slots;
- evidence rows;
- chart intents;
- report sections.

## Target Runtime Chain

```text
workspace import
-> data profiler
-> semantic layer
-> task router / clarification
-> fact planner
-> metric registry
-> SQL / calculation tools
-> evidence payload
-> insight writer
-> fact validator
-> answer writer or report writer
-> chart/report/export tools
-> Next.js product UI
```

## P20 Task Plan

### P20-H0: Architecture Cleanup And Main Path Inventory

Goal: Make the current product chain understandable before adding new behavior.

Files to inspect first:

- `README.md`
- `DEVELOPMENT_PLAN.md`
- `DEVELOPMENT_STATUS.md`
- `api/app.py`
- `workspaces/analysis_runner.py`
- `workspaces/report_runner.py`
- `workspaces/product_result_builder.py`
- `workspaces/answer_consistency.py`
- `agents/final_answer_composer.py`
- `agents/answer_reviewer.py`
- `tools/evidence_tool.py`
- `agents/schema_repair.py`
- `question_understanding/`
- `sql_planning/`
- `semantic_layer/`
- `frontend/app/workspaces/`
- `frontend/components/`
- current relevant tests under `tests/` and `frontend/tests/`

- [x] Add or update boundary tests that fail if active product imports old demo/action/mock/chart-agent/eval paths.
- [x] Identify duplicate answer/report composition paths and choose one current path.
- [x] Delete obsolete compatibility code that conflicts with P20, instead of preserving old behavior.
- [x] Remove or rewrite tests that only assert old fixed template output.
- [x] Keep the product runnable after cleanup: upload data, generate profile/semantic layer, ask a question, restore history, generate a basic report.
- [x] Record exact removed paths and verification results in `DEVELOPMENT_STATUS.md`.

Acceptance:

- The current main analysis/report path is clear in docs and code.
- No old chart-agent, action workflow, mock SaaS, Streamlit, old eval, fixed-template, deterministic action template, or keyword-inference path is active.
- The project still clearly demonstrates multi-agent and tool-calling boundaries.

P20-H0 completion note on 2026-07-01:

- Added `tests/test_p20_architecture_cleanup_boundaries.py` to inventory and protect the current chain: FastAPI workspace API, analysis/report runners, LangGraph nodes, SQL review/schema repair/execution, evidence validation, reviewer/composer, visualization/report, trace, and Next.js product rendering.
- Updated stale P17 cleanup-boundary assertions that still described P19 and the old P20 responsiveness scope.
- Removed the obsolete trace-driven SQL template-mining/eval helper path: `sql_planning.feedback`, the `template_mining_event` trace payload in `agents/guarded_llm_enhancer.py`, and `tests/test_llm_template_mining_eval_suite.py`.
- Preserved useful provider structured-output smoke validation by moving it to `tests/test_llm_smoke_eval.py`.
- Remaining report presets and deterministic SQL templates are treated as current guarded compatibility/fallback paths for P20-H0 only; replacing them with generalized profiling, semantic-layer, and task-contract behavior is explicitly deferred to P20-H1 through P20-H4.
- Verification passed: `python3 -m pytest tests/test_p17_product_cleanup_boundaries.py tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py -q`, `python3 -m pytest tests/test_project_initialization.py tests/test_mcp_tool_layer.py -q` (`9 passed`), `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py tests/test_business_answer_quality.py -q` (`60 passed`), `python3 -m pytest -q` (`391 passed, 13 skipped`), `cd frontend && npm test -- workspace-flow.test.tsx` (`49 passed`), `cd frontend && npm test` (`62 passed`), and `cd frontend && npm run build` passed. P20 cleanup later removed the duplicated P11 cleanup-boundary test file.

### P20-H1: General Data Profiling And Semantic Layer

Goal: Make imported data self-describing so later agents do not rely on table-specific assumptions.

Expected capabilities:

- Identify table names and columns from current workspace data.
- Infer field roles: time, numeric metric, categorical dimension, identifier, text, status, amount, count, cost, revenue-like, rating-like.
- Infer safe Chinese business labels and aliases from actual column names and headers, including Chinese, English, and mixed raw fields.
- Store a workspace-level semantic layer that can be read by question understanding, SQL planning, schema repair, answer writing, report writing, and frontend settings.

- [x] Add failing tests using at least two different fixture shapes: the Chinese channel sample and one non-channel business dataset.
- [x] Implement profile/semantic output that describes dimensions, metrics, time fields, and candidate relationships without hardcoding current table names.
- [x] Fix semantic-layer reading so YAML and JSON are both handled where current code expects semantic context.
- [x] Ensure schema repair uses the same semantic context as SQL planning.
- [x] Update Data Settings UI only if required to show the generalized semantic layer clearly.

Acceptance:

- A new workspace can expose available dimensions, metrics, and time fields regardless of whether it contains channel/marketing data.
- Schema repair must not fall back to old ecommerce tables when the current workspace has a valid semantic layer.

P20-H1 completion note on 2026-07-01:

- Added RED coverage for Unicode CSV headers, Chinese store-operation fields, non-channel store/inventory semantic drafts, Chinese relationship candidates, workspace YAML/JSON semantic loading, workspace metric lookup, settings loading, and schema repair semantic hints.
- Workspace profiling now emits generalized field metadata: table/column names, original SQL type, inferred type, `field_role`, business-meaning candidates such as `revenue_like`, `cost_like`, `amount_like`, `count_like`, `rating_like`, and `date_like`, plus group-by and aggregation suitability.
- Semantic drafts now derive `tables`, `metrics`, `dimensions`, `time_fields`, `entities`, `field_roles`, `semantic_aliases`, `relationships`, and `available_analysis_capabilities` from the actual workspace profile. They support Chinese field names and English snake_case fields, and do not invent missing `channel` or `revenue` metrics.
- Added `load_workspace_semantic_layer()` as a shared single-file YAML/JSON reader and wired it into settings summary, workspace context summary, metric lookup, and schema repair; schema repair no longer emits the old JSON-only semantic-layer read error for YAML workspaces.
- Data Settings received only a small role-label update for the generalized profile roles.
- Verification passed: profiler/semantic focused `15 passed`, schema/metric/settings/P20 focused `17 passed`, workspace analysis/product-result regression `27 passed`, and combined P20-H1 backend set `36 passed`.

P20-H1 repair requirement after Chinese-scope decision on 2026-07-02:

- Generated metric formulas must quote SQL identifiers safely, including table names and columns with spaces, parentheses, punctuation, or Chinese characters. For example, prefer `SUM("store_ops"."Sales Amount")` over `SUM(store_ops.Sales Amount)`.
- English or mixed raw fields must receive Chinese business aliases from `business_meaning_candidates`, so questions like "按门店看销售额" can match fields such as `Sales Amount`, `sales_amount`, or `revenue`.
- Product-facing semantic labels should prefer Chinese business terms when the field meaning is known; raw English names remain available as technical aliases, not main answer wording.
- H1 is not considered ready for H2 until these formula-safety and Chinese-alias regressions pass.

P20-H1 repair completion note on 2026-07-02:

- Added RED coverage for mixed English headers (`Store Name`, `Sales Amount`, `Cost Amount`, `Score (NPS)`, `Order Date`) and Chinese semantic questions over those fields.
- Generated metric formulas now use quoted SQLite identifiers, for example `SUM("store_ops"."Sales Amount")`, `SUM("store_ops"."Cost Amount")`, and `AVG("store_ops"."Score (NPS)")`.
- Semantic aliases and labels now prefer Chinese business language when field meaning is known: 销售额/收入/营收, 成本/费用/支出, 满意度/评分/得分, 门店/店铺, while preserving raw field names as technical aliases.
- Workspace metric lookup now matches Chinese questions such as "按门店看销售额", "按门店看成本", and "按门店看满意度" to English/mixed raw headers without inventing channel, orders, or ROI fields.
- Verification passed: semantic/metric/P20 repair `14 passed`, profiler/semantic/settings `16 passed`, workspace analysis/product-result `27 passed`, P17/P20 boundary checks `18 passed`, and full backend regression `403 passed, 13 skipped`.

### P20-H2: General Analysis Task Contract And Clarification

Goal: Convert user questions into a reusable task contract before SQL or answer generation.

Target contract:

```json
{
  "task_type": "compare | rank | trend | summary | anomaly | recommendation | report | clarification",
  "dimensions": [],
  "metrics": [],
  "time_range": null,
  "filters": [],
  "decision_goal": null,
  "missing_slots": [],
  "output_language": "zh"
}
```

- [x] Add tests for complete questions, incomplete questions, follow-up answers, and ambiguous metric/time requests.
- [x] Track missing slots individually; do not continue analysis until required slots are filled or an explicit default is applied.
- [x] If a default is used, write it into the resolved question and final answer caveats.
- [x] Treat budget, optimization, and recommendation questions as normal analytical tasks, not unsafe requests, unless they ask for actual external execution or sensitive access.
- [x] Keep product-facing answers, clarifying questions, chart annotations, and reports in Chinese. Raw English field names may appear only in technical details or when no Chinese semantic label can be inferred.

Acceptance:

- A partial follow-up such as "花费" does not silently proceed if time range is still required.
- "加预算", "减少预算", "优化产品", and "关注异常门店" are recommendation tasks, not blanket rejections.

P20-H2 completion note on 2026-07-02:

- Added `question_understanding/task_contract.py` as the shared normalization point for deterministic and provider-backed question understanding. It emits `task_type`, Chinese metrics/dimensions, `time_range`, filters, decision goal, missing slots, defaults, resolved question, fixed `output_language: "zh"`, and confidence.
- Deterministic question understanding now recognizes complete Chinese business tasks such as “最近90天按门店比较销售额”, incomplete recommendation tasks such as “帮我分析渠道表现，看看哪个渠道该加预算”, and English/mixed raw headers through workspace semantic aliases such as `Sales Amount` -> 销售额 and `Store Name` -> 门店.
- Clarification routing now asks concise Chinese slot-level follow-ups. Partial continuation answers such as “花费” fill only the metric and keep the pending run waiting for `time_range`; completed continuations merge the original question and supplemental answer before resuming analysis.
- Provider-backed question understanding can include optional `analysis_task`, but local normalization still applies defaults, forces Chinese output language, maps semantic aliases, and recomputes missing slots so provider output cannot bypass clarification rules.
- No P20-H3 fact layer, metric registry, evidence payload, or P20-H4 final answer/report rewrite was added in H2.
- Verification passed: question/clarification/pending focused `20 passed`, workspace/workflow focused `16 passed`, provider/structured-output focused `44 passed`, P20 semantic/metric focused `8 passed`, and full backend regression `412 passed, 13 skipped`.

### P20-H3: Fact Layer, Metric Registry, And Evidence Payload

Goal: Make facts and metric calculations stable before the model writes conclusions.

Required concepts:

- Base aggregation: sum, average, count, min, max.
- Ranking and comparison: top N, bottom N, full peer comparison when needed.
- Time analysis: date filter, trend bucket, latest available date fallback.
- Derived metrics: ratio, share, growth rate, average order value, ROAS, net return, margin-like metrics when source fields exist.
- Metric formulas must be named and included in the evidence payload.

- [x] Add tests proving ROI/ROAS/net-return formulas are not mixed.
- [x] Add tests proving "highest/best/worst/most worth" questions return enough comparison rows, not only one row.
- [x] Add tests proving evidence accepts rounded values, Chinese units, percentages, and business aliases.
- [x] Implement a metric registry that derives formulas only when required source fields exist.
- [x] Ensure SQL/tool output includes columns, rows, metric formulas, time scope, filters, comparison scope, and warnings.
- [x] Keep raw SQL and raw rows in technical details, not the main business answer.

Acceptance:

- Evidence can support "2.6 万" from `26255.44`.
- The system can distinguish ROAS from net ROI.
- A top-answer question includes enough rows to prove the comparison, not only the winner.

P20-H3 completion note on 2026-07-02:

- Added `build_metric_registry()` in `tools/metric_tool.py`. It builds a JSON-safe registry from workspace semantic metrics and keeps base formulas, units, business labels, source fields, and warnings.
- Derived metrics are generated only when source fields exist: ROAS = `revenue / spend`, net return = `(revenue - spend) / spend`, margin rate = `(revenue - cost) / revenue`, and average order value = `revenue / order_count`. Missing inputs produce warnings instead of invented ROI, ROAS, margin, or AOV.
- Metric agent state now carries `metric_registry` separately from legacy `metric_context`, so downstream prompt/tool consumers can use formulas without breaking existing matched-metric behavior.
- Added `build_evidence_payload()` in `tools/evidence_tool.py`. The payload includes task type, metrics, dimensions, time scope, filters, comparison scope, columns, rows, formulas, warnings, display/formatted values, `technical_sql`, and technical row metadata.
- Product results now expose the reusable fact payload under `evidence.fact_payload` and `technical_details.fact_payload`. Main `business_answer` remains clean of raw SQL and raw rows; those stay in technical details.
- Comparison/ranking/recommendation tasks mark peer comparison insufficient when only one row is returned. Multi-row top/best/recommendation evidence retains all returned comparison rows instead of only the winner.
- Chinese display values support business aliases and formats such as `26255.44` -> `2.6 万`, `99800` -> `10.0 万`, and percentage metrics such as `0.367` -> `36.7%`, while raw values remain in `rows`.
- Non-channel datasets are covered by store and support-ticket style tests; no active logic assumes `orders`, `marketing_spend`, `channel`, or `revenue` must exist.
- No legacy demo/mock/action/chart-agent/eval path was restored or newly deleted in H3. The legacy audit only found historical notes, cleanup/boundary tests, and tests that verify unsupported mock/tool choices are rejected.
- Verification passed: `python3 -m pytest tests/test_metric_tool.py tests/test_evidence_tool.py tests/test_evidence_validator.py tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q` (`48 passed`), `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py tests/test_answer_consistency.py -q` (`41 passed`), `python3 -m pytest tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py tests/test_mcp_tool_layer.py -q` (`12 passed`), and full backend regression `python3 -m pytest` (`414 passed, 12 skipped`).

P20-H3 task-contract metric-normalization repair on 2026-07-02:

- Fixed question-understanding normalization so ROAS, ROI, and net return remain distinct before SQL planning and fact payload construction.
- Deterministic `understand_question()` now maps “最近90天各渠道 ROAS 最高的是谁？” to `intent.metric = roas` and `analysis_task.metrics = ["ROAS"]`, while ROI stays `ROI`.
- Deterministic and provider-backed task contracts now map `net return`, `net ROI`, `net_return`, `净投放回报率`, and `净回报率` to the business metric label `净投放回报率`; these questions no longer ask for a missing metric.
- Provider-backed normalization applies the same alias table, so provider outputs cannot collapse `roas` into ROI or leave `net_return` as an unrecognized raw metric.
- P20-H3 metric-normalization repair also prevents `net ROI` / `netroi` from being double-counted as both net return and ROI.
- P20-H3 metric-normalization repair now preserves explicit multi-metric questions that ask for net return and plain ROI together.
- Existing sales, spend, order count, AOV, repurchase, satisfaction, and sales-volume metric recognition was left unchanged.
- This repair stayed inside P20-H3 task-contract / metric-semantic interfaces. It did not change P20-H4 answer/report generation behavior and did not restore old demo/eval/action/chart/mock paths.
- Verification passed: `python3 -m pytest tests/test_question_understanding_router.py tests/test_provider_backed_question_understanding.py -q` (`32 passed`), `python3 -m pytest tests/test_metric_tool.py tests/test_evidence_tool.py tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q` (`45 passed`), `python3 -m pytest tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py -q` (`8 passed`), and full backend regression `python3 -m pytest` (`419 passed, 12 skipped`).

### P20-H4: Business Insight, Answer, And Report Generation

Goal: Let the model produce useful business judgment without letting it invent facts.

Target answer behavior:

- Lead with the direct conclusion.
- Explain the key evidence in business language.
- Give practical next actions when the user asks for advice.
- Mark assumptions and risks clearly.
- Avoid fixed wording and raw field names in the main answer.
- Write product-facing output in Chinese business language; do not keep English answer/report branches as P20 acceptance requirements.
- Do not downgrade to "证据不足" when the evidence payload supports a useful answer.

Report behavior:

- Reports reuse validated evidence and insights from the analysis chain.
- Reports do not independently invent a new conclusion.
- Management reports include executive summary, key findings, evidence/chart narrative, recommendations, risks/limits, and technical appendix.

- [x] Add tests for Chinese business answers across factual, comparison, recommendation, and report tasks.
- [x] Update answer writer/composer so validation checks facts and rankings, not reasonable evidence-backed recommendations.
- [x] Remove old fixed "insufficient evidence" downgrade paths that fire when rows exist and the task is answerable.
- [x] Update report runner/writer to reuse the same evidence/insight payload.
- [x] Ensure chart selection follows task intent: ranking, trend, comparison, scatter/quadrant, or table preview.

Acceptance:

- A supported recommendation can say "建议优先小规模测试 X" with evidence and risk boundary.
- A report and the originating analysis do not contradict each other.
- Main answer language is readable to a business user, not a parameter dump.

P20-H4 completion note on 2026-07-02:

- Added regression coverage for supported recommendation answers that should not be downgraded when multi-row evidence is sufficient, fact-only questions that should not force recommendations, budget/recommendation tradeoffs across revenue/spend/ROI, Chinese-first report synthesis for English report goals, and fallback chart selection by task intent.
- Final answer composer now treats stale `downgrade_to_insufficient_evidence` reviews as rebuildable when the result rows include supported entities and metrics and no unsupported entity/metric claims. True missing rows or unsupported claims still downgrade.
- Product result building only fills recommendations when the user asks for advice, recommendation, prioritization, budget, or next action. Factual answers keep caveats without turning into action plans.
- Answer consistency now handles budget recommendation questions with multi-metric tradeoffs instead of skipping them; revenue scale, spend, ROI, ROAS, and net-return style metrics can be explained as different decision lenses without being collapsed.
- Visualization fallback now chooses ranked bar, line, or scatter based on task intent and emits Chinese business titles and annotations.
- Report synthesis is Chinese-first and continues to reuse section `business_answer`, evidence rows, chart artifacts, and technical appendix separation.
- Verification passed: answer/reviewer/composer focused `35 passed`; product result, workspace analysis/report, report cleanup, and visualization focused `60 passed`; metric/evidence/question-understanding focused `54 passed`; P17/P20/project boundary checks `21 passed`; full backend regression `430 passed, 12 skipped`.

### P20-H5: Realistic Acceptance, Cleanup, And Documentation Closeout

Goal: Prove P20 works as a general product foundation, not just with one sample dataset.

Required acceptance scenarios:

- Chinese channel/marketing dataset.
- At least one non-channel dataset, such as product sales, store operations, customer cohorts, support tickets, inventory, or finance-like data.
- Factual ranking question.
- Multi-metric comparison question.
- Recommendation question.
- Trend or anomaly question.
- Management report generation.
- Clarification continuation.

- [x] Run focused backend tests for P20 modules.
- [x] Run related frontend tests.
- [x] Run full backend regression.
- [x] Run frontend build.
- [x] Run opt-in real DeepSeek acceptance if local flags are enabled.
- [x] Re-run legacy audit:

```bash
rg -n "chart_agent|visualization_planner|chart_tool|action_delivery|action_drafter|powerbi_publisher_mock|jira_ticket_mock|fixed template|deterministic action template|keyword inference|streamlit|eval/run_eval"
```

- [x] Confirm generated files are not staged.
- [x] Update `README.md`, `DEVELOPMENT_PLAN.md`, and `DEVELOPMENT_STATUS.md` with exact results.

Acceptance:

- P20 demonstrates a clean multi-agent/tool-calling product path.
- The project remains clean: no unused old paths, no generated artifacts, no compatibility clutter for obsolete product behavior.
- Current functionality works before any P21 external business integrations begin.

P20-H5 completion note on 2026-07-02:

- Added `tests/test_p20_realistic_acceptance.py` with two non-channel Chinese business scenarios: store sales/satisfaction and support ticket operations.
- Store sales acceptance covers factual question, ranking, comparison, trend, recommendation, chart artifact, fact payload, and management-report synthesis through the current workspace product path.
- Support ticket acceptance covers team-level工单量、平均响应时长、满意度 analysis without relying on channel, orders, marketing spend, revenue, or ROI fields.
- General `business_review` report section prompts now use the current workspace schema/profile/semantic layer and no longer assume demo-specific tables or fields.
- Common service-operation labels were added for `team_name`, `ticket_count`, and `avg_response_minutes`.
- Schema-review failure guidance now points users to current workspace tables, fields, metrics, and dimensions rather than a demo-specific field set.
- Added opt-in `tests/test_p20_live_deepseek_acceptance.py` for non-channel store analysis. It verifies provider-backed question understanding and SQL planning when live flags and `DEEPSEEK_API_KEY` are configured; by default it skips. Forced local live verification with those flags passed against real DeepSeek: `1 passed`.
- Cleanup audit found old cleanup terms only in historical/superseded notes, boundary tests, negative mock-tool tests, or this plan's audit command; no active main product path imports old action/chart/mock/eval modules.
- Verification passed: question-understanding/P17/P20/project/P20 acceptance boundary set `45 passed, 1 skipped`; metric/evidence/workspace-analysis/product-result focused set `49 passed`; report/composer/visualization focused set `36 passed`; full backend regression `434 passed, 13 skipped`; frontend Vitest `62 passed`; frontend production build passed.

## Deferred Work

P20 should not focus on external SaaS publishing or speed optimization until the general analysis foundation is reliable.

Deferred:

- Real China-oriented external tool integrations.
- Background report/chart jobs.
- Fast factual route optimization.
- Multilingual product output.
- Auth/RBAC.
- Vector database.
- Deployment/CI/Docker.

These can become later phases once P20 produces stable evidence-backed answers and reports.

## P20 Completion Definition

P20 is complete when InsightFlow can truthfully be described as:

> A Chinese-first general business data analysis multi-agent platform that profiles uploaded datasets, builds a semantic layer, maps raw Chinese/English/mixed fields into Chinese business semantics, routes natural-language questions into analysis tasks, calls SQL/calculation/chart/report tools to produce evidence, validates factual claims, and writes Chinese business-readable answers and management reports.
