from pathlib import Path
import re
import shutil
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
SMOKE = (ROOT / "scripts" / "docker_smoke_test.sh").read_text(encoding="utf-8")
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def _target_body(name: str) -> str:
    match = re.search(rf"(?ms)^{re.escape(name)}:[^\n]*\n((?:\t.*\n|\n)*)", MAKEFILE)
    assert match, f"missing Makefile target: {name}"
    return match.group(1)


def test_makefile_default_is_help_and_required_targets_exist():
    assert re.search(r"(?m)^\.DEFAULT_GOAL\s*:?=\s*help\s*$", MAKEFILE)
    targets = {
        "help", "build", "up", "down", "restart", "ps", "logs",
        "compose-check", "test-backend", "test-frontend", "build-frontend",
        "test", "smoke",
    }
    for target in targets:
        assert re.search(rf"(?m)^{re.escape(target)}:", MAKEFILE)
    assert "clean:" not in MAKEFILE


def test_makefile_down_is_non_destructive_and_smoke_uses_canonical_script():
    down = _target_body("down")
    assert "docker compose down" in down
    assert not re.search(r"(?:^|\s)(?:-v|--volumes|prune)(?:\s|$)", down)
    assert "scripts/docker_smoke_test.sh" in _target_body("smoke")
    assert "--no-cache" not in MAKEFILE
    assert "--env-file /dev/null config -q" in _target_body("compose-check")


def test_smoke_has_strict_mode_unique_project_trap_and_cleanup_guard():
    assert "#!/usr/bin/env bash" in SMOKE
    assert "set -euo pipefail" in SMOKE
    assert "insightflow-smoke-" in SMOKE
    assert "$(date +%Y%m%d%H%M%S)-$$" in SMOKE
    assert re.search(r"trap\s+cleanup\s+EXIT", SMOKE)
    assert "trap 'handle_signal 130' INT" in SMOKE
    assert "trap 'handle_signal 143' TERM" in SMOKE
    assert "require_safe_project_name" in SMOKE
    assert '"${PROJECT_NAME}"_*' in SMOKE
    assert "down -v --remove-orphans" in SMOKE
    assert "--no-cache" not in SMOKE
    assert "eval " not in SMOKE


def test_smoke_never_reads_real_env_or_runs_global_prune():
    assert "mktemp" in SMOKE and "empty.env" in SMOKE
    assert '--env-file "${EMPTY_ENV_FILE}"' in SMOKE
    assert not re.search(r"(?:source|\.)\s+[^\n]*\.env", SMOKE)
    assert "docker volume prune" not in SMOKE
    assert "docker system prune" not in SMOKE
    assert "docker image prune" not in SMOKE


def test_smoke_health_api_product_persistence_and_restart_contracts():
    assert "HEALTH_TIMEOUT_SECONDS" in SMOKE
    assert "deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))" in SMOKE
    assert "wait_for_health backend" in SMOKE
    assert "wait_for_health frontend" in SMOKE
    assert "/health/live" in SMOKE and "/health/ready" in SMOKE
    assert "/api/workspaces" in SMOKE
    assert "/sources/upload" in SMOKE and "/profile" in SMOKE and "/semantic-layer/draft" in SMOKE
    assert "/runs" in SMOKE and "RUN_ID" in SMOKE
    assert "/reports" in SMOKE and "REPORT_ID" in SMOKE
    assert "/download" in SMOKE and "/export" in SMOKE and "WORD_URL" in SMOKE
    assert "CHART_CONTRACT" in SMOKE
    assert "workspace-data" in SMOKE and "report-data" in SMOKE and "trace-data" in SMOKE
    assert re.search(r"compose down\n.*assert_project_volumes.*compose up -d", SMOKE, re.S)
    assert "compose restart backend" in SMOKE
    assert "Application shutdown complete" in SMOKE
    assert "Application startup complete" in SMOKE


def test_smoke_checks_non_root_ports_mounts_and_no_key_runtime():
    assert SMOKE.count('== "10001"') >= 2
    assert 'HostIp"] == "127.0.0.1"' in SMOKE
    assert "/var/run/docker.sock" in SMOKE
    assert 'test -z "${DEEPSEEK_API_KEY:-}"' in SMOKE
    assert 'test -z "${OPENAI_API_KEY:-}"' in SMOKE
    assert "command -v lark-cli" in SMOKE


def test_ci_is_secretless_and_calls_the_same_smoke_script():
    workflow = yaml.safe_load(CI)
    job = workflow["jobs"]["verify"]
    assert job["timeout-minutes"] > 0
    assert job["runs-on"] == "ubuntu-latest"
    assert "python-version: \"3.12\"" in CI
    assert "node-version: \"22\"" in CI
    assert "python -m pip install -r requirements-dev.txt" in CI
    assert "python -m pytest" in CI
    assert "npm ci" in CI and "npm test" in CI and "npm run build" in CI
    assert "docker compose --env-file /dev/null config -q" in CI
    assert "bash -n scripts/docker_smoke_test.sh" in CI
    assert "scripts/docker_smoke_test.sh" in CI
    forbidden = ("DEEPSEEK_API_KEY", "LARK_CLI", "docker push", "deploy", "prometheus", "grafana")
    assert not any(value.lower() in CI.lower() for value in forbidden)


def _link_command(fake_bin: Path, name: str) -> None:
    source = shutil.which(name)
    assert source, f"required test command is unavailable: {name}"
    (fake_bin / name).symlink_to(source)


def _preflight_environment(tmp_path: Path) -> tuple[dict[str, str], Path, Path]:
    isolated_tmp = tmp_path / "tmp"
    fake_bin = tmp_path / "bin"
    isolated_tmp.mkdir()
    fake_bin.mkdir()
    for command in ("date", "dirname", "mktemp", "rm"):
        _link_command(fake_bin, command)
    environment = {
        "PATH": str(fake_bin),
        "TMPDIR": str(isolated_tmp),
        "HOME": str(tmp_path / "unused-home"),
    }
    return environment, fake_bin, isolated_tmp


def test_missing_docker_preflight_is_nonzero_and_leaves_no_temp_directory(tmp_path):
    environment, _fake_bin, isolated_tmp = _preflight_environment(tmp_path)

    result = subprocess.run(
        ["/bin/bash", str(ROOT / "scripts" / "docker_smoke_test.sh")],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 127
    assert "required command is missing: docker" in result.stderr
    assert list(isolated_tmp.glob("insightflow-smoke.*")) == []


def test_engine_preflight_preserves_failure_and_never_touches_resources(tmp_path):
    environment, fake_bin, isolated_tmp = _preflight_environment(tmp_path)
    docker_calls = tmp_path / "docker-calls"
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" >> \"$FAKE_DOCKER_CALLS\"\n"
        "if [ \"$1 $2\" = \"compose version\" ]; then exit 0; fi\n"
        "if [ \"$1\" = \"info\" ]; then exit 42; fi\n"
        "exit 99\n",
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)
    for command in ("curl", "python3"):
        fake = fake_bin / command
        fake.write_text("#!/bin/sh\nexit 98\n", encoding="utf-8")
        fake.chmod(0o755)
    environment["FAKE_DOCKER_CALLS"] = str(docker_calls)

    result = subprocess.run(
        ["/bin/bash", str(ROOT / "scripts" / "docker_smoke_test.sh")],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 42
    assert "Docker Engine is unavailable" in result.stderr
    assert list(isolated_tmp.glob("insightflow-smoke.*")) == []
    assert docker_calls.read_text(encoding="utf-8").splitlines() == [
        "compose version",
        "info",
    ]
