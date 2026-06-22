from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

from workspaces.models import WorkspaceRecord, utc_now_iso


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "workspace"


class WorkspaceStore:
    def __init__(self, root_dir: str | Path = "workspaces"):
        self.root_dir = Path(root_dir)

    def create_workspace(self, name: str) -> dict:
        workspace_id = f"{_slugify(name)}-{uuid4().hex[:8]}"
        root = self.root_dir / workspace_id
        (root / "raw" / "uploaded_files").mkdir(parents=True, exist_ok=False)
        (root / "runs").mkdir(parents=True, exist_ok=True)
        now = utc_now_iso()
        record = WorkspaceRecord(
            workspace_id=workspace_id,
            name=name,
            created_at=now,
            updated_at=now,
            root_path=str(root),
            analysis_db_path=str(root / "analysis.db"),
            profile_path=str(root / "profile.json"),
            semantic_layer_path=str(root / "semantic_layer.yaml"),
        )
        self._write_record(record.to_dict())
        return record.to_dict()

    def list_workspaces(self) -> list[dict]:
        if not self.root_dir.exists():
            return []
        records = []
        for metadata_path in sorted(self.root_dir.glob("*/workspace.json")):
            records.append(json.loads(metadata_path.read_text(encoding="utf-8")))
        return records

    def get_workspace(self, workspace_id: str) -> dict:
        metadata_path = self.root_dir / workspace_id / "workspace.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Workspace not found: {workspace_id}")
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    def save_workspace(self, workspace: dict) -> dict:
        workspace["updated_at"] = utc_now_iso()
        self._write_record(workspace)
        return workspace

    def resolve_workspace_path(self, workspace_id: str, relative_path: str | Path) -> Path:
        workspace_root = (self.root_dir / workspace_id).resolve()
        candidate = (workspace_root / relative_path).resolve()
        if candidate != workspace_root and workspace_root not in candidate.parents:
            raise ValueError(f"Resolved path is outside workspace: {relative_path}")
        return candidate

    def _write_record(self, workspace: dict) -> None:
        root = Path(workspace["root_path"])
        root.mkdir(parents=True, exist_ok=True)
        (root / "workspace.json").write_text(
            json.dumps(workspace, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
