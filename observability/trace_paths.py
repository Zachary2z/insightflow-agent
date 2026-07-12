from __future__ import annotations

import os
from pathlib import Path


def safe_trace_run_id(run_id: object) -> str:
    text = run_id if type(run_id) is str else ""
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in text.strip())
    return safe or "run_unknown"


def has_symlink_component(path: Path) -> bool:
    absolute = Path(os.path.abspath(path))
    components = (*reversed(absolute.parents), absolute)
    return any(component.exists() and component.is_symlink() for component in components)
