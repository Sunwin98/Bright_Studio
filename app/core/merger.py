"""Wrap the existing skin_merger.py to combine multiple skin addons into one.

The original file's functions are reused as-is (imported by path); only the
interactive main() is replaced. Emoji prints are captured, not sent to stdout.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil

import config

_MERGER_PATH = str(config.FACTORY_ROOT / "skin_merger.py")
_mod = None


def _load():
    global _mod
    if _mod is None:
        spec = importlib.util.spec_from_file_location("skin_merger_orig", _MERGER_PATH)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _mod = m
    return _mod


def scan_pairs(source_path: str) -> list[dict]:
    m = _load()
    if not os.path.isdir(source_path):
        raise ValueError(f"ไม่พบโฟลเดอร์: {source_path}")
    pairs = m.find_addon_pairs(source_path)
    return [{"name": n, "bp": bp, "rp": rp} for (n, bp, rp) in pairs]


def merge(pairs: list[dict], merged_name: str, output_dir: str | None = None,
          color: str = "§b") -> dict:
    m = _load()
    if len(pairs) < 2:
        raise ValueError("ต้องเลือกอย่างน้อย 2 addon")
    merged_name = (merged_name or f"MergedSkins_{len(pairs)}").strip()

    out_base = output_dir or str(config.FACTORY_ROOT / "Merged")
    os.makedirs(out_base, exist_ok=True)
    folder_name = merged_name.replace(" ", "_")
    merged_path = os.path.join(out_base, folder_name)
    if os.path.exists(merged_path):
        shutil.rmtree(merged_path)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        all_contents = {}
        for p in pairs:
            all_contents[p["name"]] = m.scan_addon_contents(p["bp"], p["rp"])

        bp_folder, rp_folder = m.create_merged_folder_structure(merged_path, folder_name)
        stats = {}
        stats["items"] = m.merge_items(all_contents, merged_path, bp_folder)
        stats["attachables"] = m.merge_attachables(all_contents, merged_path, rp_folder)
        stats["tex_items"] = m.merge_textures(all_contents, merged_path, rp_folder, "textures_items")
        stats["tex_skin"] = m.merge_textures(all_contents, merged_path, rp_folder, "textures_skin")
        stats["models"] = m.merge_models(all_contents, merged_path, rp_folder)
        stats["animations"] = m.merge_animations(all_contents, merged_path, rp_folder)
        m.merge_lang_files(all_contents, merged_path, rp_folder, merged_name)
        m.merge_item_texture_json(all_contents, merged_path, rp_folder, merged_name)
        addon_names = [p["name"] for p in pairs]
        m.create_merged_manifests(merged_path, merged_name, color, len(addon_names), bp_folder, rp_folder)
        try:
            m.copy_pack_icon(str(config.FACTORY_ROOT), merged_path, bp_folder, rp_folder)
        except Exception:
            pass
        try:
            m.create_merged_readme(merged_path, merged_name, addon_names, stats, bp_folder, rp_folder)
        except Exception:
            pass

    log = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return {"merged_path": merged_path, "stats": stats, "log": log,
            "total_files": sum(stats.values())}
