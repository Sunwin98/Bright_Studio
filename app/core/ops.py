"""Packaging (.mcaddon) and deploy-to-Minecraft operations."""
from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import config


def make_mcaddon(name: str, bp_path: str | None, rp_path: str | None,
                 output_dir: str | None = None) -> str:
    """Zip the BP and/or RP folders into <name>.mcaddon. Each pack folder sits at
    the archive root (how Minecraft expects a multi-pack .mcaddon)."""
    parts = [(p, os.path.basename(p)) for p in (bp_path, rp_path) if p and os.path.isdir(p)]
    if not parts:
        raise ValueError("ไม่พบโฟลเดอร์ BP หรือ RP ที่จะแพ็ค")

    out_dir = output_dir or os.path.dirname(parts[0][0])
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{name}.mcaddon")

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, arc in parts:
            for root, _dirs, files in os.walk(folder):
                for f in files:
                    fp = os.path.join(root, f)
                    rel = os.path.join(arc, os.path.relpath(fp, folder))
                    z.write(fp, rel)
    return out


def import_mcaddon(mcaddon_path: str, dest_store: str | None = None) -> dict:
    """Unzip a .mcaddon's pack folders (any that contain manifest.json) into a
    project store. Complements make_mcaddon — round-trips a shared/downloaded
    addon back into the workspace so it shows up in the Project Browser."""
    if not mcaddon_path or not os.path.isfile(mcaddon_path):
        raise ValueError(f"ไม่พบไฟล์: {mcaddon_path}")
    if not zipfile.is_zipfile(mcaddon_path):
        raise ValueError("ไฟล์นี้ไม่ใช่ .mcaddon/.zip ที่ถูกต้อง")

    dest_root = Path(dest_store) if dest_store else config.PROJECT_STORES[0]
    dest_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp).resolve()
        with zipfile.ZipFile(mcaddon_path) as z:
            for member in z.namelist():
                target = (tmp_path / member).resolve()
                if tmp_path not in target.parents and target != tmp_path:
                    raise ValueError(f"ไฟล์ zip มีพาธไม่ปลอดภัย: {member}")
            z.extractall(tmp_path)

        packs = sorted({p.parent for p in tmp_path.rglob("manifest.json") if p.parent != tmp_path})
        if not packs:
            raise ValueError("ไม่พบ pack (manifest.json) ในไฟล์นี้")

        imported = []
        for pack_dir in packs:
            dest = dest_root / pack_dir.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(pack_dir, dest)
            imported.append(str(dest))

    return {"imported": imported, "dest_store": str(dest_root)}


def deploy_status() -> dict:
    mj = config.find_com_mojang()
    return {"found": mj is not None, "com_mojang": str(mj) if mj else None}


def _pack_identity(dest: Path, ptype: str) -> dict:
    """Read the just-deployed pack's manifest header so callers can wire it into
    a world (add-to-world flow). Tolerant JSON; never raises."""
    info = {"type": ptype, "name": dest.name, "uuid": None,
            "version": [1, 0, 0], "path": str(dest)}
    mp = dest / "manifest.json"
    if not mp.is_file():
        return info
    try:
        from app.core.filemanager import _load_json
        manifest = _load_json(mp)
        header = manifest.get("header", {}) if isinstance(manifest, dict) else {}
        info["uuid"] = header.get("uuid")
        if header.get("version") is not None:
            info["version"] = header.get("version")
        name = (header.get("name") or "").strip()
        # Ignore unresolved localization tokens (e.g. "pack.name") as a display name.
        if name and not name.startswith("pack."):
            info["name"] = name
    except Exception:
        pass
    return info


def deploy_project(bp_path: str | None, rp_path: str | None) -> dict:
    """Copy BP/RP into Minecraft's development pack folders for in-game testing.

    Response keeps the legacy `deployed` (list of dest path strings) and
    `com_mojang`, and adds `deployed_packs` — pack identities read from each
    deployed manifest so the caller can add them straight into a world."""
    mj = config.find_com_mojang()
    if mj is None:
        raise ValueError(
            "หา com.mojang ไม่เจอ — ติดตั้ง Minecraft Bedrock ก่อน "
            "หรือกำหนด MC_COM_MOJANG_OVERRIDE ใน config.py"
        )

    deployed = []
    deployed_packs = []
    jobs = []
    if bp_path and os.path.isdir(bp_path):
        jobs.append((bp_path, mj / "development_behavior_packs", "behavior"))
    if rp_path and os.path.isdir(rp_path):
        jobs.append((rp_path, mj / "development_resource_packs", "resource"))
    if not jobs:
        raise ValueError("ไม่พบโฟลเดอร์ BP หรือ RP ที่จะ deploy")

    for src, dest_root, ptype in jobs:
        dest_root.mkdir(parents=True, exist_ok=True)
        dest = dest_root / os.path.basename(src)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        deployed.append(str(dest))
        deployed_packs.append(_pack_identity(dest, ptype))

    return {"deployed": deployed, "deployed_packs": deployed_packs, "com_mojang": str(mj)}
