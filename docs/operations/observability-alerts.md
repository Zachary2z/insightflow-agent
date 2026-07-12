# InsightFlow Observability Alerts And Runbooks

本文是 P38 的本地运维 Runbook。所有排查只使用健康状态、聚合指标、固定类别和受控结构化事件；Observability 失败不得成为业务请求失败的原因。告警阈值由 `observability/alerts/alert-rules.yml` 定义，确定性时间序列验收位于 `observability/tests/rule-tests.yml`。

## 安全边界

允许查看：Compose 服务状态、健康端点、Grafana 聚合面板、Prometheus target/rule 状态，以及结构化日志中的 `timestamp`、`event`、安全 correlation ID、Route Template、operation、provider、status、error_type、latency 和计数。`request_id`/`run_id` 只用于关联受控事件，不得成为指标 Label。

禁止查看、打印或复制：请求/响应正文、用户问题、Prompt/System Message、原始行、SQL、Provider request/response/payload、异常原文或 traceback、Authorization/Cookie/Header 内容、Token/Secret、发布 URL、CLI stdout/stderr、本机绝对路径、Workspace/Report/Trace 正文。禁止递归读取 Trace、Workspace 或 Report 目录；禁止真实 DeepSeek 调用；禁止真实 Feishu 登录、发布或重试；禁止 `docker system prune`、`docker volume prune` 以及任何业务 Volume 删除。

只查看受控 backend 事件的安全模板：

```bash
docker compose logs --no-log-prefix --tail 200 backend \
  | jq -Rc 'fromjson? | {timestamp,event,request_id,run_id,workspace_id,report_id,route,operation,provider,status,error_type,latency_ms}'
```

如果输出不是应用 JSON 行，停止使用该管道并只看 Grafana/Prometheus 聚合信号；不要改用会输出原始内容的全文搜索。

## 本地日常操作

基础服务只启动 backend/frontend：

```bash
make up
make ps
make logs
make down
```

Observability Profile 要求通过本地忽略提交的 `.env` 或部署 Secret 注入非空 `GRAFANA_ADMIN_PASSWORD`。不得把密码写入命令历史、Compose、文档或仓库文件。启动、状态、受控日志和停止命令：

```bash
make observability-up
make observability-ps
make observability-logs
make observability-down
```

默认端口是 backend `127.0.0.1:8000`、frontend `127.0.0.1:3000`、Prometheus `127.0.0.1:9090`、Grafana `127.0.0.1:3001`；分别可由 `BACKEND_HOST_PORT`、`FRONTEND_HOST_PORT`、`PROMETHEUS_HOST_PORT`、`GRAFANA_HOST_PORT` 覆盖。规则与完整安全验收：

```bash
make observability-alert-tests
make observability-check
make observability-acceptance
```

这些入口不需要 Provider/Feishu 凭证，不调用外部服务，不等待真实告警持续时间，也不删除 Volume。

日常停止使用 `make observability-down`，它保留全部 Volume。确需只清理 Prometheus/Grafana 监控数据时，先确认临时或目标 `COMPOSE_PROJECT_NAME`，再执行：

```bash
make observability-down-v
```

该目标只删除当前 Compose project 显式命名的 `prometheus-data` 和 `grafana-data`，保留 `workspace-data`、`report-data`、`trace-data`。不得用 `docker compose down -v` 代替，也不得使用全局 prune。

## BackendUnavailable

触发条件：`up{job="insightflow-backend"} == 0` 持续 1 分钟，severity=`critical`。

先看 Dashboard：System Health / Backend up，然后看同页 request throughput 与 runtime storage。

允许的安全检查：

```bash
docker compose ps backend
curl --fail http://127.0.0.1:${BACKEND_HOST_PORT:-8000}/health/live
curl --fail http://127.0.0.1:${BACKEND_HOST_PORT:-8000}/health/ready
docker compose logs --no-log-prefix --tail 100 backend \
  | jq -Rc 'fromjson? | {timestamp,event,route,operation,status,error_type,latency_ms}'
docker compose exec backend id
docker compose exec backend sh -c 'test -w /app/workspaces && test -w /app/reports && test -w /app/logs/traces'
```

禁止：输出环境变量、打开业务文件、打印 traceback/异常正文、修改 Volume 所有权为 root、挂载 Docker socket、删除任何 Volume。

恢复建议：确认端口和三处挂载可写后运行 `docker compose up -d backend`；仅对瞬态进程故障可运行 `docker compose restart backend`。恢复后验证 live/ready 和 Prometheus Targets，而不是执行真实业务分析。

升级人工：容器反复退出、readiness 持续失败、挂载不可写、需要权限/配置/镜像变更，或 5 分钟内未恢复。

## HighHttp5xxRate

触发条件：请求速率至少 0.1 req/s、5xx 比率超过 5%，持续 5 分钟。

先看 Dashboard：System Health / HTTP 4xx/5xx，再看 HTTP P95 latency；只按 Route Template 和 status class 聚合。

允许的安全检查：`make observability-ps`、live/ready、Prometheus Targets，以及上面的结构化日志安全模板。用同一安全 `request_id` 关联 `http_request_started`/`http_request_completed` 与 workflow/tool 完成事件；只比较 event/status/error_type，不读取正文或原始 Trace。

禁止：查询原始 URL/Query/Header、异常文本、SQL、Prompt、Rows、Provider payload；不得通过重放真实业务请求定位。

恢复建议：若单一受控 operation/error_type 异常，先恢复对应依赖或回滚最近明确变更；若 backend 不健康，按 BackendUnavailable 处理。恢复后用 health 请求和 mock/failure-injection 验收确认 5xx 比率回落。

升级人工：影响多个 Route、主要 API 持续 15 分钟、无法从固定类别定位，或修复需要读取业务内容/变更数据。

## HighApiLatency

触发条件：请求速率至少 0.1 req/s、HTTP P95 超过 2 秒，持续 10 分钟。

先看 Dashboard：System Health / HTTP P95 latency；再看 Analysis Workflow 的 run/node latency 和 Provider And Tool 的 LLM/SQL latency。

允许的安全检查：`docker compose ps`、health、聚合 CPU/内存/请求并发、固定 Route Template/operation/provider/status 的耗时面板。只用 correlation ID 比较阶段边界时间，不展开业务 Trace。

禁止：性能排查时打印 Prompt、SQL、Rows、Provider 响应、Trace 正文或本地路径；不得调用真实 Provider 制造样本。

恢复建议：先减少已确认的本地资源竞争或恢复故障依赖；对瞬态容器异常可受控重启单个服务。用 `make observability-acceptance` 和健康请求复核，不用真实分析负载验证。

升级人工：资源正常但延迟继续上升、多个 operation 同时退化、持续 20 分钟，或需要容量/架构变更。

## HighLlmFailureRate

触发条件：LLM 请求速率至少 0.02 req/s，error/timeout 比率超过 10%，持续 10 分钟。

先看 Dashboard：Provider And Tool / LLM errors and timeouts，再看 fallback rate 和 operation latency。

允许的安全检查：只确认配置是否存在，不显示值：

```bash
docker compose exec backend sh -c 'test -n "$DEEPSEEK_API_KEY" && echo configured || echo missing'
```

同时查看 provider/operation/status/error_type 聚合和 `llm_request_completed` 受控事件，确认已有 deterministic fallback 是否产生安全业务结果。

禁止：显示、复制或轮换 Token；输出 Provider payload；调用真实 DeepSeek；用用户 Prompt 重试；把动态 model/error text 变成 Label。

恢复建议：若密钥缺失，保持 no-key 安全 fallback 并由授权人员在部署 Secret 修复；若 timeout/error 为外部依赖问题，停止自动重试并保留 fallback。使用 mock timeout/schema fixtures 复核。

升级人工：需要凭证变更、Provider 状态确认、fallback 无法提供安全结果，或失败持续 20 分钟。

## HighSqlFailureRate

触发条件：SQL execution 请求速率至少 0.02 req/s，error/timeout/failed 比率超过 10%，持续 10 分钟。

先看 Dashboard：Provider And Tool / SQL Execution，再看 SQL Validation rejection；区分 validation rejection 与 execution failure。

允许的安全检查：只看 `sql_validation_completed`/`sql_execution_completed` 的 status、risk_level、error_type、latency 聚合；确认 readiness 和 Workspace 挂载可写。使用临时测试数据库和 mock fixture 复现。

禁止：打印 SQL、表/列名、数据库路径、结果行、Trace tool summary；不得修改或打开真实业务数据库。

恢复建议：validation rejection 保持 fail closed，不绕过 validator；execution failure 先恢复文件/连接/权限边界，再用临时 SQLite fixture 验证。不要把失败 SQL 直接重放到业务库。

升级人工：需要检查或修复真实数据、变更 schema/validator policy、同类错误持续 20 分钟，或出现数据完整性风险。

## HighEvidenceFailureRate

触发条件：Evidence validation 请求速率至少 0.02 req/s，error/rejected/failed 比率超过 10%，持续 10 分钟。

先看 Dashboard：Analysis Workflow / Evidence Task status，再看 Provider And Tool / Evidence Validation。

允许的安全检查：只看 route/status/reason_category、`evidence_validation_completed` 和 workflow completion 的固定字段；用合成 claims/rows fixture 验证 unsupported claim 会被阻断或安全降级。

禁止：读取原始 Evidence、业务行、报告正文、SQL、Prompt、Workspace/Report/Trace JSON；不得降低校验阈值来消除告警。

恢复建议：保持不受支持的 hard fact 被 blocked；回滚最近明确的 evidence contract/validator 变更，或修复合成测试揭示的兼容问题。用 `make observability-acceptance` 复核。

升级人工：需要查看业务数据、多个 route 同时失败、出现无证据硬结论，或失败持续 20 分钟。

## ExternalPublishFailureBurst

触发条件：10 分钟内 Feishu error/failed 至少 3 次，并持续 1 分钟。

先看 Dashboard：Delivery / Feishu Publish，再看 report/export 状态；Doc 成功但 Sheet/chart post-step warning 不应被误判为完整发布失败。

允许的安全检查：只确认 CLI 是否存在，不登录、不执行发布：

```bash
docker compose exec backend sh -c 'command -v lark >/dev/null && echo present || echo missing'
```

检查 `external_publish_completed` 的 platform/status/error_type 和 safe publish result；容器基础镜像未安装 CLI 时，明确 failed 是预期安全行为。

禁止：真实 Feishu 登录、发布或重试；显示 Token、Doc/Sheet URL、CLI stdout/stderr；挂载本机 Home/认证目录；重新生成报告、调用 LLM 或执行 SQL。

恢复建议：CLI 缺失时保留安全失败并等待受控部署设计；CLI/publish failure 不应破坏现有报告。只用 mock runner/non-zero/missing-binary fixtures 验证恢复，不做真实发布。

升级人工：任何认证、安装 CLI、网络或真实发布动作；需要检查外部平台状态；同一报告重复失败或告警持续 15 分钟。

## RuntimeStorageHigh

触发条件：Trace 挂载所在文件系统的 label-free 聚合使用率超过 80%，持续 15 分钟。

先看 Dashboard：System Health / Runtime Storage，再看 backend availability。该 Gauge 只使用 `statvfs` 聚合计数，不扫描文件。

允许的安全检查：

```bash
docker system df
docker volume inspect "${COMPOSE_PROJECT_NAME:-insightflow}_trace-data"
docker compose exec backend python -m observability.trace_retention \
  --trace-dir /app/logs/traces --max-age-days 30 --max-total-bytes 1073741824
```

Retention 命令默认 dry-run，只报告安全候选计数/字节和固定跳过原因。不得递归列出或读取 Trace/Workspace/Report 内容。

禁止：`docker system prune`、`docker volume prune`、`docker compose down -v`、手工删除业务文件或 Volume、读取 Trace 正文。监控数据清理只能使用确认 project name 后的 `make observability-down-v`，且不会替代 Trace retention。

恢复建议：先完成 dry-run 和人工复核；只有授权后才对受控 Trace root 增加 `--delete`，活动 run 和非 Trace artifact 必须保持保护。扩容或业务数据处置不属于自动 Runbook。

升级人工：需要实际删除 Trace、容量仍不足、使用率超过 90%、无法确认 Volume/project 边界，或任何操作可能触及业务 Volume。

## 告警规则验证与变更

`make observability-alert-tests` 使用合成 Counter/Histogram/Gauge 序列验证 7 条 recording rules 和全部 8 条 alerts。Firing 用例在评估时间上满足各自阈值和 `for` 持续时间；低流量/未持续用例证明不会误报。修改阈值、持续时间、Label 或 Dashboard/Runbook Annotation 时，必须同步规则夹具和本文，并运行：

```bash
make observability-check
make observability-acceptance
```

规则、夹具、Dashboard 和 Runbook 不得包含密钥、业务内容、原始路径、SQL、Prompt、Provider payload 或动态 ID Label。
