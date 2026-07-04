# P15 Analysis Reliability And History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Analysis Workbench reliable enough for real product use by preserving analysis history, restoring previous results after navigation, automatically recovering from schema-mismatch SQL failures once, and showing business-friendly failure explanations when recovery is not possible.

**Architecture:** P15 keeps the current workspace-run storage model: every analysis remains a workspace-rooted run under `workspaces/{workspace_id}/runs/{run_id}/run_{id}.json`. Add small backend read APIs and frontend history components on top of those persisted run files. Add one bounded SQL repair loop for reviewer-detected schema mismatches; do not add fixed SQL templates, keyword-heavy business rule trees, or a parallel chat backend.

**Tech Stack:** FastAPI, Pydantic, filesystem-backed workspace run artifacts, Next.js App Router, React, TypeScript, Vitest, Testing Library, pytest, opt-in real DeepSeek live tests.

---

## Product Problems Being Solved

### 1. Analysis Results Disappear After Navigation

Today, `AnalysisRunner` stores the active run in React state and caches a run response in `sessionStorage`. If the user leaves the Analysis Workbench, opens another workspace page, refreshes, or returns later, the workbench does not show what they already asked.

The backend already persists run files, but there is no product API to list or load them. P15 turns persisted run files into a user-facing analysis history.

### 2. SQL Schema Mismatch Fails Too Technically

Real DeepSeek can occasionally generate SQL for an old or adjacent schema. Example failure:

```text
User: 给我一下最近30天几个渠道的数据
Clarification answer: 都看
Bad SQL used: order_items, products, p.product_name
Actual workspace tables: orders, marketing_spend, customers
```

The SQL reviewer correctly blocks the query. The product problem is that the system stops immediately and shows raw technical errors instead of attempting a bounded repair and explaining the failure in business terms.

## P15 Product Direction

Primary Analysis Workbench shape:

```text
workspace
-> 分析工作台
-> ask a business question
-> current analysis result
-> analysis history list loaded from persisted workspace runs
-> click any previous run
-> restore question thread, business answer, evidence, charts, and technical details
-> continue clarification or follow-up when the run state allows it
```

Failure recovery shape:

```text
LLM SQL candidate
-> SQL reviewer
-> if reviewer detects Unknown table / Unknown column
-> run one schema-aware SQL repair attempt with the real workspace schema
-> review repaired SQL
-> execute if approved
-> otherwise return business-friendly failure summary and collapsed technical detail
```

## Clean-Code Requirements

- Keep one clear backend boundary for run history loading. Do not scan run files ad hoc from API route bodies.
- Create a small `WorkspaceRunStore` helper instead of putting filesystem traversal directly in `api/app.py`.
- Keep frontend API calls in `frontend/lib/api.ts`; do not fetch directly from deeply nested components.
- Keep `AnalysisRunner` readable by extracting history UI into `AnalysisHistoryPanel` and small formatting helpers.
- Do not use `localStorage` or `sessionStorage` as the source of truth for history. Session cache may be removed or kept only as a non-authoritative optimization.
- Do not introduce fixed SQL templates for channel questions. SQL repair must be schema-aware and provider-backed or deterministic validation-backed, not keyword-rule backed.
- Do not expose raw SQL review internals as the primary product answer. Technical details stay collapsed.
- Keep generated run/report/chart/trace artifacts untracked.

## File Structure

### Create

- `workspaces/run_store.py`
  - List persisted workspace run summaries.
  - Load a specific run file safely within the workspace root.
  - Normalize run summary fields for UI consumption.
- `frontend/components/AnalysisHistoryPanel.tsx`
  - Shows recent analysis questions, status, headline/failure summary, timestamp, and view action.
- `tests/test_workspace_run_history_api.py`
  - Backend tests for list/detail run APIs and path safety.

### Modify

- `api/models.py`
  - Add response models for run summary, run list, and run detail.
- `api/app.py`
  - Add `GET /api/workspaces/{workspace_id}/runs`.
  - Add `GET /api/workspaces/{workspace_id}/runs/{run_id}`.
- `workspaces/analysis_runner.py`
  - Ensure completed, failed, and waiting-for-clarification runs have enough product fields for history.
- `graph/nodes.py` or the current SQL reviewer / guarded SQL candidate path
  - Add one schema-mismatch repair pass after reviewer rejects Unknown table/column errors.
- `workspaces/product_result_builder.py`
  - Add business-friendly failure reason fields for product UI when SQL review fails.
- `frontend/lib/api.ts`
  - Add `listWorkspaceRuns()` and `getWorkspaceRun()`.
- `frontend/components/AnalysisRunner.tsx`
  - Load history on mount.
  - Refresh history after each new run or continuation.
  - Restore a selected run into the current workbench result.
- `frontend/components/RunResultLoader.tsx`
  - Prefer backend run detail API over `sessionStorage`.
- `frontend/components/BusinessAnswerCard.tsx` or the current failure-rendering component
  - Show product-friendly failure explanations.
- `frontend/tests/workspace-flow.test.tsx`
  - Cover history list, restore selected run, and business-friendly failure display.
- Live test files
  - Add a real DeepSeek regression for the `最近30天几个渠道的数据` + `都看` clarification scenario.

## Task P15-H1: Backend Run History APIs

**Goal:** Make persisted workspace run files available as product history.

**Implementation steps:**

1. Add failing tests in `tests/test_workspace_run_history_api.py`.
2. Create `workspaces/run_store.py`.
3. Implement summary extraction from run JSON:
   - `run_id`
   - `status`
   - `question`
   - `headline`
   - `created_at` or `saved_at`
   - `has_chart`
   - `requires_clarification`
   - `failure_reason`
4. Add `GET /api/workspaces/{workspace_id}/runs`.
5. Add `GET /api/workspaces/{workspace_id}/runs/{run_id}`.
6. Reject unsafe run ids and paths.
7. Run focused backend tests.

**Acceptance:**

- History includes completed, failed, and waiting-for-clarification runs.
- Failed runs are not hidden.
- Detail endpoint returns a normal `WorkspaceRunResponse`-shaped payload with `product_result`.
- API never exposes arbitrary filesystem paths.

## Task P15-H2: Analysis History Panel

**Goal:** Let users see and restore previous questions directly inside Analysis Workbench.

**Implementation steps:**

1. Add failing frontend tests for history rendering and run selection.
2. Add `listWorkspaceRuns()` and `getWorkspaceRun()` to `frontend/lib/api.ts`.
3. Create `AnalysisHistoryPanel`.
4. Mount it in `AnalysisRunner` below the ask panel or beside the current result, using responsive layout.
5. Load history when the workbench opens.
6. Refresh history after a run, clarification continuation, or follow-up.
7. Clicking a history item loads the full run detail and displays it through existing `RunResult`.

**Acceptance:**

- User can leave the page, return to Analysis Workbench, and see previous questions.
- User can click a previous run and see the same question thread, answer, evidence, charts, and technical details.
- Failed runs show as failed records instead of disappearing.
- The UI remains Chinese and business-facing.

## Task P15-H3: Run Detail Uses Backend Source Of Truth

**Status:** Complete.

**Goal:** Remove the product dependency on `sessionStorage` for run detail restoration.

**Implementation steps:**

1. Add failing frontend test for `RunResultLoader` fetching backend detail when session cache is empty.
2. Update `RunResultLoader` to call `getWorkspaceRun()`.
3. Keep `sessionStorage` only as optional fast-path cache if it does not complicate the component.
4. Show a clear Chinese empty/error state if the run was deleted or cannot be read.

**Acceptance:**

- `/workspaces/{workspaceId}/runs/{runId}` works after refresh.
- A copied run-detail URL works in a new browser session.
- Technical details remain collapsed by default.

## Task P15-H4: One-Pass SQL Schema Repair

**Status:** Complete.

**Goal:** Recover from LLM SQL candidates that reference nonexistent tables or columns.

**Implementation steps:**

1. Add backend tests that force a bad SQL candidate using `products` / `order_items` against a workspace that only has `orders` / `marketing_spend`.
2. Detect reviewer failures containing schema mismatch signals:
   - `Unknown table`
   - `Unknown column`
   - missing table or column validation errors from the existing reviewer
3. Build a repair prompt/context containing:
   - original user question
   - rejected SQL
   - reviewer rejection reasons
   - exact current database schema
   - semantic-layer metric/dimension hints when available
4. Ask the configured SQL candidate provider for one repaired candidate.
5. Run the existing SQL reviewer again.
6. Execute only if the repaired candidate passes.
7. Record repair metadata in trace:
   - `schema_repair_attempted`
   - `schema_repair_succeeded`
   - `schema_repair_reason`
   - rejected and repaired SQL summaries

**Acceptance:**

- There is at most one automatic schema repair attempt per run.
- The repair path still goes through `validate_sql()` before execution.
- No fixed channel SQL template is introduced.
- If repair succeeds, the user sees a normal business answer.
- If repair fails, the user sees a product-friendly failure with technical detail collapsed.

## Task P15-H5: Business-Friendly Failure UX

**Status:** Complete.

**Goal:** Replace raw SQL reviewer output in the main UI with a clear explanation.

**Implementation steps:**

1. Add product result fields for failure display, for example:
   - `business_answer.headline`
   - `business_answer.summary`
   - `business_answer.next_actions`
   - `technical_details.validation_logs`
2. Map schema mismatch failures to Chinese business copy:
   - "系统尝试使用当前数据中不存在的表或字段，本轮未执行查询。"
   - "当前工作区可分析渠道、收入、订单、投放花费等指标。"
   - "可以重新分析最近 30 天各渠道收入、花费和 ROI，或上传商品明细数据后再分析商品维度。"
3. Keep raw reviewer reasons in collapsed technical details.
4. Add UI tests that assert raw `Unknown table` text is not the primary visible answer.

**Acceptance:**

- Users can understand why the analysis failed without reading SQL.
- The main failure card suggests a useful next action.
- Technical users can still expand details to inspect reviewer reasons.

## Task P15-H6: Real DeepSeek Product Regression

**Status:** Complete.

**Goal:** Prove the real product path handles the scenario that exposed the bug.

**Implementation steps:**

1. Add an opt-in live test using existing live-test environment flags.
2. Use the real workspace-style sample data with `orders`, `marketing_spend`, and `customers`.
3. Ask:

```text
给我一下最近30天几个渠道的数据
```

4. If the system asks what metric to use, answer:

```text
都看
```

5. Assert the completed or repaired result includes channel-level revenue/spend/ROI concepts.
6. Assert final SQL/result does not reference:
   - `products`
   - `order_items`
   - `product_name`
   - `quantity * unit_price`
7. Add a frontend or API-level check that after navigation/refresh the run appears in history.

**Acceptance:**

- Live DeepSeek path no longer fails the `都看` scenario because of stale ecommerce schema assumptions.
- If the provider still produces bad SQL initially, the schema-repair path either fixes it or returns a business-friendly failure.
- History persists after page navigation.

**Closeout notes:**

- Added `tests/test_p15_live_deepseek_analysis_reliability.py` as a real opt-in DeepSeek regression. It creates a temporary workspace with realistic `orders`, `marketing_spend`, and `customers` data, generates profile and semantic-layer context, asks the original channel question, continues with `都看` when clarification is requested, and verifies completed or business-friendly failed product output.
- The verified live run asked a metric clarification, accepted `都看` as the only user continuation, completed analysis, returned Chinese business output with evidence rows, and restored the result from workspace run history detail.
- Added non-live persistence/history regressions so full product results are saved to workspace run files and old raw `product_result.business_answer` values are sanitized when loaded through history/detail APIs.

## Verification Commands

Run focused tests during implementation:

```bash
python3 -m pytest tests/test_workspace_run_history_api.py -q
python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_provider_assisted_sql_planning_workflow.py -q
cd frontend && npm test -- workspace-flow.test.tsx
```

Run full regression before P15 closeout:

```bash
python3 -m pytest
cd frontend && npm test
cd frontend && npm run build
```

Run opt-in live verification before P15 closeout:

```bash
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1 \
INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1 \
INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING=1 \
python3 -m pytest tests/test_p15_live_deepseek_analysis_reliability.py -q
```

P11/P12/P13 live tests remain available for cross-phase regression when needed.

## Artifact Hygiene

Do not commit:

```text
.env
frontend/.next/
frontend/node_modules/
.pytest_cache/
__pycache__/
workspaces/*/runs/*
workspaces/*/reports/*
reports/charts/*
reports/markdown/*
logs/traces/*
sample_data/
```

Use `git status --short` and `git ls-files` audits before every P15 commit.

## P15 Out Of Scope

- Full Business Q&A chat backend.
- Real SaaS integrations.
- Auth/RBAC.
- Deployment.
- PDF/PPT export.
- Scheduled reports.
- Vector databases.
- Replacing the SQL reviewer, evidence validator, artifact policy, or trace logger.
- Adding hardcoded SQL or keyword-heavy business rule trees.
- Restoring historical UI/eval/chart product paths.
