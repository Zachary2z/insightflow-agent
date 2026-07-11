# P37 Containerized Reproducible Deployment

Status: complete; H1-H5 complete
Date: 2026-07-11

## Goal

P37 moves InsightFlow from a locally started FastAPI/Next.js prototype to a reproducibly deployable application. A new developer or an acceptance environment should be able to build, start, verify, stop, and restart the product through documented commands without installing Python or Node.js on the host.

The target product path is:

```text
source checkout
-> validated environment configuration
-> deterministic backend/frontend image builds
-> Docker Compose starts the product
-> backend liveness and readiness become healthy
-> frontend becomes reachable after backend readiness
-> workspace/report/trace artifacts survive service restart
-> container smoke test exercises a safe local product path
```

Containerization is an operational boundary only. It must not change the Analysis Workbench evidence chain, Report Center generation path, answer contracts, chart contracts, export packages, or external publishing semantics.

## Engineering Outcomes

P37 is complete only when it provides all of the following:

- Multi-stage backend and frontend images with small runtime stages.
- Non-root runtime users and read/write permissions limited to intended runtime directories.
- Reproducible dependency installation with explicit dependency-lock strategy.
- Separate build-time and runtime configuration.
- No `.env`, credentials, generated workspaces, local databases, traces, reports, test caches, or frontend development artifacts inside production images.
- Docker Compose orchestration with health checks, persistent volumes, internal service discovery, restart policy, and optional profiles where appropriate.
- Liveness and readiness contracts that distinguish process health from product readiness.
- One-command local operations for build, start, stop, logs, tests, and smoke verification.
- Automated acceptance proving service startup, API/UI reachability, persistence, shutdown, and secret/artifact hygiene.
- Documentation that explains local development, container operation, configuration, troubleshooting, and current production boundaries.

## Current Foundations To Reuse

- Backend entry point: `api.app:app`.
- Frontend entry point: Next.js application in `frontend/`.
- Runtime configuration is already environment-driven for DeepSeek, product live mode, frontend API base, and `lark-cli`.
- Local product paths already separate source modules from generated workspace, report, chart, and trace artifacts.
- `.gitignore` already identifies most generated/sensitive paths.
- `tests/conftest.py` can generate the local SQLite test fixture on demand.
- Existing no-key behavior allows deterministic local startup and selected non-live acceptance without DeepSeek credentials.

## Product And Deployment Scope

### In Scope

- Backend production image for FastAPI/Uvicorn.
- Frontend production image using Next.js standalone output.
- Root and frontend `.dockerignore` files.
- Compose services for the backend and frontend.
- Named volumes or explicitly documented bind mounts for persistent workspace/report/trace data.
- Backend `/health/live` and `/health/ready` endpoints.
- Container health checks and dependency ordering.
- Environment templates and validation for required versus optional configuration.
- Makefile or equivalent checked-in command surface.
- Container smoke test runnable locally and in CI.
- Image inspection tests for secrets, generated artifacts, development dependencies where practical, and non-root operation.
- Deployment and troubleshooting documentation.
- Compose extension points needed by P38 for Prometheus and Grafana.

### Out Of Scope

- Kubernetes, Helm, service mesh, autoscaling, blue/green deployment, or multi-region deployment.
- Public cloud provisioning, domain registration, TLS certificate automation, CDN, or production ingress.
- OAuth UI, RBAC, multi-tenant isolation, billing, or user-account management.
- Replacing SQLite with a network database.
- Running multiple backend replicas against shared local SQLite/workspace volumes.
- Baking DeepSeek keys, Feishu credentials, `.env`, databases, reports, or traces into an image.
- Treating optional external services as readiness requirements.
- Changing business answers, evidence planning, SQL review, chart generation, report composition, or Feishu publishing content.
- Pretending `lark-cli` authentication exists inside a container when it has not been explicitly mounted/configured.

## Target Runtime Architecture

```text
Host / CI runner
|
+-- docker compose
    |
    +-- frontend:3000
    |   +-- Next.js standalone runtime
    |   +-- calls backend through configured API base
    |
    +-- backend:8000
        +-- FastAPI/Uvicorn
        +-- /health/live
        +-- /health/ready
        +-- /metrics reserved for P38
        +-- workspace-data volume
        +-- report-data volume
        +-- trace-data volume
```

P38 may extend the same Compose project with `prometheus` and `grafana`. P37 should keep the network and configuration layout ready for this extension without adding placeholder services.

## Configuration Contract

Configuration must be classified rather than treated as one undifferentiated `.env` file.

### Build-Time Configuration

- Frontend production build mode.
- Next.js standalone output.
- Public browser API base only when it must be embedded in the client bundle.
- No secret may be passed through `ARG` or persisted in an image layer.

### Runtime Non-Secret Configuration

- Backend bind host and port.
- Frontend bind host and port.
- Product live-mode switches.
- Workspace/report/trace roots.
- Log level and, later, observability switches.
- Optional `LARK_CLI_BIN` when the CLI is genuinely available in the runtime environment.

### Runtime Secrets

- `DEEPSEEK_API_KEY`.
- Future direct Feishu/OpenAPI credentials.
- Any deployment-platform credentials.

Secrets must be injected at runtime through environment variables, Docker secrets, or the deployment platform. They must not appear in Compose defaults, image history, logs, health responses, or smoke-test output.

## Health Contract

### Liveness

`GET /health/live` answers whether the application process can serve requests.

Expected response:

```json
{"status": "ok", "service": "insightflow-api"}
```

Liveness must not call DeepSeek, Feishu, SQLite business queries, or other external dependencies. A temporary provider failure must not cause a container restart loop.

### Readiness

`GET /health/ready` answers whether the backend can safely accept product traffic.

Minimum checks:

- required runtime directories exist or can be created;
- required directories are readable/writable by the non-root runtime user;
- application configuration is structurally valid;
- the local storage boundary can perform a small safe check without touching user data.

Optional DeepSeek credentials, provider availability, and Feishu authentication are reported only as capability status when safe; they do not make the base product unready.

Health responses must not expose paths, keys, environment dumps, stack traces, provider responses, or credentials.

## Persistent Data Contract

At minimum the following runtime state must survive container recreation:

- workspace metadata and imported workspace data;
- analysis run history and report records;
- exported report documents and chart assets when retained by current product behavior;
- trace files until P38 retention policies are active.

Named volumes should be the safe default. Development bind mounts may be documented separately. Image source code remains immutable; writable application state must be directed only to intended volume-backed paths.

Backup/restore automation is not required in P37, but volume ownership, paths, and data-loss behavior of `docker compose down -v` must be documented clearly.

## P37 Tasks

### P37-H1: Production Build Contracts And Images

Create deterministic production images before orchestration.

Expected changes:

- Add a backend `Dockerfile` with builder/runtime stages.
- Use a supported slim Python base image and pin the major/minor runtime version.
- Install dependencies without a compiler/toolchain in the final stage where possible.
- Run the backend as a dedicated non-root user.
- Add root `.dockerignore` rules covering `.git`, `.env*` except safe templates, virtual environments, caches, test outputs, workspace data, reports, traces, local databases, temporary files, `.next`, and `node_modules`.
- Enable `output: "standalone"` in `frontend/next.config.ts`.
- Add `frontend/Dockerfile` with dependency, build, and non-root runtime stages.
- Add a frontend `.dockerignore`.
- Use deterministic frontend installation through `npm ci` and the committed lockfile.
- Decide and document the Python lock strategy. P37 should prefer a compiled/locked runtime dependency set or exact pins rather than leaving production builds on unconstrained package resolution.

Tests and verification:

- Backend image builds from a clean context.
- Frontend image builds from a clean context.
- Both runtime containers execute as non-root.
- Production images do not contain `.env`, local `.db` files, workspace/report/trace artifacts, test caches, `.git`, or `node_modules` from the host.
- Backend imports `api.app` and frontend standalone server starts.
- Image build does not require DeepSeek or Feishu credentials.

Definition of done:

- Dockerfiles and ignore rules are present and reviewable; creating the repository commit remains an explicit user action.
- Build commands are documented and deterministic on a clean checkout.
- Security and image-content checks are executed for H1; reusable smoke/CI automation remains the explicit P37-H4 deliverable.

Implementation result (2026-07-11): complete for H1. The repository now has Python 3.12 slim and Node 22 Alpine multi-stage production images, exact Python runtime pins, Next.js standalone output, `npm ci`, non-root UID/GID 10001 users, and root/frontend context exclusions. The acceptance commands below were executed directly for H1; the reusable smoke/CI automation required by the phase remains P37-H4 work.

Verified commands and results:

```bash
docker build -t insightflow-backend:p37-h1 .
docker build -t insightflow-frontend:p37-h1 ./frontend
docker run --rm --entrypoint id insightflow-backend:p37-h1
docker run --rm --entrypoint id insightflow-frontend:p37-h1
docker run --rm --entrypoint python insightflow-backend:p37-h1 -c 'import api.app'
.venv/bin/python -m pytest tests/test_project_initialization.py tests/test_runtime_provider.py tests/test_product_live_mode.py -q
cd frontend && npm test
cd frontend && npm run build
git diff --check
```

- Both images built and ran as Linux arm64 on Apple Silicon. The official base images support multiple architectures, but amd64 was not verified in this pass.
- Backend id was `uid=10001(insightflow) gid=10001(insightflow)`; frontend id was `uid=10001(nextjs) gid=10001(nodejs)`.
- Bounded 30-attempt startup checks reached backend OpenAPI after 4 polls and the frontend root page after 2 polls; logs confirmed listeners on `0.0.0.0:8000` and `0.0.0.0:3000`. Cleanup left no test containers.
- Backend focused regression passed (`14 passed`), frontend Vitest passed (`84 passed`), frontend production build passed, the production Python set passed `pip check`, and `git diff --check` passed.
- Lock regeneration reproduced all 56 exact Python pins. `npm audit --omit=dev` reports 3 moderate production findings (`echarts`, `next`, and transitive `postcss`); the registry currently proposes major-version changes rather than a safe in-range repair, so H1 records the risk instead of silently forcing a major upgrade.
- Synthetic full-context images proved `.dockerignore` removes `.env`, `.git`, local DBs, runtime workspace/report/trace artifacts, caches/tests, host `node_modules`, and `.next` before `COPY`; final-image checks found no local DB/runtime artifact, source `.env`, private-key marker, assigned DeepSeek secret, pytest, or pip-tools.
- Python locking uses `requirements.txt` as direct runtime input and `requirements.lock` as exact production pins generated with `pip-tools==7.5.3` on Python 3.12/Linux arm64. `requirements-dev.txt` adds pinned pytest/pip-tools outside production. The lock avoids platform-specific URLs and hashes so one exact version set can resolve native wheels per target; Linux arm64 is verified, while amd64 remains unverified rather than being claimed reproducible.
- `NEXT_PUBLIC_API_BASE` is a public build argument only. Private backend configuration must never be placed in `NEXT_PUBLIC_*`; Compose/browser networking remains P37-H3.

### P37-H2: Health And Lifecycle Contracts

Add explicit service lifecycle behavior.

Expected changes:

- Add `/health/live` and `/health/ready` to FastAPI.
- Keep health response models small and safe.
- Centralize readiness checks so they can be unit tested without starting the full server.
- Validate intended writable directories during readiness.
- Ensure application startup does not require a model key.
- Confirm Uvicorn receives termination signals and exits cleanly.
- Add a backend container health check using Python or a tool intentionally present in the runtime image; do not install a large package only for health checking.

Tests and verification:

- Liveness succeeds when the process is serving.
- Readiness succeeds in a valid no-key environment.
- Readiness fails safely when required storage is unwritable.
- Health output contains no absolute paths, keys, environment dumps, SQL, prompts, or traces.
- SIGTERM stops the backend within the Compose grace period.

Definition of done:

- Compose can depend on the backend's actual readiness rather than a sleep or port-only check.

Implementation result (2026-07-11): complete for H2. `api/health.py` now owns strict health response models, centralized configuration/storage checks, and unique exclusive create/read/write/delete probes that do not scan or read existing Workspace content. `api/lifecycle.py` owns the background analysis Executor; FastAPI lifespan rejects new submissions during shutdown, cancels queued futures, waits for running work to finish, and releases threads. The backend Dockerfile uses a silent Python-standard-library readiness HEALTHCHECK.

Verified commands and results:

```bash
python3 -m pytest tests/test_health_api.py -q
python3 -m pytest tests/test_workspace_api.py tests/test_workspace_run_history_api.py tests/test_workspace_analysis_runner.py tests/test_project_initialization.py -q
docker build --no-cache -t insightflow-backend:p37-h2 .
cd frontend && npm test
cd frontend && npm run build
git diff --check
```

- Health/lifecycle tests passed (`17 passed`); focused Workspace/lifecycle regression passed (`82 passed`); frontend Vitest passed (`84 passed`); frontend production build and diff check passed.
- The Linux arm64 container started without DeepSeek/OpenAI keys, Feishu credentials, or `lark-cli`. Live returned `200` with the strict two-field contract; ready returned `200` with workspace/report/trace/configuration all `ok`.
- Controlled required-storage failures returned `503` without paths, exception text, secrets, SQL, prompts, trace data, user content, environment values, or provider responses. Exclusive probes were cleaned and never overwrote a collision file.
- Image inspection confirmed the readiness HEALTHCHECK parameters (10-second interval, 3-second timeout, 10-second start period, 3 retries). Bounded polling reached Docker `healthy` within 45 seconds. A forced health-command connection failure returned non-zero with empty output.
- The runtime identity remained `uid=10001(insightflow) gid=10001(insightflow)`. `docker stop -t 10` exited 0 in about 0.56 seconds and Uvicorn logged normal application shutdown. The temporary container was removed, and the existing P37-H1 frontend image was not rebuilt or modified.
- Compose, named volumes, service networking, full smoke/CI operations, Kubernetes probes, frontend health, DeepSeek/Feishu probing, P37 closeout, and P38 observability were not implemented in H2.

### P37-H3: Compose Orchestration And Persistence

Build the one-command product runtime.

Expected changes:

- Add `compose.yaml` with backend and frontend services.
- Use internal service DNS for server-to-server access and an explicit browser-facing API base for client requests.
- Add named volumes for persistent runtime data.
- Add `restart: unless-stopped` or an explicitly justified equivalent.
- Add health-based dependency ordering where supported.
- Add reasonable stop grace periods.
- Keep secrets out of the Compose file and provide a safe `.env.example` contract.
- Document port overrides and volume locations.
- Document Feishu behavior: base containers must work without `lark-cli`; a real CLI/auth mount is optional, explicit, and must not weaken the default image/security boundary.
- Reserve a Compose profile or extension layout for P38 observability services if helpful, but do not ship nonfunctional placeholders.

Tests and verification:

- `docker compose config` succeeds without revealing secrets.
- `docker compose up --build -d` reaches healthy state.
- Frontend can reach the configured backend.
- Container recreation preserves a created workspace and report/run history.
- `docker compose down` preserves named volumes.
- `docker compose down -v` data-loss behavior is documented.

Definition of done:

- A clean host with Docker can run the base product using documented commands.

Implementation result (2026-07-11): complete for H3. `compose.yaml` now defines the backend and frontend production services, preserves the backend image HEALTHCHECK, gates frontend startup on backend readiness, adds a lightweight Node frontend health check, uses loopback-only host ports and one explicit non-internal bridge network, and persists Workspace/report/trace state in three separate logical named volumes. Both services retain the image-defined UID/GID 10001 runtime and use `init`, restart, and bounded graceful-stop contracts.

Verified commands and results:

```bash
docker compose --env-file /dev/null config -q
COMPOSE_PROJECT_NAME=insightflow-p37-h3-audit docker compose --env-file /dev/null up --build -d
python3 -m pytest tests/test_compose_contract.py tests/test_health_api.py tests/test_workspace_api.py tests/test_workspace_run_history_api.py tests/test_workspace_analysis_runner.py tests/test_project_initialization.py -q
cd frontend && npm test
cd frontend && npm run build
git diff --check
```

- Both services reached Docker `healthy` on Linux arm64. Live, ready, and the redirect-following frontend root request returned `200`; backend was `uid=10001(insightflow)` and frontend was `uid=10001(nextjs)`. Empty DeepSeek/OpenAI key values and missing `lark-cli` did not block startup or readiness.
- The isolated volumes were `insightflow-p37-h3-audit_workspace-data -> /app/workspaces`, `..._report-data -> /app/reports`, and `..._trace-data -> /app/logs/traces`. All mounted roots were `10001:10001` and writable.
- An API-created Workspace plus unique report and trace markers survived `docker compose down` and a fresh `up -d`. The original Workspace id returned `200`, both markers remained, readiness returned `200`, and storage stayed writable.
- Backend restart returned to healthy. Full Compose stop took about 1 second and logs recorded the complete normal Uvicorn application shutdown sequence; subsequent start restored both healthy services.
- Compose/health/Workspace regression passed (`105 passed`), frontend Vitest passed (`84 passed`), frontend production build and diff check passed.
- BuildKit cache was reused without `--no-cache`. Docker system usage moved from 6 images / 1.4 GB and 5.22 GB build cache to 8 images / 1.402 GB and 5.222 GB build cache. No prune ran and no pre-existing volume was touched.
- Audit cleanup removed all isolated containers, network, volumes, Workspace, and markers. The tagged `insightflow-backend:p37-h3` and `insightflow-frontend:p37-h3` images remain for reuse.
- The base Compose contract does not bundle or mount Feishu CLI/auth state. Local `.env` runtime injection is only a convenience and is not claimed as production secret management.
- Historical H3 note superseded: P37-H4 and P37-H5 are now complete; P38 has not started.

### P37-H4: Operations Commands, Smoke Tests, And CI Readiness

Implementation result (2026-07-11): complete. The root Makefile now provides a safe help-first operation surface. The executable `scripts/docker_smoke_test.sh` is the single local/CI no-key acceptance path, and `.github/workflows/ci.yml` calls that exact script after backend/frontend tests, frontend build, Compose validation, and syntax checking.

Turn the deployment setup into a repeatable engineering workflow.

Expected changes:

- Add a Makefile or equivalent help-first command surface for build/up/down/restart/status/logs/test/build/smoke operations without a destructive clean target.
- Add `scripts/docker_smoke_test.sh` or an equivalent test runner.
- Smoke test waits on health with a bounded timeout rather than sleeping blindly.
- Exercise at least health, a safe workspace/API path, frontend reachability, and persistence across restart.
- Ensure cleanup executes on failure.
- Return non-zero exit codes for build, startup, health, API, persistence, or hygiene failures.
- Add a CI-ready command that can run without live model credentials.
- If CI is introduced in this phase, it must run unit tests, frontend tests/build, Compose validation, image builds, and the no-key container smoke test.

Tests and verification:

- Smoke test passes from a clean checkout.
- A deliberately broken backend health state causes a bounded, readable failure.
- Smoke output contains no API keys, raw uploaded rows, SQL results, local secret paths, or provider payloads.
- The operations commands are documented and work consistently.

Definition of done:

- Container acceptance can be executed locally and by an automated runner with the same command.

Verified H4 result:

- The successful isolated project used the required `insightflow-smoke-` prefix with timestamp/PID uniqueness, ports `127.0.0.1:18000` and `127.0.0.1:13000`, a temporary empty env file, coordinated public API/CORS settings, normal BuildKit cache, bounded 90-second Docker health polling, and curl connection/total timeouts.
- Both services reached healthy; live returned `status=ok`; ready returned `status=ready` with four `ok` checks; frontend returned 200. Both services ran as UID 10001 without DeepSeek/OpenAI keys or `lark-cli`; only loopback ports were published; Docker socket, `.env`, and user Home were not mounted.
- A unique Workspace was created, fetched, found in the list, populated with a synthetic CSV, and profiled. It was not a user Workspace and no real business data, DeepSeek call, or Feishu call was used.
- The three expected project-prefixed volumes were correctly mounted and writable. The Workspace plus report/trace markers survived ordinary `down` and a fresh `up -d`; readiness remained ready. Backend graceful restart recovered healthy and logged completed shutdown/startup without Executor exit blockage.
- Prefix/label guards ran before isolated `down -v`; final audit found no Smoke containers, networks, or volumes. No global prune or user-volume deletion occurred; reusable images and BuildKit cache remain.
- Full backend tests passed (`788 passed, 15 skipped`), frontend Vitest passed (`84 passed`), frontend production build passed, and the requested focused backend/operations selection passed (`112 passed`). Script syntax, Make help/Compose/test/smoke, operations contracts, and diff checks passed.
- Docker system usage changed from 8 images / 1.402 GB and 5.222 GB Build Cache to 8 images / 1.486 GB and 5.531 GB Build Cache. No cleanup beyond the isolated project ran.
- GitHub Actions was not remotely executed. The workflow is configured and locally statically checked only; amd64 is not claimed as verified.

### P37-H5: Acceptance, Documentation, And Closeout

Verify the product boundary after containerization.

Required acceptance:

- Backend pytest suite passes under the supported development/runtime strategy.
- Frontend Vitest suite and production build pass.
- Backend and frontend images build with no cache from a clean context.
- Compose validation and no-key smoke acceptance pass.
- A workspace/run/report persistence scenario survives service recreation.
- Analysis Workbench and Report Center remain separate product paths.
- Word export and chart static assets remain available in volume-backed storage.
- Optional live DeepSeek and Feishu checks remain explicitly gated and are not required for base readiness.
- `git diff --check` passes.
- Generated runtime artifacts remain ignored and untracked.
- README, `.env.example`, development status, and troubleshooting docs match the verified commands.

Closeout evidence must record exact commands and results. It must not claim live provider, Feishu, multi-replica, cloud, TLS, or disaster-recovery readiness unless those checks actually ran.

Implementation result (2026-07-11): complete. Compose uses final `insightflow-backend:p37` and `insightflow-frontend:p37` tags. The only final no-cache Compose build passed on actual Linux arm64; both images run as UID 10001, backend keyless import and `pip check` pass, frontend standalone content is present, and final-image hygiene excludes local/runtime artifacts. amd64 was not verified.

The expanded canonical Smoke used isolated project `insightflow-smoke-20260711203054-9270`. Both services became healthy; live, ready, and frontend returned 200; all four readiness checks were `ok`; runtime ports/mounts/optional-capability boundaries passed. It created a synthetic Workspace, CSV profile, semantic draft, Analysis Run/history, ReportRecord, ReportDocument and Evidence Ledger, downloaded Markdown, exported/downloaded a real `.docx`, and required either a persisted static chart asset or an explicit safe warning. All product records and exports survived ordinary `compose down` followed by `up`; graceful restart passed. No real DeepSeek or Feishu call ran, and cleanup removed only the isolated project resources.

Verification results:

```text
focused product-boundary pytest: 127 passed
H5/operations/Compose contracts: 21 passed
make test backend: 796 passed, 15 skipped
separate full backend pytest: 796 passed, 15 skipped
frontend Vitest (twice): 84 passed
frontend production build (twice): passed
make compose-check / make smoke / bash -n / git diff --check: passed
npm audit --omit=dev: 3 moderate findings; breaking-major fix only, not forced
```

The GitHub workflow is configured and passed local static contract checks only; no remote GitHub Actions run occurred. Docker usage was 8 images / 1.486 GB plus 5.531 GB cache before final build, 10 images / 1.752 GB plus 7.444 GB cache before cleanup, and 3 images / 783.4 MB plus 7.444 GB cache after removing only unreferenced P37 H1/H1-review/H2/H3 tags. `docker system df` reported 5.935 GB cache reclaimable. No Volume or global cache prune ran. The two final `:p37` images remain; no H5/Smoke container, network, or Volume remains. Deployment and troubleshooting guidance is in `docs/deployment.md`. P38 remains Planned, with P38-H1 as the next planned task.

## Suggested File Layout

```text
Dockerfile
.dockerignore
compose.yaml
Makefile
scripts/
  docker_smoke_test.sh
frontend/
  Dockerfile
  .dockerignore
docs/
  deployment.md
```

Final names may follow repository conventions, but the responsibilities should remain separate.

## Risks And Mitigations

### SQLite And Multiple Workers

Risk: multiple Uvicorn workers or replicas can create unsafe assumptions around SQLite and local workspace files.

Mitigation: default to one backend process/container for P37, document the boundary, and avoid presenting horizontal scaling as supported.

### Browser Versus Container Networking

Risk: `backend:8000` resolves inside Compose but not in the user's browser.

Mitigation: distinguish server-internal URLs from the public browser API base and test both paths.

### Volume Ownership

Risk: the non-root runtime user cannot read or write mounted paths.

Mitigation: define runtime UID/GID behavior, create intended directories during the image build/startup path, and test readiness against mounted volumes.

### Secret Leakage Through Build Context

Risk: `.env`, databases, traces, or generated reports enter image layers even if they are later deleted.

Mitigation: exclude them with `.dockerignore` before build, inspect the final image, and never pass secrets as build arguments.

### Feishu CLI Coupling

Risk: bundling a locally authenticated CLI makes the image non-portable and may leak credentials.

Mitigation: keep Feishu CLI support optional and explicit; the base image and health contract must not depend on it.

## Exit Criteria

P37 is complete when a clean Docker-capable environment can build and operate InsightFlow through documented commands; health and persistence behavior are tested; runtime users and image contents meet the security boundary; the existing product paths pass regression; and no credentials or generated user artifacts are embedded in images or emitted by acceptance tooling.
