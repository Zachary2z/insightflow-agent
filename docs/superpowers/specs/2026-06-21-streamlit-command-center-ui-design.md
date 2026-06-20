# InsightFlow Agent Streamlit Command Center UI 设计

## 背景

当前项目的核心能力已经超过原来的 Streamlit tab demo。P0/P1/P2/P3 的 Agent、工具、LLM Provider、PromptOps、FastAPI、MCP、Trace Dashboard、Action Workflow 都已经具备，但当前 `app.py` 仍以横向 tab 展示：

- SQL Analysis
- Report Generation
- Weekly Business Review
- Action Workflow
- MCP Tool Layer
- Async Run API
- Trace Dashboard

这个结构能证明功能存在，但不能清楚表达“用户从问题到答案、证据、报告、行动、审计”的完整工作流，也没有把 LLM 来源、fallback、prompt、结构化校验、安全边界、证据链作为一级信息呈现。

本设计选择主方案 A：**Command Center**。主界面做成业务分析工作台；运行详情吸收方案 B 的 Trace 时间线；另保留方案 C 的能力总览入口。

## 目标

1. 让用户一进入界面就知道 InsightFlow 能做什么，而不是在多个 tab 中猜。
2. 让一次运行的输出结构清楚：问题理解、SQL、数据、证据、报告、行动、Trace。
3. 明确呈现来源：deterministic / DeepSeek provider、`provider_called`、`fallback_used`、prompt id、结构化校验、SQL 校验、Evidence Validator、Approval Gate。
4. 保留现有 Streamlit 技术栈，先把信息架构和演示体验做好。
5. 为后续 React + TypeScript + FastAPI 正式前端保留可迁移的信息结构。

## 非目标

1. 本阶段不迁移 React。
2. 本阶段不实现 Docker、CI、RBAC、外部 ActionOps 集成。
3. 本阶段不放宽任何安全边界。
4. 本阶段不让 LLM 绕过 `validate_sql()`、SQL Reviewer、Evidence Validator、Approval Gate、Audit Logger 或 Trace Logger。
5. 本阶段不把 Streamlit 做成复杂前端框架，只做清晰、可演示、可维护的内部工作台。

## 当前完整功能地图

### P0 Agentic SQL Core

- 中文业务问题输入。
- Schema Agent 读取 SQLite ecommerce schema。
- Metric Agent 获取 GMV、订单量、AOV 等指标定义。
- SQL Generator 生成 SELECT SQL。
- SQL Reviewer 调用 `validate_sql()`。
- SQL Executor 调用 `run_sql()`。
- Error Fix Agent 支持一次执行失败修复。
- Insight Agent 基于真实执行结果生成回答。
- Trace Logger 保存完整运行 trace。
- P0 eval 20 个用例。

### P1 Reliable Analysis & Report Core

- Business Context Retrieval：业务规则、表字段文档、历史 SQL 示例。
- Evidence Validator：区分 supported findings、hypotheses、unsupported claims。
- Chart Agent：生成柱状图、折线图等 PNG 图表。
- Report Agent：生成带 SQL、证据、图表、trace 路径的 Markdown 报告。

### P2 Business Review & Action Workflow

- Report Supervisor：生成周报/月报，多 SQL 子任务。
- Controlled Report Planner：可选 provider 选择 allowlisted 报告章节。
- Guarded SQL / Insight Enhancement：可选 provider 提供 SQL candidate 或 claims，但必须经过校验。
- Action Workflow：Action Planner、Risk Assessor、Approval Gate、Action Executor、Action Verifier、Audit Logger。
- Action 工具支持 task、metric alert、email draft，但创建动作必须经过审批。

### P3 MCP & Engineering Core

- MCP Tool Layer：database/report/action MCP-style contract。
- FastAPI Async Run API：提交 run、查询状态、取 trace/events、取消。
- Trace Dashboard Data Layer：trace 数量、事件、节点延迟、工具调用、SQL repair、eval、approval、audit。
- Streamlit Unified Demo：当前 7 个 tab demo。
- LLM Provider / PromptOps：provider contract、prompt registry、prompt version、usage/cost/latency metadata、smoke eval。
- DeepSeek Provider：`.env` 配置、真实 provider、结构化输出校验、malformed/schema failure 处理。
- Question Understanding：metric、dimension、time_range、filters、operation、limit、risk_flags。
- Clarification Router：问题不完整时生成澄清问题。
- SQL Planning Router：template / llm_candidate / clarify / reject。
- Guarded SQL Candidate：LLM 可提出 candidate，但必须 `validate_sql()` 通过。
- Business Review Decomposition：LLM 可选 allowlisted 章节，不能给 SQL 或事实 claims。
- Report Writer：LLM 可基于 Evidence Validator 输出润色报告。
- Insight Claim Typing：LLM 可辅助 claim 分类，但 Evidence Validator 最终裁决。
- Action Drafter：LLM 可草拟 task / alert / email payload，但不能执行。
- Template Mining & LLM Eval：从成功 trace 挖掘 candidate 模式，并做 schema-aware smoke eval。

## 推荐信息架构

主界面采用以下导航：

1. **工作台**
   - 默认入口。
   - 输入业务问题。
   - 选择运行类型：SQL 分析、报告生成、业务复盘、行动建议。
   - 展示一次 run 的核心结果。

2. **运行详情**
   - 以一次 run 为中心。
   - 展示 Intent、SQL & Data、Evidence、Report、Action、Trace。
   - Trace 采用时间线，而不是直接倾倒 JSON。

3. **能力总览**
   - 用卡片说明 P0/P1/P2/P3 完整能力。
   - 每个能力标记阶段、状态、入口、关键安全边界。

4. **观测与审计**
   - Trace Dashboard 汇总。
   - Approval records。
   - Audit logs。
   - Eval summary。

5. **LLM Ops**
   - provider 开关状态。
   - prompt registry。
   - live DeepSeek test 状态说明。
   - provider/fallback 统计。
   - schema validation 失败摘要。

6. **集成接口**
   - MCP tool contracts。
   - FastAPI async run API。
   - endpoint 和 tool contract 展示。

## 工作台布局

工作台首屏分为四块：

1. 顶部运行栏
   - 输入业务问题。
   - 示例问题选择。
   - 运行类型选择。
   - 数据库路径和 trace 目录放入高级设置。
   - provider 状态只展示，不默认要求 API key。

2. 主结果区
   - 最终回答。
   - 关键指标。
   - 图表预览。
   - 报告路径。
   - 行动草稿状态。

3. 来源与安全区
   - Question Understanding source。
   - SQL Planning source。
   - SQL Candidate source。
   - Claim Typing source。
   - Report Writer source。
   - Action Drafter source。
   - 每项展示 `provider_called`、`fallback_used`、prompt id、validation 状态。
   - 展示 `validate_sql()`、SQL Reviewer、Evidence Validator、Approval Gate、Audit Logger 是否参与。

4. 运行详情入口
   - Intent。
   - SQL & Data。
   - Evidence。
   - Report。
   - Action。
   - Trace。

## 运行详情布局

运行详情以一次 run 的状态为中心，推荐使用纵向结构：

1. **Intent**
   - metric
   - dimension
   - time_range
   - filters
   - operation
   - limit
   - risk_flags
   - clarification questions

2. **SQL & Data**
   - generated SQL 或 accepted candidate SQL。
   - SQL review result。
   - SQL validation status。
   - execution columns / rows / row_count / latency。
   - repair attempt。

3. **Evidence**
   - supported findings。
   - hypotheses。
   - unsupported claims blocked。
   - unsupported claim rate。
   - chart paths。

4. **Report**
   - report path。
   - weekly/monthly report sections。
   - report subtask status。
   - provider-backed report writer metadata。

5. **Action**
   - planned actions。
   - provider-backed draft metadata。
   - risk assessment。
   - approval status。
   - created actions。
   - verification result。
   - audit log id。

6. **Trace Timeline**
   - 按节点顺序展示：
     - node
     - tool_name
     - status
     - latency_ms
     - retry_count
     - provider_called
     - fallback_used
     - error / error_type
   - 默认只展示摘要，点击展开 JSON。

## 来源展示规则

所有 provider-backed 模块都应该尽量统一显示为来源卡片：

```text
模块: Question Understanding
来源: DeepSeek Provider / Deterministic
provider_called: true
fallback_used: false
prompt_id: question_understanding
validation: passed
边界: 不生成 SQL，不执行 SQL
```

推荐展示模块：

- Question Understanding
- Clarification Router
- SQL Planning Router
- Guarded SQL Candidate
- Report Planner
- Claim Typing
- Report Writer
- Action Drafter

如果 provider 没启用，则显示：

```text
来源: Deterministic baseline
provider_called: false
fallback_used: false
原因: provider not configured
```

如果 provider 失败，则显示：

```text
来源: Deterministic fallback
provider_called: true
fallback_used: true
错误: provider_error 或 validation_error
```

## 能力总览布局

能力总览使用 C 方案的卡片，但不作为主入口。卡片字段：

- 能力名称。
- 阶段：P0/P1/P2/P3。
- 状态：available / local-api / provider-optional。
- 主要入口函数或模块。
- 是否需要 API key。
- 关键边界。

建议卡片：

- SQL Analysis
- Evidence-backed Report
- Weekly / Monthly Business Review
- Approval-gated Action Workflow
- MCP Tool Layer
- FastAPI Async Run API
- Trace Dashboard
- LLM Provider & PromptOps
- Template Mining & Eval

## 观测与审计布局

当前 `dashboard/trace_dashboard.py` 已经能提供结构化数据，界面应从 JSON dump 改为：

- 顶部指标：
  - trace_count
  - event_count
  - sql_fix_count
  - eval pass rate
  - approval count
  - audit log count

- 表格：
  - node latency
  - tool call counts
  - failure distribution
  - approval records
  - audit logs

- 详情：
  - 选中 trace 文件后查看 timeline。
  - JSON 放在 expander 里。

## LLM Ops 布局

LLM Ops 页面负责回答：“大模型到底参与了什么？”

建议展示：

- Provider 配置状态：
  - DeepSeek key 是否存在，只显示 configured / not configured，不显示 key。
  - 各 runtime env switch 是否开启。

- Prompt registry：
  - prompt_id
  - version
  - description

- Runtime participation：
  - provider_called count
  - fallback_used count
  - schema validation errors
  - prompt-specific error types

- Live test 说明：
  - live DeepSeek tests 需要显式开启。
  - default no-key baseline 不调用真实 provider。

## Streamlit 实现边界

实现时应优先重构展示组件，而不是重写业务逻辑：

- 继续复用 `run_demo_question()`。
- 继续复用 `run_report_generation_demo()`。
- 继续复用 `run_weekly_review_demo()`。
- 继续复用 `run_action_workflow_demo()`。
- 继续复用 `build_mcp_contract_summary()`。
- 继续复用 `build_async_run_api_summary()`。
- 继续复用 `build_trace_dashboard_summary()`。

新增或调整的代码应集中在 `app.py` 的 UI helper 层，避免修改 Agent、Tool、Graph 的核心行为。

如果需要拆分文件，应保持边界清晰：

- `app.py`：Streamlit entrypoint。
- `ui/view_models.py`：从 workflow state 提取 UI-friendly view model。
- `ui/components.py`：来源卡片、trace timeline、能力卡片等通用组件。

是否拆分文件由实施时的代码规模决定。若改动较小，可先保持在 `app.py`。

## 测试策略

先 TDD 更新或新增 Streamlit helper 测试：

1. 能力总览包含 P0/P1/P2/P3 和 LLM Ops。
2. 来源 view model 能从 state 中提取 `provider_called`、`fallback_used`、prompt id、validation error。
3. Trace timeline view model 能保留 node、tool、latency、provider/fallback。
4. no-key baseline 的 UI 状态显示 deterministic，不要求 API key。
5. 工作台运行仍调用现有 workflow helper，不绕过核心 workflow。
6. 现有 full pytest 继续通过。
7. P0 eval 继续 20/20。

## 后续前端工程化方向

Streamlit 是当前阶段的内部 demo / 工作台。正式产品前端建议：

- React + TypeScript + Vite。
- Tailwind CSS + shadcn/ui。
- TanStack Query 管理 FastAPI 数据。
- ECharts 或 Recharts 展示业务图表和 trace metrics。
- FastAPI 保持后端入口。
- Async Run 先 polling，后续升级 SSE 或 WebSocket。

React 迁移时直接复用本设计的信息架构：

- Command Center。
- Run Detail。
- Capability Catalog。
- Observability。
- LLM Ops。
- Integrations。

## 验收标准

1. Streamlit 主界面从分散 tab demo 变成清晰的 Command Center。
2. 用户能在一次 run 中看到答案、SQL、数据、证据、报告、Action、Trace。
3. 用户能清楚看到 LLM 是否参与、是否 fallback、用了哪个 prompt、结构化校验是否通过。
4. 用户能看到 `validate_sql()`、Evidence Validator、Approval Gate、Audit Logger 等安全边界。
5. 能力总览完整覆盖 P0/P1/P2/P3。
6. Trace Dashboard 从 JSON dump 升级为指标、表格、timeline 和详情。
7. 默认无 API key 时界面仍可运行 deterministic baseline。
8. 不改变现有 Agent/Tool/Graph 安全边界。
9. `python3 -m pytest` 通过。
10. `python3 eval/run_eval.py` 仍 20/20 passed。
