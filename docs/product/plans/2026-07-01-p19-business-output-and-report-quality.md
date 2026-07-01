# P19 Business Output And Report Quality

P19 turns the now-live DeepSeek analysis chain into output that business users can trust, read quickly, and act on. P18 made conclusions, evidence, recommendations, charts, and reports more consistent; P19 raises the product bar from "technically valid answer" to "business-ready answer and management-ready report."

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

## Non-Goals

P19 does not:

- Add React/Next.js architecture rewrites beyond focused UI rendering needed for answer/report quality.
- Add RBAC, deployment, Docker, scheduling, vector search, or external SaaS publishing.
- Restore old Streamlit/eval/demo/action/mock paths.
- Introduce hardcoded table-specific business rule trees.
- Hide failures by fabricating unsupported recommendations.
- Remove technical details entirely; it only keeps them out of the default business reading path.

## Product Principles

1. **Evidence before recommendation.** If a recommendation names a channel, segment, product, or region, at least one evidence bullet must name the same entity and metric.
2. **Business language first.** Main answers use Chinese business terms, units, and rounded values. Raw field names belong in technical details.
3. **Tradeoffs are explicit.** Multi-metric questions should say which metric drives the conclusion and when another metric points elsewhere.
4. **No fake certainty.** If data is insufficient, say what is missing and suggest the next query instead of forcing an action.
5. **Reports are synthesized, not concatenated.** The report runner should produce a coherent executive summary and action plan from section outputs.
6. **Charts explain the point.** Charts should appear with title, unit, and one business annotation tied to the same conclusion.

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

### P19-H1: Answer Evidence Alignment

Goal: Prevent conclusions and `why`/evidence bullets from naming different winning entities.

Scope:

- Add tests for channel and segment examples where the recommended entity must match supporting evidence.
- Extend `workspaces/answer_consistency.py` with entity/metric alignment checks.
- Ensure `headline`, `direct_answer`, `why`, `evidence_bullets`, and `recommendations` do not contradict each other.

Acceptance:

- A recommendation naming `微信私域` cannot cite `自然流量` as the primary reason unless it explicitly explains the tradeoff.
- Multi-metric answers must distinguish "收入最高", "ROI 最高", "订单数最高", and "综合建议".
- Existing P16 `business_answer` shape is unchanged.

### P19-H2: Business Vocabulary And Unit Normalization

Goal: Remove raw technical field names from user-facing copy.

Scope:

- Add a small, generic vocabulary layer for common analytical fields:
  - `total_revenue` -> `总收入`
  - `order_count` -> `订单数`
  - `avg_order_value` / `avg_revenue` -> `客单价`
  - `total_spend` -> `投放成本`
  - `roi` -> `ROI`
  - `channel` -> `渠道`
  - `segment` -> `客户分群`
- Format values with Chinese units where helpful: 万元, 元, 单, 百分比/倍数.
- Keep raw names available in technical details only.

Acceptance:

- Main answer and report section body do not show raw column names unless the user explicitly asks for technical detail.
- Evidence bullets include readable metric names and rounded values.
- No table-specific business rule tree is introduced; mapping is generic and small.

### P19-H3: Decision-Ready Answer Structure

Goal: Make each answer useful to a business user in one screen.

Scope:

- Improve `business_answer` building so `direct_answer` includes:
  - the answer,
  - the main reason,
  - the tradeoff when metrics disagree.
- Ensure recommendations are concrete and not duplicates of the direct answer.
- Add caveats when data is insufficient, only one comparison row exists, or required cost/ROI fields are missing.

Acceptance:

- For "哪个渠道最值得加预算", answer includes recommendation, evidence, and next action.
- For "哪个分群最值得重点运营", answer handles revenue/order/AOV tradeoff instead of forcing a single winner without口径.
- Empty `recommendations` are allowed only when the answer is descriptive and no action is requested.

### P19-H4: Report Synthesis Layer

Goal: Stop reports from being a raw concatenation of section outputs.

Scope:

- Add a report synthesis step in `workspaces/report_runner.py`.
- Generate Chinese management-facing report fields from section `business_answer`s:
  - executive_summary,
  - key_findings,
  - action_plan,
  - risk_and_limits.
- Keep technical appendices unchanged but remove technical labels from default Markdown/body sections.

Acceptance:

- Executive summary is short, non-repetitive, and action-oriented.
- Report headings are Chinese-first.
- `_No recommendations recorded_` no longer appears in business-facing Markdown; use a Chinese empty-state sentence only when needed.

### P19-H5: Chart Narrative Integration

Goal: Make charts explain the business point instead of appearing as detached artifacts.

Scope:

- Align chart annotations with the final answer entity and metric.
- If provider chart spec references missing columns, fall back to validated existing execution columns without surfacing internal validation text to the user.
- Ensure report UI displays chart image, title, unit, and business annotation together.

Acceptance:

- Chart annotation does not contradict the business answer.
- Report center shows generated charts inline, not only as artifact paths.
- Technical chart validation errors remain in technical details, not the business body.

### P19-H6: Report Markdown And Frontend Reader Polish

Goal: Make report output readable as a real management document.

Scope:

- Update `workspaces/report_markdown.py` to render the new synthesized report structure.
- Update `ReportViewer` / `ReportSection` only where needed to match the same structure.
- Keep SQL, trace paths, provider metadata, and raw rows behind collapsed technical details.

Acceptance:

- Markdown report starts with Chinese title and management summary.
- Section titles are Chinese and business-facing.
- Report body can be read without opening technical appendix.

### P19-H7: Real DeepSeek Acceptance And Regression

Goal: Verify the improved output with real model calls and current Chinese business data.

Scope:

- Add or update opt-in live tests for:
  - channel budget question,
  - customer segment priority question,
  - management report generation.
- Run deterministic full regression and frontend tests.
- Run one real DeepSeek acceptance manually or through opt-in tests.

Acceptance:

- `python3 -m pytest` passes.
- `cd frontend && npm test` passes.
- `cd frontend && npm run build` passes.
- Real live run contains `provider_called: true` for question understanding, SQL planning/candidate, insight drafting, and claim typing.
- Business answer and report output do not show raw technical fields in the main body.

## Suggested Execution Order

1. P19-H1: alignment correctness first.
2. P19-H2: vocabulary/unit cleanup.
3. P19-H3: decision-ready answer structure.
4. P19-H4: report synthesis.
5. P19-H5: chart narrative.
6. P19-H6: report/frontend polish.
7. P19-H7: live acceptance and closeout.

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
- Reports are synthesized into a coherent management document.
- Charts are visible and annotated in the report body.
- Technical detail remains available but not dominant.
- The implementation stays generic for business datasets and does not become a table-specific rule tree.
- Full backend/frontend regression passes.
