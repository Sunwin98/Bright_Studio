"""Minecraft Bedrock com.mojang scanner for the File Manager.

Pure logic (no FastAPI). Reads pack manifests, worlds, and a world's applied
add-ons. The API layer (app/api/filemanager.py) wraps these and enforces the
path sandbox before any destructive/reveal action.
"""
from __future__ import annotations

import json
from pathlib import Path

PACK_DIRS = {
    "behavior": "behavior_packs",
    "resource": "resource_packs",
}
WORLDS_DIR = "minecraftWorlds"


def _load_json(p: Path):
    """Tolerant JSON read: strips BOM, ignores // line comments and trailing
    commas that some hand-edited Bedrock manifests contain."""
    text = p.read_text(encoding="utf-8-sig")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re
        text = re.sub(r"//[^\n]*", "", text)
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        return json.loads(text)


def _strip_mc_codes(s: str) -> str:
    """Remove Minecraft § formatting codes (e.g. §c, §l) from a display name."""
    import re
    return re.sub(r"§.", "", s).strip()


def _lang_name(folder: Path) -> str | None:
    """Resolve a localized pack name from texts/*.lang (`pack.name=...`)."""
    texts = folder / "texts"
    if not texts.is_dir():
        return None
    candidates = [texts / "th_TH.lang", texts / "en_US.lang"]
    candidates += sorted(p for p in texts.glob("*.lang") if p not in candidates)
    for lf in candidates:
        if not lf.is_file():
            continue
        try:
            for line in lf.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                if line.strip().startswith("pack.name"):
                    _, _, val = line.partition("=")
                    val = _strip_mc_codes(val.strip())
                    if val:
                        return val
        except OSError:
            continue
    return None


def _manifest_name(manifest: dict, folder: Path) -> str:
    header = manifest.get("header", {}) if isinstance(manifest, dict) else {}
    name = _strip_mc_codes((header.get("name") or "").strip())
    # Localization tokens (e.g. "pack.name") can't be shown as-is → try the
    # pack's texts/*.lang first, then fall back to the folder name.
    if not name or (" " not in name and "." in name) or name.startswith("pack."):
        return _lang_name(folder) or folder.name
    return name


def _version_str(header: dict) -> str:
    v = header.get("version")
    if isinstance(v, list):
        return ".".join(str(x) for x in v)
    return str(v) if v is not None else "?"


def _read_pack(folder: Path, ptype: str) -> dict | None:
    mp = folder / "manifest.json"
    if not mp.is_file():
        return None
    try:
        manifest = _load_json(mp)
    except Exception:
        return {"name": folder.name, "uuid": None, "version": "?",
                "type": ptype, "path": str(folder), "icon": None, "broken": True}
    header = manifest.get("header", {}) if isinstance(manifest, dict) else {}
    icon = folder / "pack_icon.png"
    return {
        "name": _manifest_name(manifest, folder),
        "uuid": header.get("uuid"),
        "version": _version_str(header),
        "raw_version": header.get("version", [1,0,0]),
        "type": ptype,
        "path": str(folder),
        "icon": str(icon) if icon.is_file() else None,
    }


def list_packs(mojang_root: Path) -> list[dict]:
    """All behavior + resource packs installed in a profile."""
    out: list[dict] = []
    for ptype, sub in PACK_DIRS.items():
        base = mojang_root / sub
        if not base.is_dir():
            continue
        for folder in sorted(base.iterdir()):
            if folder.is_dir():
                pack = _read_pack(folder, ptype)
                if pack:
                    out.append(pack)
    return out


def list_worlds(mojang_root: Path) -> list[dict]:
    base = mojang_root / WORLDS_DIR
    if not base.is_dir():
        return []
    out: list[dict] = []
    for folder in sorted(base.iterdir()):
        if not folder.is_dir():
            continue
        name_file = folder / "levelname.txt"
        name = folder.name
        if name_file.is_file():
            try:
                name = name_file.read_text(encoding="utf-8").strip() or folder.name
            except Exception:
                pass
        icon = folder / "world_icon.jpeg"
        # Deliberately avoid recursive dir-size here: with dozens of large worlds
        # an rglob over each folder makes the listing take seconds. Folder mtime
        # (last played) is O(1) and more useful anyway.
        try:
            mtime = folder.stat().st_mtime
        except OSError:
            mtime = 0
        out.append({
            "name": name,
            "path": str(folder),
            "icon": str(icon) if icon.is_file() else None,
            "mtime": mtime,
        })
    # Most recently played first.
    out.sort(key=lambda w: w["mtime"], reverse=True)
    return out


def uuid_name_map(mojang_roots) -> dict[str, str]:
    """Build uuid→pack name across one or more com.mojang roots. Worlds and their
    packs can live in different profiles (e.g. Shared), so callers should pass
    every root to resolve names reliably."""
    if isinstance(mojang_roots, Path):
        mojang_roots = [mojang_roots]
    m: dict[str, str] = {}
    for root in mojang_roots:
        for pack in list_packs(root):
            if pack.get("uuid"):
                m[str(pack["uuid"]).lower()] = pack["name"]
    return m


def world_addons(world_path: Path, all_packs: list[dict]) -> dict:
    installed_map = {str(p.get("uuid")).lower(): p for p in all_packs if p.get("uuid")}
    
    def resolve(fname: str, ptype: str) -> list[dict]:
        fp = world_path / fname
        applied_uuids = set()
        rows = []
        
        if fp.is_file():
            try:
                entries = _load_json(fp)
            except Exception:
                entries = []
            if isinstance(entries, list):
                for e in entries:
                    if not isinstance(e, dict):
                        continue
                    uuid = str(e.get("pack_id", "")).lower()
                    ver = e.get("version")
                    applied_uuids.add(uuid)
                    
                    if uuid in installed_map:
                        name = installed_map[uuid]["name"]
                    else:
                        name = "(ไม่ทราบชื่อ / ไม่ได้ติดตั้ง)"
                        
                    rows.append({
                        "uuid": e.get("pack_id"),
                        "name": name,
                        "version": ".".join(str(x) for x in ver) if isinstance(ver, list) else str(ver),
                        "raw_version": ver,
                        "type": ptype,
                        "installed": uuid in installed_map,
                        "applied": True
                    })
        
        for pack in all_packs:
            if pack.get("type") == ptype:
                uuid = str(pack.get("uuid", "")).lower()
                if uuid not in applied_uuids:
                    rows.append({
                        "uuid": pack.get("uuid"),
                        "name": pack.get("name"),
                        "version": pack.get("version"),
                        "raw_version": pack.get("raw_version", [1,0,0]), 
                        "type": ptype,
                        "installed": True,
                        "applied": False
                    })
        
        return rows

    return {
        "behavior": resolve("world_behavior_packs.json", "behavior"),
        "resource": resolve("world_resource_packs.json", "resource"),
    }

def toggle_world_addon(world_path: Path, ptype: str, pack_id: str, version: list, action: str) -> None:
    filename = f"world_{ptype}_packs.json"
    fp = world_path / filename
    entries = []
    if fp.is_file():
        try:
            entries = _load_json(fp)
        except Exception:
            entries = []
        if not isinstance(entries, list):
            entries = []
    
    if action == "enable":
        exists = any(str(e.get("pack_id", "")).lower() == pack_id.lower() for e in entries if isinstance(e, dict))
        if not exists:
            entries.append({"pack_id": pack_id, "version": version})
    elif action == "disable":
        entries = [e for e in entries if isinstance(e, dict) and str(e.get("pack_id", "")).lower() != pack_id.lower()]
    else:
        raise ValueError("action must be enable or disable")
    
    if fp.is_file():
        import shutil
        shutil.copy2(fp, fp.with_suffix(".json.bak"))
    
    fp.write_text(json.dumps(entries, indent=4), encoding="utf-8")

