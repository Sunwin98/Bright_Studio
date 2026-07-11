"""Weapon tests:
1. generate_script / create_*_entity output byte-identical to the ORIGINAL tool.
2. Full generate() end-to-end on a fake BP+RP.
"""
import importlib.util
import json
import os
import sys
import tempfile

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, STUDIO)

from app.core.weapon import tdc_source as t  # noqa: E402
from app.core.weapon import generator  # noqa: E402

ORIG_PATH = r"D:\Downloads\ท่าโจมตี\สร้างท่าโจมตี+สกิลอาวุธ.py"


def load_original():
    spec = importlib.util.spec_from_file_location("tdc_orig", ORIG_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)  # __main__ guard prevents the GUI from launching
    return m


def test_byte_identical(tmp, orig):
    ident = "tdcmodel:demo_sword"
    dummy = f"{ident}_dummy_entity"
    entity_ids = {"attack": [], "skill": []}

    a = os.path.join(tmp, "orig_bp"); b = os.path.join(tmp, "port_bp")
    for d in (a, b):
        os.makedirs(os.path.join(d, "scripts"), exist_ok=True)

    # generate_script
    fa = orig.generate_script(a, ident, entity_ids, dummy)
    fb = t.generate_script(b, ident, entity_ids, dummy)
    assert fa == fb, f"script filename differs: {fa} vs {fb}"
    ja = open(os.path.join(a, "scripts", fa), encoding="utf-8").read()
    jb = open(os.path.join(b, "scripts", fb), encoding="utf-8").read()
    assert ja == jb, f"JS mismatch (len {len(ja)} vs {len(jb)})"
    assert len(ja) > 50000, "JS unexpectedly small"

    # entities
    orig.create_bp_entity(a, f"{ident}_attack_cube_1")
    t.create_bp_entity(b, f"{ident}_attack_cube_1")
    orig.create_dummy_entity(a, dummy)
    t.create_dummy_entity(b, dummy)
    ra = os.path.join(tmp, "orig_rp"); rb = os.path.join(tmp, "port_rp")
    orig.create_rp_entity(ra, f"{ident}_attack_cube_1")
    t.create_rp_entity(rb, f"{ident}_attack_cube_1")

    fid = ident.replace(":", "_")
    pairs = [
        (os.path.join(a, "entities", f"{fid}_attack_cube_1.json"), os.path.join(b, "entities", f"{fid}_attack_cube_1.json")),
        (os.path.join(a, "entities", f"{fid}_dummy_entity.json"), os.path.join(b, "entities", f"{fid}_dummy_entity.json")),
        (os.path.join(ra, "entity", f"{fid}_attack_cube_1.entity.json"), os.path.join(rb, "entity", f"{fid}_attack_cube_1.entity.json")),
        (os.path.join(ra, "models", "entity", f"{fid}_attack_cube_1.geo.json"), os.path.join(rb, "models", "entity", f"{fid}_attack_cube_1.geo.json")),
    ]
    for pa, pb in pairs:
        assert open(pa, encoding="utf-8").read() == open(pb, encoding="utf-8").read(), f"mismatch {pa}"
    print(f"  byte-identical: OK (JS {len(ja)} bytes + entities match original)")


def make_pack(root, kind):
    os.makedirs(root, exist_ok=True)
    manifest = {"format_version": 2, "header": {"name": kind, "uuid": "00000000-0000-0000-0000-000000000001", "version": [1, 0, 0]},
                "modules": [{"type": "data" if kind == "BP" else "resources", "uuid": "00000000-0000-0000-0000-000000000002", "version": [1, 0, 0]}]}
    json.dump(manifest, open(os.path.join(root, "manifest.json"), "w", encoding="utf-8"), indent="\t")


def test_end_to_end(tmp):
    bp = os.path.join(tmp, "MyWeapon_BP"); rp = os.path.join(tmp, "MyWeapon_RP")
    make_pack(bp, "BP"); make_pack(rp, "RP")
    # an item JSON
    items_dir = os.path.join(bp, "items"); os.makedirs(items_dir, exist_ok=True)
    item = {"format_version": "1.21.10", "minecraft:item": {"description": {"identifier": "tdcmodel:blade"}, "components": {}}}
    ip = os.path.join(items_dir, "blade.json")
    json.dump(item, open(ip, "w", encoding="utf-8"), indent=4)

    opts = {"atk1": True, "atk2": True, "atk3": True, "sk1": True, "sk2": False, "sk3": False,
            "atk1_sec": False, "atk2_sec": False, "atk3_sec": False, "sk1_sec": False, "sk2_sec": False, "sk3_sec": False}
    res = generator.generate(bp, rp, True, True, [ip], opts)
    assert res["count"] == 1
    assert res["scripts"] == ["tdcmodel_tdcmodel_blade.js"]
    assert os.path.exists(os.path.join(bp, "scripts", "tdcmodel_tdcmodel_blade.js"))
    assert os.path.exists(os.path.join(bp, "scripts", "main.js"))
    # attack entities (3) created in BP + RP; skill1 created, skill2/3 not
    assert os.path.exists(os.path.join(bp, "entities", "tdcmodel_blade_attack_cube_1.json"))
    assert os.path.exists(os.path.join(rp, "entity", "tdcmodel_blade_skill_cube_1.entity.json"))
    assert not os.path.exists(os.path.join(bp, "entities", "tdcmodel_blade_skill_cube_2.json"))
    # main.js imports the script
    main_js = open(os.path.join(bp, "scripts", "main.js"), encoding="utf-8").read()
    assert 'import "./tdcmodel_tdcmodel_blade.js";' in main_js
    print("  end-to-end: OK (script + main.js + entities per toggles)")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        test_end_to_end(tmp)
        orig = load_original()
        test_byte_identical(tmp, orig)
    print("ALL WEAPON TESTS PASSED")
