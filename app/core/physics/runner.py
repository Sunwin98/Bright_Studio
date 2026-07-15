"""Dispatch, dry-run bone discovery, timestamped backups, and JSON validation
around the five physics generators.

Each generator edits the animation (+ optional attachable) JSON in place, so we
copy a `.bak-<timestamp>` of every target before saving and re-parse afterwards
to guarantee we never leave a commission file corrupted.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
from datetime import datetime

from app.core.physics.back_hair import BackHairPhysicsGeneratorV2
from app.core.physics.back_hair_yaw import BackHairYawOnlyGenerator
from app.core.physics.cape import CapePhysicsGenerator
from app.core.physics.chest import ChestPhysicsGenerator
from app.core.physics.front_hair import FrontHairPhysicsGenerator
from app.core.physics.head import HeadRotationGenerator
from app.core import history

# tool -> metadata. bone_source: where bones are discovered for dry-run.
TOOLS = {
    "back_hair": {
        "cls": BackHairPhysicsGeneratorV2, "label": "ผมหลัง (Wave + Yaw + Pitch)",
        "bone_source": "model", "needs_attachable": True, "mode": "prefix_strength",
    },
    "back_hair_yaw": {
        "cls": BackHairYawOnlyGenerator, "label": "ผมหลัง (Yaw only, ไม่มี wave)",
        "bone_source": "model", "needs_attachable": True, "mode": "prefix_strength",
    },
    "cape": {
        "cls": CapePhysicsGenerator, "label": "ผ้าคลุม/เสื้อผ้า (Cape)",
        "bone_source": "animation", "needs_attachable": False, "mode": "prefix_intensity",
    },
    "chest": {
        "cls": ChestPhysicsGenerator, "label": "หน้าอก/เกราะ (Spring-Damping)",
        "bone_source": "animation", "needs_attachable": False, "mode": "prefix",
    },
    "front_hair": {
        "cls": FrontHairPhysicsGenerator, "label": "ผมหน้า (Front Hair)",
        "bone_source": "animation", "needs_attachable": False, "mode": "prefix",
    },
    "head": {
        "cls": HeadRotationGenerator, "label": "หัว/คอเอียง + Smooth Head",
        "bone_source": "none", "needs_attachable": False, "mode": "bone_name",
    },
}


def list_tools() -> list[dict]:
    return [
        {"id": k, "label": v["label"], "bone_source": v["bone_source"],
         "needs_attachable": v["needs_attachable"], "mode": v["mode"]}
        for k, v in TOOLS.items()
    ]


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_bones(tool: str, animation_path: str, model_path: str | None, prefixes: list[str]) -> dict:
    """Dry-run: return {prefix: [bone,...]} without modifying anything."""
    meta = TOOLS.get(tool)
    if not meta:
        raise ValueError(f"ไม่รู้จักเครื่องมือ: {tool}")
    if meta["bone_source"] == "none":
        return {}

    gen = meta["cls"]()
    if meta["bone_source"] == "model":
        if not model_path or not os.path.exists(model_path):
            raise ValueError("ต้องระบุไฟล์ Model (.geo.json)")
        gen.model_data = _load_json(model_path)
    else:  # animation
        if not animation_path or not os.path.exists(animation_path):
            raise ValueError("ต้องระบุไฟล์ Animation (.json)")
        gen.animation_data = _load_json(animation_path)

    result = {}
    for prefix in prefixes:
        prefix = prefix.strip()
        if not prefix:
            continue
        result[prefix] = gen.find_bones_with_prefix(prefix)
    return result


def _backup(path: str, stamp: str) -> str:
    bak = f"{path}.bak-{stamp}"
    shutil.copy2(path, bak)
    return bak


def apply(payload: dict) -> dict:
    tool = payload.get("tool")
    meta = TOOLS.get(tool)
    if not meta:
        raise ValueError(f"ไม่รู้จักเครื่องมือ: {tool}")

    animation_path = payload.get("animation_path")
    model_path = payload.get("model_path")
    attachable_path = payload.get("attachable_path") or None
    prefixes = [p.strip() for p in (payload.get("prefixes") or []) if p and p.strip()]
    bone_name = (payload.get("bone_name") or "").strip()
    bone_groups_payload = payload.get("bone_groups") or []

    if not animation_path or not os.path.exists(animation_path):
        raise ValueError("ไม่พบไฟล์ Animation")
    if meta["needs_attachable"] and (not attachable_path or not os.path.exists(attachable_path)):
        raise ValueError("เครื่องมือนี้ต้องมีไฟล์ Attachable")
    if meta["bone_source"] == "model" and (not model_path or not os.path.exists(model_path)):
        raise ValueError("เครื่องมือนี้ต้องมีไฟล์ Model (.geo.json)")
    if meta["mode"] != "bone_name" and not prefixes and not bone_groups_payload:
        raise ValueError("ต้องระบุ bone prefix หรือ bone groups อย่างน้อย 1 ตัว")
    if meta["mode"] == "bone_name" and not bone_name:
        raise ValueError("ต้องระบุชื่อ bone")

    history_snapshot = history.create_snapshot(
        "แก้ไขฟิสิกส์",
        [path for path in (animation_path, attachable_path) if path],
        source=payload.get("source_path") or animation_path,
        status="กำลังแก้ไข",
    )
    history_id = history_snapshot["id"]

    # backups (before any write)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backups = [_backup(animation_path, stamp)]
    if attachable_path and os.path.exists(attachable_path):
        backups.append(_backup(attachable_path, stamp))

    gen = meta["cls"]()
    buf = io.StringIO()
    exported_path = None
    with contextlib.redirect_stdout(buf):
        _run_tool(tool, meta, gen, animation_path, model_path, attachable_path, prefixes, bone_name, payload)
        
        # Repackage if source_path is provided and is an archive
        source_path = payload.get("source_path")
        if source_path:
            from pathlib import Path
            import zipfile
            src = Path(source_path)
            if src.suffix.lower() in {".mcaddon", ".mcpack", ".zip"} and src.is_file():
                anim_p = Path(animation_path)
                try:
                    parts = anim_p.parts
                    if "hs_studio_packio" in parts:
                        idx = parts.index("hs_studio_packio")
                        temp_root = Path(*parts[:idx + 2])
                        new_name = f"{src.stem}_physics{src.suffix}"
                        new_path = src.parent / new_name
                        
                        with zipfile.ZipFile(new_path, "w", zipfile.ZIP_DEFLATED) as zf:
                            for f in temp_root.rglob("*"):
                                if f.is_file():
                                    zf.write(f, f.relative_to(temp_root))
                        
                        print(f"📦 สร้างและส่งออกแอดออนใหม่ที่มีฟิสิกส์สำเร็จแล้วที่: {new_path}")
                        exported_path = str(new_path)
                except Exception as e:
                    print(f"⚠️ ไม่สามารถส่งออกไฟล์แอดออนใหม่ได้: {e}")

    # validate the files still parse
    _load_json(animation_path)
    if attachable_path and os.path.exists(attachable_path):
        _load_json(attachable_path)

    log = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    history.update_snapshot(history_id, changed=[animation_path] + ([attachable_path] if attachable_path else []), status="completed")
    return {"log": log, "backups": backups, "exported_path": exported_path, "history_id": history_id}


def _run_tool(tool, meta, gen, animation_path, model_path, attachable_path, prefixes, bone_name, payload):
    bone_groups_payload = payload.get("bone_groups") or []

    if tool in ("back_hair", "back_hair_yaw"):
        gen.load_files(animation_path, model_path, attachable_path)
        strength = payload.get("strength")  # None -> auto
        if bone_groups_payload:
            for bg in bone_groups_payload:
                prefix = bg.get("prefix")
                bones = bg.get("bones") or []
                if not bones:
                    continue
                gen.bone_groups.append({"prefix": prefix, "bones": bones, "strength_multiplier": strength})
        else:
            for prefix in prefixes:
                bones = gen.find_bones_with_prefix(prefix)
                if not bones:
                    print(f"⚠️ ไม่พบ bones สำหรับ '{prefix}' ใน Model - ข้าม")
                    continue
                gen.bone_groups.append({"prefix": prefix, "bones": bones, "strength_multiplier": strength})
        anim_refs = gen.update_animation_file()
        gen.update_attachable_file(anim_refs)
        gen.save_files()

    elif tool == "cape":
        gen.load_files(animation_path, attachable_path)
        gen.cape_intensity = payload.get("intensity", "medium")
        if bone_groups_payload:
            for bg in bone_groups_payload:
                prefix = bg.get("prefix")
                bones = bg.get("bones") or []
                if not bones:
                    continue
                gen.bone_groups.append({"prefix": prefix, "bones": bones})
        else:
            for prefix in prefixes:
                bones = gen.find_bones_with_prefix(prefix)
                if not bones:
                    print(f"⚠️ ไม่พบ bones สำหรับ '{prefix}' - ข้าม")
                    continue
                gen.bone_groups.append({"prefix": prefix, "bones": bones})
        anim_refs = gen.update_animation_file()
        if attachable_path:
            gen.update_attachable_file(anim_refs)
        gen.save_files()

    elif tool in ("chest", "front_hair"):
        gen.load_files(animation_path, attachable_path)
        if bone_groups_payload:
            for bg in bone_groups_payload:
                prefix = bg.get("prefix")
                bones = bg.get("bones") or []
                if not bones:
                    continue
                gen.bone_groups.append({"prefix": prefix, "bones": bones})
        else:
            for prefix in prefixes:
                bones = gen.find_bones_with_prefix(prefix)
                if not bones:
                    print(f"⚠️ ไม่พบ bones สำหรับ '{prefix}' - ข้าม")
                    continue
                gen.bone_groups.append({"prefix": prefix, "bones": bones})
        anim_refs = gen.update_animation_file()
        if attachable_path:
            gen.update_attachable_file(anim_refs)
        gen.save_files()

    elif tool == "head":
        gen.load_files(animation_path, attachable_path)
        gen.head_bone_name = bone_name
        head_anim, smooth_anim = gen.update_animation_file()
        if attachable_path:
            gen.update_attachable_file(head_anim, smooth_anim)
        gen.save_files()
