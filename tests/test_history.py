"""Project file history tests."""
import json

from app.core import history


def test_snapshot_lists_and_restores_a_folder(tmp_path, monkeypatch):
    history_root = tmp_path / "history"
    monkeypatch.setattr(history, "HISTORY_ROOT", history_root)
    project = tmp_path / "Demo_RP"
    project.mkdir()
    manifest = project / "manifest.json"
    manifest.write_text(json.dumps({"version": 1}), encoding="utf-8")
    (project / "textures").mkdir()
    (project / "textures" / "sword.png").write_bytes(b"old")

    snapshot = history.create_snapshot("ก่อนปรับไอเทม", [project], source=str(project))
    manifest.write_text(json.dumps({"version": 2}), encoding="utf-8")
    (project / "textures" / "sword.png").write_bytes(b"new")
    (project / "new.json").write_text("{}", encoding="utf-8")

    result = history.restore_snapshot(snapshot["id"])

    assert json.loads(manifest.read_text(encoding="utf-8"))["version"] == 1
    assert (project / "textures" / "sword.png").read_bytes() == b"old"
    assert not (project / "new.json").exists()
    assert result["backup"]["label"].startswith("ก่อนกู้คืน")
    assert history.list_snapshots(10)[0]["label"].startswith("ก่อนกู้คืน")


def test_snapshot_delete_does_not_touch_project(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY_ROOT", tmp_path / "history")
    file_path = tmp_path / "one.json"
    file_path.write_text("{}", encoding="utf-8")

    snapshot = history.create_snapshot("จุดทดสอบ", [file_path])
    history.delete_snapshot(snapshot["id"])

    assert file_path.exists()
    assert history.list_snapshots() == []
