# P38 Observability And Operations

Status: planned after P37; H1-H6 pending
Date: 2026-07-11

## Goal

P38 turns the existing local execution trace into an operations-ready observability system. Operators should be able to answer:

- Is the API healthy and responsive?
- Which workflow node, provider, SQL/tool boundary, report step, or external publisher is failing?
- Is the failure isolated or systemic?
- What changed in request volume, latency, route mix, provider behavior, or evidence validation?
- Which `request_id` and `run_id` identify the affected analysis without exposing customer data?
- Which alert fired, what does it mean, and what safe remediation should be attempted?

The target path is:

```text
incoming HTTP request
-> request correlation context
-> workflow run/session/workspace correlation
-> allowlisted structured application events
-> existing business trace through TraceSink
-> bounded Prometheus metrics
-> provisioned Grafana dashboards
-> tested alert rules and operational runbooks
```

P38 complements rather than replaces the existing business evidence/audit model. Evidence Ledger answers "why is this business conclusion supported?"; observability answers "how did the system execute and is it operating correctly?".

## Engineering Outcomes

P38 is complete only when it provides:

- A documented observability contract and event taxonomy.
- Correlation across HTTP request, workspace, analysis run, session, workflow node, tool call, report generation, and external publishing.
- Structured JSON application logs using allowlisted fields and central redaction.
- A trace-sink abstraction that preserves the current local trace/dashboard behavior.
- Prometheus metrics for HTTP, workflow, provider, SQL, evidence, chart, report, and external publishing boundaries.
- Bounded metric labels with automated cardinality checks.
- Provisioned Grafana dashboards stored in the repository.
- Actionable alert rules with severity, duration, evidence, and runbook links.
- Local retention and resource defaults for logs/traces/metrics.
- Failure-injection and security tests proving signals appear without leaking prompts, rows, credentials, raw provider responses, or internal paths.
- Operational documentation covering normal checks, triage, retention, and known limitations.

## Current Foundations To Reuse

- `tools.trace_logger` already normalizes tool/node events and persists per-run JSON traces.
- Agent state already carries `run_id`, `session_id`, workflow node data, tool summaries, latency, status, error type, and retry count.
- Workspace analysis/report stores provide stable run/report lifecycle boundaries.
- SQL validation/execution, LLM providers, chart generation, document export, and Feishu publishing already return structured status and timing information in several paths.
- The project already applies safe output filtering to export and external-publish artifacts.
- `dashboard/trace_dashboard.py` provides an existing local trace inspection surface that must remain usable during migration.
- P37 provides Compose networking, health endpoints, configuration boundaries, and an operational command surface.

## Observability Model

### Signal Types

1. Structured logs: discrete application and operational events used for diagnosis.
2. Metrics: bounded numeric time series used for trends, SLOs, dashboards, and alerts.
3. Business execution traces: ordered InsightFlow workflow/tool events associated with one analysis run.
4. Distributed traces: optional later OTLP/OpenTelemetry extension; not required to complete the initial P38 scope unless it can be added without destabilizing the business trace.

### Correlation Fields

The correlation model should support:

```text
request_id
run_id
session_id
workspace_id
report_id
node
tool_name
operation
provider
status
error_type
latency_ms
retry_count
```

Not every signal contains every field. Logs and business traces can contain bounded opaque identifiers. Metrics must not use `request_id`, `run_id`, `session_id`, `workspace_id`, `report_id`, user questions, table names, filenames, or error messages as labels.

### Event Taxonomy

Recommended event names:

```text
http_request_started
http_request_completed
workflow_run_started
workflow_run_completed
agent_node_started
agent_node_completed
llm_request_completed
sql_validation_completed
sql_execution_completed
evidence_validation_completed
chart_generation_completed
report_generation_completed
document_export_completed
external_publish_completed
trace_persist_completed
```

Event names, statuses, error types, and operation names must come from controlled vocabularies where possible.

## Security And Privacy Boundary

Observability is not allowed to become a second data export path.

### Never Log Or Label

- DeepSeek or platform API keys, bearer tokens, cookies, authorization headers, or Feishu credentials.
- Full prompts, system messages, raw provider requests/responses, or model reasoning.
- Uploaded CSV/Excel/SQLite rows or raw SQL result rows.
- Raw evidence tables, report evidence values, or customer business data.
- Full generated SQL in normal logs.
- Local absolute paths, database paths, workspace filesystem layout, or temporary file names.
- Entire environment/configuration dumps.
- Raw exceptions when they may contain any prohibited content.
- User questions as metric labels or default log fields.

### Allowed By Default

- Opaque correlation identifiers in logs/traces.
- Controlled operation/node/tool/provider names.
- Success/failure/warning status.
- Latency, retry count, row count, evidence count, chart count, and token counts when they do not expose content.
- Normalized error categories.
- Safe, length-bounded summaries produced by centralized allowlisting/redaction.

Redaction must be centralized and tested with malicious/secret-like fixtures. Call sites must not each invent their own sanitizer.

## Target Architecture

```text
FastAPI / workflow / tools
|
+-- CorrelationContext
|   +-- contextvars-based request/run/workspace fields
|
+-- StructuredLogger
|   +-- allowlisted JSON to stdout
|   +-- container runtime collects stdout
|
+-- TraceSink
|   +-- LocalJsonTraceSink
|   +-- StructuredLogTraceSink
|   +-- CompositeTraceSink
|   +-- future OtlpTraceSink
|
+-- MetricsRegistry
    +-- /metrics
    +-- Prometheus
        +-- recording/alert rules
        +-- Grafana dashboards
```

Production-oriented container logging should prefer stdout/stderr rather than additional unbounded log files. Existing per-run JSON traces may remain volume-backed with explicit retention until a later external trace backend is adopted.

## Metrics Contract

Names below are the proposed stable surface; implementation may refine suffixes to follow Prometheus conventions.

### HTTP

```text
insightflow_http_requests_total{method,route,status_class}
insightflow_http_request_duration_seconds{method,route}
insightflow_http_requests_in_progress{method,route}
```

Use normalized route templates rather than raw URLs or IDs.

### Workflow And Agent Nodes

```text
insightflow_runs_total{route,status}
insightflow_run_duration_seconds{route,status}
insightflow_node_executions_total{node,status}
insightflow_node_duration_seconds{node,status}
insightflow_clarifications_total{reason_category}
insightflow_retries_total{operation,error_type}
```

### LLM Provider

```text
insightflow_llm_requests_total{provider,operation,status}
insightflow_llm_duration_seconds{provider,operation,status}
insightflow_llm_tokens_total{provider,operation,token_type}
insightflow_llm_fallbacks_total{operation,reason_category}
```

Model names should be normalized to an approved bounded set or excluded if runtime variability would create unbounded cardinality.

### SQL And Evidence

```text
insightflow_sql_validations_total{status,risk_level}
insightflow_sql_executions_total{status,error_type}
insightflow_sql_duration_seconds{status}
insightflow_evidence_validations_total{status,reason_category}
insightflow_evidence_tasks_total{status,route}
```

Never use SQL text, table names, column names, workspace IDs, or database paths as labels.

### Product Delivery

```text
insightflow_chart_generations_total{chart_type,status}
insightflow_report_generations_total{status}
insightflow_document_exports_total{format,status}
insightflow_external_publishes_total{platform,status}
insightflow_external_publish_duration_seconds{platform,status}
```

### Process And Storage

Use standard process/runtime collectors where safe. Add bounded application storage gauges only when they can be measured cheaply and without path labels, for example total retained trace bytes or workspace storage bytes.

## Dashboard Contract

### System Health Dashboard

- Backend up/health state.
- Request throughput.
- 4xx/5xx rates.
- P50/P95/P99 request latency.
- In-progress requests.
- Process CPU/memory and container restart indicators when available.

### Analysis Workflow Dashboard

- Runs by fast/standard/deep route and status.
- End-to-end run latency.
- Node execution latency and failure count.
- Clarification and retry rates.
- Evidence validation/task success rate.

### Provider And Tool Dashboard

- LLM request rate, latency, timeout/error rate, token volume, and fallback rate.
- SQL validation rejection rate and execution failure rate.
- Chart/report/export/publish success rates.

### Delivery Dashboard

- Analysis completion rate.
- Report generation and Word export rates.
- Chart generation success/skip rate.
- Feishu document/sheet publish status.

Dashboards must be provisioned from version-controlled JSON or configuration. Manual dashboard creation is not the source of truth.

## Alert Contract

Initial alerts should be small, actionable, and tied to runbooks.

| Alert | Initial condition | Severity | Required runbook focus |
|---|---|---|---|
| BackendUnavailable | backend unavailable for 1 minute | critical | container health, startup error, volume permissions |
| HighHttp5xxRate | 5xx ratio above 5% for 5 minutes with minimum traffic | warning/critical by duration | recent error categories and failing routes |
| HighApiLatency | P95 above agreed threshold for 10 minutes | warning | workflow/provider/SQL latency decomposition |
| HighLlmFailureRate | provider failures/timeouts above 10% for 10 minutes | warning | key/config, provider status, fallback behavior |
| HighSqlFailureRate | SQL execution failures exceed threshold | warning | validation versus execution error categories |
| HighEvidenceFailureRate | evidence validation failures stay elevated | warning | source compatibility, planning, validator changes |
| ExternalPublishFailureBurst | repeated Feishu publish failures | warning | CLI/auth/platform status without logging credentials |
| RuntimeStorageHigh | retained runtime storage above 80% of configured capacity | warning | retention and safe cleanup |

Thresholds must be configurable and tuned using observed local/acceptance behavior. Alerts should include dashboard and runbook references, not raw customer data.

## Retention And Cardinality Policy

- Structured container logs: bounded by deployment runtime rotation; document local defaults.
- Local JSON business traces: retain by age and/or total size; never delete active-run files.
- Prometheus data: use a conservative local retention duration and size limit.
- Grafana: persist provisioned configuration and only necessary local state.
- Metric label values: controlled enumerations or normalized route templates only.
- New metrics require a label-cardinality review.
- Per-run identifiers belong in logs/traces, never metric labels.

P38 may add a safe maintenance command for trace retention. It must default to dry-run or clearly scoped deletion behavior and must never delete workspace/report business artifacts when managing trace retention.

## P38 Tasks

### P38-H1: Observability Contract And Correlation Context

Define the boundary before instrumenting call sites.

Expected changes:

- Add `observability/` with shared context, event, redaction, and configuration modules.
- Define typed/validated structured event fields and controlled vocabularies.
- Generate or accept a safe `request_id` at the HTTP boundary.
- Use `contextvars` or an equivalent request-safe approach for correlation propagation.
- Bind `run_id`, `session_id`, `workspace_id`, and `report_id` only when known.
- Return `X-Request-ID` or a documented equivalent response header.
- Define central field allowlisting, secret detection, length limits, and error normalization.
- Document which identifiers may appear in logs/traces versus metrics.

Tests:

- Concurrent requests do not leak correlation context into each other.
- Invalid/injected request IDs are normalized or replaced.
- Context is cleared after request completion.
- Redaction removes keys, bearer tokens, secret-like URLs, local paths, prompts, rows, and provider payload fixtures.
- Event serialization is JSON-safe and bounded.

Definition of done:

- All later instrumentation depends on one reviewed contract rather than ad hoc logging fields.

### P38-H2: Structured Application Logs And HTTP Middleware

Create a safe machine-readable log stream.

Expected changes:

- Configure Python logging to emit one JSON object per event to stdout in container mode.
- Keep a readable development formatter behind explicit configuration if useful.
- Add FastAPI middleware for request start/completion, normalized route, method, status class, and latency.
- Add safe exception middleware/handlers that log normalized error categories and preserve current business-friendly API responses.
- Instrument major workflow lifecycle, report, export, and publishing boundaries using shared helpers.
- Do not duplicate large trace payloads into logs.
- Configure log level and format through environment variables.

Tests:

- JSON logs parse and contain required correlation fields.
- 2xx, 4xx, 5xx, and exception paths emit correct normalized completion events.
- Raw URL IDs/query strings are not used as route fields.
- Prohibited fields/content do not appear in captured logs.
- Logging failures do not break the product request.

Definition of done:

- An operator can filter one request/run and identify the failing bounded operation from stdout logs.

### P38-H3: Business Trace Sink Refactor

Preserve current business tracing while removing direct persistence coupling.

Expected changes:

- Define a `TraceSink` protocol.
- Implement `LocalJsonTraceSink` using the current safe per-run trace behavior.
- Implement `StructuredLogTraceSink` for compact trace lifecycle events where valuable.
- Implement `CompositeTraceSink` with failure isolation between sinks.
- Route current `save_trace` behavior through the sink boundary without changing the trace payload contract unexpectedly.
- Preserve `dashboard/trace_dashboard.py` compatibility or add a tested migration adapter.
- Add configurable retention for local traces by age/size with safe scope.
- Keep an extension point for OTLP/OpenTelemetry without requiring it for local operation.

Tests:

- Existing trace tests and dashboard behavior remain valid.
- One failing sink does not lose a successful local trace or fail the business answer.
- Trace filenames remain path-safe.
- Retention never escapes the configured trace root and never touches active trace files or other artifacts.
- Prohibited content is redacted before emission to non-local sinks.

Definition of done:

- Business code depends on the trace contract, not a specific local filesystem destination.

### P38-H4: Prometheus Metrics

Instrument bounded operational and AI-workflow metrics.

Expected changes:

- Add Prometheus client dependency and one central metrics registry/module.
- Expose `/metrics` on the backend or a documented internal metrics endpoint.
- Instrument HTTP requests, workflow runs/nodes, provider calls, SQL validation/execution, evidence validation, chart generation, report generation, document export, and external publishing.
- Reuse existing measured latency rather than measuring incompatible durations twice.
- Normalize labels through allowlists and fallback buckets such as `other`/`unknown`.
- Avoid double registration under test reload/import behavior.
- Decide whether `/metrics` is public in local Compose and document the production ingress boundary.

Tests:

- Expected counters/histograms change for success, failure, fallback, and timeout fixtures.
- Route labels use templates.
- IDs, questions, SQL, table/column names, filenames, error strings, and model-produced text never appear as labels.
- Cardinality stays within explicit bounds under randomized IDs/errors.
- Metrics instrumentation does not change API/product results.

Definition of done:

- Prometheus can scrape meaningful system and workflow metrics with stable bounded labels.

### P38-H5: Prometheus, Grafana, Dashboards, And Alerts

Build the local operational surface using P37 Compose.

Expected changes:

- Add Prometheus service/configuration with backend scrape target and bounded retention.
- Add Grafana service with provisioned data source and dashboards.
- Add recording rules where they simplify latency/error calculations.
- Add alert rules for availability, error rate, latency, provider failure, SQL/evidence failure, external publishing, and storage.
- Add health checks, persistent data where justified, resource/retention defaults, and an `observability` Compose profile if appropriate.
- Keep Grafana credentials configurable and prevent unsafe default exposure in documented non-local deployments.

Tests and verification:

- Compose configuration validates with and without the observability profile.
- Prometheus target becomes healthy.
- Provisioned dashboards load without manual edits.
- Alert rules pass `promtool check rules` or equivalent validation.
- Grafana provisioning files parse and use the expected data source.

Definition of done:

- A new environment can start the dashboards and alerts from version-controlled configuration.

### P38-H6: Failure Injection, Runbooks, Acceptance, And Closeout

Prove that observability works when the product fails.

Required scenarios:

- Backend unavailable.
- API handler exception.
- Provider timeout/failure and safe fallback where supported.
- SQL validation rejection and SQL execution failure.
- Evidence validation failure.
- Chart/report/export failure.
- Feishu CLI missing or publish failure.
- Unwritable trace destination with another sink remaining available.
- High-cardinality/random identifiers supplied at request boundaries.
- Secret-like and malicious content entering error messages or tool summaries.

For each scenario verify:

- product behavior remains correct and safe;
- expected structured event is present;
- expected metric changes;
- correlation identifiers connect the relevant logs/traces;
- no prohibited content is emitted;
- configured alert can be evaluated/fired when its duration/threshold is met;
- runbook gives a safe diagnosis and recovery path.

Final acceptance:

- Backend and frontend regression pass.
- P37 base Compose smoke test still passes without observability services.
- Observability-profile Compose smoke test passes.
- Dashboard and alert configuration validation passes.
- Redaction and cardinality suites pass.
- Existing trace dashboard remains functional.
- `git diff --check` and artifact hygiene checks pass.
- README/deployment docs, `.env.example`, status, dashboards, alerts, and runbooks match verified behavior.

## Suggested File Layout

```text
observability/
  __init__.py
  context.py
  events.py
  logging.py
  metrics.py
  middleware.py
  redaction.py
  trace_sink.py
ops/
  prometheus/
    prometheus.yml
    alerts.yml
    recording_rules.yml
  grafana/
    provisioning/
    dashboards/
docs/
  operations/
    observability.md
    runbooks.md
```

Final names may follow repository conventions, but correlation, redaction, logging, metrics, trace sinks, dashboards, and runbooks should remain independently testable.

## Rollout Strategy

1. Land event contracts, context, and redaction with logging disabled or development-only where necessary.
2. Enable structured HTTP/workflow logs and compare against current behavior.
3. Move local trace persistence behind `TraceSink` while preserving the dashboard.
4. Add metrics incrementally at stable boundaries and run cardinality tests.
5. Add Prometheus/Grafana as an optional Compose profile.
6. Tune dashboards and alert thresholds using deterministic acceptance and real local workloads.
7. Make the documented observability profile part of release acceptance.

Every step must be reversible through configuration and must not make logging/metrics availability a prerequisite for answering a user request.

## Risks And Mitigations

### Sensitive Data Leakage

Risk: prompts, rows, SQL results, provider responses, or credentials appear in logs/traces.

Mitigation: allowlist fields, central redaction, adversarial fixtures, bounded summaries, and no raw exception/provider serialization.

### Metric Cardinality Explosion

Risk: per-request IDs, workspace IDs, raw routes, error strings, or business dimensions become labels.

Mitigation: controlled enums, route templates, explicit label review, randomized cardinality tests, and `unknown`/`other` buckets.

### Observability Breaking Product Traffic

Risk: logger, trace backend, or metrics failures cause analysis failures.

Mitigation: local non-blocking instrumentation, sink failure isolation, bounded work, and tests proving product output survives signal failures.

### Duplicate Or Misleading Signals

Risk: middleware, node wrappers, and existing trace calls double count one operation.

Mitigation: define ownership for every metric/event and add exact-count tests for representative workflows.

### Alert Fatigue

Risk: low-volume development traffic or transient provider errors trigger noisy alerts.

Mitigation: minimum traffic conditions, sustained durations, severity tiers, tunable thresholds, and runbook-backed alerts only.

### Unbounded Local Storage

Risk: trace, Prometheus, or Grafana data grows without limit.

Mitigation: explicit age/size retention, volume documentation, storage alerts, and safe cleanup tooling.

## Exit Criteria

P38 is complete when operators can correlate a user-visible failure from request to workflow/tool boundary; dashboards show system, agent, provider, SQL/evidence, and delivery health; tested alerts lead to actionable runbooks; existing business traces remain available; instrumentation failures do not break product traffic; label cardinality is bounded; and no prompts, raw rows, credentials, provider payloads, or internal paths leak through logs, metrics, traces, dashboards, alerts, or acceptance output.
