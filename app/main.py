"""FastAPI app for Heaven Send Studio.

Serves the SPA from /web and mounts one router per tool. Routers are added as
each phase lands; missing ones simply don't register (kept import-guarded so the
shell runs even before a tool is built).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import config
from app.api import dialogs

app = FastAPI(title="Heaven Send Studio")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(dialogs.router)

# Optional routers — register if the module exists (phased delivery).
# Only swallow the case where the router module itself is absent; a broken
# import *inside* a present router must surface, not be silently skipped.
import importlib.util

for _mod in ("projects", "knowledge", "skin", "physics", "weapon", "checker", "merger", "settings", "filemanager", "fsbrowse", "packio", "scriptlab"):
    if importlib.util.find_spec(f"app.api.{_mod}") is None:
        continue
    module = __import__(f"app.api.{_mod}", fromlist=["router"])
    app.include_router(module.router)


@app.get("/api/health")
def health():
    return {"ok": True, "app": "Heaven Send Studio"}


# Static SPA. Mounted last so /api/* wins.
app.mount("/", StaticFiles(directory=str(config.WEB_DIR), html=True), name="web")
