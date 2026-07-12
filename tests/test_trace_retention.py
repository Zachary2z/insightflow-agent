from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


NOW = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)


def _trace(path: Path, size: int, *, age_days: int) -> Path:
    run_id = path.stem
    payload = {
        "run_id": run_id,
        "session_id": None,
        "user_question": None,
        "status": "completed",
        "question_thread": {},
        "event_count": 0,
        "trace": [],
        "saved_at": "2026-07-01T00:00:00Z",
    }
    path.write_text(json.dumps(payload) + (" " * size), encoding="utf-8")
    timestamp = (NOW - timedelta(days=age_days)).timestamp()
    os.utime(path, (timestamp, timestamp))
    return path


def _apply_trace_retention(trace_root: Path, **kwargs):
    from observability.trace_retention import apply_trace_retention

    kwargs.setdefault("allowed_trace_root", trace_root)
    return apply_trace_retention(trace_root, **kwargs)


def test_retention_defaults_to_dry_run_and_reports_age_candidates(tmp_path):
    from observability.trace_retention import apply_trace_retention

    old = _trace(tmp_path / "old.json", 10, age_days=31)
    _trace(tmp_path / "recent.json", 20, age_days=1)

    result = _apply_trace_retention(tmp_path, max_age_days=30, now=NOW)

    assert result.dry_run is True
    assert result.scanned_count == 2
    assert result.candidate_count == 1
    assert result.candidate_bytes == old.stat().st_size
    assert result.deleted_count == 0
    assert old.exists()


def test_retention_explicit_delete_removes_only_old_trace(tmp_path):
    from observability.trace_retention import apply_trace_retention

    old = _trace(tmp_path / "old.json", 10, age_days=31)
    recent = _trace(tmp_path / "recent.json", 20, age_days=1)

    old_size = old.stat().st_size
    result = _apply_trace_retention(tmp_path, max_age_days=30, delete=True, now=NOW)

    assert result.deleted_count == 1
    assert result.deleted_bytes == old_size
    assert not old.exists()
    assert recent.exists()


def test_retention_capacity_deletes_oldest_until_under_limit(tmp_path):
    from observability.trace_retention import apply_trace_retention

    oldest = _trace(tmp_path / "oldest.json", 30, age_days=3)
    middle = _trace(tmp_path / "middle.json", 30, age_days=2)
    newest = _trace(tmp_path / "newest.json", 30, age_days=1)

    expected_deleted_bytes = oldest.stat().st_size + middle.stat().st_size
    result = _apply_trace_retention(
        tmp_path, max_total_bytes=newest.stat().st_size, delete=True, now=NOW
    )

    assert result.candidate_count == 2
    assert result.deleted_bytes == expected_deleted_bytes
    assert not oldest.exists()
    assert not middle.exists()
    assert newest.exists()


def test_retention_protects_active_runs_and_reports_capacity_unmet(tmp_path):
    from observability.trace_retention import apply_trace_retention

    active = _trace(tmp_path / "run_active.json", 80, age_days=10)
    removable = _trace(tmp_path / "run_other.json", 20, age_days=5)

    result = _apply_trace_retention(
        tmp_path,
        max_age_days=1,
        max_total_bytes=10,
        active_run_ids={"run_active"},
        delete=True,
        now=NOW,
    )

    assert active.exists()
    assert not removable.exists()
    assert result.skipped_reasons["active_run"] == 1
    assert result.skipped_reasons["capacity_unmet_protected"] == 1


def test_retention_normalizes_active_run_ids_like_local_persistence(tmp_path):
    from observability.trace_retention import apply_trace_retention
    from tools.trace_logger import save_trace

    saved = save_trace("../active/run", [], trace_dir=tmp_path)
    path = Path(saved["trace_path"])
    timestamp = (NOW - timedelta(days=10)).timestamp()
    os.utime(path, (timestamp, timestamp))

    result = _apply_trace_retention(
        tmp_path,
        max_age_days=1,
        active_run_ids={"../active/run"},
        delete=True,
        now=NOW,
    )

    assert path.exists()
    assert result.skipped_reasons["active_run"] == 1


def test_retention_skips_symlinks_directories_temp_and_non_json_files(tmp_path):
    from observability.trace_retention import apply_trace_retention

    outside = _trace(tmp_path.parent / "outside.json", 15, age_days=50)
    (tmp_path / "linked.json").symlink_to(outside)
    (tmp_path / "directory.json").mkdir()
    (tmp_path / ".write.tmp").write_text("temporary", encoding="utf-8")
    (tmp_path / "report.md").write_text("report", encoding="utf-8")

    result = _apply_trace_retention(tmp_path, max_age_days=1, delete=True, now=NOW)

    assert outside.exists()
    assert (tmp_path / "linked.json").is_symlink()
    assert (tmp_path / "directory.json").is_dir()
    assert (tmp_path / ".write.tmp").exists()
    assert (tmp_path / "report.md").exists()
    assert result.deleted_count == 0
    assert result.skipped_reasons["symlink"] == 1


def test_retention_missing_root_returns_empty_result(tmp_path):
    from observability.trace_retention import apply_trace_retention

    result = _apply_trace_retention(tmp_path / "missing", max_age_days=30)

    assert result.scanned_count == 0
    assert result.candidate_count == 0
    assert result.deleted_count == 0


def test_retention_rejects_root_below_symlink_parent(tmp_path):
    from observability.trace_retention import apply_trace_retention

    outside = tmp_path / "outside"
    outside.mkdir()
    trace_root = outside / "traces"
    trace_root.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="real directory"):
        _apply_trace_retention(linked_parent / "traces", max_age_days=30)


def test_retention_never_touches_workspace_report_or_source_artifacts(tmp_path):
    from observability.trace_retention import apply_trace_retention

    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    workspace = tmp_path / "workspaces" / "workspace.json"
    report = tmp_path / "reports" / "report.docx"
    source = tmp_path / ".env"
    for path in (workspace, report, source):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("must survive", encoding="utf-8")
    _trace(trace_root / "old.json", 10, age_days=31)

    _apply_trace_retention(trace_root, max_age_days=30, delete=True, now=NOW)

    assert workspace.read_text(encoding="utf-8") == "must survive"
    assert report.read_text(encoding="utf-8") == "must survive"
    assert source.read_text(encoding="utf-8") == "must survive"


def test_retention_skips_candidate_replaced_after_scan(tmp_path, monkeypatch):
    import observability.trace_retention as retention

    candidate = _trace(tmp_path / "run_race.json", 10, age_days=31)
    original_stat = retention._file_stat
    calls = 0

    def replacing_stat(path):
        nonlocal calls
        if Path(path) == candidate:
            calls += 1
            if calls == 2:
                candidate.unlink()
                candidate.write_bytes(b"new trace must survive")
        return original_stat(path)

    monkeypatch.setattr(retention, "_file_stat", replacing_stat)
    result = retention.apply_trace_retention(
        tmp_path, allowed_trace_root=tmp_path, max_age_days=30, delete=True, now=NOW
    )

    assert candidate.read_bytes() == b"new trace must survive"
    assert result.deleted_count == 0
    assert result.skipped_reasons["changed_during_scan"] == 1


def test_retention_cli_failure_does_not_emit_exception_or_path(tmp_path, capsys):
    from observability.trace_retention import main

    secret_path = tmp_path / "SELECT-secret-token-do-not-leak"
    secret_path.write_text("not a directory", encoding="utf-8")

    exit_code = main(["--trace-dir", str(secret_path), "--max-age-days", "30"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "validation_error" in captured.out
    assert captured.err == ""
    for forbidden in (str(secret_path), "SELECT-secret", "token-do-not-leak", "Traceback"):
        assert forbidden not in captured.out + captured.err


def test_retention_rejects_workspace_root_outside_allowed_trace_root(tmp_path):
    from observability.trace_retention import apply_trace_retention

    allowed = tmp_path / "logs" / "traces"
    workspace_root = tmp_path / "workspaces"
    allowed.mkdir(parents=True)
    workspace_root.mkdir()
    workspace = workspace_root / "workspace.json"
    workspace.write_text('{"workspace_id":"workspace-secret"}', encoding="utf-8")

    with pytest.raises(ValueError, match="outside allowed trace root"):
        apply_trace_retention(
            workspace_root,
            allowed_trace_root=allowed,
            max_age_days=1,
            delete=True,
            now=NOW,
        )

    assert workspace.exists()


def test_retention_rejects_workspace_run_directory_even_when_json_contains_trace(tmp_path):
    from observability.trace_retention import apply_trace_retention

    allowed = tmp_path / "authorized-traces"
    run_root = tmp_path / "workspaces" / "ws_1" / "runs" / "run_1"
    allowed.mkdir()
    run_root.mkdir(parents=True)
    business_run = run_root / "run.json"
    business_run.write_text(
        json.dumps({"run_id": "run", "trace": [], "status": "completed", "product_result": {}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="outside allowed trace root"):
        apply_trace_retention(
            run_root,
            allowed_trace_root=allowed,
            max_age_days=1,
            delete=True,
            now=NOW,
        )

    assert business_run.exists()


@pytest.mark.parametrize("relative_target", ["workspaces", "workspaces/ws_1/runs/run_1", "reports", "reports/r_1"])
def test_retention_rejects_configured_protected_business_root(
    tmp_path, monkeypatch, relative_target
):
    import observability.trace_retention as retention

    protected_root = tmp_path / relative_target.split("/")[0]
    target = tmp_path / relative_target
    target.mkdir(parents=True)
    business_json = target / "business.json"
    business_json.write_text('{"run_id":"business","trace":[]}', encoding="utf-8")
    monkeypatch.setattr(retention, "PROTECTED_BUSINESS_ROOTS", (protected_root,))

    with pytest.raises(ValueError, match="protected root"):
        retention.apply_trace_retention(
            target,
            allowed_trace_root=target,
            max_age_days=1,
            delete=True,
            now=NOW,
        )

    assert business_json.exists()


@pytest.mark.parametrize("target_name", ["reports", "reports/report_1"])
def test_retention_rejects_report_roots_and_preserves_all_artifacts(tmp_path, target_name):
    from observability.trace_retention import apply_trace_retention

    allowed = tmp_path / "logs" / "traces"
    report_root = tmp_path / target_name
    allowed.mkdir(parents=True)
    report_root.mkdir(parents=True)
    artifacts = {
        "report.json": "{}",
        "trace.json": json.dumps({"run_id": "trace", "trace": []}),
        "report.md": "# report",
        "report.docx": "word",
        "chart.svg": "<svg/>",
    }
    for name, content in artifacts.items():
        (report_root / name).write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="outside allowed trace root"):
        apply_trace_retention(
            report_root,
            allowed_trace_root=allowed,
            max_age_days=1,
            delete=True,
            now=NOW,
        )

    assert {path.name for path in report_root.iterdir()} == set(artifacts)


def test_retention_skips_non_trace_and_malformed_json_inside_allowed_root(tmp_path):
    ordinary = tmp_path / "old.json"
    malformed = tmp_path / "broken.json"
    ordinary.write_text('{"workspace_id":"ws_1"}', encoding="utf-8")
    malformed.write_text('{"token":"synthetic-token-do-not-leak"', encoding="utf-8")

    result = _apply_trace_retention(tmp_path, max_age_days=0, delete=True, now=NOW)

    assert ordinary.exists()
    assert malformed.exists()
    assert result.candidate_count == 0
    assert result.skipped_reasons["invalid_trace_document"] == 1
    assert result.skipped_reasons["json_parse_failed"] == 1
    assert "synthetic-token" not in repr(result)


def test_retention_skips_filename_mismatch_and_event_count_mismatch(tmp_path):
    filename_mismatch = _trace(tmp_path / "actual.json", 0, age_days=30)
    payload = json.loads(filename_mismatch.read_text(encoding="utf-8"))
    payload["run_id"] = "different"
    filename_mismatch.write_text(json.dumps(payload), encoding="utf-8")

    count_mismatch = _trace(tmp_path / "count.json", 0, age_days=30)
    payload = json.loads(count_mismatch.read_text(encoding="utf-8"))
    payload["event_count"] = 1
    count_mismatch.write_text(json.dumps(payload), encoding="utf-8")

    result = _apply_trace_retention(tmp_path, max_age_days=0, delete=True, now=NOW)

    assert filename_mismatch.exists()
    assert count_mismatch.exists()
    assert result.skipped_reasons["filename_run_id_mismatch"] == 1
    assert result.skipped_reasons["invalid_trace_document"] == 1


def test_retention_deletes_legacy_and_h3_traces_but_keeps_business_json(tmp_path):
    from tools.trace_logger import save_trace

    legacy = _trace(tmp_path / "legacy_run.json", 0, age_days=31)
    saved = save_trace("h3_run", [{"status": "success"}], trace_dir=tmp_path)
    h3 = Path(saved["trace_path"])
    business = tmp_path / "workspace.json"
    business.write_text(json.dumps({"run_id": "workspace", "trace": [], "event_count": 0}), encoding="utf-8")
    old_timestamp = (NOW - timedelta(days=31)).timestamp()
    os.utime(h3, (old_timestamp, old_timestamp))
    os.utime(business, (old_timestamp, old_timestamp))

    preview = _apply_trace_retention(tmp_path, max_age_days=30, now=NOW)
    assert preview.candidate_count == 2
    assert legacy.exists() and h3.exists() and business.exists()

    result = _apply_trace_retention(tmp_path, max_age_days=30, delete=True, now=NOW)
    assert result.deleted_count == 2
    assert not legacy.exists()
    assert not h3.exists()
    assert business.exists()


def test_retention_cli_misconfigured_workspace_target_fails_closed_without_leakage(
    tmp_path, monkeypatch, capsys
):
    from observability.trace_retention import main

    allowed = tmp_path / "logs" / "traces"
    workspace_root = tmp_path / "workspaces" / "secret-token-do-not-leak"
    allowed.mkdir(parents=True)
    workspace_root.mkdir(parents=True)
    workspace = workspace_root / "workspace.json"
    workspace.write_text('{"sql":"SELECT secret FROM customers"}', encoding="utf-8")
    monkeypatch.setenv("INSIGHTFLOW_TRACE_DIR", str(allowed))

    exit_code = main(
        ["--trace-dir", str(workspace_root), "--max-age-days", "1", "--delete"]
    )
    output = capsys.readouterr()

    assert exit_code == 2
    assert workspace.exists()
    assert json.loads(output.out) == {"success": False, "error_type": "validation_error"}
    for forbidden in (str(tmp_path), "secret-token", "SELECT secret", "Traceback"):
        assert forbidden not in output.out + output.err


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({}, "at least one retention limit"),
        ({"max_age_days": -1}, "max_age_days"),
        ({"max_total_bytes": -1}, "max_total_bytes"),
        ({"max_age_days": 100_000}, "max_age_days"),
    ],
)
def test_retention_rejects_invalid_or_unbounded_configuration(tmp_path, kwargs, message):
    from observability.trace_retention import apply_trace_retention

    with pytest.raises(ValueError, match=message):
        apply_trace_retention(tmp_path, allowed_trace_root=tmp_path, **kwargs)
