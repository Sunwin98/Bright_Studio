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


class ExtractModelRequest(BaseModel):
    model_path: str


@router.post("/physics/extract_model")
def extract_model(req: ExtractModelRequest):
    try:
        from pathlib import Path
        from app.core.physics.inspector import _load_json, find_bone_chains
        
        p = Path(req.model_path)
        if not p.is_file():
            raise ValueError(f"Model file not found: {p}")
            
        data = _load_json(p)
        if not data or not isinstance(data, dict):
            raise ValueError(f"Invalid JSON in model file: {p}")
            
        geometries = data.get("minecraft:geometry", [])
        if isinstance(geometries, dict):
            geometries = [geometries]
            
        all_bones = []
        for geo in geometries:
            if not isinstance(geo, dict): continue
            bones_list = geo.get("bones", [])
            if not isinstance(bones_list, list): continue
            for bone in bones_list:
                name = bone.get("name")
                if name:
                    all_bones.append({"name": name, "parent": bone.get("parent")})
                    
        # Remove duplicates preserving order
        seen = set()
        unique_bones = []
        for b in all_bones:
            if b["name"] not in seen:
                seen.add(b["name"])
                unique_bones.append(b)
                
        chains = find_bone_chains(unique_bones)
        return {
            "bones": [b["name"] for b in unique_bones],
            "discovered_chains": chains
        }
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
    source_path: Optional[str] = None


@router.post("/physics/apply")
def apply(req: ApplyRequest):
    try:
        return runner.apply(req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

