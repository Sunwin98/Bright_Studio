"""Weapon/item creator: add a held item to existing BP+RP packs and auto-wire it
to a custom model through an attachable.

The key automation: the model's geometry identifier is read straight from the
.geo.json and written into the attachable's geometry.default, so the item ↔ model
link is never mistyped (identifiers rarely match the filename — e.g. a file named
soen_sword.geo.json can hold "geometry.rento2").
"""
from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from typing import List

import config


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_]", "_", s.strip().lower())
    return re.sub(r"_+", "_", s).strip("_")


def create_addon_skeleton(output_dir: str, addon_name: str) -> tuple[str, str, str]:
    """Create a fresh <name>/<name>_BP + <name>_RP with manifests (BP depends on RP).
    Returns (project_dir, bp_path, rp_path)."""
    safe = _slug(addon_name) or f"addon_{uuid.uuid4().hex[:6]}"
    base = os.path.join(output_dir, safe)
    bp = os.path.join(base, f"{safe}_BP")
    rp = os.path.join(base, f"{safe}_RP")
    os.makedirs(bp, exist_ok=True)
    os.makedirs(rp, exist_ok=True)

    rp_uuid = str(uuid.uuid4())
    rp_manifest = {
        "format_version": 2,
        "header": {"name": f"{addon_name} RP", "description": addon_name,
                   "uuid": rp_uuid, "version": [1, 0, 0], "min_engine_version": [1, 21, 0]},
        "modules": [{"type": "resources", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]}],
    }
    bp_manifest = {
        "format_version": 2,
        "header": {"name": f"{addon_name} BP", "description": addon_name,
                   "uuid": str(uuid.uuid4()), "version": [1, 0, 0], "min_engine_version": [1, 21, 0]},
        "modules": [{"type": "data", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]}],
        "dependencies": [{"uuid": rp_uuid, "version": [1, 0, 0]}],
    }
    with open(os.path.join(rp, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(rp_manifest, f, indent=2, ensure_ascii=False)
    with open(os.path.join(bp, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(bp_manifest, f, indent=2, ensure_ascii=False)

    # pack icons (best-effort from master assets)
    src_icon = config.MASTER_ASSETS / "pack_icon.png"
    if src_icon.exists():
        for pack in (bp, rp):
            try:
                shutil.copy2(src_icon, os.path.join(pack, "pack_icon.png"))
            except OSError:
                pass
    return base, bp, rp


def read_geometry_id(model_path: str) -> str:
    with open(model_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    geos = data.get("minecraft:geometry")
    if not geos:
        raise ValueError("ไฟล์โมเดลไม่มี 'minecraft:geometry'")
    ident = geos[0].get("description", {}).get("identifier")
    if not ident:
        raise ValueError("อ่าน geometry identifier จากโมเดลไม่ได้")
    return ident


def _merge_item_texture(rp_path: str, icon_key: str, texture_ref: str) -> None:
    path = os.path.join(rp_path, "textures", "item_texture.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"resource_pack_name": "vanilla", "texture_name": "atlas.items", "texture_data": {}}
    data.setdefault("texture_data", {})[icon_key] = {"textures": texture_ref}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _append_lang(pack_path: str, line: str) -> None:
    texts = os.path.join(pack_path, "texts")
    os.makedirs(texts, exist_ok=True)
    lang = os.path.join(texts, "en_US.lang")
    existing = ""
    if os.path.exists(lang):
        with open(lang, "r", encoding="utf-8") as f:
            existing = f.read()
    if line in existing:
        return
    with open(lang, "a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(line + "\n")


def build_item(req: dict) -> dict:
    log: List[str] = []
    project_path = None

    bp = req.get("bp_path")
    rp = req.get("rp_path")

    # Create a brand-new addon (BP+RP+manifests) when packs aren't provided.
    if not bp or not rp:
        addon_name = (req.get("addon_name") or req.get("display_name") or req.get("item_name") or "").strip()
        if not addon_name:
            raise ValueError("ต้องระบุชื่อ Add-on (สำหรับสร้างแอดออนใหม่)")
        output_dir = req.get("output_dir") or str(config.DEFAULT_OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        project_path, bp, rp = create_addon_skeleton(output_dir, addon_name)
        log.append(f"📦 สร้างแอดออนใหม่: {os.path.basename(project_path)} (BP+RP+manifest)")
    else:
        if not os.path.exists(os.path.join(bp, "manifest.json")):
            raise ValueError("โฟลเดอร์ BP ไม่ถูกต้อง (ไม่พบ manifest.json)")
        if not os.path.exists(os.path.join(rp, "manifest.json")):
            raise ValueError("โฟลเดอร์ RP ไม่ถูกต้อง (ไม่พบ manifest.json)")

    namespace = _slug(req.get("namespace") or "")
    name = _slug(req.get("item_name") or "")
    if not namespace or not name:
        raise ValueError("ต้องระบุ namespace และชื่อไอเทม (a-z, 0-9, _)")
    identifier = f"{namespace}:{name}"
    file_base = f"{namespace}_{name}"
    icon_key = file_base

    model_path = req.get("model_path")
    model_texture = req.get("model_texture_path")
    icon_path = req.get("icon_path")
    if not model_path or not os.path.exists(model_path):
        raise ValueError("ต้องระบุไฟล์โมเดล (.geo.json)")
    if not model_texture or not os.path.exists(model_texture):
        raise ValueError("ต้องระบุ texture ของโมเดล (.png)")
    if not icon_path or not os.path.exists(icon_path):
        raise ValueError("ต้องระบุ icon ของไอเทม (.png)")

    # auto-connect: geometry id straight from the model file
    geometry_id = read_geometry_id(model_path)
    log.append(f"🔗 อ่าน geometry: {geometry_id}")

    display_name = (req.get("display_name") or name).strip()

    # ── RP: model ─────────────────────────────────────────────────────────────
    models_dir = os.path.join(rp, "models", "entity", "attachable")
    os.makedirs(models_dir, exist_ok=True)
    shutil.copy2(model_path, os.path.join(models_dir, f"{file_base}.geo.json"))

    # RP: model texture
    mtex_dir = os.path.join(rp, "textures", "entity", "attachable")
    os.makedirs(mtex_dir, exist_ok=True)
    shutil.copy2(model_texture, os.path.join(mtex_dir, f"{file_base}.png"))
    model_tex_ref = f"textures/entity/attachable/{file_base}"

    # RP: inventory icon + item_texture
    icon_dir = os.path.join(rp, "textures", "items")
    os.makedirs(icon_dir, exist_ok=True)
    shutil.copy2(icon_path, os.path.join(icon_dir, f"{file_base}icon.png"))
    _merge_item_texture(rp, icon_key, f"textures/items/{file_base}icon")
    log.append("🖼️ คัดลอกโมเดล + texture + icon และลง item_texture.json")

    # optional held animation
    anim_defs = {}
    anim_scripts = []
    anim_path = req.get("held_animation_path")
    if anim_path and os.path.exists(anim_path):
        anims_dir = os.path.join(rp, "animations")
        os.makedirs(anims_dir, exist_ok=True)
        shutil.copy2(anim_path, os.path.join(anims_dir, f"{file_base}.animation.json"))
        try:
            with open(anim_path, "r", encoding="utf-8") as f:
                names = list(json.load(f).get("animations", {}).keys())
            for i, n in enumerate(names):
                key = f"anim_{i}"
                anim_defs[key] = n
                anim_scripts.append(key)
            log.append(f"🎞️ ผูก animation {len(names)} ตัว")
        except Exception:
            pass

    # ── RP: attachable (auto-wired) ───────────────────────────────────────────
    desc = {
        "identifier": identifier,
        "materials": {"default": "entity_alphatest", "enchanted": "entity_alphatest_glint"},
        "textures": {"default": model_tex_ref, "enchanted": "textures/misc/enchanted_item_glint"},
        "geometry": {"default": geometry_id},
        "render_controllers": ["controller.render.item_default"],
    }
    if anim_defs:
        desc["animations"] = anim_defs
        desc["scripts"] = {"animate": anim_scripts}
    attachable = {"format_version": "1.10.0", "minecraft:attachable": {"description": desc}}
    att_dir = os.path.join(rp, "attachables")
    os.makedirs(att_dir, exist_ok=True)
    att_path = os.path.join(att_dir, f"{file_base}.json")
    with open(att_path, "w", encoding="utf-8") as f:
        json.dump(attachable, f, indent=2, ensure_ascii=False)
    log.append("🔗 สร้าง attachable เชื่อม item → model อัตโนมัติ")

    # ── BP: item ──────────────────────────────────────────────────────────────
    components = {
        "minecraft:max_stack_size": 1,
        "minecraft:display_name": {"value": display_name},
        "minecraft:icon": icon_key,
    }
    if req.get("damage") is not None:
        components["minecraft:damage"] = int(req["damage"])
    if req.get("enchantable_slot"):
        components["minecraft:enchantable"] = {
            "slot": req["enchantable_slot"], "value": int(req.get("enchantable_value") or 10)}
    if req.get("cooldown_seconds"):
        components["minecraft:cooldown"] = {
            "category": file_base, "duration": float(req["cooldown_seconds"])}
    item = {
        "format_version": "1.20.50",
        "minecraft:item": {
            "description": {
                "identifier": identifier,
                "menu_category": {"category": req.get("menu_category") or "equipment"},
            },
            "components": components,
        },
    }
    items_dir = os.path.join(bp, "items")
    os.makedirs(items_dir, exist_ok=True)
    item_path = os.path.join(items_dir, f"{file_base}.json")
    with open(item_path, "w", encoding="utf-8") as f:
        json.dump(item, f, indent=2, ensure_ascii=False)
    log.append("⚔️ สร้าง item ใน BP")

    _append_lang(bp, f"item.{identifier}.name={display_name}")

    log.append("🎉 สำเร็จ")
    return {
        "log": log,
        "identifier": identifier,
        "geometry_id": geometry_id,
        "project_path": project_path,
        "bp_path": bp,
        "rp_path": rp,
        "item_path": item_path,
        "attachable_path": att_path,
        "give_command": f"/give @s {identifier}",
    }
