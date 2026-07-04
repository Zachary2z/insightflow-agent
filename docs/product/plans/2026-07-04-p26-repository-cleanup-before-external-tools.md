# P26 Repository Cleanup Before External Tools

## Goal

P26 is a cleanup-only phase before real external business tool integrations. It keeps the historical development record, but removes repository noise and stale assumptions that make the current product look older or more demo-like than it is.

Current product guidance remains FastAPI + Next.js + workspace import/profile/semantic layer + Analysis Workbench + Report Center.

Status: complete. P26 removed tracked generated artifacts, preserved historical records, and verified the current backend/frontend product chain before P27 external business tool planning.

## Scope

- Keep historical docs under `docs/product/plans/` and `docs/superpowers/specs/`.
- Remove generated runtime artifacts from git tracking.
- Keep `.gitkeep` placeholders for empty artifact directories.
- Make low-level tests generate their local SQLite fixture when needed instead of requiring a committed database.
- Keep negative boundary tests that prevent old chart/action/mock/eval paths from coming back.
- Do not delete current multi-agent/tool-calling code paths that are still tested or used by the current graph, analysis, evidence, visualization, or report chain.

## Non-Goals

- No new external SaaS/tool integration.
- No UI redesign.
- No rewrite of Analysis Workbench or Report Center.
- No deletion of historical development records.
- No removal of multi-agent structure just to reduce file count.

## Implementation

1. Add repository hygiene coverage.
   - Assert generated databases, report outputs, trace files, `.superpowers`, and workspace run/report artifacts are not tracked.
   - Assert historical docs are retained and marked as historical.
   - Assert current docs name FastAPI + Next.js as the current product path.

2. Remove tracked generated database.
   - Stop tracking `data/ecommerce.db`.
   - Keep it ignored.
   - Preserve local developer convenience by generating it from `data.seed_data.seed_database()` during pytest startup when missing.

3. Clean local generated noise.
   - Remove ignored `__pycache__`, `.pytest_cache`, local chart PNG outputs, trace outputs, and generated workspace run/report directories where safe.
   - Keep `.venv`, `frontend/node_modules`, and `.env` untouched.

4. Documentation closeout.
   - Update README, development plan, and status so the current product path is clear.
   - Explain that `data/ecommerce.db` is a generated local fixture, not a committed source artifact.

## Acceptance Criteria

- `data/ecommerce.db` is no longer tracked by git.
- Normal pytest can recreate the local fixture if it is absent.
- Historical development docs remain in place.
- Current docs do not present old Streamlit/eval/mock/action/chart paths as active guidance.
- Generated runtime artifacts remain ignored and untracked.
- Focused P26 hygiene tests pass.
- Full backend tests pass.
- Relevant frontend tests pass.

## Closeout Verification

- `python3 -m pytest tests/test_p26_repository_hygiene.py tests/test_schema_tool.py tests/test_sql_executor.py tests/test_p0_agents.py tests/test_workflow.py -q`
- `python3 -m pytest`
- `npm test` in `frontend/`
- `npm run build` in `frontend/`
- `git diff --check`
