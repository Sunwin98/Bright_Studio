"""packio: archive/folder → BP/RP auto-classification."""
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import packio


def _manifest(ptype: str, name: str) -> dict:
    mod_type = "data" if ptype == "behavior" else "resources"
    return {
        "format_version": 2,
        "header": {"name": name, "uuid": "00000000-0000-0000-0000-000000000001",
                   "version": [1, 0, 0], "min_engine_version": [1, 20, 0]},
        "modules": [{"type": mod_type, "uuid": "00000000-0000-0000-0000-000000000002",
                     "version": [1, 0, 0]}],
    }


def _make_pack(root: Path, folder: str, ptype: str, name: str) -> Path:
    d = root / folder
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps(_manifest(ptype, name)), encoding="utf-8")
    return d


def test_folder_with_bp_rp(tmp_path):
    _make_pack(tmp_path, "Cool_BP", "behavior", "Cool BP")
    _make_pack(tmp_path, "Cool_RP", "resource", "Cool RP")
    r = packio.inspect_source(str(tmp_path))
    assert r["bp_path"].endswith("Cool_BP")
    assert r["rp_path"].endswith("Cool_RP")
    assert len(r["packs"]) == 2


def test_single_pack_folder(tmp_path):
    d = _make_pack(tmp_path, "OnlyRP", "resource", "Only RP")
    r = packio.inspect_source(str(d))
    assert r["bp_path"] is None
    assert r["rp_path"] == str(d)


def test_mcaddon_archive(tmp_path):
    src = tmp_path / "src"
    _make_pack(src, "A_BP", "behavior", "A BP")
    _make_pack(src, "A_RP", "resource", "A RP")
    archive = tmp_path / "a.mcaddon"
    with zipfile.ZipFile(archive, "w") as zf:
        for f in src.rglob("*"):
            zf.write(f, f.relative_to(src))
    r = packio.inspect_source(str(archive))
    assert r["bp_path"] and r["bp_path"].endswith("A_BP")
    assert r["rp_path"] and r["rp_path"].endswith("A_RP")
    # Repeat inspection reuses the same extraction dir.
    r2 = packio.inspect_source(str(archive))
    assert r2["bp_path"] == r["bp_path"]


def test_rejects_unknown_ext(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hi", encoding="utf-8")
    try:
        packio.inspect_source(str(f))
        assert False, "should have raised"
    except ValueError:
        pass


def test_missing_path():
    try:
        packio.inspect_source(r"C:\definitely\missing\path.mcaddon")
        assert False, "should have raised"
    except FileNotFoundError:
        pass
