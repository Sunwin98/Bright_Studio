"""Safe, local project snapshots used by every file-writing tool.

Snapshots live outside project folders so restoring a project never depends on
the add-on's own files.  Each entry contains the exact files or folders needed
to restore the state that existed before an action.
"""
from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import config


HISTORY_ROOT = config.SETTINGS_FILE.parent / ".storage" / "history"
MAX_SNAPSHOTS = 100


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _snapshot_dir(snapshot_id: str) -> Path:
    root = HISTORY_ROOT.resolve()
    target = (root / snapshot_id).resolve()
    if root not in target.parents:
        raise ValueError("snapshot id ไม่ถูกต้อง")
    return target


def _read_meta(snapshot_id: str) -> dict:
    folder = _snapshot_dir(snapshot_id)
    meta_path = folder / "meta.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"ไม่พบประวัติไฟล์: {snapshot_id}")
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"อ่านประวัติไฟล์ไม่ได้: {exc}") from exc
    if not isinstance(data, dict) or data.get("id") != snapshot_id:
        raise ValueError("ข้อมูลประวัติไฟล์ไม่ถูกต้อง")
    return data


def _prune() -> None:
    if not HISTORY_ROOT.is_dir():
        return
    entries = []
    for folder in HISTORY_ROOT.iterdir():
        if not folder.is_dir():
            continue
        try:
            meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
            entries.append((str(meta.get("created_at", "")), folder))
        except Exception:
            continue
    entries.sort(reverse=True)
    for _created, folder in entries[MAX_SNAPSHOTS:]:
        shutil.rmtree(folder, ignore_errors=True)


def create_snapshot(label: str, paths: list[str | Path], *, changed: list[str] | None = None,
                    source: str | None = None, status: str = "completed") -> dict:
    """Copy existing paths into a restore point and return its metadata."""
    roots: list[Path] = []
    seen: set[str] = set()
    for raw in paths:
        if not raw:
            continue
        path = Path(raw).expanduser().resolve()
        key = str(path).casefold()
        if key in seen or not path.exists():
            continue
        seen.add(key)
        roots.append(path)
    if not roots:
        raise ValueError("ไม่พบไฟล์หรือโฟลเดอร์สำหรับสร้างประวัติ")

    HISTORY_ROOT.mkdir(parents=True, exist_ok=True)
    snapshot_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    folder = _snapshot_dir(snapshot_id)
    payload_dir = folder / "payload"
    payload_dir.mkdir(parents=True)
    items = []

    for index, original in enumerate(roots):
        if original.is_dir():
            payload = payload_dir / str(index)
            shutil.copytree(original, payload)
            kind = "directory"
        else:
            payload = payload_dir / str(index) / original.name
            payload.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, payload)
            kind = "file"
        items.append({
            "original_path": str(original),
            "payload": str(payload.relative_to(folder)),
            "kind": kind,
            "name": original.name,
        })

    meta = {
        "id": snapshot_id,
        "label": str(label or "บันทึกสถานะไฟล์").strip(),
        "created_at": _now(),
        "status": status,
        "source": source,
        "changed": [str(p) for p in (changed or [])],
        "items": items,
    }
    (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _prune()
    return meta


def list_snapshots(limit: int = 100) -> list[dict]:
    HISTORY_ROOT.mkdir(parents=True, exist_ok=True)
    rows = []
    for folder in HISTORY_ROOT.iterdir():
        if not folder.is_dir():
            continue
        try:
            meta = _read_meta(folder.name)
            rows.append({
                "id": meta["id"],
                "label": meta.get("label", "บันทึกสถานะไฟล์"),
                "created_at": meta.get("created_at"),
                "status": meta.get("status", "completed"),
                "source": meta.get("source"),
                "changed_count": len(meta.get("changed") or []),
                "item_count": len(meta.get("items") or []),
            })
        except (FileNotFoundError, ValueError, OSError):
            continue
    rows.sort(key=lambda row: (row.get("created_at") or "", row.get("id") or ""), reverse=True)
    return rows[:max(1, min(int(limit or 100), MAX_SNAPSHOTS))]


def get_snapshot(snapshot_id: str) -> dict:
    meta = _read_meta(snapshot_id)
    return {
        **meta,
        "files": [
            {
                "name": item.get("name"),
                "path": item.get("original_path"),
                "kind": item.get("kind"),
            }
            for item in meta.get("items", [])
        ],
    }


def update_snapshot(snapshot_id: str, *, changed: list[str] | None = None,
                    status: str | None = None) -> dict:
    folder = _snapshot_dir(snapshot_id)
    meta = _read_meta(snapshot_id)
    if changed is not None:
        meta["changed"] = [str(item) for item in changed]
    if status is not None:
        meta["status"] = status
    (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def restore_snapshot(snapshot_id: str) -> dict:
    meta = _read_meta(snapshot_id)
    items = meta.get("items") or []
    originals = [item.get("original_path") for item in items if item.get("original_path")]
    backup = None
    existing = [path for path in originals if Path(path).exists()]
    if existing:
        backup = create_snapshot(
            "ก่อนกู้คืน " + str(meta.get("label") or "ประวัติไฟล์"),
            existing,
            source="restore",
        )

    restored = []
    folder = _snapshot_dir(snapshot_id)
    for item in items:
        original = Path(item["original_path"])
        payload = (folder / item["payload"]).resolve()
        if folder not in payload.parents or not payload.exists():
            raise ValueError("ข้อมูลไฟล์ในประวัติไม่ครบ")
        original.parent.mkdir(parents=True, exist_ok=True)
        if item.get("kind") == "directory":
            if original.exists():
                shutil.rmtree(original)
            shutil.copytree(payload, original)
        else:
            shutil.copy2(payload, original)
        restored.append(str(original))

    return {
        "restored": restored,
        "backup": backup,
        "snapshot": get_snapshot(snapshot_id),
    }


def delete_snapshot(snapshot_id: str) -> None:
    folder = _snapshot_dir(snapshot_id)
    _read_meta(snapshot_id)
    shutil.rmtree(folder)
