# P32 Multi Evidence Task Planning

Date: 2026-07-06

## Why P32 Exists

P31 made Analysis Workbench more credible by grounding questions through Business Lens and keeping follow-ups inside one analysis thread. Real DeepSeek testing after P31 exposed the next product gap: some business questions naturally require more than one piece of evidence, but the current Analysis Workbench still tends to produce one primary SQL result. When the model tries to answer a complex question by returning multiple SQL statements in one candidate, the SQL reviewer correctly rejects it because one execution step must remain one safe `SELECT`.

P32 solves this without weakening SQL safety. The product should support one user question producing multiple evidence tasks, while each task still owns exactly one reviewed SQL query, one execution result, and clear evidence refs.

## Product Goal

Upgrade Analysis Workbench from mostly single-result answers to evidence-task-backed answers:

```text
user question
-> question understanding and Business Lens
-> fast fact gate, if eligible
-> otherwise evidence task planning
-> one safe SQL per evidence task
-> reviewed execution per task
-> analysis evidence pack / ledger
-> one Chinese business answer
-> optional chart artifacts
-> same-thread memory
```

Fast factual questions must stay fast. Report Center must stay independent and continue using its existing `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument` path.

## What Changes

### 1. Keep Fast Fact As The Low-Latency Path

Fast fact is not replaced by multi-evidence planning.

Fast fact should still handle simple, low-risk questions such as:

- `最近90天哪个渠道收入最高？`
- `本月哪个门店销售额最高？`
- `所有数据里销售额总计是多少？`

The fast path remains:

```text
question understanding / local fast fact gate
-> one evidence task
-> one SQL review and execution
-> one compact evidence result
-> concise Chinese answer
```

Fast fact should avoid the heavy Business Answer provider and visualization unless the user explicitly requests a chart.

### 2. Add Analysis Evidence Tasks For Standard And Deep Questions

Standard and deep questions can produce a small list of evidence tasks. The default cap should be conservative:

- normal Analysis Workbench: 1-4 evidence tasks
- report generation: keep the current report-specific path; do not migrate in P32

Each evidence task should be explicit and narrow:

```json
{
  "task_id": "revenue_by_channel",
  "question": "按渠道统计收入",
  "metrics": ["销售额"],
  "dimensions": ["渠道"],
  "time_policy": "用户未指定时间，使用完整可用时间范围",
  "purpose": "判断各渠道收入规模",
  "max_rows": 20
}
```

Every task must produce at most one SQL candidate for review. If a provider returns multiple SQL statements, P32 should not execute them directly. It should either:

- split and keep only one safe `SELECT` for the current evidence task when unambiguous, or
- trigger one repair request asking the model to rewrite the current task as a single SQLite `SELECT`, or
- mark that task failed with a business-readable data limit while allowing other successful tasks to continue.

The reviewer boundary remains strict:

- one statement only
- read-only `SELECT` only
- workspace tables and columns only
- no dangerous keywords
- no sensitive fields
- no raw provider SQL in the main UI

### 3. Build An Analysis Evidence Pack/Ledger From Task Results

Analysis Workbench should not copy Report Center chapters, but it should reuse the same evidence principles:

- facts
- tables
- chart refs
- data limits
- tool-call summaries
- evidence refs
- safe display values

The current `QuestionEvidencePack` and lightweight `question_evidence_ledger` should evolve to carry multiple task results. This should stay separate from Report Center's full `ReportEvidencePack + EvidenceLedger`, but the shape and naming should be close enough that future connector/export work can consume both consistently.

The business answer provider should receive the merged analysis evidence ledger once, then write one answer. It should not receive a stitched list of mini answers.

### 4. Reuse Report Center Ideas, Not Its Product Path

Current Report Center already follows the right high-level model:

```text
ReportPlan
-> ReportEvidencePack
-> EvidenceLedger
-> one ReportDocument
```

P32 should reuse the evidence architecture ideas from Report Center, especially ledger-backed facts, evidence refs, data boundaries, and chart artifact contracts. It should not make Analysis Workbench call Report Center planners or turn reports into stitched analysis answers.

Report Center remains:

```text
report goal
-> report plan
-> report evidence collection
-> report evidence ledger
-> one complete report document
```

Analysis Workbench becomes:

```text
question
-> analysis evidence task plan
-> task execution
-> analysis evidence ledger
-> one business answer
```

## Latency Design

P32 must improve capability without making every question slow.

Rules:

- Run the fast fact gate before multi-evidence planning.
- Cap normal evidence tasks at 4.
- Prefer deterministic task planning from Business Lens when the intent is obvious.
- Use a provider planner only when the question is broad, comparative, or requires explanation across multiple metrics.
- Execute different evidence tasks independently and, where implementation allows, in parallel rather than forcing unnecessary serial work.
- Keep each individual task internally sequential: SQL candidate -> SQL review -> approved SQL execution. SQL review and SQL execution for the same SQL must never run in parallel because execution cannot bypass the review boundary.
- Call the Business Answer provider once after the evidence ledger is built.
- Generate charts only for the most useful 1-2 evidence tables or when explicitly requested.

Parallelism should be conservative and configurable:

- `max_evidence_tasks = 4`
- `max_parallel_evidence_tasks = 3` by default
- later environments may raise `max_parallel_evidence_tasks` to the task cap after live stability is proven

The default is not a hard product limitation. It protects DeepSeek/API rate limits, future real database connections, trace readability, and frontend progress clarity. If tasks are more than the parallel limit, run the highest-priority evidence first:

1. core facts required to answer the direct question;
2. supporting facts needed for explanation or recommendation;
3. optional trend/anomaly/chart helper evidence.

Partial completion is allowed. If a lower-priority task fails or times out, successful evidence should still produce an answer with a clear data limit instead of failing the entire analysis.

Expected effect:

- fast fact stays the shortest path;
- standard/deep questions become more reliable for multi-metric questions;
- complex questions no longer fail just because the model tried to emit multiple SQL statements in one candidate.

## P32 Implementation Slices

### P32-H1 Evidence Task Contract And Planning

Define a compact Analysis Evidence Task contract and planner:

- `EvidenceTask`
- `EvidenceTaskPlan`
- `EvidenceTaskResult`
- task status and data-limit fields
- max task count
- deterministic task planning from Business Lens for common cases
- provider-assisted planning only when needed

Tests should cover:

- fast fact remains one task;
- revenue plus spend creates multiple tasks;
- broad unsupported requests produce clear limits;
- planner does not create report chapters or report documents.

Status: complete on 2026-07-07.

H1 result:

- Added `workspaces.evidence_tasks` with `EvidenceTask`, `EvidenceTaskPlan`, `EvidenceTaskResult`, and shared one-SQL-only task policy metadata.
- `EvidenceTask` carries `task_id`, `question`, `purpose`, `metrics`, `dimensions`, `time_policy`, `priority`, `max_rows`, `status`, `data_limits`, and `sql_policy`.
- `EvidenceTaskPlan` carries `route`, `tasks`, `max_evidence_tasks`, `max_parallel_evidence_tasks`, `status`, `planner_source`, `needs_clarification`, `data_limits`, and `safety_policy`.
- `max_evidence_tasks` defaults to `4`; `max_parallel_evidence_tasks` defaults to `3` and is only metadata until H2 implements task execution.
- Fast facts plan exactly one high-priority `core_fact` task. Standard/deep routes plan from Business Lens metrics/dimensions and can produce separate core facts plus supporting efficiency/trend/anomaly evidence tasks, capped at four.
- Revenue plus spend / income plus cost / ROI-style questions can plan multiple tasks without asking a provider to emit multiple SQL statements for one task.
- Broad unsupported questions produce `needs_clarification` and/or `data_limits` plans instead of fabricated tasks.
- The contract records that one evidence task can have at most one SQL statement and that SQL candidate -> SQL review -> approved SQL execution is sequential inside a task. SQL review and execution for the same SQL are not allowed to run in parallel.
- Coordinator now attaches the plan to Analysis Workbench `AnalysisTask` metadata and state-level `evidence_task_plan`; H1 does not change the current Evidence Agent runner or execute tasks in parallel.
- Report Center remains independent on `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument`; H1 did not call the Report Center planner or migrate report code.

### P32-H2 Task Runner And Analysis Ledger Integration

Run each task through the existing safe SQL boundary:

- guarded SQL candidate
- SQL review
- optional schema repair where already supported
- SQL execution
- evidence validation

Then merge successful task results into the Analysis Workbench evidence pack / question evidence ledger.

Tests should cover:

- multiple task results merge into one ledger;
- failed task adds data limits without blocking all successful evidence;
- multi-statement provider SQL is not executed and is repaired or rejected safely;
- main UI/product result does not expose raw SQL, trace paths, provider metadata, API keys, local absolute paths, or raw row dumps.

Status: complete on 2026-07-06.

H2 result:

- Added `workspaces.evidence_task_runner.run_evidence_task_plan`.
- The runner executes each `EvidenceTask` as an independent narrowed Analysis Workbench state and delegates to the existing Evidence Agent safe path: SQL candidate -> SQL review -> optional existing schema repair/execution fix -> approved SQL execution -> evidence validation -> task result.
- The graph invokes the runner only for standard/deep plans with multiple core tasks spanning more than one source table. This targets the P32 multi-evidence gap while preserving the existing single-SQL path for fast facts, explicit `initial_sql`, helper-only questions, and same-table multi-metric questions.
- Cross-task execution uses `max_parallel_evidence_tasks=3` by default, capped by `max_evidence_tasks`, and can be configured through the runner argument or `INSIGHTFLOW_MAX_PARALLEL_EVIDENCE_TASKS`. Inside one task, review and execution remain sequential.
- `question_evidence_ledger` now carries task provenance on facts, derived metrics, table refs, evidence refs, and task refs. Merged ledgers combine successful task facts and failed-task data limits without exposing raw SQL, trace paths, provider metadata, API keys/secrets, or local absolute paths to business-safe payloads.
- Multi-statement SQL returned by a provider is rejected by the guarded candidate/reviewer path and is never executed directly. The failed task records a data limit; successful lower/upper priority tasks continue where allowed.
- Failed non-core tasks no longer fail the whole analysis. If all core tasks fail, the runner returns a business-friendly evidence-insufficient state.
- Business Answer still runs once from the merged evidence/ledger; P32-H2 does not stitch mini answers.
- Report Center remains independent on `ReportPlan + ReportEvidencePack + EvidenceLedger + ReportDocument`.
- No old active path was deleted in H2. The graph trigger was deliberately narrowed so existing single-result paths remain active where they are still the correct product behavior.
- Verification passed: the required backend pytest groups, plus `cd frontend && npm test` (`72 passed`) and `cd frontend && npm run build`.

### P32-H3 Product Acceptance, Live Verification, And Cleanup

Update Business Answer and frontend only as needed to show multi-evidence answers cleanly:

- one business answer, not stitched mini answers;
- evidence summary groups by task;
- chart artifacts bind to task/evidence refs;
- same-thread follow-up memory preserves task/ledger refs;
- fast fact path remains visibly quick.

Run realistic and live DeepSeek tests:

- simple fast fact;
- revenue plus spend analysis;
- complex follow-up inside the same thread;
- a question that previously caused multi-SQL rejection.

Old paths and unreachable compatibility code may be deleted. Do not preserve duplicate single-result-only paths if the new multi-evidence task path fully replaces them. Keep Report Center independent and do not remove historical development docs.

H3 result:

- Product Result now turns multi-task ledger evidence into business-readable `task_groups`, with labels such as `收入证据`, `投放花费证据`, `效率辅助证据`, and `趋势辅助证据`.
- Analysis Workbench still displays a single `business_answer` generated from the merged ledger; task results are shown as supporting evidence, not as separate answers.
- Data limits are cleaned for the main product surface. Failed auxiliary evidence is described as missing auxiliary evidence; failed core evidence is described as insufficient core evidence. The main UI no longer exposes task ids, ledger ids, raw evidence refs, chart refs, raw SQL, trace paths, provider metadata, or raw chart JSON.
- Chart artifacts preserve ECharts-first rendering with image fallback and inherit question-ledger `evidence_refs` when the visualization result does not include direct refs.
- Same-thread follow-up still preserves evidence refs internally for context but displays business-readable continuity. Run-history restoration now rebuilds stale pre-H3 product results when raw P32 `evidence_task_results`, `question_evidence_ledger`, or `chart_artifacts` would otherwise be hidden or lost.
- Report Center independence was re-audited. The active report path remains `ReportPlan -> ReportEvidencePack -> EvidenceLedger -> one-pass ReportDocument -> validate/render/save`, and report code does not call `run_workspace_analysis`.
- Post-review fixes closed the live multi-task chart gap: sparse task-runner rows are transformed into a business-readable long chart table for visualization only, so explicit multi-task chart requests now produce grouped-bar ECharts artifacts while preserving the original execution/evidence data for answers and ledgers.
- Post-review fixes also removed the old consistency-path leak where `task_id`/`task_purpose` values such as `corefact_...` could be treated as business entities in the final product answer. The answer evidence and consistency layers now share entity detection, internal task markers are scrubbed, and repeated synonymous metric rows are de-duplicated for the main UI.
- Real DeepSeek acceptance was rerun on a temporary Chinese business workspace:
  - fast_fact: `最近30天哪个渠道收入最高？只回答事实。` completed in 14.68s, did not invoke the task runner, produced no chart, and answered that `私域社群` had the highest revenue.
  - multi-task chart: `最近30天按渠道比较收入和投放花费，用图表展示哪个渠道更值得关注？` completed in 56.42s through `evidence_task_runner` with 4 tasks, produced 1 ECharts `grouped_bar` chart artifact with `question_evidence_pack` refs, and produced one merged business answer without internal task ids.
  - deep judgment: `结合最近30天收入、投放花费和客服投诉，哪个渠道最需要优先优化？请给出证据和建议。` completed in 80.55s through `evidence_task_runner` with 4 tasks and produced 1 ECharts `grouped_bar` chart artifact. The answer is evidence-bound, but the phrasing can still be improved for “risk/optimization” decisions; keep this as a P33 answer-strategy polish item rather than a P32 evidence-task blocker.
  - Report Center live provider: `生成一份最近30天渠道经营复盘报告，覆盖收入结构、投放花费、客服投诉、关键风险和下一步建议。` completed in 21.88s with `provider_supplied=true`, `generation_flow=ledger_backed_report_center`, 4 ECharts-compatible chart artifacts, and opening summary: `最近30天（2026年6月）经营复盘显示，总收入达48.9万元，主要来自私域社群和直播间，合计占比72.0%；客户群体中成长型团队贡献最高，达38.0%。客服工单共1620件，物流延迟、售后退款和功能咨询各占33.3%，问题分布均衡。数据覆盖3张数据表、450行、12个字段，但缺少成本、利润和ROI字段，无法全面评估盈利质量。`
- Remaining follow-up risks after P32: full-provider multi-task analysis can still take roughly 50-80s, and comprehensive risk/optimization answers need a cleaner decision-orientation layer. These are follow-up polish/integration items, not blockers for closing P32's multi-evidence foundation.

## Acceptance Criteria

- Fast fact route still works and stays low-latency.
- Standard/deep Analysis Workbench questions can use multiple evidence tasks.
- Each evidence task executes at most one reviewed safe SQL statement.
- Multi-statement SQL from a provider is never executed directly.
- Successful and failed task evidence is represented clearly in the analysis ledger.
- Business Answer is generated once from the merged ledger.
- Report Center remains independent and keeps its existing report-plan/evidence-ledger/document path.
- Frontend renders one coherent answer with task/evidence summaries, not separate mini reports.
- Same-thread follow-ups keep using the current run/thread memory.
- Old active paths that conflict with P32 are removed.
- Full regression, frontend tests/build, artifact hygiene audit, old-path audit, and real DeepSeek verification pass before closeout.

Status: accepted for P32 closeout on 2026-07-07.
