# Lightweight Agentic BI Platform Evolution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve InsightFlow Agent from an ecommerce BI workflow demo into a lightweight Agentic BI platform prototype with realistic business scenarios, a small semantic layer, controlled LLM-assisted planning, advanced visualization, clearer Agent Pipeline UX, and preserved safety boundaries.

**Architecture:** Keep the existing Agent/Tool/Graph backbone. Add realistic scenario data, semantic metadata, visualization intelligence, and product-facing scenario workflows around the current workflow instead of replacing it. Split growing UI/data modules only where it reduces complexity and makes the Agent behavior easier to demonstrate.

**Tech Stack:** Python, SQLite, LangGraph, Streamlit, FastAPI, matplotlib or Plotly, YAML/JSON semantic metadata, DeepSeek-compatible optional LLM provider, pytest.

---

## 1. Current Project Inventory

### 1.1 What Already Exists

InsightFlow Agent already has the foundations of an Agentic BI system:

- LangGraph workflow in `graph/workflow.py`.
- Typed workflow state in `graph/state.py`.
- Workflow nodes in `graph/nodes.py`.
- Agents under `agents/` for question understanding, clarification, schema retrieval, metric retrieval, SQL generation, SQL review, execution repair, insight generation, evidence validation, report writing, action planning, risk assessment, action execution, and action verification.
- Tools under `tools/` for schema, metrics, SQL validation, SQL execution, evidence validation, chart rendering, report saving, approval records, action records, audit logging, and trace logging.
- LLM provider and PromptOps under `llm_ops/`.
- SQL planning and template mining under `sql_planning/`.
- Question understanding under `question_understanding/`.
- FastAPI async run API under `api/`.
- MCP-style tool contracts under `mcp_servers/`.
- Trace dashboard data layer under `dashboard/`.
- Streamlit Command Center in `app.py`, `ui/view_models.py`, and `ui/components.py`.
- P0 eval runner in `eval/run_eval.py`.
- Baseline P0 eval cases in `eval/test_questions.json`.

### 1.2 Existing Engineering Foundations

The current project already has useful engineering foundations:

- `requirements.txt` for dependency installation.
- `.env.example` for provider configuration shape.
- `.gitignore` for local environment and generated artifact hygiene.
- `tests/` with unit, integration-style, workflow, provider, Streamlit import, MCP, FastAPI, trace, eval, report, action, and live-provider opt-in tests.
- `eval/run_eval.py` and `eval/test_questions.json` as a deterministic P0 regression benchmark.
- `logs/traces/`, `tools/trace_logger.py`, and `dashboard/trace_dashboard.py` for trace observability.
- `tools/audit_logger.py`, `tools/approval_tool.py`, and action records for auditability.
- `llm_ops/prompt_registry.py`, `llm_ops/structured_output.py`, and `llm_ops/runtime_provider.py` for provider abstraction, prompt metadata, structured-output validation, and fallback behavior.
- `api/` for FastAPI async workflow execution.
- `mcp_servers/` for MCP-style tool contracts.
- `README.md`, `DEVELOPMENT_PLAN.md`, and `DEVELOPMENT_STATUS.md` for user-facing and development-state documentation.
- `.gitkeep` files under generated output directories so reports, charts, and traces have stable locations without committing generated artifacts.

### 1.3 Current Strengths

- Clear Agent/Tool/Graph separation.
- `validate_sql()` and SQL Reviewer prevent unsafe SQL from reaching `run_sql()`.
- Evidence Validator prevents unsupported claims from becoming final findings.
- Approval Gate and Audit Logger prevent action creation without approval and preserve action records.
- Trace Logger makes every workflow inspectable.
- Optional DeepSeek provider is gated by runtime switches and structured-output validation.
- Deterministic no-key baseline works and must remain available.
- FastAPI and MCP surfaces prove the system is not only a Streamlit demo.

### 1.4 Current Gaps

- Demo data is too narrow: mostly orders, order_items, products, categories, and users.
- P0 questions are too template-oriented: Top products, categories, city GMV, order count, and safety blocks.
- `agents/sql_generator.py` is intentionally deterministic and keyword-driven, which makes the project look like a rules demo for many questions.
- `tools/chart_tool.py` supports only bar, line, and pie charts.
- Streamlit shows many technical capabilities, but it still does not make each Agent's role obvious enough for product demos or interviews.
- The project has no lightweight semantic layer for metrics, dimensions, entities, join paths, and business terms beyond `data/metrics.yaml`, `data/table_docs.md`, and `data/business_rules.md`.
- Realistic LLM participation is hard to demonstrate because the data and scenario eval do not require enough non-template reasoning.
- There is no `pyproject.toml` or equivalent central test/lint configuration.
- There is no single local quality command for seed, focused tests, full tests, P0 eval, and scenario eval.
- Live-provider tests exist, but test markers and skip rules should be centralized so no external API is called accidentally.
- Generated artifact hygiene is documented, but not enforced by tests.
- There is no lightweight engineering contract test that verifies key docs, env examples, output directories, and run commands stay consistent.

## 2. Target Product Shape

The target is not a heavy universal BI suite. The target is a lightweight Agentic BI platform prototype:

```text
Business question
-> Intent and scenario understanding
-> Semantic metric and join-path retrieval
-> Analysis plan
-> SQL candidate generation
-> SQL validation and review
-> SQL execution
-> Evidence validation
-> Visualization planning and rendering
-> Report writing
-> Approval-gated action drafting
-> Trace and audit
```

The product should feel like a focused analysis workbench:

- **Ask:** quick question answering and simple SQL analysis.
- **Scenarios:** realistic business workflows such as GMV decline diagnosis, marketing ROI, inventory risk, refund anomaly, and promotion review.
- **Visualize:** advanced chart generation from user intent and query results.
- **Reports:** evidence-backed analysis reports and business reviews.
- **Actions:** approval-gated action recommendations.
- **Agent Pipeline:** clear explanation of each Agent, tool call, LLM participation, fallback, and safety gate.
- **Ops:** Trace, Audit, Eval, LLM Ops, MCP, and FastAPI surfaces for technical review.

## 3. Scope Cuts To Keep The Project Lightweight

### 3.1 Keep

- SQLite as the primary demo database.
- Streamlit as the main frontend.
- Existing FastAPI async API.
- Existing MCP-style contracts.
- Existing optional DeepSeek provider.
- Existing deterministic baseline.
- Existing P0 eval as a regression baseline.
- Existing action workflow as local SQLite task, alert, and email draft records.

### 3.2 Deprioritize

- React frontend.
- Docker and CI until after realistic scenarios are stable.
- Full RBAC and multi-tenant account management.
- External task systems, email sending, Slack, Jira, or CRM integrations.
- Multiple production data warehouse connectors.
- Dashboard builder or drag-and-drop BI editor.
- Automatic production template writing from mined LLM traces.

### 3.3 Modify Or Reduce

- Move old technical demo surfaces below product-facing scenario workflows.
- Keep Capability Catalog as an appendix page, not a main path.
- Keep Trace JSON collapsed by default.
- Convert raw source/safety tables into Agent Pipeline summaries.
- Split `app.py` into smaller UI page modules once the scenario UI lands.
- Split `agents/report_supervisor.py` section templates into a separate module before adding more scenario reports.
- Split `data/seed_data.py` into focused seed modules before adding more realistic tables.

### 3.4 Project Structure Guardrails

These guardrails are required for every phase after P4:

| Area | Guardrail |
|---|---|
| `app.py` | Acts as Streamlit entrypoint and workflow helper host; product pages live in `ui/pages.py`. |
| `ui/` | Owns presentation, view models, and Streamlit rendering; it does not call SQL tools directly. |
| `graph/` | Owns workflow orchestration; UI changes must not add alternate workflow paths. |
| `agents/` | Owns reasoning and domain roles; new Agents require trace metadata and eval coverage. |
| `tools/` | Owns side effects, validation, SQL execution, chart rendering, approval, audit, and trace. |
| `semantic_layer/` | Owns metric, dimension, entity, and join-path metadata; it does not execute SQL. |
| `visualization/` | Owns chart spec validation and rendering; it receives validated data only. |
| `data/` | Owns deterministic demo data and documentation; realistic scenarios are separate from base seed data. |
| `eval/` | Owns regression and scenario evaluation; no demo behavior is accepted without eval coverage. |

Size and ownership constraints:

- Do not add new top-level packages unless they appear in this plan or replace an existing oversized module.
- Do not add a second frontend framework.
- Do not add a second database engine.
- Do not add a new provider path unless it uses `llm_ops/runtime_provider.py`, trace metadata, and structured validation.
- Do not add new Streamlit top-level tabs outside `Ask`, `Scenarios`, `Visualize`, `Reports`, `Actions`, `Agent Pipeline`, and `Ops`.
- Do not add raw SQL execution paths outside the existing workflow and SQL tool boundary.
- Do not add new template-only demo behavior unless the same phase adds eval coverage.
- If a file becomes responsible for two unrelated behaviors, split it in the same phase instead of carrying the weight forward.

## 4. Target Repository Changes

```text
data/
  seed_data.py
  seed_realistic_scenarios.py
  scenario_profiles.py
  business_rules.md
  table_docs.md
  sql_examples.json
  metrics.yaml

semantic_layer/
  __init__.py
  metrics.yaml
  dimensions.yaml
  entities.yaml
  join_paths.yaml
  loader.py
  retriever.py

visualization/
  __init__.py
  chart_registry.py
  chart_spec.py
  chart_validator.py
  chart_renderer.py

agents/
  analysis_planner.py
  visualization_planner.py

ui/
  pages.py
  agent_pipeline.py
  scenario_view_models.py
  visualization_components.py

eval/
  realistic_scenarios.json
  run_realistic_eval.py

engineering/
  local_quality.md

tests/
  test_realistic_seed_data.py
  test_semantic_layer.py
  test_analysis_planner.py
  test_visualization_intelligence.py
  test_realistic_eval_runner.py
  test_agent_pipeline_view_model.py
  test_ui_structure_slimming.py
  test_project_structure_guardrails.py
  test_engineering_contracts.py

pyproject.toml
Makefile
```

This structure adds platform capabilities without rewriting the existing graph, tools, or provider layer.

Planned moves and reductions are part of the development scope:

```text
app.py
  Keep only Streamlit bootstrap, workflow helper calls, and page dispatch.
  Move page rendering to ui/pages.py.

ui/components.py
  Keep reusable display components.
  Move Agent Pipeline-specific rendering to ui/agent_pipeline.py.
  Move chart-specific rendering to ui/visualization_components.py.

Capability Catalog / MCP / FastAPI / Trace Dashboard
  Move from primary product navigation into Ops.
  Keep them available for technical review.

Raw trace JSON
  Remove as a primary page-level surface.
  Keep inside collapsed debug expanders.

data/seed_data.py
  Keep base ecommerce schema and seed entrypoint.
  Move realistic scenario inserts into data/seed_realistic_scenarios.py.

agents/report_supervisor.py
  Keep orchestration behavior.
  Extract scenario report section templates when P9 adds scenario report polish.
```

No planned task deletes `graph/`, `agents/`, `tools/`, `llm_ops/`, `dashboard/`, `api/`, `mcp_servers/`, or `eval/`. The lightweight goal is to reduce demo clutter and oversized files while preserving the Agent/Tool/Graph architecture.

## 5. Roadmap Overview

| Phase | Name | Purpose | Weight |
|---|---|---|---|
| P4 | Realistic Scenario Dataset | Make the demo feel like real business analysis instead of fixed templates | Medium |
| P5 | Lightweight Semantic Layer | Make metrics, dimensions, entities, and join paths configurable | Medium |
| P6 | Scenario Analysis Planner | Let Agent workflow decompose real business questions before SQL | Medium |
| P7 | Visualization Intelligence | Generate advanced charts from user intent and validated data | Medium |
| P8 | Agent Pipeline UX | Make multi-agent/tool/LLM participation obvious in Streamlit | Low-medium |
| P8.5 | Structural Slimming And UI Consolidation | Move old demo surfaces into Ops and split oversized UI/data files | Low-medium |
| P9 | Realistic Eval And Demo Polish | Prove the scenario workflows are reliable and resume-ready | Low-medium |
| P10 | Lightweight Engineering Hardening | Add local quality gates, test markers, artifact hygiene, and docs consistency checks | Low |

The phases should be implemented sequentially. P4 and P5 unlock meaningful LLM usage; P7 makes the platform feel like data analysis rather than SQL execution; P8 makes the Agent value visible; P8.5 removes or moves old demo surfaces so the product stays lightweight before P9 demo polish; P10 makes the lightweight structure repeatable without introducing production DevOps weight.

## 6. P4 Realistic Scenario Dataset

### Goal

Expand the ecommerce demo database with realistic business scenario data that requires multi-table analysis and makes non-template questions meaningful.

### Files

- Modify: `data/seed_data.py`
- Create: `data/seed_realistic_scenarios.py`
- Create: `data/scenario_profiles.py`
- Modify: `data/table_docs.md`
- Modify: `data/business_rules.md`
- Modify: `data/metrics.yaml`
- Create: `tests/test_realistic_seed_data.py`

### New Tables

| Table | Purpose |
|---|---|
| `marketing_campaigns` | Campaign metadata, channel, spend owner, date range |
| `campaign_daily_metrics` | Daily impressions, clicks, spend, attributed orders, attributed GMV |
| `traffic_sessions` | Channel, sessions, product/category landing target, add-to-cart, checkout, paid orders |
| `inventory_snapshots` | Product inventory by day, available quantity, inbound quantity |
| `stockout_events` | Product-level stockout windows |
| `refund_requests` | Refund request date, order, product, reason, amount, status |
| `product_reviews` | Product ratings, review sentiment, review date |
| `pricing_events` | Price changes and discount windows |
| `promotion_events` | Promotion campaign metadata and target products/categories |
| `fulfillment_events` | Shipping delay, delivery status, logistics issue reason |

### Scenario Events To Seed

1. Cameras GMV decline caused by stockout and refund-rate increase.
2. Paid search channel drives high GMV but low ROI after spend increases.
3. Promotion increases order count but reduces AOV and net GMV quality.
4. High-GMV product also has high negative review rate and refund risk.
5. City-level conversion drops because checkout conversion falls while sessions remain stable.

### TDD Steps

- [ ] Write failing tests in `tests/test_realistic_seed_data.py` asserting new tables exist after seeding.
- [ ] Write failing tests asserting each scenario event is queryable with deterministic SQL.
- [ ] Extend seed code with deterministic random seed and fixed scenario injections.
- [ ] Run `python3 -m pytest tests/test_realistic_seed_data.py -q`.
- [ ] Run `python3 -m pytest tests/test_seed_data.py tests/test_schema_tool.py tests/test_sql_validator.py -q`.
- [ ] Run `python3 eval/run_eval.py`.

### Acceptance

- Existing P0 schema remains compatible.
- Existing P0 eval remains 20/20.
- New realistic tables have stable row counts and fixed known anomalies.
- Scenario facts can be validated through SQL, not prose.
- Sensitive fields remain protected by existing validator rules.

## 7. P5 Lightweight Semantic Layer

### Goal

Add a small semantic layer so the system can map business language to metrics, dimensions, entities, and join paths without becoming a heavy BI modeling platform.

### Files

- Create: `semantic_layer/__init__.py`
- Create: `semantic_layer/metrics.yaml`
- Create: `semantic_layer/dimensions.yaml`
- Create: `semantic_layer/entities.yaml`
- Create: `semantic_layer/join_paths.yaml`
- Create: `semantic_layer/loader.py`
- Create: `semantic_layer/retriever.py`
- Modify: `agents/metric_agent.py`
- Modify: `tools/metric_tool.py`
- Modify: `data/metrics.yaml` only if the old file is kept as a compatibility alias.
- Create: `tests/test_semantic_layer.py`

### Metrics To Support

- `gmv`
- `net_gmv`
- `order_count`
- `aov`
- `refund_rate`
- `conversion_rate`
- `checkout_conversion_rate`
- `cac`
- `roi`
- `roas`
- `repeat_purchase_rate`
- `stockout_rate`
- `negative_review_rate`
- `on_time_delivery_rate`

### Dimensions To Support

- product
- category
- city
- channel
- campaign
- customer_segment
- time
- promotion

### Join Paths To Support

Examples:

- orders -> order_items -> products -> categories
- orders -> users -> customer_segments
- marketing_campaigns -> campaign_daily_metrics
- traffic_sessions -> products
- refund_requests -> orders -> order_items -> products
- inventory_snapshots -> products
- product_reviews -> products

### TDD Steps

- [ ] Write failing tests that load metrics, dimensions, entities, and join paths.
- [ ] Write failing tests for alias resolution such as "销售额", "GMV", "收入" -> `gmv`.
- [ ] Write failing tests for join path retrieval from `refund_rate by category`.
- [ ] Implement YAML loaders and structured retrieval helpers.
- [ ] Update Metric Agent to use semantic layer while preserving old `data/metrics.yaml` compatibility.
- [ ] Run `python3 -m pytest tests/test_semantic_layer.py tests/test_metric_tool.py tests/test_p0_agents.py -q`.
- [ ] Run `python3 eval/run_eval.py`.

### Acceptance

- Semantic metadata is human-readable and versionable.
- Existing metric retrieval behavior remains compatible.
- New scenario metrics can be retrieved without hardcoded if/else expansion.
- Join paths are retrieved as metadata only; they do not bypass SQL validation.

## 8. P6 Scenario Analysis Planner

### Goal

Introduce a scenario-aware planning layer that decomposes real business questions into analysis steps before SQL generation.

### Files

- Create: `agents/analysis_planner.py`
- Modify: `graph/state.py`
- Modify: `graph/workflow.py`
- Modify: `graph/nodes.py`
- Modify: `llm_ops/prompt_registry.py`
- Modify: `llm_ops/structured_output.py`
- Modify: `llm_ops/runtime_provider.py`
- Create: `tests/test_analysis_planner.py`
- Create: `tests/test_provider_backed_analysis_planner.py`

### Planner Output Contract

```json
{
  "success": true,
  "scenario_type": "gmv_decline_diagnosis",
  "analysis_steps": [
    {
      "step_id": "gmv_trend",
      "question": "Compare Cameras GMV over current and previous period.",
      "required_metrics": ["gmv"],
      "required_dimensions": ["category", "time"],
      "candidate_tables": ["orders", "order_items", "products", "categories"]
    }
  ],
  "provider_called": false,
  "fallback_used": false,
  "prompt_id": "",
  "validation_error": "",
  "provider_error": ""
}
```

### Supported Scenario Types

- `quick_metric_lookup`
- `gmv_decline_diagnosis`
- `marketing_roi_review`
- `inventory_risk_analysis`
- `refund_anomaly_analysis`
- `promotion_review`
- `customer_segment_analysis`
- `general_non_template_analysis`

### TDD Steps

- [ ] Write failing deterministic planner tests for each supported scenario type.
- [ ] Write failing tests that provider output cannot include SQL or final claims.
- [ ] Write failing tests that malformed provider output falls back to deterministic plan.
- [ ] Add planner node after SQL planning or before guarded SQL candidate for non-template routes.
- [ ] Ensure planner output is written to trace with `provider_called`, `fallback_used`, and `prompt_id`.
- [ ] Run `python3 -m pytest tests/test_analysis_planner.py tests/test_provider_backed_analysis_planner.py -q`.
- [ ] Run `python3 -m pytest tests/test_workflow.py tests/test_provider_assisted_sql_planning_workflow.py -q`.
- [ ] Run `python3 eval/run_eval.py`.

### Acceptance

- Planner decomposes complex questions but does not execute SQL.
- Provider planner cannot provide SQL, facts, or action payloads.
- Existing P0 workflow remains compatible.
- Non-template questions produce visible planning trace evidence.

## 9. P7 Visualization Intelligence

### Goal

Let users request complex charts using natural language, while validating chart specs and rendering only from real query results.

### Files

- Create: `visualization/__init__.py`
- Create: `visualization/chart_registry.py`
- Create: `visualization/chart_spec.py`
- Create: `visualization/chart_validator.py`
- Create: `visualization/chart_renderer.py`
- Create: `agents/visualization_planner.py`
- Modify: `agents/chart_agent.py`
- Modify: `tools/chart_tool.py` or create `tools/advanced_chart_tool.py`
- Modify: `llm_ops/prompt_registry.py`
- Modify: `llm_ops/structured_output.py`
- Create: `tests/test_visualization_intelligence.py`

### First Supported Chart Types

| Chart Type | Use Case |
|---|---|
| `ranked_bar` | Top products, channels, categories |
| `line` | GMV, order count, conversion trend |
| `grouped_bar` | segment, channel, city, or category comparison |
| `dual_axis_line` | GMV plus refund rate, order count plus AOV |
| `funnel` | session -> add_to_cart -> checkout -> paid |
| `heatmap` | cohort, city x category, product x risk level |
| `scatter` | GMV vs refund rate, sales vs negative reviews |
| `risk_matrix` | high value plus high risk quadrants |

### Chart Spec Contract

```json
{
  "chart_type": "dual_axis_line",
  "title": "GMV and refund rate trend",
  "x": "date",
  "y": "gmv",
  "y_secondary": "refund_rate",
  "series": "category_name",
  "required_columns": ["date", "gmv", "refund_rate"],
  "explanation_basis": ["supported_findings"],
  "provider_called": false,
  "fallback_used": false,
  "prompt_id": ""
}
```

### Safety Rules

- Chart spec may only reference columns present in `execution_result`.
- Chart renderer never fabricates data.
- Unsupported chart types return structured fallback.
- LLM can suggest chart specs but cannot bypass spec validation.
- Chart explanation must use Evidence Validator outputs.
- Chart files must be written to configured chart output directories.

### TDD Steps

- [ ] Write failing tests for each first-batch chart type using small synthetic result sets.
- [ ] Write failing tests that invalid chart specs with missing columns are rejected.
- [ ] Write failing tests that unsupported chart types fall back to a safe table or bar chart.
- [ ] Implement chart registry, spec validation, and renderer.
- [ ] Add Visualization Planner with deterministic and provider-backed paths.
- [ ] Integrate Chart Agent with validated chart specs.
- [ ] Run `python3 -m pytest tests/test_visualization_intelligence.py tests/test_chart_agent.py tests/test_chart_tool.py -q`.
- [ ] Run `python3 eval/run_eval.py`.

### Acceptance

- Complex charts render from real execution results.
- Chart specs are inspectable in trace.
- LLM chart planning is optional and structured.
- Existing simple chart behavior remains compatible.

## 10. P8 Agent Pipeline UX

### Goal

Make multi-agent behavior visible to product reviewers, interviewers, and developers without forcing users to read raw trace JSON.

### Files

- Create: `ui/agent_pipeline.py`
- Create: `ui/scenario_view_models.py`
- Create: `ui/visualization_components.py`
- Create: `ui/pages.py`
- Modify: `ui/view_models.py`
- Modify: `ui/components.py`
- Modify: `app.py`
- Create: `tests/test_agent_pipeline_view_model.py`
- Modify: `tests/test_streamlit_app.py`

### New UI Navigation

```text
Ask
Scenarios
Visualize
Reports
Actions
Agent Pipeline
Ops
```

### Agent Pipeline Card Fields

- Agent name
- Business role
- Input summary
- Output summary
- Tool called
- LLM provider status
- `provider_called`
- `fallback_used`
- `prompt_id`
- Safety gate
- Status
- Latency
- Error type

### UI Reduction Rules

- Capability Catalog moves under Ops.
- MCP Tool Layer moves under Ops.
- FastAPI Async API moves under Ops.
- Trace JSON stays collapsed.
- Source & Safety table is replaced or supplemented by Agent Pipeline cards.
- Business users see answer, evidence, charts, and recommendations before technical metadata.

### TDD Steps

- [ ] Write failing tests for `build_agent_pipeline_view_model()`.
- [ ] Write failing tests that pipeline cards preserve provider and fallback metadata.
- [ ] Write failing tests that safety gates are attached to SQL Review, Evidence, Approval, Audit, and Trace steps.
- [ ] Split app rendering into UI page helpers without changing existing workflow helpers.
- [ ] Run `python3 -m pytest tests/test_agent_pipeline_view_model.py tests/test_streamlit_app.py -q`.
- [ ] Run `python3 eval/run_eval.py`.

### Acceptance

- A reviewer can identify each Agent's role from the UI.
- LLM participation is visible per Agent.
- Tool calling is visible per Agent.
- Raw JSON is available but no longer the primary explanation surface.

## 11. P8.5 Structural Slimming And UI Consolidation

### Goal

Make the application lighter by turning old demo pages and oversized files into focused product pages, Ops-only technical surfaces, and small UI/data modules.

This is a required phase, not an optional cleanup pass.

### Files

- Modify: `app.py`
- Modify: `ui/pages.py`
- Modify: `ui/components.py`
- Modify: `ui/agent_pipeline.py`
- Modify: `ui/visualization_components.py`
- Modify: `ui/view_models.py`
- Modify: `data/seed_data.py`
- Modify: `data/seed_realistic_scenarios.py`
- Modify: `agents/report_supervisor.py` if P9 report templates have already made it larger.
- Create: `tests/test_ui_structure_slimming.py`
- Create: `tests/test_project_structure_guardrails.py`
- Modify: `tests/test_streamlit_app.py`

### Required Structure Changes

| Area | Required Change | Must Keep |
|---|---|---|
| Primary navigation | Keep `Ask`, `Scenarios`, `Visualize`, `Reports`, `Actions`, `Agent Pipeline`, `Ops` | Existing workflow helpers remain callable |
| Capability Catalog | Move under `Ops` | P0/P1/P2/P3 coverage remains visible |
| MCP Tool Layer | Move under `Ops` | MCP contract summary remains visible |
| FastAPI Async API | Move under `Ops` | Async run API summary remains visible |
| Trace Dashboard | Move detailed metrics under `Ops`; show trace timeline in Agent Pipeline | Trace count, event count, SQL fix count, eval pass rate remain visible |
| Raw trace JSON | Collapse under debug expanders | Timeline and node details remain visible |
| `app.py` | Reduce to bootstrap, shared helpers, and page dispatch | `run_demo_question()`, `run_report_generation_demo()`, `run_weekly_review_demo()`, `run_action_workflow_demo()` remain |
| `data/seed_data.py` | Keep base seed entrypoint; move scenario inserts out | Existing P0 database remains reproducible |
| `agents/report_supervisor.py` | Extract scenario section templates when report polish expands them | Report supervisor still owns report orchestration |

### Explicit Non-Deletes

- Do not delete `graph/workflow.py`.
- Do not delete `graph/state.py`.
- Do not delete Agent modules that participate in SQL, evidence, report, or action workflows.
- Do not delete Tool modules that enforce validation, execution, approval, audit, or trace behavior.
- Do not delete `llm_ops/` provider and PromptOps code.
- Do not delete `api/` or `mcp_servers/`; move their Streamlit display into Ops only.
- Do not delete P0 eval files.

### TDD Steps

- [ ] Write failing tests in `tests/test_ui_structure_slimming.py` asserting the primary navigation model contains only `Ask`, `Scenarios`, `Visualize`, `Reports`, `Actions`, `Agent Pipeline`, and `Ops`.
- [ ] Write failing tests asserting Capability Catalog, MCP Tool Layer, FastAPI Async API, and full Trace Dashboard are grouped under Ops.
- [ ] Write failing tests asserting raw trace JSON is rendered through collapsed debug sections rather than as the default trace surface.
- [ ] Write failing tests asserting `app.py` still exposes `run_demo_question()`, `run_report_generation_demo()`, `run_weekly_review_demo()`, `run_action_workflow_demo()`, `build_mcp_contract_summary()`, `build_async_run_api_summary()`, and `build_trace_dashboard_summary()`.
- [ ] Write failing tests in `tests/test_project_structure_guardrails.py` asserting `app.py` imports `ui.pages` for page rendering and does not import SQL execution tools directly.
- [ ] Write failing tests asserting no new Streamlit top-level page names exist outside `Ask`, `Scenarios`, `Visualize`, `Reports`, `Actions`, `Agent Pipeline`, and `Ops`.
- [ ] Write failing tests asserting `data/seed_data.py` imports scenario seed helpers instead of containing scenario table insert blocks directly.
- [ ] Move page rendering code from `app.py` into `ui/pages.py` while preserving current helper signatures.
- [ ] Move Agent Pipeline rendering code into `ui/agent_pipeline.py`.
- [ ] Move visualization rendering code into `ui/visualization_components.py`.
- [ ] Move realistic scenario seed inserts into `data/seed_realistic_scenarios.py`; keep `data/seed_data.py` as the base seed entrypoint.
- [ ] Extract report section templates from `agents/report_supervisor.py` only if scenario report polish has added new template sections by this point.
- [ ] Run `python3 -m pytest tests/test_ui_structure_slimming.py tests/test_project_structure_guardrails.py tests/test_streamlit_app.py -q`.
- [ ] Run `python3 -m pytest`.
- [ ] Run `python3 eval/run_eval.py`.

### Acceptance

- The default Streamlit experience no longer feels like a collection of technical demos.
- Business workflow pages appear before Ops surfaces.
- Capability Catalog, MCP, FastAPI, Trace Dashboard, Audit, LLM Ops, and Eval remain available under Ops.
- Raw trace JSON is no longer the first explanation of Agent behavior.
- `app.py` is smaller and page rendering has clear ownership in `ui/pages.py`.
- Base seed data and scenario seed data have separate ownership.
- Project structure guardrail tests pass and prevent accidental growth back into old demo structure.
- No Agent/Tool/Graph safety boundary is removed or weakened.

## 12. P9 Realistic Eval And Demo Polish

### Goal

Add a scenario eval suite that proves the platform can handle realistic questions while preserving P0 regression guarantees.

### Files

- Create: `eval/realistic_scenarios.json`
- Create: `eval/run_realistic_eval.py`
- Modify: `dashboard/trace_dashboard.py` if scenario eval metrics need dashboard display.
- Modify: `README.md`
- Modify: `DEVELOPMENT_STATUS.md`
- Modify: `DEVELOPMENT_PLAN.md`
- Create: `tests/test_realistic_eval_runner.py`

### Scenario Eval Categories

- `gmv_decline_diagnosis`
- `marketing_roi_review`
- `inventory_risk_analysis`
- `refund_anomaly_analysis`
- `promotion_review`
- `visualization_request`
- `approval_gated_action`
- `unsafe_or_sensitive_request`

### Eval Assertions

- Workflow status.
- Required trace nodes.
- SQL review approved or rejected.
- Execution success.
- Evidence Validator present.
- Chart generated when expected.
- Provider metadata present when provider switch is enabled.
- No provider path bypasses validation.
- Action workflow waits for approval unless explicitly approved.

### TDD Steps

- [ ] Write failing tests for loading scenario eval cases.
- [ ] Write failing tests for summarizing scenario eval metrics.
- [ ] Add 15 scenario cases first, then expand to 30 after stable behavior.
- [ ] Run scenario eval with deterministic baseline.
- [ ] Add optional live provider command documented but skipped by default.
- [ ] Run `python3 -m pytest tests/test_realistic_eval_runner.py -q`.
- [ ] Run `python3 eval/run_realistic_eval.py`.
- [ ] Run `python3 eval/run_eval.py`.

### Acceptance

- P0 eval remains separate and remains passing.
- Realistic scenario eval shows Agent, semantic, chart, evidence, and action coverage.
- Live provider eval remains explicit opt-in.
- Eval report is readable enough for resume and demo review.

## 13. P10 Lightweight Engineering Hardening

### Goal

Make the project easier to run, test, review, and maintain without turning it into a heavy production platform.

This phase is intentionally lightweight. It should improve local developer experience and quality gates, but it should not add Docker, CI, RBAC, deployment automation, external data connectors, or production observability platforms.

### Files

- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `engineering/local_quality.md`
- Create: `tests/test_engineering_contracts.py`
- Modify: `README.md`
- Modify: `DEVELOPMENT_STATUS.md`
- Modify: `DEVELOPMENT_PLAN.md`
- Modify: `.gitignore` only if generated artifacts are currently missing from ignore rules.
- Modify: `requirements.txt` only if a lightweight local quality dependency is added.

### Required Engineering Scope

| Area | Required Change | Must Avoid |
|---|---|---|
| Test configuration | Centralize pytest markers for live provider tests, slow tests, and eval-related tests | Accidental live API calls during default test runs |
| Local quality command | Add one command that runs seed, focused engineering tests, full pytest, and P0 eval | Complex shell scripts with hidden state |
| Artifact hygiene | Assert generated databases, reports, charts, traces, and local env files are either ignored or represented by `.gitkeep` | Committing `.env`, API keys, generated DBs, generated reports, or trace dumps |
| Documentation consistency | Keep README quickstart, eval commands, Streamlit command, and provider opt-in instructions aligned with actual files | Duplicated stale setup instructions |
| Runtime safety checks | Verify no-key deterministic baseline remains the default | Provider-required local startup |
| Structure checks | Reuse P8.5 guardrails for app/UI/data ownership | Heavy packaging or deployment work |

### TDD Steps

- [ ] Write failing tests in `tests/test_engineering_contracts.py` asserting `.env.example`, `requirements.txt`, `README.md`, `DEVELOPMENT_PLAN.md`, and `DEVELOPMENT_STATUS.md` exist.
- [ ] Write failing tests asserting `.env`, `data/ecommerce.db`, `data/action_ops.db`, `eval/report.md`, `reports/charts/*`, `reports/markdown/*`, and `logs/traces/*` are ignored or represented by committed `.gitkeep` sentinel files.
- [ ] Write failing tests asserting `README.md` documents `python data/seed_data.py`, `streamlit run app.py`, `python3 -m pytest`, and `python3 eval/run_eval.py`.
- [ ] Write failing tests asserting live-provider tests are opt-in through explicit environment switches and are not part of the default deterministic quality gate.
- [ ] Add `pyproject.toml` with pytest marker configuration for `live`, `eval`, and `slow`.
- [ ] Add a small `Makefile` with `seed`, `test`, `eval`, and `quality` targets.
- [ ] Add `engineering/local_quality.md` documenting the exact local verification flow.
- [ ] Update `README.md` so the quickstart and quality commands match the Makefile.
- [ ] Run `python3 -m pytest tests/test_engineering_contracts.py -q`.
- [ ] Run `make quality`.
- [ ] Run `python3 -m pytest`.
- [ ] Run `python3 eval/run_eval.py`.

### Acceptance

- A new developer can run one documented local command to verify the project.
- Default tests do not require API keys.
- Live DeepSeek tests remain explicit opt-in.
- Generated artifacts are not accidentally committed.
- README setup commands match actual repo files.
- Engineering additions stay lightweight: no Docker, no CI, no deployment config, no user account system, no production queueing.
- The project remains demo-ready and resume-reviewable from a fresh clone.

## 14. Phase Dependency Order

```text
P4 Realistic Scenario Dataset
-> P5 Lightweight Semantic Layer
-> P6 Scenario Analysis Planner
-> P7 Visualization Intelligence
-> P8 Agent Pipeline UX
-> P8.5 Structural Slimming And UI Consolidation
-> P9 Realistic Eval And Demo Polish
-> P10 Lightweight Engineering Hardening
```

P8 can start after P6 if the UI needs to improve before visualization is complete. P7 should not start before P4 because complex charts need richer data. P8.5 must happen before P9 so the final demo polish happens on the lightweight product structure rather than the old demo surface. P10 should happen after the product shape is stable enough that local quality commands and docs will not churn heavily.

## 15. Non-Negotiable Safety Boundaries

- LLM must not execute SQL.
- LLM must not bypass `validate_sql()`.
- LLM must not bypass SQL Reviewer.
- LLM must not bypass Evidence Validator.
- LLM must not bypass Approval Gate.
- LLM must not write audit or trace decisions.
- LLM-generated chart specs must pass chart spec validation.
- LLM-generated SQL candidates must pass `validate_sql()` and SQL Reviewer.
- LLM-generated report text must use Evidence Validator outputs.
- LLM-generated action drafts must flow through Risk Assessor, Approval Gate, Action Executor, and Audit Logger.
- Deterministic no-key baseline must remain available.
- P0 eval must remain passing after every phase.

## 16. What To Delete Or Avoid As Work Proceeds

### Required Moves During P8.5

- Move old top-level technical pages into Ops.
- Move Capability Catalog behind Ops.
- Move MCP Tool Layer and FastAPI Async API displays behind Ops.
- Move raw trace JSON into collapsed debug expanders.
- Extract Streamlit page rendering out of `app.py`.
- Extract realistic scenario seed inserts out of `data/seed_data.py`.
- Extract report section templates from `agents/report_supervisor.py` if scenario report polish has expanded template code.

### Avoid Adding

- New external SaaS integrations.
- User account systems.
- Complex permission models.
- Production queueing.
- Background scheduler.
- Vector database.
- Full dashboard builder.
- Heavy CI/CD or deployment automation before the lightweight local quality gate exists.
- Docker setup before realistic scenarios and local quality commands are stable.
- More template SQL without scenario eval coverage.
- More LLM prompts that are not wired into runtime and trace.

## 17. Resume And Demo Outcomes

After this plan, the project should demonstrate:

- A realistic business question that cannot be solved by simple templates.
- Agent planning that decomposes the analysis.
- Semantic metric and join-path retrieval.
- Optional LLM SQL candidate generation.
- SQL validation and review before execution.
- Evidence-backed findings.
- Advanced chart generation from validated data.
- Report generation grounded in evidence.
- Approval-gated action drafting.
- Trace and audit visibility.
- Agent Pipeline UI that makes multi-agent collaboration obvious.

Good demo script:

1. Ask: "为什么 Cameras 最近 GMV 下滑？"
2. Show scenario plan: GMV trend, traffic conversion, stockout, refund rate, review sentiment.
3. Show SQL candidates and accepted SQL.
4. Show Evidence Validator separating supported findings and hypotheses.
5. Show charts: dual-axis GMV/refund trend, funnel, inventory risk matrix.
6. Show report summary.
7. Show action recommendation requiring approval.
8. Show Agent Pipeline with LLM participation and safety gates.

## 18. Verification Standard For Every Phase

Each phase must run:

```bash
python3 -m pytest <focused tests>
python3 -m pytest
python3 eval/run_eval.py
```

After P8.5 exists, each phase must also run:

```bash
python3 -m pytest tests/test_project_structure_guardrails.py tests/test_ui_structure_slimming.py -q
```

After P9 exists, each phase that touches scenario behavior must also run:

```bash
python3 eval/run_realistic_eval.py
```

After P10 exists, every phase must also run:

```bash
make quality
```

Live DeepSeek tests stay opt-in and require explicit user approval before sending demo schema, prompts, or data summaries to an external API.

## 19. First Implementation Slice

Start with P4 only.

Recommended first slice:

- Create realistic scenario tables.
- Seed fixed anomalies.
- Add tests proving those anomalies are queryable.
- Update table docs and metrics.
- Keep all workflow code unchanged.

This first slice improves demo realism without changing Agent behavior. It is the safest foundation for later LLM and visualization work.
