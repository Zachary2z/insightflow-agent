# P13 Business Answer And Product UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the P13 Analysis Workbench product experience with structured business answers, clarification continuation, business-first reports, data settings, chart polish, and live DeepSeek product acceptance while preserving the existing guarded SQL, evidence, visualization, artifact, and trace boundaries.

**Architecture:** Add a structured product response layer on top of the current workflow result rather than replacing the workflow. Persist pending clarification runs under the workspace, resolve a short clarification answer into a visible `resolved_question`, then continue through the existing guarded workflow. Keep raw workflow fields available for compatibility during migration, but make frontend and report readers consume first-class `question_thread`, `business_answer`, `evidence`, `chart_artifacts`, `report`, and `technical_details` objects.

**Tech Stack:** FastAPI, Pydantic, LangGraph workflow state, workspace filesystem stores, pytest, DeepSeek provider helpers, Next.js App Router, React, TypeScript, Vitest, Testing Library, matplotlib local renderer.

---

## File Structure Map

### Backend Product Output

- Create `workspaces/product_models.py`
  - Dataclass or typed helper definitions for `QuestionThread`, `BusinessAnswer`, `EvidenceSummary`, `ChartArtifact`, `TechnicalDetails`, and `ProductAnalysisResult`.
- Create `workspaces/product_result_builder.py`
  - Pure transformer from raw workflow state to P13 product response objects.
  - Keeps `raw_result` compatibility in API response during migration.
- Modify `api/models.py`
  - Add Pydantic request and response fields for structured analysis output and clarification continuation.
- Modify `workspaces/analysis_runner.py`
  - Wrap `run_workflow()` output with `build_product_analysis_result()`.
  - Preserve current raw keys so existing tests and stored run detail pages still work while frontend migrates.
- Modify `api/app.py`
  - Return structured fields from `POST /api/workspaces/{workspace_id}/runs`.
  - Add artifact serving endpoint for chart images under workspace-root validated paths.

### Clarification Continuation

- Create `workspaces/pending_clarification_store.py`
  - Store pending runs under `workspaces/{workspace_id}/pending_runs/{pending_run_id}.json`.
  - Load, complete, expire, and validate workspace ownership.
- Create `question_understanding/resolved_question.py`
  - Deterministic resolver that combines original question, understanding, clarification prompt, answer, and workspace context into `resolved_question`.
  - Provider hook can be added after deterministic tests pass, but P13 must not require it for no-key mode.
- Modify `graph/state.py`
  - Add `original_question`, `clarification_question`, `clarification_answer`, `resolved_question`, `pending_run_id`, and `question_thread`.
- Modify `graph/workflow.py`
  - Accept optional continuation inputs and initialize state with original/resolved question fields.
- Modify `graph/nodes.py`
  - Ensure traces retain original question, clarification question, clarification answer, and resolved question.
- Modify `api/app.py`
  - Support continuation request shape on `POST /api/workspaces/{workspace_id}/runs`.

### Business Answer Quality

- Modify `llm_ops/runtime_provider.py`
  - Add product/live mode helper that enables question understanding, clarification, SQL planning, SQL candidate, insight drafting, claim typing, visualization, and report writer provider paths together when a single product mode flag is set and a provider key is available.
- Modify `llm_ops/prompt_registry.py`
  - Strengthen `insight_drafter` instructions for recommendation-first prose and structured business answer fields.
- Modify `llm_ops/structured_output.py`
  - Validate product-facing insight output and reject parameter dumps.
- Modify `agents/insight_agent.py`
  - Produce `business_answer` fields and keep raw row dumps only in `technical_details`.

### Reports

- Modify `workspaces/report_models.py`
  - Add business-facing section fields and technical appendix fields without removing existing stored fields abruptly.
- Modify `workspaces/report_runner.py`
  - Build report sections with business-facing summaries first and internal section prompts/SQL/provider metadata under technical appendix data.
- Modify `workspaces/report_markdown.py`
  - Render business report first, Markdown download preserved, technical appendix separated and collapsed with Markdown-compatible `<details>`.
- Modify `api/app.py`
  - Add report progress/status fields if report generation remains synchronous.

### Frontend Workbench

- Modify `frontend/lib/api.ts`
  - Add types and client calls for structured run results, clarification continuation, artifact URLs, report appendix, and data settings.
- Modify `frontend/components/AnalysisRunner.tsx`
  - Turn the current form/result split into the Analysis Workbench shell.
- Modify `frontend/components/RunResult.tsx`
  - Render P13 structured fields first and keep legacy fallback.
- Create `frontend/components/WorkspaceReadinessHeader.tsx`
  - Workspace name, source/profile/semantic readiness, and product/live mode status.
- Create `frontend/components/AnalysisThreadCard.tsx`
  - Single compact card for user question, understanding, clarification, answer, resolved question, continue/edit controls.
- Create `frontend/components/BusinessAnswerCard.tsx`
  - Recommendation-first answer UI.
- Create `frontend/components/EvidencePanel.tsx`
  - Verified metrics and table preview.
- Create `frontend/components/ChartArtifactGallery.tsx`
  - Image rendering for chart artifacts through API URLs.
- Create `frontend/components/TechnicalDetailsDisclosure.tsx`
  - Collapsed SQL, rows, trace, provider metadata, and validation logs.

### Frontend Reports And Settings

- Modify `frontend/components/ReportViewer.tsx`
  - Business report reader, section navigation, progress/status, Markdown download, collapsed technical appendix.
- Modify `frontend/components/ReportSection.tsx`
  - Hide purpose/internal question/SQL/provider metadata from main section body.
- Create `frontend/components/ReportTechnicalAppendix.tsx`
  - Collapsed report and section technical details.
- Create `frontend/app/workspaces/[workspaceId]/settings/page.tsx`
  - Data Settings route.
- Create `frontend/components/DataSettings.tsx`
  - Data sources, profile, semantic layer, model/product-live mode, safety/audit sections.
- Modify `frontend/components/DatasetManager.tsx`
  - Reuse or embed as Data Settings data source area.

### Chart Product Quality

- Modify `visualization/chart_renderer.py`
  - Configure CJK-capable font fallback, value labels, units, business annotation, and better title/axis spacing.
- Modify `visualization/chart_validator.py`
  - Allow optional `unit`, `value_label`, and `business_annotation` fields in chart spec.
- Modify `agents/visualization_agent.py`
  - Preserve chart metadata in `chart_artifacts`.
- Modify `visualization_delivery/adapters.py`
  - Return chart display metadata and artifact path suitable for frontend image URLs.

---

## Task P13-H1: Product Output Model

### Goal

Split the current raw workflow result blob into product-facing `question_thread`, `business_answer`, `evidence`, `chart_artifacts`, `report`, and `technical_details` objects while keeping old `result` compatibility for the existing API and run detail storage.

### Files

- Create `workspaces/product_models.py`
- Create `workspaces/product_result_builder.py`
- Modify `workspaces/analysis_runner.py`
- Modify `api/models.py`
- Modify `api/app.py`
- Modify `frontend/lib/api.ts`
- Test `tests/test_product_result_builder.py`
- Test `tests/test_workspace_analysis_runner.py`
- Test `frontend/tests/api-client.test.ts`

### TDD Steps

- [ ] **Step 1: Write backend transformer tests**

Add `tests/test_product_result_builder.py`:

```python
def test_product_result_builder_splits_business_and_technical_fields():
    from workspaces.product_result_builder import build_product_analysis_result

    raw = {
        "run_id": "run_1",
        "status": "completed",
        "user_question": "哪个渠道该加预算？",
        "question_understanding": {"strategy": "llm_candidate", "intent": {"metric": "revenue", "dimension": "channel"}},
        "final_answer": "建议加大 paid_search，因为收入最高且 ROI 领先。",
        "generated_sql": "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
        "execution_result": {"success": True, "columns": ["channel", "revenue"], "rows": [["paid_search", 200.0]]},
        "evidence_result": {"data_supported_findings": [{"claim": "paid_search revenue is 200.0"}]},
        "visualization_trace": {"artifact_path": "/tmp/ws/runs/run_1/charts/channel.png", "provider_called": True},
        "trace_path": "/tmp/ws/runs/run_1/trace.json",
    }

    product = build_product_analysis_result(raw, workspace_id="ws_1")

    assert product["question_thread"]["original_question"] == "哪个渠道该加预算？"
    assert product["business_answer"]["headline"]
    assert product["evidence"]["table_preview"]["columns"] == ["channel", "revenue"]
    assert product["chart_artifacts"][0]["path"].endswith("channel.png")
    assert product["technical_details"]["sql"].startswith("SELECT channel")
    assert product["technical_details"]["raw_rows"] == [["paid_search", 200.0]]
    assert "raw_rows" not in product["business_answer"]
```

- [ ] **Step 2: Run failing backend transformer test**

Run: `python3 -m pytest tests/test_product_result_builder.py -q`

Expected: fail because `workspaces.product_result_builder` does not exist.

- [ ] **Step 3: Implement product model and transformer**

Create `workspaces/product_models.py` with serializable structures:

```python
PRODUCT_RESULT_VERSION = "p13.v1"

def empty_business_answer() -> dict:
    return {
        "headline": "",
        "summary": "",
        "recommendations": [],
        "next_actions": [],
        "caveats": [],
        "confidence": "medium",
        "source": "",
    }
```

Create `workspaces/product_result_builder.py` with:

```python
def build_product_analysis_result(raw: dict, *, workspace_id: str | None = None) -> dict:
    execution = raw.get("execution_result") or {}
    return {
        "version": "p13.v1",
        "workspace_id": workspace_id or raw.get("workspace_id"),
        "run_id": raw.get("run_id"),
        "status": raw.get("status", "unknown"),
        "question_thread": build_question_thread(raw),
        "business_answer": build_business_answer(raw),
        "evidence": build_evidence(execution, raw.get("evidence_result") or {}),
        "chart_artifacts": build_chart_artifacts(raw),
        "report": None,
        "technical_details": build_technical_details(raw),
    }
```

Keep helper functions pure and deterministic; do not call providers here.

- [ ] **Step 4: Wrap workspace analysis output while preserving legacy raw result**

Modify `workspaces/analysis_runner.py` so the returned dict has both legacy raw keys and structured product fields:

```python
product_result = build_product_analysis_result(result, workspace_id=workspace_id)
result["product_result"] = product_result
result.update({
    "question_thread": product_result["question_thread"],
    "business_answer": product_result["business_answer"],
    "evidence": product_result["evidence"],
    "chart_artifacts": product_result["chart_artifacts"],
    "technical_details": product_result["technical_details"],
})
```

- [ ] **Step 5: Extend API models and frontend types**

Modify `api/models.py`:

```python
class WorkspaceRunResponse(BaseModel):
    success: bool
    workspace_id: str
    run_id: str | None = None
    result: dict[str, Any]
    product_result: dict[str, Any] | None = None
```

Modify `frontend/lib/api.ts`:

```ts
export type ProductAnalysisResult = {
  version: "p13.v1" | string;
  question_thread: QuestionThread;
  business_answer: BusinessAnswer;
  evidence: EvidenceSummary;
  chart_artifacts: ChartArtifact[];
  technical_details: TechnicalDetails;
};
```

- [ ] **Step 6: Add API compatibility test**

Extend `tests/test_workspace_analysis_runner.py`:

```python
assert result["product_result"]["business_answer"]["headline"]
assert result["technical_details"]["sql"] == result["generated_sql"]
assert result["final_answer"]
```

Extend `frontend/tests/api-client.test.ts`:

```ts
expect(run.product_result?.business_answer.headline).toBe("Paid search leads revenue.");
expect(run.result.final_answer).toBe("Paid search leads revenue.");
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py -q
cd frontend && npm test -- api-client.test.ts
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add workspaces/product_models.py workspaces/product_result_builder.py workspaces/analysis_runner.py api/models.py api/app.py frontend/lib/api.ts tests/test_product_result_builder.py tests/test_workspace_analysis_runner.py frontend/tests/api-client.test.ts
git commit -m "feat: add p13 product analysis result model"
```

### Acceptance

- API still returns `result` with existing raw fields.
- API also returns `product_result` and top-level structured fields.
- `business_answer` never contains SQL, raw rows, trace, or provider metadata.
- `technical_details` includes SQL, rows, trace path, provider metadata, and validation/debug fields.

---

## Task P13-H2: Clarification Continuation

### Goal

Allow users to answer only the clarification prompt, persist a pending clarification run, generate and display `resolved_question`, and continue through the original guarded SQL/evidence/chart/answer flow.

### Files

- Create `workspaces/pending_clarification_store.py`
- Create `question_understanding/resolved_question.py`
- Modify `api/models.py`
- Modify `api/app.py`
- Modify `workspaces/analysis_runner.py`
- Modify `graph/workflow.py`
- Modify `graph/state.py`
- Modify `graph/nodes.py`
- Modify `tools/trace_logger.py` if trace envelope needs extra fields
- Test `tests/test_pending_clarification_store.py`
- Test `tests/test_clarification_continuation_api.py`
- Test `tests/test_provider_backed_clarification_router.py`
- Test `tests/test_product_result_builder.py`

### TDD Steps

- [ ] **Step 1: Write pending store tests**

Add `tests/test_pending_clarification_store.py`:

```python
def test_pending_clarification_store_persists_and_completes_run(tmp_path):
    from workspaces.pending_clarification_store import PendingClarificationStore
    from workspaces.store import WorkspaceStore

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Clarification Workspace")
    pending_store = PendingClarificationStore(store)

    pending = pending_store.create_pending_run(
        workspace_id=workspace["workspace_id"],
        run_id="run_1",
        original_question="帮我分析渠道表现",
        question_understanding={"intent": {"dimension": "channel"}},
        clarification_question="你希望分析哪个时间范围？",
        raw_result={"status": "waiting_for_clarification"},
    )

    loaded = pending_store.load_pending_run(workspace["workspace_id"], pending["pending_run_id"])
    assert loaded["original_question"] == "帮我分析渠道表现"
    assert loaded["status"] == "pending"

    completed = pending_store.complete_pending_run(
        workspace_id=workspace["workspace_id"],
        pending_run_id=pending["pending_run_id"],
        clarification_answer="最近 90 天",
        resolved_question="分析最近 90 天各渠道表现并给出预算建议。",
    )
    assert completed["status"] == "completed"
```

- [ ] **Step 2: Write continuation API test**

Add `tests/test_clarification_continuation_api.py`:

```python
def test_workspace_run_can_continue_pending_clarification(tmp_path):
    from fastapi.testclient import TestClient
    from api.app import create_app
    from workspaces.store import WorkspaceStore

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace_id = store.create_workspace("Clarification API")["workspace_id"]

    calls = []

    def fake_runner(**kwargs):
        calls.append(kwargs)
        if not kwargs.get("clarification_answer"):
            return {
                "run_id": "run_pending",
                "status": "waiting_for_clarification",
                "user_question": kwargs["user_question"],
                "question_understanding": {"strategy": "clarify", "intent": {"dimension": "channel"}},
                "clarification_questions": ["你希望分析哪个时间范围？"],
                "clarification_result": {"requires_clarification": True},
                "execution_result": {},
            }
        return {
            "run_id": "run_completed",
            "status": "completed",
            "user_question": kwargs["user_question"],
            "original_question": "帮我分析渠道表现",
            "clarification_answer": "最近 90 天",
            "resolved_question": kwargs["user_question"],
            "final_answer": "最近 90 天 paid_search 表现最好。",
            "execution_result": {"success": True, "columns": ["channel"], "rows": [["paid_search"]]},
        }

    client = TestClient(create_app(workspace_store=store, analysis_runner=fake_runner))
    first = client.post(f"/api/workspaces/{workspace_id}/runs", json={"user_question": "帮我分析渠道表现"}).json()
    pending_run_id = first["product_result"]["question_thread"]["pending_run_id"]

    second = client.post(
        f"/api/workspaces/{workspace_id}/runs",
        json={"pending_run_id": pending_run_id, "clarification_answer": "最近 90 天"},
    )

    assert second.status_code == 200
    payload = second.json()
    thread = payload["product_result"]["question_thread"]
    assert thread["original_question"] == "帮我分析渠道表现"
    assert thread["clarification_answer"] == "最近 90 天"
    assert thread["resolved_question"]
    assert payload["product_result"]["status"] == "completed"
```

- [ ] **Step 3: Run failing continuation tests**

Run:

```bash
python3 -m pytest tests/test_pending_clarification_store.py tests/test_clarification_continuation_api.py -q
```

Expected: fail because store, request shape, and injected runner support do not exist.

- [ ] **Step 4: Implement pending store**

Create `workspaces/pending_clarification_store.py` with JSON persistence:

```python
class PendingClarificationStore:
    def __init__(self, workspace_store: WorkspaceStore):
        self.workspace_store = workspace_store

    def create_pending_run(self, *, workspace_id: str, run_id: str, original_question: str, question_understanding: dict, clarification_question: str, raw_result: dict) -> dict:
        pending_run_id = f"pending_{uuid4().hex[:8]}"
        payload = {
            "pending_run_id": pending_run_id,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "status": "pending",
            "original_question": original_question,
            "question_understanding": question_understanding,
            "clarification_question": clarification_question,
            "raw_result": raw_result,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        self._write(workspace_id, pending_run_id, payload)
        return payload
```

Use `WorkspaceStore.resolve_workspace_path()` for path validation.

- [ ] **Step 5: Implement deterministic resolved question builder**

Create `question_understanding/resolved_question.py`:

```python
def resolve_question(*, original_question: str, clarification_question: str, clarification_answer: str, understanding: dict, workspace_context: dict | None = None) -> str:
    metric = (understanding.get("intent") or {}).get("metric") or "核心指标"
    dimension = (understanding.get("intent") or {}).get("dimension") or "相关维度"
    answer = clarification_answer.strip()
    return f"{original_question.strip()}；补充条件：{clarification_question.strip()} {answer}。请按 {dimension} 分析 {metric}，并给出业务结论、证据和建议。"
```

Keep deterministic output readable in no-key mode.

- [ ] **Step 6: Extend request model**

Modify `api/models.py`:

```python
class WorkspaceRunCreateRequest(BaseModel):
    user_question: str | None = None
    initial_sql: str | None = None
    pending_run_id: str | None = None
    clarification_answer: str | None = None
```

Validation rule in `api/app.py`: require either `user_question` or both `pending_run_id` and `clarification_answer`.

- [ ] **Step 7: Wire continuation into API and runner**

Modify `create_app()` to accept `analysis_runner: Callable[..., dict[str, Any]] | None = None` for tests.

In `POST /api/workspaces/{workspace_id}/runs`:

```python
if request.pending_run_id:
    pending = pending_store.load_pending_run(workspace_id, request.pending_run_id)
    resolved_question = resolve_question(
        original_question=pending["original_question"],
        clarification_question=pending["clarification_question"],
        clarification_answer=request.clarification_answer or "",
        understanding=pending["question_understanding"],
    )
    result = selected_analysis_runner(
        store=store,
        workspace_id=workspace_id,
        user_question=resolved_question,
        initial_sql=request.initial_sql,
        clarification_answer=request.clarification_answer,
        original_question=pending["original_question"],
        clarification_question=pending["clarification_question"],
        pending_run_id=request.pending_run_id,
        resolved_question=resolved_question,
    )
```

When an initial run returns `waiting_for_clarification`, create a pending record and inject `pending_run_id` into `question_thread`.

- [ ] **Step 8: Preserve trace fields**

Modify workflow initialization/state so continuation runs carry:

```python
state["original_question"] = original_question or user_question
state["clarification_question"] = clarification_question or ""
state["clarification_answer"] = clarification_answer or ""
state["resolved_question"] = resolved_question or user_question
state["pending_run_id"] = pending_run_id or ""
```

Ensure saved trace payload includes these fields.

- [ ] **Step 9: Extend provider-backed clarification tests**

In `tests/test_provider_backed_clarification_router.py`, add:

```python
assert result["trace"][-1]["node"] == "early_response_node"
assert result["status"] == "waiting_for_clarification"
```

Then add a continuation test through `run_workspace_analysis()` with `initial_sql` or a mock runner to prove the resolved question enters SQL execution.

- [ ] **Step 10: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_pending_clarification_store.py tests/test_clarification_continuation_api.py tests/test_provider_backed_clarification_router.py tests/test_product_result_builder.py -q
```

Expected: pass.

- [ ] **Step 11: Commit**

```bash
git add workspaces/pending_clarification_store.py question_understanding/resolved_question.py api/models.py api/app.py workspaces/analysis_runner.py graph/workflow.py graph/state.py graph/nodes.py tools/trace_logger.py tests/test_pending_clarification_store.py tests/test_clarification_continuation_api.py tests/test_provider_backed_clarification_router.py tests/test_product_result_builder.py
git commit -m "feat: add clarification continuation flow"
```

### Acceptance

- User can answer only "最近 90 天" after a time-range clarification.
- Backend persists pending clarification run before continuation.
- API accepts `pending_run_id` and `clarification_answer`.
- `resolved_question` is visible in `question_thread` before SQL execution.
- Trace contains `original_question`, `clarification_question`, `clarification_answer`, and `resolved_question`.
- Continuation uses the existing guarded SQL review, execution, evidence, chart, and answer path.

---

## Task P13-H3: Business Answer Quality And Product Live Mode

### Goal

Enable provider-backed insight drafting in product/live mode, produce readable business conclusions, and fail tests when product-facing answers are raw parameter or key-value dumps.

### Files

- Modify `llm_ops/runtime_provider.py`
- Modify `llm_ops/prompt_registry.py`
- Modify `llm_ops/structured_output.py`
- Modify `agents/insight_agent.py`
- Modify `workspaces/product_result_builder.py`
- Test `tests/test_product_live_mode.py`
- Test `tests/test_business_answer_quality.py`
- Test `tests/test_provider_backed_insight_agent.py` if existing; otherwise create it

### TDD Steps

- [ ] **Step 1: Write product/live mode helper tests**

Add `tests/test_product_live_mode.py`:

```python
def test_product_live_mode_enables_provider_flags_together(monkeypatch):
    from llm_ops.runtime_provider import product_live_mode_enabled, provider_insight_drafting_enabled

    monkeypatch.setenv("INSIGHTFLOW_PRODUCT_LIVE_MODE", "1")
    assert product_live_mode_enabled() is True
    assert provider_insight_drafting_enabled() is True


def test_no_key_mode_can_run_without_product_live_provider(monkeypatch):
    from llm_ops.runtime_provider import build_insight_drafting_provider

    monkeypatch.setenv("INSIGHTFLOW_PRODUCT_LIVE_MODE", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    assert build_insight_drafting_provider() is None
```

- [ ] **Step 2: Write answer quality tests**

Add `tests/test_business_answer_quality.py`:

```python
def test_business_answer_rejects_raw_key_value_dump():
    from workspaces.product_result_builder import build_business_answer

    raw = {
        "final_answer": "1. channel=paid_search, revenue=200.0, order_count=10\n2. channel=email, revenue=100.0",
        "insight": {"source": "deterministic", "fallback_used": True},
    }

    answer = build_business_answer(raw)

    assert answer["headline"] != "channel=paid_search, revenue=200.0, order_count=10"
    assert answer["quality_flags"] == ["raw_parameter_dump_detected"]
    assert "channel=" not in answer["summary"]
```

Add provider positive test:

```python
def test_provider_insight_output_becomes_recommendation_first_business_answer():
    from agents.insight_agent import run_insight_agent
    from llm_ops.provider import MockLLMProvider

    state = {
        "user_question": "哪个渠道该加预算？",
        "execution_result": {"success": True, "columns": ["channel", "revenue"], "rows": [["paid_search", 200.0]], "row_count": 1},
    }
    provider = MockLLMProvider({"candidate_claims": ["paid_search revenue is 200.0"], "draft_summary": "建议优先加码 paid_search，因为它贡献了最高收入 200.0。"})

    result = run_insight_agent(state, provider=provider)

    assert result["insight"]["source"] == "provider"
    assert result["business_answer"]["headline"].startswith("建议")
    assert "channel=" not in result["business_answer"]["summary"]
```

- [ ] **Step 3: Run failing tests**

Run:

```bash
python3 -m pytest tests/test_product_live_mode.py tests/test_business_answer_quality.py -q
```

Expected: fail until helpers and answer quality checks exist.

- [ ] **Step 4: Implement product/live mode helper**

In `llm_ops/runtime_provider.py`:

```python
def product_live_mode_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get("INSIGHTFLOW_PRODUCT_LIVE_MODE", "")).strip().lower() in {"1", "true", "yes", "on"}
```

Update provider flag helpers to return true when product live mode is true for product-safe providers:

```python
return _flag_enabled("INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING", values) or product_live_mode_enabled(values)
```

Apply to question understanding, clarification router, SQL planning, SQL candidate, insight drafting, claim typing, visualization agent, and report writer. Do not apply to action drafter or real SaaS delivery.

- [ ] **Step 5: Improve insight prompt and schema validation**

Update `insight_drafter` prompt to require:

```text
Return concise business prose with:
- a recommendation-first headline,
- evidence-backed explanation,
- next actions,
- caveats when needed.
Do not answer by dumping raw field=value pairs or SQL rows.
```

Update `llm_ops/structured_output.py` so `_validate_insight_drafter()` rejects `draft_summary` when most lines match `\b\w+=`.

- [ ] **Step 6: Add business answer construction in insight agent**

In `agents/insight_agent.py`, add a normalized `business_answer`:

```python
business_answer = build_business_answer({"final_answer": output["final_answer"], "insight": output})
updated = {
    **state,
    "insight": output,
    "business_answer": business_answer,
    "final_answer": output["final_answer"],
    "claims_to_validate": output.get("candidate_claims", []),
}
```

Fallback should produce a short "已完成查询，但需要产品模式草拟业务结论" style summary if a row dump is detected; raw rows remain in `technical_details`.

- [ ] **Step 7: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_product_live_mode.py tests/test_business_answer_quality.py tests/test_workspace_analysis_runner.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add llm_ops/runtime_provider.py llm_ops/prompt_registry.py llm_ops/structured_output.py agents/insight_agent.py workspaces/product_result_builder.py tests/test_product_live_mode.py tests/test_business_answer_quality.py
git commit -m "feat: improve p13 business answer quality"
```

### Acceptance

- `INSIGHTFLOW_PRODUCT_LIVE_MODE=1` enables product-safe provider-backed paths together.
- No-key mode still runs with deterministic fallbacks.
- Product-facing final answer tests fail on raw `field=value` dumps.
- Provider-backed insight drafting participates in product/live mode.
- Business answer includes headline, summary, recommendations or next actions, caveats, confidence, and quality flags.

---

## Task P13-H4: Analysis Workbench UI

### Goal

Replace the current disconnected form/result output with a compact integrated Analysis Workbench that shows the question thread, clarification continuation, resolved question, business answer, evidence, chart, and collapsed technical details in one flow.

### Files

- Modify `frontend/components/AnalysisRunner.tsx`
- Modify `frontend/components/RunResult.tsx`
- Create `frontend/components/WorkspaceReadinessHeader.tsx`
- Create `frontend/components/AnalysisThreadCard.tsx`
- Create `frontend/components/BusinessAnswerCard.tsx`
- Create `frontend/components/EvidencePanel.tsx`
- Create `frontend/components/ChartArtifactGallery.tsx`
- Create `frontend/components/TechnicalDetailsDisclosure.tsx`
- Modify `frontend/lib/api.ts`
- Modify `frontend/tests/workspace-flow.test.tsx`

### TDD Steps

- [ ] **Step 1: Write AnalysisThreadCard test**

In `frontend/tests/workspace-flow.test.tsx`:

```tsx
it("renders the integrated analysis thread in one card", () => {
  render(
    <RunResult
      result={{
        product_result: {
          question_thread: {
            original_question: "帮我分析渠道表现",
            system_understanding: "按渠道比较收入表现",
            clarification_question: "你希望分析哪个时间范围？",
            clarification_answer: "最近 90 天",
            resolved_question: "分析最近 90 天各渠道收入和 ROI，并给出预算建议。",
          },
          business_answer: { headline: "建议优先加码 paid_search", summary: "paid_search 收入最高。", next_actions: ["提高预算"], caveats: [], confidence: "medium" },
          evidence: { table_preview: { columns: ["channel", "revenue"], rows: [{ channel: "paid_search", revenue: 200 }] } },
          chart_artifacts: [],
          technical_details: { sql: "SELECT 1", raw_rows: [[1]], provider_metadata: { model: "deepseek" } },
        },
      }}
    />,
  );

  expect(screen.getByText("帮我分析渠道表现")).toBeTruthy();
  expect(screen.getByText("你希望分析哪个时间范围？")).toBeTruthy();
  expect(screen.getByText("最近 90 天")).toBeTruthy();
  expect(screen.getByText(/分析最近 90 天/)).toBeTruthy();
  expect(screen.getByText("建议优先加码 paid_search")).toBeTruthy();
  expect(screen.queryByText("SELECT 1")).toBeNull();
  expect(screen.getByRole("button", { name: "Technical details" })).toBeTruthy();
});
```

- [ ] **Step 2: Write clarification continuation UI test**

```tsx
it("submits only the clarification answer for a pending run", async () => {
  vi.mocked(runAnalysis)
    .mockResolvedValueOnce({
      success: false,
      workspace_id: "ws_1",
      run_id: "run_pending",
      product_result: {
        status: "waiting_for_clarification",
        question_thread: {
          pending_run_id: "pending_1",
          original_question: "帮我分析渠道表现",
          clarification_question: "你希望分析哪个时间范围？",
        },
      },
      result: {},
    })
    .mockResolvedValueOnce({
      success: true,
      workspace_id: "ws_1",
      run_id: "run_done",
      product_result: {
        status: "completed",
        question_thread: {
          original_question: "帮我分析渠道表现",
          clarification_answer: "最近 90 天",
          resolved_question: "分析最近 90 天各渠道表现。",
        },
        business_answer: { headline: "paid_search 表现最好", summary: "收入最高。", next_actions: [], caveats: [], confidence: "medium" },
        evidence: { table_preview: { columns: [], rows: [] } },
        chart_artifacts: [],
        technical_details: {},
      },
      result: {},
    });

  render(<AnalysisRunner workspaceId="ws_1" />);
  fireEvent.change(screen.getByLabelText("Question"), { target: { value: "帮我分析渠道表现" } });
  fireEvent.click(screen.getByRole("button", { name: "Run analysis" }));
  fireEvent.change(await screen.findByLabelText("Clarification answer"), { target: { value: "最近 90 天" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue analysis" }));

  await waitFor(() => expect(runAnalysis).toHaveBeenLastCalledWith("ws_1", { pendingRunId: "pending_1", clarificationAnswer: "最近 90 天" }));
});
```

- [ ] **Step 3: Run failing frontend tests**

Run: `cd frontend && npm test -- workspace-flow.test.tsx`

Expected: fail until components and API request shape exist.

- [ ] **Step 4: Extend frontend API types**

In `frontend/lib/api.ts`:

```ts
export type RunAnalysisRequest = {
  userQuestion?: string;
  initialSql?: string;
  pendingRunId?: string;
  clarificationAnswer?: string;
};
```

Map to snake_case body:

```ts
body: JSON.stringify({
  ...(request.userQuestion ? { user_question: request.userQuestion } : {}),
  ...(request.pendingRunId ? { pending_run_id: request.pendingRunId } : {}),
  ...(request.clarificationAnswer ? { clarification_answer: request.clarificationAnswer } : {}),
})
```

- [ ] **Step 5: Build compact thread and business-first components**

Create components with fixed responsibilities:

```tsx
export default function AnalysisThreadCard({ thread, onContinue }: Props) {
  return (
    <article className="panel analysis-thread">
      <h3>Analysis thread</h3>
      {/* original question, understanding, clarification, answer, resolved question */}
    </article>
  );
}
```

`RunResult` should select `const product = result.product_result ?? result` and render:

1. `AnalysisThreadCard`
2. `BusinessAnswerCard`
3. `EvidencePanel`
4. `ChartArtifactGallery`
5. `TechnicalDetailsDisclosure`

`TechnicalDetailsDisclosure` must use `<details>` closed by default.

- [ ] **Step 6: Remove initial SQL from primary workbench**

Keep initial SQL available only inside a collapsed "advanced input" disclosure so the Analysis Workbench is business-first.

- [ ] **Step 7: Run focused frontend tests**

Run:

```bash
cd frontend && npm test -- workspace-flow.test.tsx
cd frontend && npm run build
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/components/AnalysisRunner.tsx frontend/components/RunResult.tsx frontend/components/WorkspaceReadinessHeader.tsx frontend/components/AnalysisThreadCard.tsx frontend/components/BusinessAnswerCard.tsx frontend/components/EvidencePanel.tsx frontend/components/ChartArtifactGallery.tsx frontend/components/TechnicalDetailsDisclosure.tsx frontend/lib/api.ts frontend/tests/workspace-flow.test.tsx
git commit -m "feat: build p13 analysis workbench ui"
```

### Acceptance

- Original question, system understanding, clarification, user answer, resolved question, and continue/edit controls appear in one compact card.
- Business answer appears before SQL and raw rows.
- SQL, raw rows, trace, provider metadata, and validation logs are collapsed by default.
- Users can continue from a pending clarification by entering only the missing answer.

---

## Task P13-H5: Reports UI Polish And Business Markdown

### Goal

Make reports read like business reports in UI and Markdown while keeping SQL, internal section prompts, trace nodes, raw rows, and provider metadata available only in a collapsed technical appendix.

### Files

- Modify `workspaces/report_models.py`
- Modify `workspaces/report_runner.py`
- Modify `workspaces/report_markdown.py`
- Modify `frontend/components/ReportViewer.tsx`
- Modify `frontend/components/ReportSection.tsx`
- Create `frontend/components/ReportTechnicalAppendix.tsx`
- Modify `frontend/tests/workspace-flow.test.tsx`
- Modify `tests/test_workspace_report_runner.py`
- Modify `tests/test_workspace_report_store.py`
- Modify `tests/test_p12_live_deepseek_workspace_report.py`

### TDD Steps

- [ ] **Step 1: Update report runner tests for separated appendix**

In `tests/test_workspace_report_runner.py`, change assertions:

```python
assert saved["sections"][0]["summary"] == "Section answer 1"
assert saved["sections"][0]["technical_details"]["sql"].startswith("SELECT channel")
assert saved["sections"][0]["technical_details"]["trace_nodes"] == ["question_understanding_agent", "sql_reviewer_agent", "sql_executor_node", "visualization_agent"]
assert "SELECT channel" not in saved["sections"][0]["summary"]
```

- [ ] **Step 2: Update Markdown tests**

In `tests/test_workspace_report_store.py`:

```python
assert "## Executive Summary" in markdown
assert "## Technical Appendix" in markdown
assert "<details>" in markdown
assert "```sql" in markdown
assert markdown.index("## Executive Summary") < markdown.index("## Technical Appendix")
```

- [ ] **Step 3: Update frontend report tests**

In `frontend/tests/workspace-flow.test.tsx`:

```tsx
expect(screen.getByText("Paid search led revenue.")).toBeTruthy();
expect(screen.queryByText(/SELECT channel/)).toBeNull();
expect(screen.queryByText(/provider_called/)).toBeNull();
expect(screen.getByRole("button", { name: "Technical appendix" })).toBeTruthy();
```

- [ ] **Step 4: Run failing tests**

Run:

```bash
python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_store.py tests/test_workspace_report_api.py -q
cd frontend && npm test -- workspace-flow.test.tsx
```

Expected: fail until model and UI separation are implemented.

- [ ] **Step 5: Add report technical fields**

In `ReportSection`, add:

```python
technical_details: dict[str, Any] = field(default_factory=dict)
business_artifacts: list[dict[str, Any]] = field(default_factory=list)
```

In `_section_from_analysis_result()`, keep legacy `sql`, `rows_preview`, `provider_metadata`, and `trace_nodes` for compatibility, but also populate:

```python
technical_details={
    "internal_question": question,
    "purpose": section_plan["purpose"],
    "sql": generated_sql,
    "rows_preview": rows_preview,
    "provider_metadata": _provider_metadata(analysis_result),
    "trace_nodes": _trace_nodes(analysis_result.get("trace") or []),
}
```

- [ ] **Step 6: Render business report first in Markdown**

Modify `render_report_markdown()` order:

1. title
2. report goal
3. executive summary
4. business sections with summary, evidence notes, chart artifacts
5. Markdown download remains same endpoint
6. `## Technical Appendix` with `<details>` per section

- [ ] **Step 7: Polish report UI**

`ReportViewer` main body displays:

- title, goal, status, type
- progress summary from status and completed/failed counts
- executive summary
- section navigation
- business sections
- Markdown download
- `ReportTechnicalAppendix` closed by default

`ReportSection` main body displays only title, status, summary, evidence notes, and chart artifacts.

- [ ] **Step 8: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_workspace_report_runner.py tests/test_workspace_report_store.py tests/test_workspace_report_api.py -q
cd frontend && npm test -- workspace-flow.test.tsx
```

Expected: pass.

- [ ] **Step 9: Commit**

```bash
git add workspaces/report_models.py workspaces/report_runner.py workspaces/report_markdown.py frontend/components/ReportViewer.tsx frontend/components/ReportSection.tsx frontend/components/ReportTechnicalAppendix.tsx frontend/tests/workspace-flow.test.tsx tests/test_workspace_report_runner.py tests/test_workspace_report_store.py tests/test_workspace_report_api.py tests/test_p12_live_deepseek_workspace_report.py
git commit -m "feat: polish business report reader"
```

### Acceptance

- Report main UI does not show internal section prompts, SQL, provider metadata, trace nodes, or raw rows.
- Technical appendix is available and collapsed by default.
- Markdown download is preserved and business-first.
- Report status/progress is clear for completed, partial, failed, and running states.

---

## Task P13-H6: Data Settings UI

### Goal

Add a Data Settings product surface for data source management, field profiling, semantic layer, product/live model mode, and safety/audit boundaries.

### Files

- Create `frontend/app/workspaces/[workspaceId]/settings/page.tsx`
- Create `frontend/components/DataSettings.tsx`
- Modify `frontend/components/DatasetManager.tsx`
- Modify `frontend/components/ProfileSummary.tsx`
- Modify `frontend/components/SemanticLayerWorkspace.tsx`
- Modify `frontend/lib/api.ts`
- Modify `api/app.py`
- Modify `api/models.py`
- Test `frontend/tests/workspace-flow.test.tsx`
- Test `frontend/tests/api-client.test.ts`
- Test `tests/test_workspace_settings_api.py`

### TDD Steps

- [ ] **Step 1: Write settings API test**

Add `tests/test_workspace_settings_api.py`:

```python
def test_workspace_settings_returns_readiness_and_safety_status(tmp_path):
    from fastapi.testclient import TestClient
    from api.app import create_app
    from workspaces.store import WorkspaceStore

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace_id = store.create_workspace("Settings Workspace")["workspace_id"]
    client = TestClient(create_app(workspace_store=store))

    response = client.get(f"/api/workspaces/{workspace_id}/settings")

    assert response.status_code == 200
    settings = response.json()
    assert settings["workspace_id"] == workspace_id
    assert "data_sources" in settings
    assert "profile" in settings
    assert "semantic_layer" in settings
    assert "model_mode" in settings
    assert settings["safety"]["sql_review"] == "enabled"
    assert settings["safety"]["trace_available"] == "enabled"
```

- [ ] **Step 2: Write frontend settings test**

In `frontend/tests/workspace-flow.test.tsx`:

```tsx
it("renders data settings sections", async () => {
  vi.mocked(getWorkspaceSettings).mockResolvedValue({
    workspace_id: "ws_1",
    data_sources: { sources: [{ name: "orders.csv", imported_tables: ["orders"] }] },
    profile: { status: "ready", tables: [{ table_name: "orders", row_count: 10, columns: [{ name: "revenue" }] }] },
    semantic_layer: { status: "ready", metrics: [{ name: "sum_revenue" }], dimensions: [{ name: "channel" }] },
    model_mode: { product_live_mode: true, provider_features: { insight_drafting: true } },
    safety: { sql_review: "enabled", sensitive_field_blocking: "enabled", trace_available: "enabled", technical_details_policy: "collapsed_by_default" },
  });

  render(<DataSettings workspaceId="ws_1" />);

  expect(await screen.findByText("Data sources")).toBeTruthy();
  expect(screen.getByText("Field profile")).toBeTruthy();
  expect(screen.getByText("Semantic layer")).toBeTruthy();
  expect(screen.getByText("Product/live mode")).toBeTruthy();
  expect(screen.getByText("Safety and audit")).toBeTruthy();
});
```

- [ ] **Step 3: Run failing tests**

Run:

```bash
python3 -m pytest tests/test_workspace_settings_api.py -q
cd frontend && npm test -- workspace-flow.test.tsx api-client.test.ts
```

Expected: fail until settings API/client/components exist.

- [ ] **Step 4: Add backend settings endpoint**

In `api/app.py`:

```python
@app.get("/api/workspaces/{workspace_id}/settings", response_model=WorkspaceSettingsResponse)
def get_workspace_settings(workspace_id: str) -> dict:
    workspace = store.get_workspace(workspace_id)
    return build_workspace_settings(store, workspace)
```

Add helper in a small file if `api/app.py` becomes crowded:

```python
def build_workspace_settings(store: WorkspaceStore, workspace: dict) -> dict:
    return {
        "workspace_id": workspace["workspace_id"],
        "data_sources": {"sources": workspace.get("sources", [])},
        "profile": load_profile_status(workspace["profile_path"]),
        "semantic_layer": load_semantic_layer_status(workspace["semantic_layer_path"]),
        "model_mode": product_mode_status(),
        "safety": {
            "sql_review": "enabled",
            "sensitive_field_blocking": "enabled",
            "trace_available": "enabled",
            "technical_details_policy": "collapsed_by_default",
        },
    }
```

- [ ] **Step 5: Add frontend client and route**

In `frontend/lib/api.ts`:

```ts
export async function getWorkspaceSettings(workspaceId: string): Promise<WorkspaceSettings> {
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/settings`);
  return parseJsonResponse(response, "Failed to load workspace settings");
}
```

Create route:

```tsx
export default function WorkspaceSettingsPage({ params }: { params: { workspaceId: string } }) {
  return <DataSettings workspaceId={params.workspaceId} />;
}
```

- [ ] **Step 6: Build DataSettings component**

`DataSettings` must render five sections with concrete fields:

- Data sources: source name, type, imported tables, upload/import entry
- Field profile: table name, row count, column name, inferred roles
- Semantic layer: metrics, dimensions, entities, time fields
- Product/live mode: mode state, provider feature coverage
- Safety and audit: SQL review, sensitive field blocking, trace availability, technical detail policy

- [ ] **Step 7: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_workspace_settings_api.py -q
cd frontend && npm test -- workspace-flow.test.tsx api-client.test.ts
cd frontend && npm run build
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add api/app.py api/models.py frontend/app/workspaces/[workspaceId]/settings/page.tsx frontend/components/DataSettings.tsx frontend/components/DatasetManager.tsx frontend/components/ProfileSummary.tsx frontend/components/SemanticLayerWorkspace.tsx frontend/lib/api.ts tests/test_workspace_settings_api.py frontend/tests/workspace-flow.test.tsx frontend/tests/api-client.test.ts
git commit -m "feat: add data settings surface"
```

### Acceptance

- Data Settings exposes data sources, field profile, semantic layer, model/product-live mode, and safety/audit boundaries.
- It does not perform auth/RBAC, deployment, SaaS integration, scheduled reports, PDF/PPT, or chat work.
- Product/live mode is visible as a status; provider flags are not exposed as a confusing checklist.

---

## Task P13-H7: Chart Product Quality And Frontend Display

### Goal

Fix Chinese font rendering, add units/value labels/business annotations, and display chart images in the frontend instead of only showing file paths.

### Files

- Modify `visualization/chart_renderer.py`
- Modify `visualization/chart_validator.py`
- Modify `agents/visualization_agent.py`
- Modify `visualization_delivery/adapters.py`
- Modify `tools/external_visualization_tool.py` if passthrough fields are needed
- Modify `api/app.py`
- Modify `frontend/components/ChartArtifactGallery.tsx`
- Modify `frontend/components/ReportSection.tsx`
- Test `tests/test_visualization_intelligence.py`
- Test `tests/test_visualization_agent_external_tools.py`
- Test `tests/test_chart_product_quality.py`
- Test `frontend/tests/workspace-flow.test.tsx`

### TDD Steps

- [ ] **Step 1: Write chart renderer product quality tests**

Add `tests/test_chart_product_quality.py`:

```python
def test_chart_renderer_supports_chinese_labels_units_and_annotations(tmp_path):
    from pathlib import Path
    from visualization.chart_renderer import render_chart

    execution_result = {
        "success": True,
        "columns": ["渠道", "收入"],
        "rows": [["付费搜索", 200.0], ["自然流量", 120.0]],
    }
    spec = {
        "chart_type": "ranked_bar",
        "title": "最近 90 天渠道收入",
        "x": "渠道",
        "y": "收入",
        "unit": "万元",
        "value_label": True,
        "business_annotation": "付费搜索收入领先，适合优先复盘 ROI。",
        "required_columns": ["渠道", "收入"],
    }

    result = render_chart(execution_result, spec, output_dir=tmp_path)

    assert result["success"] is True
    assert Path(result["chart_path"]).is_file()
    assert result["chart_spec"]["unit"] == "万元"
    assert result["chart_spec"]["business_annotation"].startswith("付费搜索")
```

- [ ] **Step 2: Write artifact serving API test**

Add to `tests/test_clarification_continuation_api.py` or a new `tests/test_workspace_artifact_api.py`:

```python
def test_workspace_artifact_endpoint_serves_chart_inside_workspace(tmp_path):
    from fastapi.testclient import TestClient
    from api.app import create_app
    from workspaces.store import WorkspaceStore

    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Artifact Workspace")
    chart = Path(workspace["root_path"]) / "runs" / "run_1" / "charts" / "chart.png"
    chart.parent.mkdir(parents=True)
    chart.write_bytes(b"png")

    client = TestClient(create_app(workspace_store=store))
    response = client.get(f"/api/workspaces/{workspace['workspace_id']}/artifacts/runs/run_1/charts/chart.png")

    assert response.status_code == 200
    assert response.content == b"png"
```

- [ ] **Step 3: Write frontend chart display test**

In `frontend/tests/workspace-flow.test.tsx`:

```tsx
expect(screen.getByAltText("最近 90 天渠道收入").getAttribute("src")).toContain("/api/workspaces/ws_1/artifacts/");
expect(screen.queryByText("workspaces/ws_1/runs/run_1/charts/revenue.png")).toBeNull();
```

- [ ] **Step 4: Run failing tests**

Run:

```bash
python3 -m pytest tests/test_chart_product_quality.py tests/test_visualization_intelligence.py tests/test_visualization_agent_external_tools.py -q
cd frontend && npm test -- workspace-flow.test.tsx
```

Expected: fail until chart spec fields, font setup, labels, and image rendering are implemented.

- [ ] **Step 5: Configure CJK-capable matplotlib fonts**

In `visualization/chart_renderer.py`, add a helper:

```python
def _configure_fonts() -> None:
    plt.rcParams["font.sans-serif"] = [
        "Noto Sans CJK SC",
        "Noto Sans CJK JP",
        "Microsoft YaHei",
        "PingFang SC",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
```

Call it before rendering each chart.

- [ ] **Step 6: Add units, value labels, annotations**

Extend chart validation to preserve optional fields:

```python
for optional in ("unit", "value_label", "business_annotation"):
    validated[optional] = chart_spec.get(optional)
```

In renderer:

```python
if spec.get("unit"):
    plt.ylabel(f"{spec['y']} ({spec['unit']})")
if spec.get("value_label"):
    for bar in bars:
        axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), _format_value(bar.get_height(), spec.get("unit")), ha="center", va="bottom")
if spec.get("business_annotation"):
    plt.figtext(0.01, 0.01, str(spec["business_annotation"]), ha="left", fontsize=9)
```

- [ ] **Step 7: Return frontend-friendly chart artifact metadata**

In `workspaces/product_result_builder.py`, chart artifact objects should include:

```python
{
    "title": chart_spec.get("title") or "Chart",
    "path": artifact_path,
    "url": f"/api/workspaces/{workspace_id}/artifacts/{relative_path}",
    "unit": chart_spec.get("unit", ""),
    "business_annotation": chart_spec.get("business_annotation", ""),
    "rendering_status": "rendered",
}
```

- [ ] **Step 8: Add artifact serving endpoint**

In `api/app.py`:

```python
@app.get("/api/workspaces/{workspace_id}/artifacts/{relative_path:path}")
def get_workspace_artifact(workspace_id: str, relative_path: str) -> FileResponse:
    artifact_path = store.resolve_workspace_path(workspace_id, relative_path)
    if not artifact_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(artifact_path)
```

- [ ] **Step 9: Render images in frontend**

`ChartArtifactGallery` should render:

```tsx
<figure>
  <img src={artifact.url} alt={artifact.title} />
  {artifact.business_annotation ? <figcaption>{artifact.business_annotation}</figcaption> : null}
</figure>
```

Keep path visible only in technical details.

- [ ] **Step 10: Run focused tests**

Run:

```bash
python3 -m pytest tests/test_chart_product_quality.py tests/test_visualization_intelligence.py tests/test_visualization_agent_external_tools.py tests/test_workspace_artifact_api.py -q
cd frontend && npm test -- workspace-flow.test.tsx
cd frontend && npm run build
```

Expected: pass.

- [ ] **Step 11: Commit**

```bash
git add visualization/chart_renderer.py visualization/chart_validator.py agents/visualization_agent.py visualization_delivery/adapters.py tools/external_visualization_tool.py api/app.py workspaces/product_result_builder.py frontend/components/ChartArtifactGallery.tsx frontend/components/ReportSection.tsx tests/test_chart_product_quality.py tests/test_workspace_artifact_api.py tests/test_visualization_intelligence.py tests/test_visualization_agent_external_tools.py frontend/tests/workspace-flow.test.tsx
git commit -m "feat: improve chart product quality"
```

### Acceptance

- Chinese labels render without missing-glyph warnings in the P13 chart tests.
- Charts include units, value labels, and business annotations when provided.
- Frontend shows chart images through workspace-validated artifact URLs.
- File paths remain available in technical details, not as the main chart UI.

---

## Task P13-H8: Real DeepSeek Product Acceptance

### Goal

Add opt-in live DeepSeek acceptance that verifies question understanding, clarification continuation, SQL planning, SQL candidate, insight drafting, visualization, and readable final business answer quality while keeping no-key mode runnable.

### Files

- Modify `tests/test_p11_live_deepseek_workspace_analysis.py`
- Create `tests/test_p13_live_deepseek_product_acceptance.py`
- Modify `tests/test_p12_live_deepseek_workspace_report.py`
- Modify `README.md`
- Modify `DEVELOPMENT_PLAN.md`
- Modify `DEVELOPMENT_STATUS.md`

### TDD Steps

- [ ] **Step 1: Add answer readability helper**

In `tests/test_p13_live_deepseek_product_acceptance.py`:

```python
def _assert_business_answer_readable(answer: dict) -> None:
    text = " ".join(str(answer.get(key, "")) for key in ("headline", "summary"))
    assert len(text.strip()) >= 20
    assert "建议" in text or "recommend" in text.lower() or answer.get("next_actions")
    assert "channel=" not in text
    assert "revenue=" not in text
    assert not text.strip().startswith("1.")
```

- [ ] **Step 2: Add live product analysis test**

```python
@pytest.mark.skipif(os.getenv("INSIGHTFLOW_LIVE_DEEPSEEK_TESTS") != "1", reason="Live DeepSeek tests are opt-in.")
def test_live_deepseek_product_analysis_uses_full_provider_chain(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_PRODUCT_LIVE_MODE", "1")
    _require_live_deepseek()
    store, workspace = _prepared_business_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="分析最近 90 天各渠道收入、投放成本和 ROI，告诉我哪个渠道应该加预算，并生成图表。",
    )

    assert result["status"] == "completed"
    assert result["question_understanding"]["provider_called"] is True
    assert result["sql_planning"]["provider_called"] is True
    assert result["llm_sql_enhancement"]["provider_called"] is True
    assert result["insight"]["provider_called"] is True
    assert result["visualization_trace"]["provider_called"] is True
    _assert_business_answer_readable(result["product_result"]["business_answer"])
```

- [ ] **Step 3: Add live clarification continuation test**

```python
def test_live_deepseek_clarification_continuation_resolves_and_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_PRODUCT_LIVE_MODE", "1")
    _require_live_deepseek()
    store, workspace = _prepared_business_workspace(tmp_path)

    first = run_workspace_analysis(store=store, workspace_id=workspace["workspace_id"], user_question="帮我分析渠道表现")
    assert first["status"] == "waiting_for_clarification"

    pending = PendingClarificationStore(store).create_pending_run(
        workspace_id=workspace["workspace_id"],
        run_id=first["run_id"],
        original_question="帮我分析渠道表现",
        question_understanding=first["question_understanding"],
        clarification_question=first["clarification_questions"][0],
        raw_result=first,
    )
    resolved = resolve_question(
        original_question=pending["original_question"],
        clarification_question=pending["clarification_question"],
        clarification_answer="最近 90 天，按渠道比较收入和 ROI",
        understanding=pending["question_understanding"],
    )
    second = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question=resolved,
        original_question=pending["original_question"],
        clarification_question=pending["clarification_question"],
        clarification_answer="最近 90 天，按渠道比较收入和 ROI",
        resolved_question=resolved,
    )

    assert second["status"] == "completed"
    assert second["product_result"]["question_thread"]["resolved_question"] == resolved
    _assert_business_answer_readable(second["product_result"]["business_answer"])
```

- [ ] **Step 4: Keep no-key mode explicit**

Add a non-live test:

```python
def test_product_live_no_key_mode_does_not_break_workspace_analysis(monkeypatch, tmp_path):
    monkeypatch.setenv("INSIGHTFLOW_PRODUCT_LIVE_MODE", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    store, workspace = _simple_workspace(tmp_path)
    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace["workspace_id"],
        user_question="按渠道汇总收入",
        initial_sql="SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
    )
    assert result["execution_result"]["success"] is True
```

- [ ] **Step 5: Run non-live tests**

Run:

```bash
python3 -m pytest tests/test_p13_live_deepseek_product_acceptance.py -q
```

Expected: skip live tests when `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS` is unset and pass no-key mode test.

- [ ] **Step 6: Run live test manually with DeepSeek credentials**

Run:

```bash
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p13_live_deepseek_product_acceptance.py -q
```

Expected: live product acceptance passes and proves provider-backed insight drafting participates.

- [ ] **Step 7: Commit**

```bash
git add tests/test_p13_live_deepseek_product_acceptance.py tests/test_p11_live_deepseek_workspace_analysis.py tests/test_p12_live_deepseek_workspace_report.py README.md DEVELOPMENT_PLAN.md DEVELOPMENT_STATUS.md
git commit -m "test: add p13 live deepseek product acceptance"
```

### Acceptance

- Live DeepSeek acceptance covers question understanding, clarification continuation, SQL planning, SQL candidate, insight drafting, and visualization.
- Final product answer is readable business prose and not a parameter dump.
- No-key mode remains runnable and deterministic tests do not require API keys.
- P11/P12 live tests continue to pass or are updated to the product/live mode flag.

---

## Task P13-H9: Documentation, Regression, Artifact Audit, And Final Verification

### Goal

Update current product documentation, run full backend/frontend verification, and audit generated artifacts without committing runtime outputs.

### Files

- Modify `README.md`
- Modify `DEVELOPMENT_PLAN.md`
- Modify `DEVELOPMENT_STATUS.md`
- No generated artifacts committed
- Test all P13-relevant backend and frontend suites

### TDD Steps

- [ ] **Step 1: Update docs with final P13 behavior**

Update README current status to:

```text
P13 Business Answer And Product UX is complete through Analysis Workbench, clarification continuation, business-facing answers, report reader polish, Data Settings, chart product quality, and live DeepSeek product acceptance.
```

Add product/live command:

```bash
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p13_live_deepseek_product_acceptance.py -q
```

- [ ] **Step 2: Update status and phase tracker**

In `DEVELOPMENT_PLAN.md`, mark P13-H1 through P13-H9 complete only after their commits pass verification.

In `DEVELOPMENT_STATUS.md`, update current snapshot:

```text
Current phase | P13 complete
Current task | Final verification complete
Next planned task | Decide next product phase
```

- [ ] **Step 3: Run targeted backend tests**

Run:

```bash
python3 -m pytest tests/test_product_result_builder.py tests/test_pending_clarification_store.py tests/test_clarification_continuation_api.py tests/test_business_answer_quality.py tests/test_product_live_mode.py tests/test_workspace_settings_api.py tests/test_chart_product_quality.py -q
python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py tests/test_workspace_report_store.py -q
```

Expected: pass.

- [ ] **Step 4: Run full backend regression**

Run:

```bash
python3 -m pytest -q
```

Expected: pass, with opt-in live tests skipped unless enabled.

- [ ] **Step 5: Run frontend verification**

Run:

```bash
cd frontend && npm test
cd frontend && npm run build
```

Expected: pass.

- [ ] **Step 6: Run live DeepSeek acceptance when credentials are available**

Run:

```bash
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p13_live_deepseek_product_acceptance.py -q
```

Expected: pass. If no key is available, final status must explicitly say the live acceptance was not run locally.

- [ ] **Step 7: Audit forbidden generated artifacts and restored legacy paths**

Run:

```bash
git status --short
git ls-files .env .venv frontend/node_modules frontend/.next .pytest_cache reports/charts logs/traces workspaces eval/report.md data/action_ops.db .superpowers
rg -n "streamlit run app.py|api/run_manager|chart_agent|visualization_planner|chart_tool|eval/run_eval.py|powerbi_publisher_mock" README.md DEVELOPMENT_PLAN.md DEVELOPMENT_STATUS.md api frontend graph agents workspaces tests
```

Expected:

- No `.env`, API keys, generated databases, generated reports, generated charts, generated traces, `.superpowers/`, or runtime workspace outputs are staged.
- `docs/superpowers/plans/*` remains excluded from normal generated-artifact commits except for this explicitly requested plan document.
- Any old-term hits are historical docs/tests or tool-catalog boundary tests, not restored product paths.

- [ ] **Step 8: Commit docs and final status**

```bash
git add README.md DEVELOPMENT_PLAN.md DEVELOPMENT_STATUS.md
git commit -m "docs: complete p13 product ux"
```

### Acceptance

- Full backend tests pass.
- Frontend tests and build pass.
- Live DeepSeek P13 acceptance passes when credentials are configured.
- Artifact audit confirms no forbidden generated outputs are committed.
- Docs describe P13 as Analysis Workbench plus future-compatible Business Q&A data model, not a full chat product.

---

## Suggested Verification Commands

Run during development:

```bash
python3 -m pytest tests/test_product_result_builder.py tests/test_pending_clarification_store.py tests/test_clarification_continuation_api.py tests/test_business_answer_quality.py tests/test_product_live_mode.py tests/test_workspace_settings_api.py tests/test_chart_product_quality.py -q
python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_workspace_report_runner.py tests/test_workspace_report_api.py tests/test_workspace_report_store.py -q
cd frontend && npm test
cd frontend && npm run build
```

Run before claiming P13 completion:

```bash
python3 -m pytest -q
cd frontend && npm test
cd frontend && npm run build
set -a; [ -f .env ] && source .env; set +a; \
INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1 \
INSIGHTFLOW_PRODUCT_LIVE_MODE=1 \
python3 -m pytest tests/test_p13_live_deepseek_product_acceptance.py -q
```

## Self-Review

### P13 Design Coverage

- Product output model is covered in P13-H1.
- Clarification continuation, pending run storage, continuation API, resolved question, and trace fields are covered in P13-H2.
- Business answer quality, provider-backed insight drafting, product/live mode, and raw dump rejection are covered in P13-H3.
- Analysis Workbench compact integrated thread and collapsed technical details are covered in P13-H4.
- Reports UI polish, hidden internal prompts/provider metadata, progress, and Markdown download are covered in P13-H5.
- Data Settings source/profile/semantic/model/safety sections are covered in P13-H6.
- Chinese chart fonts, units, labels, annotations, and image display are covered in P13-H7.
- Real DeepSeek acceptance for question understanding, continuation, SQL planning/candidate, insight drafting, visualization, and readable answers is covered in P13-H8.
- Final docs, regressions, and artifact audit are covered in P13-H9.

### Scope Guardrails

- Business Q&A Mode remains a future-compatible data model consideration only; this plan does not implement a full chat product.
- The plan does not include real SaaS integrations, auth/RBAC, deployment, scheduled reports, PDF export, or PPT export.
- The plan does not restore Streamlit, old ecommerce-only demo flows, old eval product paths, `chart_agent`, `visualization_planner`, or `chart_tool`.
- Guarded SQL review, deterministic SQL execution, evidence validation, visualization tool policy, trace persistence, and technical audit visibility remain intact.

### Placeholder Scan

- The plan contains no placeholder markers and no open-ended "optimize frontend" work.
- Every task names specific files, tests, commands, and acceptance checks.
- Every task is independently checkable and commit-sized.
