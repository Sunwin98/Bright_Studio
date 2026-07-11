"""API for universal addon intake (.mcaddon/.zip/folder → BP/RP paths)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core import packio

router = APIRouter(prefix="/api/packio", tags=["packio"])


class InspectBody(BaseModel):
    path: str


@router.post("/inspect")
def inspect(body: InspectBody):
    try:
        return packio.inspect_source(body.path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"อ่านแพ็คไม่ได้: {e}")
