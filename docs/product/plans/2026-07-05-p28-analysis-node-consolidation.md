# P28 - Analysis Workbench Node Consolidation

Historical / Superseded note: this phase record predates P33-H2. Mentions of `final_answer_composer` or old answer consistency helpers describe the P28/P23-era design and are not current active Analysis Workbench paths. P33-H2 deleted `agents/final_answer_composer.py` and `workspaces/answer_consistency.py`; final Analysis Workbench answers now flow through BusinessAnswerAgent, and chart annotation leak cleanup lives in `workspaces/chart_annotation_safety.py`.

Date: 2026-07-05

P28 is the next Analysis Workbench hardening phase after P27. P27 made the workflow easier to understand as multi-agent collaboration, but live DeepSeek testing showed the analysis path can still spend too many provider calls on adjacent responsibilities. P28 should reduce repeated LLM work by consolidating overlapping nodes, while keeping the current evidence and safety boundaries intact.

This phase is intentionally conservative. It does not introduce a new aggressive fast/slow routing system, does not make fast facts completely model-free, and does not change Report Center into an Analysis Workbench wrapper. The goal is to simplify the current path first.

## Current Problem

The current Analysis Workbench path is product-correct but still has duplicated boundaries:

```text
用户提问
-> 问题理解，大模型
-> 追问判断
-> SQL 规划，大模型
-> 分析规划，大模型
-> Schema 查询
-> 指标匹配
-> SQL 候选生成，大模型
-> SQL 安全审核
-> SQL 执行
-> 证据校验
-> 洞察生成，大模型
-> 回答审查，可能大模型
-> 最终回答生成，可能大模型
-> 声明分类，大模型
-> 证据审计
-> 图表生成，按需大模型
-> 保存结果
```

The expensive overlap is mainly in three places:

- `sql_planning_router_agent` and `analysis_planner_agent` both plan evidence/query strategy.
- `insight_agent`, `answer_reviewer`, and `final_answer_composer` all participate in shaping the same final business answer.
- `insight_claim_typer_agent` and `evidence_auditor_agent` both classify/check answer claims against evidence.

P28 should remove this duplicated provider work without weakening these required boundaries:

- SQL safety review remains non-bypassable.
- SQL execution remains a deterministic tool call.
- Evidence validation and `QuestionEvidencePack` remain required.
- Hard facts must still be checked against evidence.
- Product-facing answers must stay Chinese, business-readable, and free of raw SQL, raw rows, provider metadata, prompt ids, trace ids, and internal ids.

## Target Path

After P28, the normal complex Analysis Workbench path should read like this:

```text
用户提问
-> 问题理解，大模型
-> 追问判断
-> 证据规划，大模型
-> 数据上下文查询
-> SQL 候选生成，大模型或安全工具路径
-> SQL 安全审核
-> SQL 执行
-> 证据校验
-> 业务回答生成，大模型
-> 确定性证据审计
-> 图表生成，按需大模型
-> 保存结果
```

Fast factual questions should keep the P21/P27 fast-fact behavior, but P28 should not make them fully model-free by default. A simple factual question may still use a model for the final concise business wording when that improves readability. The immediate P28 win is to remove repeated planning/review/classification calls, not to build a fragile no-model fast path.

## Expected Provider Call Reduction

Before P28, a complex analysis run can call the provider roughly here:

```text
question_understanding
sql_planning
analysis_planning
sql_candidate
insight_drafting
answer_reviewer
final_answer_composer
claim_typing
visualization, when requested
```

After P28, the target provider calls are:

```text
question_understanding
evidence_planning
sql_candidate
business_answer
visualization, only when requested or clearly chartable
```

In normal complex analysis, this should reduce repeated provider calls from roughly seven or eight to roughly four or five, depending on whether visualization is needed. Fast facts should continue to skip the heavy business-answer chain and visualization unless explicitly requested.

## Scope

P28 does:

- Merge SQL planning and analysis planning into one Evidence Planning surface.
- Keep schema lookup and metric lookup as deterministic tool steps, either inside Evidence Agent or behind a clear Data Context helper.
- Merge insight drafting, answer review, and final answer composition into one Business Answer generation surface.
- Move claim typing into the Business Answer output contract where practical.
- Keep Evidence Auditor as a deterministic hard-fact checker over `QuestionEvidencePack`, candidate claims, and answer output.
- Keep visualization on-demand or conditional as in P27.
- Add tests that prove provider call count and trace shape are simpler for representative fast-fact and complex questions.
- Run at least one real DeepSeek acceptance after the phase to verify the final output still reads naturally and remains evidence-backed.
- Delete old compatibility wrappers, dead prompt flags, unused tests, and stale documentation that conflict with the new current path.

P28 does not:

- Rewrite Report Center.
- Route Report Center through Analysis Workbench nodes.
- Restore stitched report sections.
- Add external SaaS integrations.
- Add vector search or semantic similarity cache.
- Add a fully model-free fast-fact system.
- Add keyword-heavy business rule trees.
- Remove SQL review, SQL execution, evidence validation, `QuestionEvidencePack`, or `AuditResult`.
- Preserve old paths merely for compatibility if the current product no longer needs them.

## H Tasks

### P28-H1 - Evidence Planning Consolidation

Goal: replace the duplicated SQL planning plus analysis planning sequence with a single Evidence Planning surface used by Analysis Workbench.

Status: Complete on 2026-07-05. The active Analysis Workbench path now calls `agents/evidence_planning.py` once from `workspaces/evidence_agent.py`, emits one `evidence_planning` workbench tool call before schema/metric lookup, keeps provider-backed SQL planning validation/fallback as the single planning provider surface, and fills deterministic scenario/context fields without calling a separate `analysis_planner_agent` provider. SQL review, SQL execution, evidence validation, `QuestionEvidencePack`, fast facts, and Report Center independence remain unchanged.

Implementation direction:

- Introduce or refactor a single `evidence_planning` contract that outputs:
  - task type;
  - metrics;
  - dimensions;
  - time range;
  - filters;
  - comparison scope;
  - query strategy;
  - chart intent;
  - missing evidence limits.
- Reuse existing question understanding and `AnalysisTask` as inputs.
- Keep deterministic fallback behavior for no-key mode.
- Keep provider output validated and normalized before downstream SQL candidate generation.
- Update traces and workbench tool calls so users see one evidence-planning step instead of two overlapping planning steps.
- Remove or deprecate the old active double-call path once tests prove the new path works.

Acceptance:

- Existing analysis questions still reach SQL review/execution/evidence validation.
- Representative complex questions call one planning provider surface, not both SQL planning and analysis planning.
- Fast facts still work.
- Report Center tests prove it remains independent.

### P28-H2 - Business Answer Consolidation

Goal: make one Business Answer Agent own final business wording instead of chaining separate model-backed insight drafting, answer reviewing, and final composing in normal successful cases.

Status: Complete on 2026-07-05. The active Analysis Workbench standard/deep path now calls one Business Answer generation surface, runs deterministic answer review/repair locally, emits candidate claims with optional categories for the Evidence Auditor, and no longer calls normal-path provider-backed `insight_agent`, `answer_reviewer`, `final_answer_composer`, or claim-typing surfaces. Fast facts remain on the lightweight composer path, and Report Center remains independent.

Implementation direction:

- Define one provider-backed business-answer prompt/schema that returns:
  - `headline`;
  - `direct_answer`;
  - `why`;
  - `evidence_bullets`;
  - `recommendations`;
  - `caveats`;
  - `confidence`;
  - `candidate_claims`;
  - optional claim categories such as hard fact, inference, recommendation, and data limit.
- Keep deterministic answer checks inside the agent after provider output.
- If provider output fails schema validation or hard fact checks, allow one repair/rebuild path rather than always running separate reviewer and final composer calls.
- Keep no-key fallback useful and Chinese.
- Keep product-facing answer output free of technical internals.

Acceptance:

- Complex answers remain natural Chinese business responses.
- Hard facts still match returned evidence.
- Recommendations can use reasonable business inference, but hard numbers and rankings must be evidence-backed.
- Normal successful complex answers should not call separate answer reviewer and final composer provider steps.

### P28-H3 - Claim Typing And Evidence Audit Simplification

Goal: stop using a separate model call just to classify claims when the Business Answer Agent can emit claim categories and the Evidence Auditor can deterministically check hard facts.

Status: Complete on 2026-07-05. Business Answer candidate claim categories are now the main claim-classification source on the Analysis Workbench path. Evidence Auditor no longer accepts or calls a claim typing provider; when categories are missing it deterministically rebuilds auditable hard facts, reasonable inferences, recommendations, and data limits from the `business_answer` structure. Hard facts are validated against `QuestionEvidencePack`, `evidence_result`, and `execution_result`, while recommendations and business inferences remain in `AuditResult.reasonable_inferences`. The obsolete provider claim typing agent, runtime flag/builder, prompt/schema branch, live workflow test, and old state/provider metadata field were removed.

Implementation direction:

- Let Business Answer output structured claim candidates/categories.
- Make Evidence Auditor prefer deterministic validation over a separate provider claim-typing call.
- Keep `AuditResult` with supported facts, reasonable inferences, unsupported claims, data limits, and confidence.
- If claim categories are missing or malformed, rebuild them deterministically from `business_answer` fields instead of calling another provider by default.
- Remove the optional provider claim typing path unless a future phase introduces a separately justified product need.

Acceptance:

- `AuditResult` is still present for fast and complex paths.
- Unsupported hard facts are blocked or downgraded.
- Business inferences and recommendations are not over-restricted when evidence supports the direction.
- Provider trace no longer shows normal-path claim typing for every complex answer.

### P28-H4 - Cleanup, Regression, And Live Verification

Goal: close the phase with a simpler current path, no stale compatibility paths, and real-provider proof.

Status: Complete on 2026-07-05. The active Analysis Workbench path is now:

```text
question understanding / clarification
-> Evidence Planning
-> schema / metric / SQL candidate / SQL review / SQL execution / evidence validation
-> Business Answer
-> deterministic Evidence Auditor
-> optional visualization
-> save result
```

H4 cleanup removed the obsolete `agents/insight_agent.py` active entry point, the old insight/reviewer/final-composer runtime provider flags/builders, the old provider prompt surfaces, and active `insight` state compatibility writes. Historical / Superseded by P33-H2: the old note that `agents/final_answer_composer.py` remained current is no longer true; P33-H2 deleted that module. Evidence Agent now validates reviewed execution row facts before Business Answer generation, so SQL review, SQL execution, evidence validation, `QuestionEvidencePack`, and downstream `AuditResult` all remain present.

Live DeepSeek verification ran because local `.env` had `DEEPSEEK_API_KEY` plus `INSIGHTFLOW_PRODUCT_LIVE_MODE=1`. The accepted smoke question was `最近90天按门店比较销售额、毛利率和满意度，请总结表现差异、数据边界，并生成图表。` Provider-backed nodes called: question understanding, Evidence Planning (`sql_planning_router`), guarded SQL candidate, Business Answer (`business_answer`), and visualization. Tool calls were evidence planning, schema lookup, metric lookup, SQL candidate builder, SQL review, and SQL execution. Evidence validation returned `validated`; Business Answer summarized 上海旗舰店 as leading, 北京国贸店 as middle, 深圳湾店 as weaker; `AuditResult` had supported facts and reasonable inferences, no unsupported claims, data limits for missing ROI/ROAS/profit-style evidence, and medium confidence. One chart artifact was produced. Report Center was not invoked and remains independent on `ReportEvidencePack + EvidenceLedger + ReportDocument`.

Two earlier live wording attempts using `风险边界/最值得优先复盘` were rejected by provider question understanding before SQL as risk-flagged requests. That sensitivity is recorded for future prompt hardening; P28-H4 did not implement external tools or change the Report Center path.

Required checks:

```bash
python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_fast_fact_path.py tests/test_evidence_agent.py tests/test_evidence_auditor_claim_categories.py -q
python3 -m pytest tests/test_business_answer_quality.py tests/test_answer_consistency.py tests/test_workspace_report_runner.py -q
python3 -m pytest tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py -q
python3 -m pytest -q
cd frontend && npm test
cd frontend && npm run build
```

Verification result:

- `python3 -m pytest tests/test_workspace_analysis_runner.py tests/test_fast_fact_path.py tests/test_evidence_agent.py tests/test_evidence_auditor_claim_categories.py -q` -> `59 passed`
- `python3 -m pytest tests/test_business_answer_quality.py tests/test_answer_consistency.py tests/test_workspace_report_runner.py -q` -> `50 passed`
- `python3 -m pytest tests/test_p20_architecture_cleanup_boundaries.py tests/test_project_initialization.py -q` -> `9 passed`
- `python3 -m pytest -q` -> `590 passed, 11 skipped`
- `cd frontend && npm test` -> `69 passed`
- `cd frontend && npm run build` -> passed
- `git diff --check` -> passed
- tracked artifact hygiene audit -> passed

Run a real DeepSeek acceptance when local opt-in flags and key are available. The closeout must report:

- what questions were asked;
- what answers were generated;
- which provider-backed nodes were called;
- which tool calls executed;
- whether Report Center remains independent;
- whether generated artifacts stayed out of git.

Cleanup requirements:

- Delete superseded node wrappers, prompt flags, compatibility branches, and tests that only protect removed behavior.
- Keep historical development documents.
- Do not commit generated databases, workspace runs, reports, charts, traces, caches, `.env`, node modules, or build outputs.
- Use `git ls-files` to audit tracked generated artifacts.
- Run an old-path audit for deleted/superseded terms and confirm remaining hits are historical notes, negative tests, or current valid contracts.

## Definition Of Done

P28 is complete when:

- Analysis Workbench has a visibly simpler path with fewer overlapping model-backed nodes.
- Complex analysis still demonstrates real multi-agent/tool-calling collaboration:
  - question understanding;
  - evidence planning;
  - schema/metric/SQL/evidence tools;
  - business answer generation;
  - evidence audit;
  - optional visualization.
- Fast facts still stay lightweight and evidence-backed.
- Report Center remains separate and uses `ReportEvidencePack + EvidenceLedger + ReportDocument`.
- No old stitched report path, old chart agent, old action/mock path, or stale compatibility layer is restored.
- Backend regression, frontend tests/build, artifact hygiene, and live DeepSeek verification pass or are explicitly documented if live flags/key are unavailable.

P28 is complete. P29 may now plan real external tool-call/export enhancement; no external Word/PPT/PDF/飞书/企业微信/钉钉/腾讯文档 integration was implemented in P28-H4.
