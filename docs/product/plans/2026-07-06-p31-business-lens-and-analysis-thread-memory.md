# P31 Business Lens And Analysis Thread Memory

P31 addresses the real-use confusion found after P30 live testing: ambiguous time fields, cross-table questions that should use different business dates, and follow-up questions that currently create separate analysis runs instead of continuing one coherent analysis thread.

P31 keeps Analysis Workbench and Report Center as separate product experiences. Report Center keeps its full `ReportEvidencePack + EvidenceLedger + ReportDocument` path. Analysis Workbench gets a lighter thread-level version of the same idea: business-lens grounding, a compact question evidence ledger, and short-term analysis thread memory.

## Product Goals

1. Make business口径 explicit and reliable.
   - The question-understanding model still reads the user's natural Chinese question first.
   - `Business Lens` then grounds the model's intent into the current workspace data: business domain, metrics, dimensions, source tables/fields, time fields, default time range, and data limits.
   - The model may suggest meaning; deterministic semantic-layer checks must confirm whether it is computable.

2. Fix time-field ambiguity without making users think like database designers.
   - Single-domain questions use the metric's own business time field, such as revenue -> order date, spend -> spend date, support metrics -> ticket date, customer registration -> registration date.
   - Cross-domain questions may use multiple time fields in one answer. For example, channel revenue can use order date while channel spend uses spend date.
   - Missing time ranges default to the full available data range only when safe, and the answer must state the time口径.
   - Clarification remains for truly ambiguous metrics, trend grain, or broad questions such as "各渠道表现怎么样？".

3. Turn Analysis Workbench runs into coherent analysis threads.
   - A user follow-up inside an analysis result should continue the same thread whether the previous state is `waiting_for_clarification` or `completed`.
   - The system should combine original question, previous answer, existing evidence, system clarification, and the user's new input before continuing.
   - Follow-ups can be condition补充, reason questions, metric expansion, dimension expansion, related analysis, chart/report requests, or口径 correction.
   - Only explicit user intent such as "重新开始" or "新建分析" should create a new analysis topic from the follow-up box.

4. Keep the code clean and fast enough for real use.
   - Do not add a heavy new provider call for every request if the existing question-understanding output plus semantic layer is enough.
   - Keep Business Lens as a small structured grounding layer, not a keyword-heavy business-rule tree.
   - Reuse existing semantic layer, metric registry, evidence pack, audit, and ChartArtifact contracts where possible.
   - Delete old/conflicting compatibility paths instead of preserving them. P31 should leave one clean current Analysis Workbench continuation path, not old-run plus new-thread parallel behavior.

## Target Analysis Workbench Path

```text
user question
-> question understanding LLM
-> Business Lens grounding
-> clarification if the business口径 is still unsafe or incomplete
-> Question Evidence Ledger requirements
-> Evidence Agent SQL/calculation/tool calls
-> compact ledger facts, data limits, and evidence refs
-> Business Answer Agent writes Chinese answer from evidence
-> Evidence Auditor checks hard facts
-> optional ChartArtifact generation
-> save/update analysis thread
-> frontend displays answer, evidence, charts, time口径, and follow-up box
```

Follow-up path:

```text
user follow-up inside an analysis thread
-> load Analysis Thread Memory
-> context continuation step combines original question, previous answer, evidence, and new input
-> Business Lens updates metrics/dimensions/time口径
-> reuse existing evidence when enough; otherwise request additional evidence
-> write the next answer in the same thread
-> update thread memory and history card
```

## Core Contracts

`BusinessLens`

```json
{
  "business_domain": "channel_performance",
  "metrics": [
    {
      "label": "收入",
      "source_table": "orders_订单明细",
      "source_field": "revenue_订单收入",
      "time_field": "order_date_下单日期"
    },
    {
      "label": "投放花费",
      "source_table": "marketing_spend_营销投放",
      "source_field": "spend_投放花费",
      "time_field": "spend_date_投放日期"
    }
  ],
  "dimensions": ["channel_获客渠道"],
  "time_range": {"type": "full_data_range"},
  "time_policy_note": "收入按下单日期统计，投放花费按投放日期统计；未指定时间范围，默认使用完整数据范围。",
  "needs_clarification": false,
  "clarification_question": ""
}
```

`AnalysisThreadMemory`

```json
{
  "thread_id": "run_123",
  "original_question": "最近90天哪个渠道收入最高？",
  "turns": [],
  "current_business_lens": {},
  "evidence_refs": [],
  "answer_summary": "微信私域收入最高。",
  "pending_clarification": null
}
```

`QuestionEvidenceLedger`

```json
{
  "ledger_id": "question_ledger_123",
  "business_lens": {},
  "facts": [],
  "derived_metrics": [],
  "data_limits": [],
  "tool_calls": [],
  "chart_refs": []
}
```

## Implementation Slices

| Slice | Scope | Acceptance |
|---|---|---|
| P31-H1 | `[x]` Add Business Lens contracts and grounding from question-understanding output plus semantic layer. | Complete: revenue/order, spend/marketing, support/ticket, and customer/registration questions bind to the correct metric and time field. Cross-table revenue + spend questions can carry two time fields and avoid a global date-field clarification when safe. |
| P31-H2 | `[x]` Add Analysis Thread Memory and same-thread follow-up API/storage. | Complete: waiting clarification and completed analysis results can both receive follow-ups without creating a second independent history card. The old behavior that creates a separate run for clarification replies or follow-ups is removed from the active API/UI path. |
| P31-H3 | `[x]` Add lightweight Question Evidence Ledger and wire it into Evidence Agent / Business Answer / Evidence Auditor. | Complete: Analysis Workbench emits a safe ledger from existing evidence structures, answers receive ledger context/time/data limits, auditor checks hard facts against ledger first, and product results expose a safe summary without report-ledger coupling. |
| P31-H4 | `[x]` Frontend polish, realistic acceptance, live DeepSeek verification gating, cleanup, and docs closeout. | Complete: the UI shows one coherent analysis thread with original question, clarifications/follow-ups, resolved question, answer, evidence, charts, time口径, and compact history. Tests cover omitted-time, cross-table, waiting-clarification follow-up, completed-answer follow-up, and answer/evidence/chart ref continuity. Old-path audit proves obsolete duplicate-run follow-up behavior and active pending continuation adapters are removed. |

## P31-H1 Completion Notes

P31-H1 completed on 2026-07-06.

- Added `question_understanding.business_lens` with `BusinessLens`, `BusinessLensMetric`, and `BusinessLensDimension`.
- The implemented lens fields are `business_domain`, `metrics`, `dimensions`, `time_range`, `time_policy_note`, `needs_clarification`, `clarification_question`, and `data_limits`.
- Each metric carries `label`, `source_table`, `source_field`, `time_field`, and `metric_role`; each dimension carries `label`, `source_table`, and `source_field`.
- Question understanding remains first. Provider-backed or deterministic question understanding still parses the user's natural-language intent; Business Lens runs afterward and validates/grounds that intent through semantic metrics, dimensions, time fields, aliases, field meanings, source table/field metadata, and profile time ranges.
- Single-metric time binding is metric-owned: revenue-like metrics use the revenue table's order/sales/business date, spend-like metrics use the spend table's spend/marketing date, support metrics use ticket/support dates, and customer-registration counts use registration dates when supported by a customer id field.
- Cross-table revenue plus spend questions can now carry separate metric time fields in one lens. If the user omits the time range and profile ranges are available, the lens records a safe full-data default plus a `time_policy_note` explaining each metric date口径 instead of asking for one global time field.
- H1 repair tightened the safe default rule: if any metric-bound time field lacks profile `min/max`, Business Lens does not emit `full_data_range`, does not write a default-full-range `time_policy_note`, and keeps the request in clarification with a data limit explaining that the data profile is missing a safe time range.
- Clarification remains for truly broad or unsafe口径: broad channel-performance questions without a metric focus, missing computable metric fields, missing per-metric time fields, or unsupported customer-registration evidence.
- `AnalysisTask` now serializes `business_lens`, and `QuestionEvidencePack.task` preserves it for P31-H2/H3.
- The old global date-field clarification branch is no longer allowed to block a safe Business Lens cross-table revenue plus spend question; it remains only for cases where Business Lens cannot safely ground the口径.
- Verification passed:
  - `python3 -m pytest tests/test_business_lens.py tests/test_analysis_coordinator_data_understanding.py -q` (`18 passed`)
  - `python3 -m pytest tests/test_question_understanding_router.py tests/test_workspace_analysis_runner.py -q` (`67 passed`)
  - `python3 -m pytest tests/test_p25_real_usage_acceptance.py tests/test_p29_acceptance.py -q` (`5 passed`)

## P31-H2 Completion Notes

P31-H2 completed on 2026-07-06.

- Added `workspaces.analysis_thread_memory` as the clean same-thread contract.
- `AnalysisThreadMemory` now stores `thread_id`, `original_question`, `turns`, `current_business_lens`, `evidence_refs`, `answer_summary`, `pending_clarification`, `latest_status`, and `latest_resolved_question`.
- Each turn stores `turn_id`, `user_input`, `resolved_question`, `status`, `answer_summary`, `business_lens`, `evidence_refs`, and `created_at`.
- Waiting clarification follow-ups use the original run id as `thread_id`, combine the original question with the user's supplement, rerun the safe analysis chain, append a new turn, and update either the completed answer summary or the same thread's `pending_clarification`.
- Completed-run follow-ups combine the original question, latest resolved question, previous answer summary, existing business lens/evidence refs, and the user's new message before rerunning the safe chain. The new answer is appended as another turn on the same thread.
- Added `POST /api/workspaces/{workspace_id}/runs/{run_id}/follow-ups` with body `{ "message": "..." }`.
- `POST /api/workspaces/{workspace_id}/runs` is now only the new-analysis entry. The old `pending_run_id` continuation body is no longer an active continuation API, and the frontend no longer sends it.
- The frontend's 用户补充 and 继续追问 forms call the same-thread follow-up API with the current `run_id`. The old `buildFollowUpQuestion` path that produced `基于上一轮分析继续追问...` as a new ordinary `user_question` was removed.
- History remains one analysis thread/card after follow-up because the same run JSON is updated in place and `WorkspaceRunStore.list_runs()` sees one `run_id`.
- The old active `PendingClarificationStore` / `pending_run_id` continuation storage path has been deleted; waiting clarification state now lives in `AnalysisThreadMemory.pending_clarification` and continues through the same run id.
- P31-H2 did not add long-term memory, vector memory, cross-workspace user preferences, or Report Center merging.
- Verification passed:
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_api.py tests/test_workspace_run_history_api.py -q` (`76 passed`)
  - `python3 -m pytest tests/test_business_lens.py tests/test_analysis_coordinator_data_understanding.py -q` (`18 passed`)
  - `python3 -m pytest tests/test_p25_real_usage_acceptance.py tests/test_p29_acceptance.py -q` (`5 passed`)
  - `cd frontend && npm test` (`71 passed`)
  - `cd frontend && npm run build` passed

## P31-H3 Completion Notes

P31-H3 completed on 2026-07-06.

- Added `workspaces.question_evidence_ledger` for the Analysis Workbench lightweight ledger. It intentionally does not reuse or call Report Center's full `ReportEvidenceLedger` / report document path.
- The ledger fields are `ledger_id`, `business_lens`, `time_policy_note`, `facts`, `derived_metrics`, `data_limits`, `tool_calls`, `evidence_refs`, `chart_refs`, `source_pack_id`, and `confidence`.
- Each fact includes `fact_id`, `label`, `value`, `unit`, `dimension`, `source_columns`, `source_row_refs`, and `evidence_ref`. Facts are built from `QuestionEvidencePack` and reviewed execution rows, not model prose.
- Derived metrics are projected from existing fact payload derived metrics, preserving `metric_id`, `label`, `formula`, `value`, `source_fact_ids` when row refs are available, `source_columns`, and `evidence_ref`.
- Missing or failed evidence produces `data_limits` and an empty facts list instead of fake facts.
- Evidence Agent emits `question_evidence_ledger` for fast-fact and standard/deep paths, and cached question evidence rebuilds the ledger from cached reviewed rows.
- Business Answer Agent passes a sanitized ledger into the provider prompt and preserves ledger `time_policy_note` plus `data_limits` after deterministic answer repair. The model can still write natural recommendations/inferences, but hard facts come from the ledger/execution evidence.
- Evidence Auditor uses ledger facts and derived metrics first for hard factual claims. Recommendations and business interpretations remain `reasonable_inferences` when supported by the ledger context and do not need to appear word-for-word as hard facts.
- `product_result` exposes top-level `question_evidence_ledger` and `evidence.ledger_summary`; SQL, trace paths, provider metadata, API keys/secrets, local absolute paths, and raw provider/tool metadata are scrubbed from the ledger UI payload.
- `AnalysisThreadMemory.evidence_refs` stores compact refs such as `question_evidence_ledger:<ledger_id>` and ledger evidence refs, not the whole ledger body per turn.
- H3 review tightened three edges found during full regression: Product Result enriches an existing ledger with chart artifact refs created later in the workflow; `business_answer` prompt rendering treats an absent ledger as an empty optional context for older/no-ledger callers; ledger hard-fact matching accepts Chinese display units such as `5.7 万`, ignores time-window numbers such as `最近90天`, and still requires metric/dimension alignment.
- Report Center remains independent on `ReportEvidencePack + EvidenceLedger + ReportDocument`.
- Verification passed:
  - `python3 -m pytest tests/test_question_evidence_ledger.py tests/test_evidence_agent.py -q` (`13 passed`)
  - `python3 -m pytest tests/test_business_answer_quality.py tests/test_evidence_auditor_claim_categories.py -q` (`23 passed`)
  - `python3 -m pytest tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py -q` (`88 passed`)
  - `python3 -m pytest tests/test_business_lens.py tests/test_analysis_coordinator_data_understanding.py -q` (`18 passed`)
  - `python3 -m pytest tests/test_workspace_api.py tests/test_workspace_run_history_api.py -q` (`25 passed`)
  - `python3 -m pytest` (`664 passed, 13 skipped`)
  - `cd frontend && npm test` (`71 passed`)

## P31-H4 Completion Notes

P31-H4 completed on 2026-07-06.

- Frontend thread UX now renders a coherent Analysis Workbench thread instead of visually separate runs. The main result area shows original question, system understanding, resolved question, clarification/follow-up turns, Business Lens time口径, business answer, safe ledger/evidence summary, chart artifacts, and collapsed technical details.
- Evidence display now includes a compact safe `ledger_summary` with ledger id, confidence, time口径, selected facts/derived metrics, data limits, and chart refs. It does not expose raw SQL, trace path, provider metadata, API keys, local paths, or raw ledger JSON in the main UI.
- Same-thread follow-up UX is the only active UI path: waiting clarification and completed-answer follow-ups call `POST /api/workspaces/{workspace_id}/runs/{run_id}/follow-ups`. Completed follow-ups no longer overwrite the top-level new-question box with the follow-up text.
- Cleanup removed the old active `pending_run_id` continuation path from API request schema, Analysis Runner, graph state/workflow, Product Result, frontend types, and stale tests. `workspaces/pending_clarification_store.py` and its tests were deleted. `POST /runs` is now a new-analysis-only entry; one negative API boundary test proves the old pending body is rejected.
- Realistic acceptance coverage is in focused regression tests: omitted-time questions bind safe metric time fields and state full-data口径; cross-table revenue plus spend questions keep per-metric time fields; waiting clarification follow-up completes in the same run; completed answer follow-up appends turns to the same run; and chart refs are carried through the question evidence ledger/product evidence summary.
- Report Center remains an independent report product path on `ReportEvidencePack + EvidenceLedger + ReportDocument`. P31 did not call Analysis Workbench report paths from Report Center and did not add real Feishu/DingTalk/WeCom/Tencent Docs/Power BI/Word/PPT connectors.
- Live DeepSeek verification was skipped honestly because the local environment had `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=False`, `INSIGHTFLOW_PRODUCT_LIVE_MODE=False`, and no `DEEPSEEK_API_KEY`.
- Verification passed:
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_api.py tests/test_workspace_run_history_api.py -q` (`73 passed`)
  - `python3 -m pytest tests/test_business_lens.py tests/test_question_evidence_ledger.py tests/test_product_result_builder.py -q` (`52 passed`)
  - `python3 -m pytest tests/test_p25_time_range_defaults.py tests/test_p29_acceptance.py -q` (`16 passed`)
  - `python3 -m pytest tests/test_clarification_routing.py tests/test_workflow.py tests/test_workspace_analysis_runner.py tests/test_workspace_api.py tests/test_workspace_run_history_api.py -q` (`81 passed`)
  - `cd frontend && npm test` (`72 passed`)
  - `cd frontend && npm run build` passed
  - `python3 -m pytest -q` (`658 passed, 13 skipped`)

## Cleanup Policy

P31 should simplify the product path, not add a second layer beside the old one.

- Remove or rewrite old follow-up/clarification continuation code that creates a new independent run when the user is continuing inside an existing analysis thread.
- Remove stale tests that only protect the old duplicate-run behavior.
- Remove dead adapters, fallback branches, temporary compatibility fields, and frontend rendering branches that become unreachable after same-thread follow-up is implemented.
- Keep historical documentation, but current docs must not present old duplicate-run continuation, old stitched report behavior, old chart/planner/tool paths, or old mock/action/eval paths as active guidance.
- If a helper remains useful, migrate the minimal helper into the new Business Lens / Thread Memory / Question Evidence Ledger modules and delete the old entry point.
- Final closeout must include an old-path scan and tracked-artifact audit. Generated workspaces, reports, charts, traces, databases, `.next`, `node_modules`, caches, and local `.env` files must not be staged.

## Expected Behavior

Question:

```text
各渠道投放花费和收入表现怎么样？
```

Expected handling:

```text
收入按订单表的下单日期统计；投放花费按营销投放表的投放日期统计。
如果用户没有指定时间范围，默认使用各自数据表的完整可用时间范围，并在答案中说明。
```

Follow-up:

```text
为什么自然流量效率更高？
```

Expected handling:

```text
The follow-up stays in the same analysis thread. The system reuses the prior channel revenue/spend evidence when enough; if explanation needs additional customer/order mix evidence, it fetches extra evidence and appends a new answer turn to the same thread.
```

## Non-Goals

- Do not build long-term personal memory, cross-workspace user preference memory, or vector memory.
- Do not merge Report Center into Analysis Workbench or stitch analysis answers into reports.
- Do not add real Feishu/DingTalk/WeCom/Tencent Docs/Power BI publishing in P31.
- Do not make Business Lens a broad keyword-heavy business rule tree.
- Do not let the LLM directly choose SQL fields or dates without semantic-layer validation.
- Do not keep old run-continuation compatibility paths if they conflict with the new single-thread follow-up model.
- Do not preserve duplicate active APIs or UI branches for "new run follow-up" just in case. If the new same-thread contract replaces the behavior, delete the old active path.

## Verification

- Focused backend tests for Business Lens grounding, per-metric time bindings, and cross-table time口径.
- Backend tests for same-thread follow-up from both `waiting_for_clarification` and `completed` states.
- Evidence/answer tests proving time口径 appears in the result and unsupported facts remain data limits.
- Frontend tests for one history card per analysis thread, follow-up turns, and compact display.
- Cleanup tests or boundary assertions proving old duplicate-run follow-up behavior is not active.
- Full `python3 -m pytest`, `cd frontend && npm test`, and `cd frontend && npm run build`.
- Opt-in live DeepSeek test showing: question, follow-up turns, path, answer, evidence, chart behavior, and elapsed time.
