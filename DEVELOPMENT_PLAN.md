# InsightFlow Agent Development Plan

This tracked plan records the project-level engineering boundaries that should guide future tasks. The full extracted planning references under `tmp/pdfs/` are local source material and are ignored by git.

## Final LLM Participation Boundary

InsightFlow treats LLMs as a controlled enhancement layer. The model can help with understanding, planning, candidate generation, wording, and suggestions, but deterministic tools remain responsible for approval, execution, validation, and audit.

The no-key deterministic baseline must continue to run without a provider, and P0 eval must remain 20/20 passing.

## Where The LLM Should Participate

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

## Where The LLM Must Not Take Ownership

| Deterministic owner | Reason |
|---|---|
| `validate_sql()` | SQL safety boundary; LLM must not self-approve SQL |
| `run_sql()` | Execution boundary; only deterministic tools execute SQL |
| `Evidence Validator` | Fact boundary; LLM claims must be independently checked |
| `Approval Gate` | Action boundary; LLM must not bypass human or rule approval |
| `Audit Logger` / `Trace Logger` | Audit boundary; LLM must not decide whether events are recorded |
| MCP database / report / action wrappers | External contracts must not bypass validators, approval, evidence, or trace requirements |
| P0 eval baseline | Core workflow must remain deterministic and provider-independent |

## Target Flow

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

## Acceptance Rules

- README, DEVELOPMENT_STATUS, requirements, and development plan language must stay aligned on LLM boundaries.
- All real-provider outputs must pass prompt-specific structured-output validation.
- LLM-assisted SQL candidates must not bypass `validate_sql()`.
- LLM-assisted insights and reports must not bypass Evidence Validator.
- LLM-assisted action drafts must not bypass Approval Gate or Audit Logger.
- Default no-key baseline must continue to run.
- P0 eval must remain 20/20 passing.
