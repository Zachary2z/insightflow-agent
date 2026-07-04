# Historical / Superseded: P13 Business Answer And Product UX Design

This document is retained only as a historical P13 design snapshot. Current implementation guidance lives in docs/product/plans/, especially the P17 cleanup plan and the completed P16 clean business output model plan. The current analysis/report implementation uses the P16 business_answer contract and must not treat older product-model, report-summary, Streamlit, eval, mock SaaS, action-workflow, or future Business Q&A wording in this snapshot as current product guidance.

## Goal

P13 turns the current workspace analysis and report flows from "technically works" into a business-facing product experience. The product should show understandable answers, evidence, charts, report progress, and technical details in the right places, while preserving the existing guarded SQL, evidence, trace, and provider boundaries.

## Product Direction

P13 has one primary product shape and one future-compatible shape:

- Primary shape: Analysis Workbench.
- Future-compatible shape: Business Q&A Mode.

The Analysis Workbench is the P13 implementation target. Business Q&A Mode is not a separate implementation target for P13, but the backend and frontend data model must avoid mixing everything into one raw result blob so a chat-first surface can reuse the same answer, evidence, chart, report, progress, and technical detail objects later.

## Current Problems To Fix

Current P11/P12 behavior proves the analysis chain can run, but several product gaps remain:

- Final answers can fall back to raw `field=value` execution rows when provider insight drafting is not enabled.
- Live DeepSeek acceptance tests verify that provider calls happen, but they do not strongly reject parameter-dump answers.
- SQL, raw execution rows, traces, and provider metadata appear too prominently in user-facing pages.
- Reports include internal section prompts, SQL, trace nodes, and provider metadata in the main reading experience.
- Chart output can show missing CJK glyphs and lacks product-grade labels, units, annotations, and visual hierarchy.
- Report generation can take long enough that a single loading state feels broken.
- Clarification is supported as a workflow stop state, but there is no product-quality continuation flow that combines the original question and the user's clarification answer.

## Core Product Model

P13 should introduce a clearer product model around analysis output. The UI and API should treat these as separate objects:

- `question_thread`: original user question, system understanding, clarification questions, user clarification answers, and resolved question.
- `business_answer`: headline conclusion, concise explanation, evidence-backed recommendations, caveats, and confidence.
- `evidence`: verified metrics, table preview, row provenance, evidence notes, and validation status.
- `chart_artifacts`: product-grade visual outputs with title, labels, units, image path or URL, and rendering status.
- `report`: report list/detail, executive summary, sections, status, progress, artifacts, and download links.
- `technical_details`: SQL, execution rows, trace path, provider metadata, validation logs, and debug fields.

Business users see `business_answer`, `evidence`, `chart_artifacts`, and `report` first. `technical_details` is always available but collapsed by default.

## Clarification Continuation

P13 must treat clarification as a normal product flow, not an error.

Current workflow can already do:

```text
user question
-> question_understanding_agent
-> clarification_router_agent
-> waiting_for_clarification
```

P13 must add the continuation half:

```text
pending analysis question
-> user answers only the missing detail
-> system combines original question + understanding + clarification answer + workspace context
-> resolved question is shown to the user
-> user continues or edits
-> normal SQL/evidence/chart/answer flow runs from the resolved question
```

The user must not have to rewrite the full question. Example:

```text
Original question:
帮我分析渠道表现，看看哪个渠道该加预算。

Clarification:
你希望分析哪个时间范围？

User answer:
最近 90 天。

Resolved question:
分析最近 90 天各渠道的收入、订单数、投放成本和 ROI，并给出预算调整建议。
```

The resolved question should be persisted and shown in the analysis thread before execution. The original question, clarification question, user answer, and resolved question must remain available in trace/audit data.

## Analysis Workbench UI

The Analysis Workbench is the primary P13 UI. It should have these sections:

1. Workspace header
   - Shows workspace name, data source readiness, profile readiness, semantic-layer readiness, and live/product mode status.

2. Business question input
   - A compact input for the user's business question.
   - Suggested prompts may be shown, but they must not replace free-form questioning.

3. Integrated analysis thread
   - This is the core UI improvement.
   - It contains the user question, system understanding, clarification, user clarification answer, resolved question, and continue/edit controls in one compact card.
   - It should use calm visual hierarchy: small labels, a light timeline, restrained colors, and compact option chips.
   - It should not split clarification into a separate page or separate unrelated module.

4. Business answer
   - Shows headline recommendation first.
   - Includes short explanation, evidence-backed next actions, caveats, and confidence.
   - Must not display raw execution rows as the final answer.

5. Evidence and chart
   - Shows product-grade chart and evidence table.
   - Chart must support Chinese text, value labels, units, and a short business annotation.

6. Technical details
   - SQL, execution rows, provider metadata, trace, and validation logs are collapsed by default.
   - Developers and advanced users can expand when needed.

## Reports UI

Reports should be a separate product surface, not only a dump of report artifacts.

Reports home:

- List reports by workspace.
- Show report type, status, created/updated time, and download availability.
- Show generation progress for running reports.
- Provide clear entry points for business review, channel performance, and revenue trend reports.

Report reader:

- Show business-facing title, report goal, executive summary, sections, charts, recommendations, and evidence notes.
- Include a left-side or top section navigation for longer reports.
- Provide Markdown download.
- Keep SQL, internal section prompts, trace nodes, provider metadata, and raw rows out of the main reading flow.
- Technical appendix can exist, but it is collapsed by default.

## Data Settings UI

Data Settings should focus on data readiness and model configuration, not analysis output.

Required areas:

- Data sources: upload/import/list CSV, Excel, and SQLite sources.
- Profile: field types, row counts, examples, and inferred roles.
- Semantic layer: editable metrics, dimensions, entities, and time fields.
- Model mode: product/live mode state and provider feature coverage.
- Safety and audit: SQL review, sensitive field blocking, trace availability, and technical detail policy.

The product should move toward one user-facing product/live mode instead of requiring users to manually enable many provider flags.

## Business Q&A Mode

Business Q&A Mode is a future-compatible surface. P13 does not need to fully implement it, but it should be designed in a way that the future mode can reuse:

- question thread,
- resolved question,
- business answer,
- evidence cards,
- chart artifacts,
- report draft,
- progress status,
- technical details.

The chat surface should be lighter than the workbench. It should offer a direct path to "open in workbench" when users need full evidence, reports, or technical detail.

## Backend/API Implications

P13 should avoid a large backend rewrite, but the current API shape needs to grow beyond one raw `result` blob.

Expected additions or changes:

- Persist pending clarification runs under the workspace.
- Add a continuation endpoint or request shape that accepts a `pending_run_id` and `clarification_answer`.
- Store `resolved_question` and question-thread data.
- Return structured answer/evidence/chart/report/technical-detail fields to the frontend.
- Add product/live mode helper so real provider-backed paths can be enabled together.

The old guarded boundaries remain:

- SQL review cannot be bypassed.
- SQL execution remains deterministic.
- Evidence validation remains required for claims.
- Visualization tool policy remains enforced.
- Technical details remain available for audit.

## Testing Requirements

P13 tests must cover product quality, not only chain execution.

Required backend tests:

- Clarification continuation combines original question and clarification answer into a resolved question.
- Continuation preserves original question, clarification question, user answer, and resolved question.
- Final answer formatter rejects raw parameter-dump answers in product-facing fields.
- Technical details still include SQL/trace/provider metadata but are separated from business answer.
- Product/live mode enables the required provider-backed paths together.

Required frontend tests:

- Analysis thread shows user question, system understanding, clarification, user answer, and resolved question in one card.
- Business answer renders before SQL or raw rows.
- Technical details are collapsed by default.
- Report reader does not show internal section prompts or provider metadata in the main report body.
- Data settings shows source/profile/semantic/model/safety sections.

Required live DeepSeek tests:

- A real analysis question calls provider-backed question understanding, SQL planning, SQL candidate, insight drafting, and visualization.
- The final answer is readable business prose with recommendation and evidence, not a key-value dump.
- A clarification case stops for clarification, accepts a short user clarification answer, resolves the question, and continues successfully.

## Out Of Scope For P13

- Full chat product implementation beyond future-compatible design.
- Real SaaS integrations such as Slack, Jira, Power BI, Notion, email, or CRM.
- Auth/RBAC.
- Deployment.
- PDF/PPT export.
- Scheduled reports.
- Large-scale async job infrastructure beyond lightweight report progress if selected during implementation.
- Restoring Streamlit, old ecommerce-only demo flows, or historical eval product paths.

## Acceptance Criteria

- Analysis Workbench shows a compact integrated question thread.
- Users can answer clarification prompts without rewriting the full original question.
- The system shows and uses a resolved question before continuing analysis.
- Business answers are readable, recommendation-first, evidence-backed, and not raw parameter dumps.
- SQL, raw rows, trace, and provider metadata are collapsed under technical details.
- Reports read like business reports and do not expose internal prompts in the main body.
- Data Settings clearly shows data sources, profile, semantic layer, model mode, and safety/audit status.
- Chart output supports Chinese text and product-grade labels.
- Live DeepSeek acceptance covers answer quality and clarification continuation.
- Existing P11/P12 guarded SQL/evidence/tool boundaries remain intact.
