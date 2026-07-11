"""Weapon and item generator API."""
from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.weapon import generator, item_builder, geo_swap, inspector
from app.core import checker

router = APIRouter(prefix="/api", tags=["weapon"])


class InspectRequest(BaseModel):
    path: str


@router.post("/weapon/inspect")
def inspect(req: InspectRequest):
    try:
        return inspector.inspect_addon_for_weapon(req.path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")



class GenerateRequest(BaseModel):
    bp_path: str = ""
    rp_path: str = ""
    gen_bp: bool = True
    gen_rp: bool = True
    items: List[str]
    entity_opts: Dict[str, bool] = {}


@router.post("/weapon/generate")
def generate(req: GenerateRequest):
    try:
        result = generator.generate(req.bp_path, req.rp_path, req.gen_bp, req.gen_rp,
                                     req.items, req.entity_opts)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    try:
        bp_check = req.bp_path if req.gen_bp else None
        rp_check = req.rp_path if req.gen_rp else None
        if bp_check or rp_check:
            result["validation"] = checker.check_addon(bp_check, rp_check)
    except Exception:
        pass
    return result


class ItemRequest(BaseModel):
    bp_path: Optional[str] = None
    rp_path: Optional[str] = None
    addon_name: Optional[str] = None
    output_dir: Optional[str] = None
    namespace: str
    item_name: str
    display_name: Optional[str] = None
    model_path: str
    model_texture_path: str
    icon_path: str
    held_animation_path: Optional[str] = None
    menu_category: str = "equipment"
    damage: Optional[int] = None
    enchantable_slot: Optional[str] = None
    enchantable_value: Optional[int] = None
    cooldown_seconds: Optional[float] = None


@router.post("/weapon/item")
def build_item(req: ItemRequest):
    try:
        result = item_builder.build_item(req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    try:
        result["validation"] = checker.check_addon(result.get("bp_path"), result.get("rp_path"))
    except Exception:
        pass
    return result


class GeoSwapRequest(BaseModel):
    rp_path: str
    bp_path: Optional[str] = None
    item_identifier: str
    bones: List[str]
    base_player_geo_path: Optional[str] = None
    gen_bp_script: bool = True


@router.post("/weapon/geo-swap")
def geo_swap_build(req: GeoSwapRequest):
    try:
        return geo_swap.build_geo_swap(req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

