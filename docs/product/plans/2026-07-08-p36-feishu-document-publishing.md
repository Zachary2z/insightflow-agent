# P36 Feishu Document Publishing

Status: H1-H7 complete
Date: 2026-07-08

## Goal

P36 turns Report Center output into a real external-tool workflow by publishing generated business reports to Feishu Docs through the open-source `lark-cli` first, while keeping the current report-generation path clean and independent.

The product outcome is:

```text
Report Center generates a ReportDocument
-> Report export package projects safe report content and chart assets
-> Feishu publisher creates a real Feishu document
-> ECharts/static chart images are inserted when available
-> optional companion Feishu Sheet stores editable evidence tables and native sheet charts
-> Report Center stores and displays the Feishu document link
```

P36 is the first external platform publishing phase. It should prove that InsightFlow can call a real business tool after analysis/report generation, without returning to simulated SaaS connectors or fixed report templates.

Live product testing on 2026-07-08 confirmed that the document-create path works with a real Feishu account, but also exposed publish-quality gaps to close inside P36 instead of deferring to a new platform phase:

- the Feishu document currently receives a simplified Markdown body, so report evidence tables that already exist in `report.md` / `ReportEvidencePack.tables` are not published;
- report charts can remain SVG-only static assets, while `lark-cli docs +media-insert` inserts only local PNG/JPEG/GIF files, so charts are skipped even though the Feishu document is created successfully.
- after H5, evidence tables and chart images could be published, but real readback showed that images were appended near the end of the Feishu document instead of appearing beside the matching report sections; evidence-table headings also cluttered the Feishu outline, and the document body could duplicate the title already owned by Feishu Docs. H6 replaces that active append-only image path with section anchors and Feishu CLI selection insertion.
- after H6, live Feishu Docs output is readable enough for report sharing. The next question is chart usability: Feishu Docs should keep polished static chart snapshots in-context, while users who need editable data and native Feishu charts should get a companion Feishu Sheet generated from the same evidence tables and chart artifacts. H7 records this hybrid path before deciding whether to adopt a Sheet-first publishing model later.

## Product Scope

### In Scope

- Publish an existing Report Center report to Feishu Docs.
- Use the existing `ReportDocument` / `p34.export_package.v1` package as the only report content source.
- Use `lark-cli` as the first Feishu implementation because it is an official open-source CLI and can be driven from backend tool code.
- Insert report charts into the Feishu document when safe static chart assets are available.
- Prefer P30/P34 ECharts-derived static SVG/PNG chart assets. Existing image fallback assets can be used if they are safe.
- Persist a safe external publish artifact on the report record: platform, document title, document id/token when available, URL, status, warnings, chart insertion counts, and created time.
- Add a Report Center UI action for `发布到飞书`, with publishing, success, warning, and failure states.
- Add deterministic tests with a fake command runner for command construction, JSON parsing, failure handling, artifact persistence, and frontend states.
- Add opt-in live Feishu verification that creates and reads back a real Feishu document when local credentials and `lark-cli` auth are configured.
- Publish report evidence tables into the Feishu document as Markdown tables generated from existing `ReportEvidencePack.tables` / `ReportDocument` output.
- Generate Feishu-safe PNG chart fallbacks from existing chart artifacts/ECharts options before `docs +media-insert`; keep ECharts interactive rendering in InsightFlow UI.
- Optionally create a companion Feishu Sheet during publishing: write report evidence tables into sheet tabs/ranges, create native Feishu sheet charts from the same chart artifact/evidence data when safe, and add the sheet link back into the Feishu document/report UI.

### Out of Scope

- No DingTalk, WeCom, Tencent Docs, Power BI, Slack, Jira, email, Google Sheets, or other platform integration in P36.
- No OAuth UI, user account management, RBAC, deployment, scheduled publishing, or multi-tenant permission model.
- No direct Feishu OpenAPI adapter in P36 unless `lark-cli` is unusable locally; keep the interface ready for a later `ApiFeishuPublisher`.
- No report rewriting, report re-planning, report section stitching, Analysis Workbench answer stitching, or fixed report templates.
- No LLM-generated chart data, no LLM-generated ECharts options, and no model recalculation during publishing.
- No fake-success external connector. If `lark-cli` is missing, unauthenticated, or the command fails, return a clear failure/warning.
- No generated Feishu tokens, trace files, exported documents, chart images, local databases, `.env`, or credentials committed to git.
- No Feishu Sheets/Base chart object integration in P36-H5/H6. P36-H7 may add a Feishu Sheets companion workbook as an optional enhancement, but it must not replace the already-working Feishu Docs publish path until live product testing proves the Sheet-first route is better.
- No Feishu content rewriting in P36-H6. H6 may change where existing section tables/chart anchors render and how heading levels are projected into Feishu Markdown, but it must not regenerate the report, ask the LLM to rewrite the body, or replace report content with a fixed template.
- No Sheet-side re-analysis in P36-H7. Feishu Sheets must receive evidence tables and chart data that already exist in the report export package; it must not query InsightFlow databases, call the LLM, rerun SQL, invent chart series, or become a second report generator.

## Current Foundations To Reuse

- Report Center remains independent on:

```text
ReportPlan
-> ReportEvidencePack
-> EvidenceLedger
-> ReportDocument
```

- P34 export tooling already builds safe packages from existing reports:

```text
workspaces.export_package.build_report_export_package()
workspaces.chart_static_export
workspaces.document_export
```

- P30/P34 chart artifacts already expose:

```text
ChartArtifact
-> echarts_option
-> image_path / image_url fallback
-> static_assets for document insertion
```

P36 should build on these contracts instead of inventing a separate report or chart path.

## Proposed Runtime Path

```text
User opens Report Center
-> user generates or opens an existing report
-> user clicks 发布到飞书
-> backend loads ReportRecord
-> backend builds p34.export_package.v1
-> Feishu publish service renders package to Feishu-safe Markdown/document blocks
-> CliFeishuPublisher calls lark-cli to create the Feishu document
-> report evidence tables are included as Markdown tables in the document body
-> chart static assets are converted/reused as Feishu-safe PNG/JPEG/GIF files and inserted through lark-cli media/doc commands when available
-> optional Feishu Sheet companion is created from evidence tables/chart artifacts and linked from the document
-> backend persists ExternalPublishResult on the report record
-> frontend shows the Feishu link, warnings, and chart insertion summary
```

The publisher is a delivery tool only. It does not call the LLM, execute SQL, validate business claims, rewrite report text, or decide report structure.

## Target Interfaces

### Publish Result

Create a small external publishing contract, for example in `workspaces/external_publishing.py`:

```python
@dataclass
class ExternalPublishResult:
    platform: str
    status: Literal["published", "warning", "failed"]
    title: str
    url: str | None = None
    document_id: str | None = None
    external_id: str | None = None
    created_at: str | None = None
    inserted_chart_count: int = 0
    failed_chart_count: int = 0
    warnings: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
```

`tool_calls` must be safe and compact: command name, success/failure, elapsed time, and high-level operation only. It must not expose credentials, raw local paths, raw CLI stdout that may contain secrets, or provider metadata.

### Publisher Interface

```python
class FeishuPublisher(Protocol):
    def publish_report(self, package: ExportPackage) -> ExternalPublishResult:
        ...
```

Initial implementation:

```text
CliFeishuPublisher
-> validates lark-cli availability/auth
-> creates a document from report Markdown or blocks
-> inserts chart images when supported
-> returns ExternalPublishResult
```

Future implementation:

```text
ApiFeishuPublisher
-> same interface
-> direct Feishu OpenAPI calls
```

## P36 Tasks

### P36-H1: Feishu Publisher Contract And CLI Adapter

Build the publishing boundary before wiring it into Report Center.

Status: complete on 2026-07-08.

Expected changes:

- Add `workspaces/external_publishing.py` for `ExternalPublishResult`, safe serialization, and common validation helpers.
- Add `workspaces/feishu_publisher.py` for `CliFeishuPublisher`, CLI command runner abstraction, command result parsing, and failure normalization.
- Keep CLI binary/config environment-driven, for example `LARK_CLI_BIN` with fallback to `lark-cli`.
- Return a clear failure if the CLI is missing, exits non-zero, returns invalid JSON, or appears unauthenticated.
- Keep command construction centralized and testable.

Tests:

- Fake command runner verifies document-create command construction.
- Missing CLI / non-zero CLI exit returns `status="failed"` with a business-readable message.
- JSON parsing extracts document URL/id when present.
- Official `lark-cli docs +create` nested JSON (`ok`, `data.document`) is parsed correctly, and `ok=false` is treated as failure.
- Safe serialization strips local absolute paths, tokens, raw stdout containing secret-like text, and credentials.
- Analysis Workbench `analysis` export packages are rejected so only full Report Center report packages can be published.
- Dict inputs missing explicit `package_version == p34.export_package.v1` are rejected instead of being treated as valid report packages.

Result:

- Added `workspaces.external_publishing.ExternalPublishResult` plus safe serialization helpers and the `FeishuPublisher` protocol.
- Added `workspaces.feishu_publisher.CliFeishuPublisher`, `CommandRunner`, `SubprocessCommandRunner`, and `CommandExecutionResult`.
- `CliFeishuPublisher` reads `LARK_CLI_BIN` with fallback to `lark-cli`, builds the official document-create command in one place as `lark-cli docs +create --doc-format markdown --title <title> --content <markdown>`, parses both official nested JSON and legacy flat JSON for document id/URL/title, and returns `published`, `warning`, or `failed` without throwing raw command failures.
- H1 repair tightened success handling: official `ok=false` returns `failed`; `ok=true` without `data.document` returns `warning`; successful nested `data.document.document_id/url` returns `published`.
- H1 repair tightened package validation: publish inputs must explicitly carry `package_version == p34.export_package.v1` and `source_type == report`.
- H1 records only safe tool-call summaries: operation, command name, success, elapsed time, and exit code. It does not store raw stdout/stderr, local absolute paths, tokens/secrets/API keys, raw SQL/rows, trace paths, provider metadata, prompts, or generated export artifacts.
- H1 does not add frontend buttons, Report Center API endpoints, chart insertion, live Feishu verification, direct OpenAPI calls, or any non-Feishu connector.

Suggested commands:

```bash
python3 -m pytest tests/test_feishu_publisher.py -q
python3 -m pytest tests/test_export_package.py tests/test_workspace_report_runner.py -q
```

### P36-H2: Report Center Publish API And UI

Wire the publisher to real reports.

Status: complete on 2026-07-08.

Expected changes:

- Add backend endpoint such as:

```text
POST /api/workspaces/{workspace_id}/reports/{report_id}/publish/feishu
```

- Endpoint behavior:
  - load the report record;
  - build `p34.export_package.v1`;
  - call `CliFeishuPublisher`;
  - persist the safe publish artifact on the report record;
  - return link/status/warnings to the frontend.
- Add Report Center UI action `发布到飞书`.
- UI states:
  - not published;
  - publishing;
  - published with link;
  - published with warnings;
  - failed with actionable message.

Tests:

- API publishes via fake publisher and persists artifact.
- API returns clear failure if report does not exist or package is not report source.
- Frontend renders publish button, loading state, success link, warnings, and failure message.

Result:

- Added `POST /api/workspaces/{workspace_id}/reports/{report_id}/publish/feishu`.
- The endpoint loads an existing Report Center report, builds `p34.export_package.v1` with `build_report_export_package()`, calls `CliFeishuPublisher.publish_report()`, persists `ExternalPublishResult.to_safe_dict()` under `report.external_publish_results.feishu`, and returns the same safe publish result to the frontend.
- Publisher business failures such as missing auth return `200` with `status="failed"` and safe warnings; missing reports return a clear `404`; only unexpected program failures become `500`.
- Report records now restore `external_publish_results` from `report.json`, so report detail can show the latest Feishu result after reload.
- Report Center detail now has a `发布到飞书` button with idle, publishing, published link, warning, and failed states. The UI displays only the safe URL/status/warnings and does not display raw command, stdout/stderr, token, trace, SQL, prompt, or tool-call internals.
- Frontend API types and `publishFeishuReport()` were added to `frontend/lib/api.ts`.
- H2 did not change the H1 official `lark-cli docs +create --doc-format markdown --title <title> --content <markdown>` command, did not add chart insertion, did not run live Feishu tests, did not call the LLM, did not rewrite reports, and did not rerun Report Runner.

Verification:

```bash
python3 -m pytest tests/test_feishu_publisher.py tests/test_workspace_report_api.py -q
python3 -m pytest tests/test_export_package.py tests/test_workspace_report_runner.py tests/test_document_export.py -q
cd frontend && npm test
cd frontend && npm run build
```

Suggested commands:

```bash
python3 -m pytest tests/test_workspace_report_api.py tests/test_feishu_publisher.py -q
cd frontend && npm test
cd frontend && npm run build
```

### P36-H3: Chart Image Insertion From ECharts Static Assets

Make charts travel with the report when the platform supports it.

Status: complete on 2026-07-08.

Expected changes:

- Reuse P34 static chart assets from the export package.
- Prefer assets generated from ECharts options; then reuse safe `image_path` / `image_url`; then fall back to chart caption/placeholders.
- Add a small chart insertion function in the Feishu publisher.
- If image insertion fails, keep the document published and return a warning instead of failing the whole publish.
- Track `inserted_chart_count` and `failed_chart_count`.

Important rule:

Feishu Docs should receive static image assets, not live ECharts JavaScript. The product can still say the chart came from the same ECharts-backed `ChartArtifact`; the external document receives the static export.

Tests:

- ECharts/static asset path is selected before legacy image fallback.
- Unsafe image paths/URLs are ignored with warnings.
- Media insertion failure returns `status="warning"` when document creation succeeded.
- The report publish artifact records chart counts.

Result:

- `CliFeishuPublisher` now treats chart insertion as a post-create step. It first calls `docs +create`, parses the official nested `data.document.document_id/url` response, then reads existing Report Center export-package `static_assets`.
- The publisher inserts only validated local PNG/JPEG/GIF chart files. SVG assets generated from ECharts options, URL-only assets, unsafe paths, missing files, and unsupported formats become warnings and increment `failed_chart_count`; none are reported as successful inserts.
- The media insertion command follows the official CLI shape:

```bash
lark-cli docs +media-insert --doc <document_id> --file <safe local file> --type image --align center --caption <caption> --width 800
```

- When `docs +create` returns a `/wiki/...` URL, insertion still uses the returned `document_id`, not the wiki URL. A `/docx/...` URL can be used only as a fallback when no id is available.
- Status aggregation is explicit: create failure returns `failed`; create success plus all chart insertions succeeding returns `published`; create success plus any chart insertion/asset failure returns `warning` while preserving the Feishu URL/document id.
- Safe publish artifacts now carry `inserted_chart_count`, `failed_chart_count`, safe `warnings`, and compact `tool_calls` for `create_document` / `insert_chart_image`. They do not expose raw stdout/stderr, local absolute paths, SQL, rows, trace, provider metadata, prompts, tokens, secrets, or access keys.
- Report Center displays the safe chart insertion count summary and still hides `tool_calls`.
- H3 did not call the LLM, rewrite the report, regenerate chart data, rerun SQL, publish Analysis Workbench answers as reports, run live Feishu verification, or add mock SaaS/action paths.

Verification:

```bash
python3 -m pytest tests/test_feishu_publisher.py tests/test_workspace_report_api.py -q
python3 -m pytest tests/test_chart_static_export.py tests/test_export_package.py -q
cd frontend && npm test -- workspace-flow.test.tsx
```

Suggested commands:

```bash
python3 -m pytest tests/test_chart_static_export.py tests/test_feishu_publisher.py tests/test_workspace_report_api.py -q
```

### P36-H4: Acceptance, Live Feishu Verification, Docs, And Cleanup

Close the phase with deterministic and real external-tool verification.

Status: complete on 2026-07-08.

Expected changes:

- Add an opt-in live test gated by explicit environment variables:

```bash
INSIGHTFLOW_FEISHU_LIVE=1
LARK_CLI_BIN=lark-cli
```

- Live acceptance should:
  - generate a minimal Report Center export package without calling DeepSeek/LLM;
  - publish the package to Feishu through `lark-cli`;
  - read back the document title or content summary when the CLI supports readback;
  - verify the URL/id is returned;
  - verify chart insertion count or chart warning behavior.
- Update `README.md`, `DEVELOPMENT_PLAN.md`, `DEVELOPMENT_STATUS.md`, and this plan with final results.
- Audit old-path references:

```bash
rg -n "mock|fake-success|action_delivery|powerbi_publisher_mock|jira_ticket_mock|chart_tool|visualization_planner|chart_agent|fixed template|deterministic action template|keyword inference"
```

Only historical/superseded notes or negative tests should remain.

Suggested verification:

```bash
python3 -m pytest tests/test_feishu_publisher.py tests/test_workspace_report_api.py tests/test_export_package.py tests/test_chart_static_export.py -q
python3 -m pytest tests/test_workspace_report_runner.py tests/test_document_export.py -q
cd frontend && npm test
cd frontend && npm run build
git diff --check
```

Optional live verification:

```bash
INSIGHTFLOW_FEISHU_LIVE=1 LARK_CLI_BIN=lark-cli \
python3 -m pytest tests/test_feishu_live_publish.py -q
```

Result:

- Added deterministic acceptance in `tests/test_workspace_report_api.py` for the final product path:

```text
existing Report Center report
-> build_report_export_package()
-> CliFeishuPublisher with fake CLI runner
-> lark-cli docs +create --doc-format markdown --title <title> --content <markdown>
-> lark-cli docs +media-insert --doc <document_id> --file <png> --type image --align center --caption <caption> --width 800
-> safe API response persisted under external_publish_results.feishu
```

- The acceptance test blocks publish-time report composer provider access and SQLite connections, proving publishing does not call the LLM path or execute SQL. It also verifies the original `ReportDocument` is unchanged and no Analysis Workbench `business_answer` is published as a report.
- Safe result checks cover stdout/stderr, absolute paths, SQL, raw rows, trace, provider metadata, prompts, tokens, secrets, and local temp/workspace paths.
- Added frontend acceptance in `frontend/tests/workspace-flow.test.tsx` proving `ReportViewer` displays only status, Feishu link, inserted/failed chart counts, and safe warnings; malicious warning/tool-call fields are filtered from the rendered UI.
- Added `tests/test_feishu_live_publish.py`, default skipped unless `INSIGHTFLOW_FEISHU_LIVE=1` and `LARK_CLI_BIN` are set. The live test uses real `lark-cli`, assumes the user is already logged in locally, creates a minimal Chinese report with one local PNG chart, asserts URL/document id/chart insert attempt, optionally reads back with `docs +fetch`, and prints only a safe boolean/count summary.
- Official commands used by P36:
  - `lark-cli docs +create --doc-format markdown --title <title> --content <markdown>`
  - `lark-cli docs +media-insert --doc <document_id> --file <safe local file> --type image --align center --caption <caption> --width 800`
  - optional readback: `lark-cli docs +fetch --doc <document_id> --doc-format markdown`
- Artifact hygiene was tightened with explicit `.gitignore` entries for generated local DBs and workspace run/report artifacts. No real Feishu link, document id, token, trace, generated DB, generated report, or generated chart artifact is committed by H4.
- Old-path audit found chart-agent/planner/tool, action delivery, mock SaaS, and fake-success wording only in historical/superseded docs, negative tests, or provider rejection tests, not active product publishing paths.
- Live Feishu verification was not run during this deterministic closeout because `INSIGHTFLOW_FEISHU_LIVE=1` and `LARK_CLI_BIN=lark-cli` were not explicitly set in the local environment.

### P36-H5: Feishu Report Tables And PNG Chart Publish Repair

Make the real Feishu document match the useful parts of the Report Center report:正文、证据表格、图表快照、行动建议和数据边界.

Status: complete on 2026-07-08.

Observed issue:

- A live publish created a real Feishu document successfully; the link is intentionally omitted from source-controlled docs.
- Local report `report_2975094e` contained Markdown evidence tables in `report.md`, but `CliFeishuPublisher._package_to_markdown()` rebuilt a simplified Markdown body from package sections and omitted those tables.
- The same report had chart artifacts with `image_path` ending in `.svg`; `static_assets` therefore had `format: "svg"`, so `_collect_chart_image_assets()` counted them as failed/unsupported and no `docs +media-insert` call ran.
- The frontend publish result showed chart counts but warning text was filtered away because the warning wording contained command-like terms such as `media insert` / `insert`.

Design:

```text
ReportRecord
-> build_report_export_package()
-> Feishu markdown renderer uses existing full report content plus evidence tables
-> chart static export prepares Feishu-safe PNG files from ECharts/chart artifacts
-> CliFeishuPublisher docs +create with complete Markdown
-> CliFeishuPublisher docs +media-insert with local PNG/JPEG/GIF files
-> safe publish result shows link, inserted/failed chart counts, and user-readable warnings
```

Implementation requirements:

- Keep publishing a delivery-only path. Do not call the LLM, regenerate reports, execute SQL, recalculate evidence, or stitch Analysis Workbench answers.
- Replace the simplified Feishu Markdown body with a renderer that preserves report structure and appends business-readable evidence tables from the existing export package / `ReportEvidencePack.tables`.
- Render tables as Markdown tables so Feishu Docs imports them as document tables. Escape cell pipes/newlines, cap very large tables to a small business-readable preview, and add a note such as `仅展示前 N 行` when truncated.
- Keep table content evidence-bound: table titles, descriptions, columns, and rows must come from existing report/evidence package data, not from model-written prose.
- Generate PNG chart fallbacks from existing chart artifacts before publishing. Prefer rendering from `echarts_option` so the PNG visually matches the InsightFlow ECharts chart as closely as practical; if that is not available, convert safe existing SVG to PNG. Do not introduce matplotlib-style template charts as the primary Feishu path.
- Update `static_assets` / chart artifacts so Feishu publishing sees local `png` assets first, while preserving SVG/ECharts artifacts for web display and Markdown/legacy fallback.
- Keep `CliFeishuPublisher` strict: only local workspace-root-safe PNG/JPEG/GIF files are inserted. SVG, URL-only, missing, and unsafe assets remain warnings, never fake successes.
- Make warning messages user-readable and safe, for example `图表「收入结构图表」当前只有 SVG 静态图，飞书文档发布需要 PNG/JPEG/GIF，已跳过。` Avoid command names, raw local paths, stdout/stderr, token-like text, SQL, trace, provider metadata, or prompt/debug text.
- Frontend should display the safe warnings and chart counts. If a warning is filtered for safety, preserve a generic safe summary such as `部分图表未插入飞书文档。`
- Do not add Feishu Sheets/Base chart object creation in this repair. A later phase can create companion Feishu Sheets with editable chart data and native sheet charts, but P36-H5 focuses on making Feishu Docs reports complete.
- Delete or replace old simplified publishing helpers that conflict with the complete report path. Do not keep parallel “simple Markdown” and “full Markdown” active paths unless the simple path is only a private test fixture.

Suggested tests:

- `tests/test_feishu_publisher.py`
  - publishing Markdown includes evidence tables from the export package;
  - table cells escape pipes/newlines and large tables are capped with a truncation note;
  - SVG-only chart assets produce safe visible warnings;
  - PNG chart assets produce `docs +media-insert` calls.
- `tests/test_chart_static_export.py` or a focused P36 test
  - ECharts chart artifact can produce/reuse a local PNG fallback for Feishu publishing;
  - SVG remains available for web/Markdown fallback but does not become the preferred Feishu asset.
- `tests/test_workspace_report_api.py`
  - API publish persists safe warnings and chart insertion counts after PNG/SVG mixed assets.
- `frontend/tests/workspace-flow.test.tsx`
  - Report detail displays safe Feishu warnings and chart counts without raw command/tool-call metadata.
- Optional live verification after local auth:

```bash
INSIGHTFLOW_FEISHU_LIVE=1 LARK_CLI_BIN=/tmp/insightflow-lark-cli/node_modules/.bin/lark-cli \
python3 -m pytest tests/test_feishu_live_publish.py -q -s
```

Suggested deterministic verification:

```bash
python3 -m pytest tests/test_feishu_publisher.py tests/test_workspace_report_api.py tests/test_chart_static_export.py -q
cd frontend && npm test -- workspace-flow.test.tsx
cd frontend && npm run build
git diff --check
```

Result:

- `p34.export_package.v1` report packages now carry sanitized `evidence_tables` projected from existing `ReportEvidencePack.tables`.
- `CliFeishuPublisher._package_to_markdown()` now renders one complete Feishu Markdown body with title, metadata, opening summary, sections, section evidence tables, chart captions, action recommendations, and data boundaries. It escapes table pipes/newlines, truncates large evidence tables to 10 rows with an explicit preview note, and keeps raw SQL, raw rows, trace, provider metadata, prompts, tokens, and local absolute paths out of the body.
- Feishu publish API now requests PNG-target static chart assets from the existing chart artifacts/ECharts options before calling the publisher. Default chart static export behavior remains SVG-compatible for Word/Markdown/web fallback, while the Feishu target can reuse existing PNG/JPEG/GIF or generate a local PNG under `exports/charts/`.
- `CliFeishuPublisher` still inserts only workspace-root-safe local PNG/JPEG/GIF files. SVG-only, URL-only, missing, unsafe, or unsupported assets produce user-readable safe warnings such as `图表「收入结构图表」当前没有可插入的 PNG/JPEG/GIF 文件，已跳过。`
- Report Center UI keeps showing the Feishu link plus inserted/failed chart counts and safe warnings. If every detailed warning is filtered, the UI now shows `部分图表未插入飞书文档。` instead of hiding the issue.
- The publish path remains delivery-only: it consumes existing reports/export packages, does not call the report composer provider, does not execute SQL, does not rerun Report Runner, does not rewrite report conclusions, and does not stitch Analysis Workbench answers into reports.
- Deterministic verification passed: `python3 -m pytest tests/test_feishu_publisher.py tests/test_workspace_report_api.py tests/test_chart_static_export.py -q` (`54 passed`), `python3 -m pytest tests/test_export_package.py tests/test_document_export.py -q` (`17 passed`), and `cd frontend && npm test -- workspace-flow.test.tsx` (`66 passed`). Live Feishu verification was not run in this repair pass.

### P36-H6: Feishu Document Layout And In-Context Chart Placement

Make the real Feishu document read like a polished business report, not a Markdown dump with chart images appended at the bottom.

Status: complete on 2026-07-09.

Observed issue from live readback:

- A real Feishu document was successfully created and chart images were uploaded.
- The document body contained the report title, summary, business sections, evidence tables, chart bullet list, recommendations, and data boundaries.
- The uploaded chart images appeared after the main content instead of under the matching report sections such as `收入结构` or `趋势变化`.
- Evidence tables rendered as `### 证据表：...`, causing the Feishu left outline to become noisy.
- The Feishu document title and the Markdown body both showed the same report title, making the top of the document feel duplicated.
- Some metadata exposed technical table names such as `customers_客户资料` in a prominent line, which is useful for traceability but not ideal for the main reading surface.

Target Feishu reading structure:

```text
Feishu document title: 最近90天趋势变化报告

摘要
经营概览
  数据概览证据表
收入结构
  收入结构证据表
  收入结构图表
趋势变化
  趋势变化证据表
  趋势变化图表
行动建议
数据边界
```

Implementation requirements:

- Keep Feishu publishing as a delivery-only path. Do not call the LLM, run SQL, re-plan reports, rewrite report prose, invent sections, regenerate chart data, or stitch Analysis Workbench answers.
- Project the existing `ReportDocument` / `p34.export_package.v1` into Feishu-friendly Markdown with a document-body mode:
  - the Feishu document title stays in `docs +create --title`;
  - the Markdown body should not repeat the same top-level `# <title>` heading;
  - metadata should be business-readable, e.g. `时间范围：最近90天` and `数据来源：订单、客户、营销投放、客服反馈`; raw table names can move to a collapsed/appendix-style technical note only if already available and safe.
- Render evidence tables close to the report section that owns them, but avoid polluting the Feishu outline:
  - use `**证据表：收入结构**` or another body-level label instead of `### 证据表：收入结构`;
  - keep Markdown tables evidence-bound and capped as in H5;
  - preserve table escaping/truncation and raw SQL/trace/provider/local-path filtering.
- Add stable chart placement anchors in the Markdown body for each chart artifact, for example:

```markdown
**图表：收入结构图表**

下图展示收入结构图表，请结合正文和证据表解读。
```

- Insert chart images at their matching anchor with `lark-cli docs +media-insert --selection-with-ellipsis <anchor text>` when the CLI supports it. The active path should place images in context, not append every chart to the end of the document.
- If a matching anchor cannot be found or the CLI insertion fails, keep document creation successful but return a safe warning such as `图表「收入结构图表」未能插入到对应章节，请在飞书文档中手动调整。` Do not expose command stderr, local paths, SQL, trace, provider metadata, prompts, tokens, or debug text.
- Remove or replace old active helper paths that only create a simplified body or append chart images globally. A fallback may exist only as a small private test fixture or explicit failure/warning boundary, not as the normal publish behavior.
- Keep chart image file safety from H5: only workspace-root-safe relative PNG/JPEG/GIF files are eligible for insertion.
- Keep Report Center UI unchanged unless needed to surface the safer placement warnings. Do not add a new report type selector or new external platform UI in H6.

Suggested tests:

- `tests/test_feishu_publisher.py`
  - Feishu Markdown body omits the duplicate top-level title while preserving summary and sections;
  - evidence table labels are body labels, not `###` headings;
  - chart anchors appear under the matching section text;
  - `docs +media-insert` commands include `--selection-with-ellipsis` with the matching chart anchor and a relative `--file`;
  - failed anchor insertion returns a safe warning and does not leak raw command output or local paths.
- `tests/test_workspace_report_api.py`
  - persisted `external_publish_results.feishu` keeps inserted/failed chart counts and safe placement warnings after publish;
  - publish still does not call the LLM, execute SQL, rerun Report Runner, or mutate the stored `ReportDocument`.
- Optional frontend test only if warning rendering changes:
  - `frontend/tests/workspace-flow.test.tsx` shows safe chart placement warnings without raw tool details.

Suggested deterministic verification:

```bash
python3 -m pytest tests/test_feishu_publisher.py tests/test_workspace_report_api.py -q
python3 -m pytest tests/test_chart_static_export.py tests/test_export_package.py -q
cd frontend && npm test -- workspace-flow.test.tsx
git diff --check
```

Result:

- `CliFeishuPublisher._package_to_markdown()` no longer writes a duplicate `# <report title>` heading. Feishu Docs owns the title through `docs +create --title`, while the Markdown body starts with business-readable metadata such as `时间范围：最近90天` and normalized source labels such as `数据来源：订单、客户、营销投放`.
- Evidence tables still come only from existing `ReportDocument` / `p34.export_package.v1` `evidence_tables`. They remain section-local, escaped, and row-capped, but their visible label is now body text such as `**证据表：渠道收入证据表**` instead of `### 证据表：...`, so they do not flood the Feishu outline.
- Chart anchors now render in the matching report section as `**图表：收入结构图表**` plus a readable chart note such as `下图展示收入结构图表，请结合正文和证据表解读。`. The active media command now uses the confirmed local CLI argument `--selection-with-ellipsis 图表：<title>`, so PNG/JPEG/GIF assets are inserted beside their report section instead of being globally appended to the document bottom.
- The post-H6 live readback repair keeps section/chart linkage stable through the whole export path: `build_report_export_package()` now preserves `chart_id`, `chart_ids`, and `source_chapter_id` by merging existing `ReportEvidencePack.charts` metadata into exported chart artifacts, and `CliFeishuPublisher` matches section `chart_refs` against those chart aliases. This prevents valid report charts from falling back into the catch-all `图表说明` section when a stored artifact id is wrapped as `artifact_chart_<chart_id>`.
- The old active append-only chart insertion path was replaced rather than kept in parallel. Unmapped chart assets get an explicit `图表说明` anchor section, and insertion failures keep the document link while returning a safe warning such as `图表「收入结构图表」未能插入到对应章节，请在飞书文档中手动调整。`
- The publish path remains delivery-only: it consumes the existing report export package, does not call the LLM, does not execute SQL, does not rerun Report Runner, does not regenerate chart data, does not rewrite report prose, and does not publish Analysis Workbench answers as reports.
- Deterministic verification passed on 2026-07-09: `python3 -m pytest tests/test_feishu_publisher.py tests/test_workspace_report_api.py tests/test_chart_static_export.py tests/test_export_package.py -q` (`66 passed`). Earlier H6 frontend verification also passed with `cd frontend && npm test -- workspace-flow.test.tsx` (`66 passed`). Live Feishu verification was not run in this repair pass.

Suggested live verification after local Feishu CLI auth:

```bash
LARK_CLI_BIN=/Users/zhangzihao/Desktop/Multi-Agent\ Project/tmp/lark-cli-tools/node_modules/.bin/lark-cli \
python3 -m pytest tests/test_feishu_live_publish.py -q -s
```

Manual live acceptance should create one fresh report, publish it to Feishu, fetch/read the Feishu document back, and verify:

- evidence tables appear near their matching sections;
- chart images appear immediately under their matching chart anchors, not all appended after `数据边界`;
- the left outline is readable and not dominated by `证据表：...` headings;
- the document does not duplicate the report title at the top;
- warnings are safe and useful if a chart cannot be placed.

### P36-H7: Feishu Sheet Companion For Editable Evidence And Native Charts

Add an optional hybrid publishing mode: keep the polished Feishu Doc as the primary reading surface, and create a companion Feishu Sheet from the same report evidence so users can inspect editable data tables and native Feishu charts.

Status: complete on 2026-07-09.

Result:

- Added `workspaces.feishu_sheet_publisher.CliFeishuSheetPublisher` plus `SheetPublishResult`, `SheetTableWriteResult`, `SheetChartCreateResult`, and a `FeishuSheetPublisher` protocol.
- The Sheet companion uses only `p34.export_package.v1`: `evidence_tables` become workbook tabs/ranges, and `chart_artifacts` become native Feishu sheet charts only for simple bar/line mappings with clear category and numeric value columns.
- The CLI path uses `lark-cli sheets +workbook-create`, `sheets +table-put`, and `sheets +chart-create`; command results are summarized without stdout/stderr, local paths, SQL, trace, provider metadata, prompts, credentials, or raw command output.
- `CliFeishuPublisher` can receive a companion Sheet publisher. When the Sheet exists, the Feishu Doc body gets one concise `## 可编辑数据和图表` link section. If the Sheet fails, the Doc publish continues as `warning` with safe Sheet warnings and no fake link.
- `ExternalPublishResult` now safely carries optional `sheet_url`, `sheet_id`, `spreadsheet_token`, `written_table_count`, `native_chart_count`, and `sheet_warnings`. Empty Sheet fields are omitted from no-Sheet safe results.
- Report Center publish API persists the safe Sheet fields under `external_publish_results.feishu`, and the frontend displays the Doc link, optional Sheet link, written table count, native chart count, and filtered warnings.
- H7 did not call the LLM, execute SQL, rerun Report Runner, rewrite reports, query databases for Sheet export, invent chart data, or restore old mock/action/fake-success connector paths.
- Deterministic verification passed: `python3 -m pytest tests/test_feishu_sheet_publisher.py tests/test_feishu_publisher.py tests/test_workspace_report_api.py -q` (`54 passed`), `python3 -m pytest tests/test_export_package.py tests/test_chart_static_export.py -q` (`19 passed`), `cd frontend && npm test -- workspace-flow.test.tsx` (`66 passed`), `cd frontend && npm run build`, and `git diff --check`. Live Feishu verification was not run in this pass.

Why this is needed:

- The current Feishu Doc path now works: it publishes a readable report with section-local evidence tables and in-context PNG/JPEG/GIF chart snapshots.
- Static images are best for report reading, but they are not editable inside Feishu.
- `lark-cli sheets` supports workbook creation, table/cell writes, and native chart creation through commands such as `sheets +workbook-create`, `sheets +table-put`, and `sheets +chart-create`.
- The product should test a hybrid route before switching to a Sheet-first route: Feishu Docs remains the business report, while Feishu Sheets becomes the editable data/chart appendix.

Target product behavior:

```text
User clicks 发布到飞书
-> existing Feishu Doc report is created from ReportDocument/export package
-> existing static chart images are inserted beside matching report sections
-> optional companion Feishu Sheet workbook is created
-> report evidence tables are written into Feishu Sheet tabs/ranges
-> native Feishu sheet charts are created from safe chart artifact/evidence data when possible
-> Feishu Doc receives a business-readable appendix link such as:
   可编辑数据表和图表：打开飞书表格
-> Report Center shows both the Feishu Doc link and, when available, the companion Sheet link
```

Implementation requirements:

- Keep the publish path delivery-only. Do not call the LLM, execute SQL, rerun Report Runner, rewrite report prose, regenerate chart data, or stitch Analysis Workbench output.
- Build the companion workbook only from existing `p34.export_package.v1` fields:
  - `evidence_tables` for sheet tables;
  - `chart_artifacts`, `static_assets`, `evidence_refs`, `chart_id` / `chart_ids`, and section ownership metadata for chart mapping;
  - report title/time range/source labels for workbook naming and a summary tab.
- Add a small, focused Sheets publisher boundary rather than mixing workbook logic into `CliFeishuPublisher` document code. Suggested shape:

```text
workspaces/feishu_sheet_publisher.py
-> FeishuSheetPublisher protocol
-> CliFeishuSheetPublisher
-> SheetPublishResult
-> command runner reuse or shared CLI command helper
```

- Use `lark-cli sheets` shortcuts when possible:
  - `sheets +workbook-create` to create the workbook;
  - `sheets +table-put` or `sheets +csv-put` to write each evidence table;
  - `sheets +chart-create` to create native charts only when the chart artifact has enough safe tabular data to map x-axis, y-axis, title, chart type, and source range.
- Do not try to embed live ECharts JavaScript into Feishu. InsightFlow UI keeps interactive ECharts; Feishu Doc gets static chart images; Feishu Sheet gets native sheet charts where possible.
- Chart creation must be conservative:
  - create native sheet charts only for simple bar/line/table-compatible chart artifacts with clear category and numeric value columns;
  - if chart mapping is ambiguous, skip native chart creation and add a safe warning such as `图表「收入结构图表」缺少可映射的分类列或数值列，已仅发布数据表。`;
  - never let the model generate chart ranges, formulas, or chart config.
- The Feishu Doc should not become cluttered. Add one concise appendix/link section, not duplicate every Sheet table back into the Doc.
- The frontend should display:
  - Feishu Doc link;
  - companion Sheet link if created;
  - written table count;
  - created native chart count;
  - safe warnings for skipped charts/tables.
- Result persistence should extend the safe external publish result without leaking raw CLI output, local absolute paths, SQL, trace, provider metadata, prompts, tokens, database paths, or generated file paths.
- If Sheet creation fails after the Doc succeeds, keep the Doc publish successful with a warning. Do not roll back the Feishu Doc.
- If the CLI lacks auth or the sheet command fails, return a safe actionable warning; do not fake a Sheet URL.
- Delete or replace any old helper that tries to make Feishu Sheet data by querying the database directly. The only allowed data source is the export package.

Suggested implementation slices:

1. **Sheets publisher contract and command mapping**
   - Add `workspaces/feishu_sheet_publisher.py`.
   - Add tests with a fake command runner for workbook create, table write, chart create, CLI failure, and safe warning normalization.
   - Prefer reusing existing command-runner patterns from `workspaces/feishu_publisher.py` without duplicating sanitization logic.

2. **Export package to Sheet workbook projection**
   - Add a small projector that converts `evidence_tables` into sheet-safe tabs/ranges and chart artifacts into conservative native chart requests.
   - Keep all table/chart data evidence-bound and capped where necessary.
   - Add tests proving no raw SQL, raw rows beyond intended evidence preview, trace paths, provider metadata, local paths, or token-like strings appear in the result.

3. **Publish API and UI integration**
   - Extend `POST /api/workspaces/{workspace_id}/reports/{report_id}/publish/feishu` to optionally request the companion Sheet after the Doc is created.
   - Persist `sheet_url`, `sheet_id`, table count, native chart count, and safe warnings under `external_publish_results.feishu`.
   - Update Report Center UI to show the Sheet link and counts without adding a separate report type selector or changing the report-generation path.

4. **Acceptance and live check**
   - Run deterministic backend/frontend tests.
   - If local auth is configured, publish one fresh report to real Feishu and verify:
     - Doc still has in-context static chart images;
     - Doc has a concise editable-data appendix link;
     - Sheet contains evidence tables;
     - native sheet charts are created when safe;
     - skipped charts show safe warnings.

Suggested tests:

- `tests/test_feishu_sheet_publisher.py`
  - workbook creation command is built through `lark-cli sheets +workbook-create`;
  - evidence tables are written to safe sheet ranges;
  - simple chart artifact creates a native sheet chart command;
  - ambiguous chart artifact is skipped with a safe warning;
  - command failures do not leak stdout/stderr, local paths, tokens, SQL, trace, or provider metadata.
- `tests/test_feishu_publisher.py`
  - document publishing can include a companion sheet link section without duplicating all sheet data in the document body;
  - Doc publish success remains success/warning if companion Sheet creation fails.
- `tests/test_workspace_report_api.py`
  - `external_publish_results.feishu` persists safe `sheet_url`, counts, and warnings.
- `frontend/tests/workspace-flow.test.tsx`
  - Report detail displays the Feishu Sheet link and table/chart counts safely.

Suggested deterministic verification:

```bash
python3 -m pytest tests/test_feishu_sheet_publisher.py tests/test_feishu_publisher.py tests/test_workspace_report_api.py -q
python3 -m pytest tests/test_export_package.py tests/test_chart_static_export.py -q
cd frontend && npm test -- workspace-flow.test.tsx
git diff --check
```

Optional live verification:

```bash
INSIGHTFLOW_FEISHU_LIVE=1 \
LARK_CLI_BIN=/Users/zhangzihao/Desktop/Multi-Agent\ Project/tmp/lark-cli-tools/node_modules/.bin/lark-cli \
python3 -m pytest tests/test_feishu_live_publish.py -q -s
```

H7 acceptance criteria:

- Existing Feishu Doc publishing still works and remains the primary report reading surface.
- A companion Feishu Sheet can be created from the same export package when requested/enabled.
- Evidence tables are editable in the Feishu Sheet.
- Native Feishu sheet charts are created only when the chart artifact/evidence table can be mapped safely.
- The Feishu Doc contains a concise link to the companion Sheet.
- Report Center displays Doc URL, optional Sheet URL, table count, native chart count, and safe warnings.
- No extra LLM call, SQL execution, report rewrite, chart-data invention, old simulated connector, or database-direct Sheet export path is introduced.
- If the Sheet path fails, the Doc publish is preserved and the user sees a safe warning.

## Success Criteria

- A generated Report Center report can be published to a real Feishu document through `lark-cli`.
- The Feishu publish result is visible in Report Center with a working link.
- Safe chart static assets are inserted when available, with warnings when insertion is not possible.
- Feishu documents include business-readable evidence tables that already exist in the Report Center report, not only free-text sections.
- Feishu chart insertion prefers local PNG/JPEG/GIF assets generated from the same chart artifact/ECharts option used by the web UI.
- Feishu chart images are inserted near their matching report sections instead of being appended at the bottom.
- Optional companion Feishu Sheets can publish editable evidence tables and native sheet charts from the same export package when H7 is enabled.
- Feishu Docs keep a concise companion Sheet link rather than duplicating all Sheet content in the report body.
- Feishu document headings and outline remain readable: no duplicate body title and no noisy evidence-table heading flood.
- Publishing consumes existing report/export artifacts and does not rewrite report content.
- No simulated SaaS connector or fake-success path is introduced.
- No credentials, local absolute paths, raw SQL, raw rows, provider metadata, prompt text, trace paths, or generated artifacts are exposed in user-facing publish results.
- Deterministic tests pass.
- Live Feishu verification is opt-in and skipped clearly when credentials/CLI/auth are unavailable.
- Old conflicting paths are deleted or kept only as historical/superseded documentation and negative tests.

## Notes For Future P37+

- A direct Feishu OpenAPI publisher can replace `CliFeishuPublisher` behind the same `FeishuPublisher` interface.
- After P36-H7 live testing, decide whether the hybrid Doc + Sheet route should become the default or whether a later Sheet-first publishing model is worth building. Keep Feishu Docs as the primary reading surface until real users prefer editable Sheets as the main artifact.
- PPT/PDF/Tencent Docs/DingTalk/WeCom publishing should reuse the same `ExportPackage -> publisher` boundary rather than inventing new report-generation paths.
- If later product requirements need interactive charts inside a web page, keep that in InsightFlow UI. External document platforms should receive static chart exports unless they explicitly support safe embedded interactive content.
