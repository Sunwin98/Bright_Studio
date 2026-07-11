"""Settings API — view/edit persisted paths (project stores, master assets,
knowledge dirs, com.mojang override). Applies live (no restart) and writes to
settings.json for next launch."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import config

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
def get_settings():
    return config.get_settings()


class SaveSettingsRequest(BaseModel):
    project_stores: List[str]
    master_assets: str
    default_output_dir: str
    knowledge_dirs: List[str] = []
    mc_com_mojang_override: Optional[str] = None


@router.post("/settings")
def save_settings(req: SaveSettingsRequest):
    try:
        return config.save_settings(req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/detect-mojang")
def detect_mojang():
    found = config.find_com_mojang()
    return {"found": found is not None, "com_mojang": str(found) if found else None}
