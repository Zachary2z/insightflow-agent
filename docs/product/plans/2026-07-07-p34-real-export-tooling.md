# P34 Real Export Tooling

Date: 2026-07-07

## Why P34 Exists

P33 closed the Analysis Workbench answer path: final answers are model-written from the clean evidence ledger, Product Result Builder only assembles product payloads, old template/rewrite paths are deleted, and chart artifacts consume ledger/sanitized evidence. The next product gap is delivery.

InsightFlow should not stop at a web answer or report page. A real business analysis product should be able to hand users a usable artifact: a Word/PPT-style report, chart images, and a clean export package that can later be sent to Feishu, DingTalk, WeCom, Tencent Docs, PowerPoint, or Word integrations.

P34 starts with local real export tooling, not external SaaS publishing. This keeps the scope stable while proving real tool-calling beyond SQL/chart rendering.

## Product Goal

After P34, Report Center should be able to export a generated report into a real downloadable business document. Analysis Workbench should be able to project its result into the same safe export package contract, even if the first visible UI entry focuses on reports.

The intended chain is:

```text
Analysis Workbench result or Report Center report
-> safe Export Package
-> chart static fallback assets
-> document export tool
-> downloadable local business file
-> future external platform connectors
```

This phase should demonstrate:

- multi-agent outputs can become real tool inputs;
- tool calls generate real files, not mock SaaS placeholders;
- exported files reuse trusted report/analysis content instead of rewriting it;
- raw SQL, trace paths, provider metadata, API keys, database paths, local absolute paths, and internal task ids stay out of export artifacts.

## Report Structure Principle

The report content structure should follow the generated report, while the export layout structure should be stable.

```text
ReportDocument decides content:
title, opening summary, sections, section titles, section prose,
action recommendations, data boundaries, chart refs, evidence refs

Export tool decides layout:
cover/title hierarchy, typography, margins, heading levels,
chart placement, tables, appendix style, downloadable file packaging
```

This means the Word/PPT export tool must not regenerate, rewrite, or re-plan the report. It should read the existing `ReportDocument` and render it cleanly.

Allowed fixed export structure:

- document title / cover area;
- opening summary;
- report sections in the same order and with the same titles as `ReportDocument.sections`;
- section-level chart placement when charts/evidence refs are available;
- action recommendations;
- data boundaries;
- evidence summary or appendix;
- generation metadata such as workspace/report id and generated time.

Not allowed:

- forcing every report into fixed business chapters such as `经营概览 / 渠道表现 / 风险问题 / 行动建议`;
- rewriting model prose during export;
- calling the LLM again inside the export tool;
- using report type as a rigid template selector;
- stitching Analysis Workbench answers into report documents;
- including raw SQL, raw rows, trace/provider metadata, local absolute paths, API keys, database paths, or hidden debugging data in the exported document.

Example:

If the generated report is a channel operating review with sections such as `收入结构`, `投放效率`, `渠道风险`, and `下一步建议`, the exported document uses those sections.

If the generated report is a customer-service ticket report with sections such as `工单量概览`, `投诉类型分布`, `响应时效`, and `优先处理建议`, the exported document uses those sections instead.

The content stays flexible. The business document style stays consistent.

## Scope

### H1 Export Package As The Unified Output Contract

Goal: make `workspaces.export_package` the clean handoff between product results and real export tools.

Implementation direction:

- Ensure Report Center records can produce an export package with title, opening summary / business answer or report document, ordered sections, action recommendations, data boundaries, chart artifacts, static asset references, evidence summaries and refs, workspace id, run/report id, and generated time.
- Ensure Analysis Workbench product results can still produce a safe export package for later use.
- Keep export packages free of raw SQL, raw rows, trace paths, provider metadata, API keys, local absolute paths, database paths, and task/debug ids.
- Do not let export packages become another answer composer.

Suggested tests:

- report export package preserves `ReportDocument` order and section titles;
- analysis export package preserves business answer and chart artifact refs;
- export package rejects or strips unsafe metadata;
- no raw SQL/trace/provider/local path leaks.

H1 completion on 2026-07-07:

- `workspaces.export_package` now emits `p34.export_package.v1` with `package_id`, `source_type` (`report` or `analysis`), `workspace_id`, `source_id`, `title`, `generated_at`, `document`, `business_answer`, `business_content_summary`, ordered `sections`, `action_recommendations`, `data_boundaries`, `chart_artifacts`, `static_assets`, `evidence_refs`, `evidence_summary`, and `warnings`.
- Report packages are projected from `ReportRecord` / `ReportDocument` and preserve the original section order and titles. The package does not reorganize reports into fixed business chapters.
- Analysis packages are projected from the current product result, keep `sections=[]`, and only carry the existing business answer, evidence summary/refs, chart artifacts/static assets, recommendations/caveats, and warnings. They do not synthesize missing answers or concatenate multiple workbench answers into a report.
- Safety projection strips or rejects raw SQL, raw rows, trace paths, provider metadata, API keys/secrets, database paths, local absolute paths, path traversal, secret-bearing URLs, task ids/purposes, debug ids, prompt text/ids/tokens, and raw `chart_spec` JSON from the user-facing package body.
- Option-only charts produce a warning when no static fallback exists; no fake image success is emitted.
- Verification: `python3 -m pytest tests/test_export_package.py -q` (`8 passed`), `python3 -m pytest tests/test_workspace_report_runner.py tests/test_product_result_builder.py tests/test_p30_acceptance.py -q` (`64 passed`), `python3 -m pytest tests/test_p30_live_chart_acceptance.py -q` (`1 skipped`), `python3 -m pytest tests/test_p33_live_acceptance.py -q` (`1 skipped`), and `cd frontend && npm test` (`73 passed`).

### H2 Chart Static Asset Export

Goal: make chart artifacts usable in documents.

Implementation direction:

- Add a local chart export tool that takes a `ChartArtifact` and returns static image asset metadata.
- Prefer existing `image_path` / `image_url` when a safe static fallback already exists.
- For ECharts artifacts, generate or preserve a static PNG/SVG fallback suitable for document insertion.
- If static export is not possible, return a clear warning and let the document include a chart placeholder or evidence table summary. Do not pretend an image exists.
- Chart data must come from the existing artifact/evidence, not from new model output.

Suggested tests:

- ECharts artifact produces or carries a static fallback;
- legacy PNG/SVG artifacts remain compatible;
- missing static fallback returns a warning;
- unsafe paths or external secret-bearing URLs are rejected.

H2 completion on 2026-07-07:

- Added `workspaces.chart_static_export` with `export_chart_static_asset()` and `export_chart_static_assets()`.
- The tool first reuses safe existing chart assets from `image_path`, `image_url`, `path`, or `url`, so legacy PNG/SVG artifacts and ECharts artifacts with static fallback remain compatible.
- When an ECharts artifact has no static fallback but has usable existing `echarts_option` series data, the tool generates a deterministic workspace-relative SVG under `exports/charts/` for document insertion.
- If `echarts_option` is insufficient, paths/URLs are unsafe, or no workspace output root is available, the tool returns clear warnings and no fake path.
- `workspaces.export_package` now uses the static export tool to populate `static_assets` and to add generated safe SVG fallback paths back into exported chart artifacts.
- The implementation uses only existing chart artifact / ECharts option data. It does not call an LLM, generate chart data, re-analyze business questions, rewrite report conclusions, force business templates, or restore old `chart_agent`, `visualization_planner`, `chart_tool`, mock SaaS, Power BI mock, Jira mock, or `action_delivery` paths.

### H3 Word Document Export Tool

Goal: generate a real `.docx` from a Report Center export package.

Implementation direction:

- Add a local document export tool that takes the safe export package and writes a `.docx`.
- The tool should only render existing report content: title, opening summary, sections from `ReportDocument.sections`, section charts when available, action recommendations, data boundaries, and evidence summary / appendix.
- The tool may apply consistent Chinese-friendly style: fonts, heading levels, compact paragraph spacing, readable tables, chart sizing, and optional footer/metadata.
- The tool must not call the LLM, change report structure, invent new sections, or rewrite conclusions.

Suggested tests:

- a `.docx` file is generated for a saved report;
- document text includes the report title, opening summary, section headings, recommendations, and data boundaries;
- chart placeholders or images are included when chart artifacts exist;
- exported document does not contain raw SQL, trace paths, provider metadata, API keys, database paths, or local absolute paths.

H3 completion on 2026-07-07:

- Added `workspaces.document_export` with `export_report_docx(export_package, workspace_root=None, output_dir=None)`.
- The function accepts `p34.export_package.v1` Report Center packages and returns structured status: `success`, `document_path`, `download_name`, `warnings`, and `artifact` metadata for a local Word document.
- The `.docx` renders only existing export-package content: title, generated metadata, opening summary / `business_content_summary`, `ReportDocument.sections` in their original order with titles/bodies/chart refs, action recommendations, data boundaries, evidence refs, and compact evidence summary counts.
- The exporter applies Chinese-friendly Word styles, compact paragraph spacing, clear title/heading/body levels, and safe chart placement.
- PNG/JPEG-compatible static chart assets are inserted from workspace-relative safe paths. Missing assets, unsafe paths, or SVG-only assets are represented by a visible placeholder and warning; the exporter does not pretend a missing image was inserted.
- Analysis Workbench packages are rejected by default for full Word report export, so workbench answers are not stitched into report templates. A separate light analysis export can be designed later if needed.
- Safety filtering is separate from document rendering and strips raw SQL, raw rows, trace/provider metadata, API keys/secrets, database paths, local absolute paths, prompt/task/debug fields, and unsafe paths from document text and asset insertion.
- The implementation does not call an LLM, re-analyze business questions, rewrite conclusions, add fixed business chapters, or restore old `chart_agent`, `visualization_planner`, `chart_tool`, mock SaaS, Power BI mock, Jira mock, or `action_delivery` paths.
- Added `tests/test_document_export.py` for generation, readable content, chart insertion/placeholder behavior, no-leak guarantees, custom section order, and Analysis package rejection.

### H4 API, Frontend Download, And Acceptance

Goal: let users trigger export from the product UI.

Implementation direction:

- Add a report export API such as `POST /api/workspaces/{workspace_id}/reports/{report_id}/export`.
- Return export status, file metadata, warnings, and a download URL/path.
- Add a Report Center button such as `导出 Word`.
- Show clear states: exporting, success with download link, warning with usable file, and failure with reason.
- Analysis Workbench export UI can stay deferred unless it is small; keep its export package support tested at the backend level.
- Run at least one real DeepSeek report generation, then export the resulting report to `.docx` and inspect the generated content.

Suggested tests:

- API exports an existing report record;
- frontend shows export button and success/failure states;
- exported file can be downloaded or read from the workspace artifact area;
- no generated export files are committed.

H4 completion on 2026-07-07:

- Added `POST /api/workspaces/{workspace_id}/reports/{report_id}/export` for Report Center Word export. The API reads an existing report record, builds a safe report export package, calls `export_report_docx()`, verifies the resulting `.docx` exists under the workspace, records a `word_document` artifact, and returns a compact response with `success`, `document_path`, `download_name`, `download_url`, `warnings`, and artifact metadata.
- Reused the existing workspace artifact download route for `.docx` files. The API returns workspace-relative `document_path` plus URL-encoded artifact download URLs, never local absolute paths.
- Report Center now has a `导出 Word` button with exporting, success/download, warning, and failure states. The UI shows business-friendly chart warnings such as `部分图表当前以占位说明展示。` and does not expose trace, SQL, provider metadata, local paths, or export-package internals.
- API and frontend tests cover successful export/download, missing reports, generated-file-missing errors, no-leak response guarantees, SVG-only chart warning behavior, frontend API typing, and ReportViewer success/warning/failure states. `tests/test_document_export.py` continues to protect Analysis Workbench package rejection so workbench answers are not exported as full reports.
- Real DeepSeek acceptance ran on a temporary Chinese channel-operation workspace with goal `生成一份最近90天渠道经营复盘报告，覆盖收入结构、投放效率、客服压力、关键风险和下一步建议。`. The generated report title was `最近90天经营复盘报告`; it completed through `ledger_backed_report_center` with `provider_supplied=true`, exported Word in 27.30s, returned warning `部分图表当前以占位说明展示。`, and the `.docx` contained title, summary, sections, recommendations, and data boundaries with no SQL, trace/provider metadata, API key, database path, prompt/task/debug fields, or local absolute paths.
- Verification passed: `python3 -m pytest tests/test_document_export.py tests/test_workspace_report_api.py tests/test_workspace_report_runner.py -q` (`46 passed`), `python3 -m pytest tests/test_export_package.py tests/test_chart_static_export.py tests/test_p30_acceptance.py -q` (`17 passed`), `python3 -m pytest -q` (`688 passed, 14 skipped`), `cd frontend && npm test` (`76 passed`), and `cd frontend && npm run build`.

P34 can close. The remaining external Feishu/DingTalk/WeCom/Tencent Docs/Power BI/PPT-style publishing work stays out of scope for this phase.

## Out Of Scope

P34 should not do:

- real Feishu/DingTalk/WeCom/Tencent Docs publishing;
- real Power BI publishing;
- auth/RBAC or external account management;
- collaborative editing;
- long-running async export queues unless strictly necessary;
- LLM-driven document rewriting during export;
- fixed business report templates;
- mock SaaS connectors;
- restoring old `action_delivery`, `powerbi_publisher_mock`, `jira_ticket_mock`, `chart_agent`, `visualization_planner`, or `chart_tool` paths.

## Cleanup Rules

Code cleanliness matters more than preserving old compatibility.

- Delete stale export/mock/action/chart paths that conflict with the real local export-tool direction.
- Keep historical docs, but mark old paths as Historical/Superseded.
- Do not preserve dead tests that only assert mock SaaS behavior or fixed report templates.
- Keep tests focused on real product behavior: export package safety, static chart asset readiness, document generation, API/UI export flow, and no-leak guarantees.

## Acceptance Criteria

P34 can close when:

- Report Center can export a generated report into a real local `.docx`.
- The document follows `ReportDocument` content structure instead of a fixed business template.
- The export layout is consistent and readable.
- Chart artifacts are inserted or represented through safe static fallbacks/placeholders.
- Export packages and generated documents do not leak raw SQL, raw rows, trace paths, provider metadata, API keys, local absolute paths, database paths, task ids, or internal debug fields.
- Analysis Workbench and Report Center can both project safe export packages, even if only Report Center has the first visible export UI.
- Backend tests, frontend tests/build, and document export tests pass.
- At least one real DeepSeek report is generated and exported in acceptance.
- Generated documents, image exports, packages, traces, reports, databases, `.next`, `node_modules`, and workspace runtime artifacts are not committed.
