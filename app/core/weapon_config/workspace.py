"""Safe, static workspace analysis for Minecraft Bedrock weapon scripts.

This intentionally never runs addon JavaScript.  It finds scripts, follows
relative imports, and exposes only literal values that can be patched back at
their exact source location.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import zipfile
import ast
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core import packio

_LITERAL = r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null)"
_DECL_RE = re.compile(
    rf"^\s*(?:export\s+)?(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*(?P<value>{_LITERAL})(?=\s*(?:;|//|$))",
    re.MULTILINE,
)
_PROP_RE = re.compile(
    rf"^\s*(?P<name>[A-Za-z_$][\w$]*|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')\s*:\s*(?P<value>{_LITERAL})(?=\s*(?:,|//|$))",
    re.MULTILINE,
)
_IMPORT_RE = re.compile(r"\bimport(?:[\s\S]*?\sfrom\s*)?[\"'](?P<path>\.{1,2}/[^\"']+)[\"']")
_FUNCTION_RE = re.compile(r"\b(?:export\s+)?(?:async\s+)?function\s+(?P<name>[A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{")
_SKILL_NAME_RE = re.compile(r"^(?:on.*use|cast|use|skill|attack|power|ability|dash|shoot|slash|spell|heal|warp)", re.I)


def _load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _line_col(text: str, offset: int) -> tuple[int, int]:
    return text.count("\n", 0, offset) + 1, offset - text.rfind("\n", 0, offset)


def _parse_literal(raw: str) -> Any:
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw == "null":
        return None
    if raw[:1] in ("'", '"'):
        # JSON understands double-quoted strings.  Single quoted JS strings are
        # common enough to support their simple escaped form here as well.
        if raw.startswith('"'):
            return json.loads(raw)
        return ast.literal_eval(raw)
    number = float(raw) if any(c in raw.lower() for c in (".", "e")) else int(raw)
    return number


def _format_literal(value: Any, original: str) -> str:
    if isinstance(value, str):
        encoded = json.dumps(value, ensure_ascii=False)
        if original.startswith("'"):
            return "'" + encoded[1:-1].replace("'", "\\'") + "'"
        return encoded
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not value.is_integer():
            return repr(value)
        return str(int(value))
    raise ValueError("ค่าที่บันทึกต้องเป็นข้อความ ตัวเลข true/false หรือ null")


def _find_closing_brace(text: str, open_at: int) -> int | None:
    """Find a matching brace without being confused by comments or strings."""
    depth, i, state = 0, open_at, "code"
    while i < len(text):
        ch, nxt = text[i], text[i + 1] if i + 1 < len(text) else ""
        if state == "line_comment":
            if ch == "\n":
                state = "code"
        elif state == "block_comment":
            if ch == "*" and nxt == "/":
                state, i = "code", i + 1
        elif state in ("single", "double", "template"):
            quote = {"single": "'", "double": '"', "template": "`"}[state]
            if ch == "\\":
                i += 1
            elif ch == quote:
                state = "code"
        else:
            if ch == "/" and nxt == "/":
                state, i = "line_comment", i + 1
            elif ch == "/" and nxt == "*":
                state, i = "block_comment", i + 1
            elif ch == "'":
                state = "single"
            elif ch == '"':
                state = "double"
            elif ch == "`":
                state = "template"
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return None


def _functions(text: str) -> list[dict]:
    found = []
    for match in _FUNCTION_RE.finditer(text):
        brace = text.find("{", match.start(), match.end())
        end = _find_closing_brace(text, brace) if brace >= 0 else None
        if end is not None:
            found.append({"name": match.group("name"), "start": match.start(), "end": end + 1})
    return found


def _semantic(name: str) -> str:
    lower = name.lower()
    groups = (
        ("damage", "Damage"), ("cooldown", "Cooldown"), ("duration", "Duration"),
        ("radius", "Radius"), ("range", "Range"), ("mana", "Mana"),
        ("particle", "Particle"), ("sound", "Sound"), ("item", "Item ID"),
        ("id", "Identifier"), ("speed", "Speed"), ("count", "Count"),
        ("chance", "Chance"), ("amp", "Amplifier"), ("heal", "Heal"),
    )
    return next((label for needle, label in groups if needle in lower), "Value")


def _display_name(name: str) -> str:
    return re.sub(r"(?<!^)([A-Z])", r" \1", name).replace("_", " ").strip()


def _skill_for(offset: int, functions: list[dict], file_name: str) -> str:
    inside = next((f["name"] for f in functions if f["start"] <= offset < f["end"] and _SKILL_NAME_RE.search(f["name"])), None)
    return inside or ("Shared config" if file_name.lower().startswith("config") else "Shared values")


def _field(path: Path, text: str, match: re.Match, kind: str, functions: list[dict]) -> dict | None:
    raw = match.group("value")
    try:
        value = _parse_literal(raw)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    start, end = match.start("value"), match.end("value")
    name = match.group("name").strip("\"'")
    line, column = _line_col(text, start)
    digest = hashlib.sha1(f"{path}|{start}|{end}|{name}".encode()).hexdigest()[:12]
    return {
        "id": digest, "path": str(path), "name": name, "label": _display_name(name),
        "semantic": _semantic(name), "kind": kind, "value": value,
        "value_type": "boolean" if isinstance(value, bool) else "number" if isinstance(value, (int, float)) else "text",
        "original": raw, "start": start, "end": end, "line": line, "column": column,
        "skill": _skill_for(start, functions, path.name),
    }


def _analyze_file(path: Path, root: Path) -> dict:
    text = _load_text(path)
    functions = _functions(text)
    fields: list[dict] = []
    seen_ranges: set[tuple[int, int]] = set()
    for kind, regex in (("variable", _DECL_RE), ("property", _PROP_RE)):
        for match in regex.finditer(text):
            candidate = _field(path, text, match, kind, functions)
            if candidate and (candidate["start"], candidate["end"]) not in seen_ranges:
                fields.append(candidate)
                seen_ranges.add((candidate["start"], candidate["end"]))
    fields.sort(key=lambda item: item["start"])

    imports = []
    for match in _IMPORT_RE.finditer(text):
        target = (path.parent / match.group("path")).resolve()
        if not target.suffix:
            target = target.with_suffix(".js")
        try:
            imports.append(str(target.relative_to(root)))
        except ValueError:
            imports.append(match.group("path"))

    skill_names = [f["name"] for f in functions if _SKILL_NAME_RE.search(f["name"])]
    lower = path.name.lower()
    role = "Skill" if skill_names else "Utility"
    if lower in {"main.js", "index.js"} or "afterevents" in text or "beforeevents" in text:
        role = "Entry"
    elif "config" in lower or (len(fields) >= 4 and not functions):
        role = "Config"
    return {
        "path": str(path), "relative_path": str(path.relative_to(root)), "name": path.name,
        "role": role, "imports": imports, "skills": skill_names,
        "fields": fields, "field_count": len(fields),
    }


def _workspace_root(source: Path, packs: list[dict]) -> Path:
    if source.is_dir():
        return source.resolve()
    pack_paths = [Path(pack["path"]) for pack in packs]
    if not pack_paths:
        raise ValueError("ไม่พบ Behavior Pack ในแอดออนนี้")
    if len(pack_paths) == 1:
        return pack_paths[0].parent
    return Path(os.path.commonpath([str(p) for p in pack_paths]))


def analyze_source(source_path: str) -> dict:
    intake = packio.inspect_source(source_path)
    source = Path(intake["source"])
    packs = intake.get("packs", [])
    behavior = [p for p in packs if p["type"] == "behavior"]
    if not behavior:
        raise ValueError("ไม่พบ Behavior Pack ที่มี scripts ในแอดออนนี้")
    root = _workspace_root(source, packs)
    files = []
    for pack in behavior:
        bp = Path(pack["path"])
        scripts = bp / "scripts"
        if not scripts.is_dir():
            continue
        for path in sorted(scripts.rglob("*.js")):
            if any(part in {"node_modules", ".hs_studio_backups"} for part in path.parts):
                continue
            files.append(_analyze_file(path, root))
    if not files:
        raise ValueError("ไม่พบไฟล์ .js ในโฟลเดอร์ scripts ของ Behavior Pack")
    all_fields = [field for file in files for field in file["fields"]]
    skills: dict[str, dict] = {}
    for file in files:
        for name in file["skills"]:
            skills[f"{file['path']}::{name}"] = {
                "id": f"{file['path']}::{name}", "name": name, "label": _display_name(name),
                "file": file["relative_path"], "field_count": sum(1 for field in file["fields"] if field["skill"] == name),
            }
    return {
        "source": str(source), "workspace_root": str(root), "packs": packs,
        "files": files, "fields": all_fields, "skills": list(skills.values()),
        "summary": {"scripts": len(files), "skills": len(skills), "editable_fields": len(all_fields)},
    }


def read_script(path: str, max_lines: int = 300) -> dict:
    file_path = Path(path)
    if file_path.suffix.lower() != ".js" or not file_path.is_file():
        raise ValueError("เลือกได้เฉพาะไฟล์ JavaScript ที่มีอยู่จริง")
    limit = max(1, min(int(max_lines), 800))
    lines = _load_text(file_path).splitlines()
    shown = lines[:limit]
    return {
        "path": str(file_path),
        "content": "\n".join(shown),
        "total_lines": len(lines),
        "shown_lines": len(shown),
        "truncated": len(lines) > len(shown),
    }


def apply_edits(edits: list[dict]) -> dict:
    if not edits:
        raise ValueError("ยังไม่มีค่าที่ต้องบันทึก")
    grouped: dict[Path, list[dict]] = defaultdict(list)
    for edit in edits:
        path = Path(str(edit.get("path", "")))
        if path.suffix.lower() != ".js" or not path.is_file():
            raise ValueError("พบไฟล์ JavaScript ที่ไม่ถูกต้อง")
        grouped[path].append(edit)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    saved = []
    for path, file_edits in grouped.items():
        text = _load_text(path)
        replacements = []
        for edit in file_edits:
            start, end = int(edit["start"]), int(edit["end"])
            original = str(edit["original"])
            if start < 0 or end < start or text[start:end] != original:
                raise ValueError(f"ไฟล์ {path.name} ถูกเปลี่ยนหลังจากสแกน กรุณาสแกนใหม่ก่อนบันทึก")
            replacements.append((start, end, _format_literal(edit.get("value"), original)))
        replacements.sort(reverse=True)
        if any(replacements[i][0] < replacements[i + 1][1] for i in range(len(replacements) - 1)):
            raise ValueError(f"พบการแก้ไขที่ทับซ้อนกันใน {path.name}")

        backup = path.parent / ".hs_studio_backups" / f"{stamp}_{hashlib.sha1(str(path).encode()).hexdigest()[:6]}_{path.name}"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
        for start, end, replacement in replacements:
            text = text[:start] + replacement + text[end:]
        path.write_text(text, encoding="utf-8")
        saved.append({"path": str(path), "backup": str(backup), "changes": len(replacements)})
    return {"ok": True, "saved": saved}


def export_addon(source_path: str, output_path: str | None = None) -> dict:
    analysis = analyze_source(source_path)
    source = Path(analysis["source"])
    root = Path(analysis["workspace_root"])
    if output_path:
        output = Path(output_path)
    else:
        base = source.with_suffix("") if source.is_file() else source
        output = base.parent / f"{base.name}_edited.mcaddon"
    if output.suffix.lower() != ".mcaddon":
        output = output.with_suffix(".mcaddon")
    output.parent.mkdir(parents=True, exist_ok=True)

    pack_dirs = [Path(pack["path"]) for pack in analysis["packs"]]
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for pack in pack_dirs:
            for file in pack.rglob("*"):
                if not file.is_file() or ".hs_studio_backups" in file.parts:
                    continue
                archive.write(file, file.relative_to(pack.parent))
    return {"ok": True, "output_path": str(output), "packs": len(pack_dirs)}
