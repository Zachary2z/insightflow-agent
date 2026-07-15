# P39-P44 Development Tracker

Last updated: 2026-07-15
Program status: Planned; implementation has not started
Current phase: P39 planned
Current task: Roadmap documentation complete; no P39 implementation task has started
Next planned task: P39-H1 Sensitive Data Policy And Validated Query Contract
Program plan: `docs/product/plans/2026-07-15-p39-p44-enterprise-analysis-evolution.md`

## Purpose

本文档是 P39-P44 的阶段跟进真相源，用于记录：

- 当前 Phase 和 H 任务状态。
- 每个阶段完成后真正新增的产品能力。
- 实际运行过的验证与明确跳过的验证。
- 风险、阻塞、设计决策和兼容层清理情况。
- 下一项可执行工作。

详细目标、架构、任务范围和验收标准以 Program Plan 为准；本 Tracker 不复制实现细节，只维护执行状态和证据。

## Status Legend

| Marker | Meaning |
|---|---|
| `[ ]` Planned | 已定义但尚未开始实施 |
| `[-]` In progress | 正在实施；必须指定唯一 Active Task |
| `[x]` Complete | 实现和必需验证均已完成，文档已同步 |
| `[!]` Blocked | 已满足阻塞判定条件，且没有安全的继续路径 |
| `[~]` Superseded | 被后续明确决策取代，保留历史记录 |

Do not mark a task complete until its required verification has actually run and the result is recorded in this tracker.

## Current Snapshot

| Field | Current value |
|---|---|
| Current implementation baseline | P38 complete |
| Program | P39-P44 Enterprise Analysis Evolution |
| Program state | Planned |
| Active implementation task | None |
| Next task | P39-H1 |
| Last completed implementation task | P38-H6 |
| Required first action | Add focused failing security-policy tests for the confirmed sensitive-column and `SELECT *` bypasses |
| Current product boundary | Single-host FastAPI + Next.js with local Workspace/SQLite/JSON state; no RBAC, tenant isolation, durable job control plane, or verified general data-readiness gate |
| Plan document | `docs/product/plans/2026-07-15-p39-p44-enterprise-analysis-evolution.md` |

## Phase Dependency Order

```text
P38 complete
-> P39 safety/correctness/demo truth
-> P40 import/readiness/semantic model
-> P41 analysis specification/capability/operators
-> P42 architecture cutover and legacy deletion
-> P43 durable runtime/access control
-> P44 evaluation/release closeout
```

P44 评测资产可以从 P39 开始逐步积累，但 P44 不能在 P39-P43 的产品能力尚未完成时被标记 Complete。P43 不允许提前把当前宽状态和旧 Orchestrator 直接搬进 PostgreSQL；必须先完成 P42 的 Contract 和边界收缩。

## Phase Overview

| Phase | Status | Planned capability unlocked | Entry condition | Exit evidence |
|---|---|---|---|---|
| P39 | `[ ]` Planned | 当前产品可以安全、准确、可重复地用于作品集演示 | P38 complete | Security/import/publish/demo/quality acceptance |
| P40 | `[ ]` Planned | 新结构化数据可以得到质量、语义、Join 和准备度判断 | P39 complete | Three-domain readiness and semantic golden suite |
| P41 | `[ ]` Planned | 五类核心业务分析可以可靠执行，不支持问题被澄清或拒绝 | P40 complete | Operator/evidence/capability cross-domain suite |
| P42 | `[ ]` Planned | 两个推理 Agent、强类型状态、统一 Runtime 和清晰模块边界 | P41 complete | Architecture boundaries, deletion audit, full regression |
| P43 | `[ ]` Planned | 多用户、权限、持久化任务、恢复和审计 | P42 complete | Multi-instance, tenant, cancel/recovery acceptance |
| P44 | `[ ]` Planned | 质量可量化、E2E 可复现、仓库可正式发布 | P39-P43 complete | Evaluation thresholds, release gates, public docs |

## Capability Progression

| Milestone | What the product can honestly claim |
|---|---|
| Current/P38 | 功能完整、具备证据链、部署和可观测性，但主要适合受控数据和单机运行 |
| After P39 | 能安全可信地演示现有分析、报告、导出和审批发布链路 |
| After P40 | 能理解不同结构化数据，并在分析前识别粒度、指标、关系和数据限制 |
| After P41 | 能可靠完成 KPI、趋势、周期比较、排名贡献度和异常下钻 |
| After P42 | 能通过两个推理 Agent 与确定性工具体系低成本扩展分析能力 |
| After P43 | 能支持多用户隔离、角色权限、持久化任务、取消、恢复和审计 |
| After P44 | 能用跨领域评测、E2E、安全和运行指标证明以上能力 |

### P39 Task Status

| Task | Status | Deliverable | Required closeout evidence |
|---|---|---|---|
| P39-H1 | `[ ]` Planned | PII/Column Policy、ValidatedQuery、Executor 批准边界、真实设置状态 | Bypass corpus, validator/executor integration, output leak tests |
| P39-H2 | `[ ]` Planned | 有界、冲突可见、可回滚的安全导入 | File limit, collision, rollback, path rejection tests |
| P39-H3 | `[ ]` Planned | 外部发布预览、人工审批、幂等和审计 | Approval/idempotency/partial failure tests |
| P39-H4 | `[ ]` Planned | 干净 Portfolio Demo 和端到端黄金流程 | Browser/E2E, terminology, confidence, leak acceptance |
| P39-H5 | `[ ]` Planned | 依赖、静态检查、secret scan 和 CI 质量基线 | Audit reports and CI job verification |
| P39-H6 | `[ ]` Planned | P39 清理、全量验收、文档同步和 P40 handoff | Full backend/frontend/build/smoke/security/doc closeout |

P39 completion changes:

- 用户面对的安全声明与真实实现一致。
- 已知敏感字段和 `SELECT *` 绕过关闭。
- 文件导入不再静默覆盖或留下半成品。
- 发布必须审批且重试不会重复创建结果。
- 固定 Demo 不包含旧失败记录、内部字段或明显业务表达错误。

### P40 Task Status

| Task | Status | Deliverable | Required closeout evidence |
|---|---|---|---|
| P40-H1 | `[ ]` Planned | ImportContract、Landing 分层和显式解析配置 | Deterministic import contract suite |
| P40-H2 | `[ ]` Planned | DataProfile、DataQualityReport、表粒度候选 | Quality blocker/warning regression |
| P40-H3 | `[ ]` Planned | SemanticModel v1 和安全 Metric 定义 | Additivity/ratio/snapshot/weighted-average suite |
| P40-H4 | `[ ]` Planned | JoinGraph、基数、覆盖率和膨胀验证 | PK/FK/many-to-many/multi-fact join suite |
| P40-H5 | `[ ]` Planned | DataReadinessReport 和确认 UX | Ready/needs-confirmation/blocked API+UI tests |
| P40-H6 | `[ ]` Planned | 电商、投放、客服三领域验收和旧路径删除 | Cross-domain golden results and cleanup audit |

P40 completion changes:

- 任意新结构化数据先得到数据与语义契约。
- 系统能够说明当前数据支持哪些分析、缺少什么、哪些关系需要确认。
- 单价、比率、余额、库存和累计值不会默认按 SUM 使用。
- 候选 Join 在未确认前不能进入生产 SQL。

### P41 Task Status

| Task | Status | Deliverable | Required closeout evidence |
|---|---|---|---|
| P41-H1 | `[ ]` Planned | AnalysisSpec 唯一业务契约 | Question-to-spec-to-output consistency tests |
| P41-H2 | `[ ]` Planned | CapabilityGate 和明确状态 | Missing-data/unsupported/unsafe routing suite |
| P41-H3 | `[ ]` Planned | KPI Summary 与 Trend Operators | Cross-domain KPI/trend golden tests |
| P41-H4 | `[ ]` Planned | Comparison、Rank/Contribution、Anomaly Operators | Time language, contribution, anomaly method tests |
| P41-H5 | `[ ]` Planned | EvidenceGateway 和结论等级 | Grounding and recommendation-boundary tests |
| P41-H6 | `[ ]` Planned | 中文澄清/不支持 UX、旧路由删除和 closeout | End-to-end operator and cleanup acceptance |

P41 completion changes:

- 用户的问题先被证明可分析，再进入查询。
- 五类核心分析使用明确 Operator，而不是依赖一条自由 SQL 猜测完成。
- 缺少成本、时间、实体或 Join 时，系统给出业务说明而不是生成伪结论。
- 收入排名不会直接升级成预算建议，相关性不会表达为因果。

### P42 Task Status

| Task | Status | Deliverable | Required closeout evidence |
|---|---|---|---|
| P42-H1 | `[ ]` Planned | API/Application/Domain/Infrastructure 模块边界 | Import/dependency boundary tests |
| P42-H2 | `[ ]` Planned | 强类型状态、Analysis/Report 独立 Orchestrator | State contract and product-path regression |
| P42-H3 | `[ ]` Planned | PlannerAgent 与 AnswerSynthesizer 两个推理 Agent | Agent ownership and deterministic-tool tests |
| P42-H4 | `[ ]` Planned | 启动时 Graph compile、显式依赖注入 | Lifecycle/provider reuse tests |
| P42-H5 | `[ ]` Planned | 统一 LLM Runtime | Timeout/retry/cancel/token/cost/error suite |
| P42-H6 | `[ ]` Planned | 旧 Agent/State/Provider/包装器删除和 ADR | Old-path audit, cycles, full regression |

P42 completion changes:

- Agent 名称与真实推理职责一致。
- 新增分析能力只需新增 Operator、Contract 和测试。
- Analysis Workbench 与 Report Center 不再共享一个宽状态袋。
- Provider、Prompt、重试、Token 和成本由统一 Runtime 管理。
- 被替代旧路径已删除，不形成长期双轨。

### P43 Task Status

| Task | Status | Deliverable | Required closeout evidence |
|---|---|---|---|
| P43-H1 | `[ ]` Planned | PostgreSQL 控制面与 Artifact Store Ports | Migration/store contract/integration tests |
| P43-H2 | `[ ]` Planned | Durable Job、Checkpoint、取消、恢复和幂等 | Kill/restart/duplicate/cancel acceptance |
| P43-H3 | `[ ]` Planned | Authentication、Tenant、Owner/Analyst/Viewer/Publisher RBAC | API/store/artifact authorization suite |
| P43-H4 | `[ ]` Planned | 行列级、导出、发布和审计策略 | Policy matrix and cross-tenant adversarial tests |
| P43-H5 | `[ ]` Planned | 保留、删除、加密和审批生命周期 | Retention/encryption/approval lifecycle tests |
| P43-H6 | `[ ]` Planned | 多实例与故障恢复 closeout | Two-API/multi-worker/recovery full acceptance |

P43 completion changes:

- 用户需要登录并按角色访问 Workspace。
- Tenant 数据在 API、Job、Store 和 Artifact 层隔离。
- 长任务可以离开页面、取消、重试并在重启后恢复。
- 谁访问、导出、修改、审批或发布了什么可以审计。
- 多个 API/Worker 不会重复执行同一幂等任务。

### P44 Task Status

| Task | Status | Deliverable | Required closeout evidence |
|---|---|---|---|
| P44-H1 | `[ ]` Planned | 三领域 50-100 黄金问题与质量指标 | Versioned evaluation report |
| P44-H2 | `[ ]` Planned | Prompt/PII/SQL/path/tenant/publish 攻击集 | Zero known high-risk bypass result |
| P44-H3 | `[ ]` Planned | Playwright 产品 E2E 和故障恢复场景 | Repeatable local/container acceptance |
| P44-H4 | `[ ]` Planned | GenAI 指标与分层 CI Release Gates | Metrics/cardinality/privacy and CI evidence |
| P44-H5 | `[ ]` Planned | README、Architecture、Security、Evaluation、ADR、Demo 和简历资产 | Public-doc link and artifact audit |
| P44-H6 | `[ ]` Planned | Release Candidate、版本说明和 Program closeout | All required gates and explicit skips |

P44 completion changes:

- 项目质量不再只通过测试数量表达，而有跨领域准确性、安全、Grounding、延迟和成本指标。
- 招聘者可以一键运行固定 Demo，并理解系统为什么可信。
- 公开文档明确架构、威胁模型、质量指标、已知限制和取舍。
- 项目形成一个可复现的正式 Release。

## Release Metrics

| Metric | Current baseline | P44 target | Evidence location |
|---|---|---|---|
| Golden SQL execution correctness | Not measured | >= 90% | TBD in P44-H1 |
| Metric aggregation correctness | Not measured | 100% | TBD in P44-H1 |
| Golden Join selection correctness | Not measured | >= 95% | TBD in P44-H1 |
| Evidence grounding | Not measured as a release metric | >= 95% | TBD in P44-H1 |
| Unsupported claim rate | Not measured | 0 | TBD in P44-H1 |
| Correct refusal rate | Not measured | >= 95% | TBD in P44-H1 |
| Known high-risk PII/SQL/tenant bypass | Confirmed gaps exist before P39 | 0 | TBD in P44-H2 |

Targets may be refined only through a recorded Decision Log entry with evidence; they must not be lowered merely to make a release pass.

## Risk Register

| ID | Risk | Phase | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| R1 | 新契约叠加在旧状态之上，形成第三套路径 | P40-P42 | High | 每个 H 明确替换和删除清单；P42-H6 做旧路径审计 | Open |
| R2 | SemanticModel 对当前 Demo 过拟合 | P40 | High | 三领域数据集、非常规列名、非营销 Fixture | Open |
| R3 | 自动 Join 造成事实重复或错误指标 | P40-P41 | Critical | 基数、覆盖率、膨胀检查；低置信度必须确认 | Open |
| R4 | CapabilityGate 变成关键词规则集合 | P41 | High | 绑定 Operator Requirements 和 SemanticModel，不以关键词作为最终判断 | Open |
| R5 | 架构重构破坏 Report Center 独立性 | P42 | High | 独立 Orchestrator 边界测试；共享底层不共享结果写作链路 | Open |
| R6 | PostgreSQL 只是把 JSON 宽状态原样搬过去 | P43 | High | P43 必须依赖 P42 typed contracts 完成 | Open |
| R7 | Auth 只在前端实现 | P43 | Critical | API/Store/Job/Artifact 四层授权测试 | Open |
| R8 | 评测被当前数据和 Prompt 过拟合 | P44 | High | 冻结训练/开发集与独立 holdout；记录 Prompt 版本 | Open |
| R9 | 为企业级引入过重基础设施 | All | Medium | 保持模块化单体；非必要不引入 Kafka/K8s/microservices | Open |
| R10 | 文档提前宣称能力完成 | All | High | 状态测试、实际验证 Ledger、明确 skipped | Open |

## Decision Log

| Date | Decision | Reason | Consequence |
|---|---|---|---|
| 2026-07-15 | P39-P44 作为 P38 之后的新 Program，P39 为下一计划阶段 | 现有瓶颈是数据/语义/架构/企业边界，而不是功能数量 | README、Development Plan、Status 和 Tracker 指向 P39-H1 |
| 2026-07-15 | 保留 FastAPI、Next.js、LangGraph 和模块化单体 | 当前框架能够满足目标，主要问题是边界与状态设计 | 不启动微服务/Kubernetes 重写 |
| 2026-07-15 | 核心推理 Agent 收缩为 PlannerAgent 与 AnswerSynthesizer | 其他职责主要是确定性工具和领域服务 | P42 删除伪 Agent 包装层 |
| 2026-07-15 | Analysis Workbench 与 Report Center 保持独立用例 | 两者交互和交付目标不同 | 只共享 Evidence/Policy/Artifact/LLM Runtime |
| 2026-07-15 | P39-P44 状态全部为 Planned | 本次只创建计划和跟进文档，没有实施任何 Phase | 不记录虚假完成或验证结果 |

New decisions must be appended; do not rewrite historical decisions without a superseding entry.

## Verification Ledger

当前没有 P39-P44 实现验收记录。以下结果只验证规划文档、当前状态一致性和既有产品回归，不能计作任何 H 任务完成。

Use this table for actual implementation verification:

| Date | Task | Command / environment | Result | Skipped / not covered | Evidence notes |
|---|---|---|---|---|---|
| 2026-07-15 | Roadmap documentation | `python -m pytest -q tests/test_p39_p44_roadmap_docs.py tests/test_p37_closeout_acceptance.py` | 10 passed | All P39-P44 implementation | New Plan/Tracker existence, current status, P38 closeout compatibility |
| 2026-07-15 | Documentation boundaries | Focused initialization, P17 cleanup, P26 hygiene, P37/P38 closeout, and P39-P44 roadmap selection | 33 passed | Frontend/Docker/live providers | Current-path, history, artifact, and status contracts |
| 2026-07-15 | Full backend regression | `python -m pytest -q` | 995 passed, 15 skipped | Frontend, Docker, live DeepSeek/Feishu | No P39 implementation capability inferred from this pass |
| 2026-07-15 | Diff and content hygiene | `git diff --check` plus new-doc local-path/secret-pattern scan | Passed | External link crawler | No whitespace error, local user path, or key-shaped content found |
| TBD | P39-H1 | TBD | Not run | All implementation checks | Task not started |

Rules:

- 只记录实际运行的命令与结果。
- Live DeepSeek、真实飞书、云、amd64 或多实例未运行时必须写在 Skipped。
- Full backend pass 不能替代浏览器/E2E、Docker、真实 Provider 或安全攻击集，反之亦然。
- Pass count、commit 和外部 CI URL 是时间性证据，更新时必须附日期。

## Phase Closeout Template

每个 Phase 完成时追加以下内容，不覆盖历史：

```markdown
## Pxx Closeout - YYYY-MM-DD

Status: Complete

### Product capability now available

- ...

### Contracts introduced or changed

- ...

### Old paths removed

- ...

### Verification actually run

- command: result

### Explicitly skipped or unverified

- ...

### Known limits carried forward

- ...

### Next planned task

- Pyy-H1 ...
```

Closeout must also synchronize:

- `README.md`
- `DEVELOPMENT_PLAN.md`
- `DEVELOPMENT_STATUS.md`
- Program Plan
- This Tracker

## Update Protocol

At the start of a task:

1. Confirm all earlier dependency tasks are Complete.
2. Change exactly one H task from Planned to In progress.
3. Record the Active Task in Current Snapshot.
4. Write or update focused failing tests before production edits.
5. Do not pull later H scope into the active slice.

During implementation:

1. Record material design decisions in Decision Log.
2. Preserve unrelated user changes.
3. Track files/contracts added, replaced and deleted.
4. Keep live/provider/publish behavior behind explicit gates.

At task completion:

1. Run required focused and related regression tests.
2. Record exact verification and skipped coverage.
3. Delete superseded code within the task boundary.
4. Mark Complete only after code, tests and docs agree.
5. Update Next Task without marking it In progress prematurely.

At phase completion:

1. Run phase-wide and full acceptance.
2. Complete the Phase Closeout entry.
3. Synchronize all canonical docs.
4. Confirm `git diff --check` and tracked-artifact hygiene.
5. Hand off only the next phase's first H task.
