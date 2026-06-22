from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DataSourceRecord:
    source_id: str
    source_type: str
    name: str
    original_path: str
    imported_tables: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkspaceRecord:
    workspace_id: str
    name: str
    created_at: str
    updated_at: str
    root_path: str
    analysis_db_path: str
    profile_path: str
    semantic_layer_path: str
    sources: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
