# P30 Chart Artifact And ECharts Enhancement

Status: Complete; H1-H6 complete on 2026-07-06

P30 upgrades InsightFlow's chart capability from mostly static, per-surface rendering into a unified, evidence-bound chart artifact system. The goal is to make Analysis Workbench charts interactive, make Report Center reuse the same trusted chart artifacts, and prepare later platform exports to Feishu/DingTalk/WeCom/Power BI without re-querying data or asking a model to redraw charts.

P30 comes after P29 because routing and risk boundaries are now stable: `fast_fact` stays quick and chart-light, `standard_analysis` and `deep_judgment` keep evidence-backed Business Answer generation, and true external actions stop before SQL. That lets chart generation become a controlled tool capability instead of another ambiguous branch.

## Goals

- Add a unified `ChartArtifact` contract for Analysis Workbench, Report Center, and later platform exports.
- Add deterministic `ChartSpec -> ECharts option` generation from reviewed SQL/evidence rows.
- Render interactive ECharts charts in the frontend while preserving existing static PNG/SVG fallbacks.
- Keep chart data evidence-bound: no model-fabricated data, no raw SQL in product-facing chart cards, and every chart can trace back to evidence rows or report ledger entries.
- Make chart generation rules explicit by route:
  - `fast_fact`: only when the user explicitly asks for a chart.
  - `standard_analysis`: auto-generate for chartable comparison, trend, and structure questions.
  - `deep_judgment`: auto-generate more actively when evidence has 2+ comparable rows and clear numeric metrics.
  - `clarify` / `reject`: never generate charts.
- Make Report Center consume chart artifacts instead of redrawing from scratch whenever a matching artifact exists.
- Prepare an export/package layer so later P31 platform connectors can publish report text, chart images/options, evidence refs, and business annotations.

## Non-Goals

- Do not implement real Feishu, DingTalk, WeCom, Tencent Docs, Power BI, Tableau, or Looker publishing in P30.
- Do not remove the existing matplotlib PNG renderer or Report Center SVG fallback until ECharts artifacts are proven stable.
- Do not let the LLM generate arbitrary ECharts options with data embedded from memory. The model may suggest chart intent/type/annotation, but deterministic code must build and validate final options from evidence rows.
- Do not make `fast_fact` auto-generate charts without explicit user intent.
- Do not add a broad keyword-heavy chart rule tree. Use route metadata, task type, evidence shape, and chartability checks.
- Do not expose raw SQL, raw trace, provider metadata, local filesystem paths, or prompt internals in product-facing chart UI.

## Current State

Analysis Workbench currently uses:

```text
Visualization Agent
-> chart_spec
-> local_renderer
-> matplotlib PNG
-> product_result.chart_artifacts
-> frontend <img>
```

Report Center currently has a separate chart path:

```text
ReportEvidenceChart
-> _render_svg_chart()
-> SVG artifact
-> report body / Markdown
```

This means Analysis Workbench and Report Center can produce charts through different logic. P30 should converge them around a shared artifact contract while keeping compatibility with existing chart outputs.

## Target Architecture

```text
reviewed SQL / QuestionEvidencePack / ReportEvidenceTable
-> ChartSpec
-> EChartsOption
-> ChartArtifact
   -> frontend interactive ECharts
   -> static PNG/SVG fallback
   -> Report Center reference
   -> future platform export package
```

The invariant is: one chart artifact owns the chart data, chart spec, renderer metadata, evidence references, and static/interactive render surfaces. Reports and external connectors should consume that artifact instead of regenerating data or chart logic independently.

## Chart Artifact Contract

Add fields to the existing chart artifact shape without breaking current `path` / `url` consumers:

```json
{
  "artifact_id": "chart_channel_revenue_001",
  "title": "最近90天渠道收入对比",
  "renderer": "echarts",
  "chart_type": "ranked_bar",
  "chart_spec": {
    "chart_type": "ranked_bar",
    "title": "最近90天渠道收入对比",
    "x": "channel_name",
    "y": "revenue",
    "unit": "元",
    "business_annotation": "私域社群收入最高。"
  },
  "echarts_option": {},
  "path": "runs/run_x/charts/channel_revenue.png",
  "url": "/api/workspaces/ws_x/artifacts/runs/run_x/charts/channel_revenue.png",
  "image_path": "runs/run_x/charts/channel_revenue.png",
  "image_url": "/api/workspaces/ws_x/artifacts/runs/run_x/charts/channel_revenue.png",
  "evidence_refs": ["question_evidence_pack"],
  "source": "analysis_workbench",
  "rendering_status": "rendered",
  "business_annotation": "私域社群收入最高。",
  "data_row_count": 3
}
```

Frontend should prefer `echarts_option` when available and fall back to `url` / `path` images.

## H1: Chart Artifact Contract And Compatibility

Status: Complete on 2026-07-06.

Create or extend a chart artifact model around the existing product result shape.

Requirements:

- Keep current fields: `title`, `path`, `url`, `rendering_status`, `unit`, `value_label`, `business_annotation`.
- Add optional fields: `artifact_id`, `renderer`, `chart_type`, `chart_spec`, `echarts_option`, `image_path`, `image_url`, `evidence_refs`, `source`, `data_row_count`.
- Persist these fields in run history and report artifacts.
- Ensure older PNG/SVG artifacts still display normally.

Expected tests:

- Product result builder preserves legacy chart artifacts.
- Product result builder includes ECharts fields when visualization output contains them.
- Run history restore keeps `echarts_option` and evidence refs.

Completion notes:

- Added the backend chart artifact field contract in `workspaces/product_models.py`: legacy fields remain `title`, `path`, `url`, `rendering_status`, `unit`, `value_label`, and `business_annotation`; optional P30 fields are `artifact_id`, `renderer`, `chart_type`, `chart_spec`, `echarts_option`, `image_path`, `image_url`, `evidence_refs`, `source`, and `data_row_count`.
- Updated product result construction so existing `chart_artifacts`, visualization trace, and visualization delivery output preserve P30 optional fields while normalizing local image paths to workspace-relative artifact API URLs.
- Kept legacy PNG/SVG image consumers compatible: `path` and `url` remain populated for image artifacts, and `image_path` / `image_url` mirror the same static fallback when available.
- Updated run history restoration and history summary chart detection so rebuilt product results retain `echarts_option`, evidence refs, image fallback fields, and future option-only artifacts.
- Extended the frontend `ChartArtifact` type with the optional P30 fields. H1 kept image fallback rendering only; H3 later added full Analysis Workbench ECharts rendering.
- H1 deliberately did not add a deterministic ECharts builder, ECharts frontend dependency, Report Center chart reuse, static export package, or real external publishing.
- Verification passed: `python3 -m pytest tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py -q` (`82 passed`), `python3 -m pytest tests/test_visualization_intelligence.py tests/test_visualization_agent_external_tools.py -q` (`19 passed`), `cd frontend && npm test` (`70 passed`), and `cd frontend && npm run build`.

## H2: Deterministic ECharts Option Builder

Status: Complete on 2026-07-06.

Add a deterministic backend builder:

```text
visualization/echarts_option_builder.py
```

Inputs:

- validated `chart_spec`;
- `execution_result` or report evidence table rows;
- optional business labels and units.

Outputs:

- ECharts `option` JSON for supported chart types.

Initial supported mapping:

- `ranked_bar` / `bar` -> category x-axis + numeric y series.
- `line` -> category/time x-axis + numeric y series.
- `grouped_bar` -> category + series grouping when a series column is present.
- `scatter` -> numeric x/y, optional label dimension.
- `dual_axis_line` -> two numeric y axes.
- fallback `table` -> no ECharts option, keep tabular preview/static fallback.

Validation rules:

- `x`, `y`, `series`, `y_secondary` must exist in returned columns when required.
- series data must come only from execution/report evidence rows.
- no arbitrary JavaScript functions in option.
- option size should be bounded by row limits; large outputs should sample or fall back to table with a data-limit note.

Expected tests:

- Builds a ranked bar option from channel revenue rows.
- Builds a line option from date trend rows.
- Rejects missing columns.
- Does not include values not present in source rows.

Completion notes:

- Added `visualization/echarts_option_builder.py` and exported `build_echarts_option` from `visualization.__init__`.
- The builder is deterministic and only consumes `chart_spec` plus reviewed `execution_result` / evidence table rows. It does not call an LLM, does not execute SQL, and does not accept model-written final ECharts options.
- Supported H2 chart types are `ranked_bar`, `bar`, `line`, `grouped_bar`, `scatter`, and `dual_axis_line`. `table` deliberately returns a table/static fallback reason without `echarts_option`.
- Input rows support the existing `columns + list[list]` execution-result shape and tolerate `list[dict]` rows. Required fields are validated against evidence columns before option generation.
- Numeric roles are validated before use. Non-numeric y values, scatter x/y values, and dual-axis series values fail clearly instead of silently producing bad data.
- Large evidence tables are bounded to at most 100 rows by default; callers may request a lower limit, and truncated options return `data_limit` with total and sampled row counts.
- The emitted option is JSON-only and does not include formatter functions, arbitrary JavaScript functions, raw SQL, trace/provider metadata, or local absolute paths. JavaScript-like, SQL-like, path-like, and trace/provider metadata text in chart titles is stripped; the same unsafe text in category/label evidence values fails validation rather than being embedded.
- H2 deliberately did not change frontend rendering, add `echarts` / `echarts-for-react`, change Visualization Agent output, remove matplotlib PNG rendering, remove Report Center SVG fallback, add platform connectors, or restore old chart agent/planner/tool paths.
- Verification passed: `python3 -m pytest tests/test_echarts_option_builder.py -q` (`11 passed`), `python3 -m pytest tests/test_product_result_builder.py tests/test_visualization_intelligence.py tests/test_visualization_agent_external_tools.py -q` (`54 passed`), and `python3 -m pytest tests/test_p29_acceptance.py -q` (`4 passed`).

## H3: Analysis Workbench ECharts Rendering

Status: Complete on 2026-07-06.

Update Visualization Agent output so a successful chart decision produces both:

- existing static artifact fields;
- new `echarts_option` and `renderer="echarts"`.

Frontend changes:

- Use the existing `echarts` dependency with a lightweight client-side React wrapper; do not add `echarts-for-react` unless a later slice proves it is necessary.
- Update `frontend/components/ChartArtifactGallery.tsx`:
  - if `artifact.echarts_option` exists, render an ECharts component;
  - if not, render current `<img>` fallback;
  - preserve caption and business annotation;
  - keep empty state unchanged.

Chart generation route policy after P30:

```text
fast_fact:
  explicit chart request only

standard_analysis:
  auto chart for chartable comparison/trend/structure evidence

deep_judgment:
  auto chart for chartable multi-row evidence, especially multi-metric comparisons and prioritization questions

clarify/reject:
  no chart
```

Expected tests:

- Fast fact without chart request still has no chart.
- Fast fact with explicit chart request has `echarts_option` and a static fallback.
- Standard analysis comparison can auto-generate a chart when evidence has a dimension and numeric metric.
- Deep judgment multi-metric channel question generates a chart when evidence is chartable.
- Frontend renders ECharts when option exists and image fallback when it does not.

Completion notes:

- Updated `agents/visualization_agent.py` so the active Analysis Workbench chart path keeps the existing local static renderer first, then calls deterministic `build_echarts_option` with the validated `chart_spec` and reviewed `execution_result` rows.
- Successful ECharts artifacts now include `renderer="echarts"`, `chart_type`, `chart_spec`, `echarts_option`, `image_path` / `image_url` static fallback, `evidence_refs`, `source="analysis_workbench"`, `data_row_count`, and the existing title/unit/value-label/business-annotation fields.
- ECharts builder failures do not fail the run. The artifact keeps its static image fallback and records `echarts_fallback_reason` in visualization trace metadata; the main UI does not show the technical reason.
- Updated `frontend/components/ChartArtifactGallery.tsx` to be a client component with a lightweight ECharts wrapper that initializes in `useEffect` using the existing `echarts` dependency. It prefers interactive ECharts when `echarts_option` exists and falls back to PNG/SVG/image rendering otherwise.
- The chart UI keeps business title, unit, and annotation, and continues to hide raw SQL, chart spec internals, trace paths, provider metadata, evidence refs, and local filesystem paths.
- Route policy remains unchanged: `fast_fact` only generates charts when the user explicitly requests a chart; `standard_analysis` and `deep_judgment` generate charts only when the evidence is chartable and current policy allows; `clarify` and `reject` do not generate charts.
- H3 deliberately did not change Report Center chart reuse, Report Center SVG fallback, matplotlib PNG rendering, old chart agent/planner/tool paths, or platform connector behavior.
- Verification passed: `python3 -m pytest tests/test_echarts_option_builder.py tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py tests/test_visualization_intelligence.py tests/test_visualization_agent_external_tools.py -q` (`114 passed`), `python3 -m pytest tests/test_p29_acceptance.py -q` (`4 passed`), `python3 -m pytest tests/test_fast_fact_path.py -q` (`13 passed`), `cd frontend && npm test` (`70 passed`), and `cd frontend && npm run build`.

## H4: Report Center Chart Artifact Reuse

Status: Complete on 2026-07-06.

Report Center should not redraw charts from scratch when a trusted chart artifact already exists for the relevant evidence. It should reference a chart artifact.

P30 should support two report paths:

1. Report evidence collector creates a chart artifact from report evidence tables using the same ChartSpec/ECharts builder.
2. Report document rendering consumes chart artifacts and embeds:
   - interactive ECharts in the web report detail view when possible;
   - static image/SVG in Markdown and future document exports.

Rules:

- A report may create a new chart artifact if the report has a new chart requirement not already covered.
- A report should not rerun SQL just to redraw an existing chart.
- Report chart refs must point to report evidence table ids or ledger evidence ids.

Expected tests:

- Report evidence chart creates a `ChartArtifact` with `echarts_option`.
- Report document includes chart artifact refs without dumping raw SQL or raw rows.
- Markdown export uses static image path or clean chart placeholder when static output is unavailable.

Completion notes:

- Added `workspaces/report_chart_artifacts.py`, a Report Center helper that converts collected `ReportEvidenceTable` rows plus report chart intent into the unified ChartArtifact contract. It uses deterministic `build_echarts_option` and does not call an LLM, execute SQL, or accept model-written final ECharts options.
- Report records now persist top-level `chart_artifacts`, while `ReportEvidenceChart` also carries the P30 fields: `artifact_id`, `renderer`, `chart_type`, `chart_spec`, `echarts_option`, `image_path`, `image_url`, `path` / `url`, `rendering_status`, `unit`, `value_label`, `business_annotation`, `evidence_refs`, `source="report_center"`, and `data_row_count`.
- The existing Report Center SVG renderer remains the static fallback. The helper links `path` / `url` and `image_path` / `image_url` to the same fallback so Markdown/download/export consumers do not need ECharts support.
- If ECharts option generation fails, report generation still completes. The chart artifact falls back to static image or chart intent, and the technical fallback reason is written to trace events, not to the main report body or Markdown.
- `frontend/components/ReportViewer.tsx` now reads `report.chart_artifacts` and reuses `ChartArtifactGallery`, so web report detail pages prefer interactive ECharts and fall back to images. Legacy evidence-pack chart image rendering remains available when a report has no unified artifacts.
- Markdown rendering remains static-only: it uses image/SVG links, titles, and business chart text, and does not embed `echarts_option`, `chart_spec`, SQL, raw rows, trace/provider metadata, local absolute paths, or internal ids in the main report.
- Report Center remains independent on `ReportEvidencePack + EvidenceLedger + ReportDocument`; H4 did not call Analysis Workbench nodes, stitch workbench answers into reports, restore `chart_agent` / `visualization_planner` / `chart_tool`, remove matplotlib PNG fallback, remove Report Center SVG fallback, or add Feishu/DingTalk/WeCom/Tencent Docs/Power BI publishing.
- Verification passed:
  - `python3 -m pytest tests/test_workspace_report_runner.py tests/test_report_planner_evidence.py tests/test_report_composer_validator.py tests/test_product_result_builder.py -q` (`107 passed`)
  - `python3 -m pytest tests/test_echarts_option_builder.py tests/test_visualization_agent_external_tools.py tests/test_workspace_analysis_runner.py -q` (`74 passed`)
  - `cd frontend && npm test` (`71 passed`)
  - `cd frontend && npm run build` passed

## H5: Static Export Fallback And Artifact Package

Keep static artifacts because external platforms and document formats usually need images.

Short-term behavior:

- Keep matplotlib PNG renderer for Analysis Workbench as fallback.
- Keep report SVG renderer as fallback.
- Store `image_path` / `image_url` alongside `echarts_option`.

Add a lightweight export package contract for future P31:

```json
{
  "package_id": "export_run_x",
  "workspace_id": "ws_x",
  "source_type": "analysis_run",
  "source_id": "run_x",
  "title": "渠道表现分析",
  "created_at": "2026-07-06T00:00:00Z",
  "language": "zh",
  "document": {"summary": "私域社群收入和投放效率领先。"},
  "business_answer": {},
  "chart_artifacts": [],
  "static_assets": [],
  "markdown_path": "",
  "document_path": "",
  "evidence_refs": [],
  "export_warnings": []
}
```

P30 should not publish this package to external platforms yet. It only prepares the internal payload.

Expected tests:

- Export package includes chart artifacts and evidence refs.
- Export package excludes raw SQL, provider metadata, traces, and local absolute paths.
- Existing artifact API can serve image fallback paths safely.

Completion notes:

- Added `workspaces/export_package.py` with `ExportPackage` (`p30.export_package.v1`) plus pure `build_report_export_package()` and `build_analysis_export_package()` helpers. The builders do not call an LLM, execute SQL, save manifests, or publish to any external platform.
- The export package contract includes `workspace_id`, `source_type` (`analysis_run` or `report`), `source_id`, `title`, `created_at`, `language="zh"`, `document`, `business_answer`, `chart_artifacts`, `static_assets`, `markdown_path`, `document_path`, `evidence_refs`, and `export_warnings`.
- Report Center packages are built from report records and include report document content, Markdown/report-document workspace-relative paths, unified chart artifacts, static SVG/image fallback assets, and evidence refs. Report Center remains independent on its report record/document/evidence path and does not call Analysis Workbench.
- Analysis Workbench packages are built from `product_result` / run-history-compatible payloads and include the P16 business-answer summary, unified chart artifacts, ECharts option metadata, static PNG/SVG/image fallback assets, and question evidence refs.
- Chart artifacts in export packages retain only the connector-facing whitelist: `artifact_id`, `title`, `renderer`, `chart_type`, `path` / `url`, `image_path` / `image_url`, `rendering_status`, `business_annotation`, `evidence_refs`, `source`, `data_row_count`, and optional `echarts_option`. Internal `chart_spec` is intentionally excluded.
- Static export fallback is explicit: Web consumers can use `echarts_option`; external platform, Markdown, and static document consumers should use `image_url` / `image_path` or `path` / `url`. Missing static fallback records `export_warnings` and does not fail package creation.
- Export packages strip raw SQL, trace paths, provider metadata, API keys, database paths, local absolute paths, path-traversal references, and chart asset URLs carrying secret-like query parameters. Workspace-relative paths and clean artifact API URLs are allowed.
- H5 did not add Feishu, DingTalk, WeCom, Tencent Docs, Power BI, Word, PPT, or any real external connector; did not restore old `chart_agent`, `visualization_planner`, or `chart_tool`; and did not add generated manifests/artifacts/databases/traces to source tracking.
- Verification passed:
  - `python3 -m pytest tests/test_export_package.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py -q` (`61 passed`)
  - `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_echarts_option_builder.py tests/test_visualization_agent_external_tools.py tests/test_report_planner_evidence.py tests/test_report_composer_validator.py -q` (`127 passed`)
  - `python3 -m pytest tests/test_workspace_report_runner.py tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py tests/test_echarts_option_builder.py -q` (`115 passed`)
  - `python3 -m pytest tests/test_visualization_agent_external_tools.py tests/test_report_planner_evidence.py tests/test_report_composer_validator.py -q` (`68 passed`)
  - `cd frontend && npm test` (`71 passed`)
  - `cd frontend && npm run build` passed

## H6: Acceptance, Cleanup, And Live Verification

Status: Complete on 2026-07-06.

Add a focused P30 acceptance suite with generated workspace data:

Required analysis questions:

- `最近90天哪个渠道收入最高？给我画图。`
  - route `fast_fact`;
  - explicit chart request;
  - ECharts ranked bar + static fallback.
- `最近90天按渠道对比收入表现。`
  - route `standard_analysis`;
  - auto chart if evidence is chartable.
- `最近90天按渠道比较收入、投放金额和投放效率，哪个渠道表现最好？`
  - route `deep_judgment`;
  - chartable multi-metric evidence;
  - ECharts option present.
- `把预算调整到私域社群并发送通知。`
  - `reject`;
  - no chart artifact.

Required report question:

- Generate a channel performance report with revenue, spend, and ROAS evidence.
  - report evidence creates chart artifacts;
  - report web view can use ECharts option;
  - Markdown/static export can use image fallback.

Live DeepSeek:

- Keep opt-in only.
- Run only when `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1`, `INSIGHTFLOW_PRODUCT_LIVE_MODE=1`, and `DEEPSEEK_API_KEY` are set.
- Live output must record route, provider-called nodes, chart artifact renderer, ECharts option presence, static fallback presence, evidence row count, and elapsed time.

Completion notes:

- Added `tests/test_p30_acceptance.py` as the focused deterministic P30 acceptance suite. It covers explicit Analysis Workbench chart requests, no-chart `fast_fact`, Report Center `source="report_center"` chart artifacts, Markdown leak prevention, report export packages, analysis export packages, and warning-only behavior for option-only charts without static fallback.
- Added `tests/test_p30_live_chart_acceptance.py` as opt-in live P30 acceptance. It builds counting DeepSeek providers from product-live runtime flags, runs one Analysis Workbench chart question and one Report Center report goal, builds export packages from both outputs, and records chart/export/timing/provider-call summaries.
- Deterministic acceptance proved that Analysis Workbench chart artifacts carry `renderer="echarts"`, `echarts_option`, image fallback, and `evidence_refs=["question_evidence_pack"]`; `fast_fact` without explicit chart intent keeps `chart_artifacts=[]`; Report Center chart artifacts carry `source="report_center"`; Markdown excludes `echarts_option`, `chart_spec`, SQL, trace, and provider metadata; both export package builders preserve chart artifacts, static assets, and evidence refs; and missing static fallback produces `export_warnings` without failing.
- Live Analysis Workbench verification used model `deepseek-v4-flash` and question `最近90天按渠道比较收入并生成图表。`. It completed through `standard_analysis` in `38874 ms`, called question understanding, SQL planning, SQL candidate, Business Answer, and Visualization providers once each, produced one `analysis_workbench` ECharts chart artifact with static fallback and `question_evidence_pack`, and built an analysis export package with one chart artifact, one static asset, one evidence ref, and no export warnings.
- Live Report Center verification used goal `生成一份最近90天经营复盘报告，关注收入结构、客户分群和趋势变化。`. It completed through `ledger_backed_report_center` in `18323 ms`, called the DeepSeek-backed report composer once, produced three `report_center` ECharts chart artifacts with static fallback and ledger/evidence refs, and built a report export package with three chart artifacts, three static assets, 79 evidence refs, and no export warnings.
- Cleanup and artifact hygiene were verified. Old `chart_agent`, `visualization_planner`, `chart_tool`, obsolete simulated connector, fixed-template, deterministic-action-template, and keyword-inference hits remain Historical/Superseded docs or negative boundary tests. No generated database, report, chart, trace, `.next`, or `node_modules` artifact was added to source tracking.
- P30 did not add Feishu, DingTalk, WeCom, Tencent Docs, Power BI, Word, PPT, or other external connector publishing. Those remain P31 scope.
- Verification passed:
  - `python3 -m pytest tests/test_p30_acceptance.py tests/test_p30_live_chart_acceptance.py -q` (`1 passed, 1 skipped`)
  - `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_PRODUCT_LIVE_MODE=1 python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_product_live_mode.py -q` (`5 passed`)
  - `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_PRODUCT_LIVE_MODE=1 python3 -m pytest tests/test_p30_live_chart_acceptance.py -q -s` (`1 passed`)
  - `python3 -m pytest tests/test_export_package.py tests/test_echarts_option_builder.py tests/test_visualization_agent_external_tools.py tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py tests/test_product_result_builder.py -q` (`135 passed`)
  - `python3 -m pytest tests/test_report_planner_evidence.py tests/test_report_composer_validator.py tests/test_p29_acceptance.py -q` (`57 passed`)
  - `cd frontend && npm test` (`71 passed`)
  - `cd frontend && npm run build` passed
  - `python3 -m pytest -q` (`638 passed, 13 skipped`)
  - `git diff --check` passed

## Expected Outcome

After P30:

- Analysis Workbench charts are interactive ECharts charts instead of PNG-only cards.
- Fast facts remain fast and only generate charts on explicit chart requests.
- Standard/deep analysis questions get charts automatically when evidence makes the chart useful.
- Report Center can reuse or create the same chart artifact format instead of owning a separate chart drawing path.
- Every chart has evidence references, a deterministic option, and a static fallback for reports/platforms.
- P31 can focus on external platform connectors because chart artifacts, evidence refs, and export packages are ready.

## Required Verification

Focused backend:

```bash
python3 -m pytest tests/test_visualization_intelligence.py tests/test_visualization_agent_external_tools.py -q
python3 -m pytest tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py tests/test_fast_fact_path.py -q
python3 -m pytest tests/test_workspace_report_runner.py tests/test_report_planner_evidence.py -q
python3 -m pytest tests/test_p30_chart_artifact_echarts.py -q
```

Frontend:

```bash
cd frontend && npm test
cd frontend && npm run build
```

Regression:

```bash
python3 -m pytest tests/test_analysis_route_policy.py tests/test_question_understanding_router.py tests/test_business_answer_quality.py -q
python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_product_live_mode.py -q
```

Opt-in live:

```bash
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 INSIGHTFLOW_PRODUCT_LIVE_MODE=1 python3 -m pytest tests/test_deepseek_live_smoke.py tests/test_product_live_mode.py tests/test_p30_live_chart_acceptance.py -q
```

Do not count skipped live tests as proof of real provider/chart behavior.
