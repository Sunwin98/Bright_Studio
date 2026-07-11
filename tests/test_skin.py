"""Equivalence + smoke test for the ported skin factory.

1. Builds a full addon end-to-end into a temp dir and validates key files.
2. Loads the ORIGINAL factory_skin_v3.py and asserts the deterministic
   create_* helpers produce byte-identical JSON to the ported ones.
"""
import importlib.util
import json
import os
import sys
import tempfile

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, STUDIO)

from PIL import Image  # noqa: E402
from app.core.skin_factory import builder  # noqa: E402
from app.core.skin_factory.models import SkinInfo  # noqa: E402

ORIG_PATH = r"D:\heaven send\Heaven_Send_Factory\factory_skin_v3.py"


def load_original():
    spec = importlib.util.spec_from_file_location("factory_skin_v3_orig", ORIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    # prevent the interactive main() from running (guarded by __main__ anyway)
    spec.loader.exec_module(mod)
    return mod


def make_test_skin(path):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    # face region 8,8..16,16
    for x in range(8, 16):
        for y in range(8, 16):
            img.putpixel((x, y), (200, 150, 120, 255))
    img.save(path)


def test_end_to_end(tmp):
    skin_png = os.path.join(tmp, "TestSkin.png")
    make_test_skin(skin_png)
    out = os.path.join(tmp, "out")
    req = {
        "addon_name": "ทดสอบสกิน",
        "ui_mode": "normal",
        "xbox_lock": True,
        "xbox_players": ["PlayerOne"],
        "output_dir": out,
        "skins": [{"skin_path": skin_png, "display_name": "หน้าทดสอบ", "slot": "1"}],
    }
    result = builder.build_addon(req)
    base = result["project_path"]
    assert os.path.isdir(base), "project dir missing"

    # find BP/RP
    bp = [d for d in os.listdir(base) if d.endswith("_BP")][0]
    rp = [d for d in os.listdir(base) if d.endswith("_RP")][0]

    # validate JSON files parse
    checks = [
        os.path.join(base, bp, "manifest.json"),
        os.path.join(base, rp, "manifest.json"),
        os.path.join(base, rp, "textures", "item_texture.json"),
    ]
    for c in checks:
        assert os.path.exists(c), f"missing {c}"
        with open(c, encoding="utf-8") as f:
            json.load(f)

    # script + xbox lock present
    main_js = os.path.join(base, bp, "scripts", "main.js")
    assert os.path.exists(main_js)
    js = open(main_js, encoding="utf-8").read()
    assert "ALLOWED_PLAYERS" in js and "PlayerOne" in js and "Iamsayhi1" in js
    # icon generated
    items_dir = os.path.join(base, rp, "textures", "items")
    pngs = [f for f in os.listdir(items_dir) if f.endswith(".png")]
    assert any("_item.png" in p for p in pngs), "no _item icon"
    print("  end-to-end: OK  ->", base)
    return result


def _same_skininfo(cls):
    return cls(
        name="skin1", display_name="TestX", skin_path="x.png",
        model_path=None, animation_path=None,
        slot_name="helmet", slot_value="slot.armor.head", equip_slot="Head",
        item_id="heaver_testx_ab12", geometry_id="geometry.testx_cd34",
    )


def test_equivalence(tmp, orig):
    """Deterministic create_* helpers must byte-match the original."""
    a = os.path.join(tmp, "orig"); b = os.path.join(tmp, "port")
    for d in (a, b):
        os.makedirs(os.path.join(d, "items"), exist_ok=True)
        os.makedirs(os.path.join(d, "attachables"), exist_ok=True)
        os.makedirs(os.path.join(d, "item_catalog"), exist_ok=True)

    orig_skin = _same_skininfo(orig.SkinInfo)
    port_skin = _same_skininfo(SkinInfo)

    # create_skin_item
    orig.create_skin_item(a, "", orig_skin)
    builder.create_skin_item(b, "", port_skin)
    # create_attachable
    orig.create_attachable(a, "", orig_skin)
    builder.create_attachable(b, "", port_skin)
    # create_item_catalog
    orig.create_item_catalog(a, "")
    builder.create_item_catalog(b, "")

    compared = 0
    for rel in [
        os.path.join("items", f"{orig_skin.item_id}.json"),
        os.path.join("attachables", f"{orig_skin.item_id}.json"),
        os.path.join("item_catalog", "crafting_item_catalog.json"),
        os.path.join("items", "heaver_icon.json"),
    ]:
        pa = os.path.join(a, rel); pb = os.path.join(b, rel)
        assert os.path.exists(pa) and os.path.exists(pb), f"missing {rel}"
        ta = open(pa, encoding="utf-8").read()
        tb = open(pb, encoding="utf-8").read()
        assert ta == tb, f"MISMATCH in {rel}:\n--orig--\n{ta}\n--port--\n{tb}"
        compared += 1
    print(f"  equivalence: OK ({compared} files byte-identical vs original)")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        test_end_to_end(tmp)
        orig = load_original()
        test_equivalence(tmp, orig)
    print("ALL SKIN TESTS PASSED")
