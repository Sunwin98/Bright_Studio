"""Visual Script Builder tests."""
import json

from app.core import history, scriptbuilder


def test_build_source_contains_event_condition_and_actions():
    source = scriptbuilder.build_source("item_use", [
        {"type": "condition", "kind": "item", "value": {"item": "demo:sword"}},
        {"type": "action", "kind": "message", "value": {"text": "พร้อม"}},
        {"type": "action", "kind": "sound", "value": {"sound": "random.orb"}},
    ])

    assert "world.afterEvents.itemUse.subscribe" in source
    assert "demo:sword" in source
    assert "พร้อม" in source
    assert "player.playSound" in source


def test_create_script_wires_manifest_and_history(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY_ROOT", tmp_path / ".history")
    bp = tmp_path / "Demo_BP"
    bp.mkdir()
    manifest = bp / "manifest.json"
    manifest.write_text(json.dumps({
        "format_version": 2,
        "header": {"uuid": "b"},
        "modules": [{"type": "data", "uuid": "data"}],
    }), encoding="utf-8")

    result = scriptbuilder.create_script(str(bp), "fire sword", "item_use", [
        {"type": "condition", "kind": "item", "value": {"item": "demo:sword"}},
        {"type": "action", "kind": "message", "value": {"text": "พร้อม"}},
    ])

    assert result["ok"] is True
    assert (bp / "scripts" / "hs_fire_sword.js").exists()
    fixed_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    assert any(module.get("type") == "script" for module in fixed_manifest["modules"])
    assert any(dep.get("module_name") == "@minecraft/server" for dep in fixed_manifest["dependencies"])
    assert history.get_snapshot(result["history_id"])["status"] == "completed"
