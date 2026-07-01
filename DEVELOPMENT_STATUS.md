# InsightFlow Agent Development Status

Last updated: 2026-07-01

This is the concise current status surface for InsightFlow Agent.

## Current Snapshot

| Field | Status |
|---|---|
| Current phase | P19 Business Output And Report Quality |
| Current task | P19-H4 complete / ready for H5 quality closeout |
| Next planned task | P19-H5 Quality closeout and live acceptance |
| Last completed task | P18-H6 regression, live acceptance, artifact hygiene, docs closeout |
| Active backend | FastAPI in `api/app.py` |
| Active frontend | Next.js + React + TypeScript in `frontend/` |
| Active analysis entry | `POST /api/workspaces/{workspace_id}/runs` |
| Active report entry | `POST /api/workspaces/{workspace_id}/reports` |
| Current answer contract | P16 `business_answer`: `headline`, `direct_answer`, `why`, `evidence_bullets`, `recommendations`, `caveats`, `confidence` |
| Main product target | Chinese business data-analysis product with guarded SQL/evidence execution, 数据源管理, 分析工作台, 报告中心, 数据设置, and future-compatible 业务问答 preview |
| Out of scope for P17 | New product features, real external integrations, auth/RBAC, deployment, vector databases, scheduled reports, fixed SQL templates, keyword-heavy business rules, and old demo restoration |

## Phase Overview

| Phase | Status | Current meaning |
|---|---|---|
| P0-P10 | `[x]` Complete | Historical foundations for SQL safety, evidence validation, provider plumbing, MCP wrappers, visualization, and trace/artifact hygiene |
| P11 | `[x]` Complete | Workspace data import, profile, semantic-layer draft, and ad hoc analysis through FastAPI + Next.js |
| P12 | `[x]` Complete | Workspace report APIs, runner, storage, Markdown download, and report UI |
| P13 | `[x]` Complete | Business-facing answers, clarification continuation, report reader polish, Data Settings, chart display |
| P14 | `[x]` Complete | Unified Chinese product shell and core workspace pages |
| P15 | `[x]` Complete | Persisted analysis history/detail, schema repair, business-friendly failure UX, real DeepSeek reliability regression |
| P16 | `[x]` Complete | Single clean `business_answer` contract across analysis, reports, Markdown, frontend rendering, and run restoration |
| P17 | `[x]` Complete | Product codebase cleanup; H1-H6 complete |
| P18 | `[x]` Complete | Business answer consistency across conclusions, evidence, recommendations, chart annotations, and reports |
| P19 | `[ ]` Planned | Compact quality phase for business-ready replies/reports using reviewer/composer, grounded recommendations, report/chart synthesis, and live acceptance |
| P20 | `[ ]` Future | Responsive analysis experience: route classification, fast factual path, progress states, caching, and background work |
| P21 | `[ ]` Future | Real business tool calling and exports after quality and responsiveness are stable |

## P19 Task Status

| Task | Status | Notes |
|---|---|---|
| P19-H1 | `[x]` Complete | Plain why/evidence entity conflicts are now corrected or downgraded by the small deterministic guard |
| P19-H2 | `[x]` Complete | Added Answer Reviewer Agent and Final Answer Composer contracts, deterministic/provider tests, and product/report integration |
| P19-H3 | `[x]` Complete | Polished business answer quality: vocabulary, units, grounded recommendations, tradeoffs, caveats, and report-section reuse |
| P19-H4 | `[x]` Complete | Reports now synthesize reviewed section answers into management summary, key findings, action priorities, chart/evidence narrative, risks/limits, and technical appendix |
| P19-H5 | `[ ]` Planned | Quality closeout: focused/full regression, frontend build, live DeepSeek acceptance, cleanup, and artifact hygiene |

## P18 Task Status

| Task | Status | Notes |
|---|---|---|
| P18-H1 | `[x]` Complete | Added RED tests for multi-metric conflict, insufficient comparison evidence, chart annotation conflict, and report inheritance; focused tests intentionally fail until H2-H4 |
| P18-H2 | `[x]` Complete | Added `workspaces/answer_consistency.py` and applied it in `build_business_answer()`; multi-metric tradeoff and single-row budget-reduction RED tests now pass |
| P18-H3 | `[x]` Complete | Align chart annotations with the final business answer |
| P18-H4 | `[x]` Complete | Report sections reuse consistency-checked answers; executive summaries stay concise and do not repeat long section direct answers |
| P18-H5 | `[x]` Complete | Tightened insight drafter prompt and lightweight structured validation for language, raw/internal text, and unsupported single-row budget actions |
| P18-H6 | `[x]` Complete | Focused/full regression, frontend checks, live acceptance gating, artifact hygiene, and docs closeout |

## P17 Task Status

| Task | Status | Notes |
|---|---|---|
| P17-H1 | `[x]` Complete | Added dependency boundary tests proving current product entry points do not require removed historical paths |
| P17-H2 | `[x]` Complete | Removed legacy action-path code and provider/prompt hooks outside the current product |
| P17-H3 | `[x]` Complete | Current visualization delivery runtime is local chart rendering and local workbook export only |
| P17-H4 | `[x]` Complete | Old eval/demo files are deleted or untracked; old design snapshots began being marked historical |
| P17-H5 | `[x]` Complete | Simplified README, DEVELOPMENT_PLAN, DEVELOPMENT_STATUS, and retained P11/P12/P13 specs so current product guidance is obvious |
| P17-H6 | `[x]` Complete | Final artifact hygiene, legacy audit, focused/full regressions, frontend build, and real DeepSeek acceptance |

## Current Product Chain

```text
workspace import
-> profile and semantic layer
-> question understanding
-> clarification router
-> SQL planning
-> guarded SQL candidate
-> SQL review
-> schema repair
-> SQL execution
-> evidence validation
-> insight/business answer
-> visualization
-> report
-> Next.js product UI
```

## Latest Verified Baseline

Latest P18-H6 closeout result on 2026-07-01:

- P18 focused regression passed for answer consistency, report runner, product result builder, business answer quality, and DeepSeek structured output.
- Full backend regression passed after updating stale P17 boundary assertions to the current P18 closeout status: `350 passed, 13 skipped`.
- Frontend Vitest and production build passed.
- Real DeepSeek acceptance was not run because the current environment has a DeepSeek key but does not have the live opt-in flags configured.
- Legacy audit found old chart/action/mock/eval/Streamlit terms only in historical/superseded notes and boundary tests, not active product guidance.
- Generated artifacts, frontend build output, pytest cache, runtime workspace outputs, traces, and sample data remain ignored and must not be committed.

P19 planning note on 2026-07-01:

- Real local DeepSeek product mode was enabled for manual product testing with `INSIGHTFLOW_PRODUCT_LIVE_MODE=1` in the untracked `.env`.
- A real channel budget question produced provider-backed analysis (`provider_called: true` across question understanding, SQL planning/candidate, insight drafting, and claim typing), proving the live path works.
- The output quality review found remaining product gaps: recommendations can cite a different entity than their evidence, raw metric names can leak into business copy, recommendations can be empty or repetitive, and reports read like stitched section output rather than synthesized management reports.
- P19 is therefore focused on business-output/report quality before external publishing integrations.
- Direction update: P19 should not become an expanding deterministic patch list for every possible model mistake. The next design direction is an Answer Reviewer Agent plus Final Answer Composer, with small deterministic checks as the last safety guardrail.
- Planning update: P19 is intentionally compacted into five H tasks so development is easier to steer, but each H task still requires tests, code cleanup, artifact hygiene, and focused/full verification.
- Cleanup policy update: P19 should delete old paths, obsolete tests, fallback/template/demo compatibility code, and unused modules when they conflict with the current FastAPI/Next.js workspace product direction. Historical behavior does not need to be preserved.
- Future notes: P20 should optimize responsiveness with route classification, fast factual path, progress states, caching, and background work. P21 should add real business tool calling/export after P19/P20 are stable.

P19-H2 completion note on 2026-07-01:

- Added structured `answer_reviewer` and `final_answer_composer` contracts with validation tests.
- Integrated reviewer/composer after insight drafting and before final P16 business answer normalization.
- Report sections reuse the reviewed/composed `business_answer`; deterministic `answer_consistency.py` remains the final small guardrail.
- Focused backend tests, full backend regression, frontend Vitest, and frontend production build passed.

P19-H3 completion note on 2026-07-01:

- Added shared language-aware business labels for common metrics and dimensions so Chinese answers prefer 收入、总收入、订单数、客单价、投放成本、ROI、渠道 and 客户分群, while English answers use total revenue, order count, average order value, spend, ROI, channel, and segment.
- Final Answer Composer now produces business-readable revise/downgrade answers, removes reviewer/internal wording from caveats, and states revenue-vs-ROI tradeoffs instead of forcing one winner.
- Product result and report section normalization apply the same field-label cleanup while keeping raw columns, rows, SQL, traces, and provider metadata in technical details.
- Added focused regression coverage for Chinese output, field-label polish, multi-metric tradeoffs, no invented ROI/profit advice, internal metadata leakage, and report section business answers.
- Follow-up fix: English questions now keep English fallback wording and English business labels instead of mixing Chinese labels into accepted/composed answers.

P19-H4 completion note on 2026-07-01:

- Report records now expose management-facing `executive_summary`, `key_findings`, `action_priorities`, `chart_and_evidence`, and `risks_and_limits` synthesized from reviewed/composed section `business_answer` values.
- Markdown reports use Chinese-first management structure for Chinese goals and English headings/content for English goals, with SQL, trace paths, provider metadata, raw rows, and internal section prompts kept in the technical appendix.
- Chart artifacts carry title, unit, safe business annotation, and path/URL into report JSON, Markdown image embeds, and the frontend report detail view.
- Missing charts render a business-friendly “暂无可展示图表” explanation instead of visualization errors or trace metadata in the main report body.
- Focused P19-H4 backend regression passed: `python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_store.py tests/test_workspace_report_api.py tests/test_report_insight_cleanup.py tests/test_chart_product_quality.py tests/test_product_result_builder.py -q` with `57 passed`.
- Focused frontend report regression passed: `cd frontend && npm test -- workspace-flow.test.tsx` with `48 passed`.

Latest P17-H6 closeout result on 2026-06-30:

- README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS were simplified into current product/status surfaces.
- P11/P12/P13 superpowers specs are marked Historical / Superseded and point current guidance to `docs/product/plans/`, P16 `business_answer`, and P17 cleanup.
- Old eval/demo/action/mock/chart wording is retained only in Historical / Superseded notes, cleanup plans, or test-boundary assertions.
- Final artifact hygiene keeps generated reports, charts, traces, workspace instances, frontend build output, pytest cache, and `__pycache__` out of the working artifact set, with only required `.gitkeep` placeholders retained.
- Legacy audit found superseded cleanup terms only in historical/superseded notes or deletion-boundary tests, not active product entry points.
- Focused cleanup boundary tests passed: `python3 -m pytest tests/test_p17_product_cleanup_boundaries.py tests/test_p11_cleanup_boundaries.py -q` with `19 passed`.
- Full backend regression passed: `python3 -m pytest`.
- Frontend tests passed: `cd frontend && npm test`.
- Frontend production build passed: `cd frontend && npm run build`.
- Real DeepSeek live acceptance passed for P15 analysis reliability, P12 workspace reports, and P13 product acceptance with product live/provider flags.

## Historical / Superseded Notes

This section is historical cleanup context only, not current product guidance.

- Historical / Superseded: `streamlit run app.py`, `eval/run_eval.py`, `tests/test_eval_runner.py`, `tests/test_streamlit_app.py`, `chart_agent`, `visualization_planner`, `chart_tool`, `action_delivery`, `action_drafter`, `powerbi_publisher_mock`, `jira_ticket_mock`, mock SaaS, fixed template behavior, deterministic action template behavior, and keyword inference are old cleanup terms.
- Historical retained fixture: `data/ecommerce.db` remains for low-level tests that directly exercise schema, SQL validation, SQL execution, workflow, report, MCP, and provider regressions. It is not the current product database.
- Historical P11/P12/P13 specs under `docs/superpowers/specs/` must be treated as snapshots. Current guidance is `docs/product/plans/`, the P16 `business_answer` contract, and P17 cleanup.
- Real China-oriented external tool calling is deferred until after P18 answer consistency, so external publishing/exporting does not amplify inconsistent conclusions.
