"""Thin Meshy API client (https://docs.meshy.ai). Pure stdlib (urllib).

Endpoints used:
  POST /openapi/v1/image-to-3d          create an image->3d task (textured, 1 call)
  POST /openapi/v2/text-to-3d           create a text->3d task (preview / refine)
  GET  /openapi/v1/image-to-3d/{id}     poll
  GET  /openapi/v2/text-to-3d/{id}      poll

Auth: Authorization: Bearer <api key>.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import urllib.error
import urllib.request
from pathlib import Path

import config

BASE = "https://api.meshy.ai"
_IMAGE = "/openapi/v1/image-to-3d"
_TEXT = "/openapi/v2/text-to-3d"


class MeshyError(Exception):
    pass


def _key() -> str:
    k = (config.MESHY_API_KEY or "").strip()
    if not k:
        raise MeshyError("ยังไม่ได้ตั้งค่า Meshy API key (ไปที่ตั้งค่า หรือกรอกในหน้าโมเดล)")
    return k


def _request(method: str, path: str, body: dict | None = None, timeout: int = 60) -> dict:
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + _key())
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("message", detail)
        except Exception:
            pass
        if e.code in (401, 403):
            raise MeshyError("API key ไม่ถูกต้อง หรือหมดสิทธิ์ (401/403)")
        if e.code == 402:
            raise MeshyError("เครดิต Meshy ไม่พอ (402)")
        raise MeshyError(f"Meshy error {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise MeshyError(f"ต่อ Meshy ไม่ได้: {e.reason}")


# ---- create tasks --------------------------------------------------------

def _image_to_data_uri(image_path: str) -> str:
    p = Path(image_path)
    if not p.is_file():
        raise MeshyError(f"ไม่พบไฟล์ภาพ: {image_path}")
    mime = mimetypes.guess_type(str(p))[0] or "image/png"
    if mime not in ("image/png", "image/jpeg", "image/jpg"):
        raise MeshyError("รองรับเฉพาะภาพ .png / .jpg")
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def create_image_task(image_path: str, target_polycount: int = 4000,
                      should_texture: bool = True, enable_pbr: bool = False,
                      ai_model: str = "latest") -> str:
    body = {
        "image_url": _image_to_data_uri(image_path),
        "ai_model": ai_model,
        "topology": "triangle",
        "target_polycount": int(target_polycount),
        "should_texture": bool(should_texture),
        "enable_pbr": bool(enable_pbr),
        "should_remesh": True,
    }
    r = _request("POST", _IMAGE, body)
    tid = r.get("result") or r.get("id")
    if not tid:
        raise MeshyError(f"Meshy ไม่คืน task id: {r}")
    return tid


def create_text_preview(prompt: str, art_style: str = "realistic",
                        target_polycount: int = 4000, ai_model: str = "latest") -> str:
    body = {
        "mode": "preview",
        "prompt": prompt,
        "art_style": art_style,
        "ai_model": ai_model,
        "topology": "triangle",
        "target_polycount": int(target_polycount),
        "should_remesh": True,
    }
    r = _request("POST", _TEXT, body)
    tid = r.get("result") or r.get("id")
    if not tid:
        raise MeshyError(f"Meshy ไม่คืน task id: {r}")
    return tid


def create_text_refine(preview_task_id: str, enable_pbr: bool = False) -> str:
    body = {"mode": "refine", "preview_task_id": preview_task_id, "enable_pbr": bool(enable_pbr)}
    r = _request("POST", _TEXT, body)
    tid = r.get("result") or r.get("id")
    if not tid:
        raise MeshyError(f"Meshy ไม่คืน task id: {r}")
    return tid


# ---- poll ----------------------------------------------------------------

def get_task(mode: str, task_id: str) -> dict:
    """mode: 'image' | 'text'. Returns the raw Meshy task object."""
    path = (_IMAGE if mode == "image" else _TEXT) + "/" + task_id
    return _request("GET", path)


def list_tasks(mode: str, page_size: int = 12) -> list[dict]:
    """Recent tasks (newest first) — lets the UI reopen/re-export past models
    without burning credits on a regeneration."""
    path = (_IMAGE if mode == "image" else _TEXT) + f"?page_size={int(page_size)}&sort_by=-created_at"
    r = _request("GET", path)
    if isinstance(r, list):
        return r
    return r.get("data") or r.get("result") or []


def summarize(task: dict) -> dict:
    """Trim a task object to what the UI needs."""
    return {
        "status": task.get("status"),
        "progress": task.get("progress", 0),
        "thumbnail_url": task.get("thumbnail_url"),
        "thumbnail_urls": task.get("thumbnail_urls"),
        "model_urls": task.get("model_urls", {}),
        "texture_urls": task.get("texture_urls", []),
        "task_error": (task.get("task_error") or {}).get("message"),
    }


# ---- download ------------------------------------------------------------

def download(url: str, dest: str | Path, timeout: int = 180) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r, open(dest, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
    except (urllib.error.URLError, OSError) as e:
        raise MeshyError(f"ดาวน์โหลดไฟล์ไม่ได้: {e}")
    return dest
