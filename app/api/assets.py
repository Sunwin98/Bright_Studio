"""Read-only asset browser API."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core import assets

router = APIRouter(prefix="/api/assets", tags=["assets"])


class ScanRequest(BaseModel):
    path: str


@router.post("/scan")
def scan(req: ScanRequest):
    try:
        return assets.scan_source(req.path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"เปิด Asset ไม่ได้: {type(exc).__name__}: {exc}")


@router.get("/file")
def file(path: str = Query(...)):
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์ Asset")
    if target.suffix.lower() not in assets.IMAGE_EXTS:
        raise HTTPException(status_code=400, detail="เปิดตัวอย่างได้เฉพาะไฟล์รูปภาพ")
    return FileResponse(target)
