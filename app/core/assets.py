"""Read-only asset index for addon folders and archives."""
from __future__ import annotations

import json
from pathlib import Path

from app.core import packio


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tga"}
MODEL_EXTS = {".geo.json", ".json"}
SKIP_PARTS = {".git", "__pycache__", ".autofix.bak"}


def _norm(value: str) -> str:
    return str(value or "").replace("\\", "/").lstrip("./").casefold()


def _relative(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _kind(path: Path) -> str:
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    if path.suffix.lower() in IMAGE_EXTS:
        return "texture"
    if name.endswith(".geo.json") or "models" in parts:
        return "model"
    if "attachables" in parts:
        return "attachable"
    if "entity" in parts:
        return "entity"
    if "animation" in name or "animations" in parts:
        return "animation"
    if path.suffix.lower() == ".js":
        return "script"
    if path.suffix.lower() == ".json":
        return "json"
    return "file"


def _walk(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        yield path


def _load_json(path: Path):
    try:
        return packio._load_json(path)
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None


def _strings(value, pointer=()):
    if isinstance(value, str):
        yield pointer, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from _strings(child, pointer + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _strings(child, pointer + (str(index),))


def _geometry_info(path: Path) -> dict:
    data = _load_json(path)
    if not isinstance(data, dict):
        return {}
    geometries = data.get("minecraft:geometry") or []
    if isinstance(geometries, dict):
        geometries = [geometries]
    ids = []
    bones = 0
    for geo in geometries:
        if not isinstance(geo, dict):
            continue
        ident = (geo.get("description") or {}).get("identifier")
        if ident:
            ids.append(ident)
        bones += len(geo.get("bones") or []) if isinstance(geo.get("bones"), list) else 0
    return {"geometry_ids": ids, "bone_count": bones, "geometry_count": len(geometries)}


def _resolve(raw: str) -> tuple[dict, list[Path]]:
    source = Path(raw).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์หรือโฟลเดอร์: {raw}")
    if source.is_file() and source.suffix.lower() not in packio.ARCHIVE_EXTS:
        return {"source": str(source), "packs": []}, [source.parent]
    info = packio.inspect_source(str(source))
    roots = [Path(p) for p in (info.get("bp_path"), info.get("rp_path")) if p]
    return info, roots or ([source] if source.is_dir() else [])


def scan_source(raw: str) -> dict:
    info, roots = _resolve(raw)
    assets = []
    by_ref: dict[str, list[dict]] = {}
    json_docs = []

    for root in roots:
        pack_type = "BP" if root == Path(info.get("bp_path") or "").resolve() else "RP"
        for path in _walk(root):
            kind = _kind(path)
            rel = _relative(root, path)
            item = {
                "id": f"{pack_type}:{path}",
                "path": str(path),
                "relative_path": rel,
                "pack": pack_type,
                "kind": kind,
                "name": path.name,
                "size": path.stat().st_size,
                "references": [],
            }
            if kind == "model":
                item["details"] = _geometry_info(path)
            assets.append(item)
            if path.suffix.lower() == ".json":
                data = _load_json(path)
                if data is not None:
                    json_docs.append((root, path, data))

            refs = {_norm(rel), _norm(str(Path(rel).with_suffix("")))}
            for ref in refs:
                by_ref.setdefault(ref, []).append(item)

    for root, source_path, data in json_docs:
        source_rel = _relative(root, source_path)
        for pointer, value in _strings(data):
            candidate = _norm(value)
            if not candidate.startswith(("textures/", "models/")):
                continue
            matches = by_ref.get(candidate) or by_ref.get(_norm(str(Path(candidate).with_suffix("")))) or []
            for asset in matches:
                asset["references"].append({"file": source_rel, "pointer": ".".join(pointer), "value": value})

    assets.sort(key=lambda item: (item["kind"], item["relative_path"].casefold()))
    return {
        "source": info.get("source", raw),
        "packs": info.get("packs", []),
        "assets": assets[:5000],
        "total": len(assets),
    }
