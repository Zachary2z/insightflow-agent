# P35 Analysis Workbench Evidence Planning And Chart Reliability

Status: Complete on 2026-07-08; H1-H4 implementation, post-live reliability repair, deterministic regression, and real DeepSeek closeout complete

## Post-Live Reliability Repair

The final P35 live review found that Analysis Workbench already had a dedicated Business Answer prompt, but the answer path could still fail because downstream validation treated some normal business wording as unsupported facts. The fix keeps answers model-written and avoids deterministic templates:

- Business Answer prompt/input now favors answer-safe evidence fields such as `fact_text`, `business_object`, label, value, and unit instead of raw column/parameter-style evidence.
- Minor provider schema drift is normalized and revalidated once; validation is not bypassed.
- If a provider draft is rejected or scrubbed into an empty/generation-failed answer after successful evidence collection, Business Answer triggers one safe-review LLM rewrite using the same answer-safe ledger. This is a failure-recovery retry only, not a normal-path template.
- Fact support now ignores rank ordinals such as `排名第1` when checking numeric evidence, and supports rounded percentage display values such as `46.15%` against ratio evidence such as `0.461538`.
- Fast-fact routing accepts the local fast-fact gate for simple factual questions when no hard disqualifier exists, so extra provider lens detail does not unnecessarily push simple questions into deep paths.
- Old row-derived answer composition remains deleted; Product Result Builder stays an assembler.

Real DeepSeek closeout passed after this repair with `deepseek-v4-flash`:

- `最近30天哪个渠道收入最高？只回答事实。`
  - route: `fast_fact`
  - elapsed: 18.38s
  - reply: `最近30天收入最高的渠道是私域社群，销售额为180000元。`
  - chart: none
- `最近90天各渠道收入表现怎么样？`
  - route: `standard_analysis`
  - elapsed: 22.58s
  - reply: `近90天各渠道收入表现：私域社群销售额最高（18万元），其次是搜索广告（12万元），直播间最低（9万元）。私域社群贡献了近一半的收入。`
  - chart: none
- Same-thread follow-up `为什么？需要注意什么？`
  - reused the same run/thread
  - elapsed: 31.83s
  - reply: `私域社群销售额最高（18万元）。需要注意：当前分析仅涵盖广告投放成本，未计算其他成本（如人力、运营），也未包含客单价等客户价值指标，因此无法全面评估利润率和长期效益。`
- `结合收入、投放花费和 ROI，哪个渠道最值得加预算？`
  - route: `deep_judgment`
  - elapsed: 30.31s
  - reply: `结合收入、投放花费和ROI，私域社群渠道最值得加预算。`
- `最近90天按渠道比较收入和投放花费，用图表展示。`
  - route: `standard_analysis`
  - elapsed: 25.61s
  - chart: ECharts artifact from `analysis_workbench`
- Report Center remained independent on `ledger_backed_report_center`
  - elapsed: 20.56s
  - chart: 4 ECharts artifacts from `report_center`

Verification:

```bash
python3 -m pytest tests/test_question_evidence_ledger.py tests/test_provider_backed_business_answer_agent.py tests/test_business_answer_quality.py tests/test_answer_consistency.py tests/test_analysis_route_policy.py tests/test_workspace_analysis_runner.py -q
# 132 passed
python3 -m pytest -q
# 721 passed, 14 skipped
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_PRODUCT_LIVE_MODE=1 python3 -m pytest tests/test_p33_live_acceptance.py -q -s
# 1 passed in 150.20s
git diff --check
# passed
```

P35 updates Analysis Workbench by learning the useful part of Report Center: plan the evidence first, group evidence clearly, then let the model write from a clean evidence ledger. It must not copy Report Center's fixed report chapters or turn workbench answers into report templates.

The current live testing problem is not that Report Center skips safety. Report Center also validates SQL, builds an EvidenceLedger, validates report facts, and repairs unsupported claims. Report Center succeeds more often because its evidence is scoped by report plan and section. Analysis Workbench is more open-ended, so one lightweight ledger currently has to serve question answering, audit, chart generation, history, and follow-up memory. When that ledger is too broad, charts can mix unrelated entities and valid model answers can be over-cleaned.

P35 should therefore introduce a question-level evidence plan and grouped Analysis Evidence Ledger for Analysis Workbench. Final answers remain model-written. Chart options remain deterministic from reviewed evidence. Old broad projection paths, row-derived answer paths, and compatibility branches that conflict with this direction should be deleted or narrowed instead of preserved.

## What To Learn From Report Center

Learn these ideas:

- Plan before collecting evidence.
- Keep evidence grouped by business purpose, dimension, metric, grain, and source.
- Give the model a clean, answer-safe ledger instead of raw rows or mixed debug payloads.
- Validate hard facts after the model writes.
- Repair only unsupported hard facts, not the whole answer.
- Bind charts to one evidence group/table so the chart has one clear business object.

Do not learn these report-specific habits:

- No fixed report chapters in Analysis Workbench.
- No stitched report sections.
- No deterministic answer templates.
- No hard-coded business examples such as specific channel names, staff names, or demo table fields.
- No broad keyword rule tree that tries to enumerate every possible user question.

## Goals

- Add a question-level `QuestionEvidencePlan` for Analysis Workbench, similar in spirit to Report Center's `ReportPlan` but shaped for one user question or same-thread follow-up.
- Replace broad ledger projection with grouped evidence units that preserve business purpose, dimension role, metric roles, source table, time policy, row grain, and chartability.
- Keep final user-facing conclusions model-written from an answer-safe grouped ledger projection.
- Preserve valid model answers when the main conclusion is supported; only remove, soften, or mark unsupported hard facts.
- Generate charts only from one coherent evidence group or from explicitly comparable groups.
- Fix metric-label integrity so values are labeled from source columns and semantic roles, not fragile metric list order.
- Improve ECharts titles, axes, legends, units, and annotations so chart artifacts read like business charts.
- Clean old conflicting paths aggressively. Do not keep compatibility code that still synthesizes answers from rows or dumps all ledger facts into chart data.

## Non-Goals

- Do not add real Feishu, DingTalk, WeCom, Tencent Docs, Power BI, Tableau, or SaaS publishing.
- Do not make the LLM generate arbitrary chart data or arbitrary ECharts options.
- Do not replace model-written Analysis Workbench answers with deterministic templates.
- Do not merge Report Center into Analysis Workbench.
- Do not make Report Center call Analysis Workbench.
- Do not restore old `chart_agent`, `visualization_planner`, `chart_tool`, stitched report sections, `final_answer_composer`, `fast_fact_composer`, or row-derived answer composers.
- Do not preserve old compatibility branches when they conflict with the current evidence-plan/grouped-ledger/ChartArtifact path.

## Target Analysis Workbench Path After P35

```text
user question / same-thread follow-up
-> Question Understanding + Business Lens grounding
-> route by evidence complexity
-> Question Evidence Plan
   -> evidence groups: purpose, source, dimension, metrics, time policy, grain, chart intent
-> Evidence Task Runner
   -> guarded SQL candidate per evidence group/task
   -> SQL review
   -> SQL execution
   -> evidence validation
-> Grouped Analysis Evidence Ledger
   -> group facts by business purpose and comparable row set
   -> label metrics from source columns / semantic roles
   -> keep data limits and unsupported evidence separate
-> Business Answer Agent
   -> model writes the final Chinese answer from grouped answer-safe ledger only
   -> unsupported hard facts are removed, softened, or listed as data limits
   -> supported conclusion is preserved
-> ChartArtifact generation, parallel where safe
   -> choose one coherent chart group
   -> build deterministic ECharts option from comparable rows only
   -> skip chart with a business warning when groups are not comparable
-> Product Result Builder
   -> assemble answer, evidence summaries, chart artifacts, history, and technical details
   -> no answer synthesis, no chart data invention, no raw SQL/raw rows/provider leaks in main UI
```

The main product rule is: Analysis Workbench may collect multiple evidence groups, but every answer paragraph and chart must be traceable to the specific grouped ledger facts that support it.

## H1: Question Evidence Plan And Grouped Ledger

Status: Complete on 2026-07-07.

Build the Analysis Workbench equivalent of Report Center's evidence organization, without report chapters.

Implementation direction:

- Add or extend a compact `QuestionEvidencePlan` contract for Analysis Workbench. It should describe evidence groups, not answer templates.
- Each evidence group should carry:
  - purpose, such as `关键事实`, `对比证据`, `投放效率证据`, `客服压力证据`, `趋势辅助证据`;
  - source table/field refs where available;
  - dimension role and display label;
  - metric roles, source columns, display labels, units, and aggregation/grain;
  - time policy;
  - whether it can support answer facts;
  - whether it can support chart generation.
- Rework `workspaces/question_evidence_ledger.py` so facts and table-like rows are stored under grouped ledger sections instead of being flattened into one mixed pool.
- Metric labels must come from returned source columns, semantic-layer labels, and metric roles. Planner metric order is only a hint, never positional truth.
- Keep legacy fields only as compatibility projections generated from the grouped ledger. Do not let legacy projections become the primary source for answer or chart generation.
- Delete or narrow old broad `build_chart_safe_table` behavior that blindly combines facts and derived metrics across groups.

Expected tests:

- A multi-metric result with columns ordered differently from requested metrics keeps labels attached to the correct values.
- Channel revenue evidence and sales-owner/support evidence stay in separate ledger groups.
- Follow-up runs preserve grouped evidence context without creating a separate disconnected analysis.
- Old flat ledger projections do not drive Business Answer or chart generation when grouped ledger data is available.

H1 implementation notes:

- Added grouped ledger sections under `question_evidence_plan` and `evidence_groups`; legacy `facts`, `derived_metrics`, and `tables` remain compatibility projections only.
- Each evidence group records purpose, source table/field refs, dimension role/label/source columns, metric role/label/source column/source fields/unit, time policy, row grain, answer/chart support, evidence refs, facts, and derived metrics.
- Business Answer receives an answer-safe grouped projection with remapped group/evidence refs and without raw SQL, raw rows, provider metadata, task ids, row refs, ledger ids, source pack ids, trace paths, or local paths.
- Metric labels bind to returned source columns and semantic metric metadata before metric-list hints, so planner metric order cannot swap labels.
- `build_chart_safe_table()` now accepts only one coherent chartable evidence group and refuses broad multi-group mixing. The current sanitized execution fallback remains for compatibility until H3 replaces chart selection with grouped candidates.
- Product Result Builder assembles grouped summaries and scrubbed group cards only; it does not synthesize answers.

## H2: Grouped Answer Generation And Non-Destructive Audit

Status: Complete on 2026-07-07.

Make Analysis Workbench answer like Report Center in the one useful sense: the model receives organized evidence, then fact validation checks the output.

Implementation direction:

- Update `workspaces/business_answer_agent.py` to consume the answer-safe grouped ledger projection.
- The prompt should ask the model to write a natural Chinese business answer from evidence groups and data limits, not fill a fixed response template.
- The model may explain causes, tradeoffs, and recommendations, but hard facts such as amounts, dates, percentages, rankings, chart values, and data sources must come from ledger facts.
- Update audit/repair so one unsupported auxiliary claim does not erase a mostly supported answer.
- Repair should remove, soften, or move unsupported hard facts into data limits. It should not regenerate a deterministic row-derived answer.
- Keep no-key fallback explicit and visibly limited.
- Delete old answer-generation, answer-rewrite, or consistency paths that still synthesize conclusions from rows, raw execution results, or fixed text patterns.

Expected tests:

- A provider answer with one unsupported auxiliary number keeps the supported main conclusion and removes only that number.
- A provider answer based on grouped channel evidence produces a business answer without leaking raw field names, raw SQL, provider metadata, task ids, or ledger internals.
- No-key/provider-failure mode does not pretend to have a natural model answer.
- Report Center remains on `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument`.

H2 implementation notes:

- `BusinessAnswerAgent` now gates provider generation on the answer-safe grouped projection returned by `build_answer_input_ledger()`. If the grouped ledger is absent or empty, the answer surface returns explicit generation failure instead of prompting from raw execution rows or composing from ledger facts.
- The `business_answer` prompt now tells the model it is a Chinese business analysis assistant, asks for natural direct prose, puts the core answer first, then evidence, suggestions, and boundaries, forbids fixed chapter/report templates, and limits hard facts to `evidence_groups` plus `data_limits`.
- Provider prompt/schema context excludes raw execution rows, SQL, `task_id`, `task_purpose`, `ledger_id`, `source_pack_id`, trace paths, provider metadata, local paths, prompt/debug fields, and other internal artifacts.
- Repair is non-destructive. Typed hard-fact claims are checked against the grouped ledger; unsupported auxiliary numbers are removed from answer sentences/items while supported main conclusions remain. Internal leaks, empty primary answers after cleanup, provider validation failure, or broadly unsupported primary facts still become generation-failed output.
- No-key/no-provider mode keeps SQL/evidence/table previews available but the main `business_answer` is `业务回答生成失败`; it no longer produces `无可用模型时使用证据账本回答` or row/ledger-derived business conclusions.
- Product Result Builder remains an assembler and Report Center remains independent on `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument`.

## H3: Grouped Chart Selection, ECharts Polish, And Acceptance

Status: Complete for deterministic implementation and regression on 2026-07-07. Real DeepSeek/manual acceptance remains recommended for P35 closeout.

Make charts consume the grouped ledger, not every available fact.

Implementation direction:

- Build chart candidates from grouped ledger sections.
- A chart candidate is valid only when it has one coherent business dimension, comparable numeric metrics, compatible unit/grain, and rows from the same group or explicitly comparable groups.
- For simple chartable questions, prefer the clean reviewed `execution_result` or its grouped ledger equivalent when it already contains one dimension and one metric.
- For deep questions, choose the group that matches the main comparison target and chart intent. If groups are not comparable, skip chart generation with a clear business note.
- Exclude totals, shares, ranks, and support-only derived metrics unless the user explicitly requested those metrics or the selected chart group declares them comparable.
- In `visualization/echarts_option_builder.py`, keep real metric names in legends instead of replacing every series with a global `value_label`.
- In `agents/visualization_agent.py`, derive chart titles, axes, units, and annotations from the selected chart group.
- Remove stale chart fallback helpers, stale tests, and compatibility code that encourage broad row/ledger projection.

Acceptance questions:

- `最近90天哪个渠道收入最高？只回答关键事实`
- `最近90天按渠道比较收入，并生成图表`
- `最近90天各渠道投放花费和收入表现怎么样？哪个渠道更值得关注？`
- `结合最近90天收入、投放花费和客服投诉，哪个渠道最需要优先优化？请给出证据和建议`

Acceptance must report route, elapsed time, provider calls, grouped evidence count, answer summary, chart count/type, chart labels/series, and leak-free status.

H3 implementation notes:

- Added `build_grouped_chart_candidate()` in `workspaces/question_evidence_ledger.py`. It consumes only `question_evidence_ledger.evidence_groups` and returns business dimension label, metric labels, display unit, row grain, evidence refs, safe columns/rows, and a deterministic chart spec.
- One coherent evidence group can generate a chart candidate. Multiple groups combine only when they share the same dimension signature and row grain and their units are compatible. 同渠道/同颗粒度的收入和投放花费 can become a grouped bar; revenue plus ROI/percentage or channel evidence plus support-owner/support-issue evidence is rejected.
- `build_chart_safe_table()` now delegates to the grouped candidate contract. It remains only a compatibility projection and no longer owns broad chart selection.
- `agents/visualization_agent.py` now prefers grouped chart candidates and bypasses provider chart-spec/tool choice when a candidate exists. If there is no coherent grouped candidate, it records a skipped chart result with a business-readable reason. The old active sparse multi-task `task_id`/`task_purpose` row-to-long-table fallback was removed; the only fallback left is a legacy single-dimension/single-metric execution result with no internal columns.
- `visualization/echarts_option_builder.py` keeps grouped-bar legend names from the real metric labels and rejects grouped bars whose `metric_units` mix incompatible unit families. Candidate-built specs produce titles/axes/units such as `最近90天渠道收入与投放花费对比`, `渠道`, and `金额 (元)` instead of generic `对象数值对比` / `数值`.
- ChartArtifact gained safe `skip_reason`, `failure_reason`, and `chart_input_source` fields. Product Result Builder and `ChartArtifactGallery` can display skip/failure reasons in business language without showing SQL, raw rows, task ids, ledger JSON, trace/provider metadata, or raw option/spec JSON in the main UI.
- Report Center was not connected to the Analysis Workbench chart selection node. It still uses `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument`, with only the generic ChartArtifact/ECharts builder contract shared.

H3 deterministic verification completed:

```bash
python3 -m pytest tests/test_question_evidence_ledger.py tests/test_visualization_agent_external_tools.py tests/test_echarts_option_builder.py -q
# 47 passed
python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q
# 95 passed
python3 -m pytest tests/test_business_answer_quality.py tests/test_answer_consistency.py -q
# 36 passed
python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q
# 38 passed
python3 -m pytest tests/test_p20_architecture_cleanup_boundaries.py -q
# 3 passed
cd frontend && npm test -- --run
# 77 passed
cd frontend && npm run build
# passed
```

Live-provider/manual acceptance remains opt-in. P35 closeout should run or explicitly skip the four acceptance questions with real DeepSeek/manual inspection and record route, elapsed time, provider calls, grouped evidence count, answer summary, chart count/type, chart labels/series, and leak-free status.

## H4: Live Closeout Repair Without Templates

Status: Complete on 2026-07-08.

Live DeepSeek testing after H3 found that deterministic regression passed, but several real-use edges still need one focused closeout repair before P35 can be considered complete. This repair should be implemented in three small steps, not split into many new subphases. The key rule remains: do not fix these cases by hard-coding the sample questions, table names, channel names, store names, or fixed answer paragraphs. Route, evidence, chart, and answer behavior must be driven by structured task complexity, semantic/business-lens grounding, grouped ledger facts, metric roles, units, dimensions, and source compatibility.

### Step 1: Fast-Fact Route And Top-N Evidence

Problem found in live testing:

- A simple question such as `最近30天哪个渠道收入最高？只回答事实和口径。` still went through `standard_analysis`.
- The SQL/evidence sometimes returned only the top row, so the final model answer correctly identified the leader but then warned that there was not enough comparison evidence.

Required change:

- Keep Question Understanding and Business Lens at the front, but make the fast-fact decision use structured complexity instead of keyword templates.
- Route to `fast_fact` only when the grounded task has one business topic, one clear fact source or main table, one primary metric, one dimension, a fact/ranking/top/bottom operation, and no need for reasons, recommendations, risk, budget decisions, report writing, or multi-table judgment.
- For top/rank fast facts, the evidence task must retain enough comparison candidates, usually top 3 or top 5 rows when available, even if the final answer only states the top result. This gives the model enough evidence to answer confidently without inventing or complaining about missing comparison scope.
- Do not restore deterministic `fast_fact_composer` or any row-derived natural-language answer. The final conclusion is still written by Business Answer from the grouped ledger.

Expected tests:

- `最近30天哪个渠道收入最高？只回答事实和口径。` routes to `fast_fact`, executes SQL, keeps multiple candidate rows when data exists, and calls Business Answer for final wording.
- A similar one-metric/one-dimension top question with different table/field labels also routes by structure, not by exact words.
- A question asking `为什么`, `建议`, `风险`, `优先复盘`, or combining several metrics stays on `standard_analysis` or `deep_judgment`.

### Step 2: Chart Candidate Subset Selection

Problem found in live testing:

- A question asking for revenue, spend, and ROAS could skip chart generation because one derived metric had a different unit.
- Earlier chart attempts could mix unrelated entities or display generic labels such as `对象数值对比` / `数值`.

Required change:

- Chart selection should choose the strongest coherent subset from the grouped ledger instead of treating an entire evidence group as all-or-nothing.
- Same dimension, same grain, and compatible unit-family metrics can form a grouped bar chart, for example revenue plus spend as amount metrics.
- Ratio/rate/rank/share metrics such as ROI/ROAS can remain in the answer, annotation, or evidence summary when they are not compatible with the chart axis.
- Exactly two incompatible but meaningful numeric metrics can use a scatter chart only when they share the same business object and row grain.
- Three or more mixed-unit metrics should not be forced into one chart. Choose a compatible subset if one exists; otherwise skip chart generation with a business-readable reason.
- The chart title, x-axis, y-axis, legend, unit, and annotation must come from grouped ledger metadata and metric labels, not fixed generic labels or sample-field rules.

Expected tests:

- Channel revenue plus spend plus ROAS generates a revenue/spend grouped bar and keeps ROAS out of the shared axis.
- Mixed unrelated groups, such as channel performance plus support issue evidence, do not produce one combined chart.
- Derived ranks/shares are not plotted unless explicitly requested and declared comparable.

### Step 3: Preserve Valid Model Answers And Fix Label/Lens Integrity

Problem found in live testing:

- One deep question produced a valid model-written business answer internally, but the final product result displayed `业务回答缺失`.
- Some evidence/audit labels could mismatch values, such as showing a satisfaction value under a sales metric label.
- Business Lens could map a metric to a source table that did not match the requested dimension when several tables contained similar business concepts.

Required change:

- Product Result Builder remains an assembler. If `business_answer_generation.success=true` and a structured `business_answer` exists, preserve it unless a blocking safety rule applies.
- Evidence audit may remove or soften unsupported hard facts, but it must not erase a mostly supported answer because of one auxiliary unsupported number.
- Metric labels must bind to source columns, semantic-layer fields, metric ids/roles, and grouped ledger evidence refs. They must not depend on metric list order.
- Business Lens grounding should prefer metric/dimension combinations that are source-compatible in the same table or explicitly joinable evidence group. It should not choose a metric table that cannot support the selected dimension just because the metric label is similar.
- If no compatible source can support the requested metric/dimension pair, return a data limit or clarification instead of silently mixing fields.

Expected tests:

- A provider-generated answer with a supported main conclusion remains visible after audit and Product Result Builder assembly.
- Metric labels remain correct when SQL returns columns in a different order from the planned metrics.
- A store-level question chooses store-compatible sales/satisfaction fields instead of channel-spend fields with similar revenue labels.

H4 implementation notes:

- Fast-fact route selection remains behind Question Understanding and Business Lens, but rank/top fact questions are now evaluated by grounded structure: one source/table, one primary metric, one dimension, simple fact/rank operation, and no reason/recommendation/risk/report/multi-table decision requirement.
- Ranking fast facts retain comparison candidates. Provider SQL that returns only `LIMIT 1` for a rank task is widened to top-N comparison evidence so Business Answer can state the leader without warning that comparison scope is missing.
- `build_grouped_chart_candidate()` now selects a coherent compatible metric subset from grouped ledger evidence. Amount metrics such as revenue and spend can form a `grouped_bar`; ROAS/ROI/rate/share/rank metrics are excluded from the amount axis unless explicitly comparable.
- Product Result Builder remains an assembler. It preserves successful structured `business_answer_generation.business_answer` output, normalizes extra model fields, and does not erase an otherwise valid model answer because auxiliary evidence is weak.
- Post-review live-test repair fixed answer scrubber number handling: time-window numbers such as `最近90天` are no longer treated as unsupported hard-fact amounts, and numeric matching is exact enough that `90` cannot corrupt supported values such as `90,000元` into malformed fragments. This keeps model-written answers intact while still removing unsupported hard facts.
- Main Product Result payloads scrub internal `ledger_id`, `source_pack_id`, task ids, raw evidence refs, and question-thread ledger refs from display summaries. Technical details remain separate.
- Business Lens now prefers metric/dimension source compatibility from the requested dimension tables, supports margin-like store metrics, and avoids silently binding product/customer/store dimensions to unrelated channel-spend metrics when labels are merely similar.

### H4 Verification And Closeout Acceptance

Deterministic checks completed:

```bash
python3 -m pytest tests/test_analysis_route_policy.py tests/test_fast_fact_path.py tests/test_workspace_analysis_runner.py -q
# 83 passed
python3 -m pytest tests/test_question_evidence_ledger.py tests/test_visualization_agent_external_tools.py tests/test_echarts_option_builder.py -q
# 50 passed
python3 -m pytest tests/test_product_result_builder.py tests/test_business_answer_quality.py tests/test_answer_consistency.py tests/test_business_lens.py -q
# 94 passed
python3 -m pytest -q
# 715 passed, 14 skipped
cd frontend && npm test -- --run
# 77 passed
git diff --check
# passed
```

Live DeepSeek closeout completed with `deepseek-v4-flash` on 2026-07-08:

- `最近30天哪个渠道收入最高？只回答事实和口径。`
  - route: `fast_fact`
  - elapsed: 26.03s
  - provider calls: question understanding 1, SQL planning 1, SQL candidate 1, Business Answer 1, visualization 0
  - key nodes: supervisor, question understanding, clarification router, evidence planning, schema, metric, guarded SQL candidate, SQL review, SQL execution, evidence validation, fast-fact evidence preparer, Business Answer, evidence auditor
  - grouped evidence count: 1
  - reply summary: private/community channel was identified as highest revenue with multiple channel candidates preserved
  - chart: none
  - main payload leakage: no raw SQL, raw rows, task id, ledger id, provider metadata, trace path, prompt/debug text
- `最近90天比较各渠道收入和投放金额，哪个渠道投放效率更值得关注？请生成图表。`
  - route: `deep_judgment`
  - elapsed: 41.79s
  - provider calls: question understanding 1, SQL planning 1, SQL candidate 1, Business Answer 1, visualization 0
  - key nodes: supervisor, question understanding, clarification router, evidence planning, schema, metric, guarded SQL candidate, SQL review, SQL execution, evidence validation, Business Answer, evidence auditor, visualization
  - grouped evidence count: 1
  - reply summary: private/community channel was identified as the strongest efficiency case using revenue and spend evidence
  - chart: 1 `grouped_bar`; labels `私域社群`, `搜索广告`, `直播间`; series `销售额`, `投放成本`; unit `元`; ROAS/ROI stayed out of the amount axis
  - main payload leakage: no raw SQL, raw rows, task id, ledger id, provider metadata, trace path, prompt/debug text
- `结合门店销售额、毛利率和满意度，哪个门店下一步最值得优先复盘？请给建议和风险边界。`
  - route: `deep_judgment`
  - elapsed: 70.86s
  - provider calls: question understanding 1, SQL planning 1, SQL candidate 1, Business Answer 1, visualization 0
  - key nodes: supervisor, question understanding, clarification router, evidence planning, schema, metric, guarded SQL candidate, SQL review, SQL execution, evidence validation, Business Answer, evidence auditor, visualization
  - grouped evidence count: 1
  - reply summary: model-written recommendation was preserved and displayed; `深圳湾店` was selected for priority review based on sales, margin, and satisfaction
  - chart: 1 scatter chart from the chartable numeric pair; evidence refs mapped to `question_evidence_pack`
  - main payload leakage: no raw SQL, raw rows, task id, ledger id, provider metadata, trace path, prompt/debug text

P35 closes because:

- the first question uses `fast_fact`, keeps comparison candidates, and still uses Business Answer for final Chinese wording;
- the second question generates a coherent revenue/spend chart or gives a precise business-readable no-chart reason, without forcing ROAS onto the same axis;
- the third question displays the valid model-written answer when generated successfully;
- chart labels match real metrics and dimensions;
- no user-facing answer/chart leaks SQL, raw rows, task ids, ledger ids, provider metadata, trace paths, prompt/debug text, or raw chart JSON;
- old conflicting paths remain deleted or narrowed, especially deterministic answer templates, row-derived answer composers, broad chart projections, and stale compatibility branches.

## Verification

Required focused checks:

```bash
python3 -m pytest tests/test_question_evidence_ledger.py tests/test_business_answer_quality.py tests/test_product_result_builder.py -q
python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_visualization_agent_external_tools.py tests/test_echarts_option_builder.py -q
cd frontend && npm test
cd frontend && npm run build
```

Required cleanup/audit:

```bash
rg -n "chart_agent|visualization_planner|chart_tool|final_answer_composer|fast_fact_composer|raw row|row-derived|template answer|deterministic answer template|keyword inference"
git status --short
```

Live-provider acceptance remains opt-in through the existing DeepSeek configuration. If live keys are not available, deterministic tests must still pass and the skip reason must be documented.

## Completion Criteria

- Analysis Workbench has a question-level evidence plan and grouped ledger, not a flat mixed fact pool as the primary answer/chart source.
- Final answers remain model-written from grouped evidence and data limits.
- No deterministic answer template replaces the model answer.
- Unsupported hard facts are repaired without erasing supported business conclusions.
- Metric labels cannot swap because of planner metric order.
- ECharts charts use one coherent business group and comparable metrics only.
- Charts do not mix unrelated objects such as channels, sales owners, support issues, totals, shares, and ranks unless explicitly planned as comparable.
- Report Center remains independent and keeps its report evidence/report document path.
- Old conflicting paths are deleted or narrowed; no unused compatibility code is kept just in case.
- No generated databases, trace files, report artifacts, chart files, exported documents, `.env`, or API keys are committed.
