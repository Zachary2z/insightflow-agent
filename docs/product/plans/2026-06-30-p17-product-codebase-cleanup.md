# P17 Product Codebase Cleanup

P17 cleans InsightFlow into a focused product codebase after P16. The goal is not to remove multi-agent or tool-calling behavior. The goal is to remove historical demo, mock, and non-current product paths so the remaining project clearly represents one real business data analysis Agent product.

Current product center:

```text
workspace data import
-> profile and semantic layer
-> natural language question
-> clarification when needed
-> provider-backed planning and SQL candidate
-> SQL review and schema repair
-> SQL execution
-> evidence validation
-> business answer
-> chart artifact
-> report
-> Next.js product UI
```

## Product Decision

P17 may delete code, tests, and docs that only support old demos, mock SaaS flows, old eval flows, or non-current action workflows. If a path does not serve the current P11-P16 product or protect a current safety/tool boundary, it should be removed instead of preserved for historical compatibility.

Keep the project recognizably multi-agent:

- keep the current analysis/report agent chain;
- keep tool boundaries for SQL validation, SQL execution, schema/profile/semantic access, evidence validation, visualization delivery, report writing, and trace logging;
- keep real DeepSeek/provider-backed tests;
- keep frontend pages that users actually use for workspace data analysis and reports.

## Keep

Current product agents:

- `question_understanding_agent`
- `clarification_router_agent`
- `sql_planning_router_agent`
- `analysis_planner_agent`
- `schema_agent`
- `metric_agent`
- `guarded_sql_candidate_agent`
- `sql_reviewer_agent`
- `schema_repair_agent`
- `insight_agent`
- `insight_claim_typer_agent`
- `visualization_agent`

Current product tools:

- `tools/schema_tool.py`
- `tools/metric_tool.py`
- `tools/sql_validator.py`
- `tools/sql_executor.py`
- `tools/evidence_tool.py`
- `tools/external_visualization_tool.py`
- `tools/report_tool.py`
- `tools/trace_logger.py`
- `visualization_delivery/`

Current product surfaces:

- `api/app.py`
- `workspaces/`
- `frontend/`
- `llm_ops/`
- `graph/`
- report runner/model/Markdown files
- P16 `business_answer` model, builder, validation, and frontend rendering

## Delete Or Isolate

P17 should remove these when tests prove they are not current product dependencies:

- action workflow agents not used by the current product UI/API:
  - `agents/action_planner.py`
  - `agents/action_drafter.py`
  - `agents/risk_assessor.py`
  - `agents/action_executor.py`
  - `agents/action_verifier.py`
- action delivery and local/mock action tools:
  - `action_delivery/`
  - `tools/action_tool.py`
  - `tools/approval_tool.py`
  - `tools/audit_logger.py`
  - `mcp_servers/action_server.py`
- mock SaaS visualization delivery entries that are not real integrations:
  - `powerbi_publisher_mock` was removed from current runtime delivery in P17-H3
- historical eval/demo scaffolding when no current test requires it:
  - old eval runner references
  - old demo-only reports
  - old generated-output docs
- historical planning/spec docs that confuse current product direction:
  - stale P11-P13 superpowers specs if they are not needed by current development;
  - old implementation plans that describe superseded UI or output contracts.

## Do Not Delete

P17 must not delete:

- SQL Reviewer or `validate_sql`;
- SQL Executor or `run_sql`;
- Evidence Validator;
- schema repair;
- trace logging;
- visualization agent and local chart rendering;
- P12 report runner;
- P16 business answer contract and tests;
- real DeepSeek live tests;
- Next.js product pages;
- workspace import/profile/semantic-layer code.

## Task Queue

| Task | Scope | Status |
|---|---|---|
| P17-H1 | Inventory current product dependencies and prove action/mock/eval paths are not required by product entry points | Complete |
| P17-H2 | Delete action workflow and mock action delivery code after focused failing boundary tests are updated | Complete |
| P17-H3 | Remove mock SaaS visualization entries or mark future integrations as explicit unsupported placeholders | Complete |
| P17-H4 | Delete obsolete historical eval/demo docs and tests that no longer protect current product behavior | Complete |
| P17-H5 | Simplify README, DEVELOPMENT_PLAN, and DEVELOPMENT_STATUS so current product and remaining agent/tool chain are obvious | Complete |
| P17-H6 | Final artifact hygiene, legacy audit, full backend/frontend regression, and real DeepSeek acceptance | Complete |

## P17-H1 Inventory Result

P17-H1 added `tests/test_p17_product_cleanup_boundaries.py` as the deletion safety boundary for H2/H3. The test intentionally protects current product paths, not historical demo paths.

Current product dependency inventory:

- FastAPI product entry: `api/app.py` exposes workspace sources, settings, profile, semantic draft, analysis runs, run history/detail, artifacts, and workspace reports.
- Analysis runner: `workspaces.analysis_runner` calls `graph.workflow.run_workflow()`, persists full P16 product results, and supports clarification continuation.
- Report runner: `workspaces.report_runner` reuses workspace analysis per report section and requires the current P16 `business_answer` contract.
- LangGraph product chain: `graph.workflow` / `graph.nodes` route through question understanding, clarification, SQL planning, analysis planner, schema, metric, guarded SQL candidate, SQL reviewer, schema repair, SQL execution, insight, insight claim typing, visualization, and trace save.
- Current product tools: schema, metric, SQL validator, SQL executor, evidence, external visualization, report, trace, and visualization delivery.
- Frontend product entry: `frontend/lib/api.ts`, `RunResult.tsx`, and `ReportSection.tsx` use workspace analysis/report APIs and the P16 `business_answer` shape.
- MCP kept boundary: database/report MCP wrappers are retained only as safe wrappers and do not expose internal validators, approval, audit, action, trace, eval, or old chart tools directly.

H1 proved these are not current product dependencies:

- action workflow agents: `agents/action_planner.py`, `agents/action_drafter.py`, `agents/risk_assessor.py`, `agents/action_executor.py`, `agents/action_verifier.py`;
- action delivery/tooling: `action_delivery/`, `tools/action_tool.py`, `tools/approval_tool.py`, `tools/audit_logger.py`, `mcp_servers/action_server.py`;
- mock SaaS names such as `jira_ticket_mock`;
- old eval runner paths and frontend action workflow paths;
- old chart paths: `agents/chart_agent.py`, `agents/visualization_planner.py`, and `tools/chart_tool.py`.

H2 recommended deletion set:

- Delete action workflow agents and action delivery/tooling after preserving any still-useful safety idea in current docs/tests.
- Delete or update tests whose only purpose is action MCP/action delivery behavior.
- Remove provider/action-drafter prompt/runtime-provider references if no current product test still requires them.

## P17-H2 Deletion Result

P17-H2 removed the action workflow and mock action delivery path from the current product codebase:

- deleted action workflow agents: `agents/action_planner.py`, `agents/action_drafter.py`, `agents/risk_assessor.py`, `agents/action_executor.py`, and `agents/action_verifier.py`;
- deleted action delivery/tooling: `action_delivery/`, `tools/action_tool.py`, `tools/approval_tool.py`, `tools/audit_logger.py`, and `mcp_servers/action_server.py`;
- removed action-drafter provider runtime hooks from `llm_ops/runtime_provider.py`;
- removed the active `action_drafter` prompt from `llm_ops/prompt_registry.py`;
- removed the action-drafter structured-output branch from `llm_ops/structured_output.py`;
- updated tests that only existed for action workflow behavior in runtime provider, product live mode, PromptOps, trace dashboard, and MCP tool-layer coverage.

TDD result:

- RED: `python3 -m pytest tests/test_p17_product_cleanup_boundaries.py -q` failed with `3 failed, 6 passed` before deletion because the action files, runtime hooks, and prompt entry still existed.
- GREEN: the same focused boundary suite passed after deletion with `9 passed`.

Verification result:

- `python3 -m pytest tests/test_project_initialization.py tests/test_mcp_tool_layer.py -q` passed with `9 passed`.
- `python3 -m pytest tests/test_runtime_provider.py tests/test_product_live_mode.py tests/test_llm_provider_promptops.py tests/test_trace_dashboard.py -q` passed with `16 passed`.
- `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py -q` passed with `34 passed`.
- `cd frontend && npm test` passed with `57 passed`.
- `cd frontend && npm run build` passed.
- Required H2 dependency audit found no active-code references to deleted action workflow, delivery, runtime-provider, prompt, MCP, frontend, workspace analysis, or workspace report paths. Remaining hits are deletion/history notes or tests asserting deleted paths remain absent.

## P17-H3 Mock SaaS Visualization Cleanup Result

P17-H3 removed the remaining mock SaaS visualization delivery runtime path:

- removed `powerbi_publisher_mock` from `visualization_delivery.tool_catalog.DELIVERY_TOOL_CATALOG`;
- removed the Power BI mock adapter dispatch branch from `visualization_delivery.adapters.execute_delivery_tool()`;
- removed `powerbi_publisher_mock` from the active `visualization_agent` prompt allowlist;
- updated `tests/test_p17_product_cleanup_boundaries.py` so mock SaaS visualization delivery is asserted as not a runtime tool option;
- updated visualization-agent tests so provider attempts to select `powerbi_publisher_mock` are rejected and fall back to the real local renderer;
- updated structured-output tests so current provider validation allows only `local_renderer` and `excel_exporter`.

Current runtime visualization delivery options:

- `local_renderer`: renders local chart artifacts from real execution rows;
- `excel_exporter`: writes local XLSX exports from real execution rows.

Future SaaS integrations are P18-only. Feishu, WeCom/DingTalk, Tencent Docs, WPS-compatible exports, Power BI, FineBI, and FanRuan must not appear as runtime visualization delivery tools until real auth/API/error-handling integrations exist.

TDD result:

- RED: `python3 -m pytest tests/test_p17_product_cleanup_boundaries.py tests/test_visualization_agent_external_tools.py tests/test_deepseek_provider_structured_output.py -q` failed with `4 failed, 36 passed` because `powerbi_publisher_mock` still existed in the runtime catalog, provider-selected mock delivery still succeeded, direct mock delivery still succeeded, and workflow trace still recorded the mock SaaS tool as a successful runtime path.
- GREEN: the same focused suite passed after cleanup with `41 passed`.

## P17-H4 Historical Eval/Demo Cleanup Result

P17-H4 closed the old eval/demo/Streamlit cleanup boundary:

- `eval/run_eval.py`, `eval/test_questions.json`, `tests/test_eval_runner.py`, and `tests/test_streamlit_app.py` are not current product files and are not tracked;
- the README Quickstart and Verification sections point only to the FastAPI backend, Next.js frontend, workspace analysis/report APIs, current backend pytest, frontend tests, frontend build, and real DeepSeek live acceptance;
- the old P12 superpowers design spec is now explicitly marked Historical / Superseded and points current implementation guidance to `docs/product/plans/` plus the P16 `business_answer` contract;
- P17 boundary tests now assert old eval/demo/Streamlit paths stay deleted or historical instead of reappearing as product instructions.

TDD result:

- RED: `python3 -m pytest tests/test_p17_product_cleanup_boundaries.py tests/test_p11_cleanup_boundaries.py -q` failed with `2 failed, 15 passed` because H4 docs still showed Planned and the P12 superpowers spec was not marked Historical / Superseded.
- GREEN: the same focused suite passed after H4 docs cleanup.

## P17-H5 Product Docs And Status Surface Result

P17-H5 simplified the main product documentation and status surfaces:

- README now describes the current FastAPI backend, Next.js frontend, workspace analysis/report APIs, current multi-agent/tool-calling chain, P16 `business_answer` contract, and P17 cleanup status.
- DEVELOPMENT_PLAN now focuses on current product direction, the P16 contract, and the P17/P18 roadmap instead of long historical phase logs.
- DEVELOPMENT_STATUS now works as a concise status surface for current phase, task, next task, last completed task, P17 H-task state, and latest verification.
- Retained P11/P12/P13 superpowers specs are marked Historical / Superseded and point current implementation guidance to `docs/product/plans/`, the P16 `business_answer` contract, and P17 cleanup.
- Old eval/demo/action/mock/chart wording is retained only in Historical / Superseded notes, P17 cleanup history, or test-boundary assertions.

## P17-H6 Final Hygiene And Acceptance Result

P17-H6 completed final cleanup closeout:

- artifact hygiene keeps generated databases, reports, chart files, traces, workspace instances, `.next`, pytest cache, `__pycache__`, sample data, `.env`, virtualenvs, and dependency directories out of committed product artifacts;
- only required `.gitkeep` placeholders remain for empty runtime artifact directories;
- legacy audit found old Streamlit, eval runner, action delivery, mock SaaS, chart-agent/planner/tool, fixed-template, deterministic-action-template, and keyword-inference terms only in Historical / Superseded documentation or deletion-boundary tests, not active product entry points;
- full backend pytest, focused cleanup boundaries, frontend Vitest, frontend production build, and real DeepSeek P12/P13/P15 live acceptance passed.

P17 is complete. P18 is the next phase and should focus on business answer consistency before real authenticated external business tool integrations. External integrations remain important, but they should not publish or export inconsistent conclusions.

## Acceptance

P17 acceptance checklist is complete:

- the current workspace analysis and report product still works;
- the remaining agents and tools map directly to the current product chain;
- mock SaaS/action paths are gone or explicitly future-only and unreachable from current product entry points;
- old Streamlit/eval/chart-agent/chart-tool/visualization-planner paths are not restored;
- P16 `business_answer` output remains the only analysis/report product answer contract;
- full backend pytest passes;
- frontend tests and production build pass;
- real DeepSeek P12, P13, and P15 acceptance tests pass;
- generated artifacts, caches, workspace runs, chart files, trace files, sample data, `.env`, `.venv`, and dependency directories remain untracked.

## P18 Follow-Up

P18 starts after P17 cleanup with `docs/product/plans/2026-06-30-p18-business-answer-consistency.md`. Its working direction is:

- align `headline`, `direct_answer`, `why`, evidence bullets, recommendations, chart annotations, and report summaries;
- handle multi-metric tradeoffs without hardcoding sample tables or field values;
- avoid unsupported budget/action recommendations when comparative evidence is insufficient;
- keep the implementation small, readable, and free of keyword-heavy business rule trees.

Real China-oriented external tool calling is deferred to a later phase:

- Feishu Bitable / Feishu Docs for evidence tables and report publishing;
- WeCom or DingTalk messages for analysis/report notification;
- Tencent Docs or WPS/Excel-compatible exports for business circulation;
- Power BI/FineBI/FanRuan only as later BI integration research.

Google Sheets is not the primary P18 target because it is not a strong default fit for China business usage.
