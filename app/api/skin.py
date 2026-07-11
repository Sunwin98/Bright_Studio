"""Skin Factory API — preview auto-icon and build a full skin addon."""
from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.skin_factory import builder
from app.core import checker

router = APIRouter(prefix="/api", tags=["skin"])


class PreviewIconRequest(BaseModel):
    skin_path: str


@router.post("/skin/preview-icon")
def preview_icon(req: PreviewIconRequest):
    if not os.path.exists(req.skin_path):
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {req.skin_path}")
    b64 = builder.preview_icon_base64(req.skin_path)
    if b64 is None:
        raise HTTPException(status_code=422, detail="สร้าง preview ไม่ได้ (ต้องมี Pillow และไฟล์ PNG ที่ถูกต้อง)")
    return {"icon_base64": b64}


class SkinInput(BaseModel):
    skin_path: str
    model_path: Optional[str] = None
    animation_path: Optional[str] = None
    display_name: Optional[str] = None
    slot: str = "1"


class SkinBuildRequest(BaseModel):
    addon_name: str
    ui_mode: str = "normal"           # normal | special | none
    xbox_lock: bool = False
    xbox_players: List[str] = []
    output_dir: Optional[str] = None
    overwrite: bool = True
    skins: List[SkinInput]


@router.post("/skin/build")
def build(req: SkinBuildRequest):
    if not req.skins:
        raise HTTPException(status_code=422, detail="ต้องมีอย่างน้อย 1 สกิน")
    try:
        result = builder.build_addon(req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    try:
        result["validation"] = checker.check_addon(result.get("bp_path"), result.get("rp_path"))
    except Exception:
        pass  # never let validation failure hide a successful build
    return result
