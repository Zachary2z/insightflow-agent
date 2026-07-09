# P29 Fast Fact And Risk Routing Stabilization

Status: Complete; H1-H4 complete

P29 fixes the two product issues exposed by real DeepSeek testing after P28:

1. Simple factual questions still route through the full standard/deep analysis path and take 20-30+ seconds.
2. Normal business questions can be rejected too early by provider question understanding when they contain words such as 加预算, 最值得, 优先复盘, or 只回答数字和口径.

P29 is intentionally before external business-tool export work. External tools will feel unreliable if the product cannot first route simple facts quickly and avoid rejecting ordinary business analysis questions.

## Goals

- Make obvious low-risk factual questions reliably use the `fast_fact` path.
- Keep fast facts evidence-backed: SQL review, SQL execution, evidence validation, fact payloads, history persistence, and technical details remain required.
- Skip heavyweight Business Answer generation and optional visualization on fast facts unless the user explicitly requests them.
- Reduce false rejections from question understanding by separating business analysis risk from real external action risk.
- Keep complex judgment, recommendation, diagnosis, report, and multi-metric tradeoff questions on the full path.
- Preserve Chinese-first product output and current Analysis Workbench / Report Center separation.
- Keep code clean: delete stale route/risk compatibility code and old tests that conflict with the current path.

## Non-Goals

- Do not build Word/PPT/PDF/Feishu/DingTalk/WeCom/Tencent Docs integrations in P29.
- Do not add vector search, semantic similar-question cache, Redis, Celery, WebSocket, or provider timeout controls.
- Do not make a broad keyword-heavy business rule tree.
- Do not replace SQL review, SQL execution, or evidence validation with model judgment.
- Do not make fast facts handle advice, strategy, budget, causal, report, or multi-metric judgment questions.

## Current Problem From Live Testing

Real DeepSeek tests on 2026-07-05 showed:

- `最近90天哪个渠道收入金额最高？` completed but routed as `standard_analysis`, called Business Answer, and took about 34 seconds.
- `最近90天哪个门店销售额最高？` completed but routed as `standard_analysis`, called Business Answer, and took about 20 seconds.
- `最近90天总销售额是多少？只回答数字和口径。` was rejected before SQL generation, even though it is a safe factual query.
- A multi-metric channel question completed correctly on `deep_judgment`, but took about 52 seconds.

The intended product behavior is:

- simple totals/rankings/counts/trends should feel fast;
- ordinary business advice questions should analyze with evidence boundaries, not be rejected as unsafe;
- only real high-risk actions should stop or require explicit confirmation.

## Design

### H1: Local Fast Fact Gate Before Provider Risk Rejection

Add a small local gate before provider-backed question-understanding rejection can stop a run.

The gate should identify only obvious safe factual questions:

- total/sum/count/average questions;
- highest/lowest/top ranking questions;
- simple trend questions when the time grain is clear or safely inferable;
- one metric, optional one dimension;
- no advice, budget action, reason, diagnosis, strategy, report, comparison tradeoff, external action, write/send/update/delete/publish intent.

If the gate is confident, mark the run as `fast_fact_candidate` and allow it to proceed to the existing safe evidence path. If the gate is uncertain, do not force fast path; use the normal P28 route.

The gate must not be a table-specific rule tree. It should use generic intent signals plus semantic-layer/profile evidence that a metric and optional dimension can be matched.

### H2: Stable Fast Fact Execution Path

When a question is accepted as `fast_fact`, the path should be:

```text
local fast fact gate
-> minimal data understanding / semantic match
-> SQL candidate or deterministic metric SQL
-> SQL review
-> SQL execution
-> evidence validation / fact payload
-> fast_fact_composer
-> save result
```

Fast facts should skip:

- Business Answer provider generation;
- deep Evidence Planning unless needed for safe SQL construction;
- optional visualization unless the user explicitly asks for a chart;
- heavy judgment-style audit beyond factual evidence validation.

The result must still include a clear Chinese `business_answer`, evidence table preview, technical SQL details, route metadata, and history persistence.

H2 completed on 2026-07-05:

- Fast facts now keep the safe execution chain: Data Understanding / Local Fast Fact Gate -> Evidence Agent SQL candidate -> SQL review -> SQL execution -> evidence validation / fact payload -> `fast_fact_composer` -> saved result and history.
- Fast facts skip the Business Answer provider path and standard/deep judgment answer generation. The workflow now lazily constructs Business Answer and Visualization providers only when those nodes execute, so a no-chart fast fact does not even initialize those heavy providers.
- Fast facts still preserve `business_answer`, `analysis_route`, evidence table preview, `question_evidence_pack`, `fact_payload`, technical SQL details, audit result, data version, normalized question, and history restoration.
- Explicit chart requests still allow visualization after the fast fact answer; ordinary fast facts skip visualization.
- Added deterministic coverage for `最近90天哪个渠道收入最高？` without `initial_sql`, `本月哪个门店销售额最高？`, omitted-time full-data default when one safe time field exists, provider request count remaining zero, lazy provider construction, and full history restoration.

### H3: Business Risk Policy Split

Replace broad early rejection with a clearer risk split:

- Safe factual query: answer with evidence.
- Business advice / judgment: allow full analysis, require evidence boundaries and caveats.
- Real external action: reject or require confirmation. Examples include sending messages, writing back to systems, deleting/updating data, publishing externally, creating tickets, moving money, or modifying budgets in a real system.

Normal phrasing such as 加预算, 最值得, 优先复盘, 只回答数字和口径 should not be rejected by itself. These are analysis requests unless the user asks the system to actually execute an external action.

H3 completed on 2026-07-05:

- Safe business advice and judgment questions stay on the full evidence-backed path and are not rejected just because they mention 加预算, 最值得, 优先复盘, or 风险边界.
- True external actions such as adjusting a real budget and sending notifications are rejected before SQL generation/review/execution.
- Provider false `unsafe_operation` flags are relaxed only when local safety checks confirm the wording is analysis/advice rather than a real external action.

### H4: Acceptance Tests And Live DeepSeek Verification

Add deterministic tests first, then implementation, then focused/full verification.

Test questions must not hard-code only 最近90天. Use interchangeable time ranges so the route does not overfit one phrase:

- `最近30天总销售额是多少？`
- `最近90天哪个渠道收入金额最高？`
- `本月哪个门店销售额最高？`
- `收入最高的客户分群是谁？` when no time range is specified and the workspace has one safe time field, use full available data range.
- `最近90天按渠道比较收入、投放金额和投放效率，哪个渠道表现最好？` should stay full path.
- `最近30天哪个渠道最值得加预算？请给证据和风险边界。` should stay full path and must not be rejected.
- `把预算调整到私域社群并发送通知。` should be treated as a real external action request and rejected or require confirmation.
- `最近90天哪个渠道收入最高？给我画图。` can stay fast_fact and generate a chart only because the user explicitly requested one.

Live DeepSeek acceptance should run when local credentials and opt-in flags are available. The live output record must include:

- asked question;
- start time, end time, elapsed seconds;
- route;
- provider-called flags;
- key trace nodes;
- final answer;
- evidence rows;
- whether chart generation was requested or skipped.

H4 completed on 2026-07-05:

- Added `tests/test_p29_acceptance.py` as the deterministic P29 acceptance matrix. It records route/routing strategy, provider call count, Business Answer provider use, SQL generation/execution, evidence rows/fact payload summary, answer summary, chart generation, trace nodes, and elapsed milliseconds for each case.
- Deterministic acceptance results:
  - `最近30天总销售额是多少？` -> `fast_fact`; no Business Answer provider; SQL reviewed/executed; evidence rows/fact payload present; no chart.
  - `最近90天哪个渠道收入金额最高？` -> `fast_fact`; no Business Answer provider; SQL/evidence present; leader `私域社群`; no chart.
  - `本月哪个门店销售额最高？` -> `fast_fact`; `this_month`; no Business Answer provider; SQL/evidence present; no chart.
  - `收入最高的客户分群是谁？` -> `fast_fact`; safe `full_data_range`; no Business Answer provider; SQL/evidence present; no chart.
  - `最近90天按渠道比较收入、投放金额和投放效率，哪个渠道表现最好？` -> `deep_judgment`; Business Answer provider called; SQL/evidence/audit present; recommendations/caveats retained.
  - `最近30天哪个渠道最值得加预算？请给证据和风险边界。` -> `deep_judgment`; Business Answer provider called; SQL/evidence/audit present; not treated as unsafe external action.
  - `把预算调整到私域社群并发送通知。` -> `reject`; stopped before SQL; no provider call, SQL, evidence rows, or chart.
  - `最近90天哪个渠道收入最高？给我画图。` -> `fast_fact`; no Business Answer provider; SQL/evidence present; chart generated because explicitly requested.
- H4 found one deterministic fallback gap: without a provider, `最近30天哪个渠道最值得加预算？请给证据和风险边界。` could still clarify for a missing metric. The fix narrowly defaults time-bounded channel budget advice to existing investment-efficiency evidence metrics (`销售额`, `花费`, `ROAS`) while keeping ambiguous no-time budget advice in clarification.
- Live DeepSeek tests now only run when the current process explicitly sets both `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1` and `INSIGHTFLOW_PRODUCT_LIVE_MODE=1`, and a DeepSeek key is available. A normal pytest run produced an explicit skip (`3 passed, 2 skipped` for live/product files). The opt-in command ran real DeepSeek and passed (`5 passed in 64.63s`).

## Expected Outcome

After P29:

- Simple fact questions should reliably take the fast path and avoid unnecessary Business Answer model calls.
- Fast fact answers should be concise, Chinese, evidence-backed, and saved to history.
- Business advice questions should no longer be mistakenly rejected just because they mention 加预算 or 优先复盘.
- Full judgment questions should still use the P28 complex path with model reasoning and deterministic evidence audit.
- The product will be better prepared for later external document/export/tool integrations because route intent and risk policy will be more stable.

## Required Verification

```bash
python3 -m pytest tests/test_p29_acceptance.py -q
python3 -m pytest tests/test_analysis_route_policy.py tests/test_workspace_analysis_runner.py tests/test_fast_fact_path.py -q
python3 -m pytest tests/test_question_understanding_router.py tests/test_provider_backed_question_understanding.py tests/test_analysis_coordinator_data_understanding.py -q
python3 -m pytest tests/test_business_answer_quality.py tests/test_evidence_auditor_claim_categories.py tests/test_product_result_builder.py -q
python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_product_live_mode.py -q
```

Run opt-in live DeepSeek checks when available. Skipped live tests are not provider proof:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_PRODUCT_LIVE_MODE=1 python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_product_live_mode.py -q
```

Final P29-H4 verification on 2026-07-05:

- `python3 -m pytest tests/test_p29_acceptance.py -q` -> `4 passed`
- `python3 -m pytest tests/test_analysis_route_policy.py tests/test_workspace_analysis_runner.py tests/test_fast_fact_path.py -q` -> `73 passed`
- `python3 -m pytest tests/test_question_understanding_router.py tests/test_provider_backed_question_understanding.py tests/test_analysis_coordinator_data_understanding.py -q` -> `48 passed`
- `python3 -m pytest tests/test_business_answer_quality.py tests/test_evidence_auditor_claim_categories.py tests/test_product_result_builder.py -q` -> `53 passed`
- `python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_product_live_mode.py -q` -> `3 passed, 2 skipped`
- `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_PRODUCT_LIVE_MODE=1 python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_product_live_mode.py -q` -> `5 passed`
