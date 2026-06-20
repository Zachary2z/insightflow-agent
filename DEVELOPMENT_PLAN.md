# InsightFlow Agent Development Plan

This document is the tracked development plan for InsightFlow Agent. It consolidates the phased roadmap, task boundaries, acceptance criteria, and final LLM participation rules that were previously spread across local extracted planning notes under `tmp/pdfs/`.

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
| P3 - MCP & Engineering Core | In progress | Task 17, 18, 19, 19A, 20, 20C, 20A, and 20B complete; Docker/CI and later hardening not started |

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

### 4.2 Future LLM Enhancement Targets

These are the concrete places where future tasks should enhance the project with real provider-backed behavior. Each one must keep deterministic fallback and existing validators.

| Target | Why the LLM is useful | Future development task | Safety boundary |
|---|---|---|---|
| Provider-backed question understanding | Improve intent extraction for more varied Chinese business phrasing, synonyms, and multi-intent questions | Task 21 - add optional DeepSeek-backed understanding path behind the existing deterministic router | Must not generate SQL or execute SQL |
| Provider-backed clarification questions | Produce clearer follow-up questions when metric, dimension, time range, or filters are missing | Task 22 - add structured clarification prompt and schema | Must not guess missing requirements |
| Provider-assisted SQL planning | Help classify complex complete questions into template vs guarded candidate vs reject | Task 23 - add optional model-assisted routing with confidence/fallback and connect `llm_candidate` to guarded SQL generation | Must not return executable SQL directly |
| Business review decomposition | Improve weekly/monthly review section planning for complex review requests | Task 24 - expand controlled report planner for richer but still allowlisted section/subtask selection | Must not provide provider-supplied SQL |
| Report writing and business-language polishing | Make reports clearer for business users while preserving traceability | Task 25 - add provider-backed report prose from verified findings, hypotheses, SQL, chart paths, and trace path | Must not add unsupported claims |
| Insight claim suggestion | Suggest hypotheses and possible business explanations from execution results and context | Task 26 - expand guarded insight prompts with stricter claim typing | Evidence Validator decides what can be used |
| Action plan and email draft wording | Turn evidence-backed findings into clearer task, alert, and email draft wording | Task 27 - add optional LLM drafting before risk assessment and approval | Must not create actions without Approval Gate and Audit Logger |
| Template mining and LLM eval suite | Identify repeated successful `llm_candidate` patterns and measure provider output quality | Task 28 - expand template mining feedback and LLM eval smoke cases | Must not auto-modify production templates or affect no-key baseline |

### 4.3 Areas That Must Stay Deterministic

| Area | Reason |
|---|---|
| `validate_sql()` | SQL safety boundary; the model cannot self-approve SQL |
| `run_sql()` | Execution boundary; only deterministic tools execute SQL |
| Evidence Validator | Fact boundary; model claims must be independently checked |
| Approval Gate | Action boundary; model output cannot bypass approval |
| Audit Logger / Trace Logger | Audit boundary; model output cannot decide whether to record events |
| MCP tool wrappers | External contracts must not bypass internal validator, evidence, approval, or trace requirements |
| P0 eval baseline | Core demo must remain provider-independent and 20/20 passing |

### 4.4 LLM Enhancement Acceptance Checklist

- Every real-provider output is validated by a prompt-specific schema before an agent consumes it.
- Every LLM-assisted SQL candidate goes through `validate_sql()`.
- Every LLM-assisted insight/report claim goes through Evidence Validator.
- Every LLM-assisted action draft goes through Risk Assessor, Approval Gate, Action Executor, and Audit Logger.
- Provider failures return structured `success: false` errors and do not crash the workflow.
- Deterministic fallback remains available without an API key.
- `python3 eval/run_eval.py` remains 20/20 passed.

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
| Task 13 | Chart Agent | `tools/chart_tool.py`, `agents/chart_agent.py` | Ranking -> bar, trend -> line, optional share -> pie, paths written to state |
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
| Task 20 | LLM Provider and PromptOps Core | `llm_ops/provider.py`, `prompt_registry.py`, `eval_smoke.py` | Complete | Provider contract, prompt versions, cost/latency metadata, smoke eval |
| Task 20C | Production DeepSeek Provider & Structured Output Validation | `llm_ops/deepseek_provider.py`, `structured_output.py` | Complete | `.env` config, opt-in live tests, malformed JSON and schema mismatch failures |
| Task 20A | Question Understanding & Clarification Router | `question_understanding/router.py`, `agents/question_understanding.py` | Complete | Extracts intent slots, returns clarify/reject/template/llm_candidate, does not generate SQL |
| Task 20B | SQL Planning Router | `sql_planning/router.py`, `feedback.py`, `agents/sql_planning_router.py` | Complete | Routes to deterministic template or guarded LLM candidate, preserves clarify/reject, does not call provider |
| Future | Docker / CI | `Dockerfile`, `docker-compose.yml`, `.github/workflows/` | Not started | Repeatable local/dev setup and CI test workflow |

### P3 Acceptance Standard

- MCP contracts return JSON-compatible dictionaries and structured errors.
- API failures return structured failed responses instead of crashing.
- Dashboard data layer does not introduce frontend or provider behavior.
- Streamlit demo makes P1/P2/P3 visible, not just P0.
- LLM provider usage is opt-in, structured, traceable, and provider-independent by default.
- P0 eval remains 20/20 passed.

## 10. Current Next-Task Queue

The next task should be selected from the remaining P3 engineering backlog. Do not start multiple future tasks at once.

| Priority | Candidate task | Notes |
|---|---|---|
| Next | Task 21 - Provider-backed Question Understanding | Add optional DeepSeek-backed intent extraction behind deterministic fallback |
| Later | Task 22 - Provider-backed Clarification Router | Add structured clarification prompt/schema while preserving reject and fallback behavior |
| Later | Task 23 - Provider-assisted SQL Planning and Guarded Candidate Integration | Connect `llm_candidate` planning to guarded SQL generation and validation |
| Later | Task 24 - LLM Business Review Decomposition | Expand controlled allowlisted report/subtask planning |
| Later | Task 25 - Evidence-backed Report Writing and Polishing | Generate prose only from verified evidence and traceable artifacts |
| Later | Task 26 - Guarded Insight Claim Typing | Add stricter claim classification before Evidence Validator filtering |
| Later | Task 27 - LLM Action and Email Drafting | Draft task/alert/email wording before approval-gated execution |
| Later | Task 28 - LLM Template Mining and Eval Suite | Expand template recommendations and opt-in LLM eval coverage |
| Later | Docker / CI | Add repeatable environment and GitHub Actions while preserving current no-key baseline |
| Later | Production run persistence | Consider persistent async job storage only after API semantics are stable |
| Later | React dashboard | Only after dashboard data contracts are stable |
| Later | RBAC / permissions | Only after action and MCP surfaces require real multi-user controls |
| Later | Full ActionOps | External task/email integrations require stricter approval, audit, and secrets handling |

## 11. Final LLM Participation Boundary

InsightFlow treats LLMs as a controlled enhancement layer. The model can help with understanding, planning, candidate generation, wording, and suggestions, but deterministic tools remain responsible for approval, execution, validation, and audit.

The no-key deterministic baseline must continue to run without a provider, and P0 eval must remain 20/20 passing.

### Where The LLM Should Participate

| Area | Phase / task | Intended role | Boundary |
|---|---|---|---|
| Provider / PromptOps | P3 Task 20 / 20C | DeepSeek adapter, prompt registry, prompt versions, structured output validation, usage/cost/latency trace metadata | Must not replace deterministic fallback |
| Question understanding | P3 Task 20A, future provider enhancement | Extract metric, dimension, time range, filters, operation, limit, and risk flags | Must not generate or execute SQL |
| Clarification routing | P3 Task 20A, future provider enhancement | Ask focused follow-up questions for ambiguous requests | Must not guess missing SQL requirements |
| SQL planning | P3 Task 20B, future provider enhancement | Choose deterministic template, guarded `llm_candidate`, clarify, or reject strategy | Must not return executable SQL directly |
| Guarded SQL candidate | P2 Task 15B, hardened by P3 Task 20 / 20C | Propose SQL candidates for clear non-template questions | Every candidate must pass `validate_sql()` before `run_sql()` |
| Controlled report planning | P2 Task 15A | Select allowlisted report sections and help decompose review tasks | Must not provide SQL or final factual claims |
| Business review decomposition | P2 / P3 enhancement | Break weekly reviews, retrospectives, anomaly analysis, channel analysis, and Top/Decline analysis into subtasks | Each subtask still goes through SQL review, SQL execution, Evidence Validator, chart, and report tools |
| Guarded insight claims | P2 Task 15B | Suggest or polish claims from execution results, metric context, and business context | Evidence Validator decides which claims can be used |
| Report writing / polishing | P2 / P3 enhancement | Turn verified findings, hypotheses, SQL, chart paths, and trace paths into clearer business prose | Must not invent unsupported data or conclusions |
| Action drafting | P2 Task 16 enhancement | Draft task, alert, and email wording from evidence-backed findings | Must not create actions without Risk Assessor, Approval Gate, Action Executor, and Audit Logger |
| Email draft content | P2 Task 16 enhancement | Draft stakeholder-facing email text | Must create drafts only; no sending and no approval bypass |
| Template mining feedback | P3 Task 20B enhancement | Summarize repeated successful `llm_candidate` intent patterns for future deterministic templates | Must not automatically modify production templates |
| LLM eval / smoke tests | P3 Task 20 / 20C | Validate provider availability, JSON shape, prompt schemas, malformed JSON handling, and provider errors | Live provider tests must remain explicit opt-in |

### Where The LLM Must Not Take Ownership

| Deterministic owner | Reason |
|---|---|
| `validate_sql()` | SQL safety boundary; LLM must not self-approve SQL |
| `run_sql()` | Execution boundary; only deterministic tools execute SQL |
| `Evidence Validator` | Fact boundary; LLM claims must be independently checked |
| `Approval Gate` | Action boundary; LLM must not bypass human or rule approval |
| `Audit Logger` / `Trace Logger` | Audit boundary; LLM must not decide whether events are recorded |
| MCP database / report / action wrappers | External contracts must not bypass validators, approval, evidence, or trace requirements |
| P0 eval baseline | Core workflow must remain deterministic and provider-independent |

### Target LLM-Assisted Flow

```text
User Question
-> Question Understanding / Clarification
-> SQL Planning Router
-> deterministic template or guarded LLM SQL candidate
-> validate_sql()
-> run_sql()
-> Evidence Validator
-> guarded insight/report polishing
-> Chart Tool / Report Tool
-> Action Plan Drafting
-> Risk Assessor / Approval Gate
-> Action Tool
-> Audit / Trace
```

### LLM Acceptance Rules

- README, DEVELOPMENT_STATUS, requirements, and development plan language must stay aligned on LLM boundaries.
- All real-provider outputs must pass prompt-specific structured-output validation.
- LLM-assisted SQL candidates must not bypass `validate_sql()`.
- LLM-assisted insights and reports must not bypass Evidence Validator.
- LLM-assisted action drafts must not bypass Approval Gate or Audit Logger.
- Default no-key baseline must continue to run.
- P0 eval must remain 20/20 passing.

## 12. Long-Term Development Principles

- Do not pile on features before the current phase is stable.
- Preserve Agent/Tool/Graph boundaries.
- Prefer deterministic baselines and optional model-assisted enhancements.
- Every new behavior needs focused tests.
- High-risk boundaries must remain tool-owned: SQL validation, SQL execution, evidence validation, approval, trace, and audit.
- User-facing demos should make implemented capabilities visible and understandable.
