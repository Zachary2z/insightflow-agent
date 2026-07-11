from __future__ import annotations

import re


KNOWN_METRIC_ACRONYMS = {
    "AOV",
    "CAC",
    "CPA",
    "CPC",
    "CPM",
    "CTR",
    "CVR",
    "GMV",
    "ROI",
    "ROAS",
}


def looks_like_raw_parameter_dump(text: str) -> bool:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return False
    dump_lines = 0
    for line in lines:
        stripped = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line)
        assignments = [
            key
            for key in re.findall(r"\b([A-Za-z_][A-Za-z0-9_. -]*)\s*=", stripped)
            if looks_like_raw_assignment_key(key)
        ]
        if len(assignments) >= 2 or (assignments and "," in stripped):
            dump_lines += 1
    return dump_lines >= max(1, len(lines) // 2)


def looks_like_raw_assignment_key(key: str) -> bool:
    token = str(key or "").strip().split()[-1] if str(key or "").strip() else ""
    if not token:
        return False
    if token.upper() in KNOWN_METRIC_ACRONYMS:
        return False
    return not (token.isupper() and len(token) <= 5)
