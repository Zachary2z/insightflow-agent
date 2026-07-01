# P19 Business Output And Report Quality

P19 turns the now-live DeepSeek analysis chain into output that business users can trust, read quickly, and act on. P18 made conclusions, evidence, recommendations, charts, and reports more consistent; P19 raises the product bar from "technically valid answer" to "business-ready answer and management-ready report."

## Direction Update

P19 should not continue as an expanding list of one-off deterministic patches for every observed model mistake. That path would make the product brittle: unanticipated wording could bypass the checks, and the code would slowly become a keyword-heavy rule tree.

The improved direction is a small review-and-revision loop:

```text
SQL execution result
-> evidence validation
-> insight drafting agent
-> answer reviewer agent
-> final answer composer
-> minimal deterministic safety check
-> product UI / report
```

The model should still do the language-heavy work: understanding the question, drafting the answer, reviewing whether the answer is supported, and rewriting the final business copy. Deterministic code should verify structure, entity/metric existence, schema safety, and no-obvious-contradiction constraints. If the reviewer or final safety check cannot support the answer, the product should downgrade to a clear evidence-insufficient answer instead of fabricating certainty.

## Why P19 Exists

Recent real runs show the product can call DeepSeek and generate guarded SQL, but the final business surface still has quality gaps:

- The answer may recommend one entity while the `why` text cites another entity from the first evidence row.
- Some answers are too short for decision-making and do not explain tradeoffs.
- Recommendations may be empty or duplicate the direct answer.
- Technical field names such as `avg_order_value` or `total_revenue` can leak into business copy.
- Multi-metric questions need clear口径 handling: revenue, order count, AOV, ROI, and spend can point to different winners.
- Reports read like stitched section output rather than a concise management document.
- Report summaries can repeat long text and mix English section titles with Chinese business copy.
- Chart artifacts exist, but chart interpretation is not consistently integrated into the report narrative.

## P19 Goal

Make analysis replies and reports feel like a real Chinese business analysis product:

- Answers should be understandable in one screen.
- Recommendations should be concrete enough to act on.
- Evidence should support the recommended entity and metric.
- Reports should be management-facing, Chinese-first, and directly readable without technical appendix expansion.
- Technical details should remain available for audit, but not pollute the main business surface.
- P19 should use an Answer Reviewer Agent and Final Answer Composer to improve generality, instead of relying on a growing list of predicted failure cases.

## Non-Goals

P19 does not:

- Add React/Next.js architecture rewrites beyond focused UI rendering needed for answer/report quality.
- Add RBAC, deployment, Docker, scheduling, vector search, or external SaaS publishing.
- Restore old Streamlit/eval/demo/action/mock paths.
- Introduce hardcoded table-specific business rule trees.
- Turn `answer_consistency.py` into a large business-rule engine.
- Hide failures by fabricating unsupported recommendations.
- Remove technical details entirely; it only keeps them out of the default business reading path.

## Product Principles

1. **Evidence before recommendation.** If a recommendation names a channel, segment, product, or region, at least one evidence bullet must name the same entity and metric.
2. **Business language first.** Main answers use Chinese business terms, units, and rounded values. Raw field names belong in technical details.
3. **Tradeoffs are explicit.** Multi-metric questions should say which metric drives the conclusion and when another metric points elsewhere.
4. **No fake certainty.** If data is insufficient, say what is missing and suggest the next query instead of forcing an action.
5. **Reports are synthesized, not concatenated.** The report runner should produce a coherent executive summary and action plan from section outputs.
6. **Charts explain the point.** Charts should appear with title, unit, and one business annotation tied to the same conclusion.
7. **Reviewer before rules.** Complex semantic checks should be handled by a structured reviewer agent; deterministic checks are the final guardrail, not the main answer-writing system.
8. **Clean code over accumulated patches.** If a fix only adds another narrow keyword branch, prefer redesigning the reviewer/composer boundary.

## Quality Bar

Reducing the number of H tasks must not reduce engineering quality. Each P19 task must meet these standards:

- Start with tests for the product behavior being changed.
- Keep ordinary tests deterministic; live DeepSeek tests remain explicit and opt-in.
- Preserve the P16 `business_answer` public shape unless a later phase explicitly replaces it.
- Keep modules small and single-purpose. Avoid growing `answer_consistency.py`, report runner, or frontend renderers into large catch-all files.
- Prefer structured contracts over parsing prose.
- Remove unused code, obsolete tests, and old fallback paths touched by the task.
- Do not preserve compatibility for old product directions. If an old path conflicts with the current reviewer/composer product direction and is not required by the active FastAPI/Next.js workspace product, delete it.
- Do not commit `.env`, generated workspaces, reports, traces, charts, `.next`, databases, or caches.
- Run focused tests for the changed area and full backend/frontend regression at closeout.

## Cleanup Policy

P19 prioritizes a clean, current product codebase over preserving historical paths. The following should be removed when encountered in touched areas:

- Unused functions, modules, components, fixtures, and tests.
- Old deterministic answer templates that duplicate reviewer/composer responsibilities.
- Legacy fallback paths that only exist to keep old demo behavior alive.
- Mock SaaS/tool placeholders that are not part of the current product.
- Historical entry points, docs, or UI paths that conflict with the current FastAPI/Next.js workspace product.

Do not delete files merely because their names contain "fallback" or "mock"; some deterministic unit-test doubles and safety fallbacks are still valid. Delete only when the code is unused, protects obsolete behavior, or conflicts with the current product direction. If a file is retained for tests or safety, make that purpose obvious.

## Reviewer/Composer Architecture

P19 should introduce two focused product-facing components:

1. **Answer Reviewer Agent**
   - Input: user question, resolved question, execution result, evidence result, semantic/profile context, draft `business_answer`, and chart/report context when available.
   - Output: structured review JSON, not user-facing prose.
   - Responsibilities:
     - Identify whether the conclusion is supported by returned rows.
     - Check whether recommended entities and metrics appear in evidence.
     - Detect unsupported claims such as "significant growth" without trend evidence.
     - Detect metric mismatch, for example asking profit but answering revenue.
     - Detect multi-metric tradeoffs and missing decision criteria.
     - Recommend one of: `accept`, `revise`, `downgrade_to_insufficient_evidence`.

2. **Final Answer Composer**
   - Input: draft answer, reviewer result, user question, evidence rows, and existing P16 shape.
   - Output: final P16 `business_answer`.
   - Responsibilities:
     - Rewrite the answer in the user's language.
     - Keep conclusion, why, evidence bullets, recommendations, and caveats aligned.
     - Preserve a concise business tone.
     - Avoid raw SQL, trace IDs, provider metadata, and raw row dumps.

The deterministic consistency layer remains small and generic:

- Validate the P16 shape.
- Confirm that final answer entities and metrics exist in execution rows or evidence.
- Remove or downgrade obvious unsupported claims.
- Avoid table-specific business logic and broad keyword trees.

This means H tasks after H1 should favor a reviewer/composer pipeline over adding more one-off checks.

Suggested reviewer output shape:

```json
{
  "status": "accept | revise | downgrade_to_insufficient_evidence",
  "language": "zh | en",
  "supported_entities": [],
  "unsupported_entities": [],
  "supported_metrics": [],
  "unsupported_metrics": [],
  "issues": [
    {
      "type": "entity_mismatch | metric_mismatch | insufficient_evidence | tradeoff_missing | unsupported_claim",
      "message": "",
      "affected_fields": []
    }
  ],
  "revision_instructions": [],
  "confidence": "low | medium | high"
}
```

## Current Hotspots

Backend:

- `workspaces/product_result_builder.py`
- `workspaces/answer_consistency.py`
- `workspaces/report_runner.py`
- `workspaces/report_markdown.py`
- `workspaces/report_models.py`
- `agents/insight_agent.py`
- `agents/visualization_agent.py`
- `llm_ops/structured_output.py`

Frontend:

- `frontend/components/RunResult.tsx`
- `frontend/components/ReportViewer.tsx`
- `frontend/components/ReportSection.tsx`
- `frontend/components/ChartArtifactGallery.tsx`
- `frontend/components/AnalysisHistoryPanel.tsx`

Tests:

- `tests/test_answer_consistency.py`
- `tests/test_product_result_builder.py`
- `tests/test_business_answer_quality.py`
- `tests/test_workspace_report_runner.py`
- `tests/test_report_insight_cleanup.py`
- `tests/test_chart_product_quality.py`
- `frontend/tests/workspace-flow.test.tsx`

## P19 Target Output Shape

The public `business_answer` contract remains the P16 shape:

```json
{
  "headline": "",
  "direct_answer": "",
  "why": "",
  "evidence_bullets": [],
  "recommendations": [],
  "caveats": [],
  "confidence": "medium"
}
```

P19 changes quality rules, not the public shape. A strong answer should render as:

```text
结论：
建议优先增加微信私域预算。

关键依据：
1. 微信私域收入最高，近 90 天收入 97.7 万元。
2. 微信私域客单价最高，约 6,181 元。
3. 抖音信息流收入第二，但效率/成本需结合 ROI 再确认。

建议动作：
- 微信私域：先增加 10%-15% 测试预算，观察 2 周 ROI。
- 抖音信息流：保留预算，优化转化链路。
- 小红书种草：暂不加预算，先排查客单价偏低原因。

限制说明：
- 当前结论基于最近 90 天数据。
- 如果目标是纯 ROI，而非收入规模，需要按 ROI 单独排序复核。
```

## P19 Report Target Shape

Reports should default to:

1. 管理层摘要
2. 核心指标总览
3. 关键发现
4. 建议动作
5. 图表与证据
6. 口径与限制
7. 技术附录（默认折叠）

Suggested action table columns:

```text
优先级 | 动作 | 对象 | 依据 | 预期影响 | 风险 | 需要补充的数据
```

## H-Task Plan

P19 should stay compact. Each H task can contain several small commits, but the product should not split into many narrow planning slices.

### P19-H1: Close Current Alignment Hole

Goal: Finish the current deterministic guard so obviously contradictory answers do not ship while the reviewer/composer architecture is being built.

Scope:

- Fix the remaining plain `why` / `evidence_bullets` entity conflict case.
- Keep this guard small and generic.
- Do not add more broad keyword branches unless they are necessary for final safety.

Acceptance:

- A recommendation naming one entity cannot leave `why` or evidence bullets focused only on another entity.
- Unsupported entities downgrade to insufficient evidence.
- Tradeoff answers are not forced into a single winner.
- Existing P16 `business_answer` shape is unchanged.

### P19-H2: Reviewer And Composer Foundation

Goal: Add the core review-and-revision loop with structured contracts.

Status: Complete as of 2026-07-01.

Scope:

- Add Answer Reviewer Agent contract and structured validation.
- Add Final Answer Composer contract that preserves P16 output.
- Integrate them after insight drafting and before product UI/report surfaces.
- Keep deterministic `answer_consistency` as a final guardrail, not the main writer.
- Add deterministic tests using local provider fixtures and at least one opt-in live DeepSeek test path.

Acceptance:

- Reviewer returns `accept`, `revise`, or `downgrade_to_insufficient_evidence`.
- Composer rewrites unsupported draft answers or downgrades when evidence is insufficient.
- Recommendation freedom is preserved: the model may make business suggestions, but facts, entities, metrics, and risks must be evidence-grounded or explicitly marked as hypotheses.
- Main answer fields do not expose reviewer internals.

### P19-H3: Business Answer Quality Polish

Goal: Make analysis replies useful to real business users without turning them into rigid templates.

Status: Complete as of 2026-07-01.

Scope:

- Normalize common metric vocabulary and units in main answer fields.
- Improve decision-ready answer structure: conclusion, basis, tradeoff, recommendation, caveat, next step.
- Remove raw field names from the main answer unless the user asks for technical detail.
- Ensure recommendations are not duplicates of the conclusion and include evidence/risk/verification when action-oriented.

Acceptance:

- Advice questions receive a grounded recommendation, not just a data restatement.
- Hypotheses are labeled as hypotheses or next-step validation, not facts.
- Multi-metric questions state the decision basis.
- Answers remain concise enough for one-screen reading.

Completion notes:

- Added a small shared language-aware business-field label map for common metrics and dimensions such as revenue, order count, AOV, spend, ROI, channel, and segment.
- Final Answer Composer now rewrites reviewer-driven revisions with business-readable evidence, non-technical caveats, and explicit revenue-vs-ROI tradeoffs when returned metrics point to different leaders.
- Product result and report section normalization replace common raw field names in main business fields while leaving technical details and table previews intact.
- Added regression tests for Chinese answer language, business-field vocabulary, tradeoffs, grounded caveats, no invented ROI/profit advice, internal metadata leakage, and report section reuse.
- Follow-up fix: English questions now use English labels and fallback evidence wording, while Chinese questions still convert raw field names into Chinese business labels.

### P19-H4: Report And Chart Synthesis

Goal: Make reports read like management documents and make charts support the same story.

Status: Complete as of 2026-07-01.

Scope:

- Synthesize report output from reviewed business answers instead of concatenating sections.
- Add Chinese-first report structure: management summary, key findings, action priorities, chart/evidence, risks/limits, technical appendix.
- Integrate chart titles, units, inline images, and business annotations into report body.
- Keep technical errors and trace metadata in technical details.

Acceptance:

- Reports have a coherent executive summary and action plan.
- Chart narrative does not contradict the final answer.
- Report Markdown and frontend reader show Chinese business-facing content first.

Completion notes:

- Report records now synthesize reviewed/composed section `business_answer` values into report-level `executive_summary`, `key_findings`, `action_priorities`, `chart_and_evidence`, and `risks_and_limits`.
- Chinese report goals produce Chinese management structure by default; English report goals keep English report-level labels and avoid mixed Chinese field labels.
- Markdown embeds chart images/links directly in the business body and carries chart title, unit, and safe business annotation alongside the report evidence narrative.
- Frontend report detail renders the same management sections and chart unit/annotation in the main report body, while SQL, trace paths, provider metadata, raw rows, and internal section prompts remain in the collapsed technical appendix.
- Missing chart output uses a business-friendly no-chart explanation and does not expose visualization errors or internal trace paths in the main report.
- Added focused coverage for synthesized summaries, language consistency, metric tradeoffs, chart metadata, no-chart fallback copy, technical leakage boundaries, Markdown rendering, API payloads, and frontend report detail rendering.
- Repair follow-up: English report goals now keep English Markdown/frontend business labels and chart captions, Chinese report goals keep Chinese labels, and chart/evidence row summaries reuse shared business field labels instead of exposing raw column names such as `total_revenue`, `order_count`, `avg_order_value`, or `segment`.

### P19-H5: Quality Closeout And Live Acceptance

Goal: Prove P19 works end to end and keep the codebase clean.

Status: Complete as of 2026-07-01.

Scope:

- Run focused and full backend tests.
- Run frontend tests and build.
- Run opt-in real DeepSeek acceptance on representative Chinese business data.
- Audit unused code, old fallback/mock/template paths, generated artifacts, and docs consistency.
- Commit only source, tests, and necessary docs.
- Delete obsolete code and tests discovered during the audit instead of documenting them as future cleanup, unless deletion would break an active product path.

Acceptance:

- Full backend/frontend regression passes.
- Live run shows model participation in the intended reviewer/composer path when live mode is enabled.
- Generated artifacts and local secrets are not committed.
- No old product direction or unused code remains in touched areas.
- The final diff does not keep compatibility code for deleted or superseded product directions.

Completion notes:

- Focused backend regression covered workspace analysis/report runners, product result builder, reviewer/composer, business answer quality, chart/report quality, and cleanup boundaries.
- Full backend pytest, frontend Vitest, and frontend production build passed at closeout.
- Real DeepSeek acceptance ran on temporary generated workspace data for three Chinese business questions: single-metric top channel revenue, revenue-vs-ROI tradeoff, and a management channel-review report.
- The live runs used real provider calls, passed SQL review, produced Chinese business answers with evidence, recommendations, caveats, and generated displayable chart/report artifacts.
- A live finding from the single-metric factual question was fixed: clean provider answers that omit `recommendations` or `caveats` are now completed with minimal evidence-based next-step guidance and query-scope limits instead of shipping an empty product surface.
- Artifact hygiene and cleanup audit were completed without staging generated databases, reports, charts, traces, frontend build output, `.env`, `.superpowers`, or real DeepSeek temporary artifacts.
- P20/P21 are explicitly deferred and were not implemented in P19-H5.

## Suggested Execution Order

1. P19-H1: close the current deterministic alignment hole.
2. P19-H2: add reviewer/composer foundation.
3. P19-H3: polish business answer quality. Complete.
4. P19-H4: synthesize reports and chart narrative, including the language-label and evidence-summary repair. Complete.
5. P19-H5: live acceptance, regression, cleanup, and closeout.

## Future Phase Notes

P20 and P21 are intentionally recorded here only as future direction. They should not distract from P19 quality work.

### P20: Responsive Analysis Experience

Goal: Shorten perceived and actual waiting time after the analysis quality loop is reliable.

Likely scope:

- Add Route Classifier Agent to choose `fast_fact`, `standard_analysis`, `report_generation`, or `clarification`.
- Add safe fast path for low-risk factual questions.
- Add progress states for analysis steps.
- Return core answer before background chart/report generation where possible.
- Cache workspace profile and semantic-layer work.
- Move heavier reports to background tasks.

Quality requirement: fast path must never handle advice, budget, strategy, causal, or report-generation questions unless the router and safety checks classify them as low-risk factual requests.

### P21: Real Business Tool Calling

Goal: Connect useful China-oriented business outputs after quality and responsiveness are stable.

Likely scope:

- Export or publish reviewed reports to practical business artifacts such as Excel, Word/PDF, PowerPoint, or Feishu document-style outputs.
- Strengthen chart generation/export as a real tool path.
- Keep external integrations authenticated and explicit.
- Avoid Google Sheets as the default China-market example.

Quality requirement: external publishing must only use reviewed, evidence-grounded answers and reports.

## Verification Commands

Focused backend:

```bash
python3 -m pytest tests/test_answer_consistency.py tests/test_product_result_builder.py tests/test_business_answer_quality.py -q
python3 -m pytest tests/test_workspace_report_runner.py tests/test_report_insight_cleanup.py tests/test_chart_product_quality.py -q
```

Frontend:

```bash
cd frontend
npm test
npm run build
```

Full:

```bash
python3 -m pytest
```

Live acceptance should remain opt-in and explicit. Do not let ordinary unit tests depend on live DeepSeek availability.

## Done Criteria

- Analysis replies are Chinese, business-readable, and decision-ready.
- Recommendations are supported by matching evidence.
- Multi-metric tradeoffs are explicit.
- Reviewer/composer flow handles unanticipated wording without relying only on predicted failure patches.
- Reports are synthesized into a coherent management document.
- Charts are visible and annotated in the report body.
- Technical detail remains available but not dominant.
- The implementation stays generic for business datasets and does not become a table-specific rule tree.
- Full backend/frontend regression passes.
