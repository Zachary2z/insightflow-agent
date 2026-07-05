# P27 Analysis Workbench Multi-Agent Refactor

## Goal

P27 is an Analysis Workbench architecture and latency phase. It turns the current many-node analysis workflow into a clearer coordinator-led multi-agent product path while keeping Report Center independent.

The goal is not to add more small agents. The goal is to reduce duplicated responsibilities, make the multi-agent collaboration easier to explain, lower Analysis Workbench latency, and prepare the codebase for real external business tools in a later phase.

## Product Boundary

Analysis Workbench and Report Center remain separate product paths.

Analysis Workbench answers one business question:

```text
user question
-> coordinator
-> data understanding
-> question evidence
-> evidence audit
-> business answer
-> optional chart
-> analysis product result
```

Report Center generates one complete report:

```text
report goal
-> report planner
-> report evidence
-> evidence ledger
-> report composer
-> report validator / repair
-> report document
```

P27 must not make Report Center call Analysis Workbench nodes to generate report chapters. Report Center must not return to stitched Analysis Workbench answers. Report Center may share low-level evidence/tool concepts, but its main path remains `ReportEvidencePack + EvidenceLedger + ReportDocument`.

## Current Pain Points

- The Analysis Workbench path has too many small nodes with overlapping responsibilities.
- Question understanding and clarification both reason about missing information.
- SQL planning and analysis planning both reason about required evidence.
- SQL generation and guarded SQL candidates are separate candidate-building surfaces.
- SQL review, schema repair, execution, and fix are exposed as many graph nodes instead of one evidence-building responsibility.
- Insight drafting, answer review, final composing, and claim typing can feel like repeated answer rewriting.
- Simple factual questions can still carry too much workflow overhead.
- Tool calls are real, but they are spread across nodes, making the multi-agent story look like a long function pipeline.

## Target Analysis Workbench Agents

### Coordinator Agent

Owns route and state, not factual calculation or final prose.

Responsibilities:

- Decide `clarify`, `fast_fact`, `standard_analysis`, `deep_judgment`, or `reject`.
- Decide which large agents are required for the run.
- Keep progress steps aligned with the real backend route.
- Avoid calling heavy model-backed agents for simple factual questions.

### Data Understanding Agent

Owns natural-language understanding and clarification.

Consolidates:

- `question_understanding`
- `clarification`
- resolved-question continuation
- the Analysis Workbench parts of route policy

Outputs a stable `AnalysisTask` with metrics, dimensions, time range, filters, decision goal, missing slots, clarification question, and resolved question.

### Evidence Agent

Owns Analysis Workbench evidence acquisition.

Consolidates:

- SQL planning
- analysis planning
- schema lookup
- metric matching
- deterministic SQL generation
- guarded LLM SQL candidate only when needed
- SQL review
- one-pass schema repair
- SQL execution
- one-pass execution fix
- question evidence payload construction

The Evidence Agent outputs `QuestionEvidencePack` and safe `tool_calls`. It must keep SQL review and read-only execution as non-bypassable safety gates.

Metric matching means translating business language such as `销售额`, `客单价`, `投放效率`, `ROI`, `复购率`, or `平均响应时长` into available fields and formulas from the current workspace semantic layer and metric registry. Missing source fields become data limits instead of invented calculations.

### Evidence Auditor Agent

Owns factual boundaries for the Analysis Workbench answer.

Consolidates:

- evidence validation
- claim typing
- factual parts of answer consistency

Outputs `AuditResult`: supported facts, reasonable inferences, unsupported claims, data limits, and confidence. Hard facts such as numbers, dates, rankings, entities, and chart values must be evidence-backed. Business explanations and recommendations can be model-written, but they must be framed as evidence-based judgment or hypotheses when the data cannot directly prove causality.

### Business Answer Agent

Owns the final Chinese business answer for Analysis Workbench.

Consolidates:

- insight drafting
- answer review
- final answer composing
- expression parts of answer consistency

Outputs the existing P16 `business_answer` shape. Simple factual questions should get concise answers. Complex recommendation or diagnosis questions should get natural Chinese explanation, evidence, recommendations, and caveats without becoming fixed templates.

### Visualization Agent

Remains separate but becomes strictly on-demand for Analysis Workbench.

It should run when the user asks for a chart, when the evidence has useful multi-row comparison or trend data, or when a complex answer benefits from visual support. It should not block simple fact answers unless the product intentionally waits for chart output.

## Nodes To Consolidate

P27 should explicitly reduce or hide these duplicated product-level nodes:

| Current nodes / responsibilities | P27 owner |
|---|---|
| `question_understanding` + `clarification` | Data Understanding Agent |
| `sql_planning` + `analysis_planner` | Evidence Agent evidence planning |
| `generate` + `guarded_candidate` | Evidence Agent SQL Candidate Builder |
| `review` + `schema_repair` + `fix` + `execute` | Evidence Agent safe execution chain |
| `evidence_validator` + `claim_typing` | Evidence Auditor Agent |
| `insight` + `answer_reviewer` + `final_answer_composer` | Business Answer Agent |
| `visualization_agent` on every completed run | On-demand Visualization Agent |

The implementation can keep smaller helper functions internally. The product graph and architecture should expose fewer, clearer responsibilities.

## Latency Work

P27 should lower Analysis Workbench latency without weakening safety:

- Move fast-path classification earlier into the Coordinator.
- For simple factual/ranking/summary questions, skip heavy insight/reviewer/composer/claim-typing work.
- Call LLM SQL candidate generation only when deterministic or semantic-layer SQL is insufficient.
- Call answer review/composition only when the answer is model-written, multi-claim, recommendation-heavy, or otherwise high-risk.
- Call visualization only when useful or requested.
- Add `QuestionEvidencePack` caching keyed by workspace id, data version, semantic-layer version, and normalized `AnalysisTask`.
- Invalidate cached evidence when data or semantic layer changes.

Do not skip SQL review, SQL execution, evidence payload construction, or factual boundary checks.

## Report Center Guardrails

P27 only adds boundary protection for Report Center.

Keep:

- `workspaces/report_runner.py`
- `workspaces/report_planner.py`
- `workspaces/report_evidence.py`
- `workspaces/report_ledger.py`
- `workspaces/report_composer.py`
- `workspaces/report_validator.py`
- `workspaces/report_markdown.py`

Add or keep tests proving:

- Report Center does not call `run_workspace_analysis()` to generate report chapters.
- Report Center still produces `ReportDocument`.
- Report Center still uses `ReportEvidencePack + EvidenceLedger`.
- Report Center does not stitch Analysis Workbench answers into report body sections.

## Implementation Slices

### H1 Agent Contracts And Boundary Tests

- Define Analysis Workbench contracts for `AnalysisTask`, `QuestionEvidencePack`, `AuditResult`, `WorkbenchToolCall`, and `CoordinatorDecision`.
- Add tests proving Report Center remains independent from Analysis Workbench nodes.
- Do not rewrite Report Center.

Status: complete. H1 added `workspaces/analysis_contracts.py` and no-key boundary tests covering contract serialization plus Report Center independence from `run_workspace_analysis()`.

### H2 Coordinator And Data Understanding

- Add a Coordinator surface for Analysis Workbench route decisions.
- Consolidate question understanding, clarification, resolved-question continuation, and fast/standard route output.
- Keep Chinese-first behavior and P25 safe full-data time defaults.

Status: complete. H2 added `workspaces/data_understanding_agent.py` and `workspaces/analysis_coordinator.py`, adapted the Analysis Workbench question-understanding graph node to emit H1 `AnalysisTask` and `CoordinatorDecision` state, and made the clarification router reuse Data Understanding's precomputed clarification result. Existing evidence, SQL execution, answer generation, visualization, and Report Center paths remain unchanged.

### H3 Evidence Agent Question Mode

- Consolidate Analysis Workbench evidence planning, schema/metric lookup, SQL candidate building, SQL review, repair, execution, and evidence payload output.
- Record clear tool calls.
- Keep SQL review non-bypassable.

Status: complete. H3 added `workspaces/evidence_agent.py` as the Evidence Agent question-mode surface, routed the Analysis Workbench evidence acquisition segment through it, emits H1 `QuestionEvidencePack` plus `WorkbenchToolCall` records, keeps SQL review non-bypassable, keeps schema repair and execution fix to one pass with re-review before execution, and leaves Report Center on its independent report path.

### H4 Evidence Auditor And Business Answer Agent

- Consolidate evidence validation and claim typing into `AuditResult`.
- Consolidate insight/reviewer/composer responsibilities into one Business Answer Agent surface.
- Preserve natural Chinese business explanations and evidence-backed recommendations.

Status: complete. H4 added `workspaces/evidence_auditor.py` and `workspaces/business_answer_agent.py`, routes standard/deep Analysis Workbench answers through the Business Answer Agent surface, emits H1 `AuditResult` on both fast_fact and standard/deep paths, keeps fast_fact on its lightweight answer path, keeps complex answers on the insight/reviewer/final-composer quality path, exposes audit details only in technical details/validation logs, and leaves Report Center on its independent report path.

### H5 Latency Optimization

- Move fast path earlier.
- Make heavy model-backed answer and visualization steps conditional.
- Add `QuestionEvidencePack` cache and invalidation tests.
- Keep complex-analysis quality and safety gates.

Status: complete. H5 tightened fast-fact metric normalization so semantic ids and business labels for the same metric do not force simple fact questions onto the heavy path; added a workspace-scoped `QuestionEvidencePack` cache keyed by workspace id, data version, semantic-layer fingerprint, and normalized task; records cache-hit trace/tool-call metadata while restoring only previously SQL-reviewed and SQL-executed successful evidence; bypasses cache for explicit `initial_sql`; invalidates on data or semantic-layer changes; and makes Analysis Workbench visualization on-demand for explicit chart requests, trends, and clearly chartable complex comparison/review questions. Fast facts still keep SQL review, SQL execution evidence, `QuestionEvidencePack`, and `AuditResult`, while standard/deep questions keep the full Business Answer Agent quality path. Report Center remains independent and does not use the Analysis Workbench evidence cache.

### H6 Cleanup, Regression, And Documentation

- Delete superseded Analysis Workbench compatibility code, duplicate routing branches, stale tests, and dead imports.
- Keep negative tests that prevent old chart/action/mock/report-stitching paths from returning.
- Run focused Analysis Workbench tests, Report Center boundary tests, full backend tests, frontend tests, frontend build, and opt-in live DeepSeek acceptance when credentials and flags are available.
- Update README, development plan, and status.

Status: complete. H6 removed obsolete Analysis Workbench graph node wrappers and route helpers that were replaced by the Evidence Agent question mode, removed dead imports and obsolete action/report/weekly report state fields, renamed misleading Data Understanding compatibility wording, deleted the old `route_after_sql_planning` implementation-detail test, and updated cleanup boundary tests to assert the current P27 graph. Regression kept fast_fact, standard/deep analysis, clarification continuation, `QuestionEvidencePack` cache, initial SQL bypass, on-demand visualization, and Report Center independent. Report Center remains on `ReportEvidencePack + EvidenceLedger + ReportDocument` and does not call Analysis Workbench nodes to generate report chapters.

## Acceptance Criteria

- Analysis Workbench is described and implemented through fewer large agent responsibilities: Coordinator, Data Understanding, Evidence, Evidence Auditor, Business Answer, and on-demand Visualization.
- Report Center remains a separate report path and does not use Analysis Workbench final answers as report sections.
- Simple factual questions use a shorter path.
- SQL review and execution safety cannot be bypassed by model output.
- Evidence and answer boundaries remain clear: hard facts require evidence; explanations and recommendations can be model-written within stated data boundaries.
- Tool calls are easier to inspect and explain.
- No-key mode remains runnable.
- Live DeepSeek mode remains opt-in and testable.
- Obsolete Analysis Workbench nodes or compatibility branches made unreachable by P27 are deleted instead of preserved.
- Generated artifacts remain ignored and untracked.
