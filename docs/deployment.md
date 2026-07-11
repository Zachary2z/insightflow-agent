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

## 持久化、停止与备份边界

| Volume | 容器路径 | 用途 |
|---|---|---|
| `workspace-data` | `/app/workspaces` | Workspace、导入数据、Run 历史、ReportRecord/ReportDocument、Markdown、Word 和 Workspace 图表产物 |
| `report-data` | `/app/reports` | 项目级报告/图表持久化根与后续扩展边界 |
| `trace-data` | `/app/logs/traces` | 当前本地 JSON Trace |

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

当前只支持一个后端实例配合本地 SQLite/Workspace 文件。P37 不支持多副本 SQLite、Kubernetes/Helm、云部署、TLS/Ingress、正式 Secret Manager、自动部署、自动镜像推送或灾备。结构化日志、Prometheus、Grafana 和告警属于仍为 Planned 的 P38。
