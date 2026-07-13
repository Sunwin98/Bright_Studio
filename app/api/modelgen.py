"""Model-gen API — Meshy image/text → 3D → Bedrock geo.json + texture."""
from __future__ import annotations

import re
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import config
from app.core.modelgen import meshy
from app.core.modelgen.obj_to_geo import convert_obj_to_geo, write_geo

router = APIRouter(prefix="/api/modelgen", tags=["modelgen"])

# Hosts the asset proxy may fetch from (Meshy presigned asset URLs).
_PROXY_HOSTS = (".meshy.ai",)


def _run(fn):
    try:
        return fn()
    except meshy.MeshyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/config")
def get_config():
    k = config.MESHY_API_KEY or ""
    return {"has_key": bool(k), "key_masked": (k[:7] + "…" + k[-3:]) if len(k) > 12 else ""}


class KeyBody(BaseModel):
    key: str


@router.post("/key")
def set_key(body: KeyBody):
    config.set_meshy_key(body.key)
    return {"ok": True, "has_key": bool(config.MESHY_API_KEY)}


class ImageBody(BaseModel):
    image_path: str
    target_polycount: int = 4000
    should_texture: bool = True
    enable_pbr: bool = False


@router.post("/image")
def gen_image(body: ImageBody):
    tid = _run(lambda: meshy.create_image_task(
        body.image_path, body.target_polycount, body.should_texture, body.enable_pbr))
    return {"task_id": tid, "mode": "image", "phase": "final"}


class TextBody(BaseModel):
    prompt: str
    art_style: str = "realistic"
    target_polycount: int = 4000


@router.post("/text")
def gen_text(body: TextBody):
    if not body.prompt.strip():
        raise HTTPException(status_code=422, detail="ต้องใส่คำอธิบายโมเดล (prompt)")
    tid = _run(lambda: meshy.create_text_preview(
        body.prompt.strip(), body.art_style, body.target_polycount))
    return {"task_id": tid, "mode": "text", "phase": "preview"}


class RefineBody(BaseModel):
    preview_task_id: str
    enable_pbr: bool = False


@router.post("/text-refine")
def gen_text_refine(body: RefineBody):
    tid = _run(lambda: meshy.create_text_refine(body.preview_task_id, body.enable_pbr))
    return {"task_id": tid, "mode": "text", "phase": "refine"}


@router.get("/status")
def status(mode: str = Query(...), task_id: str = Query(...)):
    if mode not in ("image", "text"):
        raise HTTPException(status_code=422, detail="mode ต้องเป็น image หรือ text")
    task = _run(lambda: meshy.get_task(mode, task_id))
    return meshy.summarize(task)


@router.get("/recent")
def recent():
    """งานล่าสุดจาก Meshy (ทั้ง image และ text) — เปิดซ้ำ/re-export ได้ ไม่เสียเครดิต"""
    def do():
        out = []
        for mode in ("image", "text"):
            try:
                for t in meshy.list_tasks(mode, 8):
                    s = meshy.summarize(t)
                    out.append({
                        "mode": mode,
                        "task_id": t.get("id"),
                        "prompt": (t.get("prompt") or "")[:80],
                        "created_at": t.get("created_at"),
                        **s,
                    })
            except meshy.MeshyError:
                continue
        out.sort(key=lambda x: x.get("created_at") or 0, reverse=True)
        return {"tasks": [t for t in out if t.get("task_id")][:16]}
    return _run(do)


@router.get("/proxy")
def proxy(url: str = Query(...)):
    """Stream a Meshy asset (glb/thumbnail/texture) through the backend so the
    in-app 3D viewer never hits CORS/CSP walls. Meshy hosts only."""
    host = urllib.parse.urlparse(url).hostname or ""
    if not (url.startswith("https://") and any(host == h.lstrip(".") or host.endswith(h) for h in _PROXY_HOSTS)):
        raise HTTPException(status_code=400, detail="proxy เฉพาะไฟล์จาก meshy.ai เท่านั้น")
    try:
        req = urllib.request.Request(url)
        r = urllib.request.urlopen(req, timeout=120)  # noqa: S310 — host allow-listed above
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ดึงไฟล์ไม่ได้: {e}")
    ctype = r.headers.get("Content-Type", "application/octet-stream")

    def gen():
        try:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                yield chunk
        finally:
            r.close()

    return StreamingResponse(gen(), media_type=ctype)


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9_]+", "_", name.strip().lower()).strip("_")
    return s or "ai_model"


def _texture_size(png_path: Path) -> tuple[int, int]:
    try:
        from PIL import Image
        with Image.open(png_path) as im:
            return im.size
    except Exception:
        return (1024, 1024)


class ExportBody(BaseModel):
    mode: str
    task_id: str
    name: str
    output_dir: str | None = None
    target_size: float = 16.0
    face_forward: bool = True


@router.post("/export")
def export(body: ExportBody):
    def do():
        task = meshy.get_task(body.mode, body.task_id)
        if task.get("status") != "SUCCEEDED":
            raise ValueError("โมเดลยังไม่เสร็จ (ต้องรอ SUCCEEDED ก่อน export)")
        model_urls = task.get("model_urls") or {}
        obj_url = model_urls.get("obj")
        if not obj_url:
            raise ValueError("Meshy ไม่มีไฟล์ OBJ ให้ export")

        out_dir = Path(body.output_dir) if body.output_dir else (config.DEFAULT_OUTPUT_DIR / "ai_models")
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = _slug(body.name)

        with tempfile.TemporaryDirectory() as td:
            obj_tmp = meshy.download(obj_url, Path(td) / "model.obj")
            obj_text = obj_tmp.read_text(encoding="utf-8", errors="replace")

            # texture (base_color) — optional
            tex_w, tex_h = 16, 16
            tex_out = None
            textures = task.get("texture_urls") or []
            base_color = None
            if textures and isinstance(textures[0], dict):
                base_color = textures[0].get("base_color")
            if base_color:
                tex_out = out_dir / f"{slug}.png"
                meshy.download(base_color, tex_out)
                tex_w, tex_h = _texture_size(tex_out)

            geo = convert_obj_to_geo(
                obj_text, slug, texture_width=tex_w, texture_height=tex_h,
                target_size=body.target_size, face_forward=body.face_forward)

        geo_path = out_dir / f"{slug}.geo.json"
        write_geo(geo, geo_path)

        # inventory icon = Meshy's rendered thumbnail (used when turning into an item)
        icon_out = None
        thumb = task.get("thumbnail_url")
        if thumb:
            try:
                icon_out = out_dir / f"{slug}_icon.png"
                meshy.download(thumb, icon_out)
            except Exception:
                icon_out = None

        return {
            "ok": True,
            "geo_path": str(geo_path),
            "texture_path": str(tex_out) if tex_out else None,
            "icon_path": str(icon_out) if icon_out else None,
            "identifier": f"geometry.{slug}",
            "slug": slug,
            "output_dir": str(out_dir),
            "polys": len(geo["minecraft:geometry"][0]["bones"][0]["poly_mesh"]["polys"]),
        }

    return _run(do)


class MakeItemBody(BaseModel):
    geo_path: str
    texture_path: str | None = None
    icon_path: str | None = None
    namespace: str = "ai"
    item_name: str
    display_name: str = ""
    addon_name: str = ""
    bp_path: str | None = None
    rp_path: str | None = None
    output_dir: str | None = None
    menu_category: str = "equipment"


@router.post("/make-item")
def make_item(body: MakeItemBody):
    """Turn an exported AI model (geo.json + texture) into a ready-to-use held
    item: BP item + RP attachable + geometry wired + give command."""
    from app.core.weapon import item_builder

    tex = body.texture_path
    if not tex or not Path(tex).is_file():
        raise HTTPException(status_code=422,
                            detail="โมเดลนี้ไม่มี texture — ทำเป็นไอเทมไม่ได้ (ลองสร้างใหม่แบบมีเท็กซ์เจอร์)")
    icon = body.icon_path if (body.icon_path and Path(body.icon_path).is_file()) else tex

    req = {
        "model_path": body.geo_path,
        "model_texture_path": tex,
        "icon_path": icon,
        "namespace": body.namespace,
        "item_name": body.item_name,
        "display_name": body.display_name or body.item_name,
        "addon_name": body.addon_name or body.item_name,
        "bp_path": body.bp_path or None,
        "rp_path": body.rp_path or None,
        "output_dir": body.output_dir or None,
        "menu_category": body.menu_category,
    }
    return _run(lambda: item_builder.build_item(req))

    return _run(do)
