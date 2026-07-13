"""OBJ -> Bedrock poly_mesh geo.json converter."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.modelgen.obj_to_geo import convert_obj_to_geo

# a unit cube (8 verts, 12 tris via quads), with uvs + normals
CUBE = """
# unit cube
v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
v 0 0 1
v 1 0 1
v 1 1 1
v 0 1 1
vt 0 0
vt 1 0
vt 1 1
vt 0 1
vn 0 0 -1
vn 0 0 1
f 1/1/1 2/2/1 3/3/1 4/4/1
f 5/1/2 8/4/2 7/3/2 6/2/2
"""


def _geo():
    return convert_obj_to_geo(CUBE, "test_model", texture_width=64, texture_height=64,
                              target_size=16.0, face_forward=False)


def test_structure():
    g = _geo()
    assert g["format_version"] == "1.16.0"
    geo = g["minecraft:geometry"][0]
    assert geo["description"]["identifier"] == "geometry.test_model"
    assert geo["description"]["texture_width"] == 64
    pm = geo["bones"][0]["poly_mesh"]
    assert pm["normalized_uvs"] is True
    assert len(pm["positions"]) == 8


def test_quads_triangulated():
    pm = _geo()["minecraft:geometry"][0]["bones"][0]["poly_mesh"]
    # 2 quads -> 4 triangles
    assert len(pm["polys"]) == 4
    for poly in pm["polys"]:
        assert len(poly) == 3          # triangles
        for vert in poly:
            assert len(vert) == 3      # [pos, normal, uv]


def test_scale_and_center():
    pm = _geo()["minecraft:geometry"][0]["bones"][0]["poly_mesh"]
    xs = [p[0] for p in pm["positions"]]
    ys = [p[1] for p in pm["positions"]]
    # tallest dim scaled to 16 units
    assert abs((max(xs) - min(xs)) - 16.0) < 0.01
    # centered on X -> symmetric about 0
    assert abs(max(xs) + min(xs)) < 0.01
    # rests on Y=0
    assert abs(min(ys)) < 0.01


def test_v_passthrough():
    pm = _geo()["minecraft:geometry"][0]["bones"][0]["poly_mesh"]
    # Bedrock poly_mesh V is bottom-up like OBJ — vt values pass through as-is.
    # (flipping V scrambles Meshy's packed UV atlas — the "เทคเจอร์เพี้ยน" bug)
    assert [0.0, 0.0] in pm["uvs"]
    assert [1.0, 1.0] in pm["uvs"]
    assert [0.0, 1.0] in pm["uvs"]


def test_face_forward_rotation():
    g = convert_obj_to_geo(CUBE, "m", target_size=16.0, face_forward=True)
    pm = g["minecraft:geometry"][0]["bones"][0]["poly_mesh"]
    # still valid + centered after 180° Y rotation
    xs = [p[0] for p in pm["positions"]]
    assert abs(max(xs) + min(xs)) < 0.01


def test_empty_obj_raises():
    import pytest
    with pytest.raises(ValueError):
        convert_obj_to_geo("# nothing\n", "x")
