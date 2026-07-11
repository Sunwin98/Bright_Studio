"""Scan the project stores and group loose folders/files into addon projects.

Convention across the workspace: an addon is a `<name>_BP` folder + `<name>_RP`
folder + optional `<name>.mcaddon`. Some projects (esp. in Projects Sillkes) are
a single parent folder holding those inside. Both shapes are grouped here.
"""
from __future__ import annotations

import os
from pathlib import Path

import config

# Noise that isn't a project.
SKIP = {"__pycache__", ".venv", ".git", ".claude", "node_modules", "coverage",
        "send", "Sillkes"}


def _has_icon(paths: dict) -> bool:
    for key in ("bp", "rp", "folder"):
        p = paths.get(key)
        if p and os.path.exists(os.path.join(p, "pack_icon.png")):
            return True
    return False


def _blank(name: str, store: str) -> dict:
    return {
        "name": name,
        "store": store,
        "has_bp": False,
        "has_rp": False,
        "has_mcaddon": False,
        "paths": {},
        "mtime": 0.0,
    }


def _peek_folder(folder: Path, group: dict) -> None:
    """A plain project folder: look one level in for BP/RP/mcaddon markers."""
    try:
        for child in folder.iterdir():
            n = child.name
            if child.is_dir():
                if n.endswith("_BP"):
                    group["has_bp"] = True
                    group["paths"].setdefault("bp", str(child))
                elif n.endswith("_RP"):
                    group["has_rp"] = True
                    group["paths"].setdefault("rp", str(child))
            elif n.lower().endswith(".mcaddon"):
                group["has_mcaddon"] = True
                group["paths"].setdefault("mcaddon", str(child))
    except OSError:
        pass


def scan_projects(stores: list[Path] | None = None) -> list[dict]:
    groups: dict[tuple[str, str], dict] = {}

    for store in (stores if stores is not None else config.PROJECT_STORES):
        if not store.exists():
            continue
        store_name = store.name

        try:
            entries = list(store.iterdir())
        except OSError:
            continue

        for entry in entries:
            name = entry.name
            if name in SKIP or name.startswith("."):
                continue

            try:
                mtime = entry.stat().st_mtime
            except OSError:
                mtime = 0.0

            if entry.is_dir():
                if name.endswith("_BP"):
                    base, flag, key_path = name[:-3], "has_bp", "bp"
                elif name.endswith("_RP"):
                    base, flag, key_path = name[:-3], "has_rp", "rp"
                else:
                    base, flag, key_path = name, None, "folder"

                key = (store_name, base)
                g = groups.setdefault(key, _blank(base, store_name))
                if flag:
                    g[flag] = True
                    g["paths"][key_path] = str(entry)
                else:
                    g["paths"]["folder"] = str(entry)
                    _peek_folder(entry, g)
                g["mtime"] = max(g["mtime"], mtime)

            elif name.lower().endswith(".mcaddon"):
                base = name[:-len(".mcaddon")]
                key = (store_name, base)
                g = groups.setdefault(key, _blank(base, store_name))
                g["has_mcaddon"] = True
                g["paths"]["mcaddon"] = str(entry)
                g["mtime"] = max(g["mtime"], mtime)

    result = []
    for g in groups.values():
        g["open_path"] = (
            g["paths"].get("bp")
            or g["paths"].get("rp")
            or g["paths"].get("folder")
            or g["paths"].get("mcaddon")
        )
        g["has_icon"] = _has_icon(g["paths"])
        result.append(g)

    result.sort(key=lambda g: g["mtime"], reverse=True)
    return result
