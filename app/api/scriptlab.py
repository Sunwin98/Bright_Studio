"""Script Lab API — open an addon, parse a script into an editable table,
save value edits back with formatting preserved."""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core import packio
from app.core.scriptlab import analyzer
from app.core.scriptlab import sync as sl_sync
from app.core.scriptlab.parser import apply_edits, read_source, write_source

router = APIRouter(prefix="/api/sl", tags=["scriptlab"])


def _guard_js(raw: str) -> Path:
    p = Path(raw)
    if p.suffix.lower() != ".js":
        raise HTTPException(status_code=400, detail="ต้องเป็นไฟล์ .js")
    if not p.is_file():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {raw}")
    if p.stat().st_size > 2_000_000:
        raise HTTPException(status_code=400, detail="ไฟล์ใหญ่เกิน 2MB")
    return p


class OpenBody(BaseModel):
    path: str


@router.post("/open")
def open_source(body: OpenBody):
    """Accept .mcaddon/.mcpack/.zip/folder → BP path + summarized script list."""
    try:
        info = packio.inspect_source(body.path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    bp = info.get("bp_path")
    if not bp:
        raise HTTPException(status_code=400, detail="ไม่พบ Behavior Pack ในไฟล์/โฟลเดอร์นี้")
    scripts = analyzer.list_scripts(Path(bp))
    if not scripts:
        raise HTTPException(status_code=404, detail="Behavior Pack นี้ไม่มีไฟล์สคริป (.js)")
    return {"source": info["source"], "bp_path": bp, "scripts": scripts}


@router.get("/parse")
def parse(js_path: str = Query(...)):
    p = _guard_js(js_path)
    try:
        return analyzer.parse_for_ui(p)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"อ่านสคริปไม่ได้: {e}")


class SaveBody(BaseModel):
    js_path: str
    mtime: float
    edits: list[dict]   # [{start, end, new_text}]


@router.post("/save")
def save(body: SaveBody):
    p = _guard_js(body.js_path)
    if not body.edits:
        raise HTTPException(status_code=400, detail="ไม่มีการแก้ไข")
    # stale check: file changed since the client parsed it → spans invalid
    if abs(p.stat().st_mtime - body.mtime) > 1e-4:
        raise HTTPException(status_code=409,
                            detail="ไฟล์ถูกแก้จากที่อื่นหลังเปิด — กดรีเฟรชก่อนแก้ต่อ")
    src = read_source(p)
    try:
        new_src = apply_edits(src, body.edits)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))
    try:
        write_source(p, new_src)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"เขียนไฟล์ไม่ได้: {e}")
    resp = {"ok": True, "mtime": p.stat().st_mtime, "backup": str(p) + ".bak"}
    # Hot-sync onto any deployed copy of this pack so /reload picks it up.
    try:
        resp.update(sl_sync.sync_to_dev(str(p)))
    except Exception as e:  # never let sync failure fail a successful save
        resp["synced"] = []
        resp["error"] = str(e)
    return resp
