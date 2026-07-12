"""Script Lab hot-sync: saved file → deployed copy under com.mojang."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from app.core.scriptlab import sync


def _manifest(uuid: str) -> str:
    return json.dumps({
        "format_version": 2,
        "header": {"name": "T", "uuid": uuid, "version": [1, 0, 0]},
        "modules": [{"type": "data", "uuid": "m-" + uuid, "version": [1, 0, 0]}],
    })


def _mk_pack(root: Path, uuid: str, content: str = "old") -> Path:
    root.mkdir(parents=True)
    (root / "manifest.json").write_text(_manifest(uuid), encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "main.js").write_text(content, encoding="utf-8")
    return root

UUID = "11111111-2222-3333-4444-555555555555"


def _fake_profiles(mojang: Path):
    return lambda: [{"name": "User: test", "path": str(mojang)}]


def test_sync_copies_to_deployed(tmp_path, monkeypatch):
    src = _mk_pack(tmp_path / "work" / "My_BP", UUID, "NEW CONTENT")
    mojang = tmp_path / "com.mojang"
    _mk_pack(mojang / "development_behavior_packs" / "My_BP", UUID, "old")
    monkeypatch.setattr(config, "find_profiles", _fake_profiles(mojang))

    r = sync.sync_to_dev(str(src / "scripts" / "main.js"))
    assert r.get("already_in_game") is False
    assert len(r["synced"]) == 1
    target = Path(r["synced"][0])
    assert target.read_text(encoding="utf-8") == "NEW CONTENT"


def test_already_in_game(tmp_path, monkeypatch):
    mojang = tmp_path / "com.mojang"
    dev = _mk_pack(mojang / "development_behavior_packs" / "My_BP", UUID)
    monkeypatch.setattr(config, "find_profiles", _fake_profiles(mojang))

    r = sync.sync_to_dev(str(dev / "scripts" / "main.js"))
    assert r.get("already_in_game") is True
    assert r["synced"] == []


def test_no_manifest_no_sync(tmp_path, monkeypatch):
    loose = tmp_path / "loose"
    loose.mkdir()
    f = loose / "main.js"
    f.write_text("x", encoding="utf-8")
    monkeypatch.setattr(config, "find_profiles", lambda: [])

    r = sync.sync_to_dev(str(f))
    assert r["synced"] == []


def test_uuid_mismatch_not_synced(tmp_path, monkeypatch):
    src = _mk_pack(tmp_path / "work" / "My_BP", UUID, "NEW")
    mojang = tmp_path / "com.mojang"
    _mk_pack(mojang / "development_behavior_packs" / "Other_BP",
             "99999999-8888-7777-6666-555555555555", "old")
    monkeypatch.setattr(config, "find_profiles", _fake_profiles(mojang))

    r = sync.sync_to_dev(str(src / "scripts" / "main.js"))
    assert r["synced"] == []
