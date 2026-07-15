# P39-P44 Enterprise Analysis Evolution

Status: Planned; implementation has not started
Date: 2026-07-15
Program range: P39-P44
Current planned phase: P39
Next planned task: P39-H1 Sensitive Data Policy And Validated Query Contract
Tracking document: `docs/product/plans/2026-07-15-p39-p44-development-tracker.md`

## Goal

P39-P44 将 InsightFlow 从“功能完整但主要适合受控数据和单机演示的 AI BI 产品”演进为“能够理解不同结构化业务数据、先判断分析是否可行、再通过确定性工具和证据约束完成分析，并具备企业运行基础和可量化质量证据的智能分析系统”。

本计划不以继续增加 Agent 数量或堆叠兼容层为目标。核心工作是重建前半段数据链路、收缩分析与 Agent 契约、补齐安全和持久化边界，并删除被新架构替代的旧路径。

目标产品定位：

> InsightFlow 是一个面向结构化业务数据的证据驱动智能分析系统，能够在不同 CSV、Excel 和数据库结构下完成数据理解、分析能力判断、常见业务分析、事实校验、可视化和报告交付。

## Why This Program Exists

P38 结束时，项目已经具备完整的 FastAPI + Next.js 产品链路、工作空间导入、数据剖析、语义层草稿、问题理解、SQL 审查与执行、Evidence Ledger、业务回答、图表、报告、Word/飞书交付、Docker/Compose 和 Prometheus/Grafana 运维能力。

当前主要瓶颈已经不再是功能数量，而是以下结构性问题：

- 导入层主要完成文件搬运，缺少格式标准化、事务性落地、冲突处理和数据准备度判断。
- 当前语义层主要依赖列名、类型、唯一值数量和少量业务词典，无法可靠表达粒度、可加性、分子分母、单位、币种和多表关系。
- 多表关系主要是名称候选，缺少主外键覆盖率、基数、Join 膨胀和路径歧义验证。
- 问题理解、SQL 规划、证据和图表之间没有一个足够强的统一 `AnalysisSpec`。
- “异常”“建议”等任务标签不等同于已经具备统计分析或决策证据。
- 当前 `AgentState` 过宽，许多确定性模块使用 Agent 命名，增加理解和维护成本。
- 分析任务依赖进程内执行与本地 JSON 状态，不能可靠取消、恢复或多实例运行。
- 认证、RBAC、多租户、行列级数据权限和外部副作用审批仍未实现。
- 现有测试数量充足，但缺少跨领域黄金问题、端到端质量指标和公开可解释的评测报告。

## Product Scope

### Stable Core Scope

P41 完成后，核心产品必须稳定支持：

- KPI 汇总。
- 时间趋势。
- 同比、环比和任意合法区间比较。
- 排名、Top-N 和贡献度。
- 维度下钻。
- 基于历史分布或同组比较的受约束异常发现。
- 多指标但粒度兼容的综合分析。
- 只引用已验证证据的业务回答和报告。

### Conditional Scope

以下能力只有在数据契约满足前置条件时才允许执行：

- 多表分析。
- ROI、ROAS、利润和利润率。
- 漏斗。
- Cohort 和留存。
- 相关性分析。

### Explicit Non-Scope

P39-P44 不承诺：

- 通用因果推断。
- 自动预测和预算优化。
- 实时流式分析或 CDC。
- 任意非结构化数据分析。
- Agent 自主写入业务系统。
- Kubernetes、服务网格或微服务拆分。
- Kafka、通用向量数据库、通用 RAG 或多模型路由平台。

不支持的问题必须返回可解释的 `unsupported` 或 `needs_*` 结果，不允许通过 LLM 猜测补齐。

## Engineering Principles

1. 数据先被理解，分析再被允许。
2. LLM 负责理解和表达，权限、计算、执行和验证由确定性系统负责。
3. Analysis Workbench 与 Report Center 保持独立产品用例，共享底层 Evidence、Policy、Artifact 和 LLM Runtime。
4. 每个新契约稳定后，在同一阶段删除被替代的旧路径；不长期维护双轨内部架构。
5. 每个 H 任务采用 red-first TDD：先证明失败，再实现最小真实路径。
6. 所有外部副作用必须显式审批、幂等和可审计。
7. 企业级优先意味着清晰边界、恢复能力和安全性，不意味着引入不必要的分布式基础设施。
8. 只报告实际运行过的验收；真实 DeepSeek、真实飞书、Docker 或发布验收未运行时必须明确记录。

## Target Product Chain

```text
CSV / Excel / approved database source
-> Landing and format normalization
-> data profiling and quality checks
-> grain/entity/time/PII inference
-> SemanticModel draft
-> JoinGraph and metric validation
-> DataReadinessReport
-> optional user confirmation
-> supported analysis capability catalog
-> question understanding
-> AnalysisSpec
-> CapabilityGate
   -> needs clarification
   -> needs semantic confirmation
   -> unsupported
   -> unsafe
   -> ready
-> Analysis Planner
-> deterministic Analysis Operator
-> PolicyEngine and ValidatedQuery
-> execution and result-quality validation
-> EvidenceBundle / Evidence Ledger
-> Answer Synthesizer
-> Claim Verifier
-> business answer / chart / report / approved delivery
```

相比当前链路，必须新增三个显式 Gate：

1. `DataReadinessReport`：判断新导入数据是否具备分析基础。
2. `CapabilityGate`：判断某个具体问题是否被当前数据和已实现方法支持。
3. `ClaimVerifier`：判断最终事实和建议是否超出 Evidence 边界。

## Target Architecture

```text
src/insightflow/
|-- api/
|   |-- routers/
|   |-- schemas/
|   `-- dependencies/
|-- application/
|   |-- analysis/
|   |-- reports/
|   `-- jobs/
|-- domain/
|   |-- ingestion/
|   |-- semantic_model/
|   |-- analysis/
|   |-- evidence/
|   `-- policies/
|-- agents/
|   |-- planner.py
|   `-- answer_synthesizer.py
|-- tools/
|   |-- catalog.py
|   |-- query.py
|   `-- charts.py
`-- infrastructure/
    |-- llm/
    |-- persistence/
    |-- observability/
    `-- publishing/
```

这是目标边界，不要求在一个提交中机械移动所有文件。每次迁移必须围绕一个可验证用例完成，并在切换后删除旧入口。

## Core Domain Contracts

### Ingestion And Readiness

```text
ImportContract
ImportedSource
ImportedTable
ImportedColumn
ImportIssue
DataProfile
DataQualityReport
DataReadinessReport
```

### Semantic Model

```text
EntityDefinition
DimensionDefinition
MetricDefinition
TimeDefinition
RelationshipDefinition
SemanticModel
JoinGraph
```

`MetricDefinition` 至少包含：公式、来源字段、业务粒度、聚合方式、可加性、单位、币种、时间字段、分子分母、去重策略、置信度和确认状态。

### Analysis

```text
AnalysisSpec
CapabilityDecision
AnalysisPlan
OperatorRequest
OperatorResult
ValidatedQuery
```

### Evidence And Output

```text
EvidenceBundle
EvidenceLedger
Claim
ClaimVerification
AnswerResult
ChartArtifact
ReportDocument
```

## Phase Summary

| Phase | Goal | User-visible outcome | Depends on |
|---|---|---|---|
| P39 | 安全、正确性与演示真实性 | 当前产品可以可信、安全地用于作品集演示 | P38 complete |
| P40 | 异构数据理解与语义层重建 | 新数据导入后能得到准备度、指标和关系确认 | P39 |
| P41 | 通用业务分析内核 | 系统能可靠执行五类核心分析并拒绝不支持问题 | P40 |
| P42 | Agent 与代码架构收缩 | 两个推理 Agent、强类型状态、清晰模块边界 | P41 |
| P43 | 企业运行与权限基础 | 多用户、持久化任务、恢复、RBAC 和审计 | P42 |
| P44 | 评测、可观测性与作品集发布 | 能用指标、E2E 和公开文档证明项目质量 | P39-P43 |

## P39: Safety, Correctness, And Portfolio Truth

Status: Planned

### Goal

关闭已经确认的安全与产品真实性缺口，使现有主链路在受支持数据上可以安全、准确、可重复地演示。P39 不提前重构完整语义层、Agent 架构或持久化平台。

### Capability After P39

用户可以安全上传受支持文件、运行现有分析、获得证据约束回答、生成报告和导出，并在明确确认后发布到飞书。设置页、安全声明、业务术语和演示数据与真实实现一致。

### P39-H1: Sensitive Data Policy And Validated Query Contract

Scope:

- 在导入/Schema 层建立 PII 标签，例如 email、phone、address、identity、payment。
- 禁止未展开和检查的 `SELECT *`。
- 检查投影、别名、函数、CTE、子查询、派生表和嵌套表达式。
- 引入 `ColumnPolicy`/`PolicyDecision`。
- `validate_sql` 输出不可变 `ValidatedQuery`，包含规范化 SQL 哈希、字段范围、策略版本和风险结果。
- Executor 只接受 `ValidatedQuery`，不能接受任意替换后的字符串。
- 结果、导出和发布层再次执行安全输出检查。
- 设置页根据真实 Policy 状态显示能力，不再无条件宣称敏感字段拦截已开启。

Required tests:

- `email`、`customer_email`、`phone_number`、大小写、引号和 Unicode 名称。
- `SELECT *`、`table.*`、别名、函数包装、CTE、Union 和子查询。
- 验证后 SQL 被替换时 Executor 拒绝执行。
- 未授权列不会出现在 Answer、Chart、Export 或 Publish Artifact。
- 设置页状态与 Policy 配置一致。

Definition of done:

- 已知 PII 绕过测试全部关闭。
- Validator 与 Executor 之间存在不可绕过的批准对象边界。
- 默认拒绝未知高风险投影，同时保留明确的业务失败说明。

### P39-H2: Safe Import And Atomic Ingestion

Scope:

- 为 CSV/Excel/SQLite 上传增加大小、行数、列数、Sheet 数和表数限制。
- 检测异常压缩比、损坏文件和不支持格式。
- 检测表名和列名清洗后的碰撞。
- 移除静默 `if_exists=replace` 行为。
- Web API 不再接受任意服务器本地 SQLite 路径；只允许上传或显式 allowlist Connector。
- 导入在临时/事务边界完成，失败不留下半导入表或错误 Source 状态。

Required tests:

- 重名表、重名列、大小写冲突和清洗后冲突。
- 超限文件、坏 Excel、空 Sheet、重复 Sheet 表名。
- 部分失败回滚，原 Workspace 数据不被覆盖。
- 路径逃逸和服务器任意文件访问被拒绝。

Definition of done:

- 导入行为是显式、可回滚、可解释的，不存在静默覆盖。

### P39-H3: Human Approval And Idempotent Publishing

Scope:

- 发布前显示安全摘要和目标平台。
- 增加明确确认步骤；未确认不能触发外部副作用。
- 为 Doc/Sheet 发布建立幂等键和审计记录。
- 重试复用已创建结果或明确进入安全恢复，不重复创建文档。
- LLM、SQL、Report Runner 均不能在发布阶段重新运行。

Required tests:

- 未确认、重复确认、网络超时、Doc 成功/Sheet 失败、重试和取消。
- 发布审计不包含凭据、完整 Prompt、SQL、原始行或本地路径。

Definition of done:

- 所有真实外部发布都经过人工审批并具备幂等与审计证据。

### P39-H4: Portfolio Demo Truth And Golden Flow

Scope:

- 建立可重复生成的 `portfolio-demo` Workspace，不提交运行时数据库或生成物。
- 清理/隔离历史失败运行和“业务回答缺失”记录。
- 修正内部字段名、Evidence Key 和技术实现名在业务页面的泄露。
- 修正同比、环比、增长率、贡献度、排名和时间范围语言。
- 统一证据置信度、回答置信度和 UI 展示。
- 回答不得在图表已存在时继续提示“需要生成图表”。
- 建立导入到 Word 导出的端到端黄金流程。

Required tests:

- 固定 Demo 的关键数字、时间比较、图表和报告结论。
- 页面无内部字段、Trace、Provider、SQL、绝对路径和 Evidence 内部标识。
- 报告建议不超过数据可以支持的决策等级。

Definition of done:

- 招聘者从头运行 Demo 时，不会看到历史脏数据、内部实现泄露或明显业务术语错误。

### P39-H5: Dependency And Quality Baseline

Scope:

- 评估并修复当前前端 production audit 中的 ECharts/PostCSS/Next.js moderate findings，不使用未经审查的强制降级或 major 跳转。
- 引入最小 Ruff、类型检查、ESLint、secret scan 和依赖审计入口。
- 将静态检查拆成可定位的 CI Job。
- 为关键安全契约设置必过 Gate。

Definition of done:

- Python production lock 没有已知漏洞。
- 前端 production audit 没有未记录的高/严重漏洞，moderate 例外必须有明确决策和截止时间。
- 静态检查不会格式化或覆盖无关用户改动。

### P39-H6: Acceptance, Cleanup, And Handoff

Scope:

- 删除被 P39 新安全/导入/发布契约替代的旧分支。
- 运行 focused、相关回归、全量后端、前端、build、Docker smoke 和安全审计。
- 同步 README、Development Plan、Development Status、本计划和 Tracker。
- 记录真实跳过的 live DeepSeek/Feishu/发布测试。

Phase exit criteria:

- 当前受支持 Demo 链路安全、准确、可重复。
- P40 可以在稳定导入边界上重建 Data Contract。

## P40: Heterogeneous Data Understanding And Semantic Model

Status: Planned

### Goal

让系统在新数据导入后先建立可验证的数据与语义契约，再决定是否允许分析。P40 解决“这份数据是什么、质量如何、可以怎样 Join、哪些指标可以怎样聚合”，不实现新的高级分析方法。

### Capability After P40

用户导入未见过的结构化数据后，可以看到表、粒度、主键候选、字段角色、指标、时间字段、PII、Join 候选、数据问题和支持能力；简单高置信度数据自动通过，复杂数据需要确认。

### P40-H1: ImportContract And Landing Layer

Scope:

- 新增 `ImportContract`、`ImportedSource`、`ImportedTable`、`ImportedColumn` 和 `ImportIssue`。
- 保存原始字段名、标准字段名、源格式、解析参数和数据版本。
- 支持显式编码、分隔符、日期格式、小数点、千分位、百分比、币种、单位和空值标记。
- 原始文件、Landing 数据和分析表分层，不能混为一个路径。
- 所有 Source 具有可追踪的导入生命周期。

Definition of done:

- 相同输入和解析配置产生确定性 Import Contract。
- 解析歧义不静默猜测，进入确认或阻断状态。

### P40-H2: DataProfile And DataQualityReport

Scope:

- Profile 行数、列数、空值率、唯一值比例、重复行、主键候选、时间范围、数值分布、常量列、类型冲突和异常值。
- 识别明细表、快照表、汇总表和维度表候选。
- 输出 `DataQualityReport`，区分 blocker、warning、info。
- 严重质量问题进入 `blocked`，普通问题进入 Answer/Report 的 Data Limits。

Definition of done:

- Data Quality 结论来自确定性统计和明确规则，不来自无法复现的模型判断。

### P40-H3: SemanticModel v1

Scope:

- 建立 Entity、Dimension、Metric、Time、Relationship 强类型定义。
- Metric 明确 additive、semi-additive、non-additive。
- 支持 sum、count、distinct count、average、weighted average、ratio 和 snapshot 语义。
- 指标绑定来源粒度、时间字段、单位、币种、分子、分母和去重策略。
- LLM 只可以提出别名和业务意义候选；确定性 Validator 负责合法性，关键语义由用户确认。

Required tests:

- price、rate、margin、balance、inventory、cumulative、distinct users 和 weighted average。
- 中英文、缩写、空格、标点和非常规字段名。

Definition of done:

- 所有启用 Metric 都有明确聚合口径，不再默认把所有数值列变成 SUM。

### P40-H4: JoinGraph And Grain Validation

Scope:

- 基于名称、类型、唯一性、值覆盖率和采样关系生成候选 Join。
- 识别一对一、一对多、多对多和不确定关系。
- 在候选阶段计算 Join Coverage、Null Rate 和行数膨胀风险。
- 定义 Fact、Dimension 和事实表之间的粒度兼容性。
- 多条路径或低置信度路径必须确认。

Required tests:

- `orders.customer_id -> customers.id`。
- 两张表都含 `user_id` 但业务实体不同。
- 多对多桥表。
- 多事实表共享维度。
- Join 后行数膨胀和重复事实。

Definition of done:

- 未确认的 Candidate Relationship 不能进入生产 SQL。

### P40-H5: DataReadiness Gate And Confirmation UX

Scope:

- 输出 `DataReadinessReport`：`ready`、`ready_with_limits`、`needs_confirmation`、`blocked`。
- 展示支持的分析、缺少的数据、待确认指标、待确认 Join 和安全风险。
- 单表高置信度数据可以自动通过。
- 复杂数据确认后生成版本化 SemanticModel；变更数据版本后重新校验。

Definition of done:

- 分析入口只接受 Ready 或明确用户确认后的数据版本。

### P40-H6: Cross-Domain Acceptance And Closeout

Scope:

- 建立电商、广告投放、客服工单至少三个非同构数据集。
- 每个数据集覆盖不同列名、语言、表数量、粒度和指标类型。
- 记录字段角色、Metric、Join 和 Readiness 黄金结果。
- 删除旧 Semantic Draft 中已经被新契约替代的默认聚合和关系逻辑。

Phase exit criteria:

- 三类数据集均能得到稳定 DataReadinessReport。
- 未确认 Join、非可加指标和错误类型不会进入分析。

## P41: General Business Analysis Kernel

Status: Planned

### Goal

建立统一 `AnalysisSpec`、`CapabilityGate` 和受约束分析算子，使系统可靠完成常见描述性和部分诊断性分析。P41 不使用自由 Agent 推理替代分析方法。

### Capability After P41

系统能够针对 Ready 数据稳定完成 KPI、趋势、周期比较、排名/贡献度和异常下钻；当数据缺少时间、成本、Join、粒度或方法前置条件时，能够澄清或明确拒绝。

### P41-H1: AnalysisSpec Contract

Scope:

- `AnalysisSpec` 统一表达目标、指标、维度、过滤、时间范围、时间粒度、比较基线、方法、决策等级和 Evidence Requirements。
- Question Understanding 只负责生成/补全 AnalysisSpec，不直接决定 SQL。
- SQL、Evidence、Chart 和 Answer 只能读取同一版本的 AnalysisSpec。

Definition of done:

- 一次分析不存在多个相互矛盾的 task/route/plan 真相源。

### P41-H2: CapabilityGate

Scope:

- 输出 `ready`、`needs_clarification`、`needs_semantic_confirmation`、`unsupported`、`unsafe`。
- 根据 SemanticModel 和 Operator Requirements 判断问题是否可执行。
- 对缺少时间、成本、分母、实体 ID、Join、样本量和已实现方法给出业务说明。

Definition of done:

- 不支持请求不会继续进入 SQL Candidate 或 Answer 生成。

### P41-H3: KPI And Trend Operators

Scope:

- 实现 `KpiSummaryOperator` 和 `TrendOperator`。
- Operator 声明所需字段、支持粒度、查询策略、证据形式、Chart 类型和降级条件。
- Trend 必须绑定明确时间字段和时间粒度。

Definition of done:

- 单指标、多指标、完整时间范围、指定时间范围和缺失时间字段行为可重复。

### P41-H4: Comparison, Contribution, And Anomaly Operators

Scope:

- 实现 `PeriodComparisonOperator`、`RankContributionOperator` 和 `AnomalyDrilldownOperator`。
- Comparison 明确当前期、基准期、绝对变化和相对变化。
- Contribution 使用兼容可加指标；Rate/Average 不能作为贡献分母。
- Anomaly 采用明确统计/规则方法和最小样本要求，不把关键词路由当作异常检测。

Definition of done:

- “6 月较 4 月”不会被错误描述为环比。
- Anomaly 结果携带方法、基线和限制。

### P41-H5: EvidenceGateway And Conclusion Levels

Scope:

- Analysis Workbench 与 Report Center 共享 EvidenceGateway、Policy 和 Artifact 底层，不合并 Orchestrator。
- `EvidenceBundle` 记录数据版本、粒度、时间范围、Operator、质量限制和事实。
- 结论分为 observation、diagnosis、recommendation、prediction、causal_claim。
- 第一版默认允许 observation 和受约束 diagnosis；高等级结论必须满足更高证据门槛。

Definition of done:

- Answer/Report 不能用收入排名直接推出预算建议，不能用相关性表达因果。

### P41-H6: Clarification, Unsupported UX, And Closeout

Scope:

- 为所有 Gate 失败提供中文业务说明和下一步数据建议。
- 建立五类 Operator 的黄金问题、边界问题和跨领域回归。
- 删除被 AnalysisSpec/CapabilityGate 替代的重复任务路由和降级触发器。

Phase exit criteria:

- 五类核心分析在三类数据集上稳定运行。
- Unsupported/Needs Confirmation 不进入模型编造路径。

## P42: Agent And Code Architecture Consolidation

Status: Planned

### Goal

在 P40/P41 契约稳定后完成代码切换：只保留两个真正需要推理的 Agent，拆分宽状态和大型入口，统一 LLM Runtime，并删除旧的包装层。P42 主要提升可维护性、一致性和延迟，不新增业务分析类型。

### Capability After P42

用户获得更一致的分析状态、错误说明和回答；开发者可以通过新增一个 Operator 和测试扩展分析能力，而不需要继续扩张 AgentState 或新增一组伪 Agent。

### P42-H1: Application And Domain Boundaries

Scope:

- 将 FastAPI Router、Application Use Case、Domain Contract 和 Infrastructure Adapter 分离。
- 拆分大型 `create_app`、Analysis Runner 和 Report Runner。
- 保持 API Contract 和产品路由兼容，内部逻辑切换到新边界。

### P42-H2: Typed State And Independent Orchestrators

Scope:

- 用 `AnalysisInput`、`AnalysisPlan`、`ExecutionContext`、`EvidenceBundle`、`AnswerResult`、`RunMetadata` 替代宽 AgentState。
- Analysis Orchestrator 与 Report Orchestrator 独立。
- Domain Contract 不使用任意 `dict[str, Any]` 作为公共接口。

### P42-H3: Two Reasoning Agents

Scope:

- `PlannerAgent`：生成/修复 AnalysisSpec、选择 Operator、决定澄清。
- `AnswerSynthesizer`：只读取 Sanitized EvidenceBundle 生成业务表达。
- Schema、Metric、SQL Reviewer、Error Fixer、Evidence Builder、Chart Renderer 等重命名为确定性 Service/Tool。
- Claim Verification 保持确定性优先。

Definition of done:

- Agent 名称只用于真正拥有模型判断职责的边界。

### P42-H4: Graph Lifecycle And Dependency Injection

Scope:

- Graph 在应用启动时构建和编译一次。
- Provider、Policy、Store、Operator Registry 和 Metrics 显式注入。
- 节点不在运行时隐式创建 Provider Client。
- 为后续 Checkpointer/Interrupt 保留稳定接口，但 P42 不提前实现完整 P43 控制面。

### P42-H5: Shared LLM Runtime

Scope:

- 统一 Provider Client、Prompt 版本、Schema、timeout、有界 retry、backoff、并发、取消、Token、Cost 和 Error Category。
- DeepSeek 保持主要 Provider，不增加不必要的多模型路由。
- Prompt/Completion 正文默认不进入日志或普通 Trace。

### P42-H6: Legacy Deletion And Architecture Acceptance

Scope:

- 通过边界测试证明旧入口不是当前依赖。
- 删除旧 AgentState 字段、重复 Question Understanding 路径、确定性 Agent 包装器、旧 Provider Builder 和过时兼容测试。
- 建立依赖方向和循环依赖检查。
- 同步 Architecture 文档和 ADR。

Phase exit criteria:

- 只有两个推理 Agent。
- 核心用例通过强类型 Contract 连接。
- 旧路径不再作为兼容分支残留。

## P43: Enterprise Runtime And Access Control Foundation

Status: Planned

### Goal

将单机文件状态和进程内任务升级为可恢复、可取消、可审计、支持多用户和多实例的企业运行基础，同时保持模块化单体。

### Capability After P43

多个用户可以在隔离 Workspace 中按角色使用系统；分析和报告任务可以离开页面继续运行，在服务重启后恢复；外部发布、导出和敏感字段访问都有授权与审计。

### P43-H1: Control-Plane Persistence And Artifact Ports

Scope:

- PostgreSQL 保存用户、租户、Workspace、Run、Report、Job、SemanticModel、Approval 和 Audit 元数据。
- SQLite/DuckDB 继续作为单 Workspace 分析引擎。
- Local/S3-compatible Artifact Store 保存图表、报告和导出物。
- 当前 JSON Store 保留为 Local Development Adapter，不再是企业控制面真相源。

### P43-H2: Durable Jobs And Checkpoints

Scope:

- Job 支持 claim、heartbeat、timeout、retry、cancel、idempotency 和 restart recovery。
- LangGraph Checkpointer 保存可恢复节点状态。
- 同一幂等请求不能被两个 Worker 重复执行。
- 发布 Job 与分析/报告 Job 分离副作用边界。

### P43-H3: Authentication, Tenant Isolation, And RBAC

Scope:

- 最小角色：Owner、Analyst、Viewer、Publisher。
- 所有 Workspace/Run/Report/Artifact 带 Tenant/Ownership 约束。
- API、Store、Job 和 Artifact 下载都执行授权，不只依赖前端隐藏。

### P43-H4: Row, Column, Export, And Audit Policies

Scope:

- 列级 PII、行级数据范围、导出、报告查看和发布策略。
- 每次授权决策携带 Policy Version。
- 审计记录 who/what/when/result，不记录敏感正文。

### P43-H5: Retention, Encryption, And Approval Lifecycle

Scope:

- 原始文件、Run、Trace、Report 和 Artifact 保留策略。
- 删除、导出和撤销访问流程。
- 敏感状态/Checkpoint 加密。
- Approval 支持 pending/approved/rejected/expired/consumed。

### P43-H6: Multi-Instance, Recovery, And Closeout

Required acceptance:

- 两个 API 实例共享控制状态。
- 多 Worker 不重复执行同一任务。
- 运行中杀死 Worker 后任务从安全边界恢复。
- 用户取消任务后不会继续发布或写入最终结果。
- Tenant A 无法枚举、下载或查询 Tenant B 数据。

Phase exit criteria:

- 系统具备企业运行基础，但不宣称已经完成公网、云或大规模生产验证。

## P44: Evaluation, Observability, And Portfolio Release

Status: Planned

### Goal

用跨领域评测、端到端验收、安全攻击集、运行指标和公开文档证明 P39-P43 的能力，形成可复现的正式作品集 Release。

### Capability After P44

用户和招聘者可以一键运行固定 Demo，查看系统如何理解数据、拒绝不支持问题、生成证据回答和报告，并看到 SQL 正确率、Grounding、安全、延迟和成本等质量证据。

### P44-H1: Cross-Domain Evaluation Suite

Scope:

- 三个以上业务领域，50-100 个黄金问题。
- 覆盖正常、模糊、缺数据、复杂 Join、非可加指标和不支持分析。
- 记录 SQL Execution Accuracy、Metric Correctness、Join Correctness、Evidence Grounding、Unsupported Claim Rate 和 Correct Refusal Rate。

Initial release targets:

| Metric | Target |
|---|---:|
| Golden SQL execution correctness | >= 90% |
| Metric aggregation correctness | 100% |
| Golden Join selection correctness | >= 95% |
| Evidence grounding | >= 95% |
| Unsupported claim rate | 0 |
| Correct refusal for unsupported requests | >= 95% |

### P44-H2: Security And Adversarial Evaluation

Scope:

- Prompt Injection、PII 访问、SQL 绕过、路径访问、批量导出、跨租户、越权发布和恶意文件。
- 安全失败必须 fail closed，且不泄露 Policy、路径、凭据或原始数据。

Release target:

- 已知高风险 SQL/PII/tenant bypass 为 0。

### P44-H3: End-To-End And Failure-Recovery Acceptance

Scope:

- Playwright 覆盖 Workspace、Import、Readiness、Semantic Confirmation、Analysis、Clarification、Chart、Report、Word、Approval。
- 覆盖 Worker kill/restart、provider timeout、SQL timeout、artifact failure 和 publish partial failure。

### P44-H4: GenAI Observability And CI Release Gates

Scope:

- 增加 LLM latency、Token、Cost、Retry、Prompt Version、Operator、Capability Decision、Grounding Failure 和 Correct Refusal 指标。
- 不记录 Prompt/Completion 正文。
- CI 分为 backend unit/integration、frontend、build、E2E、security、Docker smoke、observability acceptance 和 optional live。

### P44-H5: Public Documentation And Portfolio Assets

Scope:

- 重写精简 README。
- 新增 `ARCHITECTURE.md`、`SECURITY.md`、`EVALUATION.md`、`CONTRIBUTING.md`、LICENSE 和关键 ADR。
- 创建截图、2-3 分钟演示视频脚本、Demo 数据说明、已知限制和面试讲解提纲。
- P0-P38 详细历史从当前主叙事移至 `docs/history/`，保留必要兼容锚点。

### P44-H6: Release Candidate And Program Closeout

Scope:

- 运行全部发布 Gate。
- 创建固定版本和变更说明。
- 记录实际平台、架构、数据集、模型和环境。
- 任何跳过的 live/cloud/amd64/real publish 检查必须明确列出。
- 同步所有计划、状态、Tracker 和 README。

Phase exit criteria:

- 仓库、Demo、评测和文档共同证明产品能力，而不是仅靠功能列表。

## Migration And Deletion Strategy

每个阶段必须维护三张清单：新增、替换、删除。

迁移规则：

1. 先用边界测试锁定当前真实路径。
2. 为新 Contract 写失败测试。
3. 实现新路径并完成 focused green。
4. 将一个完整 Use Case 切换到新路径。
5. 删除被替代的旧分支、字段、Provider 和测试。
6. 运行相关回归与全量验收。
7. 同步 Plan、Status、Tracker 和 README。

禁止为了“兼容”长期保留：

- 两套 SemanticModel。
- 两套 Analysis Task/AnalysisSpec。
- 两套 AgentState。
- 两个默认 SQL 执行入口。
- 同一能力的 Agent 和 Service 双命名。
- 旧结果 Builder 内的业务结论写作逻辑。

## Verification Ladder

每个 H 任务至少执行：

1. 新增/修改契约的 focused tests。
2. 受影响模块回归。
3. API/产品路径集成测试。
4. 前端测试和 build（涉及产品/UI 时）。
5. `git diff --check`。
6. 阶段 Closeout 时执行全量 backend/frontend、Docker/Compose、安全与文档验收。

Live DeepSeek、真实飞书、跨架构镜像、云环境或发布测试必须保持显式 opt-in，并在未运行时记录为 skipped，而不是默认视为通过。

## Program-Wide Exit Criteria

P39-P44 全部完成必须满足：

- 新导入的结构化业务数据先产生可验证 Import、Quality、Semantic 和 Readiness Contract。
- 未确认 Join、非可加指标和歧义时间字段不会进入分析。
- 五类核心分析通过统一 AnalysisSpec、CapabilityGate 和 Operator 执行。
- 不支持问题被正确澄清或拒绝，不进入模型编造路径。
- SQL 只能通过 ValidatedQuery 执行；PII、路径、tenant 和外部发布边界不可绕过。
- Analysis Workbench 与 Report Center 保持独立用例，但共享 Evidence/Policy/Artifact/LLM Runtime。
- 只有 PlannerAgent 和 AnswerSynthesizer 作为核心推理 Agent；确定性模块不再伪装为 Agent。
- 任务支持持久化、取消、重试、幂等、恢复和审计。
- 多用户、RBAC、Tenant、行列级策略在 API、Job、Store 和 Artifact 层一致执行。
- 跨领域评测、E2E、安全攻击集和恢复验收达到发布阈值。
- 主 README、Architecture、Security、Evaluation、计划、状态和 Tracker 与真实实现同步。
- 不存在未记录的 live/provider/publish/cloud 验收声明。

完成后的准确产品表述应为：

> InsightFlow 能够在不同结构化业务数据导入场景下建立数据与语义契约，判断问题是否可分析，并通过受约束的 Agent 编排、确定性分析算子、安全查询和证据校验，完成常见描述性与部分诊断性分析；系统具备多用户权限、持久化任务、故障恢复、审计和量化评测基础。
