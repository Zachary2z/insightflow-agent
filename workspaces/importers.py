from __future__ import annotations

import re
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

import pandas as pd

from workspaces.models import DataSourceRecord
from workspaces.store import WorkspaceStore


def sanitize_identifier(value: str) -> str:
    sanitized = re.sub(r"[^\w]+", "_", value.strip().lower(), flags=re.UNICODE).strip("_")
    if not sanitized:
        sanitized = "table"
    if sanitized[0].isdigit():
        sanitized = f"t_{sanitized}"
    return sanitized


def _copy_raw_file(store: WorkspaceStore, workspace: dict, file_path: Path) -> str:
    del store
    raw_dir = Path(workspace["root_path"]) / "raw" / "uploaded_files"
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / file_path.name
    if target.exists():
        target = raw_dir / f"{target.stem}_{uuid4().hex[:6]}{target.suffix}"
    shutil.copy2(file_path, target)
    return str(target)


def _append_source(store: WorkspaceStore, workspace_id: str, source: DataSourceRecord) -> dict:
    workspace = store.get_workspace(workspace_id)
    workspace.setdefault("sources", []).append(source.to_dict())
    store.save_workspace(workspace)
    return store.increment_data_version(workspace_id)


def _write_frame(db_path: str, table_name: str, frame: pd.DataFrame) -> None:
    frame = frame.rename(columns={column: sanitize_identifier(str(column)) for column in frame.columns})
    with sqlite3.connect(db_path) as conn:
        frame.to_sql(table_name, conn, if_exists="replace", index=False)


def import_csv(store: WorkspaceStore, workspace_id: str, csv_path: str | Path) -> dict:
    workspace = store.get_workspace(workspace_id)
    source_path = Path(csv_path)
    table_name = sanitize_identifier(source_path.stem)
    raw_path = _copy_raw_file(store, workspace, source_path)
    frame = pd.read_csv(source_path)
    _write_frame(workspace["analysis_db_path"], table_name, frame)
    source = DataSourceRecord(
        source_id=f"src_{uuid4().hex[:8]}",
        source_type="csv",
        name=source_path.name,
        original_path=raw_path,
        imported_tables=[table_name],
    )
    workspace = _append_source(store, workspace_id, source)
    return {
        "success": True,
        "source": source.to_dict(),
        "imported_tables": [table_name],
        "data_version": workspace["data_version"],
    }


def import_excel(store: WorkspaceStore, workspace_id: str, excel_path: str | Path) -> dict:
    workspace = store.get_workspace(workspace_id)
    source_path = Path(excel_path)
    raw_path = _copy_raw_file(store, workspace, source_path)
    sheets = pd.read_excel(source_path, sheet_name=None)
    imported_tables = []
    for sheet_name, frame in sheets.items():
        table_name = sanitize_identifier(sheet_name)
        _write_frame(workspace["analysis_db_path"], table_name, frame)
        imported_tables.append(table_name)
    source = DataSourceRecord(
        source_id=f"src_{uuid4().hex[:8]}",
        source_type="excel",
        name=source_path.name,
        original_path=raw_path,
        imported_tables=imported_tables,
    )
    workspace = _append_source(store, workspace_id, source)
    return {
        "success": True,
        "source": source.to_dict(),
        "imported_tables": imported_tables,
        "data_version": workspace["data_version"],
    }


def import_sqlite(store: WorkspaceStore, workspace_id: str, sqlite_path: str | Path) -> dict:
    workspace = store.get_workspace(workspace_id)
    source_path = Path(sqlite_path)
    imported_tables = []
    with sqlite3.connect(source_path) as source_conn, sqlite3.connect(workspace["analysis_db_path"]) as target_conn:
        table_rows = source_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        for (table_name,) in table_rows:
            clean_name = sanitize_identifier(table_name)
            frame = pd.read_sql_query(f'SELECT * FROM "{table_name}"', source_conn)
            frame.to_sql(clean_name, target_conn, if_exists="replace", index=False)
            imported_tables.append(clean_name)
    source = DataSourceRecord(
        source_id=f"src_{uuid4().hex[:8]}",
        source_type="sqlite",
        name=source_path.name,
        original_path=str(source_path),
        imported_tables=imported_tables,
    )
    workspace = _append_source(store, workspace_id, source)
    return {
        "success": True,
        "source": source.to_dict(),
        "imported_tables": imported_tables,
        "data_version": workspace["data_version"],
    }
