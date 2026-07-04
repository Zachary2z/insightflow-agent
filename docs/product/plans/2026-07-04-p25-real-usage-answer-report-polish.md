# P25 Real Usage Answer And Report Polish Plan

> Required subskill: `superpowers:writing-plans`

## Goal

P25 turns the P24 real-use findings into a cleaner, more business-ready product phase. The focus is not adding another large framework. The focus is making Analysis Workbench answers and Report Center documents feel reliable in real Chinese business usage:

- answer the user's primary question directly before explaining tradeoffs;
- keep evidence limits accurate and non-contradictory;
- avoid stale field assumptions when the uploaded dataset changes;
- let Report Center infer report intent from the user's goal instead of forcing template-like report types;
- keep code clean by deleting old paths, stale tests, and compatibility branches that no longer serve the current FastAPI/Next.js product.

P25 stays before external export/tool integrations. Word/PPT/PDF, 飞书, 钉钉, 企业微信, Tencent Docs, scheduled reports, auth/RBAC, deployment, vector search, and old demo/mock paths remain out of scope.

## Why This Phase Exists

Manual testing on workspace `p24-32cc63f6` showed that the current generic evidence chain is much stronger than earlier phases, but several real-usage issues remain:

- Some answers are not decisive enough when the user asks for one primary metric, such as “ROI 最高的是谁”.
- Some `data_limits` conflict with calculated evidence, such as showing `repeat_rate` while also saying 复购率未计算.
- Some fallback SQL paths can still reference stale fields like `order_date`, `city`, or `total_revenue` when the workspace schema does not contain them.
- Report Center can overreact to the word “渠道” inside a broad business-review goal and produce the same title for different report intents.
- The visible “报告类型” selector makes reports feel template-driven. The product should primarily use the user's report goal to infer structure.
- Manual testing after P25-H3 showed that missing time ranges are still too strict. Questions such as “哪个客户分群贡献的收入最高？” can safely use the dataset's full available time range when there is one clear time field, but the product currently asks for clarification instead.

## Target Chain

```text
user question or report goal
-> semantic-layer-backed evidence requirements
-> SQL / metric / evidence tools calculate hard facts
-> model explains, judges, and recommends within evidence boundaries
-> deterministic validation checks key facts and contradictions
-> Chinese business answer or coherent Chinese report document
```

The model should have room to write useful business explanations and recommendations. Deterministic code should verify hard facts, rankings, units, dates, and unsupported claims, not force every answer into a rigid template.

## P25-H1 Analysis Answer Decisiveness And Evidence Limits

Scope:

- Add fail-first tests for real user questions found during manual testing:
  - “最近90天哪个渠道 ROI 最高？为什么？”
  - “哪个客户分群复购率最高？”
  - “哪个商品品类成交金额最高，哪个销量最高？”
  - “帮我做一下门店经营复盘。”
- Make the answer composer respect the primary metric in the question. If the user asks ROI, the first sentence should answer ROI; revenue scale or spend can follow as context.
- Treat SQL-derived aliases and calculated metrics as supported evidence when they are produced by the current run.
- Rewrite evidence-limit logic so it distinguishes:
  - unavailable source data;
  - calculated/derived metrics already available;
  - additional metrics that would improve confidence but are not required for the current answer.
- Remove stale field fallback assumptions. If a dataset lacks a required field, explain the missing field using the actual profile/semantic layer instead of trying old demo columns.
- Delete obsolete tests or branches that protect noisy or contradictory limit wording.

Acceptance:

- ROI questions directly name the highest ROI object and then explain tradeoffs.
- Repeat-rate questions either show the calculated result or say why it cannot be calculated, never both.
- Product/category questions do not claim that already-calculated amount or quantity metrics are missing.
- Store/report-style analysis either completes from actual fields or returns a readable missing-evidence explanation based on actual fields.

## P25-H2 Report Goal Inference, Titles, And UI Simplification

Status: Complete on 2026-07-04.

Scope:

- Add fail-first tests for broad report goals that mention channels but are not only channel reports:
  - “生成一份最近90天经营复盘报告，包含收入、客户、商品、渠道投放表现和建议。”
  - “生成一份管理层经营简报，重点看渠道效率、商品表现和客户分群。”
- Make whole-report intent win over local keywords:
  - 经营复盘 -> `最近90天经营复盘报告`
  - 管理层经营简报 -> `最近90天管理层经营简报`
  - only channel-performance goals -> `最近90天渠道表现复盘报告`
  - only trend goals -> `最近90天趋势变化报告`
- Simplify Report Center's main form. The primary input should be the report goal. Remove or hide the visible report-type selector unless it is placed under advanced settings.
- Keep one coherent report document path. Do not restore per-section Analysis Workbench stitching.
- Report chapters should be inferred from goal + available data + evidence ledger coverage, not from a fixed template selector.
- Delete tests and code that require users to select `business_review`, `channel_performance`, or `revenue_trend` as the main product behavior.

Acceptance:

- Two broad goals that mention渠道 no longer both produce `最近90天渠道表现复盘报告`.
- Channel-only and trend-only goals still infer appropriate specialized titles.
- The report reads as one document, not multiple Analysis Workbench answers pasted together.
- The main Report Center UI no longer feels like choosing a rigid report template.

Result:

- Added fail-first coverage for broad经营复盘, 管理层经营简报, channel-only, and trend-only report goals.
- Added a compact report intent/title/topic helper in `workspaces/report_planner.py` so whole-report intents win before local keywords. Broad经营复盘 and管理层经营简报 can still include渠道投放表现 chapters without changing the whole report title to渠道表现复盘.
- Simplified Report Center's primary form to the report goal. `report_type` remains only as an internal API default (`business_review`) when the frontend does not supply one.
- Removed product-facing report-type labels from the report list/detail metadata so Report Center does not read like a fixed template selector.
- Kept the existing ledger-backed one-pass `ReportDocument` path; no per-section Analysis Workbench stitching or old stitched report summary path was restored.

## P25-H3 Real Usage Acceptance, Cleanup, And Documentation

Status: Complete on 2026-07-04.

Scope:

- Add a compact realistic acceptance suite using generated Chinese business datasets, not saved workspace artifacts.
- Replay the manual questions above through no-key deterministic mode and live DeepSeek mode when opt-in flags and key are available.
- Record live-provider acceptance output: question, recognized task, evidence requirements, SQL/evidence summary, final answer, report goal, report title, section titles, data limits, provider-call status, and any validation repair.
- Run focused backend tests, full pytest, frontend tests/build, tracked-artifact audit, old-path audit, and `git diff --check`.
- Update README, DEVELOPMENT_PLAN, DEVELOPMENT_STATUS, and this plan with actual results.

Cleanup requirement:

- Delete old paths, stale compatibility code, obsolete tests, dead imports, and unreachable branches that conflict with the current Chinese-first product.
- Do not keep old report-type behavior, old demo-schema assumptions, old stitched-report behavior, or old mock/demo product paths only for historical compatibility.
- Keep the project recognizably multi-agent/tool-calling: profiling, task understanding, SQL planning/review/execution, evidence validation, chart/report artifact generation, model judgment, and report composition should remain clear and current.

Acceptance:

- The same real-use questions produce Chinese, direct, evidence-consistent answers.
- Report Center infers intent from user goals and produces coherent report titles/documents.
- Live DeepSeek acceptance is run when local credentials and opt-in flags are present; otherwise live tests skip explicitly.
- No generated workspace data, reports, traces, chart files, `.env`, `.next`, caches, or local artifacts are committed.

Result:

- Added `tests/test_p25_real_usage_acceptance.py`, a compact generated-data acceptance suite. It creates Chinese channel, customer, product, and store datasets under pytest temp paths and does not depend on saved workspace artifacts.
- Analysis Workbench coverage now replays:
  - “最近90天哪个渠道 ROI 最高？为什么？” -> first answer sentence names 私域社群 as the ROI leader.
  - “哪个客户分群复购率最高？” -> calculated 复购率 evidence is treated as supported and does not create contradictory data limits.
  - “哪个商品品类成交金额最高，哪个销量最高？” -> 成交金额 and 销量 are both preserved as supported facts, including different leaders.
  - “帮我做一下门店经营复盘。” -> uses current 门店/销售额/订单数/毛利率/满意度 evidence and does not revive stale demo fields.
- Report Center coverage now replays the four P25 report goals and verifies goal-derived titles: `最近90天经营复盘报告`, `最近90天管理层经营简报`, `最近90天渠道表现复盘报告`, and `最近90天趋势变化报告`. Broad reports that mention渠道 still include渠道投放表现 chapters without title hijack.
- Report output remains one `ReportDocument`. Business-facing text is checked for no `章节业务答案`, SQL, raw rows, query ids, trace/provider metadata, internal prompt text, or old stitched top-level `sections` report shape.
- Real DeepSeek acceptance ran with local `.env` plus explicit opt-in flags and passed: `4 passed in 253.36s`. The recorded live analysis question was “最近90天按渠道比较收入、投放金额和 ROI，哪个渠道投放效率最高？请给证据、图表和风险边界。” The recognized task was a 渠道 rank with metrics 销售额、投放成本、收入金额、投放金额、ROI and `investment_efficiency`; SQL grouped `channel_spend` by 渠道 and calculated 总收入、总投放、ROI、ROAS; evidence rows ranked 私域社群 first by ROI/ROAS; `data_limits` was empty for those calculated ROI facts.
- Live report acceptance used the goal “生成经营复盘报告，覆盖门店表现、商品表现、客户分群、客服运营、渠道投放表现、利润和复购率。” It produced `最近90天经营复盘报告` with sections `经营概览`, `门店表现`, `收入结构`, `客服问题`, `客服运营`, `渠道投放表现`, and `趋势变化`. Data boundaries explicitly named unsupported 客户分群、利润/毛利/净利 and 复购/留存 evidence. Provider calls were recorded; validation passed after one provider repair pass; deterministic fallback repair was not needed.
- Fixed a live-provider edge case where provider metric fragments such as `ROI（收入`, `投放）`, and `销售额（收入）` caused data limits to claim calculated ROI evidence was missing even when evidence columns contained ROI/ROAS/revenue/spend. Metric token normalization now strips bracket punctuation, considers fragment tokens, and recognizes spend synonyms.
- Old-path cleanup audit found no active product path for old chart agents, action delivery/drafter, mock SaaS, old stitched reports, fixed templates, keyword inference, Streamlit, or eval runners. Remaining hits are historical/superseded docs, negative boundary tests, provider/tool rejection tests, or assertions that old strings are absent from output.
- Remaining risk: live provider prose may still frame broad multi-metric ROI questions as a tradeoff when the prompt asks for revenue, spend, and ROI together. Exact ROI leader questions and deterministic answer consistency now answer ROI first, and data limits no longer contradict calculated ROI evidence.

## P25-H4 Default Full Data Time Range For Safe Cases

Status: Complete on 2026-07-04.

Scope:

- Change the missing-time-range behavior from one-size-fits-all clarification to a conservative default policy:
  - if the user explicitly gives a time range, use it exactly;
  - if the user omits a time range and the relevant data has one clear date/time field, default to the full available time range in the current dataset;
  - if multiple plausible date/time fields exist and choosing one changes the business meaning, ask a concise clarification;
  - if the question asks for “最近”, “趋势”, “同比”, “环比”, “变化”, or a period comparison without enough window/grain detail, keep asking clarification unless a safe default is already explicit in the workspace/report context;
  - if a table has no usable time field, run a full-table analysis only when the question does not depend on time, and clearly say this is based on all currently available records.
- Persist this default into the normalized `analysis_task.defaults_applied`, `resolved_question`, evidence requirements, fact payload, business answer caveats, chart annotation, and Report Center `ReportDocument.time_range`.
- Report Center should use the same policy. If the goal has no time range but the report has one safe full data range, title/metadata should read like `基于当前完整数据的经营复盘报告` or include the actual date span, not hard-code `最近90天`.
- Keep the implementation small and clean. Prefer a shared helper for safe time-range defaulting instead of adding table-specific business rules.
- Delete obsolete tests/code that require clarification for every missing time range when a safe full-data default is available.

Acceptance:

- “哪个客户分群贡献的收入最高？这些客户有什么特点？” completes without clarification when the workspace has one safe order/customer transaction date. The answer states the applied full data range.
- “按商品品类看成交金额和销量，哪个品类贡献最高？是否值得重点运营？” completes without clarification when one safe sales date exists, and says it used the full available data range.
- “收入趋势怎么样？” still asks for clarification when the required trend window/grain is ambiguous.
- If multiple time fields are present, such as 订单日期 and 支付日期, the product asks which date field to use instead of guessing.
- Report goals without explicit time range use the safe full-data range in title/metadata/body and do not silently label the report `最近90天`.
- Existing P25 behavior stays intact: direct primary-metric answers, evidence-limit consistency, report goal/title inference, one coherent report document, and old-path cleanup do not regress.

Result:

- Added a shared `workspaces/time_range_defaults.py` helper used by Analysis Workbench and Report Center. The helper reads semantic-layer `time_fields` and profile `value_range` metadata, so it stays generic and does not hardcode orders/customers/marketing tables or sample Chinese data.
- Analysis Workbench now applies `full_data_range` when a question omits time and exactly one safe time field exists. The applied default is written into `analysis_task.time_range`, `defaults_applied`, `resolved_question`, shared evidence payloads, fast-fact context packs, and business-answer caveats.
- Multiple plausible time fields now produce a `date_field` clarification, and trend/同比/环比/变化 analysis questions without grain produce a `time_grain` clarification such as “你希望按天、周还是月查看趋势？是否使用完整数据范围？”
- Report Center now defaults no-time report goals to the safe full data span and titles them with `完整数据...` rather than silently using `最近90天`. Explicit goals such as `生成最近7天渠道表现复盘报告`, `生成最近180天经营复盘报告`, `生成最近6个月收入趋势报告`, and `生成本季度经营复盘报告` keep the user-specified time range.
- If a missing-time report goal has multiple plausible time fields, Report Center now stops and returns a clear `date_field` clarification instead of falling back to `当前工作区全部可用数据`.
- Report evidence and document data boundaries state “你没有指定时间范围” plus the concrete start/end dates. Report validation now treats those structured time-range dates as supported time context rather than unsupported prose numbers.
- Focused and full verification passed: new P25-H4 tests, adjacent analysis/report/evidence tests, P20/P25 realistic acceptance, full backend regression, frontend tests, and frontend build.
- Live DeepSeek smoke passed with local `.env` and explicit provider flags. `哪个客户分群贡献的收入最高？` completed with full range `2025-01-15 至 2026-06-30`; `收入趋势怎么样？` asked for `time_grain`; provider-backed Report Center generated `完整数据渠道表现复盘报告` with validation `passed` and a visible full-range data boundary.

## Verification Ladder

Use focused checks first:

```bash
python3 -m pytest tests/test_product_result_builder.py tests/test_answer_consistency.py tests/test_workspace_analysis_runner.py -q
python3 -m pytest tests/test_report_planner_evidence.py tests/test_workspace_report_runner.py tests/test_report_composer_validator.py -q
```

Then run product regression:

```bash
python3 -m pytest tests/test_p20_realistic_acceptance.py tests/test_metric_tool.py tests/test_evidence_tool.py -q
python3 -m pytest
cd frontend && npm test
cd frontend && npm run build
git diff --check
```

Live DeepSeek acceptance remains opt-in:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER=1 \
python3 -m pytest tests/test_p20_live_deepseek_acceptance.py tests/test_p12_live_deepseek_workspace_report.py tests/test_p11_live_deepseek_workspace_analysis.py -q
```

P25-H3 verification result:

- `python3 -m pytest tests/test_p25_real_usage_acceptance.py tests/test_evidence_tool.py tests/test_report_planner_evidence.py -q` -> `48 passed`
- `python3 -m pytest tests/test_product_result_builder.py tests/test_answer_consistency.py tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py -q` -> `96 passed`
- `python3 -m pytest tests/test_p20_realistic_acceptance.py tests/test_metric_tool.py tests/test_workspace_profiler.py tests/test_workspace_semantic_draft.py -q` -> `31 passed`
- `python3 -m pytest -q` -> `548 passed, 12 skipped`
- `cd frontend && npm test` -> `69 passed`
- `cd frontend && npm run build` -> passed
- Live DeepSeek command with question-understanding, SQL-planning, SQL-candidate, visualization, and report-composer flags -> `4 passed in 253.36s`
