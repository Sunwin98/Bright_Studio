"""Addon Checker API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core import checker

router = APIRouter(prefix="/api", tags=["checker"])


class CheckRequest(BaseModel):
    bp_path: Optional[str] = None
    rp_path: Optional[str] = None


class FixRequest(CheckRequest):
    source: Optional[str] = None
    repairs: list[dict] = Field(default_factory=list)


@router.post("/checker/check")
def check(req: CheckRequest):
    if not req.bp_path and not req.rp_path:
        raise HTTPException(status_code=422, detail="ต้องระบุ BP หรือ RP อย่างน้อย 1 ฝั่ง")
    try:
        return checker.check_addon(req.bp_path, req.rp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/checker/fix")
def fix(req: FixRequest):
    if not req.bp_path and not req.rp_path:
        raise HTTPException(status_code=422, detail="ต้องระบุ BP หรือ RP อย่างน้อย 1 ฝั่ง")
    try:
        if req.source:
            return checker.fix_source(req.source, req.bp_path, req.rp_path, req.repairs)
        return checker.fix_addon(req.bp_path, req.rp_path, req.repairs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
