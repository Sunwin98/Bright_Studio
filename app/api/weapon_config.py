"""API for the replacement Weapon Config Studio workspace."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core import weapon_config

router = APIRouter(prefix="/api/weapon-config", tags=["weapon-config"])


class AnalyzeRequest(BaseModel):
    source_path: str


class ScriptRequest(BaseModel):
    path: str
    max_lines: int = 300


class Edit(BaseModel):
    path: str
    start: int
    end: int
    original: str
    value: Any


class SaveRequest(BaseModel):
    edits: list[Edit]


class ExportRequest(BaseModel):
    source_path: str
    output_path: str | None = None


def _run(action):
    try:
        return action()
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Weapon Config Studio: {type(exc).__name__}: {exc}") from exc


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    return _run(lambda: weapon_config.analyze_source(req.source_path))


@router.post("/script")
def script(req: ScriptRequest):
    return _run(lambda: weapon_config.read_script(req.path, req.max_lines))


@router.post("/save")
def save(req: SaveRequest):
    return _run(lambda: weapon_config.apply_edits([item.model_dump() for item in req.edits]))


@router.post("/export")
def export(req: ExportRequest):
    return _run(lambda: weapon_config.export_addon(req.source_path, req.output_path))
