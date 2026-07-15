"""Small, predictable JavaScript builders for common Bedrock events."""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from app.core import history


EVENTS = {
    "item_use": {"label": "ผู้เล่นใช้ไอเทม", "supports_item": True},
    "player_spawn": {"label": "ผู้เล่นเกิดหรือเข้าโลก", "supports_item": False},
    "entity_hit": {"label": "ผู้เล่นตีโดน Entity", "supports_item": False},
    "block_break": {"label": "ผู้เล่นทำลายบล็อก", "supports_item": False},
    "tick": {"label": "ทำงานซ้ำทุกช่วงเวลา", "supports_item": False},
}


def _js(value: str) -> str:
    return json.dumps(str(value or ""), ensure_ascii=False)


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "").strip()).strip("_-")
    return slug[:48] or "custom_event"


def _action_lines(block: dict, indent: str = "  ") -> list[str]:
    kind = str(block.get("kind") or "")
    value = block.get("value") or {}
    if not isinstance(value, dict):
        value = {"text": str(value)}
    if kind == "message":
        return [f"{indent}player.sendMessage({_js(value.get('text') or 'ข้อความจาก Addon')});"]
    if kind == "sound":
        return [f"{indent}player.playSound({_js(value.get('sound') or 'random.orb')});"]
    if kind == "effect":
        effect = value.get("effect") or "speed"
        ticks = int(value.get("ticks") or 100)
        amplifier = int(value.get("amplifier") or 0)
        return [f"{indent}player.addEffect({_js(effect)}, {ticks}, {{ amplifier: {amplifier}, showParticles: true }});"]
    if kind == "command":
        return [f"{indent}player.runCommand({_js(value.get('command') or 'say Hello')});"]
    if kind == "give":
        item = value.get("item") or "minecraft:diamond"
        amount = int(value.get("amount") or 1)
        return [f"{indent}player.runCommand({_js(f'give @s {item} {amount}')});"]
    if kind == "particle":
        return [f"{indent}player.dimension.spawnParticle({_js(value.get('particle') or 'minecraft:basic_flame_particle')}, player.location);"]
    return [f"{indent}// ยังไม่ได้กำหนด Action: {kind or 'ไม่ระบุ'}"]


def build_source(event_id: str, blocks: list[dict]) -> str:
    if event_id not in EVENTS:
        raise ValueError("ไม่รู้จักเหตุการณ์ที่เลือก")
    blocks = [block for block in (blocks or []) if isinstance(block, dict)]
    conditions = [block for block in blocks if block.get("type") == "condition"]
    actions = [block for block in blocks if block.get("type") == "action"]
    lines = ["import { world, system } from \"@minecraft/server\";", ""]

    if event_id == "item_use":
        lines += ["world.afterEvents.itemUse.subscribe((event) => {", "  const player = event.source;", "  const item = event.itemStack;", "  if (!player || !item) return;"]
        for condition in conditions:
            if condition.get("kind") == "item":
                lines.append(f"  if (item.typeId !== {_js((condition.get('value') or {}).get('item') or 'minecraft:stick')}) return;")
        for action in actions:
            lines.extend(_action_lines(action))
        lines += ["});", ""]
    elif event_id == "player_spawn":
        lines += ["world.afterEvents.playerSpawn.subscribe((event) => {", "  const player = event.player;", "  if (!player) return;"]
        for action in actions:
            lines.extend(_action_lines(action))
        lines += ["});", ""]
    elif event_id == "entity_hit":
        lines += ["world.afterEvents.entityHitEntity.subscribe((event) => {", "  const player = event.damagingEntity;", "  const target = event.hitEntity;", "  if (!player || !target) return;"]
        for action in actions:
            lines.extend(_action_lines(action))
        lines += ["});", ""]
    elif event_id == "block_break":
        lines += ["world.afterEvents.playerBreakBlock.subscribe((event) => {", "  const player = event.player;", "  if (!player) return;"]
        for action in actions:
            lines.extend(_action_lines(action))
        lines += ["});", ""]
    else:
        interval = max(1, int(next((block.get("value", {}).get("ticks") for block in blocks if block.get("kind") == "interval"), 20) or 20))
        lines += [f"system.runInterval(() => {{", "  for (const player of world.getAllPlayers()) {"]
        for action in actions:
            lines.extend(_action_lines(action, "    "))
        lines += ["  }", f"}}, {interval});", ""]
    return "\n".join(lines)


def create_script(bp_path: str, name: str, event_id: str, blocks: list[dict], overwrite: bool = False) -> dict:
    root = Path(bp_path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("ต้องเลือกโฟลเดอร์ Behavior Pack")
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("ไม่พบ manifest.json ใน Behavior Pack")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise ValueError(f"อ่าน manifest ไม่ได้: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("manifest ต้องเป็น JSON object")

    slug = _safe_slug(name)
    rel_script = f"scripts/hs_{slug}.js"
    script_path = (root / rel_script).resolve()
    if root not in script_path.parents:
        raise ValueError("ชื่อไฟล์ไม่ถูกต้อง")
    if script_path.exists() and not overwrite:
        raise ValueError(f"มีไฟล์ {rel_script} อยู่แล้ว")

    modules = manifest.get("modules") if isinstance(manifest.get("modules"), list) else []
    script_modules = [module for module in modules if isinstance(module, dict) and module.get("type") == "script"]
    entry_path = None
    entry_text = None
    manifest_changed = False
    if script_modules:
        module = script_modules[0]
        entry = str(module.get("entry") or "").replace("\\", "/")
        if entry:
            entry_path = (root / entry).resolve()
            if root not in entry_path.parents:
                raise ValueError("entry ใน manifest อยู่นอก Behavior Pack")
            if entry_path.is_file():
                entry_text = entry_path.read_text(encoding="utf-8")
            else:
                module["entry"] = rel_script
                manifest_changed = True
        if not entry:
            module["entry"] = rel_script
            manifest_changed = True
    else:
        modules.append({"type": "script", "language": "javascript", "entry": rel_script, "uuid": str(uuid.uuid4())})
        manifest["modules"] = modules
        manifest_changed = True

    dependencies = manifest.get("dependencies") if isinstance(manifest.get("dependencies"), list) else []
    if not any(isinstance(dep, dict) and dep.get("module_name") == "@minecraft/server" for dep in dependencies):
        dependencies.append({"module_name": "@minecraft/server", "version": [1, 0, 0]})
        manifest["dependencies"] = dependencies
        manifest_changed = True

    if entry_path and entry_path.is_file() and entry_path != script_path:
        import_line = f'import "./{script_path.relative_to(entry_path.parent).as_posix()}";'
        if import_line not in (entry_text or ""):
            entry_text = (entry_text or "").rstrip() + "\n\n" + import_line + "\n"

    snapshot_paths = [manifest_path]
    if script_path.exists():
        snapshot_paths.append(script_path)
    if entry_path and entry_path.is_file():
        snapshot_paths.append(entry_path)
    snapshot = history.create_snapshot("สร้าง Script Builder", snapshot_paths, source=str(root), status="กำลังแก้ไข")
    history_id = snapshot["id"]
    try:
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(build_source(event_id, blocks), encoding="utf-8")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if entry_path and entry_text is not None:
            entry_path.write_text(entry_text, encoding="utf-8")
    except OSError as exc:
        history.update_snapshot(history_id, status="ล้มเหลว")
        raise ValueError(f"สร้างไฟล์ไม่ได้: {exc}") from exc

    changed = [str(script_path), str(manifest_path)]
    if entry_path and entry_text is not None:
        changed.append(str(entry_path))
    history.update_snapshot(history_id, changed=changed, status="completed")
    return {
        "ok": True,
        "script_path": str(script_path),
        "manifest_path": str(manifest_path),
        "entry_path": str(entry_path) if entry_path and entry_text is not None else None,
        "manifest_changed": manifest_changed,
        "history_id": history_id,
    }
