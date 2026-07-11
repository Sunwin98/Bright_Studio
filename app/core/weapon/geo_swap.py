"""Geo Swap (per SPEC-geo-swap-system.md): swap the player's geometry to one with
the weapon bone embedded while the item is held, so a single animation drives arm
+ weapon (no attachable rotation stacking).

Implementation is registry-driven and idempotent: every generate rewrites the
shared render controller and player.entity.json from the registry, so adding a
second weapon never clobbers the first, and regenerating the same weapon is a
no-op. RP files are written; a small standalone BP tag-driver script is optional.

All names derive from the item identifier (SPEC §4) so addons don't collide.
Note: player.entity.json is one-per-game — if another addon overrides the player
model, packs will fight by load order (unavoidable; surfaced as a warning).
"""
from __future__ import annotations

import json
import os
import re
import shutil
from typing import List

# Standard player bones — user bones must not collide with these (SPEC §8).
STANDARD_BONES = {
    "root", "body", "head", "hat", "rightarm", "leftarm", "rightitem", "leftitem",
    "rightsleeve", "leftsleeve", "rightleg", "leftleg", "rightpants", "leftpants",
    "jacket", "cape", "waist",
}

DEFAULT_PIVOTS = {
    "rightArm": [-5, 22, 0], "leftArm": [5, 22, 0],
    "body": [0, 24, 0], "head": [0, 24, 0],
}

# Minimal-but-valid humanoid fallback (replace with real vanilla player.geo for
# production — standard bone names kept so vanilla animations still apply).
FALLBACK_PLAYER_GEO = {
    "format_version": "1.12.0",
    "minecraft:geometry": [{
        "description": {
            "identifier": "geometry.humanoid.custom",
            "texture_width": 64, "texture_height": 64,
            "visible_bounds_width": 2, "visible_bounds_height": 3,
            "visible_bounds_offset": [0, 1.5, 0],
        },
        "bones": [
            {"name": "body", "pivot": [0, 24, 0], "cubes": [
                {"origin": [-4, 12, -2], "size": [8, 12, 4], "uv": [16, 16]}]},
            {"name": "waist", "neverRender": True, "pivot": [0, 12, 0]},
            {"name": "head", "parent": "body", "pivot": [0, 24, 0], "cubes": [
                {"origin": [-4, 24, -4], "size": [8, 8, 8], "uv": [0, 0]}]},
            {"name": "hat", "parent": "head", "pivot": [0, 24, 0], "cubes": [
                {"origin": [-4, 24, -4], "size": [8, 8, 8], "uv": [32, 0], "inflate": 0.5}]},
            {"name": "rightArm", "parent": "body", "pivot": [-5, 22, 0], "cubes": [
                {"origin": [-8, 12, -2], "size": [4, 12, 4], "uv": [40, 16]}]},
            {"name": "rightItem", "parent": "rightArm", "pivot": [-6, 15, 1], "neverRender": True},
            {"name": "leftArm", "parent": "body", "pivot": [5, 22, 0], "cubes": [
                {"origin": [4, 12, -2], "size": [4, 12, 4], "uv": [32, 48]}]},
            {"name": "rightLeg", "parent": "body", "pivot": [-1.9, 12, 0], "cubes": [
                {"origin": [-3.9, 0, -2], "size": [4, 12, 4], "uv": [0, 16]}]},
            {"name": "leftLeg", "parent": "body", "pivot": [1.9, 12, 0], "cubes": [
                {"origin": [-0.1, 0, -2], "size": [4, 12, 4], "uv": [16, 48]}]},
        ],
    }],
}

FALLBACK_PLAYER_ENTITY = {
    "format_version": "1.10.0",
    "minecraft:client_entity": {
        "description": {
            "identifier": "minecraft:player",
            "materials": {"default": "entity_alphatest", "cape": "entity_alphatest",
                          "animated": "player_animated"},
            "textures": {"default": "textures/entity/steve", "cape": "textures/entity/cape_invisible"},
            "geometry": {"default": "geometry.humanoid.custom", "cape": "geometry.cape"},
            "scripts": {"scale": "0.9375"},
            "render_controllers": [
                {"controller.render.player.third_person": "!variable.is_first_person"},
                {"controller.render.player.first_person": "variable.is_first_person && !variable.map_face_icon"},
                {"controller.render.player.map": "variable.map_face_icon"},
            ],
            "enable_attachables": True,
        }
    },
}


def _slug_id(identifier: str) -> str:
    return identifier.replace(":", "_")


def _valid_bone(name: str) -> bool:
    return bool(re.fullmatch(r"[a-zA-Z0-9_]+", name))


def parse_bones(bones_raw: List[str]) -> list[dict]:
    """['sword_edit', 'scabbard:body'] -> [{name,parent}] (default parent rightArm)."""
    out = []
    for entry in bones_raw:
        entry = entry.strip()
        if not entry:
            continue
        if ":" in entry:
            name, parent = entry.split(":", 1)
        else:
            name, parent = entry, "rightArm"
        name, parent = name.strip(), parent.strip()
        if not _valid_bone(name) or not _valid_bone(parent):
            raise ValueError(f"ชื่อ bone ไม่ถูกต้อง: {entry}")
        if name.lower() in STANDARD_BONES:
            raise ValueError(f"ชื่อ bone ชนกับ bone มาตรฐานของ player: {name}")
        out.append({"name": name, "parent": parent})
    return out


def _bone_object(bone: dict) -> dict:
    parent = bone["parent"]
    pivot = DEFAULT_PIVOTS.get(parent, [0, 0, 0])
    return {
        "name": bone["name"], "parent": parent, "pivot": pivot,
        "cubes": [{"origin": [pivot[0] - 1, pivot[1] - 12, -1], "size": [2, 12, 2], "uv": [0, 0]}],
    }


def _load_base_geo(base_player_geo_path: str | None) -> dict:
    if base_player_geo_path and os.path.exists(base_player_geo_path):
        with open(base_player_geo_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(json.dumps(FALLBACK_PLAYER_GEO))


def _read_json(p: str):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(p: str, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _build_controller(registry: dict) -> dict:
    """Nested ternary picking the swap geometry per active tag, ending Geometry.default."""
    items = registry.get("items", {})
    expr = "Geometry.default"
    for entry in reversed(list(items.values())):
        tag = entry["tag"]
        key = entry["geometry_key"]
        expr = f"q.any_tag('{tag}') ? Geometry.{key} : ({expr})"
    return {
        "format_version": "1.10.0",
        "render_controllers": {
            "controller.render.tdc_geo_swap": {
                "geometry": expr,
                "materials": [{"*": "Material.default"}],
                "textures": ["Texture.default"],
            }
        },
    }


def _merge_player_entity(rp: str, registry: dict, log: list) -> None:
    path = os.path.join(rp, "entity", "player.entity.json")
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
        data = _read_json(path)
        log.append("🔁 merge player.entity.json ที่มีอยู่ (สำรอง .bak)")
    else:
        data = json.loads(json.dumps(FALLBACK_PLAYER_ENTITY))
        log.append("🆕 สร้าง player.entity.json จาก template (ควรตรวจกับ vanilla จริง)")

    desc = data["minecraft:client_entity"]["description"]
    geo = desc.setdefault("geometry", {})
    for entry in registry.get("items", {}).values():
        geo[entry["geometry_key"]] = entry["geometry_id"]

    # swap the third_person controller to ours, keep its molang condition
    rcs = desc.get("render_controllers", [])
    for i, rc in enumerate(rcs):
        if isinstance(rc, str):
            if rc == "controller.render.player.third_person":
                rcs[i] = "controller.render.tdc_geo_swap"
        elif isinstance(rc, dict):
            for name in list(rc.keys()):
                if name == "controller.render.player.third_person":
                    rc["controller.render.tdc_geo_swap"] = rc.pop(name)
    desc["render_controllers"] = rcs
    _write_json(path, data)


def _bp_tag_script(bp: str, identifier: str, prefix: str, log: list) -> None:
    scripts_dir = os.path.join(bp, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    fname = f"geo_swap_{prefix}.js"
    tag = f"geo_{prefix}"
    js = f'''import {{ world, system, EquipmentSlot }} from "@minecraft/server";

// Auto-generated Geo Swap tag driver for {identifier}
const ITEM = "{identifier}";
const GEO_TAG = "{tag}";

system.runInterval(() => {{
  for (const player of world.getAllPlayers()) {{
    let holding = false;
    try {{
      const eq = player.getComponent("equippable");
      const main = eq && eq.getEquipment(EquipmentSlot.Mainhand);
      holding = !!(main && main.typeId === ITEM);
    }} catch (e) {{}}
    try {{
      if (holding) {{ if (!player.hasTag(GEO_TAG)) player.addTag(GEO_TAG); }}
      else {{ if (player.hasTag(GEO_TAG)) player.removeTag(GEO_TAG); }}
    }} catch (e) {{}}
  }}
}}, 2);
'''
    with open(os.path.join(scripts_dir, fname), "w", encoding="utf-8") as f:
        f.write(js)

    # wire into main.js barrel (append import if missing)
    main_js = os.path.join(scripts_dir, "main.js")
    line = f'import "./{fname}";\n'
    existing = ""
    if os.path.exists(main_js):
        with open(main_js, "r", encoding="utf-8") as f:
            existing = f.read()
    if line.strip() not in existing:
        with open(main_js, "a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write(line)
    log.append(f"🏷️ สร้าง BP tag driver: scripts/{fname} + ต่อ main.js")


def build_geo_swap(req: dict) -> dict:
    log: List[str] = []
    warnings: List[str] = []

    rp = req.get("rp_path")
    if not rp or not os.path.exists(os.path.join(rp, "manifest.json")):
        raise ValueError("โฟลเดอร์ RP ไม่ถูกต้อง (ไม่พบ manifest.json)")
    identifier = (req.get("item_identifier") or "").strip()
    if ":" not in identifier:
        raise ValueError("ต้องระบุ item identifier (เช่น tdcmodel:fire_sword)")

    prefix = _slug_id(identifier)
    bones = parse_bones(req.get("bones") or [])
    if not bones:
        raise ValueError("ต้องระบุ bone อย่างน้อย 1 ตัว (เช่น sword_edit)")

    geo_id = f"geometry.{prefix}_player"
    geo_key = f"{prefix}_swap"
    tag = f"geo_{prefix}"

    # 1. player geo with embedded bones
    geo = _load_base_geo(req.get("base_player_geo_path"))
    if "minecraft:geometry" not in geo or not geo["minecraft:geometry"]:
        raise ValueError("ไฟล์ base player geo ไม่ถูกต้อง")
    geo["minecraft:geometry"][0]["description"]["identifier"] = geo_id
    geo_bones = geo["minecraft:geometry"][0].setdefault("bones", [])
    existing_names = {b.get("name", "").lower() for b in geo_bones}
    for b in bones:
        if b["name"].lower() not in existing_names:
            geo_bones.append(_bone_object(b))
    geo_path = os.path.join(rp, "models", "entity", f"{prefix}_player.geo.json")
    _write_json(geo_path, geo)
    log.append(f"🧍 สร้าง player geo: {geo_id} (+{len(bones)} bone)")

    # 2. registry upsert
    reg_path = os.path.join(rp, "tdc_geo_swap_registry.json")
    registry = {"version": 1, "items": {}}
    if os.path.exists(reg_path):
        try:
            registry = _read_json(reg_path)
        except Exception:
            pass
    registry.setdefault("items", {})[identifier] = {
        "tag": tag, "geometry_key": geo_key, "geometry_id": geo_id,
        "bones": [f"{b['name']}:{b['parent']}" for b in bones],
    }
    _write_json(reg_path, registry)
    log.append(f"📒 อัปเดต registry ({len(registry['items'])} item)")

    # 3. shared render controller (regenerated from registry)
    rc_path = os.path.join(rp, "render_controllers", "tdc_geo_swap.render_controllers.json")
    _write_json(rc_path, _build_controller(registry))
    log.append("🎛️ regenerate render controller (รวมทุก item)")

    # 4. player.entity.json (create or merge)
    _merge_player_entity(rp, registry, log)

    # 5. optional BP tag driver
    bp = req.get("bp_path")
    if req.get("gen_bp_script") and bp and os.path.exists(os.path.join(bp, "manifest.json")):
        _bp_tag_script(bp, identifier, prefix, log)

    warnings.append("player.entity.json เป็นไฟล์เดียวต่อเกม — ถ้ามีแอดออนอื่นแก้โมเดลผู้เล่นอาจชนกัน")
    warnings.append("UV ของ bone อาวุธต้องจัดใน Blockbench เอง (placeholder uv [0,0])")
    if not req.get("base_player_geo_path"):
        warnings.append("ใช้ player geo แบบ fallback — ควรแทนด้วย vanilla player.geo.json จริงสำหรับงานจริง")

    log.append("🎉 สำเร็จ")
    return {
        "log": log, "warnings": warnings,
        "tag": tag, "geometry_id": geo_id, "geometry_key": geo_key,
        "registry_items": list(registry["items"].keys()),
    }
