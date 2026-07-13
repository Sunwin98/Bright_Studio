"""Convert a Wavefront OBJ (as produced by Meshy) into a Minecraft Bedrock
geometry file using `poly_mesh` (geometry format 1.16.0+, the same arbitrary-
mesh path Blockbench uses to import models).

Pure Python, no dependencies. OBJ is plain text so we parse it directly:
  v  x y z        vertex position
  vt u v          texture coord (0..1)
  vn x y z        normal
  f  a/b/c ...    face (1-based indices into v/vt/vn), 'a', 'a/b', 'a//c', 'a/b/c'

Bedrock notes handled here:
  * UV V axis passes through UNCHANGED — Bedrock poly_mesh V is bottom-up like
    OBJ (verified against the Meshy/Blockbench plugin, which flips V only when
    converting *into* Blockbench's top-left UV space).
  * Model is centered on X/Z and scaled so its tallest dimension is a chosen
    number of Minecraft units (16 units = 1 block), resting with min-Y at 0.
  * n-gon faces are fan-triangulated into tris (Bedrock poly_mesh accepts tris).
"""
from __future__ import annotations

import json
from pathlib import Path


def _parse_obj(text: str):
    positions: list[list[float]] = []
    uvs: list[list[float]] = []
    normals: list[list[float]] = []
    faces: list[list[tuple[int, int, int]]] = []  # each vert = (pi, ui, ni), 0-based, -1 = none

    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] == "#":
            continue
        parts = line.split()
        tag = parts[0]
        if tag == "v" and len(parts) >= 4:
            positions.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif tag == "vt" and len(parts) >= 3:
            uvs.append([float(parts[1]), float(parts[2])])
        elif tag == "vn" and len(parts) >= 4:
            normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif tag == "f" and len(parts) >= 4:
            verts = []
            for tok in parts[1:]:
                bits = tok.split("/")
                pi = int(bits[0]) - 1 if bits[0] else -1
                ui = int(bits[1]) - 1 if len(bits) > 1 and bits[1] else -1
                ni = int(bits[2]) - 1 if len(bits) > 2 and bits[2] else -1
                verts.append((pi, ui, ni))
            faces.append(verts)
    return positions, uvs, normals, faces


def _fan_triangulate(verts):
    """[v0,v1,v2,v3,...] -> [(v0,v1,v2),(v0,v2,v3),...]"""
    return [(verts[0], verts[i], verts[i + 1]) for i in range(1, len(verts) - 1)]


def convert_obj_to_geo(
    obj_text: str,
    identifier: str,
    texture_width: int = 16,
    texture_height: int = 16,
    target_size: float = 16.0,
    face_forward: bool = True,
) -> dict:
    """Return a Bedrock geometry dict. `identifier` becomes geometry.<identifier>.

    target_size: tallest bounding-box dimension in Minecraft units (16 = 1 block).
    face_forward: rotate 180° about Y so the model faces +Z (Meshy faces the
                  camera / -Z); matches how items/entities are viewed in-game.
    """
    positions, uvs, normals, faces = _parse_obj(obj_text)
    if not positions or not faces:
        raise ValueError("OBJ ไม่มี geometry (ไม่พบ vertex/face)")

    # --- normalize scale + center on X/Z, rest on Y=0 ---
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    zs = [p[2] for p in positions]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    span = max(max_x - min_x, max_y - min_y, max_z - min_z) or 1.0
    scale = target_size / span
    cx = (min_x + max_x) / 2.0
    cz = (min_z + max_z) / 2.0

    out_positions = []
    for x, y, z in positions:
        nx = (x - cx) * scale
        ny = (y - min_y) * scale
        nz = (z - cz) * scale
        if face_forward:
            nx, nz = -nx, -nz  # 180° about Y
        out_positions.append([round(nx, 4), round(ny, 4), round(nz, 4)])

    out_normals = []
    for nx, ny, nz in normals:
        if face_forward:
            nx, nz = -nx, -nz
        out_normals.append([round(nx, 4), round(ny, 4), round(nz, 4)])
    if not out_normals:  # OBJ had no normals — poly_mesh needs at least a stub
        out_normals.append([0.0, 1.0, 0.0])

    out_uvs = [[round(u, 5), round(v, 5)] for u, v in uvs]  # V bottom-up, same as OBJ
    if not out_uvs:
        out_uvs.append([0.0, 0.0])

    default_n = len(out_normals) - 1
    default_u = len(out_uvs) - 1

    polys = []
    for verts in faces:
        tris = _fan_triangulate(verts) if len(verts) > 3 else [tuple(verts)]
        for tri in tris:
            poly = []
            for (pi, ui, ni) in tri:
                # Bedrock poly vertex order = [position_idx, normal_idx, uv_idx]
                poly.append([
                    pi,
                    ni if ni >= 0 else default_n,
                    ui if ui >= 0 else default_u,
                ])
            polys.append(poly)

    # bounding box for visible bounds (in the normalized/scaled space)
    bb_w = max(max_x - min_x, max_z - min_z) * scale
    bb_h = (max_y - min_y) * scale

    return {
        "format_version": "1.16.0",
        "minecraft:geometry": [
            {
                "description": {
                    "identifier": f"geometry.{identifier}",
                    "texture_width": int(texture_width),
                    "texture_height": int(texture_height),
                    "visible_bounds_width": round(bb_w / 16.0 + 0.5, 3),
                    "visible_bounds_height": round(bb_h / 16.0 + 0.5, 3),
                    "visible_bounds_offset": [0, round(bb_h / 32.0, 3), 0],
                },
                "bones": [
                    {
                        "name": "root",
                        "pivot": [0, 0, 0],
                        "poly_mesh": {
                            "normalized_uvs": True,
                            "positions": out_positions,
                            "normals": out_normals,
                            "uvs": out_uvs,
                            # each poly: array of verts, vert = [pos_idx, normal_idx, uv_idx]
                            "polys": polys,
                        },
                    }
                ],
            }
        ],
    }


def write_geo(geo: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(geo, indent=2), encoding="utf-8")
