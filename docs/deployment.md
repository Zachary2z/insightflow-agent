# InsightFlow Docker 部署与排障

本文是 P37 单机 Docker Compose 运行手册。当前实际验收平台为 Docker Desktop 上的 `linux/arm64`；没有验证 `amd64`、远程 CI、云环境或 Kubernetes。

## 系统要求与预检

- Docker Desktop，或 Linux Docker Engine + Docker Compose v2。
- 用于执行 Makefile 的 `make`，以及 Smoke 所需的 `bash`、`curl`、`python3`、`mktemp`。
- 默认端口 `127.0.0.1:8000` 与 `127.0.0.1:3000` 可用。

```bash
docker version
docker compose version
docker info
docker compose --env-file /dev/null config -q
```

## 无密钥启动

基础启动、健康检查和 Smoke 不需要 DeepSeek/OpenAI Key，也不需要 `lark-cli`。

```bash
make build
make up
make ps
```

访问前端 <http://127.0.0.1:3000>，后端为 <http://127.0.0.1:8000>。当前 Compose 使用最终镜像标签 `insightflow-backend:p37` 和 `insightflow-frontend:p37`，端口只绑定回环地址。

常用命令：

```bash
make help
make build
make up
make down
make restart
make ps
make logs
make compose-check
make test
make smoke
```

`make smoke` 使用唯一的隔离 project、空 env 文件和隔离 Volume，验证健康、前端、非 root、Workspace/Run/Report、Markdown、Word、图表合同、持久化和 graceful restart；结束时只删除该隔离 project 的资源。

## Live Mode

把真实值只放在已忽略的本地 `.env` 或部署平台的运行时 Secret 注入机制中：

```env
INSIGHTFLOW_PRODUCT_LIVE_MODE=1
DEEPSEEK_API_KEY=replace_me
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
```

然后运行 `docker compose up --build -d`。不要把 Secret 放入 Docker build args、`NEXT_PUBLIC_*` 或版本库。Compose 环境变量不是正式 Secret Manager；容器元数据可能显示运行时环境变量。Live DeepSeek 测试必须额外显式设置 `INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1`，普通测试默认 skip。

浏览器 API 地址是构建期公开值。覆盖端口时应协调以下配置并重新构建前端：

```env
BACKEND_HOST_PORT=18000
FRONTEND_HOST_PORT=13000
NEXT_PUBLIC_API_BASE=http://localhost:18000
INSIGHTFLOW_CORS_ORIGINS=http://localhost:13000,http://127.0.0.1:13000
```

## 健康端点

- `GET /health/live`：只判断 API 进程能否服务，不调用 DeepSeek、飞书或业务 SQL。
- `GET /health/ready`：检查 Workspace、Report、Trace 存储及基础配置，成功时四项均为 `ok`。

```bash
curl --fail http://127.0.0.1:8000/health/live
curl --fail http://127.0.0.1:8000/health/ready
docker compose ps
```

DeepSeek、OpenAI Key、飞书认证和 Word/飞书发布工具都不是基础 readiness 依赖。

## 结构化应用日志、Request ID 与 TraceSink（P38-H1/H2/H3）

所有 HTTP 响应（包括 live/ready、OpenAPI、Workspace API、404 和正常业务 4xx）都会尽可能返回 `X-Request-ID`。客户端传入的单个 `X-Request-ID` 只有在长度为 1～64、仅含字母/数字/`-`/`_`/`.`，且不是 SQL-like 或 secret-like 内容时才保留；其他情况生成 `req_<uuid hex>`，不会回显恶意值，也不会改变 API 正文。

当前 ID 通过 `ContextVar` 在一次请求内传播，并在请求结束或异常退出时 reset。H2 默认向 stdout 输出逐行 JSON 应用事件；`http_request_started` 包含 request/method/started，`http_request_completed` 增加匹配后的 Route Template（未匹配为 `unmatched`）、状态码/类别、受控状态和毫秒耗时。响应开始前的未处理异常记录 `500/5xx + status=error +` 归一化 `error_type`；响应已经开始后的流式异常保留已经发送的状态码/类别，但仍记录 `status=error + error_type`，不会误计为 success。异常原文、repr 和 traceback 不进入事件，原异常继续向上抛出。线程池分析任务显式复制并 reset 安全 request/workspace/run ID；Workflow、Report、Word Export 和 External Publish 记录紧凑生命周期完成事件。

```env
INSIGHTFLOW_LOG_FORMAT=json
INSIGHTFLOW_LOG_LEVEL=INFO
INSIGHTFLOW_TRACE_SINKS=local
INSIGHTFLOW_TRACE_DIR=logs/traces
```

格式只接受 `json`/`text`，级别只接受 `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`；未知值回退 JSON/INFO，不接受 Logger/Handler/Formatter 类路径。`text` 仅用于本地可读调试，Compose 默认 JSON。日志不创建本地文件或新 Volume。生产容器关闭 Uvicorn access log，避免原始 URL/Query 绕过应用事件合同；Uvicorn startup/error 日志仍可保持独立文本。

应用事件不记录请求/响应正文、Query、Authorization/Cookie/其他 Header、异常原文、SQL、Prompt、Rows、Provider payload、发布 URL/Token/CLI stdout/stderr 或本地路径。日志写入失败不会改变 HTTP、分析、报告、导出或发布结果。

`INSIGHTFLOW_TRACE_SINKS` 只接受 `local`（默认）或 `local,structured`；未知值和类路径回退 local-only。Local Sink 保持现有 Trace JSON 与 Dashboard/Workspace Run 兼容，使用同根临时文件、flush/fsync 和原子替换，并拒绝符号链接逃逸。Structured Sink 只输出 `event=trace_persist_completed`、安全 run/session ID、operation/status/error category、latency 与 event count；完整 Trace、用户问题、thread、tool summaries、SQL、Prompt、Rows、Provider payload、异常文本和本地路径不会进入 stdout。Composite 中辅助 Sink 失败不会影响本地 Trace 或业务答案；本地 Sink 失败继续保持现有失败语义。

Trace Retention 不在请求路径自动运行，默认 dry-run：

```bash
# 预览 30 天以上候选文件
docker compose exec backend python -m observability.trace_retention \
  --trace-dir /app/logs/traces --max-age-days 30

# 同时按 1 GiB 容量约束并显式删除；活动 Run 可重复保护
docker compose exec backend python -m observability.trace_retention \
  --trace-dir /app/logs/traces --max-age-days 30 \
  --max-total-bytes 1073741824 --active-run-id run_active --delete
```

也可设置 `INSIGHTFLOW_TRACE_RETENTION_DAYS` 和 `INSIGHTFLOW_TRACE_RETENTION_MAX_BYTES` 作为 CLI 默认值；没有 `--delete` 始终只预览。`INSIGHTFLOW_TRACE_DIR` 定义独立可信根（Compose 固定为挂载 `trace-data` 的 `/app/logs/traces`），`--trace-dir` 只能等于它或选择其安全子目录，不能扩大授权边界。目标越界、与 Workspace/Report 业务根重叠、或包含符号链接时，代码会在扫描前 fail closed，CLI 只返回安全错误类别。

授权根内也不是所有 JSON 都可删除：文件必须符合 Local JSON `TraceDocument` 兼容合同，包括 object 顶层、字符串 run/status、文件名与安全化 run id 一致、trace list、匹配的非负 event count、UTC `saved_at`、object question thread，以及兼容的 session/question 类型。普通、损坏、Workspace Run、Report Center trace、Evidence/cache JSON 会以固定安全原因跳过；目录、临时文件、Markdown、Word、Chart、`.env` 和源码不进入候选。Workspace Run 与 Report Center Trace 仍不属于 H3 Retention 管理范围。

## Prometheus 应用指标（P38-H4）

`GET /metrics` 返回 `prometheus_client.CONTENT_TYPE_LATEST` 文本，不读取 Workspace、Report、Trace 或数据库，也不依赖 DeepSeek、Feishu 或网络。`/metrics` 自身排除在 HTTP 指标外以避免抓取反馈；live/ready 和其他请求计入。HTTP Histogram buckets 为 `0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10` 秒；Node/LLM/SQL 为 `0.001..30` 秒；Workflow/Publish 为 `0.01..300` 秒。

所有 Label 由中央 allowlist 归一化。分析 route 只允许 `fast/standard/deep/clarification/unknown`；Node、Provider、Operation、Status、Reason/Error、SQL Risk、Chart Type、Format 和 Platform 都有固定集合，未知值折叠为 `unknown` 或 `other`。HTTP route 只允许应用注册的 Route Template，真实 ID、Query 和原始 URL 永不成为 Label。Recorder 的 Counter/Histogram/Gauge 失败不会改变业务结果。

Metrics 辅助解析同样 fail-safe：Retry 只接受原生非负整数，字符串、float、bool 和自定义对象不会被转换；单次 Node Retry delta 最多记录 10，并通过固定 operation 映射一次性累加。Node status 只接受原生字符串，`trace_save_failed` 归类为 `error`，未知对象归类为 `unknown`。Metric lookup、Counter、Histogram 或 Gauge 失败不会阻止业务函数、改变返回值或替换原始 RuntimeError/TimeoutError。

```bash
curl --fail http://127.0.0.1:8000/metrics
```

当前 `/metrics` 没有应用层认证。Compose 的 backend host port 只绑定 `127.0.0.1`，Profile 中 Prometheus 通过内部服务名抓取；生产 Ingress/反向代理必须把它限制为内部 Prometheus 抓取，禁止直接暴露公网。指标仅代表当前单进程、单 backend 实例，不做多进程聚合。

## 可选 Observability Profile（P38-H5）

基础 `make up` / `docker compose up -d` 仍只启动 backend/frontend。监控栈必须显式启用，且 Grafana 管理员密码必须放在忽略提交的本地 `.env` 或部署 Secret 中；`.env.example` 故意保留空值。缺失密码时 `make observability-up` 和 Grafana 容器都会明确拒绝启动，不会回退 `admin/admin`。

```bash
make observability-check
make observability-alert-tests
make observability-acceptance
make observability-up
make observability-ps
make observability-logs
make observability-down
```

本地地址：Prometheus <http://127.0.0.1:9090>，Grafana <http://127.0.0.1:3001>。Host Port 可由 `PROMETHEUS_HOST_PORT` 和 `GRAFANA_HOST_PORT` 改写；管理员名可由 `GRAFANA_ADMIN_USER` 改写。Grafana 禁止匿名访问和用户注册。生产必须把两者放在内部网络，并通过反向代理/Ingress、认证和授权继续限制，绝不可直接暴露公网。

Prometheus 使用固定 `15s` scrape 和 `30s` evaluation，只抓取内部 `backend:8000/metrics` 与自身，不使用公网 target、Docker/Kubernetes discovery、云凭证或管理 API。TSDB 同时限制 `retention.time=7d` 与 `retention.size=2GB`；资源上限为 1 CPU/512 MiB。Grafana 上限为 1 CPU/384 MiB。固定镜像 `prom/prometheus:v3.5.0`、`grafana/grafana:12.1.0` 用于防止 `latest` 漂移并保持验收可复现。

Grafana 自动 Provision 固定 UID `prometheus` 的默认 Data Source，URL 为内部 `http://prometheus:9090`；`InsightFlow Observability` Folder 自动加载 System Health、Analysis Workflow、Provider And Tool、Delivery，不需手工导入。Recording/Alert Rules 位于 `observability/alerts/`，阈值与安全排查见 `docs/operations/observability-alerts.md`。Runtime Storage 只使用 Trace 挂载文件系统的无 Label 聚合 `statvfs` 使用率；不扫描文件、不读业务内容、不输出路径，读取失败不影响 `/metrics` 或请求。

`make observability-down` 保留所有 Volume。确需永久删除监控历史时，先核对 `COMPOSE_PROJECT_NAME`，再使用 `make observability-down-v`；它只删除显式命名的 `prometheus-data`/`grafana-data`，不会删除三个业务 Volume。禁止使用 `docker system prune` 或 `docker volume prune`。

## Failure Injection、告警测试与 Runbook（P38-H6）

`make observability-alert-tests` 使用 Prometheus 合成时间序列直接推进评估时间，不等待真实 5/10/15 分钟；它断言 7 条 recording rules 的结果、BackendUnavailable/HTTP 5xx/API latency/LLM/SQL/Evidence/Feishu/RuntimeStorage 全部 8 条 alerts 的 firing，并覆盖低流量或持续时间不足时不误报。`make observability-check` 同时执行 Compose、Prometheus config/rules、告警夹具、Grafana provisioning 和 Dashboard 合同检查。

`make observability-acceptance` 是安全、可重复、无凭证的 P38 验收入口。它通过 mock/临时文件覆盖 API 5xx、Provider timeout/fallback、SQL rejection/execution failure、Evidence failure、Chart/Report/Export failure、Feishu CLI/publish failure、Trace 本地 sink 不可写、随机 Request ID 基数和恶意敏感输入；不会调用真实 DeepSeek，不登录或真实发布 Feishu，不删除业务或监控 Volume。LLM、SQL、Evidence、Chart 完成事件使用与 HTTP/Workflow/Delivery/Trace 相同的 correlation/redaction 合同，指标仍不含 ID、原始路径、异常文本、SQL 或业务内容 Label。

完整逐告警诊断、禁止事项、恢复和升级条件见 `docs/operations/observability-alerts.md`。日常停止必须保留 Volume；只清理监控数据时才在确认 `COMPOSE_PROJECT_NAME` 后使用 `make observability-down-v`。

## 持久化、停止与备份边界

| Volume | 容器路径 | 用途 |
|---|---|---|
| `workspace-data` | `/app/workspaces` | Workspace、导入数据、Run 历史、ReportRecord/ReportDocument、Markdown、Word 和 Workspace 图表产物 |
| `report-data` | `/app/reports` | 项目级报告/图表持久化根与后续扩展边界 |
| `trace-data` | `/app/logs/traces` | 当前本地 JSON Trace |
| `prometheus-data` | `/prometheus` | 可选 Profile 的 Prometheus TSDB |
| `grafana-data` | `/var/lib/grafana` | 可选 Profile 的 Grafana 本地状态 |

`docker compose down`（也是 `make down`）删除容器和网络，但保留 Volume。`docker compose down -v` 会永久删除当前 Compose project 的三个 Volume；只有在确认 project name、实际卷名和备份后才能使用。

P37 没有自动备份/恢复或灾备。备份应在服务停止或应用写入已冻结时，由部署者使用 Docker Volume 备份机制复制三个 Volume；Workspace 相关记录与导出物应作为一个一致性集合处理。不要只备份镜像。

## 排障

### 端口冲突

用 `lsof -nP -iTCP:8000 -sTCP:LISTEN` 和 `lsof -nP -iTCP:3000 -sTCP:LISTEN` 找占用者，或在 `.env` 覆盖两个 host port、公开 API base 和 CORS 后重新构建前端。不要把浏览器 API base 写成仅容器内可解析的 `http://backend:8000`。

### backend unhealthy

```bash
docker compose ps
docker compose logs --tail 200 backend
docker compose exec backend id
docker compose exec backend python -c 'import api.app'
docker compose exec backend python -m pip check
```

检查 `/health/ready` 四项状态、Volume 可写性和配置结构。健康输出不会返回内部路径；具体原因从受控容器日志和挂载状态排查。

### frontend unhealthy

```bash
docker compose logs --tail 200 frontend
docker compose exec frontend id
curl --fail --location http://127.0.0.1:3000/
```

确认 backend 已 healthy、前端 standalone `server.js` 正常、端口无冲突，并确认 `NEXT_PUBLIC_API_BASE` 与实际后端 host port 一致。该值变更后必须重建前端镜像。

### Volume 权限

两个容器运行 UID 10001；后端三个挂载根必须对 UID/GID 10001 可写。

```bash
docker compose exec backend id
docker compose exec backend sh -c 'ls -ld /app/workspaces /app/reports /app/logs/traces && test -w /app/workspaces && test -w /app/reports && test -w /app/logs/traces'
docker volume ls
docker volume inspect <project>_workspace-data
```

不要为快速修复而挂载用户 Home、`.env` 或 Docker Socket，也不要把容器改成 root。外部预置 Volume 时，应在部署流程中把所有权设为 10001:10001。

### Docker 磁盘占用

```bash
docker system df
docker buildx du
docker image ls 'insightflow-*'
```

P37 保留最终两个 `:p37` 镜像。删除旧项目标签前先确认没有容器引用。不要使用 `docker volume prune` 或 `docker system prune -a --volumes`。BuildKit cache 可能属于其他项目，是否做全局 cache prune 应由机器所有者决定。Docker Desktop 的 Docker.raw 逻辑容量不等于实际物理占用。

## Feishu CLI 与生产边界

基础镜像不安装 `lark-cli`，不挂载本机 Home 或飞书认证目录，也不在健康检查中调用发布工具。因此容器内飞书发布会返回明确失败/警告，不会假成功。非容器本机模式仍可使用已经安装和登录的 CLI；容器化飞书认证需要后续单独设计。

当前只支持一个后端实例配合本地 SQLite/Workspace 文件。P37 不支持多副本 SQLite、Kubernetes/Helm、云部署、TLS/Ingress、正式 Secret Manager、自动部署、自动镜像推送或灾备。P38-H1-H6 的 Request ID、关联/脱敏、结构化事件、TraceSink/Retention、应用指标、Prometheus/Grafana、Dashboards、告警、确定性规则测试、Failure Injection 和 Runbook 已完成。Alertmanager、OpenTelemetry/OTLP、外部 Observability SaaS、Docker socket、云凭证和前端遥测仍未实现。
