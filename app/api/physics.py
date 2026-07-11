"""Physics API — list tools, dry-run bone discovery, inspect addons, and apply physics in place."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.physics import runner, inspector

router = APIRouter(prefix="/api", tags=["physics"])


@router.get("/physics/tools")
def tools():
    return {"tools": runner.list_tools()}


class InspectRequest(BaseModel):
    path: str


@router.post("/physics/inspect")
def inspect(req: InspectRequest):
    try:
        return inspector.inspect_addon_for_physics(req.path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


class BonesRequest(BaseModel):
    tool: str
    animation_path: Optional[str] = None
    model_path: Optional[str] = None
    prefixes: List[str] = []


@router.post("/physics/bones")
def bones(req: BonesRequest):
    try:
        found = runner.find_bones(req.tool, req.animation_path, req.model_path, req.prefixes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    return {"bones": found}


class BoneGroup(BaseModel):
    prefix: str
    bones: List[str]


class ApplyRequest(BaseModel):
    tool: str
    animation_path: str
    model_path: Optional[str] = None
    attachable_path: Optional[str] = None
    prefixes: List[str] = []
    bone_groups: Optional[List[BoneGroup]] = None
    bone_name: Optional[str] = None
    intensity: str = "medium"       # cape
    strength: Optional[float] = None  # back_hair (None = auto)


@router.post("/physics/apply")
def apply(req: ApplyRequest):
    try:
        return runner.apply(req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

