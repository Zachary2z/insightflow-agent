# Historical / Superseded: P16 Clean Business Output Model

This document is retained as the P16 completion record. Its early report-section wording is historical: P22/P23 superseded the old section-business-answer report path with one-pass `ReportDocument` generation, `EvidenceLedger` validation, and ledger-referenced artifacts/tool calls. Current report guidance lives in `docs/product/plans/2026-07-02-p22-evidence-driven-report-generation.md` and `docs/product/plans/2026-07-03-p23-core-evidence-and-report-tooling-readiness.md`.

P16 is complete. It is a clean product-direction reset for answer and report presentation, not a compatibility layer for old generated runs. P16-H1, P16-H2, P16-H3, P16-H4, P16-H5, and P16-H6 are complete: the backend product answer model, insight drafting prompt, structured-output validation, provider-backed insight agent, product-result builder, run-history restoration, frontend analysis rendering path, report section JSON, report reader, Markdown renderer, final cleanup, artifact hygiene, full regression, and real DeepSeek acceptance now use and protect the single clean `business_answer` contract.

Historical P16 target at the time:

```text
business question
-> guarded SQL and evidence pipeline
-> clean structured business answer
-> chart/evidence support
-> report section using the same business answer shape
-> technical details collapsed
```

## Product Decision

P16 may delete code, tests, and local generated artifacts that only exist to support old run/report output shapes. The implementation does not need to preserve previously generated workspace run/report files if they conflict with the current product direction.

Keep the existing guarded runtime boundaries:

- question understanding
- SQL planning and candidate generation
- SQL reviewer
- SQL execution
- evidence validation
- chart/artifact delivery
- trace/technical details as collapsed support

Do not add parallel business entry points or new agent families just to improve wording.

## New Business Answer Contract

Use one product-facing answer shape:

```json
{
  "headline": "",
  "direct_answer": "",
  "why": "",
  "evidence_bullets": [],
  "recommendations": [],
  "caveats": [],
  "confidence": "medium"
}
```

Field meaning:

- `headline`: one concise business conclusion.
- `direct_answer`: direct answer to the user's question in the user's language.
- `why`: short explanation of the reasoning supported by current evidence.
- `evidence_bullets`: key facts from SQL execution/evidence validation, formatted for business readers.
- `recommendations`: action suggestions only when the evidence supports them.
- `caveats`: data limits, missing context, or uncertainty.
- `confidence`: `low`, `medium`, or `high`.

Remove old product assumptions where possible:

- Do not keep `summary` as the primary answer body.
- Do not keep `next_actions` as a separate future-facing field if `recommendations` already covers it.
- Do not keep history-specific conversion code for old answer shapes.
- Do not make the frontend infer structure from free-form text.

## Prompt And Model Contract

Upgrade the insight drafting prompt to produce the new business answer JSON shape directly.

The prompt must require:

- same language as the user question unless the user explicitly requests another language
- recommendation-first but evidence-bound wording
- no raw `field=value` dumps
- no SQL in product answer fields
- no provider metadata, trace IDs, or internal prompt text
- no unsupported causal claims
- no recommendation when evidence is too weak

The structured-output validator should reject responses that miss required fields, use the wrong language, or put raw parameter dumps into business-facing fields.

## Product Result Builder

Rewrite the product result builder around small helpers:

```text
build_business_answer
-> validate/normalize model answer
-> extract evidence bullets from execution/evidence if needed
-> create clean failure answer when SQL review/execution fails
-> return the single business answer contract
```

Keep fallback behavior only for current product reliability:

- provider unavailable
- invalid provider JSON
- SQL review failure
- no rows returned
- evidence too weak

Do not keep fallback behavior whose only purpose is to render old persisted runs.

## Report Contract

Reports should reuse the same business answer shape at section level.

Recommended section shape:

```json
{
  "section_id": "",
  "title": "",
  "status": "",
  "business_answer": {
    "headline": "",
    "direct_answer": "",
    "why": "",
    "evidence_bullets": [],
    "recommendations": [],
    "caveats": [],
    "confidence": "medium"
  },
  "business_artifacts": [],
  "technical_details": {}
}
```

The main report should read like a management report:

1. Management summary
2. Key findings by section
3. Evidence and charts
4. Recommendations
5. Caveats and limits
6. Collapsed technical appendix

SQL, trace nodes, provider metadata, internal section prompts, raw rows, and debug details belong only in technical details.

## Frontend Contract

`BusinessAnswerCard` should display the new contract in this order:

1. 结论
2. 直接回答
3. 为什么
4. 关键证据
5. 建议动作
6. 限制说明

Report detail pages should reuse the same presentation pattern for each section instead of maintaining a separate text interpretation layer.

Frontend code should not support multiple historical answer shapes. If old local generated runs cannot render, clean them or regenerate them with the new product path.

## Cleanup Scope

Allowed cleanup during P16:

- remove old answer-shape compatibility code
- remove old run/report sanitization that only exists for historical generated files
- remove tests that assert old `summary`/`next_actions` behavior as a primary product path
- clean local generated workspace runs/reports/charts/traces when needed

Not allowed:

- deleting current guarded SQL/evidence/runtime boundaries
- deleting useful tests that protect real provider behavior
- replacing live DeepSeek acceptance with mocked-only tests
- reintroducing fixed SQL templates or keyword-heavy business rules
- restoring Streamlit, old eval UI, old chart agent/planner/tool paths

## Suggested Task Queue

| Task | Scope | Status |
|---|---|---|
| P16-H1 | Define the single clean business answer model and fail-first backend tests | Complete |
| P16-H2 | Upgrade `insight_drafter` prompt and structured-output validation for the new contract | Complete |
| P16-H3 | Rewrite `product_result_builder` around the new contract and remove old history-only compatibility | Complete |
| P16-H4 | Update `BusinessAnswerCard`, run result rendering, and frontend types to use only the new contract | Complete |
| P16-H5 | Update report section JSON, report reader, and Markdown renderer to reuse the business answer contract | Complete |
| P16-H6 | Delete obsolete tests/code, clean generated artifacts, run full regression and real DeepSeek acceptance | Complete |

## P16-H1 Completion Notes

Completed on 2026-06-30:

- `PRODUCT_RESULT_VERSION` is now `p16.v1`.
- `empty_business_answer()` and `build_business_answer()` return only `headline`, `direct_answer`, `why`, `evidence_bullets`, `recommendations`, `caveats`, and `confidence`.
- Backend tests now fail if `summary`, `next_actions`, `source`, or `quality_flags` remain primary product answer fields.
- Chinese questions are protected against English-only product answers by rebuilding readable Chinese business fields from execution evidence.
- Raw `field=value` parameter dumps, SQL, provider metadata, and trace details stay out of product-facing answer fields.
- SQL review/schema failures, no-row results, and weak-evidence results return business-friendly P16 answers with low confidence or caveats instead of unsupported recommendations.
- P15-era run-history rebuild logic for old persisted product-result shapes was removed; current product paths should generate or store P16-shaped results.

Verification:

- `python3 -m pytest tests/test_product_result_builder.py tests/test_business_answer_quality.py tests/test_provider_backed_insight_agent.py -q` -> `17 passed`
- `python3 -m pytest tests/test_workspace_run_history_api.py tests/test_workspace_analysis_runner.py -q` -> `20 passed`
- `python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_api.py -q` -> `22 passed`
- `python3 -m pytest tests/test_p13_live_deepseek_product_acceptance.py -q` -> `1 passed, 2 skipped`
- `cd frontend && npm test -- workspace-flow.test.tsx` -> `43 passed`
- `cd frontend && npm run build` -> passed

## P16-H2 Completion Notes

Completed on 2026-06-30:

- `insight_drafter` now prompts for JSON only with `candidate_claims` and the P16 `business_answer` object; it no longer asks for `draft_summary` as product output.
- The prompt explicitly requires same-language business fields, Chinese business-facing output for Chinese questions unless English is requested, evidence-bound bullets and recommendations, caveats for weak evidence, and no raw field dumps, SQL, trace ids, provider metadata, raw rows, internal prompt text, or unsupported causal claims.
- `llm_ops.structured_output` now validates the P16 `business_answer` structure for `insight_drafter`, rejects draft-summary-only output, rejects empty required fields, invalid confidence, wrong array fields, English-only Chinese answers, raw parameter dumps, SQL, trace ids, and provider metadata in business-facing fields.
- `agents.insight_agent` now reads validated `content["business_answer"]`, uses `direct_answer` as `final_answer`, keeps fallback output inside the same P16 contract, and continues to pass `candidate_claims` to Evidence Validator through `claims_to_validate`.
- Old provider-backed insight tests that used `draft_summary` as the main product output were rewritten to use `business_answer`; only negative tests retain `draft_summary` to prove the old output is rejected.

Verification:

- `python3 -m pytest tests/test_provider_backed_insight_agent.py tests/test_business_answer_quality.py tests/test_deepseek_provider_structured_output.py -q` -> `29 passed`
- `python3 -m pytest tests/test_product_result_builder.py tests/test_p13_live_deepseek_product_acceptance.py -q` -> `9 passed, 2 skipped`
- `python3 -m pytest tests/test_p0_agents.py tests/test_workspace_analysis_runner.py -q` -> `17 passed`
- `python3 -m pytest tests/test_report_insight_cleanup.py -q` -> `6 passed`

## P16-H3 Completion Notes

Completed on 2026-06-30:

- `workspaces.product_result_builder.build_business_answer()` now has a short current-contract flow: SQL review failure returns a business-friendly failure answer; usable provider `business_answer` is normalized and returned; invalid, missing, wrong-language, raw-dump, SQL, trace, or provider-metadata answers are rebuilt from evidence; weak evidence returns low confidence, caveats, and no recommendations.
- `business_answer_is_usable()` centralizes the current P16 answer checks for required keys, Chinese question language, raw parameter dumps, SQL/trace/provider metadata leakage, and weak-evidence recommendation/caveat rules.
- Old history-only compatibility around stale summary/next-action answer shapes was removed from the run-history path. `workspaces.run_store` only accepts `p16.v1` product results whose `business_answer` passes the current contract; stale P13 or invalid P16 results are rebuilt safely.
- Focused tests now cover clean provider answer preservation, partial-English Chinese answers, weak evidence without recommendations, raw/SQL/trace leak rejection, SQL review failure output, stale P13 rebuilds, and invalid P16 rebuilds.

Verification:

- `python3 -m pytest tests/test_product_result_builder.py tests/test_business_answer_quality.py tests/test_workspace_run_history_api.py -q` -> `36 passed`
- `python3 -m pytest tests/test_provider_backed_insight_agent.py tests/test_workspace_analysis_runner.py tests/test_p0_agents.py -q` -> `19 passed`
- `python3 -m pytest` -> `323 passed, 13 skipped`

## P16-H4 Completion Notes

Completed on 2026-06-30:

- `frontend/lib/api.ts` now defines the analysis `BusinessAnswer` type with only the current required fields: `headline`, `direct_answer`, `why`, `evidence_bullets`, `recommendations`, `caveats`, and `confidence`.
- `BusinessAnswerCard` now renders the current contract in business-reader order: 结论, 直接回答, 为什么, 关键证据, 建议动作, 限制说明, and 置信度.
- `RunResult` now only renders backend `product_result` payloads with `version == "p16.v1"` and an exact current-contract `business_answer`. Missing product results or legacy/malformed answer shapes produce a product-level error state instead of falling back to `final_answer`, evidence rows, or old answer fields.
- Analysis history display remains summary-driven by backend `headline`, `failure_reason`, `status`, and `has_chart`; frontend tests no longer expect English summaries for Chinese questions.
- Report section `summary` and `executive_summary` were intentionally left unchanged for P16-H5 and are now covered by the H5 completion notes below.

Verification:

- TDD red: `cd frontend && npm test -- workspace-flow.test.tsx` failed with 3 expected failures before implementation.
- `cd frontend && npm test -- workspace-flow.test.tsx api-client.test.ts` -> `54 passed`
- `cd frontend && npm test` -> `56 passed`
- `cd frontend && npm run build` -> passed
- `python3 -m pytest tests/test_workspace_run_history_api.py tests/test_product_result_builder.py -q` -> `22 passed`
- Legacy-field audit found remaining hits only in report-contract H5 scope, negative tests, cleanup-boundary tests, and non-product technical summary fields.

## P16-H5 Completion Notes

Completed on 2026-06-30:

- `workspaces.report_models.ReportSection` now contains the current `business_answer` object and no longer emits active `summary` in new report JSON.
- `workspaces.report_runner` now builds section business answers only from `analysis_result.product_result.business_answer` with `version == "p16.v1"` or from top-level current `analysis_result.business_answer`; invalid or missing current answers produce a clear low-confidence failed section instead of falling back to old `final_answer`.
- Report-level `executive_summary` remains, but it is derived from section `business_answer.headline` and `direct_answer`.
- SQL, raw rows/result preview, provider metadata, trace nodes, workspace run paths, and raw final-answer text stay in `technical_details` / technical appendix rather than business answer fields.
- `workspaces.report_markdown` renders each report section in business order: 结论, 直接回答, 为什么, 关键证据, 建议动作, 限制说明, and 置信度, followed by chart artifacts and a technical appendix.
- `frontend/lib/api.ts` now types report sections with the current `BusinessAnswer`; `frontend/components/ReportSection.tsx` renders `section.business_answer` and no longer uses `section.summary` or `evidence_notes` as report body.
- The P12 live report acceptance test now checks section `business_answer` and Markdown section headings instead of old `summary`.

Verification:

- TDD red: focused report backend tests failed with missing `business_answer` / unsupported constructor field / legacy completed-section behavior; focused frontend tests failed because the report reader still rendered old `summary`.
- `python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_api.py tests/test_workspace_report_store.py tests/test_provider_backed_report_writer.py -q` -> `32 passed` (superseded/deleted in P22-H1 closeout; the old provider-backed report writer path is no longer an active Report Center path)
- `python3 -m pytest tests/test_product_result_builder.py tests/test_report_insight_cleanup.py -q` -> `16 passed`
- `python3 -m pytest tests/test_p12_live_deepseek_workspace_report.py -q` -> `1 skipped` without live flags
- `python3 -m pytest` -> `324 passed, 13 skipped`
- `cd frontend && npm test -- workspace-flow.test.tsx api-client.test.ts` -> `54 passed`
- `cd frontend && npm test` -> `56 passed`
- `cd frontend && npm run build` -> passed
- H5 audit command found no active `section.summary`, `summary=`, `_business_summary`, or `_compat_technical_details` report path. Remaining hits are report-level `executive_summary` derived from `business_answer`, negative legacy/draft-summary tests, cleanup-boundary tests, and unrelated technical compatibility wording.

## P16-H6 Completion Notes

Completed on 2026-06-30:

- `frontend/components/ReportSection.tsx` now performs exact runtime validation for P16 `business_answer`. Malformed or legacy report answers show `报告章节结构异常`, do not render empty business fields, and do not fall back to old summary/evidence/artifact content.
- `frontend/components/RunResult.tsx` has a tighter prop contract aligned with implementation: callers pass a backend response wrapper, and rendering only proceeds from `product_result.version == "p16.v1"` plus a valid current `business_answer`.
- `frontend/lib/api.ts` no longer exposes `WorkspaceReportSection.summary` as active report rendering type surface.
- `workspaces.report_markdown` no longer carries an unused provider-metadata summary helper.
- `workspaces.product_result_builder` now preserves a supported recommendation for budget/allocation questions when provider text must be rebuilt from validated evidence, while weak evidence still blocks unsupported recommendations.
- `workspaces.product_result_builder` now treats report-internal section prompts as technical leakage and rebuilds English-only evidence notes into row-based Chinese evidence bullets for Chinese questions.
- `tests/test_product_result_builder.py` and `frontend/tests/workspace-flow.test.tsx` include H6 regressions for these cleanup boundaries.
- `.gitignore` now ignores local `sample_data/`; local sample CSV/XLSX files remain untracked and are not product artifacts.
- The required legacy-field audit was run. Remaining hits are report-level `executive_summary`, history summary labels, technical trace/context summaries, negative tests proving legacy/draft-summary rejection, and historical cleanup-boundary tests.

Verification:

- `python3 -m pytest` -> `327 passed, 13 skipped`
- `cd frontend && npm test` -> `57 passed`
- `cd frontend && npm run build` -> passed
- Real DeepSeek P15 reliability acceptance with live/product/provider flags -> `1 passed`
- Real DeepSeek P12 report acceptance with live/product/provider flags -> `1 passed`
- Real DeepSeek P13 product acceptance with live/product/provider flags -> `3 passed`
- Required generated-cache cleanup command completed after verification.

## Acceptance

- Business answers always expose `headline`, `direct_answer`, `why`, `evidence_bullets`, `recommendations`, `caveats`, and `confidence`.
- Chinese questions return Chinese business-facing answer fields unless the user explicitly asks for another language.
- Product-facing fields do not contain raw SQL, trace IDs, provider metadata, raw rows, or parameter dumps.
- Recommendations are omitted or caveated when evidence is weak.
- Report sections use the same business answer shape as single analysis results.
- Main report pages and Markdown read like business reports, with technical details collapsed or appended.
- Old answer-shape compatibility and tests are deleted or converted to negative rejection tests where they conflict with the current product direction.
- Full backend tests pass.
- Frontend tests and production build pass.
- Real DeepSeek product acceptance covers Chinese analysis, clarification continuation, history reliability, and report generation paths.
- Generated workspace runs/reports/charts/traces and local sample data remain untracked unless explicitly requested.

## Out Of Scope

- Full Business Q&A chat backend.
- Real SaaS integrations such as Slack, Jira, Power BI, Notion, email, CRM, or ticketing systems.
- Auth/RBAC.
- Deployment.
- PDF/PPT export.
- Scheduled reports.
- Vector databases.
- New agent families for wording only.
- Fixed SQL templates or keyword-heavy business rules.
