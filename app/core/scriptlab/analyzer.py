"""File-level intelligence for Script Lab: what is this script / this field?

Everything here reads signals the shop's scripts already carry — header
docblocks, Thai inline comments, `// ==== section ====` headers, key naming
conventions — no guessing beyond light keyword heuristics.
"""
from __future__ import annotations

import re
from pathlib import Path

from .parser import ScriptParser, read_source

# ---------------------------------------------------------------------------
# Field heuristics: tag + unit from the key name
# ---------------------------------------------------------------------------

_TAG_RULES: list[tuple[str, re.Pattern]] = [
    ("damage",   re.compile(r"damage|dmg|atk|attack_?power", re.I)),
    ("cooldown", re.compile(r"cooldown|\bcd\b|_cd$|interval", re.I)),
    ("range",    re.compile(r"range|radius|distance|reach", re.I)),
    ("duration", re.compile(r"duration|time|delay|ticks?$", re.I)),
    ("speed",    re.compile(r"speed|velocity", re.I)),
    ("heal",     re.compile(r"heal|regen|hp|health|mana", re.I)),
    ("item",     re.compile(r"item_?id|itemid", re.I)),
    ("sound",    re.compile(r"sound|sfx", re.I)),
    ("particle", re.compile(r"particle|effect|fx", re.I)),
]

_ITEM_ID_RE = re.compile(r"^[a-z0-9_.]+:[a-z0-9_./]+$")


def field_meta(key: str, path: str, value) -> dict:
    """{tag, unit} for a field."""
    hay = f"{path} {key}"
    tag = ""
    for name, pat in _TAG_RULES:
        if pat.search(hay):
            tag = name
            break
    unit = ""
    if re.search(r"ticks?$|_ticks|ticks_", key, re.I) or re.search(r"cooldowns?\.", path, re.I):
        if isinstance(value, (int, float)):
            unit = "ticks"
    elif re.search(r"percent|_pct", key, re.I):
        unit = "percent"
    if isinstance(value, str) and _ITEM_ID_RE.match(value):
        tag = tag or "item"
        unit = "item_id"
    return {"tag": tag, "unit": unit}


# ---------------------------------------------------------------------------
# File summary
# ---------------------------------------------------------------------------

def _header_summary(src: str) -> str:
    """First meaningful lines of the leading docblock / comment run."""
    lines: list[str] = []
    m = re.match(r"\s*(?:import[^\n]*\n|\s)*?/\*\*?([\s\S]*?)\*/", src[:4000])
    if m:
        for raw in m.group(1).splitlines():
            t = raw.strip().lstrip("*").strip()
            if t and "สงวนลิขสิทธิ์" not in t and "copyright" not in t.lower():
                lines.append(t)
            if len(lines) >= 3:
                break
    if not lines:
        for raw in src[:3000].splitlines()[:15]:
            t = raw.strip()
            if t.startswith("//"):
                t = t.lstrip("/").strip()
                t = re.sub(r"^[=\-\s]+|[=\-\s]+$", "", t)
                if t:
                    lines.append(t)
                if len(lines) >= 2:
                    break
            elif t and not t.startswith(("import", "export")):
                break
    return " · ".join(lines)[:180]


def _kind(filename: str, n_editable: int, tier: int) -> str:
    low = filename.lower()
    if low in ("config.js", "configs.js") or low.endswith("_config.js"):
        return "config"
    if low.startswith("skill") or "_skill" in low:
        return "skill"
    if low in ("utils.js", "util.js", "helpers.js"):
        return "util"
    if low in ("main.js", "index.js"):
        return "main"
    if tier == 2 or n_editable == 0:
        return "inline"
    return "script"


def summarize_script(path: Path) -> dict:
    try:
        src = read_source(path)
    except OSError as e:
        return {"path": str(path), "name": path.name, "error": str(e)}
    result = ScriptParser(src).parse()
    editable = [f for f in result.fields if not f.readonly]
    return {
        "path": str(path),
        "name": path.name,
        "summary": _header_summary(src),
        "kind": _kind(path.name, len(editable), result.tier),
        "field_count": len(editable),
        "size": len(src),
    }


_KIND_ORDER = {"config": 0, "main": 1, "skill": 2, "script": 3, "inline": 4, "util": 5}


def list_scripts(bp_path: Path) -> list[dict]:
    """Every .js under <bp>/scripts (recursive), summarized + sorted."""
    base = bp_path / "scripts"
    if not base.is_dir():
        base = bp_path  # some packs keep scripts at root
    out = []
    for p in sorted(base.rglob("*.js")):
        if p.is_file() and p.stat().st_size < 2_000_000:
            out.append(summarize_script(p))
    out.sort(key=lambda s: (_KIND_ORDER.get(s.get("kind", "script"), 9), s["name"]))
    return out


def parse_for_ui(path: Path) -> dict:
    """Full parse of one script, shaped for the frontend table."""
    src = read_source(path)
    result = ScriptParser(src).parse()

    groups: dict[str, dict] = {}
    for f in result.fields:
        if "." in f.path:
            top, section = f.path.split(".")[0], f.section
        else:
            top, section = (f.section or "ค่าเดี่ยว"), ""
        g = groups.setdefault(top, {"name": top, "fields": []})
        meta = field_meta(f.key, f.path, f.value)
        f.section = section
        g["fields"].append({
            "id": f.id,
            "path": f.path,
            "key": f.key,
            "value": f.value if not f.readonly else None,
            "raw": f.raw if len(f.raw) < 400 else f.raw[:400] + "…",
            "type": f.type,
            "start": f.start,
            "end": f.end,
            "comment": f.comment,
            "section": f.section,
            "readonly": f.readonly,
            "quote": f.quote,
            "items": f.items,
            "tag": meta["tag"],
            "unit": meta["unit"],
        })

    return {
        "file_summary": _header_summary(src),
        "tier": result.tier,
        "groups": list(groups.values()),
        "mtime": Path(path).stat().st_mtime,
    }
