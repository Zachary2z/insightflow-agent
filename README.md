# InsightFlow Agent

InsightFlow Agent is a LangGraph-based multi-agent tool-calling BI workflow for BI-style SQL analysis.

P0, P1, P2, P3, P4, P5, P6, P7, P8.1, P8.2, P8.3, P8.4, and P8.5 are complete. The current system can take a Chinese business question, route it through a LangGraph multi-agent SQL workflow, validate and execute SELECT SQL against a SQLite ecommerce database, repair one execution error, draft insights from real query output, save trace artifacts, run a 20-case eval benchmark, retrieve P1 business context, classify evidence-backed versus unsupported claims, save traceable Markdown analysis reports, generate weekly and monthly business review reports from explicit/provider-selected report sections, create provider-backed approval-gated action plans, expose selected tool capabilities through a P3 MCP-style tool contract layer, submit workflow runs through a FastAPI async run API, summarize trace/eval/action observability metrics for a dashboard data layer, provide a controlled no-key LLM Provider and PromptOps core, expose an opt-in production DeepSeek provider adapter with strict structured-output validation, classify user questions into structured intent, optionally use validated provider-backed question-understanding, clarification, SQL-planning, guarded SQL-candidate, business-review decomposition, insight-drafting, evidence-backed report-writing, guarded insight claim-typing, action/email-drafting, and visualization-agent paths, mine validated `llm_candidate` trace patterns for future template recommendations, seed realistic ecommerce scenario tables, retrieve semantic metrics/dimensions/entities/join paths, decompose realistic business questions into scenario analysis steps, choose validated visualization specs and delivery tools from real execution results, export real rows to XLSX, mock external Power BI and Jira-style publishing without network access, preserve SQL validation before any SQL execution, and expose the cleaned agent/tool/validator/artifact path in Streamlit.

## Current Status

P0 - Agentic SQL Core, P1 - Reliable Analysis & Report Core, P2 - Business Review & Action Workflow, P3 - MCP & Engineering Core, P4 - Realistic Scenario Dataset, P5 - Lightweight Semantic Layer, P6 - Scenario Analysis Planner, P7 - Visualization Intelligence, P8.1 - Visualization Agent Dedupe & External Tool Calling, P8.2 - Intent & SQL Planning Agent Cleanup, P8.3 - Report & Insight Agent Cleanup, P8.4 - Action Agent & Tool Adapter Cleanup, and P8.5 - Agent Pipeline UX are complete. P9 - Realistic Eval And Demo Polish is next.

Implemented:

- SQLite ecommerce database
- Schema, metric, SQL validation, SQL execution, and trace tools
- Supervisor, Schema, Metric, SQL Generator, SQL Reviewer, Error Fix, and Insight agents
- LangGraph workflow with review, execution, one-retry repair, failure, insight, and trace-save paths
- Streamlit glass-box demo
- 20-case eval benchmark
- P1 business context retrieval for business rules, table docs, and historical SQL examples
- P1 evidence validation for data-supported findings, hypotheses, and unsupported claims
- P1/P8 visualization artifacts through the LLM-first `VisualizationAgent`, validated chart specs, local renderer, Excel exporter, and Power BI mock publisher
- P1 Markdown report generation with SQL, execution evidence, charts, and trace links
- P2 deterministic Report Supervisor for weekly business review reports with multiple SQL subtasks, evidence validation, chart paths, trace paths, and saved Markdown output
- P2/P8.3 controlled LLM Report Planner for structured report section selection and clarification questions without LLM-generated SQL or final claims; provider-unavailable states do not auto-select fixed sections in the product path
- P2 optional guarded LLM SQL and insight enhancement with SQL validation, deterministic fallback, and Evidence Validator claim blocking
- P2/P8.4 Action Workflow with provider-backed contextual action plans, risk assessment, approval gate, local SQLite task/alert/email records, mock Jira-style ticket delivery, action verification, and audit logs
- P3 MCP-style Tool Layer with database, report, and action server contracts over existing deterministic tools
- P3 FastAPI async run API with run submission, status polling, trace retrieval, event retrieval, and cancellation status
- P3 Trace Dashboard data layer with node latency, tool call, SQL execution, SQL repair, eval, approval, and audit metrics
- P3 Streamlit unified demo with SQL analysis, report generation, weekly review, action workflow, MCP, async API, and trace dashboard views
- P3/P8.5 Streamlit Command Center UI with Ask & Analyze, Reports, Actions, Observability, LLM Ops, Integrations, Capability Catalog, source metadata, agent pipeline, tool-call cards, validator gates, artifact panel, and glass-box trace timeline
- P3 LLM Provider and PromptOps core with prompt registry, prompt/version metadata, mock provider contract, model cost/latency trace metadata, and LLM smoke eval harness
- P3 production DeepSeek provider adapter with `.env` config loading, opt-in live smoke tests, malformed JSON handling, and strict prompt-specific output validation
- P3 Question Understanding & Clarification Router with deterministic intent slots, missing-slot clarification, sensitive/unsafe rejection, and strategy recommendations before SQL planning
- P3 SQL Planning Router with deterministic template matching, guarded `llm_candidate` policy, clarify/reject preservation, and template-mining feedback summaries
- P3 Provider-backed Question Understanding with optional DeepSeek-compatible intent extraction, prompt-specific schema validation, deterministic fallback, and trace metadata
- P3 Provider-backed Clarification Router with optional DeepSeek clarification questions, deterministic fallback, runtime workflow trace, and SQL-before-clarification blocking only when provider clarification is active
- P3 Provider-assisted SQL Planning and Guarded Candidate Integration with optional DeepSeek-backed SQL source routing, guarded candidate generation, `validate_sql()` approval, deterministic fallback, and runtime workflow trace
- P3/P8.3 LLM Business Review Decomposition with optional DeepSeek-backed report-section planning for weekly/monthly reviews, allowlisted sections only, provider SQL/claim rejection, explicit `provider_unavailable` handling, and report supervisor trace metadata
- P3 Evidence-backed Report Writing and Polishing with optional DeepSeek-backed report prose generated only from Evidence Validator outputs, SQL records, chart paths, and trace paths; unsupported claims are rejected and deterministic fallback is preserved
- P8.3 Provider-backed Insight Drafting with `insight_drafter` structured output in the core workflow; provider candidate claims are passed to claim typing/Evidence Validator, and unsafe provider output falls back to real-row structured claims
- P3 Guarded Insight Claim Typing with optional DeepSeek-backed claim classification before Evidence Validator, runtime workflow/report-supervisor trace, fallback metadata, and Evidence Validator final ownership
- P8.4 LLM Action and Email Planning with optional DeepSeek-backed task, alert, email draft, and delivery-tool selection before deterministic Risk Assessor, Approval Gate, Action Executor, adapters, and Audit Logger
- P3 LLM Template Mining and Eval Suite with workflow-trace mining for repeated successful `llm_candidate` patterns, schema-aware LLM smoke evals, expected malformed/schema failure cases, and opt-in live DeepSeek eval coverage
- P4 realistic ecommerce scenario dataset with campaign, traffic, inventory, refund, review, promotion, pricing, and fulfillment tables
- P5 lightweight semantic layer for metrics, dimensions, entities, join paths, semantic retrieval, metric-tool compatibility, and context semantic attachment
- P6 Scenario Analysis Planner with deterministic and provider-backed scenario decomposition into `analysis_steps`, semantic-layer metrics/dimensions/tables, workflow state/trace metadata, and fallback on malformed or unsafe provider output
- P7 Visualization Intelligence with validated chart specs for `ranked_bar`, `line`, `grouped_bar`, `dual_axis_line`, `funnel`, `heatmap`, `scatter`, and `risk_matrix`; renderer fallback for unsupported chart types; provider-backed visualization planning through PromptOps structured output; and workflow trace metadata without bypassing SQL or evidence boundaries
- P8.1 Visualization Agent Dedupe & External Tool Calling with `agents/visualization_agent.py` as the only business visualization entry point; provider-backed structured output chooses both `chart_spec` and `delivery_tool_id`; deterministic code validates chart columns and delivery policy, executes `local_renderer`, `excel_exporter`, or `powerbi_publisher_mock`, records trace metadata, and never fabricates rows
- P8.2 Intent & SQL Planning Agent Cleanup with provider-backed question understanding and SQL planning as the product path; unsafe/sensitive guards run before providers; malformed provider intent/planning output returns explicit `provider_unavailable` states instead of reviving keyword/template routing; provider `llm_candidate` paths skip `sql_generator.py` and go directly to guarded SQL candidates, while provider-selected templates are rendered by matched template id rather than question keywords

P8.1 deleted the old `agents/chart_agent.py`, `agents/visualization_planner.py`, and `tools/chart_tool.py` product paths. Visualization decisions now enter only through `agents/visualization_agent.py`; local rendering, Excel export, and Power BI mock publishing run through `tools/external_visualization_tool.py` plus `visualization_delivery/`. P8.2 moves intent and SQL strategy ownership to provider-backed agents when configured; provider failures no longer fall through to duplicate business keyword routing. P8.3 moves report-section selection and insight drafting to provider-backed paths when configured; provider-unavailable report planning does not auto-select fixed sections, while Streamlit's local weekly demo passes explicit demo sections. P8.4 removes fixed action templates from the product path: `agents/action_planner.py` now routes provider-backed action/delivery decisions through PromptOps structured output, missing providers return `provider_unavailable`, and `agents/action_executor.py` calls `action_delivery/` adapters only after approval. P8.5 makes the cleaned pipeline visible in Streamlit through agent pipeline, tool-call, validator-gate, and artifact panels.

Track current phase, task status, test status, acceptance progress, and remaining engineering backlog in [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md). Track the full phased development plan, LLM enhancement development roadmap, next-task queue, and final LLM participation rules in [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).

## LLM Enhancement Roadmap

The default P0/P1/P2 workflow is deterministic and does not call a real LLM, so an API key is not required for the completed workflow. P3 Task 20 adds no-key provider and PromptOps infrastructure with a mock provider contract. P3 Task 20C adds a production `DeepSeekProvider`, but live DeepSeek calls remain explicitly opt-in through `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1`.

LLM usage should now be the product path for business decisions, bounded by tools, validators, and trace. Completed deterministic features remain historical context or safety boundaries, but conflicting old product paths can be deleted during cleanup:

- **Current retained baseline**: SQL validation, SQL execution, evidence validation, report saving, approval, audit, and trace logging remain deterministic safety/execution boundaries.
- **P2 controlled enhancement**: introduce an optional LLM adapter for report task planning, report section outlining, business-language polishing, and user clarification questions. LLM outputs must be structured and checked before use.
- **P2 guarded SQL enhancement**: allow an LLM to propose SQL candidates only after schema, metric, and business context retrieval. Every candidate must still pass `validate_sql()` before `run_sql()`.
- **P3 question understanding**: Task 20A adds a structured intent and clarification layer that extracts metric, dimension, time range, filters, operation, and risk flags before SQL planning.
- **P3 SQL planning router**: Task 20B routes clear questions to deterministic templates, complex but complete questions to guarded LLM SQL candidates, ambiguous questions to clarification, and dangerous or sensitive requests to rejection or safety handling.
- **P3 engineering hardening**: Task 20 adds provider abstraction, prompt templates, prompt/version tracking, cost and latency metadata, LLM eval cases, and trace-ready observability around model-assisted steps.
- **P3 production provider hardening**: Task 20C adds a first-class `DeepSeekProvider`, `.env`-driven config, strict JSON schema validation, optional live smoke tests, and structured fallback/error handling before any production LLM routing depends on real model output.
- **P3 provider-backed question understanding**: Task 21 adds an optional provider-backed path behind the deterministic question-understanding router. Provider output must pass the `question_understanding` structured-output validator, is normalized to the existing intent schema, and falls back deterministically on provider errors, malformed JSON, schema mismatch, or missing provider configuration.
- **P3 provider-backed clarification**: Task 22 added an optional provider-backed clarification router. In the current cleanup direction, provider-backed clarification is the product path when enabled; missing-provider behavior should be structured and should not grow into a duplicate business-rule engine.
- **P3 provider-assisted SQL planning and candidates**: Task 23 wires optional DeepSeek-backed SQL planning and guarded SQL candidate generation into `run_workflow()`. Planning output cannot contain SQL, candidate SQL must pass `validate_sql()`, and the original SQL Reviewer still approves SQL before execution.
- **P8.3 provider-backed business review decomposition cleanup**: Report planning is the product path for section selection when a provider is configured. Provider output can select only allowlisted weekly/monthly report sections and is rejected if it supplies SQL or factual claims. Provider errors, malformed JSON, schema mismatch, unknown sections, or leaked SQL/claim fields return `source: "provider_unavailable"` with no auto-selected fixed sections.
- **P3 evidence-backed report writing**: Task 25 wires optional DeepSeek-backed report prose into `run_report_agent()` and `run_report_supervisor_agent()` after Evidence Validator. Provider prose must pass the `report_writer` schema, reference only verified findings or hypotheses, and is rejected if it includes blocked unsupported claims.
- **P8.3 provider-backed insight drafting and guarded claim typing**: `insight_drafter` can draft candidate claims and concise prose from real execution rows in the core workflow. Candidate claims then flow into `insight_claim_typer` and Evidence Validator; provider classification is advisory, and Evidence Validator still decides supported findings, hypotheses, and blocked unsupported claims.
- **P8.4 action and delivery planning**: `run_action_planner_agent()` is now LLM-first for action suggestions. Provider output can draft task, metric-alert, email-draft payloads, and `delivery_tool_id` values from Evidence Validator outputs; missing providers return structured `provider_unavailable` without fixed action templates. Deterministic code validates delivery policy and only `agents/action_executor.py` can call local SQLite or mock Jira-style adapters after approval.
- **P3 template mining and eval**: Task 28 writes safe template-mining metadata into accepted guarded SQL candidate trace events, mines saved workflow trace files for repeated successful `llm_candidate` intent signatures, and expands `run_llm_smoke_eval()` with prompt-specific structured validation plus expected malformed/schema-failure cases.
- **P3 runtime LLM wiring standard**: Task 21A wires provider-backed question understanding into the real `run_workflow()` path. Future LLM tasks must also connect to a real runtime entry point, write provider/fallback trace evidence, and include live DeepSeek smoke coverage for that path.
- **P7 visualization safety layer**: Completed chart specs, validation, and rendering safety remain as reusable boundaries.
- **P8.1 LLM-first visualization delivery**: `VisualizationAgent` is now the only visualization business entry point. Provider output chooses both a validated chart spec and a registered delivery tool such as local rendering, Excel export, or a Power BI mock publisher. Deterministic code handles chart validation, tool policy validation, adapter execution, artifact hygiene, and trace metadata. Old chart-decision rules and obsolete chart-agent/chart-tool tests were deleted.

LLM boundaries:

- The LLM must not execute SQL, bypass `validate_sql()`, override `Evidence Validator`, create final evidence-backed claims without data support, or trigger action tools without approval gates.
- Reports and insights must remain traceable to SQL, execution results, business context, evidence validation, charts, and saved artifacts.

Final LLM participation map:

| Area | LLM role | Hard boundary |
|---|---|---|
| Provider / PromptOps | DeepSeek adapter, prompt registry, prompt versions, structured output validation, usage/cost/latency trace metadata | Must preserve deterministic safety boundaries and structured provider-unavailable handling |
| Question understanding | Extract metric, dimension, time range, filters, operation, limit, and risk flags | Must not generate or execute SQL |
| Clarification routing | Ask focused follow-up questions for ambiguous requests | Must not guess missing SQL requirements |
| SQL planning | Choose template, guarded `llm_candidate`, clarify, or reject strategy | Must not return executable SQL directly |
| Guarded SQL candidate | Propose SQL candidates for clear non-template questions | Every candidate must pass `validate_sql()` before `run_sql()` |
| Report planning | Select allowlisted report sections and help decompose review tasks | Must not provide SQL or final factual claims |
| Insight/report wording | Suggest claims or polish business-language summaries | Every claim must pass Evidence Validator before use |
| Action drafting | Draft task, alert, or email wording from evidence-backed findings | Must not create actions without Risk Assessor, Approval Gate, Action Executor, and Audit Logger |
| Visualization delivery | Choose chart spec and delivery tool from a validated catalog | Must pass chart validation, tool policy validation, adapter execution boundaries, and no-fabricated-data checks |
| Template mining feedback | Summarize repeated successful `llm_candidate` patterns from saved workflow traces | Must not automatically modify production templates |
| LLM eval / smoke tests | Validate provider availability, JSON shape, prompt schemas, and failure handling | Live provider tests must remain explicit opt-in |

The development plan tracks this as the final LLM participation boundary: LLMs may help with understanding, planning, candidates, wording, and suggestions; deterministic tools remain responsible for approval, execution, validation, and audit.

Runtime LLM development standard:

- Do not stop at standalone provider helpers; each LLM task must be wired into `graph.workflow`, FastAPI, Streamlit helpers, report supervisor, or action workflow.
- Keep provider-unavailable behavior structured; do not preserve duplicate business-rule engines just for no-key mode.
- Record `provider_called`, `fallback_used`, prompt id/version, validation status, and fallback errors in state or trace.
- Add both mocked runtime tests and a live DeepSeek smoke test for the affected workflow path.

Enable provider-backed visualization decisions in the runtime workflow:

```bash
export INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1
export DEEPSEEK_API_KEY=...
python -c "from graph.workflow import run_workflow; print(run_workflow('请画最近 30 天 GMV 趋势图')['visualization_decision'])"
```

The visualization provider can only return a chart spec, delivery tool id, and tool reason. It cannot generate SQL, final claims, action payloads, credentials, secrets, fabricated rows, or fabricated metrics, and every referenced column must exist in the real `execution_result`.

## Question Understanding And SQL Routing

P3 separates natural-language understanding from SQL planning so the system can become smarter without turning into a black-box Text2SQL app.

**Question Understanding & Clarification Router** decides whether a user question is clear enough for SQL planning. It extracts structured slots such as:

- `metric`: GMV, order count, AOV, repurchase rate, or another known metric
- `dimension`: product, category, city, user, channel, or another grouping
- `time_range`: this week, last 30 days, this month, quarter, or a custom period
- `filters`: paid orders, excluding refunds, new users, high-AOV customers, or other constraints
- `operation`: top N, trend, comparison, decline, summary, or drilldown
- `limit`: Top 5, Top 10, or another row limit

If required slots are missing, it returns `strategy: clarify` with focused clarification questions instead of forcing SQL generation. If a request asks for sensitive fields or unsafe operations, it returns `strategy: reject` before SQL generation. Complete stable BI intent returns `strategy: template`; complete but non-template intent returns `strategy: llm_candidate` for a later planning step.

Task 20A does not produce SQL, select a concrete SQL template, expose `matched_template`, or set routing confidence. Those belong to Task 20B.

**SQL Planning Router** decides whether SQL should come from a deterministic template or from the guarded LLM SQL candidate path. Template SQL remains the fast, reliable default for common BI questions. Guarded LLM candidates are used only when the question is clear enough but no existing template covers it. Every LLM candidate must still pass `validate_sql()` before execution.

The intended routing contract is:

```python
{
    "strategy": "template | llm_candidate | clarify | reject",
    "matched_template": "top_products_gmv",
    "confidence": 0.92,
    "missing_slots": [],
    "clarification_questions": [],
    "risk_flags": [],
    "reason": "Question matches a stable Top-N GMV template."
}
```

These tasks belong in P3 because they depend on mature provider, prompt, trace, and eval infrastructure. They should not weaken the current deterministic baseline.

Task 20C hardens real-provider model output with a dedicated `DeepSeekProvider`, prompt-specific JSON schema validation, malformed-output rejection, optional live smoke tests, and traceable provider metadata. Tasks 21-27 reuse that layer for provider-backed question understanding, clarification, SQL planning, guarded SQL candidates, business review decomposition, report writing, claim typing, and action/email drafting without weakening deterministic fallback, `validate_sql()`, SQL Reviewer, Evidence Validator, Approval Gate, Audit Logger, or execution boundaries.

Task 21 provider-backed question understanding can be called explicitly:

```python
from llm_ops.provider import MockLLMProvider
from question_understanding.provider_backed import understand_question_with_provider

provider = MockLLMProvider(
    {
        "strategy": "template",
        "intent": {
            "metric": "gmv",
            "dimension": "category",
            "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近 30 天"},
            "filters": ["paid_orders"],
            "operation": "top_n",
            "limit": 5,
            "risk_flags": [],
        },
        "missing_slots": [],
        "clarification_questions": [],
        "risk_flags": [],
        "reason": "Provider extracted a complete BI intent.",
    }
)

result = understand_question_with_provider("最近 30 天销售额最高的 5 个品类是什么？", provider=provider)
print(result["source"])
print(result["provider_called"])
print(result["fallback_used"])
```

Accepted provider output includes `source: "provider"`, `provider_called: true`, and `fallback_used: false`. After P8.2, provider exceptions, malformed JSON, and schema mismatch return an explicit `source: "provider_unavailable"` response with `provider_called: true`, `fallback_used: true`, and either `provider_error` or `validation_error`; they do not revive keyword-heavy business intent routing.

Task 21A wires provider-backed question understanding into the real runtime workflow. `graph.workflow.run_workflow()` now runs the Question Understanding Agent before schema retrieval, so Streamlit `run_demo_question()` and the FastAPI async run manager inherit the same behavior.

Enable real DeepSeek-backed question understanding in the runtime workflow:

```bash
export INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1
export DEEPSEEK_API_KEY=...
python -c "from graph.workflow import run_workflow; print(run_workflow('最近 30 天销售额最高的 5 个商品是什么？')['question_understanding'])"
```

The runtime switch affects question understanding only. The LLM still does not generate SQL, execute SQL, bypass `validate_sql()`, bypass Evidence Validator, or trigger approval-gated actions. SQL strategy is handled by the separate SQL Planning Agent and, when configured, provider-selected guarded SQL candidates still pass through `validate_sql()` and SQL Reviewer before execution.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python data/seed_data.py
streamlit run app.py
```

Copy `.env.example` to `.env` and fill in values as needed.

## Run Tests

```bash
python -m pytest
```

Run the P0 eval benchmark:

```bash
python eval/run_eval.py
```

## Seed Database

```bash
python data/seed_data.py
```

This creates `data/ecommerce.db` with the P0 ecommerce schema:

- `users`: 120 rows
- `orders`: 540 rows across `paid`, `cancelled`, and `refunded`
- `order_items`: 1,336 rows
- `products`: 36 rows
- `categories`: 6 rows

## What P0 Can Do

- Accept Chinese business questions in Streamlit.
- Read the real SQLite schema with `get_database_schema()`.
- Retrieve metric definitions such as GMV with `retrieve_metric_definition()`.
- Generate SELECT SQL for P0 ecommerce analysis scenarios.
- Review SQL with `validate_sql()` before execution.
- Block dangerous SQL such as `DELETE`, `DROP`, `UPDATE`, and sensitive-field exports before `run_sql()`.
- Execute approved SQL with `run_sql()` and return structured columns, rows, row count, timing, and errors.
- Repair one supported execution failure and rerun the fixed SQL after validation.
- Generate final answers only from `execution_result`.
- Save run traces to `logs/traces/{run_id}.json`.
- Run 20 eval cases with `eval/run_eval.py`.

## P0 Architecture

```text
User question
-> Supervisor Agent
-> Schema Agent -> get_database_schema()
-> Metric Agent -> retrieve_metric_definition()
-> SQL Generator Agent
-> SQL Reviewer Agent -> validate_sql()
-> SQL Executor Tool -> run_sql()
-> Error Fix Agent, when execution fails once
-> SQL Reviewer Agent -> validate_sql(), for fixed SQL
-> SQL Executor Tool -> run_sql(), for fixed SQL
-> Insight Agent
-> Trace Logger
```

The main entry point is `graph.workflow.run_workflow()`. Streamlit calls the same workflow used by eval, so demo behavior and benchmark behavior stay aligned.

## Metric Definitions

Metric definitions live in `data/metrics.yaml` and can be retrieved with `retrieve_metric_definition()`.

P0 metrics:

- `gmv`: sales amount, using `SUM(order_items.quantity * order_items.unit_price)`
- `order_count`: paid order count
- `aov`: average order value
- `category_gmv`: category-level GMV
- `product_sales`: product-level paid item quantity

Example:

```bash
python -c "from tools.metric_tool import retrieve_metric_definition; print(retrieve_metric_definition('最近 30 天销售额最高的 5 个商品是什么？'))"
```

## Business Context Retrieval

Task 11 adds a lightweight Business Context Retrieval layer for P1. It uses Markdown and JSON sources plus keyword matching; it does not require a vector database.

Context sources:

- `data/business_rules.md`: business rules such as paid-order-only GMV and sensitive-field handling
- `data/table_docs.md`: table and field descriptions for the ecommerce schema
- `data/sql_examples.json`: historical SQL examples for common BI questions

Tool interface:

```python
from tools.context_tool import retrieve_business_context

context = retrieve_business_context("最近 30 天销售额最高的 5 个商品是什么？")
print(context["matched_rules"])
print(context["matched_table_docs"])
print(context["matched_sql_examples"])
print(context["trace_event"])
```

Agent interface:

```python
from agents.context_retriever import run_context_retriever_agent
from agents.supervisor import initialize_run

state = initialize_run("最近 30 天销售额最高的 5 个商品是什么？")
state = run_context_retriever_agent(state)
print(state["business_context"]["context_summary"])
print(state["trace"][-1])
```

The tool returns structured JSON-compatible dictionaries and never raises file loading errors into the workflow. On failure it returns `success: false`, empty match lists, an `error`, and a trace-ready event. The Agent only reads `state["user_question"]`, writes `state["business_context"]`, and appends trace; it does not access the database, execute SQL, or generate reports.

## Evidence Validator

Task 12 adds an Evidence Validator layer for P1. It separates claims into:

- `data_supported_findings`: claims backed by `execution_result` rows or explicit business context
- `hypotheses`: claims framed as possible explanations or requiring more data
- `unsupported_claims_blocked`: deterministic claims without supporting evidence

Tool interface:

```python
from tools.evidence_tool import validate_evidence

result = validate_evidence(
    claims=[
        "Laptop Pro 14 的 GMV 为 511248.56",
        "可能与广告流量下降有关，需要 ad_impressions、ctr 和 conversion_rate 数据进一步验证",
        "库存不足是导致 Camera A 销量下降的主要原因",
    ],
    execution_result={
        "success": True,
        "columns": ["product_name", "gmv"],
        "rows": [["Laptop Pro 14", 511248.56]],
        "row_count": 1,
    },
)
print(result["data_supported_findings"])
print(result["hypotheses"])
print(result["unsupported_claims_blocked"])
```

Agent interface:

```python
from agents.evidence_validator import run_evidence_validator_agent

state["claims_to_validate"] = ["Laptop Pro 14 的 GMV 为 511248.56"]
state = run_evidence_validator_agent(state)
print(state["evidence_result"])
print(state["trace"][-1])
```

The Agent writes `state["evidence_result"]` and appends trace. It does not run SQL, generate charts, or save reports.

## Visualization Agent

P8.1 makes `agents/visualization_agent.py` the only business visualization entry point. It receives the user question, `analysis_steps`, `execution_result`, and `evidence_result`, then asks the provider for structured output containing:

- `chart_spec`
- `delivery_tool_id`
- `tool_reason`

Provider output is rejected if it contains SQL, final claims, action payloads, credentials, secrets, fabricated rows, fabricated metrics, unknown chart types, unknown delivery tools, or columns not present in the real `execution_result`. Rejected or unavailable provider output falls back to a minimal local-renderer decision based only on mechanical column availability.

Delivery tools:

- `local_renderer`: delegates to `visualization/chart_renderer.py` and renders only real execution rows.
- `excel_exporter`: writes a local `.xlsx` workbook containing only `execution_result.columns` and `execution_result.rows`.
- `powerbi_publisher_mock`: simulates external BI publishing without OAuth, API keys, network access, or real Power BI calls, returning `mock://powerbi/{run_id}/{artifact_name}`.

External visualization tool:

```python
from tools.external_visualization_tool import call_external_visualization_tool

result = call_external_visualization_tool(
    delivery_tool_id="local_renderer",
    execution_result={
        "success": True,
        "columns": ["product_name", "gmv"],
        "rows": [["Laptop Pro 14", 511248.56], ["Camera A", 456050.99]],
        "row_count": 2,
    },
    chart_spec={
        "chart_type": "ranked_bar",
        "x": "product_name",
        "y": "gmv",
        "title": "Top Products by GMV",
        "run_id": "run_001",
    },
    run_id="run_001",
)
print(result["artifact_path"])
print(result["trace_event"])
```

MCP still exposes a `generate_chart` tool name for compatibility, but internally it calls `tools/external_visualization_tool.py` with `delivery_tool_id="local_renderer"`. There is no legacy `tools/chart_tool.py` business or rendering entry point.

## Report Agent

Task 14 adds Markdown report generation for P1. The Report Agent composes already-available state into a traceable analysis report and calls `save_report()` to write `reports/markdown/{run_id}_report.md`.

Report sections:

- 用户问题
- 使用的业务指标
- 业务上下文
- 执行 SQL
- 查询结果摘要
- 数据支持结论
- 需要进一步验证的假设
- 图表路径
- 下一步建议
- Trace 路径

Tool interface:

```python
from tools.report_tool import save_report

result = save_report(
    run_id="run_001",
    report_content="# InsightFlow Analysis Report\n\nTrace path: logs/traces/run_001.json",
)
print(result["report_path"])
print(result["trace_event"])
```

Agent interface:

```python
from agents.report_agent import run_report_agent

state = run_report_agent(state)
print(state["report_path"])
print(state["trace"][-1])
```

The Agent writes `state["report_result"]` and `state["report_path"]`, and appends trace. It does not run SQL, generate charts, or include blocked unsupported claims as deterministic report findings.

## Evidence-backed Report Writing

Task 25 adds an optional provider-backed report writer after Evidence Validator. The provider can polish business prose for both `run_report_agent()` and `run_report_supervisor_agent()`, but it only receives verified findings, verified hypotheses, blocked unsupported claims, SQL records, chart paths, and trace path. It cannot generate SQL, execute SQL, or turn unsupported claims into final report prose.

Enable real DeepSeek-backed report writing:

```bash
export INSIGHTFLOW_USE_PROVIDER_REPORT_WRITER=1
export INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER=1
export DEEPSEEK_API_KEY=...
python -c "from agents.report_supervisor import run_report_supervisor_agent; from agents.supervisor import initialize_run; s=initialize_run('帮我生成本月电商经营复盘，重点看 GMV 和 Top 商品。'); s['db_path']='data/ecommerce.db'; r=run_report_supervisor_agent(s); print(r['report_writer_result']); print(r['weekly_report_path'])"
```

Accepted provider output includes `source: "provider"`, `provider_called: true`, `fallback_used: false`, prompt id/version, model, usage, and latency metadata. Provider errors, malformed JSON, schema mismatch, unverified claim references, or any blocked unsupported claim text fall back to deterministic report wording. Saved Markdown reports include an `LLM 辅助报告表达` section only after provider output passes structured validation.

Live DeepSeek workflow smoke:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_REPORT_WRITER=1 python3 -m pytest tests/test_deepseek_report_writer_live.py -q
```

## Provider-backed Insight Drafting and Claim Typing

P8.3 adds provider-backed insight drafting before claim typing. The `insight_drafter` provider can return candidate claims and concise prose from the real `execution_result`, but it cannot return SQL, final claims, action payloads, credentials, or fabricated data. Unsafe or malformed provider output returns a structured `source: "provider_unavailable"` fallback built mechanically from real execution rows. The fallback still writes `claims_to_validate`, so Evidence Validator remains the factual boundary.

Task 26 adds optional provider-backed claim typing before Evidence Validator. The provider can classify candidate claims as `data_supported_finding`, `hypothesis`, or `unsupported`, but that classification is advisory: `validate_evidence()` still produces the final supported/hypothesis/blocked split.

Enable real DeepSeek-backed insight drafting and claim typing in the core workflow:

```bash
export INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING=1
export INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING=1
export DEEPSEEK_API_KEY=...
python -c "from graph.workflow import run_workflow; r=run_workflow('最近 30 天销售额最高的 5 个商品是什么？'); print(r['insight']); print(r['claim_typing_result'])"
```

The same provider can be passed to `run_report_supervisor_agent(..., claim_typing_provider=provider)` or enabled through the runtime switch for report sections. Provider output must pass the `insight_claim_typer` schema and cannot generate SQL, execute SQL, bypass Evidence Validator, or create final claims without data.

Live DeepSeek workflow smoke:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING=1 python3 -m pytest tests/test_deepseek_claim_typing_workflow_live.py -q
```

## Business Review Report

Task 15 adds a deterministic P2 Report Supervisor for weekly business review reports. It decomposes a weekly report request into structured sections, then runs each SQL subtask through the existing schema, metric, SQL review, SQL execution, Evidence Validator, Chart Agent, Report Tool, and Trace Logger boundaries.

Core sections:

- 本周 GMV
- 本周订单量
- 本周客单价
- Top 商品
- Top 品类
- 销售下降品类
- 下周建议

Agent interface:

```python
from agents.report_supervisor import run_report_supervisor_agent
from agents.supervisor import initialize_run

state = initialize_run("帮我生成一份本周电商经营分析周报，包括销售额、订单量、Top 商品、下降品类和运营建议。")
state["db_path"] = "data/ecommerce.db"
state["trace_dir"] = "logs/traces"
state = run_report_supervisor_agent(state)

print(state["weekly_report_path"])
print(state["trace_path"])
print(state["report_sub_tasks"][0]["review_result"])
print(state["report_sub_tasks"][0]["execution_result"])
```

The supervisor writes:

- `report_type`: `weekly_business_report`
- `report_sections`: planned weekly report sections
- `report_sub_tasks`: per-section SQL, `review_result`, `execution_result`, evidence result, chart paths, status, and error
- `weekly_report_path`: `reports/markdown/{run_id}_weekly_business_report.md`
- `trace_path`: `logs/traces/{run_id}.json`

Failed subtasks are recorded with `status: failed` and their structured review/execution error, but they do not crash the whole weekly report workflow. Evidence Validator remains responsible for separating data-supported findings, hypotheses, and unsupported claims. Task 15 does not introduce LLM planning, guarded LLM SQL generation, action tools, approval gates, MCP, FastAPI, or dashboard behavior.

## Controlled LLM Report Planner

Task 15A adds an optional controlled planning layer for weekly business reports. The planner can call a supplied `llm_provider` to select report section IDs and ask clarification questions, but it cannot supply SQL, execute SQL, produce final claims, or bypass deterministic report templates.

Safety contract:

- Provider input includes `allowed_section_ids`, `must_not_generate_sql`, `must_not_execute_sql`, and `must_not_generate_final_claims`.
- Provider output is accepted only when section IDs match existing deterministic templates.
- Unknown sections and provider-supplied SQL are ignored.
- Missing, malformed, or unusable provider responses fall back to deterministic Task 15 sections.
- Clarification responses set `status: report_plan_needs_clarification` and return questions without running report SQL.

Agent interface:

```python
from agents.report_planner import run_report_planner_agent
from agents.supervisor import initialize_run

state = initialize_run("帮我生成一份本周电商经营分析周报，优先看 GMV 和 Top 商品。")

state = run_report_planner_agent(
    state,
    llm_provider=lambda prompt: {
        "report_type": "weekly_business_report",
        "sections": [{"section_id": "weekly_gmv"}, {"section_id": "top_products"}],
    },
)

print(state["report_plan"])
print([section["section_id"] for section in state["report_sections"]])
```

Report Supervisor integration:

```python
from agents.report_supervisor import run_report_supervisor_agent
from agents.supervisor import initialize_run

state = initialize_run("帮我生成一份本周电商经营分析周报，优先看 GMV 和 Top 商品。")
state["db_path"] = "data/ecommerce.db"

state = run_report_supervisor_agent(
    state,
    llm_provider=lambda prompt: {
        "report_type": "weekly_business_report",
        "sections": [{"section_id": "weekly_gmv"}, {"section_id": "top_products"}],
    },
)
print(state["weekly_report_path"])
```

Without a configured report-planning provider, `run_report_planner_agent()` returns a structured `source: "provider_unavailable"` plan with no selected sections. This prevents the fixed weekly/monthly section catalog from becoming a parallel product-path planner. Local demos and tests that need a no-key weekly review pass explicit `report_sections` as a fixture.

Task 24 wires the PromptOps-backed `report_planner` path into the real Report Supervisor runtime. When enabled, DeepSeek can help choose the weekly or monthly review sections before the supervisor runs the existing SQL review, SQL execution, Evidence Validator, chart, report, and trace steps.

Enable real DeepSeek-backed business review decomposition:

```bash
export INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER=1
export DEEPSEEK_API_KEY=...
python -c "from agents.report_supervisor import run_report_supervisor_agent; from agents.supervisor import initialize_run; s=initialize_run('帮我生成一份本月电商经营分析月报，重点看 GMV、Top 商品和下月建议。'); s['db_path']='data/ecommerce.db'; print(run_report_supervisor_agent(s)['report_plan'])"
```

The accepted provider plan includes `source: "provider"`, `provider_called: true`, and `fallback_used: false`. Provider exceptions, malformed JSON, schema mismatch, unknown sections, or leaked fields such as `sql`, `generated_sql`, `claims`, or `final_claims` return `source: "provider_unavailable"` with validation/error metadata in `report_plan` and trace. The provider can choose allowlisted sections for weekly or monthly reports, but the supervisor still uses deterministic section SQL definitions from the local catalog and never executes provider-supplied SQL.

Live DeepSeek workflow smoke:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER=1 python3 -m pytest tests/test_deepseek_business_review_planner_live.py -q
```

## Guarded LLM SQL and Insight Enhancement

Task 15B adds optional guarded enhancement agents. These agents accept supplied provider callables for tests or future adapters, but the deterministic baseline still needs no API key and does not call an LLM.

Guarded SQL candidate rules:

- The provider sees `schema_text`, `metric_context`, `business_context`, and current deterministic SQL.
- Provider output can include SQL candidates, but every candidate is checked with `validate_sql()`.
- Only the first approved SELECT candidate can replace `generated_sql`.
- Rejected, unsafe, malformed, or missing candidates leave deterministic SQL unchanged.
- This agent never calls `run_sql()`.

```python
from agents.guarded_llm_enhancer import run_guarded_sql_candidate_agent

state = run_guarded_sql_candidate_agent(
    state,
    llm_provider=lambda prompt: {
        "sql_candidates": [
            {
                "sql": "SELECT COUNT(*) AS order_count FROM orders WHERE status = 'paid' LIMIT 100",
                "rationale": "Safe paid-order count candidate.",
            }
        ]
    },
)
print(state["llm_sql_enhancement"])
print(state["generated_sql"])
```

Guarded insight enhancement rules:

- Provider output is treated as claims, not trusted final prose.
- Claims are checked with `validate_evidence()` against execution results and context.
- `guarded_summary` contains only data-supported findings and hypotheses.
- Unsupported deterministic claims are recorded in `unsupported_claims_blocked` and excluded from the guarded summary.

```python
from agents.guarded_llm_enhancer import run_guarded_insight_enhancer_agent

state = run_guarded_insight_enhancer_agent(
    state,
    llm_provider=lambda prompt: {
        "claims": [
            "Laptop Pro 14 的 GMV 为 511248.56",
            "库存不足是导致销量下降的主要原因",
            "可能需要进一步验证广告流量和转化率数据。",
        ]
    },
)
print(state["llm_insight_enhancement"]["guarded_summary"])
print(state["llm_insight_enhancement"]["unsupported_claims_blocked"])
```

Task 15B does not introduce action tools, approvals, MCP, FastAPI, dashboard behavior, provider abstraction, cost tracking, or prompt registry features.

## Action Workflow

Task 16 added a local, auditable action workflow; P8.4 makes action suggestions provider-backed and moves execution into explicit delivery adapters. It does not send real emails, run background jobs, call network SaaS APIs, or bypass approval gates.

Workflow:

```text
Evidence Validator
-> Action Planner
-> Risk Assessor
-> Approval Gate
-> Action Executor
-> Action Delivery Adapter
-> Action Verifier
-> Audit Logger
```

Implemented tools:

- `create_task()` writes tasks to SQLite.
- `create_metric_alert()` writes metric alerts to SQLite.
- `create_email_draft()` writes email drafts to SQLite.
- `record_approval()` writes approval records to SQLite.
- `verify_action_execution()` confirms created local records exist.
- `log_audit_event()` writes approval, execution, and verification audit events.
- `action_delivery/` registers `local_sqlite` and `jira_ticket_mock`; the Jira adapter returns `mock://jira/...` without network or API keys.

Agent interface:

```python
from agents.action_planner import run_action_planner_agent
from agents.action_executor import run_action_executor_agent
from agents.action_verifier import run_action_verifier_agent
from agents.risk_assessor import run_risk_assessor_agent
from tools.approval_tool import record_approval

state = run_action_planner_agent(state)
state = run_risk_assessor_agent(state)

# Approval gate blocks execution until approval_status is approved.
approval = record_approval(
    state["action_db_path"],
    {
        "run_id": state["run_id"],
        "approval_status": "approved",
        "approved_by": "ops_manager",
        "reason": "Approved for operational follow-up.",
    },
)
state["approval_status"] = approval["approval_status"]
state["approval_record"] = approval

state = run_action_executor_agent(state)
state = run_action_verifier_agent(state)
print(state["created_actions"])
print(state["action_verification_result"])
print(state["audit_log_id"])
```

Approval rules:

- `create_task`, `create_metric_alert`, and `create_email_draft` require approval.
- Unapproved actions are blocked and audited.
- Approved local actions create SQLite records, mock external actions return explicit `mock://...` artifact URLs, and local records are verified.
- Audit logs preserve approval blocking, action execution, and action verification events.

Task 16 does not introduce MCP, FastAPI, React, async jobs, RBAC, external SaaS task creation, or real email sending.

## LLM Action and Email Drafting

Task 27 adds an optional provider-backed action drafter inside the real action workflow. `run_action_planner_agent()` still builds the deterministic action plan first, then calls the DeepSeek-compatible `action_drafter` path only when a provider is supplied or `INSIGHTFLOW_USE_PROVIDER_ACTION_DRAFTER=1` is enabled.

Enable real DeepSeek-backed action drafting:

```bash
export INSIGHTFLOW_USE_PROVIDER_ACTION_DRAFTER=1
export DEEPSEEK_API_KEY=...
python3 -c "from agents.supervisor import initialize_run; from agents.action_planner import run_action_planner_agent; s=initialize_run('请基于 Cameras GMV 下滑创建运营跟进任务、监控告警和邮件草稿。'); s['evidence_result']={'success': True, 'data_supported_findings': [{'claim': 'Cameras 的 GMV 变化为 -12000.0'}], 'hypotheses': [{'claim': '可能需要进一步验证广告流量和转化率数据。', 'needs_more_data': ['ad_impressions', 'conversion_rate']}], 'unsupported_claims_blocked': ['库存不足是确定原因']}; print(run_action_planner_agent(s)['action_draft_result'])"
```

Accepted provider output writes `state["action_draft_result"]` with `provider_called`, `fallback_used`, prompt id/version, model, usage, latency, provider errors, and validation errors. Accepted drafts replace only the pending `action_plan.actions` payloads. They do not create tasks, create alerts, create email drafts, set approval status, send email, write audit records, or bypass Risk Assessor, Approval Gate, Action Executor, or Audit Logger.

Live DeepSeek workflow smoke:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_ACTION_DRAFTER=1 python3 -m pytest tests/test_deepseek_action_drafter_live.py -q
```

## MCP Tool Layer

Task 17 adds a lightweight MCP-style contract layer under `mcp_servers/`. It exposes JSON-compatible tool contracts and wrapper functions for selected external-facing capabilities, while keeping internal safety and audit modules inside the system boundary.

Implemented MCP-style servers:

- `database-mcp-server`: `get_database_schema`, `get_sample_rows`, `run_sql`
- `report-mcp-server`: `generate_chart`, `save_report`
- `action-mcp-server`: `create_task`, `create_metric_alert`, `create_email_draft`

Not exposed as MCP tools:

- SQL review internals
- Permission and approval record tools
- Trace logging
- Eval runner

Safety boundaries:

- `mcp_run_sql()` loads schema, retrieves metric context, runs the existing SQL reviewer internally, and only then calls `run_sql()` with reviewed SQL.
- `mcp_save_report()` requires successful evidence validation and rejects reports with blocked unsupported claims.
- `mcp_create_task()`, `mcp_create_metric_alert()`, and `mcp_create_email_draft()` require `approval_status="approved"` before writing operational records.
- MCP wrappers return structured dictionaries with `success`, `mcp_server`, `tool_name`, and either `result` or `error`.
- The layer does not start a network server and does not add FastAPI, async jobs, dashboards, Docker, CI, or provider/prompt infrastructure.

Example:

```python
from mcp_servers.database_server import get_tool_contract, mcp_run_sql

print(get_tool_contract())

result = mcp_run_sql(
    db_path="data/ecommerce.db",
    sql="SELECT COUNT(*) AS order_count FROM orders",
)
print(result["review_result"]["approved"])
print(result["result"]["rows"])
```

## FastAPI Async Run API

Task 18 adds a minimal FastAPI app under `api/` for submitting LangGraph workflow runs without changing the deterministic baseline.

Run locally:

```bash
uvicorn api.app:app --reload
```

Implemented endpoints:

- `POST /api/runs`: enqueue a workflow run and return `run_id`.
- `GET /api/runs/{run_id}`: read run status and summary.
- `GET /api/runs/{run_id}/trace`: read current or completed trace data.
- `GET /api/runs/{run_id}/events`: read run lifecycle events.
- `POST /api/runs/{run_id}/cancel`: mark an active run as cancelled.

Supported statuses:

- `queued`
- `running`
- `waiting_for_approval`
- `completed`
- `failed`
- `cancelled`

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"user_question":"最近 30 天销售额最高的 5 个商品是什么？"}'
```

The API uses an in-memory `RunManager` and a thread pool to execute existing `graph.workflow.run_workflow()` calls. It is intentionally local and lightweight: Task 18 does not add persistent queues, SSE, dashboard views, React, RBAC, Docker, CI, or new LLM/provider behavior.

## Trace Dashboard Data Layer

Task 19 adds `dashboard.trace_dashboard.build_trace_dashboard()` for dashboard-ready observability summaries. It reads trace JSON artifacts, optional eval summaries, and optional action workflow SQLite records, then returns a JSON-compatible dictionary.

Metrics included:

- Agent node latency totals and averages
- Tool call counts
- SQL execution latency totals and averages
- SQL repair count
- Failure type distribution
- Eval totals and pass rate
- Action approval records
- Audit log records
- Structured load errors for bad trace files or unreadable action DBs

Example:

```python
from dashboard.trace_dashboard import build_trace_dashboard
from eval.run_eval import load_cases, run_eval_cases

eval_summary = run_eval_cases(load_cases())
dashboard = build_trace_dashboard(
    trace_dir="logs/traces",
    eval_summary=eval_summary,
    action_db_path="data/action_ops.db",
)

print(dashboard["agent_node_latency_ms"])
print(dashboard["tool_call_counts"])
print(dashboard["eval_metrics"])
```

Task 19 is a data layer only. It does not add React, Streamlit UI changes, SSE, dashboard frontend routing, RBAC, Docker/CI, provider abstraction, PromptOps, or new LLM behavior.

## Streamlit Unified Demo

Task 19A upgrades the Streamlit app from a P0-only glass-box SQL demo into a clear product demo for the backend capabilities that already exist.

Views:

- SQL Analysis: preserve the current P0 workflow view with Agent steps, SQL, SQL review, execution, repair, final answer, and trace.
- Report Generation: expose P1 evidence validation, chart generation, and Markdown report saving.
- Weekly Business Review: expose P2 report supervisor sections, SQL subtasks, evidence, charts, and saved weekly report path.
- Action Workflow: show action planning, risk assessment, approval gate state, created task/alert/email draft records, verification, and audit logs.
- MCP Tool Layer: show database/report/action MCP-style contracts and safe wrapper outputs.
- Async Run API: explain local FastAPI usage and show run status, trace, and event payloads in a demo-friendly way.
- Trace Dashboard: presents `build_trace_dashboard()` summaries such as node latency, tool counts, SQL execution latency, repair count, eval pass rate, approvals, and audit logs.

Task 19A improves clarity without changing core safety boundaries. The UI does not bypass SQL Validator, Evidence Validator, approval gate, MCP contracts, or deterministic workflow behavior. It does not introduce React, RBAC, Docker/CI, persistent queues, provider abstraction, PromptOps, or new LLM behavior.

## LLM Provider And PromptOps Core

Task 20 introduces a controlled `llm_ops` layer for future model-assisted steps. It is infrastructure only: it does not call a real model by default, does not require an API key, and does not change the deterministic workflow baseline.

Implemented pieces:

- `llm_ops.prompt_registry.DEFAULT_PROMPT_REGISTRY` stores versioned prompt templates for `report_planner`, `guarded_sql_candidate`, `guarded_insight_claims`, `report_writer`, `insight_drafter`, `insight_claim_typer`, `action_drafter`, `question_understanding`, `clarification_router`, and `sql_planning_router`.
- `llm_ops.provider.LLMRequest` and `run_llm_request()` define the provider contract and return JSON-compatible results with `success`, `content`, `usage`, `latency_ms`, `error`, and `trace_event`.
- `llm_ops.provider.MockLLMProvider` supports deterministic tests and smoke evals without network calls.
- `llm_ops.eval_smoke.run_llm_smoke_eval()` runs lightweight prompt/provider checks with expected output keys.
- `llm_ops.deepseek_provider.DeepSeekProvider` calls DeepSeek through the existing provider contract when explicitly configured.
- `llm_ops.structured_output.run_validated_llm_request()` validates model output against prompt-specific schemas before agents can consume it.

Example:

```python
from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMRequest, MockLLMProvider, run_llm_request

rendered = DEFAULT_PROMPT_REGISTRY.render(
    "report_planner",
    {
        "user_question": "帮我生成本周经营周报。",
        "allowed_section_ids": ["weekly_gmv", "top_products"],
    },
)

result = run_llm_request(
    MockLLMProvider({"sections": [{"section_id": "weekly_gmv"}]}),
    LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
    ),
)
print(result["trace_event"])
```

Safety boundaries:

- `guarded_sql_candidate` prompts explicitly require `validate_sql()` and never execute SQL.
- `guarded_insight_claims` prompts require Evidence Validator verification before claims can be used.
- The provider layer does not expose approval-gated action tools and does not trigger tasks, alerts, or email drafts. `action_drafter` can only draft payload text before risk assessment and approval.
- Provider failures are returned as `success: false` with structured errors instead of crashing workflows.
- Malformed JSON returns `llm_malformed_json_error`.
- Schema mismatches return `llm_schema_validation_error`; for example, `report_planner.sections` must be an array of objects, not a loose string list.

DeepSeek config:

```env
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=0
```

`DEEPSEEK_MODEL` is intentionally configurable. Use `deepseek-v4-pro` for stronger reasoning and SQL-planning quality, or switch to `deepseek-v4-flash` for cheaper/faster smoke tests. The config loader also normalizes common aliases such as `DeepSeekv4pro`, `v4pro`, and `v4flash`.

Live DeepSeek tests are opt-in:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 python3 -m pytest tests/test_deepseek_live_smoke.py -q
```

The default workflow and full test suite still run without any API key.

## Question Understanding Router

Task 20A adds a deterministic question-understanding layer. It can be used before SQL planning to classify whether a question is complete, ambiguous, or unsafe.

```python
from question_understanding.router import understand_question

result = understand_question("最近 30 天销售额最高的 5 个商品是什么？")
print(result["strategy"])
print(result["intent"])
```

The output is JSON-compatible:

```python
{
    "strategy": "template | llm_candidate | clarify | reject",
    "intent": {
        "metric": "gmv",
        "dimension": "product",
        "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近 30 天"},
        "filters": ["paid_orders"],
        "operation": "top_n",
        "limit": 5,
        "risk_flags": [],
    },
    "missing_slots": [],
    "clarification_questions": [],
    "risk_flags": [],
}
```

Boundaries:

- It does not generate SQL.
- It does not execute SQL.
- It does not choose a concrete SQL template or emit `matched_template`.
- Sensitive-field or unsafe-write requests return `strategy: reject` before SQL planning.

Task 21 adds an optional provider-backed wrapper:

```python
from question_understanding.provider_backed import understand_question_with_provider

result = understand_question_with_provider(question, provider=provider)
```

Provider output is accepted only after the `question_understanding` structured-output schema validates `strategy`, `intent`, `missing_slots`, `clarification_questions`, and `risk_flags`. Accepted output is normalized into the same intent schema as the deterministic router. `provider=None`, provider exceptions, malformed JSON, and schema mismatch all keep the deterministic no-key baseline by falling back to `understand_question(question)`.

Additional boundaries:

- It does not generate SQL.
- It does not execute SQL.
- It does not emit `matched_template`, `confidence`, or selected table fields.
- Sensitive or unsafe provider risk flags force `strategy: reject` and preserve the risk flags.
- Agent trace events include `provider_called` and `fallback_used`.

Task 21A runtime behavior:

- `run_workflow()` always writes `question_understanding`, `intent_slots`, and `routing_strategy` into workflow state.
- With `INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1` and a valid `DEEPSEEK_API_KEY`, the workflow creates a `DeepSeekProvider` and calls the provider-backed path.
- Without the flag or without a key, this historical path uses deterministic question understanding; P8 cleanup should not expand that rule path and may replace it with structured provider-unavailable handling where it conflicts with the LLM-first product path.
- Streamlit demo helpers and FastAPI async runs inherit this through the core workflow.
- A live workflow smoke test is available with:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 \
  python3 -m pytest tests/test_deepseek_question_understanding_workflow_live.py -q
```

Task 22 runtime behavior:

- `run_workflow()` now runs a clarification router after question understanding and before schema retrieval.
- With `INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER=1` and a valid `DEEPSEEK_API_KEY`, ambiguous questions call the DeepSeek-backed clarification prompt and return focused follow-up questions.
- Provider clarification stops before schema retrieval, SQL generation, SQL execution, and SQL planning.
- Without the flag or without a key, this historical path continues through the existing P0 SQL workflow; P8 cleanup should not expand that path into a duplicate product experience.
- Provider output must pass the `clarification_router` structured-output validator before it is used.

Example:

```bash
export INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER=1
export DEEPSEEK_API_KEY=...
python3 -c "from graph.workflow import run_workflow; print(run_workflow('帮我看看销售情况')['clarification_result'])"
```

A live workflow smoke test is available with:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER=1 \
  python3 -m pytest tests/test_deepseek_clarification_workflow_live.py -q
```

## SQL Planning Router

Task 20B adds a SQL source planning layer. It consumes Task 20A output and decides whether the next step should use a deterministic template, a guarded LLM SQL candidate path, clarification, or rejection.

```python
from question_understanding.router import understand_question
from sql_planning.router import plan_sql_strategy

understanding = understand_question("最近 30 天销售额最高的 5 个商品是什么？")
planning = plan_sql_strategy(understanding)
print(planning["strategy"])
print(planning["matched_template"])
```

Example output:

```python
{
    "strategy": "template",
    "matched_template": "top_products_gmv",
    "confidence": 0.94,
    "template_variables": {
        "metric": "gmv",
        "dimension": "product",
        "operation": "top_n",
        "limit": 5,
        "time_range": {"type": "last_n_days", "value": 30, "raw_text": "最近 30 天"},
        "filters": ["paid_orders"],
    },
    "validation_policy": {"must_validate_sql_before_execution": True},
}
```

For complete questions that do not match a deterministic template, the router returns `strategy: llm_candidate` with `candidate_policy.provider_prompt_id = "guarded_sql_candidate"`. The deterministic Task 20B router does not call a provider and does not return SQL. Repeated successful `llm_candidate` patterns can be summarized with `sql_planning.feedback.summarize_template_mining_feedback()` to identify future deterministic template candidates.

## LLM Template Mining and Eval Suite

Task 28 adds workflow-trace mining for accepted guarded SQL candidates. When a guarded candidate is accepted after `validate_sql()`, the trace event stores safe metadata for template mining: strategy, accepted flag, provider flag, candidate count, user question, and structured intent. It does not store provider SQL for template mining, and it never writes or modifies production templates.

Mine recommendations from saved workflow traces:

```python
from sql_planning.feedback import mine_template_candidates_from_trace_files

result = mine_template_candidates_from_trace_files(
    ["logs/traces/run_example.json"],
    min_success_count=3,
)
print(result["candidates"])
```

Candidate recommendations include `intent_signature`, `success_count`, `recommended_template_id`, `sample_questions`, and `auto_apply: false`. A human still has to review the pattern, design the deterministic SQL template, add tests, and run `validate_sql()`/P0 eval before any template becomes production behavior.

Task 28 also expands `llm_ops.eval_smoke.run_llm_smoke_eval()` so smoke cases can opt into prompt-specific structured validation:

```python
from llm_ops.eval_smoke import run_llm_smoke_eval

result = run_llm_smoke_eval(
    [
        {
            "case_id": "question_understanding_schema",
            "prompt_id": "question_understanding",
            "variables": {"user_question": "最近 30 天销售额最高的 5 个商品是什么？"},
            "expected_keys": ["strategy", "intent", "missing_slots", "clarification_questions", "risk_flags"],
            "validate_output": True,
            "expected_success": True,
        }
    ],
    provider=provider,
)
```

Eval cases can also set `expected_success: false` and `expected_error_type` to verify malformed JSON and schema mismatch handling without treating safe rejection as a test failure.

Live DeepSeek eval suite:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 python3 -m pytest tests/test_deepseek_llm_eval_suite_live.py -q
```

Task 23 runtime behavior:

- `run_workflow()` now writes `sql_planning`, `sql_routing_strategy`, and guarded candidate metadata into workflow state.
- With `INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1` and a valid `DEEPSEEK_API_KEY`, the workflow calls the `sql_planning_router` prompt before schema/SQL generation.
- SQL planning provider output is accepted only after structured validation and must not include SQL or SQL candidates.
- With `INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1`, `llm_candidate` routes call the `guarded_sql_candidate` prompt after deterministic SQL generation.
- Candidate SQL is never executed directly. It must first pass `validate_sql()` inside the guarded candidate agent, then pass the existing SQL Reviewer before `run_sql()`.
- Without flags or without an API key, the deterministic baseline continues.

Example:

```bash
export INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1
export INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1
export DEEPSEEK_API_KEY=...
python3 -c "from graph.workflow import run_workflow; r = run_workflow('本月各城市客单价对比'); print(r['sql_planning']); print(r['llm_sql_enhancement'])"
```

A live workflow smoke test is available with:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 \
  python3 -m pytest tests/test_deepseek_sql_planning_workflow_live.py -q
```

Boundaries:

- It does not generate SQL.
- It does not execute SQL.
- Provider-assisted planning can call a real LLM only when explicitly enabled, but planning still cannot return SQL.
- Any later SQL, whether template-generated or LLM-proposed, must still pass `validate_sql()` before `run_sql()`.

## Schema Tool

The schema tool reads SQLite metadata and returns both structured table metadata and prompt-friendly `schema_text`.

```bash
python -c "from tools.schema_tool import get_database_schema; print(get_database_schema('data/ecommerce.db')['schema_text'])"
```

## SQL Validator

The SQL validator checks generated SQL before execution. It only approves safe SELECT statements, blocks dangerous keywords and sensitive fields, validates table/column names against the schema, appends a default `LIMIT 100` when needed, and checks GMV metric rules when metric context is provided.

```python
from tools.metric_tool import retrieve_metric_definition
from tools.schema_tool import get_database_schema
from tools.sql_validator import validate_sql

schema = get_database_schema("data/ecommerce.db")
metric = retrieve_metric_definition("最近 30 天销售额最高的 5 个商品是什么？")
sql = """
SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS sales
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE o.status = 'paid'
GROUP BY p.product_name
ORDER BY sales DESC
LIMIT 5
"""
print(validate_sql(sql, schema, metric))
```

## SQL Executor

The SQL executor runs approved SELECT statements against SQLite and returns structured execution results. It rejects non-SELECT SQL, caps returned rows with `max_rows`, captures database errors, and emits a trace-ready event.

```python
from tools.sql_executor import run_sql

sql = """
SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gmv
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE o.status = 'paid'
GROUP BY p.product_name
ORDER BY gmv DESC
LIMIT 5
"""
print(run_sql("data/ecommerce.db", sql))
```

## Trace Logger

The trace logger records node and tool-call events for each Agent run. `append_trace()` adds normalized events to state without mutating the original state, and `save_trace()` writes structured JSON artifacts to `logs/traces/{run_id}.json`.

Required trace fields:

- `run_id`
- `session_id`
- `node`
- `tool_name`
- `tool_input_summary`
- `tool_output_summary`
- `status`
- `latency_ms`
- `error_type`
- `retry_count`
- `timestamp`

Example:

```python
from tools.trace_logger import append_trace, save_trace

state = {"run_id": "run_001", "session_id": "session_001", "trace": []}
state = append_trace(state, {
    "node": "sql_executor",
    "tool_name": "run_sql",
    "tool_input_summary": "SELECT 1",
    "tool_output_summary": "1 row returned",
    "status": "success",
    "latency_ms": 12,
})
print(save_trace("run_001", state["trace"], session_id="session_001"))
```

## P0 Agents

P0 agents are lightweight state-transforming modules. They return structured dictionaries and keep the Agent/Tool boundary clear: agents orchestrate state and reasoning, while tools perform schema lookup, metric retrieval, SQL validation, SQL execution, and trace persistence.

Implemented modules:

- `agents.supervisor.initialize_run()` initializes run/session state.
- `agents.schema_agent.run_schema_agent()` calls `get_database_schema()`.
- `agents.metric_agent.run_metric_agent()` calls `retrieve_metric_definition()`.
- `agents.sql_generator.run_sql_generator()` generates structured SELECT SQL output.
- `agents.sql_reviewer.run_sql_reviewer()` calls `validate_sql()`.
- `agents.error_fixer.run_error_fix_agent()` repairs one deterministic P0 SQL error class.
- `agents.insight_agent.run_insight_agent()` answers only from `execution_result`.

Example:

```python
from agents.metric_agent import run_metric_agent
from agents.schema_agent import run_schema_agent
from agents.sql_generator import run_sql_generator
from agents.sql_reviewer import run_sql_reviewer
from agents.supervisor import initialize_run

state = initialize_run("最近 30 天销售额最高的 5 个商品是什么？")
state = run_schema_agent(state, "data/ecommerce.db")
state = run_metric_agent(state)
state = run_sql_generator(state)
state = run_sql_reviewer(state)
print(state["sql_generation"])
print(state["review_result"])
```

## LangGraph Workflow

The P0 workflow composes the Agent and Tool layers with LangGraph:

```text
schema -> metric -> generate -> review
review approved -> execute
review rejected -> fail -> save_trace
execute success -> insight -> save_trace
execute failure and retry_count < 1 -> error_fix -> review
execute failure after retry -> fail -> save_trace
```

Example:

```python
from graph.workflow import run_workflow

result = run_workflow(
    "最近 30 天销售额最高的 5 个商品是什么？",
    db_path="data/ecommerce.db",
)
print(result["generated_sql"])
print(result["final_answer"])
print(result["trace_path"])
```

## Run Demo

```bash
streamlit run app.py
```

Open the Streamlit URL. The unified demo now displays:

- Ask & Analyze Command Center for one-run question, intent, SQL review/execution, evidence, report/action output, source metadata, safety boundaries, and trace timeline
- Reports for P1 evidence-backed charts/Markdown reports and P2 weekly/monthly business reviews
- Actions for approval-gated task, alert, email draft, verification, and audit output
- Observability for trace count, event count, SQL repair count, eval pass rate, approvals, audit logs, node latency, tool counts, failures, and raw details
- LLM Ops for provider configured/not configured status, runtime switches, prompt registry, deterministic baseline, provider_called/fallback_used/error visibility through run source cards
- Integrations for MCP Tool Layer contracts and FastAPI Async Run API endpoints/local run demo
- Capability Catalog for P0/P1/P2/P3 coverage including LLM Provider & PromptOps and Template Mining & Eval

The Command Center preserves the original P0 glass-box workflow while making P1/P2/P3 capabilities, provider participation, fallback behavior, and safety gates visible from the same Streamlit app.

## Demo Questions

- 最近 30 天销售额最高的 5 个商品是什么？
- 最近 3 个月销售额最高的品类是什么？
- 每个城市的总销售额是多少？
- 删除所有取消订单的数据。
- 帮我导出所有用户的手机号和邮箱。

## Eval

Run the P0 benchmark:

```bash
python eval/run_eval.py
```

Current eval summary:

- Total cases: 20
- Passed cases: 20
- Pass rate: 100.00%
- SQL execution success rate: 92.31%
- SQL first-pass success rate: 91.67%
- SQL repair success rate: 100.00%
- Dangerous SQL block rate: 100.00%
- Metric definition accuracy: 100.00%

The generated report is written to `eval/report.md`.

## P0 Limits

- The SQL Generator is deterministic and covers the P0 ecommerce demo scope; it is not a general text-to-SQL model yet.
- Error Fix Agent supports a narrow one-retry repair path for P0 failure cases.
- React UI, persistent async jobs, RBAC, dashboard frontend views, Docker/CI, and full ActionOps product features remain outside the current baseline.
- P1 Reliable Analysis & Report Core is complete: Business Context Retrieval, Evidence Validator, Chart Agent, and Report Agent are implemented.
