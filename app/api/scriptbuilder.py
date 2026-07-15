"""Visual Script Builder API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core import scriptbuilder

router = APIRouter(prefix="/api/scriptbuilder", tags=["scriptbuilder"])


class CreateRequest(BaseModel):
    bp_path: str
    name: str = "custom_event"
    event_id: str
    blocks: list[dict] = Field(default_factory=list)
    overwrite: bool = False


@router.get("/events")
def events():
    return {"events": [{"id": key, **value} for key, value in scriptbuilder.EVENTS.items()]}


@router.post("/preview")
def preview(req: CreateRequest):
    try:
        return {"script": scriptbuilder.build_source(req.event_id, req.blocks)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/create")
def create(req: CreateRequest):
    try:
        return scriptbuilder.create_script(req.bp_path, req.name, req.event_id, req.blocks, req.overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"สร้าง Script ไม่ได้: {exc}")
