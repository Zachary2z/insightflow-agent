# InsightFlow Frontend UI Consolidation

Date: 2026-07-10

Status: Complete.

## Goal

Apply the approved HTML prototype to the real Next.js frontend while preserving every active workspace capability and the product boundary between Analysis Workbench and Report Center.

## Product Decisions

- Use one decision-desk shell with three primary destinations: 数据准备、分析、报告。
- Group 数据源、字段画像、业务语义 as tabs under 数据准备 instead of separate global navigation items.
- Keep 工作区设置 secondary and compact; it summarizes readiness, model participation, and safety instead of duplicating the full data-preparation pages.
- Present analysis output answer-first: 业务结论、图表、证据, followed by 分析线程、分析进度、折叠技术详情.
- Keep Report Center independent and place report creation before the report library.
- Retire the static Business Q&A preview from the active product path; its historical route redirects to Analysis Workbench.

## Functional Boundaries

- Preserve the existing workspace, dataset, profiling, semantic-layer, analysis, same-thread follow-up, history restoration, chart, report, export, and Feishu publishing APIs.
- Do not merge report generation into analysis answers.
- Do not expose SQL, provider metadata, trace paths, or raw rows in the main business UI.
- Keep responsive desktop/mobile navigation, visible focus states, reduced-motion handling, skip links, and keyboard-operable history navigation.

## Verification

- Frontend Vitest: `83 passed`.
- Next.js production build: passed, including all workspace routes and the lightweight historical redirect route.
- P14 route/boundary plus workspace/run-history/report/settings API regression: `55 passed`.
- Browser QA: passed at 1280px and 390px. No horizontal overflow; desktop sidebar, mobile bottom navigation, data-preparation tabs, compact settings, report-first creation, history drawer focus/close behavior, result restoration, answer-first result order, and Business Q&A redirect were verified against a real local workspace.
- `git diff --check`: passed.

The first backend regression attempt exposed a stale local virtual environment missing the already-declared `python-docx` dependency. Installing the declared package into `.venv` restored the two Word-export tests; no backend product code change was required.

The approved visual reference remains `docs/product/prototypes/2026-07-10-insightflow-ui-consolidation.html`.
