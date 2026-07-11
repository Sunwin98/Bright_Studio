"""Headless port of Heaven Send Skin Factory V3.

The create_*/generate_* helpers are lifted from factory_skin_v3.py with their
logic unchanged; only the interactive main() and ANSI printing are replaced by a
parameterized build_addon(req) and a log list. Master assets are read in place
from config.MASTER_ASSETS (nothing is duplicated).
"""
from __future__ import annotations

import base64
import io
import json
import os
import random
import re
import shutil
import string
import uuid
from typing import List, Optional

import config
from app.core.skin_factory.models import SkinInfo

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# ── constants (mirror factory_skin_v3) ────────────────────────────────────────
STORE_NAME = config.STORE_NAME
CREATOR_NAME = config.CREATOR_NAME
FILE_PREFIX = config.FILE_PREFIX
MASTER_ICON = "pack_icon.png"
MASTER_MODEL = "ต้นแบบ.geo.json"
MASTER_STARLIB2 = "starlib2"
MASTER_UI_HEAVEN = "ui heaven"
DEFAULT_CREATOR = "Iamsayhi1"

ARMOR_SLOTS = {
    "1": ("helmet", "slot.armor.head", "Head", "หมวก (Head)"),
    "2": ("chestplate", "slot.armor.chest", "Chest", "เสื้อเกราะ (Chest)"),
    "3": ("leggings", "slot.armor.legs", "Legs", "กางเกง (Legs)"),
    "4": ("boots", "slot.armor.feet", "Feet", "รองเท้า (Feet)"),
    "5": ("mainhand", "slot.weapon.mainhand", "Mainhand", "มือขวา (Mainhand)"),
}

THAI_TO_ENG = {
    'ก': 'k', 'ข': 'k', 'ค': 'k', 'ฆ': 'k', 'ง': 'ng',
    'จ': 'j', 'ฉ': 'ch', 'ช': 'ch', 'ซ': 's', 'ฌ': 'ch',
    'ญ': 'y', 'ฎ': 'd', 'ฏ': 't', 'ฐ': 't', 'ฑ': 't',
    'ฒ': 't', 'ณ': 'n', 'ด': 'd', 'ต': 't', 'ถ': 't',
    'ท': 't', 'ธ': 't', 'น': 'n', 'บ': 'b', 'ป': 'p',
    'ผ': 'p', 'ฝ': 'f', 'พ': 'p', 'ฟ': 'f', 'ภ': 'p',
    'ม': 'm', 'ย': 'y', 'ร': 'r', 'ล': 'l', 'ว': 'w',
    'ศ': 's', 'ษ': 's', 'ส': 's', 'ห': 'h', 'ฬ': 'l',
    'อ': 'o', 'ฮ': 'h',
    'ะ': 'a', 'า': 'a', 'ิ': 'i', 'ี': 'i', 'ึ': 'u',
    'ื': 'u', 'ุ': 'u', 'ู': 'u', 'เ': 'e', 'แ': 'ae',
    'โ': 'o', 'ใ': 'ai', 'ไ': 'ai', 'ำ': 'am',
    '่': '', '้': '', '๊': '', '๋': '', '์': '',
    'ั': 'a', '็': '', 'ๆ': '', 'ๅ': 'a',
}

# ── logging (replaces ANSI print_*) ───────────────────────────────────────────
_LOG: List[str] = []


def _log(msg: str) -> None:
    _LOG.append(msg)


def print_success(msg): _log(f"✅ {msg}")
def print_info(msg): _log(f"📌 {msg}")
def print_warning(msg): _log(f"⚠️ {msg}")
def print_error(msg): _log(f"❌ {msg}")


# ── utilities (verbatim logic) ────────────────────────────────────────────────
def generate_uuid(): return str(uuid.uuid4())
def generate_unique_id(length=4): return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))
def is_thai(text): return bool(re.search(r'[฀-๿]', text))


def transliterate_thai(text):
    return ''.join(THAI_TO_ENG.get(c, c.lower() if c.isalnum() or c in '_- ' else '') for c in text)


def sanitize_filename(name):
    if is_thai(name):
        name = transliterate_thai(name)
    name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))
    return name.lower() if name else f"skin_{generate_unique_id()}"


# ── icon generation ───────────────────────────────────────────────────────────
def generate_icon_from_skin(skin_path, dest_folder, item_id):
    if not PILLOW_AVAILABLE:
        shutil.copy2(skin_path, os.path.join(dest_folder, f"{item_id}.png"))
        shutil.copy2(skin_path, os.path.join(dest_folder, f"{item_id}_item.png"))
        return False
    try:
        icon_result = _crop_face_icon(skin_path)
        if icon_result is None:
            skin = Image.open(skin_path).convert("RGBA")
            w, h = skin.size
            crop_size = min(w, h, 128)
            icon_result = skin.crop((0, 0, crop_size, crop_size))
        icon_result.resize((16, 16), Image.LANCZOS).save(os.path.join(dest_folder, f"{item_id}.png"))
        icon_result.save(os.path.join(dest_folder, f"{item_id}_item.png"))
        return True
    except Exception as e:
        print_warning(f"Icon generation failed: {e}")
        shutil.copy2(skin_path, os.path.join(dest_folder, f"{item_id}.png"))
        return False


def _crop_face_icon(skin_path):
    """Shared crop logic (face+hair overlay, body fallback). Returns Image or None."""
    skin = Image.open(skin_path).convert("RGBA")
    w, h = skin.size
    if w == h and w >= 64:
        scale = w // 64
        face = skin.crop((8 * scale, 8 * scale, 16 * scale, 16 * scale))
        hair = skin.crop((40 * scale, 8 * scale, 48 * scale, 16 * scale))
        if face.getextrema()[3][1] > 0:
            return Image.alpha_composite(face, hair)
        body_x1, body_y1 = 20 * scale, 20 * scale
        body_x2, body_y2 = 28 * scale, 28 * scale
        if body_x2 <= w and body_y2 <= h:
            body_crop = skin.crop((body_x1, body_y1, body_x2, body_y2))
            if body_crop.getextrema()[3][1] > 0:
                return body_crop
    return None


def preview_icon_base64(skin_path) -> Optional[str]:
    """Return a base64 PNG (64px) of the auto-cropped icon, or None."""
    if not PILLOW_AVAILABLE:
        return None
    try:
        icon = _crop_face_icon(skin_path)
        if icon is None:
            skin = Image.open(skin_path).convert("RGBA")
            w, h = skin.size
            crop_size = min(w, h, 128)
            icon = skin.crop((0, 0, crop_size, crop_size))
        icon = icon.resize((64, 64), Image.NEAREST)
        buf = io.BytesIO()
        icon.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


# ── file creation (verbatim from factory_skin_v3) ─────────────────────────────
def create_folder_structure(base_path, addon_name):
    bp, rp = f"{addon_name}_BP", f"{addon_name}_RP"
    for f in [
        os.path.join(base_path, bp), os.path.join(base_path, bp, "items"),
        os.path.join(base_path, bp, "functions"), os.path.join(base_path, bp, "scripts"),
        os.path.join(base_path, bp, "item_catalog"),
        os.path.join(base_path, rp), os.path.join(base_path, rp, "animations"),
        os.path.join(base_path, rp, "models", "entity"), os.path.join(base_path, rp, "textures", "items"),
        os.path.join(base_path, rp, "textures", "skin"), os.path.join(base_path, rp, "attachables"),
        os.path.join(base_path, rp, "texts"), os.path.join(base_path, rp, "ui"),
    ]:
        os.makedirs(f, exist_ok=True)
    return bp, rp


def create_manifests(base_path, addon_name, bp_folder, rp_folder, use_script=True):
    rp_uuid = generate_uuid()
    bp_uuid = generate_uuid()

    rp_manifest = {
        "format_version": 2,
        "header": {"name": f"§b§l{addon_name}§r §7| §fRP", "description": f"§l[{addon_name}] [สร้างโดย {CREATOR_NAME}]\n§7{STORE_NAME} ขอบคุณที่ใช้บริการ https://discord.gg/heavensend", "uuid": rp_uuid, "version": [1, 0, 0], "min_engine_version": [1, 21, 0]},
        "modules": [{"type": "resources", "uuid": generate_uuid(), "version": [1, 0, 0]}]
    }
    with open(os.path.join(base_path, rp_folder, "manifest.json"), 'w', encoding='utf-8') as f:
        json.dump(rp_manifest, f, indent=4, ensure_ascii=False)

    if use_script:
        bp_manifest = {
            "format_version": 2,
            "header": {"name": f"§b§l{addon_name}§r §7| §fBP", "description": f"§l[{addon_name}] [สร้างโดย {CREATOR_NAME}]\n§7{STORE_NAME} ขอบคุณที่ใช้บริการ https://discord.gg/heavensend", "uuid": bp_uuid, "version": [1, 0, 0], "min_engine_version": [1, 21, 0]},
            "modules": [
                {"type": "data", "uuid": generate_uuid(), "version": [1, 0, 0]},
                {"type": "script", "language": "javascript", "uuid": generate_uuid(), "entry": "scripts/main.js", "version": [1, 0, 0]}
            ],
            "dependencies": [{"uuid": rp_uuid, "version": [1, 0, 0]}, {"module_name": "@minecraft/server", "version": "1.17.0"}, {"module_name": "@minecraft/server-ui", "version": "1.3.0"}]
        }
    else:
        bp_manifest = {
            "format_version": 2,
            "header": {"name": f"§b§l{addon_name}§r §7| §fBP", "description": f"§l[{addon_name}] [สร้างโดย {CREATOR_NAME}]\n§7{STORE_NAME} ขอบคุณที่ใช้บริการ https://discord.gg/heavensend", "uuid": bp_uuid, "version": [1, 0, 0], "min_engine_version": [1, 21, 0]},
            "modules": [
                {"type": "data", "uuid": generate_uuid(), "version": [1, 0, 0]}
            ],
            "dependencies": [{"uuid": rp_uuid, "version": [1, 0, 0]}]
        }
    with open(os.path.join(base_path, bp_folder, "manifest.json"), 'w', encoding='utf-8') as f:
        json.dump(bp_manifest, f, indent=4, ensure_ascii=False)
    return rp_uuid


def create_skin_item(base_path, bp_folder, skin: SkinInfo):
    item = {
        "format_version": "1.21.10",
        "minecraft:item": {
            "description": {"identifier": f"{FILE_PREFIX}:{skin.item_id}", "menu_category": {"category": "equipment", "group": f"{FILE_PREFIX}:{FILE_PREFIX}_skins"}},
            "components": {"minecraft:max_stack_size": 1, "minecraft:icon": skin.item_id, "minecraft:display_name": {"value": f"§b§l{skin.display_name}"}, "minecraft:wearable": {"slot": skin.slot_value}}
        }
    }
    with open(os.path.join(base_path, bp_folder, "items", f"{skin.item_id}.json"), 'w', encoding='utf-8') as f:
        json.dump(item, f, indent=4, ensure_ascii=False)


def create_selector_item(base_path, bp_folder, addon_name, selector_id, icon_id):
    item = {
        "format_version": "1.21.10",
        "minecraft:item": {
            "description": {"identifier": f"{FILE_PREFIX}:{selector_id}", "menu_category": {"category": "equipment", "group": f"{FILE_PREFIX}:{FILE_PREFIX}_skins"}},
            "components": {"minecraft:max_stack_size": 1, "minecraft:icon": f"{icon_id}_item", "minecraft:display_name": {"value": f"§d§l{addon_name} §r§7(กดใช้เพื่อเปิดเมนู)"}}
        }
    }
    with open(os.path.join(base_path, bp_folder, "items", f"{selector_id}.json"), 'w', encoding='utf-8') as f:
        json.dump(item, f, indent=4, ensure_ascii=False)


def create_attachable(base_path, rp_folder, skin: SkinInfo):
    is_held = skin.slot_value in ("slot.weapon.mainhand", "slot.weapon.offhand")
    material = "entity_alphatest" if is_held else "armor"
    render_ctrl = "controller.render.item_default" if is_held else "controller.render.armor"
    att = {
        "format_version": "1.10.0",
        "minecraft:attachable": {
            "description": {
                "identifier": f"{FILE_PREFIX}:{skin.item_id}",
                "materials": {"default": material},
                "textures": {"default": f"textures/skin/{skin.item_id}"},
                "geometry": {"default": skin.geometry_id},
                "render_controllers": [render_ctrl],
                "item": {f"{FILE_PREFIX}:{skin.item_id}": "q.owner_identifier == 'minecraft:player'"}
            }
        }
    }
    if skin.animation_names:
        att["minecraft:attachable"]["description"]["animations"] = {f"anim_{i}": n for i, n in enumerate(skin.animation_names)}
        att["minecraft:attachable"]["description"]["scripts"] = {"animate": [f"anim_{i}" for i in range(len(skin.animation_names))]}
    with open(os.path.join(base_path, rp_folder, "attachables", f"{skin.item_id}.json"), 'w', encoding='utf-8') as f:
        json.dump(att, f, indent=4, ensure_ascii=False)


def create_selector_attachable(base_path, rp_folder, selector_id):
    att = {
        "format_version": "1.10.0",
        "minecraft:attachable": {
            "description": {"identifier": f"{FILE_PREFIX}:{selector_id}", "materials": {"default": "entity_alphatest"}, "textures": {"default": "textures/items/heaven"}, "geometry": {"default": "geometry.air"}, "render_controllers": ["controller.render.armor"]}
        }
    }
    with open(os.path.join(base_path, rp_folder, "attachables", f"{selector_id}.json"), 'w', encoding='utf-8') as f:
        json.dump(att, f, indent=4, ensure_ascii=False)


def create_model(script_dir, base_path, rp_folder, skin: SkinInfo):
    dest = os.path.join(base_path, rp_folder, "models", "entity", f"{skin.item_id}.geo.json")
    if skin.model_path and os.path.exists(skin.model_path):
        shutil.copy2(skin.model_path, dest)
        with open(dest, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if "minecraft:geometry" in data and len(data["minecraft:geometry"]) > 0:
            return data["minecraft:geometry"][0]["description"]["identifier"]
    else:
        source = os.path.join(script_dir, MASTER_MODEL)
        if os.path.exists(source):
            with open(source, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "minecraft:geometry" in data and len(data["minecraft:geometry"]) > 0:
                data["minecraft:geometry"][0]["description"]["identifier"] = skin.geometry_id
            with open(dest, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
    return skin.geometry_id


def create_air_model(base_path, rp_folder):
    air = {"format_version": "1.12.0", "minecraft:geometry": [{"description": {"identifier": "geometry.air", "texture_width": 16, "texture_height": 16, "visible_bounds_width": 0, "visible_bounds_height": 0, "visible_bounds_offset": [0, 0, 0]}, "bones": []}]}
    with open(os.path.join(base_path, rp_folder, "models", "entity", "air.geo.json"), 'w', encoding='utf-8') as f:
        json.dump(air, f, indent=4)


def copy_animation(base_path, rp_folder, skin: SkinInfo):
    if not skin.animation_path or not os.path.exists(skin.animation_path):
        return None
    dest = os.path.join(base_path, rp_folder, "animations", f"{skin.item_id}.animation.json")
    shutil.copy2(skin.animation_path, dest)
    try:
        with open(dest, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if "animations" in data:
            return list(data["animations"].keys())
    except Exception:
        pass
    return None


def create_item_texture(base_path, rp_folder, skins: List[SkinInfo], selector_id):
    data = {"resource_pack_name": STORE_NAME, "texture_name": "atlas.items", "texture_data": {"heaven": {"textures": "textures/items/heaven"}}}
    for s in skins:
        data["texture_data"][s.item_id] = {"textures": f"textures/items/{s.item_id}"}
        data["texture_data"][f"{s.item_id}_item"] = {"textures": f"textures/items/{s.item_id}_item"}
    with open(os.path.join(base_path, rp_folder, "textures", "item_texture.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def create_lang_file(base_path, rp_folder, addon_name, skins: List[SkinInfo], selector_id):
    lines = [
        "## ════════════════════════════════════════════════════════════",
        f"## {STORE_NAME} - {addon_name}",
        f"## Created by {CREATOR_NAME}",
        "## ════════════════════════════════════════════════════════════",
        "## COPYRIGHT NOTICE / ลิขสิทธิ์",
        f"## This add-on is the property of {STORE_NAME}, created by {CREATOR_NAME}.",
        "## All rights reserved. Redistribution or resale is prohibited.",
        f"## แอดออนนี้เป็นลิขสิทธิ์ของ {STORE_NAME} สร้างโดย {CREATOR_NAME}",
        "## สงวนลิขสิทธิ์ทั้งหมด ห้ามแจกจ่ายหรือขายต่อ",
        "## Contact / ติดต่อ: discord.gg/heavensend",
        "## ════════════════════════════════════════════════════════════",
        ""
    ]
    for s in skins:
        lines.append(f"item.{FILE_PREFIX}:{s.item_id}.name=§b§l{s.display_name}")
    if selector_id:
        lines.append(f"item.{FILE_PREFIX}:{selector_id}.name=§d§l{addon_name} Selector")
    with open(os.path.join(base_path, rp_folder, "texts", "en_US.lang"), 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


def create_terms_file(base_path, addon_name, rp_folder):
    content = f"""════════════════════════════════════════════════════════════
  📜 นโยบายและข้อตกลงการใช้งาน / Terms of Service
  {STORE_NAME} — {addon_name}
════════════════════════════════════════════════════════════

[ ภาษาไทย ]

1. ลิขสิทธิ์
   แอดออนนี้เป็นผลงานของ {STORE_NAME} สร้างโดย {CREATOR_NAME}
   สงวนลิขสิทธิ์ทั้งหมด รวมถึงโมเดล, เท็กซ์เจอร์, แอนิเมชัน,
   สคริปต์ และไฟล์ทั้งหมดในแพ็ค

2. สิทธิ์การใช้งาน
   - ใช้งานได้ 1 คน ต่อ 1 การซื้อ (สิทธิ์ส่วนบุคคล)
   - ใช้ได้ในเซิร์ฟเวอร์ส่วนตัวหรือโลกของผู้ซื้อเท่านั้น
   - ห้ามแจกจ่าย, ส่งต่อ, อัปโหลดซ้ำ หรือขายต่อไม่ว่ากรณีใด

3. สิ่งที่ห้ามทำ
   - ห้ามแจกจ่ายหรือแชร์ไฟล์แอดออนให้ผู้อื่น
   - ห้ามขายต่อ หรือนำไปรวมแพ็คขาย
   - ห้ามแก้ไข, ลบ หรือเปลี่ยนเครดิตผู้สร้าง
   - ห้ามอ้างว่าเป็นผลงานของตนเอง
   - ห้ามนำโมเดล/เท็กซ์เจอร์ไปใช้ในแอดออนอื่นโดยไม่ได้รับอนุญาต

4. การรับประกัน
   - หากแอดออนมีปัญหาจากการอัปเดตเกม สามารถแจ้งขอแก้ไขได้
   - ไม่รับผิดชอบกรณีใช้งานผิดวิธีหรือดัดแปลงไฟล์เอง

5. การละเมิด
   หากพบการละเมิดข้อตกลง {STORE_NAME} สงวนสิทธิ์ในการดำเนินการ
   ตามความเหมาะสม รวมถึงระงับสิทธิ์การใช้งานและรายงานไปยัง
   แพลตฟอร์มที่เกี่ยวข้อง

════════════════════════════════════════════════════════════

[ English ]

1. Copyright
   This add-on is the intellectual property of {STORE_NAME},
   created by {CREATOR_NAME}. All rights reserved including models,
   textures, animations, scripts, and all files within the pack.

2. License
   - Licensed to 1 person per purchase (personal use license)
   - May only be used in the buyer's personal server or world
   - Redistribution, sharing, re-uploading, or reselling is
     strictly prohibited

3. Restrictions
   - Do not distribute or share addon files with others
   - Do not resell or include in other packs for sale
   - Do not modify, remove, or alter creator credits
   - Do not claim this work as your own
   - Do not use models/textures in other addons without permission

4. Support
   - If the addon breaks due to a game update, contact us for a fix
   - No support for issues caused by user modifications

5. Violation
   Any breach of these terms may result in revocation of license
   and reporting to relevant platforms.

════════════════════════════════════════════════════════════
  Contact / ติดต่อ: discord.gg/heavensend
  (C) {STORE_NAME} — Created by {CREATOR_NAME}
════════════════════════════════════════════════════════════
"""
    filepath = os.path.join(base_path, rp_folder, "TERMS.txt")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def create_item_catalog(base_path, bp_folder):
    item = {"format_version": "1.21.10", "minecraft:item": {"description": {"identifier": f"{FILE_PREFIX}:icon", "menu_category": {"category": "none"}}, "components": {"minecraft:max_stack_size": 1, "minecraft:icon": "heaven"}}}
    with open(os.path.join(base_path, bp_folder, "items", "heaver_icon.json"), 'w', encoding='utf-8') as f:
        json.dump(item, f, indent=4, ensure_ascii=False)
    catalog = {"format_version": "1.21.60", "minecraft:crafting_items_catalog": {"categories": [{"category_name": "equipment", "groups": [{"group_identifier": {"icon": f"{FILE_PREFIX}:icon", "display_name": "HeaverSend", "name": f"{FILE_PREFIX}:{FILE_PREFIX}_skins"}, "items": []}]}]}}
    with open(os.path.join(base_path, bp_folder, "item_catalog", "crafting_item_catalog.json"), 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=4, ensure_ascii=False)


def create_functions(base_path, bp_folder, addon_name, skins: List[SkinInfo]):
    safe_name = sanitize_filename(addon_name)
    tick = {"replace": False, "values": [f"{safe_name}_skin_effect"]}
    with open(os.path.join(base_path, bp_folder, "functions", "tick.json"), 'w', encoding='utf-8') as f:
        json.dump(tick, f, indent=4)
    lines = [f"# {addon_name} - Invisibility Effect", "# Generated by Skin Factory V3", ""]
    for s in skins:
        slot_map = {
            "slot.armor.head": "slot.armor.head",
            "slot.armor.chest": "slot.armor.chest",
            "slot.armor.legs": "slot.armor.legs",
            "slot.armor.feet": "slot.armor.feet",
            "slot.weapon.mainhand": "slot.weapon.mainhand",
            "slot.weapon.offhand": "slot.weapon.offhand",
        }
        loc = slot_map.get(s.slot_value, "slot.armor.head")
        lines.append(f"effect @a[hasitem={{item={FILE_PREFIX}:{s.item_id},location={loc}}}] invisibility 5 255 true")
    with open(os.path.join(base_path, bp_folder, "functions", f"{safe_name}_skin_effect.mcfunction"), 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


# ── script generation (Normal + Special UI) ───────────────────────────────────
def create_normal_ui_script(base_path, bp_folder, addon_name, skins, selector_id, allowed_players, enable_xbox_lock):
    _write_ui_script(base_path, bp_folder, addon_name, skins, selector_id, allowed_players, enable_xbox_lock, special=False)


def create_special_ui_script(base_path, bp_folder, addon_name, skins, selector_id, allowed_players, enable_xbox_lock):
    _write_ui_script(base_path, bp_folder, addon_name, skins, selector_id, allowed_players, enable_xbox_lock, special=True)


def _write_ui_script(base_path, bp_folder, addon_name, skins, selector_id, allowed_players, enable_xbox_lock, special):
    skins_obj = ",\n    ".join([f'{s.name}: {{ id: "{FILE_PREFIX}:{s.item_id}", name: "{s.display_name}", slot: "{s.equip_slot}", icon: "textures/items/{s.item_id}_item" }}' for s in skins])
    if special:
        buttons = "\n    ".join([f'form.button("§d§l♡ {s.display_name}", SKINS.{s.name}.icon);' for s in skins])
    else:
        buttons = "\n    ".join([f'form.button("§0§l{s.display_name}", SKINS.{s.name}.icon);' for s in skins])
    cases = "\n            ".join([f'case {i}: toggleSkin(player, SKINS.{s.name}); break;' for i, s in enumerate(skins)])

    global_allowed = ""
    xbox_check = ""
    if enable_xbox_lock and allowed_players:
        players_str = ', '.join([f'"{p}"' for p in allowed_players])
        global_allowed = f'const ALLOWED_PLAYERS = [{players_str}];\n\nfunction isAllowed(name) {{\n    return ALLOWED_PLAYERS.some(n => n.toLowerCase() === name.toLowerCase());\n}}'
        xbox_check = '''if (!isAllowed(player.name)) {
        player.onScreenDisplay.setActionBar("§c§r§fคุณไม่มีสิทธิ์ใช้งานไอเทมนี้!");
        return;
    }'''

    title_line = 'form.title("§f§0§0");  // Trigger custom UI' if special else f'form.title("§d§l{addon_name}");'
    body_line = 'form.body("");' if special else 'form.body("§7เลือกสกินที่ต้องการสวมใส่:");'
    remove_btn = 'form.button("§c§l✖ ถอดสกินทั้งหมด", "textures/ui/cancel");' if special else 'form.button("§c§lถอดสกินทั้งหมด", "textures/ui/cancel");'
    close_btn = 'form.button("§8§l◀ ปิดเมนู", "textures/ui/cancel");' if special else 'form.button("§7§lปิดเมนู", "textures/ui/cancel");'

    script = f'''import {{ world, system, ItemStack }} from "@minecraft/server";
import {{ ActionFormData }} from "@minecraft/server-ui";

const SKINS = {{
    {skins_obj}
}};
const SELECTOR_ITEM = "{FILE_PREFIX}:{selector_id}";
{global_allowed}

world.afterEvents.itemUse.subscribe((event) => {{
    const player = event.source;
    const item = event.itemStack;
    if (item?.typeId !== SELECTOR_ITEM) return;
    {xbox_check}
    system.run(() => openSkinMenu(player));
}});

function openSkinMenu(player) {{
    const form = new ActionFormData();
    {title_line}
    {body_line}
    {buttons}
    {remove_btn}
    {close_btn}

    form.show(player).then((res) => {{
        if (res.canceled) return;
        switch (res.selection) {{
            {cases}
            case {len(skins)}: removeAllSkins(player); break;
        }}
    }});
}}

function toggleSkin(player, skin) {{
    try {{
        const eq = player.getComponent("equippable");
        if (!eq) return;
        const current = eq.getEquipment(skin.slot);
        if (current?.typeId === skin.id) {{
            eq.setEquipment(skin.slot, undefined);
            player.onScreenDisplay.setActionBar("§c§l[{addon_name}] §r§fถอด " + skin.name + " §fแล้ว!");
        }} else {{
            eq.setEquipment(skin.slot, new ItemStack(skin.id, 1));
            player.onScreenDisplay.setActionBar("§a§l[{addon_name}] §r§fสวมใส่ " + skin.name + " §fแล้ว!");
        }}
    }} catch (e) {{}}
}}

function removeAllSkins(player) {{
    try {{
        const eq = player.getComponent("equippable");
        if (!eq) return;
        for (const key in SKINS) {{
            const current = eq.getEquipment(SKINS[key].slot);
            if (current?.typeId === SKINS[key].id) eq.setEquipment(SKINS[key].slot, undefined);
        }}
        player.onScreenDisplay.setActionBar("§c§l[{addon_name}] §r§fถอดสกินทั้งหมดแล้ว!");
    }} catch (e) {{}}
}}
'''

    if enable_xbox_lock and allowed_players:
        spawn_code = f'''
// Give selector to allowed players on spawn
world.afterEvents.playerSpawn.subscribe((event) => {{
    const player = event.player;
    if (!isAllowed(player.name)) return;

    system.runTimeout(() => {{
        try {{
            const inventory = player.getComponent("inventory")?.container;
            if (!inventory) return;

            for (let i = 0; i < inventory.size; i++) {{
                if (inventory.getItem(i)?.typeId === SELECTOR_ITEM) return;
            }}

            inventory.addItem(new ItemStack(SELECTOR_ITEM, 1));
            player.onScreenDisplay.setActionBar("§a§l[{addon_name}] §r§fได้รับ Selector Item แล้ว!");
        }} catch (e) {{}}
    }}, 40);
}});

'''
        script = script.rstrip() + spawn_code

        protect_code = f'''
// Prevent non-allowed players from wearing skins
system.runInterval(() => {{
    for (const player of world.getAllPlayers()) {{
        if (isAllowed(player.name)) continue;

        try {{
            const eq = player.getComponent("equippable");
            if (!eq) continue;

            for (const key in SKINS) {{
                const item = eq.getEquipment(SKINS[key].slot);
                if (item?.typeId === SKINS[key].id) {{
                    eq.setEquipment(SKINS[key].slot, undefined);
                    player.onScreenDisplay.setActionBar("§c§r§fคุณไม่มีสิทธิ์สวมใส่สกินนี้!");
                }}
            }}
        }} catch (e) {{}}
    }}
}}, 20);

'''
        script = script.rstrip() + protect_code

    label = "Special UI Skin Selector" if special else "Skin Selector"
    script += f'''
console.warn("[{addon_name}] {label} loaded!");
'''
    with open(os.path.join(base_path, bp_folder, "scripts", "main.js"), 'w', encoding='utf-8') as f:
        f.write(script)


def create_special_ui_files(script_dir, base_path, rp_folder):
    src_starlib = os.path.join(script_dir, MASTER_STARLIB2)
    dst_starlib = os.path.join(base_path, rp_folder, "ui", "starlib2")
    if os.path.exists(src_starlib):
        shutil.copytree(src_starlib, dst_starlib, dirs_exist_ok=True)

    src_ui = os.path.join(script_dir, MASTER_UI_HEAVEN)
    dst_ui = os.path.join(base_path, rp_folder, "textures", "ui", "ui heaven")
    os.makedirs(dst_ui, exist_ok=True)
    if os.path.exists(src_ui):
        for f in os.listdir(src_ui):
            if f.endswith('.png'):
                shutil.copy2(os.path.join(src_ui, f), os.path.join(dst_ui, f))

    ui_defs = {"ui_defs": ["ui/starlib2/global.jsonc", "ui/starlib2/style.jsonc", "ui/starlib2/package_button/common_button.jsonc", "ui/starlib2/package_button/button_templates.jsonc", "ui/starlib2/package_button/button_skins.jsonc", "ui/starlib2/package_screen/screen_template.jsonc", "ui/starlib2/package_screen/notification.jsonc", "ui/starlib2/package_dynamic/dynamic_grid.jsonc", "ui/starlib2/package_dynamic/dynamic_cycler.jsonc", "ui/starlib2/package_dynamic/dynamic_dropdown.jsonc", "ui/starlib2/package_custom/custom_input_set.jsonc", "ui/starlib2/package_custom/custom_text_field.jsonc", "ui/starlib2/package_custom/custom_progress.jsonc", "ui/starlib2/package_custom/custom_slider.jsonc", "ui/heaven_skin.json", "ui/server_form.json"]}
    with open(os.path.join(base_path, rp_folder, "ui", "_ui_defs.json"), 'w', encoding='utf-8') as f:
        json.dump(ui_defs, f, indent=2, ensure_ascii=False)

    server_form = {"namespace": "server_form", "long_form@starlib_pkg_screen_template.screen_template": {"$SCREEN_TEMPLATE_fade_enabled": False, "$FORM_TEMPLATE_header_control": "global.empty_panel", "$HEADER_TEMPLATE_close_button_control": "global.empty_panel", "variables": [{"requires": "(not ((#title_text - '§f§0§0') = #title_text))", "$forms_holder_controls|default": [], "$forms_holder_controls": [{"custom_form@heaven_skin.main": {}}]}]}}
    with open(os.path.join(base_path, rp_folder, "ui", "server_form.json"), 'w', encoding='utf-8') as f:
        json.dump(server_form, f, indent=2, ensure_ascii=False)

    heaven_skin = {"namespace": "heaven_skin", "main@heaven_skin.screen": {"$SCREEN_TEMPLATE_fade_enabled": False, "$FORM_TEMPLATE_header_control": "global.empty_panel", "$HEADER_TEMPLATE_close_button_control": "global.empty_panel", "$FORM_TEMPLATE_appear_sub_contents_padding": True, "$FORM_TEMPLATE_appear_header_padding": False, "$FORM_TEMPLATE_between_contents_padding_size": [0, 1], "$FORM_TEMPLATE_content_size": ["100% - 16px", "100% - 16px"], "$forms_holder_controls": [{"form@global.title_binding": {"$form_size": [280, 200], "$scrolling_content": "heaven_skin.buttons_grid", "$key": "§f§0§0", "$control": "starlib_pkg_screen_template.form_template", "size": ["100%c", "100%c"]}}], "$FORM_TEMPLATE_content_control": "heaven_skin.customContent", "bindings": [{"binding_name": "#title_text"}, {"binding_type": "view", "source_property_name": "(not ((#title_text - '§f§0§0') = #title_text))", "target_property_name": "#visible"}]}, "buttons_grid@global.grid": {"$grid_item": "heaven_skin.grid_button", "layer": 6}, "grid_button": {"type": "panel", "size": ["100%", 30], "controls": [{"grid_button@starlib_pkg_button_templates.grid_item_template": {"$GRID_ITEM_root_control": "heaven_skin.custom_pink_button", "$GRID_ITEM_size": ["100%", 30]}}]}, "custom_pink_button": {"type": "panel", "size": "$GRID_ITEM_size", "controls": [{"row_content": {"type": "stack_panel", "orientation": "horizontal", "size": ["85%", 26], "anchor_from": "center", "anchor_to": "center", "layer": 10, "controls": [{"icon_container": {"type": "panel", "size": [26, 26], "controls": [{"icon": {"type": "image", "layer": 12, "size": [24, 24], "anchor_from": "center", "anchor_to": "center", "bindings": [{"binding_name": "#form_button_texture", "binding_name_override": "#texture", "binding_type": "collection", "binding_collection_name": "form_buttons"}, {"binding_name": "#form_button_texture_file_system", "binding_name_override": "#texture_file_system", "binding_type": "collection", "binding_collection_name": "form_buttons"}, {"binding_type": "view", "source_property_name": "(not((#texture = '') or (#texture = 'loading')))", "target_property_name": "#visible"}]}}]}}, {"spacer": {"type": "panel", "size": [2, 26]}}, {"bar_container": {"type": "panel", "size": ["fill", 26], "controls": [{"bg_bar": {"type": "image", "texture": "textures/ui/ui heaven/bar", "size": ["100%", "100%"], "layer": 10}}, {"text_label": {"type": "label", "text": "#form_button_text", "font_size": "normal", "color": [1.0, 0.6, 0.85, 1.0], "anchor_from": "center", "anchor_to": "center", "shadow": True, "layer": 13, "bindings": [{"binding_collection_name": "form_buttons", "binding_name": "#form_button_text", "binding_type": "collection"}]}}]}}]}}, {"interaction_root_button@common.button": {"size": ["100%", "100%"], "layer": 20, "$pressed_button_name": "button.form_button_click", "bindings": [{"binding_collection_name": "form_buttons", "binding_type": "collection_details"}], "controls": [{"default": {"type": "panel", "size": ["100%", "100%"]}}, {"hover": {"type": "image", "texture": "textures/ui/white_background", "color": [1.0, 1.0, 1.0], "alpha": 0.2, "size": ["100%", "100%"]}}, {"pressed": {"type": "image", "texture": "textures/ui/white_background", "color": [0.8, 0.8, 0.8], "alpha": 0.3, "size": ["100%", "100%"]}}]}}]}, "customContent": {"type": "stack_panel", "orientation": "vertical", "size": ["100%", "100%"], "controls": [{"title_section": {"type": "panel", "size": ["100%", "28%"], "controls": [{"title@style.image": {"size": ["100%", "100%"], "texture": "textures/ui/ui heaven/title", "layer": 99}}]}}, {"spacer": {"type": "panel", "size": ["100%", 4]}}, {"scrolling_panel@global.scrolling_panel": {"$scrolling_content": "heaven_skin.buttons_grid", "size": ["100%", "fill"]}}, {"bottom_spacer": {"type": "panel", "size": ["100%", 6]}}]}, "screen": {"type": "panel", "size": ["100%", "100%"], "controls": [{"screen": {"type": "panel", "size": ["100%cm", "100%cm"], "max_size": ["100% - 20px", "100% - 20px"], "controls": [{"forms_holder": {"type": "panel", "size": ["100%cm", "100%cm"], "controls": "$forms_holder_controls", "$forms_holder_controls|default": []}}]}}, {"background@style.image": {"texture": "textures/ui/ui heaven/background", "size": ["150%", "150%"], "layer": 4}}, {"border@style.image": {"texture": "textures/ui/ui heaven/border", "layer": 6, "size": ["128%", "128%"]}}]}}
    with open(os.path.join(base_path, rp_folder, "ui", "heaven_skin.json"), 'w', encoding='utf-8') as f:
        json.dump(heaven_skin, f, indent=2, ensure_ascii=False)


# ── orchestrator ──────────────────────────────────────────────────────────────
def build_addon(req: dict) -> dict:
    """Build a complete skin addon. req keys:
    addon_name, ui_mode ('normal'|'special'|'none'), xbox_lock (bool),
    xbox_players (list[str]), output_dir (optional), overwrite (bool),
    skins: [{skin_path, model_path?, animation_path?, display_name?, slot ('1'..'5')}]
    Returns {project_path, give_commands, log}.
    """
    _LOG.clear()
    script_dir = str(config.MASTER_ASSETS)  # read live so Settings changes apply immediately

    addon_name = (req.get("addon_name") or "").strip() or f"MultiSkin_{generate_unique_id(4)}"
    ui_mode = req.get("ui_mode", "normal")
    use_special_ui = ui_mode == "special"
    no_ui_mode = ui_mode == "none"
    enable_xbox_lock = bool(req.get("xbox_lock")) and not no_ui_mode
    allowed_players: List[str] = []
    if enable_xbox_lock:
        allowed_players.append(DEFAULT_CREATOR)
        allowed_players.extend([p.strip() for p in (req.get("xbox_players") or []) if p and p.strip()])

    skin_inputs = req.get("skins") or []
    if not skin_inputs:
        raise ValueError("ต้องมีอย่างน้อย 1 สกิน")

    skins: List[SkinInfo] = []
    for idx, si in enumerate(skin_inputs, start=1):
        skin_path = si.get("skin_path")
        if not skin_path or not os.path.exists(skin_path):
            raise ValueError(f"ไม่พบไฟล์สกินชิ้นที่ {idx}: {skin_path}")
        model_path = si.get("model_path") or None
        animation_path = si.get("animation_path") or None
        default_name = os.path.splitext(os.path.basename(skin_path))[0]
        display_name = (si.get("display_name") or "").strip() or default_name
        slot_choice = str(si.get("slot") or "1")
        slot_name, slot_value, equip_slot, _ = ARMOR_SLOTS.get(slot_choice, ARMOR_SLOTS["1"])

        safe_name = sanitize_filename(display_name)
        item_id = f"{FILE_PREFIX}_{safe_name}_{generate_unique_id(4)}"
        geometry_id = f"geometry.{safe_name}_{generate_unique_id(4)}"

        skins.append(SkinInfo(
            name=f"skin{idx}", display_name=display_name, skin_path=skin_path,
            model_path=model_path, animation_path=animation_path,
            slot_name=slot_name, slot_value=slot_value, equip_slot=equip_slot,
            item_id=item_id, geometry_id=geometry_id,
        ))
        print_success(f"เพิ่มสกิน: {display_name} ({slot_name})")

    safe_addon = sanitize_filename(addon_name)
    selector_id = f"{safe_addon}_selector"

    output_dir = req.get("output_dir") or str(config.DEFAULT_OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    base_path = os.path.join(output_dir, safe_addon)
    if os.path.exists(base_path):
        if not req.get("overwrite", True):
            raise ValueError(f"มีโปรเจกต์ชื่อนี้อยู่แล้ว: {base_path}")
        shutil.rmtree(base_path)

    bp_folder, rp_folder = create_folder_structure(base_path, safe_addon)
    print_success("สร้างโครงสร้างโฟลเดอร์")

    src_icon = os.path.join(script_dir, MASTER_ICON)
    if os.path.exists(src_icon):
        shutil.copy2(src_icon, os.path.join(base_path, bp_folder, "pack_icon.png"))
        shutil.copy2(src_icon, os.path.join(base_path, rp_folder, "pack_icon.png"))
        shutil.copy2(src_icon, os.path.join(base_path, rp_folder, "textures", "items", "heaven.png"))
        print_success("คัดลอก pack_icon.png")

    create_manifests(base_path, addon_name, bp_folder, rp_folder, use_script=not no_ui_mode)
    print_success("สร้าง manifest.json")

    for skin in skins:
        actual_geo = create_model(script_dir, base_path, rp_folder, skin)
        skin.geometry_id = actual_geo
        skin.animation_names = copy_animation(base_path, rp_folder, skin)
        shutil.copy2(skin.skin_path, os.path.join(base_path, rp_folder, "textures", "skin", f"{skin.item_id}.png"))
        generate_icon_from_skin(skin.skin_path, os.path.join(base_path, rp_folder, "textures", "items"), skin.item_id)
        create_skin_item(base_path, bp_folder, skin)
        create_attachable(base_path, rp_folder, skin)
        print_success(f"สกิน: {skin.display_name}")

    if not no_ui_mode:
        create_selector_item(base_path, bp_folder, addon_name, selector_id, skins[0].item_id)
        create_air_model(base_path, rp_folder)
        create_selector_attachable(base_path, rp_folder, selector_id)
        print_success("สร้าง Selector item")

    sel = selector_id if not no_ui_mode else None
    create_item_texture(base_path, rp_folder, skins, sel)
    create_lang_file(base_path, rp_folder, addon_name, skins, sel)
    create_item_catalog(base_path, bp_folder)
    create_functions(base_path, bp_folder, addon_name, skins)
    create_terms_file(base_path, addon_name, rp_folder)
    print_success("สร้างไฟล์เสริม (textures, lang, catalog, functions, TERMS)")

    if not no_ui_mode:
        if use_special_ui:
            create_special_ui_script(base_path, bp_folder, addon_name, skins, selector_id, allowed_players, enable_xbox_lock)
            create_special_ui_files(script_dir, base_path, rp_folder)
            print_success("สร้าง Special UI + Script")
        else:
            create_normal_ui_script(base_path, bp_folder, addon_name, skins, selector_id, allowed_players, enable_xbox_lock)
            print_success("สร้าง Normal UI Script")
    else:
        print_success("โหมด No UI - ไม่สร้าง Script และ Selector")

    if no_ui_mode:
        gives = [f"/give @s {FILE_PREFIX}:{s.item_id}" for s in skins]
    else:
        gives = [f"/give @s {FILE_PREFIX}:{selector_id}"]

    print_success("เสร็จสิ้น!")
    return {
        "project_path": base_path,
        "bp_path": os.path.join(base_path, bp_folder),
        "rp_path": os.path.join(base_path, rp_folder),
        "give_commands": gives,
        "log": list(_LOG),
    }
