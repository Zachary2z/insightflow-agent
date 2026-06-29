# P14 Product UI Shell And Business Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the P13 working product into a coherent Chinese business data-analysis web product whose Next.js UI matches the clickable P14 prototype and supports a realistic data-to-question-to-answer-to-report workflow.

**Architecture:** P14 keeps the existing FastAPI, workspace, guarded SQL, report, artifact, and live DeepSeek/provider-backed runtime. The main work is frontend productization: formalize a shared product shell and design tokens, then migrate workspace pages into the same navigation, spacing, card, status, and Chinese copy system. Backend changes are limited to small product-facing metadata endpoints only if the frontend cannot derive readiness from existing APIs.

**Tech Stack:** Next.js App Router, React, TypeScript, Vitest, Testing Library, FastAPI, pytest, existing workspace APIs, existing live DeepSeek opt-in tests.

---

## Reference Inputs

- Primary prototype: `docs/product/prototypes/p14-clickable-product-ui.html`
- P13 design spec: `docs/superpowers/specs/2026-06-24-p13-business-answer-product-ux-design.md`
- P13 implementation plan: `docs/superpowers/plans/2026-06-24-p13-business-answer-product-ux-implementation-plan.md`
- Current frontend app routes: `frontend/app/workspaces/**`
- Current frontend components: `frontend/components/**`
- Current frontend tests: `frontend/tests/workspace-flow.test.tsx`, `frontend/tests/api-client.test.ts`

## Product Scope

P14 is not a backend-agent rewrite. P14 is the product UI and workflow hardening phase that makes the current product feel like one coherent application.

### In Scope

- Promote the clickable P14 HTML prototype into the source-of-truth visual reference.
- Replace the fragmented workspace navigation with one reusable Chinese product shell.
- Redesign the Next.js workspace pages to match the prototype:
  - 数据源管理
  - 分析工作台
  - 报告中心
  - 数据设置
  - 业务问答 preview
- Keep real model mode and guarded execution visible as product status, not developer flags.
- Preserve P11/P12/P13 backend behavior and live DeepSeek acceptance.
- Add frontend tests that assert user-facing Chinese product copy and navigation flows.
- Keep generated files, workspace runs, reports, charts, traces, `.env`, and local prototype leftovers out of commits.

### Out Of Scope

- Real SaaS integrations such as Slack, Jira, Power BI, Notion, email, CRM, or ticketing systems.
- Auth/RBAC.
- Deployment.
- PDF/PPT export.
- Scheduled reports.
- Replacing the guarded SQL, evidence, visualization, report, or trace boundaries.
- Restoring Streamlit, old ecommerce-only UI, old eval UI, old `chart_agent`, old `visualization_planner`, or old `chart_tool`.

## File Structure

### Create

- `frontend/components/ProductShell.tsx`
  - Shared product shell for workspace pages: brand, workspace switcher label, model status, horizontal navigation, and content container.
- `frontend/components/ProductPageHeader.tsx`
  - Shared page hero/header with eyebrow, title, description, and optional action.
- `frontend/components/ProductCard.tsx`
  - Shared product card wrapper and variants.
- `frontend/components/ProductStatus.tsx`
  - Shared status pill, metric card, readiness row, and compact status helpers.
- `frontend/components/BusinessQAPreview.tsx`
  - Non-backend chat-style preview that reuses product language and links back to the Analysis Workbench.
- `frontend/app/workspaces/[workspaceId]/business-qa/page.tsx`
  - Future-compatible Business Q&A preview route. It must be visibly marked as preview and must not pretend to be a complete chat product.
- `frontend/tests/product-shell.test.tsx`
  - Focused tests for shell navigation, active route labels, Chinese copy, and preview route behavior.

### Modify

- `frontend/app/globals.css`
  - Add or consolidate product design tokens, layout utilities, product shell styles, card styles, horizontal navigation, responsive behavior.
- `frontend/app/workspaces/page.tsx`
  - Chinese product copy and clearer workspace entry.
- `frontend/app/workspaces/new/page.tsx`
  - Chinese create-workspace flow.
- `frontend/app/workspaces/[workspaceId]/datasets/page.tsx`
  - Rename and redesign as 数据源管理.
- `frontend/app/workspaces/[workspaceId]/analysis/page.tsx`
  - Wrap in `ProductShell`, align title/copy with prototype, remove old page-level link strip.
- `frontend/app/workspaces/[workspaceId]/reports/page.tsx`
  - Wrap in `ProductShell`, align with 报告中心.
- `frontend/app/workspaces/[workspaceId]/reports/[reportId]/page.tsx`
  - Wrap in `ProductShell`, keep report reader business-first.
- `frontend/app/workspaces/[workspaceId]/settings/page.tsx`
  - Wrap in `ProductShell`, align with 数据设置.
- `frontend/app/workspaces/[workspaceId]/profile/page.tsx`
  - Keep accessible, but link as supporting setup page rather than primary nav.
- `frontend/app/workspaces/[workspaceId]/semantic-layer/page.tsx`
  - Keep accessible, but link as supporting setup page rather than primary nav.
- `frontend/app/workspaces/[workspaceId]/runs/[runId]/page.tsx`
  - Wrap in product shell and keep technical details clearly secondary.
- `frontend/components/DatasetManager.tsx`
  - Replace old English form labels with product Chinese copy and card structure.
- `frontend/components/AnalysisRunner.tsx`
  - Align question input, analysis thread, and result sections with prototype layout.
- `frontend/components/AnalysisThreadCard.tsx`
  - Make the compact integrated thread match the prototype: 用户问题, 系统理解, 追问, 用户补充, 整理后.
- `frontend/components/RunResult.tsx`
  - Keep business answer first; SQL/raw rows remain collapsed.
- `frontend/components/ReportGenerator.tsx`
  - Chinese business report generation copy.
- `frontend/components/ReportList.tsx`
  - Product report list styling and Chinese status labels.
- `frontend/components/ReportViewer.tsx`
  - Preserve business report reader; align shell and header.
- `frontend/components/DataSettings.tsx`
  - Align section labels with 数据源, 字段画像, 语义层, 模型模式, 安全与审计.
- `frontend/components/WorkspaceList.tsx`
  - Chinese product copy and primary entry button.
- `frontend/components/WorkspaceNewForm.tsx`
  - Chinese form labels and success/error copy.
- `frontend/tests/workspace-flow.test.tsx`
  - Update assertions from old English copy to P14 Chinese product copy.

### Do Not Modify Unless A Test Proves It Is Necessary

- `api/app.py`
- `workspaces/analysis_runner.py`
- `workspaces/report_runner.py`
- `graph/nodes.py`
- `graph/workflow.py`
- `llm_ops/**`
- `agents/**`

## Task P14-H1: Prototype Reference And Planning Closeout

**Files:**
- Create/keep: `docs/product/prototypes/p14-clickable-product-ui.html`
- Create: `docs/product/plans/2026-06-29-p14-product-ui-shell-and-business-workflow.md`
- Modify: `DEVELOPMENT_PLAN.md`
- Modify: `DEVELOPMENT_STATUS.md`

- [ ] **Step 1: Confirm the prototype is tracked in a non-ignored docs path**

Run:

```bash
test -f docs/product/prototypes/p14-clickable-product-ui.html
git check-ignore -v docs/product/prototypes/p14-clickable-product-ui.html || true
```

Expected: the file exists and `git check-ignore` prints no ignore rule.

- [ ] **Step 2: Verify the prototype contains the required navigable views**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
text = Path("docs/product/prototypes/p14-clickable-product-ui.html").read_text(encoding="utf-8")
required = [
    "数据源管理",
    "分析工作台",
    "报告中心",
    "数据设置",
    "业务问答模式",
    "data-page-target=\"sources\"",
    "data-page-target=\"workbench\"",
    "data-page-target=\"reports\"",
    "data-page-target=\"settings\"",
    "data-page-target=\"qa\"",
]
missing = [item for item in required if item not in text]
if missing:
    raise SystemExit("missing prototype markers: " + ", ".join(missing))
print("prototype reference passed")
PY
```

Expected: `prototype reference passed`.

- [ ] **Step 3: Update phase docs**

Record P14 as the active phase in `DEVELOPMENT_PLAN.md` and `DEVELOPMENT_STATUS.md`. The docs must say:

- P13 is complete.
- P14 is active.
- P14-H1 is the clickable product UI prototype and plan.
- P14-H2 is the next implementation task: shared Next.js product shell and design tokens.

- [ ] **Step 4: Run focused docs checks**

Run:

```bash
rg -n "P14|p14-clickable-product-ui|Product UI Shell|Business Q&A|业务问答|数据源管理|分析工作台|报告中心|数据设置" DEVELOPMENT_PLAN.md DEVELOPMENT_STATUS.md docs/product/prototypes/p14-clickable-product-ui.html docs/product/plans/2026-06-29-p14-product-ui-shell-and-business-workflow.md
```

Expected: hits in the plan, status, development plan, and prototype.

- [ ] **Step 5: Commit H1**

Run:

```bash
git add DEVELOPMENT_PLAN.md DEVELOPMENT_STATUS.md docs/product/prototypes/p14-clickable-product-ui.html docs/product/plans/2026-06-29-p14-product-ui-shell-and-business-workflow.md
git commit -m "docs: plan p14 product ui shell"
```

## Task P14-H2: Shared Product Shell And Design Tokens

**Files:**
- Create: `frontend/components/ProductShell.tsx`
- Create: `frontend/components/ProductPageHeader.tsx`
- Create: `frontend/components/ProductCard.tsx`
- Create: `frontend/components/ProductStatus.tsx`
- Create: `frontend/tests/product-shell.test.tsx`
- Modify: `frontend/app/globals.css`
- Modify: `frontend/app/workspaces/[workspaceId]/analysis/page.tsx`
- Modify: `frontend/app/workspaces/[workspaceId]/datasets/page.tsx`
- Modify: `frontend/app/workspaces/[workspaceId]/reports/page.tsx`
- Modify: `frontend/app/workspaces/[workspaceId]/settings/page.tsx`

- [ ] **Step 1: Write failing shell tests**

Create `frontend/tests/product-shell.test.tsx` with tests that render `ProductShell` around sample content and assert:

- brand text `InsightFlow`
- workspace label
- model status `真实模型已开启`
- horizontal nav labels `数据源管理`, `分析工作台`, `报告中心`, `数据设置`, `业务问答`
- active nav state can be identified with `aria-current="page"`

Run:

```bash
cd frontend && npm test -- product-shell.test.tsx
```

Expected before implementation: fail because `ProductShell` does not exist.

- [ ] **Step 2: Implement product shell components**

Create focused components with these public interfaces:

```tsx
// frontend/components/ProductShell.tsx
export type ProductShellProps = {
  workspaceId: string;
  active: "sources" | "analysis" | "reports" | "settings" | "business-qa";
  children: React.ReactNode;
};
```

```tsx
// frontend/components/ProductPageHeader.tsx
export type ProductPageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
};
```

```tsx
// frontend/components/ProductCard.tsx
export type ProductCardProps = {
  children: React.ReactNode;
  className?: string;
};
```

```tsx
// frontend/components/ProductStatus.tsx
export type StatusPillProps = {
  children: React.ReactNode;
  tone?: "green" | "orange" | "blue" | "neutral";
};
```

- [ ] **Step 3: Add CSS tokens and shell styles**

Modify `frontend/app/globals.css` to add the product-shell classes used by the components. Mirror the prototype structure:

- `product-shell`
- `product-topbar`
- `product-nav`
- `product-nav-list`
- `product-nav-link`
- `product-page`
- `product-page-header`
- `product-card`
- `status-pill`
- responsive behavior for smaller screens

- [ ] **Step 4: Wrap four primary routes**

Update these pages to use `ProductShell` and `ProductPageHeader`:

- `frontend/app/workspaces/[workspaceId]/datasets/page.tsx`
- `frontend/app/workspaces/[workspaceId]/analysis/page.tsx`
- `frontend/app/workspaces/[workspaceId]/reports/page.tsx`
- `frontend/app/workspaces/[workspaceId]/settings/page.tsx`

Remove old page-level link strips from these routes. The reusable shell owns primary navigation.

- [ ] **Step 5: Run focused frontend tests**

Run:

```bash
cd frontend && npm test -- product-shell.test.tsx workspace-flow.test.tsx
```

Expected: all focused frontend tests pass.

- [ ] **Step 6: Build frontend**

Run:

```bash
cd frontend && npm run build
```

Expected: Next.js production build passes and includes workspace routes.

- [ ] **Step 7: Commit H2**

Run:

```bash
git add frontend/app frontend/components frontend/tests
git commit -m "feat: add p14 product shell"
```

## Task P14-H3: Data Source Management Redesign

**Files:**
- Modify: `frontend/app/workspaces/[workspaceId]/datasets/page.tsx`
- Modify: `frontend/components/DatasetManager.tsx`
- Modify: `frontend/tests/workspace-flow.test.tsx`

- [ ] **Step 1: Write failing tests for Chinese data source page copy**

In `frontend/tests/workspace-flow.test.tsx`, update the DatasetManager test to assert:

- `数据源管理`
- `上传 CSV / Excel`
- `导入 SQLite`
- `已导入数据源`
- imported rows still show `orders.csv`, `customers.csv`, and imported table names when mocked

Run:

```bash
cd frontend && npm test -- workspace-flow.test.tsx
```

Expected before implementation: fail on old English labels.

- [ ] **Step 2: Redesign DatasetManager copy and layout**

Update `DatasetManager.tsx` so the page behaves like the prototype:

- primary card: upload file
- secondary action: SQLite import
- table/list: imported data sources
- readiness sidebar or inline readiness summary
- no raw developer wording such as `Upload source` as primary visible copy

- [ ] **Step 3: Run focused frontend tests**

Run:

```bash
cd frontend && npm test -- workspace-flow.test.tsx
```

Expected: dataset tests pass with Chinese copy.

- [ ] **Step 4: Commit H3**

Run:

```bash
git add frontend/app/workspaces/[workspaceId]/datasets/page.tsx frontend/components/DatasetManager.tsx frontend/tests/workspace-flow.test.tsx
git commit -m "feat: redesign data source management"
```

## Task P14-H4: Analysis Workbench Redesign

**Files:**
- Modify: `frontend/app/workspaces/[workspaceId]/analysis/page.tsx`
- Modify: `frontend/components/AnalysisRunner.tsx`
- Modify: `frontend/components/WorkspaceReadinessHeader.tsx`
- Modify: `frontend/components/AnalysisThreadCard.tsx`
- Modify: `frontend/components/BusinessAnswerCard.tsx`
- Modify: `frontend/components/EvidencePanel.tsx`
- Modify: `frontend/components/ChartArtifactGallery.tsx`
- Modify: `frontend/components/TechnicalDetailsDisclosure.tsx`
- Modify: `frontend/tests/workspace-flow.test.tsx`

- [ ] **Step 1: Write failing tests for prototype workbench states**

In `frontend/tests/workspace-flow.test.tsx`, assert that the analysis flow renders:

- `分析工作台`
- `问一个业务问题`
- `分析线程`
- `用户问题`
- `系统理解`
- `追问`
- `用户补充`
- `整理后`
- `业务结论`
- `技术详情`

Run:

```bash
cd frontend && npm test -- workspace-flow.test.tsx
```

Expected before implementation: fail where old copy or layout is still present.

- [ ] **Step 2: Update workbench layout**

Update `AnalysisRunner.tsx` to match the prototype flow:

- workspace readiness card
- question input card
- integrated thread card
- business result first
- evidence and chart after the answer
- technical details collapsed

Keep the existing API calls and continuation behavior unchanged.

- [ ] **Step 3: Preserve live product behavior**

Run non-live focused tests:

```bash
python3 -m pytest tests/test_clarification_routing.py tests/test_p13_live_deepseek_product_acceptance.py -q
```

Expected: routing tests pass and live tests skip unless live flags are enabled.

- [ ] **Step 4: Run frontend focused tests**

Run:

```bash
cd frontend && npm test -- workspace-flow.test.tsx
```

Expected: analysis workbench tests pass.

- [ ] **Step 5: Commit H4**

Run:

```bash
git add frontend/app/workspaces/[workspaceId]/analysis/page.tsx frontend/components frontend/tests/workspace-flow.test.tsx
git commit -m "feat: redesign analysis workbench"
```

## Task P14-H5: Report Center Redesign

**Files:**
- Modify: `frontend/app/workspaces/[workspaceId]/reports/page.tsx`
- Modify: `frontend/app/workspaces/[workspaceId]/reports/[reportId]/page.tsx`
- Modify: `frontend/components/ReportGenerator.tsx`
- Modify: `frontend/components/ReportList.tsx`
- Modify: `frontend/components/ReportViewer.tsx`
- Modify: `frontend/components/ReportSection.tsx`
- Modify: `frontend/components/ReportTechnicalAppendix.tsx`
- Modify: `frontend/tests/workspace-flow.test.tsx`

- [ ] **Step 1: Write failing report-center copy tests**

Update report tests to assert:

- `报告中心`
- `新建报告`
- `管理层收入复盘`
- `生成状态`
- `执行摘要`
- `下载 Markdown`
- technical details remain outside the main report body

Run:

```bash
cd frontend && npm test -- workspace-flow.test.tsx
```

Expected before implementation: fail on old English labels or missing product layout.

- [ ] **Step 2: Redesign report list and generator**

Update `ReportGenerator.tsx` and `ReportList.tsx` so the route reads as a report center:

- report list first
- clear generation card
- Chinese report type labels
- status labels `已完成`, `生成中`, `失败`

- [ ] **Step 3: Redesign report reader**

Update `ReportViewer.tsx`, `ReportSection.tsx`, and `ReportTechnicalAppendix.tsx` so:

- business report body is first
- technical appendix remains collapsed
- generated chart images still display
- Markdown download remains visible

- [ ] **Step 4: Run report backend regressions**

Run:

```bash
python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_api.py tests/test_workspace_report_store.py -q
```

Expected: report backend regressions pass.

- [ ] **Step 5: Run frontend focused tests**

Run:

```bash
cd frontend && npm test -- workspace-flow.test.tsx
```

Expected: report UI tests pass.

- [ ] **Step 6: Commit H5**

Run:

```bash
git add frontend/app/workspaces/[workspaceId]/reports frontend/components/Report* frontend/tests/workspace-flow.test.tsx
git commit -m "feat: redesign report center"
```

## Task P14-H6: Data Settings Redesign

**Files:**
- Modify: `frontend/app/workspaces/[workspaceId]/settings/page.tsx`
- Modify: `frontend/components/DataSettings.tsx`
- Modify: `frontend/tests/workspace-flow.test.tsx`

- [ ] **Step 1: Write failing data-settings tests**

Update tests to assert:

- `数据设置`
- `数据源`
- `字段画像`
- `语义层`
- `模型模式`
- `安全与审计`
- `真实模型模式`
- `SQL 审核不可绕过`

Run:

```bash
cd frontend && npm test -- workspace-flow.test.tsx
```

Expected before implementation: fail where current English section copy remains.

- [ ] **Step 2: Redesign DataSettings sections**

Update `DataSettings.tsx` to keep the existing `getWorkspaceSettings()` API but present sections in the prototype order:

1. 数据源
2. 字段画像
3. 语义层
4. 模型模式
5. 安全与审计

- [ ] **Step 3: Run focused tests**

Run:

```bash
cd frontend && npm test -- workspace-flow.test.tsx
```

Expected: settings tests pass.

- [ ] **Step 4: Commit H6**

Run:

```bash
git add frontend/app/workspaces/[workspaceId]/settings/page.tsx frontend/components/DataSettings.tsx frontend/tests/workspace-flow.test.tsx
git commit -m "feat: redesign data settings"
```

## Task P14-H7: Business Q&A Preview Route

**Files:**
- Create: `frontend/components/BusinessQAPreview.tsx`
- Create: `frontend/app/workspaces/[workspaceId]/business-qa/page.tsx`
- Modify: `frontend/components/ProductShell.tsx`
- Modify: `frontend/tests/product-shell.test.tsx`
- Modify: `frontend/tests/workspace-flow.test.tsx`

- [ ] **Step 1: Write failing preview route tests**

Add tests that assert:

- `业务问答模式`
- `未来模式预览`
- chat-like messages render
- `打开工作台查看完整证据` links to `/workspaces/{workspaceId}/analysis`

Run:

```bash
cd frontend && npm test -- product-shell.test.tsx workspace-flow.test.tsx
```

Expected before implementation: fail because the route/component does not exist.

- [ ] **Step 2: Implement preview route**

Create `BusinessQAPreview.tsx` as a static, clearly labeled preview. It must not call a new backend endpoint. It should explain that this mode will reuse the same answer, evidence, chart, report, and progress objects.

- [ ] **Step 3: Add preview route to shell nav**

Update `ProductShell.tsx` so `业务问答` links to:

```text
/workspaces/{workspaceId}/business-qa
```

Use `active="business-qa"` for that route.

- [ ] **Step 4: Run focused frontend tests and build**

Run:

```bash
cd frontend && npm test -- product-shell.test.tsx workspace-flow.test.tsx
cd frontend && npm run build
```

Expected: tests and build pass, and Next.js build lists the business-qa route.

- [ ] **Step 5: Commit H7**

Run:

```bash
git add frontend/app/workspaces/[workspaceId]/business-qa frontend/components/BusinessQAPreview.tsx frontend/components/ProductShell.tsx frontend/tests
git commit -m "feat: add business qa preview"
```

## Task P14-H8: Full Product Regression And Live Acceptance

**Files:**
- Modify: `DEVELOPMENT_PLAN.md`
- Modify: `DEVELOPMENT_STATUS.md`
- Optional modify: `README.md`
- Test-only modify if needed: `tests/test_p13_live_deepseek_product_acceptance.py`

- [ ] **Step 1: Run full backend tests**

Run:

```bash
python3 -m pytest -q
```

Expected: all non-live backend tests pass.

- [ ] **Step 2: Run full frontend tests and build**

Run:

```bash
cd frontend && npm test
cd frontend && npm run build
```

Expected: all frontend tests pass and production build succeeds.

- [ ] **Step 3: Run real DeepSeek product acceptance**

Run:

```bash
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p13_live_deepseek_product_acceptance.py -q
```

Expected: live P13/P14 product acceptance passes with real DeepSeek provider calls.

- [ ] **Step 4: Run P11 and P12 live regressions**

Run:

```bash
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p11_live_deepseek_workspace_analysis.py -q

set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p12_live_deepseek_workspace_report.py -q
```

Expected: both live regressions pass.

- [ ] **Step 5: Run legacy and artifact audits**

Run:

```bash
rg -n "chart_agent|visualization_planner|chart_tool|streamlit run app.py|eval/run_eval.py|powerbi_publisher_mock|fixed template|deterministic action template|keyword inference" README.md DEVELOPMENT_PLAN.md DEVELOPMENT_STATUS.md api frontend graph agents workspaces tests

git ls-files | rg "(^\\.env$|frontend/\\.next/|(^|/)\\.pytest_cache/|(^|/)__pycache__/|^workspaces/.+/runs/|^workspaces/.+/reports/|^reports/charts/.+\\.(png|jpg|jpeg|svg)$|^reports/markdown/.+\\.(md|html|pdf)$|^logs/traces/.+\\.json$|^sample_data/)"
```

Expected: legacy hits are historical/test-boundary only; tracked generated-artifact check produces no generated files.

- [ ] **Step 6: Update closeout docs**

Record exact verification results in `DEVELOPMENT_STATUS.md`. Mark P14 complete only if all required H-tasks and verification commands pass.

- [ ] **Step 7: Commit H8**

Run:

```bash
git add DEVELOPMENT_PLAN.md DEVELOPMENT_STATUS.md README.md tests/test_p13_live_deepseek_product_acceptance.py
git commit -m "docs: close p14 product ui shell"
```

Only include `README.md` or test files if they were actually modified.

## Final Acceptance Criteria

- P14 clickable prototype is tracked under `docs/product/prototypes/`.
- Next.js workspace pages share one horizontal product shell.
- The primary UI is Chinese and business-facing.
- `/datasets` behaves like 数据源管理, not an English developer form.
- `/analysis` behaves like 分析工作台 and keeps the integrated clarification thread.
- `/reports` behaves like 报告中心 and keeps report technical details secondary.
- `/settings` behaves like 数据设置 with data/profile/semantic/model/safety sections.
- `/business-qa` exists as a clearly labeled preview, not a fake completed chat product.
- Frontend tests cover product shell navigation and core Chinese user-facing copy.
- Full backend tests pass.
- Full frontend tests and build pass.
- Real DeepSeek P13/P14 product acceptance passes.
- P11 and P12 live regressions pass.
- No generated artifacts are committed.
- No old Streamlit/eval/chart-agent product path is restored.

## Execution Order

1. P14-H1: Prototype reference and plan closeout.
2. P14-H2: Shared shell and tokens.
3. P14-H3: Data source management redesign.
4. P14-H4: Analysis Workbench redesign.
5. P14-H5: Report Center redesign.
6. P14-H6: Data Settings redesign.
7. P14-H7: Business Q&A preview route.
8. P14-H8: full regression, live acceptance, docs closeout.

Do not start H3-H7 before H2 lands. The shell and CSS tokens are the foundation that prevents each page from drifting into a different design again.
