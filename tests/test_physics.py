"""Physics tests: apply each tool on fixtures, validate output, and assert the
extracted classes produce byte-identical JSON to the ORIGINAL scripts.
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, STUDIO)

from app.core.physics import runner  # noqa: E402

PHYS_SRC = r"D:\heaven send\Heaven_Send_Factory\Physics[mvp] final"

ANIM = {
    "format_version": "1.8.0",
    "animations": {
        "animation.test.idle": {
            "loop": True,
            "bones": {
                "Cape1": {"rotation": [0, 0, 0]},
                "Cape2": {"rotation": [0, 0, 0]},
                "Cape3": {"rotation": [0, 0, 0]},
                "Chest1": {"rotation": [0, 0, 0]},
                "Chest2": {"rotation": [0, 0, 0]},
                "Head": {"rotation": [0, 0, 0]},
            },
        }
    },
}
MODEL = {
    "format_version": "1.12.0",
    "minecraft:geometry": [{
        "description": {"identifier": "geometry.test"},
        "bones": [{"name": f"hair_{i}"} for i in range(1, 6)] + [{"name": "Head"}],
    }],
}
ATTACH = {
    "format_version": "1.10.0",
    "minecraft:attachable": {
        "description": {
            "identifier": "test:item", "materials": {"default": "entity_alphatest"},
            "textures": {"default": "t"}, "geometry": {"default": "geometry.test"},
        }
    },
}


def write_fixture(d):
    os.makedirs(d, exist_ok=True)
    ap = os.path.join(d, "anim.json"); mp = os.path.join(d, "model.geo.json"); tp = os.path.join(d, "att.json")
    json.dump(ANIM, open(ap, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    json.dump(MODEL, open(mp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    json.dump(ATTACH, open(tp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return ap, mp, tp


def load_orig():
    mods = {}
    for name in ["back_hair_v2", "back_hair_v2_yaw", "cape_physics", "chest_physics", "head_rotation"]:
        spec = importlib.util.spec_from_file_location(f"orig_{name}", os.path.join(PHYS_SRC, name + ".py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        mods[name] = m
    return mods


def drive_original(mods, tool, ap, mp, tp):
    """Replicate runner._run_tool using the ORIGINAL classes."""
    if tool == "cape":
        g = mods["cape_physics"].CapePhysicsGenerator(); g.load_files(ap, tp); g.cape_intensity = "medium"
        for pre in ["Cape"]:
            g.bone_groups.append({"prefix": pre, "bones": g.find_bones_with_prefix(pre)})
        g.update_attachable_file(g.update_animation_file()); g.save_files()
    elif tool == "chest":
        g = mods["chest_physics"].ChestPhysicsGenerator(); g.load_files(ap, tp)
        for pre in ["Chest"]:
            g.bone_groups.append({"prefix": pre, "bones": g.find_bones_with_prefix(pre)})
        g.update_attachable_file(g.update_animation_file()); g.save_files()
    elif tool == "head":
        g = mods["head_rotation"].HeadRotationGenerator(); g.load_files(ap, tp); g.head_bone_name = "Head"
        h, s = g.update_animation_file(); g.update_attachable_file(h, s); g.save_files()
    elif tool == "back_hair":
        g = mods["back_hair_v2"].BackHairPhysicsGeneratorV2(); g.load_files(ap, mp, tp)
        for pre in ["hair_"]:
            g.bone_groups.append({"prefix": pre, "bones": g.find_bones_with_prefix(pre), "strength_multiplier": None})
        g.update_attachable_file(g.update_animation_file()); g.save_files()
    elif tool == "back_hair_yaw":
        g = mods["back_hair_v2_yaw"].BackHairYawOnlyGenerator(); g.load_files(ap, mp, tp)
        for pre in ["hair_"]:
            g.bone_groups.append({"prefix": pre, "bones": g.find_bones_with_prefix(pre), "strength_multiplier": None})
        g.update_attachable_file(g.update_animation_file()); g.save_files()


TOOL_PREFIX = {"cape": ["Cape"], "chest": ["Chest"], "back_hair": ["hair_"], "back_hair_yaw": ["hair_"]}


def run_case(tool, base, mods):
    port = os.path.join(base, f"{tool}_port"); orig = os.path.join(base, f"{tool}_orig")
    p_ap, p_mp, p_tp = write_fixture(port)
    o_ap, o_mp, o_tp = write_fixture(orig)

    payload = {"tool": tool, "animation_path": p_ap, "model_path": p_mp, "attachable_path": p_tp,
               "prefixes": TOOL_PREFIX.get(tool, []), "bone_name": "Head", "intensity": "medium", "strength": None}
    res = runner.apply(payload)
    assert res["backups"], "no backups made"

    with contextlib.redirect_stdout(io.StringIO()):  # original class prints emoji; console is cp1252
        drive_original(mods, tool, o_ap, o_mp, o_tp)

    for fn in ("anim.json", "att.json"):
        a = open(os.path.join(orig, fn), encoding="utf-8").read()
        b = open(os.path.join(port, fn), encoding="utf-8").read()
        assert a == b, f"[{tool}] MISMATCH in {fn}"
    # basic sanity: output parses and grew
    anim = json.load(open(p_ap, encoding="utf-8"))
    assert len(anim["animations"]) > 1, f"[{tool}] no physics animation added"
    print(f"  {tool}: OK (byte-identical to original, backups={len(res['backups'])})")


if __name__ == "__main__":
    mods = load_orig()
    with tempfile.TemporaryDirectory() as base:
        for tool in ["cape", "chest", "head", "back_hair", "back_hair_yaw"]:
            run_case(tool, base, mods)
    print("ALL PHYSICS TESTS PASSED")
