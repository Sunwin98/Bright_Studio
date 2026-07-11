"""Universal addon intake: accept a .mcaddon/.mcpack/.zip file OR a folder and
resolve it into behavior/resource pack paths automatically.

Classification comes from each pack's manifest.json `modules[].type`:
  data / script          -> behavior pack
  resources / skin_pack  -> resource pack

Archives are extracted to a per-source temp dir (keyed by path+mtime) under
%TEMP%/hs_studio_packio so repeat inspections reuse the same extraction.
"""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
import zipfile
from pathlib import Path

ARCHIVE_EXTS = {".mcaddon", ".mcpack", ".zip"}

_BEHAVIOR_TYPES = {"data", "script", "javascript"}
_RESOURCE_TYPES = {"resources", "skin_pack"}


def _load_json(p: Path):
    text = p.read_text(encoding="utf-8-sig")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        text = re.sub(r"//[^\n]*", "", text)
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        return json.loads(text)


def _classify_manifest(mp: Path) -> str | None:
    """'behavior' | 'resource' | None from a manifest.json path."""
    try:
        m = _load_json(mp)
    except Exception:
        return None
    if not isinstance(m, dict):
        return None
    for mod in m.get("modules", []) or []:
        t = str(mod.get("type", "")).lower()
        if t in _BEHAVIOR_TYPES:
            return "behavior"
        if t in _RESOURCE_TYPES:
            return "resource"
    return None


def _pack_name(mp: Path) -> str:
    try:
        m = _load_json(mp)
        name = re.sub(r"§.", "", str(m.get("header", {}).get("name", ""))).strip()
        if name and not name.startswith("pack."):
            return name
    except Exception:
        pass
    return mp.parent.name


def _extract(archive: Path) -> Path:
    """Extract archive to a stable temp dir; reuse if already extracted."""
    stat = archive.stat()
    key = hashlib.sha1(f"{archive}|{stat.st_size}|{stat.st_mtime_ns}".encode()).hexdigest()[:16]
    dest = Path(tempfile.gettempdir()) / "hs_studio_packio" / key
    marker = dest / ".extracted"
    if marker.is_file():
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        # Guard against zip-slip: reject entries escaping dest.
        base = dest.resolve()
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if base not in target.parents and target != base:
                raise ValueError(f"ไฟล์ในแพ็คมี path อันตราย: {info.filename}")
        zf.extractall(dest)
        # Nested .mcpack inside .mcaddon → extract those too.
        for inner in list(dest.rglob("*.mcpack")) + list(dest.rglob("*.zip")):
            inner_dir = inner.with_suffix("")
            try:
                with zipfile.ZipFile(inner) as izf:
                    izf.extractall(inner_dir)
            except Exception:
                continue
    marker.write_text("ok", encoding="utf-8")
    return dest


def _find_packs(root: Path) -> list[dict]:
    """Every pack dir under root (dir containing manifest.json), classified."""
    packs = []
    seen: set[str] = set()
    for mp in sorted(root.rglob("manifest.json")):
        folder = mp.parent
        # Skip manifests nested inside an already-recorded pack (subpacks).
        if any(str(folder).startswith(s) for s in seen):
            continue
        ptype = _classify_manifest(mp)
        if not ptype:
            continue
        seen.add(str(folder))
        packs.append({"type": ptype, "path": str(folder), "name": _pack_name(mp)})
    return packs


def inspect_source(raw: str) -> dict:
    """Resolve a file/folder into {bp_path, rp_path, packs, source}.

    Accepts: .mcaddon/.mcpack/.zip file, a pack folder, or a folder that
    contains packs (e.g. <name>_BP + <name>_RP)."""
    src = Path(raw)
    if not src.exists():
        raise FileNotFoundError(f"ไม่พบ: {raw}")

    if src.is_file():
        if src.suffix.lower() not in ARCHIVE_EXTS:
            raise ValueError(f"รองรับเฉพาะ {', '.join(sorted(ARCHIVE_EXTS))} (ได้ {src.suffix})")
        root = _extract(src)
    else:
        root = src

    packs = _find_packs(root)
    bp = next((p for p in packs if p["type"] == "behavior"), None)
    rp = next((p for p in packs if p["type"] == "resource"), None)
    return {
        "source": str(src),
        "bp_path": bp["path"] if bp else None,
        "rp_path": rp["path"] if rp else None,
        "packs": packs,
    }
