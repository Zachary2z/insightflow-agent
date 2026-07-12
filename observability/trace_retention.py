from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable

from observability.redaction import classify_error
from observability.trace_paths import has_symlink_component, safe_trace_run_id


MAX_RETENTION_DAYS = 36_500
MAX_RETENTION_BYTES = 1 << 60
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE_ROOT = PROJECT_ROOT / "logs" / "traces"
PROTECTED_BUSINESS_ROOTS = (
    PROJECT_ROOT / "workspaces",
    PROJECT_ROOT / "reports",
    Path("/app/workspaces"),
    Path("/app/reports"),
)


@dataclass(frozen=True, slots=True)
class TraceRetentionResult:
    dry_run: bool
    scanned_count: int
    scanned_bytes: int
    candidate_count: int
    candidate_bytes: int
    deleted_count: int
    deleted_bytes: int
    skipped_reasons: dict[str, int]


@dataclass(frozen=True, slots=True)
class _TraceFile:
    path: Path
    size: int
    modified_at: float
    run_id: str
    device: int
    inode: int
    modified_at_ns: int


def _bounded_integer(name: str, value: int | None, maximum: int) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0 or value > maximum:
        raise ValueError(f"{name} must be between 0 and {maximum}")
    return value


def _file_stat(path: Path) -> os.stat_result:
    return os.stat(path, follow_symlinks=False)


def _configured_trace_root() -> Path:
    return Path(os.getenv("INSIGHTFLOW_TRACE_DIR", str(DEFAULT_TRACE_ROOT)))


def _resolved_without_symlinks(path: Path) -> Path:
    if has_symlink_component(path):
        raise ValueError("path must be a real directory without symbolic links")
    try:
        return path.resolve(strict=False)
    except OSError:
        raise ValueError("path cannot be resolved") from None


def _contains(parent: Path, child: Path) -> bool:
    return child == parent or parent in child.parents


def _authorize_trace_root(trace_root: Path, allowed_trace_root: Path) -> tuple[Path, Path]:
    resolved_root = _resolved_without_symlinks(trace_root)
    resolved_allowed = _resolved_without_symlinks(allowed_trace_root)
    if not _contains(resolved_allowed, resolved_root):
        raise ValueError("outside allowed trace root")

    protected = tuple(_resolved_without_symlinks(path) for path in PROTECTED_BUSINESS_ROOTS)
    resolved_project = PROJECT_ROOT.resolve()
    resolved_default_trace = DEFAULT_TRACE_ROOT.resolve(strict=False)
    protected_project_path = _contains(resolved_project, resolved_root) and not _contains(
        resolved_default_trace, resolved_root
    )
    if protected_project_path or any(
        _contains(path, resolved_root) or _contains(resolved_root, path) for path in protected
    ):
        raise ValueError("protected root")
    return resolved_root, resolved_allowed


def _is_utc_timestamp(value: object) -> bool:
    if type(value) is not str:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)


def _trace_document_skip_reason(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "json_parse_failed"
    except (OSError, UnicodeError):
        return "trace_read_failed"

    if type(payload) is not dict:
        return "invalid_trace_document"
    run_id = payload.get("run_id")
    if type(run_id) is not str:
        return "invalid_trace_document"
    if path.stem != safe_trace_run_id(run_id):
        return "filename_run_id_mismatch"
    trace = payload.get("trace")
    event_count = payload.get("event_count")
    if type(trace) is not list or type(event_count) is not int or event_count < 0:
        return "invalid_trace_document"
    if event_count != len(trace):
        return "invalid_trace_document"
    if not _is_utc_timestamp(payload.get("saved_at")):
        return "invalid_trace_document"
    if type(payload.get("status")) is not str or type(payload.get("question_thread")) is not dict:
        return "invalid_trace_document"
    if payload.get("session_id") is not None and type(payload.get("session_id")) is not str:
        return "invalid_trace_document"
    if payload.get("user_question") is not None and type(payload.get("user_question")) is not str:
        return "invalid_trace_document"
    return None


def apply_trace_retention(
    trace_root: str | Path,
    *,
    allowed_trace_root: str | Path | None = None,
    max_age_days: int | None = None,
    max_total_bytes: int | None = None,
    active_run_ids: Iterable[str] = (),
    delete: bool = False,
    now: datetime | None = None,
) -> TraceRetentionResult:
    max_age_days = _bounded_integer("max_age_days", max_age_days, MAX_RETENTION_DAYS)
    max_total_bytes = _bounded_integer("max_total_bytes", max_total_bytes, MAX_RETENTION_BYTES)
    if max_age_days is None and max_total_bytes is None:
        raise ValueError("at least one retention limit is required")
    if type(delete) is not bool:
        raise ValueError("delete must be a boolean")

    root = Path(trace_root)
    allowed_root = Path(allowed_trace_root) if allowed_trace_root is not None else _configured_trace_root()
    resolved_root, _ = _authorize_trace_root(root, allowed_root)
    empty = TraceRetentionResult(not delete, 0, 0, 0, 0, 0, 0, {})
    if not root.exists():
        return empty
    if has_symlink_component(root) or not root.is_dir():
        raise ValueError("trace_root must be a real directory")
    try:
        strict_root = root.resolve(strict=True)
    except OSError:
        raise ValueError("trace_root cannot be resolved") from None
    if strict_root != resolved_root:
        raise ValueError("trace_root changed during authorization")
    active = {safe_trace_run_id(run_id) for run_id in active_run_ids}
    skipped: Counter[str] = Counter()
    files: list[_TraceFile] = []
    protected_bytes = 0
    scanned_count = 0
    scanned_bytes = 0

    try:
        entries = sorted(root.iterdir(), key=lambda item: item.name)
    except OSError:
        return TraceRetentionResult(not delete, 0, 0, 0, 0, 0, 0, {"scan_failed": 1})
    for path in entries:
        if path.is_symlink():
            skipped["symlink"] += 1
            continue
        if path.suffix != ".json":
            skipped["not_final_json"] += 1
            continue
        if not path.is_file():
            skipped["not_file"] += 1
            continue
        if path.parent.resolve() != resolved_root:
            skipped["outside_root"] += 1
            continue
        try:
            stat = _file_stat(path)
        except OSError:
            skipped["stat_failed"] += 1
            continue
        scanned_count += 1
        scanned_bytes += stat.st_size
        skip_reason = _trace_document_skip_reason(path)
        if skip_reason is not None:
            skipped[skip_reason] += 1
            continue
        run_id = path.stem
        if run_id in active:
            skipped["active_run"] += 1
            protected_bytes += stat.st_size
            continue
        files.append(
            _TraceFile(
                path,
                stat.st_size,
                stat.st_mtime,
                run_id,
                stat.st_dev,
                stat.st_ino,
                stat.st_mtime_ns,
            )
        )

    ordered = sorted(files, key=lambda item: (item.modified_at, item.path.name))
    candidates: dict[Path, _TraceFile] = {}
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if max_age_days is not None:
        cutoff = (current_time - timedelta(days=max_age_days)).timestamp()
        for item in ordered:
            if item.modified_at < cutoff:
                candidates[item.path] = item

    total_bytes = protected_bytes + sum(item.size for item in files)
    projected_bytes = total_bytes - sum(item.size for item in candidates.values())
    if max_total_bytes is not None and projected_bytes > max_total_bytes:
        for item in ordered:
            if item.path in candidates:
                continue
            candidates[item.path] = item
            projected_bytes -= item.size
            if projected_bytes <= max_total_bytes:
                break
        if projected_bytes > max_total_bytes:
            skipped["capacity_unmet_protected"] += 1

    selected = sorted(candidates.values(), key=lambda item: (item.modified_at, item.path.name))
    deleted_count = 0
    deleted_bytes = 0
    if delete:
        for item in selected:
            try:
                current = _file_stat(item.path)
                identity = (current.st_dev, current.st_ino, current.st_mtime_ns, current.st_size)
                expected = (item.device, item.inode, item.modified_at_ns, item.size)
                if identity != expected or item.path.parent.resolve() != resolved_root:
                    skipped["changed_during_scan"] += 1
                    continue
                item.path.unlink()
                deleted_count += 1
                deleted_bytes += item.size
            except Exception:
                skipped["delete_failed"] += 1

    return TraceRetentionResult(
        dry_run=not delete,
        scanned_count=scanned_count,
        scanned_bytes=scanned_bytes,
        candidate_count=len(selected),
        candidate_bytes=sum(item.size for item in selected),
        deleted_count=deleted_count,
        deleted_bytes=deleted_bytes,
        skipped_reasons=dict(sorted(skipped.items())),
    )


def _optional_env_integer(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise ValueError("invalid arguments")


def main(argv: list[str] | None = None) -> int:
    try:
        parser = _SafeArgumentParser(description="Preview or apply bounded local JSON Trace retention.")
        allowed_trace_root = _configured_trace_root()
        parser.add_argument("--trace-dir", default=str(allowed_trace_root))
        parser.add_argument("--max-age-days", type=int, default=_optional_env_integer("INSIGHTFLOW_TRACE_RETENTION_DAYS"))
        parser.add_argument("--max-total-bytes", type=int, default=_optional_env_integer("INSIGHTFLOW_TRACE_RETENTION_MAX_BYTES"))
        parser.add_argument("--active-run-id", action="append", default=[])
        parser.add_argument("--delete", action="store_true", help="Actually delete candidates; default is dry-run.")
        args = parser.parse_args(argv)
        result = apply_trace_retention(
            args.trace_dir,
            allowed_trace_root=allowed_trace_root,
            max_age_days=args.max_age_days,
            max_total_bytes=args.max_total_bytes,
            active_run_ids=args.active_run_id,
            delete=args.delete,
        )
    except Exception as exc:
        payload = {"success": False, "error_type": classify_error(exc) or "internal_error"}
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return 2
    print(json.dumps(asdict(result), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
