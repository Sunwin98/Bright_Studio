"""Find junk/backup folders inside the project stores.

DRY-RUN by design: this module only *reports* candidates (with sizes). Deletion
goes through app.core.projects.manage.delete_project, which enforces the
under-store guard. Versioned duplicates are intentionally NOT auto-flagged —
they're too easily real, separate commissions.
"""
from __future__ import annotations

import os
from pathlib import Path

import config
from app.core.projects.manage import folder_size

# Folder names that are safe to treat as removable junk/backups.
JUNK_NAMES = {
    "send", "sillkes", "blackup", "backup", "backups",
    "__pycache__", ".venv", "node_modules", "coverage", ".pytest_cache",
}


def find_junk() -> list[dict]:
    """Walk each store and report junk folders. Once a junk folder is found we
    report it whole and don't descend further into it."""
    found = []
    for store in config.PROJECT_STORES:
        if not store.exists():
            continue
        for root, dirs, _files in os.walk(store):
            keep = []
            for d in dirs:
                if d.lower() in JUNK_NAMES:
                    p = os.path.join(root, d)
                    found.append({
                        "path": p,
                        "name": d,
                        "store": store.name,
                        "size_bytes": folder_size(p),
                        "reason": _reason(d),
                    })
                    # don't descend into it
                else:
                    keep.append(d)
            dirs[:] = keep
    found.sort(key=lambda x: x["size_bytes"], reverse=True)
    return found


def _reason(name: str) -> str:
    n = name.lower()
    if n in ("send", "sillkes"):
        return "สำเนา backup ซ้อน (recursive copy)"
    if n in ("blackup", "backup", "backups"):
        return "โฟลเดอร์ backup"
    return "cache/ไฟล์ระบบ"


def total_size(candidates: list[dict]) -> int:
    return sum(c["size_bytes"] for c in candidates)
