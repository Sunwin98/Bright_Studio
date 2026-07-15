"""Asset index tests."""
import json

from app.core import assets


def test_asset_scan_indexes_textures_models_and_references(tmp_path):
    root = tmp_path / "Demo"
    bp = root / "Demo_BP"
    rp = root / "Demo_RP"
    (rp / "textures" / "items").mkdir(parents=True)
    (rp / "models" / "entity").mkdir(parents=True)
    bp.mkdir(parents=True)
    (bp / "manifest.json").write_text(json.dumps({"format_version": 2, "header": {"uuid": "b"}, "modules": [{"type": "data", "uuid": "bm"}]}), encoding="utf-8")
    (rp / "manifest.json").write_text(json.dumps({"format_version": 2, "header": {"uuid": "r"}, "modules": [{"type": "resources", "uuid": "rm"}]}), encoding="utf-8")
    (rp / "textures" / "items" / "Sword.png").write_bytes(b"png")
    (rp / "textures" / "item_texture.json").write_text(json.dumps({"texture_data": {"sword": {"textures": "textures/items/Sword"}}}), encoding="utf-8")
    (rp / "models" / "entity" / "sword.geo.json").write_text(json.dumps({"minecraft:geometry": [{"description": {"identifier": "geometry.sword"}, "bones": [{"name": "root"}]}]}), encoding="utf-8")

    result = assets.scan_source(str(root))

    texture = next(item for item in result["assets"] if item["name"] == "Sword.png")
    model = next(item for item in result["assets"] if item["name"] == "sword.geo.json")
    assert texture["kind"] == "texture"
    assert texture["references"][0]["file"] == "textures/item_texture.json"
    assert model["details"]["geometry_ids"] == ["geometry.sword"]
    assert model["details"]["bone_count"] == 1
