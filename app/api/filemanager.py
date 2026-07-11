"""File Manager API — browse & manage the Minecraft Bedrock com.mojang folder.

The browser can't touch the filesystem directly (unlike the reference Neutralino
app), so everything goes through here. Every endpoint that takes a `path`
sandboxes it under a real com.mojang root before reading, deleting, or opening —
a hard stop against path traversal / deleting arbitrary files.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

import config
from app.core import filemanager as fm

router = APIRouter(prefix="/api/fm", tags=["filemanager"])


def _roots() -> list[Path]:
    return [Path(p["path"]).resolve() for p in config.find_profiles()]


def _guard(raw: str) -> tuple[Path, Path]:
    """Resolve `raw` and confirm it sits inside a com.mojang root.

    Returns (resolved_path, mojang_root). Raises 400 otherwise."""
    if not raw:
        raise HTTPException(status_code=400, detail="path ว่าง")
    try:
        target = Path(raw).resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="path ไม่ถูกต้อง")
    for root in _roots():
        if target == root or root in target.parents:
            return target, root
    raise HTTPException(status_code=400, detail="path อยู่นอกขอบเขต com.mojang (ปฏิเสธ)")


def _profile_root(idx: int) -> Path:
    roots = _roots()
    if idx < 0 or idx >= len(roots):
        raise HTTPException(status_code=404, detail="ไม่พบโปรไฟล์")
    return roots[idx]


@router.get("/profiles")
def profiles():
    return {"profiles": config.find_profiles()}


@router.get("/addons")
def addons(profile: int = 0):
    return {"packs": fm.list_packs(_profile_root(profile))}


@router.get("/worlds")
def worlds(profile: int = 0):
    return {"worlds": fm.list_worlds(_profile_root(profile))}


@router.get("/world_addons")
def world_addons(path: str = Query(...)):
    target, _ = _guard(path)
    if not target.is_dir():
        raise HTTPException(status_code=404, detail="ไม่พบโฟลเดอร์โลก")
    all_packs = []
    for r in _roots():
        all_packs.extend(fm.list_packs(r))
    return fm.world_addons(target, all_packs)

class ToggleWorldAddonBody(BaseModel):
    world_path: str
    ptype: str
    pack_id: str
    version: list
    action: str

@router.post("/toggle_world_addon")
def toggle_world_addon(body: ToggleWorldAddonBody):
    target, _ = _guard(body.world_path)
    if not target.is_dir():
        raise HTTPException(status_code=404, detail="ไม่พบโฟลเดอร์โลก")
    try:
        fm.toggle_world_addon(target, body.ptype, body.pack_id, body.version, body.action)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Toggle failed: {e}")
    return {"ok": True}



@router.get("/icon")
def icon(path: str = Query(...)):
    target, _ = _guard(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="ไม่พบไอคอน")
    return FileResponse(str(target))


class PathBody(BaseModel):
    path: str


@router.post("/delete")
def delete(body: PathBody):
    target, _ = _guard(body.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์/โฟลเดอร์")
    try:
        from send2trash import send2trash
    except ImportError:
        raise HTTPException(status_code=500, detail="ต้องติดตั้ง send2trash (pip install send2trash)")
    try:
        send2trash(str(target))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ลบไม่สำเร็จ: {e}")
    return {"ok": True, "trashed": str(target)}


@router.post("/reveal")
def reveal(body: PathBody):
    target, _ = _guard(body.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์/โฟลเดอร์")
    try:
        os.startfile(str(target))  # noqa: S606 — Windows Explorer / default handler
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เปิดไม่สำเร็จ: {e}")
    return {"ok": True}
