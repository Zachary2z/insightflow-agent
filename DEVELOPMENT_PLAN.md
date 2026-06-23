# InsightFlow Agent Development Plan

This document is the tracked development plan for InsightFlow Agent. It consolidates the phased roadmap, task boundaries, acceptance criteria, and final LLM participation rules that were previously spread across local extracted planning notes under `tmp/pdfs/`.

## Phase Development Status

Update this table after every completed phase or task so the current project position is visible at the top of the development plan.

| Phase | Name | Status | Latest result | Next action |
|---|---|---|---|---|
| P0 | Agentic SQL Core | `[x]` Complete | Core SQL workflow, validation, execution, trace, Streamlit demo, and original 20-case P0 eval baseline are complete. | Regression only |
| P1 | Reliable Analysis & Report Core | `[x]` Complete | Business context, evidence validation, charts, and Markdown reports are complete. | Regression only |
| P2 | Business Review & Action Workflow | `[x]` Complete | Weekly/monthly reports, guarded LLM enhancement, and approval-gated local actions are complete. | Regression only |
| P3 | MCP & Engineering Core | `[x]` Complete for scoped baseline | MCP contracts, FastAPI async API, trace dashboard data, Command Center UI, provider hardening, question understanding, SQL planning, and template mining are complete. | Defer Docker/CI unless explicitly selected |
| P4 | Realistic Scenario Dataset | `[x]` Complete | Realistic ecommerce scenario tables, deterministic anomalies, table docs, business rules, and seed tests are complete. | Regression only |
| P5 | Lightweight Semantic Layer | `[x]` Complete | `semantic_layer/` now loads metrics, dimensions, entities, and join paths; metric/context retrieval reads semantic metadata while preserving legacy metric compatibility. | Regression only |
| P6 | Scenario Analysis Planner | `[x]` Complete | `agents/analysis_planner.py` now decomposes scenario questions into semantic analysis steps, supports provider fallback, and writes workflow trace state. | Regression only |
| P7 | Visualization Intelligence | `[x]` Complete | `visualization/` now validates chart specs against real execution columns, renders first-batch advanced charts from real rows, falls back safely for unsupported charts, and supports provider-backed visualization planning through PromptOps. | Regression only |
| P8.1 | Visualization Agent Dedupe & External Tool Calling | `[x]` Complete | `agents/visualization_agent.py` is the only visualization business entry point; provider output selects chart spec plus delivery tool; local renderer, XLSX exporter, and Power BI mock run behind chart/tool validation; old chart agent/planner product paths were deleted. | Regression only |
| P8.2 | Intent & SQL Planning Agent Cleanup | `[x]` Complete | Provider-backed question understanding and SQL planning are the product path when configured; unsafe/sensitive guards run before providers; provider failures return explicit `provider_unavailable`; provider `llm_candidate` skips `sql_generator.py`; provider templates render by matched template id. | Regression only |
| P8.3 | Report & Insight Agent Cleanup | `[x]` Complete | Provider-backed report planning is the product path for section selection; provider-unavailable plans do not auto-select fixed sections; `insight_drafter` now drafts candidate claims before claim typing/Evidence Validator. | Regression only |
| P8.4 | Action Agent & Tool Adapter Cleanup | `[x]` Complete | Fixed action templates are removed from the product path; provider-backed action planning now selects contextual action payloads and delivery tools; execution moved to `agents/action_executor.py` and `action_delivery/` adapters behind approval/audit. | Regression only |
| P8.5 | Agent Pipeline UX | `[x]` Complete | Streamlit run summaries now expose agent pipeline steps, tool-call cards, validator gates, artifact links, provider prompt/fallback metadata, and source metadata without changing backend boundaries. | Regression only |
| P9 | Realistic Eval And Demo Polish | `[x]` Complete | 32-case realistic eval, P9 metrics, no-key mock provider/action coverage, unsafe rejection, and demo question polish are complete. | Regression only |
| P10 | MCP Contract & Lightweight Engineering Hardening | `[x]` Complete | External-safe MCP contract metadata, internal-tool exposure tests, eval artifact hygiene notes, and generated-artifact ignore coverage are complete. | Regression only |
| P11 | General Data Analysis Product | `[~]` Product hardening in progress | Core workspace backend, importers, profiling, semantic draft, workspace-aware analysis, Next.js scaffold, live DeepSeek acceptance, H1 FastAPI data source endpoints, H2 frontend wiring, and H3 old UI/API cleanup are complete; stronger natural-language live acceptance and docs cleanup still remain. | Complete H4-H5 before P12 |

Current development position: **P11 General Data Analysis Product is implemented as a working backend/product prototype, but P11 Product Hardening is still required before P12.**

## P11 Product Hardening Plan

This checklist records the required cleanup after the P11 implementation audit on 2026-06-23. P11 is not considered product-complete until these tasks pass.

### Task H1 - FastAPI Data Source Endpoints

Status: complete. `api/app.py` now exposes CSV/Excel upload, SQLite import, and source listing endpoints backed by the existing workspace importers. `api/models.py` includes source response/request contracts, `tests/test_workspace_api.py` covers upload/import/list/error paths, and `requirements.txt` includes `python-multipart` for FastAPI file uploads.

Goal: expose the existing CSV, Excel, and SQLite importers through product APIs instead of requiring Python-only test calls.

Required endpoints:

```text
POST /api/workspaces/{workspace_id}/sources/upload
POST /api/workspaces/{workspace_id}/sources/sqlite
GET  /api/workspaces/{workspace_id}/sources
```

Files:

- Modify `api/app.py`.
- Modify `api/models.py`.
- Extend `tests/test_workspace_api.py`.

Acceptance:

- CSV upload imports a table into the workspace `analysis.db`.
- Excel upload imports one table per sheet.
- SQLite registration/import copies user tables into the workspace `analysis.db`.
- `GET /sources` returns source metadata from `workspace.json`.
- Unsupported file types return HTTP 400.
- Missing workspace returns HTTP 404.

Verification:

```bash
python3 -m pytest tests/test_workspace_api.py tests/test_workspace_importers.py -q
```

### Task H2 - Wire Next.js Into The Product APIs

Status: complete. The Next.js workspace routes now call the product API client for workspace listing and creation, source upload/import/list, profile generation, semantic draft generation, workspace analysis submission, and defensive run-result rendering. Frontend tests cover the API client and interactive product flow, placeholder H2 copy has been removed, and FastAPI CORS now allows the local Next.js product frontend to call the backend in a browser.

Goal: replace placeholder pages with a usable product flow.

Files:

- Modify `frontend/lib/api.ts`.
- Modify `frontend/app/workspaces/page.tsx`.
- Modify `frontend/app/workspaces/new/page.tsx`.
- Modify `frontend/app/workspaces/[workspaceId]/datasets/page.tsx`.
- Modify `frontend/app/workspaces/[workspaceId]/profile/page.tsx`.
- Modify `frontend/app/workspaces/[workspaceId]/semantic-layer/page.tsx`.
- Modify `frontend/app/workspaces/[workspaceId]/analysis/page.tsx`.
- Modify `frontend/app/workspaces/[workspaceId]/runs/[runId]/page.tsx`.
- Modify or add components under `frontend/components/`.
- Extend `frontend/tests/api-client.test.ts`.
- Extend `frontend/tests/workspace-flow.test.tsx`.

Acceptance:

- `/workspaces` loads and renders workspace list from FastAPI.
- `/workspaces/new` can create a workspace through the API.
- `/datasets` can upload CSV/Excel, register SQLite path, and show sources.
- `/profile` can trigger and render profile generation.
- `/semantic-layer` can trigger and render semantic-layer draft.
- `/analysis` can submit a natural-language question to the workspace run API.
- `/runs/[runId]` renders SQL, result rows, chart/artifact path, trace path, and provider metadata.
- No page contains placeholder text such as "will load", "will connect", "will appear", or "will call".

Verification:

```bash
cd frontend
npm test
npm run build
```

### Task H3 - Delete Replaced Streamlit UI And Old Ecommerce API Entry

Status: complete. The tracked `ui/` package, old in-memory `RunManager`, legacy async run API tests, old `/api/runs` FastAPI routes, and `RunCreateRequest` ecommerce default were removed from the current product path. Workspace-scoped `/api/workspaces/{workspace_id}/runs` remains the product analysis entry.

Goal: prevent the old demo product path from steering future development.

Files:

- Delete `ui/__init__.py`.
- Delete `ui/components.py`.
- Delete `ui/view_models.py`.
- Modify `api/app.py`.
- Modify `api/models.py`.
- Modify or delete `api/run_manager.py` tests as needed.
- Modify `tests/test_async_run_api.py`.
- Modify `tests/test_project_initialization.py`.
- Extend `tests/test_p11_cleanup_boundaries.py`.

Acceptance:

- The tracked `ui/` package is gone.
- Old `/api/runs` endpoints are removed from the product API or explicitly moved out of the product path.
- `RunCreateRequest` no longer defaults to `data/ecommerce.db`.
- `test_project_initialization.py` no longer expects Streamlit/old UI files.
- `test_p11_cleanup_boundaries.py` asserts `app.py`, `ui/`, old eval files, and old mock-action acceptance tests are absent.
- `data/ecommerce.db` may remain only as a low-level validator/executor fixture, not as an API default or main product entry.

Verification:

```bash
python3 -m pytest tests/test_p11_cleanup_boundaries.py tests/test_project_initialization.py -q
python3 -m pytest tests/test_workspace_api.py tests/test_workspace_analysis_runner.py -q
```

### Task H4 - Strengthen Live DeepSeek Workspace Acceptance

Goal: prove the product handles a natural business question, not a SQL-shaped prompt.

Files:

- Modify `tests/test_p11_live_deepseek_workspace_analysis.py`.
- Modify `llm_ops/prompt_registry.py` or `llm_ops/structured_output.py` only if the live failure shows a prompt/schema gap.
- Modify `workspaces/semantic_draft.py` only if the semantic context is insufficient for natural questions.

New live question should be business-natural, for example:

```text
最近 90 天哪个渠道收入下降最明显？请按渠道对比收入表现，并生成适合业务复盘的图表。
```

Acceptance:

- The test does not pass `initial_sql`.
- The test does not spell out SQL formulas, exact table names, or exact SELECT clauses in the user question.
- `question_understanding.provider_called` is true.
- `sql_planning.provider_called` is true.
- `llm_sql_enhancement.provider_called` is true.
- `visualization_trace.provider_called` is true.
- SQL review approves the generated SQL.
- SQL executes against workspace `analysis.db`.
- Chart/artifact output is rooted under the workspace run directory, not `reports/charts/`.
- Trace contains `question_understanding_agent`, `sql_planning_router_agent`, `guarded_sql_candidate_agent`, and `visualization_agent` provider events.

Verification:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 \
INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1 \
python3 -m pytest tests/test_p11_live_deepseek_workspace_analysis.py -q
```

### Task H5 - Clean Current Product Documentation

Goal: make docs guide future agents toward P11, not historical Streamlit/ecommerce/eval work.

Files:

- Modify `README.md`.
- Modify `DEVELOPMENT_PLAN.md`.
- Modify `DEVELOPMENT_STATUS.md`.

Acceptance:

- Top-level current status says P11 Product Hardening is in progress until H1-H4 are complete.
- Current quickstart uses FastAPI and Next.js.
- Historical `streamlit run app.py`, `eval/run_eval.py`, and `data/ecommerce.db` references are either removed from current sections or clearly marked `Historical` / `Superseded`.
- Mock Jira/Power BI/action-delivery references are not described as current P11 product acceptance.
- P12 is not started until P11 hardening is complete.

Audit:

```bash
rg -n "streamlit run app.py|eval/run_eval.py|data/ecommerce.db|mock jira|powerbi_publisher_mock|fixed template|deterministic action template|keyword inference" README.md DEVELOPMENT_PLAN.md DEVELOPMENT_STATUS.md
```

### P11 Hardening Final Verification

Run before marking P11 complete:

```bash
python3 -m pytest
cd frontend && npm test && npm run build
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 \
INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1 \
python3 -m pytest tests/test_p11_live_deepseek_workspace_analysis.py -q
git status --short --ignored
git ls-files | rg -n "(^app.py$|^ui/|^eval/run_eval.py$|^eval/test_questions.json$|test_streamlit_app|test_action_workflow|test_provider_backed_action_drafter|test_deepseek_action_drafter_live|data/action_ops.db|eval/report.md|frontend/(node_modules|\\.next)|reports/charts/.+\\.(png|xlsx)|logs/traces/.+json)" || true
```

## 1. Project Positioning

InsightFlow Agent is a LangGraph-based multi-agent tool-calling BI workflow.

The project is not intended to be a generic Text2SQL demo or a generic data-analysis chatbot. Its core product identity is:

- Multi-agent collaboration
- Tool calling
- Real SQL execution
- Execution feedback and repair
- Traceability
- Eval-driven development
- Evidence-backed reporting
- Approval-gated action workflow

Development principle:

- P0 builds a small, stable Agentic SQL Core.
- P1 adds reliable analysis and traceable reporting.
- P2 adds business review and action workflow.
- P3 adds MCP, API, dashboard, LLM provider hardening, and engineering core.
- P4-P7 add realistic data, semantic context, scenario planning, and validated chart specs.
- P8.1-P8.4 should turn the cleanup analysis into real development work: remove duplicated agent decisions, move business judgment to LLM-backed agents, keep validators deterministic, and make tool calls look like realistic business workflows.

## 1.1 Current Agent Capability Direction

The project should now emphasize **multi-agent reasoning and tool calling**, not large keyword-rule systems. Deterministic code remains important, but mainly for safety, validation, execution, trace, and audit. If an old product-path feature conflicts with the new agent/tool direction, delete it instead of preserving compatibility.

Current capability layers:

| Layer | Agent or module | Role | Decision style |
|---|---|---|---|
| Intent | Question Understanding / Clarification | Understand business intent and missing context | LLM-first product path; deterministic code only for safety and provider-unavailable handling |
| Planning | SQL Planning Router / Analysis Planner | Choose analysis path and decompose scenario questions | LLM-first product path; deterministic code only for safety and provider-unavailable handling |
| Execution safety | SQL Reviewer, `validate_sql()`, `run_sql()` | Approve and execute SQL safely | Deterministic only |
| Fact safety | Insight Claim Typer + Evidence Validator | Classify claims and block unsupported findings | Provider can classify; Evidence Validator decides |
| Visualization | VisualizationAgent | Choose chart spec and delivery tool from user question, analysis steps, evidence, and real result columns | LLM-first product path; deterministic code validates chart columns, tool policy, artifacts, and trace |
| Delivery | Visualization delivery adapters | Execute Local / Excel / Power BI mock delivery | Deterministic policy gates and real-row artifact execution |
| Action | Action Planner / Drafter / Risk / Approval / Audit | Draft, assess, approve, execute, and audit actions | Provider can draft; approval and audit stay deterministic |

Rules should be limited to:

- Provider-unavailable behavior that is explicit and minimal; do not keep a full duplicate rule engine just to support no-key mode.
- Hard validators such as SQL safety, column existence, evidence boundaries, tool availability, auth/approval requirements, and artifact hygiene.
- Simple mechanical decisions where a model would add no value, such as checking whether a requested tool id exists.

Rules should not grow into large business-intent keyword trees for chart type or external delivery choice. Those decisions are where the project should show Agent behavior through structured provider output, validation, fallback, and trace.

Deletion policy:

- Conflicting legacy product paths should be deleted during the migration slice that replaces them.
- Obsolete tests for deleted behavior should be deleted or rewritten for the new product path.
- Temporary wrappers are allowed only when needed to keep imports stable during the same slice; they should not preserve old decision behavior.
- Do not run broad regression suites for behavior that is intentionally removed. Run focused tests for the new path during development, then run full regression and P0 eval at phase completion or before a commit/push.

## 1.2 Agent Capability And Tool Cleanup Plan

This section records the current cleanup direction before implementation. The goal is to reduce ambiguous rule-vs-agent ownership, delete duplicated business-decision logic, and make the project read as a real multi-agent tool-calling BI system.

Core principle:

```text
LLM-backed Agents decide business intent, analysis plans, chart/tool choices, report wording, and action suggestions.
Deterministic Validators decide safety, evidence, permissions, execution eligibility, artifact integrity, trace, and audit.
Tools execute real work only after the relevant validator or policy gate passes.
```

### 1.2.1 Must Keep As Deterministic Boundaries

These modules should remain deterministic. They are not "rule clutter"; they are safety, execution, evidence, or audit boundaries.

| Module | Ownership | Reason |
|---|---|---|
| `tools/sql_validator.py` | SQL safety validator | Blocks unsafe SQL, unknown tables/columns, sensitive fields, and non-SELECT statements. |
| `tools/sql_executor.py` | SQL execution tool | Executes reviewed SQL against the real database; LLMs must never execute SQL directly. |
| `tools/evidence_tool.py` | Evidence validator | Separates supported findings, hypotheses, and unsupported claims from real execution results. |
| `visualization/chart_validator.py` | Chart spec validator | Ensures model-selected chart specs reference only real `execution_result.columns`. |
| `tools/approval_tool.py` | Approval boundary | Prevents model-generated actions from self-approving. |
| `tools/audit_logger.py` | Audit boundary | Records action and approval events deterministically. |
| `tools/trace_logger.py` | Trace boundary | Records workflow and tool events deterministically. |
| `tools/schema_tool.py` | Schema tool | Reads the real database schema. |
| `tools/metric_tool.py` | Metric definition tool | Reads governed metric definitions and keeps metric semantics inspectable. |
| `tools/context_tool.py` | Business context tool | Reads business rules, table docs, and examples used by agents. |
| `tools/report_tool.py` | Report artifact tool | Saves report files after evidence and writing steps. |
| `tools/action_tool.py` | Action execution tool | Creates local task, metric-alert, and email-draft records after approval. |
| `semantic_layer/` | Semantic context layer | Provides metrics, dimensions, entities, and join paths as governed context for agents. |
| `llm_ops/` | Provider and structured-output layer | Keeps model calls prompt-versioned, schema-validated, traceable, and provider-optional. |

### 1.2.2 Replace Or Delete Business-Decision Rules

These areas should no longer grow as keyword or template rule systems. Conflicting product-path logic should be removed, not kept as a parallel compatibility path. If provider-unavailable behavior is needed, keep it explicit, small, and outside the main intelligence path.

| Current area | Problem | Target change |
|---|---|---|
| `question_understanding/router.py` complex keyword extraction | Intent understanding can become a large keyword tree. | Replace product path with LLM-first `QuestionUnderstandingAgent`; keep only basic unsafe/sensitive guards and explicit provider-unavailable behavior. |
| `sql_planning/router.py` business routing | Strategy selection between template, candidate, clarify, and reject is a planning decision. | Move product path to LLM-first `SQLPlanningAgent`; keep deterministic reject/safety only. |
| `agents/sql_generator.py` template expansion | More templates make the project look like rules rather than agentic planning. | Remove from the product path; keep only isolated test/demo SQL if a retained eval explicitly needs it. |
| `agents/report_supervisor.py::plan_business_review_sections()` | Fixed report section planning duplicates LLM report planning. | Replace product path with provider-backed `ReportPlanningAgent`; delete or isolate deterministic weekly/monthly section templates. |
| `agents/action_planner.py::build_action_plan()` | Fixed action templates make recommendations look scripted. | Replace product path with LLM-backed `ActionPlanningAgent`; Risk Assessor, Approval Gate, Executor, and Audit stay deterministic. |
| `agents/insight_agent.py` template insight generation | Template claims are less useful than contextual insight drafting. | Replace product path with LLM-backed insight drafting; Evidence Validator keeps final authority. |
| `agents/visualization_planner.py` chart keyword inference | Chart selection is exactly where agentic judgment should show. | Replace product path with P8.1 `VisualizationAgent`; chart validator and renderer remain deterministic. |
| `agents/chart_agent.py` old chart decision path | Duplicates P7/P8 visualization planning. | Deleted after the new Visualization Agent took ownership. |
| `tools/chart_tool.py` chart type inference | A tool should render, not decide business visualization intent. | Deleted; retained rendering is reached through `tools/external_visualization_tool.py` and `visualization_delivery/` adapters. |

### 1.2.3 Target Agent Ownership After Cleanup

| Capability | Target owner | LLM role | Deterministic boundary |
|---|---|---|---|
| User intent and missing context | `QuestionUnderstandingAgent` | Extract intent and ask clarification questions. | Unsafe/sensitive reject policy and explicit provider-unavailable behavior. |
| Scenario and analysis planning | `AnalysisPlannerAgent` | Decompose business questions into steps and required metrics/dimensions. | Semantic-layer context, SQL/evidence boundaries. |
| SQL strategy and candidates | `SQLPlanningAgent` / guarded SQL candidate agent | Propose strategy or candidate SQL. | `validate_sql()` and SQL Reviewer before `run_sql()`. |
| Insight drafting | `InsightAgent` / claim typer | Draft candidate findings and classify claim types. | Evidence Validator decides what survives. |
| Visualization decision | `VisualizationAgent` | Choose chart spec and delivery tool. | Chart Validator, Tool Policy Validator, real-row renderer/exporter. |
| Report writing | `ReportAgent` / `ReportWriterAgent` | Write business prose from verified findings and artifacts. | Evidence result and report artifact tool. |
| Action planning | `ActionPlanningAgent` / `ActionDrafterAgent` | Suggest task, alert, and email draft payloads. | Risk Assessor, Approval Gate, Action Executor, Audit Logger. |

### 1.2.4 Migration Order

The cleanup should be implemented in small TDD slices. Do not rewrite the whole project at once.

1. **P8.1 Visualization first**: remove duplicated chart decision ownership from `chart_agent`, `chart_tool`, and `visualization_planner`; introduce `VisualizationAgent` and external visualization tool adapters.
2. **Intent and SQL planning second**: make provider-backed intent and SQL planning the product path; delete deterministic business routing and keep only safety guards.
3. **Report planning third**: replace fixed section ownership in `report_supervisor` with LLM-backed report planning, while every SQL subtask still goes through validator/executor/evidence.
4. **Insight and action planning fourth**: replace template-style insight and action suggestions with LLM-backed drafting, while Evidence Validator, Risk Assessor, Approval Gate, Action Executor, and Audit Logger remain deterministic.
5. **Delete dead compatibility code inside each slice**: when a replacement path is accepted, delete conflicting old behavior and its obsolete tests in the same slice.

### 1.2.5 Agent Capability Dedupe Plan

The following recommendations are accepted as the cleanup target. The purpose is to remove duplicate agent responsibilities and keep each agent's ownership obvious.

| Current overlap | Decision | Development change | Acceptance |
|---|---|---|---|
| `agents/chart_agent.py` + `agents/visualization_planner.py` + `tools/chart_tool.py` | Delete duplicated chart decision ownership. | Add P8.1 `agents/visualization_agent.py`; remove old chart-decision behavior and obsolete chart decision tests. | Only one product path decides chart type and delivery tool. |
| `agents/question_understanding.py` + `agents/clarification_router.py` | Keep both, clarify ownership. | `QuestionUnderstandingAgent` owns intent/risk/missing-context judgment; `ClarificationRouterAgent` only formats/finalizes follow-up questions when the intent agent chooses `clarify`. | No separate keyword-heavy clarify decision tree. |
| `agents/sql_planning_router.py` + `agents/sql_generator.py` + `agents/guarded_llm_enhancer.py` | Consolidate under SQL planning ownership. | `SQLPlanningAgent` chooses strategy and candidate path; remove `sql_generator.py` from the product path; guarded candidate remains the path for provider SQL candidates. | No expanding SQL template library as the main intelligence. |
| `agents/report_planner.py` + `agents/report_supervisor.py::plan_business_review_sections()` | Replace fixed section ownership. | Provider-backed `ReportPlanningAgent` chooses sections; `report_supervisor.py` orchestrates execution only. Delete or isolate fixed sections and obsolete tests. | Report Supervisor no longer owns business section planning in the product path. |
| `agents/insight_agent.py` + `agents/insight_claim_typer.py` + `agents/guarded_llm_enhancer.py` insight path | Merge into one insight drafting pipeline. | New target path: LLM drafts candidate insights, claim typer classifies them, Evidence Validator filters them. Remove template-style deterministic insight as the product path. | Evidence Validator remains final authority; no duplicate insight-generation logic. |
| `agents/action_planner.py` + `agents/action_drafter.py` | Replace fixed action templates. | `ActionPlanningAgent` uses provider-backed planning to create candidate task/alert/email actions; `ActionDrafterAgent` can become part of that pipeline or be folded into it. | Action suggestions are contextual, while Risk/Approval/Execution/Audit remain deterministic. |
| `agents/risk_assessor.py` containing both risk assessment and execution | Split responsibilities. | Keep `RiskAssessorAgent` for risk/approval requirement; move execution logic into `ActionExecutorAgent` file or module. | Risk evaluation and tool execution are separate traceable steps. |
| `agents/report_agent.py` + `agents/report_supervisor.py` | Keep both, clarify scope. | `ReportAgent` saves a single analysis report; `ReportSupervisorAgent` orchestrates multi-section business reviews. | No duplicate report planning; report writing/saving boundaries stay clear. |

### 1.2.6 Agent Capability Upgrade Plan

These agent capabilities should be improved as part of cleanup, not merely renamed.

| Agent capability | Current limitation | Target capability | Required tests |
|---|---|---|---|
| Question understanding | Keyword extraction can miss business nuance. | LLM-first intent extraction with missing context, risk flags, and clarification strategy. | Provider success, malformed output handling, unsafe request rejection, provider-unavailable behavior. |
| SQL planning | Rule router and template generation overlap. | LLM-first strategy selection and guarded candidate generation. | Provider strategy success, SQL leak rejection in planning output, candidate validation, SQL Reviewer preservation. |
| Analysis planning | Already useful but still separate from downstream tool choices. | Use semantic context to plan multi-step analysis and expose required metrics/dimensions/tables to SQL and visualization agents. | Multi-step scenario planning, provider failure handling, semantic context preservation. |
| Insight drafting | Template insights are shallow. | LLM-generated candidate findings from execution rows, then claim typing and Evidence Validator filtering. | Unsupported claim blocked, supported claim retained, provider failure handling. |
| Visualization | P7 supports chart specs, but chart/tool ownership is split. | P8.1 `VisualizationAgent` selects chart spec and delivery tool from catalog. | Valid tool selection, missing-column rejection, unknown-tool rejection, real-row rendering/export. |
| Report planning/writing | Fixed sections and writer are split across supervisor/planner/writer. | Report planner selects sections; writer writes from verified evidence only; supervisor only orchestrates. | Section selection validation, SQL/claim leak rejection, evidence-backed writing. |
| Action planning | Fixed action templates reduce agentic value. | LLM-backed action suggestions from evidence, then deterministic risk/approval/execution/audit. | Action payload schema validation, approval gate preservation, audit preservation. |

### 1.2.7 Tool Realism And Replacement Plan

The tool layer should resemble tools a real business analyst, operator, or BI team would actually use. Keep core data/safety tools. Replace demo-like tools where they obscure the agent's external-tool-calling ability.

| Current tool/module | Business realism | Decision | Development plan |
|---|---|---|---|
| `tools/schema_tool.py` | High | Keep | Continue as schema discovery tool for SQL and planning agents. |
| `tools/metric_tool.py` | High | Keep | Treat as governed metric-store access; align with `semantic_layer/`. |
| `semantic_layer/` | High | Keep | Use as business semantic context for planning and visualization decisions. |
| `tools/sql_validator.py` | High | Keep | Continue as mandatory SQL gate. |
| `tools/sql_executor.py` | High | Keep | Continue as read-only execution tool. |
| `tools/evidence_tool.py` | High | Keep | Continue as factual-claim boundary. |
| `tools/context_tool.py` | Medium-high | Keep and improve later | Keep as local business knowledge source; later can become a knowledge-base adapter. |
| `tools/chart_tool.py` | Low-medium | Delete | Removed after P8.1; local rendering now runs via `tools/external_visualization_tool.py` and `visualization_delivery/` adapters. |
| `visualization/chart_renderer.py` | Medium | Keep as local renderer | Use for quick local PNG/structured output from real rows. |
| Planned `excel_exporter` | High | Add in P8.1 | Export real execution rows and chart-ready workbook for finance/ops review. |
| Planned `powerbi_publisher_mock` | High as business analogy, mock in implementation | Add in P8.1 as explicit mock | Demonstrate external BI publishing without OAuth/SaaS complexity. Return `mock://powerbi/...` and trace metadata. |
| `tools/report_tool.py` | Medium | Keep now, enhance later | Markdown remains base artifact; future adapters can add PDF/PPT/Notion-style outputs. |
| `tools/action_tool.py` | Medium | Keep execution core, replace product surface later | Local SQLite task/alert/email draft stays only as one audited adapter; later add Jira/Slack/Email mock adapters. |
| MCP server wrappers | High | Keep and extend | Use as external-facing contracts for database/report/action and future visualization/action adapters. |
| `tools/approval_tool.py` / `tools/audit_logger.py` | High | Keep | Mandatory for action safety and compliance-style traceability. |

### 1.2.8 Tool Replacement Development Slices

| Slice | Scope | Files likely affected | Acceptance |
|---|---|---|---|
| Tool Slice 1 | Visualization external tools | `agents/visualization_agent.py`, `visualization_delivery/`, `tools/external_visualization_tool.py`, deleted `agents/chart_agent.py`, deleted `tools/chart_tool.py` | LLM selects local/Excel/Power BI mock; validators approve; adapter executes; old chart decisions and obsolete tests are deleted. |
| Tool Slice 2 | Action external adapters | `agents/action_planner.py`, `agents/action_drafter.py`, `agents/risk_assessor.py`, `tools/action_tool.py`, future `action_delivery/` | LLM suggests business actions; deterministic approval/audit gates; local SQLite tool becomes one adapter among mocked Jira/Slack/Email-style tools. |
| Tool Slice 3 | Report delivery adapters | `agents/report_agent.py`, `agents/report_writer.py`, `tools/report_tool.py`, future `report_delivery/` | Markdown remains base; optional PDF/PPT/Notion-style mock delivery proves report tool-calling without real SaaS. |
| Tool Slice 4 | MCP contract cleanup | `mcp_servers/` | External contracts expose the new tool adapters without exposing internal validators as bypassable tools. |

### 1.2.9 Cleanup Acceptance Rules

- No business-decision rule tree should be expanded when a provider-backed agent already owns that decision.
- Conflicting legacy behavior should be deleted, not preserved as a parallel compatibility path.
- Every LLM-backed decision must have a prompt-specific schema and structured-output validation.
- Every model output must record `provider_called`, `fallback_used`, prompt id/version, validation error, and provider error where relevant.
- Every tool call must be traceable and must run only after its validator or policy gate passes.
- Provider-unavailable behavior may remain, but it must be explicit and minimal, not a duplicate business-rule engine.
- During a migration slice, run focused tests for the new path and retained safety boundaries. Delete or rewrite obsolete tests for removed behavior. Run full pytest and P0 eval at phase completion or before commit/push, not after every small edit.

## 2. Reference Strategy

Use reference projects selectively. InsightFlow should borrow engineering ideas, not copy project structure wholesale.

| Reference | Use for | Avoid copying |
|---|---|---|
| `adamfaik/sql-agent` | LangGraph SQL workflow, SQLite execution, execution failure repair, glass-box demo, eval benchmark, ecommerce questions | Single-file style, Text2SQL-only framing, weak Agent/Tool separation |
| `mallahyari/langgraph-sql-agent` | Multi-agent modularization, router/table selector/validator/executor/visualization planner, graph conditional edges, later FastAPI/SSE ideas | Starting with heavy React/FastAPI architecture, weaker SQL validation |
| `azain47/Multi-Agent-Text2SQL-System` | Parser-based SQL validation, feedback formatting, iterative repair loop, max retry/history ideas | Full complex system shape; use only local validation/feedback patterns |

## 3. Current Phase Status

| Phase | Status | Summary |
|---|---|---|
| P0 - Agentic SQL Core | Complete | SQLite ecommerce DB, schema/metric/sql tools, validator, executor, trace, agents, LangGraph workflow, Streamlit demo, 20-case eval |
| P1 - Reliable Analysis & Report Core | Complete | Business context retrieval, evidence validation, chart generation, Markdown report generation |
| P2 - Business Review & Action Workflow | Complete | Weekly business review, controlled LLM report planner, guarded LLM SQL/insight enhancement, approval-gated actions |
| P3 - MCP & Engineering Core | Complete for scoped baseline | Task 17, 18, 19, 19A, Streamlit Command Center UI hardening, 20, 20C, 20A, 20B, 21, 21A, 22, 23, 24, 25, 26, 27, and 28 complete; Docker/CI deferred unless explicitly selected |
| P4 - Realistic Scenario Dataset | Complete | Realistic scenario seed tables, deterministic anomaly profiles, business rules, table docs, and focused seed tests complete |
| P5 - Lightweight Semantic Layer | Complete | Semantic metrics, dimensions, entities, join paths, loader/retriever, metric tool compatibility, and context semantic attachment complete |
| P6 - Scenario Analysis Planner | Complete | Scenario-aware deterministic planner, provider-backed planner validation, workflow state/trace wiring, and P0-safe fallback are complete |
| P7 - Visualization Intelligence | Complete | Deterministic and provider-backed visualization planning, chart spec validation, advanced renderer fallback, chart-agent integration, and workflow trace metadata are complete |

## 4. LLM Enhancement Development Roadmap

This section is the product-facing list of where the project should use a large model. It separates already implemented controlled LLM pieces from future enhancements that still need development.

LLM participation rule: the model helps with understanding, planning, candidates, wording, and suggestions. Deterministic tools keep ownership of validation, execution, approval, trace, and audit.

### 4.1 Implemented LLM-Related Capabilities

| Capability | Current implementation | Files | Status |
|---|---|---|---|
| Controlled report planning | Optional provider hook selects allowlisted weekly report sections and can ask clarification questions | `agents/report_planner.py` | Complete |
| Guarded SQL candidate enhancement | Optional provider proposes SQL candidates; accepted SQL must pass `validate_sql()` | `agents/guarded_llm_enhancer.py` | Complete |
| Guarded insight enhancement | Optional provider proposes claims; claims must pass Evidence Validator before use | `agents/guarded_llm_enhancer.py` | Complete |
| Provider and PromptOps layer | Provider contract, prompt registry, prompt versions, usage/cost/latency trace metadata, smoke eval | `llm_ops/` | Complete |
| Production DeepSeek adapter | `.env` config, opt-in live test, provider errors, malformed JSON handling, strict prompt schemas | `llm_ops/deepseek_provider.py`, `llm_ops/structured_output.py` | Complete |
| Question understanding router | Deterministic extraction of metric, dimension, time range, filters, operation, limit, risk flags | `question_understanding/`, `agents/question_understanding.py` | Complete |
| SQL planning router | Deterministic routing to template, guarded `llm_candidate`, clarify, or reject | `sql_planning/`, `agents/sql_planning_router.py` | Complete |
| Provider-backed question understanding | Optional provider-backed intent extraction with prompt-specific validation and deterministic fallback | `question_understanding/provider_backed.py`, `llm_ops/prompt_registry.py`, `llm_ops/structured_output.py`, `agents/question_understanding.py` | Complete |
| Runtime provider-backed question understanding wiring | Core workflow runs question understanding before schema retrieval; env-gated DeepSeek provider can participate in workflow state and trace | `graph/workflow.py`, `graph/state.py`, `llm_ops/runtime_provider.py` | Complete |
| Provider-backed clarification router | Optional provider-backed clarification questions with prompt-specific validation, deterministic fallback, runtime workflow state, and trace metadata | `question_understanding/clarification.py`, `agents/clarification_router.py`, `graph/workflow.py`, `llm_ops/structured_output.py` | Complete |
| Provider-assisted SQL planning and guarded candidates | Optional provider-backed SQL source routing plus guarded candidate SQL generation in the core workflow; accepted candidates still require `validate_sql()` and SQL Reviewer approval | `sql_planning/provider_backed.py`, `agents/sql_planning_router.py`, `agents/guarded_llm_enhancer.py`, `graph/workflow.py` | Complete |
| Provider-backed business review decomposition | Optional provider-backed weekly/monthly report section planning in the report supervisor runtime; accepted plans can only select allowlisted sections and cannot provide SQL or claims | `agents/report_planner.py`, `agents/report_supervisor.py`, `llm_ops/runtime_provider.py`, `llm_ops/structured_output.py` | Complete |
| Provider-backed report writing | Optional provider-backed prose polishing after Evidence Validator for analysis reports and business review reports; accepted prose can only use verified findings/hypotheses and traceable artifacts | `agents/report_writer.py`, `agents/report_agent.py`, `agents/report_supervisor.py`, `llm_ops/runtime_provider.py`, `llm_ops/structured_output.py` | Complete |
| Provider-backed insight claim typing | Optional provider-backed claim classification before Evidence Validator in the core workflow and report supervisor; Evidence Validator keeps final authority | `agents/insight_claim_typer.py`, `graph/workflow.py`, `agents/report_supervisor.py`, `llm_ops/runtime_provider.py`, `llm_ops/structured_output.py` | Complete |
| Provider-backed action and email drafting | Optional provider-backed task, alert, and email draft payload drafting inside the action workflow before Risk Assessor and Approval Gate; accepted drafts cannot create records or set approval state | `agents/action_drafter.py`, `agents/action_planner.py`, `llm_ops/runtime_provider.py`, `llm_ops/structured_output.py` | Complete |
| Template mining and LLM eval suite | Saved workflow trace mining for successful `llm_candidate` patterns plus schema-aware smoke evals for valid output, malformed JSON, and schema mismatch | `sql_planning/feedback.py`, `llm_ops/eval_smoke.py`, `agents/guarded_llm_enhancer.py` | Complete |
| Scenario analysis planner | Optional provider-backed scenario decomposition with deterministic fallback, semantic-layer metrics/dimensions/tables, and workflow trace metadata | `agents/analysis_planner.py`, `graph/workflow.py`, `llm_ops/runtime_provider.py`, `llm_ops/structured_output.py` | Complete |
| Visualization safety layer | Chart spec registry, validation, and rendering from real execution rows | `visualization/` | Complete |
| Visualization delivery decision | LLM-first decision for both chart spec and delivery tool selection, gated by chart/tool validators and external-tool adapters | `agents/visualization_agent.py`, `visualization_delivery/`, `tools/external_visualization_tool.py`, `llm_ops/structured_output.py` | Complete |

### 4.2 Current LLM Enhancement Target

P8.1-P8.5, P9, and the P10 lightweight hardening slice are complete. The current model-assisted product path is already wired through intent, SQL planning, scenario planning, insight/report wording, visualization delivery, and action drafting with deterministic validators and adapters as boundaries. P10 tightened external contracts, artifact hygiene, and local quality without adding new business-decision rule trees.

| Target | Why the LLM is useful | Planned task | Safety boundary |
|---|---|---|---|
| Visualization decision | Interpret business delivery intent such as "给老板看的看板", "导出给财务复核", "临时看一下", and choose both chart spec and delivery tool | P8.1 Visualization Agent | Must not generate SQL, final claims, action payloads, or reference missing result columns |
| External visualization tool choice | Select Local Renderer, Excel Exporter, or Power BI mock publisher from a tool catalog based on business goal and available capabilities | P8.1 Tool Catalog and Delivery Tool | Tool execution must pass tool availability, auth, approval, evidence, and artifact validation |
| Agent trace explanation | Explain why a tool was chosen and whether provider/fallback/external-tool calls happened | P8.1 Workflow integration | Trace must be factual metadata, not unsupported business claims |
| Intent and SQL planning cleanup | Replace keyword-heavy routing with model-assisted planning while preserving SQL validation | P8.2 Intent & SQL Planning Agent Cleanup | Planning output must not execute SQL or bypass SQL Reviewer |
| Report and insight cleanup | Replace fixed report sections and template insights with evidence-gated LLM planning/drafting | P8.3 Report & Insight Agent Cleanup | Evidence Validator remains final authority |
| Action and tool adapter cleanup | Replace fixed action templates with contextual action planning and realistic adapters | P8.4 Action Agent & Tool Adapter Cleanup | Risk, approval, execution, and audit remain deterministic |

### 4.3 Areas That Must Stay Deterministic

| Area | Reason |
|---|---|
| `validate_sql()` | SQL safety boundary; the model cannot self-approve SQL |
| `run_sql()` | Execution boundary; only deterministic tools execute SQL |
| Evidence Validator | Fact boundary; model claims must be independently checked |
| Chart Validator | Visualization boundary; model-selected chart specs must reference only real `execution_result.columns` |
| Tool Policy Validator | External tool boundary; model-selected delivery tools must exist, be available, and satisfy auth/approval requirements |
| Approval Gate | Action boundary; model output cannot bypass approval |
| Audit Logger / Trace Logger | Audit boundary; model output cannot decide whether to record events |
| MCP tool wrappers | External contracts must not bypass internal validator, evidence, approval, or trace requirements |
| P0 eval checkpoint | Core eval must remain 20/20 at phase completion checkpoints, but deleted legacy behavior does not need to keep old tests. |

### 4.4 LLM Enhancement Acceptance Checklist

- Every real-provider output is validated by a prompt-specific schema before an agent consumes it.
- Every LLM enhancement must be wired into a real runtime path, not stop at standalone helper support.
- Every LLM enhancement must leave trace/state evidence of `provider_called`, provider-unavailable handling, prompt id/version, validation error, and provider error where relevant.
- Live DeepSeek smoke tests are required for major provider-backed phase completion, not for every small cleanup edit.
- Every LLM-assisted SQL candidate goes through `validate_sql()`.
- Every LLM-assisted insight/report claim goes through Evidence Validator.
- Every LLM-assisted action draft goes through Risk Assessor, Approval Gate, Action Executor, and Audit Logger.
- Provider failures return structured `success: false` errors or explicit provider-unavailable states and do not crash the workflow.
- Conflicting deterministic product paths should be deleted instead of preserved as no-key alternatives.
- Focused tests are sufficient during a migration slice; full pytest and `python3 eval/run_eval.py` run at phase completion or before commit/push.

## 5. Target Repository Structure

The project should continue to preserve clear Agent/Tool/Graph boundaries.

```text
insightflow-agent/
├── agents/
├── api/
├── dashboard/
├── data/
├── eval/
├── graph/
├── llm_ops/
├── mcp_servers/
├── question_understanding/
├── reports/
├── sql_planning/
├── tests/
├── tools/
├── visualization/
├── visualization_delivery/
├── app.py
├── DEVELOPMENT_PLAN.md
├── DEVELOPMENT_STATUS.md
├── README.md
└── requirements.txt
```

## 6. P0 - Agentic SQL Core

Goal: prove that InsightFlow is a multi-agent tool-calling SQL execution workflow, not a black-box Text2SQL wrapper.

### P0 Tasks

| Task | Name | Core files | Acceptance |
|---|---|---|---|
| Task 0 | Project initialization | `requirements.txt`, `README.md`, `app.py`, base folders | Dependencies install, pytest runs, Streamlit starts, folders exist |
| Task 1 | Ecommerce SQLite database | `data/seed_data.py`, `data/ecommerce.db` | Database has users/orders/order_items/products/categories with realistic sample data |
| Task 2 | Metric definition | `data/metrics.yaml`, `tools/metric_tool.py` | GMV/order/AOV definitions return formula and required filters |
| Task 3 | Schema tool | `tools/schema_tool.py` | Reads tables/columns/types and produces prompt-friendly schema text |
| Task 4 | SQL validator | `tools/sql_validator.py` | Blocks unsafe SQL, unknown tables/columns, sensitive fields, and bad metric definitions |
| Task 5 | SQL executor | `tools/sql_executor.py` | Executes real SELECT SQL with timeout/row cap and structured errors |
| Task 6 | Trace logger | `tools/trace_logger.py` | Saves node/tool/status/error/retry/latency trace events |
| Task 7 | P0 agents | `agents/supervisor.py`, `schema_agent.py`, `metric_agent.py`, `sql_generator.py`, `sql_reviewer.py`, `error_fixer.py`, `insight_agent.py` | Agents call tools instead of directly accessing external resources |
| Task 8 | LangGraph workflow | `graph/state.py`, `graph/nodes.py`, `graph/workflow.py` | Review -> execute -> repair/fail -> insight -> trace path works end to end |
| Task 9 | Streamlit glass-box demo | `app.py` | User can see agent steps, SQL, review, execution, repair, final answer, trace |
| Task 10 | P0 eval | `eval/test_questions.json`, `eval/run_eval.py`, `eval/report.md` | 20-case benchmark runs and reports success/repair/safety metrics |

### P0 Acceptance Standard

- Chinese business questions can run through the full workflow.
- SQL is generated as SELECT-only and reviewed before execution.
- Dangerous SQL does not enter `run_sql()`.
- Execution failures can be repaired once.
- Final answers are based on `execution_result`.
- Every run has a trace artifact.
- `python3 eval/run_eval.py` remains 20/20 passed.

## 7. P1 - Reliable Analysis & Report Core

Goal: produce traceable business analysis artifacts, not just SQL answers.

| Task | Name | Core files | Acceptance |
|---|---|---|---|
| Task 11 | Business context retrieval | `data/business_rules.md`, `data/table_docs.md`, `data/sql_examples.json`, `tools/context_tool.py`, `agents/context_retriever.py` | Returns relevant rules, examples, and field docs into state |
| Task 12 | Evidence Validator | `tools/evidence_tool.py`, `agents/evidence_validator.py` | Separates data-supported findings, hypotheses, and unsupported claims |
| Task 13 | Chart Agent | Historical P1 path, superseded by `agents/visualization_agent.py`, `tools/external_visualization_tool.py`, and `visualization_delivery/` | Current path uses provider-backed visualization decisions plus validated delivery adapters |
| Task 14 | Report Agent | `tools/report_tool.py`, `agents/report_agent.py` | Saves Markdown report with SQL, execution result, evidence, chart paths, trace path |

### P1 Acceptance Standard

- Reports are traceable to SQL and execution results.
- Unsupported claims are blocked or separated.
- Chart/report generation never bypasses evidence validation.
- P0 eval remains passing.

## 8. P2 - Business Review & Action Workflow

Goal: support weekly business reviews, retrospectives, and lightweight operational actions.

| Task | Name | Core files | Acceptance |
|---|---|---|---|
| Task 15 | Business Review Report | `agents/report_supervisor.py` | Weekly review decomposes into multiple SQL subtasks with review, execution, evidence, chart, and Markdown output |
| Task 15A | Controlled LLM Report Planner | `agents/report_planner.py` | Optional LLM selects only allowlisted report sections and can ask clarification questions |
| Task 15B | Guarded LLM SQL and Insight Enhancement | `agents/guarded_llm_enhancer.py` | SQL candidates require `validate_sql()`; insight claims require Evidence Validator |
| Task 16 | Action Workflow | `agents/action_planner.py`, `agents/risk_assessor.py`, `agents/action_verifier.py`, `tools/action_tool.py`, `tools/approval_tool.py`, `tools/audit_logger.py` | Action plans, risk assessment, approval gate, task/alert/email draft records, verification, audit logs |

### P2 Acceptance Standard

- Weekly reports can run multiple SQL subtasks.
- Failed subtasks are recorded structurally and do not crash the full report.
- Action creation requires approval.
- Audit logs preserve approval blocking, execution, and verification.
- LLM-assisted P2 features are optional and never replace deterministic fallback.

## 9. P3 - MCP & Engineering Core

Goal: standardize tool access, expose engineering interfaces, improve observability, and harden controlled LLM usage.

| Task | Name | Core files | Status | Acceptance |
|---|---|---|---|---|
| Task 17 | MCP Tool Layer | `mcp_servers/database_server.py`, `report_server.py`, `action_server.py`, `contracts.py` | Complete | Exposes database/report/action MCP-style wrappers without exposing internal validators/audit/eval |
| Task 18 | FastAPI + Async Run API | `api/app.py`, `api/run_manager.py`, `api/models.py` | Complete | Submit run, poll status, fetch trace/events, cancel active runs |
| Task 19 | Trace Dashboard data layer | `dashboard/trace_dashboard.py` | Complete | Summarizes trace, SQL repair, tool, eval, approval, and audit metrics |
| Task 19A | Streamlit Unified Demo | `app.py` | Complete | Shows P0/P1/P2/P3 capabilities clearly in one product demo |
| Hardening | Streamlit Command Center UI | `app.py`, `ui/view_models.py`, `ui/components.py` | Complete | First-level Command Center navigation, one-run detail, LLM Ops, Observability/Audit, Integrations, and Capability Catalog without changing backend safety boundaries |
| Task 20 | LLM Provider and PromptOps Core | `llm_ops/provider.py`, `prompt_registry.py`, `eval_smoke.py` | Complete | Provider contract, prompt versions, cost/latency metadata, smoke eval |
| Task 20C | Production DeepSeek Provider & Structured Output Validation | `llm_ops/deepseek_provider.py`, `structured_output.py` | Complete | `.env` config, opt-in live tests, malformed JSON and schema mismatch failures |
| Task 20A | Question Understanding & Clarification Router | `question_understanding/router.py`, `agents/question_understanding.py` | Complete | Extracts intent slots, returns clarify/reject/template/llm_candidate, does not generate SQL |
| Task 20B | SQL Planning Router | `sql_planning/router.py`, `feedback.py`, `agents/sql_planning_router.py` | Complete | Routes to deterministic template or guarded LLM candidate, preserves clarify/reject, does not call provider |
| Task 21 | Provider-backed Question Understanding | `question_understanding/provider_backed.py`, `llm_ops/prompt_registry.py`, `llm_ops/structured_output.py`, `agents/question_understanding.py` | Complete | Optional provider-backed intent extraction, structured validation, deterministic fallback, no SQL generation or execution |
| Task 21A | Runtime Provider-backed Question Understanding Wiring | `graph/workflow.py`, `graph/state.py`, `llm_ops/runtime_provider.py` | Complete | Env-gated DeepSeek provider can participate in core workflow question understanding without changing SQL validation or execution boundaries |
| Task 22 | Provider-backed Clarification Router | `question_understanding/clarification.py`, `agents/clarification_router.py`, `graph/workflow.py`, `llm_ops/runtime_provider.py` | Complete | Env-gated DeepSeek provider can participate in runtime clarification; ambiguous provider-backed clarification stops before schema retrieval and SQL generation |
| Task 23 | Provider-assisted SQL Planning and Guarded Candidate Integration | `sql_planning/provider_backed.py`, `agents/sql_planning_router.py`, `agents/guarded_llm_enhancer.py`, `graph/workflow.py` | Complete | Env-gated DeepSeek provider can participate in runtime SQL planning and guarded SQL candidates; planning cannot return SQL and candidate SQL still requires validation/review |
| Task 24 | LLM Business Review Decomposition | `agents/report_planner.py`, `agents/report_supervisor.py`, `llm_ops/runtime_provider.py`, `llm_ops/structured_output.py` | Complete | Env-gated DeepSeek provider can participate in weekly/monthly business review decomposition; provider can only select allowlisted sections and cannot return SQL or final claims |
| Task 25 | Evidence-backed Report Writing and Polishing | `agents/report_writer.py`, `agents/report_agent.py`, `agents/report_supervisor.py`, `llm_ops/runtime_provider.py`, `llm_ops/structured_output.py` | Complete | Env-gated DeepSeek provider can participate in report prose after Evidence Validator; provider cannot add unsupported claims, generate SQL, or bypass traceability |
| Task 26 | Guarded Insight Claim Typing | `agents/insight_claim_typer.py`, `graph/workflow.py`, `agents/report_supervisor.py`, `llm_ops/runtime_provider.py`, `llm_ops/structured_output.py` | Complete | Env-gated DeepSeek provider can classify candidate claims before Evidence Validator; classification is advisory and cannot bypass evidence filtering |
| Task 27 | LLM Action and Email Drafting | `agents/action_drafter.py`, `agents/action_planner.py`, `llm_ops/runtime_provider.py`, `llm_ops/structured_output.py` | Complete | Env-gated DeepSeek provider can draft pending task, alert, and email payloads before Risk Assessor and Approval Gate; provider cannot create records, set approval state, or send email |
| Task 28 | LLM Template Mining and Eval Suite | `sql_planning/feedback.py`, `llm_ops/eval_smoke.py`, `agents/guarded_llm_enhancer.py` | Complete | Mines saved workflow traces for repeated successful `llm_candidate` intent signatures and validates prompt outputs in smoke evals; recommendations are never auto-applied |
| Future | Docker / CI | `Dockerfile`, `docker-compose.yml`, `.github/workflows/` | Not started | Repeatable local/dev setup and CI test workflow |

### P3 Acceptance Standard

- MCP contracts return JSON-compatible dictionaries and structured errors.
- API failures return structured failed responses instead of crashing.
- Dashboard data layer does not introduce frontend or provider behavior.
- Streamlit demo makes P1/P2/P3 visible, not just P0.
- Streamlit Command Center shows one-run intent, SQL, evidence, report/action, provider/fallback, safety, and trace details without bypassing workflow helpers.
- LLM provider usage is opt-in, structured, traceable, and provider-independent by default.
- P0 eval remains 20/20 passed.

## 10. Current Next-Task Queue

The next task should be selected from the P4-P10 platform evolution roadmap. Do not start multiple future tasks at once. Historical phase plans remain tracked, but the active queue should stay focused on the smallest useful next slice.

| Priority | Candidate task | Notes |
|---|---|---|
| Done | P8.1 Visualization Agent Dedupe & External Tool Calling | Consolidate chart and delivery decisions into a Visualization Agent. The provider chooses chart spec and delivery tool from a catalog; validators and adapters enforce safety. |
| Done | P8.2 Intent & SQL Planning Agent Cleanup | Replace keyword-heavy intent and SQL routing with LLM-first agents while preserving SQL Validator and SQL Executor boundaries. |
| Done | P8.3 Report & Insight Agent Cleanup | Replace fixed report sections and template insight generation with LLM-first planning/drafting gated by Evidence Validator. |
| Done | P8.4 Action Agent & Tool Adapter Cleanup | Replace fixed action templates with LLM-first action planning and realistic action delivery adapters behind approval/audit. |
| Done | P8.5 Agent Pipeline UX | Make the cleaned P8.1-P8.4 multi-agent/tool-calling path visible in Streamlit after backend behavior is real. |
| Done | P9 Realistic Eval And Demo Polish | Added eval/demo cases for realistic cleaned agent paths and external-tool traces. |
| Done | P10 MCP Contract & Lightweight Engineering Hardening | External MCP contracts are marked as external-safe, internal validator/audit/trace tools are kept out of the public contract, and generated eval/report/trace/mock artifacts are documented and ignored. |

## 10.1 P8.1 Visualization Agent Dedupe & External Tool Calling

Goal: redesign visualization so it demonstrates agentic tool use instead of a large rule tree. P7 chart specs and validators stay as the safe foundation. P8.1 adds a single, clearer agent-facing layer that chooses **what to visualize** and **which delivery tool to call**.

### P8.1 Core Shape

| Component | Planned files | Role |
|---|---|---|
| Visualization Agent | `agents/visualization_agent.py` | Public agent entry point. Reads user question, `analysis_steps`, `execution_result`, and `evidence_result`; asks provider for a structured visualization decision when enabled; falls back deterministically only when needed. |
| Chart Spec Foundation | `visualization/chart_spec.py`, `visualization/chart_validator.py`, `visualization/chart_renderer.py` | Reuse P7 normalization, column validation, and local rendering. These are safety/tool layers, not business-intent rule engines. |
| Delivery Catalog | `visualization_delivery/tool_catalog.py` | Defines available delivery tools such as `local_renderer`, `excel_exporter`, and `powerbi_publisher_mock`, including capabilities, required inputs, auth needs, and artifact types. |
| Delivery Decision Schema | `visualization_delivery/decision.py`, `llm_ops/structured_output.py`, `llm_ops/prompt_registry.py` | Structured provider output for chart spec plus selected delivery tool, reason, expected artifact, and fallback metadata. |
| External Visualization Tool | `tools/external_visualization_tool.py`, `visualization_delivery/delivery_tool.py`, `visualization_delivery/adapters.py` | Deterministic tool wrapper that validates the selected tool and calls the adapter. Adapters execute real local work or explicit mocks. |
| Workflow Integration | `graph/state.py`, `graph/nodes.py`, `graph/workflow.py` | Add visualization decision, delivery result, and trace metadata after SQL execution and Evidence Validator. Do not move or bypass SQL/evidence safety nodes. |
| Legacy deletion | `agents/chart_agent.py`, `agents/visualization_planner.py`, `tools/chart_tool.py` | Deleted old chart-decision behavior and obsolete tests once the new Visualization Agent owned the product path. No import-safe wrapper is retained. |

### P8.1 Tool Catalog

| Tool id | Purpose | Real business analogy | P8.1 implementation boundary |
|---|---|---|---|
| `local_renderer` | Quick local chart preview | Analyst quickly checks a chart in a notebook or internal tool | Uses existing renderer and real execution rows. |
| `excel_exporter` | Create an `.xlsx` workbook with data and chart-ready sheet | Finance or operations review in Excel | Writes local workbook from real rows only. |
| `powerbi_publisher_mock` | Simulate publishing a chart spec and dataset to BI dashboard tooling | Manager-facing dashboard delivery | Explicit mock adapter returns a `mock://powerbi/...` artifact and trace metadata; no real SaaS auth/API in P8.1. |

### P8.1 LLM-First Policy

- Use the provider for meaningful business decisions: chart type, chart fields, delivery tool, and explanation of tool choice.
- Use deterministic code for hard boundaries: known tool ids, required columns, unsupported chart types, auth/approval requirements, row provenance, artifact paths, and trace metadata.
- Do not add large keyword trees for chart/tool selection. If provider is unavailable or invalid, return an explicit provider-unavailable decision or a minimal non-conflicting local renderer path; do not preserve the old chart-decision rule engine.
- Provider output must not contain SQL, final claims, action payloads, approval state, direct external credentials, or fabricated data.
- Tool adapters must receive only validated chart specs and real `execution_result.rows`.

### P8.1 TDD Plan

1. Add failing tests for provider-backed chart and delivery decisions in `tests/test_visualization_agent_delivery.py`.
2. Test that valid provider output can choose `local_renderer`, `excel_exporter`, or `powerbi_publisher_mock`.
3. Test that SQL leaks, final claims, action payloads, unknown tool ids, missing columns, malformed JSON, and provider errors are rejected or handled without reviving the old chart-decision path.
4. Test that Excel export and local render use real rows only and report `fabricated_data: false`.
5. Test that the Power BI adapter is clearly marked as a mock external tool call with `external_tool_called: true`.
6. Wire workflow state and trace after the tests describe the expected behavior.
7. Run focused visualization tests and retained workflow/chart safety regressions during development. Run full pytest and P0 eval at P8.1 completion or before commit/push.

### P8.1 Acceptance

- Provider-backed Visualization Agent can select both chart spec and delivery tool through PromptOps structured output.
- The system visibly demonstrates multi-agent behavior: SQL planning/execution/evidence remain separate from visualization planning and delivery.
- The system visibly demonstrates tool calling: the selected external visualization tool is validated, called, and traced.
- Provider-unavailable behavior is explicit and does not keep a duplicate chart rule engine.
- Chart specs still cannot reference columns absent from `execution_result`.
- Render/export/publish adapters use only real execution rows and never fabricate data.
- Provider output containing SQL, final claims, action payloads, approval fields, unknown tools, missing columns, or malformed shapes is rejected.
- Workflow trace records selected tool, provider status, fallback status, validation status, external-tool call status, and artifact path or mock URL.
- Obsolete chart-decision tests are deleted or rewritten for the new Visualization Agent path.
- P0 workflow and P0 eval are verified at P8.1 completion.

## 10.2 P8.2 Intent & SQL Planning Agent Cleanup

Goal: remove keyword-heavy business intent and SQL routing decisions from the primary product path. LLM-backed agents should decide intent, clarification, and SQL strategy; deterministic code should only guard safety and provider-unavailable handling.

### P8.2 Scope

| Component | Files likely affected | Development change |
|---|---|---|
| Question Understanding Agent | `agents/question_understanding.py`, `question_understanding/provider_backed.py`, `question_understanding/router.py` | Make provider-backed understanding the product path. Delete keyword-heavy product behavior from `router.py`; keep only unsafe/sensitive guards and explicit provider-unavailable handling. |
| Clarification Router Agent | `agents/clarification_router.py`, `question_understanding/clarification.py` | Keep as a separate agent, but it should only act when Question Understanding chooses `clarify`. |
| SQL Planning Agent | `agents/sql_planning_router.py`, `sql_planning/provider_backed.py`, `sql_planning/router.py` | Make provider-backed SQL strategy the product path. Delete deterministic business routing from the product path. |
| SQL Generator | `agents/sql_generator.py` | Stop expanding deterministic templates as main intelligence. Remove from product path; isolate only if a retained demo/eval explicitly needs it. |
| Guarded SQL Candidate | `agents/guarded_llm_enhancer.py` | Keep candidate generation behind structured output and `validate_sql()`. |
| Workflow | `graph/state.py`, `graph/nodes.py`, `graph/workflow.py` | Trace provider/fallback status for intent and SQL planning, and preserve SQL Reviewer before execution. |

### P8.2 TDD Plan

1. Add tests proving provider-backed question understanding is the default product path when provider is configured.
2. Add tests proving unsafe/sensitive questions are still blocked before SQL execution.
3. Add tests proving malformed provider intent output is rejected or handled without reviving keyword routing.
4. Add tests proving provider SQL planning output cannot contain executable SQL directly.
5. Add tests proving guarded SQL candidates still require `validate_sql()` and SQL Reviewer before `run_sql()`.
6. Delete or rewrite duplicate keyword-heavy business routing tests that no longer describe the product path.

### P8.2 Acceptance

- The primary workflow no longer depends on large keyword trees for business intent and SQL strategy.
- Question Understanding and Clarification have distinct ownership.
- SQL Planning decides strategy, but cannot execute SQL or bypass `validate_sql()`.
- `sql_generator.py` is no longer treated as the expanding intelligence layer.
- Provider errors and missing-provider mode have clear structured handling.
- Obsolete keyword-routing tests are deleted or rewritten.
- P0 workflow and P0 eval are verified at P8.2 completion.

## 10.3 P8.3 Report & Insight Agent Cleanup

Goal: remove fixed report-section and template-insight ownership from the product path. Report and insight content should come from LLM-backed planning/drafting, while Evidence Validator remains the factual boundary.

### P8.3 Scope

| Component | Files likely affected | Development change |
|---|---|---|
| Report Planning Agent | `agents/report_planner.py`, `agents/report_supervisor.py` | Make provider-backed report section planning the product path. Delete fixed weekly/monthly section planning from product logic; isolate only test fixtures that are still needed. |
| Report Supervisor | `agents/report_supervisor.py` | Orchestrate schema/context/metric/review/execution/evidence/chart/report only; stop owning business section decisions. |
| Insight Drafting | `agents/insight_agent.py`, `agents/insight_claim_typer.py`, `agents/guarded_llm_enhancer.py` | Replace template insight generation with LLM candidate insight drafting, then claim typing, then Evidence Validator. |
| Report Writing | `agents/report_writer.py`, `agents/report_agent.py` | Keep writing after Evidence Validator; provider prose must reference verified findings, hypotheses, SQL records, and artifacts only. |
| Evidence Boundary | `tools/evidence_tool.py`, `agents/evidence_validator.py` | Keep deterministic final authority. |

### P8.3 TDD Plan

1. Add tests proving provider-backed report planning chooses valid section ids and rejects SQL/final claims.
2. Add tests proving Report Supervisor executes sections but does not own product-path section selection.
3. Add tests proving LLM insight drafts are filtered by claim typing and Evidence Validator.
4. Add tests proving unsupported report/insight claims are blocked.
5. Delete or rewrite tests that assert fixed report sections as product behavior.
6. Run report supervisor, report agent, evidence validator, and workflow focused regressions during development. Run full pytest and P0 eval at P8.3 completion.

### P8.3 Acceptance

- `[x]` Report planning is LLM-first in the product path.
- `[x]` Report Supervisor is an orchestrator, not a section-rule owner.
- `[x]` Insight drafting is contextual, not template-only.
- `[x]` Evidence Validator remains final authority for all findings.
- `[x]` Reports remain traceable to SQL, execution rows, evidence, charts, and trace paths.
- `[x]` Obsolete fixed-section tests are deleted or rewritten.
- `[x]` P0 workflow and P0 eval are verified at P8.3 completion.

## 10.4 P8.4 Action Agent & Tool Adapter Cleanup

Goal: replace fixed action templates with contextual LLM-backed action planning, while keeping risk, approval, execution, verification, audit, and tool adapters deterministic.

Status: complete. `agents/action_planner.py` no longer builds fixed action templates in the product path; missing providers return structured `provider_unavailable`. Provider-backed structured output drafts action payloads and delivery-tool ids, then deterministic policy/adapters execute only after risk assessment and approval.

### P8.4 Scope

| Component | Files likely affected | Development change |
|---|---|---|
| Action Planning Agent | `agents/action_planner.py`, `agents/action_drafter.py` | Merge or clarify action planning/drafting so LLM-backed planning creates contextual task, alert, and email-draft suggestions. |
| Risk Assessor | `agents/risk_assessor.py` | Keep deterministic risk/approval requirement logic, but split execution logic out of this file. |
| Action Executor | New or split module such as `agents/action_executor.py` | Own calls to action tools after approval. |
| Action Tool Adapters | `tools/action_tool.py`, future `action_delivery/` | Keep local SQLite records, then add Jira/Slack/Email-style mock adapters as realistic business tools. |
| Approval and Audit | `tools/approval_tool.py`, `tools/audit_logger.py`, `agents/action_verifier.py` | Keep deterministic and mandatory. |

### P8.4 TDD Plan

1. Add tests proving LLM-backed action planning produces schema-valid task/alert/email suggestions from evidence.
2. Add tests proving action planning cannot set approval status or create records directly.
3. Add tests proving Risk Assessor and Approval Gate still block unapproved execution.
4. Add tests proving Action Executor calls tools only after approval.
5. Add tests for local SQLite action adapter plus at least one realistic mock adapter contract.
6. Add tests proving audit and verification records are written for blocked and executed actions.

### P8.4 Acceptance

- `[x]` Action suggestions are contextual and LLM-backed in the product path.
- `[x]` Fixed action templates are removed from the product path.
- `[x]` Risk assessment, approval, execution, verification, and audit are separate traceable steps.
- `[x]` Realistic action delivery adapters are tool-callable but cannot bypass approval.
- `[x]` Provider failures and missing-provider mode remain structured.
- `[x]` Obsolete fixed-action-template tests are deleted or rewritten.
- `[x]` P0 workflow and P0 eval are verified at P8.4 completion.

## 10.5 P8.5 Agent Pipeline UX

Goal: after P8.1-P8.4 backend cleanup is complete, update Streamlit so users can clearly see the multi-agent and tool-calling path.

Status: complete. `ui/view_models.py` now builds agent pipeline, tool-call, validator-gate, and artifact-panel structures from existing workflow state/trace data. `app.py` renders those panels in the Command Center run summary, and `ui/components.py` contains reusable table renderers.

### P8.5 Scope

| UI area | Files likely affected | Development change |
|---|---|---|
| Agent timeline | `app.py`, `ui/view_models.py`, `ui/components.py` | Show which agent made each decision, which provider prompt was used, and whether fallback occurred. |
| Tool-call cards | `app.py`, `ui/components.py` | Show schema/metric/sql/chart/report/action/external-tool calls as separate inspectable cards. |
| Validator gates | `app.py`, `ui/components.py` | Show SQL Validator, Evidence Validator, Chart Validator, Tool Policy, Approval, and Audit as explicit gates. |
| Artifact panel | `app.py`, `ui/view_models.py` | Link generated charts, Excel exports, mock Power BI URLs, reports, traces, and audit records. |

### P8.5 Acceptance

- `[x]` The UI makes the cleaned agent/tool/validator path visible.
- `[x]` Provider, fallback, validation, and tool-call metadata are easy to inspect.
- `[x]` No backend safety boundary is changed by the UI work.
- `[x]` Relevant Streamlit tests remain passing; full pytest and P0 eval run at P8.5 completion.

## 11. Final LLM Participation Boundary

InsightFlow treats LLMs as a controlled enhancement layer. The model can help with understanding, planning, candidate generation, wording, and suggestions, but deterministic tools remain responsible for approval, execution, validation, and audit.

The retained deterministic safety baseline must continue to protect SQL, evidence, approval, trace, and audit. LLM-first product paths may return structured provider-unavailable responses instead of preserving duplicate business-rule engines. P0 eval must remain 20/20 passing at phase completion checkpoints.

### Where The LLM Should Participate

| Area | Phase / task | Intended role | Boundary |
|---|---|---|---|
| Provider / PromptOps | P3 Task 20 / 20C | DeepSeek adapter, prompt registry, prompt versions, structured output validation, usage/cost/latency trace metadata | Must not replace deterministic fallback |
| Question understanding | P3 Task 20A / 21 / 21A, cleaned in P8.2 | Extract metric, dimension, time range, filters, operation, limit, and risk flags | Must not generate or execute SQL |
| Clarification routing | P3 Task 20A / 22 | Ask focused follow-up questions for ambiguous requests | Must not guess missing SQL requirements |
| SQL planning | P3 Task 20B / 23, cleaned in P8.2 | Choose template, guarded `llm_candidate`, clarify, or reject strategy | Must not return executable SQL directly |
| Guarded SQL candidate | P2 Task 15B, hardened and wired by P3 Task 20 / 20C / 23 | Propose SQL candidates for clear non-template questions | Every candidate must pass `validate_sql()` and SQL Reviewer before `run_sql()` |
| Controlled report planning | P2 Task 15A / P3 Task 24, cleaned in P8.3 | Select report sections and help decompose review tasks | Must not provide SQL or final factual claims |
| Business review decomposition | P3 Task 24, cleaned in P8.3 | Break weekly/monthly reviews, retrospectives, anomaly analysis, channel analysis, and Top/Decline analysis into subtasks | Each subtask still goes through SQL review, SQL execution, Evidence Validator, chart, and report tools |
| Guarded insight claims | P2 Task 15B / P3 Task 26, cleaned in P8.3 | Suggest or classify claims from execution results, metric context, and business context | Evidence Validator decides which claims can be used |
| Report writing / polishing | P3 Task 25, cleaned in P8.3 | Turn verified findings, hypotheses, SQL, chart paths, and trace paths into clearer business prose | Must not invent unsupported data or conclusions |
| Visualization planning | P7, cleaned in P8.1 | Select chart type and chart spec fields from user intent, analysis steps, execution columns, and evidence outputs | Must only reference real execution columns and must not generate SQL, final claims, or action payloads |
| Visualization delivery | P8.1 | Select an external visualization delivery tool from a catalog and explain why it fits the business request | Must call only registered adapters after chart/tool validation; no credentials, direct SaaS calls, final claims, or action payloads from provider output |
| Action drafting/planning | P3 Task 27, cleaned in P8.4 | Draft task, alert, and email wording from evidence-backed findings | Must not create actions without Risk Assessor, Approval Gate, Action Executor, and Audit Logger |
| Email draft content | P3 Task 27, cleaned in P8.4 | Draft stakeholder-facing email text | Must create drafts only; no sending and no approval bypass |
| Template mining feedback | P3 Task 28 | Summarize repeated successful `llm_candidate` intent patterns from saved workflow traces for future deterministic templates | Must not automatically modify production templates |
| LLM eval / smoke tests | P3 Task 20 / 20C / 28 | Validate provider availability, JSON shape, prompt schemas, malformed JSON handling, schema mismatch, and provider errors | Live provider tests must remain explicit opt-in |

### Where The LLM Must Not Take Ownership

| Deterministic owner | Reason |
|---|---|
| `validate_sql()` | SQL safety boundary; LLM must not self-approve SQL |
| `run_sql()` | Execution boundary; only deterministic tools execute SQL |
| `Evidence Validator` | Fact boundary; LLM claims must be independently checked |
| `Chart Validator` | Visualization boundary; LLM-selected specs must reference real execution columns only |
| `Tool Policy Validator` | External tool boundary; LLM-selected delivery tools must exist and satisfy adapter policy |
| `Approval Gate` | Action boundary; LLM must not bypass human or rule approval |
| `Audit Logger` / `Trace Logger` | Audit boundary; LLM must not decide whether events are recorded |
| MCP database / report / action wrappers | External contracts must not bypass validators, approval, evidence, or trace requirements |
| P0 eval baseline | Core workflow must remain deterministic and provider-independent |

### Target LLM-Assisted Flow

```text
User Question
-> QuestionUnderstandingAgent / ClarificationRouterAgent
-> SQLPlanningAgent
-> guarded LLM SQL candidate or explicit provider-unavailable handling
-> validate_sql()
-> run_sql()
-> Evidence Validator
-> Visualization Agent
-> Chart Validator / Tool Policy Validator
-> External Visualization Tool
-> Local Renderer / Excel Exporter / Power BI mock
-> Insight Drafting / Report Writing
-> Report Tool
-> ActionPlanningAgent
-> Risk Assessor / Approval Gate
-> Action Executor / Action Tool Adapter
-> Audit / Trace
```

### LLM Acceptance Rules

- README, DEVELOPMENT_STATUS, requirements, and development plan language must stay aligned on LLM boundaries.
- All real-provider outputs must pass prompt-specific structured-output validation.
- LLM work must be connected to a real runtime path with focused tests, trace evidence, and opt-in live DeepSeek verification where relevant.
- LLM-assisted SQL candidates must not bypass `validate_sql()`.
- LLM-assisted insights and reports must not bypass Evidence Validator.
- LLM-assisted action drafts must not bypass Approval Gate or Audit Logger.
- Missing-provider behavior must be structured and must not revive removed rule trees.
- P0 eval must remain 20/20 passing at phase completion checkpoints.

## 12. Long-Term Development Principles

- Do not pile on features before the current phase is stable.
- Preserve Agent/Tool/Graph boundaries.
- Prefer LLM-first product paths with deterministic safety boundaries; do not keep conflicting deterministic product paths.
- Every new behavior needs focused tests.
- High-risk boundaries must remain tool-owned: SQL validation, SQL execution, evidence validation, approval, trace, and audit.
- User-facing demos should make implemented capabilities visible and understandable.
