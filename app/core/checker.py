"""Addon validator — catches the "fails silently" mistakes before they hit the
game: bad JSON, manifest/UUID problems, missing script entry, broken icon and
geometry references.

Low-false-positive by design: only flags things that are almost certainly wrong.
Vanilla-looking geometry ids and non-item texture refs are skipped.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

VANILLA_GEO_PREFIXES = ("geometry.humanoid", "geometry.item", "geometry.cube",
                        "geometry.player", "geometry.armor", "geometry.cape")


def _issue(level, msg, file=None):
    return {"level": level, "message": msg, "file": file}


def _walk_json(root: Path):
    for p in root.rglob("*.json"):
        yield p


def _rel(root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def _load(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _check_manifest(pack: Path, label: str, issues: list, uuids: dict):
    mp = pack / "manifest.json"
    if not mp.exists():
        issues.append(_issue("error", f"{label}: ไม่พบ manifest.json", "manifest.json"))
        return None
    try:
        data = _load(mp)
    except Exception as e:
        issues.append(_issue("error", f"{label}: manifest.json อ่านไม่ได้ ({e})", "manifest.json"))
        return None

    if "format_version" not in data:
        issues.append(_issue("error", f"{label}: manifest ไม่มี format_version", "manifest.json"))
    header = data.get("header", {})
    if not header.get("uuid"):
        issues.append(_issue("error", f"{label}: manifest header ไม่มี uuid", "manifest.json"))
    else:
        uuids.setdefault(header["uuid"], []).append(f"{label} header")
    if "min_engine_version" not in header:
        issues.append(_issue("warn", f"{label}: header ไม่มี min_engine_version", "manifest.json"))
    for m in data.get("modules", []):
        u = m.get("uuid")
        if not u:
            issues.append(_issue("error", f"{label}: module ({m.get('type')}) ไม่มี uuid", "manifest.json"))
        else:
            uuids.setdefault(u, []).append(f"{label} module:{m.get('type')}")
    return data


def _check_json_parse(pack: Path, label: str, issues: list):
    for p in _walk_json(pack):
        try:
            _load(p)
        except Exception as e:
            issues.append(_issue("error", f"{label}: JSON เสีย — {e}", _rel(pack, p)))


def _check_script_entry(bp: Path, bp_manifest, issues):
    if not bp_manifest:
        return
    for m in bp_manifest.get("modules", []):
        if m.get("type") == "script":
            entry = m.get("entry", "")
            if entry and not (bp / entry).exists():
                issues.append(_issue("error", f"BP: script entry ไม่พบไฟล์ '{entry}'", "manifest.json"))


def _check_dependency(bp_manifest, rp_manifest, issues):
    if not bp_manifest or not rp_manifest:
        return
    rp_uuid = rp_manifest.get("header", {}).get("uuid")
    deps = bp_manifest.get("dependencies", [])
    dep_uuids = {d.get("uuid") for d in deps if d.get("uuid")}
    if rp_uuid and rp_uuid not in dep_uuids:
        issues.append(_issue("warn", "BP ไม่ได้ depend RP uuid — อาจโหลด RP ไม่พร้อมกัน", "manifest.json"))
    has_script = any(m.get("type") == "script" for m in bp_manifest.get("modules", []))
    dep_modules = {d.get("module_name") for d in deps if d.get("module_name")}
    if has_script and "@minecraft/server" not in dep_modules:
        issues.append(_issue("error", "BP มี script module แต่ไม่ได้ depend '@minecraft/server'", "manifest.json"))


def _check_item_textures(rp: Path, issues):
    itp = rp / "textures" / "item_texture.json"
    if not itp.exists():
        return
    try:
        data = _load(itp)
    except Exception:
        return
    for key, val in (data.get("texture_data") or {}).items():
        refs = val.get("textures")
        refs = [refs] if isinstance(refs, str) else (refs or [])
        for ref in refs:
            if not _texture_exists(rp, ref):
                issues.append(_issue("error", f"item_texture '{key}' ชี้ไป '{ref}' ที่ไม่มีไฟล์",
                                     "textures/item_texture.json"))


def _texture_exists(rp: Path, ref: str) -> bool:
    for ext in (".png", ".tga", ".jpg"):
        if (rp / (ref + ext)).exists():
            return True
    return (rp / ref).exists()


def _collect_geometry_ids(rp: Path) -> set:
    ids = set()
    models = rp / "models"
    if not models.exists():
        return ids
    for p in models.rglob("*.json"):
        try:
            data = _load(p)
        except Exception:
            continue
        for g in data.get("minecraft:geometry", []) or []:
            ident = g.get("description", {}).get("identifier")
            if ident:
                ids.add(ident)
    return ids


def _check_geometry_refs(rp: Path, issues):
    defined = _collect_geometry_ids(rp)
    for sub in ("attachables", "entity"):
        d = rp / sub
        if not d.exists():
            continue
        for p in d.rglob("*.json"):
            try:
                data = _load(p)
            except Exception:
                continue
            desc = None
            if "minecraft:attachable" in data:
                desc = data["minecraft:attachable"].get("description", {})
            elif "minecraft:client_entity" in data:
                desc = data["minecraft:client_entity"].get("description", {})
            if not desc:
                continue
            for _slot, ref in (desc.get("geometry") or {}).items():
                if not ref or ref.startswith(VANILLA_GEO_PREFIXES) or ref == "geometry.default":
                    continue
                if ref not in defined:
                    issues.append(_issue("warn", f"geometry '{ref}' ถูกอ้างแต่ไม่พบใน models/",
                                         _rel(rp, p)))


def check_addon(bp_path: str | None, rp_path: str | None) -> dict:
    issues: list = []
    uuids: dict = {}

    bp = Path(bp_path) if bp_path else None
    rp = Path(rp_path) if rp_path else None

    bp_manifest = rp_manifest = None
    if bp and bp.exists():
        _check_json_parse(bp, "BP", issues)
        bp_manifest = _check_manifest(bp, "BP", issues, uuids)
        _check_script_entry(bp, bp_manifest, issues)
    elif bp_path:
        issues.append(_issue("error", f"ไม่พบโฟลเดอร์ BP: {bp_path}"))

    if rp and rp.exists():
        _check_json_parse(rp, "RP", issues)
        rp_manifest = _check_manifest(rp, "RP", issues, uuids)
        _check_item_textures(rp, issues)
        _check_geometry_refs(rp, issues)
    elif rp_path:
        issues.append(_issue("error", f"ไม่พบโฟลเดอร์ RP: {rp_path}"))

    _check_dependency(bp_manifest, rp_manifest, issues)

    for u, where in uuids.items():
        if len(where) > 1:
            issues.append(_issue("error", f"UUID ซ้ำ {u} ใช้ที่: {', '.join(where)}", "manifest.json"))

    errors = sum(1 for i in issues if i["level"] == "error")
    warns = sum(1 for i in issues if i["level"] == "warn")
    return {"ok": errors == 0, "errors": errors, "warnings": warns, "issues": issues}
