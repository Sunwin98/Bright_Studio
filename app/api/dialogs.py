"""Native file/folder pickers via the pywebview window.

run.py sets `window` after the webview window is created. When the studio runs
in a plain browser (dev mode) the window is None, so /api/dialog returns 501 and
the frontend falls back to a manual path text box.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["dialogs"])

# Set by run.py once the webview window exists.
window = None


def set_window(win) -> None:
    global window
    window = win


class DialogRequest(BaseModel):
    mode: str = "open_file"          # open_file | open_files | folder | save
    directory: str | None = None      # start directory
    filters: list[str] | None = None  # e.g. ["Images (*.png)"]
    save_filename: str | None = None


@router.post("/dialog")
def open_dialog(req: DialogRequest):
    if window is None:
        raise HTTPException(status_code=501, detail="native dialog unavailable (browser mode)")

    import webview

    dialog_map = {
        "open_file": webview.OPEN_DIALOG,
        "open_files": webview.OPEN_DIALOG,
        "folder": webview.FOLDER_DIALOG,
        "save": webview.SAVE_DIALOG,
    }
    dtype = dialog_map.get(req.mode, webview.OPEN_DIALOG)
    allow_multiple = req.mode == "open_files"

    start_dir = ""
    if req.directory and os.path.isdir(req.directory):
        start_dir = req.directory

    result = window.create_file_dialog(
        dtype,
        directory=start_dir,
        allow_multiple=allow_multiple,
        file_types=tuple(req.filters) if req.filters else (),
        save_filename=req.save_filename or "",
    )

    if not result:
        return {"paths": []}
    paths = list(result) if isinstance(result, (list, tuple)) else [result]
    return {"paths": [str(Path(p)) for p in paths]}


from fastapi import UploadFile, File
import shutil
import tempfile

@router.post("/dialog/upload")
def upload_file(file: UploadFile = File(...)):
    temp_dir = Path(tempfile.gettempdir()) / "bright_studio_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = temp_dir / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"path": str(file_path)}


from fastapi.responses import FileResponse

@router.get("/dialog/download")
def download_file(path: str):
    p = Path(path)
    if not p.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(p, filename=p.name)

