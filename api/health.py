from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel


SERVICE_NAME = "insightflow-api"
CheckStatus = Literal["ok", "error"]


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["insightflow-api"] = SERVICE_NAME


class ReadinessChecks(BaseModel):
    workspace_storage: CheckStatus
    report_storage: CheckStatus
    trace_storage: CheckStatus
    configuration: CheckStatus


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    service: Literal["insightflow-api"] = SERVICE_NAME
    checks: ReadinessChecks


@dataclass(frozen=True)
class ReadinessPaths:
    workspace_root: Path
    report_root: Path
    trace_root: Path


ProbeNameFactory = Callable[[], str]
StorageCheck = Callable[[Path], CheckStatus]
ConfigurationCheck = Callable[[ReadinessPaths], CheckStatus]


def _probe_name() -> str:
    return f".insightflow-health-{uuid4().hex}"


def check_storage_directory(
    directory: Path,
    *,
    probe_name_factory: ProbeNameFactory = _probe_name,
) -> CheckStatus:
    """Check one runtime directory without reading or replacing user files."""
    probe_path: Path | None = None
    descriptor: int | None = None
    probe_created = False
    try:
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir() or not os.access(directory, os.R_OK | os.W_OK):
            return "error"

        probe_path = directory / probe_name_factory()
        descriptor = os.open(
            probe_path,
            os.O_CREAT | os.O_EXCL | os.O_RDWR,
            0o600,
        )
        probe_created = True
        os.write(descriptor, b"ok")
        os.lseek(descriptor, 0, os.SEEK_SET)
        if os.read(descriptor, 2) != b"ok":
            return "error"
        os.close(descriptor)
        descriptor = None
        probe_path.unlink()
        probe_created = False
        probe_path = None
        return "ok"
    except Exception:
        return "error"
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if probe_created and probe_path is not None:
            try:
                probe_path.unlink(missing_ok=True)
            except OSError:
                pass


def check_configuration(paths: ReadinessPaths) -> CheckStatus:
    values = (paths.workspace_root, paths.report_root, paths.trace_root)
    if not all(isinstance(value, Path) for value in values):
        return "error"
    if any(not str(value).strip() or "\x00" in str(value) for value in values):
        return "error"
    return "ok"


class ReadinessChecker:
    def __init__(
        self,
        paths: ReadinessPaths,
        *,
        storage_check: StorageCheck = check_storage_directory,
        configuration_check: ConfigurationCheck = check_configuration,
    ):
        self.paths = paths
        self._storage_check = storage_check
        self._configuration_check = configuration_check

    @staticmethod
    def _safe_check(check: Callable[[], CheckStatus]) -> CheckStatus:
        try:
            return "ok" if check() == "ok" else "error"
        except Exception:
            return "error"

    def check(self) -> ReadinessResponse:
        checks = ReadinessChecks(
            workspace_storage=self._safe_check(
                lambda: self._storage_check(self.paths.workspace_root)
            ),
            report_storage=self._safe_check(
                lambda: self._storage_check(self.paths.report_root)
            ),
            trace_storage=self._safe_check(
                lambda: self._storage_check(self.paths.trace_root)
            ),
            configuration=self._safe_check(
                lambda: self._configuration_check(self.paths)
            ),
        )
        status = "ready" if all(value == "ok" for value in checks.model_dump().values()) else "not_ready"
        return ReadinessResponse(status=status, checks=checks)
