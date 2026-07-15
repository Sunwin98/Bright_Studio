"""File history and restore points API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core import history

router = APIRouter(prefix="/api/history", tags=["history"])


class SnapshotRequest(BaseModel):
    paths: list[str] = Field(default_factory=list)
    label: str = "บันทึกสถานะไฟล์"
    source: str | None = None


@router.get("")
def list_history(limit: int = Query(100, ge=1, le=100)):
    return {"snapshots": history.list_snapshots(limit)}


@router.post("/snapshot")
def create_snapshot(req: SnapshotRequest):
    try:
        return history.create_snapshot(req.label, req.paths, source=req.source)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"สร้างประวัติไฟล์ไม่ได้: {exc}")


@router.get("/{snapshot_id}")
def get_history(snapshot_id: str):
    try:
        return history.get_snapshot(snapshot_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/{snapshot_id}/restore")
def restore_history(snapshot_id: str):
    try:
        return history.restore_snapshot(snapshot_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"กู้คืนไฟล์ไม่ได้: {exc}")


@router.delete("/{snapshot_id}")
def delete_history(snapshot_id: str):
    try:
        history.delete_snapshot(snapshot_id)
        return {"ok": True, "deleted": snapshot_id}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
