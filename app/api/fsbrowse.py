"""Read-only filesystem browsing for the in-app file explorer.

The custom explorer window (web/js/ui/explorer.js) replaces both the native
pywebview/Neutralino dialogs and Windows Explorer pop-ups. Listing is read-only;
nothing here writes, deletes, or executes. Localhost-only like the rest of the
API.
"""
from __future__ import annotations

import os
import string
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

import config

router = APIRouter(prefix="/api/fs", tags=["fsbrowse"])


def _home() -> Path:
    return Path(os.path.expanduser("~"))


@router.get("/roots")
def roots():
    """Drives + quick-access shortcuts shown in the explorer sidebar."""
    drives = []
    for letter in string.ascii_uppercase:
        p = Path(f"{letter}:\\")
        if p.exists():
            drives.append({"name": f"{letter}:", "path": str(p)})

    home = _home()
    quick = []

    def add(label: str, icon: str, p: Path) -> None:
        if p and p.is_dir():
            quick.append({"name": label, "icon": icon, "path": str(p)})

    # icon = a name from web/js/ui/icons.js (frontend maps this to an SVG).
    add("หน้าแรก", "home", home)
    add("เดสก์ท็อป", "box", home / "Desktop")
    add("ดาวน์โหลด", "download", home / "Downloads")
    add("เอกสาร", "document", home / "Documents")
    add("รูปภาพ", "image", home / "Pictures")
    for prof in config.find_profiles():
        add(prof["name"], "pickaxe", Path(prof["path"]))
    for zone, stores in getattr(config, "ZONE_STORES", {}).items():
        label = "โปรเจกต์สกิน" if zone == "skin" else "โปรเจกต์สกิล" if zone == "skill" else zone
        for s in stores:
            add(label, "folder", Path(s))

    return {"drives": drives, "quick": quick}


@router.get("/list")
def list_dir(path: str = Query(...), exts: str = Query("")):
    """List one directory. `exts` = comma-separated extensions to show
    (e.g. ".mcaddon,.zip"); empty = show all files."""
    try:
        p = Path(path).resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="path ไม่ถูกต้อง")
    if not p.is_dir():
        raise HTTPException(status_code=404, detail="ไม่พบโฟลเดอร์")

    wanted = {e.strip().lower() for e in exts.split(",") if e.strip()}
    dirs, files = [], []
    try:
        entries = sorted(p.iterdir(), key=lambda x: x.name.lower())
    except PermissionError:
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์เข้าถึงโฟลเดอร์นี้")
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))

    for entry in entries:
        name = entry.name
        if name.startswith("$") or name.lower() in ("system volume information",):
            continue
        try:
            if entry.is_dir():
                dirs.append({"name": name, "path": str(entry)})
            elif entry.is_file():
                ext = entry.suffix.lower()
                if wanted and ext not in wanted:
                    continue
                files.append({
                    "name": name,
                    "path": str(entry),
                    "ext": ext,
                    "size": entry.stat().st_size,
                })
        except OSError:
            continue

    parent = str(p.parent) if p.parent != p else None
    return {"path": str(p), "parent": parent, "dirs": dirs, "files": files}
