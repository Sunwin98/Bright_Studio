"""Hot-sync a saved Script Lab file into any deployed copy of its pack.

After a save, if the edited script belongs to a pack that is ALSO deployed under
a com.mojang `development_behavior_packs` (or `behavior_packs`), copy the saved
file onto the deployed copy so the user only has to type `/reload` in-game.

Pure logic, no FastAPI. Never raises — failures come back as `{"error": ...}`.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import config
from app.core.filemanager import _load_json

_SCAN_SUBDIRS = ("development_behavior_packs", "behavior_packs")


def _find_pack_root(js_path: Path) -> Path | None:
    """Nearest ancestor dir of the js file that contains a manifest.json."""
    for parent in js_path.parents:
        if (parent / "manifest.json").is_file():
            return parent
    return None


def _pack_uuid(pack_root: Path) -> str | None:
    mp = pack_root / "manifest.json"
    if not mp.is_file():
        return None
    try:
        manifest = _load_json(mp)
    except Exception:
        return None
    header = manifest.get("header", {}) if isinstance(manifest, dict) else {}
    uuid = header.get("uuid")
    return str(uuid).lower() if uuid else None


def sync_to_dev(js_path: str) -> dict:
    """Copy the saved file onto every matching deployed pack copy.

    Returns {"synced": [target paths], "already_in_game": bool}. If the file
    isn't inside a manifest'd pack → {"synced": []}. If the pack root itself
    already lives under a com.mojang root → {"already_in_game": True, "synced": []}.
    """
    try:
        p = Path(js_path).resolve()
        pack_root = _find_pack_root(p)
        if pack_root is None:
            return {"synced": []}
        pack_root = pack_root.resolve()

        profile_roots: list[Path] = []
        for prof in config.find_profiles():
            try:
                profile_roots.append(Path(prof["path"]).resolve())
            except Exception:
                continue

        # If the pack we just edited *is* the in-game copy, nothing to sync.
        for root in profile_roots:
            if pack_root == root or root in pack_root.parents:
                return {"already_in_game": True, "synced": []}

        uuid = _pack_uuid(pack_root)
        if not uuid:
            return {"synced": []}

        rel = p.relative_to(pack_root)

        synced: list[str] = []
        seen: set[str] = set()
        for root in profile_roots:
            for sub in _SCAN_SUBDIRS:
                base = root / sub
                if not base.is_dir():
                    continue
                for mp in base.glob("*/manifest.json"):
                    deployed_root = mp.parent.resolve()
                    if deployed_root == pack_root:
                        continue  # don't copy onto ourselves
                    if _pack_uuid(deployed_root) != uuid:
                        continue
                    target = deployed_root / rel
                    key = str(target).lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    try:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(p, target)
                        synced.append(str(target))
                    except OSError:
                        continue

        return {"synced": synced, "already_in_game": False}
    except Exception as e:  # defensive: sync must never break a save
        return {"synced": [], "error": str(e)}
