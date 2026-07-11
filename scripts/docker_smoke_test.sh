#!/usr/bin/env bash
set -euo pipefail

PROJECT_PREFIX="insightflow-smoke-"
PROJECT_NAME="${PROJECT_PREFIX}$(date +%Y%m%d%H%M%S)-$$"
BACKEND_PORT="${INSIGHTFLOW_SMOKE_BACKEND_PORT:-18000}"
FRONTEND_PORT="${INSIGHTFLOW_SMOKE_FRONTEND_PORT:-13000}"
HEALTH_TIMEOUT_SECONDS="${INSIGHTFLOW_SMOKE_HEALTH_TIMEOUT_SECONDS:-90}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_DIR=""
EMPTY_ENV_FILE=""
CSV_FILE=""
LOG_FILE=""
CLEANUP_STARTED=0
DOCKER_CLEANUP_REQUIRED=0

log() {
  printf '[insightflow-smoke] %s\n' "$*"
}

fail() {
  log "ERROR: $*" >&2
  exit 1
}

safe_project_name() {
  case "${PROJECT_NAME}" in
    insightflow-smoke-[a-zA-Z0-9-]*) ;;
    *) return 1 ;;
  esac
  [[ "${PROJECT_NAME}" =~ ^insightflow-smoke-[a-zA-Z0-9-]+$ ]]
}

require_safe_project_name() {
  safe_project_name || fail "Refusing operation for unsafe project name"
}

compose() {
  docker compose --project-name "${PROJECT_NAME}" --env-file "${EMPTY_ENV_FILE}" "$@"
}

project_resources() {
  case "$1" in
    container) docker container ls --all --filter "label=com.docker.compose.project=${PROJECT_NAME}" --format '{{.Names}}' ;;
    network) docker network ls --filter "label=com.docker.compose.project=${PROJECT_NAME}" --format '{{.Name}}' ;;
    volume) docker volume ls --filter "label=com.docker.compose.project=${PROJECT_NAME}" --format '{{.Name}}' ;;
    *) log "ERROR: unsupported project resource type" >&2; return 2 ;;
  esac
}

cleanup() {
  local exit_code=$?
  local cleanup_failed=0
  local volume_name=""
  local volumes=""
  local leftovers=""
  if [[ "${CLEANUP_STARTED}" -eq 1 ]]; then
    return
  fi
  CLEANUP_STARTED=1
  trap - EXIT INT TERM
  set +e

  if [[ "${DOCKER_CLEANUP_REQUIRED}" -eq 1 ]]; then
    if ! safe_project_name; then
      log "ERROR: refusing Docker cleanup for unsafe project name" >&2
      cleanup_failed=1
    elif ! docker info >/dev/null 2>&1; then
      log "ERROR: Docker Engine is unavailable; skipping Docker resource cleanup" >&2
      cleanup_failed=1
    else
      volumes="$(project_resources volume)"
      if [[ "$?" -ne 0 ]]; then
        log "ERROR: could not inspect isolated Volumes; refusing Docker cleanup" >&2
        cleanup_failed=1
      else
        while IFS= read -r volume_name; do
          [[ -z "${volume_name}" ]] && continue
          case "${volume_name}" in
            "${PROJECT_NAME}"_*) ;;
            *)
              log "ERROR: refusing cleanup because a project Volume has an unexpected name" >&2
              cleanup_failed=1
              ;;
          esac
        done <<< "${volumes}"
      fi

      if [[ "${cleanup_failed}" -eq 0 ]]; then
        log "Cleaning only isolated project ${PROJECT_NAME}"
        compose down -v --remove-orphans >/dev/null 2>&1
        if [[ "$?" -ne 0 ]]; then
          log "ERROR: isolated Compose cleanup failed" >&2
          cleanup_failed=1
        fi
        leftovers="$(project_resources container)$(project_resources network)$(project_resources volume)"
        if [[ "$?" -ne 0 || -n "${leftovers}" ]]; then
          log "ERROR: isolated Smoke resources remain after cleanup" >&2
          cleanup_failed=1
        else
          log "Cleanup confirmed: no Smoke containers, networks, or Volumes remain"
        fi
      fi
    fi
  fi

  if [[ -n "${TEMP_DIR}" && -d "${TEMP_DIR}" ]]; then
    rm -rf "${TEMP_DIR}"
    if [[ -d "${TEMP_DIR}" ]]; then
      log "ERROR: temporary Smoke directory could not be removed" >&2
      cleanup_failed=1
    fi
  fi
  if [[ "${cleanup_failed}" -ne 0 && "${exit_code}" -eq 0 ]]; then
    exit_code=1
  fi
  exit "${exit_code}"
}

handle_signal() {
  local signal_exit_code="$1"
  trap - INT TERM
  exit "${signal_exit_code}"
}

preflight() {
  local command=""
  local status=0
  for command in docker curl python3 mktemp; do
    if ! command -v "${command}" >/dev/null 2>&1; then
      log "ERROR: required command is missing: ${command}" >&2
      return 127
    fi
  done
  docker compose version >/dev/null 2>&1 || {
    status=$?
    log "ERROR: docker compose is unavailable" >&2
    return "${status}"
  }
  docker info >/dev/null 2>&1 || {
    status=$?
    log "ERROR: Docker Engine is unavailable" >&2
    return "${status}"
  }
}

create_temp_dir() {
  TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/insightflow-smoke.XXXXXX")"
  EMPTY_ENV_FILE="${TEMP_DIR}/empty.env"
  CSV_FILE="${TEMP_DIR}/smoke.csv"
  LOG_FILE="${TEMP_DIR}/backend.log"
}

wait_for_health() {
  local service="$1"
  local deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
  local container_id=""
  local status=""
  while (( SECONDS < deadline )); do
    container_id="$(compose ps -q "${service}")"
    if [[ -n "${container_id}" ]]; then
      status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "${container_id}" 2>/dev/null || true)"
      if [[ "${status}" == "healthy" ]]; then
        log "${service} is healthy"
        return 0
      fi
      if [[ "${status}" == "unhealthy" ]]; then
        compose logs --tail 40 "${service}" >&2 || true
        fail "${service} became unhealthy"
      fi
    fi
    sleep 2
  done
  compose logs --tail 40 "${service}" >&2 || true
  fail "Timed out after ${HEALTH_TIMEOUT_SECONDS}s waiting for ${service} health"
}

curl_to_file() {
  local output="$1"
  local status=""
  shift
  status="$(curl --silent --show-error --fail --location --connect-timeout 3 --max-time 15 --output "${output}" --write-out '%{http_code}' "$@")"
  [[ "${status}" == "200" ]] || fail "HTTP request did not return 200"
}

assert_health_json() {
  local path="$1"
  local expected_status="$2"
  local output="${TEMP_DIR}/health-${expected_status}.json"
  curl_to_file "${output}" "http://127.0.0.1:${BACKEND_PORT}${path}"
  python3 - "${output}" "${expected_status}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
assert payload.get("status") == sys.argv[2]
if sys.argv[2] == "ready":
    checks = payload.get("checks", {})
    assert set(checks) == {"workspace_storage", "report_storage", "trace_storage", "configuration"}
    assert all(value == "ok" for value in checks.values())
PY
}

assert_runtime_contract() {
  local backend_id frontend_id
  backend_id="$(compose ps -q backend)"
  frontend_id="$(compose ps -q frontend)"
  [[ "$(docker inspect --format '{{.Config.User}}' "${backend_id}")" == "insightflow:insightflow" ]] || fail "backend image user is unexpected"
  [[ "$(docker inspect --format '{{.Config.User}}' "${frontend_id}")" == "nextjs:nodejs" ]] || fail "frontend image user is unexpected"
  [[ "$(compose exec -T backend id -u)" == "10001" ]] || fail "backend is not UID 10001"
  [[ "$(compose exec -T frontend id -u)" == "10001" ]] || fail "frontend is not UID 10001"
  compose exec -T backend sh -c 'test -z "${DEEPSEEK_API_KEY:-}" && test -z "${OPENAI_API_KEY:-}" && ! command -v lark-cli >/dev/null 2>&1'

  python3 - "${backend_id}" "${frontend_id}" "${BACKEND_PORT}" "${FRONTEND_PORT}" <<'PY'
import json
import subprocess
import sys

backend_id, frontend_id, backend_port, frontend_port = sys.argv[1:]
containers = [json.loads(subprocess.check_output(["docker", "inspect", item], text=True))[0] for item in (backend_id, frontend_id)]
expected_ports = ((containers[0], f"{backend_port}/tcp", "8000/tcp"), (containers[1], f"{frontend_port}/tcp", "3000/tcp"))
for container, _host_label, container_port in expected_ports:
    bindings = container["NetworkSettings"]["Ports"][container_port]
    assert bindings and all(binding["HostIp"] == "127.0.0.1" for binding in bindings)
    for mount in container.get("Mounts", []):
        joined = f'{mount.get("Source", "")} {mount.get("Destination", "")}'
        assert "/var/run/docker.sock" not in joined
        assert not joined.endswith("/.env") and " /.env" not in joined
        assert not any(part in joined for part in ("/Users/", "/home/"))

backend_mounts = {mount["Name"]: mount["Destination"] for mount in containers[0].get("Mounts", []) if mount.get("Type") == "volume"}
expected_targets = {"workspace-data": "/app/workspaces", "report-data": "/app/reports", "trace-data": "/app/logs/traces"}
for logical_name, target in expected_targets.items():
    matches = [name for name, destination in backend_mounts.items() if name.endswith("_" + logical_name) and destination == target]
    assert len(matches) == 1
assert not containers[1].get("Mounts")
PY
}

assert_project_volumes() {
  local require_writable="${1:-false}"
  local count=0
  local volume_name=""
  local mountpoint=""
  while IFS= read -r volume_name; do
    [[ -z "${volume_name}" ]] && continue
    case "${volume_name}" in
      "${PROJECT_NAME}"_workspace-data|"${PROJECT_NAME}"_report-data|"${PROJECT_NAME}"_trace-data) ;;
      *) fail "Unexpected isolated Volume name" ;;
    esac
    mountpoint="$(docker volume inspect --format '{{.Mountpoint}}' "${volume_name}")"
    [[ -n "${mountpoint}" ]] || fail "Volume mountpoint is missing"
    count=$((count + 1))
  done < <(project_resources volume)
  [[ "${count}" -eq 3 ]] || fail "Expected exactly three isolated Volumes"
  if [[ "${require_writable}" == "true" ]]; then
    compose exec -T backend sh -c 'for path in /app/workspaces /app/reports /app/logs/traces; do test "$(id -u)" = 10001 && test -w "$path"; done'
  fi
}

create_workspace_and_profile() {
  local create_json="${TEMP_DIR}/workspace-create.json"
  local get_json="${TEMP_DIR}/workspace-get.json"
  local list_json="${TEMP_DIR}/workspace-list.json"
  local upload_json="${TEMP_DIR}/workspace-upload.json"
  local profile_json="${TEMP_DIR}/workspace-profile.json"
  local semantic_json="${TEMP_DIR}/workspace-semantic.json"
  local workspace_name="smoke-${PROJECT_NAME}"

  curl_to_file "${create_json}" -H 'Content-Type: application/json' -d "{\"name\":\"${workspace_name}\"}" "http://127.0.0.1:${BACKEND_PORT}/api/workspaces"
  WORKSPACE_ID="$(python3 - "${create_json}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    value = json.load(handle).get("workspace_id", "")
assert value
print(value)
PY
)"
  export WORKSPACE_ID

  curl_to_file "${get_json}" "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}"
  curl_to_file "${list_json}" "http://127.0.0.1:${BACKEND_PORT}/api/workspaces"
  python3 - "${get_json}" "${list_json}" "${WORKSPACE_ID}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    detail = json.load(handle)
with open(sys.argv[2], encoding="utf-8") as handle:
    listing = json.load(handle)
assert detail.get("workspace_id") == sys.argv[3]
assert any(item.get("workspace_id") == sys.argv[3] for item in listing.get("workspaces", []))
PY

  printf 'order_id,channel,revenue\n1,web,120.5\n2,store,98.0\n' > "${CSV_FILE}"
  curl_to_file "${upload_json}" -F "file=@${CSV_FILE};type=text/csv;filename=smoke.csv" "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/sources/upload"
  curl_to_file "${profile_json}" -X POST "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/profile"
  curl_to_file "${semantic_json}" -X POST "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/semantic-layer/draft"
  python3 - "${upload_json}" "${profile_json}" "${semantic_json}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    upload = json.load(handle)
with open(sys.argv[2], encoding="utf-8") as handle:
    profile = json.load(handle)
with open(sys.argv[3], encoding="utf-8") as handle:
    semantic = json.load(handle)
assert upload.get("success") is True and upload.get("imported_tables") == ["smoke"]
assert profile.get("success") is True
assert any(table.get("table_name") == "smoke" for table in profile.get("profile", {}).get("tables", []))
assert semantic.get("success") is True
assert semantic.get("semantic_layer")
PY
  log "Unique Workspace, synthetic CSV profile, and semantic draft passed"
}

create_run_and_assert_history() {
  local create_json="${TEMP_DIR}/run-create.json"
  local detail_json="${TEMP_DIR}/run-detail.json"
  local history_json="${TEMP_DIR}/run-history.json"
  local deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
  curl_to_file "${create_json}" -H 'Content-Type: application/json' \
    -d '{"user_question":"按渠道汇总收入并说明当前可安全生成的结论。","initial_sql":"SELECT channel, SUM(revenue) AS total_revenue FROM smoke GROUP BY channel ORDER BY total_revenue DESC"}' \
    "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/runs"
  RUN_ID="$(python3 - "${create_json}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    value = json.load(handle).get("run_id", "")
assert value
print(value)
PY
)"
  export RUN_ID

  while (( SECONDS < deadline )); do
    status="$(curl --silent --show-error --location --connect-timeout 3 --max-time 15 --output "${detail_json}" --write-out '%{http_code}' "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/runs/${RUN_ID}")"
    if [[ "${status}" == "404" ]]; then
      sleep 1
      continue
    fi
    [[ "${status}" == "200" ]] || fail "Run detail request did not return 200"
    if python3 - "${detail_json}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
status = payload.get("status") or (payload.get("result") or {}).get("status") or (payload.get("product_result") or {}).get("status")
raise SystemExit(0 if status and status != "running" else 1)
PY
    then
      break
    fi
    sleep 2
  done
  curl_to_file "${history_json}" "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/runs"
  python3 - "${detail_json}" "${history_json}" "${RUN_ID}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    detail = json.load(handle)
with open(sys.argv[2], encoding="utf-8") as handle:
    history = json.load(handle)
run_id = sys.argv[3]
assert detail.get("run_id") == run_id
result = detail.get("result") or {}
product = detail.get("product_result") or result.get("product_result") or {}
status = detail.get("status") or result.get("status") or product.get("status")
assert status in {"completed", "failed", "waiting_clarification", "waiting_for_clarification"}, status
assert any(item.get("run_id") == run_id for item in history.get("runs", []))
if status == "failed":
    assert result.get("error_message") or product.get("failure_reason")
elif status in {"waiting_clarification", "waiting_for_clarification"}:
    assert product.get("clarification") or result.get("clarification_question")
else:
    answer = product.get("business_answer") or result.get("business_answer") or {}
    assert answer.get("headline") and answer.get("direct_answer")
    if answer.get("headline") == "业务回答生成失败":
        assert "不会" in answer.get("direct_answer", "") or "失败" in answer.get("direct_answer", "")
print(status)
PY
  log "Analysis Run persisted with an explicit no-provider success/degradation/failure contract"
}

create_report_and_exports() {
  local create_json="${TEMP_DIR}/report-create.json"
  local detail_json="${TEMP_DIR}/report-detail.json"
  local list_json="${TEMP_DIR}/report-list.json"
  local export_json="${TEMP_DIR}/report-export.json"
  curl_to_file "${create_json}" -H 'Content-Type: application/json' \
    -d '{"report_type":"channel_performance","report_goal":"基于全部合成数据生成渠道收入经营复盘，明确数据边界。"}' \
    "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/reports"
  REPORT_ID="$(python3 - "${create_json}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
assert payload.get("report_id")
print(payload["report_id"])
PY
)"
  export REPORT_ID
  curl_to_file "${detail_json}" "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/reports/${REPORT_ID}"
  curl_to_file "${list_json}" "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/reports"
  curl_to_file "${TEMP_DIR}/report.md" "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/reports/${REPORT_ID}/download"
  curl_to_file "${export_json}" -X POST "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/reports/${REPORT_ID}/export"
  WORD_URL="$(python3 - "${detail_json}" "${list_json}" "${export_json}" "${REPORT_ID}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    detail = json.load(handle).get("report") or {}
with open(sys.argv[2], encoding="utf-8") as handle:
    listing = json.load(handle)
with open(sys.argv[3], encoding="utf-8") as handle:
    exported = json.load(handle)
report_id = sys.argv[4]
assert detail.get("report_id") == report_id
assert detail.get("status") in {"completed", "partial"}
assert detail.get("plan") and detail.get("evidence_pack") and detail.get("document")
appendix = (detail.get("document") or {}).get("technical_appendix") or {}
assert appendix.get("evidence_ledger")
assert any(item.get("report_id") == report_id for item in listing.get("reports", []))
assert exported.get("success") is True
assert exported.get("download_name", "").endswith(".docx")
assert exported.get("download_url")
print(exported["download_url"])
PY
)"
  export WORD_URL
  curl_to_file "${TEMP_DIR}/report.docx" "http://127.0.0.1:${BACKEND_PORT}${WORD_URL}"
  python3 - "${TEMP_DIR}/report.md" "${TEMP_DIR}/report.docx" <<'PY'
import sys
from pathlib import Path
markdown = Path(sys.argv[1]).read_text(encoding="utf-8")
docx = Path(sys.argv[2]).read_bytes()
assert markdown.strip() and "#" in markdown
assert docx.startswith(b"PK") and len(docx) > 1000
PY

  if compose exec -T backend sh -c 'find "/app/workspaces/$1/reports/$2/artifacts" -type f \( -name "*.svg" -o -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.gif" \) -print -quit | grep -q .' sh "${WORKSPACE_ID}" "${REPORT_ID}"; then
    CHART_CONTRACT="static_asset"
  else
    CHART_CONTRACT="$(python3 - "${detail_json}" "${export_json}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle).get("report") or {}
with open(sys.argv[2], encoding="utf-8") as handle:
    exported = json.load(handle)
warnings = [str(item) for item in exported.get("warnings", [])]
warnings += [str(item) for item in (report.get("evidence_pack") or {}).get("warnings", [])]
warnings += [str(item) for item in (report.get("plan") or {}).get("data_limits", [])]
assert warnings, "report has neither a static chart asset nor an explicit safe warning"
print("explicit_warning")
PY
)"
  fi
  export CHART_CONTRACT
  log "ReportRecord, ReportDocument, Markdown, Word, and chart/static warning contract passed"
}

write_volume_markers() {
  REPORT_MARKER="report-${PROJECT_NAME}"
  TRACE_MARKER="trace-${PROJECT_NAME}"
  export REPORT_MARKER TRACE_MARKER
  compose exec -T backend sh -c 'printf "%s" "$1" > /app/reports/smoke-marker && printf "%s" "$2" > /app/logs/traces/smoke-marker' sh "${REPORT_MARKER}" "${TRACE_MARKER}"
}

assert_persistence() {
  local workspace_json="${TEMP_DIR}/workspace-after-recreate.json"
  local run_json="${TEMP_DIR}/run-after-recreate.json"
  local report_json="${TEMP_DIR}/report-after-recreate.json"
  curl_to_file "${workspace_json}" "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}"
  python3 - "${workspace_json}" "${WORKSPACE_ID}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
assert payload.get("workspace_id") == sys.argv[2]
PY
  curl_to_file "${run_json}" "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/runs/${RUN_ID}"
  curl_to_file "${report_json}" "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/reports/${REPORT_ID}"
  curl_to_file "${TEMP_DIR}/report-after-recreate.md" "http://127.0.0.1:${BACKEND_PORT}/api/workspaces/${WORKSPACE_ID}/reports/${REPORT_ID}/download"
  curl_to_file "${TEMP_DIR}/report-after-recreate.docx" "http://127.0.0.1:${BACKEND_PORT}${WORD_URL}"
  python3 - "${run_json}" "${report_json}" "${RUN_ID}" "${REPORT_ID}" "${TEMP_DIR}/report-after-recreate.md" "${TEMP_DIR}/report-after-recreate.docx" <<'PY'
import json
import sys
from pathlib import Path
with open(sys.argv[1], encoding="utf-8") as handle:
    run = json.load(handle)
with open(sys.argv[2], encoding="utf-8") as handle:
    report = json.load(handle).get("report") or {}
assert run.get("run_id") == sys.argv[3]
assert report.get("report_id") == sys.argv[4]
assert report.get("document") and report.get("evidence_pack")
assert Path(sys.argv[5]).read_text(encoding="utf-8").strip()
assert Path(sys.argv[6]).read_bytes().startswith(b"PK")
PY
  if [[ "${CHART_CONTRACT}" == "static_asset" ]]; then
    compose exec -T backend sh -c 'find "/app/workspaces/$1/reports/$2/artifacts" -type f \( -name "*.svg" -o -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.gif" \) -print -quit | grep -q .' sh "${WORKSPACE_ID}" "${REPORT_ID}"
  fi
  compose exec -T backend sh -c 'test "$(cat /app/reports/smoke-marker)" = "$1" && test "$(cat /app/logs/traces/smoke-marker)" = "$2"' sh "${REPORT_MARKER}" "${TRACE_MARKER}"
  assert_health_json "/health/ready" "ready"
}

assert_graceful_restart() {
  local started_at=$SECONDS
  compose restart backend
  if (( SECONDS - started_at > 45 )); then
    fail "backend restart exceeded the bounded lifecycle window"
  fi
  wait_for_health backend
  compose logs --no-color backend > "${LOG_FILE}"
  grep -q 'Shutting down' "${LOG_FILE}" || fail "backend logs do not show graceful shutdown"
  grep -q 'Application shutdown complete' "${LOG_FILE}" || fail "backend logs do not show completed application shutdown"
  grep -q 'Application startup complete' "${LOG_FILE}" || fail "backend logs do not show completed application startup"
  assert_health_json "/health/ready" "ready"
  log "Graceful backend restart and Executor shutdown/startup lifecycle passed"
}

main() {
  require_safe_project_name
  : > "${EMPTY_ENV_FILE}"
  unset DEEPSEEK_API_KEY OPENAI_API_KEY LARK_CLI_BIN || true
  export DEEPSEEK_API_KEY="" OPENAI_API_KEY="" INSIGHTFLOW_PRODUCT_LIVE_MODE="0"
  export BACKEND_HOST_PORT="${BACKEND_PORT}" FRONTEND_HOST_PORT="${FRONTEND_PORT}"
  export NEXT_PUBLIC_API_BASE="http://127.0.0.1:${BACKEND_PORT}"
  export INSIGHTFLOW_CORS_ORIGINS="http://127.0.0.1:${FRONTEND_PORT},http://localhost:${FRONTEND_PORT}"
  log "Starting isolated project ${PROJECT_NAME} on backend ${BACKEND_PORT} and frontend ${FRONTEND_PORT}"
  compose config -q
  log "Compose configuration passed"
  compose build backend frontend
  DOCKER_CLEANUP_REQUIRED=1
  compose up -d
  wait_for_health backend
  wait_for_health frontend

  assert_health_json "/health/live" "ok"
  assert_health_json "/health/ready" "ready"
  curl_to_file "${TEMP_DIR}/frontend.html" "http://127.0.0.1:${FRONTEND_PORT}/"
  assert_runtime_contract
  assert_project_volumes true
  create_workspace_and_profile
  create_run_and_assert_history
  create_report_and_exports
  write_volume_markers

  compose down
  assert_project_volumes false
  compose up -d
  wait_for_health backend
  wait_for_health frontend
  assert_persistence
  log "Workspace, Run, Report, Markdown, Word, chart contract, and all three Volumes persisted across down/up"

  assert_graceful_restart
  log "Docker Smoke acceptance passed"
}

cd "${ROOT_DIR}"
preflight
trap cleanup EXIT
trap 'handle_signal 130' INT
trap 'handle_signal 143' TERM
create_temp_dir
main "$@"
