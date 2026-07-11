"""Merger API — combine multiple skin addons into one."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core import merger

router = APIRouter(prefix="/api", tags=["merger"])


@router.get("/merger/scan")
def scan(path: str):
    try:
        return {"pairs": merger.scan_pairs(path)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


class Pair(BaseModel):
    name: str
    bp: str
    rp: str


class MergeRequest(BaseModel):
    pairs: List[Pair]
    merged_name: str
    output_dir: Optional[str] = None
    color: str = "§b"


@router.post("/merger/merge")
def merge(req: MergeRequest):
    try:
        return merger.merge([p.model_dump() for p in req.pairs], req.merged_name,
                            req.output_dir, req.color)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
