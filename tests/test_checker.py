"""Addon checker auto-fix tests."""
import json
import zipfile

from app.core import checker


def test_fix_addon_repairs_safe_manifest_fields_and_dependency(tmp_path):
    bp = tmp_path / "Demo_BP"
    rp = tmp_path / "Demo_RP"
    bp.mkdir()
    rp.mkdir()

    (bp / "manifest.json").write_text(json.dumps({
        "header": {"name": "Demo BP", "version": [1, 0, 0]},
        "modules": [{"type": "data"}],
    }), encoding="utf-8")
    (rp / "manifest.json").write_text(json.dumps({
        "format_version": 2,
        "header": {
            "name": "Demo RP",
            "version": [1, 0, 0],
        },
        "modules": [{"type": "resources"}],
    }), encoding="utf-8")

    result = checker.fix_addon(str(bp), str(rp))

    assert result["changed"] is True
    assert len(result["backups"]) == 2
    assert result["check"]["errors"] == 0
    assert not [issue for issue in result["check"]["issues"] if issue.get("fixable")]
    fixed_bp = json.loads((bp / "manifest.json").read_text(encoding="utf-8"))
    fixed_rp = json.loads((rp / "manifest.json").read_text(encoding="utf-8"))
    assert fixed_bp["dependencies"][0]["uuid"] == fixed_rp["header"]["uuid"]


def test_fix_addon_does_not_modify_when_only_manual_issues_exist(tmp_path):
    bp = tmp_path / "Demo_BP"
    bp.mkdir()
    manifest = bp / "manifest.json"
    manifest.write_text(json.dumps({
        "format_version": 2,
        "header": {"uuid": "11111111-1111-1111-1111-111111111111"},
        "modules": [{"type": "script", "uuid": "33333333-3333-3333-3333-333333333333", "entry": "missing.js"}],
    }), encoding="utf-8")

    result = checker.fix_addon(str(bp), None)

    assert result["changed"] is False
    assert result["backups"] == []
    assert "missing.js" in manifest.read_text(encoding="utf-8")


def test_fix_source_replaces_original_mcaddon_and_keeps_backup(tmp_path):
    archive = tmp_path / "Demo.mcaddon"
    bp = {
        "header": {"name": "Demo BP", "version": [1, 0, 0]},
        "modules": [{"type": "data"}],
    }
    rp = {
        "format_version": 2,
        "header": {"name": "Demo RP", "version": [1, 0, 0]},
        "modules": [{"type": "resources"}],
    }
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("Demo_BP/manifest.json", json.dumps(bp))
        output.writestr("Demo_RP/manifest.json", json.dumps(rp))

    result = checker.fix_source(str(archive))

    assert result["source_replaced"] is True
    assert (tmp_path / "Demo.mcaddon.autofix.bak").exists()
    with zipfile.ZipFile(archive) as fixed:
        fixed_bp = json.loads(fixed.read("Demo_BP/manifest.json"))
    assert fixed_bp["format_version"] == 2
    assert result["check"]["errors"] == 0


def test_checker_suggests_and_repairs_case_sensitive_texture_path(tmp_path):
    rp = tmp_path / "Demo_RP"
    texture_dir = rp / "textures" / "Items"
    texture_dir.mkdir(parents=True)
    (rp / "manifest.json").write_text(json.dumps({
        "format_version": 2,
        "header": {"uuid": "22222222-2222-2222-2222-222222222222"},
        "modules": [{"type": "resources", "uuid": "44444444-4444-4444-4444-444444444444"}],
    }), encoding="utf-8")
    (texture_dir / "Sword.png").write_bytes(b"png")
    texture_json = rp / "textures" / "item_texture.json"
    texture_json.write_text(json.dumps({
        "texture_data": {"sword": {"textures": "textures/items/sword"}},
    }), encoding="utf-8")

    before = checker.check_addon(None, str(rp))
    issue = next(item for item in before["issues"] if item.get("repair"))
    assert issue["fixable"] is True
    assert issue["repair"]["to"] == "textures/Items/Sword"

    result = checker.fix_addon(None, str(rp))

    assert result["changed"] is True
    assert result["changes"][0]["fix_id"] == "repair_texture_path"
    fixed = json.loads(texture_json.read_text(encoding="utf-8"))
    assert fixed["texture_data"]["sword"]["textures"] == "textures/Items/Sword"
    assert result["check"]["errors"] == 0


def test_checker_requires_selection_when_texture_candidates_are_ambiguous(tmp_path):
    rp = tmp_path / "Demo_RP"
    (rp / "textures" / "items_a").mkdir(parents=True)
    (rp / "textures" / "items_b").mkdir(parents=True)
    (rp / "manifest.json").write_text(json.dumps({
        "format_version": 2,
        "header": {"uuid": "55555555-5555-5555-5555-555555555555"},
        "modules": [{"type": "resources", "uuid": "66666666-6666-6666-6666-666666666666"}],
    }), encoding="utf-8")
    (rp / "textures" / "items_a" / "Sword.png").write_bytes(b"a")
    (rp / "textures" / "items_b" / "Sword.png").write_bytes(b"b")
    texture_json = rp / "textures" / "item_texture.json"
    texture_json.write_text(json.dumps({
        "texture_data": {"sword": {"textures": "textures/missing/Sword"}},
    }), encoding="utf-8")

    before = checker.check_addon(None, str(rp))
    issue = next(item for item in before["issues"] if item.get("repair"))
    assert issue.get("fixable") is not True
    assert len(issue["repair"]["candidates"]) == 2

    result = checker.fix_addon(None, str(rp))

    assert result["changed"] is False
    assert texture_json.read_text(encoding="utf-8").find("missing/Sword") >= 0


def test_fix_source_rebuilds_archive_for_texture_path_repair(tmp_path):
    archive = tmp_path / "TextureFix.mcpack"
    rp_manifest = {
        "format_version": 2,
        "header": {"uuid": "77777777-7777-7777-7777-777777777777"},
        "modules": [{"type": "resources", "uuid": "88888888-8888-8888-8888-888888888888"}],
    }
    item_texture = {"texture_data": {"sword": {"textures": "textures/items/sword"}}}
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("Demo_RP/manifest.json", json.dumps(rp_manifest))
        output.writestr("Demo_RP/textures/Items/Sword.png", b"png")
        output.writestr("Demo_RP/textures/item_texture.json", json.dumps(item_texture))

    result = checker.fix_source(str(archive))

    assert result["source_replaced"] is True
    assert (tmp_path / "TextureFix.mcpack.autofix.bak").exists()
    with zipfile.ZipFile(archive) as fixed:
        repaired = json.loads(fixed.read("Demo_RP/textures/item_texture.json"))
    assert repaired["texture_data"]["sword"]["textures"] == "textures/Items/Sword"
    assert result["check"]["errors"] == 0
