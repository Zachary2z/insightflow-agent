# P18 Business Answer Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make analysis and report outputs consistent, evidence-bound, and business-usable across general datasets without hardcoding the current sample tables.

**Architecture:** Add one lightweight consistency layer between execution evidence and product-facing output. The layer should infer the user's decision need, check whether evidence is sufficient, reconcile `business_answer`, chart annotation, and report summary, and add caveats when a confident business recommendation is not supported. Keep generation flexible through the provider, but make deterministic code own safety, sufficiency, and consistency checks.

**Tech Stack:** Python, FastAPI workspace backend, LangGraph workflow, DeepSeek provider path, Next.js frontend, pytest, Vitest.

---

## Product Problem

P16 gave InsightFlow one clean `business_answer` shape. P17 cleaned old demo/mock/action paths. Real Chinese business data testing then exposed a new product-quality issue:

- `headline` / `direct_answer` may select one entity.
- `why` may cite the first evidence row, which may represent another entity.
- `recommendations` may suggest a budget action even when the answer says evidence is insufficient.
- `chart_artifacts[].business_annotation` may independently claim a different winner.
- report sections and executive summaries inherit these conflicts.

This is not a sample-data bug. It is a general business-analysis problem: questions like "best", "worth focusing on", "increase budget", "reduce budget", "why", and "management report" require a clear decision basis and enough comparative evidence.

## Product Decision

P18 is now the next phase before real external SaaS integrations. External tool calling remains important, but it should not be expanded until business conclusions are reliable; otherwise external tools only publish inconsistent conclusions faster.

P18 must remain general:

- Do not hardcode table names such as `orders`, `customers`, `marketing_spend`, or `support_tickets`.
- Do not hardcode current sample values such as specific Chinese channel names or customer segments.
- Do not build a large keyword-heavy business rules tree.
- Do not restore old eval, Streamlit, action workflow, mock SaaS, chart-agent, visualization-planner, or chart-tool paths.

## Target Output Behavior

For single-metric ranking questions:

```text
Question: 最近90天哪个渠道收入最高？
Answer: 微信私域收入最高。Evidence and chart annotation point to the same entity and metric.
```

For multi-metric decision questions:

```text
Question: 按客户分群看收入、订单量和客单价，哪个分群最值得重点运营？
Answer: If the goal is revenue scale, choose 成长型团队; if the goal is high-value account expansion, choose 高价值企业. The recommendation states the chosen decision basis or presents the tradeoff.
```

For insufficient comparison evidence:

```text
Question: 最近90天哪个渠道 ROI 最高，哪个渠道应该减少预算？
Evidence: only one returned row.
Answer: The returned row shows the current top ROI channel, but it is not enough to determine which channel should reduce budget. No unsupported budget recommendation is generated.
```

For reports:

```text
Executive summary = concise management-level synthesis of consistent section answers.
Section answer = conclusion, direct answer, why, evidence, recommendations, caveats.
Chart annotation = fact-only or aligned with the final section answer.
Technical appendix = SQL, rows, trace, provider metadata, and internal prompts.
```

## Code Quality Requirements

P18 must make the code cleaner, not more tangled.

- Prefer one new focused module: `workspaces/answer_consistency.py`.
- Keep `workspaces/product_result_builder.py` as an orchestrator/assembler.
- Keep helpers small and pure where practical.
- Use plain `dict`, `list`, and small dataclasses only if they clearly improve readability.
- Avoid global mutable state.
- Avoid large prompt strings outside `llm_ops/prompt_registry.py`.
- Do not add a generic rules engine.
- Do not add table-specific or sample-specific business branches.
- Tests should cover product behavior, not private implementation details.

Recommended helper boundary:

```python
def apply_answer_consistency(
    *,
    user_question: str,
    business_answer: dict[str, Any],
    execution_result: dict[str, Any],
    evidence_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a P16 business_answer that is internally consistent and evidence-bound."""
```

```python
def safe_chart_annotation(
    *,
    annotation: str,
    business_answer: dict[str, Any],
    execution_result: dict[str, Any],
) -> str:
    """Return a chart annotation that does not contradict the final business answer."""
```

## Files

Create:

- `workspaces/answer_consistency.py`
- `tests/test_answer_consistency.py`

Modify:

- `workspaces/product_result_builder.py`
- `workspaces/report_runner.py`
- `workspaces/report_markdown.py` if report Markdown needs summary wording cleanup
- `agents/visualization_agent.py` only if chart prompt context must include the final answer later; prefer product-result-level reconciliation first
- `llm_ops/prompt_registry.py` if prompt wording must require decision basis more clearly
- `llm_ops/structured_output.py` only if a schema-level guard is truly needed
- `tests/test_product_result_builder.py`
- `tests/test_workspace_report_runner.py`
- `tests/test_business_answer_quality.py`
- `tests/test_deepseek_provider_structured_output.py` if prompt/schema contract changes

Do not modify frontend first unless backend output exposes a new field. A later UI task may display decision basis, but P18 should work with the current P16 contract.

## Task Queue

| Task | Scope | Status |
|---|---|---|
| P18-H1 | Add failing tests for multi-metric conflict, insufficient comparison evidence, and chart annotation conflict | Complete |
| P18-H2 | Implement lightweight answer consistency helpers and apply them in product result builder | Complete |
| P18-H3 | Make chart annotation fact-only or aligned with the final business answer | Complete |
| P18-H4 | Make report sections and executive summaries reuse consistency-checked answers | Complete |
| P18-H5 | Tighten provider prompts/validation only where needed, without adding rigid templates | Complete |
| P18-H6 | Run focused/full regression, real DeepSeek acceptance, artifact hygiene, and documentation closeout | Complete |

## P18-H1 Test-First Coverage

- [ ] Add `tests/test_answer_consistency.py::test_multi_metric_best_question_returns_tradeoff_instead_of_conflicting_single_winner`.

Use rows where the first metric leader and second metric leader differ:

```python
execution_result = {
    "success": True,
    "columns": ["segment", "total_revenue", "order_count", "avg_revenue_per_order"],
    "rows": [
        ["成长型团队", 2798216.93, 628, 4455.76],
        ["高价值企业", 2158510.79, 340, 6348.56],
    ],
}
```

Expected behavior:

- final answer should not say only `高价值企业最值得重点运营` without a caveat or tradeoff;
- answer should mention both `成长型团队` and `高价值企业`, or state the chosen decision basis clearly;
- `why` must not contradict `headline`.

- [ ] Add `tests/test_answer_consistency.py::test_budget_reduction_question_with_single_row_does_not_generate_unsupported_recommendation`.

Use one-row ROI evidence:

```python
execution_result = {
    "success": True,
    "columns": ["channel", "total_revenue", "total_spend", "roi"],
    "rows": [["自然流量", 452191.41, 26255.44, 16.22]],
}
```

Expected behavior:

- direct answer may say the returned row shows `自然流量` ROI;
- answer must not determine which channel should reduce budget;
- `recommendations` must be empty or explicitly request more complete comparison evidence;
- `caveats` must mention insufficient comparison evidence.

- [ ] Add `tests/test_answer_consistency.py::test_chart_annotation_is_sanitized_when_it_names_a_different_winner`.

Expected behavior:

- if business answer chooses or explains entity A but chart annotation claims entity B is "最值得/最佳/应该", annotation is replaced with a fact-only description or a statement aligned with the final answer.

- [ ] Add `tests/test_workspace_report_runner.py` coverage proving report sections use consistency-checked `business_answer`.

Expected behavior:

- section `business_answer` does not carry conflicts;
- executive summary does not duplicate long direct answers or internal section prompt text.

Run after adding tests:

```bash
python3 -m pytest tests/test_answer_consistency.py tests/test_product_result_builder.py tests/test_workspace_report_runner.py -q
```

Expected before implementation: focused tests fail for missing module or current conflicting behavior.

## P18-H1 Completion Notes

Completed on 2026-06-30 as RED test coverage only; no production consistency layer was implemented in H1.

- Added `tests/test_answer_consistency.py::test_multi_metric_best_question_returns_tradeoff_instead_of_conflicting_single_winner`.
  - Proves current `build_business_answer()` accepts a P16-shaped answer that declares one segment as the winner while `why` anchors on a different first-row segment and does not explain metric tradeoff or decision basis.
- Added `tests/test_answer_consistency.py::test_budget_reduction_question_with_single_row_does_not_generate_unsupported_recommendation`.
  - Proves current `build_business_answer()` accepts a budget reduction recommendation even when the returned ROI evidence has only one row and cannot identify which channel should reduce budget.
- Added `tests/test_answer_consistency.py::test_chart_annotation_is_sanitized_when_it_names_a_different_winner`.
  - Proves current `build_product_analysis_result()` passes through a chart `business_annotation` that names a different strongest object and uses recommendation language independent of the final `business_answer`.
- Added `tests/test_workspace_report_runner.py::test_report_does_not_inherit_conflicting_section_answer_or_repeat_long_direct_answer`.
  - Proves the report path accepts the same internally conflicting P16-shaped section answer and can propagate the long direct answer into `executive_summary`.

Focused RED verification:

- `python3 -m pytest tests/test_answer_consistency.py -q` -> expected `3 failed`.
- `python3 -m pytest tests/test_answer_consistency.py tests/test_product_result_builder.py tests/test_workspace_report_runner.py -q` -> expected `4 failed, 24 passed`.

Current failure points are intentional and should be addressed by P18-H2 through P18-H4:

- missing multi-metric decision-basis/tradeoff reconciliation;
- missing insufficient-comparison guard for budget reduction advice;
- missing chart annotation alignment/sanitization;
- missing report-level consistency protection and concise executive-summary handling.

## P18-H2 Backend Consistency Layer

- [x] Create `workspaces/answer_consistency.py`.

Initial responsibilities:

- normalize rows to dictionaries using execution columns;
- infer whether the question is comparative/advisory/report-like using small generic markers;
- detect insufficient comparison evidence for questions that require both winners and losers;
- detect entity disagreement across `headline`, `direct_answer`, `why`, `recommendations`, and evidence rows when the text contains strong recommendation words;
- add caveats and remove unsupported recommendations when evidence is insufficient;
- build a tradeoff answer when multiple numeric metrics have different leaders.

Keep marker lists small and generic. Examples of acceptable generic markers:

```python
ADVICE_MARKERS = ("应该", "建议", "最值得", "重点", "加预算", "减少预算", "increase", "reduce", "recommend")
COMPARISON_MARKERS = ("哪个", "最高", "最低", "对比", "排名", "best", "top", "lowest")
```

Examples of unacceptable hardcoding:

```python
if table_name == "customers":
if segment == "成长型团队":
if channel == "微信私域":
```

- [x] Apply the helper in `workspaces/product_result_builder.py` after candidate business answer normalization and before returning the answer.

Target flow:

```text
build_business_answer
-> SQL failure answer if needed
-> normalize usable provider answer or build fallback
-> apply_answer_consistency
-> return P16 business_answer
```

- [x] Run focused tests:

```bash
python3 -m pytest tests/test_answer_consistency.py tests/test_product_result_builder.py tests/test_business_answer_quality.py -q
```

Expected: pass.

## P18-H2 Completion Notes

Completed on 2026-06-30 as the lightweight `business_answer` consistency layer only.

- Added `workspaces/answer_consistency.py` with `apply_answer_consistency(...)`.
  - Normalizes execution rows into dictionaries from returned columns and rows.
  - Uses small generic advice/comparison/budget markers, without table-specific, field-specific, channel-specific, segment-specific, or sample-data branches.
  - Detects multi-metric decision conflicts when different numeric metrics have different leading objects, then rewrites the answer into a tradeoff/decision-basis answer.
  - Formats tradeoff text as business-readable metric sentences instead of raw `field=value` parameter dumps.
  - Detects single-row budget-reduction risk and removes unsupported budget-reduction recommendations, adding a comparison-evidence caveat instead.
- Applied the helper inside `workspaces/product_result_builder.build_business_answer()` for both usable provider answers and fallback-built answers before returning the P16 contract.
- Preserved the P16 `business_answer` shape: `headline`, `direct_answer`, `why`, `evidence_bullets`, `recommendations`, `caveats`, and `confidence`.

Follow-up H2 wording fix on 2026-06-30:

- Strengthened `tests/test_answer_consistency.py::test_multi_metric_best_question_returns_tradeoff_instead_of_conflicting_single_winner` so tradeoff answers cannot contain raw `total_revenue=`, `order_count=`, or `avg_revenue_per_order=` fragments.
- Updated tradeoff wording to sentences such as `按收入看，成长型团队领先，数值为 2,798,216.93。`, using a small generic metric label helper for revenue, orders, average revenue per order, ROI, and spend.
- Tightened tradeoff formatting so Chinese output avoids extra word spacing, English output uses English metric labels, and numeric values avoid scientific notation while keeping readable thousand separators.

Focused H2 verification:

- `python3 -m pytest tests/test_answer_consistency.py::test_multi_metric_best_question_returns_tradeoff_instead_of_conflicting_single_winner tests/test_answer_consistency.py::test_english_tradeoff_answer_uses_english_metric_labels_and_readable_numbers tests/test_answer_consistency.py::test_budget_reduction_question_with_single_row_does_not_generate_unsupported_recommendation tests/test_product_result_builder.py tests/test_business_answer_quality.py -q` -> `30 passed`.
- `python3 -m pytest tests/test_answer_consistency.py -q` -> expected `3 passed, 1 failed`; remaining failure is chart annotation alignment for P18-H3.
- `python3 -m pytest tests/test_product_result_builder.py tests/test_business_answer_quality.py tests/test_workspace_report_runner.py -q` -> expected `38 passed, 1 failed`; remaining failure is report section/executive-summary consistency for P18-H4.

## P18-H3 Chart Annotation Alignment

- [x] Update `build_chart_artifacts()` in `workspaces/product_result_builder.py` to pass chart annotations through `safe_chart_annotation()`.

Preferred behavior:

- keep a factual annotation if it only describes chart data;
- remove or rewrite an annotation that claims a different "best/should/recommend" conclusion from the business answer;
- avoid asking the visualization agent to make independent business recommendations.

- [x] Provider prompt changes were not needed; product-result-level reconciliation handles H3 without changing `llm_ops/prompt_registry.py`.

- [x] Run focused tests:

```bash
python3 -m pytest tests/test_answer_consistency.py tests/test_visualization_agent_external_tools.py tests/test_deepseek_provider_structured_output.py -q
```

Expected: pass.

## P18-H3 Completion Notes

Completed on 2026-06-30 as chart annotation alignment only.

- Added `safe_chart_annotation(...)` in `workspaces/answer_consistency.py`.
  - Keeps factual chart annotations unchanged.
  - Replaces raw `field=value` style annotations with a factual chart-reading note.
  - Replaces recommendation-style annotations when they name a single object that is not aligned with the final `business_answer`, or when the final answer is a tradeoff/decision-basis answer and the chart annotation independently names one winner.
- Applied the helper in `workspaces/product_result_builder.build_chart_artifacts()` using the final P16 `business_answer` as the decision basis.
- Did not restore old chart agent, chart tool, visualization planner, or external placeholder paths.
- Did not change the P16 `business_answer` shape.

Focused H3 verification:

- `python3 -m pytest tests/test_answer_consistency.py::test_chart_annotation_is_sanitized_when_it_names_a_different_winner -q` -> `1 passed`.
- `python3 -m pytest tests/test_answer_consistency.py -q` -> `4 passed`.
- `python3 -m pytest tests/test_answer_consistency.py tests/test_product_result_builder.py tests/test_business_answer_quality.py tests/test_visualization_agent_external_tools.py -q` -> `45 passed`.
- `python3 -m pytest tests/test_workspace_report_runner.py -q` -> expected H4 remaining failure: `1 failed, 11 passed`.

## P18-H4 Report Consistency

- [x] Update `workspaces/report_runner.py` so `_business_answer_from_analysis_result()` accepts only consistency-checked product answers.

- [x] Update `_executive_summary()` to produce concise summary items instead of `headline - direct_answer` duplicates when both are nearly identical.

- [x] Ensure internal section prompts remain in `technical_details`, not business report text.

- [x] Run focused report tests:

```bash
python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_api.py tests/test_workspace_analysis_runner.py -q
```

Expected: pass.

## P18-H4 Completion Notes

Completed on 2026-07-01 as report-level consistency reuse only.

- Updated `workspaces/report_runner.py` so report section answers are rebuilt through `build_business_answer(...)` with the section question, `execution_result`, and `evidence_result`.
  - A raw `product_result.business_answer` from a section runner is no longer trusted directly.
  - Multi-metric conflicts in report sections now pass through the same consistency layer used by analysis results, producing tradeoff / decision-basis wording.
- Updated executive summary construction to use short management-facing section headlines instead of concatenating long `direct_answer` bodies.
  - Tradeoff answers retain the key decision-basis meaning.
  - Internal section prompt text, raw SQL, trace/provider metadata, and parameter-dump style content are not promoted into summary text.
- Updated report runner tests to expect concise summaries while preserving complete P16 section `business_answer` bodies.

Focused H4 verification:

- `python3 -m pytest tests/test_workspace_report_runner.py::test_report_does_not_inherit_conflicting_section_answer_or_repeat_long_direct_answer -q` -> `1 passed`.
- `python3 -m pytest tests/test_workspace_report_runner.py -q` -> `12 passed`.
- `python3 -m pytest tests/test_answer_consistency.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py tests/test_business_answer_quality.py -q` -> `43 passed`.
- `python3 -m pytest tests/test_workspace_api.py -q` -> `9 passed`.
- `cd frontend && npm test` -> `57 passed`.

## P18-H5 Prompt Contract Tightening

Only do this if H1-H4 show deterministic consistency cannot fully protect product quality.

- [x] Update `insight_drafter` prompt in `llm_ops/prompt_registry.py` to ask for a clear decision basis in prose, without adding a new public answer field yet.

Prompt intent:

```text
When the question asks for best/should/recommend and multiple metrics are present, state the decision basis. If metrics point to different entities, present the tradeoff instead of forcing one winner. Do not recommend budget changes without sufficient comparative evidence.
```

- [x] Add structured-output tests only for language, shape, and safety. Do not test exact model wording.

Run:

```bash
python3 -m pytest tests/test_deepseek_provider_structured_output.py tests/test_provider_backed_insight_agent.py -q
```

Expected: pass.

## P18-H5 Completion Notes

Completed on 2026-07-01 as lightweight provider prompt and structured-output validation tightening only.

- Updated the `insight_drafter` prompt to explicitly ask for same-language business prose, decision-basis wording for multi-metric best/should/recommend/budget questions, tradeoff wording when metrics point to different entities, and no budget changes without sufficient comparative evidence.
- Kept the P16 public `business_answer` shape unchanged and did not add rigid templates, table-specific rules, old action/mock paths, chart-agent paths, or real external integrations.
- Tightened `insight_drafter` structured validation so model output falls back when product-facing fields include internal report section prompt text or budget/resource recommendations from single-row comparison evidence.
- Follow-up boundary fix: single-row budget validation now allows evidence-gathering recommendations such as adding complete comparison data before deciding budget changes, while still rejecting unsupported budget/resource action advice.
- Added focused prompt/validation coverage in `tests/test_deepseek_provider_structured_output.py` and adjusted the provider recommendation quality test to use comparable evidence before accepting a provider recommendation.

Focused H5 verification:

- `python3 -m pytest tests/test_deepseek_provider_structured_output.py::test_insight_drafter_prompt_includes_business_consistency_constraints tests/test_deepseek_provider_structured_output.py::test_insight_drafter_validation_rejects_budget_action_from_single_row_evidence tests/test_deepseek_provider_structured_output.py::test_insight_drafter_validation_rejects_internal_report_section_prompt_in_business_answer -q` -> `3 passed`.
- `python3 -m pytest tests/test_deepseek_provider_structured_output.py tests/test_business_answer_quality.py -q` -> `35 passed`.
- `python3 -m pytest tests/test_answer_consistency.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py tests/test_business_answer_quality.py tests/test_deepseek_provider_structured_output.py -q` -> `64 passed`.

## P18-H6 Verification And Closeout

- [x] Run focused product tests:

```bash
python3 -m pytest tests/test_answer_consistency.py tests/test_product_result_builder.py tests/test_business_answer_quality.py tests/test_workspace_report_runner.py -q
```

- [x] Run current cleanup boundaries:

```bash
python3 -m pytest tests/test_p17_product_cleanup_boundaries.py tests/test_p11_cleanup_boundaries.py -q
```

- [x] Run full backend regression:

```bash
python3 -m pytest
```

- [x] Run frontend checks:

```bash
cd frontend && npm test
cd frontend && npm run build
```

- [x] Check real DeepSeek acceptance configuration and run where credentials and live flags are available:

```bash
set -a; [ -f .env ] && source .env; set +a
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 \
INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING=1 \
INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1 \
python3 -m pytest tests/test_p13_live_deepseek_product_acceptance.py tests/test_p15_live_deepseek_reliability.py tests/test_p12_live_deepseek_workspace_report.py -q
```

- [x] Run artifact and legacy audits:

```bash
git status --short --ignored
git ls-files data/action_ops.db eval/report.md 'reports/charts/*' 'reports/markdown/*' 'logs/traces/*' 'sample_data/*' 'workspaces/workspace-*' 'frontend/.next/*' '.pytest_cache/*'
rg -n "chart_agent|visualization_planner|chart_tool|action_delivery|action_drafter|powerbi_publisher_mock|jira_ticket_mock|fixed template|deterministic action template|keyword inference|streamlit|eval/run_eval"
```

Generated artifacts, workspace runs, charts, traces, caches, `.env`, and local sample data must not be committed.

## P18-H6 Completion Notes

Completed on 2026-07-01 as regression, live-acceptance gating, artifact hygiene, and docs closeout only.

- Focused P18 regression:
  - `python3 -m pytest tests/test_answer_consistency.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py tests/test_business_answer_quality.py tests/test_deepseek_provider_structured_output.py -q` -> `65 passed`.
- Full backend regression:
  - Initial `python3 -m pytest` run exposed stale P17 cleanup-boundary assertions that still expected P18 external tool-calling status text.
  - Updated those boundary assertions to the current P18 closeout status.
  - Final `python3 -m pytest` -> `350 passed, 13 skipped`.
- Frontend regression:
  - `cd frontend && npm test` -> `57 passed`.
  - `cd frontend && npm run build` -> passed.
- Real DeepSeek acceptance:
  - Checked local configuration without printing secrets.
  - `DEEPSEEK_API_KEY` is present, but `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS` and `INSIGHTFLOW_PRODUCT_LIVE_MODE` are not configured in the current environment.
  - Live DeepSeek acceptance was not run; no mocked or skipped live result is counted as a pass.
- Artifact and legacy hygiene:
  - Legacy audit found `chart_agent`, `visualization_planner`, `chart_tool`, `action_delivery`, `action_drafter`, `powerbi_publisher_mock`, `jira_ticket_mock`, fixed-template wording, keyword inference, Streamlit, and `eval/run_eval` only in historical/superseded notes or boundary tests that assert those paths are not active.
  - Tracked artifact check found only retained placeholders (`logs/traces/.gitkeep`, `reports/charts/.gitkeep`, `reports/markdown/.gitkeep`) and the historical low-level fixture `data/ecommerce.db`; no generated runtime outputs were staged.
  - Ignored local artifacts such as `.env`, `.pytest_cache/`, `frontend/.next/`, `__pycache__/`, `sample_data/`, and workspace runtime directories remain untracked and must not be committed.

P18 final outcome: complete. Business answers, report sections, executive summaries, and chart annotations now share the same consistency guardrails while preserving the P16 `business_answer` contract and the current guarded FastAPI/Next.js product path.

## Acceptance Criteria

P18 is complete when:

- analysis workbench `business_answer` does not internally contradict its evidence;
- chart annotation does not contradict the business answer;
- budget/recommendation questions do not produce unsupported actions from insufficient evidence;
- multi-metric questions explain decision basis or tradeoff;
- report sections and executive summaries inherit consistent answers;
- implementation remains small, readable, and free of table-specific or sample-specific hardcoding;
- full backend pytest passes;
- frontend tests and build pass;
- real DeepSeek acceptance passes when live flags and API key are available;
- generated artifacts are not committed.

## Deferred To Later Phase

Real China-oriented external business tool calling remains a later phase after P18:

- Feishu Bitable / Feishu Docs;
- WeCom or DingTalk notifications;
- Tencent Docs or WPS/Excel-compatible exports;
- BI platforms such as FineBI/FanRuan/Power BI only after auth/API/error handling is designed.

Google Sheets is not a default target for the China-oriented product direction.
