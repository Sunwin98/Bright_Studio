"""Coverage for the replacement Weapon Config Studio workspace."""
from __future__ import annotations

import json
import os
import sys
import zipfile

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, STUDIO)

from app.core.weapon_config import analyze_source, apply_edits, export_addon, read_script  # noqa: E402


def _pack(root):
    bp = os.path.join(root, "demo_BP")
    scripts = os.path.join(bp, "scripts")
    os.makedirs(scripts, exist_ok=True)
    with open(os.path.join(bp, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"format_version": 2, "header": {"name": "demo", "uuid": "a", "version": [1, 0, 0]},
                   "modules": [{"type": "script", "uuid": "b", "version": [1, 0, 0]}]}, f)
    with open(os.path.join(scripts, "config.js"), "w", encoding="utf-8") as f:
        f.write('export const DAMAGE = 7;\nexport const SETTINGS = {\n  COOLDOWN: 40,\n  ENABLED: true,\n  ITEM_ID: "demo:blade"\n};\n')
    with open(os.path.join(scripts, "skill_slash.js"), "w", encoding="utf-8") as f:
        f.write('import { DAMAGE } from "./config.js";\nexport function castSlash(player) {\n  const radius = 8;\n  return DAMAGE + radius;\n}\n')
    with open(os.path.join(scripts, "main.js"), "w", encoding="utf-8") as f:
        f.write('import { castSlash } from "./skill_slash.js";\n')
    return bp


def test_analyze_and_patch_workspace(tmp):
    _pack(tmp)
    result = analyze_source(tmp)
    assert result["summary"] == {"scripts": 3, "skills": 1, "editable_fields": 5}
    config = next(file for file in result["files"] if file["name"] == "config.js")
    damage = next(field for field in config["fields"] if field["name"] == "DAMAGE")
    assert damage["semantic"] == "Damage"

    saved = apply_edits([{**{key: damage[key] for key in ("path", "start", "end", "original")}, "value": 12}])
    assert saved["ok"]
    assert os.path.isfile(saved["saved"][0]["backup"])
    assert "DAMAGE = 12" in open(config["path"], encoding="utf-8").read()
    preview = read_script(config["path"], max_lines=2)
    assert preview["shown_lines"] == 2 and preview["truncated"]


def test_export_addon(tmp):
    _pack(tmp)
    output = os.path.join(tmp, "out.mcaddon")
    result = export_addon(tmp, output)
    assert result["ok"] and os.path.isfile(output)
    with zipfile.ZipFile(output) as archive:
        assert "demo_BP/manifest.json" in archive.namelist()
        assert "demo_BP/scripts/config.js" in archive.namelist()
