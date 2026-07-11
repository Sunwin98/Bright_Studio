"""Project Browser API — list grouped projects and open a folder in Explorer."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.projects.scanner import scan_projects
from app.core.projects import manage
from app.core import ops, cleanup

router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects")
def list_projects(zone: str = ""):
    """zone: "" = default PROJECT_STORES; otherwise a key in config.ZONE_STORES
    (e.g. "skin" / "skill") to scan that zone's own stores."""
    import config
    stores = None
    if zone:
        stores = config.ZONE_STORES.get(zone)
        if stores is None:
            raise HTTPException(status_code=404, detail=f"ไม่รู้จักโซน: {zone}")
    return {"projects": scan_projects(stores)}


class OpenFolderRequest(BaseModel):
    path: str


@router.post("/projects/open-folder")
def open_folder(req: OpenFolderRequest):
    p = Path(req.path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบพาธ: {req.path}")
    target = p if p.is_dir() else p.parent
    try:
        os.startfile(str(target))  # Windows; unicode-safe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"opened": str(target)}


class PackRequest(BaseModel):
    name: str
    bp_path: str | None = None
    rp_path: str | None = None
    output_dir: str | None = None


@router.post("/projects/export")
def export_mcaddon(req: PackRequest):
    try:
        out = ops.make_mcaddon(req.name, req.bp_path, req.rp_path, req.output_dir)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"mcaddon": out}


class ImportRequest(BaseModel):
    mcaddon_path: str
    dest_store: str | None = None


@router.post("/projects/import")
def import_mcaddon(req: ImportRequest):
    try:
        return ops.import_mcaddon(req.mcaddon_path, req.dest_store)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deploy/status")
def deploy_status():
    return ops.deploy_status()


class DeployRequest(BaseModel):
    bp_path: str | None = None
    rp_path: str | None = None


@router.post("/projects/deploy")
def deploy(req: DeployRequest):
    try:
        return ops.deploy_project(req.bp_path, req.rp_path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class InfoRequest(BaseModel):
    paths: Dict[str, str]


@router.post("/projects/info")
def info(req: InfoRequest):
    return manage.project_info(req.paths)


@router.get("/projects/thumbnail")
def thumbnail(bp: str | None = None, rp: str | None = None, folder: str | None = None):
    icon = manage.find_icon({"bp": bp, "rp": rp, "folder": folder})
    if not icon or not manage._under_stores(Path(icon)):
        raise HTTPException(status_code=404, detail="ไม่พบ icon")
    return FileResponse(icon)


class DeleteRequest(BaseModel):
    paths: List[str]


@router.post("/projects/delete")
def delete(req: DeleteRequest):
    try:
        return manage.delete_project(req.paths)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RenameRequest(BaseModel):
    paths: Dict[str, str]
    new_name: str


@router.post("/projects/rename")
def rename(req: RenameRequest):
    try:
        return manage.rename_project(req.paths, req.new_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/duplicate")
def duplicate(req: RenameRequest):
    try:
        return manage.duplicate_project(req.paths, req.new_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cleanup/scan")
def cleanup_scan():
    candidates = cleanup.find_junk()
    return {"candidates": candidates, "total_bytes": cleanup.total_size(candidates)}
