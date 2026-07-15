"""Addon validator — catches the "fails silently" mistakes before they hit the
game: bad JSON, manifest/UUID problems, missing script entry, broken icon and
geometry references and common resource texture paths.

Low-false-positive by design: only flags things that are almost certainly wrong.
Vanilla-looking geometry ids are skipped, and path repairs require a matching
file candidate before they are offered.
"""
from __future__ import annotations

import json
import io
import os
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path

from app.core import history

VANILLA_GEO_PREFIXES = ("geometry.humanoid", "geometry.item", "geometry.cube",
                        "geometry.player", "geometry.armor", "geometry.cape")


def _issue(level, msg, file=None, *, fix_id=None, fixable=False, fix_label=None):
    issue = {"level": level, "message": msg, "file": file}
    if fixable:
        issue["fixable"] = True
        issue["fix_id"] = fix_id
        issue["fix_label"] = fix_label or "แก้ปัญหานี้อัตโนมัติ"
    return issue


def _walk_json(root: Path):
    for p in root.rglob("*.json"):
        yield p


def _rel(root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def _load(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _check_manifest(pack: Path, label: str, issues: list, uuids: dict):
    mp = pack / "manifest.json"
    if not mp.exists():
        issues.append(_issue("error", f"{label}: ไม่พบ manifest.json", "manifest.json"))
        return None
    try:
        data = _load(mp)
    except Exception as e:
        issues.append(_issue("error", f"{label}: manifest.json อ่านไม่ได้ ({e})", "manifest.json"))
        return None

    if not isinstance(data, dict):
        issues.append(_issue("error", f"{label}: manifest ต้องเป็น JSON object", "manifest.json"))
        return None
    if "format_version" not in data:
        issues.append(_issue(
            "error", f"{label}: manifest ไม่มี format_version", "manifest.json",
            fix_id="manifest_format_version", fixable=True, fix_label="เติม format_version = 2",
        ))
    raw_header = data.get("header")
    if raw_header is None:
        header = {}
    elif isinstance(raw_header, dict):
        header = raw_header
    else:
        issues.append(_issue("error", f"{label}: manifest header ต้องเป็น object", "manifest.json"))
        header = {}
    if not header.get("uuid"):
        if raw_header is None or isinstance(raw_header, dict):
            issues.append(_issue(
                "error", f"{label}: manifest header ไม่มี uuid", "manifest.json",
                fix_id="missing_header_uuid", fixable=True, fix_label="สร้าง UUID ใหม่ให้ header",
            ))
    else:
        uuids.setdefault(header["uuid"], []).append(f"{label} header")
    if "min_engine_version" not in header:
        issues.append(_issue("warn", f"{label}: header ไม่มี min_engine_version", "manifest.json"))
    modules = data.get("modules", [])
    if modules is None:
        modules = []
    if not isinstance(modules, list):
        issues.append(_issue("error", f"{label}: manifest modules ต้องเป็น array", "manifest.json"))
        modules = []
    for m in modules:
        if not isinstance(m, dict):
            issues.append(_issue("error", f"{label}: รายการ module ใน manifest ไม่ถูกต้อง", "manifest.json"))
            continue
        u = m.get("uuid")
        if not u:
            issues.append(_issue(
                "error", f"{label}: module ({m.get('type')}) ไม่มี uuid", "manifest.json",
                fix_id="missing_module_uuid", fixable=True, fix_label="สร้าง UUID ใหม่ให้ module",
            ))
        else:
            uuids.setdefault(u, []).append(f"{label} module:{m.get('type')}")
    return data


def _check_json_parse(pack: Path, label: str, issues: list):
    for p in _walk_json(pack):
        try:
            _load(p)
        except Exception as e:
            issues.append(_issue("error", f"{label}: JSON เสีย — {e}", _rel(pack, p)))


def _check_script_entry(bp: Path, bp_manifest, issues):
    if not bp_manifest:
        return
    modules = bp_manifest.get("modules", [])
    if not isinstance(modules, list):
        return
    for m in modules:
        if not isinstance(m, dict):
            continue
        if m.get("type") == "script":
            entry = m.get("entry", "")
            if entry and not (bp / entry).exists():
                issues.append(_issue("error", f"BP: script entry ไม่พบไฟล์ '{entry}'", "manifest.json"))


def _check_dependency(bp_manifest, rp_manifest, issues):
    if not bp_manifest or not rp_manifest:
        return
    rp_header = rp_manifest.get("header") if isinstance(rp_manifest.get("header"), dict) else {}
    rp_uuid = rp_header.get("uuid")
    deps = bp_manifest.get("dependencies", [])
    if not isinstance(deps, list):
        deps = []
    dep_uuids = {d.get("uuid") for d in deps if isinstance(d, dict) and d.get("uuid")}
    if rp_uuid and rp_uuid not in dep_uuids:
        issues.append(_issue(
            "warn", "BP ไม่ได้ depend RP uuid — อาจโหลด RP ไม่พร้อมกัน", "manifest.json",
            fix_id="missing_rp_dependency", fixable=True, fix_label="เพิ่ม dependency ของ BP ไปยัง RP",
        ))
    modules = bp_manifest.get("modules", [])
    if not isinstance(modules, list):
        modules = []
    has_script = any(isinstance(m, dict) and m.get("type") == "script" for m in modules)
    dep_modules = {d.get("module_name") for d in deps if isinstance(d, dict) and d.get("module_name")}
    if has_script and "@minecraft/server" not in dep_modules:
        issues.append(_issue("error", "BP มี script module แต่ไม่ได้ depend '@minecraft/server'", "manifest.json"))


def _check_item_textures(rp: Path, issues):
    itp = rp / "textures" / "item_texture.json"
    if not itp.exists():
        return
    try:
        data = _load(itp)
    except Exception:
        return
    return _check_item_textures_smart(rp, itp, data, issues)
    for key, val in (data.get("texture_data") or {}).items():
        refs = val.get("textures")
        refs = [refs] if isinstance(refs, str) else (refs or [])
        for ref in refs:
            if not _texture_exists(rp, ref):
                issues.append(_issue("error", f"item_texture '{key}' ชี้ไป '{ref}' ที่ไม่มีไฟล์",
                                     "textures/item_texture.json"))


def _texture_exists(rp: Path, ref: str) -> bool:
    if not isinstance(ref, str) or not ref.strip():
        return False
    wanted = {_normal_path(ref)}
    wanted.update(_normal_path(ref + ext) for ext in (".png", ".tga", ".jpg"))
    return any(_normal_path(_rel(rp, path)) in wanted for path in rp.rglob("*") if path.is_file())


_TEXTURE_EXTS = {".png", ".tga", ".jpg", ".jpeg"}


def _normal_path(value: str) -> str:
    return str(value or "").replace("\\", "/").lstrip("./")


def _texture_ref_from_file(path: Path, rp: Path, original: str) -> str:
    rel = _normal_path(_rel(rp, path))
    if Path(original).suffix.lower() in _TEXTURE_EXTS:
        return rel
    return str(Path(rel).with_suffix("")).replace("\\", "/")


def _texture_candidates(rp: Path, ref: str) -> list[dict]:
    """Find conservative path repairs, ordered from safest to least certain."""
    requested = _normal_path(ref)
    requested_no_ext = str(Path(requested).with_suffix("")) if Path(requested).suffix.lower() in _TEXTURE_EXTS else requested
    requested_no_ext = _normal_path(requested_no_ext)
    requested_parent = str(Path(requested_no_ext).parent).replace("\\", "/")
    requested_stem = Path(requested_no_ext).name.casefold()

    files = [p for p in rp.rglob("*") if p.is_file() and p.suffix.lower() in _TEXTURE_EXTS and ".autofix." not in p.name]
    scored: list[tuple[int, Path]] = []
    for path in files:
        rel = _normal_path(_rel(rp, path))
        rel_no_ext = _normal_path(str(Path(rel).with_suffix("")))
        score = 0
        if rel.casefold() == requested.casefold():
            score = 100
        elif rel_no_ext.casefold() == requested_no_ext.casefold():
            score = 95
        elif str(Path(rel_no_ext).parent).replace("\\", "/").casefold() == requested_parent.casefold() and Path(rel_no_ext).name.casefold() == requested_stem:
            score = 90
        elif Path(rel_no_ext).name.casefold() == requested_stem:
            score = 60
        if score:
            scored.append((score, path))

    scored.sort(key=lambda item: (-item[0], _normal_path(_rel(rp, item[1])).casefold()))
    candidates: list[dict] = []
    seen: set[str] = set()
    for score, path in scored:
        candidate = _texture_ref_from_file(path, rp, ref)
        if candidate.casefold() in seen:
            continue
        seen.add(candidate.casefold())
        candidates.append({"path": candidate, "confidence": "high" if score >= 90 else "medium"})
    return candidates[:8]


def _repair_id(pack: str, file: str, pointer: list, kind: str) -> str:
    pointer_json = json.dumps(pointer, ensure_ascii=False, separators=(",", ":"))
    return f"{pack}:{_normal_path(file)}:{pointer_json}:{kind}"


def _missing_texture_issue(rp: Path, issues: list, file: Path, ref: str, pointer: list, label: str) -> None:
    candidates = _texture_candidates(rp, ref)
    repair = {
        "id": _repair_id("RP", _rel(rp, file), pointer, "texture_path"),
        "kind": "texture_path",
        "pack": "RP",
        "path": _rel(rp, file),
        "pointer": pointer,
        "from": ref,
        "candidates": [item["path"] for item in candidates],
    }
    if candidates and candidates[0]["confidence"] == "high":
        repair["to"] = candidates[0]["path"]
        repair["confidence"] = "high"
        issue = _issue("error", f"{label} ชี้ไป '{ref}' แต่ไม่พบไฟล์, พบไฟล์ที่น่าจะใช่ '{candidates[0]['path']}'", _rel(rp, file), fix_id="repair_texture_path", fixable=True, fix_label=f"แก้พาธเป็น {candidates[0]['path']}")
    elif candidates:
        repair["confidence"] = "medium"
        issue = _issue("error", f"{label} ชี้ไป '{ref}' แต่ไม่พบไฟล์, พบไฟล์ที่อาจใช่หลายรายการ", _rel(rp, file))
    else:
        issue = _issue("error", f"{label} ชี้ไป '{ref}' ที่ไม่มีไฟล์", _rel(rp, file))
    issue["repair"] = repair
    issues.append(issue)


def _iter_texture_refs(data, pointer: list):
    if isinstance(data, str):
        yield pointer, data
    elif isinstance(data, list):
        for index, value in enumerate(data):
            yield from _iter_texture_refs(value, pointer + [index])
    elif isinstance(data, dict):
        for key, value in data.items():
            yield from _iter_texture_refs(value, pointer + [key])


def _check_item_textures_smart(rp: Path, file: Path, data: dict, issues: list):
    for key, val in (data.get("texture_data") or {}).items():
        if not isinstance(val, dict):
            continue
        refs = val.get("textures")
        if isinstance(refs, str):
            refs = [refs]
            base_pointer = ["texture_data", key, "textures"]
        elif isinstance(refs, list):
            base_pointer = ["texture_data", key, "textures"]
        else:
            continue
        for index, ref in enumerate(refs):
            if isinstance(ref, str) and not _texture_exists(rp, ref):
                pointer = base_pointer if isinstance(val.get("textures"), str) else base_pointer + [index]
                _missing_texture_issue(rp, issues, file, ref, pointer, f"item_texture '{key}'")


def _check_texture_file_refs(rp: Path, file: Path, data: dict, issues: list, label: str, base_pointer: list | None = None) -> None:
    for pointer, ref in _iter_texture_refs(data, base_pointer or []):
        if not _texture_exists(rp, ref):
            _missing_texture_issue(rp, issues, file, ref, pointer, label)


def _check_attachable_textures(rp: Path, issues):
    for sub in ("attachables", "entity"):
        folder = rp / sub
        if not folder.exists():
            continue
        for file in folder.rglob("*.json"):
            try:
                data = _load(file)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            root_key = "minecraft:attachable" if "minecraft:attachable" in data else "minecraft:client_entity"
            root = data.get(root_key)
            desc = root.get("description", {}) if isinstance(root, dict) else {}
            textures = desc.get("textures") if isinstance(desc, dict) else None
            if isinstance(textures, dict):
                _check_texture_file_refs(
                    rp, file, textures, issues, f"texture ใน {_rel(rp, file)}",
                    [root_key, "description", "textures"],
                )


def _collect_geometry_ids(rp: Path) -> set:
    ids = set()
    models = rp / "models"
    if not models.exists():
        return ids
    for p in models.rglob("*.json"):
        try:
            data = _load(p)
        except Exception:
            continue
        for g in data.get("minecraft:geometry", []) or []:
            ident = g.get("description", {}).get("identifier")
            if ident:
                ids.add(ident)
    return ids


def _check_geometry_refs(rp: Path, issues):
    defined = _collect_geometry_ids(rp)
    for sub in ("attachables", "entity"):
        d = rp / sub
        if not d.exists():
            continue
        for p in d.rglob("*.json"):
            try:
                data = _load(p)
            except Exception:
                continue
            desc = None
            if "minecraft:attachable" in data:
                desc = data["minecraft:attachable"].get("description", {})
            elif "minecraft:client_entity" in data:
                desc = data["minecraft:client_entity"].get("description", {})
            if not desc:
                continue
            for _slot, ref in (desc.get("geometry") or {}).items():
                if not ref or ref.startswith(VANILLA_GEO_PREFIXES) or ref == "geometry.default":
                    continue
                if ref not in defined:
                    issues.append(_issue("warn", f"geometry '{ref}' ถูกอ้างแต่ไม่พบใน models/",
                                         _rel(rp, p)))


def check_addon(bp_path: str | None, rp_path: str | None) -> dict:
    issues: list = []
    uuids: dict = {}

    bp = Path(bp_path) if bp_path else None
    rp = Path(rp_path) if rp_path else None

    bp_manifest = rp_manifest = None
    if bp and bp.exists():
        _check_json_parse(bp, "BP", issues)
        bp_manifest = _check_manifest(bp, "BP", issues, uuids)
        _check_script_entry(bp, bp_manifest, issues)
    elif bp_path:
        issues.append(_issue("error", f"ไม่พบโฟลเดอร์ BP: {bp_path}"))

    if rp and rp.exists():
        _check_json_parse(rp, "RP", issues)
        rp_manifest = _check_manifest(rp, "RP", issues, uuids)
        _check_item_textures(rp, issues)
        _check_attachable_textures(rp, issues)
        _check_geometry_refs(rp, issues)
    elif rp_path:
        issues.append(_issue("error", f"ไม่พบโฟลเดอร์ RP: {rp_path}"))

    _check_dependency(bp_manifest, rp_manifest, issues)

    for u, where in uuids.items():
        if len(where) > 1:
            issues.append(_issue("error", f"UUID ซ้ำ {u} ใช้ที่: {', '.join(where)}", "manifest.json"))

    errors = sum(1 for i in issues if i["level"] == "error")
    warns = sum(1 for i in issues if i["level"] == "warn")
    return {"ok": errors == 0, "errors": errors, "warnings": warns, "issues": issues}


def _backup_and_write(path: Path, data: dict, backups: list[str]) -> None:
    backup = path.with_name(path.name + ".autofix.bak")
    if not backup.exists():
        shutil.copy2(path, backup)
        backups.append(str(backup))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _set_json_pointer(data, pointer: list, value) -> None:
    if not pointer:
        raise ValueError("พาธ JSON ว่าง ไม่สามารถแก้ไขได้")
    current = data
    for part in pointer[:-1]:
        current = current[part]
    last = pointer[-1]
    if isinstance(current, dict):
        current[last] = value
    elif isinstance(current, list) and isinstance(last, int):
        current[last] = value
    else:
        raise ValueError("พาธ JSON ไม่ถูกต้อง")


def _repair_selections(before: dict, requested: list[dict] | None) -> list[tuple[dict, str]]:
    requested_map = {
        str(item.get("repair_id")): str(item.get("to"))
        for item in (requested or [])
        if isinstance(item, dict) and item.get("repair_id") and item.get("to")
    }
    selected: list[tuple[dict, str]] = []
    for issue in before.get("issues", []):
        repair = issue.get("repair")
        if not isinstance(repair, dict) or repair.get("kind") != "texture_path":
            continue
        repair_id = str(repair.get("id") or "")
        candidate = requested_map.get(repair_id)
        if candidate is None and issue.get("fixable"):
            candidate = repair.get("to")
        if not candidate or candidate == repair.get("from"):
            continue
        if candidate not in (repair.get("candidates") or []):
            continue
        selected.append((repair, candidate))
    return selected


def fix_addon(bp_path: str | None, rp_path: str | None, repairs: list[dict] | None = None) -> dict:
    """Apply low-risk repairs, back up each changed manifest, then re-check."""
    before = check_addon(bp_path, rp_path)
    fix_ids = {i.get("fix_id") for i in before["issues"] if i.get("fixable")}
    changes: list[dict] = []
    backups: list[str] = []
    manifests: dict[str, tuple[Path, dict]] = {}
    documents: dict[Path, dict] = {}

    for label, raw_path in (("BP", bp_path), ("RP", rp_path)):
        if not raw_path:
            continue
        pack = Path(raw_path)
        if not pack.is_dir():
            continue
        manifest_path = pack / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            data = _load(manifest_path)
        except Exception:
            continue
        if isinstance(data, dict):
            manifests[label] = (manifest_path, data)

    dirty: set[str] = set()

    def changed(label: str, fix_id: str, message: str) -> None:
        manifest_path, _data = manifests[label]
        dirty.add(str(manifest_path))
        changes.append({"fix_id": fix_id, "file": str(manifest_path), "message": message})

    if "manifest_format_version" in fix_ids:
        for label, (_path, data) in manifests.items():
            if "format_version" not in data:
                data["format_version"] = 2
                changed(label, "manifest_format_version", f"{label}: เติม format_version = 2")

    if "missing_header_uuid" in fix_ids:
        for label, (_path, data) in manifests.items():
            header = data.get("header")
            if header is None:
                header = {}
                data["header"] = header
            if isinstance(header, dict) and not header.get("uuid"):
                header["uuid"] = str(uuid.uuid4())
                changed(label, "missing_header_uuid", f"{label}: สร้าง UUID ใหม่ให้ header")

    if "missing_module_uuid" in fix_ids:
        for label, (_path, data) in manifests.items():
            modules = data.get("modules")
            if not isinstance(modules, list):
                continue
            for module in modules:
                if isinstance(module, dict) and not module.get("uuid"):
                    module["uuid"] = str(uuid.uuid4())
                    changed(label, "missing_module_uuid", f"{label}: สร้าง UUID ใหม่ให้ module ({module.get('type')})")

    if "BP" in manifests and "RP" in manifests:
        _bp_path, bp_data = manifests["BP"]
        _rp_path, rp_data = manifests["RP"]
        rp_header = rp_data.get("header") if isinstance(rp_data.get("header"), dict) else {}
        rp_uuid = rp_header.get("uuid")
        if rp_uuid:
            dependencies = bp_data.get("dependencies")
            if dependencies is None:
                dependencies = []
                bp_data["dependencies"] = dependencies
            if isinstance(dependencies, list) and not any(
                isinstance(dep, dict) and dep.get("uuid") == rp_uuid for dep in dependencies
            ):
                version = rp_header.get("version")
                dependencies.append({
                    "uuid": rp_uuid,
                    "version": version if isinstance(version, list) else [1, 0, 0],
                })
                changed("BP", "missing_rp_dependency", "BP: เพิ่ม dependency ไปยัง RP")

    for repair, replacement in _repair_selections(before, repairs):
        pack_root = {"BP": bp_path, "RP": rp_path}.get(repair.get("pack"))
        if not pack_root:
            continue
        root = Path(pack_root).resolve()
        target = (root / str(repair.get("path") or "")).resolve()
        if root not in target.parents or target.suffix.lower() != ".json" or not target.is_file():
            continue
        try:
            data = documents.setdefault(target, _load(target))
            current = data
            for part in repair.get("pointer") or []:
                current = current[part]
            if current != repair.get("from"):
                continue
            _set_json_pointer(data, repair["pointer"], replacement)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            continue
        changes.append({
            "fix_id": "repair_texture_path",
            "file": str(target),
            "message": f"{repair.get('path')}: แก้พาธ {repair.get('from')} → {replacement}",
        })

    for manifest_path, data in manifests.values():
        if str(manifest_path) in dirty:
            _backup_and_write(manifest_path, data, backups)
    for document_path, data in documents.items():
        _backup_and_write(document_path, data, backups)

    return {
        "changed": bool(changes),
        "changes": changes,
        "backups": backups,
        "check": check_addon(bp_path, rp_path),
    }


_ARCHIVE_EXTS = {".mcaddon", ".mcpack", ".zip"}


def _rewrite_zip_bytes(blob: bytes, extracted_root: Path, changed_files: set[Path], applied: set[Path]) -> bytes:
    """Replace changed manifest entries, including manifests inside nested .mcpack files."""
    source = io.BytesIO(blob)
    output = io.BytesIO()
    with zipfile.ZipFile(source, "r") as zin, zipfile.ZipFile(output, "w") as zout:
        for info in zin.infolist():
            name = info.filename
            data = zin.read(info)
            if not name.endswith("/"):
                target = (extracted_root / Path(name)).resolve()
                if target in changed_files:
                    data = target.read_bytes()
                    applied.add(target)
                else:
                    nested_root = (extracted_root / Path(name).with_suffix("")).resolve()
                    nested_changes = {p for p in changed_files if nested_root in p.parents}
                    if Path(name).suffix.lower() in {".mcpack", ".zip"} and nested_changes and nested_root.is_dir():
                        data = _rewrite_zip_bytes(data, nested_root, nested_changes, applied)
            zout.writestr(info, data)
    return output.getvalue()


def _replace_archive(source: Path, extracted_root: Path, changes: list[dict]) -> str:
    changed_files = {Path(change["file"]).resolve() for change in changes if change.get("file")}
    applied: set[Path] = set()
    updated = _rewrite_zip_bytes(source.read_bytes(), extracted_root, changed_files, applied)
    if applied != changed_files:
        missing = ", ".join(str(path) for path in sorted(changed_files - applied))
        raise ValueError(f"ไม่พบไฟล์ที่ต้องแก้ใน archive: {missing}")

    backup = source.with_name(source.name + ".autofix.bak")
    if not backup.exists():
        shutil.copy2(source, backup)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, dir=str(source.parent), suffix=source.suffix + ".autofix.tmp"
        ) as temp:
            temp.write(updated)
            temp.flush()
            temp_path = Path(temp.name)
        os.replace(temp_path, source)
    except Exception:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise
    return str(backup)


def fix_source(source: str, bp_path: str | None = None, rp_path: str | None = None, repairs: list[dict] | None = None) -> dict:
    """Fix a folder or replace the original archive after rebuilding it safely."""
    source_path = Path(source)
    if not source_path.exists():
        raise ValueError(f"ไม่พบ source: {source}")

    if source_path.is_dir():
        before = check_addon(bp_path, rp_path)
        history_id = None
        if repairs or any(issue.get("fixable") for issue in before.get("issues", [])):
            snapshot = history.create_snapshot("แก้ปัญหาอัตโนมัติ", [source_path], source=str(source_path), status="กำลังแก้ไข")
            history_id = snapshot["id"]
        result = fix_addon(bp_path, rp_path, repairs)
        if history_id:
            history.update_snapshot(
                history_id,
                changed=[change.get("message") or change.get("file") for change in result.get("changes", [])],
                status="completed" if result.get("changed") else "ไม่มีการเปลี่ยนแปลง",
            )
            result["history_id"] = history_id
        result["source"] = str(source_path)
        result["source_replaced"] = False
        return result

    if source_path.suffix.lower() not in _ARCHIVE_EXTS:
        raise ValueError("แก้อัตโนมัติรองรับเฉพาะโฟลเดอร์, .mcaddon, .mcpack และ .zip")

    from app.core import packio

    resolved = packio.inspect_source(str(source_path))
    actual_bp = resolved.get("bp_path")
    actual_rp = resolved.get("rp_path")
    if not actual_bp and not actual_rp:
        raise ValueError("ไม่พบ BP/RP ใน archive ที่เลือก")

    before = check_addon(actual_bp, actual_rp)
    history_id = None
    if repairs or any(issue.get("fixable") for issue in before.get("issues", [])):
        snapshot = history.create_snapshot("แก้ปัญหาอัตโนมัติ", [source_path], source=str(source_path), status="กำลังแก้ไข")
        history_id = snapshot["id"]
    result = fix_addon(actual_bp, actual_rp, repairs)
    if not result["changed"]:
        if history_id:
            history.update_snapshot(history_id, status="ไม่มีการเปลี่ยนแปลง")
            result["history_id"] = history_id
        result["source"] = str(source_path)
        result["source_replaced"] = False
        return result

    # packio.inspect_source returns the original source; _extract is stable and
    # is intentionally called here so the same extraction root is used for the
    # changed manifest paths returned by fix_addon.
    extracted_root = packio._extract(source_path)
    source_backup = _replace_archive(source_path, extracted_root, result["changes"])
    if history_id:
        history.update_snapshot(
            history_id,
            changed=[str(source_path)] + [change.get("message") or change.get("file") for change in result.get("changes", [])],
            status="completed",
        )
    fixed = packio.inspect_source(str(source_path))
    report = check_addon(fixed.get("bp_path"), fixed.get("rp_path"))
    return {
        "changed": True,
        "changes": result["changes"],
        "backups": [source_backup],
        "source": str(source_path),
        "source_backup": source_backup,
        "source_replaced": True,
        "history_id": history_id,
        "check": report,
    }
