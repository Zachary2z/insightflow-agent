# P22 Evidence-Driven Report Generation Implementation Plan

**Date:** 2026-07-02

**Status:** In progress; P22-H1 and P22-H2 closeout complete

**Product Direction:** P22 turns Report Center from stitched analysis answers into a Chinese business report generator. The report path should collect evidence with tools, let the model write one coherent report from that evidence, validate key facts, and render a clean report page. Old report-section answer stitching should be deleted instead of preserved.

**Architecture Principle:** Keep facts and writing separate. SQL, metric, evidence, and chart tools own numbers and artifacts. The model owns business explanation and readable Chinese prose only after evidence is collected. Validation checks key numbers, rankings, entities, and time ranges without blocking reasonable evidence-backed judgment.

## Why P22 Exists

Real product testing after P21 showed that analysis answers can be useful, but reports still feel like several Analysis Workbench answers pasted together. The current report route runs preset sections, calls the analysis runner for each section, and renders each section's `business_answer` fields into Markdown. This creates several product problems:

- reports read like repeated `结论 / 直接回答 / 为什么 / 建议` blocks instead of one coherent report;
- superseded report titles and section names can remain English or internal in the old path, such as `Business Review` or `Evidence Backed Recommendations`;
- recommendations repeat generic lines and may not connect across chapters;
- user-requested topics such as 客服问题 can be missed by generic preset sections;
- report generation waits for several full analysis runs in sequence;
- the report object is not a clean contract for future Word, PPT, 飞书文档, 腾讯文档, or other export tools.

P22 solves this by replacing the old section-answer stitching path with an evidence-first report document pipeline.

## P22 Non-Goals

P22 does not include:

- real Word/PPT/飞书/腾讯文档 integration yet;
- authenticated external SaaS connections;
- scheduled reports;
- RBAC/auth/deployment work;
- vector databases or semantic cache;
- English/bilingual product output branches;
- keeping legacy report JSON compatibility;
- restoring old Streamlit, eval, fixed-template, chart-agent, action-workflow, mock SaaS, or demo-specific paths.

Old code, tests, docs, routes, and compatibility branches that only support the stitched report path should be deleted instead of preserved. Keep one clean current product path.

## Product Target After P22

After P22, Report Center should let a user ask:

```text
帮我生成一份最近90天经营复盘报告，包含收入结构、客户分群、客服问题和行动建议。
```

The product should produce a complete Chinese business report with:

- report title;
- generation status, time range, and data sources;
- one short opening summary;
- natural body chapters;
- charts placed near the relevant chapter;
- final action recommendations;
- data boundaries;
- collapsed evidence, SQL, validation, and trace details.

The main report should not expose Analysis Workbench fields such as:

- `headline`;
- `direct_answer`;
- `why`;
- `evidence_bullets`;
- `recommendations`;
- `confidence`;
- raw SQL;
- raw rows;
- prompt/provider metadata;
- trace IDs.

Those details can remain in collapsed technical appendix areas when useful.

## Target Report Shape

Example output:

```markdown
# 最近90天经营复盘报告

时间范围：2026-04-01 至 2026-06-30
数据来源：订单明细、客户资料、营销投放、客服反馈

最近90天，公司整体收入为 386.76 万元，总订单数为 915 单。收入主要来自企业SaaS订阅、数据分析服务和运营代投服务，其中企业SaaS订阅贡献最高。客户分群中，成长型团队是当前最重要的收入来源；客服侧需要重点关注交付延期和退款投诉，它们可能影响后续复购和客户满意度。

## 收入结构

企业SaaS订阅是最近90天收入最高的品类，收入约 121 万元；数据分析服务订单数最多，说明需求覆盖面较广，但客单价仍有提升空间。

[收入结构图表]

## 客户分群

成长型团队贡献收入最高，约 147.3 万元；高价值企业排名第二。当前收入主要依赖具备持续采购能力的客户群，后续应优先维护这两类客户。

[客户分群图表]

## 客服问题

客服反馈中，交付延期和退款投诉是需要重点关注的问题。如果这类问题集中出现在高收入客户群，会影响续费、复购和口碑。

[客服问题图表]

## 行动建议

1. 优先维护成长型团队和高价值企业，设计续费、增购和重点客户跟进策略。
2. 针对交付延期建立专项复盘机制，减少高价值客户流失风险。
3. 对数据分析服务尝试提升客单价，验证打包服务或高级版本转化效果。
4. 下一轮分析补充毛利、复购率、合同周期和销售人效，以支持更精确的预算决策。

## 数据边界

本报告基于当前工作区最近90天的订单、客户、营销和客服数据生成。当前数据尚未覆盖真实利润、合同周期和销售人效，因此涉及预算加码、资源投入和利润判断时，需要结合财务口径进一步确认。
```

## New Report Pipeline

```text
report goal
-> Report Planner
-> ReportPlan
-> Evidence Collector
-> ReportEvidencePack
-> Report Composer
-> ReportDocument
-> Fact Validator
-> Report Renderer
-> Report Center UI / Markdown / future exporters
```

### Report Planner

The planner converts the user's Chinese report goal and workspace profile/semantic layer into a report plan.

Responsibilities:

- infer report style, such as 经营复盘、趋势分析、问题诊断、客户分析、销售周报;
- create Chinese chapter plans based on the goal and available data;
- identify evidence requirements for each chapter;
- avoid fixed demo sections and English defaults;
- ask for clarification only when the report goal is too broad or critical scope is missing.

The planner output should be structured, not prose:

```json
{
  "title": "最近90天经营复盘报告",
  "report_style": "经营复盘",
  "time_range": "最近90天",
  "data_sources": ["订单明细", "客户资料", "营销投放", "客服反馈"],
  "chapters": [
    {
      "chapter_id": "revenue_structure",
      "title": "收入结构",
      "evidence_needs": ["按产品品类统计收入和订单数", "生成收入结构图表"]
    }
  ]
}
```

### Evidence Collector

The collector turns the report plan into evidence queries and chart requests.

Responsibilities:

- call the current SQL/metric/evidence/chart tools;
- reuse the current guarded SQL path, SQL review, schema repair, SQL execution, metric registry, and evidence validation;
- produce reusable evidence facts, tables, charts, warnings, and caveats;
- keep raw SQL and raw rows out of main report fields;
- avoid writing final report prose.

Evidence output should be structured:

```json
{
  "facts": [
    {
      "fact_id": "revenue_total_90d",
      "label": "最近90天总收入",
      "value": 3867562.48,
      "display_value": "386.76 万元",
      "source_chapter_id": "overview",
      "evidence_ref": "query_001"
    }
  ],
  "tables": [],
  "charts": [],
  "warnings": [],
  "data_limits": []
}
```

### Report Composer

The composer is the main model-backed writing step. It receives the full `ReportPlan` and `ReportEvidencePack` and writes one `ReportDocument`.

Responsibilities:

- write Chinese business prose;
- connect chapters into one coherent narrative;
- provide specific, evidence-backed recommendations;
- explain business tradeoffs when evidence supports them;
- avoid repeated analysis-answer fields;
- avoid inventing numbers, entities, or unavailable fields.

The composer should be given writing freedom, but only inside the evidence boundary.

### Fact Validator

The validator checks key facts after composition.

Responsibilities:

- confirm reported numeric values exist in the evidence pack;
- confirm top-ranked entities match the evidence pack;
- confirm time range and data source statements match the plan/evidence;
- mark unsupported claims for revision or warning;
- avoid rejecting reasonable qualitative judgment when the judgment cites supporting evidence.

Validation should be lightweight and deterministic where possible. The validator should not become a rigid template engine.

### Report Renderer

The renderer converts `ReportDocument` into product UI and Markdown. Future Word/PPT/飞书/腾讯文档 exporters should consume the same document object.

Main page order:

1. title;
2. status, time range, data sources;
3. opening summary;
4. chapters with charts;
5. final action recommendations;
6. data boundaries;
7. collapsed technical appendix.

## Proposed File Boundaries

Create or refactor toward these focused modules:

```text
workspaces/report_models.py
workspaces/report_planner.py
workspaces/report_evidence.py
workspaces/report_composer.py
workspaces/report_validator.py
workspaces/report_renderer.py
workspaces/report_runner.py
workspaces/report_store.py
frontend/components/ReportDetail.tsx
frontend/app/workspaces/[workspaceId]/reports/[reportId]/page.tsx
```

Responsibilities:

- `report_models.py`: report contracts only.
- `report_planner.py`: user goal to `ReportPlan`.
- `report_evidence.py`: plan to `ReportEvidencePack`.
- `report_composer.py`: plan/evidence to `ReportDocument`.
- `report_validator.py`: key fact validation.
- `report_renderer.py`: Markdown and UI-friendly render data.
- `report_runner.py`: orchestration only.
- `report_store.py`: persistence only.
- frontend report components: display report, not compose report.

## Old Paths To Delete Or Replace

P22 should remove these current behaviors from the main path:

- fixed English `REPORT_TYPE_PRESETS` as the report's primary chapter source;
- per-section loop that calls `run_workspace_analysis()` to create report chapters;
- report-level narrative functions that only extract or prefix section answers:
  - `_synthesize_report_narrative`;
  - `_key_findings`;
  - `_action_priorities`;
  - `_management_summary`;
  - `_chart_and_evidence`;
- Markdown sections that render `章节业务答案` as the main report body;
- report main-body labels such as `结论 / 直接回答 / 为什么 / 关键证据 / 建议动作 / 置信度`;
- old tests that assert `Business Review`, `Overall Performance`, `Evidence Backed Recommendations`, or stitched section-answer output;
- obsolete report agents, writers, supervisors, or compatibility adapters if they are not used by the new plan/evidence/composer/validator path.

Do not preserve old paths "just in case". If a helper remains useful, migrate the minimal helper into the new module and delete the old entry point.

P22-H1 closeout deleted the old `agents/report_supervisor.py`, `agents/report_agent.py`, `agents/report_writer.py`, `agents/report_planner.py`, their legacy tests, and the old provider-backed report writer/planner prompt/schema/runtime flags. User-visible report body copy was also cleaned so the main report reads as business language rather than phase or engineering notes.

## P22-H1: Report Contract And Old Path Cutover

Status: Complete on 2026-07-02.

Goal: Establish the new report document contracts and cut off the old stitched-section main path.

Scope:

- define `ReportPlan`, `ReportChapterPlan`, `EvidenceRequirement`, `ReportEvidencePack`, `ReportEvidenceFact`, `ReportEvidenceTable`, `ReportEvidenceChart`, `ReportDocument`, `ReportDocumentSection`, and `ReportValidationResult`;
- update `run_workspace_report()` to express the new pipeline shape;
- remove fixed English presets from the main path;
- remove per-section `run_workspace_analysis()` report generation;
- update tests to fail against old stitched output.

Acceptance:

- report records no longer use `Business Review` as the default Chinese report title;
- main report documents no longer expose `章节业务答案`;
- report runner orchestration is easy to read: plan -> evidence -> compose -> validate -> render -> save;
- old stitched-section tests are deleted or rewritten.

Implemented H1 notes:

- `workspaces/report_models.py` now defines the P22 contracts: `ReportPlan`, `ReportChapterPlan`, `EvidenceRequirement`, `ReportEvidencePack`, `ReportEvidenceFact`, `ReportEvidenceTable`, `ReportEvidenceChart`, `ReportDocument`, `ReportDocumentSection`, and `ReportValidationResult`.
- `workspaces/report_runner.py` now follows `plan -> evidence -> compose -> validate -> render -> save`. The H1 planner/evidence/composer are intentionally minimal skeletons based on workspace profile and semantic-layer context; H2 replaces this with real Chinese report planning and evidence collection.
- Fixed English `REPORT_TYPE_PRESETS`, old section-question generation, per-section `run_workspace_analysis()` report generation, retry loops, and stitched narrative helpers were deleted from the report main path.
- `workspaces/report_markdown.py` renders `ReportDocument` directly and keeps plan/evidence/validation details in a collapsed technical appendix.
- The frontend report detail page renders document sections, recommendations, and data boundaries. The old report `ReportSection` business-answer renderer was deleted.
- Tests for report runner, store, API, frontend report detail, P20 realistic report acceptance, and live report acceptance were rewritten so they protect the new document contract instead of stitched section output.

## P22-H2: Planner And Evidence Collector

Goal: Generate report-specific evidence packs from current workspace data.

Scope:

- implement Chinese report planning from report goal + workspace profile + semantic layer;
- support 经营复盘 first, with generic chapter planning based on available data;
- collect revenue/product/customer/support/trend evidence only when matching fields exist;
- produce warnings when requested evidence is unavailable;
- generate only useful report charts;
- keep SQL, raw rows, and technical fields in appendix/technical details.

Acceptance:

- a report goal mentioning 收入结构、客户分群、客服问题、行动建议 produces matching chapter plans when data supports them;
- if the workspace has no support data, the report says the support chapter lacks source data instead of inventing it;
- evidence pack contains facts, tables, charts, warnings, and data limits;
- evidence collection does not write final report prose.

Implemented H2 notes:

- Added `workspaces/report_planner.py` for Chinese-first planning from `report_type`, `report_goal`, workspace profile, and semantic layer. It plans chapters for 经营概览、收入结构、客户分群、客服问题、趋势变化、行动建议 based on the user goal and available data.
- Added `workspaces/report_evidence.py` for evidence collection from current workspace data. It reuses `build_metric_registry()`, `validate_sql()`, `run_sql()`, and `build_evidence_payload()` instead of introducing a separate SQL path.
- Evidence packs now include Chinese labels, display values, source chapter ids, evidence refs, business-readable table titles/descriptions/columns/rows, chart intents, warnings, data limits, and technical query details.
- Missing requested evidence is kept as a planned chapter with missing evidence requirements and as warnings/data limits in the evidence pack.
- `run_workspace_report()` no longer accepts the old removed compatibility parameter and keeps the current plan -> evidence -> compose -> validate -> render -> save flow.
- Markdown and frontend main views render business-readable evidence summaries and small tables, while internal evidence ids, SQL, raw rows, provider metadata, and trace details stay in the technical appendix.

## P22-H3: Report Composer And Fact Validator

Goal: Let the model write one coherent Chinese report from evidence, then validate key facts.

Scope:

- implement `ReportComposer`;
- design a Chinese prompt that gives writing freedom while requiring evidence-backed numbers;
- output `ReportDocument`;
- implement deterministic key-fact validation;
- mark unsupported numeric/entity/ranking claims for revision or warning.

Acceptance:

- reports read like one complete business report;
- no repeated `结论 / 直接回答 / 为什么` blocks in the main report;
- recommendations are specific, prioritized, and tied to evidence;
- unsupported numbers or top-ranked entities are caught by validation;
- reasonable qualitative judgments are allowed when grounded in evidence.

## P22-H4: Renderer, Frontend Report Page, And Closeout

Goal: Make Report Center display the new report format cleanly and complete the cleanup.

Scope:

- replace Markdown rendering with the new `ReportDocument` renderer;
- update report detail UI to show title, status/time/data sources, opening summary, chapters, charts, final recommendations, data boundaries, and collapsed appendix;
- keep chart preview inline, with download/export as secondary action;
- update docs and tests;
- run cleanup audit for old report labels and paths.

Acceptance:

- report page first looks like a report, not a debugging page;
- technical details are collapsed;
- chart artifacts display near relevant chapters;
- Markdown download matches the clean report structure;
- old stitched report path is not reachable;
- focused and full regressions pass.

## Testing Strategy

Keep tests that verify current product behavior. Delete tests that only protect old report stitching.

Required focused tests:

```bash
python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_api.py tests/test_workspace_report_store.py -q
python3 -m pytest tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py -q
cd frontend && npm test -- --run tests/workspace-flow.test.tsx tests/api-client.test.ts
```

Historical commands that referenced deleted legacy files such as `tests/test_report_planner.py` are superseded by the current Report Center contract, store, API, and runner tests.

Required closeout checks:

```bash
rg -n "Business Review|Overall Performance|Evidence Backed Recommendations|章节业务答案|REPORT_TYPE_PRESETS|_synthesize_report_narrative|_key_findings|_action_priorities|_management_summary|_chart_and_evidence|run_workspace_analysis\\(" workspaces agents frontend tests README.md DEVELOPMENT_PLAN.md DEVELOPMENT_STATUS.md docs/product/plans -S
python3 -m pytest
cd frontend && npm run build
```

Allowed remaining search hits:

- historical notes explicitly marked superseded;
- negative tests proving old paths are not current;
- analysis-workbench UI labels, where `直接回答` may still be appropriate for ad hoc analysis and not Report Center.

## Live Acceptance Scenario

Use a realistic Chinese workspace with orders/customers/marketing/support data. Generate:

```text
帮我生成一份最近90天经营复盘报告，包含收入结构、客户分群、客服问题和行动建议。
```

Expected product result:

- coherent Chinese report;
- chapters reflect the requested topics;
- at least two useful charts when data supports them;
- specific final recommendations;
- data boundaries mention unavailable fields such as profit, contract period, or sales efficiency when absent;
- no English default section titles;
- no stitched Analysis Workbench answer blocks.

## Definition Of Done

P22 is complete when:

- the old stitched report generation path is removed from the active code path;
- Report Center uses `ReportPlan -> ReportEvidencePack -> ReportDocument -> validation -> renderer`;
- report output is Chinese-first, coherent, and business-readable;
- facts, charts, and recommendations are grounded in evidence;
- future external document/export tools can consume `ReportDocument`;
- obsolete report code and tests are deleted or rewritten;
- focused backend tests, full backend regression, frontend tests, frontend build, and cleanup audit pass.

After P22, real external report/chart/export integrations can start from a clean `ReportDocument` contract instead of binding to Analysis Workbench internals.
