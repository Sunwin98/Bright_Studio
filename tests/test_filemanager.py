"""File Manager tests: scanner reads packs/worlds from a fake com.mojang tree,
world add-on names resolve across profiles, and the API path guard rejects
anything outside a com.mojang root.
"""
import json
import os
import sys

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, STUDIO)

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from app.core import filemanager as fm  # noqa: E402
import app.api.filemanager as fmapi  # noqa: E402


def _make_pack(root, sub, folder, name, uuid, version=(1, 0, 0)):
    p = root / sub / folder
    p.mkdir(parents=True)
    (p / "manifest.json").write_text(json.dumps({
        "header": {"name": name, "uuid": uuid, "version": list(version)}
    }), encoding="utf-8")
    (p / "pack_icon.png").write_bytes(b"\x89PNG\r\n")
    return p


def _mojang(tmp_path):
    root = tmp_path / "com.mojang"
    _make_pack(root, "behavior_packs", "AbelBP", "§cAbel Skills BP", "aaa-bp")
    _make_pack(root, "resource_packs", "AbelRP", "pack.name", "aaa-rp")  # token -> folder name
    return root


def test_list_packs(tmp_path):
    root = _mojang(tmp_path)
    packs = fm.list_packs(root)
    names = {p["name"] for p in packs}
    # color code stripped; localization token falls back to folder name
    assert "Abel Skills BP" in names
    assert "AbelRP" in names
    assert {p["type"] for p in packs} == {"behavior", "resource"}
    assert all(p["icon"] and p["icon"].endswith("pack_icon.png") for p in packs)


def test_list_worlds(tmp_path):
    root = tmp_path / "com.mojang"
    w = root / "minecraftWorlds" / "WORLD1"
    w.mkdir(parents=True)
    (w / "levelname.txt").write_text("My Cool World", encoding="utf-8")
    worlds = fm.list_worlds(root)
    assert len(worlds) == 1
    assert worlds[0]["name"] == "My Cool World"
    assert "mtime" in worlds[0]


def test_world_addons_resolves_names(tmp_path):
    root = _mojang(tmp_path)
    w = root / "minecraftWorlds" / "W"
    w.mkdir(parents=True)
    (w / "world_behavior_packs.json").write_text(json.dumps([
        {"pack_id": "aaa-bp", "version": [1, 0, 0]},
        {"pack_id": "missing-uuid", "version": [2, 0, 0]},
    ]), encoding="utf-8")
    all_packs = fm.list_packs(root)
    res = fm.world_addons(w, all_packs)
    bp = res["behavior"]
    assert bp[0]["name"] == "Abel Skills BP" and bp[0]["installed"] is True
    assert bp[1]["installed"] is False


def test_guard_rejects_outside(tmp_path, monkeypatch):
    root = _mojang(tmp_path)
    monkeypatch.setattr(fmapi, "_roots", lambda: [root.resolve()])
    # inside is fine
    inside, got_root = fmapi._guard(str(root / "behavior_packs" / "AbelBP"))
    assert got_root == root.resolve()
    # outside is rejected
    with pytest.raises(HTTPException) as ei:
        fmapi._guard(str(tmp_path.parent / "somewhere_else"))
    assert ei.value.status_code == 400
