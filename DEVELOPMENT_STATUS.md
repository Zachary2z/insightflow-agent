# InsightFlow Agent Development Status

Last updated: 2026-07-02

This is the concise current status surface for InsightFlow Agent.

## Current Snapshot

| Field | Status |
|---|---|
| Current phase | P20 General Business Analysis Foundation |
| Current task | P20-H2 Chinese analysis task contract and clarification continuation complete; next is P20-H3 |
| Next planned task | P20-H3 Fact layer, metric registry, and evidence payload |
| Last completed task | P20-H2 Chinese analysis task contract and clarification continuation |
| Active backend | FastAPI in `api/app.py` |
| Active frontend | Next.js + React + TypeScript in `frontend/` |
| Active analysis entry | `POST /api/workspaces/{workspace_id}/runs` |
| Active report entry | `POST /api/workspaces/{workspace_id}/reports` |
| Current answer contract | P16 `business_answer`: `headline`, `direct_answer`, `why`, `evidence_bullets`, `recommendations`, `caveats`, `confidence` |
| Main product target | Chinese-first general business data-analysis multi-agent product with data profiling, semantic layer, task routing, SQL/calculation/chart/report tool calls, evidence validation, Chinese business answers, and Chinese management reports |
| Out of scope for P20 | Real external integrations, auth/RBAC, deployment, vector databases, scheduled reports, fixed SQL templates, keyword-heavy business rules, table-specific demo logic, and old demo restoration |

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
| P19 | `[x]` Complete | Compact quality phase for business-ready replies/reports using reviewer/composer, grounded recommendations, report/chart synthesis, cleanup, and live acceptance |
| P20 | `[~]` In progress | General business analysis foundation: cleanup, generalized profiling/semantic layer, task contract, fact/evidence layer, answer/report generation |
| P21 | `[ ]` Future | Responsive analysis experience: route classification, fast factual path, progress states, caching, and background work |
| P22 | `[ ]` Future | Real business tool calling and exports after generalized analysis quality and responsiveness are stable |

## P20 Task Status

| Task | Status | Notes |
|---|---|---|
| P20-H0 | `[x]` Complete | Architecture cleanup and main path inventory; removed stale template-mining eval/helper path and clarified current product chain |
| P20-H1 | `[x]` Complete | General profiling/semantic baseline plus safe metric formula quoting and Chinese aliases for English/mixed raw fields |
| P20-H2 | `[x]` Complete | Normalized Chinese `analysis_task` contract, slot-level clarification, partial continuation stays pending, provider output normalized to Chinese |
| P20-H3 | `[ ]` Planned | Fact layer, metric registry, and evidence payload with stable formulas and comparison scope |
| P20-H4 | `[ ]` Planned | Business insight, answer, chart, and report generation from validated evidence |
| P20-H5 | `[ ]` Planned | Realistic acceptance, cleanup audit, documentation closeout, and live DeepSeek verification when enabled |

## P19 Task Status

| Task | Status | Notes |
|---|---|---|
| P19-H1 | `[x]` Complete | Plain why/evidence entity conflicts are now corrected or downgraded by the small deterministic guard |
| P19-H2 | `[x]` Complete | Added Answer Reviewer Agent and Final Answer Composer contracts, deterministic/provider tests, and product/report integration |
| P19-H3 | `[x]` Complete | Polished business answer quality: vocabulary, units, grounded recommendations, tradeoffs, caveats, and report-section reuse |
| P19-H4 | `[x]` Complete | Reports synthesize reviewed answers into management narrative, with language-aware Markdown/frontend labels and business-labeled evidence summaries |
| P19-H5 | `[x]` Complete | Quality closeout: focused/full regression, frontend build, live DeepSeek acceptance, cleanup audit, and artifact hygiene |

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

Latest P20-H2 task-contract result on 2026-07-02:

- Question understanding now emits a normalized `analysis_task` contract with `task_type`, Chinese `dimensions` and `metrics`, `time_range`, `filters`, `decision_goal`, `missing_slots`, `defaults_applied`, `resolved_question`, fixed `output_language: "zh"`, and confidence.
- Complete Chinese analysis questions such as “最近90天按门店比较销售额” proceed without clarification, while incomplete recommendation questions such as “帮我分析渠道表现，看看哪个渠道该加预算” ask concise Chinese follow-ups for missing metric and time range instead of being rejected or sent to SQL.
- English or mixed raw headers in semantic context, such as `Sales Amount` and `Store Name`, normalize to Chinese business slots such as 销售额 and 门店; English user questions still produce `output_language: "zh"`.
- Clarification continuation now merges the original question with the user's short supplement. A partial answer such as “花费” fills only the metric and keeps the pending run waiting for `time_range`; a completed supplement can continue through the normal analysis path.
- Provider-backed question understanding can return optional `analysis_task`, but local normalization applies defaults, forces Chinese output language, maps workspace semantic aliases, and recomputes missing slots so provider output cannot bypass clarification rules.
- Verification passed: `python3 -m pytest tests/test_question_understanding_router.py tests/test_clarification_routing.py tests/test_pending_clarification_store.py -q` (`20 passed`), `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workflow.py -q` (`16 passed`), `python3 -m pytest tests/test_provider_backed_question_understanding.py tests/test_provider_backed_clarification_router.py tests/test_deepseek_provider_structured_output.py -q` (`44 passed`), `python3 -m pytest tests/test_p20_general_semantic_layer.py tests/test_metric_tool.py -q` (`8 passed`), and full backend regression `python3 -m pytest` (`412 passed, 13 skipped`).

Latest P20-H1 generalized semantic-layer result on 2026-07-01:

- CSV/Excel import identifier sanitization now preserves Unicode business headers, so Chinese field names remain available for profiling instead of collapsing to duplicate placeholder names.
- Workspace profiling now emits generalized `original_type`, `inferred_type`, `field_role`, `business_meaning_candidates`, `suitable_group_by`, and `suitable_aggregations` fields while preserving legacy `role_candidates`.
- Semantic-layer drafts are generated from actual workspace fields into `tables`, `metrics`, `dimensions`, `time_fields`, `entities`, `field_roles`, `semantic_aliases`, `relationships`, and `available_analysis_capabilities`; missing `channel` or `revenue` fields are not invented.
- Added `load_workspace_semantic_layer()` as the shared YAML/JSON workspace semantic-layer reader and wired it into settings summary, workspace context summary, metric lookup, and schema repair.
- Schema repair now reads workspace YAML semantic layers without the previous JSON-only “semantic layer could not be read” failure.
- Data Settings recognizes the generalized `metric`, `id`, `status`, and `text` field-role labels.
- Verification passed: `python3 -m pytest tests/test_workspace_profiler.py tests/test_workspace_semantic_draft.py tests/test_semantic_layer.py -q` (`15 passed`), `python3 -m pytest tests/test_schema_tool.py tests/test_metric_tool.py tests/test_workspace_settings_api.py tests/test_p20_general_semantic_layer.py -q` (`17 passed`), `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q` (`27 passed`), combined P20-H1 backend set (`36 passed`), frontend workspace-flow Vitest (`49 passed`), frontend production build passed, and full backend regression passed (`401 passed, 13 skipped`).

P20 language-scope update on 2026-07-02:

- P20 now targets a Chinese-first business product: product-facing UI copy, clarifying questions, answers, chart annotations, reports, Markdown exports, and provider prompts should be Chinese.
- English and mixed raw headers remain supported as imported data reality, but they should be mapped into Chinese business labels and aliases instead of creating bilingual product output branches.
- Historical P19 English-output behavior is no longer a P20 acceptance requirement. Multilingual output is deferred until after the Chinese business analysis chain is stable.
- P20-H1 needs a focused repair before H2 because current semantic metric formulas may not safely quote headers with spaces or punctuation, and English raw fields such as `Sales Amount` need Chinese semantic aliases such as 销售额.

P20-H1 repair completion note on 2026-07-02:

- Semantic metric formulas now quote SQLite identifiers safely, including table and column names with spaces, punctuation, parentheses, Chinese characters, and embedded double quotes.
- Semantic drafts now derive Chinese business aliases and labels from `business_meaning_candidates` and common raw header words, so English/mixed fields such as `Sales Amount`, `Cost Amount`, `Score (NPS)`, and `Store Name` map to 销售额、成本、满意度、门店.
- Workspace metric lookup can answer Chinese semantic questions such as “按门店看销售额”, “按门店看成本”, and “按门店看满意度” against English/mixed raw headers without inventing channel, orders, or ROI fields.
- Verification passed: `python3 -m pytest tests/test_workspace_semantic_draft.py tests/test_metric_tool.py tests/test_p20_general_semantic_layer.py -q` (`14 passed`), `python3 -m pytest tests/test_workspace_profiler.py tests/test_semantic_layer.py tests/test_workspace_settings_api.py -q` (`16 passed`), `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_product_result_builder.py -q` (`27 passed`), P17/P20 boundary checks (`18 passed`), and full backend regression `python3 -m pytest` (`403 passed, 13 skipped`).

Latest P20-H0 cleanup result on 2026-07-01:

- Current main path inventory remains: import/profile/semantic layer -> question understanding/clarification -> SQL planning/review/schema repair/execution -> evidence validation -> reviewer/composer/business answer -> visualization/report -> Next.js UI.
- Added `tests/test_p20_architecture_cleanup_boundaries.py` to protect active agent/tool boundaries and prevent old action/chart/mock/eval/template-mining paths from returning to the main product chain.
- Removed the old trace-driven SQL template-mining helper path: `sql_planning.feedback`, `tests/test_llm_template_mining_eval_suite.py`, and `template_mining_event` trace payloads from `agents/guarded_llm_enhancer.py`.
- Preserved provider structured-output smoke coverage in `tests/test_llm_smoke_eval.py`.
- Focused cleanup baseline initially failed because P17 boundary tests still asserted P19/responsiveness-era status text; those assertions now point at P20 General Business Analysis Foundation.
- Verification passed: cleanup/P20 focused boundaries `22 passed`; project initialization/MCP boundaries `9 passed`; workspace analysis/report/product-result/business-answer focused regression `60 passed`; full backend regression `391 passed, 13 skipped`; frontend workspace-flow Vitest `49 passed`; full frontend Vitest `62 passed`; frontend production build passed.
- Legacy audit after cleanup found remaining old action/chart/mock/eval/template terms only in Historical / Superseded documentation or negative boundary/provider tests; no active main product import depends on them.

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
- Future notes at the time of P19 planning originally pointed P20 toward responsiveness, but real product testing later re-scoped P20 into the general business analysis foundation. Responsiveness is now P21 and real business tool calling/export is now P22.

P19-H2 completion note on 2026-07-01:

- Added structured `answer_reviewer` and `final_answer_composer` contracts with validation tests.
- Integrated reviewer/composer after insight drafting and before final P16 business answer normalization.
- Report sections reuse the reviewed/composed `business_answer`; deterministic `answer_consistency.py` remains the final small guardrail.
- Focused backend tests, full backend regression, frontend Vitest, and frontend production build passed.

Historical P19-H3 completion note on 2026-07-01:

- Added shared language-aware business labels for common metrics and dimensions. This included bilingual behavior for P19 acceptance, but P20 supersedes it with Chinese-first product output and English/mixed raw-header recognition only.
- Final Answer Composer now produces business-readable revise/downgrade answers, removes reviewer/internal wording from caveats, and states revenue-vs-ROI tradeoffs instead of forcing one winner.
- Product result and report section normalization apply the same field-label cleanup while keeping raw columns, rows, SQL, traces, and provider metadata in technical details.
- Added focused regression coverage for Chinese output, field-label polish, multi-metric tradeoffs, no invented ROI/profit advice, internal metadata leakage, and report section business answers.
- Follow-up fix at that time: English questions kept English fallback wording and English business labels instead of mixing Chinese labels into accepted/composed answers. This remains historical context, not a P20 product requirement.

Historical P19-H4 completion note on 2026-07-01:

- Report records now expose management-facing `executive_summary`, `key_findings`, `action_priorities`, `chart_and_evidence`, and `risks_and_limits` synthesized from reviewed/composed section `business_answer` values.
- Markdown reports used Chinese-first management structure for Chinese goals and English headings/content for English goals in P19. P20 supersedes this with Chinese-first product output while keeping SQL, trace paths, provider metadata, raw rows, and internal prompts in technical appendices.
- Chart artifacts carry title, unit, safe business annotation, and path/URL into report JSON, Markdown image embeds, and the frontend report detail view.
- Missing charts render a business-friendly “暂无可展示图表” explanation instead of visualization errors or trace metadata in the main report body.
- Focused P19-H4 backend regression passed: `python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_store.py tests/test_workspace_report_api.py tests/test_report_insight_cleanup.py tests/test_chart_product_quality.py tests/test_product_result_builder.py -q` with `57 passed`.
- Focused frontend report regression passed: `cd frontend && npm test -- workspace-flow.test.tsx` with `49 passed`.

Historical P19-H4 repair note on 2026-07-01:

- English report goals rendered English business labels in Markdown and the frontend report reader for P19 acceptance. This is superseded in P20; current product output should stay Chinese.
- Report-level chart/evidence summaries reuse the shared business field label helper so fields such as `total_revenue`, `order_count`, `avg_order_value`, and `segment` are shown as business-readable labels instead of raw column names.
- Focused repair regressions covered P19 bilingual Markdown/report detail rendering. P20 should replace or delete those assertions when they conflict with Chinese-first product behavior.

P19-H5 completion note on 2026-07-01:

- Focused backend regression passed for workspace analysis, workspace reports, product result builder, reviewer/composer, business-answer quality, chart/report cleanup, and P17 cleanup boundaries: `100 passed`.
- Full backend pytest passed: `388 passed, 13 skipped`.
- Frontend Vitest passed: `60 passed`.
- Frontend production build passed.
- Real DeepSeek acceptance completed against temporary generated workspace data outside the repo for three Chinese business questions: a single-metric top-revenue question, a revenue-vs-ROI tradeoff question, and a management channel-review report.
- Live acceptance showed real provider participation, SQL review approval, Chinese business answers with evidence, recommendations and limits, chart artifacts with displayable report/API paths, and report-level management summary, key findings, action priorities, chart/evidence, and risks/limits.
- H5 fixed a live acceptance quality gap where a clean provider factual answer could omit recommendations and caveats; the product result builder now fills only minimal evidence-based next-step guidance and query-scope caveats for sufficiently supported answers.
- Artifact hygiene was rechecked: generated databases, reports, report Markdown, chart artifacts, traces, `.env`, frontend build output, `.superpowers`, and real DeepSeek temporary artifacts remain untracked/ignored and were not staged.
- Cleanup audit found old action/chart/mock/template terms only in historical notes, deleted-file assertions, ignored generated artifacts, or necessary test doubles; no current product entry point was restored or duplicated.
- This older closeout note has been superseded by the P20 planning note below: P20 is now the general business analysis foundation, while responsiveness moves to P21 and real business tool calling moves to P22.

P19 closeout fix note on 2026-07-01:

- ProductShell model status now reads `/api/workspaces/{workspace_id}/settings` `model_mode` instead of hardcoding live mode.
- Key-only DeepSeek configuration displays `仅已配置密钥`; only `product_live_mode=true` displays `真实模型已开启`.
- Workspace settings model-mode summary reads the merged local `.env` and process environment, so provider key presence and product live mode remain separate states.
- Frontend coverage now includes loading, key-only, live-mode-on, and fetch-failure model status states without relying on a real backend.
- Local ignored generated artifacts were cleaned from `.superpowers`, chart PNG outputs, run workspaces, pytest/cache directories, `__pycache__`, and frontend build output; retained `.env`, tracked placeholders, and the historical `data/ecommerce.db` fixture were not removed or staged.
- P20 has been re-scoped after real product testing: it is now the general business analysis foundation phase, not responsiveness work. Responsiveness moves to P21 and real business tool calling moves to P22.

P20 planning note on 2026-07-01:

- Real P19 workspace testing showed that the system can query useful evidence but still over-downgrade answers to "证据不足" because safety, evidence, consistency, and expression responsibilities are too tightly coupled.
- P20 should split the chain into factual tool output, model judgment, fact validation, and business expression/report writing.
- P20 must support general business datasets by reasoning over dimensions, metrics, time fields, filters, decision goals, evidence rows, chart intents, and report sections instead of hardcoding `orders`, `channel`, `marketing_spend`, `revenue`, or ROI-only channel analysis.
- P20 cleanup policy: delete old paths, obsolete tests, fallback/template/demo compatibility code, and unused modules when they conflict with the current FastAPI/Next.js workspace product direction. Historical behavior does not need to be preserved.
- P20 implementation guidance lives in `docs/product/plans/2026-07-01-p20-general-business-analysis-foundation.md`.

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
