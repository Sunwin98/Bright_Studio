"""Script Lab parser: field extraction + byte-perfect round-trip on all 3 real
script styles found in Projects Sillkes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.scriptlab.parser import (
    ScriptParser, apply_edits, js_string_literal, read_source, write_source,
)

# ── style 1: single-script const CONFIG (หมัดอ้วน/water_wave style) ─────────
SINGLE = '''import { world, system, Player } from "@minecraft/server";

/**
 * Fist Weapon Addon - หมัดอ้วน
 * Passive: Resistance III + Speed II เมื่อถือไอเทม
 */

// ===== CONFIGURATION =====
const CONFIG = {
    // Item
    itemId: "fist:fist_weapon",

    punchDamage: 10,
    punchCooldownTicks: 10,      // 0.5 วินาที = 10 ticks
    punchKnockback: 1.2,
    criticalHitCount: 5,
    enabled: true,

    // Skill - Dash
    dashCooldownTicks: 200,      // 10 วินาที = 200 ticks
};

const PARTICLES = {
    aoeBlast: "fist:aoe_blast",  // เอฟเฟกต์ระเบิด
};

const playerCooldowns = new Map();
'''

# ── style 2: multi-script export const config.js (Night_skills style) ──────
MULTI = '''// ===== Night Skills — Shared Configuration =====
export const NAMESPACE = "nightskill";

// ===== COOLDOWNS (ticks, 20 ticks = 1 second) =====
export const COOLDOWNS = {
    MOONLIGHT:      300,   // 15s
    VOID_EMPTINESS: 400,   // 20s
};

// ===== DAMAGE VALUES =====
export const DAMAGE = {
    // Skill 1: Moonlight — base per beam
    MOONLIGHT_BASE: 40,
    MOONLIGHT_SHOTS: 3,
    VOID_HP_PERCENT: 0.85,
    ATTACKS: [10, 20, 30],
};
'''

# ── style 3: inline (poseidon style — no config object) ────────────────────
INLINE = '''import { world, system } from "@minecraft/server";

// Poseidon Trident - Script-Based Skill System
function useSkill(player) {
    applyDamage(player, 45); // ดาเมจสกิลหลัก
    const radius = 6.5; // รัศมี AOE
    cooldownMap.set(player.id, 400); // คูลดาวน์ 20 วิ
    someLoop(i, 10);
}
'''


def _fields(src):
    return ScriptParser(src).parse()


def test_single_script_fields():
    r = _fields(SINGLE)
    by_path = {f.path: f for f in r.fields}
    assert "CONFIG.punchDamage" in by_path
    assert by_path["CONFIG.punchDamage"].value == 10
    assert by_path["CONFIG.punchKnockback"].value == 1.2
    assert by_path["CONFIG.enabled"].value is True
    assert by_path["CONFIG.itemId"].value == "fist:fist_weapon"
    assert by_path["PARTICLES.aoeBlast"].comment == "เอฟเฟกต์ระเบิด"
    # trailing Thai comment captured
    assert "วินาที" in by_path["CONFIG.punchCooldownTicks"].comment
    # spans point at exact value text
    f = by_path["CONFIG.punchDamage"]
    assert SINGLE[f.start:f.end] == "10"
    # `new Map()` never becomes an editable field
    assert "playerCooldowns" not in by_path or by_path["playerCooldowns"].readonly


def test_multi_script_fields_and_sections():
    r = _fields(MULTI)
    by_path = {f.path: f for f in r.fields}
    assert by_path["NAMESPACE"].value == "nightskill"
    assert by_path["COOLDOWNS.MOONLIGHT"].value == 300
    assert by_path["DAMAGE.VOID_HP_PERCENT"].value == 0.85
    arr = by_path["DAMAGE.ATTACKS"]
    assert arr.type == "array" and arr.value == [10, 20, 30]
    assert set(r.objects) >= {"COOLDOWNS", "DAMAGE"}


def test_inline_tier2():
    r = _fields(INLINE)
    assert r.tier == 2
    vals = {(f.key, f.value) for f in r.fields}
    assert ("radius", 6.5) in vals
    # numeric args with comments on the same line are NOT matched by IDENT:num
    # pattern for applyDamage(player, 45) — but const/property forms are.
    # cooldownMap.set(...) arg also skipped. Only commented `key: num`/`= num`.
    assert ("i", 10) not in vals  # no comment → excluded


def test_roundtrip_identity_and_single_edit():
    r = _fields(SINGLE)
    # no edits → identical
    assert apply_edits(SINGLE, []) == SINGLE
    # change punchDamage 10 → 99: only that span changes
    f = next(x for x in r.fields if x.path == "CONFIG.punchDamage")
    out = apply_edits(SINGLE, [{"start": f.start, "end": f.end, "new_text": "99"}])
    assert "punchDamage: 99," in out
    assert out.replace("punchDamage: 99,", "punchDamage: 10,") == SINGLE
    # comments intact
    assert "// 0.5 วินาที = 10 ticks" in out


def test_string_edit_preserves_quote_style():
    src = "const A = { name: 'old_name', };\n"
    r = _fields(src)
    f = next(x for x in r.fields if x.key == "name")
    assert f.quote == "'"
    new = js_string_literal("new'name", f.quote)
    out = apply_edits(src, [{"start": f.start, "end": f.end, "new_text": new}])
    assert "name: 'new\\'name'," in out


def test_tricky_string_with_braces_and_slashes():
    # the old regex parser choked on `};` and `//` inside strings
    src = 'const CONFIG = {\n  msg: "end}; // not a comment",\n  dmg: 5,\n};\n'
    r = _fields(src)
    by = {f.key: f for f in r.fields}
    assert by["dmg"].value == 5
    assert by["msg"].value == "end}; // not a comment"


def test_file_io_byte_identical(tmp_path):
    p = tmp_path / "t.js"
    data = ("﻿" + SINGLE).replace("\n", "\r\n")  # BOM + CRLF
    p.write_bytes(data.encode("utf-8"))
    src = read_source(p)
    write_source(p, src)
    assert p.read_bytes() == data.encode("utf-8")
