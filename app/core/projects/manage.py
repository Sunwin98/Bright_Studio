"""Project management ops: rename / delete / duplicate / size / thumbnail.

Every path is validated to live under a configured project store before any
destructive action, so a crafted request can't touch the rest of the disk.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import config


def _stores() -> list[Path]:
    stores = list(config.PROJECT_STORES)
    for zone_stores in getattr(config, "ZONE_STORES", {}).values():
        stores.extend(zone_stores)
    return [s.resolve() for s in stores]


def _under_stores(p: Path) -> bool:
    p = p.resolve()
    for s in _stores():
        try:
            p.relative_to(s)
            return True
        except ValueError:
            continue
    return False


def _suffix_of(name: str) -> str:
    if name.endswith("_BP"):
        return "_BP"
    if name.endswith("_RP"):
        return "_RP"
    if name.lower().endswith(".mcaddon"):
        return ".mcaddon"
    return ""


def _existing_paths(paths: dict) -> list[str]:
    out = []
    for key in ("bp", "rp", "mcaddon", "folder"):
        p = paths.get(key)
        if p and os.path.exists(p):
            out.append(p)
    return out


def folder_size(path: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def project_info(paths: dict) -> dict:
    size = 0
    icon = None
    for p in _existing_paths(paths):
        if os.path.isdir(p):
            size += folder_size(p)
            cand = os.path.join(p, "pack_icon.png")
            if icon is None and os.path.exists(cand):
                icon = cand
        else:
            try:
                size += os.path.getsize(p)
            except OSError:
                pass
    return {"size_bytes": size, "icon_path": icon}


def find_icon(paths: dict) -> str | None:
    for key in ("bp", "rp", "folder"):
        p = paths.get(key)
        if p:
            cand = os.path.join(p, "pack_icon.png")
            if os.path.exists(cand):
                return cand
    return None


def delete_project(paths: list[str]) -> dict:
    removed = []
    for p in paths:
        path = Path(p)
        if not _under_stores(path):
            raise ValueError(f"ปฏิเสธ: พาธอยู่นอก project store — {p}")
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(str(path))
    return {"removed": removed}


def _validate_name(name: str) -> str:
    name = name.strip()
    if not name or any(c in name for c in '\\/:*?"<>|'):
        raise ValueError("ชื่อใหม่ไม่ถูกต้อง")
    return name


def rename_project(paths: dict, new_name: str) -> dict:
    new_name = _validate_name(new_name)
    renamed = []
    for p in _existing_paths(paths):
        src = Path(p)
        if not _under_stores(src):
            raise ValueError(f"ปฏิเสธ: พาธอยู่นอก project store — {p}")
        dst = src.with_name(new_name + _suffix_of(src.name))
        if dst.exists():
            raise ValueError(f"มีอยู่แล้ว: {dst.name}")
        src.rename(dst)
        renamed.append(str(dst))
    return {"renamed": renamed}


def duplicate_project(paths: dict, new_name: str) -> dict:
    new_name = _validate_name(new_name)
    created = []
    for p in _existing_paths(paths):
        src = Path(p)
        if not _under_stores(src):
            raise ValueError(f"ปฏิเสธ: พาธอยู่นอก project store — {p}")
        dst = src.with_name(new_name + _suffix_of(src.name))
        if dst.exists():
            raise ValueError(f"มีอยู่แล้ว: {dst.name}")
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        created.append(str(dst))
    return {"created": created}
